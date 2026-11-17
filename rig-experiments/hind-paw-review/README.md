# Arka pati ve baldır düzeltmesi

Önceki deney dosyasındaki sprintin 7–9. karelerinde sağ arka bacak aşırı toplanıyor, baldırın kalçayla birleştiği yerde uzun ve keskin bir kat oluşuyordu. Bu karelerde `IKROT` patiyi sabit dünya yönünde tutarken `shin.R` başka bir açıya dönüyordu. Yeni sprintte her iki arka pati havadayken hedef en çok 0,028 model birimi alçalıyor, 0,010 dışarı açılıyor ve −8° yuvarlanıyor. Havadaki ağdan ölçülen taban yüksekliği değişikliği kademeli açıp kapatıyor. Yere yaklaşırken öne uzanma kısaltıldı ve taban yüksekliği için küçük bir düzeltme eklendi.

7–9. karelerin eş kadrajlı renderlarında kıvrım önemli ölçüde azaldı. 14. karede basış sırasında önceki sivri birleşim yumuşadı. 2. karede sağ baldırın p95 değeri hâlâ 0,312 ve kalça birleşiminde sıkışma seçiliyor. Ön bacaklar, omuz ve rastgele ekstrem pozlar için anatomik kabul bu turda açık.

[Blender dosyası](FARE_HIND_PAW_REVIEW.blend) · [Godot GLB](FARE_HIND_PAW_REVIEW.glb) · [Sağ arka pati yakın planları](sag_arka_pati.jpg) · [24 fps](pati_karsilastirma.mp4) · [8 fps](pati_yavas.mp4)

| Ölçüm | Önceki sprint | Yeni sprint |
| --- | ---: | ---: |
| Sağ diz bölgesi kenar gerilmesi p95, 7/8/9. kare | 0,293 / 0,338 / 0,320 | 0,068 / 0,078 / 0,089 |
| Sağ ayak bileği kenar gerilmesi p95, 24 karede en yüksek | 0,292 | 0,190 |
| Sol ayak bileği kenar gerilmesi p95, 24 karede en yüksek | 0,175 | 0,125 |
| En düşük arka taban Z, tam kareler | −0,00248 | +0,00050 |
| Part 6 kesişme olayı, kare 1–24 | 68 | 54 |
| Interleg kesişme olayı, kare 1–24 | 10 | 6 |

Arka tabanlar 24 yarım karede de `Z=0` üstünde kaldı. En düşük sağ ve sol örnekler sırasıyla +0,000434 ve +0,000435 model birimi. Blender penceresinde 24 ve 8 fps oynatmada her iki hızda da 24 farklı kare örneklendi. 25. kare konum kapanışı tam, uç hız farkı p95 0,0000619 model birimi/kare. Yerinde sprintte oyun ilerleme hızı tanımlanmadığı için kaymasız zemin teması doğrulanmadı. Ön patilerin taban yüksekliği bu düzeltmenin hedefi dışındaydı.

Kayıtlı Blender dosyasında 7–9. kareler aktif sprint ve NLA ayrıldıktan sonra Pose Mode’da eşdeğer dönüşümlerle kuruldu. Yeniden kurma hatası yaklaşık (4,02 × 10^{-7}) model birimi. Yeni hareket `run_sprint_hind_paw_TRIAL` adlı ayrı aksiyonda. Ebeveyn mesh, ağırlıklar, kemik yapısı, önceki sprint ve expression aksiyonu korundu. Pose Mode’da farklı bir klibi düzenlerken iki `ik_foot` kontrolünün konum ve dönüşünü ayarlayarak aynı tür açılma sağlanabilir. Salınımdan basışa geçiş otomatik bir IK sınırı olarak eklenmedi.

Blender 5.1.2 GLB’yi yeniden içe aktardı. Godot 4.7.2 Linux headless, gerçek `AnimationPlayer` ile bir saniyelik sprinti ve iki saniyelik nefes, nabız ve bıyık klibini oynattı. 52 kemik, 17 morph ve klip başına 62 track. Sprint örneklerinde morph farkı sıfır. Android cihaz testi açık. [Sprint geometrisi](sprint_geometry.json.gz) · [Pati ölçümleri](paw_metrics.json) · [Pose Mode](pose_mode.json) · [Blender geri alımı](roundtrip.json) · [Godot](godot_playback.json)

## Deney ve yeniden üretim

Blender’da 60 salınım kombinasyonu tarandı. Ardından yere dönüşteki kapanma için beş öne uzanma miktarı karşılaştırıldı. Seçimde 7–9 ve 14. karelerin yakın planı, iki tarafın gerilmesi, taban yüksekliği ve tüm döngüdeki kesişmeler dikkate alındı. Salınımı düzeltip basışa dokunmayan varyant 62 Part 6 ve 10 interleg olayı verdi. Son varyant 54 ve 6 verdi. [Salınım taraması](swing_screen.json.gz) · [Basış taraması](stance_screen.json)

Depo kökünden Blender 5.1.2 ile yeniden üretim.

```bash
blender -b -t 4 --python-exit-code 1 -P rig-experiments/anatomy_hind_paw_trial.py -- \
  rig-experiments/pose-review/artifacts/FARE_POSE_REVIEW_UNAPPROVED.blend \
  ./hind-paw-build --candidate .028 .010 -8 --stance-reach .45

blender -b -t 4 --python-exit-code 1 -P rig-experiments/anatomy_expression_export.py -- \
  ./hind-paw-build/HIND_PAW_TRIAL.blend run_sprint_hind_paw_TRIAL ./hind-paw-export

sha256sum -c rig-experiments/hind-paw-review/SHA256SUMS
```

`deliver/mouse_rig.blend` başlangıç ve bitişte aynı hash’i verdi. [Kaynak ve yeni dosya hash’leri](SHA256SUMS)
