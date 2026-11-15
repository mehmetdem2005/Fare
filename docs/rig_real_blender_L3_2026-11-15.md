# Fare Rig — gerçek Blender L3 denetimi (2026-11-15)

**GitHub Actions run:** https://github.com/mehmetdem2005/Fare/actions/runs/43734479048  
**Deney dalı:** `rig-experiments/real-blender-ci`  
**Test aracı:** Blender 5.1.2, `bpy.context.evaluated_depsgraph_get()` + `evaluated_get().to_mesh()`.  
**Automatic Weights:** Kullanılmadı.

## ÖNEMLİ MODEL AYRIMI

Bu rapor Github deposunun **`deliver/mouse_rig.blend`** modeli için geçerlidir: başlangıçta **49 kemik, 19.466 vertex**.

Sohbette hazırlanan **`FareModeli_v6_HeadEar_Refined_CANDIDATE.blend`** ise **41 kemik, 22.703 vertex** içeriyor. v6 ikili dosyası henüz bu dala yüklenmediği için v6'nın gerçek Blender L3 sonucunu bu belgeye atfetmeyin.

## Gerçek Blender sonuçları

| Deney | Omurga segmenti | Toplam kemik | Tekil poz | Birleşik poz | Dağıtılmış spine poz | Save/reopen |
|---|---:|---:|---:|---:|---:|---|
| GitHub kaynak | 5 | 49 | 90 | 8 | 8 | Giriş okunabildi |
| spine7 | 7 | 51 | 102 | 8 | 8 | PASS |
| spine9 | 9 | 53 | 114 | 8 | 8 | PASS |

- Başlangıç rest vertexine en büyük sapma: spine7 `1.9993958e-07`, spine9 `2.6289044e-07` model birimi.
- Toplam vertex ağırlığında en büyük fark: `2.98023224e-08`.
- Yeni distal kemiklerin bireysel pose testi: spine7'de 2, spine9'da 4.
- Geometrinin iyi görünmesi **L4** render, yüzey öz-kesişim ve export testleri tamamlanana kadar onaylanmış sayılmaz.

## Gerçek Blender dağıtılmış bükülme p95 kenar oranı

| Eksen + toplam hedef açı | 5 | 7 | 9 |
|---|---:|---:|---:|
| X −30° | 0.47400 | 0.42205 | 0.40375 |
| X +30° | 0.31090 | 0.25871 | 0.24731 |
| Z −30° | 0.31567 | 0.30895 | 0.31257 |
| Z +30° | 0.32170 | 0.31506 | 0.31858 |

Ölçüm, toplam komut açısını segment sayısına bölüp her omurga kemiğine uyguluyor. Nihai baş dönmesi/uzunluğu eşitlenmediği için bu tek başına mutlak kalite kanıtı değil. 30° yüksek gerilme hâlâ kalıyor. Android deform kemik maliyeti ve GLB ihracı ayrıca test edilmeden nihai model seçilmeyecek.

## Bulunan QA pipeline kusurları ve çözümleri

1. **Test-kemik listesi kırpılıyordu.** Yeni distal spine kemikleri listede yer açarken bazı ön bacakları dışarı atıyordu. Kırpma kaldırıldı.
2. **IK kontrol kemikleri yanlışlıkla deform testine alınıyordu.** Filtre `bone.use_deform` ve kontrollü kemik adlarına daraltıldı.
3. **Eski spine pozları yeni distal segment kalitesini ölçmüyordu.** Kendi distal rotasyon testleri ve eşit hedef toplam açılı dağıtılmış eğilme testleri eklendi.
4. **Adayları kaydetmeden önce sahne animasyonu kapatılıyordu.** Mevcut action ve NLA mute durumları test öncesinde kaydedilip save öncesinde geri getirildi.
5. **Kaydedilmiş çıktı yeniden açılmıyordu.** Şimdi dosya Blender'da tekrar açılıp yeni bone adları ve sayıları doğrulanıyor.

## v6 için sıradaki kalite kapısı

Dosya **`rig-experiments/input/FareModeli_v6_HeadEar_Refined_CANDIDATE.blend`** yoluna, aynı izole dala eklenirse `push` olayı otomatik test workflow'unu çalıştırır. Rapor `input_kind=v6_conversation_schema` olmalı; ayrıca 43/45 kemikli adaylar gerçek Blender ile üretilip test edilmelidir.

**Uyarı:** Bu GitHub deposu herkesin erişimine açıktır. Modeli yüklemek modeli halka açık hale getirir. Bu istenmiyorsa özel depo kullanılmalıdır.

Kanıtlar: Github Actions çalışma logu, artifact ZIP içindeki `qa_summary.json`, `spine7.json` ve `spine9.json`.
