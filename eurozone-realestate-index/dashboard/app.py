"""
Streamlit dashboard for the Eurozone Real Estate Market & Investment
Affordability Index.

Run with: streamlit run dashboard/app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import folium
import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import text
from streamlit_folium import st_folium

from config.settings import settings
from src.database.db import engine

st.set_page_config(
    page_title="Eurozone Real Estate Affordability Index",
    page_icon="🏠",
    layout="wide",
)

PALETTE = px.colors.sequential.Tealgrn
CATEGORICAL_PALETTE = px.colors.qualitative.Prism


# ---------------------------------------------------------------------------
# Custom CSS
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    .kpi-card {
        background-color: #FFFFFF;
        border: 1px solid #E5E4DD;
        border-radius: 10px;
        padding: 1.1rem 1.3rem;
        text-align: left;
    }
    .kpi-label {
        font-size: 0.8rem;
        color: #6B6B63;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        margin-bottom: 0.2rem;
    }
    .kpi-value {
        font-size: 1.9rem;
        font-weight: 700;
        color: #2E5B4E;
    }
    div[data-testid="stExpander"] {
        border: none;
        box-shadow: none;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Data loading (cached so we don't hit the DB on every filter interaction)
# ---------------------------------------------------------------------------
@st.cache_data(ttl=600)
def load_listings() -> pd.DataFrame:
    query = text(
        """
        SELECT id, title, city, country, country_code, property_type,
               price_eur, size_sqm, bedrooms, price_per_sqm,
               affordability_score, latitude, longitude, listing_url,
               scraped_at
        FROM property_listings
        WHERE affordability_score IS NOT NULL
        """
    )
    with engine.connect() as conn:
        return pd.read_sql(query, conn)


@st.cache_data(ttl=600)
def load_indicators() -> pd.DataFrame:
    query = text("SELECT country_code, indicator_code, year, value FROM eurostat_indicators")
    with engine.connect() as conn:
        return pd.read_sql(query, conn)


listings_df = load_listings()
indicators_df = load_indicators()

if listings_df.empty:
    st.error(
        "No property listings found in the database. "
        "Run the pipeline first: `python pipelines/flow.py`"
    )
    st.stop()


# ---------------------------------------------------------------------------
# Sidebar filters
# ---------------------------------------------------------------------------
st.sidebar.header("Filters")

countries = sorted(listings_df["country"].unique())
with st.sidebar.expander("Country", expanded=True):
    selected_countries = st.pills(
        "Country", countries, selection_mode="multi", default=countries,
        label_visibility="collapsed",
    )

property_types = sorted(listings_df["property_type"].unique())
with st.sidebar.expander("Property Type", expanded=True):
    selected_types = st.pills(
        "Property Type", property_types, selection_mode="multi", default=property_types,
        label_visibility="collapsed",
    )

bedroom_options = sorted(listings_df["bedrooms"].unique())
with st.sidebar.expander("Bedrooms", expanded=False):
    selected_bedrooms = st.pills(
        "Bedrooms", bedroom_options, selection_mode="multi", default=bedroom_options,
        label_visibility="collapsed",
    )

st.sidebar.markdown("")
price_min, price_max = int(listings_df["price_eur"].min()), int(listings_df["price_eur"].max())
price_range = st.sidebar.slider(
    "Price Range (EUR)", price_min, price_max, (price_min, price_max), step=1000
)

score_range = st.sidebar.slider("Affordability Score", 0, 100, (0, 100))

filtered_df = listings_df[
    (listings_df["country"].isin(selected_countries))
    & (listings_df["property_type"].isin(selected_types))
    & (listings_df["price_eur"].between(*price_range))
    & (listings_df["bedrooms"].isin(selected_bedrooms))
    & (listings_df["affordability_score"].between(*score_range))
]

st.sidebar.markdown("---")
st.sidebar.caption(f"Showing {len(filtered_df):,} of {len(listings_df):,} listings")


# ---------------------------------------------------------------------------
# Header + KPIs
# ---------------------------------------------------------------------------
st.title("🏠 Eurozone Real Estate Market & Investment Affordability Index")
st.caption(
    "Automated pipeline: Scrapy → Eurostat API → PostgreSQL → Affordability Score → Dashboard"
)

kpi_data = [
    ("Total Listings", f"{len(filtered_df):,}"),
    ("Avg. Price", f"€{filtered_df['price_eur'].mean():,.0f}" if len(filtered_df) else "—"),
    (
        "Avg. Affordability Score",
        f"{filtered_df['affordability_score'].mean():.1f}" if len(filtered_df) else "—",
    ),
    ("Countries Covered", f"{filtered_df['country'].nunique()}"),
]

cols = st.columns(4)
for col, (label, value) in zip(cols, kpi_data):
    col.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("<br>", unsafe_allow_html=True)
st.markdown("---")


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------
chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    st.subheader("Price Distribution")
    fig_hist = px.histogram(
        filtered_df, x="price_eur", nbins=40,
        labels={"price_eur": "Price (EUR)"},
        color_discrete_sequence=[PALETTE[len(PALETTE) // 2]],
    )
    fig_hist.update_layout(showlegend=False, height=350)
    st.plotly_chart(fig_hist, use_container_width=True)

with chart_col2:
    st.subheader("Affordability Score vs. Price")
    fig_scatter = px.scatter(
        filtered_df,
        x="price_eur",
        y="affordability_score",
        color="country",
        color_discrete_sequence=CATEGORICAL_PALETTE,
        hover_data=["title", "city", "property_type"],
        labels={"price_eur": "Price (EUR)", "affordability_score": "Affordability Score"},
    )
    fig_scatter.update_layout(height=350)
    st.plotly_chart(fig_scatter, use_container_width=True)

st.subheader("Average Price per m² by Country")
avg_by_country = (
    filtered_df.groupby("country")["price_per_sqm"].mean().sort_values(ascending=False).reset_index()
)
fig_bar = px.bar(
    avg_by_country,
    x="country",
    y="price_per_sqm",
    labels={"country": "Country", "price_per_sqm": "Avg. Price per m² (EUR)"},
    color="price_per_sqm",
    color_continuous_scale="Tealgrn",
)
fig_bar.update_layout(height=350)
st.plotly_chart(fig_bar, use_container_width=True)


# ---------------------------------------------------------------------------
# Map
# ---------------------------------------------------------------------------
st.subheader("Listings Map (colored by Affordability Score)")


def _score_color(score: float) -> str:
    if score >= 66:
        return "green"
    elif score >= 33:
        return "orange"
    return "red"


if len(filtered_df):
    map_center = [filtered_df["latitude"].mean(), filtered_df["longitude"].mean()]
    m = folium.Map(location=map_center, zoom_start=4, tiles="cartodbpositron")

    # Sample for performance if too many points
    map_df = filtered_df if len(filtered_df) <= 500 else filtered_df.sample(500, random_state=42)

    for _, row in map_df.iterrows():
        folium.CircleMarker(
            location=[row["latitude"], row["longitude"]],
            radius=5,
            color=_score_color(row["affordability_score"]),
            fill=True,
            fill_opacity=0.7,
            popup=folium.Popup(
                f"<b>{row['title'][:60]}</b><br>"
                f"{row['city']}, {row['country']}<br>"
                f"€{row['price_eur']:,.0f} — {row['size_sqm']:.0f}m²<br>"
                f"Score: {row['affordability_score']:.1f}",
                max_width=250,
            ),
        ).add_to(m)

    st_folium(m, width=None, height=500, returned_objects=[])
else:
    st.info("No listings match the current filters.")


# ---------------------------------------------------------------------------
# Data table
# ---------------------------------------------------------------------------
st.subheader("Filtered Listings")
st.dataframe(
    filtered_df[
        [
            "title", "city", "country", "property_type", "price_eur",
            "size_sqm", "bedrooms", "price_per_sqm", "affordability_score",
        ]
    ].sort_values("affordability_score", ascending=False),
    use_container_width=True,
    hide_index=True,
)

st.caption(
    "Data note: property listings sourced from a scraping-practice site (books.toscrape.com) "
    "with realistic synthetic location/attribute augmentation for demonstration purposes. "
    "Eurostat macroeconomic indicators are real, live data. See README for details."
)