# FFmpeg Setup for Audio Processing

The streaming service requires FFmpeg to decode WebM/Opus audio streams to PCM for Voice Activity Detection (VAD).

## Windows Installation

1. **Download FFmpeg:**

   - Go to https://ffmpeg.org/download.html
   - Download the Windows build from https://github.com/BtbN/FFmpeg-Builds/releases
   - Extract the zip file to a folder (e.g., `C:\ffmpeg`)

2. **Add to PATH:**

   - Open System Properties > Advanced > Environment Variables
   - Add `C:\ffmpeg\bin` to your PATH environment variable
   - Restart your terminal/IDE

3. **Verify Installation:**
   ```bash
   ffmpeg -version
   ```

## Alternative: Using Chocolatey (Windows)

```bash
choco install ffmpeg
```

## Alternative: Using Conda

```bash
conda install ffmpeg -c conda-forge
```

## Testing

After installation, you can test the audio processing pipeline by running your FastAPI server and connecting with a WebSocket client that sends WebM/Opus audio chunks.
