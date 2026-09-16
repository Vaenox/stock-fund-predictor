# Proje İlerleme Kaydı

Bu dosya, fazlarda alınan kararların, tamamlanan işlerin ve sıradaki taskların kısa özetini tutar. Yeni bir sohbette projeye devam ederken önce bu dosya referans alınmalıdır.

## Güncel Durum

- Aktif faz: **Faz 5 — Model Tuning / Feature Importance / Signal-Risk Foundation**
- Son tamamlanan faz: **Faz 4 — ML Baseline / XGBoost**
- Faz 1 ürün spesifikasyonu: `docs/phase-1-product-spec.md`
- Faz 2 dokümanları: `docs/phase-2-data-sources.md`, `docs/phase-2-data-model.md`, `docs/phase-2-provider-adapter.md`, `docs/phase-2-historical-ingestion.md`, `docs/phase-2-free-data-providers.md`
- Faz 2 canonical market data contract: `docs/data-contract.md`
- Faz 3 teknik analiz contract: `docs/phase-3-technical-analysis.md`
- Faz 3 ML feature contract: `docs/ml-feature-contract.md`
- Faz 4 ML baseline contract: `docs/phase-4-ml-baseline.md`
- Faz 4 baseline evaluation raporu: `docs/phase-4-ml-baseline-evaluation.md`
- Faz 5 contract: `docs/phase-5-model-tuning-and-signals.md`

## Faz 0 — Proje Başlangıcı ve Roadmap

- Proje amacı: hisse ve fonlar için veri + teknik analiz + ML tabanlı fırsat analizi.
- MVP stack: Next.js/TypeScript, Tailwind/shadcn/ui, Lightweight Charts, FastAPI, Pandas/NumPy/Polars, scikit-learn + XGBoost/LightGBM, PostgreSQL/TimescaleDB, Redis, Supabase Auth, Docker.
- İlk ML hedefi: 5 işlem günü ileri getiri `> +3%`.
- Kritik riskler: look-ahead bias, data leakage, survivorship bias, slippage/işlem maliyetleri ve model drift.

## Faz 1 — Product Design

- BIST hisseleri + Türkiye yatırım fonları.
- 5 işlem günlük tahmin ufku.
- İlk model: XGBoost.
- Kullanıcı sinyali: BUY / HOLD / SELL.
- Final yaklaşım: ML olasılığı + teknik skor + risk adjustment.
- Teknik skor ve risk skorunun ML tahmininden ayrı tutulması kararlaştırıldı.
- Random split yerine zaman sıralı validation / walk-forward yaklaşımı belirlendi.

## Faz 2 — Data Infrastructure — TAMAMLANDI

- BIST ve TEFAS provider, normalization, validation, persistence, quality ve streaming altyapısı tamamlandı.
- Gerçek BIST full-universe coverage: 516/516 quote.
- Gerçek TEFAS full universe: 2040/2040 fon.
- Historical + live PostgreSQL persistence ve duplicate/upsert kontrolleri doğrulandı.
- Incremental stock/fund ingestion smoke testleri geçti.
- E2E provider → normalize → validate → upsert → quality pipeline gerçek PostgreSQL ile geçti.

### Faz 2 Kabul Sonucu

- Stock E2E: geçti.
- Fund E2E: geçti.
- Repeat ingestion: duplicate üretmedi.
- Future-dated invalid records: persistence'a girmedi.
- Son E2E sonucu: `E2E DATA PIPELINE SMOKE TEST PASSED`.

## Faz 3 — Technical Analysis Engine — TAMAMLANDI

- Indicator engine: `backend/app/analysis/indicators.py`.
- Stock/fund indicator setleri oluşturuldu ve test edildi.
- Warm-up ve look-ahead davranışı doğrulandı.
- Explainable 0–100 technical score stock/fund için oluşturuldu.
- ML feature dataset builder: `backend/app/analysis/features.py`.
- Feature schema/leakage contract: `docs/ml-feature-contract.md`.
- Real BIST + TEFAS indicator, technical score ve ML feature smoke testleri geçti.
- Feature unit tests `6/6`, full analysis test suite `18/18` geçti.

### Faz 3 Kabul Sonucu

- Analysis tests: `18 passed`.
- BIST/TEFAS indicator ve score smoke: geçti.
- Stock/fund feature smoke: geçti.
- Look-ahead kontrolleri: geçti.
- Faz 3: kabul edildi.

## Faz 4 — ML Baseline / XGBoost — TAMAMLANDI

### Tamamlanan

