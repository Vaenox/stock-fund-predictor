# Faz 4 — ML Baseline Evaluation Report

Bu doküman, Faz 4 XGBoost baseline'ının gerçek BIST ve TEFAS feature datasetleri üzerindeki ilk walk-forward sonuçlarını kayıt altına alır.

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

## THYAO — BIST

Gerçek baseline smoke başarılı oldu. Target dağılımı `374` negatif / `106` pozitif gözlem.

Fold sonuçları belirgin şekilde değişiyor: ROC-AUC `0.2843 → 0.6113 → 0.5128`. Üçüncü test fold'unda yalnızca 1 pozitif gözlem bulunuyor. Bu sonuçlar pipeline'ın çalıştığını doğrular; tek başına genellenebilir model performansı kanıtı değildir.

## AFA — TEFAS

Gerçek baseline smoke başarılı oldu. Target dağılımı `84` negatif / `24` pozitif gözlem.

Fold 2'de ROC-AUC `0.8800` ve PR-AUC `0.8369` görülürken Fold 1 daha düşük, Fold 3 ise test setinde hiç pozitif gözlem olmadığı için ROC-AUC/PR-AUC hesaplanamaz durumdadır. Bu nedenle tek bir fold'un yüksek metriklerine dayanarak model kalitesi sonucu çıkarılmamalıdır.

## AAL — TEFAS

AAL ile yapılan gerçek smoke testlerinde ilk training fold tek sınıflı kaldı. Bu nedenle XGBoost binary classifier eğitimi yapılamadı.

- `days=1000`, `n_splits=3`: fold 1 training target tek sınıf.
- `n_splits=1`, `test_size=40`, `gap=5`: yine fold 1 training target tek sınıf.

Bu veri problemi nedeniyle validation kuralı gevşetilmedi, sentetik veri kullanılmadı ve AAL sonuç tablosuna başarılı bir baseline sonucu olarak eklenmedi.

## Teknik Değerlendirme

İlk gerçek veri sonuçları şu anda üç şeyi doğruluyor:

1. Phase 3 causal feature datasetleri gerçek XGBoost baseline'a bağlanabiliyor.
2. Walk-forward split ve `gap=5` kuralı gerçek veride uygulanıyor.
3. 5-günde `%3+` target bazı fonlarda seyrek olduğundan fold-level class distribution açıkça izlenmeli.

Bu aşamada tuning, threshold optimizasyonu veya BUY/HOLD/SELL üretimine geçilmemelidir. Önce daha geniş bir gerçek örnek seti ile baseline davranışı kayda alınmalıdır.

## Sonraki Adım

- Farklı BIST sembollerinden ve iki sınıflı yeterli TEFAS fonlardan birkaç baseline smoke sonucu daha toplamak.
- Sonuçları aynı tabloya eklemek.
- Gerekli minimum veri / target dağılımı kabul kriterini netleştirmek.
- Ardından Faz 4 acceptance kararını vermek.
