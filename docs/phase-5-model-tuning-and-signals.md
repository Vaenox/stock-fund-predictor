# Faz 5 — Model Tuning / Feature Importance / Signal-Risk Foundation

## Amaç

Faz 4'te kabul edilen XGBoost baseline üzerine kontrollü hyperparameter tuning, feature importance raporlama ve daha sonra ML probability + technical score + risk adjustment birleşimine temel olacak deterministik sözleşmeleri oluşturmak.

## Validation ve Leakage Kuralları

- Dış evaluation protokolü expanding / chronological walk-forward olarak korunur.
- Leakage gap `>= 5` korunur.
- Dış test foldları tuning sırasında hiçbir şekilde kullanılmaz.
- Her dış fold için tuning yalnızca o fold'un training döneminin içinde yapılır.
- Inner validation da zaman sıralı walk-forward olmalıdır; random split kullanılmaz.
- Inner validation model seçimi içindir; dış test fold yalnızca final fold metriği içindir.
- Feature selection veya hyperparameter tuning gelecekteki gözlemleri kullanamaz.

## Tuning

Başlangıçta sınırlı ve okunabilir bir XGBoost arama uzayı kullanılacaktır. İlk sürümde Optuna veya benzeri optimizer kullanılabilir; ancak arama reproducible seed ile çalışmalı ve aday sayısı konfigüre edilebilmelidir.

Arama hedefi öncelikle inner validation PR-AUC / ROC-AUC davranışını dikkate almalıdır. Accuracy tek başına objective değildir.

## Baseline Karşılaştırması

Aynı outer walk-forward fold'larında:

1. Faz 4 baseline modeli fit/evaluate edilir.
2. Aynı fold'un yalnızca training döneminde tuning yapılır.
3. Seçilen tuned config dış test foldunda bir kez değerlendirilir.
4. Baseline ve tuned sonuçları aynı raporda yan yana tutulur.

## Feature Importance

- XGBoost feature importance `gain` temelli raporlanmalıdır.
- Importance değeri yalnızca model açıklaması olarak kullanılmalıdır; nedensellik iddiası değildir.
- Stock ve fund feature setleri ayrı raporlanmalıdır.
- Fold bazında importance mümkün olduğunca kayıt altına alınmalıdır.

## Probability Calibration

Threshold optimizasyonundan önce olasılıkların calibration davranışı ayrıca değerlendirilecektir. Calibration, dış test verisini kullanarak tuning yapılacak şekilde tasarlanamaz.

## Risk Adjustment

Risk katmanı ML modelinden ayrı tutulur.

Risk adjustment için ilk girdiler:
- volatilite,
- trend zayıflığı,
- likidite/volume davranışı (stock için),
- veri kalitesi / stale data durumu.

Risk adjustment deterministik ve açıklanabilir olmalıdır.

## Signal Foundation

Final signal daha sonra:

```text
ML Probability
      +
Technical Score
      +
Risk Adjustment
      ↓
Signal Score
      ↓
BUY / HOLD / SELL
```

şeklinde ele alınacaktır.

Signal eşikleri henüz performans sonucu görülmeden sabitlenmiş “kazanan” değerler olarak kabul edilmeyecektir.

## Kabul Kriterleri

- Inner validation dış test foldunu kullanmamalıdır.
- Outer fold sırası korunmalıdır.
- `gap >= 5` korunmalıdır.
- Aynı seed ile tuning tekrarlanabilir olmalıdır.
- Baseline vs tuned evaluation aynı outer test foldları üzerinde karşılaştırılabilmelidir.
- Feature importance stock/fund için ayrı üretilebilmelidir.
- Signal-risk birleşimi deterministik unit testlerle doğrulanmalıdır.
