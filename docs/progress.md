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

## Faz 5 — Model Tuning / Feature Importance / Signal-Risk Foundation — TAMAMLANDI

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
- Yeni AFA gerçek nested sonucu henüz alınmadı; production representation `raw_all` olarak korunuyor.### Faz 5 Nested Representation Selection — Inner Tuning Teşhis Logu

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
- TEFAS fallback için `--chunk-delay` CLI parametresi eklendi; varsayılan 3 saniyedir.- Kaynak çıktısı korunuyor: `PostgreSQL canonical history` veya `TEFAS provider (DB history insufficient)`.
- Production model/target/signal contract değiştirilmedi.- Düzeltme commit: `917193d6bd6bfb61112c7efebef90061435a93ad`.

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


### Faz 6 — THYAO Backtest Sonrası Aligned Benchmark Deneyi

- Bir sonraki kontrollü karşılaştırma için `smoke_test_backtest_real.py` aynı OOS fold tarihleri içinde üç referansı yan yana çalıştıracak şekilde genişletildi:
  - Phase 5 continuous signal strategy,
  - aynı next-open/cost kurallarıyla buy-and-hold (%100 target weight),
  - transaction cost ve slippage sıfır olan costless buy-and-hold.
- Benchmarklar da her outer fold içinde bağımsız çalışır; cross-fold execution veya fold gap'inin benchmark getirisine dahil edilmesi yoktur.
- Amaç model/threshold seçmek değil; strategy getirisi ile basit piyasa getirisi ve execution maliyet etkisini ayırmaktır.
- Her fold için strategy minus buy-and-hold total return ayrıca yazdırılacaktır.
- Kod commit: `b037e46f439323fa82b4c2123ff31dfb24415766`.
- Bu yeni runner henüz Codespace'te çalıştırılmadı; sonraki doğrulama aynı THYAO komutunun tekrar çalıştırılmasıdır.


### Faz 6 — THYAO Benchmark Assertion ve Buy-and-Hold Tanım Düzeltmesi

- THYAO benchmark karşılaştırması teknik olarak strategy sonuçlarını üretti ancak smoke test sonunda `benchmark_result.equity_curve["cash"] >= 0` assertion'ında durdu.
- İnceleme sonucunda iki konu ayrıştırıldı: küçük floating-point negatiflik için cash kontrollerinde `-1e-8` toleransı gerekli; daha önemlisi `target_weight=1.0` değerini her gün backtest engine'e vermek gerçek buy-and-hold değil, günlük %100 hedef ağırlığa yeniden dengeleme anlamına geliyor.
- Benchmark runner yeniden tanımlandı: ilk in-fold executable next-open'da bir kez pozisyon açılır, hisseler son OOS close'a kadar değiştirilmeden tutulur ve ara rebalancing yapılmaz.
- Maliyetli benchmark yalnızca ilk alış işlemindeki transaction cost ve slippage'ı içerir; zorunlu final liquidation varsayılmıyor. Costless benchmark aynı pozisyonun sıfır execution maliyetli referansıdır.
- Strategy backtest engine'i değiştirilmedi; benchmark yalnızca karşılaştırma referansı olarak runner seviyesinde tutuldu.
- Son temizlik commit: `20979f25590b8f149f9353959750b6418d570e27`.
- Bu düzeltme henüz Codespace'te yeniden çalıştırılmadı; yeni benchmark çıktıları gerçek karşılaştırma olarak ilk kez bu rerun'da alınmalı.


### Faz 6 — THYAO Aligned Buy-and-Hold Benchmark Sonucu

- Codespace gerçek backtest + aligned benchmark smoke testi başarıyla tamamlandı: `REAL BACKTEST SMOKE TEST PASSED`.
- THYAO: 685 raw / 481 dataset / 120 OOS signal; veri kaynağı Borsapy provider fallback.
- Fold 1 (2026-04-03 -> 2026-06-05): strategy **+2.3824%**, true buy-and-hold **-0.0657%**, excess **+2.4481 puan**; costless B&H +0.0842%.
- Fold 2 (2026-06-08 -> 2026-08-03): strategy **+0.4097%**, true buy-and-hold **+6.0386%**, excess **-5.6289 puan**; costless B&H +6.1977%.
- Fold 3 (2026-08-04 -> 2026-09-28): strategy **-2.2571%**, true buy-and-hold **-10.0251%**, excess **+7.7680 puan**; costless B&H -9.8901%.
- Strategy fold getirilerinin basit ortalaması yaklaşık **+0.1783%**; true B&H için yaklaşık **-1.3507%**. Bu bağımsız foldlar nedeniyle pooled portfolio sonucu değildir.
- Fold getirileri yalnızca descriptive olarak sıralı bileşiklendiğinde strategy yaklaşık **+0.4815%**, B&H yaklaşık **-4.6546%** verir; bu da gerçek tek-portföy backtest değildir, çünkü foldlar bağımsız başlatılıp pozisyon taşımadan resetlenmiştir.
- Strategy turnover 1.2640–1.5394 aralığında; transaction cost ve slippage toplamı 3 fold üzerinde sırasıyla **420.844638** ve **210.422319**.
- Yorum: Strategy iki foldun ikisinde B&H karşısında pozitif excess return üretirken Fold 2'de belirgin şekilde geride kalıyor. ML/signal ROC-AUC de foldlar arasında 0.4453–0.5931, PR-AUC 0.1062–0.3739 aralığında ve özellikle 3. fold signal PR düşüktür. Bu nedenle THYAO tek başına robust strategy kanıtı değildir.
- Production kararı değişmedi: raw_all, h5/+3%, mevcut signal/risk contract ve continuous position-sizing mapping korunuyor. Bu backtest sonucu model veya threshold seçmek için kullanılmıyor.
- Bir sonraki kontrollü çalışma: aynı pipeline'ı birden fazla stock/fund sembolünde çalıştırıp fold/asset bazında **strategy excess return, Sharpe, max drawdown, turnover ve benchmark farkı** dağılımını çıkarmak. Amaç genelleme kontrolüdür.


### Faz 6 — Çoklu Hisse Genelleme Backtest Runner

- `backend/scripts/smoke_test_backtest_multi_stock_real.py` eklendi.
- Varsayılan semboller: THYAO, ASELS, TUPRS, BIMAS; her sembol aynı 3 x 40 OOS / gap=5 / h5+3% protokolünde bağımsız değerlendirilir.
- Her fold için Phase 5 continuous signal strategy, true buy-and-hold benchmark ve costless buy-and-hold referansı kullanılır.
- Strategy ve benchmark foldları bağımsızdır; foldlar arasında pozisyon taşınmaz veya gap gözlemleri execution'a katılmaz.
- Her sembolde veri yetersizliği veya tuning failure diğer sembolleri gizlemez; failure listelenir ve script sonunda non-zero exit code verir.
- Summary; ortalama/medyan strategy excess return, pozitif excess fold oranı, Sharpe, max drawdown ve turnover ile birlikte fold bazlı tablo üretir.
- Fonlar bu runner'a dahil edilmedi. TEFAS fon history'sinde OHLCV `open` alanı bulunmadığı için Phase 6 next-open equity engine'i fonlara aynen uygulamak metodolojik olarak uygun görülmedi; fonlar için ayrı daily unit-price execution contract'ı sonraki controlled task'tır.
- Kod commit: `e45268daf37500e05c90edf7a04883e32104778f`.
- Codespace'te multi-stock runner henüz çalıştırılmadı; sonraki doğrulama 4 sembol / 12 fold gerçek backtest çalıştırmasıdır.

### Faz 6 — Çoklu Hisse Gerçek Backtest Sonucu

- Codespace gerçek multi-stock backtest smoke testi başarıyla tamamlandı: **REAL MULTI-STOCK BACKTEST SMOKE TEST PASSED**.
- Kapsam: THYAO, ASELS, TUPRS, BIMAS; toplam **12 bağımsız OOS fold** (4 sembol x 3 fold), her sembolde 120 OOS signal row.
- Production contract değişmedi: h=5 / +3%, outer 3 x 40, gap=5, continuous 0-100 signal -> 0-1 target weight mapping, BIST execution cost varsayımları ve true buy-and-hold benchmark.
- Cross-symbol sonuç: mean strategy return per fold **+1.6929%**; mean B&H **+5.7082%**; mean strategy excess **-4.0153%**; median excess **-3.9245%**; positive excess fold rate **41.67% (5/12)**; mean Sharpe **+0.940**; mean max drawdown **-4.0359%**; mean turnover **2.1201**.
- Sembol bazında üç foldun ortalama excess getirisi: **THYAO +1.5291%**, **ASELS -2.2918%**, **TUPRS -11.4314%**, **BIMAS -3.8671%**. Bu hesap bağımsız foldların basit aritmetik ortalamasıdır; pooled portfolio sonucu değildir.
- THYAO'da strategy 2/3 foldda B&H'yi geçti; ASELS 1/3, TUPRS 1/3, BIMAS 1/3 foldda geçti. Pozitif excess fold oranı çoğunlukla negatif kaldığı için mevcut sizing policy robust alpha kanıtı sayılmıyor.
- En belirgin gözlem: TUPRS'ın Fold 2 ve Fold 3'te güçlü buy-and-hold trendini yakalayamadığı görülüyor (excess **-14.2793%** ve **-24.1993%**). Continuous signal/weight mapping'in güçlü trending dönemlerde yeterince yüksek exposure tutmama ihtimali kontrollü olarak test edilecek.
- ASELS Fold 2'de B&H karşısında pozitif excess (**+1.6778%**) olmasına rağmen strategy return **-7.2105%**, Sharpe **-2.017** ve MaxDD **-11.6833%** oldu. Benchmarkı geçmek tek başına yeterli risk kriteri değildir.
- Signal kalite metrikleri sembol/fold bazında heterojen: ROC-AUC yaklaşık **0.2853–0.8828**, PR-AUC **0.1062–0.7162**. Bu sonuçlar backtest bağlamında diagnostiktir; model/threshold seçimi için tek başına kullanılmayacak.
- Faz 6 genelleme sonucu: Phase 5 signal-chain ve historical next-open execution contractı gerçek çoklu hisse verisi üzerinde çalışıyor; ancak mevcut continuous sizing policy ile B&H'ye karşı **robust excess alpha doğrulanmadı**.
- Production kararı değişmedi: raw_all, h5/+3%, mevcut signal/risk weighting ve continuous position-sizing mapping korunuyor.
- Fonlar ayrı tutuluyor; TEFAS history'de gerçek open bulunmadığı için stock next-open engine'i fonlara aynen uygulanmayacak. Fonlar için ayrı daily unit-price execution contractı tasarlanacak.

### Faz 6 — Nested Signal-Score Exposure Mapping Deneyi Altyapısı

