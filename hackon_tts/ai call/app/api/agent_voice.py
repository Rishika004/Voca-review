import os
import json
import base64
import aiohttp
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from dotenv import load_dotenv
from app.services.llm_service import generate_response
from app.services.streaming_service import AudioStreamingService
from app.utils.logging_config import get_logger

router = APIRouter()
logger = get_logger(__name__)

load_dotenv()
API_KEY = os.getenv("ELEVEN_LABS_API_KEY")
VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"
MODEL_ID = "eleven_turbo_v2_5"


@router.websocket("/agent/voice")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("🔌 WebSocket connection accepted.")

    # This function will be called by the streaming service when a transcription is ready
    async def on_transcription_update(transcription: str):
        logger.info(f"📝 Transcription received: '{transcription}'")

        # 1. Generate AI response
        logger.info("🧠 Generating AI response...")
        agent_reply = generate_response(transcription)
        logger.info(f"💬 AI response generated: '{agent_reply}'")

        # 2. Send text response to client
        await websocket.send_json({"user_text": transcription, "agent_reply": agent_reply})
        logger.info("✅ Text response sent to client.")

        # 3. Stream TTS audio from ElevenLabs
        logger.info("🔊 Starting ElevenLabs TTS streaming...")
        url = f"wss://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}/stream-input?model_id={MODEL_ID}"

        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(url) as el_ws:
                await el_ws.send_json({
                    "text": " ",
                    "xi_api_key": API_KEY,
                    "voice_settings": {"stability": 0.5, "similarity_boost": 0.8},
                })

                await el_ws.send_json({"text": agent_reply, "flush": True})
                await el_ws.send_json({"text": ""})  # End marker

                logger.info("⏳ Receiving audio stream from ElevenLabs...")
                audio_chunks = []
                while True:
                    msg = await el_ws.receive()
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        data = json.loads(msg.data)
                        if data.get("audio"):
                            audio_chunks.append(base64.b64decode(data["audio"]))
                        if data.get("isFinal"):
                            break
                    elif msg.type in [aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR]:
                        break

                if audio_chunks:
                    complete_audio = b"".join(audio_chunks)
                    await websocket.send_bytes(complete_audio)
                    logger.info(f"✅ Sent {len(complete_audio)} bytes of audio to client.")

    # Initialize the streaming service for this connection
    streaming_service = AudioStreamingService(on_transcription_update)

    try:
        while True:
            # Receive audio data from the client
            data = await websocket.receive_bytes()
            
            # Process the audio chunk with the streaming service
            await streaming_service.process_audio_chunk(data)

    except WebSocketDisconnect:
        logger.info("🔌 WebSocket connection closed.")
    except Exception as e:
        logger.error(f"❌ An error occurred in the WebSocket: {e}")
