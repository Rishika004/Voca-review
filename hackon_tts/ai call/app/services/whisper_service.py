# currently im conveting wav file from Downsampling from 48kHz → 16kHz
#                                      🔊 Converting from stereo → mono
                                       # 💾 Saving in PCM 16-bit format
# using: ffmpeg -i abc.wav -ar 16000 -ac 1 -c:a pcm_s16le fixed1.wav 
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
import onnxruntime  # ✅ Force import early so Silero VAD doesn't fail
# print("onnxruntime:", onnxruntime.__version__)  # optional debug line

import soundfile as sf
import io
import sys
import numpy as np
from faster_whisper import WhisperModel
import tempfile
import logging

# Set up logging with immediate flushing
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Force stdout to be unbuffered for immediate output
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# Load model once
model = WhisperModel("small", device="cpu", compute_type="int8")
SAMPLE_RATE = 16000  # For saving output WAV

def transcribe_audio(audio_bytes: bytes) -> str:
    logger.info(f"🎤 Starting transcription of {len(audio_bytes)} bytes")
    sys.stdout.flush()

    # Check the header before processing
    if len(audio_bytes) >= 12:
        try:
            riff_marker = audio_bytes[0:4].decode('ascii', errors='ignore')
            logger.info(f"🔍 Whisper service RIFF marker: '{riff_marker}'")
            
            # Log first 12 bytes as hex
            header_hex = ' '.join(f'{b:02x}' for b in audio_bytes[:12])
            logger.info(f"🔍 Whisper service first 12 bytes: {header_hex}")
        except Exception as e:
            logger.error(f"❌ Error checking audio header: {e}")
    else:
        logger.warning(f"⚠️ Audio data too small: {len(audio_bytes)} bytes")

    # Step 1: Read from real .wav (not raw PCM)
    logger.info("📖 Reading audio data with soundfile...")
    sys.stdout.flush()
    try:
        data, sr = sf.read(io.BytesIO(audio_bytes))  # No format=RAW here!
        logger.info(f"✅ Audio loaded: sample_rate={sr}, shape={data.shape}")
        sys.stdout.flush()
    except Exception as e:
        logger.error(f"❌ Failed to read audio data: {e}")
        sys.stdout.flush()
        raise

    # Step 2: Convert stereo to mono if needed
    if len(data.shape) == 2:
        logger.info("🔄 Converting stereo to mono...")
        data = data.mean(axis=1)
        logger.info("✅ Converted to mono")
    else:
        logger.info("✅ Audio is already mono")

    # Step 3: Save to temp WAV file
    logger.info("💾 Saving to temporary WAV file...")
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        sf.write(f.name, data, SAMPLE_RATE)
        logger.info(f"✅ Temporary file created: {f.name}")

        logger.info("🧠 Running Whisper transcription...")
        segments, _ = model.transcribe(
            f.name,
            beam_size=2,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500)
        )

        # Convert segments to list to count them
        segment_list = list(segments)
        logger.info(f"✅ Whisper completed: {len(segment_list)} segments found")

    transcription = " ".join([seg.text for seg in segment_list])
    logger.info(f"📝 Final transcription: '{transcription}'")
    return transcription
