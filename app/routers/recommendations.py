from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
from app.database import get_db
from app.schemas import Recommendation

router = APIRouter()

REASON_CODE_RECOMMENDATIONS = {
    "10.4": "Implement 3D Secure authentication to reduce card-not-present fraud. Review your fraud scoring rules.",
    "13.1": "Improve delivery confirmation and tracking. Use signed delivery for high-value orders.",
    "13.3": "Strengthen product descriptions and quality control. Implement return policies.",
    "12.6": "Ensure transaction receipts match billed amounts. Review duplicate transaction prevention logic.",
    "13.2": "Clarify subscription cancellation policy. Send reminders before recurring charges.",
}


@router.get("/recommendations", response_model=List[Recommendation])
def get_recommendations(db: Session = Depends(get_db)):
    rows = db.execute(text("""
        SELECT
            m.id AS merchant_id,
            m.name AS merchant_name,
            c.reason_code,
            COUNT(*) AS chargeback_count
        FROM chargebacks c
        JOIN transactions t ON t.id = c.transaction_id
        JOIN merchants m ON m.id = t.merchant_id
        GROUP BY m.id, m.name, c.reason_code
        ORDER BY m.id, chargeback_count DESC
    """)).fetchall()

    merchant_top: dict = {}
    for row in rows:
        mid = row[0]
        if mid not in merchant_top:
            merchant_top[mid] = {
                "merchant_id": row[0],
                "merchant_name": row[1],
                "dominant_reason_code": row[2],
                "chargeback_count": row[3],
            }

    return [
        Recommendation(
            merchant_id=v["merchant_id"],
            merchant_name=v["merchant_name"],
            dominant_reason_code=v["dominant_reason_code"],
            chargeback_count=v["chargeback_count"],
            recommendation=REASON_CODE_RECOMMENDATIONS.get(
                v["dominant_reason_code"],
                "Review chargeback patterns and implement additional fraud prevention measures.",
            ),
        )
        for v in merchant_top.values()
    ]
