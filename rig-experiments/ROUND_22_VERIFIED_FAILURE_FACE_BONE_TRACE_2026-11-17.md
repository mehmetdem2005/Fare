# Round22 — verified Blender LBS hotspot and bone-gradient forensic analysis

**Date:** 17 Nov 2026 (Europe/Istanbul). **Status:** PASS L3 mechanistic forensic analysis; FAIL / UNFIXED anatomical result. **No repaired GLB/BLEND delivered.**

## Files, source identity and final CI

- Repository: `mehmetdem2005/Fare`; experiment branch `rig-experiments/real-blender-ci`. No default/production branch edits.
- Authoritative original `deliver/mouse_rig.blend` unchanged SHA256 `173ca67a372f5c04f27d922ef02f37921bbaf184cff0094976df326b4ec095b6`, 49 bones, 19,466 vertices.
- Compared verified v8 gait BLEND SHA256 `984a21447c0217bc8ff91d02f9af1509324aa94dfaf29c543abd3d92f9b12c70` against independently saved/reopened 0.170 candidate SHA256 `cb67f61b9a1a771366df53b10b89e1bec827c81450e2bac300be2c96b52e85bc`.
- Script `rig-experiments/round22_failure_face_bone_trace.py`; runner `.github/workflows/fare-round22-hotspot-bone-trace.yml`.
- [Final verified Round22 CI](https://github.com/mehmetdem2005/Fare/actions/runs/43983176789), [artifact containing exact 199 hotspot records and 9-frame LBS per-bone decomposition](https://github.com/mehmetdem2005/Fare/actions/runs/43983176789/artifacts/14283876918). Final code commit `c87aa030e0d5cc3f9d7c08de47f7b52f7e1d04c8`.
- Strictly compare SAME triangle ID and SAME baseline-selected edge across saved original/candidate, not different independently chosen edges. The previous experimental Round22 run `43982748886` had varying baseline/candidate chosen edges: it was corrected and superseded by the final run above.
- The script independently opens both actual Blender files, evaluates the original run action on frames **7, 8, 9, 10, 11, 14, 15, 16, 17**, and traces exact fixed original triangle vertices, reference normal sign, face area and new nonadjacent BVH pairs.
- Before using any theoretical LBS attribution, actual armature bone matrices, evaluated pre-armature mesh (shape-key enabled), original vertex weights and original Blender dependency-graph result are cross-checked. LBS prediction maximum selected-vertex error: **original 5.192071149038655e-8; candidate 4.9421560620597e-8 model units**. Decomposition of each selected common edge into common-transform plus spatial weight-gradient terms passed its algebraic identity. Hence the measured weight/rotation mechanism is grounded in real Blender and not a standalone abstract proxy.

## Exact persistent geometric hotspots

All vertex IDs below refer to the SAME unchanged 49-bone mesh topology; area ratios are nonnegative posed triangle area divided by ORIGINAL rest area, not enclosed-volume ratios.

| Gait frame | Triangle ID | Vertex IDs | Baseline same-face area ratio | Candidate same-face area ratio | Interpretation |
|---|---|---|---:|---:|---|
| 7 | 467 | 671,774,731 | 0.373478 | 0.200123 | New local reduction without normal reversal |
| 8 | 351 | 1317,703,980 | 0.336489 | 0.162415 | New local reduction |
| 9–11 | **434** | **218,270,586** | see JSON | see JSON | **NEW corotated-rest normal inversion on all three frames** |
| 14 | **216** | **2018,1402,1389** | **0.096958** | **0.005003** | Near-degenerate triangle; locally much WORSE |
| 17 | **812** | **7562,7390,7772** | **0.099883** | **0.008593** | Near-degenerate triangle; locally much WORSE |

Also see Round20 for per-frame global minima rather than same-face comparisons. For example f7's global baseline min 0.293784 comes from a different face than candidate face 467, baseline 0.373478.

In frame10's inverted face 434, exactly the same canonical original-selected edge [586,218] has LBS gradient/rest-edge magnitude **1.355183 (original)→1.323270 (candidate)**. The negative flip occurred **despite the scalar gradient magnitude decreasing** — illustrating orientation and vector cancellation effects.

At frame14 triangle 216, fixed edge [1402,1389] similarly changed from gradient/rest-edge **1.106449→1.004475**, while face area collapsed to 0.005003. At frame17 triangle 812, fixed edge [7772,7562] went from **0.774432→0.714617**, yet area fell 0.099883→0.008593. This is why prescribing more weight smoothing purely from a decreasing gradient magnitude is unsafe.

The f10 new-inversion hotspot is influenced by **thigh.L, neck, spine_05, upper_arm.L** across its selected edge. At f14 the near-degenerate triangle features **upper_arm.L / thigh.L** blend; f17 has **upper_arm.R / thigh.R** blend. These are measured influences at observed vertices, **not yet a proven unique anatomical repair**.

Over 199 selected face-frame samples the summed absolute spatial weight discontinuities (a heuristic sample-weighted diagnostic, **NOT absolute causal ranking or percentage of distortion**) were led by thigh.L 16.4154, upper_arm.L 13.2937, thigh.R 10.8003, upper_arm.R 10.6809; other sampled groups include neck 3.4779, shin.R 2.3574, spine_05 2.1057. Sampling is hotspot-biased and repeats faces across frames, so rankings must not be generalized to the whole torso.

## Scientific conclusion

- **Failed hypothesis:** constant-strength, whole-belt longitudinal redistribution between front upper arms and rear thighs, despite improving overall 24-frame interleg p95, cannot preserve correct triangle orientation and minimum areas throughout this gait; all 0.168/0.170/0.175/0.200 were rejected by Round21.
- **Positive observation:** direct LBS weight/bone coupling explains evaluated Blender mesh positions to numerical precision; failures are actual skin-deformed surfaces and not just CI stale caches or mismatched saved files.
- **Negative/remaining uncertainty:** this is still not a full causal proof that ONE named bone is at fault. Normal flips, triangle area loss and overlaps reflect nonlinear combined bone rotation + spatially varying weight effects. Reducing a scalar local gradient did not guarantee correct oriented surface. BVH overlap count is a proxy and full volume, muscle, self-intersection, plantar contact and gameplay are untested.

## Next constrained intervention (not performed or approved)

1. Use triangle 434 f9/10/11, triangle 216 f14, triangle 812 f17, and f7/8 hot triangles as regression sentinels.
2. Build anatomically restricted experimental ablations of front/hind hip-to-shoulder IK target frames and local weight *direction*, **never just scale**, one isolated control at a time with exact resets. Include post-armature face normals and area during solving and check limb-root separation.
3. Compare every frame 1..24 plus 25 seam, not only hotspot frames. Include six ROI p95/p99, per-frame 1069-triangle minimum/p05 signed normal checks, BVH, and actual real Blender camera views. Reject any new inversion, BVH increase, minimum-area significant loss, foreleg strain regression or new sliding.
4. Verify any candidate by independent save/reopen and original-provenance signature. No production `deliver` copy, no default merge, no finished GLB until L4 anatomy and L5 Godot/Android verification separately pass.
5. Maintain this report and [Round18–21 findings](ROUND_18_21_SAVED_WEIGHT_AND_FULL_CYCLE_FINDINGS_2026-11-17.md) as negative and positive technical evidence. Never state a complete repair based only on CI success.

**Final scientific disposition: L3 forensic trace succeeded; skin deformation repair remains unresolved.**
