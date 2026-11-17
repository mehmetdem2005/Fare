"""Screen hind-paw roll and reach on the Fare sprint in Blender."""
import argparse
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix

sys.path.insert(0, str(Path(__file__).resolve().parent))
from anatomy_manual_replay import KNEE
from anatomy_baseline import render

ACTION = "run_sprint_v8_swing_clearance_TRIAL"
NEW_ACTION = "run_sprint_hind_paw_TRIAL"
SIDES = ("R", "L")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--candidate", nargs=3, type=float, metavar=("DROP", "OUT", "PITCH"))
    parser.add_argument("--stance-reach", type=float, default=0.0)
    parser.add_argument("--stance-screen", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    args.output.mkdir(parents=True, exist_ok=False)
    bpy.ops.wm.open_mainfile(filepath=str(args.source.resolve()))
    mesh = bpy.data.objects["Mouse"]
    rig = next(mod.object for mod in mesh.modifiers if mod.type == "ARMATURE")
    scene = bpy.context.scene
    animation = rig.animation_data
    use_nla = animation.use_nla
    animation.use_nla = False
    original = bpy.data.actions[ACTION]
    animation.action = original
    targets = {side: rig.pose.bones[f"ik_foot.{side}"] for side in SIDES}
    parts = np.array([p.value for p in mesh.data.attributes["part_id"].data])
    rest = np.array([v.co[:] for v in mesh.data.vertices])
    edges = np.array([tuple(e.vertices) for e in mesh.data.edges])
    lengths = np.linalg.norm(rest[edges[:, 1]] - rest[edges[:, 0]], axis=1)
    centers = {"knee.R": rest[np.ravel(KNEE)].mean(axis=0)}
    centers["knee.L"] = centers["knee.R"] * [-1, 1, 1]
    centers.update({f"ankle.{side}": np.array((mesh.matrix_world.inverted() @ rig.matrix_world)
                    @ rig.data.bones[f"foot.{side}"].head_local) for side in SIDES})
    masks = {name: ((np.linalg.norm(rest - center, axis=1) < (.055 if "knee" in name else .048))
                    [edges].all(axis=1) & (lengths > .001)) for name, center in centers.items()}

    def sample():
        bpy.context.view_layer.update()
        depsgraph = bpy.context.evaluated_depsgraph_get()
        evaluated = mesh.evaluated_get(depsgraph)
        buf = np.empty(3 * len(rest), dtype=np.float32)
        evaluated.data.vertices.foreach_get("co", buf)
        xyz = buf.reshape(-1, 3)
        world = np.array(evaluated.matrix_world)
        heights = xyz @ world[2, :3] + world[2, 3]
        strain = abs(np.linalg.norm(xyz[edges[:, 1]] - xyz[edges[:, 0]], axis=1) /
                     np.maximum(lengths, 1e-10) - 1)
        return {side: {"sole_z": float(heights[parts == tag].min()),
                       **{region: float(np.quantile(strain[masks[f"{region}.{side}"]], .95))
                          for region in ("knee", "ankle")}}
                for side, tag in zip(SIDES, (7, 8))}

    def transform(side, matrix, height, params, stance_reach=0):
        drop, out, pitch = params
        u = min(1.0, max(0.0, (height - .005) / .024))
        weight = u * u * (3 - 2 * u)
        moved = Matrix.Rotation(math.radians(pitch * weight), 4, "X") @ matrix
        moved.translation = matrix.translation
        moved.translation.x += (-1 if side == "R" else 1) * out * weight
        moved.translation.z -= min(drop * weight, max(0, height - .010))
        if stance_reach:
            forward = max(0.0, targets[side].bone.head_local.y - matrix.translation.y)
            moved.translation.y += forward * stance_reach * (1 - weight)
            moved.translation.z += max(0.0, .0005 - height)
        return moved

    frames = range(1, 26) if args.candidate else (4, 6, 7, 8, 9, 10, 12)
    if args.stance_screen:
        frames = tuple(range(12, 22))
    baseline = {}
    poses = {}
    for frame in frames:
        scene.frame_set(frame)
        baseline[frame] = sample()
        poses[frame] = {side: target.matrix.copy() for side, target in targets.items()}

    if not args.candidate:
        numbers = []
        variants = [((drop, out, pitch), 0.0) for drop in (0, .012, .020, .028)
                    for out in (0, .010, .020) for pitch in (-16, -8, 0, 8, 16)]
        if args.stance_screen:
            variants = [((.028, .010, -8), reach) for reach in (0, .15, .25, .35, .45)]
        for params, reach in variants:
            samples = {}
            for frame in frames:
                scene.frame_set(frame)
                for side, target in targets.items():
                    target.matrix = transform(side, poses[frame][side], baseline[frame][side]["sole_z"], params, reach)
                samples[frame] = sample()
            values = [result for sample_frame in samples.values() for result in sample_frame.values()]
            numbers.append({"inputs": params, "stance_reach": reach, "min_height": min(v["sole_z"] for v in values),
                            "knee_max": max(v["knee"] for v in values),
                            "ankle_max": max(v["ankle"] for v in values), "samples": samples})
        (args.output / "screen.json").write_text(json.dumps({"baseline": baseline, "variants": numbers}))
        return

    trial = original.copy()
    trial.name = NEW_ACTION
    trial.use_fake_user = True
    animation.action = trial
    previous_rotation = {side: target.rotation_euler.copy() for side, target in targets.items()}
    for frame in frames:
        scene.frame_set(frame)
        for side, target in targets.items():
            target.matrix = transform(side, poses[frame][side], baseline[frame][side]["sole_z"], args.candidate, args.stance_reach)
            target.keyframe_insert(data_path="location", frame=frame, group=target.name)
            rotation = target.rotation_euler.copy()
            rotation.make_compatible(previous_rotation[side])
            target.rotation_euler = rotation
            previous_rotation[side] = rotation
            target.keyframe_insert(data_path="rotation_euler", frame=frame, group=target.name)
    scene.frame_set(1)
    animation.use_nla = use_nla
    bpy.ops.wm.save_as_mainfile(filepath=str((args.output / "HIND_PAW_TRIAL.blend").resolve()), compress=True)
    animation.use_nla = False

    camera = bpy.data.objects.new("Hind paw review", bpy.data.cameras.new("Hind paw review"))
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

    comparison = {}
    for label, action in (("before", original), ("after", trial)):
        animation.action = action
        comparison[label] = {}
        for frame in frames:
            scene.frame_set(frame)
            comparison[label][frame] = sample()
            for side, direction in (("R", (-1, .18, -.12)), ("L", (1, .18, -.12))):
                center = (.14 if side == "L" else -.14, .11, .096)
                render(scene, camera, frame, f"{label}_{side}", direction, center, .32, args.output)
    (args.output / "comparison.json").write_text(json.dumps(comparison, indent=2))


if __name__ == "__main__":
    main()
