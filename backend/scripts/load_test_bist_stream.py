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

# The public fallback CSV can lag behind Borsa İstanbul's current ticker codes.
# These mappings were verified against documented BIST/KAP code changes.
CURRENT_SYMBOL_ALIASES = {
    "DAGHL": "TRHOL",
    "GRTRK": "GRTHO",
    "ITTFH": "LRSHO",
    "KOZAA": "TRMET",
    "MIPAZ": "LYDHO",
    "PEGYO": "PEHOL",
    "QNBFB": "QNBTR",
    "QNBFL": "QNBFK",
    "TETMT": "LYDYE",
    "UZERB": "INTEK",
}
# YGYO was removed from listing after the bankruptcy process and is not an active
# TradingView symbol for the streaming universe.
RETIRED_SYMBOLS = {"YGYO"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Load-test the BIST TradingView WebSocket subscription layer."
    )
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--max-symbols", type=int, default=0)
    parser.add_argument(
        "--require-quote-for-all",
        action="store_true",
        help="Fail unless every requested symbol emits at least one canonical quote event",
    )
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
        source_symbol = str(row.get("symbol", "")).strip().upper()
        if not source_symbol:
            continue
        if source_symbol in RETIRED_SYMBOLS:
            skipped += 1
            continue

        symbol = CURRENT_SYMBOL_ALIASES.get(source_symbol, source_symbol)
        if not TICKER_PATTERN.fullmatch(symbol) or symbol in seen:
            skipped += 1
            continue

        seen.add(symbol)
        source_name = str(row.get("name", symbol)).strip() or symbol
        name = (
            f"{source_name} (renamed from {source_symbol})"
            if symbol != source_symbol
            else source_name
        )
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
    quoted_symbols: set[str] = set()
    candle_symbols: set[str] = set()

    def on_quote(event) -> None:
        nonlocal quote_count
        quote_count += 1
        quoted_symbols.add(event.provider_symbol)

    def on_candle(event) -> None:
        nonlocal candle_count
        candle_count += 1
        candle_symbols.add(event.provider_symbol)

    manager = BistStreamManager(
        provider_name=provider.name,
        stream_factory=bp.TradingViewStream,
        symbols=symbols,
    )
    manager.add_quote_callback(on_quote)
    manager.add_candle_callback(on_candle)

    requested = [item.provider_symbol for item in symbols]
    requested_set = set(requested)
    print(f"Universe source: {universe_source}")
    print(f"Discovered symbols: {len(requested)}")
    if skipped:
        print(f"Skipped stale/non-ticker CSV rows: {skipped}")
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

        missing_quote_symbols = sorted(requested_set - quoted_symbols)
        quote_coverage = (len(quoted_symbols) / len(requested_set)) * 100.0

        print(f"Quote events observed: {quote_count}")
        print(
            f"Unique symbols with quote: {len(quoted_symbols)}/{len(requested_set)} "
            f"({quote_coverage:.2f}%)"
        )
        print(f"Candle events observed: {candle_count}")
        if candle_symbols:
            print(f"Unique symbols with candle: {len(candle_symbols)}/{len(requested_set)}")
        if missing_quote_symbols:
            print(
                f"Symbols without quote events ({len(missing_quote_symbols)}): "
                f"{', '.join(missing_quote_symbols)}"
            )

        if args.require_quote_for_all and missing_quote_symbols:
            print(
                "LOAD TEST FAILED: strict quote coverage requested, but some symbols "
                "did not emit a canonical quote event",
                file=sys.stderr,
            )
            return 1

        if args.require_quote_for_all:
            print(
                "LOAD TEST PASSED: every requested symbol emitted at least one "
                "canonical quote event"
            )
        else:
            print(
                "LOAD TEST PASSED: subscription layer accepted the requested universe; "
                "quote coverage reported separately"
            )
        return 0
    except Exception as exc:
        print(f"LOAD TEST FAILED: {exc}", file=sys.stderr)
        return 1
    finally:
        manager.stop()


if __name__ == "__main__":
    raise SystemExit(main())
