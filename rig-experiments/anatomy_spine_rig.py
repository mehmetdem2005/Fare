"""Add a distributed spine control and render independent Pose Mode stress tests."""
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix

sys.path.insert(0, str(Path(__file__).parent))
from anatomy_baseline import VIEWS, render


def main():
    source, destination = map(Path, sys.argv[sys.argv.index("--") + 1:])
    destination.mkdir(parents=True, exist_ok=True)
    output = destination / "SPINE_RIG_EXPERIMENT.blend"
    if output.exists():
        raise ValueError("Choose a fresh output directory")
    bpy.ops.wm.open_mainfile(filepath=str(source.resolve()))
    mesh = bpy.data.objects["Mouse"]
    rig = next(m.object for m in mesh.modifiers if m.type == "ARMATURE")
    bones = [f"spine_{i:02}" for i in range(1, 6)]
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    control = rig.data.edit_bones.new("spine_curve")
    control.head = (0, .09, .42)
    control.tail = (0, -.02, .42)
    control.parent = rig.data.edit_bones["hips"]
    control.use_deform = False
    bpy.ops.object.mode_set(mode="POSE")
    rig.data.collections.new("Spine controls").assign(rig.data.bones["spine_curve"])
    pose = rig.pose.bones["spine_curve"]
    fractions = (.16, .24, .27, .21, .12)
    for bone, fraction in zip(bones, fractions):
        for axis, prop in enumerate(("flex", "twist", "side_bend")):
            if prop not in pose:
                pose[prop] = 0.0
                pose.id_properties_ui(prop).update(min=-35, max=35, description="Distributed angle in degrees")
            constraint = rig.pose.bones[bone].constraints.new("TRANSFORM")
            constraint.name = f"Spine curve {prop}"
            constraint.target = rig
            constraint.subtarget = pose.name
            constraint.owner_space = constraint.target_space = "LOCAL"
            constraint.mix_mode_rot = "ADD"
            constraint.map_from = constraint.map_to = "ROTATION"
            setattr(constraint, f"map_to_{'xyz'[axis]}_from", "XYZ"[axis])
            setattr(constraint, f"from_min_{'xyz'[axis]}_rot", math.radians(-35))
            setattr(constraint, f"from_max_{'xyz'[axis]}_rot", math.radians(35))
            setattr(constraint, f"to_min_{'xyz'[axis]}_rot", math.radians(-35 * fraction))
            setattr(constraint, f"to_max_{'xyz'[axis]}_rot", math.radians(35 * fraction))
            driver = pose.driver_add("rotation_euler", axis).driver if bone == bones[0] else None
            if driver:
                variable = driver.variables.new()
                variable.targets[0].id = rig
                variable.targets[0].data_path = f'pose.bones["spine_curve"]["{prop}"]'
                driver.expression = f"{variable.name} * {math.pi / 180}"
    pose.rotation_mode = "XYZ"
    bpy.ops.wm.save_as_mainfile(filepath=str(output.resolve()), compress=True)
    rig.animation_data.action = None
    for track in rig.animation_data.nla_tracks:
        track.mute = True
    for bone in rig.pose.bones:
        bone.matrix_basis = Matrix.Identity(4)
    scene = bpy.context.scene
    cam = bpy.data.objects.new("Spine review", bpy.data.cameras.new("Spine review"))
    scene.collection.objects.link(cam)
    scene.camera = cam
    cam.data.type = "ORTHO"
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = scene.render.resolution_y = 512
    scene.render.resolution_percentage = 100
    scene.display.shading.show_cavity = True
    torso = [v.index for v in mesh.data.vertices if abs(v.co.x) < .12 and -.12 < v.co.y < .23
             and mesh.data.attributes["part_id"].data[v.index].value == 6]
    region = set(torso)
    edges = np.array([tuple(e.vertices) for e in mesh.data.edges if set(e.vertices) <= region])

    def sample():
        rig.update_tag()
        bpy.context.view_layer.update()
        evaluated = mesh.evaluated_get(bpy.context.evaluated_depsgraph_get())
        coords = np.empty(len(mesh.data.vertices) * 3, dtype=np.float32)
        evaluated.data.vertices.foreach_get("co", coords)
        xyz = coords.reshape(-1, 3)
        return np.linalg.norm(xyz[edges[:, 0]] - xyz[edges[:, 1]], axis=1), xyz

    neutral, base = sample()
    results = {}
    for prop in ("flex", "twist", "side_bend"):
        for angle in (-30, -15, 15, 30):
            pose[prop] = float(angle)
            lengths, xyz = sample()
            maximum = float(np.linalg.norm(xyz[torso] - base[torso], axis=1).max())
            assert maximum > .001, (prop, angle)
            results[f"{prop}_{angle}"] = {
                "edge_strain_p95": float(np.quantile(abs(lengths / np.maximum(neutral, 1e-8) - 1), .95)),
                "max_displacement": maximum,
            }
            if abs(angle) == 30:
                for view in ("three_quarter", "bottom"):
                    render(scene, cam, abs(angle), f"{prop}_{angle}_{view}", VIEWS[view],
                           (0, 0, .22), 1.35, destination)
            pose[prop] = 0.0
            axis = "XYZ"[("flex", "twist", "side_bend").index(prop)]
            middle = rig.pose.bones["spine_03"]
            middle.matrix_basis = Matrix.Rotation(math.radians(angle), 4, axis)
            concentrated, _ = sample()
            results[f"{prop}_{angle}"]["single_joint_edge_strain_p95"] = float(
                np.quantile(abs(concentrated / np.maximum(neutral, 1e-8) - 1), .95))
            middle.matrix_basis = Matrix.Identity(4)
    (destination / "pose_metrics.json").write_text(json.dumps(results, indent=2) + "\n")


if __name__ == "__main__":
    main()
