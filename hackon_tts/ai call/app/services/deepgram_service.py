import os
import json
import asyncio
import aiohttp
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
DEEPGRAM_URL = (
    "wss://api.deepgram.com/v1/listen"
    "?model=nova-2"
    "&language=en"
    "&punctuate=true"
    "&smart_format=true"
    "&interim_results=true"
    "&utterance_end_ms=1000"
    "&vad_events=true"
    "&encoding=linear16"
    "&sample_rate=16000"
    "&channels=1"
)


class DeepgramStreamingService:
    """
    Streams audio to Deepgram in real-time.
    Calls on_transcript(text) when a final transcript is ready.
    """

    def __init__(self, on_transcript):
        self.on_transcript = on_transcript
        self._dg_ws = None
        self._session = None
        self._recv_task = None
        self._connected = False

    async def connect(self):
        """Open Deepgram WebSocket connection."""
        self._session = aiohttp.ClientSession()
        headers = {"Authorization": f"Token {DEEPGRAM_API_KEY}"}
        self._dg_ws = await self._session.ws_connect(DEEPGRAM_URL, headers=headers)
        self._connected = True
        self._recv_task = asyncio.create_task(self._receive_loop())
        logger.info("Deepgram WebSocket connected")

    async def send_audio(self, pcm_bytes: bytes):
        """Send raw PCM16 audio bytes to Deepgram."""
        if self._connected and self._dg_ws:
            await self._dg_ws.send_bytes(pcm_bytes)

    async def _receive_loop(self):
        """Listen for Deepgram transcript events."""
        import time
        try:
            async for msg in self._dg_ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    msg_type = data.get("type", "")

                    if msg_type == "Results":
                        channel = data.get("channel", {})
                        alternatives = channel.get("alternatives", [])
                        if not alternatives:
                            continue

                        transcript = alternatives[0].get("transcript", "").strip()
                        is_final = data.get("is_final", False)
                        speech_final = data.get("speech_final", False)

                        if transcript:
                            logger.info(
                                f"Deepgram {'FINAL' if is_final else 'interim'}: '{transcript}'"
                            )

                        # Trigger on speech_final (end of utterance detected)
                        if speech_final and transcript:
                            logger.info(f"Speech final — triggering pipeline: '{transcript}'")
                            try:
                                await self.on_transcript(transcript)
                            except Exception as cb_err:
                                logger.error(f"on_transcript callback error: {cb_err}")

                    elif msg_type == "UtteranceEnd":
                        logger.info("Deepgram UtteranceEnd received")

        except Exception as e:
            logger.error(f"Deepgram receive loop error: {e}")

    async def close(self):
        """Close Deepgram connection."""
        self._connected = False
        if self._dg_ws:
            await self._dg_ws.close()
        if self._session:
            await self._session.close()
        if self._recv_task:
            self._recv_task.cancel()
        logger.info("Deepgram connection closed")
