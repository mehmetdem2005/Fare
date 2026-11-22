# S8-A — Önceden hazırlanmış dünya / hibrit GPU optimizasyonu

## Uygulanan veri yolu
1. Godot 4.7.2 CI içinde 5×5 adet 40 metrelik chunk hazırlanır. Her biri arazi ArrayMesh, çarpışma ConcavePolygonShape3D ve nehir varsa su ArrayMesh ile akış Image kaynağı olarak \`assets/baked_chunks/v3/\` içine kaydedilir. **Bu paket oyunun dosyalarına dahildir.**
2. Oyun her chunk için önce \`res://\` paketine, sonra telefonun \`user://world_cache/v3/\` klasörüne bakar. Yoksa S1–S6'nın aynı deterministik üreticisi kullanılır.
3. Yeni chunk'lar RAM'de 5×5 yakın bölgeyle sınırlı; bir süre sonra yalnızca bir chunk'ın disk yazımı yapılır. Kalıcı telefon diski en fazla 100 önbellek paketini tutacak biçimde sınırlandırılır.
4. İkinci \`river_lite.gdshader\` uzak su içindir: S3 akışını ve S5 gökyüzü paletini korur ama S4'ün tam ekran renk/depth tamponlarını **örneklemez**. 56/66m histerezisli seçim uygulanır. Yakındaki su S4 shader'ıyla aynı kalır.
5. Çam MultiMesh gölgeleri yakın mesafede açık; diğer chunk'larda uzaklığa göre kapalı. Çimen/çakıl/cobble gruplarının görünürlük sınırları var.
6. Zemin geometri kaynaklarındaki UV2.x nehir derinliği KORUNUR. UV2.y hafif statik normal/eğim AO'su tutar. Bu bir LightmapGI bake işlemi değildir.

## Bilerek yapılmayan ve doğrulanması gerekenler
- GPU, çizilen her karede hâlâ çalışır; depolama/RAM, ekran gölgelendirmenin yerine geçmez.
- Tam LightmapGI için ayrı ışık UV kanalı gerekir. UV2.x halen S4 derinlik metadata'sı olduğundan üzerine lightmap yazılmayacak.
- Pişirilmiş yansıma, akış atlası ve görüntü efektlerinin kalite karşılaştırması ve termal Mali GPU profili GERÇEK ANDROID'DE yapılacak.
- Android oyunun ilk açılışı, ekran kopyası maliyeti, p95/p99 kare süresi, depolama artışı ve cache-hitch testleri henüz doğrulanmadı.
- S7 çevresel ses/ıslak iz/yaprak/mikro su parçacıklarına bundan sonra geçilecek.

## Testlerin amaçladığı kabul
\`tools/bake_world_chunks.gd\` → \`CHUNK_PACK_READY\`, \`tests/chunk_cache_s8a_test.gd\` → \`CACHE_S8A_OK\`; orijinal rig/su/S0–S6 smoke testleri aynen çalışmaya devam eder.
