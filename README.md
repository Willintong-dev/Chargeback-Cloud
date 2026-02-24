# MonteVerde Market — Dispute Intelligence API

Analytic API backend for MonteVerde Market's risk team to identify chargeback patterns, prioritize investigations, and reduce their chargeback ratio.

## Architecture

```
app/
├── main.py          # FastAPI app, lifespan handler, router registration
├── database.py      # SQLite engine, SessionLocal, get_db() dependency
├── models.py        # SQLAlchemy ORM models with explicit indexes
├── schemas.py       # Pydantic response models
├── constants.py     # Shared config: currency rates, thresholds, SQL helpers
└── routers/
    ├── merchants.py      # Chargeback ratio ranking
    ├── reason_codes.py   # Reason code breakdown
    ├── segments.py       # High-risk segment detection
    ├── trends.py         # Temporal trend analysis
    ├── alerts.py         # Alert engine (3 signal types)
    ├── fraud.py          # Fraud pattern detection (CTE-based)
    ├── recommendations.py # Action recommendations (window function)
    └── win_rate.py       # Dispute outcome correlation
scripts/
└── seed_data.py     # Generates 5900+ txs with engineered fraud patterns
tests/
├── conftest.py      # In-memory SQLite fixtures (StaticPool)
└── test_api.py      # 19 tests covering all endpoints
```

All analytical queries use raw SQL via SQLAlchemy `text()`. ORM is only used for schema definition and seed inserts. Currency conversion rates are centralized in `constants.py` and injected into SQL via `currency_to_usd_sql()` to avoid duplication.

## Deployment

**Local:**
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**Production (any WSGI/ASGI host):**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

To swap SQLite for PostgreSQL, replace `SQLALCHEMY_DATABASE_URL` in `database.py` — all queries use ANSI SQL compatible with PostgreSQL except `strftime()` in `trends.py` (replace with `DATE_TRUNC`).

## Stack

- **Python 3.11+** / **FastAPI** — async HTTP framework with auto Swagger UI
- **SQLite** — zero-config embedded database
- **SQLAlchemy** — ORM + raw SQL via `text()` for analytics
- **Faker** — realistic test data generation
- **pytest + httpx** — test suite with FastAPI TestClient

## Quick Start

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Then seed the database and explore:

```bash
curl -X POST http://localhost:8000/api/seed
curl http://localhost:8000/api/merchants/chargeback-ratio
curl "http://localhost:8000/api/segments/high-risk?dimension=country&threshold=1.5"
curl "http://localhost:8000/api/trends?granularity=weekly"
curl http://localhost:8000/api/reason-codes
curl http://localhost:8000/api/alerts
curl http://localhost:8000/api/fraud-patterns
curl http://localhost:8000/api/recommendations
open http://localhost:8000/docs
```

## Run Tests

```bash
pytest tests/ -v
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/seed` | Load test data (12 merchants, 5000+ txs, 200+ chargebacks) |
| GET | `/api/merchants/chargeback-ratio` | Merchants ranked by chargeback ratio |
| GET | `/api/reason-codes` | Breakdown by reason code (count + total amount) |
| GET | `/api/segments/high-risk` | Segments with ratio > threshold (`?dimension=country\|category\|payment_method&threshold=1.5`) |
| GET | `/api/trends` | Chargeback volume over time (`?granularity=daily\|weekly`) |
| GET | `/api/alerts` | Active alerts with severity (HIGH/MEDIUM) |
| GET | `/api/fraud-patterns` | Repeat offenders by customer_id and BIN patterns within 48h |
| GET | `/api/recommendations` | Action recommendations per merchant based on dominant reason code |
| GET | `/api/win-rate` | Dispute win rate correlation by reason code (won/lost/open breakdown) |
| GET | `/docs` | Swagger UI |

## Alert Logic

- **HIGH_CHARGEBACK_RATIO**: Merchant ratio > 1.5% → severity HIGH
- **WEEKLY_SPIKE**: Last 7 days chargebacks > 2× previous 7 days → severity MEDIUM
- **HIGH_VALUE_DISPUTE**: Transaction > $500 USD equivalent with chargeback → severity HIGH
  - Conversion: MXN ÷ 17, COP ÷ 4000, CLP ÷ 950

## Key Insights from Test Data

Analysis of the synthetic Oct–Dec 2024 dataset reveals two merchants ("TechZone Express MX" and "Moda Rapida CO") with chargeback ratios above 3%, well beyond the 1.5% processor threshold that triggers penalties. The dominant reason code across both is **13.1 (Merchandise Not Received, 35%)** and **10.4 (Card-Not-Present Fraud, 30%)**, suggesting a dual problem: fulfillment failures in the physical goods segment and weak CNP fraud controls on credit card transactions. Electronics is the highest-risk product category by both volume and dollar exposure.

A clear Black Friday spike (week of Nov 25) shows chargebacks tripling relative to the prior week — driven largely by Digital Goods and Electronics purchases made with credit cards carrying three specific BIN prefixes that appear in 48-hour fraud clusters. Five repeat-offender customer IDs account for chargebacks spread across multiple merchants, indicating a coordinated pattern rather than isolated buyer disputes. Win rate analysis shows merchants recover disputes under code **12.6 (Duplicate Processing)** at a significantly higher rate than **10.4 (CNP Fraud)**, where evidence requirements are stricter. The recommended immediate actions are: enforce 3DS on Electronics/Digital Goods credit card transactions and implement BIN-level velocity checks at authorization time.

## Test Data Profile

- 12 merchants (2 problematic with ratio >1.5%)
- 5,000+ transactions spanning Oct–Dec 2024
- ~4% global chargeback ratio
- Black Friday spike (Nov 25): 3× normal chargeback volume
- 5 repeat offender customer IDs with 3+ chargebacks across merchants
- 3 high-risk BIN patterns with multiple chargebacks within 48h windows
- Reason codes: 10.4 (30%), 13.1 (35%), 13.3 (20%), 12.6 (8%), 13.2 (7%)
