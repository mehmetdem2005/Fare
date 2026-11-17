# Gerçek Blender rig deneyi (izole dal)

Bu dizin mevcut `deliver/mouse_rig.blend` ile sohbet içinde geliştirilen `FareModeli_v6_HeadEar_Refined_CANDIDATE.blend` **aynı model değil** bilgisini açıkça korur.

- Bu dal sadece deneysel Blender CI içindir; mevcut `deliver/` ve `scripts/` üzerine yazılmaz.
- GitHub Actions, Blender 5.1.2 ile **gerçek bpy dependency graph evaluated mesh** üzerinden test yapar.
- `rig-experiments/input/FareModeli_v6_HeadEar_Refined_CANDIDATE.blend` bulunursa v6 üzerinden omurga adayları üretilir; bulunmazsa depodaki önceki rig üzerinde yalnız test ortamının doğruluğu sınanır.
- Automatic Weights hiçbir zaman çalıştırılmaz.
- Baş/kulak ROI, kenar gerilimi, 0 derece regresyon, tekil kemikler, sağ/sol ve birleşik pozlar ayrı JSON test kayıtlarına yazılır.
- Geliştirme dalındaki dosyalar onaylanmadan `deliver/` içine taşınmaz.

**Doğrulama:** Workflow işinin yeşil olması yalnız gerçekten kaydedilmiş raporlarla anlamlıdır. Adayların üzerinde çalışıp çalışmadığı, `RigCandidates/overview.json` ve `qa_summary.json` ile belirlenir. Hata raporu da artifact olarak saklanır.

## Kısmi görev ve açık engel
ChatGPT tarafından hazırlanan v6 ikili dosyası GitHub depoda henüz yoksa bu işin koşusu **v6 deformasyonunu test etmiş sayılmaz**. Önce gerçek Blender test altyapısı ve depodaki farklı modele ait baz çizgisi doğrulanır.

## Kaynak
`RIGGING_WEIGHTPAINT_EXPERIENCE.md` projenin teknik hafızasıdır. Deformasyon sonuçlarını L1 statik, L2 matematiksel, L3 bpy evaluated mesh, L4 Blender render, L5 GLB/oyun motoru olarak ayrı raporlayın.

## Son doğrulanmış durum — 17 Kasım 2026 / Round 25

- Bu turun üzerinde çalıştığı dosya **49 kemikli mevcut Fare modeli**, 19.466 verteksli v8 koşu animasyonudur; yukarıda sözü edilen **ayrı v6 adayının doğrulanmış onarımı olduğu iddia edilmez**.
- [Round 23](ROUND_23_25_BONE_IK_SPATIAL_REPAIR_EXPERIMENTS_2026-11-17.md): 702 bağımsız IK/kemik poz denemesi gerçek Blender'da başarıyla çalıştı. f14 ve f17 karın alanı, **hips X −2°** tek-kare müdahaleyle ciddi iyileşti; bütün koşu için geçerli değildir.
- Round 24: 36 farklı anatomik maske/ağırlık denemesi; **0 kabul edilen**.
- Round 25: 32 yumuşak geçişli koşu/IK/kasık-kalça poz müdahalesi, 24+1 gerçek Blender karesi; **0 kabul edilen**.
- [Ayrıntılı tamamlanmış teknik rapor](ROUND_23_25_BONE_IK_SPATIAL_REPAIR_EXPERIMENTS_2026-11-17.md) ve [Round22 kalıcı kök-neden kanıtları](ROUND_22_VERIFIED_FAILURE_FACE_BONE_TRACE_2026-11-17.md).
- **Durum: ÇÖZÜLMEDİ.** İyi tek-kare sonuçları üretim BLEND/GLB dosyası sayma. Godot ve Android L5 hiç doğrulanmadı. Kaynak `deliver/`, `scripts/` ve varsayılan dal değişmedi.

## Son deney serisi — Round 26–37 (17 Kasım 2026)

