# Sprint v4 + protected flank skinning (2026-11-15)

**Model identity:** `deliver/mouse_rig.blend` (49 bones, 19,466 vertices), NOT the separate 41-bone conversation model. Isolated branch `rig-experiments/real-blender-ci`. Production `main` and `deliver/` unchanged.

## What actually passed in Blender 5.1.2
- [Run v4 vs v3 L3](https://github.com/mehmetdem2005/Fare/actions/runs/43748300092): shoulder-origin-aware front IK control during swing, 24 FPS × 24 frames plus seam; front chest p95 worst **1.29484→1.07800 (−16.75%)**, mean **0.56423→0.50574 (−10.37%)**, posterior unchanged. Seam 0.0, action 124 GLB channels.
- [Protected flank weight trials L3](https://github.com/mehmetdem2005/Fare/actions/runs/43748522958): 222 body vertices updated, `upper_arm.L/R` and `thigh.L/R` ratios only; total weights conserved to **2.98e−8**. `strength=.65` interleg worst p95 **1.78065075→1.63383686 (−8.24%)**, chest worst 1.06533867→1.06234776; central/rear/distal foreleg unchanged. (These ROI definitions differ from the animation comparison; do not directly mix cross-test numbers.)
- [Final experimental BLEND / GLB / Workbench render](https://github.com/mehmetdem2005/Fare/actions/runs/43749107270): 49 bones, 19,466 verts, `run_sprint_v4` with 124 GLB animation channels, skin present, 12-frame GIF and 32 Blender multi-angle views. Artifacts available on that run (retention 30 days).

## Approaches rejected
- Three `upper_arm→forearm→hand` smoothing candidates improved elbow locally but **worsened distal foreleg 11–38%**: [run](https://github.com/mehmetdem2005/Fare/actions/runs/43748019290).
- Hind IK origin follow v5 improved chest worst only 1.2% and worsened rear belly worst 1.3%: [run](https://github.com/mehmetdem2005/Fare/actions/runs/43748767266).
- Flank `strength=.95` slightly worsened chest worst; only .65 is selected.
- Direct fore/hind→spine transfer from earlier rounds severely worsened interleg and is never used.

## Hard remaining defect
Although improved and exported, interleg p95 worst **1.63384 (163% relative edge change)** remains unacceptable. Visual review still shows belly fold/squeeze during parts of bound. This is an **EXPERIMENTAL** model, not production-ready or perfectly repaired.

## Next correct technical step
Author IK-aware shoulder/elbow corrective shape-key morphs using ACTUAL evaluated bone rotations and mesh surface constraints, not blind weight transfers. Check wall penetrations, foot slide, local volumes, Godot/Android GLB runtime (L5) and all 8 viewpoints before approving. Always read `RIGGING_WEIGHTPAINT_EXPERIENCE.md` before next round.
