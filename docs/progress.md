# Proje İlerleme Kaydı

Bu dosya, fazlarda alınan kararların, tamamlanan işlerin ve sıradaki taskların kısa özetini tutar. Yeni bir sohbette projeye devam ederken önce bu dosya referans alınmalıdır.

## Güncel Durum

- Aktif faz: **Faz 5 — Model Tuning / Feature Importance / Signal-Risk Foundation**
- Son tamamlanan faz: **Faz 4 — ML Baseline / XGBoost**
- Faz 5'te tuning, feature representation, direction, threshold ve signal-risk validation deneyleri sürüyor.

## Faz 2 — Data Infrastructure — TAMAMLANDI

- BIST ve TEFAS provider, normalization, validation, persistence, quality ve streaming altyapısı tamamlandı.
- Gerçek BIST full-universe coverage: 516/516 quote.
- Gerçek TEFAS full universe: 2040/2040 fon.
- Historical + live PostgreSQL persistence, duplicate/upsert ve E2E pipeline doğrulandı.

## Faz 3 — Technical Analysis Engine — TAMAMLANDI

- Stock/fund indicator engine, Technical Score Engine ve ML feature dataset builder tamamlandı.
- Warm-up, look-ahead ve leakage kontrolleri tamamlandı.
- Analysis test suite: 18 passed.

## Faz 4 — ML Baseline / XGBoost — TAMAMLANDI

- Leakage-aware expanding walk-forward splitter, gap >= 5, XGBoost baseline wrapper ve metrikler tamamlandı.
- Gerçek BIST smoke coverage: THYAO, ASELS, TUPRS, BIMAS.
- Gerçek TEFAS smoke coverage: AFA, AFT, AFS.
- AAL one-class training problemi doğrulandı; validation gevşetilmedi.
- Faz 4 acceptance: 3 passed.

## Faz 5 — Model Tuning / Feature Importance / Signal-Risk Foundation — AKTİF

### Güncel Bulgular

- Inner walk-forward tuning, feature importance, calibration, risk adjustment ve signal foundation tamamlandı.
- Feature representation ablation altı sembolde tamamlandı; raw_all / normalized_all / stationary_core candidate olarak korunuyor, production contract sessizce değiştirilmedi.
- 6-symbol direction diagnostic tamamlandı. ML probability için 3 direct / 3 inverse; Technical Score için ROC yönünde 4 inverse / 2 direct görüldü. Global production inversion seçilmedi.
- 6-symbol threshold smoke coverage tamamlandı. Global BUY/HOLD/SELL threshold winner seçilmedi; raw signal ölçeği semboller arasında belirgin biçimde değişiyor.
- Meta-aggregation outer OOS deneysel olarak değerlendirildi; fold instability nedeniyle production default seçilmedi.
- Phase 5 acceptance: 3 passed; tüm ML test suite: 75 passed in 6.15s.

### Faz 5 Baseline vs Tuned Direction — AFA

Canonical PostgreSQL history ile gerçek 3-fold / 120 OOS baseline-vs-tuned direction comparison tamamlandı.

**AFA — 674 raw rows, 470 training rows, 120 OOS rows, target rate 0.208**

- Fold 1: baseline direct ROC 0.4323, PR 0.3539; inverse ROC 0.5677, PR 0.4227. Tuned direct ROC 0.4479, PR 0.3848; inverse ROC 0.5521, PR 0.4768.
- Fold 2: baseline direct ROC 0.6319, PR 0.4759; inverse ROC 0.3681, PR 0.1091. Tuned direct ROC 0.7083, PR 0.5720; inverse ROC 0.2917, PR 0.0889.
- Fold 3: baseline direct ROC 0.3714, PR 0.1130; inverse ROC 0.6286, PR 0.1845. Tuned direct ROC 0.4914, PR 0.1428; inverse ROC 0.5086, PR 0.2103.

**AFA Aggregate OOS**

- Baseline: direct ROC 0.3398, PR 0.2137; inverse ROC 0.6602, PR 0.2959.
- Tuned: direct ROC 0.3587, PR 0.2324; inverse ROC 0.6413, PR 0.3402.

**Karar:** Tuning AFA'da bazı performans metriklerini iyileştirdi ancak direction davranışını çözmedi. Aggregate direct ROC 0.3587 < inverse 0.6413; foldlar heterojen.

### Faz 5 Baseline vs Tuned Direction — THYAO

Canonical stock history yetersiz olduğu için Borsapy provider fallback kullanıldı. Gerçek 3-fold / 120 OOS comparison tamamlandı.

