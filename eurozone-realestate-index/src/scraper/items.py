"""
Scrapy Item definitions.

An Item is a structured container for scraped data — think of it as a
lightweight schema/DTO. Defining fields explicitly (rather than yielding
raw dicts) lets Scrapy validate structure and lets our pipelines process
items predictably.
"""

import scrapy


class PropertyListingItem(scrapy.Item):
    # --- Identity ---
    listing_id = scrapy.Field()       # Unique source ID (stand-in: book UPC)
    source_site = scrapy.Field()      # Which spider/site this came from
    listing_url = scrapy.Field()      # Canonical URL of the listing

    # --- Core listing attributes ---
    title = scrapy.Field()
    description = scrapy.Field()
    property_type = scrapy.Field()    # Apartment / House / Studio etc.
    price_eur = scrapy.Field()        # Numeric price in EUR
    size_sqm = scrapy.Field()         # Size in square meters
    bedrooms = scrapy.Field()
    condition_rating = scrapy.Field() # 1-5 scale (stand-in: book star rating)
    availability_status = scrapy.Field()

    # --- Location (synthetic for demo source, real for production source) ---
    city = scrapy.Field()
    country = scrapy.Field()
    country_code = scrapy.Field()     # ISO alpha-2, used to join Eurostat data
    latitude = scrapy.Field()
    longitude = scrapy.Field()

    # --- Metadata ---
    scraped_at = scrapy.Field()       # ISO timestamp of scrape
    is_synthetic_location = scrapy.Field()  # Transparency flag: True for demo data