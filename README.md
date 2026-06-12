# Fare — 3D Fare Modeli Rig Projesi

Tripo AI üretimi fare modelinin (`source/mouse3dmodel1k.glb`) sıfırdan temiz rig +
hassas ağırlıklandırma çalışması. Ortam: **Blender 5.1.2** (headless, Cycles CPU).

## Durum

- [x] Model analizi (geometri, mevcut rig, dokular)
- [x] Rig planı + görseller (`rig_plan/`)
- [x] Plan onayı + revizyon istekleri (bıyık kemiği yok, taşma yok, IK/FK, tek parça)
- [x] İskelet kurulumu + ağırlıklandırma (`scripts/build_rig2.py`)
- [x] Stres testleri / QA (`qa/`)
- [x] Temiz GLB + .blend teslimi (`deliver/`)

## Skinning v3 — yırtılma kökten çözüldü

1. **Sürekli iade dağıtımı**: sökülen ağırlıkların "en yakın 2 kemiğe" dağıtımı
   Voronoi sınırlarında süreksizdi (19.2mm açılma!) → tüm core'a 1/d² sürekli
   dağıtım + yumuşak neck uygunluğu → **0.03mm** (yapısal olarak yırtılamaz)
2. **Tüp-torso**: çekirdek ağırlıklar omurga-ekseni arclength'inin saf fonksiyonu
   (radyal sabit) → üst üste kürk kabukları aynı kesitte özdeş hareket eder
3. **Dilate+trilinear voxel alanı**: gövde+pati+ayak tek sürekli 3B alandan örner
4. **10 driver'lı düzeltici shape key** (dirsek/diz/omuz/kalça/kulak L-R):
   pozda şindıl-köprülü delta-mush → rest'e ters-skin; GLB'de morph target +
   her animasyonda örneklenmiş weight kanalı

5. **Geometrik kaynak (tek parça)**: gövde panellerinin bitişik kenarları
   1.5mm Merge-by-Distance ile kaynaklandı — 181 kopuk parça → **6 bileşen**
   (ana kabuk + gözler), 22.703 → 20.060 vertex; UV/doku korunur. Kalan üst
   üste şindıllar ±normal ışın eşlemesiyle özdeş ağırlık paylaşır.

## Oyun animasyonları — 7 seamless loop (24fps, in-place)

| Action | Süre | Senaryo |
|---|---|---|
| `idle` | 96f | nefes, kulak seğirmesi, koklama, kuyruk salınımı |
| `walk` | 32f | 4-vuruş lateral yürüyüş, kalça salınımı, karşı-kuyruk |
| `run` | 14f | sıçramalı koşu (bound), omurga flex/extend |
| `sniff` | 72f | burun yerde koklama turu, kulaklar önde |
| `look_around` | 120f | sola-tut-sağa tetikte tarama, kulak takibi |
| `eat` | 60f | arka ayak üstü oturup patiden kemirme |
| `alert` | 48f | donup dikleşme, kulaklar dimdik, mikro titreme |

Faz-tabanlı örnekleme → ilk kare == son kare (kusursuz döngü). Bacaklar
**IK hedefli** (ik_hand/ik_foot + dünya-uzayı IKROT oryantasyon kilidi) —
sıfır kayma/gömülme (doğrulayıcı: tüm aksiyonlarda en derin uç ≥ −3mm).
Jest kolları aksiyon bazında influence keyi ile FK'ya geçer. Ayrıca 8
saldırı animasyonu: bite, swipe L/R, double_claw, pounce, tail_whip,
spin (360°), jump_slam — hepsi rest'ten başlar rest'te biter.

## Teslimat

| Dosya | İçerik |
|---|---|
| `deliver/mouse_rigged.glb` | Tek mesh + 39 joint iskelet + skin (4 etki/vertex), dokular gömülü |
| `deliver/mouse_rig.blend` | Aynısı + IK kontrol katmanı (4 bacak IK + pole, FK/IK blend) |

