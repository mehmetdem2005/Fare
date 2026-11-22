# FARE VADİSİ / FARE MARTIN — YENİ SOHBETE TEKNİK DEVİR
**Tarih:** 2026-11-22. **Konu:** Mevcut Fare Vadisi prototipinden yeni, sonlu, fare ölçüsünde devasa AAA haritaya hazırlık. **Bu doküman bağlam devri; oyun kodu değişikliği veya yeni APK değildir.**

## EN ÖNEMLİ KARAR
Kullanıcı **sonsuz veya giderek genişleyen prosedürel bir dünya istemiyor**. Mevcut Fare Vadisi haritasını **beğenmiyor**: rastgele/noise arazi, devasa hissettirmeyen boyutlar, fare boyuyla kıyaslandığında sığ su, suni nehir yatağı/çukurlar, geometrik-şerit dalga akıntısı ve farenin yürüdüğü zemine uymayan kamera. Mevcut harita sadece oyun çekirdeği, chunk, CPU/GPU, su fiziği ve optimizasyon test yatağı. Gelecekte sıfırdan **elle yönetilen, tasarlanmış, sonlu, AAA görsel kaliteyi hedefleyen** yeni harita yapılacak. Prototip haritayı final gibi cilalama. **Her sorun ayrı mühendislik paketi olarak planlanmalı.**

**Tam ve güncel MASTER PLAN:** [AAA_FINITE_WORLD_SCALE_RIVER_CAMERA_MASTER_PLAN.md](./AAA_FINITE_WORLD_SCALE_RIVER_CAMERA_MASTER_PLAN.md) (çalışma dalındaki güncel sürümü oku; 18. bölümde devasa ölçü ve nehrin değişken genişliği).

## GERÇEK ÖLÇEK — FARE GÖZÜNDEN DEVASA ÇEVRE
Plan tasarım örneği: 9 cm (0.09m) fare baş/gövde boyu (gerçek GLB AABB henüz ölçülmedi), 1.70m insan yaklaşık **19 fare gövdesi**; 5.1m çam (3 insan) **57**, 8.5m çam (5 insan) **94**, 15–30m olgun çam **167–333 fare gövdesi** uzunluğunda. 0.15m taş ~1.7 fare gövdesi; 0.8m kaya ~9 gövde. 3.5cm göz yüksekliği ve ~4cm sırt yüksekliği yalnız deneysel tasarım varsayımı, ölçülmüş veri değil. **1 Godot birimi = 1m**; mesh/rig/capsule/camera/zemin/su aynı ölçek sisteminden türetilmeli. Fare gözünden bir çamın tepesinin kadraj dışında kalması doğal; yapay camera zoom/nesne şişirme gereksiz. Ağaç yaş/çap/kök/kabuk çeşitliliği ve gerçek yüzey yakın planı.

## NEHİR ASLA CETVEL GİBİ DEĞİL
Nehir sol ve sağ kıyıları authored bağımsız 3D eğriler, değişken W_wetted ve W_bankfull, yerel erozyon, çakıl bar, kayalık dar boğaz, ada/yan kol, farklı kesitler, farklı en derin hat (thalweg), sığ geçit, derin havuz ve akıntı ile şekillenecek. **Tek sinüs veya düzenli random genişlik artışı yok.** Örnek ıslak genişlik (final hüküm değil): yan kol 0.4–1.5m, kaya boğazı 2–5m, orman ana kanal 6–14m, havuz 15–30m. Derinlik yalnız görsel shader değil gerçek 3D bathymetry/mesh+collision; örnek derin havuz 1–3m, fare için devasa. Akış devasa suyu doğal göstermeli: Q≈A×V ile kaba fizik tutarlılığı, kaya çevresi wake, foam, lokal vortex, değişken roughness, periyodik görünmeyen wave/normal UV ve yeterli atlas çözünürlüğü. Suyun fiziği/render aynı veriyi kullanacak.

## KAMERA
Mevcut kodda Kamera focus=player+(0,0.23,0), distance=3.4m, FOV 65, **tek ray** ve lerp(9*dt); **zemin normalini okumuyor**. Yeni sistem fare göz yüksekliği ve hızına göre look-ahead, çoklu terrain/slope probes, yere yaklaşma/iniş, kök tüneli, uçurum, kaya, yüzme/suya girme/batma modları, hacimli kamera collision, sönümlü ve FPS-kararlı hareket, manuel kontrol önceliği. Hareket/rig yüzey teması ve kamera testi ayrı başlayıp birlikte entegre edilmeli.

