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

## Gerçek Signal-Chain OOS Sonuçları

Production-compatible signal chain; h5/+3% target, mevcut raw_all representation ve 3-fold chronological outer OOS protokolü ile AFA, AFT ve THYAO üzerinde çalıştırıldı. Her dış foldda tuning yalnızca outer-training içinde yapıldı.

### AFA

- 674 raw / 470 dataset / 120 OOS.
- Fold 1: inner PR 1.0000; pre-risk ROC/PR 0.3828/0.3406; final 0.4167/0.3584; final target Spearman -0.1415; forward-return Spearman +0.0081.
- Fold 2: inner PR 0.4831; pre-risk 0.7153/0.3676; final 0.7014/0.2420; final target Spearman +0.2094; forward-return Spearman -0.1454.
- Fold 3: inner PR 0.5694; pre-risk 0.1486/0.0872; final 0.1486/0.0872; final target Spearman -0.4027; forward-return Spearman -0.0728.
- Aggregate: pre-risk ROC/PR 0.2863/0.1869; final 0.2931/0.1679. Risk adjustment ROC'u çok küçük artırsa da PR ve forward-return association iyileşmedi.

### AFT

- 677 raw / 473 dataset / 120 OOS.
- Fold 1: inner PR 0.5020; pre-risk 0.5581/0.6166; final 0.4848/0.5706; target Spearman -0.0261; forward-return +0.0283.
- Fold 2: inner PR 0.7000; pre-risk 0.8725/0.6817; final 0.9902/0.9583; target Spearman +0.6065; forward-return +0.2940.
- Fold 3: inner PR 0.7114; pre-risk 0.1880/0.2216; final 0.0883/0.2067; target Spearman -0.6682; forward-return -0.6764.
- Aggregate: pre-risk ROC/PR 0.4956/0.4300; final 0.4881/0.4636. Risk adjustment foldlar arasında farklı yönde etkiler üretiyor.

### THYAO

- 685 raw / 481 dataset / 120 OOS; PostgreSQL canonical history yetersiz olduğu için Borsapy fallback.
- Fold 1: inner PR 0.6896; pre-risk 0.6667/0.3692; final 0.7013/0.3265; target Spearman +0.2650; forward-return +0.1032.
- Fold 2: inner PR 0.5441; pre-risk 0.4086/0.1997; final 0.3297/0.1909; target Spearman -0.2464; forward-return -0.1298.
- Fold 3: inner PR 0.2835; pre-risk 0.5586/0.1132; final 0.5225/0.0980; target Spearman +0.0206; forward-return -0.5315.
- Aggregate: pre-risk ROC/PR 0.6170/0.2405; final 0.5581/0.1924. Final signal association da pre-risk seviyesine göre zayıfladı.

### Signal-chain değerlendirmesi

- Üç sembolde de 120 OOS observation boyunca signal score deterministik olarak üretildi ve 0–100 sınırları korundu.
- Foldlar arası direction ve metric davranışı stabil değil; özellikle AFA ve AFT'te rejim/fold bağımlılığı belirgin.
- Risk adjustment'ın etkisi evrensel bir performans iyileşmesi göstermiyor. Risk katmanı bu aşamada deterministic foundation olarak korunuyor; OOS sonucu kullanılarak weight/risk penalty optimize edilmiyor.
- Final signal dağılımları semboller arasında belirgin biçimde farklı: AFA median 30.867, AFT 29.792, THYAO 14.227. Bu nedenle daha önce görülen global threshold ölçekleme problemi devam ediyor.
- Historical OOS freshness bilgisi yeniden üretilemediğinden bu testte `quality_ok=True, stale_days=0` kullanıldı. Sonuçlar stale-data mekanizmasının historical performansını ölçmüyor.
- **Karar:** signal direction, mevcut weights, risk penalty ve BUY/HOLD/SELL threshold değişmedi. Bu çalışma signal-chain'in teknik olarak çalıştığını ve leakage-aware OOS değerlendirmesinin üretilebildiğini gösterir; model/sinyal genellenebilirliği için yeterli universal evidence oluşturmaz.
- Smoke sonucunun üçü de: `REAL SIGNAL CHAIN SMOKE TEST PASSED`.

Kod: `backend/scripts/smoke_test_signal_chain_real.py`  
Commit: `22562255dd05b9044c2ce5e5f402f9d01284c0fd`.