- `backend/app/backtesting/strategy.py` içindeki mevcut linear score-to-weight mapping korunarak dört önceden tanımlı monoton sizing policy eklendi: `linear`, `concave`, `convex`, `capped`.
- `concave`: normalize signal'ın karekökü; düşük/orta skorları lineer mapping'e göre daha yüksek exposure'a taşır. `convex`: normalize signal'ın karesi; yüksek skorları öne çıkarır. `capped`: linear shape'i koruyup maksimum exposure'ı varsayılan **0.75** ile sınırlar.
- `run_signal_score_backtest()` ve frame hazırlama fonksiyonları `mapping_policy` ve `capped_weight` kabul edecek şekilde genişletildi. Default `linear`, yani mevcut production davranışı değişmedi.
- `backend/tests/backtesting/test_strategy.py` mapping shape, bounded/monotonic behavior, custom cap ve invalid policy kontrolleriyle genişletildi. Codespace test sonucu henüz alınmadı.
- `backend/scripts/smoke_test_backtest_mapping_real.py` eklendi. Amaç aynı 4 stock / outer 3 x 40 / gap=5 / h5+3% protokolünde mapping sensitivity ve nested mapping selection yapmaktır.
- Mapping selection leak-aware nested tasarlandı: her outer fold için mapping policy yalnızca outer-training içindeki 2 inner fold üzerinden değerlendirilir; her inner fold'da model yalnızca o inner-training slice üzerinde fit edilir. Outer OOS policy sonuçları seçimden sonra ilk kez kullanılır.
- Inner selection kriteri önceden tanımlı ve deterministik: mean excess return, median excess return, mean Sharpe, mean max drawdown, mean turnover ve sabit policy order tie-break. En az iki valid inner fold şartı korunur.
- Runner tüm mapping policy'lerini outer OOS'ta ayrıca raporlar; ayrıca nested-selected policy'nin outer sonuçlarını ayrı özetler. Böylece seçilen policy ile aynı OOS'ta sonradan seçilmiş policy arasında ayrım korunur.
- Bu deney model, target, representation veya BUY/HOLD/SELL threshold seçmiyor. Amaç yalnızca position-sizing policy hassasiyetini ve güçlü trend dönemlerindeki exposure davranışını incelemek.
- Yeni kod commitleri: `18a1bc79d6882848371fd7f0db71405560e9847c`, `538a6e499ce282654c305adaea1ce418e1ba28ab`, `c1aba36ac10bb7f406f569723403b16449c208b0`, `25d14d207a50c8e0fd045661526edb74808f7f68`.

### Faz 6 — Nested Exposure Mapping Gerçek Sonucu

- Codespace'te mapping sensitivity smoke testi başarıyla tamamlandı: **REAL NESTED MAPPING SENSITIVITY SMOKE TEST PASSED**. Backtesting testleri: **27 passed, 0.69s**.
- Kapsam: THYAO, ASELS, TUPRS, BIMAS; 4 mapping policy (`linear`, `concave`, `convex`, `capped`) ve 12 outer OOS fold.
- All-policy outer OOS ortalamalarında `concave` en iyi sonuç verdi: strategy **+3.1312%**, B&H **+5.7082%**, mean excess **-2.5769%**, median excess **-2.4548%**, positive excess fold rate **41.67%**, mean Sharpe **0.953**, mean MaxDD **-6.8030%**, turnover **2.3083**.
- Production `linear` ile `capped` gözlemlenen OOS sonuçta tamamen aynı kaldı: mean excess **-4.0153%**, positive excess **41.67%**, mean Sharpe **0.940**, mean MaxDD **-4.0359%**, turnover **2.1201**. Bu veri aralığında signal score'ların capped limitini aşmadığı/etkilemediği görülüyor; dolayısıyla capped policy için ek fayda kanıtlanmadı.
- `convex` en düşük mean excess verdi: **-5.2326%**; buna karşılık mean MaxDD daha sınırlı (**-1.6846%**) ve turnover daha düşük (**1.2667**). Bu, düşük exposure ile risk azaltılabildiğini ancak benchmarkı yakalamadığını gösteriyor.
- Nested selection her outer fold için yalnızca inner OOS sonuçlarından policy seçti. Seçim frekansı: concave **7/12**, convex **5/12**, linear/capped **0/12**.
- Nested-selected outer OOS: mean strategy return **+2.0430%**, mean B&H **+5.7082%**, mean excess **-3.6651%**, median excess **-3.3757%**, positive excess **41.67%**, mean Sharpe **1.175**, mean MaxDD **-4.7980%**, turnover **1.8199**.
- Sembol bazında nested-selected mean excess: THYAO **+0.5325%**, ASELS **-2.1372%**, TUPRS **-9.8525%**, BIMAS **-3.2033%**. THYAO dışında üç sembolde ortalama excess negatif kaldı.
- Özellikle TUPRS'ta concave exposure OOS getiriyi linear'a göre iyileştiriyor (Fold 2: **+13.2315%** vs +8.1626%; Fold 3: **+16.7957%** vs +8.7952%), fakat güçlü B&H trendini yine yakalayamıyor. Bu nedenle mapping tek başına temel eksikliği çözmedi.
- Sonuç: concave belirgin bir sensitivity winner gibi görünse de **nested-selected policy ile robust cross-symbol alpha doğrulanmadı**. Positive excess fold rate değişmedi ve nested-selected mean excess hâlâ negatiftir.
- Production kararı değişmedi: mevcut `linear` mapping korunuyor. Mapping policy'yi production'a taşımadan önce daha uzun tarih aralığı / daha fazla sembol ve execution-cost sensitivity ile ek doğrulama yapılması gerekiyor.
- Kod/test/doc commitleri: `18a1bc79d6882848371fd7f0db71405560e9847c`, `538a6e499ce282654c305adaea1ce418e1ba28ab`, `c1aba36ac10bb7f406f569723403b16449c208b0`, `25d14d207a50c8e0fd045661526edb74808f7f68`, `aa49d3519a51312d6048e666558394ce2313c85e`, sonuç kaydı bu güncellemeyle tamamlandı.

### Faz 6 — Genişletilmiş Nested Exposure Mapping Sonucu (8 Hisse / 24 Fold)

- Codespace'te aynı nested mapping sensitivity deneyinin 2000 günlük istek ve 8 sembolle genişletilmiş çalışması başarıyla tamamlandı: **REAL NESTED MAPPING SENSITIVITY SMOKE TEST PASSED**.
- Provider tarafında istenen 2000 takvim günü karşılığında mevcut Borsapy history **1367 raw / 1163 dataset** satırı sağladı; tüm 8 sembolde aynı coverage görüldü.
- Kapsam: THYAO, ASELS, TUPRS, BIMAS, KCHOL, SAHOL, SISE, EREGL; toplam **24 outer OOS fold** ve her fold için 4 mapping policy.
- All-policy outer OOS: `concave` mean strategy **+1.6609%**, mean B&H **+3.4012%**, mean excess **-1.7403%**, median excess **+0.2374%**, positive excess fold rate **50.00%**, mean Sharpe **0.496**, mean MaxDD **-7.3565%**, turnover **2.1404**.
- `linear` ve `capped` aynı outer OOS sonuçları verdi: mean excess **-2.6119%**, median **-0.0553%**, positive excess **50.00%**, mean Sharpe **0.418**, mean MaxDD **-4.3188%**, turnover **1.9574**. Capped policy için bu veri setinde gözlenen ek bir fayda oluşmadı.
- `convex` mean excess **-3.2581%** ile en zayıf policy oldu; buna rağmen mean MaxDD **-1.6705%** ve turnover **1.1376** ile en düşük risk/exposure yaklaşımını temsil etti. Bu policy benchmarka yaklaşmadı.
- Nested-selected OOS sonucu: mean strategy return **+0.6280%**, mean B&H **+3.4012%**, mean excess **-2.7732%**, median excess **-0.6533%**, positive excess fold rate **45.83%**, mean Sharpe **0.571**, mean MaxDD **-4.4895%**, turnover **1.5913**.
- Nested selection frekansı: **concave 12/24 (%50)**, **convex 11/24 (%45.83)**, **linear 1/24 (%4.17)**, `capped` 0/24. Policy seçiminde concave lider olsa da foldlar arasında ciddi değişkenlik devam ediyor.
- Sembol bazında nested-selected mean excess: THYAO **+0.2706%**, SAHOL **+1.1803%**, SISE **+4.0961%** pozitif; ASELS **-1.5063%**, BIMAS **-3.8459%**, KCHOL **-1.8163%**, TUPRS **-10.2270%**, EREGL **-10.3371%** negatif.
- TUPRS ve EREGL, güçlü B&H dönemlerinde stratejinin ciddi biçimde geride kaldığı iki belirgin örnek olarak kaldı. Concave bu açığı azaltabiliyor ancak ortadan kaldırmıyor.
- Genişletilmiş deney sonucu: 8 sembol / 24 fold ile concave'in sensitivity avantajı önceki 4-symbol deneyine göre daha genellenebilir görünüyor; ancak **nested-selected mean excess hâlâ -2.7732%** olduğu için production sizing policy değişikliği için yeterli kanıt yok.
- Production kararı yine değişmedi: `linear` mapping production default olarak korunuyor.
- Bir sonraki kontrollü adım: aynı 8 sembol / 24 fold nested policy değerlendirmesini **execution-cost sensitivity** (maliyetsizden yüksek maliyet varsayımlarına) karşılaştırmak ve concave avantajının turnover/maliyet etkisine ne kadar duyarlı olduğunu ölçmek. Bu da production seçimi değil, policy robustness deneyi olarak tutulacak.
- Gerçek çalıştırma kaynağı: kullanıcı Codespace çıktısı; test komutunda aynı 8 sembol ve `--days 2000` kullanıldı.

### Faz 6 — Execution-Cost Sensitivity Runner Hazırlığı

- `backend/scripts/smoke_test_backtest_cost_sensitivity_real.py` eklendi.
- Varsayılan maliyet grid'i: **0/0, 5/2.5, 10/5, 20/10 bps** (transaction/slippage).
- Deney aynı 8 hisse / 24 outer fold / gap=5 / h5+3% protocolunu koruyor.
- Leakage-safe nested mapping selection her cost scenario için ayrı yapılıyor: policy seçimi outer-training içindeki inner foldlarda net excess return ve mevcut deterministik tie-break düzeniyle gerçekleştiriliyor; outer OOS yalnızca son değerlendirmede kullanılıyor.
- Model ve signal frame'leri maliyetten bağımsız olduğu için her sembol/fold için aynı inner ve outer signal frame'leri maliyet senaryoları arasında yeniden kullanılıyor. Böylece cost sensitivity yalnızca execution assumptions'ı değiştiriyor.
- Runner her cost seviyesinde tüm policy'lerin outer OOS sonuçlarını ve nested-selected policy özetini; mean/median excess, positive fold rate, Sharpe, MaxDD, turnover ve policy selection frequency ile raporluyor.
- Production mapping, model, target ve representation bu deneyde değiştirilmedi.
- Runner commit: `41a4d79806906cd305756c481370168b435856af`.

### Faz 6 — Execution-Cost Sensitivity Gerçek Sonucu

- Codespace'te backtesting testleri başarıyla tamamlandı: **27 passed, 0.72s**.
- Gerçek execution-cost sensitivity smoke testi başarıyla tamamlandı: **REAL NESTED EXECUTION-COST SENSITIVITY SMOKE TEST PASSED**.
- Kapsam: **8 hisse / 24 outer fold / 4 cost scenario / 4 exposure policy**; protocol aynı kaldı: outer 3 x 40, gap=5, inner 2 x 20, target h5/+3%.
- Test edilen maliyet senaryoları: **0/0, 5/2.5, 10/5, 20/10 bps** (transaction/slippage).

**All-policy outer OOS sonucu**

- concave tüm dört maliyet seviyesinde en yüksek mean excess return'u korudu:
  - 0/0: mean excess **-1.5708%**, median **+0.3859%**, positive excess **50.00%**, mean Sharpe **0.600**, mean MaxDD **-7.2673%**, turnover **2.1402**.
  - 5/2.5: mean excess **-1.6556%**, median **+0.3125%**, positive excess **50.00%**, mean Sharpe **0.548**, mean MaxDD **-7.3119%**, turnover **2.1403**.
  - 10/5: mean excess **-1.7403%**, median **+0.2374%**, positive excess **50.00%**, mean Sharpe **0.496**, mean MaxDD **-7.3565%**, turnover **2.1404**.
  - 20/10: mean excess **-1.9093%**, median **+0.0597%**, positive excess **50.00%**, mean Sharpe **0.392**, mean MaxDD **-7.4458%**, turnover **2.1405**.
