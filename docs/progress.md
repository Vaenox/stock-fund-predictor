# Proje İlerleme Kaydı

Bu dosya, fazlarda alınan kararların, tamamlanan işlerin ve sıradaki taskların kısa özetini tutar. Yeni bir sohbette projeye devam ederken önce bu dosya referans alınmalıdır.

## Güncel Durum

- Aktif faz: **Faz 6 — Backtest / Prediction Evaluation Foundation**
- Son tamamlanan faz: **Faz 5 — Model Tuning / Feature Importance / Signal-Risk Foundation**
- Faz 5 tamamlandı: tuning, feature representation, calibration, direction/threshold diagnostics, risk adjustment, signal foundation ve gerçek signal-chain OOS coverage doğrulandı. Production contractlar değiştirilmedi.
- Faz 5 kapanış testi: **140 passed, 6.43s**. Targeted TEFAS provider/retry testleri: **7 passed, 1.09s**.

## Faz 2 — Data Infrastructure — TAMAMLANDI

- BIST ve TEFAS provider, normalization, validation, persistence, quality ve streaming altyapısı tamamlandı.
- Gerçek BIST full-universe coverage: 516/516 quote.
- Gerçek TEFAS full universe: 2040/2040 fon.
- Historical + live PostgreSQL persistence, duplicate/upsert ve E2E pipeline doğrulandı.

## Faz 3 — Technical Analysis Engine — TAMAMLANDI

- Stock/fund indicator engine, Technical Score Engine ve ML feature dataset builder tamamlandı.
- Warm-up, look-ahead ve leakage kontrolleri tamamlandı.
- Analysis test suite: 18 passed.

## Faz 4 — ML Baseline / XGBoost — TAMAMLANDI

- Leakage-aware expanding walk-forward splitter, gap >= 5, XGBoost baseline wrapper ve metrikler tamamlandı.
- Gerçek BIST smoke coverage: THYAO, ASELS, TUPRS, BIMAS.
- Gerçek TEFAS smoke coverage: AFA, AFT, AFS.
- AAL one-class training problemi doğrulandı; validation gevşetilmedi.
- Faz 4 acceptance: 3 passed.

## Faz 5 — Model Tuning / Feature Importance / Signal-Risk Foundation — AKTİF

### Güncel Bulgular

- Inner walk-forward tuning, feature importance, calibration, risk adjustment ve signal foundation tamamlandı.
- Faz 5 gerçek signal-chain coverage 7 sembol / 840 OOS gözlemine ulaştı.
- Faz 5 kapanış testleri Codespace'te 140/140 backend test ile doğrulandı.
- Feature representation ablation altı sembolde tamamlandı; raw_all / normalized_all / stationary_core candidate olarak korunuyor, production contract sessizce değiştirilmedi.
- 6-symbol direction diagnostic tamamlandı. ML probability için 3 direct / 3 inverse; Technical Score için ROC yönünde 4 inverse / 2 direct görüldü. Global production inversion seçilmedi.
- 6-symbol threshold smoke coverage tamamlandı. Global BUY/HOLD/SELL threshold winner seçilmedi; raw signal ölçeği semboller arasında belirgin biçimde değişiyor.
- Meta-aggregation outer OOS deneysel olarak değerlendirildi; fold instability nedeniyle production default seçilmedi.
- Phase 5 acceptance: 3 passed; tüm ML test suite: 75 passed in 6.15s.

### Faz 5 Baseline vs Tuned Direction — AFA

Canonical PostgreSQL history ile gerçek 3-fold / 120 OOS baseline-vs-tuned direction comparison tamamlandı.

**AFA — 674 raw rows, 470 training rows, 120 OOS rows, target rate 0.208**

- Fold 1: baseline direct ROC 0.4323, PR 0.3539; inverse ROC 0.5677, PR 0.4227. Tuned direct ROC 0.4479, PR 0.3848; inverse ROC 0.5521, PR 0.4768.
- Fold 2: baseline direct ROC 0.6319, PR 0.4759; inverse ROC 0.3681, PR 0.1091. Tuned direct ROC 0.7083, PR 0.5720; inverse ROC 0.2917, PR 0.0889.
- Fold 3: baseline direct ROC 0.3714, PR 0.1130; inverse ROC 0.6286, PR 0.1845. Tuned direct ROC 0.4914, PR 0.1428; inverse ROC 0.5086, PR 0.2103.

**AFA Aggregate OOS**

- Baseline: direct ROC 0.3398, PR 0.2137; inverse ROC 0.6602, PR 0.2959.
- Tuned: direct ROC 0.3587, PR 0.2324; inverse ROC 0.6413, PR 0.3402.

**Karar:** Tuning AFA'da bazı performans metriklerini iyileştirdi ancak direction davranışını çözmedi. Aggregate direct ROC 0.3587 < inverse 0.6413; foldlar heterojen.

### Faz 5 Baseline vs Tuned Direction — THYAO

Canonical stock history yetersiz olduğu için Borsapy provider fallback kullanıldı. Gerçek 3-fold / 120 OOS comparison tamamlandı.

**THYAO — 685 raw rows, 481 training rows, 120 OOS rows, target rate 0.158**

- Fold 1: baseline direct ROC 0.4502, PR 0.3554; inverse ROC 0.5498, PR 0.2654. Tuned direct ROC 0.5108, PR 0.3712; inverse ROC 0.4892, PR 0.2216.
- Fold 2: baseline direct ROC 0.4695, PR 0.2431; inverse ROC 0.5305, PR 0.3308. Tuned direct ROC 0.3763, PR 0.1929; inverse ROC 0.6237, PR 0.3060.
- Fold 3: baseline direct ROC 0.9189, PR 0.4250; inverse ROC 0.0811, PR 0.0543. Tuned direct ROC 0.9189, PR 0.6000; inverse ROC 0.0811, PR 0.0538.

**THYAO Aggregate OOS**

- Baseline: direct ROC 0.5597, PR 0.2883, Spearman 0.0755; inverse ROC 0.4403, PR 0.1894.
- Tuned: direct ROC 0.5638, PR 0.2731, Spearman 0.0807; inverse ROC 0.4362, PR 0.1500.

**Karar:** Tuning THYAO'da aggregate ROC-AUC'yi çok sınırlı artırdı; PR-AUC 0.2883 -> 0.2731 düştü. Aggregate direction direct kaldı. Production direction değiştirilmedi.

### Faz 5 Nested Representation Selection — Altyapı

- `backend/scripts/smoke_test_representation_nested_real.py` oluşturuldu.
- Candidate representations: `raw_all`, `normalized_all`, `stationary_core`.
- Production target contract sabit tutuluyor: horizon=5, threshold=+3%.
- Her outer fold için representation yalnızca outer-train içindeki 2-fold inner walk-forward sonuçlarından seçiliyor; her representation kendi inner XGBoost tuning'inden geçiriliyor.
- En az 2 valid inner fold kuralı korunuyor; PR-AUC primary, ROC-AUC ve fold PR std secondary criteria.
- Seçilen representation yalnızca ilgili outer fold üzerinde OOS değerlendiriliyor.
- Bu aşamada production representation değiştirilmedi; gerçek AFA/THYAO smoke sonuçları bekleniyor.

### Faz 5 Nested Representation Selection — argparse Help String Düzeltmesi

- `--threshold` CLI parametresi eklendikten sonra `argparse` başlatılırken `ValueError: badly formed help string` oluştu.
- Kök neden `help="... +1%"` içindeki `%` karakterinin argparse'ın printf-style help formatting mekanizması tarafından format işareti olarak yorumlanmasıdır.
- Help metni yüzde işareti yerine `+1 percent` olacak şekilde düzeltildi. Threshold davranışı ve veri/model mantığı değiştirilmedi.
- Düzeltme commit: `542fdc5ebc83c3ef864f848164e9ff0d0dfd5786`.

### Faz 5 Nested Representation Selection — AFA Gerçek Sonucu ve Yorum

### Faz 5 Nested Representation Selection — AFT ve THYAO Gerçek Sonuçları

**AFT — PostgreSQL canonical history, 677 raw / 473 dataset rows, h5/+3%**

- Outer 1: `normalized_all` seçildi. Inner PR 0.3770, ROC 0.6149, PR std 0.2073, direction 50%, valid folds 2. Outer ROC 0.4646, PR 0.4913, Spearman -0.0609.
- Outer 2: `raw_all` seçildi. Inner PR 0.4698, ROC 0.6434, PR std 0.0998, direction 100%, valid folds 2. Outer ROC 0.6127, PR 0.3366, Spearman +0.1395.
- Outer 3: `raw_all` seçildi. Inner PR 0.4334, ROC 0.5293, PR std 0.1362, direction 50%, valid folds 2. Outer ROC 0.5755, PR 0.3616, Spearman +0.1225.
- Representation selection foldlar arasında sabit kalmadı; `normalized_all` yalnızca ilk fold'da, `raw_all` sonraki iki fold'da seçildi. Production representation değişikliği için bu tek-sembol kanıt yeterli görülmedi.

**THYAO — Borsapy provider fallback, 685 raw / 481 dataset rows, h5/+3%**

