# Fare — 3D Fare Modeli Rig Projesi

Tripo AI üretimi fare modelinin (`source/mouse3dmodel1k.glb`) sıfırdan temiz rig +
ağırlıklandırma çalışması. Ortam: **Blender 5.1.2** (headless, Cycles CPU).

## Durum

- [x] Model analizi (geometri, mevcut rig, dokular)
- [x] Rig planı + görseller (`rig_plan/`)
- [ ] Plan onayı
- [ ] İskelet kurulumu + ağırlıklandırma
- [ ] Test pozları / QA
- [ ] Temiz GLB + .blend teslimi

## Model

| Özellik | Değer |
|---|---|
| Boyut | ~0.58 × 1.0 × 0.45 m (burun −Y yönünde) |
| Geometri | 10 parça, ~30.700 üçgen (gövde 22.846) |
| Dokular | basecolor / normal / roughness-metallic, 1024² |
| Mevcut rig | Tripo otomatik — bozuk, sıfırdan yenilenecek |

Parçalar: `body`, `ear_L/R`, `paw_front_L/R`, `foot_hind_L/R`, `whiskers_L/R`, `tail`
(+ silinecek çöp `Icosphere`).

## Mevcut rigin sorunları (`rig_plan/mevcut_rig_sorunlari.png`)

- Asimetrik: sol arka bacak 5 kemik, sağ arka bacak 2 kemik
- Ön bacaklar kafa kemiğine bağlı (yanlış hiyerarşi)
- Anlamsız isimler (`bone_6`, `bone_17`, …), L/R simetri kuralı yok
- Pati kemikleri zemin altına taşıyor, gövdeyi delen dev root kemiği
- Model orta düzlemi X=0'da değil (−0.035 kaymış)

## Planlanan iskelet — 35 kemik (34 deform + `root`)

```
root  (zemin, origin — deform değil)
└─ hips
   ├─ spine_01 ─ spine_02
   │            ├─ neck ─ head
   │            │         ├─ snout ─ whisker.L / whisker.R
   │            │         └─ ear.L / ear.R
   │            ├─ shoulder.L ─ upper_arm.L ─ forearm.L ─ hand.L ─ front_toes.L
   │            └─ shoulder.R ─ … (simetrik)
   ├─ thigh.L ─ shin.L ─ foot.L ─ toes.L
   ├─ thigh.R ─ … (simetrik)
   └─ tail_01 ─ tail_02 ─ tail_03 ─ tail_04 ─ tail_05 ─ tail_06
```

Eklem koordinatları geometri analizinden çıkarıldı (omurga kemeri, dirsek/diz
bükülme noktaları, kuyruk eğrisi, kulak/bıyık kökleri): `scripts/plan_data.py`.

## Ağırlıklandırma stratejisi

1. Mesh +0.035 m X kaydırılarak ortalanır, parçalar yeniden adlandırılır
2. Her mesh **yalnız ilgili kemik alt kümesine** bone-heat (otomatik ağırlık) ile bağlanır
   (ör. kulak → `ear.L + head`; kuyruk → `tail_01..06 + hips`)
3. Temizlik: maks. **4 etki/vertex**, normalize, 0.01 altı temizliği
4. Eklem bölgelerinde yumuşatma (dirsek, diz, boyun, kuyruk kökü)
5. QA: test pozları render edilip deformasyon kontrol edilir

## Yeniden üretim

```bash
blender -b -P scripts/inspect.py        # model envanteri
blender -b -P scripts/analyze.py        # eklem yerleşim analizi
blender -b -P scripts/plan_visual.py    # plan renderları
python3 scripts/annotate.py             # etiketli plan sayfaları
```
