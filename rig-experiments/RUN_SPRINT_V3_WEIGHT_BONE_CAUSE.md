# Sprint v3 – Deep abdomen bone/weight analysis (2026-11-15)

**Scope:** GitHub `deliver/mouse_rig.blend`, 49 bones / 19,466 vertices. NOT the separate conversation 41-bone v6 model. All tests use Blender 5.1.2 real dependency-graph evaluated mesh. `main` and original `deliver/` assets remain unchanged.

## Confirmed root causes

- **Severe cross-limb weight assignment on the same body skin.** Fixed anterior ROI: 2,125 verts / 6,045 edges, 2,124 belong to `part_id=6` (body mesh). 215 vertices have simultaneous `upper_arm` and `thigh` weights >0.1. Narrow interleg abdomen ROI: 160 / 487 mixed verts; aggregate upper-arm 34.4%, hind-thigh 48.9%, spine ~0.7%. This suggests a skin transition requiring local anatomical control, not blanket normalization.
- **Very abrupt proximal-to-distal forelimb weight curves.** Edge 2714–2733 changes `upper_arm.L` 0.9187→0.0883, `hand.L` 0.0386→0.5782 and additional forearm influence. Frame 3 relative edge stretch 4.27345. In first-frame top 60 edges, 44 include upperarm+thigh; frame 9 top 60, 47 include upperarm+forearm/hand.
- **Rig interplay:** six-phase fixed ROI mean p95 0.56744 full; front IK disabled 0.33634, hind IK disabled 0.45714, all spine rotations off 0.40644, all 4 IK off 0.14716. Hip rotation off **worsens** p95 to 0.62524. These are isolation tests, NOT viable gait fixes.
- **Not a weight-normalization or tiny-edge artifact:** weights sum 0.99999996–1.00000004, no >4-influence vertices in fixed ROI; p95 stable across minimum rest edge lengths 0.000001–0.005. Independent full-pose crosscheck 6/6 phases pass.

## Trials and acceptance

1. [Deep joint/weight audit L3 PASS](https://github.com/mehmetdem2005/Fare/actions/runs/43745590181).
2. [Direct fore/hind→spine transfer](https://github.com/mehmetdem2005/Fare/actions/runs/43746008617): **REJECTED**. Interleg worst p95 2.0636→2.3884 (60%) or 3.2432 (95%), despite some wide-ROI gain.
3. [Initial topological smoothing](https://github.com/mehmetdem2005/Fare/actions/runs/43746482316): mixed gains, posterior regression. **REJECTED for production**.
4. [Flank-protected topological smoothing](https://github.com/mehmetdem2005/Fare/actions/runs/43746691237): 267 vertices adjusted, weight sums preserved within 3e-8; interleg worst p95 2.0636→1.7959 (-12.97%), anterior chest 1.2745→1.2084 (-5.18%), central torso worst unchanged 1.4222, posterior worst 0.23805→0.23834 (small regression), distal foreleg unchanged. **EXPERIMENT ONLY; NOT PRODUCTION ACCEPTED** due severe remaining strain.

## Next pipeline requirements

- Separate foreleg elbow/paw `upper_arm→forearm→hand` transition from mixed interleg `upper_arm↔thigh` and central torso; do not use a single blanket mask.
- Analyze and validate full IK-generated upper-arm local transforms, actual elbow/shoulder corrective morph driver activation, and phase-lock foot targets with spine.
- For each future trial, compare the *same fixed IDs and same full sprint frames* in interleg, anterior chest, central belly, posterior torso and distal foreleg; weight conservation alone is not enough.
- Reject any solution with material regressions or unresolved 100%+ relative strain. Workbench multiple POV/real game GLB L4–L5 gates remain open.

See the linked GitHub Action artifacts for full `bone_weight_root_cause.json`, candidate `ventral_weight_trials.json` and `topology_weight_trials.json`. Additional persistent notes are stored in `RIGGING_WEIGHTPAINT_EXPERIENCE.md` (user Library).