- Outer 1/2/3'ün tamamında `raw_all` seçildi.
- Inner PR: 0.4733, 0.3581, 0.2719; inner ROC: 0.5475, 0.4401, 0.4152; valid folds 2.
- Outer sonuçlar: fold 1 ROC 0.5108 / PR 0.3712 / Spearman +0.0142; fold 2 ROC 0.3763 / PR 0.1929 / Spearman -0.1789; fold 3 ROC 0.9189 / PR 0.6000 / Spearman +0.3823.
- THYAO'da representation seçimi stabil biçimde `raw_all` tarafında kaldı. Bununla birlikte outer foldlar ve direction heterojenliği nedeniyle bu tek sembol sonucu genel production representation değişikliği için tek başına yeterli değildir.

**AFA + AFT + THYAO birlikte**

- AFA'da geçerli iki outer foldun ikisinde `stationary_core` seçildi; bir outer fold sparse +3% target nedeniyle inconclusive kaldı.
- AFT'de `normalized_all` 1/3, `raw_all` 2/3 outer foldda seçildi.
- THYAO'da `raw_all` 3/3 outer foldda seçildi.
- Üç sembol birlikte tek bir universal representation davranışı göstermiyor. Özellikle AFA'daki `stationary_core` seçimi AFT/THYAO'da tekrar edilmedi.
- Mevcut production representation **`raw_all` olarak korunuyor**. `normalized_all` ve `stationary_core` deneysel adaylar olarak tutuluyor.


- AFA, PostgreSQL canonical history ile 674 raw / 470 dataset satırında h5/+3% target ile nested representation smoke çalıştırıldı.
- Outer fold 1 representation selection yapılamadı: üç representation da `inner validation has no two-class fold` nedeniyle atlandı. Bu fold sonucu INCONCLUSIVE kabul ediliyor; crash artık beklenmiyor.
- Outer fold 2 `stationary_core` seçildi: inner PR-AUC 0.7375, ROC-AUC 0.8203, PR std 0.2625, direction 100%, valid folds 2. Aynı representation'ın outer OOS sonucu ROC 0.6389, PR 0.3532, Spearman +0.1444.
- Outer fold 3 `stationary_core` seçildi: inner PR-AUC 0.5110, ROC-AUC 0.5877, PR std 0.0361, direction 100%, valid folds 2. Outer OOS ROC 0.2343, PR 0.0953, Spearman -0.3045.
- Seçim iki outer foldda da `stationary_core` olsa da inner -> outer performans taşınması zayıf/heterojen: fold 3'te inner skorların altında belirgin OOS bozulma var. Bu nedenle yalnızca AFA'nın iki geçerli outer folduna dayanarak production representation değiştirilmiyor.
- Toplam seçim coverage 2/3 outer fold; bu nedenle `NESTED REPRESENTATION SELECTION PASSED` çıktısı teknik smoke başarı olarak görülebilir, fakat representation seçimi için yeterli genelleme kanıtı olarak kabul edilmiyor.
- Mevcut production representation `raw_all` korunuyor.
- Kod commit: `5eddbfcfa4b984bb459b74d297af65479c1e9a3c`.

### Faz 5 Nested Representation Selection — Sparse Target için Inconclusive Handling ve Threshold Parametresi

- AFA +3% nested representation çalışmasının temel sonucu veri/sınıf yoğunluğu nedeniyle representation selection'ın bazı outer foldlarda geçerli sonuç üretememesidir; bunu kod hatası gibi göstermek yerine açıkça `INCONCLUSIVE` olarak raporlamak üzere hata yönetimi eklendi.
- `smoke_test_representation_nested_real.py` artık `--threshold` parametresini destekliyor; varsayılan production-compatible değer `0.03` (+3%). Parametre dataset target oluşturulurken `MLFeatureConfig.positive_return_threshold` içine aktarılıyor.
- `_score_representation()` kaynaklı `ValueError` outer fold bazında yakalanıyor. `_select_representation()` geçerli aday bulamazsa ilgili outer fold atlanıyor; hiçbir outer fold sonuç vermezse traceback yerine `NESTED REPRESENTATION SELECTION INCONCLUSIVE` yazıp exit code 2 dönüyor.
- `_evaluate_outer()` içindeki tuning/evaluation `ValueError` da outer fold bazında yakalanıyor.
- Bu değişiklik representation veya target'ı otomatik olarak değiştirmiyor; amaç sparse target durumunu sessiz failure yerine açık deney sonucu olarak raporlamak.
- +1% gibi daha yüksek event yoğunluklu thresholdlar yalnızca diagnostic/representation smoke amacıyla ayrıca çalıştırılabilir; production target contract hâlâ h5/+3%.
- Kod commit: `db757c206f68df5cc80a836d901737546691778f`.

### Faz 5 Nested Representation Selection — Mevcut Tuning Sözleşmesine Geri Dönüş

- Gemini/harici analiz, AFA'da `validation_pos` değerinin çok düşük olmasının temel class-imbalance nedenini doğru teşhis ediyor; ancak mevcut repository kodu açısından çözümün stratified split veya `validation_pos >= 0` fallback olması uygun değil.
- Önceki nested script, sparse AFA hedefinde representation-level ve hyperparameter-level foldlara gereğinden fazla minimum-event şartı koyarak deneyin tamamını kilitlemişti.
- Düzeltme: representation nested smoke artık projede daha önce gerçek veride kullanılan `smoke_test_feature_ablation_real.py` içindeki `_select_best_candidate(...)` tuning davranışını yeniden kullanıyor. Bu helper representation-specific `columns` ile çalışıyor ve mevcut chronological inner folds içinde iki-sınıflı validation bulunan fold skorlarını kullanıyor; mevcut tuning sözleşmesini yeniden icat etmiyor.
- Representation selection dışındaki `outer` protokolü korunuyor: chronological walk-forward, outer test size 40, gap=5, production target h5/+3%. Representation seçiminde 2 validation fold şartı ayrıca korunuyor; tek/çiftsınıfsız representation foldları skorlanmıyor.
- Böylece class imbalance için zamanı bozan stratification kullanılmıyor ve production target +3% sadece smoke testi çalışsın diye değiştirilmemiş oluyor.
- Düzeltme commit: `d164a82d844d2e61d028459abda98f51ca3b37e0`.
- Yeni AFA gerçek sonucu henüz alınmadı; production representation `raw_all` olarak korunuyor.

### Faz 5 Nested Representation Selection — Sparse AFA Fold Tasarımı Düzeltmesi

- Son AFA çıktısı kök nedeni kesinleştirdi: 470 dataset satırında h5/+3% target yalnızca yaklaşık 36–37 pozitif event içeriyor ve son kronolojik validation pencerelerinde 40/60/80 gözlem içinde yalnızca 0–1 pozitif event bulunuyor.
- Önceki düzeltme representation ve tuning validationlarının her ikisinde de her fold için minimum 2 pozitif + 2 negatif şartı koyduğu için, mevcut AFA zaman serisinde geçerli nested fold üretmeyi imkânsız hale getirdi.
- Bu şart gereğinden katıydı. Representation selection validation'ında en az iki sınıflı fold şartı korunurken sparse-event inner hyperparameter tuning tarafında olay yeterliliği `validation >= 1 positive, >= 2 negative` olarak ayrıştırıldı. Amaç sahte denge üretmek değil, +3% event'in mevcut tarihsel yoğunluğunda modeli tune edebilmek.
- Ancak daha önemlisi, representation-level fold oluşturma artık yapay biçimde 80/100'e kadar pencere arayıp tüm deneyin başlamasını engellemiyor; standart chronological 2-fold / 40 observation selection düzeni korunuyor ve geçersiz foldlar ayrıca raporlanıyor.
- Production target, outer test fold, gap ve representation seti değiştirilmedi. Production representation yine `raw_all`.
- Düzeltme commit: `781df1a21aabe127c6ffeacf67735b7f6a18d030`.

### Faz 5 Nested Representation Selection — Adaptive Event-Stable Fold Düzeltmesi

- Önceki 20 -> 40 düzeltmesine rağmen AFA'da hata devam etti; son çıktı, 40'lık representation foldunun içinde hyperparameter tuning için gereken iki kronolojik validation foldunun da stabil olmadığına işaret etti.
- Sabit validation boyutu kullanmak yerine nested representation tuning için yeni `_find_stable_inner_splits()` helper'ı eklendi.
- Helper yalnızca outer-training döneminde çalışıyor ve kronolojik walk-forward splitlerden en küçük uygun pencereyi seçiyor: representation selection için 40/60/80; representation-specific hyperparameter tuning için 40/60/80/100.
- Bir foldun geçerli sayılması için training tarafında en az 2 pozitif + 2 negatif, validation tarafında en az 2 pozitif + 2 negatif event gerekiyor. Böylece seyrek +3% target nedeniyle tek pozitifli veya tek-sınıflı validation pencereleri candidate selection'a sokulmuyor.
- Representation score yine iki ayrı chronological validation foldu üzerinden hesaplanıyor; seçilen candidate yalnızca ilgili representation feature kolonlarıyla fit ediliyor. Outer test foldları selection dışında tutuluyor.
- Bu yaklaşım production target'ı, outer test boyutunu veya leakage gap'ini gevşetmiyor; yalnızca sparse-event nested validation penceresini outer-training içinde daha yeterli hale getiriyor.
- Düzeltme commit: `1efd56388f2ede16e9a1b5158972a84e0d417c4e`.
- Yeni AFA gerçek sonucu henüz alınmadı; production representation `raw_all` olarak korunuyor.

