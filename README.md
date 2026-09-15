# Stock & Fund Predictor

Fon ve hisse senetleri için piyasa verilerini, teknik analizi, makine öğrenmesi tahminlerini, risk skorlamasını, backtest ve paper trading süreçlerini tek bir web uygulamasında birleştirmeyi amaçlayan finansal analiz platformu.

> **Not:** Uygulama kesin al/sat garantisi vermeyi hedeflemez. Tahminleri olasılık, beklenen getiri, risk ve model performansı ile birlikte sunar. Gerçek işlem özellikleri eklenmeden önce ilgili veri lisansları, broker şartları ve yürürlükteki mevzuat ayrıca değerlendirilmelidir.

## 🎯 Proje Hedefi

Platformun temel akışı:

```text
Market Data
    ↓
Feature Engineering
    ↓
Technical Indicators
    ↓
ML Model
    ↓
Prediction
    ↓
Risk Engine
    ↓
Final Signal
    ↓
Backtest / Paper Trading
```

Desteklenecek varlıklar başlangıçta hisse senetleri ve fonlar; ilerleyen aşamalarda ETF ve farklı piyasalar olabilir.

## 🧱 Önerilen Teknoloji Stack'i

| Katman | Teknoloji | Amaç |
|---|---|---|
| Frontend | Next.js + TypeScript | Web uygulaması ve dashboard |
| UI | Tailwind CSS + shadcn/ui | Modern ve tutarlı arayüz |
| Grafik | TradingView Lightweight Charts | Mum grafik ve fiyat görselleştirme |
| Backend | Python + FastAPI | Finansal veri ve ML API'leri |
| Data Processing | Pandas + NumPy + Polars | Veri işleme ve feature engineering |
| Technical Analysis | TA-Lib / pandas-ta | RSI, MACD, EMA, Bollinger vb. |
| ML | scikit-learn + XGBoost / LightGBM | İlk tahmin modelleri |
| Deep Learning | PyTorch | İleri aşama modelleri |
| Database | PostgreSQL + TimescaleDB | Finansal zaman serileri ve uygulama verileri |
| Cache | Redis | Cache ve hızlı veri erişimi |
| Task Queue | Celery + Redis | Veri/model görevleri |
| Auth | Supabase Auth | Kullanıcı kimlik doğrulama |
| Container | Docker | Ortam standardizasyonu |
| Deployment | Vercel + Railway/Render/AWS | Frontend ve backend dağıtımı |
| Monitoring | Sentry + Grafana | Hata, performans ve gözlemleme |

### MVP için önerilen başlangıç

```text
Next.js + TypeScript
        ↓
FastAPI
        ↓
PostgreSQL / TimescaleDB
        ↓
Python ML (XGBoost)
        ↓
Redis
        ↓
Docker
```

Deep learning ilk sürümde zorunlu değildir. Öncelik güvenilir veri, doğru feature engineering ve sağlam backtest altyapısıdır.

---

# 🗺️ Roadmap

## Faz 1 — Ürün Tasarımı

- [ ] Desteklenecek piyasaları belirle: BIST, NASDAQ, NYSE vb.
- [ ] Fon türlerini ve veri kapsamını belirle.
- [ ] Tahmin hedeflerini tanımla.
- [ ] BUY / HOLD / SELL sinyal mantığını belirle.
- [ ] Risk ve güven skorlarının nasıl üretileceğini tanımla.

Önerilen ilk tahmin hedefi:

> “Önümüzdeki 5 işlem gününde pozitif getiri olma olasılığı nedir?”

Örnek sınıflandırma hedefi:

```text
1 → 5 işlem günü içinde +%3 üzeri
0 → değil
```

---

## Faz 2 — Veri Altyapısı

- [ ] Market data sağlayıcısını seç.
- [ ] Veri sağlayıcının API, lisans ve yeniden dağıtım şartlarını doğrula.
- [ ] Historical price ingestion sistemi oluştur.
- [ ] Günlük / saatlik / gerektiğinde daha sık veri toplama altyapısı oluştur.
- [ ] Veri kalite kontrolleri ekle.
- [ ] Eksik veri, duplicate kayıt ve corporate action senaryolarını ele al.

Önerilen ana veri modeli:

```text
assets
├── stocks
├── funds
└── ETFs

prices
├── timestamp
├── open
├── high
├── low
├── close
└── volume
```

Ek veri alanları:

```text
fundamentals
technical_indicators
news
predictions
model_versions
```

---

## Faz 3 — Teknik Analiz Motoru

İlk tahmin katmanını ML olmadan oluştur.

- [ ] RSI
- [ ] MACD
- [ ] EMA 20
- [ ] EMA 50
- [ ] EMA 200
- [ ] Bollinger Bands
- [ ] ATR
- [ ] ADX
- [ ] Volume analizi
- [ ] Volatility ölçümü

Örnek teknik skor:

```text
Technical Score: 0 — 100

SELL ←──────── HOLD ────────→ BUY
```

