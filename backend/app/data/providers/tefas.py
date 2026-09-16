from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from time import sleep
from typing import Any, Callable

import httpx

from .base import MarketDataProvider, ProviderFundPrice, ProviderStockBar, ProviderSymbol


class TefasProviderError(RuntimeError):
    """Raised when the public TEFAS API response cannot be consumed."""


@dataclass(frozen=True, slots=True)
class TefasSettings:
    base_url: str = "https://www.tefas.gov.tr/api/funds"
    fund_kind: str = "YAT"
    timeout: float = 30.0
    max_days_per_request: int = 28
    discovery_lookback_days: int = 7
    page_size: int = 10000
    max_pages: int = 100
    rate_limit_retries: int = 4
    rate_limit_backoff_seconds: float = 2.0
    inter_chunk_delay_seconds: float = 1.0


class TefasProvider(MarketDataProvider):
    """Public TEFAS fund-data adapter using the current JSON endpoints."""

    info_endpoint = "fonGnlBlgSiraliGetir"

    def __init__(
        self,
        settings: TefasSettings | None = None,
        *,
        client: httpx.Client | None = None,
        request: Callable[..., httpx.Response] | None = None,
    ) -> None:
        self._settings = settings or TefasSettings()
        self._client = client
        self._request = request

    @property
    def name(self) -> str:
        return "tefas"

    def _post(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self._settings.base_url.rstrip('/')}/{endpoint}"
        headers = {
            "Accept": "*/*",
            "Content-Type": "application/json",
            "Origin": "https://www.tefas.gov.tr",
            "Referer": "https://www.tefas.gov.tr/tr/fon-verileri",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/146.0.0.0 Safari/537.36"
            ),
        }
        if self._settings.rate_limit_retries < 0:
            raise ValueError("rate_limit_retries cannot be negative")
        if self._settings.rate_limit_backoff_seconds < 0:
            raise ValueError("rate_limit_backoff_seconds cannot be negative")
        if self._settings.inter_chunk_delay_seconds < 0:
            raise ValueError("inter_chunk_delay_seconds cannot be negative")

        response: httpx.Response | None = None
        for attempt in range(self._settings.rate_limit_retries + 1):
            try:
                if self._request is not None:
                    response = self._request(
                        "POST", url, json=payload, headers=headers, timeout=self._settings.timeout
                    )
                else:
                    client = self._client or httpx.Client(timeout=self._settings.timeout)
                    response = client.post(url, json=payload, headers=headers)

                if response.status_code == 429 and attempt < self._settings.rate_limit_retries:
                    retry_after = response.headers.get("Retry-After")
                    try:
                        delay = (
                            float(retry_after)
                            if retry_after is not None
                            else self._settings.rate_limit_backoff_seconds * (2**attempt)
                        )
                    except ValueError:
                        delay = self._settings.rate_limit_backoff_seconds * (2**attempt)
                    sleep(delay)
                    continue

                response.raise_for_status()
                data = response.json()
                break
            except (httpx.HTTPError, ValueError) as exc:
                if response is not None and response.status_code == 429 and attempt < self._settings.rate_limit_retries:
                    continue
                raise TefasProviderError(f"TEFAS request failed: {endpoint}") from exc
        else:
            raise TefasProviderError(f"TEFAS request failed: {endpoint}")

        if not isinstance(data, dict):
            raise TefasProviderError("TEFAS response is not a JSON object")
        if data.get("errorCode") or data.get("errorMessage"):
            message = str(data.get("errorMessage") or data.get("errorCode"))
            if "out of bounds" in message.lower() or "veri bulunamadı" in message.lower():
                return {"resultList": []}
            raise TefasProviderError(f"TEFAS API error: {message}")
        return data

    @staticmethod
    def _chunks(start_date: date, end_date: date, max_days: int):
        if max_days < 1:
            raise ValueError("max_days must be positive")
        current = start_date
        while current <= end_date:
            chunk_end = min(current + timedelta(days=max_days - 1), end_date)
            yield current, chunk_end
            current = chunk_end + timedelta(days=1)

    @staticmethod
    def _date(value: Any) -> date:
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        text = str(value)
        for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%Y%m%d"):
            try:
                return datetime.strptime(text[:10], fmt).date()
            except ValueError:
                continue
        raise TefasProviderError(f"Invalid TEFAS date: {value!r}")

    @staticmethod
    def _decimal(value: Any) -> Decimal:
        try:
            return Decimal(str(value).replace(",", "."))
        except Exception as exc:
            raise TefasProviderError(f"Invalid TEFAS numeric value: {value!r}") from exc

    def _fetch_range(
        self,
        fund_code: str | None,
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        if start_date > end_date:
            raise ValueError("start_date cannot be after end_date")
        if self._settings.page_size < 1:
            raise ValueError("page_size must be positive")
        if self._settings.max_pages < 1:
            raise ValueError("max_pages must be positive")

        rows: list[dict[str, Any]] = []
        seen_keys: set[tuple[str, str]] = set()
        chunks = list(self._chunks(start_date, end_date, self._settings.max_days_per_request))

        for chunk_index, (chunk_start, chunk_end) in enumerate(chunks):
            page_start = 1
            for _page in range(self._settings.max_pages):
                payload = {
                    "fonTipi": self._settings.fund_kind,
                    "fonKodu": fund_code.strip().upper() if fund_code else None,
                    "aramaMetni": None,
                    "fonTurKod": None,
                    "fonGrubu": None,
                    "sfonTurKod": None,
                    "fonTurAciklama": None,
                    "kurucuKod": None,
                    "basTarih": chunk_start.strftime("%Y%m%d"),
                    "bitTarih": chunk_end.strftime("%Y%m%d"),
                    "basSira": page_start,
                    "bitSira": page_start + self._settings.page_size - 1,
                    "dil": "TR",
                    "sFonTurKod": "",
                    "fonKod": "",
                    "fonGrup": "",
                    "fonUnvanTip": "",
                }
                data = self._post(self.info_endpoint, payload)
                page_rows = [
                    row for row in (data.get("resultList") or []) if isinstance(row, dict)
                ]
                if not page_rows:
                    break

                for row in page_rows:
                    code = str(row.get("fonKodu", "")).strip().upper()
                    row_date = str(row.get("tarih", row.get("date", ""))).strip()
                    key = (row_date, code)
                    if code and row_date and key not in seen_keys:
                        seen_keys.add(key)
                        rows.append(row)

                if len(page_rows) < self._settings.page_size:
                    break
                page_start += self._settings.page_size

            else:
                raise TefasProviderError(
                    "TEFAS pagination exceeded max_pages="
                    f"{self._settings.max_pages} for {chunk_start}..{chunk_end}"
                )

            if chunk_index < len(chunks) - 1 and self._settings.inter_chunk_delay_seconds > 0:
                sleep(self._settings.inter_chunk_delay_seconds)

        return rows

    def fetch_fund_history_bulk(
        self,
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        """Fetch daily info for the complete YAT universe in paginated bulk requests."""
        return self._fetch_range(None, start_date, end_date)

    @staticmethod
    def _to_symbol(row: dict[str, Any]) -> ProviderSymbol | None:
        code = str(row.get("fonKodu", "")).strip().upper()
        if not code:
            return None
        return ProviderSymbol(
            provider="tefas",
            provider_symbol=code,
            canonical_symbol=code,
            name=str(row.get("fonUnvan", row.get("fonAdi", code))).strip(),
            asset_type="FUND",
            exchange=None,
            currency="TRY",
        )

    def list_symbols(self) -> list[ProviderSymbol]:
        """Discover the current YAT fund universe from the latest available day."""
        today = datetime.now(timezone.utc).date()
        lookback = max(self._settings.discovery_lookback_days, 0)

        for offset in range(lookback + 1):
            candidate = today - timedelta(days=offset)
            rows = self._fetch_range(None, candidate, candidate)
            if not rows:
                continue

            result: list[ProviderSymbol] = []
            seen: set[str] = set()
            for row in rows:
                symbol = self._to_symbol(row)
                if symbol is None or symbol.provider_symbol in seen:
                    continue
                seen.add(symbol.provider_symbol)
                result.append(symbol)
            if result:
                return result

        return []

    def get_symbol_metadata(self, provider_symbol: str) -> ProviderSymbol:
        today = datetime.now(timezone.utc).date()
        rows = self._fetch_range(
            provider_symbol,
            today - timedelta(days=self._settings.discovery_lookback_days),
            today,
        )
        if not rows:
            raise TefasProviderError(f"TEFAS fund not found: {provider_symbol}")
        symbol = self._to_symbol(rows[0])
        if symbol is None:
            raise TefasProviderError(f"TEFAS fund not found: {provider_symbol}")
        return symbol

    def get_daily_history(
        self,
        provider_symbol: str,
        start_date: date,
        end_date: date,
    ) -> list[ProviderStockBar]:
        raise NotImplementedError("TEFAS provider is fund-only")

    def get_latest_price(self, provider_symbol: str) -> ProviderStockBar:
        raise NotImplementedError("TEFAS provider is fund-only")

    def get_fund_history(
        self,
        provider_symbol: str,
        start_date: date,
        end_date: date,
    ) -> list[ProviderFundPrice]:
        records: list[ProviderFundPrice] = []
        for row in self._fetch_range(provider_symbol, start_date, end_date):
            price = row.get("fiyat")
            if price in (None, ""):
                price = row.get("fonFiyat")
            if price in (None, ""):
                price = row.get("price")
            if price in (None, ""):
                continue

            pricing_value = row.get("tarih", row.get("date"))
            if pricing_value in (None, ""):
                continue

            portfolio_size = row.get("portfoyBuyukluk")
            if portfolio_size in (None, ""):
                portfolio_size = row.get("portfoyBuyuklugu")

            records.append(
                ProviderFundPrice(
                    provider_symbol=provider_symbol.strip().upper(),
                    pricing_date=self._date(pricing_value),
                    unit_price=self._decimal(price),
                    total_net_assets=(
                        self._decimal(portfolio_size)
                        if portfolio_size not in (None, "")
                        else None
                    ),
                    source_timestamp=datetime.now(timezone.utc),
                    raw=row,
                )
            )
        return records

    def health_check(self) -> bool:
        try:
            return bool(self.list_symbols())
        except (TefasProviderError, ValueError):
            return False