### Faz 5 Nested Representation Selection — Hyperparameter Inner Validation Penceresi Düzeltmesi

- AFA gerçek çalıştırmasında yeni diagnostic log kök nedeni netleştirdi: representation-level validation 40 gözleme çıkarılmış olmasına rağmen, representation-specific hyperparameter tuning içinde validation boyutu hâlâ 20 idi.
- AFA'nın h5/+3% target'ında representation training frame'lerinin pozitif oranı yaklaşık %12–14 iken, son 20 gözlemli inner validation pencereleri tek sınıfa düşebiliyor. Bu durumda 12 XGBoost candidate'ın tamamı iki valid inner fold şartını karşılayamıyor; representation seçimi başlamadan `no representation has the required number of valid inner folds` oluşuyor.
- Düzeltme: representation-specific hyperparameter tuning validation boyutu 20 -> 40 yapıldı. Representation selection validation boyutu da 40 olarak kalıyor. Inner tuning ve representation selection artık aynı yeterli olay örnekleme penceresini kullanıyor; outer test yine 40 ve gap=5.
- Ayrıca tuning foldları candidate loop'tan önce kontrol edilerek tek-sınıflı foldların nedeni doğrudan hata mesajında raporlanacak. Selection stability kuralı gevşetilmedi; iki valid inner fold hâlâ zorunlu.
- Düzeltme commit: `6ff8464c7d980b82bf92f52f077f30988638b799`.
- Production representation hâlâ `raw_all`; yeni AFA nested sonuçları henüz alınmadı.

### Faz 5 Nested Representation Selection — AFA'da Tek Sınıflı Validation Fold Teşhisi ve Stabilizasyon

- Üçüncü AFA rerun'da veri hazırlama yine aynı: 674 raw rows, 470 dataset rows; failure yine `_select_representation` seviyesinde oluştu.
- Kod incelemesinde `_score_representation()` içinde representation seçim validation'larının 20 gözlem olduğu görüldü. AFA'nın mevcut +3% target'ı seyrek olduğundan 20 gözlemli validation fold tek sınıf kalabiliyor. Kod bu foldları `continue` ile atladığı için `valid_folds` 2'ye ulaşmadan tüm representation skorları `None` olabiliyor; aynı hata mesajı bu durumu gizliyordu.
- Bu davranış representation/model problemi değil, nested representation selection'ın validation penceresinin seyrek pozitif target için fazla küçük olabilmesidir. Production outer test folduna dokunulmadı.
- Stabilizasyon: representation selection içindeki iki validation foldunun `test_size` değeri 20 -> 40 yapıldı. Hyperparameter tuning'in kendi validation boyutu ise 20 olarak korundu. Candidate tuning ayrıca en az iki valid inner fold üreten adaylar arasından seçiliyor; tek/eksik fold skoru selection'a sokulmuyor.
- Böylece representation selection daha yeterli event örneği içeren validation penceresi kullanıyor; outer leakage protokolü, gap=5 ve production target h5/+3% değişmedi.
- Düzeltme commit: `0b645f23b92dd706241f65ad14e40a2e719323ad`.
- Yeni AFA gerçek sonucu henüz alınmadı; production representation `raw_all` olarak korunuyor.

### Faz 5 Nested Representation Selection — Representation-Specific Tuning Düzeltmesi

- AFA rerun'da diagnostic log beklenmesine rağmen `_select_representation` aşamasında yine tüm adayların valid fold şartını geçemediği için exception detayları görünmedi.
- Kod incelemesiyle asıl metodolojik hata doğrulandı: nested representation scripti `app.ml.tuning.select_best_candidate()` çağırıyordu; bu ortak tuning helper'ı her zaman production `feature_columns(asset_type)` setini doğrulayıp kullanıyor. Bu nedenle `normalized_all` ve özellikle `stationary_core` representation seçimi gerçekten kendi feature seti üzerinden tuning yapmıyordu.
- Düzeltme: nested script içine representation-specific candidate tuning helper eklendi. Candidate grid aynı tutuldu; inner walk-forward PR-AUC hesaplaması artık doğrudan ilgili representation'ın `columns` seti ile yapılıyor.
- Outer evaluation da aynı representation-specific tuning helper'ına taşındı; böylece seçilen representation'ın hyperparameter seçimi ve final outer fit aynı feature representation üzerinde gerçekleşiyor.
- Selection threshold/gap/class-balance kuralları gevşetilmedi.
- Düzeltme commit: `f2633ab57d6b3b7b62e77a29128bb2813898e242`.
- Yeni AFA gerçek nested sonucu henüz alınmadı; production representation `raw_all` olarak korunuyor.

### Faz 5 Nested Representation Selection — Inner Tuning Teşhis Logu

- AFA rerun'da veri hazırlama yine başarılı: 674 raw, 470 dataset rows.
- `_score_representation` çağrı sözleşmesi düzeltildikten sonra selection aşamasında tüm representation adaylarının en az 2 valid inner fold şartını geçemediği tekrar görüldü.
- Nested scriptte `select_best_candidate` kaynaklı `ValueError` daha önce sessizce `continue` edildiği için gerçek eleme nedeni görünmüyordu.
- Teşhis amacıyla inner fold boyutları, train/validation positive rate ve yakalanan `ValueError` artık loglanıyor. Bu değişiklik metodolojiyi gevşetmiyor; yalnızca hangi inner tuning koşulunun adayları elediğini görünür kılıyor.
- Commit: `f099e436deb90d46ffc0310acb2ee8ad205d44e8`.
- Bu aşamada production representation `raw_all` olarak korunuyor; yeni gerçek AFA sonucu henüz alınmadı.

### Faz 5 Nested Representation Selection — İkinci Kod Hatası Düzeltmesi

- AFA rerun sonrası `TypeError: _score_representation() got an unexpected keyword argument 'columns'` görüldü.
- Kod incelemesinde önceki düzeltmenin çağrı tarafına `columns` eklediği ancak fonksiyon gövdesinin parametre imzasının eksik kaldığı ve ayrıca `prepared/frame` isimlerinin tutarsız olduğu doğrulandı.
- Düzeltme: `_score_representation` artık `prepared` ve `columns: tuple[str, ...]` parametrelerini açıkça kabul ediyor; walk-forward ve dropna işlemleri bu hazırlanmış frame/column seti üzerinde yürütülüyor.
- Düzeltme commit: `ef98ac8c020727d96e80c15effdf07000115ee25`.
- AFA nested representation gerçek sonucu henüz alınmadı; production representation `raw_all` olarak korunuyor.

### Faz 5 Nested Representation Selection — İlk AFA Çalıştırması ve Düzeltme

- AFA nested representation smoke PostgreSQL canonical history ile veri hazırlama aşamasını geçti: 674 raw rows, 470 dataset rows.
- İlk çalıştırmada `_select_representation` tüm adaylarda `valid_folds < 2` gördü ve `no representation has the required number of valid inner folds` hatası verdi.
- İnceleme sonucunda representation'ın outer-train için zaten hazırlanmış frame'inin `_score_representation` içinde ikinci kez `_prepare_variant` ile hazırlanması tespit edildi. Özellikle normalized/stationary varyantlarda bu, nested seçim frame'inin yanlışlıkla yeniden dönüştürülmesine neden olabiliyordu.
- Düzeltme: `_score_representation` artık kendisine verilen hazırlanmış frame ve açık feature-column seti üzerinde çalışıyor; representation varyantı ikinci kez uygulanmıyor.
- Düzeltme commit: `770f772d3cda1d20708e30a1716e7f1168fc631e`.
- Production representation hâlâ `raw_all`; AFA gerçek nested sonuçları henüz değerlendirilmedi.

### Faz 5 Nested Target-Contract Selection — Düzeltilmiş Gerçek Çalıştırma

Selection stability düzeltmesinden sonra AFA ve THYAO nested smoke tekrar çalıştırıldı. Candidate selection artık yalnızca en az 2 valid inner fold'a sahip adaylar arasından yapılıyor; PR-AUC primary objective, ROC-AUC ve fold PR std secondary criteria. Class balance raporlanıyor ancak keyfi bir hedef orana göre optimize edilmiyor.

**AFA — PostgreSQL canonical history, 674 raw rows**

- Outer 1: h=5, threshold=1%; inner PR 0.4419, ROC 0.7578, PR std 0.1373, positive 0.200, direction 100%, valid folds 2.
- Outer 2: h=5, threshold=1%; inner PR 0.7127, ROC 0.5463, PR std 0.0855, positive 0.625, direction 50%, valid folds 2.
- Outer 3: h=10, threshold=3%; inner PR 0.9037, ROC 0.7679, PR std 0.0963, positive 0.375, direction 100%, valid folds 2.
- Outer fold sonuçları: fold 1 h=5/+1% ROC 0.4258 / PR 0.6247 / Spearman -0.1226; fold 2 h=5/+1% ROC 0.5514 / PR 0.5209 / Spearman +0.0889; fold 3 h=10/+3% ROC 0.3354 / PR 0.2513 / Spearman -0.2546.
- AFA selection tek bir contract üzerinde sabit kalmadı; ilk iki fold +1%, son fold +3% seçildi. Inner skorların outer OOS'a aynı ölçüde taşınmadığı görüldü.
- Bu nedenle AFA sonucu production target değişimi için yeterli değildir.

