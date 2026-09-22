# Proje İlerleme Kaydı

Bu dosya, fazlarda alınan kararların, tamamlanan işlerin ve sıradaki taskların kısa özetini tutar. Yeni bir sohbette projeye devam ederken önce bu dosya referans alınmalıdır.

## Güncel Durum

- Aktif faz: **Faz 5 — Model Tuning / Feature Importance / Signal-Risk Foundation**
- Son tamamlanan faz: **Faz 4 — ML Baseline / XGBoost**
- Faz 1 ürün spesifikasyonu: `docs/phase-1-product-spec.md`
- Faz 2 canonical market data contract: `docs/data-contract.md`
- Faz 3 teknik analiz contract: `docs/phase-3-technical-analysis.md`
- Faz 3 ML feature contract: `docs/ml-feature-contract.md`
- Faz 4 ML baseline contract: `docs/phase-4-ml-baseline.md`
- Faz 4 baseline evaluation raporu: `docs/phase-4-ml-baseline-evaluation.md`
- Faz 5 contract: `docs/phase-5-model-tuning-and-signals.md`
- Faz 5 tuning evaluation: `docs/phase-5-tuning-evaluation.md`

## Faz 2 — Data Infrastructure — TAMAMLANDI

- BIST ve TEFAS provider, normalization, validation, persistence, quality ve streaming altyapısı tamamlandı.
- Gerçek BIST full-universe coverage: 516/516 quote.
- Gerçek TEFAS full universe: 2040/2040 fon.
- Historical + live PostgreSQL persistence, duplicate/upsert ve E2E pipeline doğrulandı.

## Faz 3 — Technical Analysis Engine — TAMAMLANDI

- Stock/fund indicator engine tamamlandı.
- Technical Score Engine ve ML feature dataset builder tamamlandı.
- Warm-up, look-ahead ve leakage kontrolleri tamamlandı.
- Analysis test suite: `18 passed`.
- Faz 3 kabul edildi.

## Faz 4 — ML Baseline / XGBoost — TAMAMLANDI

- Leakage-aware expanding walk-forward splitter oluşturuldu.
- `gap >= 5` kuralı uygulandı.
- XGBoost baseline wrapper ve metrikler oluşturuldu.
- Fold train/test class counts `FoldMetrics` içine eklendi.
- Phase 4 acceptance suite oluşturuldu.
- Gerçek BIST smoke coverage: `THYAO`, `ASELS`, `TUPRS`, `BIMAS` geçti.
- Gerçek TEFAS smoke coverage: `AFA`, `AFT`, `AFS` geçti.
- `AAL` one-class training problemi doğrulandı ve validation kuralı gevşetilmedi.
- TEFAS provider 429 için retry/backoff davranışı eklendi.

### Faz 4 Acceptance

```text
PYTHONPATH=. pytest tests/ml/test_phase4_acceptance.py -q
3 passed
```

**Faz 4 kabul edildi ve kapatıldı.** Baseline teknik çalışırlığı ve leakage-aware evaluation sözleşmesini doğrular; production model kalitesi/genellenebilirlik garantisi değildir.

## Faz 5 — Model Tuning / Feature Importance / Signal-Risk Foundation — AKTİF

### Tamamlanan

