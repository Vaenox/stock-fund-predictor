# Faz 6 — Prediction API Contract

## Amaç

Prediction persistence katmanını FastAPI üzerinden yalnızca okuma tarafında expose etmek.

Bu aşamada API:
- canonical asset metadata okur,
- son persisted prediction'ı döner,
- persisted prediction history'yi tarih/pagination filtreleriyle döner.

Prediction üretme ve DB'ye yeni prediction yazma endpointi bu aşamada eklenmez. Üretim servisi mevcut haliyle provider/veri yükleme orkestrasyonundan ayrıdır; önce read API contractının stabil olması tercih edilir.

## Endpointler

### GET /health

Basit uygulama health endpointidir.

Başarılı yanıt:

```json
{
  "status": "ok"
}
```

### GET /api/v1/assets/{symbol}

Canonical asset metadata döner.

`symbol` normalize edilerek uppercase kullanılır.

Örnek:

```json
{
  "id": "uuid",
  "asset_type": "STOCK",
  "canonical_symbol": "THYAO",
  "name": "Türk Hava Yolları",
  "isin": null,
  "exchange": "BIST",
  "currency": "TRY",
  "status": "ACTIVE"
}
```

404:
- Asset canonical universe içinde bulunmuyorsa.

### GET /api/v1/assets/{symbol}/predictions/latest

Asset için generated prediction kayıtları arasından en güncel prediction'ı döner.

Sıralama:
1. `prediction_date DESC`
2. `generated_at DESC`

Prediction response:
- audit id
- asset id
- prediction/date/data-as-of
- horizon ve target threshold
- model family/version
- feature representation
- ML probability
- Technical Score
- Risk Score / adjustment
- final Signal Score
- target weight
- quality/stale metadata
- provider
- reasons
- created_at

404:
- Asset bulunmuyorsa.
- Asset var fakat prediction history yoksa.

### GET /api/v1/assets/{symbol}/predictions

Persisted prediction history'yi newest-first döner.

Query parametreleri:

| Parametre | Tip | Default | Sınır |
|---|---|---:|---|
| `start_date` | date | null | - |
| `end_date` | date | null | - |
| `limit` | int | 100 | 1..500 |
| `offset` | int | 0 | >=0 |

`start_date > end_date` durumunda 400 döner.

Yanıt doğrudan prediction listesi şeklindedir. Toplam kayıt sayısı bu aşamada ayrı bir count query ile expose edilmez.

## Auth kararı

Bu read-only contract içinde kullanıcı kimliği veya watchlist ilişkisi endpoint parametrelerine eklenmez.

Auth daha sonra Supabase Auth üzerinden ayrı dependency/authorization katmanında ele alınacak. Kullanıcı watchlist'i asset/prediction persistence modelinin içine gömülmeyecek.

## Prediction generation kararı

Bu aşamada:
- `POST /api/v1/assets/{symbol}/predictions` yok.
- API layer provider çağrısı başlatmıyor.
- API layer prediction service'e raw dataframe taşımıyor.

İleride generation endpointi eklenecekse, orchestration'ın ayrı bir application service üzerinden yapılması ve persistence'ın append-only contractının korunması gerekiyor.

## Response precision

API response schema'daki sayısal alanlar frontend tüketimi için JSON number olarak expose edilir. PostgreSQL tarafındaki Numeric saklama contractı ve internal Decimal kullanımı değiştirilmez.
