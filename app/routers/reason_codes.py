from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
from app.database import get_db
from app.schemas import ReasonCodeSummary

router = APIRouter()


@router.get("/reason-codes", response_model=List[ReasonCodeSummary])
def get_reason_codes(db: Session = Depends(get_db)):
    result = db.execute(text("""
        SELECT
            reason_code,
            reason_description,
            COUNT(*) AS count,
            SUM(amount) AS total_amount,
            ROUND(CAST(COUNT(*) AS FLOAT) / (SELECT COUNT(*) FROM chargebacks) * 100, 2) AS percentage
        FROM chargebacks
        GROUP BY reason_code, reason_description
        ORDER BY count DESC
    """))
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
