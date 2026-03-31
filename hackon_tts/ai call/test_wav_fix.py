#!/usr/bin/env python3
"""
Test script to verify the WAV processing fix
"""

import asyncio
import struct
import io
import soundfile as sf
from app.services.streaming_service import AudioStreamingService
from app.utils.logging_config import setup_logging, get_logger

# Set up logging
setup_logging(level="INFO", force_flush=True)
logger = get_logger(__name__)

def create_test_wav(samples, sample_rate=16000, channels=1):
    """Create a test WAV file with the given samples"""
    bits_per_sample = 16
    byte_rate = sample_rate * channels * bits_per_sample // 8
    block_align = channels * bits_per_sample // 8
    data_size = len(samples) * 2  # 2 bytes per sample
    file_size = 36 + data_size
    
    # Create WAV header
    wav_header = struct.pack('<4sI4s4sIHHIIHH4sI',
        b'RIFF',           # Chunk ID
        file_size,         # Chunk size
        b'WAVE',           # Format
        b'fmt ',           # Subchunk1 ID
        16,                # Subchunk1 size (16 for PCM)
        1,                 # Audio format (1 for PCM)
        channels,          # Number of channels
        sample_rate,       # Sample rate
        byte_rate,         # Byte rate
        block_align,       # Block align
        bits_per_sample,   # Bits per sample
        b'data',           # Subchunk2 ID
        data_size          # Subchunk2 size
    )
    
    # Convert samples to bytes
    pcm_data = struct.pack('<' + 'h' * len(samples), *samples)
    
    return wav_header + pcm_data

async def test_transcription(text):
    """Mock transcription callback"""
    logger.info(f"🎯 Mock transcription result: '{text}'")
    print(f"SUCCESS: Transcription received: '{text}'")

async def main():
    """Test the WAV processing fix"""
    logger.info("🧪 Starting WAV processing test...")
    
    # Create a streaming service
    service = AudioStreamingService(test_transcription)
    
    # Create test WAV chunks (simulating frontend behavior)
    logger.info("📦 Creating test WAV chunks...")
    
    # Create 3 separate WAV chunks with different audio data
    chunk1_samples = [1000, 2000, 3000, 4000] * 2000  # 8000 samples
    chunk2_samples = [5000, 6000, 7000, 8000] * 2000  # 8000 samples
    chunk3_samples = [9000, 10000, 11000, 12000] * 2000  # 8000 samples
    
    chunk1_wav = create_test_wav(chunk1_samples)
    chunk2_wav = create_test_wav(chunk2_samples)
    chunk3_wav = create_test_wav(chunk3_samples)
    
    logger.info(f"📊 Test chunks created:")
    logger.info(f"   Chunk 1: {len(chunk1_wav)} bytes")
    logger.info(f"   Chunk 2: {len(chunk2_wav)} bytes")
    logger.info(f"   Chunk 3: {len(chunk3_wav)} bytes")
    
    # Verify each chunk has proper RIFF header
    for i, chunk in enumerate([chunk1_wav, chunk2_wav, chunk3_wav], 1):
        if chunk[:4] == b'RIFF':
            logger.info(f"✅ Chunk {i} has valid RIFF header")
        else:
            logger.error(f"❌ Chunk {i} has invalid RIFF header")
    
    # Process chunks through the service
    logger.info("🔄 Processing chunks through AudioStreamingService...")
    
    try:
        await service.process_audio_chunk(chunk1_wav)
        await service.process_audio_chunk(chunk2_wav)
        await service.process_audio_chunk(chunk3_wav)
        
        # Force transcription if buffer hasn't reached threshold
        if service.audio_samples:
            logger.info("🔄 Forcing transcription of remaining buffer...")
            await service._transcribe_buffer()
        
        logger.info("✅ Test completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
