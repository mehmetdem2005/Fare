# FARE — AAA Sonlu Dünya / Ölçek / Nehir / Yüzeye Uyumlu Kamera
## MASTER PLAN • Tasarım sözleşmesi ve ayrı mühendislik iş paketleri

**Durum:** PLAN ONLY / geliştirme kodu değiştirilmeyecek  
**Tarih:** 2026-11-22  
**Motor ve hedef:** Godot 4.7.2 Mobile, Android 11+, fare ölçeğinde yüksek görsel kalite, *sonlu ve elle yönetilen* bir oyun dünyası  
**Prototip dalı:** feat/river-s0-s1-geomorphology  
**Korunacak orijinal dal:** game/godot-mobile-mouse-valley-clean  
**Kapsam:** Nihai haritanın yapılması DEĞİL; nihai haritanın tasarım, fizik, kamera, su, sanat ve optimizasyon sözleşmesinin hazırlanması.

> KARAR-001: Mevcut Fare Vadisi sahnesi nihai harita değildir. Görsel tasarımı beğenilmiyor ve yeniden yaratılacak. Yalnız teknik bench/test sahnesidir. 112 hazır chunk veya sonsuz prosedürel dünya nihai harita hedefi olarak yorumlanamaz.
>
> KARAR-002: Son harita *sonlu*, bilinçli düzenlenmiş, doğal ve fare göz hizasında büyük görünen çevreye sahip olacak. Dünya toptan rastgele prosedürel olarak tasarlanmayacak. Editörde üretilen, elle düzeltilen veya yönetmenlik yapılan veriler çalışma zamanından önce pişirilecek.
>
> KARAR-003: Ölçek denetimi onaylanmadan nehir, kamera, yürüyüş hızı veya çevre boyutları “final” sayılmayacak.
>
> KARAR-004: AAA görünüm hedefi; AAA bütçe, donanım veya otomatik kalite garantisi değildir. Android performans ve sanat kalitesi AYRI kabul kapılarından geçer.
>
> KARAR-005: Bu dosya iş paketlerinin bağımlılıklarını ve doğrulama koşullarını tanımlar. Uygulama, oyun dosyalarını değiştirme, yeni harita imal etme ve APK build bu planın kapsamı dışındadır.
> KARAR-006: Çevrenin devasa hissi gerçek metre ve fare gövde/göz oranlarıyla inşa edilir. Örnek 9 cm fare, insan ve farklı yaşta 5–30m çam referansları bölüm 18'de karşılaştırılır.
> KARAR-007: Nehir genişliği ve iki kıyı birbirini tekrar eden paralel sinüsler olmayacaktır. Kıyı, derinlik, su kotu ve akış; topografik/jeomorfolojik gerekçe ile yerel olarak değişecektir.

---

# 0. GERÇEK KOD BULGULARI — NEDEN ŞİMDİKİ HARİTA YANLIŞ HİSSETTİRİYOR?

Bu bölüm kullanıcı gözlemleriyle koddan doğrulanan olguları ayırır. Aşağıdaki boyutlar Godot dünyasında metre kabul edilmiş değerlerdir; *gerçek GLB fare bedeninin boyu bu incelemede henüz ölçülmedi*.

| ID | Kullanıcı gözlemi | Kaynakta doğrulanan mekanizma | Sonuç / doğrulama açığı |
|---|---|---|---|
| S-01 | Fareye göre çevre ölçeksiz | scripts/mouse_valley.gd: CapsuleShape3D radius=0.24 m, height=0.84 m; player visual y=-0.41 m | Fizik temsilcisi gerçek fareden çok büyük olabilir; GLB AABB ve bind pose ölçülmeden kesin bedensel çakışma söylenemez |
| S-02 | Fare çok hızlı / kamera çok uzak hissettirebilir | WALK_SPEED=3.4 m/s, RUN_SPEED=5.9 m/s; kamera follow_distance=3.4 m | Ölçek, hız, takip mesafesi aynı fiziksel sözleşmeye bağlı değil |
| R-01 | Su birikintisi gibi; derinlik fare boyu kadar | RiverProfile._center_depth merkezde yaklaşık 0.045–1.245 m, WATER_SURFACE 0.26-z*0.0015 | Derinlik tek sinüs-türevi profil ile belirlendiği ve fare kapsülü 0.84 m olduğu için birçok kesit görsel olarak sığ kalır |
| R-02 | Yatak çukuru ve düşey topografya kötü | RiverProfile._shape(): derinlik fade üssü ve sınırlı scour; ground_sample bed_y = water_y-depth | Gerçek bir thalweg, çakıl seti, pool-riffle dizisi, kıyı taşkın sekisi ve çok ölçekli bathymetry katmanı yok |
| R-03 | Nehrin iki kıyısı ve dönüşleri yapay | center_x için sabit 48 m kontrol aralıklı sinüs bileşimi; genişlik iki sinüs bileşimi | Şekil deterministik ama sanat yönetimi yok; doğal görünen kıvrım amaç fonksiyonu tanımlı değil |
| R-04 | Su yüzeyi geometrik | RiverSurfaceBuilder her 40 m chunk'ta 80×18 düzenli satır/kolon ızgarası; vertex yükseltme dalgası sinüs | Jeometri çizgisel örnekleniyor; mikro akıntı, kırılma, engel çevresi ve foam davranışı yeterli görsel zenginliğe sahip değil; üçgen ızgarası tek başına kusur kanıtı değildir |
| R-05 | Akış şekilli, düzenli, tekdüze | RiverFlowField.sample hesap tabanlı tangent/yan hız/engel vorteksi; 32×32 RGBA8 atlas; shader iki sürekli scroll wave_map koordinatı + tek sinüslü küçük vertex dalgası | Desen periyodik algılanabilir; fiziksel doğruluk ve görsel kalite ayrıca cihaz görüntüsüyle incelenmeli |
| T-01 | Arazi rastgele görünüyor | _base_height: iki FastNoiseLite, x'e bağlı mountain_factor; küçük/orta taş ve bitki yine deterministik RNG | Tohumlu rastgele dağıtım var; jeolojik form, habitat ve sanat kompozisyonu için üretim kuralları yetersiz |
| C-01 | Kamera kötü / eğime uyumsuz | _update_camera: focus=player pos +0.23m, 3.4m orbit, tek intersect_ray, lerp(delta*9), look_at; zemin normalini/gelecek eğimi örneklemez | Yüzey boyunca akıllı izleme, çok noktalı engel taraması, çarpışma hacmi, hız yönü, eğim-yüzey kipleri yok |
| M-01 | Hareket araziyle bütünleşmiyor | CharacterBody3D move_and_slide, floor_snap_length 0.12, animasyon değişimi; eğim temelli vücut pozu/kamera sözleşmesi yok | Hareket testini ve kamera testini ayrı, sonra birlikte doğrulamak gerekiyor |

**Kaynak işaretleri:** scripts/mouse_valley.gd 5–13, 260–319, 484–526, 607–625, 671–699, 1374–1453; world/river/river_profile.gd 7–108; world/river/river_surface_builder.gd; world/river/river_flow_field.gd; shaders/river.gdshader; docs/S0_BASELINE.md.

**Henüz bilmediğimiz:** GLB'nin gerçek bind-pose AABB ölçüsü, göz/kafa referans noktası, gerçek fare türü/yaşı, hedef harita alanı, sanat yönetimi, telefon GPU'nun suya harcadığı milisaniye, zemin eğimlerinin fotoğraf/video temelli gerçek kabulü. Bunları rakam uydurarak kapatmayacağız.

---

# 1. BÜTÜN PAKETLERİN ORTAK DEĞİŞMEZLERİ

1. **Dünya koordinatı:** 1 Godot birimi = 1 metre. Ölçek bütünlüğü fare modeli/rig/çarpışma/temas/animasyon/su/bitki/kamera arasında aynı.
2. **Fare birinci referans nesnedir:** Fare gövde uzunluğu L, yerden sırt yüksekliği H, göz yüksekliği E, bacak erişimi P; her ölçü mesh/rig ve oyun tasarımından çıkarılarak ScaleBible dosyasında saklanacak.
3. **Geçişler gerçek:** Derin suya adım atma, yamaçtan iniş, taş tırmanma, kıyıdan suya geçiş ve su altında bakış birbirine geometrik/fiziksel olarak bağlanmalı.
4. **Deterministik, fakat tekdüze değil:** Determinizm test ve cache için; coğrafyanın salt sinüs/noise görünmesi için değil.
5. **Şekil ve render aynı veri kaynağını kullanır:** Suyun görünen sınırı ile collision/bed/foot contact/flow farklı haritalardan bağımsız tahminlerle hesaplanmayacak.
6. **Sanat sahnesi ile performans sahnesi ayrıdır:** Mevcut prototip performans karşılaştırması için sabitlenir. Yeni içerik için kendi harita projesi/paketi kurulur.
7. **Geri alınabilirlik:** Her iş paketi bağımsız feature flag, test sahnesi, rollback planı ve kullanıcı görsel kabulü ile ilerler. Ana oyun dalını bozma.
8. **Sabit bütçe, dinamik kalite:** Mobil donanımda görsel kalite hedefleri FPS/VRAM/p99/ısı şartlarını ihlal ederse gizli kalite düşürme değil, açık ve ölçülen LOD/özellik kararı alınır.

