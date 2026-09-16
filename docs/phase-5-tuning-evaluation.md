# Faz 5 — Tuning Evaluation

Bu doküman, Faz 4 baseline XGBoost ile Faz 5 tuned XGBoost'un aynı outer walk-forward test foldlarında karşılaştırılmasından elde edilen ilk gerçek veri sonucunu kayıt altına alır.

## Evaluation Kuralları

- Outer validation: expanding / chronological walk-forward.
- Leakage gap: `5` gözlem.
- Her outer fold için tuning yalnızca ilgili training döneminde yapılır.
- Outer test fold tuning sırasında görülmez.
- Inner objective: PR-AUC / Average Precision.
- Baseline ve tuned model aynı outer test foldunda karşılaştırılır.

## THYAO — BIST

Gerçek veri: `1000` günlük pencere, `684` ham satır, `480` training satırı.

| Fold | Baseline ROC-AUC | Tuned ROC-AUC | Baseline PR-AUC | Tuned PR-AUC | Baseline Accuracy | Tuned Accuracy | Tuned Config |
|---|---:|---:|---:|---:|---:|---:|---|
| 1 | 0.2157 | 0.2549 | 0.1246 | 0.1310 | 0.8500 | 0.8500 | depth=4, lr=0.03, min_child_weight=3 |
| 2 | None | None | None | None | 1.0000 | 1.0000 | depth=4, lr=0.05, min_child_weight=1 |
| 3 | 0.8947 | 0.9474 | 0.3333 | 0.5000 | 0.9500 | 0.9500 | depth=5, lr=0.03, min_child_weight=3 |

### Inner tuning result

- Best inner PR-AUC: `1.000000`
- Bu değer yalnızca tuning sırasında kullanılan inner validation skorudur; outer test performansı olarak yorumlanmaz.
- Seçim seed'i `42` ile reproducible yapıdadır.

### Dış test yorumu

Fold 1'de tuned modelin ROC-AUC ve PR-AUC değerleri baseline'a göre yükseldi; Fold 3'te de aynı yönde değişim görüldü. Fold 2 test seti tek sınıflı olduğundan ROC-AUC ve PR-AUC iki model için de hesaplanamadı. Accuracy üç fold'da da değişmedi.

Bu tek sembol üzerindeki ilk karşılaştırma tuning yaklaşımının outer test protokolünde çalıştığını gösterir. Daha geniş sembol/fon örneklemi olmadan tuned modelin genellenebilirliği veya production performansı hakkında sonuç çıkarılmaz.

## Sonraki Adım

- Birden fazla BIST ve TEFAS örneğinde aynı outer baseline-vs-tuned karşılaştırmasını çalıştırmak.
- Fold-level feature importance değerlerini toplamak.
- Sonuçlara göre probability calibration ihtiyacını değerlendirmek.
