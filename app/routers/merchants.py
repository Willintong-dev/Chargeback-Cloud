from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
from app.database import get_db
from app.schemas import MerchantRatio

router = APIRouter()


@router.get("/merchants/chargeback-ratio", response_model=List[MerchantRatio])
def get_merchant_chargeback_ratio(
    limit: int = Query(50, ge=1, le=500, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: Session = Depends(get_db),
):
    """
    Return all merchants ranked by chargeback ratio (descending).
    Merchants with ratio > 1.5% are candidates for the HIGH_CHARGEBACK_RATIO alert.
    """
    result = db.execute(text("""
        SELECT
            m.id AS merchant_id,
            m.name,
            m.country,
            COUNT(DISTINCT t.id) AS total_transactions,
            COUNT(DISTINCT c.id) AS total_chargebacks,
            ROUND(
                CAST(COUNT(DISTINCT c.id) AS FLOAT) / NULLIF(COUNT(DISTINCT t.id), 0) * 100,
                4
            ) AS chargeback_ratio
        FROM merchants m
        LEFT JOIN transactions t ON t.merchant_id = m.id
        LEFT JOIN chargebacks c ON c.transaction_id = t.id
        GROUP BY m.id, m.name, m.country
        ORDER BY chargeback_ratio DESC
        LIMIT :limit OFFSET :offset
    """), {"limit": limit, "offset": offset})
    rows = result.fetchall()
    return [
        MerchantRatio(
            merchant_id=row[0],
            name=row[1],
            country=row[2],
            total_transactions=row[3],
            total_chargebacks=row[4],
            chargeback_ratio=row[5] if row[5] is not None else 0.0,
        )
        for row in rows
    ]