---

# 2. PAKET A — FARENİN GERÇEK ÖLÇEĞİ VE FİZİKSEL ORANLAR [ÖNCELİK P0]

## Amaç
Fareyi bir insan boyunda dolaştırıp nehri su birikintisine dönüştüren göreli ölçek sorununu kökten çözmek. Birbirini yanlış ölçekleyen 3D model, capsule, animasyon, bitki, arazi, su, ses ve kamera ayarlarını aynı referansa bağlamak.

## Gerekli girişler
- Orijinal düzeltilmiş 49 kemikli GLB, bind pose, animasyon örnekleri, collision capsule ve node transform zinciri.
- Tasarlanacak farenin yaklaşık türü/biyolojik fenotipi ve oyunsal stilizasyon kararı.
- Fotoğraf/ref: fare yanında çakıl, toprak, yaprak, dal, mantar, dere taşı, kıyı kesiti. İnsan ölçeği kameraya sokulmayacak.

## Tasarım yöntemi
A1. Blender veya import aracı ile AABB ve temel kemik konumları ölçülür: burun→kuyruk dibi L; yer→sırt H; ayak→göz E; gövde açıklığı W; bacak erişimi P. Kuyruk ayrıca raporlanır. Her sahnede aynı referans nesne ölçüm bloğu çizilir.

A2. Fare biyolojik ölçeği başlangıç *tasarım hipotezi* olarak burun-kuyruk dibi 0.08–0.12 m bandında düşünülür; kesin değer GLB karşılaştırması ve oyun sanat hedefiyle karara bağlanır. Kuyruk bu gövde boyuna karıştırılmaz. Bu bir kesin zooloji iddiası veya zorunlu oynanış değeri değildir.

A3. Tek ortak ScaleBible: visual_scale, collider_radius/height, eye_anchor, ground_clearance, step_height, water probes, camera_distance_min/max, obstacle_passable_width, locomotion stride, walk/run velocity. Ayrık sabitleri elle kopyalama yok.

A4. Hareket hızı m/s yanında L/s (bir saniyede kaç gövde boyu) olarak raporlanır; mevcut 3.4/5.9 m/s değerleri yeni farenin hareket hızı olarak otomatik korunmaz. 0.15–0.6 m/s gibi alternatifler yalnız prototip deney aralığıdır; animasyon ve hissiyatla belirlenir.

A5. Mevcut GLB'yi zorla yeniden export etmek yerine önce root ölçek/pivot/rig hiyerarşisi ile uygulanabilirlik kanıtı; skinning ve 49-bone deformasyon regresyonu korunur. Tüm collision shape'ler non-uniform scale hatalarından arındırılır.

## Bağımsız çıktılar
ScaleBible.md + scale_contract.json/Resource + GLB AABB/kemik raporu + 1:1 fare/çakıl/ot/su referans dioraması + eski/yeni scale overlay screenshot.

## Kabul ölçütleri
- Fare mesh ↔ collider overlap, ayak teması ve göz noktası poz/animasyon boyunca incelenir; havada yürüme veya zemine gömülme olmaz.
- Ölçek tablolarında hiçbir eksik değişken yok; birime aykırı m/mm/cm kullanımı CI'da işaretlenir.
- 49 kemik ve skin bind aynı kalır; eski rig animasyonu yeni fizik ölçeğinde bozulmaz.
- Nehir tasarımına geçmeden görsel ölçü sahnesi kullanıcı tarafından onaylanır.

## Bağımlılık / risk
A bitmeden B, C, D, E, F için mutlak metre ve kamera mesafesi kararı verilmez. Değişiklik oyun fiziğine zincirleme etki eder; önce yalnız diorama/branch üzerinde çalışılır.

---

# 3. PAKET B — SONLU, ELLE TASARLANMIŞ AAA HARİTA VE DOĞAL TOPRAK [P0]

## Amaç
Salt noise'dan çıkan simetrik yamaçlar ve rastgele bitki döşemesi yerine coğrafi neden-sonuç ilişkisi ve oynanış akışı olan tasarlanmış bir açık dünya üretmek. **Sonsuz dünya yok.**

## Yöntem / yaratıcı tasarım sırası
B1. Harita sınırı, oyuncu deneyimi süresi, oynanış rotaları, seyir noktaları, riskli ve sakin alanlar ve hikâyenin gerektirdiği lokasyonlar için 2D layout + atmosfer referans panosu. Coğrafi alan büyüklüğü şimdiden keyfi 1 km²/10 km² olarak kilitlenmez.

B2. Önce insan ölçeğinde değil FARE GÖZÜNDEN 3–5 “hero area” bloklanır: örnek olarak orman zemini, kök altı geçit, nehir kıyısı, derin su kıyısı, taşlı dar geçit. Bunlar taslak adaydır; otomatik olarak final harita kanonu değildir.

B3. Jeomorfoloji katmanları birbirinden ayrılır: makro havza (su nereye akar), orta ölçek eğim/teras/eroyon/birikim (toprak neden burada), mikro ölçek çatlak/çamur/taneler/çöküntüler (fare neye basar). Her katmanın malzeme, collision ve gameplay etkisi ayrı kaydedilir.

B4. Elle çizilmiş spline/heightfield ve gerektiğinde özel Blender mesh: oyulmuş kök altı, dik banket, dar yarık ve mağara *yalnız heightmap ile* modellenmeye zorlanmaz. Sahne tasarımcısı authored masks + lokal procedural gürültü kullanabilir; gürültü yalnız detay üreteci, kompozisyon tasarımcısı değildir.

B5. Her habitat için ekolojik yerleşim: güneş/nem/toprak/substrat/eğim/trafik maskeleri; taş ve çakıl yatakları akıntı/yerçekimi, yosun nem/ışık, çimen açık alan, kök birikim ve eroziyona göre. Saf random konumlandırmanın görsel sonucu final kabul edilmez.

B6. “Hero” foreground zengin, uzak alan makul: fare göz hizasında ön plan çamur, ıslak tortu, minik kökler, taneli taşlar ve ayak izi; uzak alan HLOD/impostor ve atmosferik bağlama. Materyaller yağlı, tekrarlanan veya renkli oyuncak görünümünde olmamalı.

B7. Traversal graph: koşulabilir yüzey / sıçrama / tırmanılabilir kaya / su geçidi / tehlikeli akıntı / dinlenme yüzeyi; render ve collision aynı authored işaretlemeyi kullanır.

## Veri sözleşmesi
WorldMapManifest: map_id/version, bounds, cell_id, biome, height source, mesh groups, LOD, collision proxy, splat masks, lighting probe, stream priority, integrity hash ve world-coordinate origin. Godot Resource veya versioned manifest + offline bake; prosedürel runtime editör olmadığı sürece ana harita geometrisi üretmez.

## Çıktılar
Dünya tasarım brief'i, oynanış/ışık moodboard'u, 2D master layout, 3D grayscale blockout, 3 sabit kamera screenshot'ı, yürüyüş video turu, authored terrain data, görsel altın referanslar.

## Kabul
- Her bölgenin belirgin, açıklanabilir jeolojik/habitat nedeni var; tekrar eden sinüs/taş şablonları görünür değil.
- Her hero-area'da fare ölçeği korundu; 1:1 yakın plan ve geniş açı karşılaştırması onaylandı.
- Rotada gereksiz duvar, rastgele boşluk, görünmez bariyer, collision kayması yok.
- İki farklı göz hizasında (fare göz seviyesi + geliştirme denetim kamerası) içerik kabulü yapılır.

---

# 4. PAKET C — NEHİR YATAĞI, DERİNLİK VE GERÇEK 3D ÇUKUR SİSTEMİ [P0, A ve B SONRASI]

## Amaç
Nehri aynı yüksekliğe göre oyulmuş düz şerit olmaktan çıkarıp kıyıdan kıyıya ve akış boyunca değişen, havzayla tutarlı 3D kanal/bathymetry hâline getirmek.

## Ayrı modeller; aynı veri otoritesi
C1. **Drainage graph:** suyun kaynağı, aşağı yöndeki çıkışı, yan kolları, tekil engeller ve vadi eğimi. Nehir yalnız +Z boyunca uzanan sinusoidal merkez hattına indirgenmez.

C2. **Bank curves:** sol/sağ kıyı **bağımsız ve elle düzenlenebilir**. Kontrollü taşkın terası, aşınmış dış kıyı, çakıllı iç kıyı, göçmüş banket, kök oyuntusu, sığ rampa ve dik düşüş. Her kesitte gameplay güvenli alanları gösterilir.

