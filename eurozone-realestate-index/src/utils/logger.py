"""
Centralized logging configuration.

Usage in any module:
    from src.utils.logger import get_logger
    logger = get_logger(__name__)
    logger.info("Something happened")

Logs go to both console (for dev visibility) and a rotating file
under /logs (for later debugging of scheduled Prefect runs).
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from config.settings import settings

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_configured_loggers: set[str] = set()


def get_logger(name: str) -> logging.Logger:
    """
    Return a configured logger for the given module name.

    Safe to call multiple times for the same name — handlers are only
    attached once per logger to avoid duplicate log lines.
    """
    logger = logging.getLogger(name)

    if name in _configured_loggers:
        return logger

    logger.setLevel(settings.log_level.upper())
    logger.propagate = False  # avoid duplicate logs via root logger

    formatter = logging.Formatter(fmt=_LOG_FORMAT, datefmt=_DATE_FORMAT)

    # Console handler — human-readable output while developing
    console_handler = logging.StreamHandler(stream=sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Rotating file handler — keeps last 5 files of 2MB each
    log_file: Path = settings.logs_dir / "pipeline.log"
    file_handler = RotatingFileHandler(
        filename=log_file, maxBytes=2 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    _configured_loggers.add(name)
    return logger