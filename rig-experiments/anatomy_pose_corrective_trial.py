"""Build an experimental pose-angle corrective from a local posed surface target."""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from anatomy_baseline import normals
from anatomy_manual_replay import KNEE


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("action")
    parser.add_argument("output", type=Path)
    parser.add_argument("--frame", type=int, default=7)
    parser.add_argument("--rings", type=int, default=7)
    parser.add_argument("--steps", type=int, default=15)
    parser.add_argument("--bounded", action="store_true")
    parser.add_argument("--taubin", action="store_true")
    parser.add_argument("--region", choices=("knee", "shoulder"), default="knee")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    args.output.mkdir(parents=True, exist_ok=False)
    bpy.ops.wm.open_mainfile(filepath=str(args.source.resolve()))
    mesh = bpy.data.objects["Mouse"]
    armature = next(mod for mod in mesh.modifiers if mod.type == "ARMATURE")
    rig = armature.object
    scene = bpy.context.scene
    animation = rig.animation_data
    for track in animation.nla_tracks:
        track.mute = True
    animation.action = bpy.data.actions[args.action]
    assert not armature.use_deform_preserve_volume

    neighbors = [set() for _ in mesh.data.vertices]
    for edge in mesh.data.edges:
        a, b = edge.vertices
        neighbors[a].add(b)
        neighbors[b].add(a)
    bone_name = "shin.R" if args.region == "knee" else "upper_arm.R"
    scene.frame_set(args.frame)
    frontier = set(np.ravel(KNEE))
    if args.region == "shoulder":
        evaluated = mesh.evaluated_get(bpy.context.evaluated_depsgraph_get())
        posed = np.array([v.co[:] for v in evaluated.data.vertices])
        rest = np.array([v.co[:] for v in mesh.data.vertices])
        bone = rig.data.bones[bone_name]
        center = mesh.matrix_world.inverted() @ rig.matrix_world @ bone.head_local.lerp(bone.tail_local, .35)
        part = mesh.data.attributes["part_id"].data
        mesh.data.calc_loop_triangles()
        triangles = np.array([t.vertices[:] for t in mesh.data.loop_triangles
                              if all(part[i].value == 6 for i in t.vertices)])
        area = np.linalg.norm(normals(rest, triangles), axis=1)
        locations = rest[triangles].mean(axis=1)
        near = np.flatnonzero((np.linalg.norm(locations - center[:], axis=1) < .065)
                              & (area > 2e-6))
        ratios = np.linalg.norm(normals(posed, triangles[near]), axis=1) / area[near]
        frontier = set(triangles[near[np.argsort(ratios)[:4]]].ravel())
    seeds = sorted(frontier)
    rings = dict.fromkeys(frontier, 0)
    for depth in range(1, args.rings):
        frontier = {near for index in frontier for near in neighbors[index]} - rings.keys()
        rings.update(dict.fromkeys(frontier, depth))
    indices = np.array(sorted(rings), dtype=int)

    def points():
        bpy.context.view_layer.update()
        obj = mesh.evaluated_get(bpy.context.evaluated_depsgraph_get())
        coords = np.empty(len(mesh.data.vertices) * 3, dtype=np.float32)
        obj.data.vertices.foreach_get("co", coords)
        return coords.reshape(-1, 3).astype(np.float64)

    def local_rotation():
        evaluated = rig.evaluated_get(bpy.context.evaluated_depsgraph_get())
        bone = evaluated.pose.bones[bone_name]
        return tuple(bone.bone.convert_local_to_pose(
            bone.matrix, bone.bone.matrix_local, parent_matrix=bone.parent.matrix,
            parent_matrix_local=bone.parent.bone.matrix_local, invert=True,
        ).to_euler("XYZ"))

    angle_samples = {}
    for frame in range(1, 26):
        scene.frame_set(frame)
        angle_samples[frame] = local_rotation()
    scene.frame_set(args.frame)
    posed = points()
    target = posed.copy()
    passes = (.50, -.53) if args.taubin else (.60,)
    patch = [(i, sorted(neighbors[i]), (1 - rings[i] / args.rings) ** 2) for i in indices]
    for _ in range(args.steps):
        for strength in passes:
            update = target.copy()
            for i, ring, weight in patch:
                update[i] += strength * weight * (target[ring].mean(axis=0) - target[i])
            target = update

    # With linear blend skinning, sampling three independent offsets gives each
    # vertex's affine map even when weights are shared with other deform bones.
    probe = mesh.shape_key_add(name="Temporary inverse-skin probe", from_mix=False)
    probe.value = 1
    basis = mesh.data.shape_keys.reference_key
    mapping = np.empty((len(indices), 3, 3))
    for axis in range(3):
        for i in indices:
            probe.data[i].co = basis.data[i].co
            probe.data[i].co[axis] += .01
        mesh.data.update()
        mapping[:, :, axis] = (points()[indices] - posed[indices]) / .01
    mesh.shape_key_remove(probe)
    delta = np.linalg.solve(mapping, (target[indices] - posed[indices])[..., None]).squeeze(-1)
    shape = mesh.shape_key_add(name=f"trial_right_{args.region}_pose", from_mix=False)
    for index, offset in zip(indices, delta):
        shape.data[index].co = basis.data[index].co + Vector(offset)
    shape.value = 1
    mesh.data.update()
    error = float(np.linalg.norm(points()[indices] - target[indices], axis=1).max())
    if error > 1e-5:
        raise RuntimeError(f"Corrective inverse skin error {error:.6g}")

    # Favor the axis which separates the sampled flexion from rest and from the
    # shallowest run samples with a broad falloff.
    peak = np.array(angle_samples[args.frame])
    axis = int(np.argmax(abs(peak)))
    if abs(peak[axis]) < .05:
        raise RuntimeError("No measurable flexion at training pose")
    driver = shape.driver_add("value").driver
    for name in "xyz"[axis]:
        variable = driver.variables.new()
        variable.name = name
        variable.type = "TRANSFORMS"
        variable.targets[0].id = rig
        variable.targets[0].bone_target = bone_name
        variable.targets[0].transform_type = f"ROT_{name.upper()}"
        variable.targets[0].transform_space = "LOCAL_SPACE"
        variable.targets[0].rotation_mode = "XYZ"
    start = peak[axis] * .55
    expression = f"min(1,max(0,({'xyz'[axis]}-{start:.9g})/({peak[axis]-start:.9g})))"
    driver.expression = f"{expression}*{expression}*(3-2*{expression})"
    if args.bounded:
        direction = math.copysign(1, peak[axis])
        furthest = max(direction * angles[axis] for angles in angle_samples.values()) + .02
        exit_angle = f"(max(0,{direction:g}*{'xyz'[axis]}-{furthest:.9g})/0.10)"
        driver.expression += f"*(0.5+0.5*cos(min(pi,pi*{exit_angle})))"
    if not driver.is_simple_expression:
        raise RuntimeError("Unexpected non-simple corrective expression")
    keyed_samples = {}
    for frame in range(1, 26):
        scene.frame_set(frame)
        keyed_samples[frame] = float(mesh.evaluated_get(
            bpy.context.evaluated_depsgraph_get()
        ).data.shape_keys.key_blocks[shape.name].value)
    if keyed_samples[args.frame] < .99:
        raise RuntimeError(f"Corrective driver failed to reach training pose: {keyed_samples}")

    output = args.output / f"{args.region.upper()}_POSE_CORRECTIVE_UNAPPROVED.blend"
    scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=str(output.resolve()), compress=True)
    with args.source.open("rb") as source_file:
        source_hash = hashlib.file_digest(source_file, "sha256").hexdigest()
    report = {
        "source": str(args.source), "source_sha256": source_hash,
        "blender": bpy.app.version_string, "action": args.action,
        "region": args.region, "seed_vertices": [int(i) for i in seeds],
        "training_frame": args.frame, "rings": args.rings, "steps": args.steps, "taubin": args.taubin, "bounded": args.bounded,
        "edit_vertices": indices.tolist(), "driver_axis": "XYZ"[axis],
        "max_inverse_skin_error": error, "driver_expression": driver.expression,
        "joint_local_rotation": angle_samples, "corrective_by_frame": keyed_samples,
    }
    (args.output / "corrective.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
