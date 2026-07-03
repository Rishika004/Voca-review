import os
import logging
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
import uuid
from datetime import datetime
from dotenv import load_dotenv
from app.services.email_service import send_meeting_confirmation

load_dotenv()
router = APIRouter()
logger = logging.getLogger(__name__)

NOTIFY_EMAIL = os.getenv("NOTIFY_EMAIL", "rishikathakur607@gmail.com")

call_records: List[dict] = []


class CallRecord(BaseModel):
    transcript: List[dict]
    lead_name: Optional[str] = None
    lead_email: Optional[str] = None
    meeting_time: Optional[str] = None
    duration_seconds: int = 0
    overall_sentiment: str = "Neutral"
    summary: str = ""


@router.post("/end")
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

    # Send emails if meeting was booked and we have the lead's email
    logger.info(f"Call ended — meeting_time='{record.meeting_time}' lead_email='{record.lead_email}'")
    if record.meeting_time and record.lead_email and record.lead_email != "—":
        logger.info("Sending meeting confirmation emails…")
        success = send_meeting_confirmation(
            lead_name=record.lead_name or "there",
            lead_email=record.lead_email,
            meeting_time=record.meeting_time,
            notify_email=NOTIFY_EMAIL,
        )
        logger.info(f"Email send result: {'SUCCESS' if success else 'FAILED'}")
    else:
        logger.warning(f"Email NOT sent — missing meeting_time or lead_email")

    return {"call_id": call_id, "status": "saved"}


@router.get("/history")
async def get_call_history():
    return {"calls": list(reversed(call_records))}
