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
- `backend/tests/ml/test_risk_adjustment.py` ile risk ölçeği, maksimum penalty, stale etkisi, fund/stock ayrımı ve config validation testleri eklendi.

### Faz 5 THYAO Outer Comparison

- Fold 1: baseline ROC `0.2157`, PR `0.1246`; tuned ROC `0.2549`, PR `0.1310`; accuracy ikisinde de `0.8500`.
- Fold 2: test fold tek sınıflı; ROC/PR iki model için de `None`; accuracy ikisinde de `1.0000`.
- Fold 3: baseline ROC `0.8947`, PR `0.3333`; tuned ROC `0.9474`, PR `0.5000`; accuracy ikisinde de `0.9500`.
- Bu tek sembol sonucunda tuning iki ölçülebilir outer fold'da ROC-AUC ve PR-AUC'yi yükseltti; ancak sample size sınırlı ve Fold 2 tek sınıflı olduğu için genellenebilirlik sonucu çıkarılmadı.

### Faz 5 Taskları

- [x] Tuning dataset / inner-validation foundation oluştur.
- [x] XGBoost hyperparameter candidate search katmanı oluştur.
- [x] Baseline vs tuned modelleri aynı outer walk-forward protokolünde karşılaştır.
- [x] Feature importance / gain raporlama foundation'ı oluştur.
- [x] Model probability calibration ihtiyacını değerlendir.
- [x] Risk adjustment foundation'ını uygula ve unit testlerini ekle.
- [ ] Risk adjustment unit testlerini Codespace üzerinde çalıştır ve PASS doğrula.
- [ ] AFA ve THYAO gerçek veri üzerinde risk smoke doğrulaması yap.
- [ ] ML probability + technical score + risk adjustment birleşim sözleşmesini uygula.
- [ ] Deterministik BUY/HOLD/SELL signal rules tasarla ve test et.
- [ ] Faz 5 acceptance testlerini oluştur ve çalıştır.

### Faz 5 Tasarım Kararları

Tuning yalnızca outer fold training periodu içinde yapılır. Outer test fold model seçimi sırasında görülmez. Inner objective olarak PR-AUC kullanılır. Threshold optimizasyonu ve BUY/HOLD/SELL tasarımı tuning sonuçlarından ayrı ele alınır.

Calibration şu aşamada zorunlu değildir; AFA kontrollü deneyinde raw probability daha iyi ortalama calibration metrikleri üretmiştir. Daha geniş veri kapsamı ile yeniden değerlendirilecektir.

Risk adjustment ML probability'den ayrıdır. Risk `0–100`, adjustment `0..-20` varsayılan aralığındadır. Stock için volatilite/trend/liquidity/data quality; fund için volatilite/trend/data quality kullanılır. Risk katmanı bu aşamada tek başına BUY/HOLD/SELL üretmez.

## Sıradaki İş

1. `tests/ml/test_risk_adjustment.py` unit testlerini çalıştır.
2. AFA ve THYAO gerçek veri üzerinde risk bileşenlerini smoke test et.
3. Sonra `ML Probability + Technical Score + Risk Adjustment` için deterministic signal foundation oluştur.
4. En son BUY/HOLD/SELL eşiklerini ve Faz 5 acceptance testlerini ele al.

## Yeni Sohbette Devam Etme Kuralı

Yeni bir sohbette projeye devam ederken bu dosya önce okunmalı. Özellikle **Güncel Durum**, **Tamamlananlar**, **aktif fazın taskları** ve **Sıradaki İş** bölümleri esas alınmalı.

> Kural: Her faz tamamlandığında kısa özet, alınan teknik/ürün kararları, tamamlanan tasklar ve sıradaki faz/tasklar burada tutulur.
