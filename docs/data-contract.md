# Market Data Contract

Bu doküman, Faz 2 market-data katmanının canonical veri sözleşmesidir. Provider'lardan gelen ham veri önce normalize edilir, ardından validator tarafından bu sözleşmeye göre kontrol edilerek PostgreSQL'e yazılır.

## 1. Genel kurallar

- Tüm varlıklar `assets` üzerinden canonical asset kimliği ile temsil edilir.
- Provider sembolleri `asset_provider_mappings` ile canonical asset'e bağlanır.
- Tarihler timezone'suz `date` olarak canonical hale getirilir.
- Gelecek tarihli market verisi kabul edilmez.
- Aynı asset ve aynı market tarihi birden fazla canonical satır üretemez.
- Ingestion işlemi PostgreSQL transaction'ı içinde yapılır; conflict durumunda canonical anahtar üzerinden upsert uygulanır.
- `source_provider` zorunludur ve ham verinin hangi provider'dan geldiğini belirtir.
- `ingested_at` zorunludur ve verinin sistem tarafından yazıldığı UTC zamanını belirtir.
- `source_timestamp` provider'ın olay/üretim zamanını taşıyabildiği durumda doldurulur; provider bunu güvenilir biçimde sağlamıyorsa `NULL` kalabilir.

## 2. Asset sözleşmesi

`assets` temel kimlik tablosudur.

| Alan | Kural |
|---|---|
| `asset_type` | `STOCK` veya `FUND` |
| `canonical_symbol` | Zorunlu, benzersiz canonical sembol |
| `name` | Zorunlu display adı |
| `currency` | MVP'de varsayılan `TRY` |
| `status` | `ACTIVE` / diğer tanımlı durumlar |

Provider sembolü canonical sembolden farklı olabilir; bu durum mapping tablosunda tutulur.

## 3. BIST stock daily bar

Canonical tablo: `stock_daily_bars`

### Zorunlu alanlar

- `asset_id`
- `trading_date`
- `open`
- `high`
- `low`
- `close`
- `source_provider`
- `ingested_at`

### İsteğe bağlı alanlar

- `adjusted_close`
- `volume`
- `turnover`
- `source_timestamp`

### Kurallar

- `open`, `high`, `low`, `close` sıfırdan büyük olmalıdır.
- `low <= open <= high` ve `low <= close <= high` olmalıdır.
- `volume` mevcutsa `>= 0` olmalıdır.
- `turnover` mevcutsa `>= 0` olmalıdır.
- `adjusted_close` mevcutsa `> 0` olmalıdır.
- `trading_date` bugünden ileri olamaz.
- Canonical benzersizlik: `(asset_id, trading_date)`.
- Aynı anahtar yeniden geldiğinde satır çoğaltılmaz; provider alanları ve ingestion metadata'sı upsert edilir.

## 4. TEFAS fund daily price

Canonical tablo: `fund_daily_prices`

### Zorunlu alanlar

- `asset_id`
- `pricing_date`
- `unit_price`
- `source_provider`
- `ingested_at`

### İsteğe bağlı alanlar

- `total_net_assets`
- `source_timestamp`

### Kurallar

- `unit_price > 0` olmalıdır.
- `total_net_assets` mevcutsa `>= 0` olmalıdır.
- `pricing_date` bugünden ileri olamaz.
- Canonical benzersizlik: `(asset_id, pricing_date)`.
- Aynı anahtar yeniden geldiğinde satır çoğaltılmaz; provider alanları ve ingestion metadata'sı upsert edilir.

## 5. Provider-specific kuralları

### BIST / borsapy

- Provider adı canonical DB kayıtlarında `borsapy` olarak tutulur.
- Canlı quote/candle verisi günlük OHLCV'den ayrı live tablolarına gider.
- Provider'dan gelen canlı event zamanı `source_timestamp` / `occurred_at` olarak korunabildiği ölçüde saklanır.
- Geçersiz TradingView sembolleri universe katmanında filtrelenir veya canonical alias ile normalize edilir.

### TEFAS

- Provider adı canonical DB kayıtlarında `tefas` olarak tutulur.
- Fon fiyatları günlük pricing datumudur; tick-level market data olarak modellenmez.
- TEFAS public JSON'daki `fonKodu`, `tarih`, `fiyat` ve mevcutsa portföy büyüklüğü canonical alanlara normalize edilir.
- Aktif/current universe discovery günlük veri penceresinden yapılır; kapanmış/işlem görmeyen eski fon kodları güncel aktif evrenin dışında kabul edilir.

## 6. Veri kalitesi semantiği

Kalite kontrolleri iki seviyelidir.

### Bloklayıcı ihlaller

Bunlar ingestion veya quality validation sonucunu başarısız yapar:

- duplicate canonical key
- geçersiz OHLC ilişkisi
- sıfır/negatif stock fiyatı
- negatif volume
- sıfır/negatif fund unit price
- negatif fund total net assets
- aynı kalite penceresinde birden fazla `source_provider`

### Uyarı / teşhis

Bunlar doğrudan ingestion'ı başarısız saydırmaz:

- beklenen piyasa işlem gününde veri bulunmaması
- aşırı günlük getiri

Eksik gün değerlendirmesi hafta sonunu otomatik olarak beklenen işlem günü saymaz; resmi piyasa kapanış günleri takvimden çıkarılır. Hisse/fon provider'ının takvim davranışı ayrıca izlenir.

## 7. Source provenance

Her canonical daily record için:

- `source_provider`: kaynağın canonical adı
- `source_timestamp`: provider event/üretim zamanı biliniyorsa
- `ingested_at`: backend'in UTC ingestion zamanı

`source_timestamp` ile `ingested_at` aynı kavram değildir ve birbirinin yerine kullanılmaz.

## 8. Incremental ingestion sözleşmesi

Incremental job:

1. İlgili asset için DB'deki `MAX(trading_date)` veya `MAX(pricing_date)` değerini watermark kabul eder.
2. Watermark yoksa `bootstrap_days` geçmişe giderek bootstrap penceresi oluşturur.
3. Watermark varsa `overlap_days` kadar geriye giderek düzeltilebilir son günleri yeniden çeker.
4. Provider verisi canonical validator'dan geçer.
5. Canonical anahtar üzerinden upsert yapılır.
6. Watermark yeni persisted son tarihle ilerler.

Bu nedenle başarılı bir overlap çalıştırmasında DB satır sayısının artmaması beklenen davranıştır.

## 9. Quality report ile ilişki

`quality.py` raporları bu contract'ın runtime gözlem katmanıdır. `ok=False` yalnızca bloklayıcı yapısal ihlaller olduğunda oluşur. Missing business dates ve extreme returns teşhis amaçlı raporlanır.

## 10. Faz 2 kabul kriterleri

Data layer, Faz 2'yi tamamlamak için aşağıdaki koşulları sağlamalıdır:

- BIST gerçek veri ingestion ve live persistence doğrulanmış olmalı.
- TEFAS gerçek bulk ve incremental ingestion doğrulanmış olmalı.
- Duplicate/upsert davranışı gerçek DB üzerinde doğrulanmış olmalı.
- BIST ve TEFAS quality kontrolü provider/source kurallarıyla çalışmalı.
- Canonical field ve validation kuralları bu contract ile uyumlu olmalı.
- Uçtan uca pipeline testleri ingestion -> validation -> persistence -> quality zincirini doğrulamalıdır.
