from datetime import date
from decimal import Decimal

from app.data.providers.matriks import MatriksEndpointConfig, MatriksRestProvider


PROVIDER = MatriksRestProvider(
    base_url="https://example.test",
    headers={"X-API-Key": "test-key"},
    endpoints=MatriksEndpointConfig(
        symbols_path="symbols",
        metadata_path="metadata/{symbol}",
        history_path="history",
        latest_path="latest",
    ),
)


def test_parse_symbol_normalizes_canonical_fields() -> None:
    symbol = PROVIDER._parse_symbol(
        {
            "symbol": "thyao",
            "name": "Türk Hava Yolları",
            "assetType": "stock",
            "exchangeCode": "BIST",
            "currency": "try",
        }
    )

    assert symbol.provider == "matriks"
    assert symbol.provider_symbol == "thyao"
    assert symbol.canonical_symbol == "THYAO"
    assert symbol.asset_type == "STOCK"
    assert symbol.exchange == "BIST"
    assert symbol.currency == "TRY"


def test_parse_bar_converts_numeric_and_date_values() -> None:
    bar = PROVIDER._parse_bar(
        {
            "date": "15.09.2026",
            "Open": "280,50",
            "High": "286.00",
            "Low": "279.90",
            "Close": "284.75",
            "Volume": "1250000",
            "Turnover": "354200000.25",
            "sourceTimestamp": "2026-09-15T15:30:00+03:00",
        },
        "THYAO",
    )

    assert bar.trading_date == date(2026, 9, 15)
    assert bar.open == Decimal("280.50")
    assert bar.high == Decimal("286.00")
    assert bar.low == Decimal("279.90")
    assert bar.close == Decimal("284.75")
    assert bar.volume == Decimal("1250000")
    assert bar.turnover == Decimal("354200000.25")
    assert bar.raw is not None
    assert bar.source_timestamp is not None


def test_get_daily_history_validates_range_before_request() -> None:
    try:
        PROVIDER.get_daily_history(
            "THYAO",
            date(2026, 9, 16),
            date(2026, 9, 15),
        )
    except ValueError as exc:
        assert str(exc) == "start_date cannot be after end_date"
    else:
        raise AssertionError("expected invalid date range to fail")
