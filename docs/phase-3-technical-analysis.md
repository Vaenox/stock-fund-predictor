# Faz 3 — Technical Analysis Engine

## Amaç

Faz 3'te temiz canonical market data üzerinden deterministik teknik göstergeler üretilir. Bu katmanın çıktısı daha sonra ML feature pipeline'ına girer; teknik göstergeler tek başına BUY/HOLD/SELL kararı üretmez.

## Veri sözleşmesi

### Stock input

`trading_date`, `open`, `high`, `low`, `close` ve mümkünse `volume` alanları gerekir. Satırlar kronolojik sıralanır; duplicate ve invalid market data kontrolleri upstream quality/validation katmanının sorumluluğundadır.

### Fund input

`pricing_date` ve `unit_price` gerekir. Fonlar için günlük NAV/unit price üzerinden fiyat-tabanlı göstergeler hesaplanır. OHLC ve hacim gerektiren göstergeler fund çıktısına eklenmez.

## İlk göstergeler

| Grup | Feature'lar |
|---|---|
| Trend | `sma_20`, `sma_50`, `sma_200`, `ema_20`, `ema_50`, `ema_200` |
| Momentum | `rsi_14`, `momentum_5`, `momentum_10`, `momentum_20`, `return_1d`, `return_5d` |
| MACD | `macd`, `macd_signal`, `macd_hist` |
| Bollinger | `bb_mid`, `bb_upper`, `bb_lower`, `bb_width`, `bb_position` |
| Volatilite | `atr_14`, `atr_pct_14`, `volatility_20` |
| Trend strength | `adx_14` |
| Volume | `volume_sma_20`, `volume_ratio_20`, `volume_change_1d` |

## Hesaplama kuralları

- Feature hesapları yalnızca mevcut ve geçmiş gözlemleri kullanır.
- Input sıralaması fonksiyon içinde kronolojik hale getirilir.
- Rolling feature'larda yeterli geçmiş oluşmadan değer üretmek yerine `NaN` korunur.
- `rsi_14` Wilder-style exponential smoothing yaklaşımıyla hesaplanır.
- MACD: EMA(12) - EMA(26), signal EMA(9).
- Bollinger: SMA(20) ± 2 × rolling standard deviation.
- ATR(14): true range'in Wilder-style smoothing değeri.
- ADX(14): directional movement ve true range üzerinden trend-strength metriği.
- Yıllıklandırılmış `volatility_20`, günlük getirinin 20 günlük standart sapmasının `sqrt(252)` ile ölçeklenmesidir.

## Look-ahead kontrolü

Indicator engine gelecekteki satırları kullanmamalıdır. Aynı index'teki bir feature'ın değeri, veri setine daha sonraki satırlar eklendiğinde değişmemelidir. Unit test'te tam ve truncate edilmiş veri setlerinde geçmiş bir index karşılaştırılır.

## Warm-up semantiği

- SMA/EMA 20 için 20 gözlem gerekir.
- SMA/EMA 50 için 50 gözlem gerekir.
- SMA/EMA 200 için 200 gözlem gerekir.
- Momentum n için n geçmiş gözlem gerekir.
- RSI/ATR/ADX gibi göstergelerde kendi periyotlarına bağlı warm-up dönemi vardır.
- Warm-up `NaN` değerleri ileride ML pipeline'ında açıkça ele alınmalıdır; burada sessizce ileri/doldurma uygulanmaz.

## Fon kapsamı

Fonlarda yalnızca unit-price tabanlı göstergeler hesaplanır. ATR, ADX ve volume tabanlı feature'lar stock OHLCV yapısına özgüdür.

## Teknik skor

Ham indicator üretimi ile teknik skor ayrı katmanlardır. `backend/app/analysis/scoring.py` deterministik ve açıklanabilir bir `0–100` skor üretir.

### Stock score bileşenleri

- Trend: fiyat/EMA20, EMA20/EMA50 ve EMA50/EMA200 ilişkileri.
- Momentum: RSI14, MACD histogramı, 5 günlük ve 20 günlük momentum.
- Volatilite: ATR/fiyat, 20 günlük yıllıklaştırılmış volatilite ve Bollinger konumu.
- Hacim: 20 günlük volume ratio ve 1 günlük volume change.
- Trend gücü: ADX14 ve Bollinger konumu.

Varsayılan ağırlıklar `30% / 30% / 15% / 15% / 10%` olarak tanımlıdır. Eksik indicator bileşenleri bu katmanda sessizce sıfırlanmaz; mevcut değilse ilgili hesap nötr `50` kabul edilir. Bu ağırlıklar üretim trading eşiği değildir ve out-of-sample backtest ile doğrulanmadan karar politikası olarak kullanılmamalıdır.

### Fund score

Fonlarda OHLCV olmadığı için hacim ve stock-only trend-strength alanları üretilmez. Trend, momentum ve volatilite bileşenleri mevcut ağırlıkları oranında yeniden normalize edilir. Böylece `0–100` skor varlık türleri arasında karşılaştırılabilir bir aralıkta kalır, ancak kullanılan feature kapsamı açıkça açıklanır.

### Explainability

Her satırda aşağıdaki alanlar tutulur:

- `technical_score`
- `technical_score_trend`
- `technical_score_momentum`
- `technical_score_volatility`
- `technical_score_volume`
- `technical_score_breadth`
- `technical_score_reason`

Bu çıktı daha sonra dashboard açıklaması ve ML feature dataset builder için kullanılacaktır.

## Faz 3 kabul kriterlerinin ilk bölümü

- [x] Indicator engine module oluşturuldu.
- [x] Stock indicator seti oluşturuldu.
- [x] Fund unit-price indicator seti oluşturuldu.
- [x] Warm-up / `NaN` semantiği belirlendi.
- [x] Look-ahead regression unit testi eklendi.
- [x] Teknik Score (`0–100`) engine oluşturuldu.
- [x] Teknik Score explainability çıktıları oluşturuldu.
- [x] Gerçek TEFAS geçmiş verisiyle indicator smoke testi — AAL, 312 satır, look-ahead kontrolü geçti.
- [ ] Gerçek BIST geçmiş verisiyle indicator smoke testi
- [ ] Teknik Score gerçek BIST + TEFAS smoke testi
- [ ] ML feature dataset builder
- [ ] Faz 3 kabul testleri
