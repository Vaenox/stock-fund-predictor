# Faz 1 — Product Specification

## 1. Amaç

MVP'nin amacı, BIST hisseleri ve Türkiye'deki yatırım fonları için geçmiş piyasa verilerinden teknik göstergeler ve makine öğrenmesi kullanarak kısa vadeli fırsatları ölçmek ve kullanıcıya açıklanabilir bir BUY / HOLD / SELL sinyali sunmaktır.

Bu ürün yatırım tavsiyesi veya kesin getiri garantisi değildir. Tahminler olasılık, risk ve geçmiş backtest sonuçlarıyla birlikte gösterilecektir.

## 2. MVP Kapsamı

### Dahil
- BIST hisseleri
- Türkiye yatırım fonları
- 5 işlem günlük tahmin ufku
- Teknik analiz göstergeleri
- ML tabanlı olasılık tahmini
- Risk skoru
- BUY / HOLD / SELL sinyali
- Tahmin geçmişi
- Watchlist
- Temel dashboard
- Backtest altyapısına uygun veri ve hedef tanımı

### MVP Dışı
- Otomatik gerçek para ile işlem
- Broker entegrasyonu
- NASDAQ / NYSE
- ETF'ler
- Deep learning modelleri
- Gelişmiş haber/sentiment sistemi

## 3. Tahmin Hedefi

İlk model binary classification olarak başlatılacaktır.

- Horizon: 5 işlem günü
- Pozitif sınıf: 5 işlem günü ileri getiri `> +3%`
- Negatif sınıf: aksi durum
- Model çıktısı: `P(5D return > +3%)`

İlerleyen aşamada BUY / HOLD / SELL için çok sınıflı hedef veya olasılık tabanlı sinyal katmanı değerlendirilebilir. İlk MVP'de model hedefi ile kullanıcı sinyali bilinçli olarak ayrıdır.

## 4. Sinyal Motoru

Son kullanıcı sinyali yalnızca ML tahmininden oluşmayacaktır.

`Final Signal = ML Probability + Technical Score + Risk Adjustment`

Başlangıç yaklaşımı:
- **BUY:** yüksek ML olasılığı + destekleyici teknik görünüm + kabul edilebilir risk
- **HOLD:** karışık sinyaller veya yeterli avantaj olmayan durum
- **SELL:** zayıf teknik görünüm / yüksek aşağı yönlü risk / pozitif hedef olasılığının yetersiz olması

Kesin eşikler veri ve backtest sonuçlarına göre belirlenecek; önceden seçilmiş eşikler backtest ile doğrulanmadan üretim kararı yapılmayacaktır.

## 5. Teknik Skor

Teknik skor zaman içinde aşağıdaki bileşenlerden oluşturulacaktır:
- Trend
- Momentum
- Volatilite
- Hacim
- Destek / direnç

Başlangıç göstergeleri için SMA/EMA, RSI, MACD, ATR ve hacim tabanlı metrikler değerlendirilecektir.

## 6. Risk Skoru

Risk skoru 0–100 aralığında tutulacaktır; yüksek değer daha yüksek riski ifade eder.

İlk bileşenler:
- Volatilite
- ATR / fiyat oranı
- Maksimum drawdown
- Likidite / hacim
- Piyasa rejimi

Risk skoru model tahmininden ayrı tutulacak ve kullanıcıya nedenleriyle birlikte gösterilecektir.

## 7. Güven ve Olasılık

Model olasılığı doğrudan "kesinlik" olarak sunulmayacaktır. Model kalibrasyonu ayrıca ölçülecek.

UI'da mümkün olduğunda:
- tahmin olasılığı,
- risk skoru,
- sinyal,
- tahmin tarihi,
- veri dönemi
birlikte gösterilecektir.

## 8. MVP Ekranları

### Dashboard
- Piyasa özeti
- Öne çıkan BUY / HOLD / SELL sinyalleri
- En yüksek ML olasılıkları
- Risk görünümü
- Watchlist özeti

### Hisse Detay
- Fiyat ve grafik
- Teknik göstergeler
- Teknik skor
- ML tahmini
- Risk skoru
- Final sinyal
- Tahmin geçmişi

### Fon Detay
- Fon fiyat/NAV geçmişi mevcut veri yapısına göre
- Performans metrikleri
- Risk görünümü
- ML tahmini ve sinyal

### Predictions
- Geçmiş tahminler
- Tahmin sonucu gerçekleşti mi?
- Model performans özeti

### Watchlist
- Kullanıcının takip ettiği varlıklar
- Güncel sinyal / risk / olasılık

### Settings
- Kullanıcı tercihleri
- Bildirim tercihleri için temel alan
- İleride genişletilecek yapı

## 9. Temel Kullanıcı Akışı

1. Kullanıcı dashboard'a girer.
2. Bir hisse veya fon seçer.
3. Fiyat, teknik göstergeler, ML olasılığı ve risk skorunu inceler.
4. Final BUY / HOLD / SELL sinyalini görür.
5. Varlığı watchlist'e ekleyebilir.
6. Tahminin geçmiş performansını inceleyebilir.

## 10. Model Değerlendirme

Sadece accuracy kullanılmayacaktır.

ML metrikleri:
- ROC-AUC
- Precision
- Recall
- F1
- Probability calibration

Trading/backtest metrikleri:
- Win rate
- Ortalama işlem getirisi
- Cumulative return
- Sharpe ratio
- Maximum drawdown
- Profit factor
- İşlem sayısı

## 11. Backtest Kuralları

- Zaman sıralı train/validation/test ayrımı kullanılacak.
- Random shuffle ile klasik cross-validation yapılmayacak.
- Walk-forward validation tercih edilecek.
- Look-ahead bias engellenecek.
- Feature üretiminde gelecek veri kullanılmayacak.
- Survivorship bias dikkate alınacak.
- Komisyon, spread ve slippage mümkün olduğunca modele dahil edilecek.
- Model performansı yalnızca tek bir dönem üzerinden değerlendirilmemeli.

## 12. Faz 1 Kabul Kriterleri

- [x] İlk pazar ve varlık kapsamı belirlendi.
- [x] Tahmin ufku belirlendi.
- [x] İlk ML hedefi belirlendi.
- [x] İlk model ailesi belirlendi.
- [x] Sinyal yaklaşımı belirlendi.
- [x] MVP ekranları tanımlandı.
- [x] Temel kullanıcı akışı tanımlandı.
- [x] Model ve backtest değerlendirme metrikleri tanımlandı.
- [x] Veri sızıntısını önleyen temel kurallar tanımlandı.

## 13. Faz 2'ye Geçiş

Faz 1'in çıktısı artık uygulamanın ne yapacağını ve başarıyı nasıl ölçeceğini tanımlar. Faz 2'de odak veri altyapısıdır:

1. BIST hisse veri kaynağı seçimi
2. Türkiye yatırım fonu veri kaynağı seçimi
3. Veri lisansı ve kullanım koşullarının kontrolü
4. OHLCV / fon verisi şemasının tasarımı
5. PostgreSQL / TimescaleDB şeması
6. Historical data ingestion
7. Incremental data update
8. Data validation ve quality checks
9. Eksik veri / duplicate / outlier kuralları
10. Feature pipeline için temiz veri sözleşmesi
