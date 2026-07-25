"""
Item Pipelines: process each scraped item after extraction.

Pipeline order (set in settings.py ITEM_PIPELINES):
    1. ValidationPipeline  - drops/flags malformed items
    2. JsonExportPipeline  - writes valid items to data/raw/ as JSON Lines

The PostgreSQL storage pipeline is added in Step 4.
"""

from __future__ import annotations

import json
from pathlib import Path

from scrapy.exceptions import DropItem

from config.settings import settings
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