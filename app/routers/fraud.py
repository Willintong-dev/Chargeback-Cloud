from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
from app.database import get_db
from app.schemas import FraudPattern

router = APIRouter()


@router.get("/fraud-patterns", response_model=List[FraudPattern])
def get_fraud_patterns(db: Session = Depends(get_db)):
    patterns = []

    repeat_offenders = db.execute(text("""
        SELECT
            t.customer_id,
            COUNT(DISTINCT c.id) AS chargeback_count,
            COUNT(DISTINCT t.merchant_id) AS merchant_count,
            SUM(c.amount) AS total_amount
        FROM chargebacks c
        JOIN transactions t ON t.id = c.transaction_id
        GROUP BY t.customer_id
        HAVING chargeback_count >= 3
        ORDER BY chargeback_count DESC
    """)).fetchall()

    for row in repeat_offenders:
        patterns.append(FraudPattern(
            pattern_type="REPEAT_OFFENDER",
            entity_id=row[0],
            chargeback_count=row[1],
            merchant_count=row[2],
            total_amount=row[3],
            time_window_hours=None,
        ))

    bin_patterns = db.execute(text("""
        SELECT
            t.card_bin,
            COUNT(DISTINCT c.id) AS chargeback_count,
            COUNT(DISTINCT t.merchant_id) AS merchant_count,
            SUM(c.amount) AS total_amount
        FROM chargebacks c
        JOIN transactions t ON t.id = c.transaction_id
        WHERE EXISTS (
            SELECT 1
            FROM chargebacks c2
            JOIN transactions t2 ON t2.id = c2.transaction_id
            WHERE t2.card_bin = t.card_bin
              AND t2.id != t.id
              AND ABS(JULIANDAY(c2.chargeback_date) - JULIANDAY(c.chargeback_date)) * 24 <= 48
        )
        GROUP BY t.card_bin
        HAVING chargeback_count >= 2
        ORDER BY chargeback_count DESC
    """)).fetchall()

    for row in bin_patterns:
        patterns.append(FraudPattern(
            pattern_type="BIN_PATTERN",
            entity_id=row[0],
            chargeback_count=row[1],
            merchant_count=row[2],
            total_amount=row[3],
            time_window_hours=48,
        ))

    return patterns
