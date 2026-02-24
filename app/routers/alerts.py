from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
from app.database import get_db
from app.schemas import Alert

router = APIRouter()

CURRENCY_TO_USD = {"MXN": 17.0, "COP": 4000.0, "CLP": 950.0}
HIGH_VALUE_THRESHOLD_USD = 500.0


@router.get("/alerts", response_model=List[Alert])
def get_alerts(db: Session = Depends(get_db)):
    alerts = []

    merchant_rows = db.execute(text("""
        SELECT
            m.id,
            m.name,
            COUNT(DISTINCT t.id) AS total_transactions,
            COUNT(DISTINCT c.id) AS total_chargebacks,
            ROUND(CAST(COUNT(DISTINCT c.id) AS FLOAT) / NULLIF(COUNT(DISTINCT t.id), 0) * 100, 4) AS ratio
        FROM merchants m
        LEFT JOIN transactions t ON t.merchant_id = m.id
        LEFT JOIN chargebacks c ON c.transaction_id = t.id
        GROUP BY m.id, m.name
        HAVING ratio > 1.5
    """)).fetchall()

    for row in merchant_rows:
        alerts.append(Alert(
            alert_type="HIGH_CHARGEBACK_RATIO",
            severity="HIGH",
            description=f"Merchant '{row[1]}' has chargeback ratio of {row[4]:.2f}% (threshold: 1.5%)",
            entity_id=row[0],
            entity_name=row[1],
            metric_value=row[4],
        ))

    spike_row = db.execute(text("""
        WITH last7 AS (
            SELECT COUNT(*) AS cnt
            FROM chargebacks
            WHERE chargeback_date >= DATE('now', '-7 days')
        ),
        prev7 AS (
            SELECT COUNT(*) AS cnt
            FROM chargebacks
            WHERE chargeback_date >= DATE('now', '-14 days')
              AND chargeback_date < DATE('now', '-7 days')
        )
        SELECT last7.cnt, prev7.cnt
        FROM last7, prev7
    """)).fetchone()

    if spike_row and spike_row[1] > 0 and spike_row[0] > 2 * spike_row[1]:
        alerts.append(Alert(
            alert_type="WEEKLY_SPIKE",
            severity="MEDIUM",
            description=f"Chargeback spike detected: {spike_row[0]} in last 7 days vs {spike_row[1]} in previous 7 days",
            metric_value=spike_row[0],
        ))

    high_value_rows = db.execute(text("""
        SELECT
            c.id,
            t.amount,
            t.currency,
            t.id AS transaction_id,
            m.name AS merchant_name,
            m.id AS merchant_id
        FROM chargebacks c
        JOIN transactions t ON t.id = c.transaction_id
        JOIN merchants m ON m.id = t.merchant_id
    """)).fetchall()

    for row in high_value_rows:
        divisor = CURRENCY_TO_USD.get(row[2], 1.0)
        amount_usd = row[1] / divisor
        if amount_usd > HIGH_VALUE_THRESHOLD_USD:
            alerts.append(Alert(
                alert_type="HIGH_VALUE_DISPUTE",
                severity="HIGH",
                description=f"High-value chargeback ${amount_usd:.2f} USD on transaction {row[3]} at '{row[4]}'",
                entity_id=row[5],
                entity_name=row[4],
                metric_value=round(amount_usd, 2),
            ))

    return alerts
