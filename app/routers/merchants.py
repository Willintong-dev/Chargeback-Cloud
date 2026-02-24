from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
from app.database import get_db
from app.schemas import MerchantRatio

router = APIRouter()


@router.get("/merchants/chargeback-ratio", response_model=List[MerchantRatio])
def get_merchant_chargeback_ratio(db: Session = Depends(get_db)):
    result = db.execute(text("""
        SELECT
            m.id AS merchant_id,
            m.name,
            m.country,
            COUNT(DISTINCT t.id) AS total_transactions,
            COUNT(DISTINCT c.id) AS total_chargebacks,
            CASE
                WHEN COUNT(DISTINCT t.id) = 0 THEN 0.0
                ELSE ROUND(CAST(COUNT(DISTINCT c.id) AS FLOAT) / COUNT(DISTINCT t.id) * 100, 4)
            END AS chargeback_ratio
        FROM merchants m
        LEFT JOIN transactions t ON t.merchant_id = m.id
        LEFT JOIN chargebacks c ON c.transaction_id = t.id
        GROUP BY m.id, m.name, m.country
        ORDER BY chargeback_ratio DESC
    """))
    rows = result.fetchall()
    return [
        MerchantRatio(
            merchant_id=row[0],
            name=row[1],
            country=row[2],
            total_transactions=row[3],
            total_chargebacks=row[4],
            chargeback_ratio=row[5],
        )
        for row in rows
    ]
