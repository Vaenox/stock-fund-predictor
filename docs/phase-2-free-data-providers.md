# Faz 2 — Ücretsiz Veri Sağlayıcı Stratejisi

## Amaç

MVP ve geliştirme aşamasında ücretli BIST veri sağlayıcısına bağımlı kalmadan **tüm BIST hisse evrenini dinamik olarak izlemek** ve fonların açıklanan günlük fiyatlarını toplamak.

## Karar

### BIST hisseleri — borsapy / TradingView WebSocket

- BIST ana provider'ı artık `borsapy`dir.
- `borsapy.companies()` ile BIST şirket evreni otomatik keşfedilecektir.
- `borsapy.TradingViewStream()` persistent WebSocket ile quote ve intraday candle akışı sağlayacaktır.
- MVP'de streaming katmanı tüm aktif BIST sembollerine toplu subscription uygulayacaktır.
- Ücretsiz TradingView BIST verisinin varsayılan olarak yaklaşık 15 dakika gecikmeli olabildiği dikkate alınacaktır.
- Gerçek zamanlı BIST kullanımının ayrıca TradingView hesabı/veri paketi gerektirdiği kabul edilecektir.
- `yfinance` artık live provider değildir; yalnızca historical/backfill veya çapraz kontrol yardımcısıdır.
- `borsapy` projesinin kendi repository notunda kişisel/eğitim kullanım sınırı bulunduğu için public/ticari ürün aşamasında lisans yeniden değerlendirilecektir.

### Türkiye yatırım fonları — TEFAS resmi JSON API

- Fon provider'ı doğrudan TEFAS'ın güncel JSON API uçlarını kullanacaktır.
- Fon fiyatı gün içinde tick-by-tick değişmediği için WebSocket gerekli değildir.
- Günlük açıklanan fiyatlar scheduled ingestion ile alınacaktır.
- Uzun tarih aralıkları için chunking, rate-limit ve endpoint değişikliğine dayanıklılık korunacaktır.
- Fon evreni `list_symbols()` ile toplu keşfedilebilecektir.

## Veri akışı

```text
BIST:
TradingView WebSocket
        ↓
     borsapy
        ↓
  Live Quote/Candle
        ↓
 Normalizer → Validator
        ↓
 Redis → TimescaleDB

FON:
TEFAS JSON API
        ↓
  TefasProvider
        ↓
 Daily Fund Price
        ↓
 Normalizer → Validator
        ↓
 PostgreSQL/TimescaleDB
```

## Provider rolleri

```text
BorsapyProvider
- BIST symbol discovery
- historical daily OHLCV
- live quote
- live candle
- WebSocket subscription lifecycle

TefasProvider
- all fund discovery
- current/daily fund data
- historical fund prices
- rate-limit/chunking

MatriksRestProvider / future FinnetProvider
- optional premium fallback
```

## Lisans / üretim notu

Ücretsiz erişim teknik olarak mümkün olsa bile veri kaynağının kullanım şartları ticari yeniden dağıtım hakkı anlamına gelmez. MVP/geliştirme sürecinde provider kısıtları açıkça dokümante edilecek; public/ticari ürüne geçmeden önce veri lisansı yeniden doğrulanacaktır.
