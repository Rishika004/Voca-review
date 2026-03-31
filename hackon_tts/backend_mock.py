# filepath: d:\projects\hackon\backend_mock.py
# Echo backend for testing frontend integration
# This mimics the structure of customerai.py but simply echoes back audio

# --- 1. Installation ---
# Simplified requirements:
#
# pip install "fastapi[all]"
# pip install soundfile numpy

# --- 2. Imports ---
import asyncio
import io
import os
import numpy as np
import soundfile as sf
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

# --- 3. Configuration ---
# Minimal configuration needed for echo server
SAMPLE_RATE = 24000  # Match the sample rate of the original backend

# --- 4. Initialization ---
print("--- Echo Test Backend Starting ---")

# This dictionary simulates the models dictionary in the original code
echo_system = {
    "ready": True  # Always ready since we don't need to load models
}

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app):
    """
    Lifespan context manager for FastAPI (modern replacement for on_event)
    """
    # Code to run during startup
    print("Echo backend initialized and ready for testing!")
    print("WebSocket endpoint available at: ws://localhost:8000/ws")
    yield
    # Code to run during shutdown
    print("Echo backend shutting down...")

# Update FastAPI to use the lifespan context manager
app = FastAPI(lifespan=lifespan)

async def echo_transcript(text: str) -> str:
    """
    Simply returns the input text, simulating LLM processing
    """
    return f"ECHO: {text}"

async def echo_audio(audio_data: bytes) -> bytes:
    """
    Returns the same audio data that was received, properly converted to WAV format
    """
    try:
        # The frontend sends raw PCM data, not complete WAV chunks.
        # We need to specify the format for soundfile to read it correctly.
        # PCM_16 is 16-bit signed integer PCM format
        data, _ = sf.read(io.BytesIO(audio_data), samplerate=SAMPLE_RATE, channels=2, format='RAW', subtype='PCM_16')

        # Ensure audio data is in the correct format (float32 numpy array)
        if data.dtype != np.float32:
            data = data.astype(np.float32)
        
        # Normalize PCM values if they exceed [-1.0, 1.0] range
        max_val = np.max(np.abs(data))
        if max_val > 1.0:
            data = data / max_val
        
        # Convert back to WAV bytes - maintaining the same format as original backend
        # This adds proper WAV headers with format info
        output_buffer = io.BytesIO()
        sf.write(output_buffer, data, SAMPLE_RATE, format='WAV', subtype='PCM_16')
        output_buffer.seek(0)
        
        return output_buffer.read()
    except Exception as e:
        print(f"Error processing audio: {e}")
        # Generate a simple sine wave if we can't process the incoming audio
        return generate_test_audio("Could not process your audio. This is a test tone.")

def generate_test_audio(message: str) -> bytes:
    """
    Generates a simple 1-second sine wave tone as fallback audio
    """
    # Simple 440Hz sine wave (A4 note)
    duration = 1.0  # seconds
    frequency = 440.0  # Hz
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), False)
    tone = 0.5 * np.sin(2 * np.pi * frequency * t)
    
    # Convert to stereo format expected by frontend
    stereo_tone = np.column_stack((tone, tone))
    
    # Convert to WAV format
    output_buffer = io.BytesIO()
    sf.write(output_buffer, stereo_tone, SAMPLE_RATE, format='WAV', subtype='PCM_16')
    output_buffer.seek(0)
    
    return output_buffer.read()

# --- 5. WebSocket Endpoint ---
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("Client connected to echo backend.")
    
    audio_chunks = []

    try:
        while True:
            data = await websocket.receive_bytes()
            audio_chunks.append(data)
            
            # Create a copy of the audio data for echoing
            audio_copy = data
            
            # Send simulated transcript message
            echo_text = "This is an echo test. I'm repeating what you said."
            await websocket.send_json({"type": "user_transcript", "data": echo_text})
            
            # Send simulated AI response message
            ai_echo_text = await echo_transcript(echo_text)
            await websocket.send_json({"type": "ai_response_text", "data": ai_echo_text})
            
            # Echo the audio back
            echo_audio_data = await echo_audio(audio_copy)
            await websocket.send_bytes(echo_audio_data)
            print("Audio echoed back to client.")

    except WebSocketDisconnect:
        print("Client disconnected from echo backend.")
        if audio_chunks:
            # Combine audio chunks into a single WAV file
            try:
                # Let's find a unique file name
                file_counter = 1
                while os.path.exists(f"recording_{file_counter}.wav"):
                    file_counter += 1
                file_name = f"recording_{file_counter}.wav"                # Read all chunks that are valid wav files and concatenate their data
                all_data = []
                samplerate = None
                for chunk in audio_chunks:
                    try:
                        # Assuming raw PCM data from the client
                        # We need to handle raw PCM data properly
                        chunk_data, sr = sf.read(io.BytesIO(chunk), samplerate=SAMPLE_RATE, channels=2, format='RAW', subtype='PCM_16')
                        
                        # Ensure consistent format
                        if chunk_data.dtype != np.float32:
                            chunk_data = chunk_data.astype(np.float32)
                            
                        # Normalize if values exceed [-1.0, 1.0] range
                        max_val = np.max(np.abs(data))
                        if max_val > 0: # Avoid division by zero for silent chunks
                            data = data / max_val

                        if samplerate is None:
                            samplerate = sr
                        all_data.append(chunk_data)
                    except Exception as e:
                        print(f"Skipping a chunk that could not be processed: {e}")
                        continue
                
                if all_data and samplerate is not None:
                    try:
                        # Concatenate all audio data
                        final_audio = np.concatenate(all_data, axis=0)
                        
                        # Write with WAV header information
                        sf.write(file_name, final_audio, samplerate, format='WAV', subtype='PCM_16')
                        print(f"Saved full recording to {file_name}")
                    except Exception as e:
                        print(f"Error concatenating or writing audio: {e}")
                    print(f"Saved full recording to {file_name}")

            except Exception as e:
                print(f"Error saving combined audio file: {e}")

    except Exception as e:
        print(f"An error occurred in the WebSocket connection: {e}")
    
    finally:
        # Check if the connection is in a state where it can be closed
        # Only close if the connection is still in CONNECTING or CONNECTED state
        if websocket.client_state.value in (0, 1):  # 0=CONNECTING, 1=CONNECTED, 2=DISCONNECTING, 3=DISCONNECTED
            try:
                await websocket.close()
                print("Connection closed.")
            except RuntimeError as e:
                print(f"Error closing connection: {e}")
        else:
            print(f"Connection already closing or closed (state: {websocket.client_state.value})")

# --- 6. Run the application ---
# To run the application, use the command:
# uvicorn backend_mock:app --host 0.0.0.0 --port 8000 --reload
# Replace `backend_mock` with the appropriate module name if different

if __name__ == "__main__":
    import uvicorn
    print("\n--- WebSocket server starting ---")
    print("WebSocket will be available at: ws://localhost:8000/ws")
    print("Waiting for client connections...")
    uvicorn.run("backend_mock:app", host="0.0.0.0", port=8000, reload=True)
