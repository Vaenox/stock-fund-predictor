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
- Analysis test suite: `18 passed`.

## Faz 4 — ML Baseline / XGBoost — TAMAMLANDI

- Leakage-aware expanding walk-forward splitter, `gap >= 5`, XGBoost baseline wrapper ve metrikler tamamlandı.
- Gerçek BIST smoke coverage: THYAO, ASELS, TUPRS, BIMAS.
- Gerçek TEFAS smoke coverage: AFA, AFT, AFS.
- AAL one-class training problemi doğrulandı; validation gevşetilmedi.
- Faz 4 acceptance: `3 passed`.

## Faz 5 — Model Tuning / Feature Importance / Signal-Risk Foundation — AKTİF

### Güncel Bulgular

- Inner walk-forward tuning, feature importance, calibration, risk adjustment ve signal foundation tamamlandı.
- Feature representation ablation altı sembolde tamamlandı; raw_all / normalized_all / stationary_core candidate olarak korunuyor, production contract sessizce değiştirilmedi.
- 6-symbol direction diagnostic tamamlandı. ML probability için 3 direct / 3 inverse; Technical Score için ROC yönünde 4 inverse / 2 direct görüldü. Global production inversion seçilmedi.
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

- Fold 1: baseline direct ROC `0.4323`, PR `0.3539`; inverse ROC `0.5677`, PR `0.4227`. Tuned direct ROC `0.4479`, PR `0.3848`; inverse ROC `0.5521`, PR `0.4768`.
- Fold 2: baseline direct ROC `0.6319`, PR `0.4759`; inverse ROC `0.3681`, PR `0.1091`. Tuned direct ROC `0.7083`, PR `0.5720`; inverse ROC `0.2917`, PR `0.0889`.
- Fold 3: baseline direct ROC `0.3714`, PR `0.1130`; inverse ROC `0.6286`, PR `0.1845`. Tuned direct ROC `0.4914`, PR `0.1428`; inverse ROC `0.5086`, PR `0.2103`.

**AFA Aggregate OOS**
- Baseline: direct ROC `0.3398`, PR `0.2137`; inverse ROC `0.6602`, PR `0.2959`.
- Tuned: direct ROC `0.3587`, PR `0.2324`; inverse ROC `0.6413`, PR `0.3402`.

**Karar:** Tuning AFA'da bazı performans metriklerini iyileştirdi ancak direction davranışını çözmedi. Aggregate direct ROC `0.3587` < inverse `0.6413`; foldlar da heterojen.

### Faz 5 Baseline vs Tuned Direction — THYAO

Canonical stock history yetersiz olduğu için bu koşuda scriptin mevcut fallback davranışıyla **Borsapy provider** kullanıldı. Gerçek 3-fold / 120 OOS comparison tamamlandı.

**THYAO — 685 raw rows, 481 training rows, 120 OOS rows, target rate 0.158**

- **Fold 1:** baseline direct ROC `0.4502`, PR `0.3554`, Spearman `-0.0655`; inverse ROC `0.5498`, PR `0.2654`. Tuned direct ROC `0.5108`, PR `0.3712`, Spearman `0.0142`; inverse ROC `0.4892`, PR `0.2216`.
- **Fold 2:** baseline direct ROC `0.4695`, PR `0.2431`; inverse ROC `0.5305`, PR `0.3308`. Tuned direct ROC `0.3763`, PR `0.1929`; inverse ROC `0.6237`, PR `0.3060`.
- **Fold 3:** baseline direct ROC `0.9189`, PR `0.4250`; inverse ROC `0.0811`, PR `0.0543`. Tuned direct ROC `0.9189`, PR `0.6000`; inverse ROC `0.0811`, PR `0.0538`.

**THYAO Aggregate OOS**
- Baseline: direct ROC `0.5597`, PR `0.2883`, Spearman `0.0755`; inverse ROC `0.4403`, PR `0.1894`.
- Tuned: direct ROC `0.5638`, PR `0.2731`, Spearman `0.0807`; inverse ROC `0.4362`, PR `0.1500`.

