from __future__ import annotations

import pandas as pd
import pytest

from app.ml.risk_adjustment import (
    RiskAdjustmentConfig,
    calculate_fund_risk_adjustment,
    calculate_stock_risk_adjustment,
)


def test_healthy_stock_has_zero_risk_penalty() -> None:
    row = pd.Series(
        {
            "close": 110.0,
            "ema_20": 105.0,
            "ema_50": 100.0,
            "ema_200": 90.0,
            "volatility_20": 0.20,
            "volume_ratio_20": 1.00,
        }
    )

    result = calculate_stock_risk_adjustment(row)

    assert result.risk_score == pytest.approx(0.0)
    assert result.adjustment == pytest.approx(0.0)
    assert result.trend_weakness_risk == pytest.approx(0.0)
    assert result.volatility_risk == pytest.approx(0.0)
    assert result.liquidity_risk == pytest.approx(0.0)
    assert result.data_quality_risk == pytest.approx(0.0)


def test_max_risk_reaches_configured_penalty() -> None:
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

    result = calculate_stock_risk_adjustment(
        row,
        quality_ok=False,
        stale_days=3,
    )

    assert result.risk_score == pytest.approx(100.0)
    assert result.adjustment == pytest.approx(-20.0)
    assert result.data_quality_risk == pytest.approx(100.0)
    assert all(value == pytest.approx(100.0) for value in (
        result.volatility_risk,
        result.trend_weakness_risk,
        result.liquidity_risk,
    ))


def test_stale_data_increases_penalty_deterministically() -> None:
    row = pd.Series(
        {
            "close": 105.0,
            "ema_20": 100.0,
            "ema_50": 100.0,
            "ema_200": 100.0,
            "volatility_20": 0.20,
            "volume_ratio_20": 1.00,
        }
    )

    fresh = calculate_stock_risk_adjustment(row, stale_days=0)
    stale = calculate_stock_risk_adjustment(row, stale_days=2)

    assert stale.data_quality_risk > fresh.data_quality_risk
    assert stale.risk_score > fresh.risk_score
    assert stale.adjustment < fresh.adjustment


def test_fund_does_not_use_stock_liquidity() -> None:
    base = {
        "unit_price": 10.0,
        "ema_20": 10.0,
        "ema_50": 10.0,
        "ema_200": 10.0,
        "volatility_20": 0.20,
    }
    low_volume_row = pd.Series({**base, "volume_ratio_20": 0.01})
    high_volume_row = pd.Series({**base, "volume_ratio_20": 10.0})

    low = calculate_fund_risk_adjustment(low_volume_row)
    high = calculate_fund_risk_adjustment(high_volume_row)

    assert low.liquidity_risk == pytest.approx(0.0)
    assert high.liquidity_risk == pytest.approx(0.0)
    assert low.risk_score == pytest.approx(high.risk_score)
    assert low.adjustment == pytest.approx(high.adjustment)


def test_missing_features_are_neutral_and_quality_can_still_raise_risk() -> None:
    row = pd.Series({"volatility_20": None})

    result = calculate_stock_risk_adjustment(row, quality_ok=True, stale_days=0)

    assert result.volatility_risk == pytest.approx(50.0)
    assert result.trend_weakness_risk == pytest.approx(50.0)
    assert result.liquidity_risk == pytest.approx(50.0)
    assert result.data_quality_risk == pytest.approx(0.0)


def test_invalid_config_is_rejected() -> None:
    with pytest.raises(ValueError, match="risk weights must sum to 1.0"):
        RiskAdjustmentConfig(liquidity_weight=0.20)
