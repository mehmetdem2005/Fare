# Fare koşusunda karın, omuz ve uzuv deformasyonu

**Sonuç.** Karın çökmesinin iki mekanizması doğrulandı. Karın derisinin ön ve arka uzuvlara birlikte bağlanması, karşıt yönde hareket eden kemikler arasında yüzeyi sıkıştırıyor. Omuz kuşağının gövdeye göre hareketsiz kaldığı koşuda, ön pati geç salınımda aynı uzvun üst kol yüzeyine giriyor. Bu iki mekanizmaya müdahale etmek karın kesişmelerini kaldırdı ve gövde kesişmelerini azalttı. Sağ baldır ve bazı uzuv bağlantılarındaki görsel ve geometrik kusurlar devam ettiği için yeni model kabul edilmedi.

## Girdiler ve görsel inceleme

Çalışma `rig-experiments/real-blender-ci` dalının `0bbcc95048d103e0ae50e6baa81f3186daf5305b` başından türetildi. `deliver/mouse_rig.blend` çalışma başlangıcında ve sonunda `173ca67a372f5c04f27d922ef02f37921bbaf184cff0094976df326b4ec095b6` değerini verdi.

| Girdi | Doğrulanan SHA256 |
| --- | --- |
| Özgün v8 | `984a21447c0217bc8ff91d02f9af1509324aa94dfaf29c543abd3d92f9b12c70` |
| R39 Blender | `bf24c3c00367790af976e5f407cb9c3b20ad11754845bd0eb63d5cbe4042d07b` |
| R41 GLB | `351a9475aeb6142331e4bc296aee957648cb055c7afc9988943a12c559c937d2` |

