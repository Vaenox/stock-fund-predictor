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
