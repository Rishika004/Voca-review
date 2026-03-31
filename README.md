# Voca Review — AI Voice Agent for Customer Feedback

Voca Review is a real-time AI-powered voice agent that conducts natural telephone-style conversations to collect customer feedback. Customers speak into their microphone, the system understands what they say, generates an intelligent response, and speaks back — all in real time.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [How It Works](#how-it-works)
- [API Reference](#api-reference)
- [Setup & Installation](#setup--installation)
- [Environment Variables](#environment-variables)
- [Running the Project](#running-the-project)
- [Key Design Decisions](#key-design-decisions)

---

## Overview

Voca Review automates customer feedback collection using a full voice pipeline:

- **Speech-to-Text** — Captures customer voice and transcribes it using OpenAI Whisper
- **LLM Response** — Generates short, conversational replies using Google Gemini 2.5 Flash
- **Text-to-Speech** — Converts the reply to natural-sounding speech using ElevenLabs
- **Real-time Streaming** — Everything happens over WebSocket for low-latency, live interaction
- **Customer Dashboard** — Tracks conversation history, sentiment, and resolution status

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Browser (Next.js)                        │
│                                                                 │
│  Microphone → AudioWorklet → WAV chunks → WebSocket Send        │
│  WebSocket Recv → AudioBuffer → Speaker                         │
│  Live transcript + agent reply displayed on screen              │
└───────────────────────────┬─────────────────────────────────────┘
                            │  WebSocket (ws://localhost:8000)
                            │  Binary WAV audio (up) / WAV + JSON (down)
┌───────────────────────────▼─────────────────────────────────────┐
│                    FastAPI Backend (Python)                      │
│                                                                 │
│  ┌──────────────────┐                                           │
│  │ AudioStreaming    │  Buffers incoming audio chunks           │
│  │ Service          │  until 2+ seconds of speech collected     │
│  └────────┬─────────┘                                           │
│           │                                                     │
│  ┌────────▼─────────┐                                           │
│  │ Whisper Service  │  faster-whisper (small, CPU, int8)        │
│  │ (STT)            │  Transcribes buffered WAV to text         │
│  └────────┬─────────┘                                           │
│           │                                                     │
│  ┌────────▼─────────┐                                           │
│  │ LLM Service      │  Google Gemini 2.5 Flash                  │
│  │ (Response Gen)   │  Generates ≤25 word conversational reply  │
│  └────────┬─────────┘                                           │
│           │                                                     │
│  ┌────────▼─────────┐                                           │
│  │ TTS Service      │  ElevenLabs Turbo v2.5 over WebSocket     │
│  │ (Speech Synth)   │  Streams base64 audio back to client      │
│  └──────────────────┘                                           │
└─────────────────────────────────────────────────────────────────┘
```

### Audio Pipeline Detail

```
Client mic (48kHz stereo)
    → AudioWorklet downsample to 16kHz mono
    → WAV RIFF binary frames sent over WebSocket
    → Backend buffers frames (2s threshold)
    → Whisper transcribes complete WAV
    → Gemini generates reply
    → ElevenLabs synthesizes speech
    → Binary WAV sent back to browser
    → Web Audio API plays response
```

---

## Tech Stack

### Backend

| Category | Tool | Purpose |
|---|---|---|
| Web Framework | FastAPI | Async REST + WebSocket server |
| Server | Uvicorn | ASGI server |
| Speech-to-Text | faster-whisper | Whisper small model, CPU, int8 quantization |
| LLM | Google Gemini 2.5 Flash | Conversational response generation |
| Text-to-Speech | ElevenLabs (eleven_turbo_v2_5) | Natural voice synthesis |
| Audio | soundfile, numpy | WAV I/O and PCM processing |
| Deep Learning | PyTorch, torchaudio | Model inference runtime |
| ONNX | onnxruntime | Optimized model execution |
| Async HTTP | aiohttp | ElevenLabs WebSocket streaming |
| Config | python-dotenv | Environment variable management |

### Frontend

| Category | Tool | Purpose |
|---|---|---|
| Framework | Next.js 15 | React-based full-stack web framework |
| UI Library | React 19 | Component-based UI |
| Language | TypeScript | Type-safe development |
| Styling | Tailwind CSS v4 | Utility-first CSS |
| Audio Capture | Web Audio API + AudioWorklet | Real-time mic capture and processing |
| Transport | WebSocket (native) | Bidirectional binary audio streaming |

---

## Project Structure

```
Voca-review/
│
├── README.md
│
└── hackon_tts/
    ├── backend_main.py          # Alternative GPU backend (Phi-3 LLM + Dia TTS)
    ├── backend_mock.py          # Echo/mock server for frontend testing
    │
    ├── ai call/                 # Core AI backend (production)
    │   ├── .env                 # API keys (not committed)
    │   ├── requirements.txt     # Python dependencies
    │   ├── start_server.py      # Server startup script
    │   ├── myapi.py             # ElevenLabs API usage example
    │   │
    │   ├── app/
    │   │   ├── main.py                      # FastAPI app, CORS, router registration
    │   │   │
    │   │   ├── api/
    │   │   │   ├── agent_voice.py           # WebSocket endpoint: full STT→LLM→TTS loop
    │   │   │   ├── chat.py                  # REST: upload audio → get text reply
    │   │   │   └── stt.py                   # REST: upload audio → get transcription
    │   │   │
    │   │   ├── services/
    │   │   │   ├── whisper_service.py       # faster-whisper transcription
    │   │   │   ├── llm_service.py           # Gemini 2.5 Flash response generation
    │   │   │   ├── tts_service.py           # ElevenLabs speech synthesis
    │   │   │   └── streaming_service.py     # Audio buffer management + pipeline orchestration
    │   │   │
    │   │   └── utils/
    │   │       └── logging_config.py        # Auto-flush logging for async debugging
    │   │
    │   └── adapter/                         # LoRA fine-tuned model adapter (optional)
    │       ├── adapter_config.json
    │       ├── adapter_model.safetensors
    │       └── tokenizer files...
    │
    └── frontend/                # Next.js web app
        ├── package.json
        ├── next.config.ts
        ├── public/
        │   └── wav-processor.js             # AudioWorklet: mic → 16kHz WAV
        └── src/app/
            ├── page.tsx                     # Main voice agent UI
            ├── customers/
            │   └── page.tsx                 # Customer conversation dashboard
            ├── layout.tsx                   # Root layout
            └── globals.css
```

---

## How It Works

### 1. Frontend — Voice Capture

The browser captures microphone input using the Web Audio API. A custom `AudioWorklet` (`wav-processor.js`) runs in a separate thread to:
- Downsample from 48kHz (mic default) to 16kHz (Whisper requirement)
- Pack samples into WAV RIFF binary frames
- Send frames continuously over a WebSocket connection

### 2. Backend — Audio Buffering

The `AudioStreamingService` receives binary WAV frames and buffers them. Once at least 2 seconds of audio has accumulated, it triggers the transcription pipeline. This threshold balances latency against transcription accuracy.

### 3. Speech-to-Text (Whisper)

The `WhisperService` uses `faster-whisper` with the `small` model running on CPU with `int8` quantization — optimized for low-resource deployment. Voice Activity Detection (VAD) filters out silence. The audio is resampled to 16kHz mono before transcription.

### 4. LLM Response (Gemini)

The transcribed text is sent to `Google Gemini 2.5 Flash` via the `google-genai` SDK. The system prompt instructs the model to act as a polite customer feedback agent, respond in ≤25 words, and support multilingual conversations. Thinking budget is set to 0 for fast responses.

### 5. Text-to-Speech (ElevenLabs)

The agent's text reply is sent to ElevenLabs over a WebSocket using the `eleven_turbo_v2_5` model with voice ID `JBFqnCBsd6RMkjVDRZzb`. The response streams back as base64-encoded audio chunks, which are decoded and assembled into a WAV file.

### 6. Response to Client

The backend sends two things back to the browser:
- A **JSON message** containing the customer's transcribed text and the agent's reply text (for UI display)
- A **binary WAV message** containing the synthesized audio

The browser plays the audio using the Web Audio API and updates the live transcript on screen.

### 7. Customer Dashboard

The `/customers` page provides a view of conversation history with call metadata, sentiment indicators, and resolution status — useful for reviewing the quality of automated interactions.

---

## API Reference

### WebSocket

#### `WS /api/agent/voice`

Main real-time voice agent endpoint.

**Client → Server:** Binary WAV audio frames (16kHz, mono, PCM16)

**Server → Client:**
- `JSON` — `{ "user_text": "...", "agent_reply": "..." }`
- `Binary` — WAV audio of agent response

---

### REST Endpoints

#### `POST /stt/transcribe`

Transcribe an uploaded audio file.

| Field | Type | Description |
|---|---|---|
| `audio` | File | WAV/MP3 audio file |

**Response:**
```json
{ "transcription": "Hello, I have a problem with my order." }
```

---

#### `POST /agent/reply`

Upload audio, get transcription + agent text reply.

| Field | Type | Description |
|---|---|---|
| `audio` | File | WAV/MP3 audio file |

**Response:**
```json
{
  "user_text": "Hello, I have a problem with my order.",
  "agent_reply": "I'm sorry to hear that! Could you share your order number?"
}
```

---

## Setup & Installation

### Prerequisites

- Python 3.10+
- Node.js 18+
- A Google Gemini API key
- An ElevenLabs API key

### Backend

```bash
cd "hackon_tts/ai call"

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Frontend

```bash
cd hackon_tts/frontend

npm install
```

---

## Environment Variables

Create a `.env` file inside `hackon_tts/ai call/`:

```env
SECRET_KEY_GOOGLE_AI=your_google_gemini_api_key
ELEVEN_LABS_API_KEY=your_elevenlabs_api_key
```

| Variable | Description | Where to get |
|---|---|---|
| `SECRET_KEY_GOOGLE_AI` | Google Gemini API key | Google AI Studio |
| `ELEVEN_LABS_API_KEY` | ElevenLabs API key | ElevenLabs Dashboard |

---

## Running the Project

### Start the Backend

```bash
cd "hackon_tts/ai call"
python start_server.py
```

The FastAPI server starts at `http://127.0.0.1:8000`.
Interactive API docs available at `http://127.0.0.1:8000/docs`.

### Start the Frontend

```bash
cd hackon_tts/frontend
npm run dev
```

The Next.js app starts at `http://localhost:3000`.

### Alternative Backends

| Backend | Command | Use case |
|---|---|---|
| Production (Gemini + ElevenLabs) | `python start_server.py` | Default |
| Mock/Echo (no AI) | `python backend_mock.py` | Frontend UI testing without API keys |
| GPU (Phi-3 + Dia TTS) | `python backend_main.py` | Fully local inference on GPU |

---

## Key Design Decisions

- **faster-whisper over openai-whisper** — 4x faster inference on CPU with int8 quantization, no GPU required
- **ElevenLabs WebSocket over REST** — Streaming TTS reduces time-to-first-audio vs. waiting for full synthesis
- **AudioWorklet over ScriptProcessor** — Runs audio processing off the main thread, preventing UI jank
- **2-second audio buffer threshold** — Balances turn-taking latency against transcription accuracy (too short = fragmented, too long = slow)
- **Gemini 2.5 Flash with thinking=0** — Fastest possible LLM response; extended thinking is unnecessary for short conversational replies
