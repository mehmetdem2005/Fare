"""Measure isolated manual Pose Mode controls without an active action."""
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector


def main():
    source, output = sys.argv[sys.argv.index("--") + 1:]
    bpy.ops.wm.open_mainfile(filepath=source)
    mesh = bpy.data.objects["Mouse"]
    rig = next(m.object for m in mesh.modifiers if m.type == "ARMATURE")
    rig.animation_data.action = None
    for track in rig.animation_data.nla_tracks:
        track.mute = True
    bpy.context.view_layer.objects.active = rig
    if rig.mode != "POSE":
        bpy.ops.object.mode_set(mode="POSE")
    for bone in rig.pose.bones:
        bone.matrix_basis = Matrix.Identity(4)

    def points():
        bpy.context.view_layer.update()
        evaluated = mesh.evaluated_get(bpy.context.evaluated_depsgraph_get())
        coords = np.empty(len(mesh.data.vertices) * 3, dtype=np.float32)
        evaluated.data.vertices.foreach_get("co", coords)
        return coords.reshape(-1, 3)

    neutral = points()
    results = {}
    for bone in rig.pose.bones:
        samples = []
        for amount in (-15, -5, 5, 15):
            bone.matrix_basis = (Matrix.Translation(Vector((0, 0, amount / 1000)))
                                 if bone.name.startswith(("ik_", "pole_"))
                                 else Matrix.Rotation(math.radians(amount), 4, "X"))
            delta = np.linalg.norm(points() - neutral, axis=1)
            samples.append({"input": amount, "max_displacement": float(delta.max()),
                            "moved_vertices": int(np.count_nonzero(delta > 1e-5))})
            bone.matrix_basis = Matrix.Identity(4)
        results[bone.name] = samples
    fk_results = {}
    for side in ("L", "R"):
        for target, segments in (("ik_hand", ("upper_arm", "forearm", "hand")),
                                 ("ik_foot", ("thigh", "shin", "foot"))):
            control = rig.pose.bones[f"{target}.{side}"]
            control["IK"] = 0.0
            rig.update_tag()
            fk_neutral = points()
            for segment in segments:
                bone = rig.pose.bones[f"{segment}.{side}"]
                bone.matrix_basis = Matrix.Rotation(math.radians(15), 4, "X")
                maximum = float(np.linalg.norm(points() - fk_neutral, axis=1).max())
                assert maximum > 1e-5, bone.name
                fk_results[bone.name] = maximum
                bone.matrix_basis = Matrix.Identity(4)
            control["IK"] = 1.0
            rig.update_tag()
    results["FK"] = fk_results
    chest = rig.pose.bones["spine_05"]
    for name in ("breath", "heartbeat"):
        chest[name] = 1.0
        rig.update_tag()
        delta = np.linalg.norm(points() - neutral, axis=1)
        value = mesh.data.shape_keys.key_blocks[f"chest_{name}"].value
        assert value > .99 and delta.max() > 1e-5, (name, value)
        results[name] = {"max_displacement": float(delta.max()),
                         "moved_vertices": int(np.count_nonzero(delta > 1e-5))}
        chest[name] = 0.0
        rig.update_tag()
    Path(output).write_text(json.dumps(results, indent=2) + "\n")


if __name__ == "__main__":
    main()
