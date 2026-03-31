// WAV Audio Processor for real-time streaming
// Processes audio to 16kHz, mono, PCM 16-bit format with proper WAV headers

class WavProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.bufferSize = 8192; // Larger buffer for better efficiency
    this.buffer = new Float32Array(this.bufferSize);
    this.bufferIndex = 0;
    this.targetSampleRate = 16000;
    this.inputSampleRate = 0;
    this.downsampleRatio = 1;
    this.initialized = false;
  }

  process(inputs, outputs, parameters) {
    const input = inputs[0];
    if (!input || input.length === 0) return true;

    const inputChannel = input[0]; // Use only the first channel (mono)
    if (!inputChannel) return true;

    // Initialize on first process call
    if (!this.initialized) {
      this.inputSampleRate = sampleRate;
      this.downsampleRatio = Math.max(
        1,
        Math.floor(this.inputSampleRate / this.targetSampleRate)
      );
      this.initialized = true;
      console.log(
        `WAV Processor initialized: ${this.inputSampleRate}Hz -> ${this.targetSampleRate}Hz (ratio: ${this.downsampleRatio})`
      );
    }

    // Process audio samples with proper downsampling
    for (let i = 0; i < inputChannel.length; i += this.downsampleRatio) {
      if (this.bufferIndex >= this.bufferSize) {
        // Buffer is full, send it
        this.sendBuffer();
        this.bufferIndex = 0;
      }

      // Downsample by taking every nth sample
      this.buffer[this.bufferIndex] = inputChannel[i];
      this.bufferIndex++;
    }

    return true;
  }

  sendBuffer() {
    if (this.bufferIndex === 0) return;

    console.log(
      `[WAV Processor] Sending buffer with ${this.bufferIndex} samples`
    );

    // Convert float32 samples to PCM 16-bit
    const pcmBuffer = new Int16Array(this.bufferIndex);
    for (let i = 0; i < this.bufferIndex; i++) {
      // Clamp to [-1, 1] and convert to 16-bit PCM
      const sample = Math.max(-1, Math.min(1, this.buffer[i]));
      pcmBuffer[i] = Math.round(sample * 32767);
    }

    console.log(
      `[WAV Processor] Converted ${pcmBuffer.length} samples to PCM 16-bit`
    );

    // Create WAV header and data
    const wavData = this.createWavData(pcmBuffer);

    console.log(
      `[WAV Processor] Created WAV data: ${wavData.byteLength} bytes`
    );

    // Send the WAV data to the main thread
    this.port.postMessage({
      type: "audioData",
      data: wavData,
    });
  }

  createWavData(pcmData) {
    console.log(
      `[WAV Processor] Creating WAV data for ${pcmData.length} PCM samples`
    );

    const sampleRate = this.targetSampleRate;
    const numChannels = 1; // Mono
    const bitsPerSample = 16;
    const byteRate = (sampleRate * numChannels * bitsPerSample) / 8;
    const blockAlign = (numChannels * bitsPerSample) / 8;
    const dataSize = pcmData.length * 2; // 2 bytes per sample
    const fileSize = 44 + dataSize;

    console.log(
      `[WAV Processor] WAV params: sampleRate=${sampleRate}, dataSize=${dataSize}, fileSize=${fileSize}`
    );

    const buffer = new ArrayBuffer(fileSize);
    const view = new DataView(buffer);

    // WAV header - RIFF chunk descriptor
    view.setUint32(0, 0x52494646, false); // "RIFF"
    view.setUint32(4, fileSize - 8, true); // File size - 8
    view.setUint32(8, 0x57415645, false); // "WAVE"

    // fmt sub-chunk
    view.setUint32(12, 0x666d7420, false); // "fmt "
    view.setUint32(16, 16, true); // Sub-chunk size (16 for PCM)
    view.setUint16(20, 1, true); // Audio format (1 = PCM)
    view.setUint16(22, numChannels, true); // Number of channels
    view.setUint32(24, sampleRate, true); // Sample rate
    view.setUint32(28, byteRate, true); // Byte rate
    view.setUint16(32, blockAlign, true); // Block align
    view.setUint16(34, bitsPerSample, true); // Bits per sample

    // data sub-chunk
    view.setUint32(36, 0x64617461, false); // "data"
    view.setUint32(40, dataSize, true); // Data size

    // Copy PCM data
    const pcmView = new Int16Array(buffer, 44);
    pcmView.set(pcmData);

    // Verify the header was written correctly
    const headerCheck = new Uint8Array(buffer, 0, 12);
    console.log(
      `[WAV Processor] Header check - First 12 bytes:`,
      Array.from(headerCheck)
        .map((b) => b.toString(16).padStart(2, "0"))
        .join(" ")
    );

    // Check if RIFF marker is present
    const riffMarker = String.fromCharCode(
      headerCheck[0],
      headerCheck[1],
      headerCheck[2],
      headerCheck[3]
    );
    console.log(`[WAV Processor] RIFF marker: "${riffMarker}"`);

    return buffer;
  }
}

registerProcessor("wav-processor", WavProcessor);