Actions arşivlerinin doğrudan indirmesi 403 verdi. Yerelde Round 13 ve Round 39 yeniden üretimleri çalıştı ve ayrı hash'lerle kaydedildi. Karşılaştırmada GitHub bağlantısı üzerinden alınan ve yukarıdaki hash'lerle eşleşen özgün arşivler kullanıldı. İlk GitHub render işi `libEGL.so.1` eksikliği nedeniyle durdu. Mesa/EGL bağımlılıkları kurulduktan sonra aynı doğrulanmış girdilerle render ve deney işi tamamlandı. [İlk GitHub çalışması](https://github.com/mehmetdem2005/Fare/actions/runs/44159921484) · [Ağırlık, omuz ve IK deney arşivi](https://github.com/mehmetdem2005/Fare/actions/runs/44163106681/artifacts/14364542024) · [Ayak bileğiyle tam CI tekrar çalışması](https://github.com/mehmetdem2005/Fare/actions/runs/44164189283)

Blender 5.1.2'de orijinalin ham Basis pozu, orijinale bellekte bağlanan v8 eylemi, özgün v8, R39 ve seçili deneyler render edildi. Üç girdide 1–25. karelerin her biri sol, sağ, ön, arka, üst, alt ve ¾ açıdan, ayrıca beş karın, göğüs ve kalça yakın planından kaydedildi. Orijinale bağlanan eylemde 49 kemiğin çözümlenmiş matrisleri v8 ile 25 karede birebir eşleşti. R39 da aynı kemik matrislerini verdi. Blender'ın pencere modunda v8, R39, geniş ağırlık ve son ayak bileği denemesinde zaman çizelgesi oynatıldı ve her birinde 24 farklı koşu karesi örneklendi.

- [24 fps koşu karşılaştırması](anatomy-evidence/sprint-comparison.mp4)
- [Karın](anatomy-evidence/final_belly.jpg) · [Sol omuz ve göğüs](anatomy-evidence/final_chest_left.jpg) · [Sağ kalça ve baldır](anatomy-evidence/final_hip_right.jpg)
- [Sayısal sonuçlar, üçgenler, ağırlıklar ve oynatma](anatomy-evidence/measurements.json)

## Nedenler ve kanıtlar

**Karın ağırlıkları.** 216 numaralı üçgen ön karın tabanında, yaklaşık `(0.088, −0.036, 0.068)` koordinatında. Vertex 2018, 1402 ve 1389 özgün v8'de %36,5–56,7 `thigh.L` ve %43,3–62,5 `upper_arm.L` ağırlığı taşıyor. 812 numaralı üçgen karşı tarafta aynı bölgede. Köşeler 7562, 7390 ve 7772, %37,8–68,9 `thigh.R` ve %29,1–60,0 `upper_arm.R` ağırlığı taşıyor. Bir üçgenin köşeleri farklı karışımlar taşıdığında ağırlık farkının oluşturduğu yer değiştirme, ortak kemik dönüşümünün koruduğu kenar yönünü kısaltabiliyor veya tersine çevirebiliyor. Round 22'deki mekanizma tam mesh üzerinden yeniden kontrol edildi. Dokuz karede hesaplanan lineer skinning ile Blender mesh'i arasındaki en büyük vertex farkı `1.14e−7` model birimiydi.

19 kemikte, üç yerel eksende ve yedi açıyla toplam **3.591** deneme kaydedildi. Her canlı denemede animasyonun aynı başlangıç kemik durumuna dönüldü. Sıfır derece farkı `1e−5` altında kaldı. Ayrı kontrol, yalnız seçilen kemiğin çözümlenmiş skinning matrisini değiştirerek diğer kemikleri ve corrective girdilerini sabit tuttu. Örneğin 14. karede `thigh.L` tek başına +15° X döndüğünde üçgen 216'nın oranı 0,0964'ten 1,1017'ye çıktı. Canlı `hips` +15° X denemesi çok daha geniş bir gövde ve IK tepkisi üretti. Bu açılar nedensellik deneyi için kullanıldı.

| Üçgen | Kare | Vertex kimlikleri | Özgün v8 alan oranı | R39 | Geniş ağırlık |
| --- | ---: | --- | ---: | ---: | ---: |
| 467 | 7 | 671, 774, 731 | 0,3241 | 0,3185 | 0,4038 |
| 351 | 8 | 1317, 703, 980 | 0,3240 | 0,3781 | 0,3649 |
| 434 | 9, 10, 11 | 218, 270, 586 | 0,7352 / 0,8258 / 0,8290 | 0,8065 / 0,7911 / 0,7534 | 0,5972 / 0,6300 / 0,6607 |
| 465 | 9 | 774, 586, 879 | 0,5148 | 0,4923 | 0,8535 |
| 809 | 9 | 7231, 7045, 7390 | 0,5008 | 0,5021 | 0,7392 |
| 216 | 14 | 2018, 1402, 1389 | 0,0964 | 0,0808 | 0,4599 |
| 812 | 17 | 7562, 7390, 7772 | 0,0997 | 0,1238 | 0,4653 |

Alan ve işaret hesabında ham Basis referans alındı. Bu yüzden eski rapordaki IK etkili referansla oranlar doğrudan karşılaştırılamaz. Üçgen 434'ün Round 22'deki yeni ters dönmesi eski reddedilmiş ağırlık varyantına aitti. Burada özgün v8 ve R39'un 9–11 karelerinde aynı işaret negatife geçmedi. Üçgen 465 ise R39'da yarı alanın altına indi.

**Ön uzuv ve salınım.** Sol ve sağ omuz kemiklerinin ebeveynlerine göre açısal değişimi ölçülen 24 karede 0° idi. Üst kolların 1. kareye göre en büyük ebeveyn-göreli farkı 31,95° ve 32,05°, ön kolların 29,15° ve 32,65° idi. Omuz, `spine_05` altında mevcut bir bağlantı sağlıyor. Bunun anatomik merkezini değiştirmeyi gerektiren doğrudan bir anatomik eşleme elde edilmedi. Omuz dönüşüne en çok 4° paylaşım eklenmesi ve pati hedefinin sadece havada alçaltılması, belirli pati–üst kol temaslarını kontrollü biçimde azalttı. Omuz denemesinin 20. karesinde 59 gövde temasının 45'i baskın `hand.R` ve `upper_arm.R` yüzeyleri arasındaydı. Örneğin üçgenler `[8517, 7953, 8637]` ve `[8712, 8591, 8292]`, yaklaşık `(−0.1012, −0.2358, 0.0896)` noktasında kesişiyordu.

**Arka uzuv.** Diz ve baldırın kendi katlanması karın ağırlıklarından ayrıldı. Karın ölçümünde sıfır kesişme veren öne özgü 0,012 salınım denemesinde 53 gövde çifti hâlâ iki tarafta da baskın `shin.R` taşıyordu. 7. karede örnek `[10364,10312,10533]` ile `[10927,10501,10258]` yüzlerinde baldır ağırlığı %47–80 ve uyluk ağırlığı %3,5–46 arasında değişiyordu. 20–24. karelerde ayrı ayak bileği cebi `[9534,9855,9335]` ve `[9558,9440,9561]` tekrar ortaya çıktı. Bu cepte `foot.R` %20–52. Sorunlu köşeler, ağırlık ve kesişme konumu arşivde tutuldu. Arka salınım denemesi uzvu yeniden boyamadan yalnız havadaki hedefi alçalttı. Bazı baldır çiftleri azaldı, 11. karede karına yeni çift eklendi.

**Omurga ve corrective'ler.** Beş segmentin ebeveyne göre en büyük ayrı açısal değişimleri sırasıyla 1,16°, 1,11°, 1,38°, 1,28° ve 0,82°. Boyun 3,70°, kalça 3,08°. Canlı omurga ve kalça kontrolleri uzuv IK zincirleri üzerinden geniş etki yaratıyor. 14. karede 216'nın 0,0964 olan alan oranı tüm düzelticiler kapalıyken 0,0990, Preserve Volume açıkken 0,0943 oldu. Corrective'ler bağımsız zorlanmış etkinleştirme ve sürücülü etkin değerleriyle ölçüldü. Omurganın veya corrective sisteminin tüm kusurların tek nedeni olduğuna dair kanıt bulunmadı.

**Basis ve topoloji.** Karın alt kümesinde ham Basis üzerinde doğrulanmış kesişme yoktu. Part 6 gövde geometrisinde Basis'te üç doğrulanmış kesişme, 1.398 sınır kenarı ve beş nonmanifold kenar vardı. Sınırlar çoğunlukla göz, kulak, pati ve kuyruk bölgelerindeydi. Sınır vertex'leri arasında 0,0005 birime kadar çakışan çift bulunmadı. Alt karındaki poz bağımlı çöküşü genel bir kaynak vertex birleştirmesiyle onarmaya dayanak çıkmadı. Ayrı ayak bileği cebi ise Basis'te zaten kesişiyordu. Vertex 9440 karşı üçgenin düzleminin 0,0000678 birim arkasındaydı. 7. karedeki diz/baldır çifti ham Basis'te kesişmedi, 20. karedeki ayak bileği çifti kesişti. Kontrollü sağ baldır ve ayak dönüşleri iki çiftin farklı hassasiyetlerini gösterdi. Her çift için LBS readback hatası `3e−8` altında kaldı. Deneme kopyasında 9440 numaralı vertex, karşı yüzün normali boyunca 0,00072 birim taşındı. Aynı öteleme mevcut tüm shape key'lere uygulandı. Bağımsız yeniden açılışta yalnızca 9440 numaralı vertex değişti, yüz bağlantıları ve shape key farkları birebir korundu. Bu değişiklik Basis'teki üç kesişmeyi ve 24 karede aynı cepten kaynaklanan 44 kesişmeyi kaldırdı. 0,012 ön salınım denemesine göre yeni gövde kesişmesi oluşmadı. Part 6 kapalı bir hacim oluşturmadığı için güvenilir kapalı hacim değeri ölçülmedi. Karın alanı ve kenar gerinimi ayrı yüzey ölçümleridir.

Anatomik değerlendirmede fare kas-iskelet modelinin eklem yerleşimleri ve dört ayak temas zamanlamasının hıza bağlı değişimi kullanıldı. Omuz hareketine sabit bir biyolojik açı eşiği dayatılmadı. Çalışma dosyasının kemik konumları anatomik referansa geometrik olarak kaydedilmediği için kesin kemik merkezi veya roll onayı verilmedi. [Fare kas-iskelet modeli](https://doi.org/10.1109/access.2021.3133078) · [Fare koşu biçimleri](https://doi.org/10.1016/j.cub.2015.04.005) · [Hıza bağlı uzuv eşgüdümü ve görsel kayıtlar](https://elifesciences.org/articles/73424)

## Müdahaleler ve deney sonuçları

Önce karın bandında uzaktaki uzuv etkisi, mevcut beş omurga kemiğinin konumuna göre gövdeye dağıtıldı. Toplam deform ağırlığı korundu. Sınır geçişi, dar bandın tek yeni ters dönüş kümesi olan 956 numaralı üçgenin köşelerinde ölçülen yanal ağırlık farkı nedeniyle genişletildi. Ardından omuz dönüşü ve pati açıklığı bağımsız olarak denendi. Her değişiklikten önce girdi kopyalandı. Her sonuç ayrı Blender sürecinde açılarak 24 kare ve 25. kare kapanışı ölçüldü.

| Deney | Karın kesişmesi, 24 kare toplamı | Part 6 gövde kesişmesi | Sonuç |
| --- | ---: | ---: | --- |
| Özgün v8 | 192 | 575 | Baz çizgisi |
| R39 | 136 | 519 | 14. karede 27 karın kesişmesi ve görünür kat |
| Dar, yarım ağırlık | 1 | — | Üçgen 956, 15–18. karelerde yeni negatif normal |
| Dar, tam ağırlık | 1 | — | 65 yeni negatif normal ve 0,0070 minimum alan |
| Geniş, yarım ağırlık | 6 | 381 | Yeni çiftler 13. kare `(463,471)`, 20. kare `(944,948)` |
| Geniş ağırlık + Corrective Smooth | 38 | — | 74 yeni negatif normal ve yeni görünür çukurlar |
| Geniş ağırlık + skapular hareket | 0 | 313 | Geç salınımda üst kol ve pati kesişmeleri |
| Omuz + ön patiyi dışa alma | 0 | 268 | Kalan ve yeni gövde kesişmeleri |
| Omuz + ön salınımı 0,008 alçaltma | 0 | 155 | 20. karede 15 gövde kesişmesi |
| Omuz + ön salınımı 0,012 alçaltma | 0 | 124 | 23 yeni gövde çifti ve sağ baldır kusurları |
| Omuz + ön ve arka salınımı 0,012 alçaltma | 1 | 99 | 11. karede yeni karın çifti ve 26 yeni gövde çifti |
| Ön salınım 0,012 + zemin yüksekliği deneyi | 1 | 121 | Kare örneklerinde zemin girişini giderdi, yeni karın çifti kaldı |
| Ön salınım 0,012 + sağ ayak bileği Basis düzeltmesi | 0 | 80 | Kaynak ayak bileği cebi giderildi. Poz bağımlı sağ diz/baldır ve omuz bağlantısı kusurları kaldı. |

Kesişme toplamları kare ve üçgen çifti üzerinden sayıldı. Sıfır toleranslı BVH'den gelen, ortak vertex taşımayan çiftlerin sonlu kenar–üçgen kesişmeleri ayrı doğrulandı. Koplanar temaslar bu kesin tanık sayısına dahil değil. Gövde sütunu Part 6 içindir. Diğer parçalardaki temaslar ve ara karelerin tümünde çarpışma garantisi kapsam dışında kaldı. Geniş geçişte yeni karın ters dönüşü yoktu. Omuz ve 0,012 ön salınım denemesinde incelenen karın minimum alan oranı 0,0141'den 0,1548'e yükseldi. Alt görünümde orta karın katı azaldı. Yan görünümde omuz-koltuk altı kıvrımı ve sağ arka uzuvda deformasyon kaldı.

## Döngü, zemin ve motor

- Özgün v8, R39 ve seçili denemelerde 1. ve 25. kare vertex konumları aynıydı. 0,012 ön salınım denemesi için uç noktalarda 0,01 kare örnekleme ile hesaplanan vertex hız farkı p95 yaklaşık `7,84e−5` model birimi/kare idi.
- `Z=0` zemin varsayımı ve 0,002 yakınlık eşiğiyle v8'de sol ön pati 11–12, sağ ön pati 11–14. karede zemine yakın. Arka patiler döngü birleşimi civarında yere yaklaşıyor. En derin giriş `−0,0024823`. Zemin deneyi bunu tam kare örneklerinde `+0,0002000` civarına çıkardı. Yerinde koşu eylemi için oyun dünyası ilerleme hızı verilmediğinden kaymasız oyun içi temas onaylanmadı.
- R41'in özgün GLB'si Blender 5.1.2'de 49 kemik, 29 morph ve `MouseRig` ile yeniden açıldı. Godot 4.7.2 headless Linux oynatmasında 14. kare düzelticisi `0,89999956`, kalça quaternion döngü farkı `0,00045389` idi. 0,008 ve 0,012 ön salınım denemelerinin ve sağ ayak bileği Basis düzeltmesinin geçici GLB dosyaları da Blender'a geri alındı. Godot bu üç denemede kaynak v8'de bulunan 14 morph, 49 kemik ve 55 animasyon kanalıyla `MouseRig` oynattı. İlk denetim yanlışlıkla 28 morph bekledi. Kaynak v8'deki 14 hedef sayısı doğrulanarak denetim tekrar çalıştırıldı.
- Gerçek Android 11/Mali testi yapılmadı. Görsel ve geometrik kabul tamamlanmadığı için yeni `.blend` veya `.glb` inceleme adayı yayımlanmadı. Deney dosyaları inceleme kanıtı üreten betikler üzerinden yeniden üretilebilir.
