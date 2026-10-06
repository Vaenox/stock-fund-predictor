from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PredictionHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    asset_id: UUID
    prediction_date: date
    generated_at: datetime
    data_as_of: date

    horizon_days: int
    target_return_threshold: float
    model_family: str
    model_version: str | None
    feature_representation: str

    ml_probability: float
    technical_score: float
    risk_score: float
    risk_adjustment: float
    signal_score: float
    target_weight: float

    quality_ok: bool
    stale_days: int
    source_provider: str
    reasons: list[str]

    created_at: datetime
