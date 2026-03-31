# Real-Time Logging Configuration

## Problem Fixed

The issue where backend logs only appeared after closing the WebSocket connection has been resolved. This was caused by Python's stdout buffering, which delays output until the buffer is full or the program exits.

## Solution Implemented

### 1. **Stdout Buffering Fix**
- Added `PYTHONUNBUFFERED=1` environment variable
- Configured `sys.stdout.reconfigure(line_buffering=True)`
- Added explicit `sys.stdout.flush()` calls after important log messages

### 2. **Centralized Logging Configuration**
- Created `app/utils/logging_config.py` for consistent logging across all modules
- Implemented `FlushingStreamHandler` that flushes after each log message
- Added real-time logging setup in all service modules

### 3. **Improved Startup Scripts**
- Created `start_server.py` with proper unbuffered configuration
- Added logging test script `test_logging.py`

## How to Run with Real-Time Logging

### Option 1: Use the startup script (Recommended)
```bash
cd "ai call"
python start_server.py
```

### Option 2: Manual startup with environment variable
```bash
cd "ai call"
set PYTHONUNBUFFERED=1
python -u -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### Option 3: PowerShell with environment variable
```powershell
cd "ai call"
$env:PYTHONUNBUFFERED="1"
python -u -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Testing Real-Time Logging

### 1. Test logging configuration:
```bash
cd "ai call"
python test_logging.py
```
You should see log messages appear every second with timestamps.

### 2. Test with WebSocket connection:
1. Start the backend using one of the methods above
2. Open the frontend and start speaking
3. You should now see logs appear immediately:
   - `🔗 WebSocket connection initiated`
   - `📥 Waiting for audio data from client...`
   - `🎵 Received audio data: X bytes`
   - `🧠 Generating AI response...`
   - etc.

## Key Changes Made

### Files Modified:
- `app/api/agent_voice.py` - Added flush calls and unbuffered configuration
- `app/services/whisper_service.py` - Added real-time logging
- `app/services/llm_service.py` - Added real-time logging
- `app/main.py` - Added centralized logging initialization

### Files Created:
- `app/utils/logging_config.py` - Centralized logging configuration
- `start_server.py` - Proper startup script with unbuffered output
- `test_logging.py` - Logging verification script
- `README_LOGGING.md` - This documentation

## Expected Behavior

**Before Fix:**
- Logs only appeared after WebSocket connection closed
- No real-time feedback during voice processing

**After Fix:**
- Logs appear immediately as events happen
- Real-time feedback during:
  - WebSocket connection establishment
  - Audio data reception
  - Transcription processing
  - AI response generation
  - TTS streaming

## Troubleshooting

If logs still don't appear in real-time:

1. **Check environment variable:**
   ```bash
   echo $PYTHONUNBUFFERED  # Should show "1"
   ```

2. **Use Python's -u flag:**
   ```bash
   python -u start_server.py
   ```

3. **Verify terminal supports real-time output:**
   - Some IDEs or terminals may still buffer output
   - Try running in a standard command prompt or PowerShell

4. **Check if logging configuration is loaded:**
   - Look for startup messages about logging configuration
   - Run `test_logging.py` to verify basic logging works
