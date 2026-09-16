from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta

from app.data.providers.tefas import TefasProvider


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a real TEFAS daily fund-universe smoke test."
    )
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--max-funds", type=int, default=0)
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
    requested_codes = {fund.provider_symbol.upper() for fund in funds}

    try:
        rows = provider.fetch_fund_history_bulk(start_date, end_date)
    except Exception as exc:
        print(f"SMOKE TEST FAILED: bulk TEFAS request failed: {exc}", file=sys.stderr)
        return 1

    rows_by_code = {}
    for row in rows:
        code = str(row.get("fonKodu", "")).strip().upper()
        if code:
            rows_by_code.setdefault(code, 0)
            rows_by_code[code] += 1

    successful = sum(1 for code in requested_codes if rows_by_code.get(code, 0) > 0)
    empty = len(requested_codes) - successful

    print(f"Discovered funds: {len(funds)}")
    print(f"History window: {start_date.isoformat()} -> {end_date.isoformat()}")
    print(f"Bulk rows returned: {len(rows)}")
    print(f"Funds with data: {successful}")
    print(f"Funds without rows in window: {empty}")

    if successful == 0:
        print("SMOKE TEST FAILED: no TEFAS history rows matched discovered funds", file=sys.stderr)
        return 1

    print("SMOKE TEST PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
