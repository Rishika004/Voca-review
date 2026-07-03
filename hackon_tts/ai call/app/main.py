from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.agent_voice import router as agent_voice_router
from app.api.calls import router as calls_router
from app.utils.logging_config import setup_logging, get_logger

# Initialize logging for real-time output
setup_logging(level="INFO", force_flush=True)
logger = get_logger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger.info("🚀 AI Call Backend starting up...")
logger.info("📝 Real-time logging configured")

app.include_router(agent_voice_router, prefix="/api", tags=["Agent voice"])
app.include_router(calls_router, prefix="/api/calls", tags=["Calls"])

logger.info("✅ All routers registered successfully")
logger.info("🔗 WebSocket endpoint available at: ws://127.0.0.1:8000/api/agent/voice")
