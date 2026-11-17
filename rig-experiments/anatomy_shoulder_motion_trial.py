"""Introduce limited scapular rotation while leaving the existing IK targets keyed."""
import argparse
import hashlib
import json
import math
import runpy
import shutil
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
SOURCE_ACTION = "run_sprint_v8_ik_phase_NUMERIC_REVIEW"
TRIAL_ACTION = "run_sprint_v8_scapular_motion_TRIAL"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    source = args.source.resolve()
    args.out.mkdir(parents=True, exist_ok=True)
    backup = (args.out / "input_before_shoulder_motion.blend").resolve()
    output = (args.out / "SCAPULAR_MOTION_TRIAL_UNAPPROVED.blend").resolve()
    if source in (backup, output):
        raise ValueError("Use a separate output directory")
    shutil.copy2(source, backup)
    h = runpy.run_path(str(HERE / "round14_skinning_forensics.py"))
    bpy.ops.wm.open_mainfile(filepath=str(source))
    mesh = bpy.data.objects["Mouse"]
    arm = next(m.object for m in mesh.modifiers if m.type == "ARMATURE")
    action = bpy.data.actions[SOURCE_ACTION]
    for track in arm.animation_data.nla_tracks:
        track.mute = True
    trajectories = {}
    for frame in range(1, 26):
        h["reset"](arm, action, frame)
        trajectories[frame] = {}
        for side in "LR":
            shoulder = arm.pose.bones[f"shoulder.{side}"]
            humerus = arm.pose.bones[f"upper_arm.{side}"]
            direction = shoulder.parent.matrix.to_3x3().inverted() @ (humerus.tail - humerus.head)
            sagittal = math.atan2(direction.z, direction.y)
            trajectories[frame][side] = (sagittal, shoulder.matrix_basis.copy(), shoulder.matrix.to_3x3().inverted() @ Vector((1, 0, 0)))
    trial = action.copy()
    trial.name = TRIAL_ACTION
    trial.use_fake_user = True
    arm.animation_data.action = trial
    measurements = {}
    for frame, pose in trajectories.items():
        bpy.context.scene.frame_set(frame)
        measurements[frame] = {}
        for side, (sagittal, basis, bend_axis) in pose.items():
            neutral = trajectories[1][side][0]
            excursion = math.atan2(math.sin(sagittal - neutral), math.cos(sagittal - neutral))
            adjustment = max(-math.radians(4), min(math.radians(4), .15 * excursion))
            shoulder = arm.pose.bones[f"shoulder.{side}"]
            shoulder.matrix_basis = basis @ Matrix.Rotation(adjustment, 4, bend_axis)
            channel = {"QUATERNION": "rotation_quaternion", "AXIS_ANGLE": "rotation_axis_angle"}.get(
                shoulder.rotation_mode, "rotation_euler")
            shoulder.keyframe_insert(channel, frame=frame, group=shoulder.name)
            measurements[frame][shoulder.name] = math.degrees(adjustment)
    bpy.context.scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=str(output), compress=True)
    (args.out / "shoulder_motion_trial.json").write_text(json.dumps({
        "source_sha256": hashlib.sha256(backup.read_bytes()).hexdigest(),
        "trial_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "trial_action": trial.name,
        "additional_scapular_degrees": measurements,
    }, indent=2) + "\n")


if __name__ == "__main__":
    main()
