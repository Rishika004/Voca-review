import os
import json
import base64
import struct
import time
import aiohttp
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from dotenv import load_dotenv
from app.services.llm_service import generate_response, reset_conversation
from app.services.deepgram_service import DeepgramStreamingService
from app.services.sentiment_service import analyze_sentiment, extract_email, extract_name, extract_meeting_time
from app.utils.logging_config import get_logger

router = APIRouter()
logger = get_logger(__name__)

load_dotenv()
ELEVEN_LABS_API_KEY = os.getenv("ELEVEN_LABS_API_KEY")
VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"
MODEL_ID = "eleven_turbo_v2_5"


def extract_pcm_from_wav(wav_bytes: bytes) -> bytes:
    if len(wav_bytes) < 44 or wav_bytes[:4] != b"RIFF":
        return wav_bytes
    pos = 12
    while pos < len(wav_bytes) - 8:
        chunk_id = wav_bytes[pos:pos+4]
        chunk_size = struct.unpack("<I", wav_bytes[pos+4:pos+8])[0]
        if chunk_id == b"data":
            return wav_bytes[pos+8: pos+8+chunk_size]
        pos += 8 + chunk_size
    return b""


@router.websocket("/agent/voice")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket connection accepted")

    reset_conversation()

    # Session state — updated as the call progresses
    session = {
        "lead_name": None,
        "lead_email": None,
        "meeting_time": None,
        "overall_sentiment": "Neutral",
        "sentiment_counts": {"Positive": 0, "Neutral": 0, "Negative": 0},
    }

    async def on_transcript(transcript: str):
        turn_start = time.perf_counter()
        logger.info(f"{'='*60}")
        logger.info(f"TRANSCRIPT: '{transcript}'")

        # Sentiment + lead extraction (fast, no API call)
        sentiment = analyze_sentiment(transcript)
        session["sentiment_counts"][sentiment] += 1
        counts = session["sentiment_counts"]
        session["overall_sentiment"] = max(counts, key=counts.get)

        if not session["lead_name"]:
            name = extract_name(transcript)
            if name:
                session["lead_name"] = name

        if not session["lead_email"]:
            email = extract_email(transcript)
            if email:
                session["lead_email"] = email

        if not session["meeting_time"]:
            meeting = extract_meeting_time(transcript)
            if meeting:
                session["meeting_time"] = meeting

        # LLM
        llm_start = time.perf_counter()
        agent_reply = generate_response(transcript)
        llm_ms = (time.perf_counter() - llm_start) * 1000
        logger.info(f"LLM: {llm_ms:.0f}ms → '{agent_reply}'")

        # Send text + metadata to browser
        await websocket.send_json({
            "type": "transcript",
            "user_text": transcript,
            "agent_reply": agent_reply,
            "sentiment": sentiment,
            "overall_sentiment": session["overall_sentiment"],
            "lead_name": session["lead_name"],
            "lead_email": session["lead_email"],
            "meeting_time": session["meeting_time"],
        })

        # TTS — ElevenLabs WebSocket streaming
        tts_start = time.perf_counter()
        first_chunk = True
        total_bytes = 0
        url = f"wss://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}/stream-input?model_id={MODEL_ID}"

        try:
            async with aiohttp.ClientSession() as session_http:
                async with session_http.ws_connect(url) as el_ws:
                    await el_ws.send_json({
                        "text": " ",
                        "xi_api_key": ELEVEN_LABS_API_KEY,
                        "voice_settings": {
                            "stability": 0.4,
                            "similarity_boost": 0.8,
                            "style": 0.1,
                            "use_speaker_boost": True
                        },
                    })
                    await el_ws.send_json({"text": agent_reply, "flush": True})
                    await el_ws.send_json({"text": ""})

                    while True:
                        msg = await el_ws.receive()
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            data = json.loads(msg.data)
                            if data.get("audio"):
                                chunk = base64.b64decode(data["audio"])
                                await websocket.send_bytes(chunk)
                                total_bytes += len(chunk)
                                if first_chunk:
                                    ttfb = (time.perf_counter() - tts_start) * 1000
                                    logger.info(f"TTS first byte: {ttfb:.0f}ms")
                                    first_chunk = False
                            if data.get("isFinal"):
                                break
                        elif msg.type in [aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR]:
                            break
        except Exception as e:
            logger.error(f"TTS error: {e}")

        total_ms = (time.perf_counter() - turn_start) * 1000
        logger.info(f"TOTAL TURN: {total_ms:.0f}ms | TTS bytes: {total_bytes}")
        logger.info(f"{'='*60}")

    dg = DeepgramStreamingService(on_transcript)
    try:
        await dg.connect()
    except Exception as e:
        logger.error(f"Deepgram connect failed: {e}")
        await websocket.close()
        return

    try:
        while True:
            raw = await websocket.receive()
            raw_bytes = raw.get("bytes")
            raw_text = raw.get("text")
            if raw_bytes:
                pcm = extract_pcm_from_wav(raw_bytes)
                if pcm:
                    await dg.send_audio(pcm)
            elif raw_text:
                # Control messages from frontend
                try:
                    msg = json.loads(raw["text"])
                    if msg.get("type") == "call_ended":
                        # Send final session state back so frontend can POST to /api/calls/end
                        await websocket.send_json({
                            "type": "call_summary",
                            "lead_name": session["lead_name"],
                            "lead_email": session["lead_email"],
                            "overall_sentiment": session["overall_sentiment"],
                        })
                except Exception:
                    pass
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await dg.close()
