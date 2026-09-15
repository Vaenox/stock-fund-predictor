# Faz 2 — Veri Kaynakları Araştırması

## Karar Özeti

MVP için veri katmanı iki ayrı kaynak ailesi üzerine kurulacaktır:

- **BIST hisseleri:** Öncelikli ticari veri sağlayıcı olarak Matriks Data değerlendirilecek.
- **Türkiye yatırım fonları:** Öncelikli kaynak olarak TEFAS'ın resmi veri/API altyapısı değerlendirilecek.
- **Alternatif BIST sağlayıcı:** Finnet Data Feed / Stock Expert API.
- **Alternatif fon sağlayıcı:** Finnet Fund Expert API.

Uygulama sağlayıcıya doğrudan bağımlı olmayacak. `DataProvider` benzeri bir abstraction katmanı kullanılacak; böylece sağlayıcı değişimi veya ikinci kaynağın eklenmesi mümkün olacak.

## 1. BIST Hisse Verisi

### Matriks Data

Matriks'in kurumsal veri servisleri REST API, XML Web Service ve MQTT/socket seçenekleri sunuyor. REST API tarafında BIST grafik/bar verileri ve çeşitli piyasa içerikleri sağlanıyor. Şirket ayrıca geçmiş ham veri ve grafik verileri sunduğunu belirtiyor.

Artıları:
- BIST verisi için profesyonel ve yerel sağlayıcı.
- REST API mevcut.
- Grafik/bar ve geçmiş veri desteği.
- BIST veri kaynağının Borsa İstanbul olduğu açıkça belirtiliyor.
- Uygulama geliştirme kullanımına yönelik API servisi mevcut.

Eksileri:
- Fiyatlandırma veri kapsamına ve kullanım tipine göre teklif ile belirleniyor.
- BIST lisans ücretleri ayrıca uygulanabiliyor.
- Verilerin yeniden dağıtımına izin verilmiyor.

### Finnet

Finnet, web/mobile/SaaS uygulamalar için API ve Data Feed çözümleri sunuyor. Stock Expert API yanında Fund Expert API de bulunuyor.

Artıları:
- Uygulama entegrasyonu için tasarlanmış API ürünleri.
- Hisse ve fon tarafını aynı sağlayıcı üzerinden çözme potansiyeli.
- Kurumsal kullanım senaryolarına uygun.

Eksileri:
- Detaylı fiyatlandırma ve veri geçmişi kapsamı için sağlayıcıdan teklif alınması gerekiyor.

### Karar

**MVP BIST kaynağı olarak Matriks öncelikli adaydır.** Ancak satın alma öncesinde Finnet ile de teklif alınarak fiyat, tarihsel kapsam ve lisans koşulları karşılaştırılacaktır.

## 2. Türkiye Yatırım Fonları

### TEFAS

TEFAS Türkiye yatırım fonları için temel referans kaynaktır. Güncel ekosistemde resmi TEFAS API altyapısı üzerinden fon bazlı fiyat geçmişi alınabilmektedir. 2026 itibarıyla eski bazı `fundturkey.com.tr` tarihsel endpointlerinin emekliye ayrıldığı ve yeni `tefas.gov.tr/api/funds/...` API'sinin kullanıldığı görülmektedir.

Artıları:
- Fon verisinin birincil/resmi kaynağı.
- Fon kodu ve fiyat geçmişi için uygun.
- Fon bazında tarihsel veri alınabiliyor.
- Yatırım fonu kapsamı geniş.

Dikkat edilmesi gerekenler:
- API davranışı ve endpointleri zaman içinde değişebiliyor.
- WAF/rate-limit ve erişim davranışı ingestion tasarımında hesaba katılmalı.
- Üretim kullanımında güncel kullanım/lisans koşulları ayrıca doğrulanmalı.
- Tek bir HTTP endpointine sıkı bağımlılık kurulmayacak.

### SPK

SPK tarafında fonlara ilişkin günlük portföy değerleri ve birim fiyat gibi bilgilerin görüntülenebildiği resmi veri kaynakları bulunuyor. SPK, fon verileri için ikincil doğrulama ve metadata kaynağı olarak değerlendirilecek.

### Karar

**MVP fon fiyat geçmişi için TEFAS birincil kaynak adayıdır. SPK ikincil doğrulama/metadata kaynağı olarak tutulacaktır.**

## 3. Lisans ve Kullanım İlkeleri

Borsa İstanbul, piyasa verilerinin lisanslı veri dağıtım kuruluşları üzerinden dağıtıldığını belirtiyor. Gösterimsiz kullanım ve veri dağıtımı için ayrıca lisans/sözleşme koşulları bulunabiliyor.

Bu nedenle:

- Public web sayfalarından scraping, üretim veri kaynağı olarak kullanılmayacak.
- Lisanssız üçüncü taraf API'ler ana veri kaynağı kabul edilmeyecek.
- Veri sağlayıcı sözleşmesi ve kullanım amacı netleşmeden production ingestion başlatılmayacak.
- Backtest için kullanılan verinin kaynağı ve lisans bilgisi metadata olarak saklanacak.

## 4. MVP Veri Sağlayıcı Mimarisi

```text
                +----------------------+
                |    Data Provider     |
                |      Interface       |
                +----------+-----------+
                           |
          +----------------+----------------+
          |                                 |
+---------v---------+             +---------v---------+
| BIST Stock Source |             | Fund Data Source  |
| Matriks / Finnet  |             | TEFAS / SPK       |
+---------+---------+             +---------+---------+
          |                                 |
          +----------------+----------------+
                           |
                    Normalization
                           |
                    Validation Layer
                           |
                    PostgreSQL / TSDB
```

Provider katmanı en az şu işlemleri soyutlamalıdır:

- `list_symbols()`
- `get_symbol_metadata()`
- `get_daily_history()`
- `get_latest_price()`
- `get_fund_history()`
- `health_check()`

## 5. Veri Saklama İlkeleri

Her normalize edilmiş kayıtta en az:

- provider
- provider_symbol
- canonical_symbol
- asset_type
- timestamp/date
- source timestamp
- ingestion timestamp
- raw/source reference

alanları tutulmalıdır.

Böylece aynı verinin iki sağlayıcıdan gelmesi halinde karşılaştırma ve hata tespiti mümkün olacaktır.

## 6. Faz 2 Sonraki Adım

Kaynak araştırması tamamlandıktan sonra doğrudan ingestion koduna geçmeden önce:

1. BIST OHLCV canonical schema
2. Fon price/NAV canonical schema
3. Asset/symbol master schema
4. Provider configuration schema
5. PostgreSQL/TimescaleDB migration
6. Data quality rules

tasarlanacaktır.

> Not: Matriks/Finnet fiyat ve lisans teklifleri alınmadan ticari sağlayıcı seçimi kesinleştirilmiş sayılmayacaktır. Bu dokümandaki "öncelikli aday" ifadesi teknik değerlendirme sonucunu belirtir; ticari satın alma kararını değil.
