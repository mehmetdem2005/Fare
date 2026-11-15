# Round 11–13: 49-bone mouse abdominal deformation forensic audit (16 Nov 2026)

**STATUS: ÇÖZÜLMEDİ. No production promotion.** Repo: mehmetdem2005/Fare. Branch: rig-experiments/real-blender-ci. Original deliver/mouse_rig.blend (49 bones; 19,466 vertices; SHA256 173ca67a372f5c04f27d922ef02f37921bbaf184cff0094976df326b4ec095b6) and main/default branch unchanged. No Automatic Weights.

## Verified real Blender CI and data

- [Round 11 — 684 isolated bone tests, 6 localized weight trials, f1/f15 multiangle renders](https://github.com/mehmetdem2005/Fare/actions/runs/43765333116); artifact 14181519107; JSON Round11/round11_rootcause.json.
- [Round 12 — 96 independent true IK XYZ target tests, 6 full-cycle IK profiles, 4 neck weight-transfer tests](https://github.com/mehmetdem2005/Fare/actions/runs/43766185704); artifact 14182725530.
- [Round 13 — 10 combined fore/hind IK phase profiles and Blender preview renders](https://github.com/mehmetdem2005/Fare/actions/runs/43766568736).
- [Round 13 independent saved BLEND reopening and unchanged skin/constraints verification](https://github.com/mehmetdem2005/Fare/actions/runs/43767152372); artifact 14182499331. Blender 5.1.2 success. Exact saved-action metric delta 0.0, original action delta 0.0, 0.0 loop seam; 49 bones, 19,466 vertices. Only numeric L3 PASS, not L4 acceptance.

## 1. Causal mechanism: evidence, not guesswork

Worst extension is frame 1, worst compression frame 15 in the latest v7. Interleg ROI has 608 body vertices and 1,676 edges. Frame 1 actual evaluated edge 154–270 has length ratio 3.343 relative to rest. Vertex 154 has weights neck 0.360855, thigh.L 0.278291, spine_05 0.360855; vertex 270 neck 0.216903, upper_arm.L 0.388728, thigh.L 0.190973, spine_05 0.203397. Another edge 731–774 has ratio 3.335; upper_arm.L endpoints 0.697132 vs 0.399925 and thigh.L endpoints 0.241645 vs 0.544663. Edge 3369–3377 ratio 3.275. Anatomically connected upper and lower limbs can legitimately influence the torso, but these specific mixed and rapidly changing weights contribute to severe actual skin stretching.

Importantly, a commanded local Euler rotation on upper_arm.L/R or thigh.L/R caused 0 degrees REAL evaluated rotation: IK constraints control them. Shifting real IK targets alters the same belly surface, proving a causal IK/skinning interaction. Round 12 single frame 1: ik_hand.L target Y+0.006 model units moved the target by 0.006000012 and reduced belly p95 by 0.058065. This is meaningful causal evidence, but a complete physical root cause for all folds remains unverified.

## 2. Bone-by-bone tests

Nineteen: hips; spine_01 through spine_05; neck; shoulders L/R; upper arms L/R; forearms L/R; hands L/R; thighs L/R; shins L/R. Each X, Y, Z ±3°, ±6°, ±12° on frame 1 and frame 15: 684 controlled trials with evaluated bone matrix and region-level edge scores. Round 11 JSON records every case. Frame15 hips X−6° improved belly p95 0.332 but worsened foreleg 0.186, so rejected. Quaternion angular logging was corrected to shortest equivalent angle in commit 7c78e10f176dc40062b48294d241b7ed8ff9b1ae.

## 3. Weight trials and failures

Six trials locally transferred upper_arm.L/R vs thigh.L/R ratios at fixed hotspot vertices. L 25% on 66 vertices improved interleg worst 1.225087 → 1.187013 but worsened central mean 0.536521 → 0.539647 and had virtually no visible improvement in rendered images; rejected as complete fix. R 50% / 75% raised worst belly stress by 0.007785 / 0.014696. Four neck→spine_05 trials on 27 vertices: even complete transfer improved worst belly by just 0.016161 but worsened central mean by 0.01932; rejected. All test weights restored to original state before next trial. Original source weights unchanged.

## 4. Best experimental combined IK candidate

The independently measured 24-frame profile front_and_hind_006 shifts ik_hand.L/R Y +0.006 and ik_foot.L/R Y −0.006 model units near the f1 extension peak via cyclic Gaussian phase taper.

| Worst p95 absolute relative edge stretch | Original verified v7 | Experiment v8 |
|---|---:|---:|
| Belly interleg | 1.225087 | **1.034970** |
| Front torso | 0.699140 | **0.605725** |
| Central belly | 1.014614 | **0.851305** |
| Rear | 0.208631 | 0.208669 (small regression) |
| Foreleg | 0.201359 | 0.201364 (small regression) |

Experimental candidate: Round13/run_sprint_v8_ik_phase_NUMERIC_REVIEW.blend SHA256 984a21447c0217bc8ff91d02f9af1509324aa94dfaf29c543abd3d92f9b12c70. Real Blender manual vs baked max vertex error 0.0. Reopened action score errors 0.0 and original action, mesh, weights, constraint signature preserved. Both 24-frame loop seams 0.0. Not exported as final GLB.

## 5. Visual evidence and unresolved failures

Workbench renders from left/right/front/back/top/bottom/two three-quarter views were produced for both baseline and candidate at f1 and f15, plus closeups. Viewed before/after comparison; still substantial elongated/undercut belly on f1 and compressed folded lower torso on f15. Therefore **L4 visual anatomical acceptance fails** despite strong numeric improvement. In particular worst belly p95 remains >1.0, meaning some local body surface edge lengths remain more than doubled.

Still NOT verified: robust self-intersection, surface normal inversions, actual volume conservation, paw ground contact/slip, full 24-frame v8 GIF or Godot/Android L5 import/playback. Never claim complete correction, production ready, or a reference-video-matched walk/run.

## 6. Next evidence-based intervention

From exact f1 excessive edge/vertex and f15 compression maps, build combined-IK-pose corrective shape keys for anatomically segmented body skin (part_id=6), rather than blanket smoothing or all weights to spine. Test actual 24 frames and f25 seam; per-edge p50/p90/p95/p99/max, triangle area, normal inversion, local self-intersection, paw contact, eight camera positions. Reject if any major new foreleg or pelvis defects occur. Reopen the BLEND and independently verify after save. Only after visual quality acceptance: separate walk, second run, animated GLB, Godot/Android.

**Technical memory:** appended rounds V/W/X to the user's exact Library RIGGING_WEIGHTPAINT_EXPERIENCE.md, with CI IDs, SHA256, failures, next steps. Do not promote or merge the NUMERIC_REVIEW model.