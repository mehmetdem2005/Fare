"""Create a separate expression demo and bake two evaluated clips for glTF."""
import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix

sys.path.insert(0, str(Path(__file__).resolve().parent))
from round41_export_and_glb_reimport import load_glb_json

SPRINT = "Sprint"
IDLE = "Idle_expressions"


def add_track(owner, name, action, slot):
    track = owner.animation_data.nla_tracks.new()
    track.name = name
    strip = track.strips.new(name, 1, action)
    strip.action_slot = slot


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("action")
    parser.add_argument("output", type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=False)
    bpy.ops.wm.open_mainfile(filepath=str(args.source.resolve()))
    scene = bpy.context.scene
    mesh = bpy.data.objects["Mouse"]
    rig = next(mod.object for mod in mesh.modifiers if mod.type == "ARMATURE")
    rig_animation = rig.animation_data
    keys = mesh.data.shape_keys
    key_animation = keys.animation_data
    sprint = bpy.data.actions[args.action]
    for track in rig_animation.nla_tracks:
        track.mute = True
    rig_animation.action = None
    for bone in rig.pose.bones:
        bone.matrix_basis = Matrix.Identity(4)
    idle = bpy.data.actions.get(IDLE)
    if idle is None:
        chest = rig.pose.bones["spine_05"]
        for name, schedule in {
            "breath": {1: 0, 12: .24, 23: .65, 31: .39, 41: .08, 49: 0},
            "heartbeat": {1: 0, 7: 0, 9: .5, 12: 0, 25: 0, 28: .5, 31: 0, 45: 0, 49: 0},
        }.items():
            for frame, value in schedule.items():
                chest[name] = float(value)
                chest.keyframe_insert(data_path=f'["{name}"]', frame=frame, group=chest.name)
        for side, phase in (("L", 0), ("R", 4)):
            bone = rig.pose.bones[f"whisker_fan.{side}"]
            bone.rotation_mode = "XYZ"
            for frame, angle in ((1, 0), (10 + phase, 5), (17 + phase, -2), (28 + phase, 2), (49, 0)):
                bone.rotation_euler.z = math.radians(angle)
                bone.keyframe_insert(data_path="rotation_euler", frame=frame, group=bone.name)
        idle = rig_animation.action
        idle.name = IDLE
        idle.use_fake_user = True
    else:
        rig_animation.action = idle
    idle_slot = rig_animation.action_slot
    rig_animation.action = sprint
    sprint_slot = rig_animation.action_slot
    scene.frame_start = 1
    scene.frame_end = 25
    scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output / "FARE_POSE_REVIEW_UNAPPROVED.blend"), compress=True)

    # Capture morph weights from the live driver graph, before replacing drivers
    # with disposable NLA curves in the export session.
    morph_values = {}
    clips = ((SPRINT, sprint, sprint_slot, 25), (IDLE, idle, idle_slot, 49))
    for name, action, slot, end in clips:
        rig_animation.action = action
        rig_animation.action_slot = slot
        morph_values[name] = {}
        for frame in range(1, end + 1):
            scene.frame_set(frame)
            evaluated = keys.evaluated_get(bpy.context.evaluated_depsgraph_get())
            morph_values[name][frame] = {key.name: key.value for key in list(evaluated.key_blocks)[1:]}

    rig_animation.action = None
    for track in list(rig_animation.nla_tracks):
        rig_animation.nla_tracks.remove(track)
    for track in list(key_animation.nla_tracks):
        key_animation.nla_tracks.remove(track)
    for driver in list(key_animation.drivers):
        key_animation.drivers.remove(driver)
    for name, action, slot, end in clips:
        add_track(rig, name, action, slot)
        key_animation.action = None
        for frame, values in morph_values[name].items():
            for shape, value in values.items():
                key = keys.key_blocks[shape]
                key.value = value
                key.keyframe_insert(data_path="value", frame=frame)
        key_action, key_slot = key_animation.action, key_animation.action_slot
        key_action.name = name + "_BakedMorphs"
        key_animation.action = None
        add_track(keys, name, key_action, key_slot)
    if rig.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    for obj in bpy.context.selected_objects:
        obj.select_set(False)
    rig.select_set(True)
    mesh.select_set(True)
    scene.frame_end = 49
    scene.frame_set(1)
    glb = args.output / "FARE_POSE_REVIEW_UNAPPROVED.glb"
    bpy.ops.export_scene.gltf(
        filepath=str(glb), use_selection=True, export_animation_mode="NLA_TRACKS",
        export_bake_animation=True, export_morph_animation=True, export_frame_range=False,
        export_frame_step=1, export_force_sampling=True, export_anim_slide_to_zero=True,
        export_influence_nb=8,
    )
    document = load_glb_json(glb)
    names = [animation["name"] for animation in document["animations"]]
    if set(names) != {SPRINT, IDLE}:
        raise RuntimeError(f"Unexpected glTF clips {names}")
    channels = {animation["name"]: [c["target"]["path"] for c in animation["channels"]]
                for animation in document["animations"]}
    if any("weights" not in c or "rotation" not in c for c in channels.values()):
        raise RuntimeError("GLB must have both skeletal and morph channels for both clips")
    report = {
        "source": str(args.source), "blender": bpy.app.version_string,
        "joints": len(document["skins"][0]["joints"]), "channels": channels,
        "morph_names": document["meshes"][0]["extras"]["targetNames"],
        "sampled_morphs": morph_values,
    }
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(glb))
    report["reimport_actions"] = list(bpy.data.actions.keys())
    report["reimport_bones"] = [len(o.data.bones) for o in bpy.data.objects if o.type == "ARMATURE"]
    report["reimport_meshes"] = [{"name": o.name, "uv_layers": list(o.data.uv_layers.keys()),
                                  "materials": list(o.data.materials.keys()),
                                  "shape_keys": list(o.data.shape_keys.key_blocks.keys()) if o.data.shape_keys else []}
                                 for o in bpy.context.scene.objects if o.type == "MESH"]
    (args.output / "glb_export_reimport.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