- Faz 5 contract oluşturuldu: `docs/phase-5-model-tuning-and-signals.md`.
- Dış test foldlarını tuning dışında tutacak inner walk-forward tasarımı oluşturuldu.
- `backend/app/ml/tuning.py` ile `TuningConfig`, inner split üretimi, candidate inner PR-AUC değerlendirmesi ve deterministic candidate selection eklendi.
- Küçük ve reproducible XGBoost candidate grid oluşturuldu (`12` aday; depth/learning-rate/min-child-weight eksenleri).
- `backend/app/ml/feature_importance.py` ile XGBoost `gain` importance raporlama foundation'ı eklendi.
- `backend/tests/ml/test_tuning.py` ile inner gap, chronological split ve deterministic selection testleri eklendi.
- `backend/tests/ml/test_feature_importance.py` ile stock feature coverage ve validation testleri eklendi.
- `backend/scripts/smoke_test_xgboost_tuning_real.py` ile gerçek BIST/TEFAS inner tuning smoke akışı eklendi.
- Gerçek THYAO tuning smoke: `REAL XGBOOST TUNING SMOKE TEST PASSED`.
- THYAO tuning sonucu: best inner PR-AUC `1.000000`; seed `42`; selected candidate outer evaluation için kullanılabilir hale getirildi.
- `backend/app/ml/comparison.py` ile aynı outer walk-forward foldlarında baseline vs tuned karşılaştırma katmanı eklendi.
- `backend/tests/ml/test_comparison.py` ile outer-fold aynılaştırma, gap ve deterministic tuning kontrolleri eklendi.
- Gerçek THYAO baseline vs tuned outer comparison sonucu `docs/phase-5-tuning-evaluation.md` içine kaydedildi.
- AFA gerçek DB verisiyle baseline vs tuned outer comparison çalıştırıldı ve fold sonuçları `docs/phase-5-tuning-evaluation.md` içine kaydedildi.
- AFA üzerinde kontrollü calibration değerlendirmesi yapıldı; raw probability ortalama Brier/LogLoss/ECE açısından sigmoid ve isotonic alternatiflerinden daha iyi çıktı. Calibration şu aşamada default pipeline'a eklenmedi.
- `backend/app/ml/risk_adjustment.py` ile deterministik risk foundation eklendi: volatilite, trend zayıflığı, stock likidite/volume ve veri quality/stale.
- `backend/tests/ml/test_risk_adjustment.py` ile risk ölçeği, maksimum penalty, stale etkisi, fund/stock ayrımı ve config validation testleri eklendi ve **6/6 geçti**.
- AFA gerçek veri risk smoke testi geçti: risk score `0.000000`, adjustment `-0.000000`.
- THYAO gerçek veri risk smoke testi geçti: risk score `45.713769`, adjustment `-9.142754`.
- `backend/app/ml/signal.py` ile ML probability + technical score + risk adjustment birleşim foundation'ı eklendi.
- `backend/app/ml/signal_scaling.py` ile ML probability ve technical score için configurable normalization foundation'ı eklendi; default bounds geçici validation değerleridir.
- `derive_signal_scale_config` ile outer test dışındaki kronolojik OOF component dağılımlarından quantile tabanlı scaling config türetme eklendi; üretim bound optimizasyonu yapılmaz.
- `calculate_percentile_scaled_signal_base` ile target bağımsız empirical-percentile normalization eklendi; referans dağılımı yalnızca geçmiş OOF componentlerinden alınır.
- `backend/tests/ml/test_signal.py` oluşturuldu ve **7/7 geçti**.
- Tüm ML test suite güncel durumda **59/59 geçti**.
- `backend/scripts/smoke_test_signal_real.py` ile gerçek veri üzerinde tuning + inference + technical score + risk + signal zinciri oluşturuldu.
- `backend/tests/ml/test_phase5_acceptance.py` ile Phase 5 risk/signal acceptance testleri oluşturuldu.
- `backend/app/ml/signal_rules.py` ile parametrik ve deterministik BUY/HOLD/SELL sınıflandırma kuralları eklendi; varsayılan eşikler validation sonucu değil, konfigürasyon değeridir.
- `backend/app/ml/signal_validation.py` ile aday threshold'lar için BUY/HOLD/SELL coverage, target rate ve forward-return metriklerini kazanan seçmeden raporlayan validation katmanı eklendi.
- `backend/scripts/smoke_test_signal_thresholds_real.py` ile model/tuning dış test foldlarından aday signal threshold metriklerini gözlemlemek için gerçek veri walk-forward smoke akışı eklendi.

### Faz 5 THYAO Outer Comparison

- Fold 1: baseline ROC `0.2157`, PR `0.1246`; tuned ROC `0.2549`, PR `0.1310`; accuracy ikisinde de `0.8500`.
- Fold 2: test fold tek sınıflı; ROC/PR iki model için de `None`; accuracy ikisinde de `1.0000`.
- Fold 3: baseline ROC `0.8947`, PR `0.3333`; tuned ROC `0.9474`, PR `0.5000`; accuracy ikisinde de `0.9500`.
- Bu tek sembol sonucunda tuning iki ölçülebilir outer fold'da ROC-AUC ve PR-AUC'yi yükseltti; ancak sample size sınırlı ve Fold 2 tek sınıflı olduğu için genellenebilirlik sonucu çıkarılmadı.

