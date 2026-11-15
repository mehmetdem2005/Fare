# Fare sprint v2 abdomen/axilla root-cause QA — 2026-11-15

**Model:** `deliver/mouse_rig.blend` (49 bones, 19,466 verts), not the separate 41-bone conversation v6. All changes confined to `rig-experiments/real-blender-ci`. Source rig, rest geometry, weights, corrective shape key shapes unchanged.

## Validated result (Blender 5.1.2 evaluated mesh)
Latest corrected cross-checked run: https://github.com/mehmetdem2005/Fare/actions/runs/43742335288

- **Anterior chest and axilla ROI:** 2,125 fixed vertices, 6,045 edges (separate from 870-vertex hind-abdomen ROI). The original v2 has **worst 95th percentile relative edge-length error 1.3053**, i.e. extreme local distortion that was invisible in the overall global-mesh p95 statistic (~0.337).
- **Corrected controlled ablations** (13 sampled phases): full mean anterior ROI p95 **0.7063**; spine disabled **0.4469** (−36.7%); forelimb IK disabled **0.4528** (−35.9%). Hips rotation disabled **0.8289** (worse), all shape keys disabled **0.7192** (worse), Preserve Volume toggled **0.7315** (worse). **Root mechanism: spine/foreleg IK coordination and uncorrected shoulder deformation**, not a globally broken shape key set.
- **Corrective drivers:** `crv_shoulder_L/R`, `crv_elbow_L/R` remain 0 in 13 sampled sprint phases. The generator in `scripts/correctives.py` targets sign-specific bone local rotations, and does not activate for these IK poses. Distinct IK-aware correctives require separate proof/authoring.
- **v3 controlled motion candidate:** 24 fps, 24 frames, 124 exported GLB animation channels, 0 loop seam. Anterior mean ROI p95 **0.6491→0.5642** (−13.1%), worst **1.3053→1.2948** (only −0.8%). Hind belly worst **0.4493→0.3788** (−15.7%). v3 is *not production approved*: the uppermost anterior strain remains extreme.
- **Key QA process failure found and fixed:** The initial ablation script left forearm IK disabled between scenarios, contaminating subsequent tests and falsely ranking hip rotation as the main cause. Updated diagnostics restore each IK/IKROT constraint and driver state and force a fresh animation evaluation between scenarios. Independent full-pose crosscheck agreed **exactly at all 13 phases** (max difference 0).

## Repro scripts in this branch
- `rig-experiments/animate_run.py`: original run_sprint_v2.
- `rig-experiments/animate_run_v3.py`: reduced-motion test candidate.
- `rig-experiments/compare_run_front.py`: 24-frame fixed anterior ROI v2/v3 comparison.
- `rig-experiments/compare_run_belly.py`: 24-frame posterior ROI comparison.
- `rig-experiments/diagnose_run_front.py`: corrected ablations + actual Blender views.
- `.github/workflows/fare-sprint-v3-qa.yml`: reproducible Blender 5.1.2 and L3/preview tests, uploads JSON/BLEND/GLB/GIF.
- Separate persistent personal reference: `RIGGING_WEIGHTPAINT_EXPERIENCE.md`.

## Next technical work

1. Inspect true worst front axilla mesh edges and vertex group pairs, including edge-length thresholds to exclude very short shingle artifacts.
2. Reconcile spine flex timing with world-space front IK hand target and root movement during foot support; do not just deactivate the necessary locomotion system.
3. Inspect IK bone local/evaluated rotations against `crv_shoulder` / `crv_elbow` driver targets and author anatomically valid corrective shape keys where needed.
4. Run multi-view Blender L3/L4 regression plus game-engine L5 import and actual ground contact before acceptance.

The 41-bone v6 conversation model has **not** received the Github sprint; its mesh/weights differ.
