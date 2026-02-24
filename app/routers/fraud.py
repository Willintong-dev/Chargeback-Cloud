from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
from app.database import get_db
from app.schemas import FraudPattern

router = APIRouter()


@router.get("/fraud-patterns", response_model=List[FraudPattern])
def get_fraud_patterns(
    limit: int = Query(50, ge=1, le=500, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: Session = Depends(get_db),
):
    """
    Detect two fraud signal types:
    - **REPEAT_OFFENDER**: customers with 3+ chargebacks across any merchants.
    - **BIN_PATTERN**: card BINs with 2+ chargebacks within a 48-hour window.
    """
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
        LIMIT :limit OFFSET :offset
    """), {"limit": limit, "offset": offset}).fetchall()

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
        WITH cb_bins AS (
            SELECT
                t.card_bin,
                c.id AS cb_id,
                c.chargeback_date,
                t.merchant_id,
                c.amount
            FROM chargebacks c
            JOIN transactions t ON t.id = c.transaction_id
        ),
        bin_pairs AS (
            SELECT DISTINCT a.card_bin
            FROM cb_bins a
            JOIN cb_bins b
              ON a.card_bin = b.card_bin
             AND a.cb_id != b.cb_id
             AND ABS(JULIANDAY(a.chargeback_date) - JULIANDAY(b.chargeback_date)) * 24 <= 48
        )
        SELECT
            cb.card_bin,
            COUNT(DISTINCT cb.cb_id)      AS chargeback_count,
            COUNT(DISTINCT cb.merchant_id) AS merchant_count,
            SUM(cb.amount)                AS total_amount
        FROM cb_bins cb
        JOIN bin_pairs bp ON bp.card_bin = cb.card_bin
        GROUP BY cb.card_bin
        HAVING chargeback_count >= 2
        ORDER BY chargeback_count DESC
        LIMIT :limit OFFSET :offset
    """), {"limit": limit, "offset": offset}).fetchall()

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
