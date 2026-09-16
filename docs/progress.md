# Proje İlerleme Kaydı

Bu dosya, fazlarda alınan kararların, tamamlanan işlerin ve sıradaki taskların kısa özetini tutar. Yeni bir sohbette projeye devam ederken önce bu dosya referans alınmalıdır.

## Güncel Durum

- Aktif faz: **Faz 4 — ML Baseline / XGBoost**
- Son tamamlanan faz: **Faz 3 — Technical Analysis Engine**
- Faz 1 ürün spesifikasyonu: `docs/phase-1-product-spec.md`
- Faz 2 dokümanları: `docs/phase-2-data-sources.md`, `docs/phase-2-data-model.md`, `docs/phase-2-provider-adapter.md`, `docs/phase-2-historical-ingestion.md`, `docs/phase-2-free-data-providers.md`
- Faz 2 canonical market data contract: `docs/data-contract.md`
- Faz 3 teknik analiz contract: `docs/phase-3-technical-analysis.md`
- Faz 3 ML feature contract: `docs/ml-feature-contract.md`
- Faz 4 ML baseline contract: `docs/phase-4-ml-baseline.md`
- Faz 4 baseline evaluation raporu: `docs/phase-4-ml-baseline-evaluation.md`

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

- [x] BIST ve TEFAS veri kaynakları araştırıldı.
- [x] Provider abstraction + DTO + normalizer + validator oluşturuldu.
- [x] Canonical asset/provider mapping/stock OHLCV/fund daily price veri modeli oluşturuldu.
- [x] SQLAlchemy + Pydantic + Alembic + PostgreSQL/TimescaleDB migration altyapısı tamamlandı.
- [x] Historical ingestion ve PostgreSQL upsert tamamlandı.
- [x] Transaction rollback ve ingestion testleri oluşturuldu.
- [x] Matriks premium adapter iskeleti oluşturuldu.
- [x] Ücretsiz BIST provider: `borsapy` + TradingView WebSocket.
- [x] Ücretsiz fon provider: doğrudan TEFAS JSON API.
- [x] BIST universe sync + bulk streaming manager oluşturuldu.
- [x] Quote/candle → canonical live DTO katmanı oluşturuldu.
- [x] Redis Streams/PubSub pipeline oluşturuldu.
- [x] Live tick/intraday candle TimescaleDB persistence + retention tamamlandı.
- [x] Stale quote/reconnect/watchdog oluşturuldu.
- [x] 16.09.2026 THYAO gerçek WebSocket smoke: quote + candle başarılı.
- [x] 16.09.2026 BIST strict full-universe streaming: 516/516 (%100) quote coverage.
- [x] TEFAS bulk retrieval ve kontrollü pagination tamamlandı.
- [x] 16.09.2026 TEFAS full universe: 2040/2040 fon coverage, duplicate yok.
- [x] Historical + live PostgreSQL persistence gerçek veriyle doğrulandı.
- [x] Duplicate/upsert + provenance gerçek veriyle doğrulandı.
- [x] Incremental stock/fund ingestion oluşturuldu ve test edildi.
- [x] 16.09.2026 gerçek BIST incremental smoke başarılı: THYAO overlap, DB `6→6`.
- [x] 16.09.2026 gerçek TEFAS incremental smoke başarılı: aktif AAL, `22/22` kayıt.
- [x] Market data quality katmanı oluşturuldu.
- [x] BIST 2025–2026 tam kapanış takvimi kalite kontrollerine bağlandı.
- [x] BIST + TEFAS real-data quality smoke testleri geçti.
- [x] Canonical data contract oluşturuldu: `docs/data-contract.md`.
- [x] E2E data pipeline smoke test oluşturuldu ve gerçek PostgreSQL üzerinde geçti.

### Faz 2 Kabul Sonucu

```text
Provider
  ↓
Normalize
  ↓
Validate
  ↓
Ingest / Upsert
  ↓
PostgreSQL
  ↓
Quality
```

- Stock E2E: geçti.
- Fund E2E: geçti.
- Repeat ingestion: duplicate üretmedi.
- Future-dated invalid records: persistence'a girmedi.
- Son E2E sonucu: `E2E DATA PIPELINE SMOKE TEST PASSED`.

