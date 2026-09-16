# Proje İlerleme Kaydı

Bu dosya, fazlarda alınan kararların, tamamlanan işlerin ve sıradaki taskların kısa bir özetini tutar. Yeni bir sohbette projeye devam ederken önce bu dosya referans alınmalıdır.

## Güncel Durum

- Aktif faz: **Faz 2 — Data Infrastructure / Veri Altyapısı**
- Son tamamlanan faz: **Faz 1 — Product Design / Ürün Tanımı**
- Faz 1 ürün spesifikasyonu: `docs/phase-1-product-spec.md`
- Faz 2 veri kaynakları araştırması: `docs/phase-2-data-sources.md`
- Faz 2 canonical veri modeli: `docs/phase-2-data-model.md`
- Faz 2 provider adapter tasarımı: `docs/phase-2-provider-adapter.md`
- Faz 2 historical ingestion tasarımı: `docs/phase-2-historical-ingestion.md`
- Faz 2 ücretsiz provider stratejisi: `docs/phase-2-free-data-providers.md`
- Güncel hedef: **borsapy/TradingView WebSocket ile BIST canlı/dinamik akışı + TEFAS JSON ile fon günlük güncellemesi**.

## Tamamlananlar

### Faz 0 — Proje Başlangıcı ve Roadmap
- Projenin amacı belirlendi: hisse ve fonlar için veri + teknik analiz + ML tabanlı al/sat fırsat analizi.
- MVP teknoloji yığını belirlendi:
  - Frontend: Next.js + TypeScript + Tailwind CSS + shadcn/ui
  - Grafik: TradingView Lightweight Charts
  - Backend: Python + FastAPI
  - Veri/analiz: Pandas + NumPy + Polars
  - ML: scikit-learn + XGBoost/LightGBM
  - Veritabanı: PostgreSQL + TimescaleDB
  - Cache: Redis
  - Auth: Supabase Auth
  - Container: Docker
- Roadmap oluşturuldu: ürün tasarımı → veri altyapısı → teknik analiz → ilk ML modeli → backtest → tahmin motoru → haber/sentiment → gelişmiş modeller → dashboard → kullanıcı sistemi → bildirimler → paper trading → gerçek işlem entegrasyonu.
- Kritik riskler kayda alındı: look-ahead bias, data leakage, survivorship bias, işlem maliyetleri/slippage ve model drift.
- İlk ML hedefi olarak 5 işlem günlük ileriye dönük getiri olasılığının tahmini belirlendi.

### Proje İskeleti
- README'deki klasör yapısı repository içinde oluşturuldu.
- `backend/app` altında api, models, schemas, services, indicators, ml/features, ml/training, ml/prediction, ml/models, backtesting, data ve core klasörleri oluşturuldu.
- `backend/tests` ve frontend tarafındaki dashboard, stocks, funds, predictions, portfolio, settings, components, lib, hooks, services ve types klasörleri oluşturuldu.
- Boş klasörlerin Git tarafından korunması için `.gitkeep` dosyaları eklendi.

### Faz 1 — Product Design
- İlk pazar: **BIST**.
- İlk varlıklar: **BIST hisseleri + Türkiye'deki yatırım fonları**.
- Gelecekte: NASDAQ/NYSE ve ETF desteği.
- İlk tahmin ufku: **5 işlem günü**.
- İlk ML hedefi: **5 işlem günü ileri getiri > +3%**.
- İlk model ailesi: **XGBoost**.
- Ana kullanıcı sinyali: **BUY / HOLD / SELL**.
- Model olasılığı; teknik skor ve risk skoru ile birlikte değerlendirilecek.
- Öncelik sırası: **veri kalitesi → feature engineering → backtest doğruluğu → model performansı → UI**.
- Gerçek para ile otomatik işlem başlangıç kapsamına alınmayacak; önce paper trading yapılacak.
- MVP ekranları ve temel kullanıcı akışları tanımlandı.
- ML ve backtest değerlendirme metrikleri belirlendi.
- Look-ahead bias, data leakage, survivorship bias ve işlem maliyetleri için temel backtest kuralları tanımlandı.
- Ayrıntılı ürün spesifikasyonu `docs/phase-1-product-spec.md` dosyasına eklendi.

