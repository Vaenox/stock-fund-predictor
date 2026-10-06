# Faz 6 — Fund Daily Unit-Price Backtest Contract

## Amaç

TEFAS fon verilerinde stock next-open execution modelinden ayrı, yalnızca günlük unit price serisine dayanan leakage-safe bir execution contract sağlamak.

## Execution Contract

- Signal date **t** üzerindeki target weight, en erken **t+1** tarihinde yayınlanan fund unit price ile uygulanır.
- Aynı gün t unit price ile execution yapılmaz.
- Stock-style `open`, `high`, `low` ve bid/ask slippage semantics kullanılmaz.
- Fractional fund units desteklenir.
- Target weight 0.0..1.0 aralığındadır.
- Buy işlemleri mevcut cash ve transaction cost dikkate alınarak sınırlandırılır; cash negatif olamaz.
- Transaction cost traded notional üzerinden bps olarak uygulanır.
- Bu foundation'da fund slippage **0** kabul edilir ve ayrıca ölçülür; unit price zaten tek günlük NAV/price observation olduğundan stock-style execution slippage modellenmez.
- Son signal'ın t+1 unit price gözlemi yoksa işlem yapılmaz.
- Forced final liquidation yoktur; pozisyon son executable valuation'da tutulur.
- BacktestResult içinde market `TEFAS` ve execution costs audit için korunur.

## API

Temel engine:

```python
from app.backtesting.fund_engine import (
    FundBacktestConfig,
    run_long_only_fund_backtest,
)
```

Girdi kolonları:

| Kolon | Anlam |
|---|---|
| `date` | Fon fiyat tarihi |
| `unit_price` | Günlük unit price |
| `target_weight` | t tarihinde hesaplanan desired exposure |

Kolon isimleri `date_column`, `price_column` ve `target_column` parametreleriyle değiştirilebilir.

## Cost Contract

Default foundation:

- Initial capital: 100,000
- Transaction cost: 10 bps
- Slippage: 0 bps

Gerçek TEFAS/fon-specific entry/exit fee, tax, redemption lock, settlement veya order-cutoff kuralları bu foundation'ın dışında tutulur; bunlar ancak veri/ürün contractı netleştirildikten sonra ayrıca modellenebilir.

## Neden t+1?

Fonlarda yalnızca günlük unit price bulunduğundan signal üretildiği tarih ile execution valuation'ını ayırmak, aynı gözlemin hem karar hem execution için kullanılmasını engeller. Bu sözleşme, stock tarafındaki next-open yaklaşımının fonlara birebir kopyası değildir; yalnızca aynı leakage-avoidance ilkesini günlük NAV serisine uygun şekilde uygular.

## Test Kapsamı

`backend/tests/backtesting/test_fund_engine.py` aşağıdakileri doğrular:

- next-day unit-price execution,
- last signal için execution yapılmaması,
- transaction cost etkisi,
- slippage'ın sıfır tutulması,
- cash'in negatif olmaması,
- target weight bounds,
- duplicate date rejection,
- positive unit price requirement,
- negative transaction cost rejection.

Bu task prediction modelini, target threshold'u, signal weighting'i veya production stock sizing policy'yi değiştirmez.