## Faz 3 — Technical Analysis Engine — TAMAMLANDI

- [x] Indicator engine: `backend/app/analysis/indicators.py`.
- [x] Stock indicator seti oluşturuldu ve test edildi.
- [x] Fund-compatible indicator seti oluşturuldu ve test edildi.
- [x] Warm-up ve look-ahead davranışı test edildi.
- [x] Technical Score Engine: `backend/app/analysis/scoring.py`.
- [x] Explainable 0–100 technical score stock/fund için oluşturuldu.
- [x] Real BIST indicator smoke: THYAO, 312 satır, `LOOK-AHEAD CHECK: PASSED`.
- [x] Real TEFAS indicator smoke: AAL, 312 satır, `LOOK-AHEAD CHECK: PASSED`.
- [x] Real BIST technical score smoke: THYAO, score `26.5866`.
- [x] Real TEFAS technical score smoke: AAL, score `68.7969`.
- [x] ML feature dataset builder: `backend/app/analysis/features.py`.
- [x] Feature schema/leakage contract: `docs/ml-feature-contract.md`.
- [x] Real stock + fund feature smoke: ikisi de `ML FEATURE SMOKE TEST PASSED`.
- [x] Feature unit tests: `6/6` geçti.
- [x] Full analysis test suite: **18/18 geçti**.
- [x] `sma_200` testinde floating-point precision toleransı düzeltildi.

### Faz 3 Kabul Sonucu

```text
Market Data
  ↓
Indicators
  ↓
Technical Score
  ↓
ML Feature Dataset
  ↓
Leakage / Warm-up Tests
```

- Analysis tests: `18 passed`.
- BIST indicator smoke: geçti.
- TEFAS indicator smoke: geçti.
- BIST technical score smoke: geçti.
- TEFAS technical score smoke: geçti.
- Stock feature smoke: geçti.
- Fund feature smoke: geçti.
- Look-ahead kontrolleri: geçti.
- Faz 3: kabul edildi.

## Faz 4 — ML Baseline / XGBoost — AKTİF

### Tamamlanan

- [x] XGBoost baseline contract oluşturuldu: `docs/phase-4-ml-baseline.md`.
- [x] `backend/app/ml/` paketi oluşturuldu.
- [x] Leakage-aware expanding walk-forward splitter oluşturuldu: `backend/app/ml/splitting.py`.
- [x] `gap >= 5` kuralı baseline evaluation'a bağlandı.
- [x] XGBoost baseline wrapper oluşturuldu: `backend/app/ml/xgboost_baseline.py`.
- [x] ROC-AUC, PR-AUC, accuracy, precision, recall ve positive-rate metrikleri eklendi.
- [x] Fold bazında train/test target sınıf sayıları `FoldMetrics` içine eklendi.
- [x] Gerçek smoke çıktısında fold target dağılımları görünür hale getirildi.
- [x] scikit-learn ve XGBoost bağımlılıkları requirements'a eklendi.
- [x] Split ve XGBoost baseline unit testleri oluşturuldu.
- [x] **16.09.2026 — Faz 4 ML unit testleri başarıyla geçti.**
- [x] **16.09.2026 — Gerçek BIST XGBoost baseline smoke başarılı: THYAO, 684 ham / 480 training row, 3 walk-forward fold.**
- [x] **16.09.2026 — Gerçek TEFAS XGBoost baseline smoke başarılı: AFA, 312 ham / 108 training row, 3 walk-forward fold.**
- [x] İlk gerçek BIST + TEFAS baseline sonuçları `docs/phase-4-ml-baseline-evaluation.md` içine kaydedildi.
- [ ] Gerçek TEFAS üzerinde farklı bir fonla daha geniş baseline coverage.

### Faz 4 Taskları

