# S9.2a — Android cold-near-river 1s stall: route prebake
Phone S9-d74eb1f1 first cold dynamic river z=4/5 chunks (x=-1 and 0) repeatedly blocked the main thread for 0.85–1.08s. Terrain mesh generation alone was ~485–488ms, water mesh sampling ~219–223ms, and flow atlas up to ~219ms. Existing 7x7 pack covered z only -3..3, so Android generated all these from scratch.
- Expand **read-only packed storage** to x=-3..3, z=-3..12, 112 total terrain+collision+water packs. Previous 49 remain **byte-identical**. Only 63 new chunk packs are created by CI.
- Extend deterministic S3 flow v2 precomputed atlas count from 14 to 32; physics/flow values and original river geometry unchanged.
- The active gameplay window stays **5x5=25**, so 112 does NOT mean 112 live chunks.
- CI tests assert all 112 pack assets, 32 flow atlas equivalents, no gaps and all old S1–S9 tests. It auto-commits source asset bundles after APK export; the emitted APK includes generated files.
- This is a bounded corridor improvement; beyond x=-3..3/z=-3..12 procedural creation still stalls and ready chunk attach can still hitch. No new shader/rig/physics change. A next staged-cosmetics patch will address repeated 150ms ready-chunk build.
- No measured Android FPS improvement until installing the new uniquely stamped APK and repeating the same route.