- [12 tur, gerçek Blender 5.1.2 kanıtları ve f14 BVH çift analizi](ROUND_26_37_SIGNED_MORPH_BVH_FORENSICS_2026-11-17.md).
- Poz bazlı ve çok yüzeyli **inverse-skin shape key** düzelticileri geliştirildi; önceki pasif driver varsayımı gerçek v8'de çürütüldü.
- 9. karede alan eşiğini aşan üçgenler 465 ve 809 tespit edilerek eşik kaynaklı hata giderildi; 8. karede BVH regresyonu önlendi.
- Son kalan engel: **14. karede BVH 27 → 30**; 16 yeni kesişen üçgen çifti ve 13 iyileşen çift; f14 minimum alan ve BVH aynı anda korunamıyor. Ön/arka parçalara bölünmüş 24 profil de elendi.
- GitHub Actions yeşil = deney başarıyla çalıştırıldı; **0 yeni model tam L3 kabulüne ulaştı**. Hâlen L4/L5 yok; orijinal 49 kemikli model ve production GLB dokunulmadı.

## Round 38–42 — Bağımsız kaydedilmiş aday ve Godot import (17 Kasım 2026)

- [Gerçek Blender 5.1.2 / GLB / Godot 4.7.2 doğrulama raporu](ROUND_38_42_GODOT_L3_VERIFICATION_2026-11-17.md).
- Round38 temas projeksiyonu: **0 kabul**, 14. kare BVH 30→30.
- Round39: orijinal v8 pozunu 14. karede ters-skin shape key ile **4.47e−8** hata düzeyinde yeniden oluşturduk; 10 animasyon profilinden **6** tam 24-kare L3 kontrolünü geçti. Kaydedilmiş deneysel `.blend` SHA: `bf24c3c00367790af976e5f407cb9c3b20ad11754845bd0eb63d5cbe4042d07b`.
- Round40: dosya bağımsız Blender işleminde yeniden açıldı, orijinal 49 kemik hareketi değişmedi; tekrar tam L3 başarı. Eski yanlış 'rest = constraints active, action=None' denetim hatası saptanıp düzeltildi.
- Round41: 5,094,784 bayt GLB; 148 Blender animasyon kanalı, 29 morph hedefi, Blender yeniden import PASS. SHA `351a9475aeb6142331e4bc296aee957648cb055c7afc9988943a12c559c937d2`.
- Round42: **gerçek Godot 4.7.2-stable** headless `PackedScene` import PASS: 49 kemik, 29 blendshape, 1 koşu animasyonu, 68 track (29 morph, 34 bone rotation).
- **ÖNEMLİ:** L4 görünür gövde-kol kırışmaları halen inceleniyor; kullanıcı Android 11/Mali gerçek cihaz testleri YAPILMADI. Üretim `deliver/` ve eski orijinal model **korundu**, GLB/BLEND yalnız deneysel inceleme adayı.

## Round 43 — Godot 4.7.2 gerçek animasyon oynatma denetimi

- [Round 43 gerçek Godot AnimationPlayer CI](https://github.com/mehmetdem2005/Fare/actions/runs/44119489962): önceki Godot import testiyle yetinmeyip gerçek `MouseRig` animasyonunu `seek()` ile 1, 9, 10, 14, 15, 17, 25 karelerinde değerlendirdi.
- Godot içinde `R39_F14_ORIGINAL_REFERENCE` animasyonlu shape key f14 **0.899999559**, f1/f25 **~0**, komşu karede ~3e-6. Kalça kemiği hareketli; Godot kuaterniyon döngü farkı max **0.000454**.
- **49 kemik + 29 morph hedefi + gerçek oynatılan düzeltici kanallar PASS.** Gerçek Android/Mali GPU, zemin teması ve L4 karın görünüm onayı hâlâ **YAPILMADI**. Üretim modeline dokunulmadı.
