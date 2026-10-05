from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


class PredictionHistoryCreate(BaseModel):
    """Validated payload for one append-only prediction history record."""

    asset_id: UUID
    prediction_date: date
    generated_at: datetime
    data_as_of: date

    horizon_days: int = Field(gt=0, le=365)
    target_return_threshold: Decimal = Field(ge=-1, le=1)
    model_family: str = Field(min_length=1, max_length=64)
    model_version: str | None = Field(default=None, max_length=128)
    feature_representation: str = Field(min_length=1, max_length=64)

    ml_probability: Decimal = Field(ge=0, le=1)
    technical_score: Decimal = Field(ge=0, le=100)
    risk_score: Decimal = Field(ge=0, le=100)
    risk_adjustment: Decimal = Field(le=0, ge=-100)
    signal_score: Decimal = Field(ge=0, le=100)
    target_weight: Decimal = Field(ge=0, le=1)

    quality_ok: bool = True
    stale_days: int = Field(ge=0)
    source_provider: str = Field(min_length=1, max_length=32)
    reasons: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_temporal_contract(self) -> "PredictionHistoryCreate":
        if self.generated_at.tzinfo is None or self.generated_at.utcoffset() is None:
            raise ValueError("generated_at must be timezone-aware")
        if self.data_as_of > self.prediction_date:
            raise ValueError("data_as_of cannot be after prediction_date")
        return self

    @field_validator(
        "model_family",
        "model_version",
        "feature_representation",
        "source_provider",
        mode="before",
    )
    @classmethod
    def strip_text(cls, value):
        if value is None:
            return value
        return str(value).strip()

    @field_validator("reasons")
    @classmethod
    def validate_reasons(cls, value: list[str]) -> list[str]:
        return [str(reason).strip() for reason in value if str(reason).strip()]
