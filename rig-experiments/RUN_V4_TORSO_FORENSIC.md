# Sprint v4 – Why the abdomen and torso still deform badly (Blender L3)

**Independent forensic run:** https://github.com/mehmetdem2005/Fare/actions/runs/43753845327  
**Model:** 49-bone, 19,466-vertex `deliver/mouse_rig.blend` regenerated with `run_sprint_v4` and the protected 65% flank mask. This is **NOT** the separate 41-bone conversation v6 model. Original production source unchanged.

## Observed confirmed mechanisms

1. **Misallocated body skin:** Of 608 vertices in the fixed lower interleg abdomen ROI, 182 have both upper-arm and thigh weight >0.1. This area's weight mass averages about 27.5% fore upper-arm, 45.3% rear thigh, and only 3.5% spine_05. A rest-coordinate GLB point plot shows a belt of cross-limb influences around the underside of the torso. Per-vertex normalization alone is not the problem.
2. **Front IK overreach in worst phase:** Blender evaluated frame 3 right fore-leg target/root distance is **1.00424×** its two-bone chain length; measured solver end-target error is 0.000822 model units. Left fore is **0.98637×** its limit. The same frame has interleg p95 surface stretch **+163.4%**.
3. **Phase-dependent opposite distortions:** frame 3 interleg 95th-percentile extension +163.4%; frame 15 interleg 95th-percentile compression ~49.6%. A single smooth-weight operation cannot solve both tension and fold with unchanged kinematics.
4. **Spine / IK coupling:** On an identical rest ROI in 13 sampled frames, disabling both front IK chains reduces anterior chest mean p95 edge distortion ~33.8%; disabling hind IK ~22.7%; isolating spine_02 ~12%; spine_03 ~9.5%. Disabling hips rotation **worsens** it ~14.3%. These are causal ablations, **not production solutions**.
5. **Corrective shape keys are insufficient, not completely disabled.** GLB contains 14 morph targets with active shoulder (.24 peak), elbow (.44 peak) and spine curl/arch drivers. Previous assertion "shoulder & elbow remain 0 all sprint" was wrong for v4 and has been corrected in the memory report. At frames 1–5 when maximum stretch happens, shoulder/elbow corrective values are effectively 0. Morphs are authored in FK/extreme solo poses while running IK is active. Disabling all shape keys actually worsened front p95 ~1.4%, so shape keys help but don't address the principal problem.
6. **Preserve Volume is not an easy fix:** The armature modifier currently has Preserve Volume disabled. Toggling it raised anterior chest mean p95 distortion ~2.3% and interleg ~3.2% in isolated ablations.
7. **Torso weight authoring risk:** `scripts/torso_repaint.py` CORE weight-distribution list omits `spine_04` and `spine_05`, although shoulder parents attach to spine_05. Verify provenance and adjust anatomy only after measuring; don't assume script alone proves final file's history.

## Reproducible evidence and next work

- Script: `rig-experiments/forensic_v4_torso.py`
- CI: `.github/workflows/fare-v4-torso-forensics.yml`
- Artifact: `Forensic/forensic_v4_torso.json` with 13 frames, 6 fixed regions, independently reset driver/IK/modifier state and full-pose crosschecks.
- Fix priorities: (1) keep front IK reach below anatomical overextension and retain elbow bend, (2) region-specific body/limb weight reassignment (no blanket spine transfer), (3) build corrective morphs on **actual combined IK and spine poses** for tension frames 3/5 and compressed frames 13/15, (4) 24-frame six-ROI p95 stretch/compression and visual regression, then Godot mobile L5.

No model modifications were made in this forensic round; do not promote experimental v4 to production.
