"""Logging configuration."""
import logging
import logging.handlers
import sys
from pathlib import Path

from .config import settings

def configure_logging() -> None:
    """Configure logging for the application."""
    logging.basicConfig(
        level=logging.DEBUG,  # Set root logger to DEBUG
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),  # Log to console
            logging.FileHandler('logs/pytask.log'),  # Log to file
        ]
    )

    # Set specific loggers to DEBUG level
    logging.getLogger('backend').setLevel(logging.DEBUG)
    logging.getLogger('backend.script_manager').setLevel(logging.DEBUG)
    logging.getLogger('backend.api.routes').setLevel(logging.DEBUG)

    # Disable noisy loggers
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

    logger = logging.getLogger(__name__)
    logger.info("Logging configured successfully") 