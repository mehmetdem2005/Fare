# Rounds 18–21 — 49-bone mouse, strict saved-weight and FULL gait anatomy test

**Recorded:** 17 November 2026, Europe/Istanbul. **Final status: NOT FIXED; ZERO CANDIDATES APPROVED.**

## 0. Scope and reproducibility

- Repository `mehmetdem2005/Fare`; isolated branch `rig-experiments/real-blender-ci`, distinct from the separate default-branch mouse model.
- The authoritative **unchanged** source `deliver/mouse_rig.blend` is 49-bone, 19,466 vertices, SHA256 `173ca67a372f5c04f27d922ef02f37921bbaf184cff0094976df326b4ec095b6`.
- Comparative v8 action/source from independent Round13: `run_sprint_v8_ik_phase_NUMERIC_REVIEW.blend`, SHA256 `984a21447c0217bc8ff91d02f9af1509324aa94dfaf29c543abd3d92f9b12c70`.
- Four Round19D candidate files were actually saved and reopened by Blender 5.1.2, each from immutable v8, not chained onto other experiments. In particular `0.170` saved candidate SHA256 `cb67f61b9a1a771366df53b10b89e1bec827c81450e2bac300be2c96b52e85bc`.
- No Automatic Weights, production edits, default-branch merges, or new game-ready GLB. Real Blender 5.1.2 depsgraph evaluated 24 frame positions plus frame 25 closure; L3 numerical vs L4 anatomical image approval vs L5 GLB/game-engine acceptance are independent.

## 1. Why this work resumed

