# Fare — Round26–37 verified signed-area morph, existing driver, and BVH collision experiments

**17 November 2026 (Europe/Istanbul) — DEFORMATION NOT YET SOLVED. NO SAFE CANDIDATE GLB.**

This is the continuation of [Rounds 23–25](ROUND_23_25_BONE_IK_SPATIAL_REPAIR_EXPERIMENTS_2026-11-17.md) and [Round22 verified triangle-to-bone causality](ROUND_22_VERIFIED_FAILURE_FACE_BONE_TRACE_2026-11-17.md). All runs used real **Blender 5.1.2** under GitHub Actions, on the isolated `rig-experiments/real-blender-ci` branch. A green CI means an experiment executed successfully; the real scientific result can be **a rejected candidate**.

## Unchanged model provenance and scope

- `deliver/mouse_rig.blend`: SHA256 `173ca67a372f5c04f27d922ef02f37921bbaf184cff0094976df326b4ec095b6`; 49 bones, 19,466 vertices; untouched.
- Verified original v8 24-frame action `run_sprint_v8_ik_phase_NUMERIC_REVIEW` from Actions run 43767152372, SHA256 `984a21447c0217bc8ff91d02f9af1509324aa94dfaf29c543abd3d92f9b12c70`.
- Independently saved **rejected** strength 0.170 original-weight candidate from 43867305596, SHA256 `cb67f61b9a1a771366df53b10b89e1bec827c81450e2bac300be2c96b52e85bc`. The modifications affected exactly 290 eligible vertices in the underbody. This rejected candidate is experimental input only, never a new original.
- No Automatic Weights; no mutation of `deliver/`, production GLB, default branch, or original v8 action. No model has passed real Blender *full 24-frame* L3 area + orientated-normal + ROI strain + per-frame nonadjacent BVH. L4 human anatomy/footfall and L5 exported GLB/Godot/Android not approved.

## Continuous experimental evidence

