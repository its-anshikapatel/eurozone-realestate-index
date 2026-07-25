"""
Item Pipelines: process each scraped item after extraction.

Pipeline order (set in settings.py ITEM_PIPELINES):
    1. ValidationPipeline    - drops/flags malformed items
    2. JsonExportPipeline    - writes valid items to data/raw/ as JSON Lines (audit trail)
    3. PostgresPipeline      - upserts valid items into the property_listings table
"""

from __future__ import annotations

import json
from pathlib import Path

from scrapy.exceptions import DropItem

from config.settings import settings
from src.database.crud import upsert_property_listing
from src.database.db import get_session
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ValidationPipeline:
    """Drops items missing required fields or with nonsensical values."""

    REQUIRED_FIELDS = ["listing_id", "title", "price_eur", "city"]

    def process_item(self, item, spider):
        for field_name in self.REQUIRED_FIELDS:
            if not item.get(field_name):
                raise DropItem(
                    f"Missing required field '{field_name}' in item: {item}"
                )

        if item["price_eur"] <= 0:
            raise DropItem(f"Invalid price_eur <= 0 in item: {item}")

        return item


class JsonExportPipeline:
    """Writes each valid item as a line of JSON into data/raw/listings.jsonl."""

    def open_spider(self, spider):
        output_dir: Path = settings.data_dir / "raw"
        output_dir.mkdir(parents=True, exist_ok=True)
        self.output_path = output_dir / "listings.jsonl"
        self.file = open(self.output_path, "w", encoding="utf-8")
        logger.info(f"Writing scraped items to {self.output_path}")

    def close_spider(self, spider):
        self.file.close()
        logger.info(f"Finished writing items to {self.output_path}")

    def process_item(self, item, spider):
        line = json.dumps(dict(item), ensure_ascii=False) + "\n"
        self.file.write(line)
        return item


class PostgresPipeline:
    """
    Upserts each valid item directly into the property_listings table.

    Commits are batched per-item here for simplicity and correctness at our
    current scale (~1000 items). At much higher volumes, you'd batch commits
    every N items to reduce round trips — noted here for future scaling.
    """

    def open_spider(self, spider):
        self.inserted_count = 0
        self.error_count = 0
        logger.info("PostgresPipeline: database session ready for writes.")

    def close_spider(self, spider):
        logger.info(
            f"PostgresPipeline finished: {self.inserted_count} upserted, "
            f"{self.error_count} failed."
        )

    def process_item(self, item, spider):
        try:
            with get_session() as session:
                upsert_property_listing(session, dict(item))
                session.commit()
            self.inserted_count += 1
        except Exception as exc:
            self.error_count += 1
            logger.error(f"Failed to upsert item {item.get('listing_id')}: {exc}")
            raise DropItem(f"Database write failed for item: {item.get('listing_id')}")

        return item