C3. **Thalweg:** yatağın en derin akış hattı merkez çizgiye sabitlenmez. Dönemeçte dış kıyıya kayabilir; kaya arkasında scour, yatak setinde yükselme, tortu üzerinde sığlaşma olur. Spline kesitlerinin birbiriyle sürekliliği ve eğim sınırları test edilir.

C4. **Section authoring:** her önemli kesit için parametreli profil: su yüzey seviyesi, sol bank kotu, sağ bank kotu, çukur merkezi/derinliği, sığ raf, dış oyulma, riffle taşları, taban malzemesi, çevre eğimi. Geometri haritasına raster/mesh olarak pişirilir.

C5. **Pool / run / riffle / ford:** sığ geçit ile ölümcül/sürükleyici derin bölge oyuncuya hem görünür hem fiziken farklıdır. Ön tasarım kuralı: sığ geçit derinliği fare karın/göğüs seviyesiyle tanımlanır; derin havuz en az birkaç fare yüksekliğini aşar ve bazı bölümlerde çok daha derin olabilir. *Mutlak metre ve eşikler A paketi onayından sonra* sabitlenir.

C6. **Su kütlesi ve zemin bağlantısı:** riverbed terrain render, collision, su yüzeyi, su derinliği probe ve batık kamera aynı bathymetry/surface authority verisini kullanır. Kıyıya yakın sızmalar, su altında havada kalan zemin veya kuru yerde su çizgisi kabul edilmez.

C7. **Doğal detay:** taban oyukları, taş çevresi girdap oyulması, yerel çamur dolgusu, çakıl dilimleri, kök altı boşlukları. Bunlar rastgele tek tip noise değil; akış ve sediment alanından maskelenen mikro varyasyondur.

## Tasarım yöntemleri
- 3D riverbed mesh / signed-distance field / authored bathymetry raster seçeneklerini aynı 3 referans kesitte karşılaştır; gizli performans bedeli nedeniyle tamamen dinamik mesh generation varsayma.
- Offline bake, görünüm/çarpışma proxy LOD ayrımı ve chunk dikişlerini taşıyan global koordinatlar kullan.
- Yükseklik alanı yeterli olmayan dik oyulmalarda özel mesh collision, ayrı yerel dar SDF veya hacimsel geometri.

## Çıktı ve test
RiverAtlas/BedDepthField/WaterLevelField, kesit dizisi, longitudinal elevation profil grafiği, derinlik heatmap'i, ekosistem tortu maskesi, 6 cross-section + x-ray screenshot, Fare suya giriş video turu.

**Kabul:** kıyı su çizgisi geometrik farkı belirlenen tolerans altında; taban ve collision hizalı; en az bir geçit ve bir derin havuz fareye göre inandırıcı; kesitler boyunca ani yapay seviye atlaması yok; tüm bunlar Android'de okunabilir.

---

# 5. PAKET D — NEHRİN DOĞAL AKIŞI, KÖPÜK, SÜRTÜNME VE GÖRSEL DÜZENSİZLİK [P0, C SONRASI]

## Sorun tanımı
Mevcut 32×32 atlas + normal texture örnekleri + iki sabit UV scroll ve sinüs vertex dalgası belirgin periyodik şekiller oluşturabilir. Bunun ne kadarının atlas çözünürlüğü, kayan texture, bank klibi veya ekran pikseli olduğu *video ve GPU profillemesinde* ayrıştırılmalı.

## Dört bağımsız katman
D1. **Makro hidrolik:** su kotu, yerel eğim, kesit alanı, genişlik, ortalama debi ve engel konumları. Debi/süreklilik kısıtına uyan yaklaşık hız alanı; gerekmedikçe telefonda tam CFD çözümü yok. Pool'da yavaş, darlıkta güçlü, sığ çakıl setinde başka türbülans.

D2. **Mezoskopik akıntı:** kayaya yaklaşma dalga deformasyonu, wake, ayrılma, dönüşte dış kıyı baskısı, düşük hızlı geri dönen cep. Su yönü ile köpük yerleşimi aynı akış haritasından türetilir. Rastgele yüksek genlikli ters akış üretilemez.

D3. **Mikro yüzey:** farklı uzamsal ve zamansal ölçeklerde advect edilen normal/roughness; fazları, hızları ve frekansları birbirinden bağımsız. Sürekli tekrar eden simetrik dalga şeritlerini önlemek için non-periodic varyasyon ve ölçülü spektral kontrol. Kıyı ve sığ set kenarında yüzey taşla temas eder.

D4. **Köpük/akıntı izi:** köpük yalnız gösteriş amaçlı beyaz şerit değil; kaya çarpışması, türbülans, keskin hız gradyanı, hava kabarcığı ve kıyı birleşmesinden doğar; zamanla kırılır, taşınır, seyrelir. Kısa ömürlü mesh/atlas/pool sistemleri bütçelidir.

## Uygulama kararı
- Önce **C yatağına bağlı CPU/Offline flow field**. Sonra aynı alanın fare kuvvetleri/akış yönü ve shader için türetilmiş sürümleri.
- Akış atlası çözünürlüğü, örnekleme filtresi, seam koruması, kıyı bitiş kenarı ve LOD uzaklığı A/B deneyle seçilir; 32×32 bugün vardır ama final zorunluluğu değildir.
- Suyun shader'ı FULL/MOBILE/FAST içerik olarak kontrollü; yüksek mobil shader'ın ekran/depth kopyası maliyetini mali cihazda ölçmeden tüm haritaya uygulama.
- Suda yoğunluk değil *okunabilirlik*: belirli sakin bölgeler, belli dramatik çalkantılı kesimler; her yerde köpük ve hareket yasak.

## Çıktı
FlowField vNext + flow arrow debug overlay + surface motion overlay + obstacle wake test + foam lifetime curves + water material A/B video/görüntü seti; 3 kalite için GPU süre karşılaştırması.

## Kabul
- Nehir 30–60s sabit kamera videosunda paralel tekrarlayan bantlar/ızgara/ayna periyodu belli etmez.
- Yüzeyde hareket eden köpük/organik parçalar akış yönüyle aynı nedenselliğe bağlıdır; sığ ve derin kesitler farklı görünür.
- Fareye uygulanan akıntı ile görünür yön aynı; belirgin duvar geçişi/chunk seam/UV kopması yok.
- Su %20/%50/%80 ekran alanı A/B GPU süresi raporlanır; görsel kalite maliyeti saklanmaz.

---

# 6. PAKET E — FAREYE GÖRE AKILLI, YÜZEY TAKİPLİ KAMERA [P0, A+C İLE PARALEL GELİŞİR]

## Sorunun kökü
Mevcut kamera tek odak offset'i (+0.23 m), 3.4 m takip mesafesi, tek ray ile çarpışma ve basit lerp/tek look_at kullanıyor. Fare göz yüksekliği, yüzey eğimi, aşağı inen zemin, kaya üstü, su durumu ve karakterin gelecekte izleyeceği yön hesaba katılmıyor.

## Modüler kamera mimarisi
E1. **Target tracker:** kafa/gövde riglerinden türetilmiş EyeAnchor/ChestAnchor/GroundAnchor; yerdeki fiziksel konum ile animasyonda oynayan kafa kemiği kontrollü karıştırılır. Kameranın piksel piksel titremesi için doğrudan bone konumunu aynen takip etmeyeceğiz.

E2. **Ground probe:** ayak altında + ileride + sol/sağ çoklu güvenli physics örneklemesi. Zemin yüksekliği, normal, eğim açısı, basamak yönü, uçurum/kopuk yüzey ve destek güvenini döndürür. Oyuncunun ayağı havadaysa “önceki güvenilir normal” kısa bir süre korunur.

E3. **Surface motion filter:** hedef yüksekliğine yay ile/critically-damped benzeri kontrollü yumuşatma; düz yerde sakin, dik inişte zemin görünümü koruyan daha hızlı yanıt, basamaklarda ani sıçramasız. Roll/yaw/pitch sahaya göre ayrı sınırlar; kameranın ufku sürekli eğrilmez.

E4. **Look-ahead:** karakter yatay hızına, ivmesine ve hareket niyetine göre biraz ileriye bakar. Bekleme/koşma/geri geri gitme/uçurum/nehir girişinde farklı; kamera yönünü rastgele çekmez, kullanıcı sürükleme hareketi önceliklidir.

E5. **Collision volume:** tek ray yerine küçük hacimli shape cast veya SpringArm3D mantığında güvenli temas; duvar/taş/büyük yaprak/yeraltı tüneli. Kamera mesafesi daralabilir, fakat oyuncuya gizlenmeyecek ve duvarın içine girip patlamayacak. Burun kesilmesi için near plane/geometry fade kontrollü.

E6. **Occlusion:** fare perdeleyen çimen/yapraklar sınırlı fademask/occluder ayarıyla çözülür; her bir yaprağa pahalı transparan shader vermek zorunlu değil. Pahalı Mobile decal/GPU overdraw tasarıma otomatik eklenmez.

