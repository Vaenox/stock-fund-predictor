from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta

from sqlalchemy import create_engine, text

from app.core.settings import get_settings
from app.data.quality import inspect_stock_bars


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run real PostgreSQL market-data quality checks.")
    parser.add_argument("--symbol", default="THYAO")
    parser.add_argument("--days", type=int, default=30)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    symbol = args.symbol.strip().upper()
    if not symbol or args.days < 1:
        print("ERROR: invalid test configuration", file=sys.stderr)
        return 2

    engine = create_engine(get_settings().database_url, future=True)
    end_date = date.today()
    start_date = end_date - timedelta(days=args.days)

    with engine.connect() as conn:
        asset_id = conn.execute(
            text("SELECT id FROM assets WHERE canonical_symbol = :symbol"),
            {"symbol": symbol},
        ).scalar_one_or_none()
        if asset_id is None:
            print(f"ERROR: asset not found: {symbol}", file=sys.stderr)
            return 1

        rows = conn.execute(
            text(
                """
                SELECT trading_date, open, high, low, close, volume, source_provider
                FROM stock_daily_bars
                WHERE asset_id = :asset_id
                  AND trading_date BETWEEN :start_date AND :end_date
                ORDER BY trading_date
                """
            ),
            {"asset_id": asset_id, "start_date": start_date, "end_date": end_date},
        ).mappings().all()

        duplicate_count = conn.execute(
            text(
                """
                SELECT COUNT(*)
                FROM (
                    SELECT asset_id, trading_date
                    FROM stock_daily_bars
                    WHERE asset_id = :asset_id
                      AND trading_date BETWEEN :start_date AND :end_date
                    GROUP BY asset_id, trading_date
                    HAVING COUNT(*) > 1
                ) duplicates
                """
            ),
            {"asset_id": asset_id, "start_date": start_date, "end_date": end_date},
        ).scalar_one()

    report = inspect_stock_bars(rows)

    print(f"Symbol: {symbol}")
    print(f"Window: {start_date.isoformat()}->{end_date.isoformat()}")
    print(f"Rows inspected: {len(rows)}")
    print(f"Duplicate keys: {len(report.duplicate_keys)}")
    print(f"Invalid OHLC rows: {len(report.invalid_ohlc)}")
    print(f"Negative volume rows: {len(report.negative_volume)}")
    print(f"Extreme return rows (>30%): {len(report.extreme_return_dates)}")
    print(f"Mixed sources: {report.mixed_sources or 'none'}")
    print(f"SQL duplicate groups: {duplicate_count}")

    if not rows:
        print("QUALITY SMOKE FAILED: no historical rows found", file=sys.stderr)
        return 1
    if duplicate_count or not report.ok:
        print("QUALITY SMOKE FAILED: quality violations detected", file=sys.stderr)
        return 1

    print("MARKET DATA QUALITY SMOKE TEST PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
