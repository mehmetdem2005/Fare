# Fare rig inceleme sürümü

**Durum: deneysel, anatomik kabul açık.** Sağ diz için pose-space düzeltici, 7–9. karelerde örneklenen iki tanık üçgenin alanlarının %50 üzerinde kalmasını sağladı ve yerel kenar gerilmesini düşürdü. Sağ dizdeki derin kıvrım, omuz ve koltuk altındaki çöküntü ile interleg kesişmeleri hâlâ gözleniyor. Blender ve Godot oynatma sonuçları bu sürümün teknik aktarımını doğruluyor.

[Blender deney dosyası](artifacts/FARE_POSE_REVIEW_UNAPPROVED.blend) · [Godot testinden geçen deney GLB’si](artifacts/FARE_POSE_REVIEW_UNAPPROVED.glb) · [SHA256](SHA256SUMS)

## Girdiler

| Rol | Dosya veya kaynak | SHA256 |
| --- | --- | --- |
| Değişmez kaynak | `deliver/mouse_rig.blend` | `173ca67a372f5c04f27d922ef02f37921bbaf184cff0094976df326b4ec095b6` |
| Animasyon kaynağı ve karşılaştırma | Yerelde yeniden üretilen Round 13 v8 | `80e95538dbdd8e741f5d02e67dadd11eeab686ad5ede099d5340451e76c73418` |
| Tarihî karşılaştırma | Yerelde yeniden üretilen R39 | `856a7c007393dae0bba2d580cc5546370779acbfb3c8e53177812bd92a98995e` |
| Düzelticinin doğrudan ebeveyni | Yeniden üretilen 52 kemikli `SPINE_RIG_EXPERIMENT.blend` | `6cef59138d42ef3ce92b0cbdbc991ee4f9b250316181f382c0cb2e52039f5d38` |

`rig-experiments/anatomical-deformation-repair` uzak dalı `66455846aca95f8095596bd28d57130598910870` üzerindeydi. Yeni `rig-experiments/pose-mode-knee-shoulder` dalı bu revizyondan açıldı. Başlangıçta çalışma ağacı temizdi ve uygulanabilir `AGENTS.md` bulunmadı. Kaynak dosya bu incelemenin başında ve sonunda tablodaki hash’i verdi.

GitHub arşivlerinin indirme sunucusu proxy üzerinden HTTP 403 döndürdü ve doğrudan bağlantı reddedildi. Bu yüzden bu tablodaki v8 ve R39, Blender 5.1.2 ile CI adımlarından yeniden üretildi. Tarihî v8, R39 ve R41’in kesin hash’li kopyaları bu oturumda açılamadı. R41 tarihî sonuçları önceki rapora aittir. [Round 13 iş akışı](../../.github/workflows/fare-round13-phase-ik.yml) · [R39 iş akışı](../../.github/workflows/fare-round39-f14-reference-restore.yml) · [R41 raporu](../ROUND_38_42_GODOT_L3_VERIFICATION_2026-11-17.md)

## Sorun envanteri ve kök neden

