import os, uuid, base64, json, websockets, asyncio, tempfile
from dotenv import load_dotenv
from elevenlabs import ElevenLabs                     # non-streaming SDK

load_dotenv()

API_KEY   = os.getenv("ELEVEN_LABS_API_KEY")
VOICE_ID  = "JBFqnCBsd6RMkjVDRZzb"
MODEL_ID  = "eleven_multilingual_v2"

client = ElevenLabs(api_key=API_KEY)

def text_to_audio(text: str) -> str:
    """Generate TTS with ElevenLabs and return the local MP3 path."""
    response = client.text_to_speech.convert(
        voice_id=VOICE_ID,
        model_id=MODEL_ID,
        text=text,
        output_format="mp3_44100_128",
    )
    path = f"output_{uuid.uuid4().hex}.mp3"
    with open(path, "wb") as f:
        for chunk in response:
            f.write(chunk)
    return path

# text_to_audio("Hello, this is a test of the ElevenLabs TTS service.")  # Example usage
# text_to_audio('[whispers] "I never knew it could be this way"')
text_to_audio('She whispered softly, "I never knew it could be this way"')

