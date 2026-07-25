"""
Prefect orchestration flow for the Eurozone Real Estate pipeline.
...
"""

from __future__ import annotations

import prefect.results  # noqa: F401

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))  # ensure `src` and `config` are importable regardless of invocation context

from prefect import flow, task
from prefect.logging import get_run_logger

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@task(retries=1, retry_delay_seconds=30, name="scrape_property_listings")
def scrape_property_listings() -> None:
    logger = get_run_logger()
    logger.info("Starting Scrapy crawl (property_spider)...")

    result = subprocess.run(
        [sys.executable, "-m", "scrapy", "crawl", "property_spider", "-s", "LOG_LEVEL=INFO"],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        logger.error(f"Scrapy crawl failed:\n{result.stderr[-4000:]}")
        raise RuntimeError("Scrapy crawl failed. See logs above.")

    logger.info("Scrapy crawl completed successfully.")


@task(retries=2, retry_delay_seconds=60, name="fetch_eurostat_indicators")
def fetch_eurostat_indicators() -> None:
    logger = get_run_logger()
    logger.info("Fetching Eurostat indicators...")

    from src.etl.run_eurostat_ingestion import run as run_eurostat_ingestion

    run_eurostat_ingestion()
    logger.info("Eurostat ingestion completed successfully.")


@task(retries=1, retry_delay_seconds=30, name="compute_affordability_scores")
def compute_affordability_scores() -> None:
    logger = get_run_logger()
    logger.info("Computing Investment Affordability Scores...")

    from src.etl.run_affordability_scoring import run as run_scoring

    run_scoring()
    logger.info("Affordability scoring completed successfully.")


@flow(name="eurozone-realestate-pipeline", log_prints=True)
def eurozone_realestate_pipeline() -> None:
    """
    Full weekly pipeline: scrape -> Eurostat -> score.

    Eurostat fetching runs independently of scraping (no dependency
    between them), but scoring must run last since it depends on both
    fresh listings and fresh indicators being present in the database.
    """
    scrape_task = scrape_property_listings.submit()
    eurostat_task = fetch_eurostat_indicators.submit()

    # Scoring waits for both upstream tasks to complete
    compute_affordability_scores.submit(
        wait_for=[scrape_task, eurostat_task]
    ).result()


if __name__ == "__main__":
    eurozone_realestate_pipeline()