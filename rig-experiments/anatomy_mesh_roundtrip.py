"""Compare animated Blender world surfaces after a real glTF reimport."""
import argparse
import json
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix
from mathutils.kdtree import KDTree

SAMPLES = {"Sprint": (1, 7, 9, 14, 25), "Idle_expressions": (1, 9, 23, 28, 49)}


def rig_for(mesh):
    return next(mod.object for mod in mesh.modifiers if mod.type == "ARMATURE")


def vertices(mesh):
    bpy.context.view_layer.update()
    obj = mesh.evaluated_get(bpy.context.evaluated_depsgraph_get())
    return [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]


def nearest_distances(target, source):
    tree = KDTree(len(target))
    for index, point in enumerate(target):
        tree.insert(point, index)
    tree.balance()
    values = [tree.find(point)[2] for point in source]
    worst = int(np.argmax(values))
    return {"max": values[worst], "max_source_vertex": worst, "p95": float(np.quantile(values, .95))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("blend", type=Path)
    parser.add_argument("glb", type=Path)
    parser.add_argument("sprint")
    parser.add_argument("output", type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    bpy.ops.wm.open_mainfile(filepath=str(args.blend.resolve()))
    mesh = bpy.data.objects["Mouse"]
    rig = rig_for(mesh)
    scene = bpy.context.scene
    rig.animation_data.use_nla = False
    surface_vertices = {i for face in mesh.data.polygons for i in face.vertices}
    source = {}
    for name, frames in SAMPLES.items():
        rig.animation_data.action = None
        for bone in rig.pose.bones:
            bone.matrix_basis = Matrix.Identity(4)
        rig.animation_data.action = bpy.data.actions[args.sprint if name == "Sprint" else name]
        for frame in frames:
            scene.frame_set(frame)
            source[name, frame] = vertices(mesh)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(args.glb.resolve()))
    mesh = next(obj for obj in bpy.context.scene.objects
                if obj.type == "MESH" and obj.data.shape_keys is not None)
    rig = rig_for(mesh)
    scene = bpy.context.scene
    report = {"blender": bpy.app.version_string, "source_vertices": len(next(iter(source.values()))),
              "reimport_vertices": len(mesh.data.vertices), "reimport_fps": scene.render.fps, "samples": {}}
    for name, frames in SAMPLES.items():
        for owner in (rig, mesh.data.shape_keys):
            animation = owner.animation_data
            animation.action = None
            for track in animation.nla_tracks:
                track.mute = not any(strip.action.name == name for strip in track.strips)
        start = next(strip.frame_start for track in rig.animation_data.nla_tracks if not track.mute
                     for strip in track.strips if strip.action.name == name)
        for frame in frames:
            import_frame = start + (frame - 1) * scene.render.fps / 24
            base_frame = int(import_frame)
            scene.frame_set(base_frame, subframe=import_frame - base_frame)
            imported = vertices(mesh)
            reference = source[name, frame]
            forward = nearest_distances(imported, reference)
            forward["worst_vertex_has_source_face"] = forward["max_source_vertex"] in surface_vertices
            report["samples"][f"{name}@{frame}"] = {
                "reference_to_reimport": forward,
                "reimport_to_reference": nearest_distances(reference, imported),
            }
    args.output.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
