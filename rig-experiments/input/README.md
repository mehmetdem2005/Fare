# Sohbette geliştirilen v6 modelinin GitHub giriş klasörü

Bu dizindeki model **mevcut depodaki `deliver/mouse_rig.blend` dosyasından farklıdır**.

Gerçek Blender üzerinde test edilmesi gereken dosyanın adı:

`FareModeli_v6_HeadEar_Refined_CANDIDATE.blend`

İnternete açık bu GitHub deposuna yüklemek modelin dosyasını herkese açık yapar. Yalnız paylaşmak istediğiniz modeli buraya koyun; `deliver/` dizinini değiştirmeyin.

Bu dosya burada bulunduğunda `Real Blender Rig QA` workflow'u v6'yı seçer; 41 kemikten başlayan iki ayrı omurga adayı (43/45 kemik) üretir. Gerçek Blender'ın değerlendirilen mesh'iyle REST ve çoklu poz testlerini yapar. Sonuçlar GitHub Actions artifact olarak saklanır.

İzole dal: `rig-experiments/real-blender-ci`.
