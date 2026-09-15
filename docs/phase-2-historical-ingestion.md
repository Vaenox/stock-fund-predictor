# Faz 2 — Historical Ingestion

## Amaç

Provider'dan alınan günlük tarihsel veriyi canonical modele dönüştürüp PostgreSQL/TimescaleDB'ye güvenli ve tekrar çalıştırılabilir şekilde yazmak.

## Pipeline

```text
Provider
  ↓
Historical Ingestion Service
  ↓
Normalizer
  ↓
Validator
  ↓
Canonical PostgreSQL / TimescaleDB
```

## Tasarım kararları

- Ingestion yalnızca mevcut `assets` kaydı ve `asset_provider_mappings` eşleşmesi üzerinden çalışır.
- Provider sembolü ile canonical asset arasında doğrulanmamış bir bağ kabul edilmez.
- Provider'dan gelen kayıtlar önce normalize, sonra validate edilir.
- Aynı `(asset_id, trading_date)` veya `(asset_id, pricing_date)` anahtarı tekrar geldiğinde PostgreSQL `ON CONFLICT DO UPDATE` ile canonical kayıt güncellenir.
- Böylece tarihsel import tekrar çalıştırıldığında duplicate satır oluşmaz.
- Batch yazımı tek transaction içinde yapılır.
- DB write başarısız olursa transaction rollback edilir ve hata üst katmana aktarılır.
- `source_provider`, `source_timestamp` ve `ingested_at` alanları korunarak provenance kaybolmaz.

## Kapsam

Hazır olanlar:

- Stock historical ingestion
- Fund historical ingestion
- Asset type kontrolü
- Provider mapping kontrolü
- Date range kontrolü
- Normalizer + validator entegrasyonu
- PostgreSQL upsert
- Transaction rollback
- Unit-level orchestration tests

Henüz kapsam dışında:

- Gerçek Matriks endpoint smoke test
- Büyük tarihsel dataset için chunk/pagination
- Retry/backoff/rate-limit yönetimi
- Incremental günlük update scheduler
- Missing/outlier/source-quality kontrollerinin genişletilmiş versiyonu

## Gerçek veri bağlantısı

Matriks adapter endpoint/header/payload bilgilerini configuration üzerinden alacak şekilde tasarlandı. Gerçek endpoint sözleşmesi ve erişim bilgileri sağlandığında ingestion service doğrudan bu adapter üzerinden çalıştırılabilir.