| Bölge ve şiddet | Tanık ve sonuç | Mekanizma ve güven |
| --- | --- | --- |
| Sağ diz ve baldır, belirgin keskin kat | 7–9. karelerde `thigh.R` / `shin.R`. Üçgenler `(10364,10312,10533)` ve `(10927,10501,10258)`. Deney ebeveyninde bu ikisi kesişmeden kat oluşuyor. F7’de ikinci üçgenin alan oranı 0,474. | Dinlenme girintisi ve yerel bükülme birlikte etkili. Sprint animasyonu çıkarıldıktan sonra eşdeğer bone matrisleriyle kat yeniden oluştu. Etki için güven yüksek. Kenar akışı ve yüz yerleşiminin katkısı ayrı retopoloji deneyiyle ölçülmedi. |
| Sağ omuz ve koltuk altı, temas bölgesinde görünür çöküntü | 7–9. kareler, `shoulder.R`, `upper_arm.R`, `forearm.R`. Alt-sağ açıdaki koyu oluk manuel eşdeğerde de görünüyor. F9’da yerel yumuşatmanın tohumları ayrı kaydedildi. | Önceki skapular paylaşım ve salınım deneyi distal çakışmaları azaltmıştı. İki yöntem bu yerel oluğu kapatmadı. Sağ üst kol tek eksenine bağlanan korrektif çevre cildinde yeni sıkışma yarattı. Bu düzelticinin reddi için güven yüksek, oluğun özgül anatomik kaynağı için güven orta. |
| Karın, önceki ana kusur büyük ölçüde azaldı | Eski üçgen 216, F14, `(2018,1402,1389)`. Üçgen 812, F17, `(7562,7390,7772)`. Adayda alan oranları sırasıyla 1,003 ve 1,011. F16–20’de kalan interleg çiftleri `64/68`, `64/1002`, `877/881`, `879/881`. | Sentinellerdeki karşıt üst kol/uyluk etkisi geniş geçişle omurgaya taşınmıştı. Bu mekanizma ve iki sentinel için güven yüksek. Kalan çiftlerin gözle görünür yüzey delmesiyle ayrıntılı eşlemesi açık. |
| Sağ ayak bileği, önceki Basis cebi | V9440 ve `(9534,9855,9335)` / `(9558,9440,9561)`. Orijinal Basis’te 3 Part 6 kesişmesi vardı. Adayda armature öncesi 12 örnekte Part 6 tanığı sıfır. | Önceden doğrulanan küçük Basis ve shape key ötelemesi yeniden uygulandı. Bu cebin Basis’e bağlı olduğuna güven yüksek. Zemin teması ayrı sorun. |
| Omurga, bileşik pozlarda aşırı sıkışma | Beş omurga segmenti, `hips` ve `neck`. −15° `flex` pozunda vücut kenar gerilmesi p95 0,337. Yakın silüette göğsün aşağı doğru toplanması görülüyor. | Dağıtılmış kontrol tek eklem bükülmesini paylaştırıyor. Göğüs ve pelvis kontrolleri, sabit IK hedefleriyle birleşince bazı pozlarda yerel sıkışma sürüyor. Bu poz numunesi için güven yüksek, tüm uzuv kombinasyonları için değerlendirme açık. |

Aynı sprint pozunu yeniden kurmak için Blender Pose Mode’da aksiyon ve NLA ayrıldı. Blender’ın çözdüğü matrisler kemiklerin lokal dönüşümlerine çevrildi ve shape key değerleri tutuldu. Ebeveyn ve deneyde 7–9. karelerin en büyük yüzey farkı (4,03 × 10^{-7}) model biriminden küçük. Bu eşleşme görünür kıvrımın klibin zaman çizelgesi dışına taşınabildiğini doğruluyor. Ön ve arka plan pozunun eşlenmesinden sonra yalnız diz sürücüsü ve omurga kontrolleri yeniden etkinleştirildi. F7 sürücü değeri canlı Pose Mode’da 1,0’a ulaştı. +8° omurga fleksiyonu ve karşı ön kolun +12° X dönüşüyle aynı tanık alanları korundu. Turuncu ve mavi kenarlar bilinen altı tanık vertex’in projeksiyonu. [Diz](evidence/knee_contact_sheet.jpg) · [Omuz](evidence/shoulder_contact_sheet.jpg) · [Ayak bileği](evidence/ankle_contact_sheet.jpg) · [Tanık envanteri](evidence/intersection_inventory.json)

