import torch
import numpy as np
from app.services.whisper_service import transcribe_audio
from app.utils.logging_config import get_logger
import io
import soundfile as sf
import struct


logger = get_logger(__name__)

class AudioStreamingService:
    """
    Manages streaming audio, detects speech, and sends it for transcription.
    """
    def __init__(self, on_transcription_update):
        logger.info("Initializing AudioStreamingService...")
        self.on_transcription_update = on_transcription_update
        
        # --- Audio Buffers ---
        self.audio_samples = []  # For PCM audio samples
        self.sample_rate = 16000  # Expected sample rate from frontend
        self.channels = 1  # Mono audio
        
        logger.info("✅ AudioStreamingService initialized.")

    def _extract_wav_data(self, wav_bytes: bytes) -> bytes:
        """
        Extracts PCM audio data from a WAV file, skipping the header.
        """
        if len(wav_bytes) < 44:
            logger.warning(f"⚠️ WAV chunk too small: {len(wav_bytes)} bytes")
            return b""
        
        # Check RIFF header
        if wav_bytes[:4] != b'RIFF':
            logger.warning("⚠️ Invalid RIFF header")
            return b""
        
        # Check WAVE format
        if wav_bytes[8:12] != b'WAVE':
            logger.warning("⚠️ Invalid WAVE format")
            return b""
        
        # Find the data chunk
        pos = 12
        while pos < len(wav_bytes) - 8:
            chunk_id = wav_bytes[pos:pos+4]
            chunk_size = struct.unpack('<I', wav_bytes[pos+4:pos+8])[0]
            
            if chunk_id == b'data':
                # Found data chunk, extract PCM data
                data_start = pos + 8
                data_end = data_start + chunk_size
                if data_end <= len(wav_bytes):
                    return wav_bytes[data_start:data_end]
                else:
                    logger.warning(f"⚠️ Data chunk size mismatch: expected {chunk_size}, available {len(wav_bytes) - data_start}")
                    return wav_bytes[data_start:]
            
            pos += 8 + chunk_size
        
        logger.warning("⚠️ No data chunk found in WAV file")
        return b""

    async def process_audio_chunk(self, chunk: bytes):
        """
        Processes an incoming audio chunk by extracting PCM data and buffering it.
        """
        logger.info(f"📨 Received audio chunk: {len(chunk)} bytes")
        
        # Check if the chunk has RIFF header
        if len(chunk) >= 12:
            riff_marker = chunk[0:4].decode('ascii', errors='ignore')
            logger.info(f"🔍 RIFF marker in chunk: '{riff_marker}'")
            
            # Log first 12 bytes as hex
            header_hex = ' '.join(f'{b:02x}' for b in chunk[:12])
            logger.info(f"🔍 First 12 bytes: {header_hex}")
        else:
            logger.warning(f"⚠️ Chunk too small: {len(chunk)} bytes")
        
        # Extract PCM data from the WAV chunk
        pcm_data = self._extract_wav_data(chunk)
        if pcm_data:
            self.audio_samples.append(pcm_data)
            logger.info(f"✅ Extracted {len(pcm_data)} bytes of PCM data")
        
        # Calculate total buffered audio duration (approximately)
        total_pcm_bytes = sum(len(sample) for sample in self.audio_samples)
        # 16-bit PCM, mono, 16kHz = 2 bytes per sample, 16000 samples per second
        duration_seconds = total_pcm_bytes / (2 * self.sample_rate)
        
        # Transcribe when we have enough audio (e.g., 2 seconds worth)
        if duration_seconds >= 2.0:
            await self._transcribe_buffer()

    async def _transcribe_buffer(self):
        """
        Combines all buffered PCM samples into a single WAV file and sends for transcription.
        """
        if not self.audio_samples:
            return

        logger.info(f"🧠 Preparing {len(self.audio_samples)} audio chunks for transcription.")
        
        try:
            # Combine all PCM data
            combined_pcm = b"".join(self.audio_samples)
            total_pcm_bytes = len(combined_pcm)
            
            logger.info(f"📊 Combined PCM data: {total_pcm_bytes} bytes")
            
            # Create a proper WAV file with header
            wav_data = self._create_wav_file(combined_pcm)
            
            # Check the created WAV file header
            if len(wav_data) >= 12:
                riff_marker = wav_data[0:4].decode('ascii', errors='ignore')
                logger.info(f"🔍 Created WAV RIFF marker: '{riff_marker}'")
                
                # Log first 12 bytes as hex
                header_hex = ' '.join(f'{b:02x}' for b in wav_data[:12])
                logger.info(f"🔍 Created WAV first 12 bytes: {header_hex}")
            
            # Send to whisper service
            transcription = transcribe_audio(wav_data)
            
        except Exception as e:
            logger.error(f"Error converting audio for transcription: {e}")
            self.audio_samples.clear()
            return

        self.audio_samples.clear()

        if transcription and transcription.strip():
            logger.info(f"📝 Transcription received: '{transcription}'")
            await self.on_transcription_update(transcription)
        else:
            logger.info("🔇 Received empty transcription.")

    def _create_wav_file(self, pcm_data: bytes) -> bytes:
        """
        Creates a complete WAV file from PCM data.
        """
        # WAV file parameters
        sample_rate = self.sample_rate
        channels = self.channels
        bits_per_sample = 16
        byte_rate = sample_rate * channels * bits_per_sample // 8
        block_align = channels * bits_per_sample // 8
        data_size = len(pcm_data)
        file_size = 36 + data_size  # 36 bytes for header + data size
        
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
        
        # Combine header and data
        wav_file = wav_header + pcm_data
        
        logger.info(f"📄 Created WAV file: {len(wav_file)} bytes (header: {len(wav_header)}, data: {len(pcm_data)})")
        
        return wav_file
