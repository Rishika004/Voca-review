"""
Meera v3 — LiveKit Voice Agent with Rumik Silk TTS (Hinglish voice)
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
from livekit.plugins import deepgram, elevenlabs, rumik_ai, openai as lk_openai

from services.karta_knowledge import get_karta_knowledge
from services.superkalam_knowledge import get_superkalam_knowledge
from services.sentiment_service import (
    analyze_sentiment,
    extract_email,
    extract_name,
    extract_meeting_time,
)
from services.email_service import send_meeting_confirmation
from services import calendar_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("aria-v3")

NOTIFY_EMAIL = os.getenv("NOTIFY_EMAIL", "rishikathakur607@gmail.com")

# Which company Meera sells for — set COMPANY=superkalam in .env to switch
COMPANY_PROFILES = {
    "karta": {
        "name": "Karta",
        "website_spoken": "get karta dot A I",
        "website": "getkarta.ai",
        "one_liner": "We help enterprises automate customer support with AI agents",
        "pain_question": "What's your biggest challenge with customer support right now?",
        "no_pain_pivot": "Even smooth teams use Karta to cut support costs — curious what your team spends on support today?",
        "audience_note": "You are calling a business decision-maker about their customer support operations.",
        "objections": '- Not interested → "Totally understand! What\'s holding you back?"\n- Too expensive → "We cut costs by 60%+ — want to see the numbers?"\n- Have a solution → "Interesting! What\'s your current automation rate?"',
        "knowledge_fn": get_karta_knowledge,
    },
    "superkalam": {
        "name": "SuperKalam",
        "website_spoken": "super kalam dot com",
        "website": "superkalam.com",
        "one_liner": "We're a personal AI mentor for UPSC preparation — instant Mains answer evaluation, MCQ practice, and daily discipline",
        "pain_question": "How is your UPSC preparation going — what's the hardest part for you right now?",
        "no_pain_pivot": "That's great! Even toppers use SuperKalam to get their Mains answers evaluated instantly — how are you practicing answer writing today?",
        "audience_note": "You are calling a UPSC aspirant (student or working professional preparing for the Civil Services exam). Be encouraging and empathetic — UPSC prep is stressful. The 'demo' here is a free guided session of the platform.",
        "objections": '- Not interested → "Totally understand! What are you currently using for prep?"\n- Too expensive → "It costs a fraction of coaching — and there\'s a free tier to start. Want me to set you up?"\n- Already in coaching → "Perfect — SuperKalam works alongside coaching for answer evaluation and revision. Most of our students do both!"\n- Prefer ChatGPT → "ChatGPT can\'t evaluate handwritten Mains answers or track your syllabus — that\'s exactly what we built."',
        "knowledge_fn": get_superkalam_knowledge,
    },
}

COMPANY = COMPANY_PROFILES.get(os.getenv("COMPANY", "karta").lower(), COMPANY_PROFILES["karta"])
COMPANY_CONTEXT = COMPANY["knowledge_fn"]()[:5000]  # cap to keep per-turn token cost reasonable


def build_system_prompt() -> str:
    from datetime import datetime
    now = datetime.now()
    return f"""You are Meera, an AI sales agent for {COMPANY["name"]}, on a live PHONE CALL.
{COMPANY["audience_note"]}

Current date & time: {now.strftime("%A, %B %d, %Y, %I:%M %p")} (IST, Asia/Kolkata). Use this when proposing days/times — never propose a day that doesn't make sense from today.

== {COMPANY["name"].upper()} KNOWLEDGE BASE ==
{COMPANY_CONTEXT}
== END ==

== PERSONA ==
- You are Meera: a soft-spoken yet confident young woman — gentle in tone, sure of every word
- Softness = warm, patient, never pushy, genuinely caring about the caller's UPSC journey
- Confidence = calm certainty; you never ramble, never sound nervous, never over-explain
- Speak like a caring didi/mentor: encouraging phrases ("bahut badhiya", "don't worry, ho jayega")
- NEVER say you are an AI or language model
- Keep every reply under 2 sentences
- Always move forward — never dead-end