**THYAO — Borsapy provider fallback, 685 raw rows**

- Outer 1: h=10, threshold=1%; inner PR 0.7033, ROC 0.4825, PR std 0.0097, positive 0.525, direction 50%, valid folds 2.
- Outer 2: h=5, threshold=1%; inner PR 0.7282, ROC 0.6836, PR std 0.1646, positive 0.375, direction 50%, valid folds 2.
- Outer 3: h=10, threshold=1%; inner PR 0.5567, ROC 0.3737, PR std 0.0023, positive 0.550, direction 50%, valid folds 2.
- Outer fold sonuçları: fold 1 h=10/+1% ROC 0.5556 / PR 0.4393 / Spearman +0.0902; fold 2 h=5/+1% ROC 0.4036 / PR 0.3459 / Spearman -0.1636; fold 3 h=10/+1% ROC 0.9737 / PR 0.7500 / Spearman +0.3577.
- THYAO'da threshold +1% üç fold'un tamamında seçildi ancak horizon 5/10 arasında değişti ve outer sonuçlar belirgin heterojen kaldı.
- Fold 3'te %5 pozitif oranı ile ROC 0.9737 / PR 0.7500 gözlenmesi örneklem/regime etkisinin güçlü olabileceğini gösteriyor; tek fold üzerinden contract seçimi yapılmadı.

**Nested selection kararı:**
- En az 2 valid inner fold kuralı gerekli ve korunuyor.
- AFA + THYAO sonuçları ortak, stable bir horizon/threshold contract göstermiyor.
- Mevcut production contract **horizon=5, threshold=+3%** olarak korunuyor.
- Nested çalışma, target contract'ın sembol/fold rejimine duyarlı olabileceğini gösteren deneysel kanıt olarak kaydedildi; production değişikliği olarak kabul edilmedi.

### Faz 5 Target Threshold Direction — AFA

Aynı leakage-safe chronological outer protokolü ile mevcut target diagnostic çalıştırıldı. Bu çalışma **descriptive diagnostic** olarak değerlendirildi; production target seçimi yapılmadı.

**AFA — PostgreSQL canonical history, 674 raw rows, 470 feature rows**

| Target | Positive rate | Baseline ROC | Baseline PR | Tuned ROC | Tuned PR | Baseline direct Spearman |
|---|---:|---:|---:|---:|---:|---:|
| >1% | 42.6% | 0.5172 | 0.5291 | 0.5159 | 0.5061 | +0.0298 |
| >2% | 22.3% | 0.4660 | 0.2992 | 0.4109 | 0.2630 | -0.0544 |
| >3% | 13.4% | 0.3398 | 0.2137 | 0.3587 | 0.2324 | -0.2254 |
| >5% | 5.7% | 0.5446 | 0.1603 | 0.7319 | 0.1139 | +0.0446 |

- AFA'da threshold değişimi direction davranışını belirgin biçimde değiştiriyor: baseline direct Spearman +0.0298 -> -0.0544 -> -0.2254 -> +0.0446.
- >3% mevcut contract'ta aggregate inverse ROC 0.6602; >5% tuned direct ROC 0.7319 olsa da PR 0.1139 ve positive rate yalnızca 5.7%.
- Bu sonuçlar outer OOS candidate selection için kullanılmamalıdır; yalnızca target definition'ın model davranışını ciddi biçimde etkilediğini gösteren diagnostic kanıttır.

### Faz 5 Target Threshold Direction — THYAO

**THYAO — Borsapy provider fallback, 685 raw rows, 481 feature rows**

| Target | Positive rate | Baseline ROC | Baseline PR | Tuned ROC | Tuned PR | Baseline direct Spearman |
|---|---:|---:|---:|---:|---:|---:|
| >1% | 39.7% | 0.5169 | 0.3722 | 0.4793 | 0.3602 | +0.0275 |
| >2% | 28.9% | 0.5977 | 0.3568 | 0.5612 | 0.3288 | +0.1353 |
| >3% | 22.0% | 0.5597 | 0.2883 | 0.5638 | 0.2731 | +0.0755 |
| >5% | 13.3% | 0.5665 | 0.3463 | 0.5133 | 0.2637 | +0.0716 |

- THYAO'da baseline direct direction dört threshold'un tamamında pozitif Spearman tarafında kaldı.
- >2% baseline ROC 0.5977 ile >3% baseline ROC 0.5597'nin üzerinde olsa da bu outer OOS candidate selection için kullanılmadı.
- AFA ile THYAO birlikte değerlendirildiğinde ortak bir threshold/direction sonucu çıkmıyor.

**Karar:** Target threshold'un direction ve class balance üzerinde güçlü etkisi doğrulandı; ancak iki sembolde ortak production target seçimi için yeterli leakage-safe evidence yok. Mevcut production contract **horizon=5, threshold=+3%** olarak korunuyor.

### Faz 5 Nested Target-Contract Selection — İlk Gerçek Çalıştırma

İlk nested smoke AFA ve THYAO üzerinde çalıştırıldı. Candidate selection inner tuned validation ile yapıldı; seçilen candidate yalnızca ilgili outer foldda değerlendirildi.

**AFA**
- Outer 1: h=10, threshold=2%; inner PR 1.0000, ROC 1.0000, ancak yalnızca 1 valid inner fold.
- Outer 2: h=10, threshold=1%; inner PR 0.9648, ROC 0.4737, 1 valid inner fold.
- Outer 3: h=10, threshold=3%; inner PR 0.9037, ROC 0.7679, 2 valid inner fold.
- Outer results: fold 1 ROC 0.4734 / PR 0.7607; fold 2 ROC 0.5000 / PR 0.5074; fold 3 ROC 0.3354 / PR 0.2513.
- Bu ilk koşu production target seçimi için kabul edilmedi. Özellikle 1 valid inner fold üzerinden PR 1.0000 gibi skorların candidate seçimine girebilmesi selection stability açısından yetersiz bulundu.

**THYAO**
- Outer 1: h=10, threshold=1%; inner PR 0.7033, ROC 0.4825, 2 valid fold.
- Outer 2: h=5, threshold=1%; inner PR 0.7282, ROC 0.6836, 2 valid fold.
- Outer 3: h=10, threshold=1%; inner PR 0.5567, ROC 0.3737, 2 valid fold.
- Outer results: fold 1 ROC 0.5556 / PR 0.4393; fold 2 ROC 0.4036 / PR 0.3459; fold 3 ROC 0.9737 / PR 0.7500.
- THYAO'da threshold +1% üç outer selection'ın tamamında görüldü; horizon 5/10 arasında değişti. Ancak outer fold sonuçları heterojen olduğundan production contract değiştirilmedi.

**Selection metodolojisi düzeltmesi**
- Candidate selection artık en az 2 valid inner fold gerektiriyor.
- 1 valid fold üzerinden gelen adaylar selection'dan çıkarılıyor.
- Class balance raporlanıyor fakat keyfi bir target rate'a (ör. %20) doğru optimize edilmiyor.
- PR-AUC primary objective; ROC-AUC ve fold PR standard deviation secondary criteria.
- Bu düzeltmeden sonra AFA ve THYAO nested smoke yeniden çalıştırılmalıdır.

### Faz 5 Taskları

- [x] Tuning dataset / inner-validation foundation oluştur.
- [x] XGBoost hyperparameter candidate search katmanı oluştur.
- [x] Baseline vs tuned modelleri aynı outer walk-forward protokolünde karşılaştır.
- [x] Feature importance / gain raporlama foundation'ı oluştur.
- [x] Model probability calibration ihtiyacını değerlendir.
- [x] Risk adjustment foundation'ını uygula ve unit testlerini ekle.
- [x] Signal foundation ve deterministic BUY/HOLD/SELL rules oluştur.
- [x] Leakage-safe signal scaling ve threshold smoke validationlarını çalıştır.
- [x] 6-symbol direction diagnostic tamamlandı; global direct/inverse production yönü seçilmedi.
- [x] AFA baseline vs tuned direction OOS karşılaştırması tamamlandı.
- [x] THYAO baseline vs tuned direction OOS karşılaştırması tamamlandı.
- [x] Tuning'in direction davranışına etkisi AFA + THYAO üzerinde ayrıştırıldı; global direction değişikliği yapılmadı.
- [x] Target threshold direction diagnostic AFA + THYAO tamamlandı.
- [ ] Target/model contract revizyonunu yalnızca leakage-safe inner validation evidence ile deneysel değerlendir.\n- [x] Nested target-contract selection smoke altyapısı oluşturuldu; 12 candidate (horizon 3/5/10 × threshold 1/2/3/5%) inner tuned validation ile seçiliyor ve outer evaluation yalnızca seçilen candidate'ın ilgili foldunda yapılıyor.
- [ ] Düzeltilmiş normalized feature/model audit'ini ilgili coverage üzerinde çalıştır.
- [x] Faz 5 acceptance testleri: 3 passed.
- [x] Tüm ML test suite: 75 passed in 6.15s.

## Faz 5 Signal Chain — Gerçek OOS Doğrulama Altyapısı

