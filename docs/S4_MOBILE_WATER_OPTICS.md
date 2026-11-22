# S4 Mobile water optics — engineering notes

Implementation: `shaders/river.gdshader`, `shaders/terrain.gdshader`, `world/river/water_quality_settings.gd` and `tools/build_water_normals.py`.

## Core geometry/optics
- `hint_depth_texture` and `INV_PROJECTION_MATRIX` reconstruct opaque riverbed view-space depth.
- Water surface fragment `-VERTEX.z` compared against opaque eye depth gives optical path (clamped to 4m).
- Beer–Lambert transmittance `exp(-absorption * optical_path)`; red light is lost fastest.
- `hint_screen_texture` reads the opaque scene; distorted UV is checked against displaced depth to avoid bringing foreground land across shore.
- Fresnel reflection from an approximate natural sky gradient + single sun glint, **not SSR**.
- Two advected, independently oriented slope tiles share S3 flow atlas. No full-fluid simulation.
- S3 obstruction foam is retained, background/foam share one transparent surface.
- Real-bed caustics: UV2.x per terrain vertex is S1 analytic water depth; imported original seamless normal tile's A channel supplies animated light caustics only where submerged.
- Generated normal tile is original code-generated output. No new external stock textures or hidden licenses.

## Mobile constraints
- **Godot Mobile renderer** screen & depth sampling supported, but can force a costly copy/flush. `LOW` disables secondary refraction lookups and caustic energy but still uses the depth/screen textures for absorption. It is **not** guaranteed to eliminate render-pass copy.
- No Mobile built-in SSR, volumetric fog or normal-roughness screen buffer.
- `ALPHA=0.985` screenspace transmission is already composed; using standard alpha 0.5 would double-blend the background.
- This is not optical perfect volumetric water: no dynamically refracted objects above surface or accurate reflected trees; actual visual calibration pending.

## Verification gates
- CI: Godot 4.7.2 stable GDScript+shader load, 49bone gameplay regression, S1–S3, S4 texture and UV2/quality shader test.
- Android: image checks from 2 camera elevations, near-shore foreground occlusion, 0.05/0.4/1.2m water depth, moving water, under-surface look, low/balanced/high GPU budget.
- Volumetric underwater camera is S6, atmospheric sun/sky is S5. No claim these are implemented.

## Optional software Vulkan render proof (new CI step)
- `tests/s4_visual_probe.gd` takes 960x540 reference capture with non-headless Godot Mobile Vulkan using Lavapipe under Xvfb.
- `tools/check_vulkan_capture.py` checks the PNG dimensions and luminance variance, preventing flat gray/black frames from being considered successful.
- This GitHub runner may not expose usable software Vulkan. Step is deliberately `continue-on-error` and reports failure in logs, not green visual acceptance.
- This proof is **not** a substitute for Adreno/Mali Android device visual and performance measurement.

## Rendering truth-in-tests correction
- CI run [45024283580](https://github.com/mehmetdem2005/Fare/actions/runs/45024283580) produced a 960x540 non-flat PNG, but log showed `Required Vulkan instance extension VK_KHR_surface not found` followed by **fallback to OpenGL 3**.
- Consequently this screenshot is **not proof** that S4 water optics render correctly on Mobile Vulkan.
- The optional probe now rejects OpenGL fallback with `S4_VULKAN_UNAVAILABLE`; its GitHub step will fail (nonblocking) until a genuine Vulkan surface is available.
- Separate Android GPU capture and optimization remain mandatory quality gates.
