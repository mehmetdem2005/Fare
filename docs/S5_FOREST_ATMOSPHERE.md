# S5 — Forest atmosphere and cohesive natural lighting

## Implemented architecture
- `ForestAtmosphere` owns **one** sun, **one** WorldEnvironment and one Godot ProceduralSkyMaterial.
- 3 explicit preset states: morning (default), midday, golden evening. No expensive every-frame radiance update.
- Sky background + ambient/reflection sourced from matching sky, sunset warm light, filmic tonemap with near-neutral adjustment.
- Cheap Godot Mobile depth+height fog; NOT volumetric fog.
- DirectionalLight3D 2-split shadow maps, up to 56m reach. Existing pine MultiMesh instances now cast actual directional shadows; grass and gravel do not.
- S4 water Fresnel sky palette, light direction and sunlight glints now sourced from the **same** sun/sky state.
- S4 bottom caustics emission intensity follows daylight; actual tree-shadow masking on caustics remains future work.
- `shaders/river_mist.gdshader`: gentle low-opacity local strips above water as batched MultiMesh, max 22 per river chunk, fade at 42m, with noise/drift. Emission/opacity deliberately restrained, no artificial big sun shafts/neon.

## Functional contracts
- `set_atmosphere_preset(preset)` on game synchronizes sky/sun/fog/reflections, per-chunk water shader uniforms and ground caustic intensity.
- S5 test checks sky+fog+2-split mobile shadow, real pine shadow casters, 3 distinct sun presets and river synchronization, local mist budgets.
- Existing 49-bone rig, joystick and river S1–S4 are not changed.

## Known limitations / mandatory verification
- Mobile GPUs may find real pine MultiMesh shadows expensive; S8 may reduce shadow range or tree casting rate.
- No cinematic god rays or actual participating volumetric media on Mobile; billboards are approximations and can show intersections/overdraw.
- A time-of-day preset changes environment deterministically; dynamic 24h weather/night cycle is NOT implemented.
- S4 procedural Fresnel sky is approximate, not SSR or reflection of trees.
- Android actual photos: morning/noon/evening shadows and mist, shoreline color and PBR look must be verified.
- Android Mali profiling: FPS, frame time p95/p99, shadow draw cost and thermal budget open. Green headless CI does not imply visual acceptance.
