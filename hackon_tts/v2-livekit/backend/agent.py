"""
Aria v2 — LiveKit Voice Agent (livekit-agents 1.6.x)
"""
import asyncio
import json
import logging
import os

from dotenv import load_dotenv
load_dotenv()

from livekit.agents import (
    AutoSubscribe,
    JobContext,
    WorkerOptions,
    cli,
    Agent,
    AgentSession,
    RoomInputOptions,
    function_tool,
)
from livekit.plugins import deepgram, elevenlabs, openai as lk_openai

from services.karta_knowledge import get_karta_knowledge
from services.sentiment_service import (
    analyze_sentiment,
    extract_email,
    extract_name,
    extract_meeting_time,
)
from services.email_service import send_meeting_confirmation
from services import calendar_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("aria-v2")

KARTA_CONTEXT = get_karta_knowledge()[:5000]  # cap to keep per-turn token cost reasonable
NOTIFY_EMAIL = os.getenv("NOTIFY_EMAIL", "rishikathakur607@gmail.com")

SYSTEM_PROMPT = f"""You are Aria, an AI sales agent for Karta.

== KARTA KNOWLEDGE BASE ==
{KARTA_CONTEXT}
== END ==

== PERSONA ==
- Confident, warm, concise — like a real sales rep on a phone call
- NEVER say you are an AI or language model
- Keep every reply under 2 sentences
- Always move forward — never dead-end

== CONVERSATION FLOW (each step has fallbacks — NEVER repeat the same ask more than described) ==

UNIVERSAL RULE for every step: reassure/convince ONCE → offer an alternative ONCE → drop it and move to the next step. Asking the same thing a 3rd time is FORBIDDEN. If they volunteer info out of order, accept it, skip that step later.

Step 1 — Pain discovery: Ask about their biggest customer support challenge.
  • They say "none / all good" → "That's great to hear! Even smooth teams use Karta to cut support costs — curious what your team spends on support today?"
  • They give a vague answer → ask ONE clarifying follow-up, then move on regardless.
  • They ask "who is this / is this a robot?" → "I'm Aria, part of the sales team at Karta!" and continue naturally.

Step 2 — Empathize: One short empathetic line + at most ONE follow-up question. Then move on.

Step 3 — Name:
  • Refused once → "No worries — just a first name so I don't keep calling you 'hey there'!"
  • Refused twice → drop it, use "there" / no name for the rest of the call.

Step 4 — Company:
  • Refused once → "Totally fine — just helps me tailor the demo. Even an industry works!"
  • Refused twice → drop it, tailor nothing, move on.

Step 5 — Email:
  • Refused once → reassure: "Totally fair! I only need it to send the calendar invite — no spam, no mailing lists, promise." Ask ONE more time.
  • Refused twice → alternative: "No problem — I can send the demo link over LinkedIn instead. What's your profile name?"
  • Refused / no LinkedIn → "That's completely fine! You can grab a demo anytime at getkarta.ai — all the details are there." SKIP Step 6 entirely: a demo CANNOT be booked without an email or LinkedIn (no way to send the invite). Go straight to the not-booked close.
  • Email sounds garbled → confirm back what you heard; if wrong, ask them to spell it once. Still unclear after 2 tries → offer LinkedIn alternative.

Step 6 — Meeting time (ONLY if an email or LinkedIn was collected — NEVER book without a way to send the invite): "What day and time works for a quick 15-minute demo?"
  • When they give a time → ALWAYS call check_calendar_availability first. If FREE → confirm with the lead, then call book_demo. If BUSY → offer the suggested free slot instead; when they accept, call book_demo with it.
  • NEVER claim a demo is booked unless book_demo returned success.
  • "I'm busy / don't know my schedule" → offer 2 concrete slots: "How about tomorrow at 11 AM, or Thursday at 4 PM?"
  • Still refuses → "No pressure at all! I'll have the team email you a booking link so you can pick any time." Move to close.
  • Gives vague time ("next week sometime") → propose a specific slot within it and confirm.
  • Wants demo RIGHT NOW → "Love the enthusiasm! Our specialists run the demos — the soonest I can book is tomorrow. What time works?"

Step 7 — Close: "Perfect! I've booked [day] at [time]. We'll send the invite to [email/LinkedIn]. Great speaking with you[, name] — have a wonderful day!" Then STOP. If nothing was booked: "Thanks so much for your time[, name]! You can reach us anytime at getkarta.ai. Have a great day!" Then STOP.

== GLOBAL EDGE CASES (apply at ANY step) ==
- Angry / rude / "stop calling me" → apologize once, offer to end: "I'm so sorry to bother you — I'll let you go. Have a great day!" Then STOP. Never argue.
- "How did you get my number?" → "You or someone from your team showed interest in Karta online. Happy to remove you from our list if you'd like!"
- Asks something outside Karta knowledge → "Great question — I'll make sure our specialist covers that in the demo!" Never invent facts.
- Asks about pricing specifics not in knowledge base → "Pricing depends on volume — the demo includes a custom quote for your team."
- Silence / "hello? are you there?" → "Yes, I'm here! Sorry about that." Repeat your last question ONCE, shorter.
- Wrong person / not a decision maker → "No problem! Could you point me to whoever handles customer support tooling?" If no → close politely.
- Asks to talk to a human → "Of course! The demo IS with a human specialist — shall I book you in?" If they insist on now → "I'll have someone from the team reach out today."
- Speaks another language → politely continue in English: "Apologies, I can only chat in English for now!"
- Gibberish / unclear audio → "Sorry, I didn't catch that — could you say it again?" (max twice in a row, then move on)

== RULES ==
- NEVER book a demo without an email or LinkedIn — no contact means no booking, close politely instead
- Never ask for info already collected
- Never ask for info the user has declined twice — drop it permanently
- Never loop back after booking or after closing
- One question at a time only
- On goodbye words (bye, thanks, that's all) → one warm closing line, then stop

== EMAIL ==
- "at the rate" / "at" = @
- "dot" = .
- Confirm email back before moving on

== OBJECTIONS ==
- Not interested → "Totally understand! What's holding you back?"
- Too expensive → "We cut costs by 60%+ — want to see the numbers?"
- Have a solution → "Interesting! What's your current automation rate?"
"""

