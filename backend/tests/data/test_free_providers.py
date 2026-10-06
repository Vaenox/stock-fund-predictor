from datetime import date
from decimal import Decimal

import pandas as pd

from app.data.providers.tefas import TefasProvider, TefasSettings
from app.data.providers.yahoo import YahooFinanceProvider, YahooSymbolConfig


def test_yahoo_symbol_uses_bist_suffix():
    assert YahooFinanceProvider.yahoo_symbol("THYAO") == "THYAO.IS"
    assert YahooFinanceProvider.yahoo_symbol("THYAO.IS") == "THYAO.IS"


def test_yahoo_list_symbols_from_configuration():
    provider = YahooFinanceProvider(
        [YahooSymbolConfig(canonical_symbol="THYAO", name="Türk Hava Yolları")]
    )
    symbols = provider.list_symbols()
    assert symbols[0].provider == "yahoo_finance"
    assert symbols[0].provider_symbol == "THYAO.IS"
    assert symbols[0].canonical_symbol == "THYAO"
    assert symbols[0].asset_type == "STOCK"


def test_yahoo_history_mapping_with_fake_ticker(monkeypatch):
    class FakeTicker:
        def __init__(self, symbol):
            self.symbol = symbol

        def history(self, **_kwargs):
            return pd.DataFrame(
                {
                    "Open": [100.0],
                    "High": [105.0],
                    "Low": [99.0],
                    "Close": [104.0],
                    "Adj Close": [103.5],
                    "Volume": [123456.0],
                },
                index=pd.DatetimeIndex(["2026-09-15"]),
            )

    monkeypatch.setattr("app.data.providers.yahoo.yf.Ticker", FakeTicker)

    records = YahooFinanceProvider().get_daily_history(
        "THYAO", date(2026, 9, 1), date(2026, 9, 15)
    )

    assert len(records) == 1
    assert records[0].provider_symbol == "THYAO.IS"
    assert records[0].close == Decimal("104.0")
    assert records[0].volume == Decimal("123456.0")


def test_tefas_history_v2_payload_and_mapping():
    captured = {}

    class FakeResponse:
        status_code = 200
        headers = {"Content-Type": "application/json"}

        def raise_for_status(self):
            return None

        def json(self):
            return {
                "resultList": [
                    {
                        "tarih": "2026-09-15",
                        "fiyat": "35.464180",
                    },
                    {
                        "tarih": "2026-09-16",
                        "fiyat": "35.700000",
                    },
                    {
                        "tarih": "2026-09-30",
                        "fiyat": "99.000000",
                    },
                ]
            }

    def fake_request(method, url, **kwargs):
        captured["method"] = method
        captured["url"] = url
        captured.update(kwargs)
        return FakeResponse()

    provider = TefasProvider(
        request=fake_request,
        settings=TefasSettings(
            history_timeout=7.0,
            history_retries=1,
            history_backoff_seconds=0.5,
        ),
    )
    records = provider.get_fund_history(
        "aak",
        date(2026, 9, 15),
        date(2026, 9, 16),
    )

    assert captured["method"] == "POST"
    assert captured["url"].endswith("/fonFiyatBilgiGetir")
    assert captured["timeout"] == 7.0
    assert captured["content"] == (
        b'{"fonKodu":"AAK","dil":"TR","periyod":13}'
    )
    assert [record.pricing_date for record in records] == [
        date(2026, 9, 15),
        date(2026, 9, 16),
    ]
    assert [record.unit_price for record in records] == [
        Decimal("35.464180"),
        Decimal("35.700000"),
    ]
    assert all(record.total_net_assets is None for record in records)


def test_tefas_history_period_uses_age_from_as_of_date():
    as_of = date(2026, 10, 6)
    assert (
        TefasProvider._history_period(
            date(2026, 10, 4),
            date(2026, 10, 6),
            as_of_date=as_of,
        )
        == 13
    )
    assert (
        TefasProvider._history_period(
            date(2026, 9, 6),
            date(2026, 10, 6),
            as_of_date=as_of,
        )
        == 1
    )
    assert (
        TefasProvider._history_period(
            date(2025, 10, 6),
            date(2026, 10, 6),
            as_of_date=as_of,
        )
        == 12
    )
    assert (
        TefasProvider._history_period(
            date(2024, 1, 10),
            date(2024, 2, 6),
            as_of_date=as_of,
        )
        == 36
    )



def test_tefas_history_period_rejects_ranges_over_five_years():
    try:
        TefasProvider._history_period(date(2020, 1, 1), date(2026, 10, 6))
    except ValueError as exc:
        assert "5-year API limit" in str(exc)
    else:
        raise AssertionError("expected ValueError")

