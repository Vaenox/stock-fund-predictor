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
- [x] scikit-learn ve XGBoost bağımlılıkları requirements'a eklendi.
- [x] Split ve XGBoost baseline unit testleri oluşturuldu.

### Faz 4 Taskları

- [x] Baseline model sözleşmesini oluştur.
- [x] Zaman serisi / walk-forward split katmanını oluştur.
- [x] Leakage gap kuralını uygula.
- [x] XGBoost baseline wrapper'ını oluştur.
- [x] Baseline metriklerini oluştur.
- [ ] ML baseline unit testlerini çalıştır.
- [ ] Gerçek BIST feature dataset ile XGBoost baseline smoke çalıştır.
- [ ] Gerçek TEFAS feature dataset ile XGBoost baseline smoke çalıştır.
- [ ] Walk-forward baseline sonuçlarını kaydet ve değerlendirme tablosu oluştur.
- [ ] Faz 4 kabul testlerini tamamla.

## Sıradaki İş

1. Codespace'te yeni ML bağımlılıklarını kur.
2. `tests/ml` unit testlerini çalıştır.
3. Gerçek BIST ve TEFAS feature dataset üzerinde XGBoost baseline smoke çalıştır.
4. Walk-forward metriklerini kaydet.
5. Faz 4 kabulünü tamamla ve sonraki model geliştirme tasklarına geç.

## Yeni Sohbette Devam Etme Kuralı

Yeni bir sohbette projeye devam ederken bu dosya önce okunmalı. Özellikle **Güncel Durum**, **Tamamlananlar**, **aktif fazın taskları** ve **Sıradaki İş** bölümleri esas alınmalı. Bir task tamamlandığında bu dosya aynı çalışma kapsamında güncellenmeli.

> Kural: Her faz tamamlandığında kısa özet, alınan teknik/ürün kararları, tamamlanan tasklar ve sıradaki faz/tasklar burada tutulur. Böylece proje farklı sohbetlerde kaldığı yerden sürdürülebilir.
