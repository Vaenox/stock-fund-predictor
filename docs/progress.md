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


### Faz 5 Threshold Smoke — İlk Deneme

İlk threshold smoke sonuçlarında THYAO ve AFA'da tüm 120 OOS gözlem SELL sınıfına düşerken ASELS/TUPRS/BIMAS/AFT'te BUY coverage çoğunlukla `0%` veya `1.7%` seviyesinde kaldı. Bu sonuçlar eşik seçimi olarak kaydedilmedi. İncelemede signal foundation'ın pre-risk teorik üst sınırının `80` olduğu görüldü; formula düzeltildi ve threshold validation yeniden çalıştırılacak.

### Faz 5 Meta-Aggregation Outer OOS Değerlendirmesi

Gerçek 3-fold outer OOS meta-aggregation smoke testi **THYAO, AFA, ASELS ve TUPRS** üzerinde değerlendirildi. Meta model outer test foldlarına erişmedi; ancak her foldda meta training için yalnızca 40 inner OOF gözlemi bulunduğu için sonuçlar düşük örneklemli deney olarak ele alınmalıdır.

- **THYAO:** fixed raw ROC-AUC `0.5289`, PR-AUC `0.2269`; meta ROC-AUC `0.4292`, PR-AUC `0.1631`. Meta yaklaşımı bu örnekte geriledi.
- **AFA:** fixed raw ROC-AUC `0.2935`, PR-AUC `0.2221`; meta ROC-AUC `0.3377`, PR-AUC `0.1561`. ROC-AUC yükselirken PR-AUC geriledi.
- **ASELS:** fixed raw ROC-AUC `0.5514`, PR-AUC `0.3819`; meta ROC-AUC `0.6039`, PR-AUC `0.5211`. Bu örnekte meta yaklaşımı iyileşti.
- **TUPRS:** fixed raw ROC-AUC `0.5573`, PR-AUC `0.4687`; meta ROC-AUC `0.4968`, PR-AUC `0.4729`. ROC-AUC gerilerken PR-AUC yalnızca sınırlı arttı.

Foldlar arasındaki meta logistic katsayılarının yönleri de stabil değildir. THYAO ve TUPRS örneklerinde ML/technical/risk katsayılarının foldlar arasında yön değiştirmesi bu aggregation katmanının mevcut örneklemde kararlı olmadığını göstermektedir.

**Karar:** Meta-aggregation **production signal pipeline'ına alınmadı**. Deneysel foundation olarak kodda tutulacak; Phase 5 kapanışı için sabit/raw signal foundation kullanılacaktır. Bu karar meta yöntemin teknik olarak başarısız olduğu iddiası değil, mevcut outer OOS coverage ve fold instability ile production default seçmek için yeterli tutarlılık görülmediği anlamına gelir.

- [x] Meta-aggregation outer OOS sonuçlarını THYAO, AFA, ASELS ve TUPRS üzerinde değerlendirdi; production default olarak seçmedi.
- [ ] Düzeltilmiş 0–100 raw signal foundation üzerinde gerçek threshold validation sonuçlarını çoklu BIST/TEFAS OOS coverage ile yeniden çalıştır ve kaydet.
- [ ] Baseline vs tuned model direction OOS karşılaştırmasını AFA ve THYAO üzerinde çalıştır; tuning'in ters yön davranışındaki etkisini ayır.
- [ ] Direction sonucu uygunsa target/model revizyonunu yalnızca validation evidence ile yap.
- [ ] Faz 5 acceptance testlerini çalıştır ve PASS doğrula.

## Sıradaki İş

1. `tests/ml/test_signal_scaling.py` ve `tests/ml` suite sonuçlarını doğrula.
2. `scripts/smoke_test_signal_scaling_real.py` ile leakage-safe scaling validation'ı THYAO ve AFA üzerinde çalıştır.
3. Raw vs scaled signal dağılımlarını ve threshold coverage'ı karşılaştır.
4. Quantile vs empirical-percentile scaling gerçek OOS sonuçlarını karşılaştır; henüz production yöntemi seçme.
5. Score monotonicity ve component association diagnostic sonuçlarını çıkar.
6. Bileşenlerin OOS bin davranışlarını THYAO/AFA dışındaki sembollerle doğrula.
7. Directionality yeterli değilse threshold yerine ML target/model veya technical/risk scoring tasarımını düzelt.
8. Meta-aggregation dış OOS sonuçlarını değerlendir; production default seçme kararı alındı.
9. Sabit/raw signal foundation için çoklu sembol threshold validation çalıştır.
10. Sonuçları `docs/phase-5-tuning-evaluation.md` veya ilgili Phase 5 raporuna kaydet.
11. Faz 5 acceptance ve gerçek signal zinciri kapanış testlerini çalıştır.
12. Baseline vs tuned model direction diagnostic'i değerlendir.
13. Target/model revizyonu gerekiyorsa validation-only deneyini çalıştır; production target değişikliğini outer test ile seçme.
14. Faz 5 acceptance ve gerçek signal zinciri kapanış testlerini çalıştır.
15. Ardından Phase 5'i kapatıp Phase 6'ya geç.

## Yeni Sohbette Devam Etme Kuralı

Yeni bir sohbette projeye devam ederken bu dosya önce okunmalı. Özellikle **Güncel Durum**, **Tamamlananlar**, **aktif fazın taskları** ve **Sıradaki İş** bölümleri esas alınmalı.

> Kural: Her faz tamamlandığında kısa özet, alınan teknik/ürün kararları, tamamlanan tasklar ve sıradaki faz/tasklar burada tutulur.
