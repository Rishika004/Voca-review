# example.py
import os
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from elevenlabs import play
import base64

load_dotenv()

elevenlabs = ElevenLabs(
  api_key=os.getenv("ELEVEN_LABS_API_KEY"),
)

voices = elevenlabs.text_to_voice.design(
    model_id="eleven_multilingual_ttv_v2",
    voice_description="A massive evil ogre speaking at a quick pace. He has a silly and resonant tone.",
    text="Your weapons are but toothpicks to me. Surrender now and I may grant you a swift end. I've toppled kingdoms and devoured armies. What hope do you have against me?",
)

for preview in voices.previews:
    # Convert base64 to audio buffer
    audio_buffer = base64.b64decode(preview.audio_base_64)

    print(f"Playing preview: {preview.generated_voice_id}")

    play(audio_buffer)