- Production signal chain için ayrı gerçek-veri smoke scripti eklendi: `backend/scripts/smoke_test_signal_chain_real.py`.
- Protokol: expanding chronological walk-forward, 3 outer fold, 40 gözlem/fold, gap=5.
- Production ML contract sabit: horizon=5, threshold=+3%; feature representation bu testte mevcut production default olan `raw_all`.
- Her outer fold içinde yalnızca outer-train döneminde 2-fold inner walk-forward XGBoost tuning yapılır; seçilen model outer test üzerinde bir kez değerlendirilir.
- Signal chain her OOS gözleminde sırayla ML probability + Technical Score + Risk Adjustment -> final 0–100 signal score üretir.
- Risk etkisini ayrıştırmak için aynı gözlemde pre-risk signal score da raporlanır; böylece risk adjustment'ın skoru ne kadar değiştirdiği ayrıca ölçülür.
- OOS raporu ROC-AUC, PR-AUC, target/forward-return Spearman, bileşen dağılımları ve risk etkisini içerir. BUY/HOLD/SELL threshold winner seçilmez.
- Historical OOS içinde geçmişe ait gerçek-time freshness/stale_days yeniden kurulamayacağı için `quality_ok=True, stale_days=0` varsayımı açıkça raporlanır; bu smoke risk composition'ı doğrular, historical freshness davranışı hakkında iddia üretmez.
- Kod commit: `22562255dd05b9044c2ce5e5f402f9d01284c0fd`.


## Faz 5 Signal Chain — Gerçek OOS Sonuçları

Production-compatible signal chain gerçek 3-fold / 120 OOS gözleminde AFA, AFT ve THYAO üzerinde çalıştırıldı. Bu çalışma teknik smoke başarıyla tamamlandı; ancak foldlar arası yön ve metrik oynaklığı nedeniyle production signal performansı için genel bir üstünlük kanıtı oluşmadı.

**AFA — PostgreSQL canonical history, 674 raw / 470 dataset rows, h5/+3%**

- Fold 1: inner PR 1.0000. Pre-risk ROC/PR 0.3828/0.3406; final 0.4167/0.3584. Final Spearman(target) -0.1415, Spearman(forward) +0.0081.
- Fold 2: inner PR 0.4831. Pre-risk 0.7153/0.3676; final 0.7014/0.2420. Final Spearman(target) +0.2094, Spearman(forward) -0.1454.
- Fold 3: inner PR 0.5694. Pre-risk 0.1486/0.0872; final 0.1486/0.0872. Final Spearman(target) -0.4027, Spearman(forward) -0.0728.
- Aggregate descriptive result: pre-risk ROC/PR 0.2863/0.1869; final ROC/PR 0.2931/0.1679. Final signal direction hâlâ negatif Spearman(target) -0.2911.

**AFT — PostgreSQL canonical history, 677 raw / 473 dataset rows, h5/+3%**

- Fold 1: inner PR 0.5020. Pre-risk ROC/PR 0.5581/0.6166; final 0.4848/0.5706. Final Spearman(target) -0.0261, Spearman(forward) +0.0283.
- Fold 2: inner PR 0.7000. Pre-risk 0.8725/0.6817; final 0.9902/0.9583. Final Spearman(target) +0.6065, Spearman(forward) +0.2940.
- Fold 3: inner PR 0.7114. Pre-risk 0.1880/0.2216; final 0.0883/0.2067. Final Spearman(target) -0.6682, Spearman(forward) -0.6764.
- Aggregate descriptive result: pre-risk ROC/PR 0.4956/0.4300; final ROC/PR 0.4881/0.4636. Risk adjustment bazı foldlarda performansı yükseltirken bazı foldlarda düşürüyor.

**THYAO — Borsapy provider fallback, 685 raw / 481 dataset rows, h5/+3%**

- Fold 1: inner PR 0.6896. Pre-risk ROC/PR 0.6667/0.3692; final 0.7013/0.3265. Final Spearman(target) +0.2650, Spearman(forward) +0.1032.
- Fold 2: inner PR 0.5441. Pre-risk 0.4086/0.1997; final 0.3297/0.1909. Final Spearman(target) -0.2464, Spearman(forward) -0.1298.
- Fold 3: inner PR 0.2835. Pre-risk 0.5586/0.1132; final 0.5225/0.0980. Final Spearman(target) +0.0206, Spearman(forward) -0.5315.
- Aggregate descriptive result: pre-risk ROC/PR 0.6170/0.2405; final ROC/PR 0.5581/0.1924. Risk adjustment sonrası aggregate association zayıflıyor: target Spearman +0.1479 -> +0.0735; forward-return Spearman -0.0015 -> -0.0624.

**Ortak gözlem ve karar**

- Signal-chain üç sembolde de teknik olarak deterministik şekilde üretildi ve tüm 120 OOS gözleminde 0–100 sınırları korundu.
- Fold yönleri ortak değil: AFA ve AFT'te güçlü fold-to-fold değişim, THYAO'da ise daha ılımlı ama yine heterojen davranış var.
- Risk adjustment sabit yönde performans iyileştirmiyor. AFA'da aggregate ROC çok küçük artarken PR düşüyor; AFT'te PR küçük artarken ROC hafif düşüyor; THYAO'da hem ROC hem PR düşüyor.
- Final signal dağılımları düşük ve sembole göre değişken: AFA median 30.867, AFT median 29.792, THYAO median 14.227. Bu nedenle daha önce gözlenen global threshold ölçekleme problemi devam ediyor; bu çalışma yeni bir BUY/HOLD/SELL threshold seçmiyor.
- Risk katmanının historical OOS ölçümünde `quality_ok=True, stale_days=0` varsayımı kullanıldı. Dolayısıyla sonuçlar freshness/stale-data davranışını değerlendirmiyor.
- **Production kararı:** signal direction, weight, risk penalty veya BUY/HOLD/SELL threshold değiştirilmedi. Mevcut production contractlar (raw_all, h5/+3%, mevcut deterministic weights/risk foundation) korunuyor.
- **Signal-chain smoke:** AFA, AFT ve THYAO için `REAL SIGNAL CHAIN SMOKE TEST PASSED`.


### Faz 5 Signal Chain — AFS Sparse Inner Validation Düzeltmesi

- AFS signal-chain çalıştırması TEFAS fallback sonrasında veri alma aşamasını geçti ancak outer fold tuning sırasında `inner validation has no two-class fold` hatasında durdu.
- Kök neden yine sparse +3% event yapısı: mevcut global `app.ml.tuning.select_best_candidate()` validation foldlarının hiçbirini kullanılabilir bulmadığında tüm adayları exception ile reddediyor.
- Global tuning helper değiştirilmedi. Signal-chain smoke scriptine, daha önce gerçek feature-ablation deneyinde kabul edilen sparse-event davranışını aynalayan local `_select_best_candidate_sparse()` helper eklendi.
- Bu helper chronological inner split ve `gap=5` kurallarını koruyor; tek-sınıflı validation foldlarını atlıyor ve en az bir iki-sınıflı validation fold bulunursa adayın ortalama PR-AUC'sini kullanıyor. Hiç geçerli fold yoksa yine açıkça inconclusive/failure veriyor.
- Train tarafının tek-sınıflı olması hâlâ hata; validation gevşetme, random/stratified split veya outer-test kullanımı yapılmadı.
- Production model/tuning helper, target contract ve signal weights değiştirilmedi.
- Düzeltme commit: `8da5e76c117c62acc3460ebcb51d4481bcd058f4`.

### Faz 5 Signal Chain — AFS Veri Kaynağı Düzeltmesi

- AFS signal-chain smoke ilk çalıştırmada `ValueError: no DB fund history found for AFS` ile durdu.
- Kök neden model/signal tarafı değil; PostgreSQL canonical history içinde AFS için hiç fund history bulunmamasıydı.
- Mevcut diğer gerçek fund smoke testlerinde kullanılan TEFAS provider fallback'i signal-chain scriptine de eklendi.
- Fund loader artık önce PostgreSQL canonical history'yi dener; kayıt sayısı `--min-db-rows` altında kalırsa TEFAS provider ile chunked history çeker.
- TEFAS fallback için `--chunk-delay` CLI parametresi eklendi; varsayılan 3 saniyedir.
- Kaynak çıktısı korunuyor: `PostgreSQL canonical history` veya `TEFAS provider (DB history insufficient)`.
- Production model/target/signal contract değiştirilmedi.
- Düzeltme commit: `917193d6bd6bfb61112c7efebef90061435a93ad`.

### Faz 5 Signal Chain — TEFAS Transport Retry Düzeltmesi

- AFS signal-chain ikinci çalıştırmasında TEFAS fallback'e ulaşıldı ancak `fonGnlBlgSiraliGetir` isteği `httpx.RemoteProtocolError: Server disconnected without sending a response` ile kesildi.
- Mevcut `TefasProvider._post()` yalnızca HTTP 429 durumunda retry yapıyor; transient `httpx.TransportError` için ilk hatada doğrudan `TefasProviderError` yükseltiyordu.
- Provider'a yalnızca `httpx.TransportError` için mevcut retry sayısını kullanan exponential backoff eklendi. 429 davranışı ve diğer HTTP/validation hataları değiştirilmedi.
- `backend/tests/data/test_tefas_rate_limit.py` içine RemoteProtocolError sonrası retry ve başarı davranışını doğrulayan test eklendi.
- Production ML/signal contract değiştirilmedi; değişiklik yalnızca veri sağlayıcı resiliency katmanındadır.
- Provider commit: `eb2c449c0b074b9100e4c3450ebf6b9dc9c0d5fb`.
- Test commit: `77a687ef853e70ab772b0408cdc7e01615c3f3bd`.
- Codespace'te test suite henüz çalıştırılmadı; AFS signal-chain yeniden denenmeli.


