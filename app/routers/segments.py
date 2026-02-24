from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
from app.database import get_db
from app.schemas import HighRiskSegment

router = APIRouter()

VALID_DIMENSIONS = {"country", "category", "payment_method"}


@router.get("/segments/high-risk", response_model=List[HighRiskSegment])
def get_high_risk_segments(
    dimension: str = Query(..., description="country, category, or payment_method"),
    threshold: float = Query(1.5, description="Chargeback ratio threshold (%)"),
    db: Session = Depends(get_db),
):
    if dimension not in VALID_DIMENSIONS:
        raise HTTPException(status_code=400, detail=f"dimension must be one of: {', '.join(VALID_DIMENSIONS)}")

    dimension_column_map = {
        "country": "t.country",
        "category": "t.product_category",
        "payment_method": "t.payment_method",
    }
    col = dimension_column_map[dimension]

    result = db.execute(text(f"""
        SELECT
            :dimension AS dimension,
            {col} AS segment_value,
            COUNT(DISTINCT t.id) AS total_transactions,
            COUNT(DISTINCT c.id) AS total_chargebacks,
            ROUND(CAST(COUNT(DISTINCT c.id) AS FLOAT) / COUNT(DISTINCT t.id) * 100, 4) AS chargeback_ratio
        FROM transactions t
        LEFT JOIN chargebacks c ON c.transaction_id = t.id
        GROUP BY {col}
        HAVING chargeback_ratio > :threshold
        ORDER BY chargeback_ratio DESC
    """), {"dimension": dimension, "threshold": threshold})

    rows = result.fetchall()
    return [
        HighRiskSegment(
            dimension=row[0],
            segment_value=row[1],
            total_transactions=row[2],
            total_chargebacks=row[3],
            chargeback_ratio=row[4],
        )
        for row in rows
    ]
