"""Add keyframeable chest and whisker articulation to a separate Fare rig."""
import argparse
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def bell(value, center, radius):
    t = max(0.0, 1 - abs(value - center) / radius)
    return t * t * (3 - 2 * t)


def drive_property(rig, curve, bone_name, property_name):
    driver = curve.driver
    driver.type = "AVERAGE"
    target = driver.variables.new().targets[0]
    target.id = rig
    target.data_path = f'pose.bones["{bone_name}"]["{property_name}"]'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    if args.output.exists():
        raise ValueError("Use a new output file")
    bpy.ops.wm.open_mainfile(filepath=str(args.source.resolve()))
    mesh = bpy.data.objects["Mouse"]
    rig = next(m.object for m in mesh.modifiers if m.type == "ARMATURE")
    keys = mesh.data.shape_keys.key_blocks
    basis = keys[0]
    parts = mesh.data.attributes["part_id"].data
    snout = mesh.vertex_groups["snout"]
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    to_rig = rig.matrix_world.inverted() @ mesh.matrix_world
    for part, side in ((0, "L"), (1, "R")):
        points = [p.co.copy() for i, p in enumerate(basis.data) if parts[i].value == part]
        near = sorted(points, key=lambda p: abs(p.x))[:max(1, len(points) // 12)]
        root = sum(near, Vector()) / len(near)
        tip = max(points, key=lambda p: abs(p.x))
        bone = rig.data.edit_bones.new(f"whisker_fan.{side}")
        bone.head = to_rig @ root
        bone.tail = to_rig @ root.lerp(tip, .48)
        bone.parent = rig.data.edit_bones["snout"]
    bpy.ops.object.mode_set(mode="OBJECT")
    controls = rig.data.collections.new("Whisker articulation")
    for part, side in ((0, "L"), (1, "R")):
        name = f"whisker_fan.{side}"
        controls.assign(rig.data.bones[name])
        rig.pose.bones[name].rotation_mode = "XYZ"
        group = mesh.vertex_groups.new(name=name)
        ids = [i for i in range(len(parts)) if parts[i].value == part]
        transferred = []
        for i in ids:
            for influence in mesh.data.vertices[i].groups:
                if influence.group == snout.index and influence.weight > 0:
                    group.add([i], influence.weight, "REPLACE")
                    transferred.append(i)
                    break
        if not transferred:
            raise ValueError(f"No snout influence on whisker island {part}")
        snout.remove(transferred)
    chest = rig.pose.bones["spine_05"]
    for name, amplitude, center, width in (
        ("breath", .007, -.045, .18),
        ("heartbeat", .0015, -.11, .072),
    ):
        chest[name] = 0.0
        chest.id_properties_ui(name).update(min=0, max=1, description=f"Keyframe {name} from 0 to 1")
        key = mesh.shape_key_add(name=f"chest_{name}", from_mix=False)
        for i, point in enumerate(basis.data):
            if parts[i].value != 6:
                continue
            x, y, z = point.co
            mask = bell(y, center, width) * bell(z, .24, .125)
            key.data[i].co = point.co + Vector((x * 7, 0, (z - .25) * 6)) * (mask * amplitude)
        drive_property(rig, key.driver_add("value"), chest.name, name)
    for side in ("L", "R"):
        for target, lower, paw in (("ik_hand", "forearm", "hand"), ("ik_foot", "shin", "foot")):
            control = rig.pose.bones[f"{target}.{side}"]
            control["IK"] = 1.0
            control.id_properties_ui("IK").update(min=0, max=1, description="0 = direct bone posing, 1 = IK target")
            for segment, constraint in ((lower, "IK"), (paw, "IKROT")):
                curve = rig.pose.bones[f"{segment}.{side}"].constraints[constraint].driver_add("influence")
                drive_property(rig, curve, control.name, "IK")
    bpy.ops.object.mode_set(mode="POSE")
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output.resolve()), compress=True)


if __name__ == "__main__":
    main()
