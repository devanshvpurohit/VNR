"""
logger.py - Centralized logging system for SURDAS

Provides subsystem-specific loggers with consistent formatting.
"""
import logging
import sys
from pathlib import Path
from config import LOG_LEVEL, LOG_FILE, LOGS_DIR

# Ensure logs directory exists
LOGS_DIR.mkdir(exist_ok=True, parents=True)

# Create formatter
FORMATTER = logging.Formatter(
    fmt='[%(asctime)s] [%(name)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Root logger configuration
_root_logger = logging.getLogger('SURDAS')
_root_logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

# Console handler (stdout)
_console_handler = logging.StreamHandler(sys.stdout)
_console_handler.setLevel(logging.INFO)
_console_handler.setFormatter(FORMATTER)
_root_logger.addHandler(_console_handler)

# File handler (detailed logs)
_file_handler = logging.FileHandler(LOG_FILE, mode='a', encoding='utf-8')
_file_handler.setLevel(logging.DEBUG)
_file_handler.setFormatter(FORMATTER)
_root_logger.addHandler(_file_handler)

# Prevent propagation to avoid duplicate logs
_root_logger.propagate = False


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for a specific SURDAS subsystem.
    
    Args:
        name: Subsystem name (e.g., "VISION", "GPS", "NAVIGATION", "VOICE")
        
    Returns:
        Logger instance
    """
    return logging.getLogger(f'SURDAS.{name}')


# Subsystem loggers
vision_logger = get_logger('VISION')
depth_logger = get_logger('DEPTH')
voice_logger = get_logger('VOICE')
navigation_logger = get_logger('NAVIGATION')
gps_logger = get_logger('GPS')
currency_logger = get_logger('CURRENCY')
ollama_logger = get_logger('OLLAMA')
system_logger = get_logger('SYSTEM')


if __name__ == "__main__":
    # Test logging
    system_logger.debug("Debug message")
    system_logger.info("Info message")
    system_logger.warning("Warning message")
    system_logger.error("Error message")
    print(f"\nLogs written to: {LOG_FILE}")
