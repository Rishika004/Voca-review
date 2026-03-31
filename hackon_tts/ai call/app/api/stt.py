from fastapi import APIRouter, UploadFile, File
from app.services.whisper_service import transcribe_audio

router = APIRouter()

@router.post("/transcribe")
async def transcribe(file: UploadFile = File(...)):
    audio_bytes = await file.read()
    text = transcribe_audio(audio_bytes)
    return {"text": text}