- Production linear ile capped yine aynı OOS sonucu verdi. Mean excess sırasıyla **-2.4718%, -2.5419%, -2.6119%, -2.7516%** oldu (0/0 -> 5/2.5 -> 10/5 -> 20/10); positive excess oranı dört seviyede de **50.00%** kaldı.
- convex en düşük mean excess'u korudu: **-3.2425%, -3.2503%, -3.2581%, -3.2739%**. Buna karşılık turnover yaklaşık **1.1375–1.1376** ile en düşük kaldı; yüksek maliyet altında Sharpe da belirgin biçimde zayıfladı.
- Böylece concave'in linear üzerindeki mean-excess avantajı maliyet arttıkça daralsa da kaybolmadı: yaklaşık **+0.90 puan** (0/0), **+0.89 puan** (5/2.5), **+0.87 puan** (10/5), **+0.84 puan** (20/10).
- Ancak dört maliyet seviyesinde de concave'in absolute mean excess'u negatif kaldı. Bu nedenle cost sensitivity, concave için robustness/sensitivity avantajını destekliyor; **production alpha kanıtı oluşturmuyor**.

**Nested-selected cost sensitivity sonucu**

- Nested-selected mean excess sırasıyla **-2.6307%, -2.6766%, -2.7732%, -2.9212%** (0/0 -> 5/2.5 -> 10/5 -> 20/10).
- Positive excess fold rate tüm maliyet seviyelerinde **45.83% (11/24)** seviyesinde kaldı.
- Mean Sharpe **0.796 -> 0.710 -> 0.571 -> 0.354** düşerek execution cost arttıkça risk-adjusted performansın zayıfladığını gösterdi.
- Mean MaxDD yaklaşık **-4.5430% -> -4.5822% -> -4.4895% -> -4.4768%** aralığında kaldı; turnover **1.6411 -> 1.6412 -> 1.5913 -> 1.5617** ile maliyet arttıkça hafifçe azaldı.
- Nested policy selection frequency:
  - 0/0: concave **13/24**, convex **10/24**, linear **1/24**, capped **0/24**.
  - 5/2.5: concave **13/24**, convex **10/24**, linear **1/24**, capped **0/24**.
  - 10/5: concave **12/24**, convex **11/24**, linear **1/24**, capped **0/24**.
  - 20/10: concave **12/24**, convex **12/24**, linear **0/24**, capped **0/24**.
- Cost yükseldikçe nested selection daha düşük-turnover convex tarafına kayma eğilimi gösteriyor; fakat bu adaptasyon mean excess'u pozitife çevirmiyor.

**Karar**
- Execution-cost sensitivity, concave policy'nin önceki 8-hisse / 24-fold deneyindeki avantajını **maliyet varsayımları altında da koruduğunu** gösterdi.
- Buna rağmen nested-selected sonuçların dört maliyet seviyesinde de negatif kalması nedeniyle linear production mapping'den concave'e geçiş yapılmıyor.
- capped policy için ek fayda kanıtı oluşmadı; linear ile aynı sonuçları üretmeye devam etti.
- Bu deneyde model, target, representation, signal weighting ve BUY/HOLD/SELL threshold contractları değiştirilmedi.
- Mevcut production execution cost varsayımı **10/5 bps** olarak korunuyor; diğer seviyeler sensitivity referansıdır.
- Production mapping kararı: **linear default korunuyor**.
- Bir sonraki kontrollü aşama: strategy/prediction history'nin persistence katmanının değerlendirilmesi ve fonlar için stock next-open engine'inden ayrı **daily unit-price backtest execution contractı** tasarlanması.

### Faz 6 — Prediction History Persistence Foundation

- PostgreSQL üzerinde append-only prediction geçmişi için `prediction_history` modeli ve `0003_prediction_history` Alembic migrationı eklendi.
- Kayıt contractı prediction tarihi, generation timestampı, `data_as_of`, horizon/target contractı, model family/version, feature representation, ML probability, Technical Score, risk score/adjustment, final signal score, continuous target weight, quality/stale bilgisi, provider ve açıklama nedenlerini taşır.
- Aynı asset/date için overwrite yapan doğal unique constraint eklenmedi; yeniden üretilen prediction ayrı audit kaydı olarak saklanır.
- Prediction history için BUY/HOLD/SELL action alanı özellikle eklenmedi; production threshold contractı hâlâ seçilmedi.
- Service katmanı `backend/app/data/prediction_history.py` altında append-only `record_prediction`, batch `record_predictions`, tarih filtreli `list_predictions` ve `get_latest_prediction` operasyonlarını sağlıyor. Update/delete operasyonu yok.
- Pydantic contractı skor/ağırlık sınırlarını, timezone-aware `generated_at` değerini ve `data_as_of <= prediction_date` kuralını doğruluyor.
- PostgreSQL migrationı aynı core bounds ve temporal kuralı CHECK constraint olarak da uyguluyor; asset/date, prediction_date ve generated_at sorguları için indexler eklendi.
- Alembic metadata kaydına yeni model bağlandı; model ve data package exportları güncellendi.
- Unit/contract test dosyası: `backend/tests/test_prediction_history.py`.
- Prediction persistence service için fake-session testleri de eklendi; başarılı commit/refresh ve boş batch davranışı contract kapsamında korunuyor.
- Bu aşamadaki değişiklik model, target, representation, signal weighting veya sizing policy değiştirmiyor.
- Codespace doğrulaması tamamlandı: `alembic upgrade head` 0002 -> 0003 migrationını başarıyla uyguladı; prediction-history targeted testleri **15 passed in 1.04s**; full backend suite **182 passed in 7.30s**.


### Faz 6 — Prediction Persistence Gerçek Smoke Doğrulaması

- Codespace'te kullanıcı tarafından doğrulanan targeted prediction testleri: **17 passed in 4.52s**.
- Codespace'te kullanıcı tarafından doğrulanan full backend suite: **184 passed in 9.81s**.
- Gerçek stock persistence smoke testi THYAO için başarıyla tamamlandı:
  - 685 raw rows, 481 training rows.
  - Prediction date / data as of: **2026-10-05**.
  - Inner PR-AUC: **0.866667**.
  - ML probability **0.0688624**, Technical Score **49.8042**, Risk Score **57.8111**, Risk Adjustment **-11.5622**.
  - Final Signal Score **11.4182**, target weight **0.114182**.
  - Prediction kaydı PostgreSQL'e yazıldı ve read-back ile doğrulandı: **REAL PREDICTION PERSISTENCE SMOKE TEST PASSED**.
  - Persisted prediction ID: 7f8c9d63-1502-46f5-abe9-8d7bbacff06b.
- Fund AFA persistence smoke'u gerçek TEFAS çağrısında fonGnlBlgSiraliGetir endpointinden JSON parse edilemeyen yanıt nedeniyle durdu. Traceback httpx.Response.json() içinde JSONDecodeError ile başlayıp TefasProviderError olarak sonlandı. Bu nedenle AFA için henüz prediction DB write/read-back başarı kanıtı yok.
- psql binary'si Codespace PATH'inde kurulu değil (psql: command not found). PostgreSQL erişimi yine container içindeki psql ile yapılabilir; host'a ayrı PostgreSQL client kurmak bu aşamada gerekli değil.
- TEFAS resiliency düzeltmesi yapıldı: TefasProvider._post() artık transient non-JSON 200/HTML benzeri cevaplarda mevcut exponential retry bütçesini kullanıyor; retryler tükendiğinde endpoint/status/content-type/body preview içeren daha açıklayıcı TefasProviderError üretiyor.
- Bu davranış için iki provider testi eklendi: transient non-JSON sonrası başarı ve retry tükenince diagnostik hata.
- Provider fix commit: eed2580e9ef1dc42972cb6a182bb3c00c6a21b84.
- AFA tekrar çalıştırmasında non-JSON retry düzeltmesinden sonra farklı bir istemci tarafı hata görüldü: h11 LocalProtocolError, "Too little data for declared Content-Length". Traceback request body gönderilirken oluştu; TEFAS response parsing aşamasına ulaşmadı.
- HTTPX/h11 kaynaklarında bu hata, gönderilen body ile ilan edilen Content-Length'in uyuşmazlığıyla ilişkilendiriliyor. Bu nedenle TEFAS POST gövdesi artık httpx `json=` parametresi yerine deterministik UTF-8 bytes olarak `content=` ile gönderiliyor. HTTP client da retry döngüsü boyunca tek bir owned client kullanacak ve işlem sonunda kapatılacak.
- Bu değişikliğin request body contractını doğrulamak için exact UTF-8 payload testi eklendi. Gerçek AFA smoke sonucu bu düzeltmeden sonra henüz alınmadı.
- Exact request-body fix commit: a46fbce433282e8a2fac7e5bb85eeb2c4c384e03.
- Exact request-body test commit: eda7c074808012a76fde56660f92a8a350d3ece8.
- Provider test commit: 1622f43c949c43b8d8186f2632b4dc6e869a0c65.
- Production target, model family/version contract, feature representation, signal weighting ve production linear sizing değiştirilmedi.


### Faz 6 — Fund Prediction Persistence Gerçek Smoke Doğrulaması

- Codespace'te AFA için gerçek fund prediction persistence smoke testi başarıyla tamamlandı:
  - Asset type: **fund**
  - Symbol: **AFA**
  - Asset ID: **cd43f75c-27b1-4e35-a544-a82bf4bcd756**
  - Raw rows: **685**
  - Training rows: **481**
  - Prediction date / data as of: **2026-10-06**
  - Model version: **xgboost-n200-d4-lr0.0500-mcw3-ss0.90-cs0.90-rl1-rs42**
  - Inner PR-AUC: **0.200000**
  - ML probability: **0.0096400**
  - Technical Score: **70.0792**
  - Risk Score: **0.0**
  - Risk Adjustment: **-0.0**
  - Final Signal Score: **26.8822**
  - Target weight: **0.268822**
  - Prediction kaydı PostgreSQL'e yazıldı ve read-back ile doğrulandı.
  - Persisted prediction ID: **28993bf1-f5ce-4618-80b9-5ff117b5dfb7**
  - Sonuç: **REAL PREDICTION PERSISTENCE SMOKE TEST PASSED**
- Böylece prediction persistence için gerçek veriyle iki asset type doğrulandı: **THYAO stock** ve **AFA fund**.
- AFA sonucundaki düşük inner PR-AUC ve çok düşük ML probability, persistence smoke'unun başarısızlığı değildir; bu testin amacı DB audit kaydının üretim prediction çıktısıyla birlikte doğru yazılıp okunmasıdır. Model performansı ayrı evaluation/backtest kapsamındadır.
- Production target (horizon=5, forward_return_5d > +3%), raw_all representation, signal weighting ve production linear sizing değiştirilmedi.



### Faz 6 — Prediction API Foundation

- FastAPI API katmanı için temel DB session dependency eklendi: `backend/app/db.py`.
- API router yapısı oluşturuldu:
  - `GET /health`
  - `GET /api/v1/assets/{symbol}`
  - `GET /api/v1/assets/{symbol}/predictions/latest`
  - `GET /api/v1/assets/{symbol}/predictions`
