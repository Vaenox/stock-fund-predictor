# Proje İlerleme Kaydı

Bu dosya, fazlarda alınan kararların, tamamlanan işlerin ve sıradaki taskların kısa bir özetini tutar. Yeni bir sohbette projeye devam ederken önce bu dosya referans alınmalıdır.

## Güncel Durum

- Aktif faz: **Faz 1 — Product Design / Ürün Tanımı**
- Son tamamlanan faz: **Proje iskeleti ve roadmap hazırlığı**
- Sonraki hedef: Faz 1 ürün spesifikasyonunu netleştirip Faz 2 veri altyapısına geçmek.

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

## Faz 1 — Product Design

### Alınan Ürün Kararları
- İlk pazar: **BIST**.
- İlk varlıklar: **BIST hisseleri + Türkiye'deki yatırım fonları**.
- Gelecekte: NASDAQ/NYSE ve ETF desteği.
- İlk tahmin ufku: **5 işlem günü**.
- İlk ML hedefi: **5 işlem günü sonunda ileri getiri %3'ün üzerindeyse pozitif sınıf**.
- İlk model ailesi: **XGBoost**.
- Kullanıcıya ana sinyal: **BUY / HOLD / SELL**.
- Model olasılığı tek başına karar olarak kullanılmayacak; teknik skor ve risk skoru ile birlikte değerlendirilecek.
- Öncelik sırası: **veri kalitesi → feature engineering → backtest doğruluğu → model performansı → UI**.
- Gerçek para ile otomatik işlem başlangıç kapsamına alınmayacak; önce paper trading yapılacak.

### Faz 1 Taskları
- [x] Ürün kapsamını belirle
- [x] İlk pazar ve varlık türlerini belirle
- [x] Tahmin ufkunu belirle
- [x] İlk ML hedefini belirle
- [x] İlk model ailesini belirle
- [x] BUY/HOLD/SELL sinyal yaklaşımını belirle
- [x] Temel riskleri ve geliştirme önceliğini belirle
- [ ] Ürün spesifikasyonunu ayrıntılı olarak yaz
- [ ] Ekranların ve temel kullanıcı akışlarının kesinleştirilmesi
- [ ] Faz 1 kabul kriterlerinin tamamlanması

## Sıradaki İş

1. Faz 1 ürün spesifikasyonunu tamamla.
2. Dashboard, asset detail, predictions, watchlist ve settings ekranlarının MVP kapsamını netleştir.
3. Faz 1'i kapat ve kaydı güncelle.
4. Faz 2'ye geç: BIST hisse/fon veri kaynaklarını ve veri şemasını belirle.
5. Veri sağlayıcı seçimini yaptıktan sonra ingestion pipeline ve PostgreSQL/TimescaleDB şemasını oluştur.

## Yeni Sohbette Devam Etme Kuralı

Yeni bir sohbette projeye devam ederken bu dosya önce okunmalı. Özellikle **Güncel Durum**, **Tamamlananlar**, **Faz 1 Taskları** ve **Sıradaki İş** bölümleri esas alınmalı. Bir task tamamlandığında bu dosya aynı commit içinde güncellenmeli.

> Kural: Yapılan her faz için kısa bir özet, alınan teknik/ürün kararları, tamamlanan tasklar ve sıradaki tasklar burada tutulur. Böylece proje farklı sohbetlerde kaldığı yerden sürdürülebilir.