### Faz 5 Signal Scaling Validation — THYAO / AFA

Gerçek 3-fold OOS scaling smoke testi başarıyla geçti. Quantile bound'lar her outer fold için yalnızca outer training içindeki inner OOF observations üzerinden türetildi; outer test observations scaling bound seçiminde kullanılmadı.

**THYAO — 120 OOS**
- Raw signal: median 11.607, mean 12.292, max 33.248.
- Scaled signal: median 19.955, mean 20.494, max 63.360.
- Scaled threshold coverage: 30/70 -> BUY 0%, HOLD 27.5%, SELL 72.5%; 40/60 -> BUY 1.7%, HOLD 5.8%, SELL 92.5%.
- Fold-specific scaling değişiyor; Fold 2 ve Fold 3 farklı probability rejimleri gösteriyor.

**AFA — 120 OOS**
- Raw signal: median 24.330, mean 24.392, max 48.309.
- Scaled signal: median 39.030, mean 45.977, max 100.000.
- Scaled threshold coverage: 30/70 -> BUY 27.5%, HOLD 32.5%, SELL 40.0%; 40/60 -> BUY 30.8%, HOLD 13.3%, SELL 55.8%.
- Fold 2 scaled signal median 88.926, Fold 3 median 25.583; bu nedenle tek global bound setinin OOS dönemlerindeki rejim değişimini tam olarak sabitlemediği görüldü.

**Karar:** Quantile ve empirical-percentile scaling ikisi de teknik olarak çalışıyor; ancak AFA ve THYAO üzerinde fold/rejim stabilitesi farklı davranıyor. Bu nedenle hiçbir yöntem production default olarak seçilmedi. BUY/HOLD/SELL eşikleri hâlâ seçilmedi. OOS monotonicity testinde hem quantile hem percentile signal skorlarında THYAO ve AFA için güçlü pozitif yönlü ilişki görülmedi; bu nedenle threshold seçimi ertelendi ve aggregation bileşenleri ayrı ayrı teşhis edilecek.

### Faz 5 Feature Representation Ablation — Güncel Sonuç

Düzeltilmiş normalization dönüşümleriyle gerçek 3-fold outer OOS feature ablation **AFA, AFT, THYAO, ASELS, TUPRS ve BIMAS** üzerinde tamamlandı. AAL, canonical history yalnızca 22 satır olduğu ve feature dataset 0 satıra düştüğü için veri yetersizliği nedeniyle bu deneyden dışarıda bırakıldı; validation kuralı gevşetilmedi.

Tuned aggregate PR-AUC liderleri:
- **AFA:** normalized_all `0.3923` > stationary_core `0.2699` > raw_all `0.2285`
- **AFT:** normalized_all `0.5136` > stationary_core `0.4722` > raw_all `0.4100`
- **THYAO:** raw_all `0.2006` > normalized_all `0.1867` > stationary_core `0.1773`
- **ASELS:** raw_all `0.4416` > normalized_all `0.4271` > stationary_core `0.3710`
- **TUPRS:** normalized_all `0.4127` > raw_all `0.4018` > stationary_core `0.3761`
- **BIMAS:** stationary_core `0.4556` > normalized_all `0.4341` > raw_all `0.3834`

Altı sembolün basit ortalama tuned PR-AUC değerleri raw_all `0.3443`, normalized_all `0.3944`, stationary_core `0.3537` oldu. Buna rağmen symbol-level ve fold-level davranışlar homojen olmadığı için normalized_all production default seçilmedi. Representation seçimi ileride yapılacaksa seçim outer test gözlemlerine göre değil, inner walk-forward validation içinde leakage-safe şekilde yapılmalıdır.

**Karar:** raw_all, normalized_all ve stationary_core üçü de candidate representation olarak korunacak; mevcut production feature contract sessizce değiştirilmeyecek. Representation selection ayrı bir validation/model-selection taskı olarak ele alınacaktır.

### Faz 5 Tasarım Kararları

Tuning yalnızca outer fold training periodu içinde yapılır. Outer test fold model seçimi sırasında görülmez. Inner objective olarak PR-AUC kullanılır. Threshold optimizasyonu ve BUY/HOLD/SELL tasarımı tuning sonuçlarından ayrı ele alınır.

