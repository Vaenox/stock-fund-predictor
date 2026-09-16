from __future__ import annotations

import numpy as np
import pandas as pd

from app.analysis.indicators import calculate_fund_indicators, calculate_stock_indicators


def _stock_frame(rows: int = 220) -> pd.DataFrame:
    dates = pd.date_range("2026-01-01", periods=rows, freq="D")
    close = pd.Series(np.linspace(100, 140, rows), dtype=float)
    return pd.DataFrame(
        {
            "trading_date": dates,
            "open": close - 1,
            "high": close + 2,
            "low": close - 2,
            "close": close,
            "volume": np.linspace(1_000, 5_000, rows),
        }
    )


def _fund_frame(rows: int = 220) -> pd.DataFrame:
    dates = pd.date_range("2026-01-01", periods=rows, freq="D")
    price = pd.Series(np.linspace(10, 14, rows), dtype=float)
    return pd.DataFrame({"pricing_date": dates, "unit_price": price})


def test_stock_indicators_are_chronological_and_have_expected_columns():
    source = _stock_frame()
    reversed_source = source.iloc[::-1].reset_index(drop=True)
    result = calculate_stock_indicators(reversed_source)

    assert result["trading_date"].is_monotonic_increasing
    expected = {
        "sma_20", "sma_50", "sma_200", "ema_20", "ema_50", "ema_200",
        "rsi_14", "macd", "macd_signal", "macd_hist", "bb_upper", "bb_lower",
        "bb_width", "bb_position", "atr_14", "atr_pct_14", "adx_14",
        "momentum_5", "momentum_10", "momentum_20", "return_1d", "return_5d",
        "volatility_20", "volume_sma_20", "volume_ratio_20", "volume_change_1d",
    }
    assert expected.issubset(result.columns)


def test_stock_indicator_warmup_is_nan_and_mature_values_are_finite():
    result = calculate_stock_indicators(_stock_frame())

    assert pd.isna(result.loc[0, "sma_20"])
    expected_sma20 = result["close"].iloc[:20].mean()
    assert result.loc[19, "sma_20"] == expected_sma20
    assert result.loc[199, "sma_200"] == result["close"].iloc[:200].mean()
    assert np.isfinite(result.loc[219, "rsi_14"])
    assert np.isfinite(result.loc[219, "atr_14"])


def test_stock_rsi_is_near_100_for_strictly_rising_series():
    result = calculate_stock_indicators(_stock_frame())
    assert result.loc[219, "rsi_14"] > 99


def test_fund_indicators_support_unit_price_only_data():
    result = calculate_fund_indicators(_fund_frame())

    assert result["pricing_date"].is_monotonic_increasing
    assert "rsi_14" in result.columns
    assert "macd_hist" in result.columns
    assert "bb_upper" in result.columns
    assert "momentum_20" in result.columns
    assert "atr_14" not in result.columns


def test_indicator_calculation_does_not_use_future_rows():
    full = _stock_frame(220)
    truncated = full.iloc[:150].copy()
    full_result = calculate_stock_indicators(full)
    truncated_result = calculate_stock_indicators(truncated)

    feature_columns = ["sma_20", "ema_20", "rsi_14", "macd", "bb_upper", "momentum_20"]
    for column in feature_columns:
        np.testing.assert_allclose(
            full_result.loc[100, column],
            truncated_result.loc[100, column],
            equal_nan=True,
        )
