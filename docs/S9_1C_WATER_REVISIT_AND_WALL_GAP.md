# S9.1c — Android observations -> water-resource reuse and true wall-gap telemetry
22 Nov 2026, source a71da08e, Android Mali/Godot Mobile.
Reported fresh S9 metrics (clean fast route): frame mean=28.97ms (~34.5 fps), p95=51.85ms, p99=69.75ms, 65 chunk jobs, 2 terrain misses, river_fx p95=93.16ms on baked/reused chunks, terrain_mesh p95=0.02ms; cache_saves=0. Large repeated river stage for packed chunks demonstrates the CPU/scene/texture code path, not yet which sub-step is expensive.
Earlier mixed-mode run reached 110 chunk jobs, terrain max 1.047s, river_fx max 1.016s, combined chunk ~1.98s; _process(delta) frame max still exactly 150ms suggests callback delta clipping. No inference of GPU device time from these.

This patch:
- Bounded 32-coordinate LRU reuse for per-water mesh, v2 flow Image, ImageTexture, S4 high and distant-lite materials. Does NOT modify river physics, mesh data, or shaders; LOD and weather preset still reconfigure material on reuse. Reload does not re-upload flow texture for the same coordinate until LRU eviction.
- Separates the synchronous river_fx stage into water_mesh, flow_atlas_fetch, water_texture_submit (CPU call wall-time, not actual GPU completion), water_materials, water_scene_attach, river_rocks, major_rocks, river_mist. Parent river_fx remains and is inclusive; summing it plus children is double counting. Existing stage stats retained in S9 JSON.
- Adds monotonic _process callback arrival gap telemetry wall_gap_max_ms and wall_gap_over_500ms_total alongside existing engine delta counters. Background/resume can produce long gaps, so raw gap is not automatically a gameplay hitch.
- Regression checks actual material/flow image identity across same-co reload; no changed 49-bone GLB. Original playable branch untouched. Existing CI, user device and Vulkan testing still mandatory.

Not yet fixed: synchronous CPU terrain generation and collider attachment, repeated rock transform calculation, GPU fragment time and real Mali driver. Do not claim FPS targets before matched APK A/B on device. To measure previous clean test compare p95/p99 and water_resource_cache_hits as well as per-river-stage p95, sampled after the player revisits a known chunk.