### Faz 2 — Data Infrastructure
- [x] BIST hisse veri kaynakları için teknik araştırma yapıldı.
- [x] Türkiye yatırım fonu veri kaynakları için teknik araştırma yapıldı.
- [x] Borsa İstanbul veri lisansı / dağıtım yapısı incelendi.
- [x] Ticari BIST adayları olarak Matriks ve Finnet kaydedildi.
- [x] Fon kaynağı olarak TEFAS ve ikincil doğrulama için SPK kaydedildi.
- [x] Provider abstraction yaklaşımı belirlendi.
- [x] Canonical asset, provider mapping, stock OHLCV ve fund daily price veri modeli tasarlandı.
- [x] SQLAlchemy 2.x + PostgreSQL/psycopg 3 backend veri erişim yaklaşımı seçildi.
- [x] SQLAlchemy ORM + Pydantic canonical şemaları oluşturuldu.
- [x] Alembic migration altyapısı oluşturuldu.
- [x] Initial PostgreSQL migration'ı oluşturuldu.
- [x] TimescaleDB hypertable için koşullu migration mantığı eklendi.
- [x] Provider interface ve DTO'ları oluşturuldu.
- [x] Normalizer + temel validator katmanı oluşturuldu.
- [x] Historical stock/fund ingestion service ve PostgreSQL upsert oluşturuldu.
- [x] Transaction rollback ve ingestion testleri oluşturuldu.
- [x] Matriks adapter iskeleti premium/opsiyonel provider olarak tutuldu.
- [x] **Ücretsiz BIST provider olarak borsapy + TradingView WebSocket seçildi.**
- [x] **Ücretsiz fon provider olarak doğrudan TEFAS JSON API seçildi.**
- [x] `BorsapyProvider` ile BIST company discovery + live quote/candle streaming entegrasyonu oluşturuldu.
- [x] `TefasProvider` ile fon evreni ve günlük fon verisi entegrasyonu oluşturuldu.
- [x] `borsapy` bağımlılığı eklendi ve güncel release'e sabitlendi.
- [x] Historical ingestion tasarımı dokümante edildi.
- [x] Ücretsiz provider stratejisi dokümante edildi.
- [x] **BIST provider universe sync servisi oluşturuldu.**
- [x] `assets` + `asset_provider_mappings` için idempotent seed akışı oluşturuldu.
- [x] BIST universe sync scripti ve testleri oluşturuldu.
- [x] **Tek persistent TradingView bağlantısını yöneten BIST bulk streaming manager oluşturuldu.**
- [x] **Quote/candle provider payloadlarını canonical live event DTO'larına dönüştüren katman oluşturuldu.**
- [x] Streaming subscription işlemleri duplicate çağrılara karşı idempotent hale getirildi.
- [x] Streaming manager için fake-stream tabanlı birim testleri oluşturuldu.
- [x] **Canonical quote/candle eventlerini Redis Streams + Pub/Sub üzerinden yayınlayan publisher oluşturuldu.**
- [x] **BIST streaming manager ile Redis publisher arasında pipeline bridge oluşturuldu.**
- [x] Redis Python client bağımlılığı eklendi.
- [x] Redis publisher ve pipeline için birim testleri oluşturuldu.
- [x] **BIST live tick ve intraday candle için TimescaleDB uyumlu tablolar oluşturuldu.**
- [x] **Live tick/candle upsert persistence katmanı oluşturuldu.**
- [x] **TimescaleDB retention ayarları config'e bağlandı (tick 30 gün, candle 180 gün varsayılan).**
- [x] Live persistence testleri oluşturuldu.
- [x] **BIST stream watchdog oluşturuldu: stale event tespiti + otomatik reconnect + bounded exponential backoff.**
- [x] **Reconnect sonrasında quote ve candle aboneliklerinin yeniden kurulması eklendi.**
- [x] Watchdog health callback ve son event zamanlarının izlenmesi eklendi.
- [x] Watchdog davranışı için birim testleri oluşturuldu.
- [x] **Tek sembollü gerçek TradingView/BIST WebSocket smoke-test scripti oluşturuldu.**
- [x] **16 Eylül 2026 — THYAO gerçek WebSocket smoke test başarıyla çalıştırıldı: quote_received=True, candle_received=True, SMOKE TEST PASSED.**
- [x] Gerçek WebSocket smoke testini GitHub Actions üzerinden manuel çalıştırmak için workflow eklendi.
- [x] **Tüm BIST evreni için streaming load-test harness'i oluşturuldu.**
- [x] Load-test, discovered tüm sembolleri tek persistent bağlantıda subscribe etmeyi ve event sayısını gözlemlemeyi destekliyor.
- [x] **TEFAS tüm-fon günlük ingestion smoke-test scripti oluşturuldu.**
- [x] TEFAS testinde tüm keşfedilen fonlar için yakın tarihli günlük geçmiş isteniyor; hatalı fon istekleri ayrı raporlanıyor.