- Asset lookup canonical symbol üzerinden yapılıyor ve path symbol uppercase normalize ediliyor.
- Latest prediction endpointi `prediction_date DESC`, ardından `generated_at DESC` sıralamasıyla append-only audit kaydının son üretimini döndürüyor.
- Prediction history endpointi `start_date`, `end_date`, `limit` ve `offset` filtrelerini destekliyor; limit 1..500 ile sınırlandırıldı.
- API response schema'sında PostgreSQL Numeric alanları frontend kullanımına uygun JSON number olarak expose ediliyor; persistence/internal Decimal contractı değişmedi.
- Asset ve prediction için 404; ters tarih aralığı için 400 contractı eklendi.
- Prediction generation için POST endpointi bu aşamada bilerek eklenmedi. API provider çağrısı yapmıyor ve raw DataFrame taşımıyor; mevcut prediction service ile veri/orkestrasyon sınırı korunuyor.
- Auth ve watchlist kullanıcı bağlamı bu read API contractına eklenmedi; ileride ayrı authorization dependency olarak ele alınacak.
- API contract dokümanı: `docs/phase-6-prediction-api.md`.
- API testleri: `backend/tests/test_api_predictions.py`; Codespace çalıştırma sonucu henüz bekleniyor.
- API foundation commitleri: 5d2d7f5dc6df730b4576eb22e16c85bcce9ef4b1, e6ccf601a438be034661ade3aa25f5610db74712, 40b3837a348df811dccd338c5e209abf3215e35c, fe53c6d8e4b009e374d7713ae4af925fa8640b94, 89d291548cfda1a8868e607089f142de21649e7f, a6d21e094e8940333399c6505bd387f428a247cf, 4633f7616e127a717a0c6c0907f4f41187cab5f1, 21684672e430fedbcb25bbceb76598f01d61fe49, c3222b0f45ffa03e0086343868619290b8f104a2, 123bfd5669547ad55493bbcb612e8b6056482f9a.


### Faz 6 — Prediction API Test Fixture Düzeltmesi

- Codespace API test çalıştırması: **5 passed, 2 failed**.
- Her iki failure da endpoint business logic kaynaklı değildi; FastAPI response validation aşamasında test fixture içindeki `PredictionHistory.created_at` alanı `None` olduğu için `datetime_type` hatası oluştu.
- Response schema'da `created_at` zorunlu olduğu için API test fixture'ına timezone-aware `created_at=GENERATED_AT` eklendi.
- Production API/router/database kodu değiştirilmedi.
- Fixture fix commit: **bc846eaed5c720cac10c1390f268af64510d6d68**.
- Bu düzeltmeden sonra targeted API testlerinin ve full backend suite'in yeniden çalıştırılması gerekiyor.


### Faz 6 — Prediction API Gerçek HTTP Doğrulaması

- Codespace'te API testleri başarıyla tamamlandı: **7 passed in 1.38s**.
- Full backend suite güncel API değişiklikleriyle başarıyla tamamlandı: **194 passed in 10.76s**.
- Uvicorn gerçek Codespace ortamında başlatıldı: `http://0.0.0.0:8000`.
- Gerçek PostgreSQL read-back üzerinden HTTP doğrulaması başarıyla yapıldı:
  - `GET /health` -> **200 OK**
  - `GET /api/v1/assets/THYAO` -> **200 OK**
  - `GET /api/v1/assets/THYAO/predictions/latest` -> **200 OK**
  - `GET /api/v1/assets/AFA/predictions/latest` -> **200 OK**
- THYAO latest prediction API response'u persisted prediction ID `7f8c9d63-1502-46f5-abe9-8d7bbacff06b` kaydını ve production metadata/scores/target weight alanlarını doğru expose etti.
- AFA latest prediction API response'u persisted prediction ID `28993bf1-f5ce-4618-80b9-5ff117b5dfb7` kaydını `source_provider=tefas`, h5/+3%, raw_all ve final target weight ile doğru expose etti.
- Böylece Faz 6 prediction persistence + read API zinciri gerçek stock ve fund verileriyle doğrulandı: **PostgreSQL -> PredictionHistory -> FastAPI -> JSON**.
- API test fixture düzeltmesi ve mevcut endpoint contractı sonrasında production target/model/representation/sizing contractları değiştirilmedi.


### Faz 6 — Fund Daily Unit-Price Backtest Foundation

- Stock next-open engine'den ayrı `backend/app/backtesting/fund_engine.py` eklendi.
- Fund execution contract: t tarihindeki target weight, en erken t+1 günün published `unit_price` değeriyle uygulanır; aynı gün unit price execution yoktur.
- Fund engine fractional unit kullanır ve target weight'i 0.0..1.0 sınırında tutar.
- Buy sizing transaction cost dahil affordability ile sınırlandırılır; cash negatif olamaz.
- Bu foundation'da stock-style slippage modellenmez; fund `slippage_cost=0` ve reported execution slippage **0 bps** olarak tutulur.
- Forced final liquidation yoktur. Son sinyal için sonraki unit price yoksa execution yapılmaz.
- `FundBacktestConfig` başlangıçta 100,000 capital ve 10 bps transaction cost varsayımını kullanır; market sonuçta `TEFAS` olarak audit edilir.
- Test dosyası `backend/tests/backtesting/test_fund_engine.py` oluşturuldu. Codespace test sonucu henüz alınmadı.
- Contract dokümanı: `docs/phase-6-fund-backtesting.md`.
- Implementation commit: **f4c1d5e6daabea8fabd17b1847140be594fa7b37**.
- Test commit: **55ea4a397f48bf37b70f07502bcb0eb17f50fa86**.
- Export commit: **a8fa8a3827b70f84ad48b5b7f61a4033ea439056**.
- Contract docs commit: **4e2cd2911e3e7249a428330ae08312105ff8b743**.



- Kullanıcı Codespace'te fund backtest targeted testini ve full backend suite'i çalıştırdı; her iki komut da **başarılı (passed)** olarak doğrulandı. Bu doğrulama benchmark helper eklenmeden önceki fund engine foundation commitleri içindi; son benchmark/runner değişiklikleri ayrıca yeniden test edilmelidir.

- Fund benchmark testinde ilk düzeltme sonrası bir stale helper adı yeniden kontrol edildi ve önceki `replaceAll` yaklaşımının doğru `calculate_fund_buy_and_hold_total_return` çağrısını da `calculate_fundcalculate_fund_buy_and_hold_total_return` biçiminde bozduğu tespit edildi.
- Gerçek kök neden yalnızca test dosyasındaki helper çağrılarıdır; `backend/app/backtesting/fund_engine.py` içindeki production benchmark helper doğru durumdadır.
- `backend/tests/test_fund_backtest_runner.py` içindeki hatalı çağrı doğrudan `calculate_fund_buy_and_hold_total_return` olarak düzeltildi. Ayrıca repo genelinde `calculate_fundcalculate_fund_buy_and_hold_total_return` araması yapıldı ve başka occurrence bulunmadı.
- Düzeltme commit: **9568151c15a34aa6e1b905354b2e9ab44d554754**. Codespace testleri henüz bu son commit üzerinde yeniden çalıştırılmadı.

### Faz 6 — Real Fund OOS Backtest Runner Hazırlığı

- `backend/scripts/smoke_test_backtest_fund_real.py` eklendi.
- Runner gerçek TEFAS fund history'yi önce PostgreSQL canonical `fund_daily_prices` tablosundan yükler; DB coverage yetersizse TEFAS provider fallback kullanır.
- Protocol stock deneyleriyle uyumlu tutuldu: outer **3 x 40 observations**, **gap=5**, production target **h5/+3%**, inner tuning için mevcut sparse-event smoke helper kullanılır.
- Her OOS fold için mevcut production signal chain uygulanır: XGBoost probability + Fund Technical Score + Fund Risk Adjustment -> final Signal Score -> production **linear** score-to-weight mapping.
- Fund execution artık ayrı engine üzerinden yapılır: target t -> t+1 daily unit price; fractional units; transaction cost; slippage=0.
- Gerçek benchmark `calculate_fund_buy_and_hold_total_return()` olarak engine katmanına alındı: ilk executable t+1 unit price'da tek alım, son unit price'a kadar pozisyonu değiştirmeden tutma, forced final liquidation yok.
- Runner fold bazında strategy return, B&H return, excess return, Sharpe, MaxDD, turnover, transaction cost ve signal ROC/PR metriklerini raporlar; ayrıca costless B&H referansı verir.
- Cross-fund summary AFA/AFT varsayılan kapsamıyla mean/median excess, positive excess rate, Sharpe, MaxDD, turnover ve signal metrics raporlar.
- Benchmark helper için unit test eklendi; initial test dosyası gerçek entry-cost hesabını deterministik olarak doğrulayacak şekilde düzeltildi.
- Codespace'te yeni benchmark/runner kodunun güncel commitleri henüz çalıştırılmadı.
- Implementation commits: **10e4f3a1d7e6280cde34b575a12f439473398e63**, **51849756be1eeef84d95cb95f7fb5818a9d49491**, **70500d9557318196484ac5728b669ab3b5cad013**, **20f48d2956d1e66188937018b08cfe5841536f92**, **dd17e1fe96a12301dff1a31e20bf2202633c701a**.
- Contract docs: **4e2cd2911e3e7249a428330ae08312105ff8b743**.



### Faz 6 — Real Fund OOS Runner Benchmark Helper Düzeltmesi

- Codespace doğrulaması: fund targeted suite **11 passed**; full backend suite **205 passed** (iki ayrı çalıştırmada da aynı sonuç).
- Gerçek AFA/AFT fund OOS smoke'u PostgreSQL canonical history'den sırasıyla **672 / 675 raw rows** ve **468 / 471 dataset rows** ile başladı; ancak iki fonda da benchmark aşamasında `NameError: name '_buy_and_hold_total_return' is not defined` nedeniyle durdu.
- Kök neden `backend/scripts/smoke_test_backtest_fund_real.py` içinde costless B&H hesabının, engine'e taşınmış helper yerine eski stock-runner özel `_buy_and_hold_total_return` adını çağırmasıydı. İlk normal benchmark çağrısı zaten doğru `calculate_fund_buy_and_hold_total_return` kullanıyordu.
- Runner içindeki yalnızca stale çağrı `calculate_fund_buy_and_hold_total_return` olarak düzeltildi. Production fund engine, execution contract veya benchmark hesabının kendisi değiştirilmedi.
- Düzeltme commit: **24876f3bdbcee88abc283cdfe988c0552c9991c1**.
- Son kod kontrolünde runner'da eski çağrı satırı bulunmadı. Bu son düzeltme için Codespace smoke/test yeniden çalıştırılmadı.

### Faz 6 — Real Fund OOS Backtest Sonuçları

- Codespace gerçek fund OOS smoke başarıyla tamamlandı: **AFA + AFT, 6/6 outer fold**, her foldda **39 executable period**, PostgreSQL canonical history kullanıldı; TEFAS fallback'e ihtiyaç olmadı.
- Test/runner altyapı doğrulaması: fund targeted suite **11 passed**, full backend suite **205 passed** ve runner `py_compile` başarılı.
- Fund execution contract gerçek OOS'ta doğrulandı: signal t -> **t+1 published unit_price**, transaction cost **10 bps**, slippage **0 bps**.

