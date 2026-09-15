# Faz 2 — Canonical Data Model

## Amaç

Veri sağlayıcılarından gelen hisse ve fon verisini provider'dan bağımsız, ML/backtest süreçlerinin doğrudan kullanabileceği canonical bir modele dönüştürmek.

## Temel karar

Veri akışı:

```text
Provider → Adapter → Normalizer → Validator → Canonical DB
```

Canonical kimlik ile provider kimliği birbirinden ayrılır. Böylece Matriks, Finnet veya gelecekte başka bir sağlayıcı aynı varlığa bağlanabilir.

## 1. Asset Master

`assets` tablosu sistemdeki finansal varlığın canonical kimliğidir.

| Alan | Tip | Açıklama |
|---|---|---|
| id | UUID | Primary key |
| asset_type | enum | STOCK / FUND |
| canonical_symbol | varchar(32) | THYAO, AAK vb. |
| name | varchar(255) | Varlık adı |
| isin | varchar(32), nullable | ISIN varsa |
| exchange | varchar(32), nullable | BIST vb. |
| currency | varchar(8) | TRY vb. |
| status | enum | ACTIVE / INACTIVE |
| created_at | timestamptz | Oluşturulma zamanı |
| updated_at | timestamptz | Son güncelleme |

`canonical_symbol` global sistem kimliği olarak kullanılacak; provider sembolü canonical tabloya gömülmeyecek.

## 2. Provider Mapping

`asset_provider_mappings` canonical asset ile dış sağlayıcıdaki sembolü eşler.

| Alan | Tip | Açıklama |
|---|---|---|
| id | UUID | Primary key |
| asset_id | UUID | FK → assets |
| provider | varchar(32) | matriks / finnet / tefas |
| provider_symbol | varchar(128) | Sağlayıcı sembolü |
| is_primary | boolean | Bu provider'ın aktif ana eşleşmesi |
| first_seen_at | timestamptz | İlk görülme zamanı |
| last_seen_at | timestamptz | Son görülme zamanı |

Aynı canonical asset birden fazla provider'a bağlanabilir.

## 3. Stock Daily OHLCV

`stock_daily_bars` günlük hisse zaman serisidir.

| Alan | Tip | Açıklama |
|---|---|---|
| asset_id | UUID | FK → assets |
| trading_date | date | Borsa işlem günü |
| open | numeric(20,8) | Açılış |
| high | numeric(20,8) | En yüksek |
| low | numeric(20,8) | En düşük |
| close | numeric(20,8) | Kapanış |
| adjusted_close | numeric(20,8), nullable | Temettü/split düzeltilmiş kapanış |
| volume | numeric(24,4), nullable | İşlem hacmi |
| turnover | numeric(24,4), nullable | İşlem tutarı |
| source_provider | varchar(32) | Canonical verinin kaynağı |
| source_timestamp | timestamptz, nullable | Kaynak zaman bilgisi |
| ingested_at | timestamptz | Sisteme alınma zamanı |

Primary key: `(asset_id, trading_date)`.

İlk sürümde canonical seri tekilleştirilir; provider değişimi aynı gün için duplicate üretmez. Ham provider payload'ları ileride ayrı raw ingestion katmanında saklanabilir.

## 4. Fund Daily Price

Fonlarda hisse OHLCV modeli kullanılmayacak. Temel seri günlük birim pay/NAV değeridir.

`fund_daily_prices`:

| Alan | Tip | Açıklama |
|---|---|---|
| asset_id | UUID | FK → assets |
| pricing_date | date | Fon fiyatının geçerli olduğu tarih |
| unit_price | numeric(20,8) | Birim pay fiyatı |
| total_net_assets | numeric(24,4), nullable | Fon toplam net varlığı |
| source_provider | varchar(32) | Veri kaynağı |
| source_timestamp | timestamptz, nullable | Kaynak zaman bilgisi |
| ingested_at | timestamptz | Sisteme alınma zamanı |

Primary key: `(asset_id, pricing_date)`.

## 5. Veri kuralları

### Stock OHLCV

- `open`, `high`, `low`, `close` sıfırdan büyük olmalı.
- `high >= max(open, close, low)` olmalı.
- `low <= min(open, close, high)` olmalı.
- `volume` ve `turnover` negatif olamaz.
- Aynı asset + trading_date ikinci kez canonical tabloya yazılmamalı.
- Gelecek tarihli kayıt kabul edilmemeli.

### Fund price

- `unit_price > 0` olmalı.
- Aynı asset + pricing_date ikinci kez canonical tabloya yazılmamalı.
- Gelecek tarihli kayıt kabul edilmemeli.

## 6. Zaman serisi kararı

`stock_daily_bars` ve `fund_daily_prices` zaman serisi tablolarıdır. PostgreSQL üzerinde tutulacak ve TimescaleDB kullanıldığında uygun migration aşamasında hypertable'a dönüştürülecek.

ORM tarafında SQLAlchemy 2.x kullanılacak. PostgreSQL bağlantısı için psycopg 3 tercih edilecek. SQLAlchemy'nin güncel PostgreSQL dialect'i psycopg desteği sağlıyor. citeturn0search0

## 7. Gelecek tablolar

İlk canonical modelde özellikle kapsam dışında bırakılan yapılar:

- corporate_actions
- trading_calendar
- raw_provider_payloads
- data_quality_events
- fund_metadata detayları
- benchmark/index serileri

Bunlar ingestion ve validation pipeline'ı sırasında ihtiyaç sırasına göre eklenecek.
