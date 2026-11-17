"""Test torso attachment weights after the limb-transform ablation.

Outputs are isolated experiments for review, with a per-vertex weight change ledger.
"""
import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

import bpy


def smoothstep(start, end, value):
    t = min(1., max(0., (value - start) / (end - start)))
    return t * t * (3 - 2 * t)


def torso_weights(y, bones):
    for (front, front_y), (back, back_y) in zip(bones, bones[1:]):
        if y <= back_y:
            t = smoothstep(front_y, back_y, y)
            return {front: 1 - t, back: t}
    return {bones[-1][0]: 1.}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--strength", type=float, choices=(.5, 1.), default=1.)
    parser.add_argument("--wide-transition", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    source = args.source.resolve()
    args.out.mkdir(parents=True, exist_ok=True)
    backup = args.out / "input_before_weight_trial.blend"
    if backup.resolve() == source:
        raise ValueError("Use a separate output directory")
    shutil.copy2(source, backup)
    bpy.ops.wm.open_mainfile(filepath=str(source))
    obj = bpy.data.objects["Mouse"]
    part = obj.data.attributes["part_id"]
    mod = next(m for m in obj.modifiers if m.type == "ARMATURE")
    arm = mod.object
    deform = {b.name for b in arm.data.bones if b.use_deform}
    torso = [(f"spine_{i:02}", arm.data.bones[f"spine_{i:02}"].center.y) for i in range(5, 0, -1)]
    limb = {f"{name}.{side}" for side in "LR" for name in
            ("shoulder", "upper_arm", "forearm", "hand", "thigh", "shin", "foot")}
    lateral_transition = (.135, .215) if args.wide_transition else (.095, .167)
    region = {}
    for v in obj.data.vertices:
        if part.data[v.index].value != 6:
            continue
        x, y, z = v.co
        belt = smoothstep(-.19, -.055, y) * (1 - smoothstep(-.015, .145, y))
        lateral = 1 - smoothstep(*lateral_transition, abs(x))
        underbody = 1 - smoothstep(.115, .255, z)
        mix = args.strength * belt * lateral * underbody
        if mix <= 1e-5:
            continue
        before = {obj.vertex_groups[g.group].name: float(g.weight) for g in v.groups
                  if obj.vertex_groups[g.group].name in deform}
        after = before.copy()
        removed = 0.
        for name in limb.intersection(before):
            delta = mix * before[name]
            after[name] -= delta
            removed += delta
        if removed <= 1e-6:
            continue
        for name, fraction in torso_weights(y, torso).items():
            after[name] = after.get(name, 0.) + removed * fraction
        for name, weight in after.items():
            if weight > 1e-9:
                obj.vertex_groups[name].add([v.index], weight, "REPLACE")
            elif name in before:
                obj.vertex_groups[name].remove([v.index])
        region[v.index] = {"before": before, "after": after, "rest_position": list(v.co)}
    if not region:
        raise ValueError("No torso vertices selected")
    candidate = (args.out / "TORSO_WEIGHT_TRIAL_UNAPPROVED.blend").resolve()
    if candidate == source:
        raise ValueError("Refusing to overwrite the input blend")
    bpy.ops.wm.save_as_mainfile(filepath=str(candidate), compress=True)
    (args.out / "weight_trial.json").write_text(json.dumps({
        "source_sha256": hashlib.sha256(backup.read_bytes()).hexdigest(),
        "trial_sha256": hashlib.sha256(candidate.read_bytes()).hexdigest(),
        "strength": args.strength,
        "lateral_transition": lateral_transition,
        "changed_vertices": region,
    }, indent=2) + "\n")


if __name__ == "__main__":
    main()
