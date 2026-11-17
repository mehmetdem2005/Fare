# Fare 49-bone rig — Rounds 23–25: Independent causal controls, spatial weight guards and continuous pose attempts

**Date:** 17 November 2026 (Europe/Istanbul). **Status: DEFORMATION NOT SOLVED. NO NEW PRODUCTION CANDIDATE.**

This is an evidence-based continuation of [Round22 verified triangle-to-bone mechanism](ROUND_22_VERIFIED_FAILURE_FACE_BONE_TRACE_2026-11-17.md) and [Rounds18–21 all-frame negative findings](ROUND_18_21_SAVED_WEIGHT_AND_FULL_CYCLE_FINDINGS_2026-11-17.md).

## Scope and immutable provenance

- Repository `mehmetdem2005/Fare`, isolated `rig-experiments/real-blender-ci` branch.
- Authoritative untouched `deliver/mouse_rig.blend`: 49 bones / 19,466 vertices, SHA256 `173ca67a372f5c04f27d922ef02f37921bbaf184cff0094976df326b4ec095b6`.
- Reference original v8 continuous gait: SHA256 `984a21447c0217bc8ff91d02f9af1509324aa94dfaf29c543abd3d92f9b12c70`.
- Rejected original 0.170 longitudinal weight trial, saved and independently reopened: SHA256 `cb67f61b9a1a771366df53b10b89e1bec827c81450e2bac300be2c96b52e85bc`. It is a controlled *experimental comparison*, not an accepted base rig.
- **No Automatic Weights.** No existing BLEND, `deliver` asset, production/default branch, GLB or animation release is overwritten. Blender 5.1.2 evaluated dependency graph is used; numerical L3 results are explicitly distinct from human L4 anatomical appearance or L5 glTF/Godot import.

## Round23 — 702 independently reset IK and torso single-actuator experiments

Script: `round23_ik_bone_ablation.py`; workflow: `fare-round23-ik-bone-ablation.yml`.

