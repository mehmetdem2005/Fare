"""Exercise the saved rig in Pose Mode with the sprint and NLA disabled."""
import argparse
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from anatomy_baseline import crossing, render
from anatomy_manual_replay import KNEE

BONES = ("shoulder", "upper_arm", "forearm", "hand", "thigh", "shin", "foot")
TARGETS = ("ik_hand.L", "ik_hand.R", "ik_foot.L", "ik_foot.R")
SPINE = tuple(f"spine_{i:02}" for i in range(1, 6))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    args.output.mkdir(parents=True, exist_ok=False)
    bpy.ops.wm.open_mainfile(filepath=str(args.source.resolve()))
    mesh = bpy.data.objects["Mouse"]
    rig = next(mod.object for mod in mesh.modifiers if mod.type == "ARMATURE")
    rig.animation_data.action = None
    rig.animation_data.use_nla = False
    bpy.context.view_layer.objects.active = rig
    if rig.mode != "POSE":
        bpy.ops.object.mode_set(mode="POSE")
    pose = rig.pose.bones
    scene = bpy.context.scene
    camera = bpy.data.objects.new("Independent pose camera", bpy.data.cameras.new("Independent pose camera"))
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.data.type = "ORTHO"
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = scene.render.resolution_y = 512
    scene.render.resolution_percentage = 100
    scene.display.render_aa = "FXAA"
    shading = scene.display.shading
    shading.color_type = "SINGLE"
    shading.single_color = (.54, .53, .51)
    shading.show_cavity = True
    shading.cavity_type = "WORLD"
    shading.show_shadows = False

    def points():
        rig.update_tag()
        bpy.context.view_layer.update()
        evaluated = mesh.evaluated_get(bpy.context.evaluated_depsgraph_get())
        coords = np.empty(len(mesh.data.vertices) * 3, dtype=np.float32)
        evaluated.data.vertices.foreach_get("co", coords)
        return coords.reshape(-1, 3)

    def reset():
        for bone in pose:
            bone.matrix_basis = Matrix.Identity(4)
        for control in TARGETS:
            pose[control]["IK"] = 1.0
        for name in ("flex", "twist", "side_bend"):
            pose["spine_curve"][name] = 0.0
        for name in ("breath", "heartbeat"):
            pose["spine_05"][name] = 0.0
        return points()

    def rotate(name, axis, degrees):
        pose[name].matrix_basis = Matrix.Rotation(math.radians(degrees), 4, axis)

    def translate(name, xyz):
        bone = pose[name]
        bone.location = bone.bone.matrix_local.to_3x3().inverted() @ Vector(xyz)

    rest = reset()
    ids = mesh.data.attributes["part_id"].data
    body = np.array([p.value == 6 for p in ids])
    edges = np.array([tuple(edge.vertices) for edge in mesh.data.edges if all(body[i] for i in edge.vertices)])
    lengths = np.linalg.norm(rest[edges[:, 0]] - rest[edges[:, 1]], axis=1)
    edges = edges[lengths > .001]
    lengths = lengths[lengths > .001]
    witness_indices = [list(tri) for tri in KNEE]

    def measure(xyz):
        updated = np.linalg.norm(xyz[edges[:, 0]] - xyz[edges[:, 1]], axis=1)
        witness = crossing(*(list(map(Vector, xyz[index])) for index in witness_indices))
        keys = mesh.data.shape_keys.evaluated_get(bpy.context.evaluated_depsgraph_get())
        return {
            "body_edge_strain_p95": float(np.quantile(abs(updated / lengths - 1), .95)),
            "knee_witness_crossing_local": witness,
            "max_surface_delta": float(np.linalg.norm(xyz - rest, axis=1).max()),
            "controls_morph_values": {key.name: key.value for key in keys.key_blocks
                                      if key.name.startswith(("chest_", "trial_right_"))},
        }

    sweeps = {}
    for name in [*(f"{b}.{side}" for b in BONES for side in "LR"), *SPINE, "neck", "hips"]:
        for axis in "XYZ":
            for angle in (-15, -10, -5, 0, 5, 10, 15):
                reset()
                for target in TARGETS:
                    pose[target]["IK"] = 0.0
                rotate(name, axis, angle)
                sweeps[f"{name}/{axis}/{angle}"] = measure(points())

    cases = {
        "neutral": {},
        "crouch": {"locations": {"hips": (0, 0, -.025)}, "spine": {"flex": 8}},
        "rise": {"locations": {"hips": (0, 0, .014)}, "spine": {"flex": -6}},
        "reach": {"locations": {"ik_hand.R": (0, -.035, .008)}, "spine": {"flex": -8}},
        "front_open_left": {"locations": {"ik_hand.L": (.023, -.01, .008)}},
        "front_open_right": {"locations": {"ik_hand.R": (-.023, -.01, .008)}},
        "spine_flex": {"spine": {"flex": 15}},
        "spine_extend": {"spine": {"flex": -15}},
        "spine_side_left": {"spine": {"side_bend": 12}},
        "spine_side_right": {"spine": {"side_bend": -12}},
        "spine_twist_left": {"spine": {"twist": 12}},
        "spine_twist_right": {"spine": {"twist": -12}},
        "bend_twist_look": {"spine": {"flex": 10, "twist": 8},
                            "rotations": {"head": ("Z", -9)}},
        "look_up": {"spine": {"flex": 5}, "rotations": {"head": ("X", 10)}},
        "look_down": {"spine": {"flex": -5}, "rotations": {"head": ("X", -10)}},
        "tail_curve": {"rotations": {"tail_01": ("Z", 10), "tail_02": ("Z", 12)}},
        "tuck": {"locations": {name: (0, 0, .025) for name in TARGETS}, "spine": {"flex": 12}},
        "landing": {"locations": {"ik_hand.L": (0, -.023, 0), "ik_hand.R": (0, -.023, 0),
                                  "hips": (0, 0, -.017)}},
        "diagonal_lift": {"locations": {"ik_hand.R": (0, -.025, .020),
                                       "ik_foot.L": (0, .025, .020)}},
        "chest_combined": {"spine": {"flex": 10}, "rotations": {"head": ("X", 8)},
                           "breath": .65, "heartbeat": .5},
        "chest_maximum_bent": {"spine": {"flex": 10}, "breath": 1.0, "heartbeat": 1.0},
        "whiskers_head": {"rotations": {"head": ("Z", 12), "snout": ("X", 4),
                                       "whisker_fan.L": ("Z", 6), "whisker_fan.R": ("Z", -3)}},
    }
    for name in TARGETS:
        cases[f"lift_{name}"] = {"locations": {name: (0, 0, .025)}}
        side = 1 if name.endswith(".L") else -1
        reach = -.016 if "hand" in name else .016
        cases[f"load_{name}"] = {"locations": {"hips": (side * .013, reach, -.007)}}

    scenarios = {}
    for name, config in cases.items():
        reset()
        for bone, xyz in config.get("locations", {}).items():
            translate(bone, xyz)
        for bone, (axis, angle) in config.get("rotations", {}).items():
            rotate(bone, axis, angle)
        for prop, value in config.get("spine", {}).items():
            pose["spine_curve"][prop] = float(value)
        for name_prop in ("breath", "heartbeat"):
            pose["spine_05"][name_prop] = float(config.get(name_prop, 0))
        scenarios[name] = {"inputs": config, **measure(points())}
        render(scene, camera, 1, name, (-1, -.30, -.12), (0, -.02, .23), 1.48, args.output)

    switches = {}
    for target in TARGETS:
        reset()
        translate(target, (0, -.018, .018))
        points()
        side = target[-1]
        end = ("hand" if "hand" in target else "foot") + "." + side
        ik = pose[end].matrix.copy()
        pose[target]["IK"] = 0.0
        points()
        fk = pose[end].matrix.copy()
        pose[target]["IK"] = 1.0
        points()
        restored = pose[end].matrix.copy()
        switches[target] = {
            "unmatched_switch_position_delta": (ik.translation - fk.translation).length,
            "unmatched_switch_rotation_rad": ik.to_quaternion().rotation_difference(fk.to_quaternion()).angle,
            "return_position_delta": (ik.translation - restored.translation).length,
        }

    result = {"source": str(args.source), "blender": bpy.app.version_string,
              "bone_count": len(rig.data.bones), "bone_collections": list(rig.data.collections.keys()),
              "sampled_scenarios": scenarios, "fk_sweeps": sweeps, "raw_ik_fk": switches,
              "reset_max_surface_delta": float(np.linalg.norm(reset() - rest, axis=1).max())}
    (args.output / "pose_acceptance.json").write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
