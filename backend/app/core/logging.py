from __future__ import annotations

import logging
import sys

from app.core.config import get_settings


def setup_logging() -> logging.Logger:
    """Configure structured console logging for the application."""
    settings = get_settings()
    log_level = logging.DEBUG if settings.debug else logging.INFO

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s | %(levelname)-7s | %(name)s:%(funcName)s:%(lineno)d - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )

    logger = logging.getLogger(settings.app_name)
    logger.setLevel(log_level)
    return logger


logger = setup_logging()