**AFA — 672 raw / 468 dataset rows**
- Fold 1: strategy **+3.8667%**, B&H **+15.2811%**, excess **-11.4143%**, Sharpe **6.057**, MaxDD **-1.0798%**, turnover **0.6175**.
- Fold 2: strategy **+1.0023%**, B&H **+4.0512%**, excess **-3.0489%**, Sharpe **1.038**, MaxDD **-2.6364%**, turnover **1.4490**.
- Fold 3: strategy **+2.3410%**, B&H **+7.4188%**, excess **-5.0778%**, Sharpe **4.829**, MaxDD **-0.3890%**, turnover **1.0403**.
- AFA aggregate: mean strategy **+2.4033%**, mean B&H **+8.9170%**, mean excess **-6.5137%**, positive excess **0/3**.

**AFT — 675 raw / 471 dataset rows**
- Fold 1: strategy **+5.7710%**, B&H **+22.0094%**, excess **-16.2385%**, Sharpe **4.347**, MaxDD **-1.5973%**, turnover **2.5248**.
- Fold 2: strategy **+0.5412%**, B&H **-4.2177%**, excess **+4.7589%**, Sharpe **0.416**, MaxDD **-3.6969%**, turnover **1.6354**.
- Fold 3: strategy **+0.1874%**, B&H **+2.4139%**, excess **-2.2265%**, Sharpe **0.218**, MaxDD **-1.7062%**, turnover **1.5305**.
- AFT aggregate: mean strategy **+2.1665%**, mean B&H **+6.7352%**, mean excess **-4.5687%**, positive excess **1/3**.

**Cross-fund summary**
- Mean strategy **+2.2849%**, mean B&H **+7.8261%**, mean excess **-5.5412%**.
- Median excess **-4.0634%**; positive excess fold rate **16.67% (1/6)**.
- Mean Sharpe **2.817**, mean MaxDD **-1.8509%**, mean turnover **1.4662**.
- Total strategy transaction cost **881.969488**.
- Signal mean ROC-AUC **0.4684**, PR-AUC **0.3825**; fold direction/performance davranışı heterojen.
- Costless B&H her foldda yalnızca tek giriş maliyeti kaldırılarak hesaplandı; strategy-vs-B&H negatif farkının ana açıklaması execution cost değil, benchmark'a göre düşük/yanlış zamanlanmış exposure olarak görülüyor. Özellikle AFT Fold 1'de **-16.2385 pp** excess varken Fold 2'de **+4.7589 pp** excess oluşması ciddi fold heterojenliği gösteriyor.

**Karar**
- Runner ve fund execution foundation **teknik olarak kabul edildi**; “REAL FUND BACKTEST SMOKE TEST PASSED” sonucu veri/engine/protocol doğrulamasıdır, alpha kanıtı değildir.
- Mevcut production signal/mapping contractı **değiştirilmiyor**. Linear sizing korunuyor; global direction inversion, threshold veya representation değişikliği yapılmıyor.
- Bu ilk gerçek fund OOS coverage ile **fund mapping veya cost-sensitivity sweep'i production policy seçmek için henüz gerekli görülmüyor**; temel strateji zaten B&H karşısında negatif excess üretiyor. Öncelik, sinyalin exposure davranışını ve fund-specific prediction calibration/coverage sorunlarını incelemek.
- Sonuç commit'i: bu progress kaydıyla birlikte güncellendi.

### Faz 6 — Fund Exposure / Signal Diagnostic Altyapısı

- İlk gerçek AFA/AFT OOS backtest sonucunda stratejinin B&H karşısında negatif excess üretmesi üzerine production contractı değiştirmeden diagnostic katmanı eklendi.
- `backend/app/backtesting/fund_diagnostics.py` şu analizleri sağlar: realized target-weight dağılımı, sabit exposure bantları (<25%, 25-50%, 50-75%, >=75%) ve ML probability / Technical Score / final Signal Score için target ve 5 günlük forward-return ilişkileri (Spearman, ROC-AUC, PR-AUC).
- Diagnostic frame contractı `target_weight` 0..1, binary `target` ve finite `forward_return_5d` alanlarını doğrular; veri/model üretimini veya execution'ı değiştirmez.
- `backend/scripts/smoke_test_fund_exposure_diagnostic_real.py` mevcut fund real-runner'ın canonical DB loader ve sparse inner tuning helper'ını yeniden kullanarak aynı 3x40 outer OOS protokolünde fold bazlı detaylı diagnostic üretir.
- Unit test dosyası `backend/tests/backtesting/test_fund_diagnostics.py` eklendi; diagnostic helperları ve invalid input davranışı kapsanıyor.
- Backtesting package exportları güncellendi.
- Son implementation commitleri: **44071ce440525391a3dce6081a418cbeeb6a2693**, **7aa1475d367baab7d42c8cb7c0eb93be3e59f24d**, **88341a30e8e2cdcacda5e5fbecf8cd61737d8286**, **61f8f97347d0435cdd9a54b0a81c1d9eec11207d**, **43a3fc172a3393b2094993033a8c3e884f241f75**.
- Bu yeni diagnostic değişiklikleri için Codespace testleri henüz çalıştırılmadı; gerçek AFA/AFT diagnostic sonucu henüz yok.

### Faz 6 — Real Fund Exposure / Signal Diagnostic Sonuçları

- Codespace doğrulaması: diagnostic targeted suite **4 passed in 1.28s**, full backend suite **209 passed in 10.73s**. Real diagnostic smoke da **PASSED** oldu; AFA/AFT için toplam **240 OOS gözlem**, 3x40 dış fold protokolü kullanıldı.- AFA: OOS mean target weight **0.3154**, median **0.3087**, max **0.5267**; gözlemlerin %68.3'ü 25% üzerindeyken yalnızca **3/120** gözlem 50% üzerindeydi ve 75% üzeri hiç yoktu. Aggregate ML ROC **0.3453**, Technical ROC **0.3301**, Signal ROC **0.2897**; signal'ın 5 günlük forward return Spearman ilişkisi **-0.1876**.
- AFA Fold 1'de yüksek exposure bandı (25-50%) target rate yalnızca **26.32%** iken <25% bandında **52.38%**; buna rağmen mean forward return bantlar arasında **+2.1593% vs +1.9455%** idi. Fold 2'de 50-75% bandı yalnızca **3 gözlem** olmasına rağmen **66.67%** positive target verdi. Fold 3'te tüm 40 gözlem 25-50% bandında ve positive target rate **12.50%** kaldı. Bu, exposure seviyesinin tek başına performans açıklaması olmadığını ve score sıralamasının fold/regime bazında bozulabildiğini gösteriyor.
- AFT: OOS mean target weight **0.2656**, median **0.2553**, max **0.5067**; 75% üzeri hiç gözlem yok, yalnızca **1/120** gözlem 50% üzerindeydi. Aggregate ML ROC **0.5878**, Technical ROC **0.4249**, Signal ROC **0.5197**; signal'ın forward return Spearman ilişkisi **+0.0807**.
- AFT Fold 2'de Signal ROC **0.9314** ve forward-return Spearman **+0.3979**; <25% bandı mean forward return **-1.5384% / 0% positive target**, 25-50% bandı **+0.3337% / 30% positive target**. Bu fold model/signal'ın işe yaradığı örnektir.
- AFT Fold 3'te Signal ROC **0.1111** ve forward-return Spearman **-0.6507**; <25% bandı **+1.9533% mean forward return / 41.94% positive target**, 25-50% bandı **-2.5189% / 0% positive target**. Bu, aynı production signal zincirinin rejim değişiminde tersine dönebildiğini gösteren güçlü OOS kanıtıdır.
- Cross-fund exposure dağılımı: mean weight **0.2905**, median **0.2950**, max **0.5267**; %31.67 <25%, %66.67 25-50%, %1.67 50-75%, **0% >=75%**. Aggregate ML ROC **0.4828**, Technical ROC **0.3752**, Signal ROC **0.4088** ve signal-forward-return Spearman **+0.0149**.
- Cross-fund exposure bantlarında <25% mean forward return **+1.0771%**, 25-50% **+1.0130%**, 50-75% **+2.0267%** (yalnızca 4 gözlem). Bu nedenle mevcut lineer score-to-weight mapping için OOS'ta monotonic outcome ilişkisi gösterilemedi.

**Teşhis / karar**
- İlk hypothesis olan “sorun yalnızca düşük exposure” desteklenmedi. Ortalama exposure gerçekten düşüktü (**0.2905**) ve yüksek exposure neredeyse hiç kullanılmadı; ancak score'un gerçekleşen forward return ile cross-fund korelasyonu yalnızca **+0.0149**, signal ROC **0.4088** idi.
- Dolayısıyla bir sonraki task mapping optimizasyonu değil; **regime-stability / score monotonicity diagnostic** olmalı. Özellikle AFT Fold 2 -> Fold 3 yön değişimi ve AFA Fold 1 -> Fold 3 bozulması ayrıştırılmalı.
- Production contractlar değiştirilmedi: target h5/+3%, raw_all, signal weighting, production linear sizing ve fund t+1 unit-price execution korunuyor.

### Faz 6 — Fund Diagnostic v2: Risk ve Pozitif Getiri Ayrıştırması

- Exposure diagnostic bir sonraki iterasyona genişletildi; production signal/output değiştirilmedi.
- Score relationship analizi artık **ML probability, Technical Score, pre-risk Signal Score, final Signal Score, Risk Score ve Risk Adjustment** için OOS target / 5-day forward-return ilişkilerini raporluyor.
- Exposure band çıktısına `forward_return_5d > 0` gerçekleşme oranı eklendi. Böylece production target olan `forward_return_5d > +3%` ile sıradan pozitif forward return birbirinden ayrıştırılabiliyor.
- Bu ayrım önemli çünkü ilk AFA/AFT backtestinde fon B&H getirileri pozitif olurken +3% classification target seyrek kalabiliyor; bu nedenle classification hedefinin exposure/risk davranışıyla ne kadar uyumlu olduğu ayrıca ölçülmeli.
- Unit testler risk-score yönü ve positive-forward-return-rate alanını kapsayacak şekilde genişletildi.
- Son code commits: **39ed13833bdc3d0bf3a031e4a642305c97d4aca6**, **02e34efa49439e22da0db268da372c86a25b8cd2**, **57b2810a968228ba42dd48b303ea928c1f68963a**, **6f69911f8aaaaab5d6fb41158f499e53ca42a8ba**.
- Bu son değişiklikler için Codespace test sonucu henüz yok.

### Faz 6 — Fund Risk Ablation Hazırlığı

- Diagnostic v2 sonucu risk layer'ın rejime bağlı davranışı görüldüğü için risk'i üretimde kapatmak veya yeniden ağırlıklandırmak yerine counterfactual OOS ablation hazırlanıyor.
- Yeni `backend/scripts/smoke_test_fund_risk_ablation_real.py`: aynı 3x40 outer OOS fold ve aynı tuned XGBoost prediction üzerinde **production risk adjustment** ile **risk_adjustment=0** koşullarını karşılaştırır; B&H, excess return, turnover ve risk contribution raporlar.
- Bu karşılaştırmada no-risk signal, final signal'dan risk cezasını çıkarmak yerine `calculate_signal_score(..., risk_adjustment=0)` ile yeniden hesaplanıyor; böylece clipping sınırlarında da counterfactual doğru tanımlanıyor.
- Diagnostic correlation helper constant input durumunda artık `None` döndürüyor; böylece AFA Fold 3'te görülen pandas `ConstantInputWarning` temizleniyor. Unit test ile sabit score davranışı kapsandı.
- Production target, signal weighting, risk config veya sizing policy değiştirilmedi; bu task yalnızca OOS evaluation/ablation.
- Son code commits: **06778b82efdf397ebb6cde4ad04e542e50b0dae5**, **f5f4703cd249ae6f97702d5a97c24f025ddce9aa**, **63ee37bc073dca79d964f99c41fe1c710fdc612a**.
- Bu yeni değişikliklerin Codespace test ve gerçek ablation sonucu henüz alınmadı.

