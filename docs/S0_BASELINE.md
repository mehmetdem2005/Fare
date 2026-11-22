# S0 — Hareketli referans ve kıyas sözleşmesi

## Kaynaklar ve değişmezler
- Repo: mehmetdem2005/Fare
- Test başlangıç commit'i: a671bb58da9efdccaeec472a88273cd54fcc8943
- Godot 4.7.2.stable Mobile Vulkan, Android 11+, landscape
- 49 kemikli MouseRig GLB, joystick/koşma/zıplama/kamera korunur.
- Kullanıcının ekran görüntüsü: 2026-11-22, nehir paralel dalga çizgili, kenarda sürekli çakıl bandı, suya fizik tepkisi yok.
- Orijinal GLB UV'leri ve ağırlıkları değiştirilmez.
- S0 Android GPU/ısı/FPS ölçümleri: henüz alınmadı. Bu aşamada başsız Godot bunların yerine geçmez.

## Sabit konum ve test pozları (dünya koordinatı, metre)
- shoreline_close: nehir kıyısından 0.4m dışarı, z=16, fare göz yüksekliği 0.55m
- shoal: z=20, su derinliği 0.02–0.18m hedef
- pool: z=100, geniş ve derin su, 0.45–1.8m hedef
- meander_outside: z=150, kıvrım dışı eğim
- seam: z=40.0 ve z=80.0, çevreleyen chunk'lar
- river_view: kameradan nehrin 55%+ ekran kapladığı test
- mouse_freefall: karada x=20 z=16, zeminden +3.5m düşüş
- room for later dedicated static screenshot camera scene, currently not implemented.

## Beklenen kalite zinciri
1. GDScript ve GLSL import
2. Headless geometri + collision ve oyuncu smoke
3. Sabit seed/parametrelerle sayısal profiller, sahil=su yüksekliği ve seam testi
4. Android'de aynı bakış açılarından screenshot karşılaştırması
5. Su yakın planı ve ısınmış cihazda p95/p99 CPU/GPU frametime
6. Görsel kabul (birim test yerine geçmez)

## Renderer
- Mobile: screen/depth texture mümkün ancak pahalı; yerleşik SSR, volumetric fog yok.
- Fragment fill/overdraw limitleri cihaz ölçümüne göre seçilecek.
- Testler 1280x720 landscape, Low/Balanced/High; Balanced ilk ölçüm.
