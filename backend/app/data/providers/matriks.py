from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Callable

import httpx

from .base import MarketDataProvider, ProviderStockBar, ProviderSymbol


class MatriksProviderError(RuntimeError):
    """Raised when the Matriks API cannot provide a valid response."""


@dataclass(frozen=True, slots=True)
class MatriksEndpointConfig:
    symbols_path: str
    metadata_path: str
    history_path: str
    latest_path: str
    health_path: str | None = None


class MatriksRestProvider(MarketDataProvider):
    """Matriks REST adapter with endpoint paths supplied from the purchased API contract.

    Matriks exposes REST services, but endpoint details and data scope depend on the
    subscribed service. Paths therefore remain configuration rather than invented constants.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        endpoints: MatriksEndpointConfig,
        *,
        timeout: float = 20.0,
        client: httpx.Client | None = None,
        request: Callable[..., httpx.Response] | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._endpoints = endpoints
        self._timeout = timeout
        self._client = client
        self._request = request

    @property
    def name(self) -> str:
        return "matriks"

    def _request_json(self, path: str, **params: Any) -> Any:
        url = f"{self._base_url}/{path.lstrip('/')}"
        headers = {"Authorization": f"Bearer {self._api_key}", "Accept": "application/json"}
        try:
            if self._request is not None:
                response = self._request("GET", url, headers=headers, params=params, timeout=self._timeout)
            else:
                client = self._client or httpx.Client(timeout=self._timeout)
                response = client.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise MatriksProviderError(f"Matriks request failed: {url}") from exc

    @staticmethod
    def _rows(payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [row for row in payload if isinstance(row, dict)]
        if isinstance(payload, dict):
            for key in ("data", "result", "items", "rows"):
                value = payload.get(key)
                if isinstance(value, list):
                    return [row for row in value if isinstance(row, dict)]
        raise MatriksProviderError("Matriks response does not contain a row collection")

    @staticmethod
    def _value(row: dict[str, Any], *keys: str) -> Any:
        for key in keys:
            if key in row and row[key] not in (None, ""):
                return row[key]
        raise MatriksProviderError(f"Required field missing from Matriks response: {keys[0]}")

    @staticmethod
    def _decimal(value: Any) -> Decimal:
        try:
            return Decimal(str(value).replace(",", "."))
        except Exception as exc:
            raise MatriksProviderError(f"Invalid numeric value from Matriks: {value!r}") from exc

    @staticmethod
    def _date(value: Any) -> date:
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        text = str(value)
        for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(text[:10], fmt).date()
            except ValueError:
                continue
        raise MatriksProviderError(f"Invalid date from Matriks: {value!r}")

    def list_symbols(self) -> list[ProviderSymbol]:
        rows = self._rows(self._request_json(self._endpoints.symbols_path))
        return [self._parse_symbol(row) for row in rows]

    def get_symbol_metadata(self, provider_symbol: str) -> ProviderSymbol:
        row = self._rows(
            self._request_json(self._endpoints.metadata_path, symbol=provider_symbol)
        )[0]
        return self._parse_symbol(row)

    def get_daily_history(
        self,
        provider_symbol: str,
        start_date: date,
        end_date: date,
    ) -> list[ProviderStockBar]:
        payload = self._request_json(
            self._endpoints.history_path,
            symbol=provider_symbol,
            start=start_date.isoformat(),
            end=end_date.isoformat(),
        )
        return [self._parse_bar(row, provider_symbol) for row in self._rows(payload)]

    def get_latest_price(self, provider_symbol: str) -> ProviderStockBar:
        row = self._rows(
            self._request_json(self._endpoints.latest_path, symbol=provider_symbol)
        )[0]
        return self._parse_bar(row, provider_symbol)

    def get_fund_history(self, provider_symbol: str, start_date: date, end_date: date):
        raise NotImplementedError("Matriks fund adapter will be added after the subscribed fund API contract is confirmed")

    def health_check(self) -> bool:
        if not self._endpoints.health_path:
            return False
        try:
            self._request_json(self._endpoints.health_path)
            return True
        except MatriksProviderError:
            return False

    @classmethod
    def _parse_symbol(cls, row: dict[str, Any]) -> ProviderSymbol:
        asset_type = str(row.get("asset_type", row.get("assetType", "STOCK"))).upper()
        return ProviderSymbol(
            provider="matriks",
            provider_symbol=str(cls._value(row, "provider_symbol", "providerSymbol", "symbol", "code")),
            canonical_symbol=str(row.get("canonical_symbol", row.get("canonicalSymbol", row.get("symbol", row.get("code"))))).upper(),
            name=str(cls._value(row, "name", "title", "description")),
            asset_type=asset_type,
            isin=row.get("isin", row.get("ISIN")),
            exchange=row.get("exchange", row.get("exchangeCode", "BIST")),
            currency=str(row.get("currency", "TRY")).upper(),
        )

    @classmethod
    def _parse_bar(cls, row: dict[str, Any], provider_symbol: str) -> ProviderStockBar:
        source_timestamp = row.get("source_timestamp", row.get("sourceTimestamp", row.get("timestamp")))
        parsed_timestamp: datetime | None = None
        if source_timestamp:
            parsed_timestamp = datetime.fromisoformat(str(source_timestamp).replace("Z", "+00:00"))

        return ProviderStockBar(
            provider_symbol=provider_symbol,
            trading_date=cls._date(cls._value(row, "trading_date", "tradingDate", "date", "Date")),
            open=cls._decimal(cls._value(row, "open", "Open")),
            high=cls._decimal(cls._value(row, "high", "High")),
            low=cls._decimal(cls._value(row, "low", "Low")),
            close=cls._decimal(cls._value(row, "close", "Close")),
            adjusted_close=(
                cls._decimal(row["adjusted_close"])
                if row.get("adjusted_close") is not None
                else None
            ),
            volume=(cls._decimal(row["volume"]) if row.get("volume") is not None else None),
            turnover=(cls._decimal(row["turnover"]) if row.get("turnover") is not None else None),
            source_timestamp=parsed_timestamp,
            raw=row,
        )
