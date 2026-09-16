# Proje İlerleme Kaydı

Bu dosya, fazlarda alınan kararların, tamamlanan işlerin ve sıradaki taskların kısa bir özetini tutar. Yeni bir sohbette projeye devam ederken önce bu dosya referans alınmalıdır.

## Güncel Durum

- Aktif faz: **Faz 2 — Data Infrastructure / Veri Altyapısı**
- Son tamamlanan faz: **Faz 1 — Product Design / Ürün Tanımı**
- Güncel hedef: **borsapy/TradingView WebSocket ile BIST canlı/dinamik akışı + TEFAS JSON ile fon günlük güncellemesi**.
- Faz 1 ürün spesifikasyonu: `docs/phase-1-product-spec.md`
- Faz 2 ana dokümanları: `docs/phase-2-data-sources.md`, `docs/phase-2-data-model.md`, `docs/phase-2-provider-adapter.md`, `docs/phase-2-historical-ingestion.md`, `docs/phase-2-free-data-providers.md`

## Tamamlananlar

### Faz 0 — Proje Başlangıcı ve Roadmap
- Projenin amacı belirlendi: hisse ve fonlar için veri + teknik analiz + ML tabanlı al/sat fırsat analizi.
- MVP teknoloji yığını belirlendi: Next.js/TypeScript, Tailwind/shadcn/ui, TradingView Lightweight Charts, FastAPI, Pandas/NumPy/Polars, scikit-learn + XGBoost/LightGBM, PostgreSQL/TimescaleDB, Redis, Supabase Auth, Docker.
- Roadmap oluşturuldu: ürün tasarımı → veri altyapısı → teknik analiz → ilk ML modeli → backtest → tahmin motoru → haber/sentiment → gelişmiş modeller → dashboard → kullanıcı sistemi → bildirimler → paper trading → gerçek işlem entegrasyonu.
- Kritik riskler kayda alındı: look-ahead bias, data leakage, survivorship bias, işlem maliyetleri/slippage ve model drift.
- İlk ML hedefi olarak 5 işlem günlük ileriye dönük getiri olasılığının tahmini belirlendi.

### Proje İskeleti
- README'deki klasör yapısı repository içinde oluşturuldu.
- Backend/frontend klasörleri ve `.gitkeep` dosyaları oluşturuldu.

### Faz 1 — Product Design
- İlk pazar: **BIST**.
- İlk varlıklar: **BIST hisseleri + Türkiye'deki yatırım fonları**.
- İlk tahmin ufku: **5 işlem günü**.
- İlk ML hedefi: **5 işlem günü ileri getiri > +3%**.
- İlk model ailesi: **XGBoost**.
- Ana kullanıcı sinyali: **BUY / HOLD / SELL**.
- Model olasılığı; teknik skor ve risk skoru ile birlikte değerlendirilecek.
- Öncelik sırası: **veri kalitesi → feature engineering → backtest doğruluğu → model performansı → UI**.
- Gerçek para ile otomatik işlem başlangıç kapsamına alınmayacak; önce paper trading yapılacak.
- MVP ekranları, kullanıcı akışları, ML/backtest metrikleri ve temel backtest kuralları tanımlandı.
- Ayrıntılı ürün spesifikasyonu `docs/phase-1-product-spec.md` dosyasına eklendi.

