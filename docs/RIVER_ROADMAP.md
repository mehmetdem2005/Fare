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
| S2 | PBR albedo-normal-roughness, sediment and wet/dry shore, 3D rocks LOD | NOT STARTED | No uniform pebble band, 40m seam, real assets logged |
| S3 | Flow vectors, obstacle wake, causal foam | NOT STARTED | CPU/GPU same flow, stationary pool no whitewater |
| S4 | Mobile water optics: absorption, refraction, Fresnel, caustics | NOT STARTED | Shallow/deep clear; no parallel sine stripes; device GPU cost |
| S5 | Sun/sky, forest shadows, fog, color, time-of-day | NOT STARTED | Scene coherent and bright on device |
| S6 | Mouse probes, swimming/buoyancy/drag, underwater camera/wet fur | NOT STARTED | Walk/shallow/swim states, no state oscillation |
| S7 | Spatial audio, footprints, droplets, leaves, bubbles, micro events | NOT STARTED | Event/lifetime bounded, camera-linked sound |
| S8 | Android device proof, LOD/preset tuning, performance/thermal | NOT STARTED | Target 30fps measured and screenshots approved |

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
