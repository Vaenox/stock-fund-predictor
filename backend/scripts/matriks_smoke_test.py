from __future__ import annotations

import sys
from datetime import date, timedelta

from app.data.providers.matriks_settings import MatriksSettings


def main() -> int:
    try:
        settings = MatriksSettings.from_env()
        provider = settings.build_provider()
    except RuntimeError as exc:
        print(f"CONFIG ERROR: {exc}")
        print("Set the Matriks API variables from the provider's test-access documentation.")
        return 2

    symbol = sys.argv[1] if len(sys.argv) > 1 else "THYAO"
    end_date = date.today()
    start_date = end_date - timedelta(days=30)

    print(f"Matriks health: {provider.health_check()}")
    print(f"Testing symbol: {symbol}")
    print(f"Range: {start_date} -> {end_date}")

    try:
        bars = provider.get_daily_history(symbol, start_date, end_date)
    except Exception as exc:
        print(f"API ERROR: {exc}")
        return 1

    print(f"Received bars: {len(bars)}")
    if not bars:
        print("SMOKE TEST FAILED: no historical bars returned")
        return 1

    first = bars[0]
    last = bars[-1]
    print(
        f"First: {first.trading_date} O={first.open} H={first.high} "
        f"L={first.low} C={first.close}"
    )
    print(
        f"Last:  {last.trading_date} O={last.open} H={last.high} "
        f"L={last.low} C={last.close}"
    )
    print("SMOKE TEST PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
