# Faz 2 — Veri Kaynakları Araştırması

## Güncel Karar Özeti

MVP veri katmanı iki ücretsiz kaynak üzerinde çalışacaktır:

- **BIST hisseleri:** `borsapy` → TradingView WebSocket tabanlı streaming.
- **Türkiye yatırım fonları:** doğrudan **TEFAS resmi JSON API**.
- **Historical/backfill yardımcı kaynağı:** ihtiyaç halinde `yfinance`.
- **Premium opsiyonlar:** Matriks / Finnet provider katmanında tutulacak, ancak MVP'nin çalışması bunlara bağlı olmayacak.

Bu seçimle hedefimiz tek bir sembol değil, **BIST hisse evreninin tamamını otomatik keşfedip toplu izlemek** ve fon tarafında TEFAS'tan geniş fon evrenini düzenli olarak güncellemektir.

## 1. BIST Hisse Verisi — borsapy

`borsapy`, BIST şirketlerini listeleme (`companies()`), çoklu hisse erişimi ve TradingView persistent WebSocket streaming desteği sağlıyor. Streaming katmanı quote ve intraday OHLCV/mum güncellemelerini callback/cached quote modeliyle sunuyor. Varsayılan TradingView BIST verisi yaklaşık 15 dakika gecikmeli; gerçek zamanlı BIST için TradingView hesabı ve ilgili BIST veri paketi gerekiyor.

Kaynak: https://github.com/saidsurucu/borsapy

### MVP kullanım şekli

```text
borsapy
   ↓
companies() → BIST sembol evreni
   ↓
TradingViewStream
   ↓
subscribe(all symbols)
   ↓
quote/candle callback
   ↓
Normalizer
   ↓
Validator
   ↓
Redis + PostgreSQL/TimescaleDB
```

### Neden borsapy?

- Tek tek sembol seçmeye bağımlı değiliz.
- BIST şirket evrenini keşfetme desteği var.
- Persistent WebSocket ile sürekli quote akışı var.
- 1m/5m/15m/30m/1h/... candle akışı alınabiliyor.
- Python backend'e doğrudan oturuyor.
- Provider abstraction sayesinde ileride Matriks/Finnet'e geçiş mümkün.

### Önemli kısıt

`borsapy` deposu kişisel/eğitim kullanımını hedeflediğini ve ticari kullanım için ayrı lisans gerektiğini belirtiyor. Bu nedenle ücretsiz provider seçimi **MVP / kişisel-geliştirme kullanımına** uygun kabul ediliyor; public/ticari ürün aşamasında lisanslama yeniden değerlendirilecek.

## 2. Türkiye Yatırım Fonları — TEFAS

Fon tarafında intraday tick verisi gerekmiyor. Fon birim fiyatı günlük oluştuğu için hedefimiz tüm uygun fonları düzenli aralıklarla çekmek ve açıklanan son fiyatı canonical veride güncel tutmak.

Güncel açık kaynak istemciler, 2026'da yenilenen TEFAS sitesinin resmi JSON endpointlerini kullandığını ve authorization/login/API key gerekmediğini gösteriyor. Özellikle `fonGnlBlgSiraliGetir` fon bilgi/fiyat verisi için, `dagilimSiraliGetirT` ise portföy dağılımı için kullanılıyor. Uzun tarih aralıklarında rate-limit nedeniyle istekleri parçalara bölmek gerekiyor.

Kaynaklar:
- https://github.com/mirzazad/pytefas
- https://github.com/eneshenderson/Tefas-API

Projede fon adapterı doğrudan TEFAS JSON endpointlerini kullanacak şekilde tutulmuştur; böylece üçüncü taraf servisimizin uptime'ına bağımlı kalmayız.

## 3. Historical / Backfill

`yfinance` yalnızca historical/backfill ve veri karşılaştırması için yardımcı provider olarak tutulacaktır. Canlı BIST streaming'in ana kaynağı değildir.

## 4. Premium Provider'lar

Matriks ve Finnet tamamen kaldırılmıyor. Provider abstraction içinde opsiyonel premium adapter olarak kalabilirler.

Avantajı:

```text
Ücretsiz MVP
    ↓
borsapy / TEFAS
    ↓
Aynı canonical model
    ↓
İleride premium provider
    ↓
Sadece adapter değişimi
```

## 5. Lisans ve Kullanım

Borsa İstanbul piyasa verisinin lisanslı dağıtım yapısı bulunduğunu belirtiyor. Bu nedenle ücretsiz erişim ile **ticari yeniden dağıtım hakkı** birbirinden ayrı değerlendirilmelidir.

MVP aşamasında:
- Ücretsiz kaynaklarla kişisel/geliştirme kullanımına odaklanılacak.
- Provider kullanım şartları repository dokümantasyonunda açık tutulacak.
- Veri kaynağı/provenance canonical kayıtlarda tutulacak.
- Public/ticari sunumdan önce veri lisansı ayrıca doğrulanacak.

## 6. Güncel Provider Mimarisi

```text
                         Provider Layer
                              │
             ┌────────────────┴────────────────┐
             │                                 │
   BIST Stock Provider                  Fund Provider
             │                                 │
      borsapy / TV WS                    TEFAS JSON API
             │                                 │
             └────────────────┬────────────────┘
                              ↓
                         Normalizer
                              ↓
                         Validator
                              ↓
                  Redis + PostgreSQL/TSDB
                              ↓
                    Technical / ML Engine
```

## 7. Provider Sorumlulukları

### BorsapyProvider

- `list_symbols()` → tüm BIST şirket evreni
- `get_symbol_metadata()`
- `get_daily_history()` → historical/backfill
- `get_latest_price()`
- `connect_stream()`
- `subscribe(symbols)`
- `get_live_quote()`
- `on_any_quote(callback)`
- `disconnect_stream()`
- `health_check()`

### TefasProvider

- `list_symbols()` → güncel fon evreni
- `get_symbol_metadata()`
- `get_fund_history()`
- `health_check()`
- rate-limit/chunking yönetimi

## 8. Faz 2 Güncel Sonraki Adımlar

1. borsapy ile tüm BIST sembollerini keşfet ve symbol master'a aktar.
2. TradingViewStream için toplu subscription yöneticisi oluştur.
3. Live quote/candle eventlerini canonical canlı veri DTO'larına dönüştür.
4. Redis pub/sub ile canlı akışı backend içinde dağıt.
5. TEFAS günlük fon güncellemesini scheduled ingestion ile çalıştır.
6. BIST live verisini TimescaleDB'de gerekli intraday tablolara yaz.
7. Data-quality / staleness / reconnect kontrollerini ekle.
8. Historical backfill ile live stream arasında aynı canonical symbol/provenance yapısını doğrula.
9. Premium provider'ları yalnızca opsiyonel fallback olarak tut.
