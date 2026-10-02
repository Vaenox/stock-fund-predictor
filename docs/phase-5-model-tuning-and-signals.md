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

AFA üzerinde yapılan kontrollü 3-fold deneyde raw XGBoost probability; ortalama Brier (`0.1931`), LogLoss (`0.7633`) ve ECE (`0.1956`) açısından sigmoid/Platt ve isotonic alternatiflerinden daha iyi sonuç vermiştir. Sigmoid yalnızca bir outer fold'da iyileşmiş, isotonic küçük calibration setinde oynak davranmıştır. Bu nedenle calibration şu aşamada default pipeline'a zorunlu olarak eklenmemiştir; daha geniş symbol/dataset coverage sonrası yeniden değerlendirilecektir.

## Risk Adjustment

Risk katmanı ML modelinden ayrı tutulur.

İlk girdiler:
- volatilite,
- trend zayıflığı,
- likidite/volume davranışı (stock için),
- veri kalitesi / stale data durumu.

Uygulanan deterministik foundation `backend/app/ml/risk_adjustment.py` içindedir.

### Risk ölçeği

- Ara risk bileşenleri `0–100` aralığındadır.
- `0` daha düşük risk, `100` daha yüksek risk anlamına gelir.
- Birleşik `risk_score` yine `0–100` aralığındadır.
- `adjustment`, sinyal katmanında kullanılmak üzere `0` ile `-max_penalty` arasında negatif bir ceza üretir. Varsayılan `max_penalty = 20`.
- Eksik bir risk girdisi otomatik olarak aşırı risk kabul edilmez; ilgili bileşen nötr `50` kabul edilir. Veri kalite/stale bilgisi ayrıca cezalandırılabilir.

### Bileşenler

- **Volatilite:** annualized `volatility_20`; `%20` ve `%50` aralığında lineer risk (`0–100`).
- **Trend zayıflığı:** fiyatın `EMA20` altında olması, `EMA20 < EMA50` ve `EMA50 < EMA200` kontrollerinin mevcut olanlar üzerinden ortalaması.
- **Likidite:** stock için `volume_ratio_20`; `0.50` veya altı yüksek, `1.00` veya üstü düşük likidite riski kabul edilir ve arası lineerdir.
- **Veri kalitesi/stale:** quality failure yüksek risk üretir. `stale_days` için varsayılan uyarı eşiği `1`, maksimum risk eşiği `3` gündür. `stale_days` çağıran katman tarafından bilinen piyasa takvimine göre hesaplanmalıdır.

Fonlarda stock-specific volume/liquidity bileşeni kullanılmaz; ağırlıklar volatilite `%40`, trend zayıflığı `%35`, veri kalite/stale `%25` olacak şekilde normalleştirilir.

Varsayılan stock ağırlıkları: volatilite `%35`, trend zayıflığı `%30`, likidite `%15`, veri kalite/stale `%20`.

Risk adjustment deterministik, açıklanabilir ve ML probability'den bağımsızdır. Bu aşamada risk katmanı tek başına BUY/HOLD/SELL üretmez.

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

### Signal Scale Düzeltmesi

Gerçek threshold smoke testinde aday 30/70, 35/65, 40/60 ve 45/55 eşiklerinin birçok varlıkta BUY üretmediği görüldü. İncelemede önceki signal uygulamasının ML `%50` + technical `%30` ağırlığını doğrudan topladığı, risk adjustment'ı ise ayrıca eklediği; böylece pre-risk skorun teorik üst sınırının `80` kaldığı tespit edildi. Bu durum 0–100 signal ölçeğinin eşiklerle uyumsuz kalmasına neden oluyordu.

Bu nedenle signal foundation, ML ve technical ağırlıklarını kendi toplamlarına göre normalize edecek şekilde düzeltildi. Risk adjustment yine ayrı, bounded negatif penalty olarak bir kez uygulanıyor. Böylece risk cezası yokken signal teorik olarak `0–100` aralığının tamamını kullanabiliyor. Önceki formülle üretilen threshold sonuçları production kararı olarak kullanılmayacak; düzeltme sonrası yeniden değerlendirilecek.

## Kabul Kriterleri

- Inner validation dış test foldunu kullanmamalıdır.
- Outer fold sırası korunmalıdır.
- `gap >= 5` korunmalıdır.
- Aynı seed ile tuning tekrarlanabilir olmalıdır.
- Baseline vs tuned evaluation aynı outer test foldları üzerinde karşılaştırılabilmelidir.
- Feature importance stock/fund için ayrı üretilebilmelidir.
- Signal-risk birleşimi deterministik unit testlerle doğrulanmalıdır.
- Risk adjustment stock/fund ayrımını korumalı ve ML probability'yi değiştirmemelidir.


## Gerçek Signal-Chain OOS Doğrulama Altyapısı

Representation deneyleri sonrasında production default olarak korunan `raw_all` representation ve h5/+3% target contract ile gerçek signal-chain değerlendirmesi için ayrı smoke scripti eklendi: `backend/scripts/smoke_test_signal_chain_real.py`.

Protokol:

- 3 outer chronological expanding walk-forward fold.
- Outer test size: 40 gözlem; leakage gap: 5.
- Her outer foldun training döneminde 2-fold inner chronological XGBoost tuning.
- Tuning objective: mevcut production sözleşmesindeki inner PR-AUC.
- Seçilen config yalnızca ilgili outer test foldunda final model olarak fit edilir.
- Her OOS gözleminde ML probability ve Technical Score birleştirilir; Risk Adjustment bounded negatif penalty olarak bir kez uygulanır.
- Risk etkisini ayrıştırmak için aynı gözlemde risk öncesi signal score da hesaplanır.
- Final raporda ROC-AUC, PR-AUC, target/forward-return Spearman, signal/risk dağılımları ve risk etkisi raporlanır.
- BUY/HOLD/SELL threshold veya signal scaling winner'ı bu smoke testinde seçilmez.

Veri kaynağı tarafında stock için PostgreSQL canonical history yeterliyse kullanılır, değilse mevcut doğrulanmış Borsapy fallback'i kullanılır; fund için PostgreSQL canonical history kullanılır.

Historical OOS içinde geçmişe ait gerçek zamanlı freshness bilgisi güvenilir biçimde yeniden kurulamayacağı için risk fonksiyonuna `quality_ok=True, stale_days=0` verilir. Bu tercih deterministic risk composition'ın OOS davranışını ölçer; historical data freshness hakkında ek iddia üretmez.

Kod commit: `22562255dd05b9044c2ce5e5f402f9d01284c0fd`.

Gerçek AFA, AFT ve THYAO sonuçları bu altyapı eklendiği anda henüz değerlendirilmiş değildir.
