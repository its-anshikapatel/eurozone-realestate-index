"""
Central configuration module.

Every other module in this project (scraper, ETL, database, pipeline,
dashboard) reads configuration from here — never directly from os.environ.
This gives us a single validated source of truth and makes it obvious
at import time if required environment variables are missing.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Resolve project root (two levels up from this file: config/settings.py -> root)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Load .env from project root explicitly, regardless of current working directory
load_dotenv(dotenv_path=PROJECT_ROOT / ".env")


def _get_env(key: str, default: str | None = None, required: bool = False) -> str:
    """Fetch an environment variable with optional required validation."""
    value = os.getenv(key, default)
    if required and not value:
        raise EnvironmentError(
            f"Missing required environment variable: '{key}'. "
            f"Check your .env file against .env.example."
        )
    return value


@dataclass(frozen=True)
class Settings:
    """Immutable settings object, instantiated once and imported everywhere."""

    # --- Database ---
    database_url: str = field(
        default_factory=lambda: _get_env("DATABASE_URL", required=True)
    )

    # --- Scraper ---
    scraper_user_agent: str = field(
        default_factory=lambda: _get_env(
            "SCRAPER_USER_AGENT",
            default="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        )
    )
    scraper_download_delay: float = field(
        default_factory=lambda: float(_get_env("SCRAPER_DOWNLOAD_DELAY", default="2"))
    )

    # --- Eurostat ---
    eurostat_base_url: str = field(
        default_factory=lambda: _get_env(
            "EUROSTAT_BASE_URL",
            default="https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data",
        )
    )

    # --- Logging ---
    log_level: str = field(default_factory=lambda: _get_env("LOG_LEVEL", default="INFO"))

    # --- Paths (derived, not from .env) ---
    project_root: Path = field(default_factory=lambda: PROJECT_ROOT)
    logs_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "logs")
    data_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "data")


# Single shared instance — import this everywhere:
#   from config.settings import settings
settings = Settings()

# Ensure runtime directories exist as soon as settings is imported
settings.logs_dir.mkdir(parents=True, exist_ok=True)
(settings.data_dir / "raw").mkdir(parents=True, exist_ok=True)