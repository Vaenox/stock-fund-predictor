# Faz 2 — Provider Adapter Katmanı

## Amaç

Provider API'lerini uygulamanın canonical veri modeline bağlayan, provider değiştiğinde ingestion ve ML katmanlarını etkilemeyen bir adapter katmanı oluşturmak.

## Akış

```text
Matriks REST → MatriksRestProvider → ProviderStockBar → Normalizer → Validator → Canonical DB
```

## Matriks adapter kararı

`backend/app/data/providers/matriks.py` içinde `MatriksRestProvider` oluşturuldu.

Adapter şunları sağlar:

- configurable base URL
- configurable HTTP headers / authentication
- configurable endpoint path'leri
- `{symbol}`, `{start}`, `{end}` endpoint template parametreleri
- symbol metadata normalization
- günlük OHLCV parsing
- Decimal dönüşümü
- desteklenen tarih formatlarının canonical `date` tipine çevrilmesi
- source timestamp parsing
- ham provider satırının `raw` alanında korunması
- HTTP / JSON hatalarının `MatriksProviderError` olarak normalize edilmesi
- health check
- başlangıç/bitiş tarih aralığı kontrolü

## Neden endpoint'ler hard-code edilmedi?

Matriks resmi olarak REST API, tarihsel/grafik veri servisleri ve farklı veri kapsamları sunuyor; ancak servis kapsamı, erişim ve teknik API detayları satın alınan ürün/sözleşmeye göre belirleniyor.

Bu nedenle uygulamada tahmini endpoint veya auth şeması üretilmedi. Gerçek endpoint path'leri, header bilgileri ve response alan eşleşmeleri Matriks'in sağladığı teknik dokümandan configuration'a aktarılacak.

## Mevcut sınır

İlk adapter hisse OHLCV akışını hedefliyor. Fon tarafındaki Matriks adapter'ı, kullanılacak fon veri servisinin teknik sözleşmesi kesinleşene kadar etkinleştirilmeyecek. Fonlarda TEFAS öncelikli kaynak olarak korunuyor.

## Testler

- symbol normalization
- numeric/date conversion
- source timestamp parsing
- invalid date range rejection
- future date rejection
- duplicate canonical record rejection
- valid canonical stock bar acceptance

## Sonraki adım

1. Matriks API test erişimini ve teknik dokümanı temin et.
2. Gerçek endpoint/header/payload eşleşmelerini config'e geçir.
3. Tek bir BIST sembolü ile historical data smoke test çalıştır.
4. Historical ingestion service'i provider + normalizer + validator zincirine bağla.
5. PostgreSQL/TimescaleDB'ye ilk gerçek tarihsel veri setini yaz.