Calibration şu aşamada zorunlu değildir; AFA kontrollü deneyinde raw probability daha iyi ortalama calibration metrikleri üretmiştir. Daha geniş veri kapsamı ile yeniden değerlendirilecektir.

Risk adjustment ML probability'den ayrıdır. Risk `0–100`, adjustment `0..-20` varsayılan aralığındadır. Stock için volatilite/trend/liquidity/data quality; fund için volatilite/trend/data quality kullanılır. Risk katmanı bu aşamada tek başına BUY/HOLD/SELL üretmez.

Signal foundation'da ML probability `0–1` değeri `0–100` ölçeğine çevrilir; ML ve technical score ağırlıklı temel skor oluşturur, risk adjustment negatif ceza olarak doğrudan uygulanır ve final sonuç `0–100` aralığına clip edilir. BUY/HOLD/SELL eşikleri henüz sabitlenmez.

### Faz 5 Taskları

- [x] Tuning dataset / inner-validation foundation oluştur.
- [x] XGBoost hyperparameter candidate search katmanı oluştur.
- [x] Baseline vs tuned modelleri aynı outer walk-forward protokolünde karşılaştır.
- [x] Feature importance / gain raporlama foundation'ı oluştur.
- [x] Model probability calibration ihtiyacını değerlendir.
- [x] Risk adjustment foundation'ını uygula ve unit testlerini ekle.
- [x] Risk adjustment unit testlerini Codespace üzerinde çalıştır ve PASS doğrula.
- [x] AFA ve THYAO gerçek veri üzerinde risk smoke doğrulaması yap.
- [x] ML probability + technical score + risk adjustment birleşim sözleşmesini uygula.
- [x] Deterministik BUY/HOLD/SELL signal rules tasarla ve test et.
- [x] Leakage-safe signal scaling walk-forward smoke testini THYAO/AFA üzerinde çalıştır ve sonuçları değerlendir.
- [x] Fold-stability/robust normalization yaklaşımını değerlendir; empirical-percentile scaling comparison smoke akışı eklendi.
- [x] THYAO ve AFA gerçek OOS scaling comparison sonuçlarını çıkardı; quantile vs percentile için stability ve threshold outcome metrikleri kaydedildi.
- [x] Signal score monotonicity / bin association analizini gerçek OOS veride çalıştır.
- [x] THYAO ve AFA OOS sonuçlarında signal score'un target/forward-return ile monoton yönlü ilişki göstermediği gözlendi; aggregation bileşenleri için ayrı association diagnostic eklendi.
- [x] ML probability / technical score / risk adjustment bileşen association sonuçlarını gerçek OOS veride çıkardı.
- [x] Bileşenlerin OOS bin davranışlarını geniş symbol coverage ile doğruladı; THYAO, ASELS, TUPRS, BIMAS, AFA ve AFT üzerinde bileşen yönlerinin sembolden sembole değiştiği görüldü.
- [x] Sabit signal ağırlıklarının yeterince robust olmadığı görüldü; leakage-safe inner-OOF logistic meta-aggregation foundation'ı eklendi.
- [x] Gerçek threshold smoke testinde raw signal ölçeğinin 0–100 eşikleriyle uyumsuz olduğu tespit edildi; ML+technical weighted base skorunun kendi toplam ağırlığına normalize edilmesiyle signal ölçeği düzeltildi. Risk adjustment ayrı negatif penalty olarak uygulanmaya devam ediyor.
- [x] AFA ve THYAO direction diagnostic ile ML probability / technical score yönlerinin sembole göre değiştiği doğrulandı; target/model katmanı threshold'dan önce yeniden incelenmeye alındı.
- [x] Model direction diagnostic canlı TEFAS bağımlılığından çıkarıldı; stock/fund canonical history artık PostgreSQL'den okunuyor. Böylece Phase 5 direction validation veri sağlayıcı TLS erişiminden ayrıştırıldı.
- [x] AFA DB-backed baseline vs tuned direction diagnostic: baseline aggregate direct ROC `0.3360`, inverse ROC `0.6640`; tuned direct ROC `0.3377`, inverse ROC `0.6623`. Her iki model de inverse yönde daha yüksek ayrıştırma gösterdi; tuning yön problemini düzeltmedi.
- [x] Direction diagnostic stock tarafında DB history yetersizse Borsapy fallback kullanacak şekilde düzeltildi; böylece THYAO testinin yalnızca kısa DB incremental verisi nedeniyle başarısız olması engellendi.
- [x] Target distribution diagnostic de aynı DB/Borsapy fallback davranışına getirildi ve indicator warm-up sonrası boş dataset için açık hata eklendi.
- [x] `+1%`, `+2%`, `+3%`, `+5%` target threshold'ları için aynı chronological outer/inner protokolünde baseline/tuned direction karşılaştırması yapacak diagnostic eklendi; bu aşama target seçimi yapmaz, yalnızca yön ve base-rate davranışını raporlar.
- [x] THYAO ve AFA üzerinde `+1/+2/+3/+5%` target direction diagnostic çalıştırıldı; threshold değişiminin model yönünü materially değiştirebildiği, ancak iki asset arasında ortak bir production target desteklenmediği görüldü. Mevcut `+3%` contract şimdilik korunuyor.

