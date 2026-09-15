from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
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
        }
        try:
            if self._request is not None:
                response = self._request(
                    "POST", url, json=payload, headers=headers, timeout=self._settings.timeout
                )
            else:
                client = self._client or httpx.Client(timeout=self._settings.timeout)
                response = client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise TefasProviderError(f"TEFAS request failed: {endpoint}") from exc
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

    def _fetch_range(self, fund_code: str, start_date: date, end_date: date) -> list[dict[str, Any]]:
        if start_date > end_date:
            raise ValueError("start_date cannot be after end_date")
        rows: list[dict[str, Any]] = []
        for chunk_start, chunk_end in self._chunks(
            start_date, end_date, self._settings.max_days_per_request
        ):
            payload = {
                "fonTipi": self._settings.fund_kind,
                "fonKodu": fund_code.strip().upper(),
                "aramaMetni": None,
                "fonTurKod": None,
                "fonGrubu": None,
                "sfonTurKod": None,
                "fonTurAciklama": None,
                "kurucuKod": None,
                "basTarih": chunk_start.strftime("%Y%m%d"),
                "bitTarih": chunk_end.strftime("%Y%m%d"),
                "basSira": 1,
                "bitSira": 100000,
                "dil": "TR",
                "sFonTurKod": "",
                "fonKod": "",
                "fonGrup": "",
                "fonUnvanTip": "",
            }
            data = self._post(self.info_endpoint, payload)
            for row in data.get("resultList") or []:
                if isinstance(row, dict):
                    rows.append(row)
        return rows

    def list_symbols(self) -> list[ProviderSymbol]:
        today = datetime.now(timezone.utc).date()
        rows = self._fetch_range("", today, today)
        return [
            ProviderSymbol(
                provider=self.name,
                provider_symbol=str(row.get("fonKod", "")).upper(),
                canonical_symbol=str(row.get("fonKod", "")).upper(),
                name=str(row.get("fonUnvan", row.get("fonAdi", ""))),
                asset_type="FUND",
                exchange=None,
                currency="TRY",
            )
            for row in rows
            if row.get("fonKod")
        ]

    def get_symbol_metadata(self, provider_symbol: str) -> ProviderSymbol:
        rows = self._fetch_range(
            provider_symbol,
            datetime.now(timezone.utc).date(),
            datetime.now(timezone.utc).date(),
        )
        if not rows:
            raise TefasProviderError(f"TEFAS fund not found: {provider_symbol}")
        row = rows[0]
        code = str(row.get("fonKod", provider_symbol)).upper()
        return ProviderSymbol(
            provider=self.name,
            provider_symbol=code,
            canonical_symbol=code,
            name=str(row.get("fonUnvan", row.get("fonAdi", code))),
            asset_type="FUND",
            currency="TRY",
        )

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
            price = row.get("fonFiyat", row.get("fiyat", row.get("fonFiyatTarihcesi")))
            if price in (None, ""):
                price = row.get("price")
            if price in (None, ""):
                continue
            records.append(
                ProviderFundPrice(
                    provider_symbol=provider_symbol.strip().upper(),
                    pricing_date=self._date(row.get("tarih", row.get("date"))),
                    unit_price=self._decimal(price),
                    total_net_assets=(
                        self._decimal(row["portfoyBuyuklugu"])
                        if row.get("portfoyBuyuklugu") is not None
                        else None
                    ),
                    source_timestamp=datetime.now(timezone.utc),
                    raw=row,
                )
            )
        return records

    def health_check(self) -> bool:
        try:
            today = datetime.now(timezone.utc).date()
            self._fetch_range("", today, today)
            return True
        except (TefasProviderError, ValueError):
            return False