## PLAN PAKETLERİ VE İLK GÖREV
**A** gerçek ScaleBible ve ColossusScaleLab (49-bone GLB AABB, model/capsule/göz metre kalibrasyonu), **B** authored sonlu harita/hero layout, **C** bağımsız kıyılar ve gerçek 3D nehir bathymetry, **D** doğal flow/foam/water optics, **E** zemine uyumlu CameraRig, **F** hareket/yüzme/ayak/rig, **G** offline baked finite map/chunk/LOD/streaming, **H** PBR ve AAA çevre/sinematografi, **I** profiling / Mali Android FPS. A — ölçek sözleşmesi **ilk gerçek üretim görevi**; kullanıcı kod yaz demeden kod yazma.
Test sahneleri: ColossusScaleLab, MouseViewLab, RiverWidthLab, RiverDepthLab, FlowContinuityLab, CameraLab, TerrainLab, AssetStreamingLab, DeviceBench.

## NEHİR PNG / HARİTA VERİLERİ (SON KONU)
Height / Bathymetry (yükseklik için tercihen 16/32-bit EXR), shoreline mask PNG, erosion, sediment/splat, wetness, flow vector RGBA (R=X hızı, G=Z hızı, B=turbulence, A=foam), normal, roughness, riverbed albedo/normal, caustics. **PNG asla nehir yatağı 3D geometri/çarpışmasının yerine geçmez.** Su genişliğini/dibini authored terrain/river data belirler. Godot 4.7.2 Mobile ile gerçek GPU testleri sonrası çözünürlük ve format kilitlenir.

## KOD / GITHUB / FPS / TEST
- Özel repo **mehmetdem2005/Fare**, çalışma dalı **feat/river-s0-s1-geomorphology**. Orijinal güvenli dal **game/godot-mobile-mouse-valley-clean** SHA **a671bb58da9efdccaeec472a88273cd54fcc8943**; PR #2 taslak, birleştirme yok. Godot 4.7.2 Mobile, Android 11 Redmi Note 8 Pro Mali.
- En son **gerçek APK CI**: kod SHA **bdffc9515fae4db0f83e1f93b27f857f87b899d8**, Actions [45051335008](https://github.com/mehmetdem2005/Fare/actions/runs/45051335008) SUCCESS, APK [artifact 14765906383](https://github.com/mehmetdem2005/Fare/actions/runs/45051335008/artifacts/14765906383). Sonraki SHA'lar MASTER PLAN dokümanı değişiklikleri; yeni APK değildir.
- Eski gerçek Android S9-d74eb1f1 FPS: sabit FAST ~37 FPS p95 50 ms p99 62.74 ms; hareket FAST ~25.8 FPS p95 60.97 ms p99 95.95 ms; worst generated chunk ~1075.56 ms, arazi 486ms / su mesh 222ms / flow atlas 219ms. GPU sabit sahne darboğazı izole edilmedi; >40s wall-gap arka plan durması olabilir. **Mükemmel optimize edildi deneme.**
- Yapılmış prototip performans yamaları: 112 baked chunk /32 flow atlas, 25 active window, dekor kademeli, invisible FAST mist atlandı; CPU-only worker terrain/water/flow, iki worker altı hazır; yakın collision sync fallback; v4 integrity SHA256 manifest cache, v3 uyum; hareket yönü ve collision-first priority. Headless CI başarı **gerçek cihaz frame/GPU/thermal testi değildir**.
- Hâlâ kontrol: main-thread collider/mesh/texture yükleme hitch, cache main-thread ResourceSaver, worker tekrar kuyruğu, flow-cache tekrar okuma, profiler period/boot/fixed ayrımı, GPU/VRAM/termal ve sahne yakın plan 30sn video. Gelecekte bunları nihai harita tasarımından ayrı track et.

## GÜVENLİK VE ÜSLUP / DEVAM ŞEKLİ
- Fare'nin orijinal **49 kemikli GLB rig, UV, skin** ve dal korunacak. Eski APK ile yeni build kimliği karıştırılmayacak.
- Her gerçek değişiklikten önce güncel branch head kontrolü, ayrı iş paketi, rollback, CI ve Android kabul gereklidir. Kullanıcı hangi adımı istiyorsa onu yap; gereksiz soru sorma ve yapılamayan işi yapılmış gibi anlatma.
- Kullanıcı samimi, doğrudan Türkçe tercih eder. Kod tasarımındaki saçmalıkları açık tespit et; asla “kusursuz AAA” gibi cihaz verisiyle doğrulanmamış iddia kullanma.