**Karar:** Tuning THYAO'da aggregate ROC-AUC'yi çok sınırlı artırdı; PR-AUC ise `0.2883 -> 0.2731` düştü. Aggregate direction hem baseline hem tuned modelde direct tarafta kaldı. Foldlar arasında yön değişimi görülse de tuning global direction'ı tersine çevirmedi. Bu nedenle AFA + THYAO kanıtı, direction davranışının tuning seçiminden kaynaklandığını desteklemiyor. Production direction değiştirilmedi.

### Faz 5 Direction Sonucu

AFA ve THYAO baseline-vs-tuned comparison birlikte tamamlandı. Bu iki sembolde tuning'in direction probleminin kök nedeni olduğuna dair kanıt yok.

- AFA: baseline inverse ROC `0.6602` → tuned inverse ROC `0.6413`; direct ROC `0.3398` → `0.3587`.
- THYAO: baseline direct ROC `0.5597` → tuned direct ROC `0.5638`; inverse ROC `0.4403` → `0.4362`.
- AFA'da tuning bazı PR metriklerini iyileştirirken inverse yön baskınlığı sürdü.
- THYAO'da tuned model ROC'u sınırlı iyileştirdi fakat aggregate PR geriledi ve direct yön korundu.

**Karar:** Global direct/inverse inversion production'a alınmayacak. Tuning direction probleminden ayrıştırıldı. Bir sonraki araştırma target definition ve/veya feature representation/model contract üzerinde leakage-safe deneyler olmalıdır; outer OOS sonuçlarına bakarak production contract değiştirilmemelidir.

### Faz 5 Threshold Validation — 6 Symbol Aggregate Observation

- THYAO: p25 11.625, median 16.478, p75 21.171, min 2.580, max 33.904.
- AFA: p25 28.904, median 30.997, p75 33.449, min 11.744, max 48.242.
- AFT: p25 22.545, median 27.375, p75 32.020, min 12.056, max 54.051.
- ASELS: p25 26.041, median 36.524, p75 49.179, min 7.881, max 72.313.
- TUPRS: p25 24.539, median 28.651, p75 33.231, min 11.633, max 65.288.
- BIMAS: p25 28.267, median 33.693, p75 47.759, min 17.006, max 71.204.

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
- [x] THYAO baseline vs tuned direction OOS karşılaştırması tamamlandı.
- [x] Tuning'in direction davranışına etkisi AFA + THYAO üzerinde ayrıştırıldı; global direction değişikliği yapılmadı.
- [ ] Target/model contract revizyonunu yalnızca leakage-safe validation evidence ile deneysel değerlendir.
- [ ] Düzeltilmiş normalized feature/model audit'ini ilgili coverage üzerinde çalıştır.
- [x] Faz 5 acceptance testleri: `3 passed`.
- [x] Tüm ML test suite: `75 passed in 6.15s`.

## Sıradaki İş

1. **Target/model contract'ını incele:** mevcut +3% / horizon 5 hedefinin direction diagnostics ile ilişkisini leakage-safe inner validation içinde test et; production targetı henüz değiştirme.
2. **Representation selection'ı araştır:** raw_all / normalized_all / stationary_core seçeneklerini inner walk-forward candidate olarak değerlendir; outer test foldunu seçimde kullanma.
3. Threshold ve gerçek signal-chain sonuçlarını ilgili Phase 5 raporuna kaydet; global BUY/HOLD/SELL winner seçme.
4. Phase 5 gerçek signal-chain kapanışını doğrula.
5. Phase 5 tamamlandıktan sonra Phase 6'ya geç.

## Yeni Sohbette Devam Etme Kuralı

Yeni bir sohbette projeye devam ederken bu dosya önce okunmalı. Özellikle **Güncel Durum**, **Tamamlananlar**, **aktif fazın taskları** ve **Sıradaki İş** bölümleri esas alınmalı.

> Kural: Her faz tamamlandığında kısa özet, alınan teknik/ürün kararları, tamamlanan tasklar ve sıradaki faz/tasklar burada tutulur.
