from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, UUIDPrimaryKeyMixin


class PredictionHistory(UUIDPrimaryKeyMixin, Base):
    """Append-only audit record for one generated prediction/signal."""

    __tablename__ = "prediction_history"

    asset_id: Mapped[UUID] = mapped_column(
        ForeignKey("assets.id", ondelete="CASCADE"),
        nullable=False,
    )
    prediction_date: Mapped[date] = mapped_column(Date, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    data_as_of: Mapped[date] = mapped_column(Date, nullable=False)

    horizon_days: Mapped[int] = mapped_column(Integer, nullable=False)
    target_return_threshold: Mapped[Decimal] = mapped_column(
        Numeric(10, 8),
        nullable=False,
    )
    model_family: Mapped[str] = mapped_column(String(64), nullable=False)
    model_version: Mapped[str | None] = mapped_column(String(128))
    feature_representation: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    ml_probability: Mapped[Decimal] = mapped_column(
        Numeric(12, 10),
        nullable=False,
    )
    technical_score: Mapped[Decimal] = mapped_column(
        Numeric(8, 4),
        nullable=False,
    )
    risk_score: Mapped[Decimal] = mapped_column(
        Numeric(8, 4),
        nullable=False,
    )
    risk_adjustment: Mapped[Decimal] = mapped_column(
        Numeric(8, 4),
        nullable=False,
    )
    signal_score: Mapped[Decimal] = mapped_column(
        Numeric(8, 4),
        nullable=False,
    )
    target_weight: Mapped[Decimal] = mapped_column(
        Numeric(12, 10),
        nullable=False,
    )

    quality_ok: Mapped[bool] = mapped_column(Boolean, nullable=False)
    stale_days: Mapped[int] = mapped_column(Integer, nullable=False)
    source_provider: Mapped[str] = mapped_column(String(32), nullable=False)
    reasons: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        CheckConstraint("horizon_days > 0", name="ck_prediction_history_horizon_positive"),
        CheckConstraint(
            "target_return_threshold BETWEEN -1 AND 1",
            name="ck_prediction_history_threshold_range",
        ),
        CheckConstraint(
            "ml_probability BETWEEN 0 AND 1",
            name="ck_prediction_history_probability_range",
        ),
        CheckConstraint(
            "technical_score BETWEEN 0 AND 100",
            name="ck_prediction_history_technical_score_range",
        ),
        CheckConstraint(
            "risk_score BETWEEN 0 AND 100",
            name="ck_prediction_history_risk_score_range",
        ),
        CheckConstraint(
            "risk_adjustment BETWEEN -100 AND 0",
            name="ck_prediction_history_risk_adjustment_range",
        ),
        CheckConstraint(
            "signal_score BETWEEN 0 AND 100",
            name="ck_prediction_history_signal_score_range",
        ),
        CheckConstraint(
            "target_weight BETWEEN 0 AND 1",
            name="ck_prediction_history_target_weight_range",
        ),
        CheckConstraint(
            "stale_days >= 0",
            name="ck_prediction_history_stale_days_nonnegative",
        ),
        CheckConstraint(
            "data_as_of <= prediction_date",
            name="ck_prediction_history_data_as_of_not_future",
        ),
        Index(
            "ix_prediction_history_asset_prediction_date",
            "asset_id",
            "prediction_date",
        ),
        Index(
            "ix_prediction_history_prediction_date",
            "prediction_date",
        ),
        Index(
            "ix_prediction_history_generated_at",
            "generated_at",
        ),
    )
