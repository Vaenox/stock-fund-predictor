from __future__ import annotations

import argparse
import sys
import time

import borsapy as bp

from app.data.providers.base import ProviderSymbol
from app.data.providers.borsapy import BorsapyProvider
from app.data.streaming.manager import BistStreamManager


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a real BIST TradingView WebSocket smoke test."
    )
    parser.add_argument("--symbol", default="THYAO", help="BIST symbol to test")
    parser.add_argument(
        "--timeout",
        type=float,
        default=20.0,
        help="Seconds to wait for the first quote",
    )
    parser.add_argument(
        "--candle-interval",
        default="1m",
        help="Candle interval for the stream smoke check",
    )
    parser.add_argument(
        "--skip-candle",
        action="store_true",
        help="Only test quote streaming",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    symbol = args.symbol.strip().upper()
    if not symbol:
        print("ERROR: symbol cannot be empty", file=sys.stderr)
        return 2

    provider = BorsapyProvider()
    metadata = ProviderSymbol(
        provider=provider.name,
        provider_symbol=symbol,
        canonical_symbol=symbol,
        name=symbol,
        asset_type="STOCK",
        exchange="BIST",
        currency="TRY",
    )

    manager = BistStreamManager(
        provider_name=provider.name,
        stream_factory=bp.TradingViewStream,
        symbols=[metadata],
    )

    quote_received = False
    candle_received = False

    def on_quote(event) -> None:
        nonlocal quote_received
        quote_received = True
        print(
            f"QUOTE {event.provider_symbol} last={event.price} "
            f"timestamp={event.timestamp} received_at={event.received_at}"
        )

    def on_candle(event) -> None:
        nonlocal candle_received
        candle_received = True
        print(
            f"CANDLE {event.provider_symbol} interval={event.interval} "
            f"O={event.open} H={event.high} L={event.low} C={event.close} "
            f"timestamp={event.timestamp}"
        )

    manager.add_quote_callback(on_quote)
    manager.add_candle_callback(on_candle)

    print(f"Starting BIST WebSocket smoke test for {symbol} ...")
    try:
        manager.start([symbol])
        if not args.skip_candle:
            manager.subscribe_candles([symbol], args.candle_interval)

        deadline = time.monotonic() + args.timeout
        while time.monotonic() < deadline:
            if quote_received and (args.skip_candle or candle_received):
                break
            time.sleep(0.5)
    except Exception as exc:
        print(f"SMOKE TEST FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    finally:
        manager.stop()

    print(f"connected={manager.is_connected}")
    print(f"quote_received={quote_received}")
    print(f"candle_received={candle_received}")

    if not quote_received:
        print(
            "SMOKE TEST FAILED: no quote received. "
            "Check network access, TradingView availability, symbol subscription "
            "and the provider's data entitlement.",
            file=sys.stderr,
        )
        return 1

    if not args.skip_candle and not candle_received:
        print(
            "SMOKE TEST FAILED: quote arrived but no candle event was received.",
            file=sys.stderr,
        )
        return 1

    print("SMOKE TEST PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
