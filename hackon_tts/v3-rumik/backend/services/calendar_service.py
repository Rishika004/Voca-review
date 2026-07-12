"""
Google Calendar integration: check availability + create demo events.

One-time setup: run `python google_auth_setup.py` (needs credentials.json from
Google Cloud Console) to generate token.json. After that this module just works.
"""
import os
import logging
from datetime import datetime, timedelta

from dotenv import load_dotenv
load_dotenv()

import dateparser
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/calendar"]
TOKEN_FILE = os.getenv(
    "GOOGLE_TOKEN_FILE",
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "token.json"),
)
TIMEZONE = os.getenv("CALENDAR_TIMEZONE", "Asia/Kolkata")
DEMO_MINUTES = int(os.getenv("DEMO_DURATION_MINUTES", "15"))


def _get_service():
    if not os.path.exists(TOKEN_FILE):
        raise RuntimeError("token.json not found — run `python google_auth_setup.py` first")
    creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        try:
            with open(TOKEN_FILE, "w") as f:
                f.write(creds.to_json())
        except OSError:
            pass  # read-only secret mount (e.g. Render) — refreshed creds live in memory
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def parse_time(text: str) -> datetime | None:
    """Turn natural language like 'tomorrow at 3pm' into a datetime."""
    dt = dateparser.parse(
        text,
        settings={
            "TIMEZONE": TIMEZONE,
            "RETURN_AS_TIMEZONE_AWARE": True,
            "PREFER_DATES_FROM": "future",
        },
    )
    return dt


def check_availability(when_text: str) -> dict:
    """Free/busy check for a natural-language time. Returns dict with status."""
    start = parse_time(when_text)
    if not start:
        return {"ok": False, "reason": f"Could not understand the time '{when_text}'"}
    end = start + timedelta(minutes=DEMO_MINUTES)

    service = _get_service()
    resp = service.freebusy().query(body={
        "timeMin": start.isoformat(),
        "timeMax": end.isoformat(),
        "timeZone": TIMEZONE,
        "items": [{"id": "primary"}],
    }).execute()
    busy = resp["calendars"]["primary"].get("busy", [])

    if not busy:
        return {"ok": True, "available": True, "start": start.isoformat(),
                "pretty": start.strftime("%A, %B %d at %I:%M %p")}

    # Suggest next free slot: try hourly slots after the requested time (working hours 9-19)
    probe = start
    for _ in range(16):
        probe = probe + timedelta(hours=1)
        if probe.hour < 9:
            probe = probe.replace(hour=9, minute=0)
        if probe.hour >= 19:
            probe = (probe + timedelta(days=1)).replace(hour=9, minute=0)
        p_end = probe + timedelta(minutes=DEMO_MINUTES)
        r = service.freebusy().query(body={
            "timeMin": probe.isoformat(),
            "timeMax": p_end.isoformat(),
            "timeZone": TIMEZONE,
            "items": [{"id": "primary"}],
        }).execute()
        if not r["calendars"]["primary"].get("busy", []):
            return {"ok": True, "available": False,
                    "suggestion": probe.strftime("%A, %B %d at %I:%M %p")}
    return {"ok": True, "available": False, "suggestion": None}


def create_event(when_text: str, lead_name: str, lead_email: str | None) -> dict:
    """Create the demo event, invite the lead, attach a Google Meet link."""
    start = parse_time(when_text)
    if not start:
        return {"ok": False, "reason": f"Could not understand the time '{when_text}'"}
    end = start + timedelta(minutes=DEMO_MINUTES)

    service = _get_service()
    body = {
        "summary": f"Karta Demo — {lead_name or 'Lead'}",
        "description": "15-minute Karta product demo booked by Aria (AI sales agent).",
        "start": {"dateTime": start.isoformat(), "timeZone": TIMEZONE},
        "end": {"dateTime": end.isoformat(), "timeZone": TIMEZONE},
        "conferenceData": {
            "createRequest": {
                "requestId": f"aria-{int(start.timestamp())}",
                "conferenceSolutionKey": {"type": "hangoutsMeet"},
            }
        },
        "reminders": {"useDefault": True},
    }
    if lead_email:
        body["attendees"] = [{"email": lead_email}]

    event = service.events().insert(
        calendarId="primary",
        body=body,
        conferenceDataVersion=1,
        sendUpdates="all",  # emails the invite to the lead automatically
    ).execute()

    meet_link = event.get("hangoutLink", "")
    logger.info(f"Calendar event created: {event.get('htmlLink')} meet={meet_link}")
    return {
        "ok": True,
        "pretty": start.strftime("%A, %B %d at %I:%M %p"),
        "meet_link": meet_link,
        "event_link": event.get("htmlLink", ""),
    }
