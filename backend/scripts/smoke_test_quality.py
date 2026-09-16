from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta

from sqlalchemy import create_engine, text

from app.core.settings import get_settings
from app.data.quality import inspect_fund_prices, inspect_stock_bars


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run real PostgreSQL market-data quality checks.")
    target = parser.add_mutually_exclusive_group()
    target.add_argument("--symbol", help="BIST stock symbol")
    target.add_argument("--fund-code", help="TEFAS fund code")
    parser.add_argument("--days", type=int, default=30)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    is_fund = args.fund_code is not None
    identifier = (args.fund_code if is_fund else (args.symbol or "THYAO")).strip().upper()
    if not identifier or args.days < 1:
        print("ERROR: invalid test configuration", file=sys.stderr)
        return 2

    engine = create_engine(get_settings().database_url, future=True)
    end_date = date.today()
    start_date = end_date - timedelta(days=args.days)
    table = "fund_daily_prices" if is_fund else "stock_daily_bars"
    date_column = "pricing_date" if is_fund else "trading_date"

    try:
        with engine.connect() as conn:
            asset_id = conn.execute(
                text("SELECT id FROM assets WHERE canonical_symbol = :symbol"),
                {"symbol": identifier},
            ).scalar_one_or_none()
            if asset_id is None:
                print(f"ERROR: asset not found: {identifier}", file=sys.stderr)
                return 1

            if is_fund:
                rows = conn.execute(
                    text(
                        """
                        SELECT pricing_date, unit_price, total_net_assets, source_provider
                        FROM fund_daily_prices
                        WHERE asset_id = :asset_id
                          AND pricing_date BETWEEN :start_date AND :end_date
                        ORDER BY pricing_date
                        """
                    ),
                    {"asset_id": asset_id, "start_date": start_date, "end_date": end_date},
                ).mappings().all()
            else:
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
                    f"""
                    SELECT COUNT(*)
                    FROM (
                        SELECT asset_id, {date_column}
                        FROM {table}
                        WHERE asset_id = :asset_id
                          AND {date_column} BETWEEN :start_date AND :end_date
                        GROUP BY asset_id, {date_column}
                        HAVING COUNT(*) > 1
                    ) duplicates
                    """
                ),
                {"asset_id": asset_id, "start_date": start_date, "end_date": end_date},
            ).scalar_one()
    except Exception as exc:
        print(f"QUALITY SMOKE FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    if is_fund:
        report = inspect_fund_prices(rows, start_date=start_date, end_date=end_date)
        print(f"Fund code: {identifier}")
        print(f"Window: {start_date.isoformat()}->{end_date.isoformat()}")
        print(f"Rows inspected: {len(rows)}")
        print(f"Duplicate keys: {len(report.duplicate_keys)}")
        print(f"Invalid unit prices: {len(report.invalid_prices)}")
        print(f"Negative total assets: {len(report.negative_assets)}")
        print(f"Missing expected business dates: {len(report.missing_business_dates)}")
        print(f"Mixed sources: {report.mixed_sources or 'none'}")
        print(f"SQL duplicate groups: {duplicate_count}")

        sources = {str(row["source_provider"]) for row in rows if row.get("source_provider")}
        if sources != {"tefas"}:
            print(f"QUALITY SMOKE FAILED: unexpected TEFAS source set: {sorted(sources)}", file=sys.stderr)
            return 1
    else:
        report = inspect_stock_bars(rows, start_date=start_date, end_date=end_date)
        print(f"Symbol: {identifier}")
        print(f"Window: {start_date.isoformat()}->{end_date.isoformat()}")
        print(f"Rows inspected: {len(rows)}")
        print(f"Duplicate keys: {len(report.duplicate_keys)}")
        print(f"Invalid OHLC rows: {len(report.invalid_ohlc)}")
        print(f"Negative volume rows: {len(report.negative_volume)}")
        print(f"Missing expected business dates: {len(report.missing_business_dates)}")
        print(f"Extreme return rows (>30%): {len(report.extreme_return_dates)}")
        print(f"Mixed sources: {report.mixed_sources or 'none'}")
        print(f"SQL duplicate groups: {duplicate_count}")

        sources = {str(row["source_provider"]) for row in rows if row.get("source_provider")}
        if sources != {"borsapy"}:
            print(f"QUALITY SMOKE FAILED: unexpected BIST source set: {sorted(sources)}", file=sys.stderr)
            return 1

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