[Successful actual Blender CI 43990624932](https://github.com/mehmetdem2005/Fare/actions/runs/43990624932); [full 702-trial JSON](https://github.com/mehmetdem2005/Fare/actions/runs/43990624932/artifacts/14287941319).

At 9 previously identified failed frames `7,8,9,10,11,14,15,16,17`, independently perturb 4 true IK targets on X/Y/Z by ±0.002/±0.004 model units (48 variants/frame), and the real `hips`, `spine_03/04/05` and `neck` bone Euler X/Y/Z by ±2° (30 variants/frame), **78 × 9 = 702 controlled tests**. Each returns to actual saved animation state independently. The no-perturbation recovery check reached ≤1e-5. All selected comparisons use the *actual altered spine_03 corotated reference* to avoid false normal inversion for torso rotations. Shortlisted controls are separately re-evaluated for nonadjacent BVH overlaps. There were 57 instantaneous shortlist rows, **not continuous-cycle acceptance**.

Most striking actual pose-specific results for *unmodified saved 0.170* candidate:

| Original candidate failure frame | Control on that frame alone | Fixed triangle/rest-normalized face area before → after | Whole-underbody minimum area before → after | Candidate BVH pairs before → after |
|---|---|---|---|---|
| 7 | `ik_foot.L` Y -0.004 | 0.200123 → 0.5688 | 0.200123 → 0.3015 | 0 → 0 |
| 8 | `spine_04` X +2° | 0.162415 → 0.3468 | 0.162415 → 0.3382 | 0 → 0 |
| 14 | `hips` X -2° | 0.005003 → 0.3714 | 0.005003 → 0.1776 | 33 → 0 |
| 17 | `hips` X -2° | 0.008593 → 0.1943 | 0.008593 → 0.0898 | 25 → 1 |

These are **causal single-frame sensitivities**, not a plausible full animation fix. A single joint improvement at frame14 must not be conflated with all-frame body/ground-contact correctness.

## Round24 — 36 separate spatially protected weight-distribution hypotheses

Script: `round24_spatial_weight_guard.py`; CI: `fare-round24-spatial-mask-screen.yml`.

[CI 43990966385](https://github.com/mehmetdem2005/Fare/actions/runs/43990966385); [36-profile JSON](https://github.com/mehmetdem2005/Fare/actions/runs/43990966385/artifacts/14287752093).

Re-open actual two saved models with exactly unchanged armature/rest/morph topology and action. Use 290 already proven edited source vertices, and compare 24 × 19,466 actual Blender posed vertex positions. Since **only static vertex weights** changed, each vertex's result is a linear function of the strength applied to the original source-to-0.170 bone-weight delta; no pose or source topology modifications are inferred.

36 profiles = three spatial seed sets (`sentinel`, `related`, `all`) × four candidate strengths (0.060, 0.100, 0.140, 0.170) × three Gaussian-free smoothstep distance-mask radii (0.012, 0.025, 0.045 model units). Original versus candidate face-area signed normals and minima, six ROI p95 strain, and possible BVH screening on fast-screen survivors were enforced over all **24** unique gait frames.

**Result: ZERO of 36 passed all no-new-inversion, minimum-area, unchanged-other-ROI and under-half-count conditions.** Most sentinel/related masks moved damaging minimum-area failures to other frames such as 13, 15, 17, 19; large `all` exclusions removed some area defects but created many newly inverted surface normals. The highest raw improvement in global belly p95 seen in this test was about 0.0728, but it was anatomically rejected. This rules out these particular spatial-distance masks, not all possible localized skin weights.

## Round25 — 32 genuine Blender 24+1-frame smoothly blended IK/hip poses

Script: `round25_pose_phase_rescue.py`; workflow `fare-round25-phase-rescue.yml`.

[Actual Blender CI 43991284356](https://github.com/mehmetdem2005/Fare/actions/runs/43991284356); [per-profile 24-frame diagnostic JSON](https://github.com/mehmetdem2005/Fare/actions/runs/43991284356/artifacts/14288236877).

Sixteen predefined time-dependent profiles × two **separately opened** original-v8 and rejected-0.170 sources = **32 full 24+1-frame actions**. Each frame independently restores the original pose, then applies cyclic Gaussian hip X (-1°/-2°/-3°), hips Y, `spine_03` and/or four exact IK target offsets derived from Round23. Frame25 is phase-matched to frame1; all workflows explicitly verified ≤1e-5 seam. Every trial computes per-frame 1,069-face area and signed co-rotated normal, sixth-ROI edge strain and real evaluated Blender geometry; BVH is reserved for candidates satisfying all conservative fast gates first.

**Result: ZERO of 32 passed full numerical anatomy acceptance.** Representative rejected 0.170 cases:

- `hipx_w2.8`: improves full-cycle worst-belly p95 by ≈0.0767 vs v8, but new rest-normal inversion f10, excessive face-area loss at f7/8 and worst other-ROI framewise p95 regression ≈0.066.
- `hipx_and_handL`: prevents the 24-frame **minimum-area** regression seen in plain hip pulse, but **still introduces a normal inversion at f10**, increases count of sub-half-area triangles by 1 in its worst frame, and worsens other ROI p95 up to ≈0.066.
- `hipx_and_footL`: protects minimum-area minima at all frames but newly reverses normals at f9/10; worse other ROI p95 remains ≈0.066.
- Larger/constant hip X rotation often changes limb deformation substantially, and can cause f1/2 or f19 regressions. The strongest instant f14/17 intervention cannot safely be applied unchanged throughout the gait.

As before, green CI means the planned physical experiments ran and negative results are faithfully recorded; `numerically_passing: []` is the actual scientific conclusion.

## Refined mechanism and next non-blind work

1. Distinct skeletal poses **can** rescue local inverted/micro-area faces by large factors without changing weights. The underbody catastrophe is not solely an unsuitable scalar vertex-weight strength. However, rigid torso motion affects neighboring limb and ground-contact regions.
2. The damaging surface events are phase-dependent and not solved by merely applying one successful static correction with Gaussian fade. In particular f10 normal reversal and foreleg strain remain constraints.
3. The next technically defensible step is **anatomically constrained joint-local corrective skinning** (pose-space deformation based on measured bone transforms, not fixed frame number) paired with principled surface collision + orientable triangle **signed area** constraints and leg-root attachment anatomy. Original Blender v8 must remain the reference; glTF compatibility of nonstandard rig modifiers must be explicitly assessed. The old Round17 unsigned area optimizer (30 rejected variants) must not be reused.
4. Before another model release: assert full 24-frame no-new-inversions, area minimum, BVH nonincrease, six ROI p95, no new self-collapse, limb kinematics and actual foot-floor contact; then save/reopen real Blender, render all offending frames from multiple cameras, export GLB and test Godot mobile import. If any fails, no publication.
5. Keep exact failure triangles 434 (frame9/10/11), 216 (frame14), 812 (frame17) as sentinel tests. Round22 already tied their edge-weight gradients to `thigh.L/R`, `upper_arm.L/R`, `neck` and `spine_05`; no unique offending bone is proved.

**End status:** An additional 702 per-frame causal bone tests, 36 whole-cycle spatial-weight trials, and 32 whole-cycle animated-pose trials were completed. None produced an anatomically safe model; source and production files are intact. Do not label the torso repaired, visually accepted or export-ready.