### Faz 2 Taskları
- [x] Veri kaynaklarını araştır ve teknik adayları belirle
- [x] Canonical market data modelini tasarla
- [x] PostgreSQL/TimescaleDB migration altyapısını oluştur
- [x] Provider interface'i kodla
- [x] Normalizer + validator katmanını kodla
- [x] Historical ingestion service'i oluştur
- [x] Matriks premium adapter iskeletini oluştur
- [x] Ücretsiz BIST provider'ını seç ve adapter'ını oluştur
- [x] Ücretsiz TEFAS provider'ını seç ve adapter'ını oluştur
- [x] Provider dokümantasyonunu güncelle
- [x] Tüm BIST sembollerini borsapy ile keşfedip asset/provider mapping sync servisini oluştur
- [x] BIST universe sync scriptini ve testini oluştur
- [x] TradingViewStream toplu subscription manager oluştur
- [x] Quote/candle → canonical live DTO dönüşümünü oluştur
- [x] Live eventleri Redis Pub/Sub/Streams üzerinden yayınla
- [x] BIST live/intraday TimescaleDB tablosunu oluştur
- [x] Reconnect, stale quote ve heartbeat kontrollerini oluştur
- [x] **Tek BIST sembolüyle gerçek WebSocket smoke test çalıştır — THYAO ile doğrulandı (16.09.2026).**
- [ ] Tüm BIST evreniyle streaming yük testi çalıştır
- [ ] TEFAS günlük tüm fon evreni smoke testini çalıştır
- [ ] İlk gerçek historical + live kayıtları PostgreSQL/TimescaleDB'ye yaz
- [ ] Duplicate/upsert + source provenance davranışını gerçek veriyle doğrula
- [ ] Incremental update pipeline oluştur
- [ ] Missing data / outlier / source-quality kontrollerini genişlet
- [ ] Temiz veri sözleşmesini (data contract) son haline getir
- [ ] Uçtan uca data pipeline testlerini tamamla

## Sıradaki İş

1. Erişilebilir gerçek ağ/CI ortamında tüm BIST evreni load testini çalıştır ve sonuçları ölç.
2. Erişilebilir gerçek ağ/CI ortamında TEFAS günlük tüm fon evreni smoke testini çalıştır.
3. İlk gerçek historical + live kayıtları PostgreSQL/TimescaleDB'ye yazıp provenance doğrulamasını tamamla.
4. Incremental update pipeline ve genişletilmiş kalite kontrollerini tamamla.

## Yeni Sohbette Devam Etme Kuralı

Yeni bir sohbette projeye devam ederken bu dosya önce okunmalı. Özellikle **Güncel Durum**, **Tamamlananlar**, **aktif fazın taskları** ve **Sıradaki İş** bölümleri esas alınmalı. Bir task tamamlandığında bu dosya aynı çalışma kapsamında güncellenmeli.

> Kural: Her faz tamamlandığında kısa özet, alınan teknik/ürün kararları, tamamlanan tasklar ve sıradaki faz/tasklar burada tutulur. Böylece proje farklı sohbetlerde kaldığı yerden sürdürülebilir.