- [x] Baseline model sözleşmesini oluştur.
- [x] Zaman serisi / walk-forward split katmanını oluştur.
- [x] Leakage gap kuralını uygula.
- [x] XGBoost baseline wrapper'ını oluştur.
- [x] Baseline metriklerini oluştur.
- [x] ML baseline unit testlerini çalıştır.
- [x] Gerçek BIST feature dataset ile XGBoost baseline smoke çalıştır.
- [x] Gerçek TEFAS feature dataset ile ilk XGBoost baseline smoke çalıştır.
- [x] Walk-forward baseline sonuçlarını kaydet ve değerlendirme tablosu oluştur.
- [ ] Birden fazla gerçek BIST + TEFAS örneği ile coverage'ı genişlet.
- [ ] Minimum target/class-distribution kabul kriterini netleştir.
- [ ] Faz 4 kabul testlerini tamamla.

### BIST Baseline Smoke Sonucu — THYAO

- Raw rows: `684`
- Training rows: `480`
- Target distribution: `{0: 374, 1: 106}`
- Fold 1: train `312/43`, test `34/6`, ROC-AUC `0.2843`, PR-AUC `0.1181`, accuracy `0.8500`, precision `0.0000`, recall `0.0000`, positive-rate `0.1500`
- Fold 2: train `332/63`, test `30/10`, ROC-AUC `0.6113`, PR-AUC `0.4765`, accuracy `0.7500`, precision `1.0000`, recall `0.0909`, positive-rate `0.2750`
- Fold 3: train `351/84`, test `39/1`, ROC-AUC `0.5128`, PR-AUC `0.0500`, accuracy `0.9750`, precision `0.0000`, recall `0.0000`, positive-rate `0.0250`
- Not: Bu sonuçlar baseline doğrulaması içindir; tek başına model kalitesi veya genellenebilirlik sonucu olarak yorumlanmamalıdır.

### TEFAS Baseline Smoke Sonucu — AFA

- Raw rows: `312`
- Training rows: `108`
- Target distribution: `{0: 84, 1: 24}`
- Fold 1: train `39/9`, test `18/2`, ROC-AUC `0.5556`, PR-AUC `0.1818`, accuracy `0.8000`, precision `0.0000`, recall `0.0000`, positive-rate `0.1000`
- Fold 2: train `53/10`, test `15/5`, ROC-AUC `0.8800`, PR-AUC `0.8369`, accuracy `0.7500`, precision `0.0000`, recall `0.0000`, positive-rate `0.2500`
- Fold 3: train `69/14`, test `20/0`, ROC-AUC `None`, PR-AUC `None`, accuracy `1.0000`, precision `0.0000`, recall `0.0000`, positive-rate `0.0000`
- Not: Fold 2'nin yüksek metrikleri tek başına model performansı sonucu olarak yorumlanmamalıdır; Fold 3 test setinde pozitif örnek yoktur.

### AAL Validation Notu

- `days=1000`, `n_splits=3` ile fold 1 training target tek sınıf oldu.
- `n_splits=1`, `test_size=40`, `gap=5` ile de fold 1 training target tek sınıf oldu.
- Bu nedenle mevcut AAL veri penceresinde XGBoost eğitimi için iki sınıflı yeterli training gözlemi doğrulanamadı.
- Single-class fold hatasını atlamak veya sentetik veri eklemek kabul edilmedi.

## Sıradaki İş

1. Birkaç gerçek BIST ve TEFAS sembolü üzerinde baseline coverage'ı genişlet.
2. Fold train/test sınıf dağılımlarını ve metrikleri ortak evaluation dokümanında tut.
3. Minimum target/class-distribution kabul kriterini belirle.
4. Faz 4 acceptance testlerini tamamla.
5. Ardından model tuning / feature importance / signal katmanına geç.

## Yeni Sohbette Devam Etme Kuralı

Yeni bir sohbette projeye devam ederken bu dosya önce okunmalı. Özellikle **Güncel Durum**, **Tamamlananlar**, **aktif fazın taskları** ve **Sıradaki İş** bölümleri esas alınmalı. Bir task tamamlandığında bu dosya aynı çalışma kapsamında güncellenmeli.

> Kural: Her faz tamamlandığında kısa özet, alınan teknik/ürün kararları, tamamlanan tasklar ve sıradaki faz/tasklar burada tutulur. Böylece proje farklı sohbetlerde kaldığı yerden sürdürülebilir.
