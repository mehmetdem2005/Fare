"""Compare evaluated sprint samples with a constraint-free Pose Mode replay."""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
from bpy_extras.object_utils import world_to_camera_view
import numpy as np
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from anatomy_baseline import crossing, normals, render

KNEE = ((10364, 10312, 10533), (10927, 10501, 10258))
BONES = ("shoulder.R", "upper_arm.R", "forearm.R", "hips", "thigh.R", "shin.R", "foot.R")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("action")
    parser.add_argument("output", type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    args.output.mkdir(parents=True, exist_ok=False)
    bpy.ops.wm.open_mainfile(filepath=str(args.source.resolve()))
    scene = bpy.context.scene
    mesh = bpy.data.objects["Mouse"]
    rig = next(mod.object for mod in mesh.modifiers if mod.type == "ARMATURE")
    animation = rig.animation_data
    for track in animation.nla_tracks:
        track.mute = True
    animation.action = bpy.data.actions[args.action]
    keys = mesh.data.shape_keys.key_blocks
    bpy.context.view_layer.objects.active = rig
    if rig.mode != "POSE":
        bpy.ops.object.mode_set(mode="POSE")

    camera = bpy.data.objects.new("Manual replay camera", bpy.data.cameras.new("Manual replay camera"))
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

    rest = np.array([mesh.matrix_world @ vertex.co for vertex in mesh.data.vertices])
    edges = np.array([tuple(edge.vertices) for edge in mesh.data.edges])
    lengths = np.linalg.norm(rest[edges[:, 0]] - rest[edges[:, 1]], axis=1)
    knee_center = rest[np.array(KNEE).ravel()].mean(axis=0)
    ankle_center = rest[9440]
    shoulder_center = np.array(rig.matrix_world @ rig.data.bones["upper_arm.R"].head_local)
    part = mesh.data.attributes["part_id"].data
    masks = {}
    for name, center, radius in (
        ("knee", knee_center, .055), ("shoulder", shoulder_center, .095)
    ):
        vertices = np.array([item.value == 6 for item in part])
        vertices &= np.linalg.norm(rest - center, axis=1) < radius
        masks[name] = vertices[edges].all(axis=1) & (lengths > .001)

    def points():
        bpy.context.view_layer.update()
        obj = mesh.evaluated_get(bpy.context.evaluated_depsgraph_get())
        return np.array([obj.matrix_world @ vertex.co for vertex in obj.data.vertices])

    def inspect(label, frame, xyz):
        fraction = np.linalg.norm(xyz[edges[:, 0]] - xyz[edges[:, 1]], axis=1)
        witness = crossing(*(list(map(Vector, xyz[list(ids)])) for ids in KNEE))
        values = {
            "knee_crossing_world": witness,
            "knee_area_ratios": (np.linalg.norm(normals(xyz, np.array(KNEE)), axis=1)
                                 / np.linalg.norm(normals(rest, np.array(KNEE)), axis=1)).tolist(),
            "edge_strain_p95": {name: float(np.quantile(abs(fraction[mask] / lengths[mask] - 1), .95))
                                for name, mask in masks.items()},
        }
        for name, center, direction, scale in (
            ("knee", knee_center, (-1, .25, -.25), .29),
            ("shoulder", shoulder_center, (-1, -.25, -.35), .35),
            ("ankle", ankle_center, (-1, .25, -.25), .23),
        ):
            render(scene, camera, frame, f"{label}_{name}", direction, center, scale, args.output)
            if name == "knee":
                bpy.context.view_layer.update()
                values["knee_overlay"] = [[tuple(world_to_camera_view(scene, camera, Vector(xyz[v])))[:2]
                                           for v in triangle] for triangle in KNEE]
        return values

    snapshots = {}
    measurements = {}
    for frame in (7, 8, 9):
        scene.frame_set(frame)
        xyz = points()
        evaluated = rig.evaluated_get(bpy.context.evaluated_depsgraph_get())
        snapshots[frame] = ({bone.name: bone.matrix.copy() for bone in evaluated.pose.bones}, xyz,
                            {key.name: key.value for key in keys})
        measurements[frame] = {"sprint": inspect("sprint", frame, xyz)}

    animation.action = None
    for bone in rig.pose.bones:
        for constraint in bone.constraints:
            constraint.mute = True
        bone.matrix_basis = Matrix.Identity(4)
    key_animation = mesh.data.shape_keys.animation_data
    if key_animation:
        key_animation.action = None
        key_animation.use_nla = False
        for driver in key_animation.drivers:
            driver.mute = True
    for driver in animation.drivers:
        driver.mute = True
    bpy.context.view_layer.update()

    def apply_matrices(matrices):
        manual_rotations = {}
        for bone in rig.pose.bones:
            parent = bone.parent
            parent_arguments = ({"parent_matrix": matrices[parent.name],
                                 "parent_matrix_local": parent.bone.matrix_local}
                                if parent else {})
            bone.matrix_basis = bone.bone.convert_local_to_pose(
                matrices[bone.name], bone.bone.matrix_local, invert=True, **parent_arguments
            )
            if bone.name in BONES:
                manual_rotations[bone.name] = [float(v) for v in bone.matrix_basis.to_euler()]
        return manual_rotations

    for frame, (matrices, expected, values) in snapshots.items():
        manual_rotations = apply_matrices(matrices)
        for name, value in values.items():
            keys[name].value = value
        xyz = points()
        measurements[frame]["manual"] = inspect("manual", frame, xyz)
        measurements[frame]["manual"]["rotation_xyz_rad"] = manual_rotations
        measurements[frame]["manual"]["max_surface_delta"] = float(np.linalg.norm(xyz - expected, axis=1).max())

    live_probes = {}
    corrective = keys.get("trial_right_knee_pose")
    if corrective is not None:
        curve = next(driver for driver in key_animation.drivers if driver.data_path == corrective.path_from_id("value"))
        curve.mute = False
        for driver in animation.drivers:
            if driver.data_path.startswith('pose.bones["spine_curve"]'):
                driver.mute = False
        spine = rig.pose.bones["spine_curve"]
        for bone in rig.pose.bones:
            for constraint in bone.constraints:
                if constraint.name.startswith("Spine curve "):
                    constraint.mute = False
        matrices, expected, values = snapshots[7]
        for name, value in values.items():
            if name != corrective.name:
                keys[name].value = value
        probes = (
            ("matched_7_live", 0, 0, 0), ("shin_minus_10", -10, 0, 0),
            ("shin_plus_10", 10, 0, 0), ("knee_and_spine_and_front_leg", 0, 8, 12),
        )
        for label, shin_offset, flex, forearm_offset in probes:
            apply_matrices(matrices)
            shin = rig.pose.bones["shin.R"]
            shin.matrix_basis @= Matrix.Rotation(math.radians(shin_offset), 4, "X")
            forearm = rig.pose.bones["forearm.L"]
            forearm.matrix_basis @= Matrix.Rotation(math.radians(forearm_offset), 4, "X")
            spine["flex"] = float(flex)
            rig.update_tag()
            xyz = points()
            evaluated_keys = mesh.data.shape_keys.evaluated_get(bpy.context.evaluated_depsgraph_get())
            live_probes[label] = inspect(label, 7, xyz)
            live_probes[label].update({"shin_offset_deg": shin_offset, "spine_flex_deg": flex,
                                       "opposite_forearm_offset_deg": forearm_offset,
                                       "corrective_value": evaluated_keys.key_blocks[corrective.name].value,
                                       "max_surface_delta_from_sprint_7": float(np.linalg.norm(xyz - expected, axis=1).max())})
    with args.source.open("rb") as source_file:
        source_hash = hashlib.file_digest(source_file, "sha256").hexdigest()
    report = {"source": str(args.source), "source_sha256": source_hash, "blender": bpy.app.version_string,
        "action": args.action, "samples": measurements, "live_pose_corrective": live_probes}
    (args.output / "manual_replay.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