### AFS Gerçek Signal-Chain OOS Sonucu

AFS, TEFAS provider fallback ile 685 raw / 481 dataset / 120 OOS gözleminde h5/+3% production target ile çalıştırıldı.

- Outer fold 1: sparse inner validation test_size=40; fold classes train/validation cardinality [(2,2),(1,2)]; inner PR 0.0385. Pre-risk ROC/PR 0.0263/0.0388; final ROC/PR 0.1711/0.0442; target Spearman -0.2484; forward-return Spearman -0.6674.
- Outer fold 2: sparse inner validation test_size=60; fold classes [(2,2),(1,2)]; inner PR 0.0250. Pre-risk 0.3793/0.2373; final 0.3824/0.2380; target Spearman -0.1819; forward-return -0.2711.
- Outer fold 3: normal inner validation test_size=20; fold classes [(2,2),(2,2)]; inner PR 0.7282. Pre-risk 0.2511/0.1297; final 0.2597/0.1321; target Spearman -0.3163; forward-return -0.2638.
- Aggregate pre-risk ROC/PR 0.4675/0.1579; final ROC/PR 0.5040/0.1658. Final target Spearman +0.0052; forward-return Spearman -0.0706.
- Risk impact mean adjustment -1.1472, mean absolute change 1.1472, max absolute change 4.6667; risk adjustment target Spearman +0.1669, forward-return -0.0400.
- Final signal median 25.081, target rate 0.167.
- Sonuç: smoke teknik olarak başarılı olsa da foldlar arasında inner score ve outer association belirgin oynak. Risk adjustment küçük aggregate ROC/PR değişimi sağlıyor ancak forward-return association iyileşmiyor. Production signal direction, weights, risk penalty ve BUY/HOLD/SELL threshold değiştirilmedi.
- Historical freshness için quality_ok=True, stale_days=0 varsayımı korunmuştur.


### ASELS, TUPRS ve BIMAS Gerçek Signal-Chain OOS Sonuçları

Üç production stock smoke sembolü de aynı 3-fold chronological / 40-test / gap=5 signal-chain protokolünü teknik olarak geçti. Üçünde de normal 20-observation inner validation iki sınıflı foldlar üretti.

#### ASELS

- 685 raw / 481 dataset / 120 OOS; Borsapy provider fallback.
- Fold 1: inner PR 0.5501; pre-risk ROC/PR 0.6752/0.4589; final 0.6781/0.4606; target Spearman +0.2890; forward-return +0.1722.
- Fold 2: inner PR 0.5297; pre-risk 0.5000/0.3599; final 0.4753/0.3493; target Spearman -0.0409; forward-return -0.1560.
- Fold 3: inner PR 0.6635; pre-risk 0.3393/0.2526; final 0.2351/0.2418; target Spearman -0.4206; forward-return -0.5332.
- Aggregate: pre-risk ROC/PR 0.5356/0.3627; final ROC/PR 0.5125/0.3546; target Spearman +0.0203; forward-return -0.0888.
- Risk impact: mean adjustment -8.2967; max absolute change 13.8152; risk adjustment target Spearman -0.2369; forward-return -0.2425.
- Final signal median 32.770.
- Risk adjustment sonrası aggregate ROC/PR düştü; foldlar arası yön değişken.

#### TUPRS

- 685 raw / 481 dataset / 120 OOS; Borsapy provider fallback.
- Fold 1: inner PR 0.6116; pre-risk ROC/PR 0.2814/0.1472; final 0.2511/0.1353; target Spearman -0.3277; forward-return -0.4889.
- Fold 2: inner PR 0.3708; pre-risk 0.6200/0.6801; final 0.6500/0.7096; target Spearman +0.2599; forward-return +0.1749.
- Fold 3: inner PR 0.6580; pre-risk 0.6591/0.6225; final 0.6162/0.6083; target Spearman +0.2003; forward-return +0.2156.
- Aggregate: pre-risk ROC/PR 0.5241/0.4580; final ROC/PR 0.5375/0.4735; target Spearman +0.0629; forward-return -0.0112.
- Risk impact: mean adjustment -6.6448; max absolute change 11.0043; risk adjustment target Spearman +0.0569; forward-return +0.0013.
- Final signal median 24.549.
- Aggregate ROC/PR küçük ölçekte yükseldi, fakat foldlar arasında direction davranışı hâlâ heterojen.

