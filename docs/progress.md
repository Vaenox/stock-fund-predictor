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

### Güncel Faz 5 Bulguları

- Inner walk-forward tuning, feature importance, calibration, risk adjustment ve signal foundation tamamlandı.
- Feature representation ablation altı sembolde tamamlandı; raw_all / normalized_all / stationary_core candidate olarak korunuyor, production contract sessizce değiştirilmedi.
- 6-symbol direction diagnostic tamamlandı. ML probability için 3 direct / 3 inverse; Technical Score için ROC yönünde 4 inverse / 2 direct gözlendi. Global production inversion seçilmedi.
- 6-symbol threshold smoke coverage tamamlandı. Global BUY/HOLD/SELL threshold winner seçilmedi; raw signal ölçeği semboller arasında belirgin biçimde değişiyor.
- Meta-aggregation outer OOS deneysel olarak değerlendirildi; fold instability nedeniyle production default seçilmedi.
- Phase 5 acceptance: `3 passed`; tüm ML test suite: `75 passed in 6.15s`.

### Faz 5 THYAO Outer Comparison

- Fold 1: baseline ROC `0.2157`, PR `0.1246`; tuned ROC `0.2549`, PR `0.1310`.
- Fold 2: test fold tek sınıflı; ROC/PR iki model için de `None`.
- Fold 3: baseline ROC `0.8947`, PR `0.3333`; tuned ROC `0.9474`, PR `0.5000`.
- Bu tek sembol sonucunda tuning iki ölçülebilir outer fold'da ROC-AUC ve PR-AUC'yi yükseltti; genellenebilirlik sonucu çıkarılmadı.

### Faz 5 Baseline vs Tuned Direction — AFA

Canonical PostgreSQL history ile gerçek 3-fold / 120 OOS baseline-vs-tuned direction comparison tamamlandı.

**AFA — 674 raw rows, 470 training rows, 120 OOS rows, target rate 0.208**

- **Fold 1:** baseline direct ROC `0.4323`, PR `0.3539`, Spearman `-0.1149`; inverse ROC `0.5677`, PR `0.4227`, Spearman `0.1149`. Tuned direct ROC `0.4479`, PR `0.3848`, Spearman `-0.0884`; inverse ROC `0.5521`, PR `0.4768`, Spearman `0.0884`.
- **Fold 2:** baseline direct ROC `0.6319`, PR `0.4759`, Spearman `0.1372`; inverse ROC `0.3681`, PR `0.1091`, Spearman `-0.1372`. Tuned direct ROC `0.7083`, PR `0.5720`, Spearman `0.2166`; inverse ROC `0.2917`, PR `0.0889`, Spearman `-0.2166`.
- **Fold 3:** baseline direct ROC `0.3714`, PR `0.1130`, Spearman `-0.1473`; inverse ROC `0.6286`, PR `0.1845`, Spearman `0.1473`. Tuned direct ROC `0.4914`, PR `0.1428`, Spearman `-0.0098`; inverse ROC `0.5086`, PR `0.2103`, Spearman `0.0098`.

**Aggregate OOS**
- Baseline: direct ROC `0.3398`, PR `0.2137`, Spearman `-0.2254`; inverse ROC `0.6602`, PR `0.2959`, Spearman `0.2254`.
- Tuned: direct ROC `0.3587`, PR `0.2324`, Spearman `-0.1987`; inverse ROC `0.6413`, PR `0.3402`, Spearman `0.1987`.

**Karar:** Tuning AFA'da aggregate direct ROC-AUC/PR-AUC'yi bir miktar yükseltti; inverse gösterimde de PR-AUC yükseldi. Ancak tuning direct/inverse yönü değiştirmedi: aggregate direct ROC `0.3587` < inverse `0.6413`. Foldlar yön açısından heterojen; Fold 2 direct, Fold 1 ve Fold 3 inverse yönde daha yüksek ayrıştırma gösteriyor. Bu nedenle tuning ters yön davranışının kök nedeni olarak görülmüyor ve production direction değiştirilmedi.

### Faz 5 Threshold Validation — 6 Symbol Aggregate Observation

- **THYAO:** p25 11.625, median 16.478, p75 21.171, min 2.580, max 33.904.
- **AFA:** p25 28.904, median 30.997, p75 33.449, min 11.744, max 48.242.
- **AFT:** p25 22.545, median 27.375, p75 32.020, min 12.056, max 54.051.
- **ASELS:** p25 26.041, median 36.524, p75 49.179, min 7.881, max 72.313.
- **TUPRS:** p25 24.539, median 28.651, p75 33.231, min 11.633, max 65.288.
- **BIMAS:** p25 28.267, median 33.693, p75 47.759, min 17.006, max 71.204.

**Karar:** Klasik global 30/70, 35/65, 40/60, 45/55 eşikleri ortak ve dengeli BUY/HOLD/SELL coverage üretmiyor. Descriptive sonuçlara dayanarak percentile/rank production default seçilmiyor; gerekirse inner walk-forward içinde leakage-safe representation selection yapılmalı.

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
- [ ] Baseline vs tuned model direction OOS karşılaştırmasını **THYAO** üzerinde çalıştır.
- [ ] Direction sonucu uygunsa target/model revizyonunu yalnızca validation evidence ile yap.
- [ ] Düzeltilmiş normalized feature/model audit'ini ilgili coverage üzerinde çalıştır.
- [x] Faz 5 acceptance testleri: `3 passed`.
- [x] Tüm ML test suite: `75 passed in 6.15s`.

## Sıradaki İş

1. **THYAO baseline vs tuned direction OOS karşılaştırmasını çalıştır.**
2. THYAO sonucunu AFA ile birlikte değerlendir; tuning'in direction davranışına etkisini ayır.
3. Gerekirse target/model revizyonunu yalnızca validation evidence ile ve outer test seçimi yapmadan deneysel olarak değerlendir.
4. Gerekirse raw_all / normalized_all / stationary_core representation selection'ı inner walk-forward içine leakage-safe candidate olarak dahil et.
5. Threshold ve gerçek signal-chain sonuçlarını ilgili Phase 5 raporuna kaydet.
6. Phase 5 gerçek signal-chain kapanışını doğrula.
7. Phase 5 tamamlandıktan sonra Phase 6'ya geç.

## Yeni Sohbette Devam Etme Kuralı

Yeni bir sohbette projeye devam ederken bu dosya önce okunmalı. Özellikle **Güncel Durum**, **Tamamlananlar**, **aktif fazın taskları** ve **Sıradaki İş** bölümleri esas alınmalı.

> Kural: Her faz tamamlandığında kısa özet, alınan teknik/ürün kararları, tamamlanan tasklar ve sıradaki faz/tasklar burada tutulur.
