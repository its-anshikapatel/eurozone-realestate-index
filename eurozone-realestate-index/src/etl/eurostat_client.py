"""
Eurostat API client.

Strategy: fetch each dataset with only the 'freq' filter (no geo filter,
since Eurostat uses inconsistent country codes across datasets — e.g.
Greece is 'EL' in some datasets, 'GR' in others). We fetch broadly, then
filter down to our target Eurozone countries locally in pandas, matching
either code spelling and normalizing to standard ISO ('GR') for storage.
"""

from __future__ import annotations

import pandas as pd
import eurostat

from src.utils.logger import get_logger

logger = get_logger(__name__)

# Standard ISO alpha-2 codes we want in OUR database.
TARGET_COUNTRIES_ISO = {
    "AT", "BE", "CY", "DE", "EE", "ES", "FI", "FR", "GR", "IE",
    "IT", "LT", "LU", "LV", "MT", "NL", "PT", "SI", "SK",
}

# Eurostat's non-standard code(s) mapped to ISO, so we can recognize them
# in raw API responses regardless of which spelling a given dataset uses.
EUROSTAT_TO_ISO = {"EL": "GR"}


def _find_geo_col(df: pd.DataFrame) -> str:
    for c in df.columns:
        if "geo" in str(c).lower():
            return c
    raise ValueError(f"Could not find a 'geo' column among: {list(df.columns)}")


def _filter_to_target_countries(df: pd.DataFrame) -> pd.DataFrame:
    """Keep only rows whose geo code (after ISO normalization) is one we want."""
    geo_col = _find_geo_col(df)
    normalized = df[geo_col].map(lambda c: EUROSTAT_TO_ISO.get(c, c))
    return df[normalized.isin(TARGET_COUNTRIES_ISO)].copy()


def fetch_median_income() -> pd.DataFrame:
    logger.info("Fetching Eurostat median income data (ilc_di03)...")
    try:
        df = eurostat.get_data_df("ilc_di03", filter_pars={"freq": "A"})
    except Exception:
        logger.exception("Failed to fetch ilc_di03 from Eurostat API.")
        raise

    df = _filter_to_target_countries(df)

    mask = (
        (df.get("statinfo") == "MED_EI")
        & (df.get("age") == "TOTAL")
        & (df.get("sex") == "T")
        & (df.get("unit") == "EUR")
    )
    filtered = df[mask].copy()
    logger.info(f"ilc_di03 filtered to {len(filtered)} rows matching MED_EI/TOTAL/T/EUR.")

    return _tidy_eurostat_df(
        filtered,
        indicator_code="MEDIAN_INCOME_EUR",
        indicator_name="Median equivalised income (EUR)",
        unit="EUR",
    )


def fetch_house_price_index() -> pd.DataFrame:
    logger.info("Fetching Eurostat House Price Index data (prc_hpi_a)...")
    try:
        df = eurostat.get_data_df("prc_hpi_a", filter_pars={"freq": "A"})
    except Exception:
        logger.exception("Failed to fetch prc_hpi_a from Eurostat API.")
        raise

    df = _filter_to_target_countries(df)

    mask = (df.get("purchase") == "TOTAL") & (df.get("unit") == "I15_A_AVG")
    filtered = df[mask].copy()
    logger.info(f"prc_hpi_a filtered to {len(filtered)} rows matching TOTAL/I15_A_AVG.")

    return _tidy_eurostat_df(
        filtered,
        indicator_code="HOUSE_PRICE_INDEX",
        indicator_name="House Price Index (2015=100)",
        unit="INDEX",
    )


def _tidy_eurostat_df(
    df: pd.DataFrame, indicator_code: str, indicator_name: str, unit: str
) -> pd.DataFrame:
    if df is None or df.empty:
        logger.warning(f"No matching rows for {indicator_code} after local filtering.")
        return pd.DataFrame(
            columns=["country_code", "indicator_code", "indicator_name", "year", "value", "unit"]
        )

    geo_col = _find_geo_col(df)
    year_cols = [c for c in df.columns if str(c).isdigit()]

    if not year_cols:
        logger.warning(
            f"No year columns found for {indicator_code}; columns: {list(df.columns)}"
        )
        return pd.DataFrame(
            columns=["country_code", "indicator_code", "indicator_name", "year", "value", "unit"]
        )

    records = []
    for _, row in df.iterrows():
        country_code = EUROSTAT_TO_ISO.get(row[geo_col], row[geo_col])
        for year_col in sorted(year_cols, key=int, reverse=True):
            value = row[year_col]
            if pd.notna(value):
                records.append(
                    {
                        "country_code": country_code,
                        "indicator_code": indicator_code,
                        "indicator_name": indicator_name,
                        "year": int(year_col),
                        "value": float(value),
                        "unit": unit,
                    }
                )
                break

    result = pd.DataFrame(records)
    logger.info(f"Tidied {indicator_code}: {len(result)} country records.")
    return result


def fetch_all_indicators() -> pd.DataFrame:
    income_df = fetch_median_income()
    hpi_df = fetch_house_price_index()
    combined = pd.concat([income_df, hpi_df], ignore_index=True)
    logger.info(f"Combined Eurostat indicators: {len(combined)} total rows.")
    return combined