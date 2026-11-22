# S2 — Poly Haven complete PBR and sediment field

**Original sources:** official Poly Haven CC0 asset API; `tools/fetch_polyhaven.py` resolves source URLs for real diffuse, `nor_gl` (OpenGL/Y+) and `Rough`, then packs RGB normal + alpha roughness to a **linear** RGBA PNG. Generated `assets/ground/polyhaven_sources.json` documents URLs and SHA-256 digests.

**Assets:**
- `grass_ground` => `grass.jpg`, `grass_nrough.png`
- `grass_path_2` => `forest.jpg`, `forest_nrough.png`
- `rocks_ground_09` => `rock.jpg`, `rock_nrough.png`
- `river_small_rocks` => `pebbles.jpg`, `pebbles_nrough.png`

Normal/roughness pack is linear, **no sRGB color sampler hint**. The shader uses world XZ aligned UVs and explicit view-space normals because the procedural terrain mesh has no tangent array. No GLB UV or skin resources are changed.

**CPU ecology fields:** `ShoreSubstrate.sample(profile,worldXZ)` uses world-seeded FastNoiseLite, bank curvature and inside/outside bank state to derive gravel, forest, mud/silt, wetness and stone likelihood. Vertex COLOR channels RGB/A carry them to shader. 3D pebbles/cobbles are two per-chunk MultiMesh groups with size distribution; real sediment masks affect placement.

**Verification:** `tools/check_ground_pbr.py` checks source provenance SHA256/dimensions and non-flat channels. `tests/shore_s2_test.gd` verifies four packed maps and a spatially varying sediment strip with 410 paired bank points.

**Known remaining work:**
- Android visual proof: normal handedness, steep-bank stretching, tile repetition, realistic individual rock silhouettes.
- More sediment textures for sand/mud/moss, additional rock models/colliders, LOD allocation.
- Material blending and alpha overdraw on actual GPU; texture import memory instrumentation.
- S3 physical river flow and foam not started. S4 water surface shader still legacy.