### Faz 5 Signal Chain — AFS Gerçek OOS Sonucu

- AFS smoke TEFAS provider fallback ile başarıyla tamamlandı: 685 raw rows, 481 dataset rows, 120 OOS rows; production target h=5 / +3%.
- Sparse inner validation fallback yalnızca gerektiğinde devreye girdi: outer fold 1'de 40 gözlem, fold 2'de 60 gözlem kullanıldı; fold 3 normal 20 gözlemli validation ile iki sınıflı kaldı. Bu seçimler outer-training dönemi içinde ve chronological walk-forward olarak yapıldı; gap=5 korundu.
- Fold 1: inner PR-AUC 0.0385; pre-risk ROC/PR 0.0263/0.0388; final 0.1711/0.0442; final Spearman(target) -0.2484; forward-return -0.6674.
- Fold 2: inner PR-AUC 0.0250; pre-risk 0.3793/0.2373; final 0.3824/0.2380; final Spearman(target) -0.1819; forward-return -0.2711.
- Fold 3: inner PR-AUC 0.7282; pre-risk 0.2511/0.1297; final 0.2597/0.1321; final Spearman(target) -0.3163; forward-return -0.2638.
- Aggregate: pre-risk ROC/PR 0.4675/0.1579; final ROC/PR 0.5040/0.1658; final Spearman(target) +0.0052; forward-return -0.0706.
- Risk impact: mean adjustment -1.1472, mean absolute change 1.1472, max absolute change 4.6667; risk adjustment Spearman(target) +0.1669, forward-return -0.0400.
- Final signal median 25.081; overall target rate 0.167. Final signal direction/association güçlü ve stabil bir ilişki göstermedi.
- Historical OOS freshness yeniden kurulamadığı için quality_ok=True, stale_days=0 varsayımı korundu; bu sonuç freshness performansı hakkında iddia üretmez.
- Karar: AFS teknik signal-chain smoke'u geçti ancak cross-fold heterojenliği ve düşük OOS association nedeniyle signal direction, weights, risk penalty veya BUY/HOLD/SELL threshold değiştirilmedi. Production contractlar (raw_all, h5/+3%, mevcut deterministic risk/signal foundation) korunuyor.
- AFS sonucu REAL SIGNAL CHAIN SMOKE TEST PASSED ile tamamlandı.


### Faz 5 Signal Chain — ASELS, TUPRS ve BIMAS Gerçek OOS Sonuçları

Üç production stock smoke sembolü de aynı 3-fold chronological / 40-test / gap=5 signal-chain protokolünü teknik olarak geçti. Üçünde de inner validation 20 gözlem ve iki sınıflı foldlar yeterli oldu; bu nedenle AFS için eklenen sparse 40/60 fallback'i burada devreye girmedi.

**ASELS — Borsapy provider fallback, 685 raw / 481 dataset / 120 OOS**

- Fold 1: inner PR 0.5501; pre-risk ROC/PR 0.6752/0.4589; final 0.6781/0.4606; target Spearman +0.2890; forward-return +0.1722.
- Fold 2: inner PR 0.5297; pre-risk 0.5000/0.3599; final 0.4753/0.3493; target Spearman -0.0409; forward-return -0.1560.
- Fold 3: inner PR 0.6635; pre-risk 0.3393/0.2526; final 0.2351/0.2418; target Spearman -0.4206; forward-return -0.5332.
- Aggregate: pre-risk ROC/PR 0.5356/0.3627; final ROC/PR 0.5125/0.3546. Final target Spearman +0.0203; forward-return Spearman -0.0888.
- Risk impact: mean adjustment -8.2967, max absolute change 13.8152; risk adjustment target Spearman -0.2369, forward-return -0.2425.
- Final signal median 32.770; target rate 0.325.

**TUPRS — Borsapy provider fallback, 685 raw / 481 dataset / 120 OOS**

- Fold 1: inner PR 0.6116; pre-risk ROC/PR 0.2814/0.1472; final 0.2511/0.1353; target Spearman -0.3277; forward-return -0.4889.
- Fold 2: inner PR 0.3708; pre-risk 0.6200/0.6801; final 0.6500/0.7096; target Spearman +0.2599; forward-return +0.1749.
- Fold 3: inner PR 0.6580; pre-risk 0.6591/0.6225; final 0.6162/0.6083; target Spearman +0.2003; forward-return +0.2156.
- Aggregate: pre-risk ROC/PR 0.5241/0.4580; final ROC/PR 0.5375/0.4735. Final target Spearman +0.0629; forward-return Spearman -0.0112.
- Risk impact: mean adjustment -6.6448, max absolute change 11.0043; risk adjustment target Spearman +0.0569, forward-return +0.0013.
- Final signal median 24.549; target rate 0.375.

**BIMAS — Borsapy provider fallback, 685 raw / 481 dataset / 120 OOS**

- Fold 1: inner PR 0.6480; pre-risk ROC/PR 0.2530/0.2184; final 0.2530/0.2170; target Spearman -0.3923; forward-return -0.3790.
- Fold 2: inner PR 0.8094; pre-risk ROC/PR 0.8203/0.6021; final 0.8164/0.5288; target Spearman +0.4386; forward-return +0.5407.
- Fold 3: inner PR 0.5615; pre-risk 0.5413/0.4791; final 0.5556/0.4240; target Spearman +0.0902; forward-return -0.0767.
- Aggregate: pre-risk ROC/PR 0.4479/0.3379; final ROC/PR 0.4486/0.3196. Final target Spearman -0.0795; forward-return Spearman -0.1140.
- Risk impact: mean adjustment -4.3475, max absolute change 9.0170; risk adjustment target Spearman +0.0504, forward-return -0.1000.
- Final signal median 28.665; target rate 0.275.

**Yedi sembollük toplam signal-chain coverage özeti**

| Symbol | Asset | Data source | Final ROC | Final PR | Final Spearman(target) | Final Spearman(fwd) | Median signal |
|---|---|---|---:|---:|---:|---:|---:|
| AFA | Fund | PostgreSQL | 0.2931 | 0.1679 | -0.2911 | -0.0728 | 30.867 |
| AFT | Fund | PostgreSQL | 0.4881 | 0.4636 | +0.6065 | +0.2940 | 29.792 |
| THYAO | Stock | Borsapy | 0.5581 | 0.1924 | +0.0735 | -0.0624 | 14.227 |
| AFS | Fund | TEFAS | 0.5040 | 0.1658 | +0.0052 | -0.0706 | 25.081 |
| ASELS | Stock | Borsapy | 0.5125 | 0.3546 | +0.0203 | -0.0888 | 32.770 |
| TUPRS | Stock | Borsapy | 0.5375 | 0.4735 | +0.0629 | -0.0112 | 24.549 |
| BIMAS | Stock | Borsapy | 0.4486 | 0.3196 | -0.0795 | -0.1140 | 28.665 |

- Her sembol 120 OOS gözleminde teknik smoke testini geçti; toplam signal-chain coverage 840 OOS gözleme ulaştı.
- Sembol bazında final ROC-AUC 0.2931–0.5581, final PR-AUC 0.1658–0.4735 ve median signal 14.227–32.770 aralığında değişti. Bu ölçek heterojenliği global BUY/HOLD/SELL threshold seçimini desteklemiyor.
- Risk adjustment etkisi semboller arasında karışık: AFA'da ROC hafif yükselip PR düştü; AFT'te ROC düşüp PR yükseldi; THYAO ve ASELS'te hem ROC hem PR düştü; AFS'te ikisi de hafif yükseldi; TUPRS'ta ikisi de yükseldi; BIMAS'ta ROC çok küçük yükselirken PR düştü.
- Yedi sembolün sembol-bazlı metriklerinin basit aritmetik ortalaması descriptive olarak pre-risk ROC 0.4820 -> final 0.4774 ve pre-risk PR 0.3106 -> final 0.3053 gösteriyor. Bu pooled OOS metriği değildir; yalnızca sembol seviyesindeki sonuçların eşit ağırlıklı özetidir.
- Aggregate Spearman yönü universal değil: semboller arasında hem pozitif hem negatif değerler bulunuyor. Bu nedenle global signal direction inversion seçilmiyor.
- Historical freshness tüm sembollerde quality_ok=True, stale_days=0 varsayımı ile ölçüldü; bu coverage gerçek zamanlı stale-data performansını doğrulamıyor.

**Faz 5 Signal-chain kararı**

- Signal-chain 7 sembolde teknik olarak tamamlandı ve deterministic 0–100 bounds korunuyor.
- Ancak OOS performansı ve direction davranışı sembol/fold bazında heterojen. Risk adjustment evrensel bir performans artışı sağlamıyor ve signal scale semboller arasında kayıyor.
- Production kararı: raw_all, h5/+3% target, mevcut ML/Technical ağırlıkları, bounded risk penalty ve signal direction korunuyor. BUY/HOLD/SELL threshold seçilmiyor.
- Signal-chain smoke coverage tamamlandı; bundan sonraki çalışmalar Faz 6 altında kontrollü deneyler olarak ele alınmalıdır.

### Faz 5 Kapanış Öncesi — TEFAS Response Compatibility Regression

