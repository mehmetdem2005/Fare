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
