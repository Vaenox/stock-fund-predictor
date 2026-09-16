from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.analysis.indicators import calculate_fund_indicators, calculate_stock_indicators
from app.analysis.scoring import (
    TechnicalScoreConfig,
    calculate_fund_technical_score,
    calculate_stock_technical_score,
)


def _stock_frame(rows: int = 220, slope: float = 0.2) -> pd.DataFrame:
    dates = pd.date_range("2026-01-01", periods=rows, freq="D")
    close = pd.Series(100 + np.arange(rows) * slope, dtype=float)
    return pd.DataFrame(
        {
            "trading_date": dates,
            "open": close - 1,
            "high": close + 2,
            "low": close - 2,
            "close": close,
            "volume": np.full(rows, 10_000.0),
        }
    )


def _fund_frame(rows: int = 220) -> pd.DataFrame:
    dates = pd.date_range("2026-01-01", periods=rows, freq="D")
    unit_price = pd.Series(10 + np.arange(rows) * 0.02, dtype=float)
    return pd.DataFrame({"pricing_date": dates, "unit_price": unit_price})


def test_stock_score_is_bounded_and_explainable():
    indicators = calculate_stock_indicators(_stock_frame())
    result = calculate_stock_technical_score(indicators)

    assert result["technical_score"].between(0, 100).all()
    assert result["technical_score_reason"].notna().all()
    assert result["technical_score_trend"].between(0, 100).all()
    assert result["technical_score_momentum"].between(0, 100).all()
    assert result["technical_score_volatility"].between(0, 100).all()


def test_stock_positive_trend_scores_above_neutral_after_warmup():
    indicators = calculate_stock_indicators(_stock_frame(slope=0.8))
    result = calculate_stock_technical_score(indicators)

    assert result.loc[219, "technical_score"] > 50
    assert result.loc[219, "technical_score_trend"] > 50
    assert result.loc[219, "technical_score_momentum"] > 50


def test_missing_stock_components_use_neutral_values():
    indicators = calculate_stock_indicators(_stock_frame()).iloc[[0]].copy()
    result = calculate_stock_technical_score(indicators)

    assert result.loc[0, "technical_score"] == pytest.approx(50.0)
    assert "nötr 50 puan" in result.loc[0, "technical_score_reason"]


def test_fund_score_uses_only_supported_components():
    indicators = calculate_fund_indicators(_fund_frame())
    result = calculate_fund_technical_score(indicators)

    assert result["technical_score"].between(0, 100).all()
    assert result["technical_score_volume"].isna().all()
    assert result["technical_score_breadth"].isna().all()
    assert result.loc[219, "technical_score"] > 50
    assert "Hacim: fon verisinde desteklenmiyor" in result.loc[219, "technical_score_reason"]


def test_fund_score_does_not_require_stock_only_columns():
    indicators = calculate_fund_indicators(_fund_frame())
    indicators = indicators.drop(columns=["bb_position"])
    result = calculate_fund_technical_score(indicators)

    assert result["technical_score"].between(0, 100).all()
    assert result["technical_score_volatility"].notna().any()


def test_config_requires_weights_to_sum_to_one():
    with pytest.raises(ValueError, match="sum to 1.0"):
        TechnicalScoreConfig(
            trend_weight=0.5,
            momentum_weight=0.5,
            volatility_weight=0.1,
            volume_weight=0.0,
            breadth_weight=0.0,
        )


def test_score_does_not_use_future_rows():
    full = calculate_stock_indicators(_stock_frame())
    truncated = full.iloc[:150].copy()
    full_scored = calculate_stock_technical_score(full)
    truncated_scored = calculate_stock_technical_score(truncated)

    for column in (
        "technical_score",
        "technical_score_trend",
        "technical_score_momentum",
        "technical_score_volatility",
    ):
        assert full_scored.loc[100, column] == pytest.approx(truncated_scored.loc[100, column])