### Faz 6 — Real Fund Risk Ablation Sonucu

- Codespace doğrulaması: fund diagnostic/risk ablation targeted suite **16 passed in 1.59s**; full backend suite **210 passed in 10.88s**. Önceki constant-correlation warning de bu çalışma ile artık görünmedi.
- AFA risk ablation: Fold 1 production **+3.8667%** vs no-risk **+4.0482%** (risk contribution **-0.1814 pp**); Fold 2 **+1.0023%** vs **+1.1280%** (**-0.1257 pp**); Fold 3 risk score **0** olduğu için iki koşul aynı (**0.0000 pp**).
- AFT risk ablation: Fold 1 production **+5.7710%** vs no-risk **+6.6887%** (**-0.9177 pp**); Fold 2 production **+0.5412%** vs no-risk **+0.0998%** (**+0.4414 pp**, risk faydalı); Fold 3 production **+0.1874%** vs no-risk **+0.7081%** (**-0.5207 pp**).
- Cross-fund: mean production return **+2.2849%**, no-risk **+2.5023%**, B&H **+7.8261%**; production excess **-5.5412%**, no-risk excess **-5.3238%**; mean risk contribution **-0.2173 pp** ve yalnızca **1/6 fold** riskten pozitif katkı aldı.

**Karar:** Risk adjustment production performansını ortalamada biraz bozuyor ancak ana alpha/excess problemi değil. Risk kaldırıldığında bile strateji B&H karşısında güçlü biçimde negatif kalıyor. Bu nedenle risk layer production'dan kaldırılmıyor ve ağırlıkları değiştirilmeden korunuyor; sonraki inceleme model score'unun gerçek getiriyi sıralama kabiliyetine odaklanıyor.

### Faz 6 — Fund Score Quantile Monotonicity Diagnostic Hazırlığı

- `summarize_score_quintiles()` eklendi. OOS score'ları eşit sayıda 5 gruba ayırarak ML probability ve final Signal Score için mean/median forward return, positive-return rate ve +3% target rate raporlanıyor.
- Ranking, score tie'larında `rank(method="first")` ile deterministik hale getiriliyor; production code/training behavior değiştirilmez.
- Real exposure diagnostic runner quintile raporunu fold ve aggregate seviyede gösterecek şekilde genişletildi.
- Amaç: continuous score'un gerçekten monotonik ekonomik ordering üretip üretmediğini, exposure mapping'den bağımsız olarak ölçmek.
- Kod commits: **1d2b2ff6e4d85df538bca87112bf52a6c287bbc5**, **c2bb524532c812c3f56bbaf5392a30adaf575694**, **2d57b32b15f28f88b8b60ba708ad41f6ed9c31ba**, **0f45fec7eb0d7ab7e7f50b8ba9f9bbad52e7303e**.
- Bu son quintile değişiklikleri için Codespace doğrulaması henüz alınmadı.

### Faz 6 — Real Fund Score Quintile Sonuçları

- Codespace doğrulaması: targeted diagnostic/backtest suite **18 passed in 1.48s**, full backend suite **212 passed in 11.29s**. Real exposure diagnostic **PASSED** oldu.
- AFA Fold 1 Signal Score quintileleri monotonik değil: Q1 **+2.0293%**, Q2 **-0.4009%**, Q3 **+4.1370%**, Q4 **+2.6746%**, Q5 **+1.7953%** mean 5-day forward return. fileciteturn818file0L61-L73
- AFA Fold 2: Signal Score Q1 **+0.7445%**, Q2 **+2.0453%**, Q3 **+0.3539%**, Q4 **-0.5164%**, Q5 **+0.0444%**. Higher score clearly monotonic değil. fileciteturn818file0L89-L101
- AFA Fold 3 daha belirgin terslik gösteriyor: Q1 **+5.0053%**, Q5 **-2.6564%**. fileciteturn818file0L117-L129
- AFT Fold 2'de Q5 **+4.4111%** ile açık ara en iyi bucket olsa da Fold 3'te Q1 **+3.8652%**, Q5 **-2.6564%**; rejim stabilitesi yok. fileciteturn818file0L189-L201 fileciteturn818file0L217-L229
- Cross-fund aggregate Signal Score quintiles: Q1 **+1.2095%**, Q2 **+0.7919%**, Q3 **+1.1780%**, Q4 **+0.8234%**, Q5 **+1.2482%**. Q5 yalnızca marjinal olarak Q1'in üzerinde ve sıra boyunca monoton artış yok. fileciteturn818file0L257-L270
- Cross-fund ML probability quintiles de tam monotonik değil: Q1 **+1.1283%**, Q2 **-0.3145%**, Q3 **+1.5202%**, Q4 **+1.6473%**, Q5 **+1.2697%**. Bu nedenle sorun yalnızca final signal composition değil; model probability ordering de istikrarlı değil. fileciteturn818file0L257-L263

**Karar:** Fund score-to-return ordering production OOS'ta yeterince monotonic olmadığı için exposure mapping veya risk ayarı ile doğrudan optimize edilmeyecek. Bir sonraki kontrollü diagnostic, +3% classification target'ın event sparsity / label noise etkisini ayırmak olacak.

### Faz 6 — Fund Target Threshold Diagnostic Hazırlığı

- Yeni `backend/scripts/smoke_test_fund_target_threshold_real.py` eklendi.
- Diagnostic threshold seti varsayılan olarak **0%, 1%, 2%, 3%, 5%**. Her threshold ayrı supervised label üretir; aynı 3x40 outer walk-forward ve gap=5 korunur.
- Her threshold için dataset target rate, fold/OOS ROC-AUC, PR-AUC, probability -> forward-return Spearman ve Q5-Q1 forward-return spread raporlanır.
- Bu çalışma threshold'u production'da seçmez; yalnızca +3% target'ın seyrek/kararsız label üretiminin model ordering üzerindeki etkisini ölçer. Production target h5/+3% değişmeden kalır.
- Son code commits: **82f134154705d778e689e872e38c5c891419978b**, **fece860cc52e5fdcdb3515c183188598e4e9ff1e**.
- Bu yeni threshold diagnostic için Codespace test/real run sonucu henüz alınmadı.

## Sıradaki İş

1. Codespace'te güncel fund engine + benchmark testlerini ve full backend suite'i tekrar çalıştır.
2. Real AFA/AFT fund OOS backtest runner'ını çalıştır; PostgreSQL canonical history kullanılıyorsa TEFAS fallback'e gerek kalmadığını, fold başına 39 executable period oluştuğunu ve benchmark/strategy metriklerini doğrula.
3. Gerçek fund OOS sonuçlarını kaydettikten sonra fund mapping/cost sensitivity gerekip gerekmediğine karar ver ve ardından Faz 6 API/prediction katmanıyla backtest sonuçlarını nasıl expose edeceğimizi tasarla.

### Faz 6 — Fund Target Threshold Diagnostic Argparse Fix

- Real threshold diagnostic çalıştırmasında argparse help metnindeki literal **%** karakteri `%` formatting olarak yorumlandığı için `ValueError: incomplete format` oluştu.
- Kod mantığı değiştirilmeden `--thresholds` help metnindeki **+3% -> +3%%** olarak düzeltildi. Commit: **51d90945ee161bbb620cf9457f3aae9631a7e4c6**.
- Bu fix için gerçek Codespace threshold diagnostic sonucu henüz alınmadı; sonraki çalıştırma threshold hesaplamasına devam etmeli.

### Faz 6 — Real Fund Target Threshold Diagnostic Sonucu

- Codespace doğrulaması: önce targeted suite **18 passed in 1.77s**, full backend suite **212 passed in 10.81s**; ardından gerçek threshold diagnostic **PASSED** oldu.
- AFA genel target oranları: **0%=69.23%**, **1%=42.74%**, **2%=22.44%**, **3%=13.46%**. OOS ordering açısından aggregate Q5-Q1 spread sırasıyla **-1.1441%**, **-0.2648%**, **+0.0009%**, **-1.3497%**; OOS probability-to-forward-return Spearman **-0.0930**, **-0.0014**, **+0.0669**, **-0.1492**. Bu fund için threshold düşürmek tek başına yeterli sinyal üretmiyor.
- AFT genel target oranları: **0%=61.57%**, **1%=48.62%**, **2%=37.58%**, **3%=28.03%**, **5%=9.77%**. En iyi aggregate ordering **1–2%** bandında: Q5-Q1 **+4.4028% / +4.1744%** ve Spearman **+0.3147 / +0.2764**; production `%3` seviyesinde bunlar **+1.1669% / +0.1887** oluyor. `%5` ise OOS ROC **0.3518**, PR **0.1282**, Spearman **-0.2513**, Q5-Q1 **-3.5399%** ile belirgin bozuluyor.
- Cross-fund ortalamasında `%1` ve `%2` threshold'ları `%3`'ten daha iyi: mean OOS ROC **0.6098 / 0.5731 / 0.4665**, mean PR **0.6251 / 0.4261 / 0.3263**, mean Spearman **+0.1566 / +0.1717 / +0.0198**, mean Q5-Q1 **+2.0690% / +2.0876% / -0.0914%**.
- `%5` yalnız AFT için geçerli kaldı; AFA'da inner validation iki-class fold koşulu sağlanamadı. Bu, yüksek threshold'da label sparsity'nin pratik olarak sorun haline geldiğini doğruluyor.

**Karar:** Label sparsity ve threshold seçimi model ordering'i anlamlı biçimde etkiliyor, özellikle AFT'de. Ancak AFA'nın `%0–2` seviyelerinde bile tutarlı ordering üretememesi nedeniyle sorun **yalnızca +3% sparse target değil**. Production contract h5/+3% şimdilik değiştirilmedi.

### Faz 6 — Güncel Sıradaki İş

1. Aynı gerçek OOS backtest protokolüyle fund strategy'yi diagnostic olarak **threshold=1%, 2%, 3%** altında karşılaştır; execution, risk layer, linear mapping ve benchmark kontratını sabit tut. Amaç daha iyi score ordering'in gerçek excess return'a dönüşüp dönüşmediğini görmek.
2. Bu backtest de AFA'da anlamlı iyileşme göstermiyorsa feature/model-regime istikrarsızlığına geç; özellikle aynı OOS pencerelerinde feature -> forward_return ilişkilerinin stabilitesini ölç.
3. Threshold sonuçlarına bakarak production target'ı henüz değiştirme; önce P&L doğrulaması ve fund-specific davranış kanıtı gerekli.

### Faz 6 — Fund Threshold Backtest Sonuçları