**THYAO — 685 raw rows, 481 training rows, 120 OOS rows, target rate 0.158**

- Fold 1: baseline direct ROC 0.4502, PR 0.3554; inverse ROC 0.5498, PR 0.2654. Tuned direct ROC 0.5108, PR 0.3712; inverse ROC 0.4892, PR 0.2216.
- Fold 2: baseline direct ROC 0.4695, PR 0.2431; inverse ROC 0.5305, PR 0.3308. Tuned direct ROC 0.3763, PR 0.1929; inverse ROC 0.6237, PR 0.3060.
- Fold 3: baseline direct ROC 0.9189, PR 0.4250; inverse ROC 0.0811, PR 0.0543. Tuned direct ROC 0.9189, PR 0.6000; inverse ROC 0.0811, PR 0.0538.

**THYAO Aggregate OOS**

- Baseline: direct ROC 0.5597, PR 0.2883, Spearman 0.0755; inverse ROC 0.4403, PR 0.1894.
- Tuned: direct ROC 0.5638, PR 0.2731, Spearman 0.0807; inverse ROC 0.4362, PR 0.1500.

**Karar:** Tuning THYAO'da aggregate ROC-AUC'yi çok sınırlı artırdı; PR-AUC 0.2883 -> 0.2731 düştü. Aggregate direction direct kaldı. Production direction değiştirilmedi.

### Faz 5 Nested Representation Selection — Altyapı

- `backend/scripts/smoke_test_representation_nested_real.py` oluşturuldu.
- Candidate representations: `raw_all`, `normalized_all`, `stationary_core`.
- Production target contract sabit tutuluyor: horizon=5, threshold=+3%.
- Her outer fold için representation yalnızca outer-train içindeki 2-fold inner walk-forward sonuçlarından seçiliyor; her representation kendi inner XGBoost tuning'inden geçiriliyor.
- En az 2 valid inner fold kuralı korunuyor; PR-AUC primary, ROC-AUC ve fold PR std secondary criteria.
- Seçilen representation yalnızca ilgili outer fold üzerinde OOS değerlendiriliyor.
- Bu aşamada production representation değiştirilmedi; gerçek AFA/THYAO smoke sonuçları bekleniyor.

### Faz 5 Nested Representation Selection — Inner Tuning Teşhis Logu

- AFA rerun'da veri hazırlama yine başarılı: 674 raw, 470 dataset rows.
- `_score_representation` çağrı sözleşmesi düzeltildikten sonra selection aşamasında tüm representation adaylarının en az 2 valid inner fold şartını geçemediği tekrar görüldü.
- Nested scriptte `select_best_candidate` kaynaklı `ValueError` daha önce sessizce `continue` edildiği için gerçek eleme nedeni görünmüyordu.
- Teşhis amacıyla inner fold boyutları, train/validation positive rate ve yakalanan `ValueError` artık loglanıyor. Bu değişiklik metodolojiyi gevşetmiyor; yalnızca hangi inner tuning koşulunun adayları elediğini görünür kılıyor.
- Commit: `f099e436deb90d46ffc0310acb2ee8ad205d44e8`.
- Bu aşamada production representation `raw_all` olarak korunuyor; yeni gerçek AFA sonucu henüz alınmadı.

### Faz 5 Nested Representation Selection — İkinci Kod Hatası Düzeltmesi

- AFA rerun sonrası `TypeError: _score_representation() got an unexpected keyword argument 'columns'` görüldü.
- Kod incelemesinde önceki düzeltmenin çağrı tarafına `columns` eklediği ancak fonksiyon gövdesinin parametre imzasının eksik kaldığı ve ayrıca `prepared/frame` isimlerinin tutarsız olduğu doğrulandı.
- Düzeltme: `_score_representation` artık `prepared` ve `columns: tuple[str, ...]` parametrelerini açıkça kabul ediyor; walk-forward ve dropna işlemleri bu hazırlanmış frame/column seti üzerinde yürütülüyor.
- Düzeltme commit: `ef98ac8c020727d96e80c15effdf07000115ee25`.
- AFA nested representation gerçek sonucu henüz alınmadı; production representation `raw_all` olarak korunuyor.

### Faz 5 Nested Representation Selection — İlk AFA Çalıştırması ve Düzeltme

