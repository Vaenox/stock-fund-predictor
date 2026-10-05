# Phase 6 — Prediction History Persistence

## Amaç

Phase 5/6 signal üretimlerini PostgreSQL üzerinde append-only ve audit edilebilir biçimde saklamak.

## Contract

Her prediction kaydı bir asset ve bir prediction date için üretilen tek bir model/signal sonucunu temsil eder.
Aynı gün aynı asset için yeniden prediction üretilmesi eski kaydı overwrite etmez; yeni bir audit kaydı oluşturur.

Temel alanlar:

- prediction_date: model/sinyal kararının ait olduğu market tarihi.
- generated_at: kaydın gerçekten üretildiği timezone-aware timestamp.
- data_as_of: prediction girdilerinin kapsadığı son market tarihi; prediction_date sonrasına gidemez.
- horizon_days: örneğin production 5.
- target_return_threshold: örneğin production 0.03.
- model_family ve model_version: model lineage için.
- feature_representation: örneğin production raw_all.
- ml_probability, technical_score, risk_score, risk_adjustment, signal_score.
- target_weight: backtest strategy katmanının alacağı continuous exposure.
- quality_ok, stale_days, source_provider ve reasons.

## Tasarım kararları

- Tablo append-only tutulur; prediction geçmişi overwrite edilmez.
- Prediction history için BUY/HOLD/SELL action alanı eklenmez; production threshold contractı henüz seçilmedi.
- Model feature vectorünün tamamı ilk contractta JSON olarak saklanmaz. Bunun yerine model/representation ve score bileşenleri lineage/audit için tutulur.
- Aynı asset/date için doğal unique constraint eklenmez; aynı tarihte farklı model sürümü veya yeniden üretim sonucu ayrı kayıtlar olarak saklanabilir.
- Bu katman backtest sonucu persistence'tan ayrıdır. Strategy-level backtest run/metric kayıtları sonraki controlled tasktır.
- PostgreSQL tarafında core numeric bounds ve data_as_of <= prediction_date kuralları CHECK constraint olarak da korunur.

## Service

backend/app/data/prediction_history.py:

- record_prediction(...)
- record_predictions(...)
- list_predictions(...)
- get_latest_prediction(...)

Service update/delete operasyonu sağlamaz.

## Migration

0003_prediction_history migrationı prediction_history tablosunu ve asset/date, prediction_date ve generated_at indexlerini oluşturur.

## Production kararı

Bu persistence işi model, target, feature representation, signal weighting veya sizing policy değiştirmez.
Production signal contract mevcut haliyle korunur.
