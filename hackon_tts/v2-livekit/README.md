# Aria v2 — LiveKit Voice Agent

## Setup

### 1. LiveKit Cloud account
1. Go to https://cloud.livekit.io → Create free account
2. Create a new Project
3. Go to Settings → Keys → copy **API Key**, **API Secret**, **WebSocket URL** (starts with `wss://`)

### 2. Backend .env
Copy `backend/.env.example` to `backend/.env` and fill in:
```
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=APIxxxxxxxxxx
LIVEKIT_API_SECRET=your-secret
DEEPGRAM_API_KEY=your-deepgram-key
GROQ_API_KEY=your-groq-key
ELEVEN_LABS_API_KEY=your-elevenlabs-key
ELEVEN_LABS_VOICE_ID=EXAVITQu4vr4xnSDxMaL
GMAIL_USER=your-email@gmail.com
GMAIL_APP_PASSWORD=your-gmail-app-password
NOTIFY_EMAIL=your-email@gmail.com
```

### 3. Install & run backend (2 terminals)

**Terminal 1 — Token server:**
```bash
cd v2-livekit/backend
pip install -r requirements.txt
uvicorn server:app --port 8001 --reload
```

**Terminal 2 — LiveKit agent worker:**
```bash
cd v2-livekit/backend
python agent.py dev
```

### 4. Install frontend dependency
```bash
cd hackon_tts/frontend
npm install livekit-client
```

### 5. Frontend env
Add to `frontend/.env.local`:
```
NEXT_PUBLIC_V2_API_URL=http://localhost:8001
```

### 6. Run frontend
```bash
cd hackon_tts/frontend
npm run dev
```

Open http://localhost:3000/v2

## What's different from v1

| | v1 | v2 (LiveKit) |
|---|---|---|
| Audio transport | Custom WebSocket + WAV/PCM | LiveKit WebRTC room |
| VAD | Browser silence detection | Silero VAD (server-side) |
| Interruptions | Manual | Built-in barge-in |
| STT | Deepgram streaming WS | Deepgram via LiveKit plugin |
| LLM | Groq direct | Groq via OpenAI-compatible plugin |
| TTS | ElevenLabs WS streaming | ElevenLabs via LiveKit plugin |
| Code complexity | ~400 lines audio plumbing | ~150 lines agent logic |

## Deploy (free)

- **Agent + server**: Render (same as v1, add `LIVEKIT_*` env vars)
- **Frontend**: Vercel (add `NEXT_PUBLIC_V2_API_URL` env var)
- LiveKit Cloud free tier: 50 GB/month traffic (plenty for demo)
