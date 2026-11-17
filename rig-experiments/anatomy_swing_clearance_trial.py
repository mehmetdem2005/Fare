"""Test clearance for hand–upper arm collisions found during the swing phase."""
import argparse
import hashlib
import json
import runpy
import shutil
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from anatomy_shoulder_motion_trial import TRIAL_ACTION
from anatomy_torso_weight_trial import smoothstep

ACTION = "run_sprint_v8_swing_clearance_TRIAL"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--direction", choices=("down", "outside"), required=True)
    parser.add_argument("--drop", type=float, choices=(.008, .012), default=.008)
    parser.add_argument("--hind", action="store_true")
    parser.add_argument("--floor-test", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    source = args.source.resolve()
    args.out.mkdir(parents=True, exist_ok=True)
    backup = (args.out / "input_before_swing_clearance.blend").resolve()
    output = (args.out / "SWING_CLEARANCE_TRIAL_UNAPPROVED.blend").resolve()
    if source in (backup, output):
        raise ValueError("Use a separate output directory")
    shutil.copy2(source, backup)
    h = runpy.run_path(str(Path(__file__).with_name("round14_skinning_forensics.py")))
    bpy.ops.wm.open_mainfile(filepath=str(source))
    mesh = bpy.data.objects["Mouse"]
    arm = next(m.object for m in mesh.modifiers if m.type == "ARMATURE")
    original = bpy.data.actions[TRIAL_ACTION]
    for track in arm.animation_data.nla_tracks:
        track.mute = True
    part = mesh.data.attributes["part_id"]
    parts = {"hand.L": 3, "hand.R": 2}
    if args.hind or args.floor_test:
        parts.update({"foot.L": 8, "foot.R": 7})
    soles = {name: [v.index for v in mesh.data.vertices if part.data[v.index].value == tag]
             for name, tag in parts.items()}
    controls = {name: arm.pose.bones[f"ik_{name}"] for name in soles}
    measurements = {}
    for frame in range(1, 26):
        h["reset"](arm, original, frame)
        positions = h["pts"](mesh)
        measurements[frame] = {}
        for side, control in controls.items():
            height = min(positions[i].z for i in soles[side])
            gate = smoothstep(.005, .020, height)
            direction = Vector((0, 0, -args.drop)) if args.direction == "down" else Vector((.012 if side.endswith(".L") else -.012, 0, 0))
            if not args.hind and side.startswith("foot."):
                gate = 0.
            delta = direction * gate
            if args.floor_test:
                delta.z += max(0., .0002 - height)
            offset = control.bone.matrix_local.to_3x3().inverted() @ delta
            measurements[frame][side] = {"location": list(control.location + offset),
                                         "offset_model_units": list(delta), "source_lowest_z": height}
    action = original.copy()
    action.name = ACTION
    action.use_fake_user = True
    arm.animation_data.action = action
    for frame, sides in measurements.items():
        bpy.context.scene.frame_set(frame)
        for side, row in sides.items():
            control = controls[side]
            control.location = row["location"]
            control.keyframe_insert("location", frame=frame, group=control.name)
    bpy.context.scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=str(output), compress=True)
    (args.out / "swing_clearance_trial.json").write_text(json.dumps({
        "source_sha256": hashlib.sha256(backup.read_bytes()).hexdigest(),
        "trial_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "trial_action": action.name,
        "direction": args.direction,
        "drop": args.drop,
        "includes_hind": args.hind,
        "floor_test": args.floor_test,
        "measurements": measurements,
    }, indent=2) + "\n")


if __name__ == "__main__":
    main()
