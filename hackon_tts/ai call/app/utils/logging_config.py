"""
Centralized logging configuration for the AI Call backend.
This ensures consistent, real-time logging across all modules.
"""

import sys
import logging
from typing import Optional

def setup_logging(
    level: str = "INFO",
    format_string: Optional[str] = None,
    force_flush: bool = True
) -> logging.Logger:
    """
    Set up logging with immediate output flushing for real-time logs.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_string: Custom format string for log messages
        force_flush: Whether to force immediate flushing of output
    
    Returns:
        Configured logger instance
    """
    
    if format_string is None:
        format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=format_string,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ],
        force=True  # Override any existing configuration
    )
    
    if force_flush:
        # Force stdout and stderr to be line-buffered for immediate output
        sys.stdout.reconfigure(line_buffering=True)
        sys.stderr.reconfigure(line_buffering=True)
    
    # Get the root logger
    logger = logging.getLogger()
    
    # Add a custom handler that flushes after each log message
    class FlushingStreamHandler(logging.StreamHandler):
        def emit(self, record):
            super().emit(record)
            self.flush()
    
    # Replace the default handler with our flushing handler
    logger.handlers.clear()
    flushing_handler = FlushingStreamHandler(sys.stdout)
    flushing_handler.setFormatter(logging.Formatter(format_string))
    logger.addHandler(flushing_handler)
    
    return logger

def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.
    
    Args:
        name: Name for the logger (usually __name__)
    
    Returns:
        Logger instance
    """
    return logging.getLogger(name)

# Initialize logging when this module is imported
setup_logging()