E7. **Mode state machine:** WALK, RUN, SLOPE_UP, SLOPE_DOWN, CLIMB, EDGE/CLIFF, JUMP/FALL, SHALLOW_WATER, SWIM, SUBMERGED, TUNNEL. Her mod kendi pivot, zoom, field-of-view, damping ve pitch limit profilini kullanır. Kamera geçişleri yumuşak/histerezisli.

E8. **Update order:** zemin örneklemesi ve karakterin fizik durumu ile render interpolasyon sırası açıkça tanımlanır; farklı framerate'te kamera titreme test edilir. Godot SpringArm3D doğrudan kullanmak zorunlu değil; tanımlı collision hacmi+öngörü+stabilite gereksinimi onun tek başına karşıladığından daha geniş.

## İlk prototip ayarları — kesin değil
- Kamera mesafesi metre yerine L gövde boyu cinsinden ayarlanacak; ilk deney 1.5–4 L, tünelde daha yakın, seyir kamerada daha uzak.
- Göz/kafa/focus mesafesi E/H üzerinden; şu andaki 3.4 m ve +0.23 m dogma değil.
- FOV 55–70° yalnız kıyas aralığı; görüş, mobil okunabilirlik ve clip güvenliği ayrıca test edilir.
- Yamaç eğimine göre kameranın otomatik pitch/height etkisi kontrollü; otomatik kamera oyuncunun kontrolüyle savaşmamalı.

## Bağımsız test ve hata matrisi
- Düz zemin 20s bekleme: kamera jitter, “nefes alma”, durduk yerde yaw yok.
- 15° / 30° / 45° yamaç: gereksiz oyuncu kaybı, ufuk taşması yok.
- Dar kök tüneli / arka duvar / kaya dibine sıkışma: near clip, false collision, ani zoom yok.
- 0.2–1.0 fare boyu yüksekliğinde taşlar: fare ve kamera teması anlaşılır.
- Koşudan durma, tam tur hızlı dokunma, geri gitme, kamera manual drag, ani uçurum: easing ve kontrol önceliği tutarlı.
- Suya giriş / dalış / baş çıkış: yüzeyde 30 fps'te jitter/efekt zıplaması yok; su altında kamera duvarın içine gitmez.
- 30/45/60 FPS ve FPS düşüşü simülasyonu: jitter/lag ölçülür.

## Çıktı ve kabul
CameraRig node hiyerarşisi taslağı, GroundProbe contract, camera profiles, 10 otomatik patika testi, yavaş çekim 1:1 A/B görüntüleri, varsayılan + erişilebilirlik manuel kamera ayarı. Kullanıcı onayı olmadan “mükemmel kamera” denmez.

---

# 7. PAKET F — FARE LOKOMOSYONU, EĞİME/YÜZEYE UYUM VE YÜZME [P1, A+E BAĞIMLI]

F1. Animasyon koşulları: walk/run/idle/sprint turn/ascending/descending/sliding/jump/landing/climb/wade/swim; aradaki blend/hysteresis süreleri, kök referans ve pelvis/omuz dengesi.

F2. Fizik collider ile mesh ayak uçları arasındaki ayrımı kapat: çoklu ayak zemin probe, gövde yumuşak tilt, pelvis vertical offset, kafa ve kuyruk ikincil hareket. Animasyon üstüne global tüm rig döndürmek yerine yerel ikincil katman.

F3. Hareket vektörleri yüzey tangent plane'e projekte edilir; izinli eğim sınırı ve taşıma fiziği tanımlanır. Suda ayak yer basma/serbest yüzme ayrılır. Kinematik sürüklenme ile görünür akış ve shader aynı kaynağı paylaşır.

F4. Koşma hızını su/çamur/kaya pürüzü etkiler; fiziksel ses/footprint/sediment ve kamera tepkileri yüzey türünden üretilir.

F5. Ayak/karın gömülmesi, false “floor”, köşe takılması, sarsıcı root snap, 49 bone deformasyonu ve havada yürüme regresyonu.

Çıktı: locomotion parameter profiles ve hareket test arenası; kamera bağımsız hareket testinden sonra kamera ile birlikte test.

---

# 8. PAKET G — SONLU HARİTA İÇİN PİŞİRİLMİŞ VERİ / CHUNK / CACHE / BELLEK [P0 TEKNİK ALTYAPI]

G1. Sonlu MapManifest, sabit dünya sınırları ve tasarımcı kontrollü girişler. Chunk sayısı harita büyüklüğü, telefon sınıfı ve görünürlük testine göre; 25 aktif chunk ve 40m hücre mevcut prototip değeridir, final şablonu değildir.

G2. Offline terrain/river/texture/vegetation/collision bake; mümkün olduğunda zaten hazır kaynak yükle. Runtime worker sadece dinamik/senaryo verisi ve gerçekten gerekli hesaplar için; “sonsuz procedural streaming” odak değil.

G3. Veri ve sunum ayrı: TerrainSurfaceData/WaterBodyData/FlowFieldData/CollisionProxyData/BiomeMasks ve per-cell resource listeleri. CPU hazırlık, main-thread commit, GPU visibility, collider readiness ve gameplay readiness ayrı durumlardır.

G4. Quality/HLOD bütçesi: ön plan gerçek geometri, orta mesafe birleşik mesh/meshlet benzeri uygun Godot çözümü, uzak plan impostor/occlusion, materyal varyasyonu/texture atlas. Ucuz görünüm uğruna bütün taşları aynı mesh, aynı renk ve aynı ölçek yapma.

G5. Cache bütünlüğü: version, map build id, terrain/river/rig schema, checksum, sahne hash; kullanıcı cache'i harita güncellemesiyle yanlış eşleşmesin. Kaynakların disk kopyaları yerine paketlenmiş prebake tercih edilebilir.

G6. RAM/VRAM/PSS ölçümü: cihazdaki gerçek bellek ve termal izleme; renderer reported memory = gerçek tüm VRAM değil. Art asset budget kamera yakınlığı ve piksel maliyetine bağlı.

G7. Geliştirme sahnesi eski prototipten bağımsız: src world provider arayüzü, fallback branch; mevcut procedural height generator final haritaya otomatik taşınmaz.

Çıktılar: MapManifest schema, asset inventory, LOD atlas, bake pipeline, asset test script, streaming timeline, device performance report, migration plan.

---

# 9. PAKET H — AAA GÖRSEL SANAT VE ÇEVRE SİNEMATOGRAFİSİ [P1, A+B+C+D SONRASI]

H1. Art direction: gerçekçi orman zemini, mikro ölçek, doğal ıslaklık/çamur/taş/çürük yaprak, foto-gerçekçi malzeme ilişkileri ve kontrollü atmosfer. İnsan gözüne değil fare kamerasına göre sahne oranı.

H2. Fotogrametri/scan veya yüksek poligon kaynaktan mobil LOD + baked AO/normal/roughness. Satın alma/telif lisansları ayrı envanter. Gerçek tarama dosyası ağırsa doğrudan telefona kopyalama yok.

H3. Aydınlatma: sabah/öğle/akşam her bölüm için sahne niyeti; çamurun ıslaklığı ile specular değişimi fiziksel nedene dayanmalı. Gölgeler tek büyük HDR/blur sahtekârlığına dönüşmemeli.

H4. Kamerayla ortak kompozisyon: fareyi görüntüden kaybetmeyecek silüet, gerçekçi odak/kontrast, yeterli navigasyon okunabilirliği. Göz hizasına yakın büyük yaprak/taşlar rastgele ekranı kapatmamalı.

H5. Materyal kareleri: su yüzeyi, su altı yatak, nemli kıyı, kuru toprak, kaya ve canlı bitki yakın/orta/uzak uzaklıklarda kıyas. PBR “var” demek yeterli değil, cihaz ekranında görsel kabul gerekir.

H6. Hedef görüntü seti: 3 hero konum × 3 ışık hâli × 3 kamera mesafesi × 2 kalite = 54 referans görüntü. Nicel performans olmadan görsel kabul sonlanmaz.

---

# 10. PAKET I — DOĞRU ÖLÇÜM, FPS KARARLILIĞI VE TEST SÖZLEŞMESİ [P0, TÜM PAKETLERLE PARALEL]

## Mevcut S9 eksikleri
- S9ChunkTrace kapalı 256 iş ring'i, parent/child/exclusive süre, GPU timestamp ve gerçek frame bağlantısı içermiyor. Kullanılmayan sahne aşamaları “0ms” görülebilir; etkisiz iş yüzdeliklerini çarpıtabilir.
- _process(delta) raporu ağır ana-thread duraklamasını kapatabilir; wall_gap_max arka plana gidişte 40+s olabilir. İkisi aynı ölçü değil.
- Fixed scene ölçümü ile sahne açılırken kaydedilen toplam chunk jobs aynı JSON içinde durabilir; test dönemlerini açıkça ayır.
- Ekrandaki draw_calls_reported renderer toplam maliyeti veya shader fragment zamanının tek başına kanıtı değildir.

