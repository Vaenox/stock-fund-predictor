# Proje İlerleme Kaydı

Bu dosya, fazlarda alınan kararların, tamamlanan işlerin ve sıradaki taskların kısa bir özetini tutar. Yeni bir sohbette projeye devam ederken önce bu dosya referans alınmalıdır.

## Güncel Durum

- Aktif faz: **Faz 2 — Data Infrastructure / Veri Altyapısı**
- Son tamamlanan faz: **Faz 1 — Product Design / Ürün Tanımı**
- Faz 1 ürün spesifikasyonu: `docs/phase-1-product-spec.md`
- Sonraki hedef: BIST hisse ve Türkiye yatırım fonu verileri için güvenilir veri kaynaklarını ve veri şemasını belirlemek.

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

## Faz 2 — Data Infrastructure

### Tasklar
- [ ] BIST hisse veri kaynaklarını araştır ve seç
- [ ] Türkiye yatırım fonu veri kaynaklarını araştır ve seç
- [ ] Veri lisansı / kullanım koşullarını kontrol et
- [ ] Historical data kapsamını belirle
- [ ] Hisse OHLCV veri şemasını tasarla
- [ ] Fon veri şemasını tasarla
- [ ] PostgreSQL / TimescaleDB şemasını oluştur
- [ ] Historical ingestion pipeline oluştur
- [ ] Incremental update pipeline oluştur
- [ ] Veri doğrulama kurallarını oluştur
- [ ] Missing data / duplicate / outlier kontrollerini oluştur
- [ ] Temiz veri sözleşmesini (data contract) tanımla
- [ ] Veri pipeline testlerini yaz

## Sıradaki İş

1. BIST hisse veri kaynaklarını karşılaştır.
2. Türkiye yatırım fonu veri kaynaklarını karşılaştır.
3. Kaynakların güvenilirlik, geçmiş veri kapsamı, API erişimi, maliyet ve kullanım şartlarını değerlendir.
4. Veri kaynağı seçildikten sonra DB şemasını tasarla.
5. Historical ingestion pipeline ile Faz 2 implementasyonuna başla.

## Yeni Sohbette Devam Etme Kuralı

Yeni bir sohbette projeye devam ederken bu dosya önce okunmalı. Özellikle **Güncel Durum**, **Tamamlananlar**, **aktif fazın taskları** ve **Sıradaki İş** bölümleri esas alınmalı. Bir task tamamlandığında bu dosya aynı çalışma kapsamında güncellenmeli.

> Kural: Her faz tamamlandığında kısa özet, alınan teknik/ürün kararları, tamamlanan tasklar ve sıradaki faz/tasklar burada tutulur. Böylece proje farklı sohbetlerde kaldığı yerden sürdürülebilir.