### Faz 5 Threshold Smoke — İlk Deneme

İlk threshold smoke sonuçlarında THYAO ve AFA'da tüm 120 OOS gözlem SELL sınıfına düşerken ASELS/TUPRS/BIMAS/AFT'te BUY coverage çoğunlukla `0%` veya `1.7%` seviyesinde kaldı. Bu sonuçlar eşik seçimi olarak kaydedilmedi. İncelemede signal foundation'ın pre-risk teorik üst sınırının `80` olduğu görüldü; formula düzeltildi ve threshold validation yeniden çalıştırılacak.

### Faz 5 Threshold Validation — THYAO Güncel Smoke

Düzeltilmiş 0–100 raw signal foundation ile THYAO üzerinde gerçek 3-fold OOS threshold validation başarıyla çalıştı. OOS 120 gözlemde signal dağılımı min 2.580, p25 11.625, median 16.478, mean 16.524, p75 21.171, max 33.904 oldu.

Aday eşiklerin tamamında BUY coverage 0% seviyesinde kaldı; SELL<=30 / BUY>=70 eşiğinde yalnızca 1 HOLD ve 119 SELL gözlemi oluştu. Daha yüksek SELL eşiklerinde tüm OOS gözlemleri SELL'e düştü. Bu nedenle THYAO sonucu herhangi bir BUY/HOLD/SELL threshold seçimini desteklemiyor.

**Karar:** THYAO threshold sonucu descriptive validation olarak kaydedildi; winner seçilmedi. Signal ölçeğinin mevcut OOS dağılımı ile klasik 30/70, 35/65, 40/60, 45/55 eşikleri uyumlu görünmüyor. Multi-symbol threshold validation devam edecek; global eşik kararı henüz alınmayacak.

### Faz 5 Threshold Validation — AFA Güncel Smoke

Düzeltilmiş 0–100 raw signal foundation ile AFA üzerinde gerçek 3-fold OOS threshold validation başarıyla çalıştı. OOS 120 gözlemde signal dağılımı min 11.744, p25 28.904, median 30.997, mean 30.621, p75 33.449, max 48.242 oldu.

Aday eşikler descriptive olarak:
- SELL<=30 / BUY>=70: BUY 0 (0.0%), HOLD 77 (64.2%), SELL 43 (35.8%); BUY target N/A; SELL target 0.372.
- SELL<=35 / BUY>=65: BUY 0 (0.0%), HOLD 24 (20.0%), SELL 96 (80.0%); BUY target N/A; SELL target 0.229.
- SELL<=40 / BUY>=60: BUY 0 (0.0%), HOLD 10 (8.3%), SELL 110 (91.7%); BUY target N/A; SELL target 0.209.
- SELL<=45 / BUY>=55: BUY 0 (0.0%), HOLD 2 (1.7%), SELL 118 (98.3%); BUY target N/A; SELL target 0.195.