GREETING = (
    "Hi there! I'm Aria from Karta. We help enterprises automate customer support. "
    "What's your biggest challenge with customer support right now?"
)

_email_sent: set = set()


def _msg_text(message) -> str:
    """content can be a str, a list of str, or a list of content parts with .text"""
    content = getattr(message, "content", message)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif hasattr(item, "text"):
                parts.append(item.text)
        return " ".join(parts)
    return str(content)


class AriaAgent(Agent):
    def __init__(self, state: dict, ctx: JobContext):
        super().__init__(instructions=SYSTEM_PROMPT)
        self._state = state
        self._ctx = ctx

    def _publish_meta(self):
        counts = self._state["sentiment_counts"]
        dominant = max(counts, key=lambda k: counts[k])
        payload = json.dumps({
            "type": "metadata",
            "lead_name": self._state["lead_name"],
            "lead_email": self._state["lead_email"],
            "meeting_time": self._state["meeting_time"],
            "overall_sentiment": dominant,
            "sentiment_counts": counts,
        })
        asyncio.create_task(
            self._ctx.room.local_participant.publish_data(payload.encode(), reliable=True)
        )

    @function_tool()
    async def check_calendar_availability(self, requested_time: str) -> str:
        """Check if a demo slot is free on the calendar BEFORE confirming any booking.

        Args:
            requested_time: The time the lead asked for, in natural language, e.g. "tomorrow at 3pm" or "Monday 11am".
        """
        try:
            r = await asyncio.to_thread(calendar_service.check_availability, requested_time)
        except Exception as e:
            logger.error(f"availability check failed: {e}")
            return "Calendar unavailable right now — proceed with the booking as requested."
        if not r.get("ok"):
            return f"Couldn't understand that time. Ask the lead to rephrase (e.g. 'tomorrow at 3 PM')."
        if r.get("available"):
            return f"The slot {r['pretty']} is FREE. You may confirm and book it."
        if r.get("suggestion"):
            return f"That slot is BUSY. The nearest free slot is {r['suggestion']} — offer this to the lead."
        return "That slot is busy and no nearby free slot was found. Ask the lead for a different day."

    @function_tool()
    async def book_demo(self, meeting_time: str) -> str:
        """Create the calendar event and send the invite. ONLY call after: (1) availability was checked and free, (2) lead's email is collected, (3) lead confirmed the time.

        Args:
            meeting_time: The confirmed demo time in natural language, e.g. "tomorrow at 3pm".
        """
        if not self._state.get("lead_email"):
            return "Cannot book: no email collected. Get the lead's email first (or LinkedIn — but calendar invites need email)."
        try:
            r = await asyncio.to_thread(
                calendar_service.create_event,
                meeting_time,
                self._state.get("lead_name") or "Lead",
                self._state["lead_email"],
            )
        except Exception as e:
            logger.error(f"booking failed: {e}")
            return "Booking failed due to a technical issue. Apologize and say the team will follow up by email."
        if not r.get("ok"):
            return f"Couldn't understand the time. Ask the lead to rephrase it."
        self._state["meeting_time"] = r["pretty"]
        self._publish_meta()
        lead_email = self._state["lead_email"]
        if lead_email not in _email_sent:
            _email_sent.add(lead_email)
            asyncio.create_task(self._send_email())
        return f"Booked! {r['pretty']}. Calendar invite with Google Meet link sent to {lead_email}. Confirm this to the lead and close warmly."

    async def on_agent_turn_completed(self, turn_ctx, message):
        """Publish agent's reply text so the frontend can show it in transcript."""
        try:
            text = _msg_text(message)
            if text.strip():
                payload = json.dumps({"type": "transcript", "speaker": "Aria", "text": text})
                await self._ctx.room.local_participant.publish_data(payload.encode(), reliable=True)
        except Exception as e:
            logger.warning(f"Could not publish agent transcript: {e}")

    async def on_user_turn_completed(self, turn_ctx, new_message):
        # Extract text — handle both string and object content
        text = _msg_text(new_message)
        if not text.strip():
            return

        logger.info(f"User said: {text}")
        sentiment = analyze_sentiment(text)
        self._state["sentiment_counts"][sentiment] += 1

        if not self._state["lead_name"]:
            name = extract_name(text)
            if name:
                self._state["lead_name"] = name

        if not self._state["lead_email"]:
            email = extract_email(text)
            if email:
                self._state["lead_email"] = email

        # Meeting booking now happens via the book_demo function tool (real calendar
        # event + invite); no keyword-based extraction to avoid double booking.
        self._publish_meta()

    async def _send_email(self):
        try:
            send_meeting_confirmation(
                lead_name=self._state["lead_name"] or "there",
                lead_email=self._state["lead_email"],
                meeting_time=self._state["meeting_time"],
                notify_email=NOTIFY_EMAIL,
            )
            logger.info("Meeting confirmation email sent")
        except Exception as e:
            logger.error(f"Email failed: {e}")


