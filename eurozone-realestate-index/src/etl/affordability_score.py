"""
Investment Affordability Score calculation.

Combines three factors into a single 0-100 score per property listing,
where 100 = most affordable / best investment value, 0 = least affordable:

    1. Price-to-Income Ratio (50% weight)
       How many years of median income it takes to buy this property.
       Lower ratio = more affordable = higher score.

    2. House Price Index position (25% weight)
       Whether the country's housing market is currently expensive
       relative to its own 2015 baseline. Lower HPI = higher score.

    3. Relative price per sqm within country (25% weight)
       Whether this specific listing is cheap or expensive compared to
       other listings in the same country. Lower relative price = higher score.

Each factor is normalized to 0-100 via min-max scaling across all listings
before combining, so the final score is always comparable across the
whole dataset regardless of the raw units of each factor.
"""

from __future__ import annotations

import pandas as pd

from src.utils.logger import get_logger

logger = get_logger(__name__)

WEIGHT_PRICE_TO_INCOME = 0.50
WEIGHT_HPI_POSITION = 0.25
WEIGHT_RELATIVE_PRICE_PER_SQM = 0.25


def _min_max_normalize_inverted(series: pd.Series) -> pd.Series:
    """
    Min-max normalize a series to 0-100, then invert it, so that the
    LOWEST raw value (e.g. lowest price-to-income ratio) maps to the
    HIGHEST score (100 = most affordable).
    """
    min_val, max_val = series.min(), series.max()
    if pd.isna(min_val) or pd.isna(max_val) or max_val == min_val:
        # No variation (or all-null) — return neutral midpoint score
        return pd.Series([50.0] * len(series), index=series.index)

    normalized = (series - min_val) / (max_val - min_val) * 100
    return 100 - normalized  # invert: lower raw value -> higher score


def calculate_affordability_scores(
    listings_df: pd.DataFrame, indicators_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Compute the Investment Affordability Score for each listing.

    Parameters
    ----------
    listings_df : DataFrame with columns
        [id, country_code, price_eur, size_sqm]  (at minimum)
    indicators_df : DataFrame with columns
        [country_code, indicator_code, value]
        Must contain rows for 'MEDIAN_INCOME_EUR' and 'HOUSE_PRICE_INDEX'.

    Returns
    -------
    DataFrame with columns [id, price_per_sqm, affordability_score]
    Countries missing an indicator get a neutral (50) contribution for
    that specific factor rather than crashing or being dropped.
    """
    df = listings_df.copy()

    # --- Factor 3 setup: price per sqm ---
    df["price_per_sqm"] = df["price_eur"] / df["size_sqm"]

    # --- Pivot indicators into wide format: one column per indicator ---
    indicators_wide = indicators_df.pivot_table(
        index="country_code", columns="indicator_code", values="value", aggfunc="first"
    ).reset_index()

    missing_income = set(df["country_code"].unique()) - set(
        indicators_wide.loc[
            indicators_wide["MEDIAN_INCOME_EUR"].notna(), "country_code"
        ]
        if "MEDIAN_INCOME_EUR" in indicators_wide.columns
        else []
    )
    missing_hpi = set(df["country_code"].unique()) - set(
        indicators_wide.loc[indicators_wide["HOUSE_PRICE_INDEX"].notna(), "country_code"]
        if "HOUSE_PRICE_INDEX" in indicators_wide.columns
        else []
    )
    if missing_income:
        logger.warning(f"Countries missing MEDIAN_INCOME_EUR: {sorted(missing_income)}")
    if missing_hpi:
        logger.warning(f"Countries missing HOUSE_PRICE_INDEX: {sorted(missing_hpi)}")

    df = df.merge(indicators_wide, on="country_code", how="left")

    # --- Factor 1: Price-to-Income Ratio ---
    if "MEDIAN_INCOME_EUR" in df.columns:
        df["price_to_income_ratio"] = df["price_eur"] / df["MEDIAN_INCOME_EUR"]
    else:
        df["price_to_income_ratio"] = pd.NA

    # --- Factor 2: HPI position (just the raw country-level HPI value) ---
    hpi_col = df["HOUSE_PRICE_INDEX"] if "HOUSE_PRICE_INDEX" in df.columns else pd.Series(
        [pd.NA] * len(df), index=df.index
    )

    # --- Factor 3: relative price per sqm, within-country ---
    df["country_avg_price_per_sqm"] = df.groupby("country_code")["price_per_sqm"].transform(
        "mean"
    )
    df["relative_price_per_sqm"] = df["price_per_sqm"] / df["country_avg_price_per_sqm"]

    # --- Normalize each factor to 0-100 (inverted: lower raw = higher score) ---
    score_pti = _min_max_normalize_inverted(df["price_to_income_ratio"].astype(float))
    score_hpi = _min_max_normalize_inverted(hpi_col.astype(float))
    score_rel_price = _min_max_normalize_inverted(df["relative_price_per_sqm"].astype(float))

    # Fill any remaining NaNs (e.g. missing indicator for a country) with
    # neutral midpoint so one missing factor doesn't zero out the listing.
    score_pti = score_pti.fillna(50.0)
    score_hpi = score_hpi.fillna(50.0)
    score_rel_price = score_rel_price.fillna(50.0)

    df["affordability_score"] = (
        WEIGHT_PRICE_TO_INCOME * score_pti
        + WEIGHT_HPI_POSITION * score_hpi
        + WEIGHT_RELATIVE_PRICE_PER_SQM * score_rel_price
    ).round(2)

    logger.info(
        f"Computed affordability scores for {len(df)} listings "
        f"(mean={df['affordability_score'].mean():.1f}, "
        f"min={df['affordability_score'].min():.1f}, "
        f"max={df['affordability_score'].max():.1f})."
    )

    return df[["id", "price_per_sqm", "affordability_score"]]