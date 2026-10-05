from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

import numpy as np
import pandas as pd
import pytest

from app.schemas.prediction_history import PredictionHistoryCreate
from app.services.prediction import generate_latest_prediction


def sample_stock_frame() -> pd.DataFrame:
    dates = pd.date_range("2024-01-01", periods=320, freq="D")
    block = np.tile(
        np.array([0.008] * 15 + [-0.006] * 15, dtype=float),
        11,
    )[: len(dates)]
    close = 100.0 * np.cumprod(1.0 + block)
    return pd.DataFrame(
        {
            "trading_date": dates,
            "open": close * 0.998,
            "high": close * 1.010,
            "low": close * 0.990,
            "close": close,
            "volume": 1_000_000.0,
        }
    )


def test_generate_latest_prediction_uses_production_contract() -> None:
    result = generate_latest_prediction(
        asset_id=uuid4(),
        asset_type="stock",
        raw_frame=sample_stock_frame(),
        source_provider="borsapy",
        generated_at=datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc),
    )

    payload = result.payload

    assert payload.horizon_days == 5
    assert payload.target_return_threshold == Decimal("0.03")
    assert payload.feature_representation == "raw_all"
    assert payload.model_family == "xgboost"
    assert payload.source_provider == "borsapy"
    assert 0 <= payload.ml_probability <= 1
    assert 0 <= payload.technical_score <= 100
    assert 0 <= payload.risk_score <= 100
    assert -20 <= payload.risk_adjustment <= 0
    assert 0 <= payload.signal_score <= 100
    assert 0 <= payload.target_weight <= 1


def test_generate_latest_prediction_rejects_naive_generation_timestamp() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        generate_latest_prediction(
            asset_id=uuid4(),
            asset_type="stock",
            raw_frame=sample_stock_frame(),
            source_provider="borsapy",
            generated_at=datetime(2026, 10, 5, 12, 0),
        )
