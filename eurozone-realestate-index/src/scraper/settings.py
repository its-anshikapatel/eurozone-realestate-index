"""
Scrapy framework settings for this project.

This is distinct from config/settings.py — this file controls crawler
behavior (concurrency, delays, pipelines), while config/settings.py holds
application-level config (DB URL, API keys) loaded from .env.
"""

import sys
from pathlib import Path

# Ensure project root is importable so we can reuse config/settings.py and
# src/utils/logger.py from within Scrapy's separate process context.
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import settings as app_settings  # noqa: E402

BOT_NAME = "eurozone_scraper"

SPIDER_MODULES = ["src.scraper.spiders"]
NEWSPIDER_MODULE = "src.scraper.spiders"

# --- Politeness / rate limiting ---
# Never hammer a site. This is non-negotiable for ethical scraping.
ROBOTSTXT_OBEY = True
DOWNLOAD_DELAY = app_settings.scraper_download_delay
RANDOMIZE_DOWNLOAD_DELAY = True
CONCURRENT_REQUESTS_PER_DOMAIN = 2
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 2
AUTOTHROTTLE_MAX_DELAY = 10

# --- Identification ---
USER_AGENT = app_settings.scraper_user_agent

# --- Retry behavior ---
RETRY_ENABLED = True
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429]

# --- Item pipelines (order matters: lower number runs first) ---
ITEM_PIPELINES = {
    "src.scraper.pipelines.ValidationPipeline": 100,
    "src.scraper.pipelines.JsonExportPipeline": 200,
    "src.scraper.pipelines.PostgresPipeline": 300,
}

# --- Logging: let Scrapy use its own, we'll inspect output directly ---
LOG_LEVEL = app_settings.log_level

# --- Output encoding ---
FEED_EXPORT_ENCODING = "utf-8"

REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"