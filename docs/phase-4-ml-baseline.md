# Faz 4 — ML Baseline / XGBoost

## Amaç

Faz 3'te üretilen causal feature dataset üzerinden ilk denetlenebilir supervised-learning baseline'ını oluşturmak.

İlk hedef:

```text
forward 5-observation return > +3% => target=1
```

## Model

- Model: XGBoost `XGBClassifier`.
- Stock ve fund feature şemaları farklı olduğu için baseline modelleri asset type bazında ayrı eğitilir.
- İlk baseline hyperparameter tuning yapmaz; sabit, okunabilir başlangıç parametreleri kullanır.
- `predict_proba` ile pozitif sınıf olasılığı üretilir.

## Validation

Random train/test split kullanılmaz.

Zaman sıralı walk-forward validation kullanılır. Forward horizon nedeniyle eğitim ve test arasında en az `gap=horizon` gözlem bırakılır; böylece eğitim tarafındaki etiket pencereleri test döneminin geleceğine taşınmaz.

Önerilen varsayılanlar:

- `n_splits=3`
- `test_size` dışarıdan belirlenir
- `gap=5`

Her fold'ta model yalnızca fold train verisi ile fit edilir ve daha sonraki test aralığında değerlendirilir.

## Metrikler

Baseline için:

- ROC-AUC
- PR-AUC / Average Precision
- Accuracy
- Precision
- Recall
- Pozitif sınıf oranı

Tek başına accuracy model kabul kriteri değildir; sınıf dengesizliği nedeniyle ROC-AUC ve PR-AUC özellikle raporlanır.

## Leakage kuralları

- `target` ve `forward_return_5d` model feature matrix'ine giremez.
- Train/test sıralaması korunur.
- Gelecek gözlemler feature üretimine dahil edilmez.
- Feature scaling zorunlu değildir; XGBoost ham sayısal feature'larla çalışır.
- Hyperparameter tuning daha sonraki aşamadır ve yalnızca train dönemleri üzerinde yapılmalıdır.

## Inference

Eğitilmiş baseline modelin çıktı sözleşmesi:

- `probability`: `predict_proba[:, 1]`
- `target_class`: `probability >= 0.5`

BUY/HOLD/SELL eşikleri bu fazda modelden ayrı tutulur ve sonraki signal/risk katmanında tanımlanır.

## Kabul

- Time-series split üretimi test edilir.
- Gap, horizon'dan küçük olamaz.
- Leakage alanları feature matrix'ten reddedilir.
- Model fit/predict smoke çalışır.
- En az bir walk-forward fold başarıyla değerlendirilir.
