from __future__ import annotations

from datetime import datetime, timezone
from threading import Event, Lock, Thread
from typing import Callable

from .manager import BistStreamManager, BistStreamManagerError
from .types import LiveCandleEvent, LiveQuoteEvent


class StreamWatchdogError(RuntimeError):
    """Raised when the stream watchdog cannot recover a connection."""


HealthCallback = Callable[[str], None]


class BistStreamWatchdog:
    """Detect stale BIST streams and reconnect with bounded exponential backoff.

    The watchdog is intentionally provider-agnostic: it only depends on the
    manager's public start/stop/subscribe APIs and canonical live events.
    """

    def __init__(
        self,
        manager: BistStreamManager,
        *,
        stale_after_seconds: float = 60.0,
        check_interval_seconds: float = 15.0,
        reconnect_backoff_seconds: float = 2.0,
        max_reconnect_backoff_seconds: float = 30.0,
        health_callback: HealthCallback | None = None,
    ) -> None:
        if stale_after_seconds <= 0 or check_interval_seconds <= 0:
            raise ValueError("stale_after_seconds and check_interval_seconds must be positive")
        if reconnect_backoff_seconds <= 0 or max_reconnect_backoff_seconds < reconnect_backoff_seconds:
            raise ValueError("invalid reconnect backoff configuration")

        self._manager = manager
        self._stale_after_seconds = stale_after_seconds
        self._check_interval_seconds = check_interval_seconds
        self._reconnect_backoff_seconds = reconnect_backoff_seconds
        self._max_reconnect_backoff_seconds = max_reconnect_backoff_seconds
        self._health_callback = health_callback
        self._lock = Lock()
        self._stop_event = Event()
        self._thread: Thread | None = None
        self._last_event_at: dict[str, datetime] = {}
        self._quote_symbols: tuple[str, ...] = ()
        self._candle_subscriptions: tuple[tuple[str, str], ...] = ()

        self._manager.add_quote_callback(self._observe_quote)
        self._manager.add_candle_callback(self._observe_candle)

    @property
    def last_event_at(self) -> dict[str, datetime]:
        with self._lock:
            return dict(self._last_event_at)

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(
        self,
        *,
        quote_symbols: list[str] | None = None,
        candle_subscriptions: list[tuple[str, str]] | None = None,
    ) -> None:
        with self._lock:
            if self.is_running:
                return
            self._quote_symbols = tuple(quote_symbols or self._manager.subscribed_symbols)
            self._candle_subscriptions = tuple(candle_subscriptions or ())
            self._stop_event.clear()
            self._thread = Thread(target=self._run, name="bist-stream-watchdog", daemon=True)
            self._thread.start()

    def stop(self) -> None:
        thread: Thread | None
        with self._lock:
            self._stop_event.set()
            thread = self._thread
            self._thread = None
        if thread is not None:
            thread.join(timeout=max(self._check_interval_seconds, 1.0) + 1.0)

    def force_reconnect(self) -> None:
        self._reconnect()

    def _observe_quote(self, event: LiveQuoteEvent) -> None:
        if event.received_at is not None:
            with self._lock:
                self._last_event_at[event.provider_symbol] = event.received_at

    def _observe_candle(self, event: LiveCandleEvent) -> None:
        if event.received_at is not None:
            with self._lock:
                self._last_event_at[f"{event.provider_symbol}:{event.interval}"] = event.received_at

    def _run(self) -> None:
        backoff = self._reconnect_backoff_seconds
        while not self._stop_event.wait(self._check_interval_seconds):
            if not self._manager.is_connected:
                try:
                    self._reconnect()
                    backoff = self._reconnect_backoff_seconds
                except BistStreamManagerError as exc:
                    self._notify(f"reconnect_failed:{exc}")
                    self._stop_event.wait(backoff)
                    backoff = min(backoff * 2, self._max_reconnect_backoff_seconds)
                continue

            if self._is_stale():
                try:
                    self._reconnect()
                    backoff = self._reconnect_backoff_seconds
                    self._notify("reconnected_after_stale")
                except BistStreamManagerError as exc:
                    self._notify(f"stale_reconnect_failed:{exc}")
                    self._stop_event.wait(backoff)
                    backoff = min(backoff * 2, self._max_reconnect_backoff_seconds)

    def _is_stale(self) -> bool:
        now = datetime.now(timezone.utc)
        with self._lock:
            expected = list(self._quote_symbols)
            expected.extend(f"{symbol}:{interval}" for symbol, interval in self._candle_subscriptions)
            if not expected:
                return False
            return any(
                key not in self._last_event_at
                or (now - self._last_event_at[key]).total_seconds() > self._stale_after_seconds
                for key in expected
            )

    def _reconnect(self) -> None:
        self._manager.stop()
        self._manager.start(list(self._quote_symbols))
        for symbol, interval in self._candle_subscriptions:
            self._manager.subscribe_candles([symbol], interval)
        with self._lock:
            self._last_event_at.clear()

    def _notify(self, message: str) -> None:
        if self._health_callback is not None:
            self._health_callback(message)