- AFA nested representation smoke PostgreSQL canonical history ile veri hazırlama aşamasını geçti: 674 raw rows, 470 dataset rows.
- İlk çalıştırmada `_select_representation` tüm adaylarda `valid_folds < 2` gördü ve `no representation has the required number of valid inner folds` hatası verdi.
- İnceleme sonucunda representation'ın outer-train için zaten hazırlanmış frame'inin `_score_representation` içinde ikinci kez `_prepare_variant` ile hazırlanması tespit edildi. Özellikle normalized/stationary varyantlarda bu, nested seçim frame'inin yanlışlıkla yeniden dönüştürülmesine neden olabiliyordu.
- Düzeltme: `_score_representation` artık kendisine verilen hazırlanmış frame ve açık feature-column seti üzerinde çalışıyor; representation varyantı ikinci kez uygulanmıyor.
- Düzeltme commit: `770f772d3cda1d20708e30a1716e7f1168fc631e`.
- Production representation hâlâ `raw_all`; AFA gerçek nested sonuçları henüz değerlendirilmedi.

### Faz 5 Nested Target-Contract Selection — Düzeltilmiş Gerçek Çalıştırma

Selection stability düzeltmesinden sonra AFA ve THYAO nested smoke tekrar çalıştırıldı. Candidate selection artık yalnızca en az 2 valid inner fold'a sahip adaylar arasından yapılıyor; PR-AUC primary objective, ROC-AUC ve fold PR std secondary criteria. Class balance raporlanıyor ancak keyfi bir hedef orana göre optimize edilmiyor.

**AFA — PostgreSQL canonical history, 674 raw rows**

- Outer 1: h=5, threshold=1%; inner PR 0.4419, ROC 0.7578, PR std 0.1373, positive 0.200, direction 100%, valid folds 2.
- Outer 2: h=5, threshold=1%; inner PR 0.7127, ROC 0.5463, PR std 0.0855, positive 0.625, direction 50%, valid folds 2.
- Outer 3: h=10, threshold=3%; inner PR 0.9037, ROC 0.7679, PR std 0.0963, positive 0.375, direction 100%, valid folds 2.
- Outer fold sonuçları: fold 1 h=5/+1% ROC 0.4258 / PR 0.6247 / Spearman -0.1226; fold 2 h=5/+1% ROC 0.5514 / PR 0.5209 / Spearman +0.0889; fold 3 h=10/+3% ROC 0.3354 / PR 0.2513 / Spearman -0.2546.
- AFA selection tek bir contract üzerinde sabit kalmadı; ilk iki fold +1%, son fold +3% seçildi. Inner skorların outer OOS'a aynı ölçüde taşınmadığı görüldü.
- Bu nedenle AFA sonucu production target değişimi için yeterli değildir.

**THYAO — Borsapy provider fallback, 685 raw rows**

- Outer 1: h=10, threshold=1%; inner PR 0.7033, ROC 0.4825, PR std 0.0097, positive 0.525, direction 50%, valid folds 2.
- Outer 2: h=5, threshold=1%; inner PR 0.7282, ROC 0.6836, PR std 0.1646, positive 0.375, direction 50%, valid folds 2.
- Outer 3: h=10, threshold=1%; inner PR 0.5567, ROC 0.3737, PR std 0.0023, positive 0.550, direction 50%, valid folds 2.
- Outer fold sonuçları: fold 1 h=10/+1% ROC 0.5556 / PR 0.4393 / Spearman +0.0902; fold 2 h=5/+1% ROC 0.4036 / PR 0.3459 / Spearman -0.1636; fold 3 h=10/+1% ROC 0.9737 / PR 0.7500 / Spearman +0.3577.
- THYAO'da threshold +1% üç fold'un tamamında seçildi ancak horizon 5/10 arasında değişti ve outer sonuçlar belirgin heterojen kaldı.
- Fold 3'te %5 pozitif oranı ile ROC 0.9737 / PR 0.7500 gözlenmesi örneklem/regime etkisinin güçlü olabileceğini gösteriyor; tek fold üzerinden contract seçimi yapılmadı.

**Nested selection kararı:**
- En az 2 valid inner fold kuralı gerekli ve korunuyor.
- AFA + THYAO sonuçları ortak, stable bir horizon/threshold contract göstermiyor.
- Mevcut production contract **horizon=5, threshold=+3%** olarak korunuyor.
- Nested çalışma, target contract'ın sembol/fold rejimine duyarlı olabileceğini gösteren deneysel kanıt olarak kaydedildi; production değişikliği olarak kabul edilmedi.

### Faz 5 Target Threshold Direction — AFA