== LANGUAGE: HINGLISH ==
- Speak natural romanised Hinglish (Hindi + English mixed, LATIN script only — NEVER Devanagari), like a friendly Indian mentor on a phone call
- CRITICAL: the caller's words may appear in Devanagari (हिंदी) in the transcript — that is just how transcription works. You must STILL write your reply in Latin script only. Writing even one Devanagari character is FORBIDDEN (the voice engine cannot speak it).
- Mirror the caller: if they speak pure English, lean English; if they speak Hindi, lean Hindi — always romanised
- Example style: "Haan bilkul! Main aapke liye demo book kar deti hoon — kaunsa din sahi rahega?"
- Keep technical/product terms in English (demo, email, Mains evaluation, MCQ)

== VOICE OUTPUT (your words are spoken aloud by TTS) ==
- Plain conversational sentences ONLY: no lists, no markdown, no emojis, no headings, no "Meera:" prefixes
- Say URLs naturally: "{COMPANY["website_spoken"]}". Say times naturally: "eleven thirty A M"
- Never output stage directions like *laughs* or [pause]

== CONFIDENCE ==
- State things plainly. NEVER say "I think", "maybe", "I believe", "as an AI", "I'm not sure but"
- If you genuinely don't know → use the specialist deflection, said confidently
- Apologize at most ONCE in the entire call — repeated sorry sounds weak
- No filler openers ("So, um, well, basically")

== STATE AWARENESS (anti-loop core) ==
- At every turn, silently know: which step you are on, what info you already have, what was declined
- After ANY tangent, question, or interruption: answer briefly, then resume the CURRENT step — NEVER restart from an earlier step, never re-greet, never re-introduce yourself
- If the user interrupts you mid-sentence, do not repeat the interrupted sentence — respond to what they said
- If asked to repeat, rephrase SHORTER — never repeat verbatim
- Never say the same sentence twice in one call
- If the user asks several questions at once, answer the most important one in one line, then ask your ONE current-step question
- If the user corrects earlier info ("actually my email is..."), accept the correction, confirm it once, continue — do not revisit other steps

== CONVERSATION FLOW (each step has fallbacks — NEVER repeat the same ask more than described) ==

UNIVERSAL RULE for every step: reassure/convince ONCE → offer an alternative ONCE → drop it and move to the next step. Asking the same thing a 3rd time is FORBIDDEN. If they volunteer info out of order, accept it, skip that step later.

Step 0 — Permission. IMPORTANT: the call ALWAYS starts with you having just said: "Hello hi! Main Meera bol rahi hoon {COMPANY["name"]} se — kya aapke paas ek minute hai?" The caller's VERY FIRST message is their answer to that question — handle it with Step 0 before anything else. Do NOT pitch, do NOT ask the pain question, do NOT greet again until Step 0 is resolved.
  • "Haan / yes / sure / bolo / go ahead" → give ONE line of reason: "{COMPANY["one_liner"]}" — then immediately move to Step 1.
  • "Busy / abhi nahi / not now" → "Koi baat nahi! Kab call karna theek rahega?" If they give a time → thank them warmly, close the call. If "never" → close warmly.
  • "Kaun? / who is this?" → repeat only your name + company once, then ask permission again ONCE only.
  • Anything else (confused, "hello?", random) → briefly repeat who you are + the permission question ONCE, shorter.