- Full backend test suite Codespace'te 139 passed, 1 failed verdi. Tek failure tests/data/test_free_providers.py::test_tefas_payload_mapping_with_fake_request.
- Kök neden TEFAS _post() retry kontrolünün response nesnesinde doğrudan status_code beklemesiydi. Mevcut lightweight FakeResponse yalnızca raise_for_status() ve json() implement ediyor; bu test contract'ı provider'daki retry değişikliğinden sonra kırıldı.
- Production davranışını değiştirmeden _post() artık status_code için default 200, headers için boş mapping kabul ediyor; gerçek httpx.Response davranışı ve 429/transport retry semantiği korunuyor.
- Mevcut fake-response mapping testi bu geriye dönük uyumluluğu doğrudan kapsıyor; ayrıca yeni test dosyası gerekmiyor.
- Düzeltme commit: 08b41f8c6fc5ed6baf727404eb289e4bef414d5d.
- Full suite bu düzeltmeden sonra henüz Codespace'te tekrar çalıştırılmadı; Phase 5 kapanışından önce yeniden çalıştırılmalıdır.

### Faz 5 Kapanış Öncesi — TEFAS fonKod Alias Regression Fix

- Önceki TEFAS compatibility düzeltmesinden sonra targeted provider testinde AttributeError kalktı ancak fake payload mapping testi 0 kayıt döndürdü.
- Kök neden doğrulandı: test/API payload row'unda fund code alanı fonKod iken _fetch_range() ve _to_symbol() yalnızca fonKodu okuyordu. Satır bu nedenle erken filtreleniyordu.
- Provider artık fon code çözümlemesinde fonKodu veya fonKod alanlarından ilk dolu değeri kullanıyor.
- Mevcut fake-response mapping testi bu davranışı doğrudan kapsıyor; production retry ve transport-error retry mantığı değiştirilmedi.
- Düzeltme commit: 2c7fa6f333374f41da7a93014eb585129889736c.
- Codespace targeted/full test rerun bu düzeltmeden sonra henüz yapılmadı; önce targeted provider + retry testleri, ardından full suite çalıştırılmalı.


### Faz 5 Kapanışı

- Codespace targeted provider/retry suite: 7 passed in 1.09s.
- Codespace full backend test suite: 140 passed in 6.43s.
- Gerçek signal-chain coverage: 7 sembol / 840 OOS gözlem.
- Faz 5 production contractları korunuyor: raw_all, horizon=5, target threshold=+3%, mevcut signal weights, bounded risk penalty, global direction inversion yok, BUY/HOLD/SELL threshold winner yok.
- Faz 6 başlangıç konusu: leakage-safe backtest ve prediction evaluation foundation.

### Faz 6 Başlangıcı — Backtest Foundation

- Faz 5 kapandı: 140 backend test geçti ve 7-symbol / 840-OOS signal-chain coverage tamamlandı.
- Faz 6 için ilk backtest foundation eklendi:
  - backend/app/backtesting/engine.py
  - backend/app/backtesting/metrics.py
  - backend/app/backtesting/__init__.py
- Engine long-only target-weight modelidir; target_weight 0.0–1.0 aralığındadır.
- Signal date t üzerindeki target ağırlık yalnızca t+1 open'da uygulanır. Bu nedenle aynı gün close veya t+1 close bilgi olarak execution kararına kullanılmaz.
- Transaction cost trade notional üzerinden bps olarak, slippage ise execution price üzerinde ayrı bps etkisi olarak uygulanır.
- Equity curve net transaction cost ve slippage sonrası tutulur.
- İlk metrikler: total return, annualized return/volatility, Sharpe, maximum drawdown, win rate, profit factor, total transaction cost, total slippage cost, total turnover.
- Backtest engine threshold seçmez; Phase 5'te production BUY/HOLD/SELL threshold seçilmediği için dışarıdan target_weight serisi alır. Bu ayrım korunmaktadır.
- Unit testleri eklendi: backend/tests/backtesting/test_engine.py ve backend/tests/backtesting/test_metrics.py.
- Faz 6 sözleşmesi docs/phase-6-backtesting.md içinde kayıtlıdır.
- Henüz Codespace test sonucu alınmadı. İlk doğrulama Phase 6 targeted tests, ardından full backend suite olmalıdır.


- Backtest buy sizing transaction costs/slippage dahil edilerek nakdin negatife düşmesini önleyecek şekilde düzeltildi; target weight maliyet sonrası küçük sapma gösterebilir.
- Bu davranış için backtest engine unit testi eklendi.

### Faz 6 Backtest — Transaction Cost Test Correction

- Phase 6 backtesting targeted suite ilk çalıştırmada 10 passed, 1 failed; full backend suite 150 passed, 1 failed verdi.
- Tek failure engine hesabından değil, testteki sabit 200.0 transaction-cost beklentisinden kaynaklandı. Pozisyon ilk execution sonrasında değer kazandığı için kapanış trade notional'ı ilk alış notional'ından daha büyüktür; dolayısıyla bps komisyon toplamı sabit 200.0 değildir.
- Test artık transaction cost'u trade logundaki toplam trade notional × configured fee rate üzerinden doğruluyor ve maliyetin equity'yi düşürdüğünü ayrıca koruyor.
- Engine davranışı değiştirilmedi.
- Test düzeltme commit: e1793186f247ef0f1f5d75712346b49c847615c1.
- Codespace'te targeted/full suite bu düzeltmeden sonra henüz tekrar çalıştırılmadı.

### Faz 6 Backtest — Continuous Signal Strategy Orchestration

- Phase 5 final signal output'unu backtest engine'e bağlayan `backend/app/backtesting/strategy.py` eklendi.
- `SignalScoreWeightConfig` 0–100 continuous score'u varsayılan olarak 0.0–1.0 target weight'e lineer ve bounded biçimde map eder. `score_floor`, `score_ceiling` ve `maximum_weight` açık konfigürasyondur.
- Bu mapping BUY/HOLD/SELL threshold seçimi veya Phase 5 production signal contractında değişiklik değildir; position sizing policy ayrı ve görünür tutulur.
- `prepare_signal_score_backtest_frame()` OOS signal, open ve close alanlarını canonical backtest frame'e dönüştürür. `run_signal_score_backtest()` bu frame'i mevcut next-open engine'e verir; aynı gün close ile execution yoktur.
- Sinyal skoru/price finite ve date uniqueness kontrolleri eklenmiştir. Target weight 0.0–1.0 sınırını korur.
- Unit testleri score mapping, capped exposure, next-open execution, source-specific kolon mapping ve non-finite score rejection davranışını kapsar.
- Local Python 3.14 doğrulaması: Phase 6 backtesting suite **16 passed, 1.49s**; full backend suite **156 passed, 13.77s**.

### Faz 6 Backtest — Named Market Cost Assumptions

- BacktestConfig'a `market_costs` eklendi. Her named market için transaction cost ve slippage bps değerleri `ExecutionCostConfig` ile ayrı tanımlanabilir.
- `run_long_only_backtest(..., market="BIST")` ve `run_signal_score_backtest(..., market="BIST")` ilgili override'ı uygular; piyasa adı case-insensitive normalize edilir. Market yoksa/bilinmiyorsa mevcut default bps davranışı korunur.
- Backtest sonucu seçilen normalized market ile kullanılan execution cost assumptions'ı açıkça taşır; historical sonuçların maliyet varsayımı audit edilebilir.
- Bu yapı market-specific tax, lot-size ve gerçek commission modelini henüz temsil etmez; onlar ayrı controlled task'lardır.
- Local Python 3.14 doğrulaması: Phase 6 backtesting suite **18 passed, 1.40s**; full backend suite **158 passed, 13.35s**.


### Codespace PostgreSQL Başlangıç Rutini

- Codespaces yeniden açıldığında PostgreSQL container'ı otomatik olarak çalışan durumda olmayabilir.
- Projede mevcut container adı sabittir: `stock-fund-predictor-postgres`.
- Her açılışta repo kökünde mevcut container'ı başlatmak için `docker start stock-fund-predictor-postgres` kullanılmalıdır.
- `docker compose up -d postgres` mevcut container durmuş haldeyken sabit `container_name` nedeniyle "container name ... is already in use" conflict hatası verebilir; bu durumda container silinmemeli, `docker start` kullanılmalıdır.
- PostgreSQL'in veri klasörü `postgres_data` named volume üzerindedir; container/volume gereksiz yere silinmemelidir.
- Ayrıntılı başlangıç talimatı: `docs/codespace-database-startup.md`.
- 2026-10-05 Codespace durumunda mevcut PostgreSQL container'ı `Exited` durumundan `docker start stock-fund-predictor-postgres` ile başarıyla `running` durumuna getirildi. Alembic migration komutu da bağlantı kurarak hata vermeden tamamlandı.



### Faz 6 — Gerçek Backtest Smoke Runner Hazırlığı