## Zorunlu yeni ölçüm düzeyi
I1. Frame/event trace: frame id, monotonic start/end, source context, mode (boot/fixed/move/swim/assetload), job id, chunk id, parent id, exclusive CPU, GPU frame/timer (destek varsa), bytes, reason ve scheduling state.

I2. Deney protokolü: cihaz+build SHA+quality+screen scale+camera pose+aynı rota+ısınma süresi+oturum başlangıcı+cache soğuk/sıcak bilgileri JSON'da saklanır. A/B'de tek değişken değiştirilir.

I3. CPU/GPU ayrımı: fixed scene A/B, framebuffer resolution sweep, su ekran yüzdesi sweep, effect toggles, shader variants; Android GPU profiler/Perfetto/AGI mümkünse. Gerekli cihaz verisi yoksa “GPU-bound” iddiası yapılmaz.

I4. Kamera kalite: düşük FPS'te p95 ve p99, camera-to-actor offset jitter ve ground normal discontinuity ölçümleri. Frame ortalaması tek başına başarı değildir.

I5. Termal: 15 ve 30 dakika, soğuk başlangıç ve ısınmış durum; CPU task sayısı, FPS p95/p99, RAM/PSS, GPU, pil/ısı bağlamı. Testte uygulamanın arka plan duraklaması ayrı işaretlenir.

I6. Yeni kamera ve yeni nehir yakın plan görsel acceptance: user visual sign-off bağımsızdır; otomatik test “AAA” etiketi veremez.

## İlk teklif performans eşiği; nihai onay değil
- Referans Android 11 cihazında Akıcı mod: hedef 30 FPS kararlı; p95 kare süresi <=33.3ms ve p99 <=50ms deneysel kabul eşiği. Bu hedef henüz ölçülerek doğrulanmadı ve cihaz sınırıyla revize edilebilir.
- “Büyük hitch yok” sadece avg FPS ile değil; >100ms frame sayısı/rotaya göre p99, collision ve kamera jitter ile karar verilir.
- Mesafe değişimine göre sabit frame ve hareketli kamera arasında shader CPU/GPU yükleri ayrıca karşılaştırılır.
- RAM/VRAM ve termal bütçeler *gerçek telefon verisinden* seçilir; mevcut renderer_memory gibi kısmi ölçümden GPU sınırı uydurulmaz.

## Hipotez çizelgesi
- H01: Ölçek değişince nehir “birikinti” hissi azalıyorsa önce estetik/fizik oranı etkisi var; raw depth de ayrıca değiştirilmeli.
- H02: Aynı sahnede çözünürlük düşürmek p95'i düşürüyorsa piksel/GPU bileşeni güçlü olabilir; tek başına kanıt değil.
- H03: Hareketli rotada frame spikes yalnız asset geçişleriyle eşleşiyorsa streaming/main commit maliyeti güçlü; sabit-sahne render sorunu ayrı.
- H04: Kamera jitter oyuncu dururken de görünüyorsa update-order/lerp/collision probeleri incelenir; FPS değişkenliğiyle birlikte test edilir.
- H05: Akış şeritleri camera sabitken periyodik tekrar ediyorsa visual advection/atlas/layering kaynaklarını tek tek bypass A/B.

---

# 11. PAKETLER ARASI ARAYÜZ SÖZLEŞMESİ

| Üreten | API/veri | Tüketen | Onay öncesi yasak |
|---|---|---|---|
| A ölçek | ScaleBible, E/H/L/P, PhysicsEnvelope | B,C,D,E,F | Kendi başına gizli ölçek çarpanı |
| B harita | AuthoredTerrain + biome + traversal masks | C,E,F,G,H | Salt RNG'den nihai geometri |
| C nehir yatağı | BedHeight, WaterLevel, WaterDepth, ShoreSDF, obstacle geometry | D,F,G,H | Shader/physics'in bağımsız derinlik tahmini |
| D akıntı | FlowVelocity, turbulence, foam, danger class | F,H | Hareket fiziğiyle ters düşen shader yönü |
| E kamera | target, surface normal, occlusion state, camera mode | F,H | Tek düz ray ile uçurum kamerayı kalıcı gizleme |
| F hareket | foot contact, posture, locomotion, state | E,H | Rig transformuna kalıcı hasar |
| G streaming | cell assets, collision readiness, visibility, budget | B–I | Kollizyon yokken chunk “hazır” ilanı |
| I ölçüm | reproducible trace, video, screenshots, device metadata | Tüm paketler | CI pass = Android kalite kabulü demek |

---

# 12. ÜRETİM SIRASI — GERÇEK BAĞIMLILIKLAR

| Etap | Öncelik | İş | Durma/ilerleme kapısı |
|---|---|---|---|
| 00 | P0 | Mevcut prototipi sabitle, build SHA ve referans görüntü/özelliklerini kaydet | Eski test APK'sı ve 49-bone geri dönüş var |
| 01 | P0 | **A Ölçek sözleşmesi** + ölçü dioraması | Fare, capsule, göz, speed, çevre 1:1 onay |
| 02 | P0 | **B Sonlu harita art/layout blockout** + topografya | Kullanıcı görsel yönü onaylıyor; henüz PBR final değil |
| 03 | P0 | **C 3D nehir yatağı ve bathymetry** | Gerçekçi derinlik; kesit/geometri/collision/shoreline kabul |
| 04 | P0 | **E yüzey takipli kamera prototipi** bağımsız test sahnesi | Eğim/engel/koşma/yüzme kamera hareketi kullanıcı onayı |
| 05 | P0 | **D hidrolik + yüzey akışı** C üzerinde | Flow/foam/wetness/physics tutarlı; geometrik görünüm yok |
| 06 | P1 | **F hareket, tırmanma, yüzme, rig etkileşimi** | 49-bone ve kapsül/zemin temas regresyonları |
| 07 | P0/P1 | **G offline asset bake + sonlu chunk streaming + cache** | Ayrı collision/data/publish kabul, hitch ölçümü |
| 08 | P1 | **H materyal/ışık/ekosistem/hero çevre** | Görsel referanslar + GPU gerçek cihaz kabul |
| 09 | P0 | **I Android profiling, termal ve alan testi** her etapta tekrarlı | p95/p99/ısı/bellek raporu + kullanıcı görsel kabulü |
| 10 | Karar | Final harita entegrasyon/adım adım içerik yayılımı | Tüm kırmızı testler giderildi; bilinmeyenler risk olarak açık |

**Önemli:** “Kamera için C bitsin” beklenmez; A ardından ayrı eğim/engel test dioramasında E geliştirilebilir. Gerçek su-kamera entegrasyonu C+D+F sonrasında test edilir. “Haritayı önce bütünüyle çiz sonra test” yaklaşımı reddedilir: küçük hero dilimi → teknik/görsel onay → diğer alanlar.

---

# 13. TEST SAHNELERİ VE VERİ TESLİMİ (HER PAKETE ZORUNLU)

- ScaleLab: 49-bone fare, cetvel, çakıl/ot/taş, su/zemin, ölçüm grafiği.
- TerrainLab: düz, 15/30/45° eğimler, farklı yüzeyler, kök altı, dikey kesit, collision overlay.
- RiverBathymetryLab: derin havuz + sığ geçit + riffle + kıyı çökmesi + engelli dış kıyı; üstten, kesit ve fare kamerasından kayıt.
- FlowLab: vektör alanı, foam, wake ve sualtı görüşü, frozen/animated shader varyantları, 30/60 saniyelik videolar.
- CameraLab: yürüyüş, sprint, dönüş, eğim, uçurum, köprü altı, tünel, suya dalış, yüze çıkış; position/normal/pitch trace.
- AssetStreamingLab: 25 eski chunk referansına bağımlı olmayan sonlu hücre veri seti, cold/warm ve fallbacks.
- DeviceBench: aynı ekran yüzdesi ve kamera pozu, sabit/hareketli/su yakın plan, GPU/CPU/p95/p99/termal.

Her teslimde bulunacak: değişen dosyalar, geri alma referansı, eski/yeni video/screenshot, QA matrisi, ölçüm cihazı/build SHA, tam başarı ve açık sorunlar. “Tamam” = kod yazıldı değil; test + görsel kabul + cihaz ölçümü.

---

# 14. KABUL EDİLMEYECEK HIZLI ÇÖZÜMLER

- Fareyi yalnızca görünürde küçültüp capsule, hız, swim depth ve kamera ofsetini aynı bırakmak.
- Nehri tek sinüsün genliğini artırarak “daha derin” saymak.
- Eğriye daha çok vertex ekleyip hâlâ düzenli/tekrarlayan köpük akışını doğal saymak.
- Renderer yükünü düşürmek adına tüm nehir fiziğini düz mavi transparan çizgiye dönüştürmek.
- Fareni her eğimde kameranın ortasına zorla sabitleyip dünyayı sallamak.
- Ayak konumunu yalnızca shader'da oynatıp gerçek collider/gait uyumsuzluğunu görmezden gelmek.
- Çekici görünüyor diye rastgele orman/taş/çukur paketlerini nihai harita saymak.
- Sonsuz chunk üretimine yeni bütçe ayırmak; sonlu dünya ve offline bake varken gereksiz.
- CI başardı diyerek Mali GPU/Vulkan ekran görüntüsü ve gerçek oyuncu kontrolünü atlamak.
- Eski 49-bone orijinal GLB/UV/rig ve güvenilir test dalı üzerine geri dönüşsüz yazmak.

