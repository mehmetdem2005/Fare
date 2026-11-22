# Fare Vadisi — V3 orman/material/mobil düzeltmeleri

Bu değişiklik `feat/river-s0-s1-geomorphology` temelinden ayrılmıştır. **Mevcut arazi geometrisi, river profile, eski baked chunk v3 ve 49 kemikli fare GLB değiştirilmedi.** Bu dal, sonlu ada/deniz heightmap'i değil, depoda bulunan **nehir prototipini** düzeltir.

## Görsel
- Çam artık kabuk ve ibre için **iki ayrı koyu PBR materyal yüzeyi** kullanıyor; daha dolu, şaşırtmalı 9 ibre halkası var. Model 4.6 m temel boyda; instance ölçeği yaklaşık 9–25m. Eski koni/tek yüzey materyali kaldırıldı.
- Çimen yoğunluğu chunk başına 150'den 950 adaya yükseltildi. Çoklu mesh opaque/instanced; shader alpha sorting yok. Ot yüksekliği varyasyonlu. Nehir suyu/kıyı yatağında bilinçli boş bırakıldı.
- Hem tam hem Android hızlı terrain shader, orman zeminini yeşil ağırlıklı renklendiriyor, rock/silt/wet masks korunuyor. Macro variation var. Android hızlı shader grass packed normal + roughness için sadece bir ek texture sample kullanıyor. Eksik normal importlarına neutral fallback sağlandı.
- Hızlı su shader iki akış yönlü normal hareketi ve 1–2 cm görsel dalgalanma oluşturuyor. Artık %98 opak bir yüzey için transparan pass ödenmiyor. **Gelgit fizik sistemi eklenmedi**: nehirde gelgit açık değil. Gerçek deniz ancak kıyı geometrisi ve collision/physics ile birlikte uygulanmalı.

## Performans
- Android/AKICI 5×5 = 25 yerine 3×3 = **9 aktif chunk**; desktop ve diğer kalite seviyelerinde mevcut 5×5 korunuyor.
- Android ilk 3×3'te pahalı dekorasyon hazır fizik/mesh'ten sonra parça parça ekleniyor.
- Android hızlı mod çimenleri 48m'de cull eder, görünür instanceları 680 ile sınırlar; tam kalite 950 yükler.
- Worker prefetch ring aktif chunk radius+1'a uyarlanır. Static multimesh ve deterministic per-chunk seed korunur.
- 8 FPS ölçümü önceki sürüme aitti. Yeni sürüm için **gerçek Redmi cihaz testleri yapılmadı; FPS artışı iddia edilmez**.

## Test
`godot --headless --path . -s res://tests/v3_forest_material_test.gd`
ve mevcut `tests/smoke.gd` / `tests/s8_mobile_rescue_test.gd`.
Bu ortamda Godot çalıştırılamadığı için testler depo içinde hazırlanmıştır, koşuldu diye işaretlenmez.

## Sınırlar
Birebir screenshot'taki denizin ada etrafına entegrasyonu bu eski depo dalında mevcut değildir. Yeni heightmap oluşturulmadı. Ağaç/gövde gerçek bake texture atlasları ayrı bir asset üretim aşaması ister; bu yama ise materyal fallback ve renk hatasını kod seviyesinde düzeltir.