## İskelet — 38 deform kemik + `root`

```
root  (origin/zemin, deform değil — GLB'de hiyerarşi kökü)
└─ hips  (sakrum → kuyruk kökü)
   ├─ spine_01 ─ spine_02 ─ spine_03   (sırt kemerini takip eder)
   │                        ├─ neck ─ head
   │                        │         ├─ snout            (bıyıklar buna rijit)
   │                        │         ├─ ear.L ─ ear_02.L ─ ear_03.L ─ ear_04.L
   │                        │         └─ ear.R ─ ear_02.R ─ ear_03.R
   │                        ├─ shoulder.L ─ upper_arm.L ─ forearm.L ─ hand.L ─ front_toes.L
   │                        └─ shoulder.R ─ … (simetrik)
   ├─ thigh.L ─ shin.L ─ foot.L ─ toes.L
   ├─ thigh.R ─ … (simetrik)
   └─ tail_01 … tail_06   (kuyruk eğrisini takip eder)
```

Kontrol katmanı (.blend, deform değil, GLB'ye gitmez): `ik_hand.L/R`, `ik_foot.L/R`,
`pole_front.L/R`, `pole_hind.L/R`. IK constraint'leri `forearm.*` ve `shin.*`
üzerinde; **influence slider = FK/IK geçişi** (1.0 = IK, 0.0 = FK, animasyonlanabilir).
Pole açıları sayısal kalibre edildi (rest sapması ön: 0.26 mm, arka: ≤3.5 mm).

## Ağırlıklandırma (bölge/zone YOK — sürekli alan)

1. Mesh **tek parçada birleştirildi** (10 ada `part_id` ile izlenir), X'te ortalandı (+0.035 m)
2. **Bone heat** difüzyonu — çözücü kararlılığı için temiz kopyada (merge-by-distance)
   çözülüp pozisyonla geri eşlendi; kulaklar ayrı çözüm (ear zinciri + head)
3. **Kapsama garantisi**: ağırlıksız kalan vertex en yakın dolu vertexten doldurulur
4. Yumuşatma (factor 0.4 × 3) → **sonra** dikiş kaynağı: pati/ayak/kuyruk/kulak
   kenar vertexleri gövde alanından barycentrik örneklenir (kopukluk imkânsız)
5. **Bıyıklar**: kemik yok; her tüp (388 bağlı bileşen) kökündeki yüz derisinin
   ağırlık karışımını sabit alır → deriyle hareket eder, asla bükülmez
6. **UV dikiş tutarlılığı**: aynı konumdaki duplike vertexler (10.359 vertex, 4.453
   küme) birebir aynı ağırlığı paylaşır → pozda dikiş çatlaması imkânsız
7. Hijyen: temizlik 0.004, **maks 4 etki/vertex**, normalize

## Doğrulamalar

- **Taşma**: 38 deform kemiğin head/¼/orta/¾/uç noktaları ışın-paritesi testiyle
  mesh içinde doğrulandı (`CONTAINMENT ✓`) — kulaklar kabuk orta hattına
  otomatik uydurulmuş zincir (L: 4, R: 3 segment)
- **Ölü grup yok**, **ağırlıksız vertex yok** (0/22.703)
- Stres pozları: baş 57° dönüş, bacak kaldırma ~50°, kuyruk kıvrımı, omurga kemeri —
  çatlak/yarık yok (`qa/final_ik_stres.png`)

## Yeniden üretim

```bash
blender -b -P scripts/build_rig2.py    # rig + skin (mouse_imported.blend -> mouse_rig.blend)
blender -b -P scripts/qa_render.py     # poz/ağırlık/iskelet QA renderları
blender -b -P scripts/qa2_render.py    # yakın çekim stres testleri
python3 scripts/assemble2.py           # QA sayfaları
blender -b -P scripts/export_glb.py    # GLB + packed blend
```

İlk plan aşaması görselleri `rig_plan/`, final QA sayfaları `qa/` klasöründe.