Önceki omuz değerlendirmesinde fare kas-iskelet yerleşimi ve yüksek hızlı koşu verisi referans alınmıştı. Bu turda kemik başı ve roll kaydedildi. Deri görüntüsünden eklem merkezi çıkarılmadı ve anatomik referansa üç boyutlu kayıt yapılmadı. [Kas-iskelet modeli](https://doi.org/10.1109/ACCESS.2021.3133078) · [Koşu ve uzuv eşgüdümü](https://elifesciences.org/articles/73424) · [Önceki anatomi raporu](../ANATOMICAL_DEFORMATION_REPORT.md)

## Kontrollü deneyler

| Ölçüm | Interleg çifti | Part 6 çifti | Değerlendirme |
| --- | ---: | ---: | --- |
| Orijinal rig ve yeniden üretilen v8 aksiyonu | 230 | 613 | Orijinal skinning |
| Yeniden üretilen v8 | 192 | 575 | Animasyon referansı |
| Yeniden üretilen R39 | 136 | 519 | Tarihî karşılaştırma |
| Ebeveyn rig ve yeniden üretilen v8 aksiyonu | 10 | 316 | Aynı klip altında rig değişikliğinin etkisi |
| Ebeveyn rig ve türev sprint | 10 | 68 | Doğrudan başlangıç |
| Diz, 7 halka ve 15 Laplace adımı | 10 | 68 | Kıvrım kenarı daha yumuşak. Alan kaybı ve p95 gerilme arttı. Reddedildi. |
| Diz, 12 halka ve 36 Laplace adımı | 10 | 77 | F7–9’da dokuz yeni olay ve alan kaybı. Reddedildi. |
| Omuz, sıkışan dört yüz çevresinde Laplace | 10 | 76 | F9 omuz p95 gerilmesi 0,189 → 0,509. Reddedildi. |
| Diz, 10 halka ve 30 Taubin adımı | 10 | 68 | Diz p95 ve en sıkışan tanığın alanı iyileşti. Deneysel inceleme dosyasına alındı. |

Her satır 1–24. karelerdeki kare-çift olaylarını sayar. 25. kare kapanışa ayrıldı. Aynı çift birden çok karede sayılabilir. BVH adaylarından ortak vertex taşıyanlar ayrı kaydedildi. Sonlu kenar ve üçgen kesişmesi görülen ayrık çiftler tabloya girdi. Koplanar teğet temas, penetrasyon derinliği ve diğer mesh parçaları bu toplamın dışında. Part 6 açık geometri olduğundan kapalı hacim verilmedi. Yeniden üretilen ebeveynde önceki **60 gövde ve 0 interleg** sonucu tekrarlanmadı. Kalan on çift omuz veya diz denemesiyle ortaya çıkmadı. Kurulum bu farkı kesin tarihî girdiyle izole edecek erişime sahip değildi. [CSV](evidence/sprint_frames.csv) · [Basis sonrası ve yarım kare deneyleri](evidence/preview_stages.json.gz)

**Diz değişikliği.** F7 hedef yüzeyi, 10 halka içinde yumuşatmanın daraltma adımını ters geçişle dengeleyen Taubin filtresi ile oluşturuldu. Yüzey farkı ölçülen LBS dönüşümü ters çevrilerek armature öncesi shape key uzayına alındı. `trial_right_knee_pose` değerini `shin.R` yerel X açısı, yumuşak eşikle sürüyor. Tam kareler ve Pose Mode yeniden açılışında kontrol bağımsız çalıştı. F7/F8/F9 diz kenar gerilmesi p95 değerleri sırasıyla 0,352/0,398/0,379 → 0,321/0,361/0,358. Alan oranları ve işaretler ayrı JSON’da. Derin kıvrımın çizgisi tüm üç karede seçiliyor. Bu düzeltici **görsel başarısızlık açıkken deney olarak** tutuldu. [Taubin deneyi](evidence/knee-taubin-trial.json) · [Yeniden açılış](evidence/preview_manual_replay.json)

Yeni preview’da topoloji, UV, malzeme, mevcut kemik hiyerarşisi ve ebeveynin ağırlıkları korundu. Ebeveyndeki ayak bileği Basis düzenlemesi, omuz ve IK aksiyon değişiklikleri, omurga kontrolü ve expression kontrolleri yeniden üretildi. Kaynak Blender aksiyonları saklandı, `Idle_expressions` eklendi. GLB’de iki klip var. Rig’de 19.466 vertex, 52 kemik, 17 morph hedefi, en çok beş deform etkisi ve 671 bağlantılı bileşen var. Ağırlık toplamı 1’den (10^{-4}) üzerinde sapan vertex yoktu. Bıyıklar `part_id` 0 ve 1, pati adaları 2/3 ve 7/8, temel gövdenin bu ölçümdeki üçgenleri 6. [Orijinal bağlama ve kontroller](evidence/original_rig_inventory.json.gz) · [Preview kemik, rest, roll, IK/pole, driver ve aksiyon envanteri](evidence/preview_rig_inventory.json.gz)

Pose Mode’da F7 eşdeğerine eklenen −10° yerel sağ baldır X dönüşünde canlı düzeltici 1,0’da kaldı ve bir tanığın alan oranı 0,348’e indi. Sürüş eğrisine ikinci bir düşüş eşiği koyan deney bu pozu alan oranı 0,566’ya taşıdı. Aynı anda bölge p95 kenar gerilmesi 0,500’den 0,601’e yükseldi. Bu değiş tokuş nedeniyle düşüş eşiği preview’a alınmadı. [Sınırlı sürücü deneyi](evidence/knee-bounded-trial.json) · [Pose Mode karşılaştırması](evidence/bounded_manual_replay.json)

## Pose Mode kullanımı ve test aralığı

- Aksiyon editöründe aktif sprinti ayırın ve NLA’yı kapatın. Koşuya dönmek için `run_sprint_v8_swing_clearance_TRIAL` aksiyonunu yeniden bağlayın. Göğüs ve bıyık örneği `Idle_expressions` aksiyonunda. Koşu 24 fps ve 1–25, idle 24 fps ve 1–49. Son kareler kapanış örneği.
- `Spine controls` koleksiyonundaki `spine_curve` kemiğini seçin. `flex`, `twist`, `side_bend` derece cinsinden sırasıyla lokal X, Y, Z dönüşleri üzerinden omurlara dağıtılır. İnce ayar için `DEF` koleksiyonunda `spine_01`–`spine_05` kemiklerini kullanın. Nötrde üç özel özellik de 0. İzole testlerde `flex` ±15°, burulma ve yana bükülme ±12°, bileşik örnekte 10° eğilme ve 8° burulma kullanıldı. −15° örneği görsel kabulü geçmedi.
- `CTRL` koleksiyonundaki `ik_hand.L/R` ve `ik_foot.L/R` hedeflerini taşıyın. `IK=1` hedef kontrollü, `IK=0` doğrudan FK. FK’de `upper_arm/forearm/hand` ve `thigh/shin/foot` yerel dönüşlerini kullanın. Dört bacakta doğrudan IK kapatıldığında örnek uç farkı yaklaşık 0,02546 model birimi. Geçişten önce pozu elle eşleyin. Otomatik IK/FK eşleme ve pole flip sınırı bu sürümde tamamlanmadı.
- `spine_05` üzerinde `breath` ve `heartbeat` 0–1 aralığında ayrı anahtarlanır. Eğilmiş göğüsle birlikte 0,65/0,5 ve 1/1 örneklendi. Tek kontrol maksimumunda ölçülen yer değiştirmeler nefeste 0,00772 ve nabızda 0,00156 model birimi. Idle demonstrasyonunda iki kontrolün zamanlamaları ayrı.
- `Whisker articulation` koleksiyonundan `whisker_fan.L/R` kemiklerini ayrı döndürün. Örnek klip Z ekseninde +5° ile −2° aralığını kullanır. Kafa ve burunla birleşik pozda sol +6°, sağ −3° örneklendi. Bıyık kökü çarpışması ve uzun süreli titreşim için ayrı nicel kabul açık.
- Sıfırlamak için konum, dönüş ve ölçeği temizleyin. Üç omurga girdisini ve iki göğüs girdisini 0, dört IK değerini 1 yapın. Aksiyon ve NLA ayrıyken tam ağda sıfırlama farkı 0 model birimi ölçüldü. Ölçekle ekstrem yanlış kullanımın güvenli aralığı belirlenmedi.

Bağımsız oturumda 21 kemik, üç eksen ve yedi açıdan 441 FK taraması çalıştı. 30 sahne örneği nötr, çömelme, yükselme, uzanma, ön bacakların yana açılması, dört tek-pati kaldırma, dört ağırlık aktarımı, baş/kuyruk, kalkış ve iniş şekilleri, çapraz kaldırma ve bileşik expression pozlarını içeriyor. Bunlar statik poz testleri. Dinamik yürüyüş, sıçrama, yön değiştirme ve iki yönlü eşlenmiş IK/FK geçişi için kabul açık. **Üretim için kabul edilmiş poz veya animasyon aralığı belirlenemedi.** Kabul için hedef aralıktaki pozlar ve ara zamanlar, yüzey delmesi ve yapay kat açısından geometri testini, yakın plan görsel incelemesini ve oynatmayı birlikte geçmeli. [Poz tablosu ve ölçek dışı olmayan taramalar](evidence/pose_acceptance.json) · [Poz kontak sayfası](evidence/pose_sheet.jpg)

## Blender ve Godot sonucu

Blender 5.1.2 kaydedilen preview’ı yeni süreçte açtı. Kontrol koleksiyonları, pose-space shape key, bağımsız göğüs değerleri, FK taramaları ve kaydedilmiş sprint okundu. Tam kare setleri yedi yönden ve beş bölge yakından clay renderlandı. F8’de orijinal renk dokusuyla da bakıldı. Sağ diz kıvrımı clay ve renkli görünümde seçiliyor. Karın orta tabanı v8’e göre daha düzgün. Omuzun üst yüzeyi akıcı görünüyor, koltuk altının oluğu özellikle alt-sağ açıda belirgin. Normal ve yavaş oynatma karşılaştırmalarında sorun dizin toplandığı 7–9. karelerde zirve yapıyor ve bacak açılınca azalıyor. Blender’da pencere modunda zaman çizelgesi 24 ve 8 fps ayarlarında çalıştırıldı. İkinci canlı denemede her iki hızda da 24 farklı kare örneklendi. [Normal hız](evidence/sprint-comparison.mp4) · [Yavaş](evidence/sprint-slow.mp4) · [Renk dokulu F8](evidence/textured_right_08.png) · [Canlı oynatma örnekleri](evidence/window_playback.json)

Sprintte 1/25 konum kapanışı tam. Uç hız farkı p95 (7,84 × 10^{-5}) model birimi/kare. (Z=0) varsayımında en düşük pati noktası −0,00248 model birimi. Yerinde koşunun oyun ilerleme hızı ve zemin temas eşlemesi tanımlanmadığından kaymasız temas kabulü açık. Gövdenin kesit alanı ve bütün hareket boyunca omur açısal ivmesi bu turda yeniden hesaplanmadı.

GLB’nin Blender’a geri alımında 52 kemik, 17 morph, UV, malzeme ve iki klip okundu. GLB’ye Blender sürücüleri yerine örneklenmiş morph ağırlıkları ve kemik hareketleri yazıldı. Sekiz etkilik export ayarı modelin en çok beş etkisini kapsıyor. Geri alım testi ithal NLA şeridinin 1’den, klibin kaynak glTF zamanının 0’dan başladığını hesaba kattı. 10 örnekte iki yönlü en yakın vertex mesafeleri kaydedildi. Sprintte ileri yönde en kötü p95 (4,1 × 10^{-7}), idle’da (1,18 × 10^{-4}) model birimi. İleri yönde en büyük 0,00246 farkın tanığı, kaynakta hiçbir yüze ait olmayan 7487 numaralı vertex. [Export ve morph örnekleri](evidence/glb_export_reimport.json) · [Yüzey geri alım ölçümü](evidence/mesh_roundtrip.json)

| Godot 4.7.2 Linux headless | Süre | Track | Örneklerde Blender’a göre morph hatası | Kemik döngü kapanışı |
| --- | ---: | ---: | ---: | --- |
| `Sprint` | 1,0 s | 61 | (8,94 × 10^{-8}) | En büyük öteleme (3,18 × 10^{-8}), dönüş 0,00098 rad |
| `Idle_expressions` | 2,0 s | 61 | (2,99 × 10^{-8}) | En büyük öteleme 0, dönüş 0,00069 rad |

Temiz Godot projesi gerçek `AnimationPlayer` ile iki klibi oynatıp örnekleri aradı. `Skeleton3D` 52 kemik, `MeshInstance3D` 17 blendshape bildirdi. Pati kemiklerinin pozları JSON’da. Godot’ta render üzerinden ayak temas şiddeti ve Mali performansı ölçülmedi. Android 11/Mali fiziksel cihaz testi **test edilmedi**. [Godot oynatma verisi](evidence/godot_playback.json)

## Yeniden üretim

Komutları Fare depo kökünden çalıştırın. Yeni çıktı dizini kullanın. Blender sürümü 5.1.2. İsteğe bağlı son argüman v8 girdisi, verilmezse yerel CI zinciri v8’i yeniden üretir.

```bash
bash rig-experiments/reproduce_pose_review.sh /path/to/blender ./fare-pose-rebuild
sha256sum -c rig-experiments/pose-review/SHA256SUMS
```

Deney karşılaştırmalarını yeniden çalıştırmak için aynı ebeveynde `anatomy_pose_corrective_trial.py` betiğini varsayılanla, `--rings 12 --steps 36` ile ve `--region shoulder --frame 9` ile ayrı çıktı dizinlerine çalıştırın. Geniş salınım öncesindeki aksiyonu karşılaştırmak için `anatomy_baseline.py` üzerinde `--action-source` ile v8’i verin. R39 için `round19d_clean_weight_readback.py` ile `--strength 0.170` çıktısını `round39_reference_restore_screen.py` betiğine aday olarak verin. Her deneyin kaynak hash’i kendi ölçüm dosyasına yazılır. Komutlar ve sayım filtreleri betiklerde.

Godot 4.7.2’de yeni bir projeye GLB, `glb_export_reimport.json` ve `anatomy_pose_godot.gd` dosyalarını kopyalayın. Önce `godot --headless --editor --path /path/to/project --import`, sonra `godot --headless --path /path/to/project --script res://anatomy_pose_godot.gd` çalıştırın. İkinci komut gerçek oynatma kontrolünün sonucunu `godot_playback.json` dosyasına kaydeder.

Sonraki onarım deneyi için açık hipotez, renkli diz tanığının ötesine yayılan girintinin eğri boyunca ayrı örneklenmesi ve bu hattın belirli FK/IK yönlerinde kesit alanı ile birlikte ölçülmesi. Böylece daha büyük bir yumuşatma yaması denemeden önce deri katının konumu ile ölçülen deformasyon hedefi eşlenebilir.
