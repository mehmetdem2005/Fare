extends SceneTree

# Round42 independent runtime resource inspection in real Godot 4.7.2.
# This does NOT assert that Redmi Note 8 Pro Android GPU playback is smooth.
# It validates a saved GLB's imported armature, blendshapes, and animation
# tracks by instantiating the actual imported PackedScene.
func _initialize() -> void:
    var result: Dictionary = {
        "status": "STARTED",
        "engine": Engine.get_version_info(),
        "real_godot_scene_instance": false,
        "skeleton_count": 0,
        "max_bone_count": 0,
        "mesh_instance_count": 0,
        "blend_shape_count": 0,
        "reference_f14_morph_found": false,
        "animation_player_count": 0,
        "animation_count": 0,
        "animation_track_count": 0,
        "blend_shape_animation_tracks": 0,
        "rotation_animation_tracks": 0,
        "morph_names": [],
        "animation_names": [],
        "issues": []
    }
    var res: Resource = load("res://R41_FARE_49BONE_SPRINT_CORRECTED_REVIEW_ONLY.glb")
    if res == null or not (res is PackedScene):
        result["issues"].append("Godot did not import GLB to a PackedScene")
        _finish(result)
        return
    var node: Node = (res as PackedScene).instantiate()
    if node == null:
        result["issues"].append("Imported GLB PackedScene failed to instantiate")
        _finish(result)
        return
    get_root().add_child(node)
    result["real_godot_scene_instance"] = true
    var pending: Array[Node] = [node]
    while not pending.is_empty():
        var current: Node = pending.pop_back()
        for child: Node in current.get_children():
            pending.append(child)
        if current is Skeleton3D:
            result["skeleton_count"] += 1
            result["max_bone_count"] = max(result["max_bone_count"], (current as Skeleton3D).get_bone_count())
        if current is MeshInstance3D:
            var obj: MeshInstance3D = current as MeshInstance3D
            result["mesh_instance_count"] += 1
            if obj.mesh != null:
                result["blend_shape_count"] += obj.mesh.get_blend_shape_count()
                for i in range(obj.mesh.get_blend_shape_count()):
                    var name: String = str(obj.mesh.get_blend_shape_name(i))
                    result["morph_names"].append(name)
                    if name == "R39_F14_ORIGINAL_REFERENCE":
                        result["reference_f14_morph_found"] = true
        if current is AnimationPlayer:
            var player: AnimationPlayer = current as AnimationPlayer
            result["animation_player_count"] += 1
            for anim_name: StringName in player.get_animation_list():
                var animation: Animation = player.get_animation(anim_name)
                if animation == null:
                    result["issues"].append("Null animation in imported animation player")
                    continue
                result["animation_count"] += 1
                result["animation_names"].append(str(anim_name))
                result["animation_track_count"] += animation.get_track_count()
                for track in range(animation.get_track_count()):
                    if animation.track_get_type(track) == Animation.TYPE_BLEND_SHAPE:
                        result["blend_shape_animation_tracks"] += 1
                    if animation.track_get_type(track) == Animation.TYPE_ROTATION_3D:
                        result["rotation_animation_tracks"] += 1
    if result["skeleton_count"] < 1 or result["max_bone_count"] < 45:
        result["issues"].append("Godot importer lost essential 49-bone skeleton")
    if result["blend_shape_count"] < 15:
        result["issues"].append("Godot importer lost almost all 29 target shapes")
    if not result["reference_f14_morph_found"]:
        result["issues"].append("Crucial f14 anatomical reference morph absent after Godot GLB import")
    if result["animation_count"] < 1:
        result["issues"].append("Godot imported no usable animations")
    if result["blend_shape_animation_tracks"] < 1:
        result["issues"].append("Godot animation lacks real blend shape morph track")
    if result["rotation_animation_tracks"] < 15:
        result["issues"].append("Godot animation lost skeletal rotation tracks")
    _finish(result)

func _finish(info: Dictionary) -> void:
    info["status"] = "PASS_GODOT_472_HEADLESS_IMPORTED_MORPH_AND_ANIMATION_ANDROID_NOT_TESTED" if info["issues"].is_empty() else "REJECT_GODOT_IMPORT_L5"
    var file: FileAccess = FileAccess.open("res://round42_godot_import.json", FileAccess.WRITE)
    if file == null:
        push_error("Could not save Godot import evidence")
        quit(1)
        return
    file.store_string(JSON.stringify(info, "\t"))
    file.close()
    print("ROUND42_GODOT ", JSON.stringify(info))
    quit(0 if info["issues"].is_empty() else 1)