Teknik göstergeleri tek başına alım/satım garantisi olarak kullanma; sonraki ML ve risk katmanlarına feature olarak aktar.

---

## Faz 4 — İlk ML Modeli

İlk modelde fiyat seviyesini doğrudan tahmin etmek yerine yön / getiri olasılığı tahmini yap.

### Model

- [ ] XGBoost baseline oluştur.
- [ ] Baseline sonuçları kaydet.
- [ ] Feature importance analizi ekle.
- [ ] Olasılık calibration uygula.

### Örnek Features

```text
RSI
MACD
EMA trendleri
ATR
Volume
Volatility
Previous returns
Market return
Sector return
USD/TRY
BIST100
```

### Örnek Output

```text
BUY   72%
HOLD  20%
SELL   8%
```

Model confidence ile gerçek model accuracy'si birbirinden ayrı değerlendirilmelidir.

---

## Faz 5 — Backtesting

Bu faz projenin en kritik bölümlerinden biridir.

- [ ] Historical backtest engine oluştur.
- [ ] Zaman bazlı train/test ayrımı uygula.
- [ ] Walk-forward validation ekle.
- [ ] Transaction cost ekle.
- [ ] Slippage varsayımlarını destekle.
- [ ] Risk metriklerini hesapla.
- [ ] Prediction history sakla.

Örnek zaman ayrımı:

```text
TRAIN
2019 ───────── 2023

TEST
              2024 ─────
```

Random train/test split yerine zaman sırasını koruyan yöntemler kullanılmalıdır.

Ölçülecek metrikler:

```text
Prediction accuracy
Precision / Recall
ROC-AUC
Win rate
Average return
Profit factor
Sharpe ratio
Maximum drawdown
Calibration
```

---

## Faz 6 — Prediction Engine

- [ ] Feature pipeline oluştur.
- [ ] Model inference servisi oluştur.
- [ ] Prediction API oluştur.
- [ ] Risk engine oluştur.
- [ ] Final signal üret.
- [ ] Prediction timestamp ve model version sakla.

Örnek çıktı:

```text
THYAO

5 Günlük Tahmin

Yükselme       %68
Yatay          %21
Düşme          %11

Beklenen Getiri
+4.2%

Risk
Orta

Sinyal
BUY

Güven
78/100
```

---

## Faz 7 — Haber ve Sentiment Analysis

- [ ] Haber veri kaynağı belirle.
- [ ] Haberleri varlıklarla eşleştir.
- [ ] Pozitif / nötr / negatif sınıflandırma yap.
- [ ] Sentiment score üret.
- [ ] Sentiment'i ML feature'ı olarak modele ekle.
- [ ] Haber etkisini backtest içerisinde ayrıca ölç.

Örnek:

```text
Technical analysis   +++
Financial health     ++
News sentiment       +++
Market trend         ++
```

---

## Faz 8 — Gelişmiş Modeller

Baseline model güvenilir hale geldikten sonra:

```text
XGBoost
   ↓
LightGBM
   ↓
Ensemble
   ↓
LSTM
   ↓
Transformer
```

- [ ] Modelleri aynı backtest protokolünde karşılaştır.
- [ ] Ensemble yaklaşımı dene.
- [ ] Model registry / versioning ekle.
- [ ] Model drift takibi ekle.

> Daha karmaşık modelin otomatik olarak daha iyi olduğu varsayılmamalıdır.

---

## Faz 9 — Web Dashboard

### Ana ekran

```text
┌─────────────────────────────────────────────┐
│ Piyasa                                      │
│ BIST 100       11.240    +1.24%             │
│ USD/TRY        42.15      +0.32%             │
└─────────────────────────────────────────────┘

En Güçlü Sinyaller

THYAO       BUY      82
ASELS       BUY      76
TUPRS       HOLD     54
AKBNK       SELL     71
```

### Varlık detay sayfası

```text
THYAO

₺XXX.XX

[ Mum Grafik ]

1D  1W  1M  3M  1Y  5Y

Technical Score       82
ML Prediction         74%
Risk Score             38

RSI                   61
MACD                  Bullish
Trend                 Bullish
Volume                High
```

- [ ] Market overview
- [ ] Varlık arama
- [ ] Hisse detay sayfası
- [ ] Fon detay sayfası
- [ ] Historical chart
- [ ] Teknik göstergeler
- [ ] Prediction paneli
- [ ] Risk paneli
- [ ] Signal history

---

## Faz 10 — Kullanıcı Sistemi

- [ ] Supabase Auth entegrasyonu
- [ ] Kullanıcı profili
- [ ] Watchlist
- [ ] Favori varlıklar
- [ ] Kullanıcı tercihleri
- [ ] Sinyal geçmişi

Örnek watchlist:

```text
Watchlist
├── THYAO
├── ASELS
├── TUPRS
└── EREGL
```

---

## Faz 11 — Alerts / Notifications

- [ ] BUY signal alarmı
- [ ] SELL signal alarmı
- [ ] Prediction score threshold alarmı
- [ ] Fiyat değişim alarmı
- [ ] Risk seviyesi alarmı
- [ ] E-posta / web notification altyapısı

