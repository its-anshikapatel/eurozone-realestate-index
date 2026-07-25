"""
CRUD (Create/Read/Update/Delete) helpers for property listings.

Centralizes how we write scraped data into PostgreSQL, including
upsert logic so re-running the scraper doesn't create duplicate rows.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session
from src.database.models import EurostatIndicator, PropertyListing
from src.utils.logger import get_logger

logger = get_logger(__name__)


def upsert_property_listing(session: Session, item: dict) -> None:
    """
    Insert a property listing, or update it if a row with the same
    (listing_id, source_site) already exists.

    Uses PostgreSQL's native ON CONFLICT DO UPDATE (upsert) for efficiency
    and correctness — avoids the read-then-write race condition of
    "check if exists, then insert or update" application-level logic.
    """
    stmt = pg_insert(PropertyListing).values(
        listing_id=item["listing_id"],
        source_site=item["source_site"],
        listing_url=item["listing_url"],
        title=item["title"],
        description=item.get("description"),
        property_type=item["property_type"],
        price_eur=item["price_eur"],
        size_sqm=item["size_sqm"],
        bedrooms=item["bedrooms"],
        condition_rating=item["condition_rating"],
        availability_status=item.get("availability_status"),
        city=item["city"],
        country=item["country"],
        country_code=item["country_code"],
        latitude=item["latitude"],
        longitude=item["longitude"],
        scraped_at=item["scraped_at"]
        if isinstance(item["scraped_at"], datetime)
        else datetime.fromisoformat(item["scraped_at"]),
        is_synthetic_location=item.get("is_synthetic_location", False),
    )

    update_columns = {
        col.name: col
        for col in stmt.excluded
        if col.name not in ("id", "listing_id", "source_site", "inserted_at")
    }

    stmt = stmt.on_conflict_do_update(
        constraint="uq_listing_source",
        set_=update_columns,
    )

    session.execute(stmt)
    
    from src.database.models import EurostatIndicator


def upsert_eurostat_indicator(session: Session, record: dict) -> None:
    """
    Insert or update a single Eurostat indicator value for a
    (country_code, indicator_code, year) combination.
    """
    stmt = pg_insert(EurostatIndicator).values(
        country_code=record["country_code"],
        indicator_code=record["indicator_code"],
        indicator_name=record["indicator_name"],
        year=record["year"],
        value=record["value"],
        unit=record.get("unit"),
    )

    update_columns = {
        col.name: col
        for col in stmt.excluded
        if col.name not in ("id", "country_code", "indicator_code", "year", "inserted_at")
    }

    stmt = stmt.on_conflict_do_update(
        constraint="uq_country_indicator_year",
        set_=update_columns,
    )

    session.execute(stmt)