Aynı leakage-safe chronological outer protokolü ile mevcut target diagnostic çalıştırıldı. Bu çalışma **descriptive diagnostic** olarak değerlendirildi; production target seçimi yapılmadı.

**AFA — PostgreSQL canonical history, 674 raw rows, 470 feature rows**

| Target | Positive rate | Baseline ROC | Baseline PR | Tuned ROC | Tuned PR | Baseline direct Spearman |
|---|---:|---:|---:|---:|---:|---:|
| >1% | 42.6% | 0.5172 | 0.5291 | 0.5159 | 0.5061 | +0.0298 |
| >2% | 22.3% | 0.4660 | 0.2992 | 0.4109 | 0.2630 | -0.0544 |
| >3% | 13.4% | 0.3398 | 0.2137 | 0.3587 | 0.2324 | -0.2254 |
| >5% | 5.7% | 0.5446 | 0.1603 | 0.7319 | 0.1139 | +0.0446 |

- AFA'da threshold değişimi direction davranışını belirgin biçimde değiştiriyor: baseline direct Spearman +0.0298 -> -0.0544 -> -0.2254 -> +0.0446.
- >3% mevcut contract'ta aggregate inverse ROC 0.6602; >5% tuned direct ROC 0.7319 olsa da PR 0.1139 ve positive rate yalnızca 5.7%.
- Bu sonuçlar outer OOS candidate selection için kullanılmamalıdır; yalnızca target definition'ın model davranışını ciddi biçimde etkilediğini gösteren diagnostic kanıttır.

### Faz 5 Target Threshold Direction — THYAO

**THYAO — Borsapy provider fallback, 685 raw rows, 481 feature rows**

| Target | Positive rate | Baseline ROC | Baseline PR | Tuned ROC | Tuned PR | Baseline direct Spearman |
|---|---:|---:|---:|---:|---:|---:|
| >1% | 39.7% | 0.5169 | 0.3722 | 0.4793 | 0.3602 | +0.0275 |
| >2% | 28.9% | 0.5977 | 0.3568 | 0.5612 | 0.3288 | +0.1353 |
| >3% | 22.0% | 0.5597 | 0.2883 | 0.5638 | 0.2731 | +0.0755 |
| >5% | 13.3% | 0.5665 | 0.3463 | 0.5133 | 0.2637 | +0.0716 |

- THYAO'da baseline direct direction dört threshold'un tamamında pozitif Spearman tarafında kaldı.
- >2% baseline ROC 0.5977 ile >3% baseline ROC 0.5597'nin üzerinde olsa da bu outer OOS candidate selection için kullanılmadı.
- AFA ile THYAO birlikte değerlendirildiğinde ortak bir threshold/direction sonucu çıkmıyor.

**Karar:** Target threshold'un direction ve class balance üzerinde güçlü etkisi doğrulandı; ancak iki sembolde ortak production target seçimi için yeterli leakage-safe evidence yok. Mevcut production contract **horizon=5, threshold=+3%** olarak korunuyor.

### Faz 5 Nested Target-Contract Selection — İlk Gerçek Çalıştırma

İlk nested smoke AFA ve THYAO üzerinde çalıştırıldı. Candidate selection inner tuned validation ile yapıldı; seçilen candidate yalnızca ilgili outer foldda değerlendirildi.

**AFA**
- Outer 1: h=10, threshold=2%; inner PR 1.0000, ROC 1.0000, ancak yalnızca 1 valid inner fold.
- Outer 2: h=10, threshold=1%; inner PR 0.9648, ROC 0.4737, 1 valid inner fold.
- Outer 3: h=10, threshold=3%; inner PR 0.9037, ROC 0.7679, 2 valid inner fold.
- Outer results: fold 1 ROC 0.4734 / PR 0.7607; fold 2 ROC 0.5000 / PR 0.5074; fold 3 ROC 0.3354 / PR 0.2513.
- Bu ilk koşu production target seçimi için kabul edilmedi. Özellikle 1 valid inner fold üzerinden PR 1.0000 gibi skorların candidate seçimine girebilmesi selection stability açısından yetersiz bulundu.

**THYAO**
- Outer 1: h=10, threshold=1%; inner PR 0.7033, ROC 0.4825, 2 valid fold.
- Outer 2: h=5, threshold=1%; inner PR 0.7282, ROC 0.6836, 2 valid fold.
- Outer 3: h=10, threshold=1%; inner PR 0.5567, ROC 0.3737, 2 valid fold.
- Outer results: fold 1 ROC 0.5556 / PR 0.4393; fold 2 ROC 0.4036 / PR 0.3459; fold 3 ROC 0.9737 / PR 0.7500.
- THYAO'da threshold +1% üç outer selection'ın tamamında görüldü; horizon 5/10 arasında değişti. Ancak outer fold sonuçları heterojen olduğundan production contract değiştirilmedi.

