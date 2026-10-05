from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from app.models.prediction_history import PredictionHistory
from app.schemas.prediction_history import PredictionHistoryCreate


ASSET_ID = uuid4()
GENERATED_AT = datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc)


def valid_payload() -> PredictionHistoryCreate:
    return PredictionHistoryCreate(
        asset_id=ASSET_ID,
        prediction_date=date(2026, 10, 5),
        generated_at=GENERATED_AT,
        data_as_of=date(2026, 10, 5),
        horizon_days=5,
        target_return_threshold=Decimal("0.03"),
        model_family="xgboost",
        model_version="smoke-v1",
        feature_representation="raw_all",
        ml_probability=Decimal("0.62"),
        technical_score=Decimal("71.5"),
        risk_score=Decimal("24.0"),
        risk_adjustment=Decimal("-4.8"),
        signal_score=Decimal("61.7"),
        target_weight=Decimal("0.617"),
        quality_ok=True,
        stale_days=0,
        source_provider="borsapy",
        reasons=["Trend olumlu", "Risk cezası uygulandı"],
    )


def test_prediction_history_accepts_production_compatible_payload() -> None:
    payload = valid_payload()

    assert payload.horizon_days == 5
    assert payload.target_return_threshold == Decimal("0.03")
    assert payload.feature_representation == "raw_all"
    assert payload.target_weight == Decimal("0.617")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("ml_probability", Decimal("1.01")),
        ("technical_score", Decimal("100.01")),
        ("risk_score", Decimal("-0.01")),
        ("risk_adjustment", Decimal("0.01")),
        ("signal_score", Decimal("100.01")),
        ("target_weight", Decimal("1.01")),
        ("stale_days", -1),
    ],
)
def test_prediction_history_rejects_out_of_range_values(field: str, value) -> None:
    values = valid_payload().model_dump()
    values[field] = value

    with pytest.raises(ValueError):
        PredictionHistoryCreate(**values)


def test_prediction_history_model_is_append_only() -> None:
    columns = {column.name for column in PredictionHistory.__table__.columns}

    assert "created_at" in columns
    assert "updated_at" not in columns
    assert "signal_score" in columns
    assert "target_weight" in columns


def test_prediction_history_indexes_support_asset_and_time_queries() -> None:
    index_names = {index.name for index in PredictionHistory.__table__.indexes}

    assert "ix_prediction_history_asset_prediction_date" in index_names
    assert "ix_prediction_history_prediction_date" in index_names
    assert "ix_prediction_history_generated_at" in index_names