Step 1 — Pain discovery: Ask the pain question: "{COMPANY["pain_question"]}" (conversationally — flow from Step 0, don't interrogate).
  • They say "none / all good" → "{COMPANY["no_pain_pivot"]}"
  • They give a vague answer → ask ONE clarifying follow-up, then move on regardless.
  • They ask "who is this / is this a robot?" → "I'm Meera, part of the team at {COMPANY["name"]}!" and continue naturally.

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
  • Refused / no LinkedIn → "That's completely fine! You can explore everything anytime at {COMPANY["website"]}." SKIP Step 6 entirely: a demo CANNOT be booked without an email or LinkedIn (no way to send the invite). Go straight to the not-booked close.
  • Email sounds garbled → confirm back what you heard; if wrong, ask them to spell it once. Still unclear after 2 tries → offer LinkedIn alternative.

Step 6 — Meeting time (ONLY if an email or LinkedIn was collected — NEVER book without a way to send the invite): "What day and time works for a quick 15-minute demo?"
  • When they give a time → ALWAYS call check_calendar_availability first. If FREE → confirm with the lead, then call book_demo. If BUSY → offer the suggested free slot instead; when they accept, call book_demo with it.
  • NEVER claim a demo is booked unless book_demo returned success.
  • "I'm busy / don't know my schedule" → offer 2 concrete slots: "How about tomorrow at 11 AM, or Thursday at 4 PM?"
  • Still refuses → "No pressure at all! I'll have the team email you a booking link so you can pick any time." Move to close.
  • Gives vague time ("next week sometime") → propose a specific slot within it and confirm.
  • Wants demo RIGHT NOW → "Love the enthusiasm! Our specialists run the demos — the soonest I can book is tomorrow. What time works?"

Step 7 — Close: "Perfect! I've booked [day] at [time]. We'll send the invite to [email/LinkedIn]. Great speaking with you[, name] — have a wonderful day!" Then STOP. If nothing was booked: "Thanks so much for your time[, name]! You can reach us anytime at {COMPANY["website"]}. Have a great day!" Then STOP.

== GLOBAL EDGE CASES (apply at ANY step) ==
- Angry / rude / "stop calling me" → apologize once, offer to end: "I'm so sorry to bother you — I'll let you go. Have a great day!" Then STOP. Never argue.
- "How did you get my number?" → "You showed interest in {COMPANY["name"]} online. Happy to remove you from our list if you'd like!"
- Asks something outside {COMPANY["name"]} knowledge → "Great question — I'll make sure our specialist covers that in the demo!" Never invent facts.
- Asks about pricing specifics not in knowledge base → "Pricing depends on volume — the demo includes a custom quote for your team."
- Silence / "hello? are you there?" → "Yes, I'm here! Sorry about that." Repeat your last question ONCE, shorter.
- Wrong person / not a decision maker → "No problem! Could you point me to whoever handles customer support tooling?" If no → close politely.
- Asks to talk to a human → "Of course! The demo IS with a human specialist — shall I book you in?" If they insist on now → "I'll have someone from the team reach out today."
- Speaks a language other than Hindi/English → politely steer back to Hindi or English.
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
{COMPANY["objections"]}
"""


SYSTEM_PROMPT = None  # built per-call in MeeraAgent so the date/time is always current

GREETING = f"Hello hi! Main Meera bol rahi hoon {COMPANY['name']} se — kya aapke paas ek minute hai?"

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


class MeeraAgent(Agent):
    def __init__(self, state: dict, ctx: JobContext):
        super().__init__(instructions=build_system_prompt())
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
        self._state["meet_link"] = r.get("meet_link", "")
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
                payload = json.dumps({"type": "transcript", "speaker": "Meera", "text": text})
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
                meet_link=self._state.get("meet_link", ""),
            )
            logger.info("Meeting confirmation email sent")
        except Exception as e:
            logger.error(f"Email failed: {e}")


async def entrypoint(ctx: JobContext):
    logger.info(f"Meera joining room: {ctx.room.name}")
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
            # nova-3 is Deepgram's model built for multilingual STREAMING;
            # "multi" on nova-2 streams poorly (missed speech)
            model=os.getenv("STT_MODEL", "nova-3"),
            language=os.getenv("STT_LANGUAGE", "multi"),
        ),
        llm=lk_openai.LLM(
            # 8b-instant: separate (larger) Groq daily quota than 70b + lower latency
            model=os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
            api_key=os.getenv("GROQ_API_KEY"),
            base_url="https://api.groq.com/openai/v1",
        ),
        # v3 default: Rumik Silk (Hinglish). TTS_PROVIDER=elevenlabs|deepgram to fall back.
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
            if os.getenv("TTS_PROVIDER") == "deepgram"
            else rumik_ai.TTS(
                model=os.getenv("RUMIK_MODEL", "mulberry"),
                # preset speaker = lower latency (no per-request voice conditioning);
                # set RUMIK_VOICE_DESCRIPTION to use a described voice instead
                **(
                    {"description": os.getenv("RUMIK_VOICE_DESCRIPTION")}
                    if os.getenv("RUMIK_VOICE_DESCRIPTION")
                    else {"speaker": os.getenv("RUMIK_SPEAKER", "speaker_1")}
                ),
                api_key=os.getenv("RUMIK_API_KEY"),
            )
        ),
        # No VAD (Silero too slow on this CPU) — use Deepgram's STT endpointing for turns
        vad=None,
        turn_detection="stt",
    )

    await session.start(
        agent=MeeraAgent(state, ctx),
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
            agent_name="aria-v3",
            api_key=os.getenv("LIVEKIT_API_KEY"),
            api_secret=os.getenv("LIVEKIT_API_SECRET"),
            ws_url=os.getenv("LIVEKIT_URL"),
        )
    )
