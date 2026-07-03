"""
Token server + Calls API for Aria v2.
Run alongside agent.py: uvicorn server:app --port 8001
"""
import os
import uuid
import logging
from datetime import datetime, timedelta
from typing import List, Optional

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from livekit.api import AccessToken, VideoGrants, LiveKitAPI
from livekit.protocol.agent_dispatch import CreateAgentDispatchRequest

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger(__name__)
call_records: List[dict] = []

LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET")
LIVEKIT_URL = os.getenv("LIVEKIT_URL")
NOTIFY_EMAIL = os.getenv("NOTIFY_EMAIL", "rishikathakur607@gmail.com")


@app.get("/api/token")
async def get_token():
    """Generate a LiveKit token in a fresh unique room and dispatch Aria."""
    if not LIVEKIT_API_KEY or not LIVEKIT_API_SECRET:
        raise HTTPException(status_code=500, detail="LiveKit credentials not configured")

    # Unique room per call — prevents double-dispatch collisions
    room = f"aria-{uuid.uuid4().hex[:8]}"
    identity = f"user-{uuid.uuid4().hex[:6]}"

    token = (
        AccessToken(api_key=LIVEKIT_API_KEY, api_secret=LIVEKIT_API_SECRET)
        .with_grants(VideoGrants(room_join=True, room=room, can_publish=True, can_subscribe=True))
        .with_identity(identity)
        .with_ttl(timedelta(hours=1))
        .to_jwt()
    )

    # Room is unique per call (UUID), so we dispatch directly — no collision check needed
    try:
        async with LiveKitAPI(
            url=LIVEKIT_URL,
            api_key=LIVEKIT_API_KEY,
            api_secret=LIVEKIT_API_SECRET,
        ) as lk:
            await lk.agent_dispatch.create_dispatch(
                CreateAgentDispatchRequest(room=room, agent_name="aria")
            )
            logger.info(f"Agent dispatched to room: {room}")
    except Exception as e:
        logger.error(f"Agent dispatch failed: {e}")
        raise HTTPException(status_code=500, detail=f"Agent dispatch failed: {e}")

    return {"token": token, "url": LIVEKIT_URL, "room": room, "identity": identity}


class CallRecord(BaseModel):
    transcript: List[dict]
    lead_name: Optional[str] = None
    lead_email: Optional[str] = None
    meeting_time: Optional[str] = None
    duration_seconds: int = 0
    overall_sentiment: str = "Neutral"
    summary: str = ""


@app.post("/api/calls/end")
async def end_call(record: CallRecord):
    call_id = f"call_{uuid.uuid4().hex[:8]}"
    entry = {
        "call_id": call_id,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "lead_name": record.lead_name or "Unknown",
        "lead_email": record.lead_email or "—",
        "meeting_time": record.meeting_time or "—",
        "meeting_status": "Scheduled" if record.meeting_time else "Not booked",
        "duration_seconds": record.duration_seconds,
        "overall_sentiment": record.overall_sentiment,
        "summary": record.summary,
        "transcript": record.transcript,
        "resolution_status": "Completed",
    }
    call_records.append(entry)
    logger.info(f"Call saved: {call_id}")
    return {"call_id": call_id, "status": "saved"}


@app.get("/api/calls/history")
async def get_call_history():
    return {"calls": list(reversed(call_records))}
