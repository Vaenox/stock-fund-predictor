# Faz 4 — ML Baseline Evaluation Report

Bu doküman, Faz 4 XGBoost baseline'ının gerçek BIST ve TEFAS feature datasetleri üzerindeki walk-forward sonuçlarını kayıt altına alır.

## Evaluation Kuralları

- Target: sonraki 5 gözlemde forward return `> +3%`.
- Validation: expanding / chronological walk-forward.
- Leakage gap: `5` gözlem veya daha fazla.
- Baseline model: XGBoost, sabit başlangıç hiperparametreleri.
- Accuracy tek başına model değerlendirme kriteri değildir.
- ROC-AUC ve PR-AUC sınıf dağılımı ile birlikte okunmalıdır.
- Training fold tek sınıflıysa fold eğitimi reddedilir; validation kuralı gevşetilmez.
- Test fold tek sınıflıysa ROC-AUC ve PR-AUC `None` olarak raporlanır.

## Sonuç Özeti

| Asset | Symbol | Raw rows | Training rows | Target 0 | Target 1 | Fold | Train 0/1 | Test 0/1 | ROC-AUC | PR-AUC | Accuracy | Precision | Recall |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Stock | THYAO | 684 | 480 | 374 | 106 | 1 | 312/43 | 34/6 | 0.2843 | 0.1181 | 0.8500 | 0.0000 | 0.0000 |
| Stock | THYAO | 684 | 480 | 374 | 106 | 2 | 332/63 | 30/10 | 0.6113 | 0.4765 | 0.7500 | 1.0000 | 0.0909 |
| Stock | THYAO | 684 | 480 | 374 | 106 | 3 | 351/84 | 39/1 | 0.5128 | 0.0500 | 0.9750 | 0.0000 | 0.0000 |
| Fund | AFA | 312 | 108 | 84 | 24 | 1 | 39/9 | 18/2 | 0.5556 | 0.1818 | 0.8000 | 0.0000 | 0.0000 |
| Fund | AFA | 312 | 108 | 84 | 24 | 2 | 53/10 | 15/5 | 0.8800 | 0.8369 | 0.7500 | 0.0000 | 0.0000 |
| Fund | AFA | 312 | 108 | 84 | 24 | 3 | 69/14 | 20/0 | None | None | 1.0000 | 0.0000 | 0.0000 |

## Expanded Real-Data Smoke Coverage

Aynı baseline smoke protokolü ile kullanıcı ortamında aşağıdaki ek gerçek veri örnekleri çalıştırıldı ve `REAL XGBOOST BASELINE SMOKE TEST PASSED` sonucu doğrulandı:

| Asset | Symbols | Status |
|---|---|---|
| Stock | `ASELS`, `TUPRS`, `BIMAS` | Passed |
| Fund | `AFT`, `AFS` | Passed |

Ek sembollerin ayrıntılı fold metrikleri kullanıcı çıktısı olarak ayrıca kaydedilmediği için bu sonuçlardan performans ortalaması çıkarılmamıştır.

## AAL — TEFAS

AAL ile yapılan gerçek smoke testlerinde ilk training fold tek sınıflı kaldı. Bu nedenle XGBoost binary classifier eğitimi yapılamadı.

- `days=1000`, `n_splits=3`: fold 1 training target tek sınıf.
- `n_splits=1`, `test_size=40`, `gap=5`: yine fold 1 training target tek sınıf.

Bu veri problemi nedeniyle validation kuralı gevşetilmedi, sentetik veri kullanılmadı ve AAL geçerli baseline sonucu olarak kabul edilmedi.

## Faz 4 Acceptance Sonucu

Resmi acceptance suite kullanıcı ortamında çalıştırıldı:

```text
PYTHONPATH=. pytest tests/ml/test_phase4_acceptance.py -q
3 passed
```

Kabul edilen kontroller:

- `predict_proba` probability contract geçerli.
- Walk-forward split kronolojik ve `gap=5` kuralına uyuyor.
- Training fold iki sınıflı olmalı; tek sınıflı training reddediliyor.
- Single-class test fold için ROC-AUC/PR-AUC `None` raporlanıyor.
- Gerçek BIST baseline smoke: `THYAO`; ek coverage `ASELS`, `TUPRS`, `BIMAS`.
- Gerçek TEFAS baseline smoke: `AFA`; ek coverage `AFT`, `AFS`.
- AAL one-class training problemi açıkça kayıt altına alındı ve validation kuralı gevşetilmedi.

### Faz 4 Kararı

**Faz 4 — ML Baseline / XGBoost kabul edildi ve kapatıldı.**

Bu kabul, baseline pipeline'ının teknik olarak çalıştığını ve leakage-aware walk-forward evaluation sözleşmesinin uygulandığını gösterir. Sonuçlar modelin üretim kalitesini veya genellenebilirliğini kanıtlamaz. Tuning, feature selection ve production signal tasarımı sonraki fazların konusudur.
