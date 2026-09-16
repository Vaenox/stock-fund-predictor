from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta

from app.data.providers.tefas import TefasProvider


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a real TEFAS daily fund-universe smoke test."
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Number of recent calendar days to request",
    )
    parser.add_argument(
        "--max-funds",
        type=int,
        default=0,
        help="Limit funds checked; 0 means all discovered funds",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.days < 1 or args.max_funds < 0:
        print("ERROR: invalid test configuration", file=sys.stderr)
        return 2

    provider = TefasProvider()
    funds = provider.list_symbols()
    if args.max_funds:
        funds = funds[: args.max_funds]
    if not funds:
        print("ERROR: no TEFAS funds discovered", file=sys.stderr)
        return 1

    end_date = date.today()
    start_date = end_date - timedelta(days=args.days)
    successful = 0
    empty = 0
    failed = 0

    print(f"Discovered funds: {len(funds)}")
    print(f"History window: {start_date.isoformat()} -> {end_date.isoformat()}")

    for fund in funds:
        try:
            rows = provider.get_fund_history(fund.provider_symbol, start_date, end_date)
        except Exception as exc:
            failed += 1
            print(f"FAILED {fund.provider_symbol}: {exc}", file=sys.stderr)
            continue

        if rows:
            successful += 1
        else:
            empty += 1

    print(f"Funds with data: {successful}")
    print(f"Funds without rows in window: {empty}")
    print(f"Fund requests failed: {failed}")

    if failed:
        print("SMOKE TEST FAILED: one or more TEFAS fund requests failed", file=sys.stderr)
        return 1

    if successful == 0:
        print("SMOKE TEST FAILED: no TEFAS history rows were returned", file=sys.stderr)
        return 1

    print("SMOKE TEST PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