### Faz 2 — Data Infrastructure
- [x] BIST ve Türkiye yatırım fonu veri kaynakları araştırıldı.
- [x] Borsa İstanbul veri lisansı / dağıtım yapısı incelendi.
- [x] Ticari BIST adayları olarak Matriks ve Finnet; fon kaynağı olarak TEFAS ve ikincil doğrulama için SPK kaydedildi.
- [x] Provider abstraction yaklaşımı belirlendi.
- [x] Canonical asset, provider mapping, stock OHLCV ve fund daily price veri modeli tasarlandı.
- [x] SQLAlchemy ORM + Pydantic canonical şemaları oluşturuldu.
- [x] Alembic ve PostgreSQL/TimescaleDB migration altyapısı oluşturuldu.
- [x] Provider interface, DTO, normalizer ve validator katmanları oluşturuldu.
- [x] Historical stock/fund ingestion service ve PostgreSQL upsert oluşturuldu.
- [x] Transaction rollback ve ingestion testleri oluşturuldu.
- [x] Matriks premium adapter iskeleti oluşturuldu.
- [x] **Ücretsiz BIST provider olarak borsapy + TradingView WebSocket seçildi.**
- [x] **Ücretsiz fon provider olarak doğrudan TEFAS JSON API seçildi.**
- [x] `BorsapyProvider` ile BIST company discovery + live quote/candle streaming entegrasyonu oluşturuldu.
- [x] `TefasProvider` ile fon evreni ve günlük fon verisi entegrasyonu oluşturuldu.
- [x] BIST universe sync servisi/scripti ve testleri oluşturuldu.
- [x] Tek persistent TradingView bağlantısını yöneten BIST bulk streaming manager oluşturuldu.
- [x] Quote/candle payloadlarını canonical live event DTO'larına dönüştüren katman oluşturuldu.
- [x] Redis Streams + Pub/Sub publisher ve streaming pipeline bridge oluşturuldu.
- [x] BIST live tick ve intraday candle için TimescaleDB tabloları ve upsert persistence katmanı oluşturuldu.
- [x] TimescaleDB retention ayarları config'e bağlandı (tick 30 gün, candle 180 gün varsayılan).
- [x] Stream watchdog: stale event tespiti, otomatik reconnect, bounded exponential backoff ve reconnect sonrası yeniden subscription oluşturuldu.
- [x] Tek sembollü gerçek WebSocket smoke test oluşturuldu ve **16.09.2026 THYAO ile başarıyla çalıştırıldı: quote_received=True, candle_received=True, SMOKE TEST PASSED.**
- [x] Gerçek WebSocket smoke testini GitHub Actions üzerinden manuel çalıştırmak için workflow eklendi.
- [x] Tüm BIST evreni için streaming load-test harness'i oluşturuldu.
- [x] Load-test universe discovery timeout dayanıklılığı geliştirildi: borsapy/KAP discovery başarısız olursa public BIST CSV fallback'i ve isteğe bağlı sembol dosyası desteği eklendi.
- [x] **BIST load-test ölçüm kriteri güçlendirildi: canonical quote event alan semboller ayrı sayılıyor; eksik semboller listeleniyor; `--require-quote-for-all` strict doğrulaması eklendi.**
- [x] **16.09.2026 — BIST strict full-universe streaming testi başarıyla tamamlandı: 516 sembol subscribe edildi, 516/516 (%100) canonical quote event alındı.**
- [x] Public fallback evrenindeki stale ticker kodları güncel TradingView sembollerine normalize edildi; `YGYO` retired olarak filtrelendi.
- [x] TEFAS tüm-fon günlük ingestion smoke-test scripti oluşturuldu.
- [x] **TEFAS bulk smoke akışı doğrulandı: 09.09.2026–16.09.2026 aralığında `--max-funds 10` ile 10/10 fon veri aldı, 0 eksik; BULK rows returned: 10000; SMOKE TEST PASSED.**
- [x] **Gerçek BIST historical + live persistence smoke-test scripti oluşturuldu ve çalıştırıldı: THYAO için 6 historical satır ve en az 1 live tick PostgreSQL'e yazıldı; SMOKE TEST PASSED.**
- [x] **Duplicate/upsert + source provenance gerçek veriyle doğrulandı: historical ikinci ingestion sonrasında satır sayısı değişmedi; `source_provider` doğrulandı ve `ingested_at` güncellendi; live conflict-key aynı kaydı güncelledi; `PERSISTENCE UPSERT/PROVENANCE VERIFIED`.**
- [x] **TEFAS bulk retrieval kontrollü sayfalama ile güncellendi; tam YAT evreni ve uzun tarih aralıkları için page-based retrieval + duplicate `(date, fund_code)` koruması eklendi.**
- [x] **16.09.2026 — TEFAS tam YAT fon evreni gerçek veriyle doğrulandı: 2040 fon keşfedildi, bulk/paginated akıştan 12233 satır döndü, 2041 unique fund code bulundu, keşfedilen 2040 fonun tamamında veri var, 0 eksik fon ve 0 duplicate `(date, fund_code)` kaydı; `FULL TEFAS UNIVERSE SMOKE TEST PASSED`.**
- [x] **Incremental historical ingestion pipeline oluşturuldu: mevcut `MAX(trading_date)` / `MAX(pricing_date)` watermark'ından devam ediyor, ilk çalıştırmada bootstrap window kullanıyor ve son günleri overlap ederek düzeltilebilir kayıtları yeniden upsert ediyor.**
- [x] **Incremental pipeline için stock/fund unit testleri ve gerçek BIST smoke-test scripti oluşturuldu.**

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
- [x] BIST universe sync servis/script/testini oluştur
- [x] TradingViewStream toplu subscription manager oluştur
- [x] Quote/candle → canonical live DTO dönüşümünü oluştur
- [x] Live eventleri Redis Pub/Sub/Streams üzerinden yayınla
- [x] BIST live/intraday TimescaleDB tablosunu oluştur
- [x] Reconnect, stale quote ve heartbeat kontrollerini oluştur
- [x] **Tek BIST sembolüyle gerçek WebSocket smoke test çalıştır — THYAO ile doğrulandı (16.09.2026).**
- [x] **Tüm BIST evreniyle streaming yük testi çalıştır ve sonuçları kalite kriterleriyle doğrula — 516/516 (%100) quote coverage.**
- [x] **TEFAS günlük tüm fon evreni smoke testini gerçek veriyle çalıştır — 2040/2040 veri coverage, 0 duplicate.**
- [x] **İlk gerçek historical + live kayıtları PostgreSQL/TimescaleDB'ye yaz ve doğrula.**
- [x] **Duplicate/upsert + source provenance davranışını gerçek veriyle doğrula.**
- [x] **Incremental update pipeline kodunu ve testlerini oluştur.**
- [ ] Incremental update pipeline'ı gerçek BIST + TEFAS verisiyle smoke-test et
- [ ] Missing data / outlier / source-quality kontrollerini genişlet
- [ ] Temiz veri sözleşmesini (data contract) son haline getir
- [ ] Uçtan uca data pipeline testlerini tamamla

## Sıradaki İş

1. **Gerçek incremental BIST + TEFAS smoke testlerini çalıştır ve watermark/overlap davranışını doğrula.**
2. Missing data / outlier / source-quality kontrollerini genişlet.
3. Temiz data contract'ı son haline getir ve uçtan uca data pipeline testlerini tamamla.
4. Ardından Faz 3 — Technical Analysis Engine'e geç.

## Yeni Sohbette Devam Etme Kuralı

Yeni bir sohbette projeye devam ederken bu dosya önce okunmalı. Özellikle **Güncel Durum**, **Tamamlananlar**, **aktif fazın taskları** ve **Sıradaki İş** bölümleri esas alınmalı. Bir task tamamlandığında bu dosya aynı çalışma kapsamında güncellenmeli.

> Kural: Her faz tamamlandığında kısa özet, alınan teknik/ürün kararları, tamamlanan tasklar ve sıradaki faz/tasklar burada tutulur. Böylece proje farklı sohbetlerde kaldığı yerden sürdürülebilir.