#### BIMAS

- 685 raw / 481 dataset / 120 OOS; Borsapy provider fallback.
- Fold 1: inner PR 0.6480; pre-risk ROC/PR 0.2530/0.2184; final 0.2530/0.2170; target Spearman -0.3923; forward-return -0.3790.
- Fold 2: inner PR 0.8094; pre-risk 0.8203/0.6021; final 0.8164/0.5288; target Spearman +0.4386; forward-return +0.5407.
- Fold 3: inner PR 0.5615; pre-risk 0.5413/0.4791; final 0.5556/0.4240; target Spearman +0.0902; forward-return -0.0767.
- Aggregate: pre-risk ROC/PR 0.4479/0.3379; final ROC/PR 0.4486/0.3196; target Spearman -0.0795; forward-return -0.1140.
- Risk impact: mean adjustment -4.3475; max absolute change 9.0170; risk adjustment target Spearman +0.0504; forward-return -0.1000.
- Final signal median 28.665.
- Risk adjustment aggregate ROC'u neredeyse değiştirmedi, PR-AUC'yi düşürdü.

### Yedi Sembol / 840 OOS Signal-Chain Coverage

| Symbol | Asset | Source | Final ROC | Final PR | Target Spearman | Forward-return Spearman | Median signal |
|---|---|---|---:|---:|---:|---:|---:|
| AFA | Fund | PostgreSQL | 0.2931 | 0.1679 | -0.2911 | -0.0728 | 30.867 |
| AFT | Fund | PostgreSQL | 0.4881 | 0.4636 | +0.6065 | +0.2940 | 29.792 |
| THYAO | Stock | Borsapy | 0.5581 | 0.1924 | +0.0735 | -0.0624 | 14.227 |
| AFS | Fund | TEFAS | 0.5040 | 0.1658 | +0.0052 | -0.0706 | 25.081 |
| ASELS | Stock | Borsapy | 0.5125 | 0.3546 | +0.0203 | -0.0888 | 32.770 |
| TUPRS | Stock | Borsapy | 0.5375 | 0.4735 | +0.0629 | -0.0112 | 24.549 |
| BIMAS | Stock | Borsapy | 0.4486 | 0.3196 | -0.0795 | -0.1140 | 28.665 |

- Her sembolde 120 OOS gözlem olmak üzere toplam 840 OOS signal-chain gözlemi değerlendirildi.
- Final ROC-AUC semboller arasında 0.2931–0.5581; final PR-AUC 0.1658–0.4735; median signal 14.227–32.770 aralığında kaldı.
- Risk adjustment etkisi uniform değil: bazı sembollerde ROC/PR iyileşirken bazılarında düşüyor. Bu nedenle risk penalty OOS sonuçlarından yeniden optimize edilmedi.
- Yedi sembolün sembol-bazlı metriklerinin eşit ağırlıklı descriptive ortalaması pre-risk ROC 0.4820 -> final 0.4774 ve pre-risk PR 0.3106 -> final 0.3053'tür. Bu pooled OOS metriği değildir.
- Signal direction ve forward-return association işaretleri semboller arasında karışık olduğu için global direction inversion seçilmedi.
- Signal score ölçeği sembol bazında belirgin biçimde değiştiği için global BUY/HOLD/SELL threshold winner seçilmedi.
- Historical freshness geçmiş OOS için yeniden kurulamadığından tüm smoke sonuçlarında quality_ok=True, stale_days=0 kullanıldı; gerçek zamanlı stale-data performansı bu deneyle ölçülmedi.

### Faz 5 Signal-Chain Kapanış Değerlendirmesi

Signal-chain altyapısı; inner tuning, Technical Score, deterministic risk adjustment ve final signal composition ile birlikte 7 sembol / 840 OOS gözleminde teknik olarak doğrulandı. Buna rağmen OOS metrics ve direction davranışı fold/symbol rejimine duyarlı ve risk adjustment evrensel performans artışı sağlamıyor.

Production contract şu aşamada değiştirilmedi:

- raw_all representation
- horizon=5
- positive return threshold=+3%
- mevcut ML/Technical signal weights
- bounded risk adjustment penalty
- global signal direction yok
- BUY/HOLD/SELL threshold winner yok

Bu aşamadan sonra yeni deneyler Faz 6 altında kontrollü olarak ele alınmalıdır.
