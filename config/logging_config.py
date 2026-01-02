"""
Logging Configuration

Configures Python logging for the RFP Intelligence application.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime


def setup_logging(log_level: str = "INFO", log_to_file: bool = True) -> logging.Logger:
    """
    Configure logging for the application.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_to_file: Whether to also log to a file
        
    Returns:
        Configured root logger
    """
    # Create logs directory
    logs_dir = Path(__file__).parent.parent / "data" / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    # Create formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    
    # File handler (with date)
    handlers = [console_handler]
    if log_to_file:
        log_file = logs_dir / f"rfp_intelligence_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)  # Log everything to file
        handlers.append(file_handler)
    
    # Configure root logger
    logging.basicConfig(
        level=logging.DEBUG,
        handlers=handlers
    )
    
    # Suppress noisy loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("anthropic").setLevel(logging.WARNING)
    
    return logging.getLogger("rfp_intelligence")


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name."""
    return logging.getLogger(f"rfp_intelligence.{name}")
