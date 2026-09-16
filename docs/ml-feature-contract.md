# ML Feature Dataset Contract

## Amaç

İlk XGBoost baseline için teknik göstergelerden deterministik, zaman sıralı ve leakage-safe bir eğitim veri seti üretmek.

## Girdi

Feature builder, `backend/app/analysis/indicators.py` çıktısını girdi kabul eder.

- Stock: `trading_date` + `close` + stock indicator seti
- Fund: `pricing_date` + `unit_price` + fund indicator seti

Göstergeler upstream indicator engine tarafından hesaplanır. Feature builder yeni bir ileriye dönük teknik gösterge üretmez.

## Feature Seti

### Stock

`SMA/EMA 20,50,200`, `RSI 14`, `MACD 12/26/9`, Bollinger alanları, `momentum 5/10/20`, `return 1d/5d`, `volatility 20d`, `ATR 14`, `ATR %`, `ADX 14`, `volume SMA 20`, `volume ratio 20`, `volume change 1d`.

### Fund

`SMA/EMA 20,50,200`, `RSI 14`, `MACD 12/26/9`, Bollinger alanları, `momentum 5/10/20`, `return 1d/5d`, `volatility 20d`.

Fonlarda hisseye özgü OHLCV/ATR/ADX/volume feature'ları kullanılmaz.

## Target

İlk supervised-learning hedefi:

```text
forward_return_5d = price[t+5] / price[t] - 1

target = 1  if forward_return_5d > 0.03
         0  otherwise
```

`t+5`, takvim günü değil sonraki **5 mevcut gözlemi** ifade eder. Bu yaklaşım fonlarda eksik/olmayan takvim günleri nedeniyle oluşabilecek yanlış horizon yorumunu engeller.

`forward_return_5d` ve `target` yalnızca eğitim datasetinde bulunur. Live/inference tarafında `build_inference_features()` bu iki alanı hiç üretmez.

## Warm-up ve Missing Data

Indicator warm-up satırları upstream katmanda `NaN` olarak korunur. Default feature builder, seçilen feature setinin tamamı hazır olmayan satırları datasetten çıkarır.

Ayrıca tam gelecek horizon'u bulunmayan son 5 gözlem eğitim datasetine alınmaz.

Sessiz forward-fill veya backward-fill yapılmaz.

## Leakage Kuralları

1. Feature kolonları yalnızca `t` anına kadar mevcut veriden gelir.
2. Target gelecekteki `t+5` gözleminden üretilebilir; target feature setinin parçası değildir.
3. Sonuçlar tarih sırasına göre tutulur.
4. Train/validation/test ayrımı bu katmanda yapılmaz; modelleme fazında zaman sıralı split / walk-forward uygulanır.
5. Random shuffle ile veri karıştırılmaz.

## API

```python
build_ml_feature_dataset(frame, asset_type="stock" | "fund", config=MLFeatureConfig(...))
build_inference_features(frame, asset_type="stock" | "fund")
```

İlk baseline için varsayılanlar:

```text
horizon = 5
positive_return_threshold = 0.03
```

## Faz 3 Kabul Kriteri

Feature builder aşağıdakileri sağlamalıdır:

- Feature kolonları deterministik olmalı.
- Stock ve fund feature sözleşmeleri ayrışmalı.
- Warm-up ve geleceği olmayan son horizon satırları kontrol edilmeli.
- Target yalnızca eğitim datasetinde olmalı.
- Truncated geçmiş üzerinde aynı anchor gözlemin feature değerleri değişmemeli.
