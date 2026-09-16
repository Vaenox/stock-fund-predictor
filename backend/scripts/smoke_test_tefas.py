from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta

from app.data.providers.tefas import TefasProvider


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a real TEFAS full YAT universe bulk/pagination smoke test."
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

    try:
        funds = provider.list_symbols()
    except Exception as exc:
        print(f"SMOKE TEST FAILED: fund discovery failed: {exc}", file=sys.stderr)
        return 1

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
        print(f"SMOKE TEST FAILED: bulk/paginated TEFAS request failed: {exc}", file=sys.stderr)
        return 1

    row_keys: list[tuple[str, str]] = []
    rows_by_code: dict[str, int] = {}
    for row in rows:
        code = str(row.get("fonKodu", "")).strip().upper()
        pricing_date = str(row.get("tarih", row.get("date", ""))).strip()
        if code and pricing_date:
            row_keys.append((pricing_date, code))
            rows_by_code[code] = rows_by_code.get(code, 0) + 1

    successful = sum(1 for code in requested_codes if rows_by_code.get(code, 0) > 0)
    empty = len(requested_codes) - successful
    duplicate_keys = len(row_keys) - len(set(row_keys))
    unique_codes_returned = len(set(code for _, code in row_keys))

    print(f"Discovered funds: {len(funds)}")
    print(f"History window: {start_date.isoformat()} -> {end_date.isoformat()}")
    print(f"Bulk/paginated rows returned: {len(rows)}")
    print(f"Unique fund codes returned: {unique_codes_returned}")
    print(f"Funds with data: {successful}")
    print(f"Funds without rows in window: {empty}")
    print(f"Duplicate (date, fund_code) rows: {duplicate_keys}")

    if successful != len(requested_codes):
        missing = sorted(requested_codes - set(rows_by_code))
        print(
            "SMOKE TEST FAILED: discovered funds missing from history: "
            + ", ".join(missing[:50]),
            file=sys.stderr,
        )
        return 1

    if duplicate_keys:
        print("SMOKE TEST FAILED: duplicate (date, fund_code) rows returned", file=sys.stderr)
        return 1

    print("FULL TEFAS UNIVERSE SMOKE TEST PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
