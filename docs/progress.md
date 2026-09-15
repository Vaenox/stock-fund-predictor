# Proje İlerleme Kaydı

Bu dosya, fazlarda alınan kararların, tamamlanan işlerin ve sıradaki taskların kısa bir özetini tutar. Yeni bir sohbette projeye devam ederken önce bu dosya referans alınmalıdır.

## Güncel Durum

- Aktif faz: **Faz 2 — Data Infrastructure / Veri Altyapısı**
- Son tamamlanan faz: **Faz 1 — Product Design / Ürün Tanımı**
- Faz 1 ürün spesifikasyonu: `docs/phase-1-product-spec.md`
- Faz 2 veri kaynakları araştırması: `docs/phase-2-data-sources.md`
- Faz 2 canonical veri modeli: `docs/phase-2-data-model.md`
- Sonraki hedef: ilk gerçek provider adapter'ı ve ingestion pipeline.

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
- [x] Öncelikli BIST sağlayıcısı olarak Matriks belirlendi; Finnet alternatif olarak kaydedildi.
- [x] Öncelikli fon kaynağı olarak TEFAS belirlendi; SPK ikincil doğrulama kaynağı olarak kaydedildi.
- [x] Provider abstraction yaklaşımı belirlendi.
- [x] Araştırma `docs/phase-2-data-sources.md` dosyasına işlendi.
- [x] Canonical asset, provider mapping, stock OHLCV ve fund daily price veri modeli tasarlandı.
- [x] Veri kuralları ve temel bütünlük kuralları dokümante edildi.
- [x] SQLAlchemy 2.x + PostgreSQL/psycopg 3 backend veri erişim yaklaşımı seçildi.
- [x] İlk SQLAlchemy ORM modelleri oluşturuldu.
- [x] İlk Pydantic canonical veri giriş şemaları oluşturuldu.
- [x] Backend temel bağımlılıkları `backend/requirements.txt` içine eklendi.
- [x] Alembic migration altyapısı oluşturuldu.
- [x] Initial PostgreSQL migration'ı oluşturuldu.
- [x] TimescaleDB kuruluysa stock/fund time-series tablolarını hypertable'a dönüştüren koşullu migration eklendi.
- [x] ORM modellerinin merkezi export'u oluşturuldu.
- [x] Provider interface'i oluşturuldu.
- [x] Provider-specific stock/fund kayıt tipleri oluşturuldu.
- [x] Stock/fund normalizer katmanı oluşturuldu.
- [x] Canonical veri validator katmanı oluşturuldu.
- [x] Duplicate ve geleceğe tarihli kayıt kontrolleri eklendi.
- [x] Normalizer/validator davranışı için backend testleri eklendi.

### Faz 2 Taskları
- [x] BIST hisse veri kaynaklarını araştır ve teknik adayları belirle
- [x] Türkiye yatırım fonu veri kaynaklarını araştır ve teknik adayları belirle
- [x] Veri lisansı / kullanım koşulları için temel araştırmayı yap
- [ ] Ticari sağlayıcı fiyat/teklif ve nihai lisans koşullarını doğrula
- [ ] Historical data kapsamını kesinleştir
- [x] Hisse OHLCV canonical veri şemasını tasarla
- [x] Fon veri şemasını tasarla
- [x] Asset/symbol master şemasını tasarla
- [x] PostgreSQL / TimescaleDB migration altyapısını oluştur
- [x] Initial market data migration'ını yaz
- [x] Provider interface'i kodla
- [x] Normalizer + validator katmanını kodla
- [ ] İlk provider adapter'ını oluştur
- [ ] Historical ingestion pipeline oluştur
- [ ] Incremental update pipeline oluştur
- [ ] Veri doğrulama kurallarını tamamla
- [ ] Missing data / duplicate / outlier kontrollerini tamamla
- [ ] Temiz veri sözleşmesini (data contract) tanımla
- [x] Provider/validator temel testlerini yaz
- [ ] Tam veri pipeline testlerini yaz

## Sıradaki İş

1. Matriks adapter'ı için gerçek API sözleşmesini netleştir.
2. Provider credentials/configuration katmanını ekle.
3. Matriks stock history adapter'ını kodla.
4. Adapter çıktısını normalizer + validator üzerinden geçir.
5. Database repository/upsert katmanını oluştur.
6. Historical ingestion pipeline'ını oluştur.
7. Sonrasında incremental daily update ve veri kalite kontrollerine geç.

## Yeni Sohbette Devam Etme Kuralı

Yeni bir sohbette projeye devam ederken bu dosya önce okunmalı. Özellikle **Güncel Durum**, **Tamamlananlar**, **aktif fazın taskları** ve **Sıradaki İş** bölümleri esas alınmalı. Bir task tamamlandığında bu dosya aynı çalışma kapsamında güncellenmeli.

> Kural: Her faz tamamlandığında kısa özet, alınan teknik/ürün kararları, tamamlanan tasklar ve sıradaki faz/tasklar burada tutulur. Böylece proje farklı sohbetlerde kaldığı yerden sürdürülebilir.
