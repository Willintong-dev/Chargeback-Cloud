from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
from app.database import get_db
from app.schemas import TrendPoint

router = APIRouter()


@router.get("/trends", response_model=List[TrendPoint])
def get_trends(
    granularity: str = Query("daily", description="daily or weekly"),
    db: Session = Depends(get_db),
):
    if granularity not in ("daily", "weekly"):
        raise HTTPException(status_code=400, detail="granularity must be 'daily' or 'weekly'")

    if granularity == "daily":
        result = db.execute(text("""
            SELECT
                DATE(chargeback_date) AS period,
                COUNT(*) AS chargeback_count,
                SUM(amount) AS total_amount
            FROM chargebacks
            GROUP BY DATE(chargeback_date)
            ORDER BY period ASC
        """))
    else:
        result = db.execute(text("""
            SELECT
                strftime('%Y-W%W', chargeback_date) AS period,
                COUNT(*) AS chargeback_count,
                SUM(amount) AS total_amount
            FROM chargebacks
            GROUP BY strftime('%Y-W%W', chargeback_date)
            ORDER BY period ASC
        """))

    rows = result.fetchall()
    return [
        TrendPoint(period=row[0], chargeback_count=row[1], total_amount=row[2])
        for row in rows
    ]