---

# 15. GEREKEN ARAŞTIRMA / KARARLAR — HALA AÇIK

| Karar | Hemen gerekiyor mu? | Veri toplanmadan hüküm verilmeyecek konu |
|---|---|---|
| Farenin mesh AABB / cinsi / hedef gövde uzunluğu | **A öncesi zorunlu** | Kamera gövde oranı, capsule, swim threshold |
| Harita büyüklüğü / hikâye rotaları / biyomlar | B blockout öncesi | kaç cell, kaç derin nehir kesiti |
| Kamera duygu tonu | E visual sign-off | yakın sinematik / daha okunabilir çevre vs |
| Nehir akış rejimi | C/D öncesi | dere mi güçlü nehir mi, taşkın/akış tedirginliği |
| Sanat referansları | B/H öncesi | gerçek foto referansı ve kalite çıtası |
| Mali GPU / telefon gerçek profili | G/H/I kabulünde zorunlu | shader fill-rate ve kalite bütçesi |
| Sonraki haritanın üretim aracı | B prototipinde | Blender terrain sculpt / Godot heightmap / hibrit |
| Hedef FPS sınıfları | cihaz testinden sonra | Low / Balanced / High kalite eşikleri |

---

# 16. UYGULAMA İÇİN GÖREV DOSYASI ŞABLONU (HER BAĞIMSIZ ETAP)

Her paket uygulandığında aşağıdaki bilgiler ayrı teknik uygulama dosyasında tutulacak:

- ID / hedef / kapsam dışı öğeler / hangi user itirazını çözüyor?
- Girdiler ve gerçek model/oyun ölçümleri.
- İki veya daha fazla alternatif tasarım, neden seçilen yöntem.
- Değiştirilecek dosyalar, yaratılacak Resource/Scene API, veri sahipliği.
- Kaynak/feature flag/rollback ve orijinal 49-bone güvenliği.
- Unit/scene/Android acceptance testleri + sahne videoları.
- Başarılı olduktan sonra kullanıcı tarafından görsel ve oynanış kabulü.
- Başarısız bulgular/denemeler için açık test geçmişi, sonraki tur planı.

**İlk gerçek üretim görevi:** A — ölçü kontratı ve ScaleLab. A onaylanmadan şu anki nehir derinlikleri veya kamera sabitleri yeni haritaya kopyalanmayacak.

---

# 17. TEKNİK DAYANAK VE BAĞLANTILAR

- GitHub proje kaynakları: https://github.com/mehmetdem2005/Fare/tree/feat/river-s0-s1-geomorphology
- Mevcut fare/camera/terrain: scripts/mouse_valley.gd
- RiverProfile, river surface builder, flow_field ve shader: world/river/ + shaders/river.gdshader
- Mevcut kaynak ve test sözleşmesi: docs/S0_BASELINE.md, docs/RIVER_ROADMAP.md
- Godot üçüncü şahıs SpringArm3D tanımı: https://docs.godotengine.org/en/stable/tutorials/3d/spring_arm.html
- Godot fizik raycast ve query güvenliği: https://docs.godotengine.org/en/stable/tutorials/physics/ray-casting.html
- Godot Mobile/Forward+ decals sınırlamaları: https://docs.godotengine.org/en/stable/tutorials/3d/using_decals.html

**Sürümleme:** Bu dosyada yalnız planlama değişikliği yapılabilir; implementation commits, APK üretimi ve sahne değişimleri ayrı onay/çalışma etaplarıdır. Kullanıcının gördüğü gerçek eskiz/oynanış kabulü, shader derlenmesiyle eşdeğer değildir.

---

# 18. DEVASA DÜNYA VE DOĞAL DEĞİŞKEN NEHİR — ÖLÇEK REFERANSI GENİŞLETMESİ (2026-11-22)

## 18.1. Zorunlu tasarım ilkeleri

- Final dünya **sonlu** olacak; mevcut harita yalnız teknik prototip. Yeni harita rastgele procedural bir vadiyi büyütmek yerine, doğal coğrafyası ve erişim rotaları elle tasarlanmış bir alan.
- Dünya fare için **gerçekten devasa** hissettirmeli. İnsanların gördüğü sıradan bir ağaç, kaya, kütük, çukur veya nehir fareye göre farklı bir coğrafyadır. Bu farkı sahte global ölçek çarpanı değil **gerçek fiziksel oran** yaratacak.
- Her obje tek kaynaktan belirlenen gerçek metreyle gelir. Fare, collision, rig, gövde/göz yüksekliği, kamera, nehir derinliği ve su fiziği hep aynı metre dünyasındadır.
- Çamların **yükseklikleri birbirinden farklı** olmalı. Kullanıcının 3–5 insan boyu örneği geçerli bir başlangıç referansıdır; yetişkin bazı çamların bundan çok daha uzun olabileceği de tasarımda açıkça görülecek.
- Nehir **cetvelle çizilmiş iki paralel kıyı** gibi olmayacak. Sol ve sağ kıyı, ıslak su genişliği, taşkın yatağı, havuz derinliği ve akıntı yer yer ve gerekçeli şekilde değişir. Tekrarlanan tek frekanslı sinus genişliği, aynı aralıklarla kaya ve eşit çapraz kesit yasak.
- Kamera ağaçların bütününü aynı kareye sığdırmak uğruna otomatik olarak insan boyuna yükselmez. Düşük fare gözünün doğal yarattığı muazzam büyüklük hissi korunur. Oynanış güvenliği ve görünürlük testleri ayrı yapılır.
- **Bu sayfada sunulan tüm metre aralıkları prototip ölçüm örneğidir, final harita ölçüsü değildir.** Gerçek 49-bone GLB ölçülmeden ve fare türü seçilmeden sabitleme yapılmaz.

## 18.2. Gerçek dünya ölçeğine dayanan örnek hesap — kaç fare boyu?

Kaynaklar: Mammal Society ev faresinin baş+gövde uzunluğunu 70–90 mm olarak verir; USDA Forest Service olgun sarıçam boyunu sıkça 15–30 m aralığında bildirir. Bu, Fare Martin'in türü veya final ağacı seçildi demek değildir. Düşünme örneği olarak 9 cm farenin **kuyruk hariç gövdesi** L = 0.09 m, farenin varsayımsal göz yüksekliği E = 0.035 m, örnek insan boyu H = 1.70 m seçilir. Göz yüksekliği **model ölçümü değildir**.

| Referans | Varsayımsal fiziksel boyut | 9 cm gövdeye göre oran | Fare gözünden algı görevi |
|---|---:|---:|---|
| Fare — burun/kuyruk kökü | 0.09 m | 1 L | Tüm ölçeğin fiziksel referansı |
| Fare göz hizası | 0.035 m (ölçülecek) | 0.39 L | Kamera düzeyi; gövde yüksekliğiyle karıştırılmayacak |
| Ufak çakıl | 0.03 m | 0.33 L | Fare için basılabilir / takılabilir ayrıntı |
| Kaya parçası | 0.15 m | 1.7 L | Yol üzerindeki tırmanma olayı |
| Büyük kaya | 0.80 m | 8.9 L | Duvar/kale hissi; yalnız dekor değil |
| Kök kemeri açıklığı | 0.12–0.45 m | 1.3–5 L | Sıkışılabilir / geçilebilir / kapanabilir koridor |
| Çam gövde çapı (örnek) | 0.35–0.90 m | 3.9–10 L | Kabuk olukları ve kökler çevre coğrafyası |
| İnsan boyu referansı | 1.70 m | 18.9 L | Fare için devasa canlı; oyunda insan olması şart değil |
| İnsanın 3 katı kısa/orta çam | 5.10 m | 56.7 L | Genç ağaç bile kale hissi |
| İnsanın 5 katı çam | 8.50 m | 94.4 L | Fareden bakılınca tepe çoğunlukla kadraj dışında |
| Olgun çam örneği | 15–30 m | 167–333 L | Enorm gövde ve uzak/neredeyse görünmez tepe |

**Boy karşılaştırması yöntemi:** 1.70 m insan / 0.09 m fare gövdesi yaklaşık 19 gövde uzunluğudur. 15 m çam / 0.09 m fare yaklaşık 167, 30 m çam / fare yaklaşık 333 gövde uzunluğudur. **Uzunluk ve yüksekliği birbiriyle karşılaştırırken bunu açıkça söyleriz**; fare sırt yüksekliği veya göz yüksekliğiyle boy oranı aynı sayı değildir. E=3.5 cm örneğinde 15 m ağaç göz yüksekliğinin yaklaşık 429 katıdır, 30 m ağaç yaklaşık 857 katıdır.

