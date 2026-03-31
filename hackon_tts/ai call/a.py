import asyncio
import websockets
import json
import time
import os

# Update this if needed
URI = "ws://127.0.0.1:8000/api/agent/voice"

AUDIO_IN  = "fixed1.wav"     # Input audio file
AUDIO_OUT = "reply.mp3"      # Output file (TTS response)

def print_timing(step_name: str, elapsed_time: float, total_time: float):
    """Print timing information in a formatted way"""
    print(f"⏱️  {step_name}: {elapsed_time:.3f}s (Total: {total_time:.3f}s)")

def print_models_info():
    """Print information about the models used in the system"""
    print("\n" + "="*60)
    print("🤖 AI VOICE AGENT - MODEL INFORMATION")
    print("="*60)
    print("📢 STT (Speech-to-Text): Faster-Whisper 'small' model")
    print("   - Device: CPU")
    print("   - Compute Type: int8")
    print("   - VAD Filter: Enabled")
    print("   - Beam Size: 2")
    print()
    print("🧠 LLM (Language Model): Google Gemini 2.5 Flash")
    print("   - Provider: Google AI")
    print("   - Max Response: ≤25 words")
    print("   - Purpose: Customer feedback collection")
    print()
    print("🔊 TTS (Text-to-Speech): ElevenLabs eleven_turbo_v2_5")
    print("   - Provider: ElevenLabs")
    print("   - Voice ID: JBFqnCBsd6RMkjVDRZzb")
    print("   - Streaming: Yes")
    print("   - Output Format: MP3")
    print("="*60)
    print()

async def main():
    # Print model information at start
    print_models_info()

    # Overall timing
    total_start_time = time.time()

    # Step 1: Read audio file
    step_start = time.time()
    if not os.path.exists(AUDIO_IN):
        print(f"❌ Error: Audio file '{AUDIO_IN}' not found!")
        return

    with open(AUDIO_IN, "rb") as f:
        payload = f.read()

    file_read_time = time.time() - step_start
    total_elapsed = time.time() - total_start_time
    print_timing("📁 Audio file read", file_read_time, total_elapsed)
    print(f"📊 Audio file size: {len(payload):,} bytes ({len(payload)/1024:.1f} KB)")

    # Step 2: WebSocket connection
    step_start = time.time()
    try:
        async with websockets.connect(URI, max_size=None) as ws:
            connection_time = time.time() - step_start
            total_elapsed = time.time() - total_start_time
            print_timing("🔗 WebSocket connection", connection_time, total_elapsed)

            # Step 3: Send audio to backend
            step_start = time.time()
            await ws.send(payload)
            send_time = time.time() - step_start
            total_elapsed = time.time() - total_start_time
            print_timing("📤 Audio upload", send_time, total_elapsed)

            # Step 4: Receive text metadata (STT + LLM processing)
            step_start = time.time()
            meta = await ws.recv()
            processing_time = time.time() - step_start
            total_elapsed = time.time() - total_start_time
            print_timing("🔄 STT + LLM processing", processing_time, total_elapsed)

            meta_data = json.loads(meta)
            user_text = meta_data.get("user_text", "")
            agent_reply = meta_data.get("agent_reply", "")

            print(f"\n📝 CONVERSATION:")
            print(f"👤 User ({len(user_text)} chars): {user_text}")
            print(f"🤖 Agent ({len(agent_reply)} chars): {agent_reply}")
            print()

            # Step 5: Receive audio stream (TTS)
            step_start = time.time()
            audio_chunks_received = 0
            total_audio_bytes = 0
            first_chunk_time = None

            with open(AUDIO_OUT, "wb") as out:
                while True:
                    try:
                        msg = await ws.recv()
                        if isinstance(msg, bytes):
                            if first_chunk_time is None:
                                first_chunk_time = time.time() - step_start
                                total_elapsed = time.time() - total_start_time
                                print_timing("🎵 First TTS chunk received", first_chunk_time, total_elapsed)

                            out.write(msg)
                            audio_chunks_received += 1
                            total_audio_bytes += len(msg)
                    except websockets.exceptions.ConnectionClosed:
                        break

            tts_total_time = time.time() - step_start
            total_elapsed = time.time() - total_start_time
            print_timing("🔊 Complete TTS streaming", tts_total_time, total_elapsed)

            print(f"📊 TTS Statistics:")
            print(f"   - Audio chunks received: {audio_chunks_received}")
            print(f"   - Total audio size: {total_audio_bytes:,} bytes ({total_audio_bytes/1024:.1f} KB)")
            if first_chunk_time:
                print(f"   - Time to first chunk: {first_chunk_time:.3f}s")
            print(f"   - Average chunk size: {total_audio_bytes/max(audio_chunks_received, 1):.0f} bytes")

    except websockets.exceptions.ConnectionClosed:
        print("❌ WebSocket connection closed unexpectedly")
        return
    except Exception as e:
        print(f"❌ Error: {e}")
        return

    # Final summary
    total_time = time.time() - total_start_time
    print(f"\n🏁 COMPLETE TURNAROUND TIME: {total_time:.3f}s")
    print(f"✅ Audio saved to {AUDIO_OUT}")

    # Performance breakdown
    if os.path.exists(AUDIO_OUT):
        output_size = os.path.getsize(AUDIO_OUT)
        print(f"📊 Output file size: {output_size:,} bytes ({output_size/1024:.1f} KB)")

    print(f"\n📈 PERFORMANCE SUMMARY:")
    print(f"   - Total processing time: {total_time:.3f}s")
    print(f"   - Input audio: {len(payload)/1024:.1f} KB")
    if 'output_size' in locals():
        print(f"   - Output audio: {output_size/1024:.1f} KB")
    print(f"   - Processing efficiency: {len(payload)/1024/max(total_time, 0.001):.1f} KB/s")

if __name__ == "__main__":
    asyncio.run(main())
