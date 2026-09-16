from __future__ import annotations

import argparse
import sys
import time
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
    parser.add_argument(
        "--tefas-request-interval",
        type=float,
        default=10.0,
        help="Seconds between TEFAS requests when manually chunking a fund history",
    )
    return parser.parse_args()


def _fund_frame(
    provider: TefasProvider,
    fund_code: str,
    start: date,
    end: date,
    *,
    request_interval: float,
) -> pd.DataFrame:
    chunk_size = 28
    records = []
    current = start
    first_request = True

    while current <= end:
        chunk_end = min(current + timedelta(days=chunk_size - 1), end)
        if not first_request and request_interval > 0:
            time.sleep(request_interval)
        chunk_records = provider.get_fund_history(fund_code, current, chunk_end)
        records.extend(chunk_records)
        print(f"TEFAS chunk: {current}->{chunk_end} rows={len(chunk_records)}")
        first_request = False
        current = chunk_end + timedelta(days=1)

    return pd.DataFrame(
        [{"pricing_date": record.pricing_date, "unit_price": record.unit_price} for record in records]
    ).drop_duplicates(subset=["pricing_date"], keep="last")


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
            frame = _fund_frame(
                TefasProvider(),
                code,
                start,
                end,
                request_interval=args.tefas_request_interval,
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
