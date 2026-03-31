from fastapi import FastAPI
from app.api import stt, chat
# from app.api.tts_stream import router as tts_ws_router
from app.api.agent_voice import router as agent_voice_router
from app.utils.logging_config import setup_logging, get_logger

# Initialize logging for real-time output
setup_logging(level="INFO", force_flush=True)
logger = get_logger(__name__)

app = FastAPI()

logger.info("🚀 AI Call Backend starting up...")
logger.info("📝 Real-time logging configured")

app.include_router(stt.router, prefix="/stt", tags=["STT"])
app.include_router(chat.router , prefix="/agent", tags=["Chat"])
# app.include_router(tts_ws_router, prefix="/api", tags=["TTS"])
app.include_router(agent_voice_router, prefix="/api", tags=["Agent voice"])

logger.info("✅ All routers registered successfully")
logger.info("🔗 WebSocket endpoint available at: ws://127.0.0.1:8000/api/agent/voice")
