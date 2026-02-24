# MonteVerde Market — Dispute Intelligence API

Analytic API backend for MonteVerde Market's risk team to identify chargeback patterns, prioritize investigations, and reduce their chargeback ratio.

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
| GET | `/docs` | Swagger UI |

## Alert Logic

- **HIGH_CHARGEBACK_RATIO**: Merchant ratio > 1.5% → severity HIGH
- **WEEKLY_SPIKE**: Last 7 days chargebacks > 2× previous 7 days → severity MEDIUM
- **HIGH_VALUE_DISPUTE**: Transaction > $500 USD equivalent with chargeback → severity HIGH
  - Conversion: MXN ÷ 17, COP ÷ 4000, CLP ÷ 950

## Test Data Profile

- 12 merchants (2 problematic with ratio >1.5%)
- 5,000+ transactions spanning Oct–Dec 2024
- ~4% global chargeback ratio
- Black Friday spike (Nov 25): 3× normal chargeback volume
- 5 repeat offender customer IDs with 3+ chargebacks across merchants
- 3 high-risk BIN patterns with multiple chargebacks within 48h windows
- Reason codes: 10.4 (30%), 13.1 (35%), 13.3 (20%), 12.6 (8%), 13.2 (7%)
