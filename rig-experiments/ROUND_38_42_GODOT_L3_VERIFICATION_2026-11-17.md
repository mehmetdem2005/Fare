# Fare — Rounds 38–42, saved candidate and real Godot 4.7.2 import

**17 November 2026.** Experimental branch only: `rig-experiments/real-blender-ci`. This document records real workflows and scientific negative findings, not a production release.

## Immutable provenance

- Original `deliver/mouse_rig.blend`: SHA256 `173ca67a372f5c04f27d922ef02f37921bbaf184cff0094976df326b4ec095b6` **untouched** (49 bones, 19,466 vertices).
- Original saved v8 `run_sprint_v8_ik_phase_NUMERIC_REVIEW`: SHA256 `984a21447c0217bc8ff91d02f9af1509324aa94dfaf29c543abd3d92f9b12c70`. Original static-weight 0.170 candidate from Round19D was NOT promoted to production.
- **Review-only saved corrected BLEND**: `R39_SAVED_NUMERIC_REVIEW_ONLY.blend`, SHA256 `bf24c3c00367790af976e5f407cb9c3b20ad11754845bd0eb63d5cbe4042d07b`, 3,919,385 bytes.
- **Review-only generated GLB**: `R41_FARE_49BONE_SPRINT_CORRECTED_REVIEW_ONLY.glb`, SHA256 `351a9475aeb6142331e4bc296aee957648cb055c7afc9988943a12c559c937d2`, 5,094,784 bytes.
- No Automatic Weights. Neither candidate nor exported GLB was written under `deliver/`.

## Verified experiments and negative records

**Round38 [real Blender Actions 44115168117](https://github.com/mehmetdem2005/Fare/actions/runs/44115168117)**: New pair-specific signed triangle-plane contact solver, original v8 reference, 60 local candidate vertices, 16 new intersecting BVH pairs. Could not reduce f14 30 overlaps (zero accepted geometry steps), because a source-near mesh may straddle the opposing plane without intersection. An intentional negative outcome, documented fully in `round38_contact_constrained_pose.json`.

**Round39 [run 44116055380](https://github.com/mehmetdem2005/Fare/actions/runs/44116055380)**: For problem frame14 only, use actual independently saved original v8 vertex positions as a localized inverse-skinned corrective pre-armature shape key. All 290 edited underbody vertices restored at that phase, world readback error **4.47e-8**, no clipped inverse skin offsets. Ten temporally constrained variants evaluated with real Blender 5.1.2 over 24 unique sprint frames plus f25 seam. **Six** passed every numerical L3 guard: no new source-corotated normal inversions, no increased under-half-area face count, no min-area regression, no increases in nonadjacent BVH overlaps, belly worst p95 improvement >.01 and other five region p95 regression <.004. Saved the best review candidate (0.90 strength, 0.20-frame-width).

**Round40 initial [run 44116812155](https://github.com/mehmetdem2005/Fare/actions/runs/44116812155)**: QA initially incorrectly called a constraint/IK-affected action=None evaluated mesh a true rest mesh and flagged weight-driven differences as a failure. This was a **false rest-pose test**; replaced with an *actual raw mesh vertex Basis datablock* and 49-bone rest-matrix comparison. Do NOT use constraint-evaluated neutral geometry as a rest-identity invariant.

**Round40 corrected [run 44117099050](https://github.com/mehmetdem2005/Fare/actions/runs/44117099050)**: Independent official Blender 5.1.2 process reopened the exact saved BLEND SHA and revalidated raw rest vertices, all original bone rest matrices and sampled animation matrices (all **zero drift**), actual baked f14 shape-key value **0.899999976**, f1/f25 zero values, 24-frame surface orientation, 1069 body triangles, six ROI p95 strain, BVH and cycle seam. Exact metric deviation from the original in-memory experiment **3.10698e-7**, zero L3 issues. Comparison images rendered at 9/10/14/17 from four actual Blender cameras.

**Round41 [run 44117917452](https://github.com/mehmetdem2005/Fare/actions/runs/44117917452)**: Real Blender binary glTF 2.0 exporter generated 5.094784 MB review GLB, **148 source animation channels** including 49 rotation and one combined morph-weight channel. Contains all **29 named morph target shapes**, including `R39_F14_ORIGINAL_REFERENCE`. Fresh Blender scene re-import recognized armature, mesh, shape keys and animation action.

**Round42 [run 44118905249](https://github.com/mehmetdem2005/Fare/actions/runs/44118905249)**: OFFICIAL Godot **4.7.2-stable** real Linux headless editor imported the exact R41 GLB, then a separate SceneTree script loaded and instantiated the imported PackedScene. Report: **Skeleton3D=1, bones=49; MeshInstance3D=1; blend shapes=29; corrected f14 morph found; AnimationPlayer=1, animation `MouseRig`, total Godot tracks=68, blendshape tracks=29, skeletal rotation tracks=34.** No script-reported import issues. This is a real Godot import (not just glTF JSON parsing), but **not Android rendering/performance**.

## Independent source-relative anatomical measurements

| Metric | Original v8 | Saved Round39 |
|---|---:|---:|
| 24-frame worst interleg p95 edge strain | 1.034969588 | **1.009359996** |
| f14 nonadjacent surface BVH pairs | 27 | **27** |
| f14 minimum rest-normalized triangle area | 0.056422795 | **0.065390747** |
| f14 body faces below half rest area | 185 | **183** |
| Any newly reversed rest-oriented normals across the gait | — | **0** |
| Worst other-region frame p95 increase | — | **0.002936317** (limit 0.004) |
| Source 49 bone animation matrix drift | — | **0.0** |

## Unresolved production gates

- Numerically accepted L3 **is NOT proof of a flawless anatomical mesh**. The reference itself has folds and 27 f14 BVH contacts; side/bottom images still show visible forelimb and belly creases. **L4 human anatomy approval NOT granted**.
- Godot 4.7.2 imported the GLB successfully but did not validate actual Android 11 Mali GPU frame rate, memory, live playback or foot-floor contact; real **Android gameplay L5 remains NOT TESTED**.
- Do not merge candidate into `deliver/`, default branch, game character release or existing GLB without explicit visual/anatomical and device acceptance.
- All future appearance fixes require the entire independent 24-frame Blender, GLB and Godot test chain rerun. Keep both source SHA and saved candidate evidence for regressions.

**Status: saved and independently verified corrected experimental model/GLB, Godot importer PASS. Production NOT APPROVED.**
