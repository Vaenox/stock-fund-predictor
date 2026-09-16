from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta

import pandas as pd

from app.analysis.indicators import calculate_fund_indicators, calculate_stock_indicators
from app.data.providers.borsapy import BorsapyProvider
from app.data.providers.tefas import TefasProvider


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run real-provider technical indicator smoke tests.")
    target = parser.add_mutually_exclusive_group()
    target.add_argument("--symbol", help="BIST stock symbol")
    target.add_argument("--fund-code", help="TEFAS fund code")
    target.add_argument("--active-fund", action="store_true", help="Auto-select a current TEFAS fund")
    parser.add_argument("--days", type=int, default=450, help="Calendar-day history window")
    return parser.parse_args()


def _stock_frame(provider: BorsapyProvider, symbol: str, start: date, end: date) -> pd.DataFrame:
    records = provider.get_daily_history(symbol, start, end)
    return pd.DataFrame(
        [
            {
                "trading_date": record.trading_date,
                "open": record.open,
                "high": record.high,
                "low": record.low,
                "close": record.close,
                "volume": record.volume,
            }
            for record in records
        ]
    )


def _fund_frame(provider: TefasProvider, fund_code: str, start: date, end: date) -> pd.DataFrame:
    records = provider.get_fund_history(fund_code, start, end)
    return pd.DataFrame(
        [{"pricing_date": record.pricing_date, "unit_price": record.unit_price} for record in records]
    )


def _assert_no_lookahead(full: pd.DataFrame, truncated: pd.DataFrame, feature_columns: list[str]) -> None:
    full_features = feature_columns
    full_result = calculate_stock_indicators(full) if "trading_date" in full.columns else calculate_fund_indicators(full)
    truncated_result = calculate_stock_indicators(truncated) if "trading_date" in truncated.columns else calculate_fund_indicators(truncated)
    probe = min(100, len(truncated_result) - 1)
    for column in full_features:
        a = full_result.loc[probe, column]
        b = truncated_result.loc[probe, column]
        if pd.isna(a) and pd.isna(b):
            continue
        if pd.isna(a) or pd.isna(b) or abs(float(a) - float(b)) > 1e-12:
            raise AssertionError(f"look-ahead detected for {column} at index {probe}: {a} != {b}")


def main() -> int:
    args = parse_args()
    if args.days < 250:
        print("ERROR: use at least 250 calendar days so long warm-up indicators can mature", file=sys.stderr)
        return 2

    end = date.today()
    start = end - timedelta(days=args.days)

    try:
        if args.symbol or not (args.fund_code or args.active_fund):
            symbol = (args.symbol or "THYAO").strip().upper()
            frame = _stock_frame(BorsapyProvider(), symbol, start, end)
            if len(frame) < 200:
                raise RuntimeError(f"insufficient BIST rows for 200-day warm-up: {len(frame)}")
            result = calculate_stock_indicators(frame)
            print(f"Symbol: {symbol}")
            print(f"Rows: {len(frame)}")
            print(f"Date window: {frame['trading_date'].min()}->{frame['trading_date'].max()}")
            print(f"RSI14 latest: {result['rsi_14'].iloc[-1]:.6f}")
            print(f"EMA20 latest: {result['ema_20'].iloc[-1]:.6f}")
            print(f"EMA200 latest: {result['ema_200'].iloc[-1]:.6f}")
            print(f"MACD hist latest: {result['macd_hist'].iloc[-1]:.6f}")
            print(f"ATR14 latest: {result['atr_14'].iloc[-1]:.6f}")
            print(f"ADX14 latest: {result['adx_14'].iloc[-1]:.6f}")
            print(f"Volume ratio20 latest: {result['volume_ratio_20'].iloc[-1]:.6f}")
            _assert_no_lookahead(frame, frame.iloc[: max(101, len(frame) - 20)], ["sma_20", "ema_20", "rsi_14", "macd", "bb_upper", "momentum_20"])
            print("LOOK-AHEAD CHECK: PASSED")
        else:
            provider = TefasProvider()
            if args.active_fund:
                symbols = provider.list_symbols()
                if not symbols:
                    raise RuntimeError("TEFAS returned no current funds")
                fund_code = symbols[0].provider_symbol
            else:
                fund_code = args.fund_code.strip().upper()
            frame = _fund_frame(provider, fund_code, start, end)
            if len(frame) < 200:
                raise RuntimeError(f"insufficient TEFAS rows for 200-day warm-up: {len(frame)}")
            result = calculate_fund_indicators(frame)
            print(f"Fund code: {fund_code}")
            print(f"Rows: {len(frame)}")
            print(f"Date window: {frame['pricing_date'].min()}->{frame['pricing_date'].max()}")
            print(f"RSI14 latest: {result['rsi_14'].iloc[-1]:.6f}")
            print(f"EMA20 latest: {result['ema_20'].iloc[-1]:.6f}")
            print(f"EMA200 latest: {result['ema_200'].iloc[-1]:.6f}")
            print(f"MACD hist latest: {result['macd_hist'].iloc[-1]:.6f}")
            _assert_no_lookahead(frame, frame.iloc[: max(101, len(frame) - 20)], ["sma_20", "ema_20", "rsi_14", "macd", "bb_upper", "momentum_20"])
            print("LOOK-AHEAD CHECK: PASSED")

        print("TECHNICAL INDICATOR SMOKE TEST PASSED")
        return 0
    except Exception as exc:
        print(f"TECHNICAL INDICATOR SMOKE TEST FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