- Real AFA/AFT fund OOS backtest, aynı execution/risk/mapping kontratı ve aynı 3x40 gap=5 protokolü ile threshold **1%, 2%, 3%** için çalıştırıldı. Üç koşul da `REAL FUND BACKTEST SMOKE TEST PASSED`; data source her iki fonda da **PostgreSQL canonical history** ve fold başına **39 executable period**.
- Threshold **1%**: cross-fund mean strategy **+3.6052%**, mean B&H **+7.8261%**, mean excess **-4.2210%**, positive excess **16.67%**, mean Sharpe **+2.473**, mean turnover **2.2990**, transaction cost **1392.578462**. AFA mean excess **-5.5503%**, AFT **-2.8916%**.
- Threshold **2%**: cross-fund mean strategy **+2.9692%**, mean B&H **+7.8261%**, mean excess **-4.8569%**, positive excess **16.67%**, mean Sharpe **+2.758**, mean turnover **1.9647**, transaction cost **1188.334957**. AFA mean excess **-6.5091%**, AFT **-3.2048%**.
- Threshold **3% (production)**: cross-fund mean strategy **+2.2849%**, mean B&H **+7.8261%**, mean excess **-5.5412%**, positive excess **16.67%**, mean Sharpe **+2.817**, mean turnover **1.4662**, transaction cost **881.969488**. AFA mean excess **-6.5137%**, AFT **-4.5687%**.
- `%1` target, `%3`'e göre mean excess'i **+1.3202 pp** iyileştiriyor ve mean strategy return'ü **+1.3203 pp** artırıyor; buna rağmen benchmark karşısında hâlâ belirgin negatif ve fold bazında yalnız **1/6** positive excess görülüyor. `%2` ise `%3`'ten daha kötü.
- Threshold diagnostic'teki daha iyi `%1–2` score ordering, özellikle AFT'de, gerçek P&L'de sınırlı iyileşmeye dönüşüyor; AFA'da `%1–2` dahi B&H'a karşı kalıcı alpha üretmiyor.
- İşletim notu: ilk `%1` komutundaki `cd .../backendd` yazım hatası shell'in mevcut dizini koruması nedeniyle script çalışmasını engellemedi; sonraki komutlar doğru `/backend` dizininde çalıştı.

**Karar:** Production target **h5/+3% şimdilik korunuyor**. `%1` diagnostic olarak en iyi üç aday arasında olsa da 3-fold/2-fund OOS'ta negatif excess problemi çözülmedi; threshold tek başına production değişikliği için yeterli kanıt değil.

### Faz 6 — Güncel Sıradaki İş

1. AFA ve AFT için outer fold bazında feature -> `forward_return_5d` Spearman/direction ve XGBoost gain importance istikrarını ölç; aynı OOS pencerelerinde feature yönünün ve model kullandığı feature'ların ne kadar değiştiğini raporla.
2. Feature/regime diagnostic'te belirgin instability çıkarsa model/feature design'a kontrollü müdahale etmeden önce bunun hangi dönemlerde oluştuğunu ayır; production target/risk/mapping contractını koru.
3. Feature stability zayıf değilse ancak score ordering zayıf kalıyorsa, model calibration/selection stability ve time-regime drift incelemesine geç.

### Faz 6 — Fund Feature Regime Stability Diagnostic Hazırlığı

- `backend/scripts/smoke_test_fund_feature_regime_stability_real.py` eklendi.
- Script AFA/AFT için aynı 3x40 outer OOS + gap=5 protokolünde her fold'da feature -> `forward_return_5d` ve feature -> target Spearman ilişkilerini, ayrıca tuned XGBoost normalized gain importance'ı çıkarıyor.
- Aggregate rapor feature yönü sign stability (`+/-` fold sayıları, std) ve gain stability (`mean normalized gain`, std, top-3 fold count) veriyor. Amaç production contractını değiştirmeden regime/feature instability'yi doğrudan kanıtlamak.
- Code commit: **057ed19e4aeab8a7630761dbcc8c39e695a2e059**. Codespace test/real-run sonucu henüz alınmadı.

### Faz 6 — Real Fund Feature Regime Stability Sonucu

- Codespace'te AFA/AFT feature-regime diagnostic PostgreSQL canonical history ile PASSED oldu; AFA 672 raw / 468 dataset, AFT 675 raw / 471 dataset, production h5/+3%, outer 3x40, gap=5.
- AFA'da 63 fold-feature gözleminin 46'sı negatif / 17'si pozitif forward-return yönünde. sma_20, bb_mid, ema_20, macd, ema_50, rsi_14 gibi bazı feature'lar üç foldun tamamında negatif yönde. bb_width, bb_lower ve volatility_20 gibi yüksek gain alan feature'lar ise foldlar arasında daha karmaşık/kararsız yön taşıyor.
- AFT'de durum daha da belirgin: 52 negatif / 11 pozitif fold-feature yönü. ema_20, sma_20, rsi_14, momentum_20, macd, ema_50, bb_position ve macd_hist üç fold boyunca negatif forward-return ilişkisine sahip.
- Buna karşın XGBoost gain dağılımı tamamen rastgele değil. AFA'da ve AFT'de birçok feature üç outer foldun tamamında top-3 gain kapsamına giriyor. Bu, modelin feature kullanımının bütünüyle selection noise olmadığını gösteriyor.
- Mevcut kanıt 'feature selection tamamen unstable' demeyi desteklemiyor. Daha güçlü bulgu, raw feature setinin bazı ekonomik ilişkileri sistematik biçimde ters yönde taşıması ve modelin bu ilişkileri OOS'ta güvenilir şekilde positive-return ordering'e çevirememesi. AFA'da problem belirgin; AFT'de ise 1-2% threshold ile ordering iyileşse bile production 3% threshold'da zayıflıyor.

Karar: Production target h5/+3%, risk layer ve raw_all representation şimdilik korunuyor. Bir sonraki kontrollü deney repository'de hazır bulunan normalized_all ve stationary_core representation'larının daha yoğun event threshold'larında 1% ve 2% nested OOS davranışını karşılaştırmak olacak. Production representation bu deney sonucuna göre otomatik değiştirilmeyecek.

### Faz 6 — Sıradaki İş

1. AFA ve AFT için nested representation smoke'u threshold=1%, sonra threshold=2% ile çalıştır; raw_all / normalized_all / stationary_core seçimlerini ve outer ROC/PR/Spearman sonuçlarını karşılaştır.
2. normalized_all veya stationary_core iki fonda da ve birden fazla outer fold'da daha iyi OOS ordering verirse representation ablation'ı daha geniş sembol/fon kapsamına çıkar; tek fondaki sonuca dayanarak production değişikliği yapma.
3. Representation farkı küçük kalırsa model selection/calibration/regime drift tarafına geç; özellikle inner PR-AUC'nin outer OOS'a taşınma oranını incele.

### Faz 6 — Nested Representation Threshold Sonuçları

- Threshold **1%** nested representation smoke AFA ve AFT üzerinde PASSED oldu. AFA'da outer seçimler `raw_all -> stationary_core -> normalized_all`; outer Spearman sırasıyla **-0.1044, +0.1149, +0.3584**. AFT'de `normalized_all` **3/3** fold seçildi; outer Spearman **-0.1812, +0.5955, +0.2651**. fileciteturn852file0L17-L57
- Threshold **2%** nested representation smoke AFA ve AFT üzerinde PASSED oldu. AFA'da `normalized_all` **3/3** fold seçildi ve outer Spearman **+0.4331, +0.2501, +0.2707**; outer ROC **0.7500, 0.6667, 0.7056**. AFT'de seçim `stationary_core -> raw_all -> normalized_all`; `stationary_core` Fold 1'de outer ROC **0.1604**, Spearman **-0.5877** ile belirgin başarısız olurken raw/normalized sonraki foldlarda güçlü sonuçlar verdi. fileciteturn852file0L61-L110
- Bu sonuçlar `normalized_all` için önceki evidence'i güçlendiriyor: AFA `%2`'de tüm outer foldlarda seçilmesi ve pozitif Spearman vermesi, AFT `%1`'de tüm outer foldlarda seçilmesi önemli. Ancak AFT `%2` Fold 1 örneği, inner selection'ın yanlış representation'ı seçebileceğini ve selection riskinin hâlâ bulunduğunu gösteriyor.

**Karar:** `normalized_all` artık güçlü deneysel aday; fakat production `raw_all` henüz değiştirilmedi. Nested selection sonucunu tek başına production kararına çevirmek yerine her representation'ın aynı outer foldlarda doğrudan karşılaştırıldığı fixed-representation ablation gerekiyor.

### Faz 6 — Sıradaki İş

1. `smoke_test_feature_ablation_real.py` ile AFA/AFT için threshold **1%** ve **2%** altında `raw_all / normalized_all / stationary_core` fixed-representation tuned OOS sonuçlarını karşılaştır.
2. Özellikle aggregate Spearman/PR/ROC yanında fold bazında direction consistency ve OOS performansını kontrol et; nested winner'ın gerçekten non-winner'ları geçtiğini doğrula.
3. `normalized_all` fixed OOS olarak iki fonda da belirgin üstün çıkarsa daha geniş fon örneklemine geç; production representation yine ancak daha geniş kanıtla değiştirilecek.

### Faz 6 — Fixed Representation Ablation Threshold Sonuçları

- AFA `%1` fixed ablation: `normalized_all` tuned aggregate ROC **0.5882**, PR **0.5869**, Spearman **+0.1526** ile `raw_all` (**0.5356 / 0.5389 / +0.0616**) ve `stationary_core` (**0.5231 / 0.5480 / +0.0400**) karşısında üstün. Fold bazında normalized Spearman **+0.1498 / +0.0716 / +0.3584**.
- AFT `%1` fixed ablation: `raw_all` tuned aggregate ROC **0.6841**, PR **0.7112**, Spearman **+0.3172** ile `normalized_all` (**0.5920 / 0.5901 / +0.1586**) ve `stationary_core` (**0.5738 / 0.6213 / +0.1272**) üzerinde. Normalized Fold 1'de negatif Spearman **-0.1812** üretirken Fold 2/3 pozitif.
- AFA `%2` fixed ablation: `normalized_all` yine açık ara üstün; tuned ROC **0.6848**, PR **0.4696**, Spearman **+0.2956**. `raw_all` **0.5099 / 0.3259 / +0.0159**, `stationary_core` **0.5353 / 0.3461 / +0.0565**.
- AFT `%2` fixed ablation: `raw_all` tuned ROC **0.6364** ve Spearman **+0.2276** ile normalized'ın (**0.5964 / +0.1610**) üzerinde; normalized PR **0.5418** ile raw PR **0.5262**'den az farkla yüksek. `stationary_core` daha zayıf (**0.5619 / 0.5074 / +0.1033**).
- Bu dört fixed OOS deney birlikte, `normalized_all`'ın AFA için güçlü ve threshold'a dayanıklı bir iyileştirme olduğunu; ancak AFT için universal olarak üstün olmadığını gösteriyor. `stationary_core` bu örnekte production adayı olarak desteklenmiyor.

**Karar:** Production representation **raw_all** korunuyor. Representation seçimini global olarak `normalized_all`'a çevirmek için evidence henüz yetersiz; sonuçlar fund-specific davranışa işaret ediyor. Sonraki kanıt adımı üçüncü gerçek fon olan **AFS** üzerinde `%1` ve `%2` fixed ablation yapmak.

### Faz 6 — Sıradaki İş

1. AFS için fixed representation ablation'ı threshold **1%** ve **2%** çalıştır.
2. AFS sonucu da normalized yönündeyse fon sayısını genişletip fund-specific/global representation kararını örneklem bazında ölç; AFA/AFT ile sınırlı kalma.
3. AFS'te raw/normalized tekrar karışık çıkarsa universal representation yerine fund-level representation selection veya representation-ensemble tasarımını ancak daha geniş OOS kanıtından sonra değerlendir.

### Faz 6 — AFS Feature Ablation Loader Fix

