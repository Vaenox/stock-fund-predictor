from __future__ import annotations

import pandas as pd
import pytest

from app.ml.risk_adjustment import calculate_stock_risk_adjustment
from app.ml.signal import SignalScoreConfig, calculate_signal_score


def test_phase5_risk_signal_chain_is_deterministic() -> None:
    row = pd.Series(
        {
            "close": 95.0,
            "ema_20": 100.0,
            "ema_50": 105.0,
            "ema_200": 110.0,
            "volatility_20": 0.35,
            "volume_ratio_20": 0.75,
        }
    )

    risk_1 = calculate_stock_risk_adjustment(row, quality_ok=True, stale_days=0)
    risk_2 = calculate_stock_risk_adjustment(row, quality_ok=True, stale_days=0)
    signal_1 = calculate_signal_score(0.65, 58.0, risk_1.adjustment)
    signal_2 = calculate_signal_score(0.65, 58.0, risk_2.adjustment)

    assert risk_1 == risk_2
    assert signal_1 == signal_2
    assert signal_1.ml_probability == pytest.approx(0.65)
    assert signal_1.risk_adjustment == pytest.approx(risk_1.adjustment)
    assert 0.0 <= signal_1.signal_score <= 100.0


def test_phase5_risk_cannot_change_ml_probability() -> None:
    row = pd.Series(
        {
            "close": 80.0,
            "ema_20": 100.0,
            "ema_50": 110.0,
            "ema_200": 120.0,
            "volatility_20": 0.50,
            "volume_ratio_20": 0.50,
        }
    )
    risk = calculate_stock_risk_adjustment(row, quality_ok=False, stale_days=3)
    result = calculate_signal_score(0.72, 65.0, risk.adjustment)

    base_ceiling = (
        0.72 * 100.0 * SignalScoreConfig().ml_weight
        + 65.0 * SignalScoreConfig().technical_weight
    ) / (
        SignalScoreConfig().ml_weight + SignalScoreConfig().technical_weight
    )

    assert result.ml_probability == pytest.approx(0.72)
    assert result.risk_adjustment <= 0.0
    assert result.signal_score <= base_ceiling


def test_phase5_negative_risk_adjustment_only_lowers_score() -> None:
    no_risk = calculate_signal_score(0.70, 60.0, 0.0)
    risk = calculate_signal_score(0.70, 60.0, -10.0)

    assert risk.signal_score < no_risk.signal_score
    assert risk.signal_score == pytest.approx(no_risk.signal_score - 10.0)
