from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
from app.database import get_db
from app.schemas import ReasonCodeSummary

router = APIRouter()


@router.get("/reason-codes", response_model=List[ReasonCodeSummary])
def get_reason_codes(
    limit: int = Query(50, ge=1, le=500, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: Session = Depends(get_db),
):
    """
    Return chargeback counts, total disputed amount, and share percentage per reason code.
    Ordered by frequency descending.
    """
    result = db.execute(text("""
        SELECT
            reason_code,
            reason_description,
            COUNT(*) AS count,
            SUM(amount) AS total_amount,
            ROUND(CAST(COUNT(*) AS FLOAT) / NULLIF((SELECT COUNT(*) FROM chargebacks), 0) * 100, 2) AS percentage
        FROM chargebacks
        GROUP BY reason_code, reason_description
        ORDER BY count DESC
        LIMIT :limit OFFSET :offset
    """), {"limit": limit, "offset": offset})
    rows = result.fetchall()
    return [
        ReasonCodeSummary(
            reason_code=row[0],
            reason_description=row[1],
            count=row[2],
            total_amount=row[3],
            percentage=row[4],
        )
        for row in rows
    ]
