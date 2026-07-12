# Aria v3 — Hinglish Voice Agent (Rumik Silk TTS)

Same architecture as v2 (LiveKit + Deepgram + Groq + Google Calendar) with:
- **TTS: Rumik Silk** (`mulberry` model) — natural Hinglish Indian voice
- **STT: Deepgram multi** — understands Hindi + English code-switching
- **Prompt: Hinglish mode** — Aria mirrors the caller's language
- Own LiveKit agent name `aria-v3` (runs alongside v2 without conflicts)

## Run
1. Get a Rumik key: https://playground.rumik.ai/api-keys → put in `backend/.env` as `RUMIK_API_KEY`
2. Terminal 1: `cd v3-rumik/backend && uvicorn server:app --port 8002`
3. Terminal 2: `cd v3-rumik/backend && python agent.py dev`
4. Frontend `.env.local`: `NEXT_PUBLIC_V3_API_URL=http://localhost:8002`
5. Open http://localhost:3000/v3

Fallbacks: set `TTS_PROVIDER=elevenlabs` or `TTS_PROVIDER=deepgram` to switch voice back.
