# Proje İlerleme Kaydı

Bu dosya, fazlarda alınan kararların, tamamlanan işlerin ve sıradaki taskların kısa özetini tutar. Yeni bir sohbette projeye devam ederken önce bu dosya referans alınmalıdır.

## Güncel Durum

- Aktif faz: **Faz 3 — Technical Analysis Engine**
- Son tamamlanan faz: **Faz 2 — Data Infrastructure**
- Faz 1 ürün spesifikasyonu: `docs/phase-1-product-spec.md`
- Faz 2 dokümanları: `docs/phase-2-data-sources.md`, `docs/phase-2-data-model.md`, `docs/phase-2-provider-adapter.md`, `docs/phase-2-historical-ingestion.md`, `docs/phase-2-free-data-providers.md`
- Faz 2 canonical market data contract: `docs/data-contract.md`
- Faz 3 teknik analiz contract: `docs/phase-3-technical-analysis.md`

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

## Faz 3 — Technical Analysis Engine — AKTİF

### Tamamlanan

- [x] Indicator engine modülü oluşturuldu: `backend/app/analysis/indicators.py`.
- [x] Stock indicator seti: SMA 20/50/200, EMA 20/50/200, RSI 14, MACD 12/26/9, Bollinger 20/2, ATR 14, ADX 14, momentum/returns, volatility, volume ratio/change.
- [x] Fund indicator seti: unit-price üzerinden SMA/EMA, RSI, MACD, Bollinger, momentum ve volatility.
- [x] Warm-up dönemleri `NaN` olarak korunuyor; sessiz forward-fill yapılmıyor.
- [x] Indicator hesapları kronolojik sıralama sonrası yalnızca geçmiş/mevcut gözlemleri kullanıyor.
- [x] Look-ahead regression unit testi eklendi.
- [x] Faz 3 technical-analysis contract oluşturuldu: `docs/phase-3-technical-analysis.md`.
- [x] Gerçek provider indicator smoke scripti oluşturuldu: `backend/scripts/smoke_test_indicators.py`.

### Faz 3 Taskları

- [x] Teknik analiz contract ve indicator mimarisini oluştur.
- [x] Indicator engine çekirdeğini oluştur.
- [x] Stock indicator setini oluştur ve test et.
- [x] Fund-compatible indicator setini oluştur ve test et.
- [x] Look-ahead / warm-up davranışını test et.
- [ ] Gerçek BIST verisiyle indicator smoke testini çalıştır.
- [ ] Gerçek TEFAS verisiyle indicator smoke testini çalıştır.
- [ ] Teknik skor (`0–100`) katmanını oluştur.
- [ ] Teknik skor için explainability bileşenlerini oluştur.
- [ ] ML feature dataset builder oluştur.
- [ ] Faz 3 kabul testlerini tamamla.

## Sıradaki İş

1. Gerçek BIST + TEFAS indicator smoke testlerini çalıştır.
2. Teknik Score (`0–100`) katmanını oluştur.
3. Indicator → ML feature dataset builder katmanını oluştur.
4. Faz 3 kabul testlerini tamamla.
5. Ardından Faz 4 — İlk ML Modeli / XGBoost baseline.

## Yeni Sohbette Devam Etme Kuralı

Yeni bir sohbette projeye devam ederken bu dosya önce okunmalı. Özellikle **Güncel Durum**, **Tamamlananlar**, **aktif fazın taskları** ve **Sıradaki İş** bölümleri esas alınmalı. Bir task tamamlandığında bu dosya aynı çalışma kapsamında güncellenmeli.

> Kural: Her faz tamamlandığında kısa özet, alınan teknik/ürün kararları, tamamlanan tasklar ve sıradaki faz/tasklar burada tutulur. Böylece proje farklı sohbetlerde kaldığı yerden sürdürülebilir.
