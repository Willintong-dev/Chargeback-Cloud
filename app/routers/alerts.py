from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
from app.database import get_db
from app.constants import HIGH_VALUE_THRESHOLD_USD, MERCHANT_RATIO_ALERT_THRESHOLD, currency_to_usd_sql
from app.schemas import Alert

router = APIRouter()


@router.get("/alerts", response_model=List[Alert])
def get_alerts(
    ratio_threshold: float = Query(MERCHANT_RATIO_ALERT_THRESHOLD, description="Chargeback ratio threshold (%) for merchant alerts"),
    db: Session = Depends(get_db),
):
    alerts = []

    merchant_rows = db.execute(text(f"""
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
        HAVING ratio > :ratio_threshold
    """), {"ratio_threshold": ratio_threshold}).fetchall()

    for row in merchant_rows:
        alerts.append(Alert(
            alert_type="HIGH_CHARGEBACK_RATIO",
            severity="HIGH",
            description=f"Merchant '{row[1]}' has chargeback ratio of {row[4]:.2f}% (threshold: {ratio_threshold}%)",
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

    usd_expr = currency_to_usd_sql()
    high_value_rows = db.execute(text(f"""
        SELECT
            t.id AS transaction_id,
            m.id AS merchant_id,
            m.name AS merchant_name,
            ROUND({usd_expr}, 2) AS amount_usd
        FROM chargebacks c
        JOIN transactions t ON t.id = c.transaction_id
        JOIN merchants m ON m.id = t.merchant_id
        WHERE {usd_expr} > :threshold
    """), {"threshold": HIGH_VALUE_THRESHOLD_USD}).fetchall()

    for row in high_value_rows:
        alerts.append(Alert(
            alert_type="HIGH_VALUE_DISPUTE",
            severity="HIGH",
            description=f"High-value chargeback ${row[3]:.2f} USD on transaction {row[0]} at '{row[2]}'",
            entity_id=row[1],
            entity_name=row[2],
            metric_value=row[3],
        ))

    return alerts