**Selection metodolojisi düzeltmesi**
- Candidate selection artık en az 2 valid inner fold gerektiriyor.
- 1 valid fold üzerinden gelen adaylar selection'dan çıkarılıyor.
- Class balance raporlanıyor fakat keyfi bir target rate'a (ör. %20) doğru optimize edilmiyor.
- PR-AUC primary objective; ROC-AUC ve fold PR standard deviation secondary criteria.
- Bu düzeltmeden sonra AFA ve THYAO nested smoke yeniden çalıştırılmalıdır.

### Faz 5 Taskları

- [x] Tuning dataset / inner-validation foundation oluştur.
- [x] XGBoost hyperparameter candidate search katmanı oluştur.
- [x] Baseline vs tuned modelleri aynı outer walk-forward protokolünde karşılaştır.
- [x] Feature importance / gain raporlama foundation'ı oluştur.
- [x] Model probability calibration ihtiyacını değerlendir.
- [x] Risk adjustment foundation'ını uygula ve unit testlerini ekle.
- [x] Signal foundation ve deterministic BUY/HOLD/SELL rules oluştur.
- [x] Leakage-safe signal scaling ve threshold smoke validationlarını çalıştır.
- [x] 6-symbol direction diagnostic tamamlandı; global direct/inverse production yönü seçilmedi.
- [x] AFA baseline vs tuned direction OOS karşılaştırması tamamlandı.
- [x] THYAO baseline vs tuned direction OOS karşılaştırması tamamlandı.
- [x] Tuning'in direction davranışına etkisi AFA + THYAO üzerinde ayrıştırıldı; global direction değişikliği yapılmadı.
- [x] Target threshold direction diagnostic AFA + THYAO tamamlandı.
- [ ] Target/model contract revizyonunu yalnızca leakage-safe inner validation evidence ile deneysel değerlendir.\n- [x] Nested target-contract selection smoke altyapısı oluşturuldu; 12 candidate (horizon 3/5/10 × threshold 1/2/3/5%) inner tuned validation ile seçiliyor ve outer evaluation yalnızca seçilen candidate'ın ilgili foldunda yapılıyor.
- [ ] Düzeltilmiş normalized feature/model audit'ini ilgili coverage üzerinde çalıştır.
- [x] Faz 5 acceptance testleri: 3 passed.
- [x] Tüm ML test suite: 75 passed in 6.15s.

## Sıradaki İş

1. **Nested target-contract selection:** oluşturulan `backend/scripts/smoke_test_target_contract_nested_real.py` ile gerçek AFA/THYAO sonuçlarını çalıştır; candidate selection inner tuned validation'da, outer evaluation yalnızca seçilen fold/candidate üzerinde. Aday threshold'lar +1%, +2%, +3%, +5%; horizon adayları 3, 5, 10 gözlem. Outer test yalnızca seçilmiş contract'ın final değerlendirmesinde kullanılmalı.
2. Selection objective olarak yalnızca ROC-AUC kullanılmamalı; PR-AUC, class balance ve fold stability birlikte raporlanmalı.
3. Seçilen contract için outer OOS sonucu yalnızca final evaluation olarak raporlanmalı; candidate seçimi sırasında outer OOS görülmemeli.
4. Representation selection'ı ayrıca raw_all / normalized_all / stationary_core seçenekleriyle inner walk-forward candidate olarak değerlendir; outer test foldunu seçimde kullanma.
5. Threshold ve gerçek signal-chain sonuçlarını ilgili Phase 5 raporuna kaydet; global BUY/HOLD/SELL winner seçme.
6. Phase 5 gerçek signal-chain kapanışını doğrula.
7. Phase 5 tamamlandıktan sonra Phase 6'ya geç.

## Yeni Sohbette Devam Etme Kuralı

Yeni bir sohbette projeye devam ederken bu dosya önce okunmalı. Özellikle **Güncel Durum**, **Tamamlananlar**, **aktif fazın taskları** ve **Sıradaki İş** bölümleri esas alınmalı.

> Kural: Her faz tamamlandığında kısa özet, alınan teknik/ürün kararları, tamamlanan tasklar ve sıradaki faz/tasklar burada tutulur.
