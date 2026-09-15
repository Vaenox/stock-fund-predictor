from datetime import date
from decimal import Decimal

import pandas as pd

from app.data.providers.tefas import TefasProvider
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


def test_tefas_payload_mapping_with_fake_request():
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "resultList": [
                    {
                        "fonKod": "AAK",
                        "fonUnvan": "ATA PORTFÖY ÇOKLU VARLIK DEĞİŞKEN FON",
                        "tarih": "15.09.2026",
                        "fonFiyat": "35,464180",
                        "portfoyBuyuklugu": "35461839.75",
                    }
                ]
            }

    def fake_request(*_args, **_kwargs):
        return FakeResponse()

    provider = TefasProvider(request=fake_request)
    records = provider.get_fund_history(
        "AAK", date(2026, 9, 15), date(2026, 9, 15)
    )

    assert len(records) == 1
    assert records[0].provider_symbol == "AAK"
    assert records[0].pricing_date == date(2026, 9, 15)
    assert records[0].unit_price == Decimal("35.464180")
    assert records[0].total_net_assets == Decimal("35461839.75")