Örnek:

```text
🔔 THYAO %5 düştü
🔔 THYAO BUY sinyaline geçti
🔔 Tahmin skoru 80 üzerine çıktı
```

---

## Faz 12 — Paper Trading

Gerçek para ile işlem yapmadan önce gerçek piyasa verisi üzerinde sanal portföy sistemi kur.

- [ ] Sanal portföy
- [ ] Sanal bakiye
- [ ] Sanal alış / satış
- [ ] Gerçek zamanlı PnL
- [ ] Position history
- [ ] Strategy performance
- [ ] Risk metrikleri

Örnek:

```text
100.000 TL
       ↓
BUY THYAO
Entry: 320
Stop: 305
Target: 340
```

Amaç modelin gerçek piyasa koşullarındaki davranışını gerçek para kullanmadan ölçmektir.

---

## Faz 13 — Gerçek İşlem Entegrasyonu

Bu aşama en sona bırakılmalıdır.

```text
Signal
   ↓
Risk Check
   ↓
User Approval
   ↓
Broker API
   ↓
Order
```

- [ ] Broker/API sağlayıcısını araştır.
- [ ] Yetkilendirme şartlarını değerlendir.
- [ ] Order validation oluştur.
- [ ] Kullanıcı onay akışı oluştur.
- [ ] Order history oluştur.
- [ ] Error / retry / reconciliation mekanizması ekle.

İlk üretim sürümünde otomatik al-sat yerine kullanıcı onaylı işlem yaklaşımı tercih edilir.

---

# 🚀 MVP Kapsamı

İlk production'a yakın sürüm aşağıdaki özellikleri içermeli:

```text
☐ Kullanıcı kayıt / giriş
☐ Hisse arama
☐ Fon arama
☐ Varlık detay sayfası
☐ Historical chart
☐ Teknik göstergeler
☐ Technical score
☐ ML prediction
☐ Risk score
☐ BUY / HOLD / SELL signal
☐ Backtest
☐ Watchlist
☐ Prediction history
```

---

# 📁 Önerilen Proje Yapısı

## Backend

```text
backend/
├── app/
│   ├── api/
│   ├── models/
│   ├── schemas/
│   ├── services/
│   ├── indicators/
│   ├── ml/
│   │   ├── features/
│   │   ├── training/
│   │   ├── prediction/
│   │   └── models/
│   ├── backtesting/
│   ├── data/
│   └── core/
│
├── tests/
├── Dockerfile
└── requirements.txt
```

## Frontend

```text
frontend/
├── app/
│   ├── dashboard/
│   ├── stocks/
│   ├── funds/
│   ├── predictions/
│   ├── portfolio/
│   └── settings/
│
├── components/
├── lib/
├── hooks/
├── services/
└── types/
```

---

# ✅ Uygulama Sırası

```text
01. Proje mimarisi
        ↓
02. Database
        ↓
03. Market data ingestion
        ↓
04. Historical data
        ↓
05. Technical indicators
        ↓
06. Technical scoring
        ↓
07. Feature engineering
        ↓
08. XGBoost model
        ↓
09. Backtesting
        ↓
10. Prediction API
        ↓
11. Next.js dashboard
        ↓
12. Watchlist
        ↓
13. Alerts
        ↓
14. Sentiment analysis
        ↓
15. Ensemble models
        ↓
16. Paper trading
        ↓
17. Production optimization
```

---

# ⚠️ Teknik Riskler ve Kontroller

## 1. Look-ahead bias

Modelin tahmin anında erişemeyeceği gelecekteki bilgilerin feature olarak kullanılmasını engelle.

## 2. Data leakage

Test dönemindeki bilgilerin training sürecine sızmadığından emin ol.

## 3. Survivorship bias

Sadece bugün hayatta kalan hisselerle geçmiş performans ölçme.

## 4. Transaction costs / slippage

Backtest sonuçlarının gerçek dışı görünmesini önlemek için maliyetleri modele dahil et.

## 5. Model drift

Piyasa rejimleri değiştiğinde model performansını düzenli izle ve gerektiğinde yeniden eğit.

---

# 📌 Task Yönetimi

Geliştirme sürecinde görevler `Task 001`, `Task 002`, ... şeklinde ilerletilebilir.

Her task için:

```text
- [ ] Yapılacak
- [x] Tamamlandı
```

mantığı kullanılmalı. Büyük özellikler ayrı issue'lara bölünmeli ve tamamlanan işler README içerisindeki ilgili checklist ile güncellenmelidir.

---

# 🏁 İlk Hedef

İlk hedef **sağlam bir veri + feature + backtest altyapısına sahip çalışan bir MVP** çıkarmaktır.

Öncelik sırası:

```text
Veri kalitesi
     >
Feature engineering
     >
Backtest doğruluğu
     >
Model performansı
     >
UI / görsellik
```

Geliştirme sırasında model karmaşıklığından önce veri kalitesi, zaman serisi doğrulaması ve gerçekçi backtest sonuçları esas alınmalıdır.
