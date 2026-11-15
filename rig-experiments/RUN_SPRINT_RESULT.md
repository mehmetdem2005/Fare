# Fare Sprint v2 — Real Blender production experiment

**Run:** https://github.com/mehmetdem2005/Fare/actions/runs/43740002030
**Isolated branch:** `rig-experiments/real-blender-ci`
**Source:** `deliver/mouse_rig.blend`, SHA256 `173ca67a372f5c04f27d922ef02f37921bbaf184cff0094976df326b4ec095b6`

## Delivered
- `run_sprint_v2`: 24 FPS, 24-frame in-place bound with IK hands/feet, spine flexion, body bounce, neck/head stabilization, ears and tail.
- `mouse_run_sprint_v2.blend`: 3,437,672 bytes, SHA256 `5f1c3157fffd559a9d305f1ec35f997c6bf0e1010eb280b67964b0637ed8da67`.
- `mouse_run_sprint_v2.glb`: 4,080,776 bytes, GLB JSON animation name `run_sprint_v2` and **124 animation channels**.
- `mouse_run_sprint_preview.gif`: 694,521 bytes, **12 frames** from actual Blender Workbench rendered frames.

## Blender evaluated mesh QA
- Blender **5.1.2**, one 49-bone 19,466-vertex rig.
- **25** mesh evaluations.
- Seam (posed frame 1 vs 25): **0.0 model units**, seamless loop.
- Quarter-cycle movement: **0.0926803** model units.
- Worst 95th-percentile relative edge strain: **0.3370**; mean **0.2599**. There may still be visual distortions or contact/sliding issues.
- This is **L3** actual Blender depsgraph + preview render, not a tested Android game engine import.

## Important: source is DIFFERENT from conversation v6
The source `deliver/mouse_rig.blend` has 49 bones, not the user's separate 41-bone `FareModeli_v6_HeadEar_Refined_CANDIDATE.blend`. This run does **not** prove v6 animation works; the rig hierarchies and IK control names differ.

## CI lessons
1. Blender PoseBones iterator yields objects; test `pb.name.startswith()`, not `bone.startswith()`.
2. Blender 5.1 GLB exporter can name a correctly exported 124-channel action `Animation`; validate channel count and relabel just GLB JSON clip name as needed.
3. Blender Workbench headless renderer requires EGL/GL and virtual display; install Mesa/libEGL/Xvfb and run render separately from export.
4. Hosted GitHub runner lacked ffmpeg; install explicitly, and always upload raw preview frames as fallback.
5. Preserve source `deliver/` files and older actions; develop in isolated branch only.

**Remaining:** Foot contact/sliding physics, detailed self-intersection/head motion, continuity with walk/idle, glTF/Android runtime L5 acceptance.
