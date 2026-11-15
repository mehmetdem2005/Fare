# Round 10 — bone-by-bone torso repair and provisional extra gaits

**Verified GitHub Actions run:** https://github.com/mehmetdem2005/Fare/actions/runs/43757931419  
**Branch:** `rig-experiments/real-blender-ci`  
**Source:** `deliver/mouse_rig.blend` — 49 bones, 19,466 verts. The 41-bone conversation v6 model is DIFFERENT. Production main and deliver/ unchanged.

## Independently evaluated bone positions
- 19 bones, 228 individual rotations at frames 3/15 (per-bone ±12/±25° on X and ±12° on Z); actual Blender 5.1.2 depsgraph, [run 43755388898](https://github.com/mehmetdem2005/Fare/actions/runs/43755388898).
- 60 distributed spine phase profiles across six fixed ROIs, 24-frame regressions. Selected distributed total 4° phase correction: Spine_01 1.24°, Spine_02 1.16°, Spine_03 0.8°, Spine_04 0.48°, Spine_05 0.32°; hips +0°. The phase is reversed at extension frame 3 and compression frame 15.
- IK `use_stretch` toggles for individual limbs have NO effect in actual poses (bone length ratios ~1). Front IK reach limits reduced v4 stretch but contribute nothing beyond optimized spine positions, so no redundant clamp in delivered action.

## True final Blender L3 scores
Saved .blend reopened independently: `Reopen/reopened_v7_test.json` **PASS_TRUE_BAKED_SAME_AS_MANUAL**, difference 0 and loop seam 0.

| ROI | Previous worst p95 | New worst p95 |
| --- | ---: | ---: |
| Interleg abdomen | 1.63384 | 1.22509 |
| Anterior chest | 1.01767 | 0.69912 |
| Central torso | 1.36059 | 1.01461 |
| Forelimb | 0.31140 | 0.20074 |
| Rear torso | 0.20496 | 0.20832 (small regression) |

**Cannot call fully fixed.** Interleg p95 still >1 and visible mass folding persists, notably in compressed pose. Additional structural skinning and pose-space corrective morph work required.

## Major QA bug corrected
An intermediate test added the **25th duplicate closing frame** to a 24-frame mean but divided by 24, making a previously good saved action appear nonreproducible. Corrected `rows[:24]`. Independent debug run [43757035162](https://github.com/mehmetdem2005/Fare/actions/runs/43757035162) established exact mesh equality at 12 poses; closure frame 25 only used for seam QA.

## Two additional ORIGINAL animations — not video matched
User URL `https://youtube.com/shorts/Q3Wtmw3E7uE` inaccessible: direct web disabled and yt-dlp on GitHub runner HTTP 429/bot login. User reference movement was **not seen**. Therefore do not describe the following as exact animations from that video.

- `run_sprint_v7_ik_spine_repaired`: 24 frames @24fps, 0 seam, 124 GLB animation channels; best corrected existing bound.
- `walk_provisional`: 36 frames @24fps, 0 seam, 124 channels; provisional four-beat walk, interleg worst p95 .45542.
- `run2_provisional`: 24 frames @24fps, 0 seam, 124 channels; provisional faster paired run, interleg worst p95 1.17460.

Three separate GLBs exported with 1 skin each, plus combined editable .blend and three rendered preview GIFs. Six viewpoints at frames 3 and 15 included in GitHub artifact. All actions labeled **experimental**, not a production pass, and not Godot mobile L5-tested.

## Reproduction
Scripts in `rig-experiments/`: `individual_bone_ik_sweep.py`, `optimize_spine_phase.py`, `verify_phase_and_ik.py`, `reopen_verify_v7.py`, `add_walk_run2.py`, `export_3_gaits.py`, `render_three_gaits.py`. Workflow `.github/workflows/fare-three-gaits-after-repair.yml`.

Persistent lessons in user Library `RIGGING_WEIGHTPAINT_EXPERIENCE.md`. No automatic weights. No production changes.
