"""Logging configuration. LOG_LEVEL env var controls verbosity."""

from __future__ import annotations

import logging
import os


def _setup_logger() -> logging.Logger:
    logger = logging.getLogger("amazon_lyr")
    if logger.handlers:
        return logger
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
    return logger


logger = _setup_logger()
