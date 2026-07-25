"""
SQLAlchemy ORM models.

Defines the database schema as Python classes. This is the single source
of truth for table structure — migrations and queries all derive from here.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


class PropertyListing(Base):
    """
    A single scraped property listing, enriched with location data.

    listing_id + source_site together form a natural unique key: the same
    listing_id could theoretically appear across different source sites.
    """

    __tablename__ = "property_listings"
    __table_args__ = (
        UniqueConstraint("listing_id", "source_site", name="uq_listing_source"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # --- Identity ---
    listing_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    source_site: Mapped[str] = mapped_column(String(200), nullable=False)
    listing_url: Mapped[str] = mapped_column(String(1000), nullable=False)

    # --- Core listing attributes ---
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(String(5000), nullable=True)
    property_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    price_eur: Mapped[float] = mapped_column(Float, nullable=False)
    size_sqm: Mapped[float] = mapped_column(Float, nullable=False)
    bedrooms: Mapped[int] = mapped_column(Integer, nullable=False)
    condition_rating: Mapped[int] = mapped_column(Integer, nullable=False)
    availability_status: Mapped[str] = mapped_column(String(100), nullable=True)

    # --- Location ---
    city: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    country: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    country_code: Mapped[str] = mapped_column(String(2), nullable=False, index=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)

    # --- Derived / computed fields (filled in by ETL, not the scraper) ---
    price_per_sqm: Mapped[float | None] = mapped_column(Float, nullable=True)
    affordability_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # --- Metadata ---
    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_synthetic_location: Mapped[bool] = mapped_column(Boolean, default=False)
    inserted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return (
            f"<PropertyListing id={self.id} city={self.city!r} "
            f"price_eur={self.price_eur} type={self.property_type!r}>"
        )


class EurostatIndicator(Base):
    """
    A single Eurostat macroeconomic data point for a country/year/indicator
    combination (e.g. average income, HICP housing index).

    Populated in Step 5 by the Eurostat API client.
    """

    __tablename__ = "eurostat_indicators"
    __table_args__ = (
        UniqueConstraint(
            "country_code", "indicator_code", "year", name="uq_country_indicator_year"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    country_code: Mapped[str] = mapped_column(String(2), nullable=False, index=True)
    indicator_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    indicator_name: Mapped[str] = mapped_column(String(200), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)

    inserted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return (
            f"<EurostatIndicator {self.country_code} {self.indicator_code} "
            f"{self.year}={self.value}>"
        )