async def entrypoint(ctx: JobContext):
    logger.info(f"Aria joining room: {ctx.room.name}")
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    state = {
        "lead_name": None,
        "lead_email": None,
        "meeting_time": None,
        "sentiment_counts": {"Positive": 0, "Neutral": 0, "Negative": 0},
    }

    session = AgentSession(
        stt=deepgram.STT(
            api_key=os.getenv("DEEPGRAM_API_KEY"),
            model="nova-2",
            language="en",
        ),
        llm=lk_openai.LLM(
            # 8b-instant: separate (larger) Groq daily quota than 70b + lower latency
            model=os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
            api_key=os.getenv("GROQ_API_KEY"),
            base_url="https://api.groq.com/openai/v1",
        ),
        # Deepgram Aura TTS — ElevenLabs free quota is exhausted (0/10000 credits).
        # Set TTS_PROVIDER=elevenlabs in .env once credits are topped up.
        tts=(
            elevenlabs.TTS(
                api_key=os.getenv("ELEVEN_LABS_API_KEY"),
                voice_id=os.getenv("ELEVEN_LABS_VOICE_ID", "EXAVITQu4vr4xnSDxMaL"),
                model="eleven_turbo_v2_5",
            )
            if os.getenv("TTS_PROVIDER") == "elevenlabs"
            else deepgram.TTS(
                model="aura-2-andromeda-en",
                api_key=os.getenv("DEEPGRAM_API_KEY"),
            )
        ),
        # No VAD (Silero too slow on this CPU) — use Deepgram's STT endpointing for turns
        vad=None,
        turn_detection="stt",
    )

    await session.start(
        agent=AriaAgent(state, ctx),
        room=ctx.room,
        room_input_options=RoomInputOptions(),
    )

    # Small delay so audio track is established before greeting
    await asyncio.sleep(1.5)
    await session.say(GREETING, allow_interruptions=True)

    # Keep alive until room closes
    await asyncio.sleep(3600)


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            # Named agent = explicit dispatch ONLY (prevents auto-dispatch duplicating jobs)
            agent_name="aria",
            api_key=os.getenv("LIVEKIT_API_KEY"),
            api_secret=os.getenv("LIVEKIT_API_SECRET"),
            ws_url=os.getenv("LIVEKIT_URL"),
        )
    )
