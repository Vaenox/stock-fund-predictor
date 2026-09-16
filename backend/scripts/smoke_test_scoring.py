from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta

import pandas as pd

from app.analysis.indicators import calculate_fund_indicators, calculate_stock_indicators
from app.analysis.scoring import calculate_fund_technical_score, calculate_stock_technical_score
from app.data.providers.borsapy import BorsapyProvider
from app.data.providers.tefas import TefasProvider


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run real-provider technical score smoke tests.")
    target = parser.add_mutually_exclusive_group()
    target.add_argument("--symbol", help="BIST stock symbol")
    target.add_argument("--fund-code", help="TEFAS fund code")
    parser.add_argument("--days", type=int, default=450, help="Calendar-day history window")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.days < 250:
        print("ERROR: use at least 250 calendar days for EMA200 warm-up", file=sys.stderr)
        return 2

    end = date.today()
    start = end - timedelta(days=args.days)

    try:
        if args.fund_code:
            code = args.fund_code.strip().upper()
            records = TefasProvider().get_fund_history(code, start, end)
            frame = pd.DataFrame(
                [{"pricing_date": r.pricing_date, "unit_price": r.unit_price} for r in records]
            )
            if len(frame) < 200:
                raise RuntimeError(f"insufficient TEFAS rows: {len(frame)}")
            result = calculate_fund_technical_score(calculate_fund_indicators(frame))
            print(f"Fund code: {code}")
        else:
            symbol = (args.symbol or "THYAO").strip().upper()
            records = BorsapyProvider().get_daily_history(symbol, start, end)
            frame = pd.DataFrame(
                [
                    {
                        "trading_date": r.trading_date,
                        "open": r.open,
                        "high": r.high,
                        "low": r.low,
                        "close": r.close,
                        "volume": r.volume,
                    }
                    for r in records
                ]
            )
            if len(frame) < 200:
                raise RuntimeError(f"insufficient BIST rows: {len(frame)}")
            result = calculate_stock_technical_score(calculate_stock_indicators(frame))
            print(f"Symbol: {symbol}")

        latest = result.iloc[-1]
        print(f"Rows: {len(frame)}")
        print(f"Technical score: {latest['technical_score']:.4f}")
        print(f"Trend: {latest['technical_score_trend']:.4f}")
        print(f"Momentum: {latest['technical_score_momentum']:.4f}")
        print(f"Volatility: {latest['technical_score_volatility']:.4f}")
        print(f"Reason: {latest['technical_score_reason']}")
        if not 0 <= float(latest["technical_score"]) <= 100:
            raise AssertionError("technical score is outside 0-100")

        print("TECHNICAL SCORE SMOKE TEST PASSED")
        return 0
    except Exception as exc:
        print(f"TECHNICAL SCORE SMOKE TEST FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
