# S8-D — Android emergency performance tier (device measured 8.1 FPS)

Input telemetry from real Android 11 / Godot 4.7.2 Mobile: 8.1 estimated FPS, mean 123.37 ms, p95 141.97 ms, p99 147.62 ms, worst main-thread chunk 1386.75 ms, cache save 283.22 ms, 25 active chunks, 62 reported draw calls, render memory 239.5 MB after 102.133 seconds.

## Changes
- Android automatically starts in **AKICI** (fast) profile, 3D internal scale 0.60, no 3D MSAA, non-shadow sun, no river mist, distant-lite water shader also used nearby, and a simplified terrain shader that reuses the original Poly Haven albedo textures and vertex sediment masks. This is an explicit image-quality trade-off, not identical photorealism or guaranteed FPS.
- The FPS overlay exposes AKICI/DENGELI/TAM GORUNTU switch. Balanced retains full near-river S4 and terrain PBR at 0.75 render scale. Full restores 1.0 render scale, original 4x MSAA, shadows, full near-river optics and terrain PBR.
- Instrumented per-chunk blocking phases: cache_read, terrain_mesh, collider, vegetation, river_fx. JSON also exports script process/physics walltime (not GPU frametime). Existing p95/p99 and >500ms counters preserved.
- User cache save on Android deferred until 8 seconds stationary and no pending chunk queue (avoids a 283ms write while moving). On Linux CI behavior is unchanged.
- Main-thread generation and collider attachment still block. This patch is a diagnostic/graphics relief, NOT nonblocking chunk streaming.
- No changes to river shape, flow physics, 49-bone rig, joystick, original caches or binary assets.
- New headless regression checks fast/balanced/full mode restoration, 49-bone rig and chunk stage instrumentation.
- Android device A/B test needed: 60s still by water, 60s moving shore, 60s crossing/cold-new-chunk and then after 12-minute warmed run; send one JSON per mode. App-resume giant frame deltas are distinct from GPU costs.

Official docs: Godot Viewport.scaling_3d_scale and Viewport.msaa_3d are runtime-adjustable; scene-tree node creation is not generally safe from arbitrary threads, so do not rush unsafe threaded mesh/collider attachment.
