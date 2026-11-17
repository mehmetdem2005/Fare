"""Record the saved rig's topology, skinning and animation dependencies."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import sys
from pathlib import Path

import bpy
from bpy_extras.anim_utils import action_get_channelbag_for_slot


def matrix(value):
    return [list(row) for row in value]


def describe_drivers(animation):
    if not animation:
        return []
    return [{
        "path": curve.data_path, "index": curve.array_index,
        "expression": curve.driver.expression, "type": curve.driver.type,
        "valid": curve.driver.is_valid,
        "variables": [{"type": var.type, "name": var.name, "targets": [
            {"object": target.id.name if target.id else None, "path": target.data_path,
             "bone": target.bone_target, "transform": target.transform_type, "space": target.transform_space}
            for target in var.targets]} for var in curve.driver.variables],
    } for curve in animation.drivers]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    bpy.ops.wm.open_mainfile(filepath=str(args.source.resolve()))
    bpy.context.view_layer.update()
    mesh = bpy.data.objects["Mouse"]
    skin = next(mod for mod in mesh.modifiers if mod.type == "ARMATURE")
    rig = skin.object
    bpy.context.view_layer.objects.active = rig
    if rig.mode != "EDIT":
        bpy.ops.object.mode_set(mode="EDIT")
    rolls = {b.name: b.roll for b in rig.data.edit_bones}
    bpy.ops.object.mode_set(mode="OBJECT")

    joints = {b.name for b in rig.data.bones if b.use_deform}
    deform_groups = {g.index for g in mesh.vertex_groups if g.name in joints}
    weights = [sum(g.weight for g in v.groups if g.group in deform_groups) for v in mesh.data.vertices]
    influence_counts = Counter(sum(g.weight > 0 for g in v.groups if g.group in deform_groups)
                               for v in mesh.data.vertices)
    parts = mesh.data.attributes["part_id"].data
    parent = list(range(len(parts)))

    def root(index):
        while index != parent[index]:
            index = parent[index]
        return index

    for edge in mesh.data.edges:
        a, b = map(root, edge.vertices)
        if a != b:
            low, high = sorted((a, b))
            parent[high] = low
    components = defaultdict(Counter)
    for i, part in enumerate(parts):
        components[root(i)][part.value] += 1

    slots = {}
    for action in bpy.data.actions:
        slots[action.name] = {"frame_range": list(action.frame_range), "slots": {}}
        for slot in action.slots:
            bag = action_get_channelbag_for_slot(action, slot)
            slots[action.name]["slots"][slot.identifier] = (
                [{"path": curve.data_path, "array_index": curve.array_index,
                  "keyframes": len(curve.keyframe_points)} for curve in bag.fcurves] if bag else []
            )
    with args.source.open("rb") as source_file:
        checksum = hashlib.file_digest(source_file, "sha256").hexdigest()
    animation = rig.animation_data
    data = {
        "source_sha256": checksum, "blender": bpy.app.version_string,
        "mesh_world": matrix(mesh.matrix_world), "armature_world": matrix(rig.matrix_world),
        "mesh_parent_inverse": matrix(mesh.matrix_parent_inverse),
        "preserve_volume": skin.use_deform_preserve_volume, "skin_vertex_group": skin.vertex_group,
        "weight_sum_min_max": [min(weights), max(weights)],
        "non_normalized_vertices": sum(abs(weight - 1) > 1e-4 for weight in weights),
        "deform_influence_counts": influence_counts,
        "parts_by_vertex_count": Counter(p.value for p in parts),
        "components": [{"first_vertex": i, "part_counts": counts} for i, counts in components.items()],
        "bones": {b.name: {"parent": b.parent.name if b.parent else None, "rest": matrix(b.matrix_local),
                           "head": list(b.head_local), "tail": list(b.tail_local), "roll_rad": rolls[b.name],
                           "deform": b.use_deform, "inherit_scale": b.inherit_scale,
                           "collections": [c.name for c in b.collections]} for b in rig.data.bones},
        "pose": {b.name: {"scale": list(b.scale), "constraints": [{
            "name": c.name, "type": c.type, "influence": c.influence, "mute": c.mute,
            **{name: getattr(c, name) for name in (
                "subtarget", "pole_subtarget", "pole_angle", "chain_count", "owner_space", "target_space"
            ) if hasattr(c, name)},
            **{name: getattr(c, name).name if getattr(c, name) else None for name in ("target", "pole_target")
               if hasattr(c, name)},
        } for c in b.constraints]} for b in rig.pose.bones},
        "actions": slots,
        "active_action": animation.action.name if animation and animation.action else None,
        "nla": [{"name": track.name, "mute": track.mute} for track in animation.nla_tracks] if animation else [],
        "armature_drivers": describe_drivers(animation),
        "shape_drivers": describe_drivers(mesh.data.shape_keys.animation_data),
        "shape_keys": [k.name for k in mesh.data.shape_keys.key_blocks],
    }
    args.output.write_text(json.dumps(data, indent=2) + "\n")


if __name__ == "__main__":
    main()
