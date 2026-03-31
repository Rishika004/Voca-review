#!/usr/bin/env python3
"""
Test script to verify that logging works in real-time.
Run this to check if logs appear immediately without buffering.
"""

import time
import sys
from app.utils.logging_config import setup_logging, get_logger

# Setup logging
setup_logging(level="INFO", force_flush=True)
logger = get_logger(__name__)

def test_real_time_logging():
    """Test that logs appear immediately without waiting for buffer to fill."""
    
    print("🧪 Testing real-time logging...")
    print("📝 You should see each log message appear immediately with timestamps")
    print("-" * 60)
    
    for i in range(10):
        logger.info(f"📊 Test log message #{i+1} - This should appear immediately")
        time.sleep(1)  # Wait 1 second between messages
    
    print("-" * 60)
    print("✅ Real-time logging test completed!")
    print("💡 If you saw each message appear with a 1-second delay, logging is working correctly")

if __name__ == "__main__":
    test_real_time_logging()
