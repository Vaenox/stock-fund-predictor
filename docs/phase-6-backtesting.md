# Faz 6 — Backtest / Prediction Evaluation Foundation

## Amaç

Phase 5'te doğrulanan signal-chain'i historical portfolio simulation katmanına taşımak. Bu fazda backtest motoru, prediction/signal zamanlaması, transaction cost, slippage ve temel risk metrikleri birbirinden açıkça ayrılır.

## İlk Sözleşme

- Backtest yalnızca zaman sıralı historical observations kullanır.
- Signal date t üzerinde üretilen target portfolio weight, en erken t+1 open fiyatında uygulanır.
- t+1 close veya daha ileri veri signal execution kararında kullanılmaz.
- Motor long-only notional/weight modelidir; target weight 0.0–1.0 arasındadır.
- Phase 5'te production BUY/HOLD/SELL threshold seçilmediği için backtest motoru threshold seçmez. Dışarıdan target_weight serisi alır.
- Transaction cost basis points (bps) ile trade notional üzerinden uygulanır.
- Slippage ayrı bir execution-price etkisi olarak modellenir; buy execution open x (1 + slippage), sell execution open x (1 - slippage).
- Equity curve net of transaction costs ve slippage olarak tutulur.
- Tarihsel OOS'ta data freshness yeniden üretilemediği için Phase 5'teki quality_ok=True, stale_days=0 varsayımı backtest'e otomatik taşınmaz; backtest veri seti bunu açıkça sağlamalıdır.

## İlk Metrikler

- Total return
- Annualized return
- Annualized volatility
- Sharpe ratio (risk-free rate 0 varsayımı)
- Maximum drawdown
- Win rate (zero-return periods hariç pozitif net-return oranı)
- Profit factor
- Total transaction cost
- Total slippage cost
- Total turnover

## Uygulama Notu

- Buy işlemlerinde target exposure hesaplanırken transaction cost ve slippage nedeniyle cash negatife düşmez; mevcut nakit işlem maliyeti dahil affordability ile sınırlandırılır.
- Bu ilk foundation fractional units kullanır; gerçek market lot/tax/commission rules sonraki aşamada ayrıca uygulanacaktır.

## Açık Konular

- Position sizing / capital allocation policy
- Lot-size ve fractional-unit rules
- Market-specific commission/tax rules
- Benchmark comparison
- Multi-asset portfolio simulation
- Prediction history persistence
- Strategy-level walk-forward backtest orchestration
- Paper trading position state

Bu konular ilk engine foundation dışında kontrollü adımlar olarak ele alınacaktır.
