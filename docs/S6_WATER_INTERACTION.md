# S6 — Mouse water mechanics first integration, 22 November 2026

## Implementation details
- Real 0.84m CharacterBody capsule drives probes at feet (-0.42m), belly (-0.23m), chest (-0.07m), and head (+0.30m).
- `MouseWaterInteraction.update()` uses **RiverProfile.sample** for water level, signed shore distance, submerged extent and real bathymetry. It uses S3 `RiverFlowField.sample()` for actual current, instead of decorative shader noise.
- Three modes `DRY`, `SHALLOW`, `SWIMMING` with different entry/exit thresholds (0.54m enter, 0.43m exit) to prevent hovering/flicker.
- Shallow mode scales ground velocity and adds small stream drift; real `SWIMMING` mode uses 1.45m/s player propulsion + 80% S3 current, damped vertical spring buoyancy about surface +0.10m, max vertical velocity cap.
- The original CharacterBody3D movement, collision, jump and touch controls stay. Existing real `MouseRig` action and corrective shapes remain; a subdued slowed paddling approximation is used until dedicated authored swimming animation is available (NOT claimed biologically correct).
- The camera sample is an independent waterline probe with +/- 8cm hysteresis and smooth underwater filter. `UnderwaterCameraFX` draws a single translucent canvas_item overlay **without extra screen framebuffer copy**.
- Surface ripples reuse 12 TorusMesh instances, near-surface alpha rings, fixed lifetime and bounded draw calls.
- Damp overlay optionally wraps up to four skinned mesh renderers with an independent translucent StandardMaterial; original imported diffuse/UV and rig resources are not replaced. May require Android aesthetic/performance tuning.

## Hard constraints and remaining work
- Full fluid sim, actual deformable fur and verified swimming anatomy **NOT done**; wet appearance is a lightweight overlay.
- Depth-dependent physically volumetric underwater scattering, filtered spatial sound, bubbles and waterline split-screen optics remain S7 or advanced polish.
- In-game camera may need collision checks and S4 water material revision to render underside; real Android screenshot mandatory.
- Water effects measured only with Godot headless unit/integration before device test.
- 3D ripple model near river banks might intersect terrain: tune placement against real ground.
- S8 mandatory: Android GPU frametime, hot 10–15min, memory, camera/flow visual acceptance.

## Unit and integration checks
- dry spawn preserved by main smoke; shoal wade, pool swim, current drift, buoyancy stabilization, camera hysteresis, ripple pool bounded, 49bone still intact.
