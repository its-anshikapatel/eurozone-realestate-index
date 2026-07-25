"""
PropertySpider: crawls a paginated listings catalog and yields
PropertyListingItem records.

Currently targets books.toscrape.com as a stable, ToS-compliant scraping
sandbox (see README for the reasoning). Field mapping treats each "book"
as a stand-in "listing" with realistic real-estate-shaped attributes.

TO REPOINT AT A REAL LISTINGS SITE:
    Only `parse_listing_card()` and `parse_listing_detail()` need new
    CSS/XPath selectors matching the target site's HTML. The Item schema,
    pipelines, cleaning, and database layers do not change.
"""

from __future__ import annotations

import hashlib
import random
from datetime import datetime, timezone

import scrapy

from src.scraper.items import PropertyListingItem

# Deterministic synthetic location pool for demo data augmentation.
# Real production spiders would extract this directly from the listing page.
_EUROZONE_CITIES = [
    ("Berlin", "Germany", "DE", 52.5200, 13.4050),
    ("Paris", "France", "FR", 48.8566, 2.3522),
    ("Madrid", "Spain", "ES", 40.4168, -3.7038),
    ("Rome", "Italy", "IT", 41.9028, 12.4964),
    ("Amsterdam", "Netherlands", "NL", 52.3676, 4.9041),
    ("Lisbon", "Portugal", "PT", 38.7223, -9.1393),
    ("Vienna", "Austria", "AT", 48.2082, 16.3738),
    ("Dublin", "Ireland", "IE", 53.3498, -6.2603),
    ("Athens", "Greece", "GR", 37.9838, 23.7275),
    ("Brussels", "Belgium", "BE", 50.8503, 4.3517),
]

_PROPERTY_TYPES = ["Apartment", "Studio", "House", "Penthouse", "Townhouse"]


def _deterministic_choice(seed_text: str, options: list):
    """
    Pick an option deterministically from a seed string, so the same
    listing always maps to the same synthetic city/type across re-scrapes.
    """
    digest = hashlib.md5(seed_text.encode("utf-8")).hexdigest()
    index = int(digest, 16) % len(options)
    return options[index]


class PropertySpider(scrapy.Spider):
    name = "property_spider"
    allowed_domains = ["books.toscrape.com"]
    start_urls = ["https://books.toscrape.com/"]

    custom_settings = {
        "FEED_EXPORT_ENCODING": "utf-8",
    }

    def parse(self, response: scrapy.http.Response):
        """
        Parse a catalog page: extract each listing card's detail link
        and follow it, then follow pagination to the next page.
        """
        listing_links = response.css("article.product_pod h3 a::attr(href)").getall()
        for link in listing_links:
            yield response.follow(link, callback=self.parse_listing_detail)

        next_page = response.css("li.next a::attr(href)").get()
        if next_page is not None:
            yield response.follow(next_page, callback=self.parse)

    def parse_listing_detail(self, response: scrapy.http.Response):
        """
        Parse an individual listing detail page into a PropertyListingItem.
        """
        title = response.css("div.product_main h1::text").get(default="").strip()

        price_text = response.css(
            "p.price_color::text"
        ).get(default="0")
        price_eur = self._parse_price(price_text)

        description = response.css(
            "#product_description ~ p::text"
        ).get(default="").strip()

        category = response.css(
            "ul.breadcrumb li:nth-child(3) a::text"
        ).get(default="Unknown").strip()

        rating_classes = response.css("p.star-rating::attr(class)").get(default="")
        condition_rating = self._parse_rating(rating_classes)

        upc = response.css(
            "table.table.table-striped tr:nth-child(1) td::text"
        ).get(default="")

        availability_text = response.css(
            "table.table.table-striped tr:nth-child(6) td::text"
        ).get(default="")

        # --- Synthetic augmentation (clearly flagged, deterministic) ---
        city, country, country_code, lat, lon = _deterministic_choice(
            upc, _EUROZONE_CITIES
        )
        property_type = _deterministic_choice(upc + "type", _PROPERTY_TYPES)
        size_sqm = 30 + (int(hashlib.md5(upc.encode()).hexdigest(), 16) % 170)
        bedrooms = 1 + (int(hashlib.md5((upc + "br").encode()).hexdigest(), 16) % 5)

        item = PropertyListingItem()
        item["listing_id"] = upc
        item["source_site"] = "books.toscrape.com (demo source)"
        item["listing_url"] = response.url
        item["title"] = title
        item["description"] = description
        item["property_type"] = property_type
        item["price_eur"] = price_eur
        item["size_sqm"] = size_sqm
        item["bedrooms"] = bedrooms
        item["condition_rating"] = condition_rating
        item["availability_status"] = availability_text
        item["city"] = city
        item["country"] = country
        item["country_code"] = country_code
        item["latitude"] = lat
        item["longitude"] = lon
        item["scraped_at"] = datetime.now(timezone.utc).isoformat()
        item["is_synthetic_location"] = True

        yield item

    @staticmethod
    def _parse_price(price_text: str) -> float:
        """Convert a currency string like '£51.77' into a float."""
        cleaned = "".join(ch for ch in price_text if ch.isdigit() or ch == ".")
        try:
            # Scale up slightly so demo prices resemble EUR property price ranges
            return round(float(cleaned) * 1000, 2) if cleaned else 0.0
        except ValueError:
            return 0.0

    @staticmethod
    def _parse_rating(class_attr: str) -> int:
        """Scrapy star-rating classes look like 'star-rating Three'."""
        mapping = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}
        for word, value in mapping.items():
            if word in class_attr:
                return value
        return 0