**Karar:** AFA da BUY coverage `0%` kaldı ve aday eşikler yalnızca HOLD/SELL dağılımını değiştirdi. Bu sonuç herhangi bir threshold winner seçimini desteklemiyor. THYAO ile birlikte signal ölçeğinin semboller arasında belirgin biçimde aşağıda kümelendiğini gösteriyor. Multi-symbol validation devam edecek; global threshold kararı alınmayacak.

### Faz 5 Threshold Validation — AFT Güncel Smoke

Düzeltilmiş 0–100 raw signal foundation ile AFT üzerinde gerçek 3-fold OOS threshold validation başarıyla çalıştı. OOS 120 gözlemde signal dağılımı min 12.056, p25 22.545, median 27.375, mean 27.801, p75 32.020, max 54.051 oldu.

Aday eşikler descriptive olarak:
- SELL<=30 / BUY>=70: BUY 0 (0.0%), HOLD 44 (36.7%), SELL 76 (63.3%); BUY target N/A; SELL target 0.303.
- SELL<=35 / BUY>=65: BUY 0 (0.0%), HOLD 17 (14.2%), SELL 103 (85.8%); BUY target N/A; SELL target 0.282.
- SELL<=40 / BUY>=60: BUY 0 (0.0%), HOLD 6 (5.0%), SELL 114 (95.0%); BUY target N/A; SELL target 0.289.
- SELL<=45 / BUY>=55: BUY 0 (0.0%), HOLD 4 (3.3%), SELL 116 (96.7%); BUY target N/A; SELL target 0.302.

**Karar:** AFT'de de BUY coverage `0%` kaldı. AFA ve THYAO ile birlikte üç sembolde klasik BUY eşikleri hiç tetiklenmedi; ancak AFT'nin maksimum signal değeri AFA'dan yüksek olsa da 55 üzeri bölgeye çıkmadı. Bu sonuç threshold winner seçimini desteklemiyor. Multi-symbol validation devam edecek; global threshold kararı alınmayacak.

### Faz 5 Meta-Aggregation Outer OOS Değerlendirmesi

Gerçek 3-fold outer OOS meta-aggregation smoke testi **THYAO, AFA, ASELS ve TUPRS** üzerinde değerlendirildi. Meta model outer test foldlarına erişmedi; ancak her foldda meta training için yalnızca 40 inner OOF gözlemi bulunduğu için sonuçlar düşük örneklemli deney olarak ele alınmalıdır.

- **THYAO:** fixed raw ROC-AUC `0.5289`, PR-AUC `0.2269`; meta ROC-AUC `0.4292`, PR-AUC `0.1631`. Meta yaklaşımı bu örnekte geriledi.
- **AFA:** fixed raw ROC-AUC `0.2935`, PR-AUC `0.2221`; meta ROC-AUC `0.3377`, PR-AUC `0.1561`. ROC-AUC yükselirken PR-AUC geriledi.
- **ASELS:** fixed raw ROC-AUC `0.5514`, PR-AUC `0.3819`; meta ROC-AUC `0.6039`, PR-AUC `0.5211`. Bu örnekte meta yaklaşımı iyileşti.
- **TUPRS:** fixed raw ROC-AUC `0.5573`, PR-AUC `0.4687`; meta ROC-AUC `0.4968`, PR-AUC `0.4729`. ROC-AUC gerilerken PR-AUC yalnızca sınırlı arttı.

Foldlar arasındaki meta logistic katsayılarının yönleri de stabil değildir. THYAO ve TUPRS örneklerinde ML/technical/risk katsayılarının foldlar arasında yön değiştirmesi bu aggregation katmanının mevcut örneklemde kararlı olmadığını göstermektedir.

**Karar:** Meta-aggregation **production signal pipeline'ına alınmadı**. Deneysel foundation olarak kodda tutulacak; Phase 5 kapanışı için sabit/raw signal foundation kullanılacaktır. Bu karar meta yöntemin teknik olarak başarısız olduğu iddiası değil, mevcut outer OOS coverage ve fold instability ile production default seçmek için yeterli tutarlılık görülmediği anlamına gelir.

