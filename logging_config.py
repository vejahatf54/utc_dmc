"""
Logging configuration for DMC application.
Sets up file-based logging to avoid cluttering the terminal.
"""

import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler

def setup_logging():
    """
    Configure logging to write to files instead of terminal.
    Creates a logs directory and rotates log files to prevent them from getting too large.
    """
    # Create logs directory if it doesn't exist
    logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    
    # Create log filename with current date
    log_filename = f"dmc_{datetime.now().strftime('%Y%m%d')}.log"
    log_filepath = os.path.join(logs_dir, log_filename)
    
    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            # File handler with rotation (max 10MB, keep 5 files)
            RotatingFileHandler(
                log_filepath,
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5,
                encoding='utf-8'
            ),
            # Keep a minimal console handler for critical errors only
            logging.StreamHandler()
        ]
    )
    
    # Set console handler to only show ERROR and above
    console_handler = logging.getLogger().handlers[-1]
    console_handler.setLevel(logging.ERROR)
    
    # Set specific loggers to appropriate levels
    logging.getLogger('services.replay_file_poke_service').setLevel(logging.INFO)
    logging.getLogger('components.replay_file_poke_page').setLevel(logging.INFO)
    
    return log_filepath

def get_logger(name):
    """Get a logger instance for the given name."""
    return logging.getLogger(name)
