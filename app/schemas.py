from pydantic import BaseModel
from typing import Optional


class MerchantRatio(BaseModel):
    merchant_id: str
    name: str
    country: str
    total_transactions: int
    total_chargebacks: int
    chargeback_ratio: float


class ReasonCodeSummary(BaseModel):
    reason_code: str
    reason_description: str
    count: int
    total_amount: float
    percentage: float


class HighRiskSegment(BaseModel):
    dimension: str
    segment_value: str
    total_transactions: int
    total_chargebacks: int
    chargeback_ratio: float


class TrendPoint(BaseModel):
    period: str
    chargeback_count: int
    total_amount: float


class Alert(BaseModel):
    alert_type: str
    severity: str
    description: str
    entity_id: Optional[str] = None
    entity_name: Optional[str] = None
    metric_value: Optional[float] = None


class FraudPattern(BaseModel):
    pattern_type: str
    entity_id: str
    chargeback_count: int
    merchant_count: int
    total_amount: float
    time_window_hours: Optional[int] = None


class Recommendation(BaseModel):
    merchant_id: str
    merchant_name: str
    dominant_reason_code: str
    chargeback_count: int
    recommendation: str