**Neden farklı boydaki ağaçlar gerekli?** 5–8 m çamları her yere eşit dağıtmak ölçekli bir dünya değil dekor katalogu oluşturur. Fidan, eğilmiş genç çam, 15–30 m olgun ağaç, devrilmiş gövde, kırık dal, seyrek açıklık ve kök çıkıntıları, topografya ve yaş/habitatla bağlantılı olmalı. Ağaç yükseklik dağılımı tamamen uniform random olmayacak.

**Tasarımda yasak kolaycılıklar:** ağaç yüksekliğini kameraya göre değiştirmek, uzaklaştırıldıkça dünyayı sıkıştırmak, fareyi yalnız görsel olarak küçültüp 0.84 m çarpışma kapsülünü bırakmak, fareyi görünür kılmak için kamerayı sürekli 3–4 m yukarı yükseltmek.

## 18.3. Devasa dünya nasıl hissedilir — kamera, rota ve mikro coğrafya

Aynı 9 cm fare referansında 20 m yol yaklaşık 222 gövde uzunluğudur. Dünyanın yüzlerce kilometrekare olması şart değildir; **fareden bakılan gerçek 20 m**, birkaç kök kemeri, kaya ve kıyı geçişiyle muazzam bir güzergâh olabilir. Ancak bu oranda uzun yolların boş ve tekrar eden düz zemin üzerinde koşturma süresi olarak dayatılması da yanlıştır.

- **0–0.5 m mikro ölçek:** çakıl, kuru yaprak, yosun, yağmur izi, çamur, kabuk çatlağı; ayak ve yakın kamera kalite alanı.
- **0.5–3 m anlık mekân:** taş arkası, kök tüneli, basamak, kütük altı, düşmüş dal; hareket ve kamera yüzey takibi.
- **3–15 m bölge:** iki dev ağaç arasındaki oyuk, nehir kıyısından görüş, avcıdan saklanma, ışık havuzu.
- **15–80 m makro sahne:** orman dokusu, yamaç, açılan nehir ve devrilmiş ağaç gövdesinin kompozisyonu.
- **80 m+ arka dünya:** sanatçı yerleştirdiği ana silüet ve topoğrafya. Uzak alan gerçek mesafeyi korur ama mobilde HLOD/impostor ile verimli çizilebilir.

**Göz hizası sinematografisi:** Fare ağacın dibinde ise ağacın tepesini zorla gösterme. Kabuk detayına yaklaş, çıkıntılı kökü dev bir köprü gibi okut, gövdenin yukarı kaybolmasına izin ver; gerçek tepe yalnız açıklıkta veya oyuncu manuel yukarı bakınca görünür. Yüksek denetim kamerasının güzel görünmesi kalite kabulü değildir.

**Kamera oran laboratuvarı:** Aynı scene içine 9 cm referans fare, 1.70 m insan silüeti (yalnız editör katmanında), 5.1 / 8.5 / 15 / 30 m ağaç konur. Fare göz hizası, kötü prototip kameranın yüksekliği ve önerilen alçak üçüncü şahıs açıları karşılaştırılır. Fare ekranda görünürken çevrenin büyüklüğü okunmalı; aşırı fisheye, yanlış FOV ve sert parallax hilesi kullanılmaz.

**Teknik bağlantı:** Paket A ScaleBible ile Kamera Paket E arasında kamera takip mesafesi metre sabiti değil fare gövde uzunluğu L, göz E, eğim ve engel görünürlüğüne bağlı profil olur. Fare fiziği, kök geçidi collider genişliği, 3D ses mesafesi ve hava/ışık perspektifi de aynı ölçülerle çalışır.

## 18.4. Nehir asla şerit gibi olmayacak — genişlik referans tablosu

Aşağıdaki genişlikler *son harita için zorunlu bir nehir türü değildir*. Tek bir 9 cm gövde örneğiyle, suyun fareye göre ne kadar büyük görünebileceğini düşünmek için önerilen tasarım örnekleridir.

| Kanal parçası | Islak su yüzeyi genişliği | Fareye göre yaklaşık | Jeomorfolojik bağlam |
|---|---:|---:|---|
| Yan kol / küçük dere | 0.4–1.5 m | 4–17 L | Su sızıntısı veya ana kanala bağlı yan kol |
| Dar kayalık boğaz | 2–5 m | 22–56 L | Kaya-kesit daralması; hızlı akış mümkün |
| Doğal orman içi nehir | 6–14 m | 67–156 L | Tek ana kanal, karşı kıyı uzağa düşer |
| Geniş açılan havuz | 15–30 m | 167–333 L | Düşük hız, büyük su alanı, derin dip mümkündür |
| Taşkın yatağı / çok kollu bölüm | Farklı birleşen kanallar | Her kol ayrı ölçülür | Kum/çakıl bar, ada, yan giriş ve taşkın izi |

**Dikkat:** "Dar bölümden sonra geniş havuz" bir animasyon efekti değil gerçek arazi şekli olmalıdır. 3 m kanalın aniden 30 m kanal olması ancak çevre geolojisi, kot, yan kol/debi veya birikim havzası bakımından açıklanabiliyorsa tasarlanır. Kendi başına sayısal çeşitlilik bir güzellik ölçütü değildir.

### 18.4.1. Bağımsız kıyılar ve değişen enkesit

Artık sağ ve sol kıyı yalnız centerline'a aynı uzaklıkta çizilen iki sınır olarak ele alınmayacak. **left_bank(s) ve right_bank(s) bağımsız, elle düzenlenebilir, kıyı yükselti ve yatak malzemesi içeren üç boyutlu eğrilerdir.** Bunların ortası bile mutlaka akış ekseni değildir.

- Dış kıyıda oyulmuş 1.5 m yükseklik, iç kıyıda çakıl dolgulu 0.2 m eğimli su geçidi olabilir. Fare için 1.5 m banket 16.7 gövde uzunluğunda dik duvardır.
- En derin nehir hattı yani **thalweg**, her zaman kanalın geometrik ortasında bulunmaz; kıvrımlarda dışa kayabilir, kaya arkasında çukur oluşabilir, çakıl setinde yükselir.
- Kıyılar paralel ilerlemez: bazıları köklerle güçlü biçimde tutulur, bazıları çöker, bazıları taşkınla geri çekilir, bazılarında su altında geniş sahanlık vardır.
- Suyun görünen genişliği (W_wetted) ile taşkın sınırının genişliği (W_bankfull) ve bütün floodplain genişliği ayrı veri alanlarıdır.
- Adalar, çevresinden akan iki kol, mevsimsel kuru kanal ve taşkınla birikmiş kök kütüğü topografyaya uygun yerleştirilir. Her 40 m chunk'ta bir "aynı ada" yok.
- Nehrin bir kesitte nispeten düz akması doğal olabilir. **Hedef düzlük yasağı değil, sebebi olmayan cetvel-şekli ve periyodik tekrar yasağıdır.**

### 18.4.2. Nehir storyboard'u — geçici, elle tasarlanacak ardışıklık

Bu satırlar haritanın nihai nehir planı değil, morfoloji farklılığını açıklayan bir örnek:

| Sahne karakteri | Örnek genişlik | Gerekçe | Farenin deneyimi |
|---|---|---|---|
| Köklü giriş vadisi | 4–8 m | Kök ve dar topoğrafya | Dev kökler arasından suya yaklaşır |
| Dış kıyı oyuntulu kıvrım | 8–16 m | Erozyon + karşı kıyıda çakıl bar | Bir kıyı uçurum, diğeri sığ ve geniş |
| Kaya eşiğinde sıkışma | 3–6 m | Ana kayanın kanal daraltması | Ses ve akıntı artar; rota değişir |
| Açılan havuz | 14–28 m | Daralmadan sonraki daha büyük havza ve scour | Sakin yüzey, korkutucu derin su |
| Çakıl adası / ayrılan kanal | Bağımsız sol/sağ kol | Birikim, sediman ve taşkın | Oyun alanı adalarla dallanır |

Kıyı ve derinlik şekilleri arasında belirgin kopma olmaz; 5 sahne aynı sırayla tekrarlanan yüzme engelleri hâline gelmez.

## 18.5. Derinlik birikinti olmayacak — fare gövdesine göre su rejimi

Derinlik, mutlak metreye göre ve ayrıca **fare gövde yüksekliği H_body** ile karşılaştırılacak. Bu yükseklik gerçek rig ölçümü gelmeden sabitlenmez. Aşağıdaki 0.04 m sırt/beden yüksekliği sadece karşılaştırma için varsayımdır.

