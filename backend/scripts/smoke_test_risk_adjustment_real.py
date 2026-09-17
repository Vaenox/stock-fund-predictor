from __future__ import annotations

import argparse
from datetime import date, timedelta

import pandas as pd

from app.analysis.indicators import calculate_fund_indicators, calculate_stock_indicators
from app.data.providers.borsapy import BorsapyProvider
from app.data.providers.tefas import TefasProvider
from app.ml.risk_adjustment import calculate_fund_risk_adjustment, calculate_stock_risk_adjustment


def _stock_frame(symbol: str, days: int) -> pd.DataFrame:
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    records = BorsapyProvider().get_daily_history(symbol, start_date, end_date)
    return pd.DataFrame(
        {
            "trading_date": [r.trading_date for r in records],
            "open": [float(r.open) for r in records],
            "high": [float(r.high) for r in records],
            "low": [float(r.low) for r in records],
            "close": [float(r.close) for r in records],
            "volume": [float(r.volume) if r.volume is not None else float("nan") for r in records],
        }
    )


def _fund_frame(code: str, days: int) -> pd.DataFrame:
    provider = TefasProvider()
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    records: list = []
    for chunk_start, chunk_end in provider._chunks(start_date, end_date, provider._settings.max_days_per_request):
        records.extend(provider.get_fund_history(code, chunk_start, chunk_end))
    return (
        pd.DataFrame(
            {
                "pricing_date": [r.pricing_date for r in records],
                "unit_price": [float(r.unit_price) for r in records],
            }
        )
        .drop_duplicates(subset=["pricing_date"])
        .sort_values("pricing_date")
        .reset_index(drop=True)
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--asset-type", choices=("stock", "fund"), required=True)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--days", type=int, default=1000)
    args = parser.parse_args()

    if args.days < 260:
        raise SystemExit("days must be at least 260")

    if args.asset_type == "stock":
        raw = _stock_frame(args.symbol.strip().upper(), args.days)
        indicators = calculate_stock_indicators(raw)
        row = indicators.iloc[-1]
        result = calculate_stock_risk_adjustment(row)
        latest_date = row["trading_date"]
    else:
        raw = _fund_frame(args.symbol.strip().upper(), args.days)
        indicators = calculate_fund_indicators(raw)
        row = indicators.iloc[-1]
        result = calculate_fund_risk_adjustment(row)
        latest_date = row["pricing_date"]

    print(f"Asset type: {args.asset_type}")
    print(f"Symbol: {args.symbol.strip().upper()}")
    print(f"Raw rows: {len(raw)}")
    print(f"Latest date: {latest_date}")
    print(f"Risk score: {result.risk_score:.6f}")
    print(f"Adjustment: {result.adjustment:.6f}")
    print(f"Volatility risk: {result.volatility_risk:.6f}")
    print(f"Trend weakness risk: {result.trend_weakness_risk:.6f}")
    print(f"Liquidity risk: {result.liquidity_risk:.6f}")
    print(f"Data quality/stale risk: {result.data_quality_risk:.6f}")
    print("Reasons:")
    for reason in result.reasons:
        print(f"  - {reason}")
    print("REAL RISK ADJUSTMENT SMOKE TEST PASSED")


if __name__ == "__main__":
    main()
