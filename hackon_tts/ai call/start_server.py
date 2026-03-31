#!/usr/bin/env python3
"""
Startup script for the AI Call backend with proper logging configuration.
This ensures immediate output flushing for real-time logging during WebSocket connections.
"""

import os
import sys
import uvicorn

# Force Python to use unbuffered output for immediate logging
os.environ['PYTHONUNBUFFERED'] = '1'

# Reconfigure stdout and stderr to be line-buffered
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

if __name__ == "__main__":
    print("🚀 Starting AI Call Backend with real-time logging...")
    print("📝 Logging is configured for immediate output")
    print("🔗 WebSocket endpoint: ws://127.0.0.1:8000/api/agent/voice")
    print("-" * 50)
    
    # Force flush before starting server
    sys.stdout.flush()
    
    # Start the FastAPI server with unbuffered output
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=False,  # Disable reload to prevent model reloading issues
        log_level="info",
        access_log=True
    )
