"""
Standalone script: compute Investment Affordability Scores for all
property listings and write price_per_sqm + affordability_score back
into the property_listings table.
"""

from __future__ import annotations

import pandas as pd
from sqlalchemy import text

from src.database.db import get_session
from src.etl.affordability_score import calculate_affordability_scores
from src.utils.logger import get_logger

logger = get_logger(__name__)


def run() -> None:
    with get_session() as session:
        listings_df = pd.read_sql(
            text("SELECT id, country_code, price_eur, size_sqm FROM property_listings"),
            session.bind,
        )
        indicators_df = pd.read_sql(
            text("SELECT country_code, indicator_code, value FROM eurostat_indicators"),
            session.bind,
        )

    if listings_df.empty:
        logger.warning("No property listings found; nothing to score.")
        return

    scored_df = calculate_affordability_scores(listings_df, indicators_df)

    with get_session() as session:
        for _, row in scored_df.iterrows():
            session.execute(
                text(
                    """
                    UPDATE property_listings
                    SET price_per_sqm = :price_per_sqm,
                        affordability_score = :affordability_score
                    WHERE id = :id
                    """
                ),
                {
                    "price_per_sqm": float(row["price_per_sqm"]),
                    "affordability_score": float(row["affordability_score"]),
                    "id": int(row["id"]),
                },
            )
        session.commit()

    logger.info(f"Updated affordability scores for {len(scored_df)} listings.")


if __name__ == "__main__":
    run()