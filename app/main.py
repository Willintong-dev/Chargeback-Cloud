from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from app.database import create_tables, get_db
from app.routers import merchants, reason_codes, segments, trends, alerts, fraud, recommendations, win_rate


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    yield


app = FastAPI(
    title="MonteVerde Market — Dispute Intelligence API",
    description="Analytic API to identify chargeback patterns, prioritize investigations and reduce chargeback ratio.",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(merchants.router, prefix="/api", tags=["Merchants"])
app.include_router(reason_codes.router, prefix="/api", tags=["Reason Codes"])
app.include_router(segments.router, prefix="/api", tags=["Segments"])
app.include_router(trends.router, prefix="/api", tags=["Trends"])
app.include_router(alerts.router, prefix="/api", tags=["Alerts"])
app.include_router(fraud.router, prefix="/api", tags=["Fraud Patterns"])
app.include_router(recommendations.router, prefix="/api", tags=["Recommendations"])
app.include_router(win_rate.router, prefix="/api", tags=["Win Rate"])


@app.post("/api/seed", tags=["Seed"])
def seed_data(db: Session = Depends(get_db)):
    from scripts.seed_data import run_seed
    inserted = run_seed(db)
    return inserted
