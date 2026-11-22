# FARE VADISI — RIVER PRODUCTION CHECKLIST (S0–S8)

This is the authoritative non-skippable roadmap for the river engineering project. A green headless CI does NOT prove Android visual quality. Every stage has independently tracked blockers.

**Safe branch:** feat/river-s0-s1-geomorphology (based on game/godot-mobile-mouse-valley-clean)
**Engine:** Godot 4.7.2 stable Mobile renderer
**Asset rule:** Keep original rig, UV, controls, camera, code history and original river shader as a fallback.
**Scope:** One stage at a time, commit/test/record findings before progressing.
**New feature approval:** User authorized implementation in current conversation.

| Stage | Scope | Status | Exit criteria / unresolved evidence |
| --- | --- | --- | --- |
| S0 | Baseline references, measurement route, test fixtures | DOCUMENTED; ANDROID OPEN | Baseline doc, deterministic reference positions and feature matrix drafted; real Android capture + device frametime still open |
| S1 | Spline center, variable asymmetric bed, shoreline, mesh/collision continuity | CODE + HEADLESS PASS; ANDROID OPEN | 1,534 depth/shore/seam samples passed, 49-bone gameplay smoke passed, shoreline collider probes added; Android visual acceptance open |
| S2 | Poly Haven normal+roughness PBR, sediment classification, wet/dry, 3D pebbles | IMPLEMENTED; CI + ANDROID PENDING | Packed CC0 PBR + provenance + spatial sediment tests; Android visual/tile repetition and rock LOD still require review |
| S3 | Flow vectors, boulder flow wake, RGBA8 GPU atlases and causal foam | VORTEX S3 POLISH IN REVIEW; CI + ANDROID PENDING | Deterministic geometry and physical velocity/foam correlation; visual water/running physics and device checks open |
| S4 | Mobile depth absorption, safe limited refraction, Fresnel sky, real-bed caustics | CODE + HEADLESS PASS; MOBILE VISUAL OPEN | Godot 4.7.2 shader/UV2/quality tests pass. 960x540 CI capture fell back to OpenGL (VK_KHR_surface unavailable), so NOT Vulkan proof; Android render/GPU metrics open |
| S5 | Procedural sky, directional pine shadows, river mist, fog and time-of-day | CODE IN REVIEW; HEADLESS/ANDROID PENDING | Central ForestAtmosphere, 3 preset states, S4 reflection linked, bounded mist batches; real Android aesthetic/shadow/GPU still open |
| S6 | Mouse water probes, depth-gated swim, flow drag/buoyancy, wet fur overlay, ripple pool, underwater camera | CODE IN REVIEW; CI + ANDROID PENDING | Water motion physics, camera hysteresis and 12 ring cap tested; real rig swim gait, waterline visual and actual Mobile GPU pending |
| S7 | Two spatial procedural river sound layers, underwater low-pass, moving leaves, prints, 8 bubbles/drops | CODE IN REVIEW; CI + ANDROID PENDING | Bounded MultiMesh/print pools, build-time WAV, S3 flow linked; real acoustic and mobile visuals open |
| S8-A | Build-time 25 precompiled chunk packs, persistent disk cache, distant water/shadows | CODE IN REVIEW; CI + ANDROID PENDING | 5x5 terrain/collision/flow, bounded runtime window and LOD; headless/Android proof open |
| S8 | Android FPS/p95/p99, RAM/VRAM, chunk streaming, APK diagnostics and thermal | TELEMETRY+CPU STRESS PASS; APK EXPORT IN REVIEW; ANDROID DEVICE OPEN | In-game opt-in FPS panel, JSON/copy report and scripted streaming-route stress; real GPU/thermal/device acceptance not yet measured |

## Non-negotiable regression suite
- Original 49-bone GLB, named MouseRig animation, no re-export/UV flip.
- Joystick touch moves mouse, camera drag orbits, run/jump remain intact.
- Spawn airborne and land on front-facing terrain collision.
- No degenerate or inverted terrain triangles.
- No discontinuity across 40m chunk seam; signed shore distance and depth continuous.
- At shoreline depth == 0, water surface/bed heights coincide.
- Water surface split and clipped into intersecting terrain chunks; no doubled overlays.
- No build/release claim without passing actual test suite and Android visual validation.

## Change policy
Mark stage **implemented/tested/visually accepted** separately; don't mark any stage complete based on importing the project.
Keep failure logs and corrective commits. The release branch stays unchanged until feature validation passes.
