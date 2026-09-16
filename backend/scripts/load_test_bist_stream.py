from __future__ import annotations

import argparse
import sys
import time

import borsapy as bp

from app.data.providers.borsapy import BorsapyProvider
from app.data.streaming.manager import BistStreamManager


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Load-test the BIST TradingView WebSocket subscription layer."
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="Seconds to observe the full subscription set",
    )
    parser.add_argument(
        "--max-symbols",
        type=int,
        default=0,
        help="Limit symbols for a controlled test; 0 means all discovered symbols",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.timeout <= 0 or args.max_symbols < 0:
        print("ERROR: invalid test configuration", file=sys.stderr)
        return 2

    provider = BorsapyProvider()
    symbols = provider.list_symbols()
    if args.max_symbols:
        symbols = symbols[: args.max_symbols]
    if not symbols:
        print("ERROR: no BIST symbols discovered", file=sys.stderr)
        return 1

    quote_count = 0
    candle_count = 0

    def on_quote(_event) -> None:
        nonlocal quote_count
        quote_count += 1

    def on_candle(_event) -> None:
        nonlocal candle_count
        candle_count += 1

    manager = BistStreamManager(
        provider_name=provider.name,
        stream_factory=bp.TradingViewStream,
        symbols=symbols,
    )
    manager.add_quote_callback(on_quote)
    manager.add_candle_callback(on_candle)

    requested = [item.provider_symbol for item in symbols]
    print(f"Discovered symbols: {len(requested)}")
    print("Starting one persistent BIST TradingView stream ...")

    started_at = time.monotonic()
    try:
        manager.start(requested)
        elapsed = time.monotonic() - started_at
        subscribed = len(manager.subscribed_symbols)
        print(f"Subscribed symbols: {subscribed}")
        print(f"Subscription setup seconds: {elapsed:.3f}")

        if subscribed != len(requested):
            print("LOAD TEST FAILED: not all requested symbols were subscribed", file=sys.stderr)
            return 1

        deadline = time.monotonic() + args.timeout
        while time.monotonic() < deadline:
            time.sleep(1.0)

        print(f"Quote events observed: {quote_count}")
        print(f"Candle events observed: {candle_count}")
        print("LOAD TEST PASSED: subscription layer accepted the full requested universe")
        return 0
    except Exception as exc:
        print(f"LOAD TEST FAILED: {exc}", file=sys.stderr)
        return 1
    finally:
        manager.stop()


if __name__ == "__main__":
    raise SystemExit(main())
