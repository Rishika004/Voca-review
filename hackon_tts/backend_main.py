# live-ai-customer-care-backend/main.py

# --- 1. Installation ---
# This version uses more advanced models and requires a powerful GPU (at least 16-24GB VRAM recommended).
#
# pip install "fastapi[all]"
# pip install faster-whisper
# pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118
# pip install transformers accelerate
# pip install soundfile numpy
# pip install git+https://github.com/nari-labs/dia.git
#
# Make sure your system has a compatible NVIDIA GPU with CUDA drivers installed.
# The torch installation command above is for CUDA 11.8. Adjust if needed.

# --- 2. Imports ---
import asyncio
import io
import numpy as np
import soundfile as sf
import torch
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from faster_whisper import WhisperModel
from transformers import pipeline

# Note: The 'dia' library from Nari Labs might not be available on PyPI.
# We install it from GitHub. Ensure you have git installed.
from dia.model import Dia

# --- 3. Configuration ---
# Hardware Configuration
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
COMPUTE_TYPE = "float16" if torch.cuda.is_available() else "int8"
TORCH_DTYPE = torch.float16 if torch.cuda.is_available() else torch.float32

# Whisper Model Configuration
WHISPER_MODEL_SIZE = "base"

# LLM Configuration
LLM_MODEL_ID = "microsoft/Phi-3-mini-4k-instruct"

# Nari Labs TTS Configuration
NARI_TTS_MODEL_ID = "nari-labs/Dia-1.6B"


# --- 4. Initialization ---
app = FastAPI()
print(f"--- System running on {DEVICE} ---")

# This dictionary will hold our models after they are loaded.
models = {}

@app.on_event("startup")
async def load_models():
    """
    Load all AI models at server startup to avoid long waits on the first request.
    This makes the server start slower but provides a much better user experience.
    """
    print("Loading all AI models. This may take a few minutes...")
    
    # Load Whisper Model
    try:
        print(f"Loading Whisper model: {WHISPER_MODEL_SIZE}")
        models["whisper"] = WhisperModel(WHISPER_MODEL_SIZE, device=DEVICE, compute_type=COMPUTE_TYPE)
        print("Whisper model loaded.")
    except Exception as e:
        print(f"Error loading Whisper model: {e}")

    # Load LLM Model (Phi-3)
    try:
        print(f"Loading LLM: {LLM_MODEL_ID}")
        models["llm_pipeline"] = pipeline(
            "text-generation",
            model=LLM_MODEL_ID,
            device_map=DEVICE,
            torch_dtype=TORCH_DTYPE,
            trust_remote_code=True,
        )
        print("LLM model loaded.")
    except Exception as e:
        print(f"Error loading LLM model: {e}")

    # Load Nari Labs TTS Model (Dia)
    try:
        print(f"Loading TTS model: {NARI_TTS_MODEL_ID}")
        models["tts"] = Dia.from_pretrained(NARI_TTS_MODEL_ID, torch_dtype=TORCH_DTYPE).to(DEVICE)
        print("TTS model loaded.")
    except Exception as e:
        print(f"Error loading TTS model: {e}")
    
    print("--- All models loaded successfully! Server is ready. ---")


async def get_llm_response(text: str) -> str:
    """
    Generates a response from the local Phi-3 LLM.
    """
    if "llm_pipeline" not in models:
        return "LLM model is not available."

    # Create the prompt with the required chat template for Phi-3
    messages = [
        {"role": "user", "content": text},
    ]
    prompt = models["llm_pipeline"].tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )

    # Generate the response
    outputs = models["llm_pipeline"](
        prompt,
        max_new_tokens=256,
        do_sample=True,
        temperature=0.7,
        top_k=50,
        top_p=0.95,
    )
    
    # Extract the generated text
    generated_text = outputs[0]["generated_text"]
    # The output includes the prompt, so we need to extract only the assistant's response
    assistant_response = generated_text.split("<|assistant|>")[-1].strip()
    return assistant_response


async def text_to_speech(text: str) -> bytes:
    """
    Converts text to speech using Nari Labs Dia and returns audio data as WAV bytes.
    """
    if "tts" not in models:
        raise RuntimeError("TTS model is not available.")
    
    # Generate the waveform. Dia expects speaker tags. We'll use [S1] for a single speaker.
    # Appending a speaker tag at the end can improve audio quality.
    formatted_text = f"[S1] {text} [S1]"
    
    output_waveform = models["tts"].generate(formatted_text, sample_rate=24000)
    
    # The output is a torch tensor. Convert it to a numpy array.
    audio_numpy = output_waveform.cpu().numpy()

    # Convert the raw audio waveform to WAV format in memory
    audio_buffer = io.BytesIO()
    sf.write(audio_buffer, audio_numpy.T, 24000, format='WAV', subtype='PCM_16')
    audio_buffer.seek(0)
    
    return audio_buffer.read()


# --- 5. WebSocket Endpoint ---
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("Client connected.")

    if not all(k in models for k in ["whisper", "llm_pipeline", "tts"]):
        error_msg = "One or more AI models failed to load. Please check the server logs."
        await websocket.send_json({"type": "error", "data": error_msg})
        await websocket.close()
        return

    try:
        audio_buffer = bytearray()
        
        while True:
            data = await websocket.receive_bytes()
            audio_buffer.extend(data)
            
            # Try to transcribe with current buffer
            audio_input = io.BytesIO(audio_buffer)
            segments, info = models["whisper"].transcribe(audio_input, beam_size=5)
            
            # Convert segments to list to check if we got any text
            segment_list = list(segments)
            user_transcript = " ".join([segment.text for segment in segment_list]).strip()
            
            if user_transcript:
                print(f"User said: {user_transcript}")
                await websocket.send_json({"type": "user_transcript", "data": user_transcript})
                
                # Clear buffer after successful transcription
                audio_buffer.clear()
                
                # Process with LLM
                ai_response_text = await get_llm_response(user_transcript)
                print(f"AI says: {ai_response_text}")
                await websocket.send_json({"type": "ai_response_text", "data": ai_response_text})
                
                # Generate TTS response
                ai_audio_data = await text_to_speech(ai_response_text)
                await websocket.send_bytes(ai_audio_data)
            
            # If buffer gets too large without successful transcription, clear it
            if len(audio_buffer) > 500_000:  # 500KB safety limit
                print("Buffer too large without transcription, clearing...")
                audio_buffer.clear()

    except WebSocketDisconnect:
        print("Client disconnected.")
    except Exception as e:
        print(f"An error occurred in the WebSocket connection: {e}")
    finally:
        if websocket.client_state != "DISCONNECTED":
            await websocket.close()
            print("Connection closed.")

# --- 6. Run the application ---
# To run this file:
# uvicorn main:app --host 0.0.0.0 --port 8000
#
# Note: --reload is omitted as it can cause issues with model loading on a GPU.
# Restart the server manually after making changes.
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000)