- `backend/scripts/smoke_test_backtest_real.py` Phase 5 signal-chain üretimini gerçek historical OHLCV ile Phase 6 backtest engine'ine bağlamak için hazırlandı.
- Stock historical data önce PostgreSQL canonical history'den okunur; DB history `--min-db-rows` altında kalırsa mevcut signal-chain davranışıyla Borsapy fallback kullanılır.
- ML feature setinde production contract olan `feature_columns("stock")` kullanılır; dataset'teki tüm kolonlar artık otomatik feature kabul edilmez.
- `--max-weight` CLI parametresi gerçekten `SignalScoreWeightConfig.maximum_weight` olarak uygulanır.
- Outer 3-fold / 40-test / gap=5 OOS sinyalleri birbirinden bağımsız backtest pencerelerinde çalıştırılır. Böylece foldlar arasındaki gap, yanlışlıkla next-open execution günü olarak kullanılmaz.
- Her foldun son sinyalinin ilgili OOS penceresi içinde bir sonraki open gözlemi olmadığı için cross-fold execution yapılmaz; foldlar bağımsız raporlanır.
- Production target contract sabit: horizon=5, positive threshold=+3%. Backtest continuous signal score -> target weight mapping kullanır; BUY/HOLD/SELL threshold seçimi yapmaz.
- Kod düzeltme commitleri: `618a88d814575d73054ef9b3469f4e77701ad7ca` ve `e8bceb300245367e77d5cb71e04f1cdeae6e2b87`.
- Codespace'te gerçek backtest smoke sonucu henüz alınmadı; PostgreSQL container'ı artık çalışır durumda olduğundan sıradaki doğrulama gerçek THYAO backtest çalıştırmasıdır.



### Faz 6 — Gerçek Backtest Smoke Veri-Yeterlilik Teşhisi

- THYAO gerçek backtest smoke ilk çalıştırmada `ValueError: not enough observations for backtest` ile durdu.
- Önceki `dataset < 140` kontrolü metodolojik olarak gereğinden keyfîydi ve kaldırıldı.
- Runner artık raw row ve hazırlanmış dataset row sayılarını çalıştırma başında açıkça yazıyor.
- Outer 3x40 / gap=5 için temel dataset yeterlilik kontrolü splitter sözleşmesine göre yapılıyor; inner tuning yetersizse hata mesajında ilgili outer training boyutu da raporlanıyor.
- Sonraki Codespace çalıştırmasında THYAO'nun gerçek raw/dataset coverage'ı görünür olacak; gerekirse `--days` artırılarak daha uzun history ile yeniden denenebilir.
- Düzeltme commit: `98a5d1846f666a54f92606dcb7e41e105e17618d`.
- Production target ve walk-forward contract değiştirilmedi.


### Faz 6 — Gerçek Backtest Smoke Pandas Kolon İndeksleme Düzeltmesi

- THYAO gerçek backtest smoke: PostgreSQL bağlantısı ve veri/fold yeterliliği geçildi; **685 raw / 481 dataset** gözlem bulundu.
- Ardından `KeyError` oluştu; kök neden `feature_columns("stock")` dönüşünün tuple olması ve pandas DataFrame kolon seçiminin `test[ml_columns]` şeklinde tuple ile yapılmasıydı.
- `ml_columns` artık açıkça `list(feature_columns("stock"))` olarak oluşturuluyor.
- Production feature contract, target, walk-forward/gap ve backtest stratejisi değiştirilmedi.
- Düzeltme commit: `ee9ef83e902654a61480b35fc1ee4018201662de`.
- Codespace gerçek backtest sonucu henüz tamamlanmadı; aynı smoke komutu yeniden çalıştırılmalı.


### Faz 6 — Gerçek Backtest Runner OHLCV / Tarih Hizalama Düzeltmesi

- THYAO gerçek backtest çalışmasında 685 raw / 481 dataset gözlemi başarıyla hazırlandı.
- Sonraki `KeyError: 'open'` hatasının kök nedeni `build_ml_feature_dataset()` çıktısının yalnızca model için `close + feature columns + target` taşıması; `open` kolonunun dataset contract'ında bulunmamasıydı.
- Backtest runner artık execution OHLCV'yi model dataset'inden beklemek yerine canonical raw market frame'den, OOS `trading_date` ile açıkça eşleştiriyor.
- Raw/technical market tarihleri `pd.Timestamp` olarak normalize ediliyor; duplicate trading date'ler erken hata olarak reddediliyor.
- Backtest stratejisi korunuyor: signal date t -> next available open t+1. Outer foldlar bağımsız çalıştırıldığı için her 40-sinyal foldunda son sinyal in-fold next-open olmadan doğal olarak execute edilmiyor; toplam 120 OOS signal row için 117 executable in-fold period bekleniyor.
- Production ML feature contract ve target (h=5, +3%) değiştirilmedi.
- Düzeltme commit: `5039d907a2c9077713c951bedc91cb2b8985c11d`.
- Codespace gerçek backtest sonucu henüz tamamlanmadı; aynı smoke komutu tekrar çalıştırılmalı.


### Faz 6 — Gerçek Backtest Runner Son Veri Sözleşmesi Kontrolü

- Real backtest runner son kontrolde model dataset'i ile execution market data ayrımı açık hale getirildi.
- ML dataset yalnızca production feature kolonları/close/target taşırken, backtest `open` ve `close` değerlerini canonical raw OHLCV frame'den OOS `trading_date` üzerinden eşleştiriyor.
- Raw ve technical indexlerde duplicate trading date kontrolü bulunuyor; tüm tarih karşılaştırmaları `Timestamp` tipine normalize ediliyor.
- Outer fold sınırında engine'in doğal “last signal has no next-open” davranışı korunuyor. Bu smoke protokolünde 3 x 40 = 120 OOS signal row ve 3 x 39 = 117 in-fold executable period bekleniyor.
- Bu yaklaşımın amacı foldlar arasındaki gap veya fold dışı fiyatları strateji getirisine yanlışlıkla dahil etmemektir.
- Son düzeltme commit: `d97a99b141ad023c7c1ac3ef5db6cf0ad19b1489`.


### Faz 6 — THYAO Gerçek Historical Backtest İlk Sonuç

- Codespace gerçek backtest smoke testi başarıyla tamamlandı: `REAL BACKTEST SMOKE TEST PASSED`.
- Veri kaynağı: **Borsapy provider (DB history insufficient)**; 685 raw row -> 481 supervised dataset row; production target h=5 / +3%; outer 3 x 40 OOS = 120 signal observation.
- Her outer fold bağımsız çalıştırıldı; her foldda 40 signal row ve 39 in-fold executable period var. Cross-fold execution kullanılmadı.
- Fold 1 (2026-04-03 -> 2026-06-05): total return **+2.3824%**, annualized return 16.4318%, vol 7.2783%, Sharpe 2.1262, max drawdown -2.1925%, win rate 43.59%, profit factor 1.5454, turnover 1.5394.
- Fold 2 (2026-06-08 -> 2026-08-03): total return **+0.4097%**, annualized return 2.6769%, vol 6.5203%, Sharpe 0.4370, max drawdown -2.4637%, win rate 48.72%, profit factor 1.0810, turnover 1.3913.
- Fold 3 (2026-08-04 -> 2026-09-28): total return **-2.2571%**, annualized return -13.7149%, vol 3.7523%, Sharpe -3.9119, max drawdown -2.3916%, win rate 35.90%, profit factor 0.4774, turnover 1.2640.
- Toplam execution maliyeti üç bağımsız fold için transaction cost **420.844638**, slippage cost **210.422319** olarak gerçekleşti.
- Fold getirilerinin basit aritmetik ortalaması yaklaşık **+0.1783%**; fold getirilerini sıralı olarak bileşiklemek yaklaşık **+0.4815%** verir. Bu değerler tam pooled portfolio performansı değildir; bağımsız fold raporlarının descriptive özetidir ve fold sınırları arasında pozisyon taşınmamıştır.
- Kritik yorum: backtest altyapısı ve OOS execution contract doğrulandı, ancak performans foldlar arasında stabil değil. Özellikle 3. foldun negatif getirisi, Sharpe'ı ve profit factor'ı stratejinin henüz genellenmiş/robust olduğunu göstermiyor.
- Bu sonuç **production signal/weight/threshold değişikliği için kullanılmayacaktır**. Phase 5 production contractları (raw_all, h5/+3%, mevcut signal/risk weighting) korunuyor.
- Bir sonraki kontrollü deney: aynı OOS tarih pencerelerinde **buy-and-hold benchmark + costsiz/costlu pasif referans + signal strategy** karşılaştırması. Amaç mutlak getiriden ziyade stratejinin basit piyasa referansına göre ek değer üretip üretmediğini görmek; model veya threshold seçimi yapmak değil.

## Sıradaki İş

1. Gerçek Phase 5 OOS output ve piyasa fiyatlarını kullanarak historical backtest çalıştır; uygun benchmark/portfolio risk metriklerini ayrı raporla.
2. Backtest sonuçlarını model/threshold seçimiyle karıştırma; production Phase 5 contractlarını başlangıç referansı olarak koru ve yeni seçimleri ayrı, leakage-safe deneyler olarak raporla.
3. Prediction history ve backtest engine tamamlandıktan sonra paper-trading için gereken veri sözleşmelerini tanımla.

## Yeni Sohbette Devam Etme Kuralı

Yeni bir sohbette projeye devam ederken bu dosya önce okunmalı. Özellikle **Güncel Durum**, **Tamamlananlar**, **aktif fazın taskları** ve **Sıradaki İş** bölümleri esas alınmalı.

> Kural: Her faz tamamlandığında kısa özet, alınan teknik/ürün kararları, tamamlanan tasklar ve sıradaki faz/tasklar burada tutulur.