- AFS fixed feature ablation çalıştırması `ValueError: no DB fund history found for AFS` ile durdu. İncelemede `smoke_test_feature_ablation_real.py` fund loader'ının DB'de kayıt yoksa TEFAS fallback'i olmadığı görüldü.
- Loader, fund real-backtest'teki mevcut DB -> TEFAS fallback sözleşmesiyle hizalandı: yeterli canonical DB satırı varsa PostgreSQL kullanılıyor, aksi durumda chunked `TefasProvider` history yükleniyor, duplicate pricing dates temizleniyor ve `chunk-delay` CLI parametresi destekleniyor.
- Stock ablation akışı ve representation/model hesaplaması değiştirilmedi. Production target, gap, feature representation seti ve tuning mantığı korunuyor.
- Düzeltme commit: **34089f8fd1f43b555f99012bc212340f5b481034**.
- Kod GitHub üzerinde tekrar okunarak fund SQL aliası, `_run` parametreleri ve CLI `chunk-delay` wiring'i doğrulandı. Gerçek AFS run sonucu bu düzeltmeden sonra henüz alınmadı.

### Faz 6 — Güncel Sıradaki İş

1. AFS fixed representation ablation'ı threshold **1%** ve **2%** için, TEFAS fallback'i kullanmasına izin vererek çalıştır.
2. AFS sonucu AFA/AFT ile birlikte değerlendirilecek; normalized_all için global representation kararı henüz alınmayacak.

### Faz 6 — TEFAS v2 Fund History Migration

- AFS fixed ablation fallback'i 1000 günlük geçmiş için eski `fonGnlBlgSiraliGetir` endpoint'ini 28 günlük parçalara bölerek çağırdığı için Codespace'te TLS handshake sırasında yaklaşık 15 dakika takıldı ve kullanıcı işlemi durdurdu.
- Güncel 2026 TEFAS istemci davranışı incelendi: tarihsel fon fiyatı için `fonFiyatBilgiGetir` v2 endpoint'i kullanılıyor ve sabit `periyod` kodlarıyla 5 yıla kadar geçmiş tek çağrıda alınabiliyor. Yeni endpoint'in request/period sözleşmesi güncel `borsapy` implementasyonu ile doğrulandı.
- `TefasProvider.get_fund_history()` artık v2 history endpoint'ini kullanıyor; 1000 günlük istek `periyod=36` ile tek çağrıda karşılanıyor. Dönen seri istenen tarih aralığına client-side filtreleniyor.
- History çağrıları için ayrı kontrollü timeout/retry ayarları eklendi: `history_timeout=15s`, `history_retries=2`, `history_backoff_seconds=1s`. Genel legacy provider retry davranışı korunuyor.
- v2 payload/mapping, period bucket seçimi, 5-yıl sınırı ve per-call transport retry kontrolü için testler eklendi.
- Provider migration commitleri: **5a0b2622677d3100a1a5f778e0ab60330f544f82**, **4f16ecd452921d7243745b8057c2c494c60e84c9**. Test commitleri: **81d128e37a17f7fb8ec3be693e92a74a262fb324**, **f28a589c020a7f35c47c3967ee1462ff717f57c0**.
- Feature ablation scripti zaten DB -> TEFAS fallback kullanıyordu; loader bu yeni provider davranışıyla artık 1000 günlük AFS fallback'i için onlarca eski endpoint çağrısı yapmayacak.
- Web doğrulaması: güncel `borsapy` TEFAS provider'ı `fonFiyatBilgiGetir` endpoint'ini ve 5 yıllık `periyod=60` üst sınırını kullanıyor. TEFAS resmi site de tarihsel fon verisi sağlıyor. citeturn607210view1turn607210view2

**Karar:** AFS testini tekrar 15+ dakika beklemeyeceğiz. Önce Codespace'te targeted TEFAS/provider testleri ve full backend suite çalıştırılacak; ardından AFS `%1/%2` ablation yeniden denenecek. Gerçek provider erişimi başarısız olursa script artık kontrollü sürede hata vermeli.

### Faz 6 — Sıradaki İş

1. Codespace'te TEFAS targeted tests + full backend suite'i çalıştır.
2. AFS `%1` fixed ablation'ı tekrar çalıştır; `Data source` ve dataset satır sayısını kontrol et.
3. AFS `%2` fixed ablation'ı çalıştır ve AFA/AFT/AFS üçlü representation karşılaştırmasını tamamla.

### Faz 6 — TEFAS v2 Test Import Fix

- Codespace targeted TEFAS/provider suite sonucunda **12 passed, 1 failed**; full backend suite **214 passed, 1 failed**. Tek hata `test_tefas_history_v2_payload_and_mapping` içinde `TefasSettings` importunun eksik olmasıydı.
- `backend/tests/data/test_free_providers.py` içindeki import `TefasProvider, TefasSettings` olacak şekilde düzeltildi. Provider mantığına dokunulmadı.
- Düzeltme commit: **4677b84d401029ad6607b301ca265ba492ef72ba**.
- Bu commit sonrası Codespace yeniden test sonucu henüz alınmadı.

### Faz 6 — Güncel Sıradaki İş

1. Targeted TEFAS/provider testini yeniden çalıştır.
2. Full backend suite'i yeniden çalıştır.
3. İkisi de geçerse AFS `%1` fixed feature ablation'ı tekrar çalıştır.

### Faz 6 — TEFAS v2 Historical Range Regression Fix

- AFS ablation tekrarında `No TEFAS fund history for AFS in requested range 2024-01-10..2024-02-06` görüldü. Kök neden `fonFiyatBilgiGetir` v2'nin `periyod` parametresinin tarih aralığı değil, bugünden geriye dönük sabit pencere seçmesi ve bizim loader'ın eski 28-gün chunk mantığını korumasıydı.
- `TefasProvider._history_period()` artık requested `start_date` yaşını `as_of_date` karşısında ölçerek smallest covering v2 bucket'ı seçiyor; 2024-01 tarihli 1000 günlük geçmiş için `periyod=36` seçiliyor. Gelecek tarihleri açıkça reddediyor.
- Regression test eklendi: 2024-01-10..2024-02-06 isteğinin `fonFiyatBilgiGetir` + `periyod=36` ile yapıldığı ve response'un client-side filtrelendiği doğrulanıyor.
- `smoke_test_feature_ablation_real.py` ve `smoke_test_backtest_fund_real.py` TEFAS fallback helper'ları artık uzun geçmişi 28 günlük v2 çağrılarına bölmüyor; doğrudan `get_fund_history(start_date, end_date)` çağrısı yapıyor. `--chunk-delay` CLI geriye dönük uyumluluk için duruyor fakat tek history çağrısında sleep uygulanmıyor.
- Provider retry branch'i per-call `effective_backoff` değerini kullanacak şekilde tamamlandı.
- Kod/test commitleri: **71e6889b1b620812c4f0b7814a7b7be4b1ff43ba**, **9b2c77d008369379fe0d62154bd1de258a948555**, **b8f343367de057c2e540f3855f005f2ccecdeeb6**, **626cbbb54835990a09fe2440c8a49e6b456804f9**, **56b40136175c1a0555587901a6cc0d0773562b77**, **3b4feaa9ae8936b958f35d2a4c07db09e61539bb**.
- Son Codespace sonucu bu düzeltmelerden önce **12 passed / 1 failed** targeted ve **214 passed / 1 failed** full suite idi; failure yalnızca eksik `TefasSettings` importuydu ve `4677b84d401029ad6607b301ca265ba492ef72ba` ile düzeltildi. Yeni provider/range fix sonrası yeniden Codespace testi henüz alınmadı.

**Karar:** AFS `%1/%2` ablation'ı için yeniden uzun bekleme yapılmayacak. Önce provider targeted testleri + full suite, ardından AFS `%1` ve `%2` ablation çalıştırılacak. Production target/representation/model contractı değişmedi.

### Faz 6 — AFS Fixed Representation Ablation — Threshold 1% Gerçek Sonucu

- Codespace'te AFS fixed representation ablation **threshold=1%** ile PASSED oldu.
- Veri kaynağı **TEFAS provider fallback**, çünkü canonical PostgreSQL history minimum satır şartını karşılamadı. **685 raw rows**, **481 dataset rows**, target contract diagnostic olarak **h5 / >1%**, gap=5, outer 3-fold / 40 OOS protokolü.
- raw_all tuned aggregate: ROC **0.5036**, PR **0.4457**, Spearman **+0.0062**. Fold Spearman: **+0.3088 / -0.1915 / +0.0559**.
- normalized_all tuned aggregate: ROC **0.5232**, PR **0.4515**, Spearman **+0.0392**. Fold Spearman: **-0.1090 / +0.1045 / +0.1096**.
- stationary_core tuned aggregate: ROC **0.5509**, PR **0.4355**, Spearman **+0.0860**. Fold Spearman: **-0.2043 / +0.1828 / +0.3064**.
- Bu runın **en yüksek tuned PR-AUC değeri normalized_all (0.4515)** olsa da aggregate ROC ve Spearman'da **stationary_core** önde. Hiçbir representation 3 outer fold boyunca kusursuz/stabil üstünlük göstermiyor.
- AFA/AFT ile birlikte değerlendirildiğinde AFS sonucu da universal bir winner üretmiyor: AFA'da normalized_all güçlüydü, AFT'de raw_all daha güçlüydü, AFS'de ROC/Spearman açısından stationary_core öne çıkarken PR'da normalized_all önde.
- TEFAS v2 migration + historical range fix'in pratik sonucu doğrulandı: AFS fallback 1000 günlük veri setini başarıyla oluşturdu ve eski uzun chunk/28-gün endpoint zincirine takılmadan ablation tamamlandı.

**Karar:** raw_all production representation olarak korunuyor. normalized_all AFA ağırlıklı güçlü deneysel aday olmaya devam ediyor; stationary_core AFS'te iyi görünse de fundlar arasında universal üstünlük kanıtı yok. Representation değişikliği yapılmıyor.

### Faz 6 — Sıradaki İş

1. AFS fixed representation ablation'ı threshold **2%** ile çalıştır.
2. AFA + AFT + AFS için %1/%2 fixed OOS sonuçlarını tek tabloda karşılaştır; representation başına hangi fonlarda ve hangi metrikte üstünlük olduğunu ölç.
3. Universal representation winner çıkmazsa fund-level representation selection/ensemble fikrini hemen production'a taşımadan önce daha geniş gerçek fon örneklemiyle doğrula.
## Yeni Sohbette Devam Etme Kuralı

Yeni bir sohbette projeye devam ederken bu dosya önce okunmalı. Özellikle **Güncel Durum**, **Tamamlananlar**, **aktif fazın taskları** ve **Sıradaki İş** bölümleri esas alınmalı.

> Kural: Her faz tamamlandığında kısa özet, alınan teknik/ürün kararları, tamamlanan tasklar ve sıradaki faz/tasklar burada tutulur.
- Production prediction orchestration için `backend/app/services/prediction.py` eklendi. Mevcut XGBoost tuning -> inference -> Technical Score -> Risk Adjustment -> final signal -> production linear score-to-weight akışı tek bir tekrar kullanılabilir service içinde toplandı.
- Service veritabanına kendisi yazmaz; `PredictionGenerationResult.payload` validated `PredictionHistoryCreate` üretir. Böylece historical smoke scriptlerine otomatik DB yan etkisi eklenmedi.
- `backend/scripts/smoke_test_prediction_persistence_real.py` eklendi. Script canonical universe'den asset'i bulur, gerçek Borsapy/TEFAS verisiyle güncel prediction üretir, `record_prediction()` ile append-only kaydeder ve `get_latest_prediction()` ile read-back doğrular.
- Live/persistence smoke'unda `quality_ok=True, stale_days=0` açıkça servis çağrısına veriliyor; stale/freshness sinyali otomatik tahmin edilmiyor. Bu, mevcut signal contractını sessizce değiştirmemek için bilinçli olarak böyle bırakıldı.
- Prediction service unit coverage eklendi: production target/representation/model family, bounded outputs ve timezone-aware generation timestampı doğrulanıyor.