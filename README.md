# 🏠 Eurozone Real Estate Market & Investment Affordability Index

An end-to-end, production-style data pipeline that scrapes property listings, integrates live Eurostat macroeconomic data, computes a custom **Investment Affordability Score (0–100)**, stores everything in PostgreSQL, and surfaces it all through an interactive Streamlit dashboard — orchestrated on a schedule with Prefect.

![Python](https://img.shields.io/badge/Python-3.12-blue)
![Scrapy](https://img.shields.io/badge/Scrapy-2.12-green)
![Prefect](https://img.shields.io/badge/Prefect-3.x-purple)
![Streamlit](https://img.shields.io/badge/Streamlit-1.40-red)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Neon-336791)

## 🎯 What this project does

1. **Scrapes** property-style listings via a custom Scrapy spider (validation + JSON audit trail + PostgreSQL upsert pipelines)
2. **Fetches live macroeconomic data** from the Eurostat API — median household income and House Price Index for 19 Eurozone countries
3. **Computes an Investment Affordability Score** per listing by combining price-to-income ratio, HPI market position, and relative price-per-m² within each country
4. **Stores everything in PostgreSQL** (Neon serverless) via SQLAlchemy ORM with proper upsert logic to avoid duplicates on re-runs
5. **Orchestrates the full pipeline** with Prefect — scraping and Eurostat fetching run concurrently, scoring runs after both complete, with automatic retries
6. **Visualizes it all** in an interactive Streamlit dashboard: KPIs, filters, charts, and a color-coded Folium map

## 🏗️ Architecture

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Scrapy    │────▶│                  │◀────│  Eurostat API    │
│   Spider    │     │   PostgreSQL     │     │  (median income, │
└─────────────┘     │   (Neon)         │     │   house price    │
                     │                  │     │   index)         │
┌─────────────┐      │  - property_     │     └─────────────────┘
│Affordability│────▶│    listings      │
│    Score     │     │  - eurostat_     │
│  Calculator  │     │    indicators    │
└─────────────┘      └────────┬─────────┘
       ▲                      │
       │                      ▼
┌──────┴───────┐      ┌───────────────┐
│   Prefect    │      │   Streamlit   │
│Orchestration │      │   Dashboard   │
└──────────────┘      └───────────────┘
```

## 📁 Project Structure

```
eurozone-realestate-index/
├── config/
│   └── settings.py              # Centralized env-based configuration
├── src/
│   ├── scraper/
│   │   ├── spiders/
│   │   │   └── property_spider.py
│   │   ├── items.py
│   │   ├── pipelines.py         # Validation, JSON export, PostgreSQL upsert
│   │   └── settings.py          # Scrapy framework settings
│   ├── etl/
│   │   ├── eurostat_client.py   # Eurostat API integration
│   │   ├── affordability_score.py
│   │   ├── run_eurostat_ingestion.py
│   │   └── run_affordability_scoring.py
│   ├── database/
│   │   ├── models.py            # SQLAlchemy ORM models
│   │   ├── db.py                # Engine/session management
│   │   └── crud.py              # Upsert helpers
│   └── utils/
│       └── logger.py            # Centralized logging
├── pipelines/
│   └── flow.py                  # Prefect orchestration flow
├── dashboard/
│   └── app.py                   # Streamlit dashboard
├── .streamlit/
│   └── config.toml              # Dashboard theme
├── tests/                       # Unit tests
├── requirements.txt
├── .env.example
└── scrapy.cfg
```

## ⚙️ Tech Stack

| Layer | Technology |
|---|---|
| Scraping | Scrapy, BeautifulSoup |
| Data processing | Pandas |
| Macroeconomic data | Eurostat API |
| Database | PostgreSQL (Neon), SQLAlchemy 2.0 |
| Orchestration | Prefect 3 |
| Dashboard | Streamlit, Plotly, Folium |
| Config/secrets | python-dotenv |

## 📊 The Investment Affordability Score

A 0–100 composite score (100 = most affordable / best investment value), weighted:

| Factor | Weight | Description |
|---|---|---|
| Price-to-Income Ratio | 50% | Years of median income needed to buy the property |
| House Price Index position | 25% | Country's current housing market position vs. 2015 baseline |
| Relative price per m² | 25% | How this listing compares to others in the same country |

Each factor is min-max normalized across the full dataset before weighting, so the score is always relative to the current data snapshot. Countries with missing macro data for a factor default to a neutral (50) contribution rather than breaking the score.

## 🚀 Getting Started

### Prerequisites
- Python 3.12
- A free [Neon](https://neon.tech) or Supabase PostgreSQL database

### Setup

```bash
git clone https://github.com/its-anshikapatel/eurozone-realestate-index.git
cd eurozone-realestate-index
python -m venv .venv
.venv\Scripts\Activate.ps1        # Windows
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
copy .env.example .env             # then fill in your DATABASE_URL
```

### Initialize the database
```bash
python -c "from src.database.db import init_db; init_db()"
```

### Run the full pipeline (scrape → Eurostat → score)
```bash
python pipelines\flow.py
```

### Launch the dashboard
```bash
streamlit run dashboard\app.py
```

## 🔄 Automated Scheduling

The Prefect flow (`pipelines/flow.py`) is designed to run on a weekly cadence. To schedule it:
- **Prefect Cloud**: create a deployment and attach a `CronSchedule` (e.g., `0 3 * * 1` for every Monday at 3 AM)
- **Self-hosted**: run `prefect server start` and register the flow with `prefect deploy`, or use Windows Task Scheduler / cron to invoke `python pipelines\flow.py` weekly

## 📝 Data Source Note

Real Eurozone listing portals (Idealista, Immobiliare.it, etc.) prohibit scraping in their Terms of Service and employ aggressive anti-bot measures unsuitable for a reliable public demo. This project instead targets **books.toscrape.com**, a stable scraping-practice sandbox maintained by Zyte (Scrapy's creators), and maps its catalog fields onto a realistic real-estate schema. City, country, property type, and size are deterministically derived (not random) from each item's unique ID so re-scrapes are stable — but these fields are **synthetic augmentation**, clearly flagged via the `is_synthetic_location` database column. Eurostat macroeconomic data is real and live.

**To point this at a real listings site**, only the CSS/XPath selectors in `src/scraper/spiders/property_spider.py`'s `parse()` and `parse_listing_detail()` methods need to change — the Item schema, pipelines, database layer, scoring logic, and dashboard are all source-agnostic.

## 🐛 Notable Engineering Challenges Solved

- **Windows venv/pip PATH conflicts**: resolved by consistently using `python -m pip` over bare `pip`, after discovering the venv's pip installation had become corrupted and needed a full rebuild
- **Twisted/pyOpenSSL/cryptography version incompatibility**: Scrapy's TLS stack requires precisely pinned versions (`twisted==24.3.0`, `pyopenssl==24.2.1`, `cryptography==42.0.5`) — newer releases break internal imports in `contextfactory.py`
- **Eurostat's inconsistent country codes**: Greece is `EL` in some datasets (`ilc_di03`) but `GR` in others (`prc_hpi_a`) — handled via broad fetch + local pandas filtering + ISO normalization at the client layer
- **Prefect/Pydantic forward-reference bug**: `PydanticUndefinedAnnotation: ResultRecordMetadata` error on flow startup, resolved by upgrading Prefect to a patched release
- **Serverless Postgres cold starts**: `pool_pre_ping=True` on the SQLAlchemy engine prevents stale-connection errors when Neon's compute suspends after inactivity and wakes on the next request
- **Module resolution across execution contexts**: explicit `sys.path` manipulation in both `pipelines/flow.py` and `dashboard/app.py` ensures `src`/`config` imports resolve correctly regardless of the working directory a script is invoked from

## 🧪 Testing

```bash
pytest tests/
```

## 📄 License

MIT
