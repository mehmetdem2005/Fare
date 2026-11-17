"""Measure live and single-transform interventions on the saved Fare rig."""
import argparse
import gzip
import hashlib
import json
import math
import runpy
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix

sys.path.insert(0, str(Path(__file__).resolve().parent))
from anatomy_baseline import ACTION, HERE, SENTINELS, array, normals

BONES = ("hips", "neck", *(f"spine_{i:02}" for i in range(1, 6)),
         *(f"{name}.{side}" for side in ("L", "R")
           for name in ("shoulder", "upper_arm", "forearm", "hand", "thigh", "shin")))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--frames", type=int, nargs="+", default=[7, 8, 9, 10, 11, 14, 15, 16, 17])
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    args.out.mkdir(parents=True, exist_ok=True)
    h = runpy.run_path(str(HERE / "round14_skinning_forensics.py"))
    bpy.ops.wm.open_mainfile(filepath=str(args.source.resolve()))
    obj = bpy.data.objects["Mouse"]
    mod = next(m for m in obj.modifiers if m.type == "ARMATURE")
    arm = mod.object
    ad = arm.animation_data
    action = bpy.data.actions[ACTION]
    for track in ad.nla_tracks:
        track.mute = True
    tri = np.array(list(SENTINELS.values()))
    areas = np.linalg.norm(normals(array([obj.matrix_world @ v.co for v in obj.data.vertices]), tri), axis=1)
    weights = [h["weights"](obj, i) for i in range(len(obj.data.vertices))]
    names = [b.name for b in arm.data.bones if b.use_deform]
    weights = np.array([[w.get(name, 0.) for name in names] for w in weights])
    cumulative = weights.sum(axis=1)
    weights /= np.where(cumulative > 0, cumulative, 1)[:, None]
    world = obj.matrix_world.copy()
    key_blocks = list(obj.data.shape_keys.key_blocks)[1:]
    key_data = obj.data.shape_keys.animation_data
    drivers = [(f, f.mute) for f in key_data.drivers] if key_data else []
    report = {"source_sha256": hashlib.sha256(args.source.read_bytes()).hexdigest(),
              "blender": bpy.app.version_string, "frames": {}}
    with gzip.open(args.out / "bone_trials.jsonl.gz", "wt") as records:
        for frame in args.frames:
            h["reset"](arm, action, frame)
            base_points = h["pts"](obj)
            base = array(base_points)
            before = h["get_input"](obj, mod)
            transforms = h["vmat"](obj, arm)
            live_bases = {b.name: b.matrix_basis.copy() for b in arm.pose.bones}
            live_matrices = {b.name: array(b.matrix) for b in arm.pose.bones}
            baseline_area = np.linalg.norm(normals(base, tri), axis=1) / areas
            before_array = array(before)
            manual = np.zeros_like(base)
            for name, matrix in transforms.items():
                idx = names.index(name)
                m = array(world @ matrix @ world.inverted())
                mask = weights[:, idx] > 0
                manual[mask] += (before_array[mask] @ m[:3, :3].T + m[:3, 3]) * weights[mask, idx, None]
            manual[cumulative == 0] = before_array[cumulative == 0]
            error = float(np.linalg.norm(manual - base, axis=1).max())
            report["frames"][frame] = {"max_lbs_readback_error": error, "comparisons": {}}
            if mod.use_deform_preserve_volume or error > 1e-5:
                raise ValueError(f"Isolated LBS control invalid at frame {frame}: {error}")
            for name, value in [("preserve_volume", True), ("linear", False)]:
                mod.use_deform_preserve_volume = value
                bpy.context.view_layer.update()
                x = array(h["pts"](obj))
                report["frames"][frame]["comparisons"][name] = {"area_ratios": (np.linalg.norm(normals(x, tri), axis=1) / areas).tolist()}
            def summarize(points):
                return (np.linalg.norm(normals(array(points), tri), axis=1) / areas).tolist()
            key_action = key_data.action if key_data else None
            if key_data:
                key_data.action = None
            initial_keys = [(k, k.value, k.mute) for k in key_blocks]
            for f, _ in drivers:
                f.mute = True
            for key, _, _ in initial_keys:
                key.mute = True
            bpy.context.view_layer.update()
            report["frames"][frame]["comparisons"]["all_correctives_off"] = summarize(h["pts"](obj))
            for key, value, mute in initial_keys:
                key.mute = False
                key.value = 1.
                bpy.context.view_layer.update()
                report["frames"][frame]["comparisons"][key.name] = {"saved_value": float(value), "solo_at_one": summarize(h["pts"](obj))}
                key.mute = True
                key.value = value
            for key, value, mute in initial_keys:
                key.mute = mute
                key.value = value
            for f, mute in drivers:
                f.mute = mute
            if key_data:
                key_data.action = key_action
            ad.action = None
            for name in BONES:
                idx = names.index(name)
                bone = arm.pose.bones[name]
                rest_inverse = world.inverted() @ arm.matrix_world @ arm.data.bones[name].matrix_local.inverted() @ arm.matrix_world.inverted() @ world
                pose_in_mesh = transforms[name] @ rest_inverse.inverted()
                for axis in "XYZ":
                    for degrees in (-15, -10, -5, 0, 5, 10, 15):
                        rot = Matrix.Rotation(math.radians(degrees), 4, axis)
                        isolated = pose_in_mesh @ rot @ rest_inverse
                        mask = np.flatnonzero(weights[:, idx] > 0)
                        direct = base.copy()
                        m = array(world @ (isolated - transforms[name]) @ world.inverted())
                        direct[mask] += (before_array[mask] @ m[:3, :3].T + m[:3, 3]) * weights[mask, idx, None]
                        for b in arm.pose.bones:
                            b.matrix_basis = live_bases[b.name]
                        bone.matrix_basis = live_bases[name] @ rot
                        bpy.context.view_layer.update()
                        live = array(h["pts"](obj))
                        if degrees == 0 and np.linalg.norm(live - base, axis=1).max() > 1e-5:
                            raise ValueError(f"Zero-degree recovery failed at {frame}, {name}, {axis}")
                        row = {"frame": frame, "bone": name, "axis": axis, "degrees": degrees,
                               "baseline_areas": baseline_area.tolist(),
                               "changed_bones": [b.name for b in arm.pose.bones if np.max(np.abs(array(b.matrix) - live_matrices[b.name])) > 1e-6]}
                        for label, x in (("direct", direct), ("live", live)):
                            row[label] = {"changed_vertices": np.flatnonzero(np.linalg.norm(x - base, axis=1) > 1e-5).tolist(),
                                          "sentinel_areas": summarize(x)}
                        records.write(json.dumps(row, separators=(",", ":")) + "\n")
            print("Ablations completed for frame", frame, flush=True)
    (args.out / "ablation_summary.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
