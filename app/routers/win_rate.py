from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
from app.database import get_db
from app.schemas import WinRateByReasonCode

router = APIRouter()


@router.get("/win-rate", response_model=List[WinRateByReasonCode])
def get_win_rate(
    limit: int = Query(50, ge=1, le=500, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: Session = Depends(get_db),
):
    """
    Return dispute win rate per reason code.
    Win rate is computed over resolved disputes only (won + lost); open cases are excluded from the denominator.
    """
    rows = db.execute(text("""
        SELECT
            reason_code,
            reason_description,
            COUNT(*) AS total,
            SUM(CASE WHEN status = 'won' THEN 1 ELSE 0 END) AS won,
            SUM(CASE WHEN status = 'lost' THEN 1 ELSE 0 END) AS lost,
            SUM(CASE WHEN status = 'open' THEN 1 ELSE 0 END) AS open,
            ROUND(
                CAST(SUM(CASE WHEN status = 'won' THEN 1 ELSE 0 END) AS FLOAT)
                / NULLIF(
                    SUM(CASE WHEN status IN ('won', 'lost') THEN 1 ELSE 0 END),
                    0
                ) * 100,
                2
            ) AS win_rate
        FROM chargebacks
        GROUP BY reason_code, reason_description
        ORDER BY win_rate DESC
        LIMIT :limit OFFSET :offset
    """), {"limit": limit, "offset": offset}).fetchall()

    return [
        WinRateByReasonCode(
            reason_code=row[0],
            reason_description=row[1],
            total=row[2],
            won=row[3],
            lost=row[4],
            open=row[5],
            win_rate=row[6] if row[6] is not None else 0.0,
        )
        for row in rows
    ]