- [x] Meta-aggregation outer OOS sonuçlarını THYAO, AFA, ASELS ve TUPRS üzerinde değerlendirdi; production default olarak seçmedi.
- [ ] Düzeltilmiş 0–100 raw signal foundation üzerinde gerçek threshold validation sonuçlarını çoklu BIST/TEFAS OOS coverage ile yeniden çalıştır ve kaydet. THYAO ilk smoke tamamlandı; BUY coverage 0% ve mevcut aday eşikler uygun görünmedi.
- [ ] Baseline vs tuned model direction OOS karşılaştırmasını AFA ve THYAO üzerinde çalıştır; tuning'in ters yön davranışındaki etkisini ayır.
- [ ] Direction sonucu uygunsa target/model revizyonunu yalnızca validation evidence ile yap.
- [x] ASELS, TUPRS ve BIMAS target threshold direction diagnostic sonuçları çıkarıldı; direct/inverse yönler sembole göre değişiyor ve tek global threshold ile açıklanamıyor.
- [x] AFT canonical history bootstrap edildi (`683` rows) ve target threshold direction diagnostic tamamlandı: +1/+2/+3% direct yön pozitif, +5% ters yöne döndü.
- [x] Ham feature auditinde AFA/AFT/THYAO'da SMA/EMA/BB gibi fiyat-seviyesi özelliklerinin çoğunda negatif OOS korelasyon görülmesi üzerine level-normalization diagnostic eklendi; henüz production feature değişikliği yapılmadı.
- [x] AFT/ASELS/TUPRS/BIMAS raw-vs-normalized model OOS karşılaştırmaları tamamlandı; normalize yaklaşım AFT/ASELS/TUPRS'da aggregate ROC/PR açısından genel üstünlük göstermedi, BIMAS'ta mixed davranış gösterdi. Bu nedenle normalize model henüz production default seçilmedi.
- [x] Normalized model diagnostic import bağımlılığı self-contained hale getirildi; `PRICE_LEVEL_FEATURES` rename/import hatası düzeltildi ve volume/price normalization dönüşümleri ortak helper kopyasıyla hizalandı.
- [x] Normalized diagnostics içinde fold Spearman index alignment ve `volume_sma_20` self-normalization kusurları düzeltildi; MACD/momentum gibi price-difference özelliklerinin de doğru şekilde fiyatla ölçeklenmesi için diagnostic dönüşümü ayrıştırıldı.
- [ ] Düzeltilmiş normalized feature/model audit'i AFA/AFT/THYAO/AFT/ASELS/TUPRS/BIMAS coverage'ında çalıştır; price-level, price-difference ve volume-level dönüşümleri aynı contract üzerinden doğrula.

- [x] Faz 5 acceptance testleri çalıştırıldı: `PYTHONPATH=. pytest tests/ml/test_phase5_acceptance.py -q` → **3 passed**.
- [x] Tüm ML test suite çalıştırıldı: `PYTHONPATH=. pytest tests/ml -q` → **75 passed in 6.15s**.

## Sıradaki İş

1. Düzeltilmiş 0–100 raw signal foundation üzerinde çoklu BIST/TEFAS gerçek OOS threshold validation'ı çalıştır; BUY/HOLD/SELL eşiklerini henüz kazanan olarak seçme.
2. Baseline vs tuned model direction OOS karşılaştırmasını AFA ve THYAO üzerinde değerlendir; tuning'in ters yön davranışına etkisini ayır.
3. Direction sonucu gerekiyorsa target/model revizyonunu yalnızca validation evidence ile ve outer test seçimi yapmadan deneysel olarak değerlendir.
4. Representation selection'ı production'a almadan önce gerekirse inner walk-forward içine raw_all / normalized_all / stationary_core seçimini leakage-safe candidate olarak dahil et.
5. Threshold ve gerçek signal-chain sonuçlarını `docs/phase-5-tuning-evaluation.md` veya ilgili Phase 5 raporuna kaydet.
6. Phase 5 gerçek signal-chain kapanışını doğrula.
7. Phase 5 tamamlandıktan sonra Phase 6'ya geç.

## Yeni Sohbette Devam Etme Kuralı

Yeni bir sohbette projeye devam ederken bu dosya önce okunmalı. Özellikle **Güncel Durum**, **Tamamlananlar**, **aktif fazın taskları** ve **Sıradaki İş** bölümleri esas alınmalı.

> Kural: Her faz tamamlandığında kısa özet, alınan teknik/ürün kararları, tamamlanan tasklar ve sıradaki faz/tasklar burada tutulur.
