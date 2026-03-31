from fastapi import APIRouter, UploadFile, File
from app.services.whisper_service import transcribe_audio
from app.services.llm_service import generate_response
# from app.services.tts_service import text_to_audio
import uuid, os
from fastapi.responses import FileResponse

router = APIRouter()

@router.post("/reply")
async def chat(file: UploadFile = File(...)):
    audio_bytes = await file.read()

    # Option A: if your transcribe_audio takes raw bytes
    user_text = transcribe_audio(audio_bytes)

    # Option B: if it takes a file path
    # temp_path = f"temp_{uuid.uuid4().hex}.wav"
    # with open(temp_path, "wb") as f:
    #     f.write(audio_bytes)
    # user_text = transcribe_audio(temp_path)

    if not user_text:
        return {"error": "Could not understand the audio."}

    agent_reply = generate_response(user_text)

    # reply_path = f"reply_{uuid.uuid4().hex}.wav"
    # text_to_audio(agent_reply, reply_path)

    # return audio
    # return FileResponse(reply_path, media_type="audio/wav", filename="reply.wav")

    return {
        "user_text": user_text,
        "agent_reply": agent_reply
    }
