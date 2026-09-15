# Faz 2 — Ücretsiz Veri Sağlayıcı Stratejisi

## Amaç

MVP ve geliştirme aşamasında ücretli BIST veri sağlayıcısına bağımlı kalmadan hisse/fon veri akışını çalıştırmak.

## Karar

### BIST hisseleri — Yahoo Finance / yfinance

- Yahoo Finance sembolü BIST için `.IS` ekiyle kullanılır; örneğin `THYAO` → `THYAO.IS`.
- `yfinance` günlük historical OHLCV verisini Python tarafında almak için kullanılacak.
- Bu provider geliştirme/kişisel kullanım için tasarlanmıştır.
- Yahoo'nun mevcut kullanım kuralları nedeniyle kamuya açık ticari bir veri servisi veya yeniden dağıtım katmanı olarak kabul edilmeyecek.
- Ürün ticari/public aşamaya geldiğinde lisanslı bir provider adapter'ı ile değiştirilecek.

### Türkiye yatırım fonları — TEFAS

- TEFAS'ın güncel fon veri sayfasının kullandığı JSON API uçları adapter içinde kullanılacak.
- Kimlik doğrulama/API key gerektirmeyen güncel endpoint davranışı esas alınacak.
- Tek çağrıda uzun tarih aralıkları için koruyucu 28 günlük chunking uygulanacak.
- Provider katmanı fiyat, tarih, fon kodu ve fon adını canonical modele dönüştürecek.
- Rate-limit ve endpoint değişiklikleri nedeniyle adapter kontrollü retry/validation ile kullanılacak.

## Veri akışı

```text
Yahoo Finance → Yahoo Adapter → Normalizer → Validator → PostgreSQL/TimescaleDB
TEFAS         → TEFAS Adapter → Normalizer → Validator → PostgreSQL/TimescaleDB
```

## Lisans / üretim notu

Borsa İstanbul resmi piyasa verisini gerçek zamanlı, gecikmeli ve günsonu olarak lisanslı veri dağıtım kuruluşları üzerinden dağıtıyor. Bu nedenle ücretsiz geliştirme kaynağı ile üretim/ticari veri dağıtımı aynı kabul edilmeyecek.

MVP'nin hedefi önce veri pipeline'ını ve modelleme altyapısını gerçek tarihsel veriyle çalıştırmak; daha sonra gereken lisanslı kaynak adapter'ını aynı interface'e takmak.
