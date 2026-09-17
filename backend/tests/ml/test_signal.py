from __future__ import annotations

import pytest

from app.ml.signal import SignalScoreConfig, calculate_signal_score


def test_signal_combines_ml_and_technical_and_applies_risk_penalty() -> None:
    result = calculate_signal_score(
        0.80,
        70.0,
        -10.0,
    )

    assert result.signal_score == pytest.approx(51.0)
    assert result.ml_probability == pytest.approx(0.80)
    assert result.technical_score == pytest.approx(70.0)
    assert result.risk_adjustment == pytest.approx(-10.0)


def test_signal_zero_risk_is_unaffected_by_penalty() -> None:
    result = calculate_signal_score(0.60, 40.0, 0.0)
    assert result.signal_score == pytest.approx(42.0)


def test_signal_is_clipped_to_zero() -> None:
    result = calculate_signal_score(0.10, 10.0, -20.0)
    assert result.signal_score == pytest.approx(0.0)


def test_signal_is_clipped_to_hundred() -> None:
    result = calculate_signal_score(1.0, 100.0, 0.0)
    assert result.signal_score == pytest.approx(80.0)


def test_positive_risk_adjustment_is_rejected() -> None:
    with pytest.raises(ValueError, match="risk_adjustment must be non-positive"):
        calculate_signal_score(0.8, 70.0, 1.0)


def test_invalid_probability_is_rejected() -> None:
    with pytest.raises(ValueError, match="ml_probability must be between 0 and 1"):
        calculate_signal_score(1.2, 70.0, 0.0)


def test_signal_config_weights_must_sum_to_one() -> None:
    with pytest.raises(ValueError, match="signal weights must sum to 1.0"):
        SignalScoreConfig(ml_weight=0.6, technical_weight=0.3, risk_weight=0.3)
