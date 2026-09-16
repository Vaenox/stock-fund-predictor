from __future__ import annotations

import argparse
import csv
import io
import re
import sys
import time
from pathlib import Path

import borsapy as bp
import httpx

from app.data.providers.base import ProviderSymbol
from app.data.providers.borsapy import BorsapyProvider
from app.data.streaming.manager import BistStreamManager

FALLBACK_UNIVERSE_URL = (
    "https://raw.githubusercontent.com/ahmeterenodaci/"
    "Istanbul-Stock-Exchange--BIST--including-symbols-and-logos/main/bist.csv"
)
TICKER_PATTERN = re.compile(r"^[A-Z0-9]{2,6}$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Load-test the BIST TradingView WebSocket subscription layer."
    )
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--max-symbols", type=int, default=0)
    parser.add_argument(
        "--symbols-file",
        type=Path,
        help="Optional newline-delimited BIST symbol file; bypasses company discovery",
    )
    parser.add_argument(
        "--universe-url",
        default=FALLBACK_UNIVERSE_URL,
        help="Fallback CSV URL used only when borsapy company discovery fails",
    )
    return parser.parse_args()


def _symbols_from_csv(text: str) -> tuple[list[ProviderSymbol], int]:
    rows = csv.DictReader(io.StringIO(text))
    result: list[ProviderSymbol] = []
    seen: set[str] = set()
    skipped = 0
    for row in rows:
        symbol = str(row.get("symbol", "")).strip().upper()
        if not symbol or symbol in seen:
            continue
        if not TICKER_PATTERN.fullmatch(symbol):
            skipped += 1
            continue
        seen.add(symbol)
        name = str(row.get("name", symbol)).strip() or symbol
        result.append(
            ProviderSymbol(
                provider="borsapy",
                provider_symbol=symbol,
                canonical_symbol=symbol,
                name=name,
                asset_type="STOCK",
                exchange="BIST",
                currency="TRY",
            )
        )
    return result, skipped


def _symbols_from_file(path: Path) -> tuple[list[ProviderSymbol], int]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return _symbols_from_csv(
        "name,symbol\n" + "\n".join(f"{line},{line}" for line in lines if line.strip())
    )


def _load_fallback_universe(url: str) -> tuple[list[ProviderSymbol], int]:
    response = httpx.get(url, timeout=15.0)
    response.raise_for_status()
    return _symbols_from_csv(response.text)


def discover_symbols(
    provider: BorsapyProvider, args: argparse.Namespace
) -> tuple[list[ProviderSymbol], str, int]:
    if args.symbols_file:
        symbols, skipped = _symbols_from_file(args.symbols_file)
        return symbols, f"file:{args.symbols_file}", skipped
    try:
        return provider.list_symbols(), "borsapy.companies", 0
    except Exception as exc:
        print(
            f"WARNING: borsapy company discovery failed ({type(exc).__name__}: {exc})",
            file=sys.stderr,
        )
        print(f"Falling back to public BIST universe CSV: {args.universe_url}")
        symbols, skipped = _load_fallback_universe(args.universe_url)
        return symbols, "public-bist-csv", skipped


def main() -> int:
    args = parse_args()
    if args.timeout <= 0 or args.max_symbols < 0:
        print("ERROR: invalid test configuration", file=sys.stderr)
        return 2

    provider = BorsapyProvider()
    try:
        symbols, universe_source, skipped = discover_symbols(provider, args)
    except Exception as exc:
        print(f"ERROR: unable to load BIST universe: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

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
    print(f"Universe source: {universe_source}")
    print(f"Discovered symbols: {len(requested)}")
    if skipped:
        print(f"Skipped non-ticker CSV rows: {skipped}")
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
