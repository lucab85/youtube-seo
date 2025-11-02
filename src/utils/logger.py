"""Logging configuration and setup."""

import sys
import logging
from typing import Optional
from pythonjsonlogger import jsonlogger
from .config import Config


# Global logger instance
_logger: Optional[logging.Logger] = None


def setup_logger(name: str = 'youtube_seo', level: Optional[str] = None) -> logging.Logger:
    """Set up structured logging with JSON formatter."""
    global _logger
    
    if _logger is not None:
        return _logger
    
    # Get log level from config or parameter
    log_level = level or Config.LOG_LEVEL
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(numeric_level)
    logger.handlers = []  # Clear existing handlers
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    
    # JSON formatter for structured logging
    json_formatter = jsonlogger.JsonFormatter(
        '%(asctime)s %(name)s %(levelname)s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(json_formatter)
    
    # Add handler to logger
    logger.addHandler(console_handler)
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    _logger = logger
    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Get or create logger instance."""
    global _logger
    
    if _logger is None:
        setup_logger()
    
    if name:
        return logging.getLogger(f'youtube_seo.{name}')
    
    return _logger


# Convenience functions
def log_info(message: str, **kwargs):
    """Log info message."""
    logger = get_logger()
    logger.info(message, extra=kwargs)


def log_error(message: str, **kwargs):
    """Log error message."""
    logger = get_logger()
    logger.error(message, extra=kwargs)


def log_warning(message: str, **kwargs):
    """Log warning message."""
    logger = get_logger()
    logger.warning(message, extra=kwargs)


def log_debug(message: str, **kwargs):
    """Log debug message."""
    logger = get_logger()
    logger.debug(message, extra=kwargs)