The last pre-existing Round19E workflow, [run 43867704717](https://github.com/mehmetdem2005/Fare/actions/runs/43867704717), failed before candidate geometry verification because the independent evaluator had a **stale 287-vertex cap**, while the saved one-shot `0.170` candidate had actually changed **290** eligible vertices. Formula read-back residuals were ≈3e-8 and not the failure.

The corrected evaluator does **not** simply increase a magic cutoff. It independently re-derives each original vertex's eligible body-belt scope and exact upper_arm.L/R-versus-thigh.L/R weight-partition recipe from original weights, checks all groups at all 19,466 vertices, guards mass, noneditable groups, changed IDs and the original producer's separately recorded eligible count.

- [Fix commit 3003196](https://github.com/mehmetdem2005/Fare/commit/300319630c5931cecd3db95abf8e5166d4a6b4d7).
- [Corrected Round19E CI 43980699080](https://github.com/mehmetdem2005/Fare/actions/runs/43980699080) **PASS L3 independent saved/reopened candidate**: modified 290 vertices, maximum individual weight delta 0.0770700573921, maximum weight-sum drift 2.98023223877e-8, evaluated 24-frame score reproducibility error 0.0, source-versus-input hash unchanged. At frame 15, corotated rest-reference inversions 56→39, 17 corrected and **0 newly inverted**; non-adjacent BVH triangle overlaps 66→35. Sixteen actual Blender images generated. This is **not** a statement about other frames.

## 2. Round20: why the apparent fix fails the full movement

New `round20_full_cycle_geometry.py` and `fare-round20-full-cycle.yml` require, on every frame 1..24, for fixed **1,069** body triangles and six anatomical ROIs:

1. Actual evaluated mesh edge stretch p95, p99 and maximum against fixed source rest.
2. Rest-area normalized triangle area minimum, p05, p95, compressed face count.
3. Co-rotated original rest-reference normal direction, to catch new inversions.
4. Nonadjacent surface triangle BVH overlaps (proxy only; not proof of watertight self-intersection).
5. Exact same original mesh/rig/morph/constraint topology fingerprint, frame25 loop seam, and real Blender rendered before/after camera comparisons. The chosen failure frame was frame 10, not hand-selected to look favorable.

[Real Blender Round20 run 43981312286](https://github.com/mehmetdem2005/Fare/actions/runs/43981312286), [full images/CSV/JSON artifact](https://github.com/mehmetdem2005/Fare/actions/runs/43981312286/artifacts/14282019464).

At strength `0.170`, full-cycle worst interleg p95 absolute edge strain **1.034969588355509→0.9580313538090135** (apparently improved). Yet:

| Frame | Baseline finding | New candidate regression |
|---|---|---|
| 7 | smallest triangle area ratio 0.293784 | 0.200123 |
| 8 | 0.228801 | 0.162415 |
| 9, 10, 11 | original normals | one NEW corotated rest normal inversion on each |
| 10 | BVH overlaps 3 | 5 |
| 14 | overlaps 27, smallest area 0.056423 | overlaps 33, smallest area 0.005003 |
| 17 | smallest area 0.036707 | 0.008593 |

The correct strict result was **REJECT_L3_FULL_CYCLE_ANATOMICAL_REGRESSION**, deliberately CI-red to prevent a misleading promotion. Earlier Round19E green L3 means the saved candidate and f15 calculations were reproducible, not that the whole animation had sound anatomy.

## 3. Round21: distinguish algorithm failure from one poorly chosen strength

Added `fare-round21-strength-screen.yml`; it loads all four independent **saved and reopened** Round19D candidates, verifies their checksums against Round19D's own JSON provenance and reruns the identical full-cycle anatomy checks in separate Blender processes.

[Round21 CI 43981764236](https://github.com/mehmetdem2005/Fare/actions/runs/43981764236); [96 camera views + four 24-frame reports + result matrix](https://github.com/mehmetdem2005/Fare/actions/runs/43981764236/artifacts/14282529316).

| Longitudinal strength | Worst belly p95, original 1.03496959 | New corotated inversions, summed over frames | Frames with increased BVH overlaps | Frames with minimum area regression | Strict acceptance |
|---|---:|---:|---|---|---|
| 0.168 | 0.95928985 | 3 | 10, 14 | 7, 8, 14, 17 | REJECT |
| 0.170 | 0.95803135 | 3 | 10, 14 | 7, 8, 14, 17 | REJECT |
| 0.175 | 0.95592772 | 3 | 10, 14 | 7, 8, 14, 15, 17 | REJECT |
| 0.200 | 0.95017025 | 3 | 14, 16 | 7, 8, 14, 15, 16, 17 | REJECT |

**ZERO accepted candidates**. Round21 CI is green **because the execution and negative-science report both succeeded**, NOT because any Blender rig is anatomically valid. The workflow explicitly writes `numerical_accepted: []` in `Round21/strength_matrix.json`.

## 4. Mechanistic interpretation, certainty, and rejection

Previous [Round14 mathematical LBS-vs-Blender](https://github.com/mehmetdem2005/Fare/actions/runs/43775373776) validated weight-gradient amplification; [Round17 full-surface rejection](https://github.com/mehmetdem2005/Fare/actions/runs/43778146399) showed that unsigned-area numerical gains can hide flipped normals and overlap expansion.

These new full-cycle facts show that **a global constant-magnitude longitudinal upper-arm/thigh weight blend cannot repair this gait across every frame**. More aggressive strength improves global edge p95 but trades away local minimum area or normal orientation. This is measured, not a mathematical proof that no other anatomical weighting function or pose-space solution could work.

No model is visually L4-approved. Workbench still images permit comparison but not automatic biological acceptance. Nonadjacent BVH pair count is a useful screening metric, not physical tissue collision ground truth, and unsigned triangle area is not closed-body volume.

## 5. Required continuation: Round22 and beyond

**Next root-cause isolation, before changing any weights again:**

1. At the repeated failure frames 7,8,9,10,11,14,15,16,17, record exact failing triangle and vertex IDs, rest/candidate normal/area, newly created nonadjacent overlapping face pairs, and neighboring deform groups.
2. For each hotspot edge, use actual evaluated pose matrices and per-vertex weights to split the LBS edge vector into *common transform* and *spatial weight gradient* contributions; cross-check the resulting vertex position against the real Blender depsgraph before accepting any cause claims.
3. Distinguish forelimb IK target excursion, torso spine/hips rotation, shoulder-thigh weight bleed, and genuine disconnected/topology shell behavior; use independently reset single-variable ablations rather than arbitrary smoothing or further strength-only sweeps.
4. Any later candidate must pass every-frame no-new-inversion, BVH nonincrease, minimum-area nonregression, ROI edge p95/nonworsening, seam, bone hierarchy/weight scope, and **fresh process save/reopen**. Inspect multiple-camera anatomical renders, then real GLB morph/constraint export, Godot playback, and Android performance separately.
5. If no candidate passes, keep original v8 isolated checkpoint. NEVER copy an unqualified review file into `deliver/` or merge to default.

**Conclusive state 17 November 2026:** The investigation advanced and the stale verifier was repaired, but production-ready mouse torso deformation is *not yet fixed*. This is intentionally recorded as an unresolved problem.