| Su ortamı | Örnek derinlik | Varsayımsal 4 cm fare yüksekliğine oran | Oynanış etkisi |
|---|---:|---:|---|
| Kıyı su filmi | 0.005–0.02 m | 0.13–0.5× | Islak ayak/çamur ve su yansısı |
| Sığ çakıl akışı | 0.03–0.12 m | 0.75–3× | Geçiş, itiş, sendeleme veya yüzmeye hazırlık |
| Olağan kanal | 0.20–0.80 m | 5–20× | Fare için ciddi su ortamı; yüzme/akıntı |
| Derin havuz | 1–3 m (tasarım örneği) | 25–75× | Su altında karanlık dip ve yüzeyden uzaklık |
| Ani kıyı düşümü | 0.3–1.5 m yerel yükseklik | 7.5–37.5× | Kıyıdan düşme tehlikesi ve kamera uyumu |

**Derinlik artırmak bütün suyu derin yapmak değildir.** Gerçekçi bir nehirde sığ, derin, düz, çukurlu ve ana akım kıyıdan farklı yerlerde bulunur. Havuzun derinliği su çizgisiyle birlikte çalışır; tek bir sinüs dalgasına kilitlenmez. Render bed mesh, collision, suda yüzme ve underwater depth attenuation aynı veri setini kullanır.

Çukur geometrisinde kaba tek heightmap bazı girintiler, banket altı oyuklar, taş/odun altındaki boşluklar için yetersiz olabilir: özel mesh/SDF veya ek yerel geometri gerektiğinde offline hazırlanır. Final ortam oyuncunun ayağının çarpacağı toprağı detaylı göstermeli; sualtında düz bir mavi yüzey bulunamaz.

## 18.6. Nehrin suyu genişlik ve derinliğe tepki verecek

Nehir şekli değişiyor diye aynı su yüzeyi dokusunun 20 metrelik alana gerilmesi de yasak. Alan ve ortalama hızın yerel ilişkisi önce kaba süreklilik denetimiyle kontrol edilir: Q yaklaşık A × V; debi, enkesit, hız ve eğim açıklanabilir olmalı. Bu formül tam CFD değildir; görsel/oynansal tutarsızlıkları yakalamak için ön denetimdir.

- Kaya boğazında hız, yüzey eğrisi ve kayanın arkasındaki kırılan akım ayrı örneklenir; tüm nehirde eşit beyaz çizgiler oluşturulmaz.
- İç kıyı sedimanı, dış kıyı oyulması, kayaya çarpan köpük, ana akıntı ve karşı akım cepleri ortak topoğrafyayla uyumlu olur.
- Havuz genişleyince yüzeyin bazı bölümleri sakin, bazı bölgeleri dönen veya tabandan kalkan kabarcıklı olabilir. **Sakin su da derin ve tehlikeli olabilir.**
- Yan kol/ada yakınında akış yönü yalnız ana nehir spline'ından çıkarılamaz; kollar için ayrı debi paylaşımı, birleşme ve vortex davranışları düşünülür.
- Foam atlas ve su normal dokusu tekrarı 30–60 saniye sabit kamerayla denetlenir. Her noktadaki görsel su vektörü fiziksel akımla tutarlı olmalıdır.

**Jeomorfoloji dayanağı:** U.S. National Park Service, havuz ve sığ-set dizileri, dış kıyıda aşınma, iç kıyıda birikim ve yatak genişliğine bağlı biçimler için örnekler sunar. Ancak bilimsel tipik mesafeleri sinüs tekrar aralığı gibi kopyalamayacağız.

## 18.7. Devasa dünya için yüzeye uyumlu kamera — yeni karar ölçütleri

Mevcut sabit 3.4 m takip mesafesi, 9 cm fare için 37.8 gövde uzunluğudur ve fare göz yüksekliği varsayımıyla ~97 göz yüksekliğine karşılık gelir. Kamera fazla yükselir/uzaklaşırsa ağaçlar büyük gerçek ölçüde olsa bile oyuncu kendisini drone gözünde hisseder.

- Varsayılan kamera **fareyi görebileceği kadar geride** ama onu insan seviyesinden izlemeyecek şekilde planlanır; takip mesafesi metre yerine L, E ve kamera/ground-probe durumuna bağlanır.
- Yamaç aşağı inerken ilerideki yüzeyi, çıkarken kaya duvarını okuyabilir. Göz yüksekliği ve zemin normalini kısa süreli filtreleyerek titremeyen, ufku gereksiz devirmeyen kamera modları planlanır.
- Yanında 20 m çam varsa bütün ağacı göstermek için farenin uzağına kaçmak yasak: dik gövde birkaç kare boyunca yukarı kaybolabilir; bu devasa his için doğru görseldir.
- Suya girerken su çizgisi ekranda yükselir; su altında gerçek derinliğe bağlı ışık sönmesi olabilir, ancak dokunun tüm görseli kapattığı yapay duvar ve aşırı bulanıklık kullanılmaz.
- Oyuncu kamerayı manuel çevirdiğinde otomatik tırmanış/iniş/engel tepkisiyle çatışmayan öncelik kuralları hazırlanır.
- Kamera doğruluk testi yalnız tek screenshot değildir: zemin eğiminde, su kenarında, ağaç dibinde, kök tünelinde, hızlı koşarken ve kamerayı döndürürken 30 FPS senaryosu doğrulanır.

## 18.8. Özel QA araçları ve teslimler

**ColossusScaleLab:** 9 cm referans fare + 1.7m insan editör silüeti + 5.1/8.5/15/30 m çam + kök ve kaya; gerçek GLB AABB ölçülünce varsayımsal değerler güncellenir. Çıktı: ölçek matrisi, 3 kamera açısı, metre/gövde uzunluğu denetimi, 49-bone rig durumu.

**MouseViewLab:** Aynı mekânda kuşbakış referans, gerçek fare göz seviyesi ve oynanabilir yakın üçüncü şahıs kadrajı. Ağacın uzak tepesi yerine gövde/kökün dev hissi, erişilebilir zemin ve fare görünürlüğü test edilir.

**RiverWidthLab:** Sol/sağ bağımsız kıyı verisi, W_wetted(s) ve W_bankfull(s) eğrileri, farklı genişlik/darlık, çakıl adası, kıvrım, taşkın izi; cross-section ve fare sahil kamerası birlikte kıyaslanır.

**RiverDepthLab:** Sığ kum seti / derin havuz / dış kıyı oyulması / kaya ardı scour; render su çizgisi, collision, taban derinliği ve suda karakter fiziği aynı referansla test edilir.

**FlowContinuityLab:** Dar boğazın yukarısı/içi/çıkışı, geniş havuz ve iki kollu adada debi/hız/foam sahnesi; 30/60 saniye tekrarlı motif, akış yönü ve su shader maliyeti değerlendirilir.

**TerrainNarrativeLab:** Rastgele şekil yerine açıklanabilir kaya, kök, su, sediman ve habitat: her hero kesitinin neden böyle oluştuğu, görünür jeomorfolojik işaretlerle anlatılabilir olmalı.

### Kabul işaretleri

- **Ölçek doğrulaması:** Farenin gerçek GLB boyu, collider, göz, kamera ve ağaçlar ortak 1m dünya sözleşmesine uyuyor; her ağacın boyu/çapı biyom ve yaşla açıklanabiliyor.
- **Devasa hissiyat:** Fare gözünden en az 3 farklı sahnede ağacın/orman tabanının/kayanın fareye oranı okunur; büyük his için sahte dünya büyütme veya kamerayı gizlice yüksekten izletme yok.
- **Nehir doğallığı:** 100m örnek kesitte her yerde aynı iki kıyı arası, aynı periyodik genişleme ve düzenli tekrarlanan bank şekli görünmüyor; doğal bir düz kesit varsa sebebi biliniyor.
- **Derinlik tutarlılığı:** Derin havuz suyu varsayımsal fare beden yüksekliğinin çok katı; sığ geçit doğal ve anlamlı bir oynanış istisnası; collision ile gerçek bed geometrisi uyuşuyor.
- **Kamera güvenliği:** Eğime, su yüzeyine ve büyük çevre objelerine uyumlu; kullanıcı kontrolünü bozmadan düşük fare bakışını koruyor.
- **Mobil performans:** Android 11/Mali'de p95/p99, su ekran kaplaması, RAM ve ısı ayrıca ölçülür. Güzel screenshot veya GitHub headless test tek başına AAA kalite kanıtı değildir.

### Gerekli teknik ve doğa referansları

- Mammal Society, House Mouse ölçüsü: https://mammal.org.uk/species-hub/full-species-hub/discover-mammals/species-house-mouse
- USDA Forest Service, Scots pine olgun boyu: https://research.fs.usda.gov/feis/species-reviews/pinsyl
- U.S. National Park Service, river/fluvial morphology: https://www.nps.gov/articles/fluvial-geomorphology-monitoring-stream-systems-in-response-to-a-changing-environment.htm
- Önceki planın Paket A–I bölümleri bu ek bölümle birlikte uygulanır; **yeni örnek ölçekler tasarım kararı olarak kesinleştirilmiş değildir**.
