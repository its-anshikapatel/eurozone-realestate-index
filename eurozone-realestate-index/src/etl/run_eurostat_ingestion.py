"""
Standalone script: fetch Eurostat indicators and upsert them into the
eurostat_indicators table. Run manually or via the Prefect flow (Step 7).
"""

from __future__ import annotations

from src.database.crud import upsert_eurostat_indicator
from src.database.db import get_session
from src.etl.eurostat_client import fetch_all_indicators
from src.utils.logger import get_logger

logger = get_logger(__name__)


def run() -> None:
    df = fetch_all_indicators()

    if df.empty:
        logger.warning("No Eurostat data fetched; nothing to store.")
        return

    inserted = 0
    with get_session() as session:
        for _, row in df.iterrows():
            upsert_eurostat_indicator(session, row.to_dict())
            inserted += 1
        session.commit()

    logger.info(f"Eurostat ingestion complete: {inserted} rows upserted.")


if __name__ == "__main__":
    run()