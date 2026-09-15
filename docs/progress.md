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
- Güncel hedef: Matriks test erişimini gerçek endpoint sözleşmesine bağlayıp ilk gerçek BIST historical veri setini PostgreSQL/TimescaleDB'ye almak.

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
- [x] Provider interface ve provider DTO'ları oluşturuldu.
- [x] Stock/fund normalizer katmanı oluşturuldu.
- [x] Future-date ve canonical duplicate validation kontrolleri oluşturuldu.
- [x] Matriks REST adapter iskeleti oluşturuldu.
- [x] Matriks adapter için configurable endpoint/header yaklaşımı oluşturuldu.
- [x] Matriks adapter parsing ve canonical validation testleri eklendi.
- [x] `httpx` ve `pytest` backend bağımlılıkları eklendi.
- [x] Historical stock/fund ingestion service oluşturuldu.
- [x] Ingestion öncesi asset type + provider mapping kontrolü eklendi.
- [x] Historical kayıtlar için PostgreSQL upsert (`ON CONFLICT DO UPDATE`) uygulandı.
- [x] Ingestion transaction rollback davranışı eklendi.
- [x] Historical ingestion orchestration testleri eklendi.
- [x] Historical ingestion tasarımı `docs/phase-2-historical-ingestion.md` dosyasına işlendi.

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
- [x] Normalizer katmanını kodla
- [x] Temel validator katmanını kodla
- [x] Matriks provider adapter iskeletini oluştur
- [x] Provider parsing / validation testlerini yaz
- [x] Historical ingestion pipeline servis katmanını oluştur
- [x] Ingestion asset/mapping güvenlik kontrollerini oluştur
- [x] Historical upsert + transaction rollback davranışını oluştur
- [x] Historical ingestion testlerini yaz
- [ ] Matriks gerçek API test erişimi ve endpoint sözleşmesini bağla
- [ ] Tek BIST sembolü üzerinde historical API smoke test çalıştır
- [ ] PostgreSQL/TimescaleDB'ye ilk gerçek tarihsel veri setini yaz
- [ ] Duplicate/upsert source provenance davranışını gerçek veriyle doğrula
- [ ] Incremental update pipeline oluştur
- [ ] Missing data / duplicate / outlier / source-quality kontrollerini genişlet
- [ ] Temiz veri sözleşmesini (data contract) son haline getir
- [ ] Uçtan uca veri pipeline testlerini yaz

## Sıradaki İş

1. Matriks API test erişimi + teknik dokümandaki gerçek endpoint/header/payload bilgilerini configuration'a geçir.
2. Tek BIST sembolü üzerinde historical API smoke test çalıştır.
3. PostgreSQL/TimescaleDB'ye ilk gerçek tarihsel veri setini yaz.
4. Duplicate/upsert ve source provenance davranışını gerçek veriyle doğrula.
5. Incremental update pipeline'ını oluştur.
6. Missing/outlier/source-quality kontrollerini ve uçtan uca pipeline testlerini genişlet.
7. Ticari lisans ve historical coverage konularını sağlayıcı görüşmesiyle kesinleştir.

## Yeni Sohbette Devam Etme Kuralı

Yeni bir sohbette projeye devam ederken bu dosya önce okunmalı. Özellikle **Güncel Durum**, **Tamamlananlar**, **aktif fazın taskları** ve **Sıradaki İş** bölümleri esas alınmalı. Bir task tamamlandığında bu dosya aynı çalışma kapsamında güncellenmeli.

> Kural: Her faz tamamlandığında kısa özet, alınan teknik/ürün kararları, tamamlanan tasklar ve sıradaki faz/tasklar burada tutulur. Böylece proje farklı sohbetlerde kaldığı yerden sürdürülebilir.