- XGBoost baseline contract oluşturuldu.
- Leakage-aware expanding walk-forward splitter oluşturuldu.
- `gap >= 5` kuralı baseline evaluation'a bağlandı.
- XGBoost baseline wrapper oluşturuldu.
- ROC-AUC, PR-AUC, accuracy, precision, recall ve positive-rate metrikleri eklendi.
- Fold bazında train/test target sınıf sayıları `FoldMetrics` içine eklendi.
- Phase 4 acceptance suite: `backend/tests/ml/test_phase4_acceptance.py` oluşturuldu.
- TEFAS smoke scriptindeki varsayılan `chunk-delay` `10s -> 0s` yapıldı.
- Gerçek BIST baseline coverage: `THYAO`, `ASELS`, `TUPRS`, `BIMAS` smoke testleri geçti.
- Gerçek TEFAS baseline coverage: `AFA`, `AFT`, `AFS` smoke testleri geçti.
- `AAL` için one-class training problemi doğrulandı; validation kuralı gevşetilmedi.

### Faz 4 Kabul Sonucu

```text
PYTHONPATH=. pytest tests/ml/test_phase4_acceptance.py -q
3 passed
```

Kabul edilenler:
- `predict_proba` probability contract.
- Chronological walk-forward ve `gap=5`.
- Two-class training fold zorunluluğu.
- Single-class test fold için ROC-AUC/PR-AUC `None` davranışı.
- Gerçek BIST + TEFAS baseline smoke coverage.

**Faz 4 — ML Baseline / XGBoost kabul edildi ve kapatıldı.**

Not: Baseline'ın teknik olarak çalışması, üretim seviyesinde model kalitesi veya genellenebilirlik garantisi değildir. Tuning ve signal tasarımı ayrı fazlardır.

## Faz 5 — Model Tuning / Feature Importance / Signal-Risk Foundation — AKTİF

### Amaç

Baseline üzerine kontrollü model iyileştirme, feature importance analizi ve ML çıktısını teknik skor/risk katmanına bağlayacak deterministik signal foundation oluşturmak.

### Faz 5 Kuralları

- Walk-forward validation korunur; random split kullanılmaz.
- `gap >= 5` korunur.
- Test dönemleri tuning sırasında görülmez.
- Hyperparameter tuning yalnızca train/validation dönemleri üzerinde yapılır.
- Test foldları final değerlendirme amacıyla ayrıdır.
- Tuning ile birlikte feature importance raporlanır.
- BUY/HOLD/SELL doğrudan tek bir ML probability threshold'undan üretilmez; teknik skor ve risk adjustment ayrı tutulur.

### Faz 5 Taskları

- [ ] Tuning dataset / inner-validation contract oluştur.
- [ ] XGBoost hyperparameter search katmanı oluştur.
- [ ] Baseline vs tuned modelleri aynı walk-forward protokolünde karşılaştır.
- [ ] Feature importance / gain raporlama katmanı oluştur.
- [ ] Model probability calibration ihtiyacını değerlendir.
- [ ] Risk adjustment contract oluştur.
- [ ] ML probability + technical score + risk adjustment birleşim sözleşmesini oluştur.
- [ ] Deterministik BUY/HOLD/SELL signal rules tasarla ve test et.
- [ ] Faz 5 acceptance testlerini oluştur ve çalıştır.

### Faz 5 Tasarım Kararı

İlk adım tuning altyapısıdır. Signal katmanı, tuned baseline değerlendirmesi ve feature importance sonuçları kaydedildikten sonra bağlanacaktır. Threshold veya BUY/HOLD/SELL kuralları test sonuçlarına bakılmadan önceden “kazanan” kabul edilmeyecektir.

## Yeni Sohbette Devam Etme Kuralı

Yeni bir sohbette projeye devam ederken bu dosya önce okunmalı. Özellikle **Güncel Durum**, **Tamamlananlar**, **aktif fazın taskları** ve **Sıradaki İş** bölümleri esas alınmalı. Bir task tamamlandığında bu dosya aynı çalışma kapsamında güncellenmeli.

> Kural: Her faz tamamlandığında kısa özet, alınan teknik/ürün kararları, tamamlanan tasklar ve sıradaki faz/tasklar burada tutulur. Böylece proje farklı sohbetlerde kaldığı yerden sürdürülebilir.

## Sıradaki İş

1. Faz 5 tuning contract'ını ve inner walk-forward validation katmanını oluştur.
2. XGBoost hyperparameter search'i test dönemlerine leakage olmadan çalıştır.
3. Baseline vs tuned sonuçlarını aynı evaluation raporuna ekle.
4. Feature importance ve risk/signal foundation'a geç.