| Round | Actual GitHub Actions run | Tested | Verified result |
|---|---|---|---|
| 26 | [44089608998](https://github.com/mehmetdem2005/Fare/actions/runs/44089608998) | 8 24-frame profiles, 7 inverse-skinned face-corrective poses | Local f14 triangle216 area .005→.300, f17 triangle812 .009→.300; temporal use introduces other area losses f14/f17; no eligible candidate |
| 27 | [44089855808](https://github.com/mehmetdem2005/Fare/actions/runs/44089855808) | 144 genuine independent manual shape-driver tests + every driver every 24 frames | Original v8 `crv_shoulder` (12–13 active frames), `crv_hip` (12–13), `crv_spine` (12), `crv_elbow` (10) really activate; not a global missing-driver problem |
| 28 | [44090137690](https://github.com/mehmetdem2005/Fare/actions/runs/44090137690) | 8 jointly guarded multi-face pose morphs | Four narrow/medium profiles cleared all-frame minimum-area and new normal-inversion regressions, improved belly worst p95 by ~.07694, but inherited central ROI p95 worsened ~.01845 |
| 29 | [44090938702](https://github.com/mehmetdem2005/Fare/actions/runs/44090938702) | 8, central 81-vertex source-restoring morphs | Worst ancillary ROI regression ~.01148, not safe |
| 30 | [44091575292](https://github.com/mehmetdem2005/Fare/actions/runs/44091575292) | 8, exact 290-vertex inverse-skin restoration at five key frames | At strength .65: safe area/normals, belly p95 improved ~.04671, worst other ROI +.005894 |
| 31 | [44091932003](https://github.com/mehmetdem2005/Fare/actions/runs/44091932003) | 12 intermediate-strength corrective profiles | Strength .92: worst other ROI +.00380048, belly worst p95 improved ~.0281473; but f9 under-half-area count regressed |
| 32 | [44092364995](https://github.com/mehmetdem2005/Fare/actions/runs/44092364995) | Independent f9 exact face indices on 2 best trial profiles | f9 faces **465** `[774,586,879]`, baseline ratio .500617→.474608; and **809** `[7231,7045,7390]`, baseline .500750→.497410. Two newly under-half faces, not one |
| 33 | [44093056389](https://github.com/mehmetdem2005/Fare/actions/runs/44093056389) | 12 phase-9-only inverse morph gains, 24 frames each | Ten profiles pass area, signed normal, count and 6-ROI strain fast gates. **All fail BVH**: f8 1→2 overlaps and f14 27→33 (at stronger morph); some f9 3→5 |
| 34 | [44093514687](https://github.com/mehmetdem2005/Fare/actions/runs/44093514687) | 25 crossed frame8 and frame14 shape amplitudes | Frame8 1→1 (BVH protected with f8 factor .50), f14 best 27→30. All face and ROI fast gates passed, but no full L3 |
| 35 | [44093935312](https://github.com/mehmetdem2005/Fare/actions/runs/44093935312) | 10 f14 morph gains .10–.62 | Below factor .42, minimum triangle area regresses; .42 preserves area baseline .05642→.05775 but BVH 27→30. No amplitude-only solution |
| 36 | [44094307427](https://github.com/mehmetdem2005/Fare/actions/runs/44094307427) | Exact f14 nonadjacent BVH intersection pair trace | **16 new** colliding face pairs, **13 former** collisions relieved, total **27→30**. Pairwise changes, not just 3 isolated pairs |
| 37 | [44094848226](https://github.com/mehmetdem2005/Fare/actions/runs/44094848226) | 24 variants splitting f14 corrective into independent two mesh-local anatomical bands | **11** moved verts in front band, **5** in rear. Split exactly reconstructs original full morph: max evaluated coordinate error **0**. All 24 variants fail 14th-frame BVH 27→at least30, although most pass other fast gates |

The exact run artifacts are retained at the associated Actions run; reports `round26_signed_normal_correctives.json` through `round37_anatomical_patch_split.json` record the full 24-frame anatomy metrics. Every experimental code file is prefixed `rig-experiments/roundXX_` and its own workflow is under `.github/workflows/fare-roundXX-`.

## Why the former apparent fix is not an actual fix

The gait's microfold is **not a single frame-independent scalar strength or missing shape driver**. Precisely correcting signed, co-rotated f14 face area changes which neighboring underbelly triangle sheets overlap. The spatial area, normal and ROI metrics can be good while the BVH reveals new nonadjacent face intersections. For example, f14 candidate with shape factor .42 has minimum rest-normalized area **.057750** versus v8 **.056423** (passes), but BVH overlaps **30** versus original **27** (fails).

Round36's 16 newly overlapping face pairs at frame14 include:
- `(180,190)`, `(186,190)` near the first chest fold;
- `(211,214)`, `(213,223)`, `(214,217)`, `(214,223)`, `(215,218)`, `(215,221)`, `(215,224)` near abdominal face 216;
- `(224,474)`, `(343,474)`, `(350,474)`, `(363,476)`;
- `(464,468)`, `(465,468)`, `(466,473)`.
The same pose also **removed 13** formerly overlapping pairs. These are deterministic BVH *triangle-pair* collisions under a fixed epsilon; they are not watertight volumetric intersection measures. Some f15 collision pairs are also rearranged despite the **total** f15 count improving 66→35. Per-frame and per-pair checks are both required.

The f14 signed patch is disjoint under vertex-band split: front IDs `[671,731,774,911,998,1389,1402,2018,2936,3095,3196]`, rear IDs `[7390,7562,7772,8331,8410]`. Every split test reconstructed the combined morph exactly at equal strength, then screened different strengths. The f14 **front** patch strength determines the minimum-area vs BVH conflict; the rear patch was not able to eliminate new overlaps. This excludes yet another blind intensity sweep.

## Scientifically required next method

1. Implement a **signed-area-constrained local *collision* solver** targeting actual R36 triangle-pair intersections, not just degeneracy/edge p95. It must use triangle–triangle penetration/contact witnesses, so a simple BVH count or triangle centroid distance alone is **not** a physically valid collision gradient.
2. Operate on the 11-vertex frontal f14 pocket only plus a regularized neighboring 1-ring where anatomically safe. Avoid new BVH pairs at any of the 24 frames; preserve the original oriented normals, local minimum areas, under-half-face counts, loop seam and all six ROI strain limits.
3. Test correction in **real Blender 5.1.2**, with true per-vertex inverse armature skinning, zero-state-leak checks and a saved/reloaded candidate. *Only if a candidate clears all gates* should it be saved as an experimental .blend.
4. For real acceptance, render both side and underneath views across the 24-frame loop, check kinematics/foot-ground contact, bake glTF-compatible keyframed shape keys, export GLB, reimport and inspect in the actual Godot/Android target. These L4/L5 steps remain **NOT DONE**.

**Final status at Round37: no fully approved fixed mouse rig, no exported GLB, and no model in `deliver/` has been altered.** All original source and previous snapshots are preserved.
