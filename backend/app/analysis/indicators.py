from __future__ import annotations

import numpy as np
import pandas as pd


STOCK_REQUIRED_COLUMNS = ("trading_date", "open", "high", "low", "close")
FUND_REQUIRED_COLUMNS = ("pricing_date", "unit_price")


def _require_columns(frame: pd.DataFrame, required: tuple[str, ...]) -> None:
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"missing required columns: {', '.join(missing)}")


def _rsi(close: pd.Series, period: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    result = 100 - (100 / (1 + rs))
    result = result.where(avg_loss.ne(0), 100.0)
    return result


def _atr(frame: pd.DataFrame, period: int) -> pd.Series:
    previous_close = frame["close"].shift(1)
    true_range = pd.concat(
        [
            frame["high"] - frame["low"],
            (frame["high"] - previous_close).abs(),
            (frame["low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return true_range.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()


def _adx(frame: pd.DataFrame, period: int) -> pd.Series:
    up_move = frame["high"].diff()
    down_move = -frame["low"].diff()
    plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0.0)

    previous_close = frame["close"].shift(1)
    true_range = pd.concat(
        [
            frame["high"] - frame["low"],
            (frame["high"] - previous_close).abs(),
            (frame["low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    atr = true_range.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1 / period, adjust=False, min_periods=period).mean() / atr
    minus_di = 100 * minus_dm.ewm(alpha=1 / period, adjust=False, min_periods=period).mean() / atr
    denominator = (plus_di + minus_di).replace(0, np.nan)
    dx = 100 * (plus_di - minus_di).abs() / denominator
    return dx.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()


def _add_price_indicators(frame: pd.DataFrame, price_column: str = "close") -> pd.DataFrame:
    result = frame.copy()
    close = result[price_column].astype(float)

    result["sma_20"] = close.rolling(20, min_periods=20).mean()
    result["sma_50"] = close.rolling(50, min_periods=50).mean()
    result["sma_200"] = close.rolling(200, min_periods=200).mean()
    result["ema_20"] = close.ewm(span=20, adjust=False, min_periods=20).mean()
    result["ema_50"] = close.ewm(span=50, adjust=False, min_periods=50).mean()
    result["ema_200"] = close.ewm(span=200, adjust=False, min_periods=200).mean()

    result["rsi_14"] = _rsi(close, 14)

    ema_12 = close.ewm(span=12, adjust=False, min_periods=12).mean()
    ema_26 = close.ewm(span=26, adjust=False, min_periods=26).mean()
    result["macd"] = ema_12 - ema_26
    result["macd_signal"] = result["macd"].ewm(span=9, adjust=False, min_periods=9).mean()
    result["macd_hist"] = result["macd"] - result["macd_signal"]

    bb_mid = close.rolling(20, min_periods=20).mean()
    bb_std = close.rolling(20, min_periods=20).std(ddof=0)
    result["bb_mid"] = bb_mid
    result["bb_upper"] = bb_mid + (2 * bb_std)
    result["bb_lower"] = bb_mid - (2 * bb_std)
    result["bb_width"] = (result["bb_upper"] - result["bb_lower"]) / bb_mid.replace(0, np.nan)
    result["bb_position"] = (close - result["bb_lower"]) / (
        result["bb_upper"] - result["bb_lower"]
    ).replace(0, np.nan)

    result["momentum_5"] = close.pct_change(5)
    result["momentum_10"] = close.pct_change(10)
    result["momentum_20"] = close.pct_change(20)
    result["return_1d"] = close.pct_change(1)
    result["return_5d"] = close.pct_change(5)
    result["volatility_20"] = result["return_1d"].rolling(20, min_periods=20).std() * np.sqrt(252)

    return result


def calculate_stock_indicators(frame: pd.DataFrame) -> pd.DataFrame:
    """Calculate canonical technical indicators for stock OHLCV data.

    Input rows are sorted chronologically before calculation. Every feature uses
    only current/past rows, so no future observations are referenced.
    """
    _require_columns(frame, STOCK_REQUIRED_COLUMNS)
    result = frame.sort_values("trading_date").reset_index(drop=True).copy()
    for column in ("open", "high", "low", "close"):
        result[column] = pd.to_numeric(result[column], errors="raise")

    result = _add_price_indicators(result)
    result["atr_14"] = _atr(result, 14)
    result["atr_pct_14"] = result["atr_14"] / result["close"].replace(0, np.nan)
    result["adx_14"] = _adx(result, 14)

    if "volume" in result.columns:
        volume = pd.to_numeric(result["volume"], errors="coerce")
        result["volume_sma_20"] = volume.rolling(20, min_periods=20).mean()
        result["volume_ratio_20"] = volume / result["volume_sma_20"].replace(0, np.nan)
        result["volume_change_1d"] = volume.pct_change()

    return result


def calculate_fund_indicators(frame: pd.DataFrame) -> pd.DataFrame:
    """Calculate indicators supported by daily fund unit-price data."""
    _require_columns(frame, FUND_REQUIRED_COLUMNS)
    result = frame.sort_values("pricing_date").reset_index(drop=True).copy()
    result["unit_price"] = pd.to_numeric(result["unit_price"], errors="raise")
    result = _add_price_indicators(result, price_column="unit_price")
    return result
