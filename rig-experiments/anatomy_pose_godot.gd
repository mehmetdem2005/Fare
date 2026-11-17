extends SceneTree

const SPRINT = "Sprint"
const IDLE = "Idle_expressions"

func _initialize() -> void:
    call_deferred("_run")

func _run() -> void:
    var model := load("res://FARE_POSE_REVIEW_UNAPPROVED.glb") as PackedScene
    var report := {"godot": Engine.get_version_info()["string"], "errors": [], "clips": {}}
    if model == null:
        report.errors.append("GLB does not load as PackedScene")
        _finish(report)
        return
    var root := model.instantiate()
    get_root().add_child(root)
    var skeleton := root.find_children("*", "Skeleton3D", true, false).front() as Skeleton3D
    var player := root.find_children("*", "AnimationPlayer", true, false).front() as AnimationPlayer
    var body := root.find_children("*", "MeshInstance3D", true, false).front() as MeshInstance3D
    var expected: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://glb_export_reimport.json"))
    if skeleton == null or player == null or body == null:
        report.errors.append("Missing skeleton, mesh or AnimationPlayer")
        _finish(report)
        return
    report.bones = skeleton.get_bone_count()
    report.morph_count = body.get_blend_shape_count()
    if report.bones != expected.joints or report.morph_count != expected.morph_names.size():
        report.errors.append("Imported skeleton or morph count differs from GLB")

    for clip: String in [SPRINT, IDLE]:
        if not player.has_animation(clip):
            report.errors.append("Missing clip " + clip)
            continue
        var action := player.get_animation(clip)
        var samples := {}
        var frames: Array = [1, 6, 7, 8, 9, 10, 14, 25] if clip == SPRINT else [1, 9, 14, 23, 28, 49]
        var latest_frame: int = frames.back()
        var morph_error := 0.0
        var bone_span := 0.0
        var seam_translation := 0.0
        var seam_rotation := 0.0
        var start: Array[Transform3D] = []
        var indices: Array[int] = []
        for bone: String in ["hips", "hand.L", "hand.R", "foot.L", "foot.R", "whisker_fan.L", "whisker_fan.R"]:
            var index := skeleton.find_bone(bone)
            if index >= 0:
                indices.append(index)
            else:
                report.errors.append("Missing bone " + bone)
        player.play(clip)
        for frame: int in frames:
            player.seek(float(frame - 1) / 24.0, true)
            player.advance(0.0)
            skeleton.force_update_all_bone_transforms()
            var weights := {}
            for morph: String in ["chest_breath", "chest_heartbeat", "trial_right_knee_pose"]:
                var i := body.find_blend_shape_by_name(morph)
                if i < 0:
                    report.errors.append("Missing morph " + morph)
                    continue
                var value := body.get_blend_shape_value(i)
                weights[morph] = value
                morph_error = maxf(morph_error, absf(value - float(expected.sampled_morphs[clip][str(frame)][morph])))
            var poses := {}
            for j: int in range(indices.size()):
                var index := indices[j]
                var pose := skeleton.get_bone_global_pose(index)
                var q := pose.basis.get_rotation_quaternion()
                poses[skeleton.get_bone_name(index)] = {
                    "translation": [pose.origin.x, pose.origin.y, pose.origin.z],
                    "rotation_xyzw": [q.x, q.y, q.z, q.w],
                }
                if frame == 1:
                    start.append(pose)
                else:
                    var displacement := pose.origin.distance_to(start[j].origin)
                    var angle := q.angle_to(start[j].basis.get_rotation_quaternion())
                    bone_span = maxf(bone_span, maxf(displacement, angle))
                    if frame == latest_frame:
                        seam_translation = maxf(seam_translation, displacement)
                        seam_rotation = maxf(seam_rotation, angle)
            samples[str(frame)] = {"weights": weights, "bone_poses": poses}
        player.stop()
        report.clips[clip] = {"seconds": action.length, "tracks": action.get_track_count(),
            "max_morph_error": morph_error, "max_sampled_bone_span": bone_span,
            "max_seam_translation": seam_translation, "max_seam_rotation_rad": seam_rotation,
            "samples": samples}
        if absf(action.length - float(latest_frame - 1) / 24.0) > .005 or morph_error > .025 or bone_span < .005:
            report.errors.append("Duration, morph or animated bone check failed for " + clip)
        if seam_translation > .002 or seam_rotation > .015:
            report.errors.append("Sampled bone cycle seam failed for " + clip)
    _finish(report)

func _finish(report: Dictionary) -> void:
    var file := FileAccess.open("res://godot_playback.json", FileAccess.WRITE)
    file.store_string(JSON.stringify(report, "\t"))
    file.close()
    print("FARE_GODOT ", report.errors)
    quit(0 if report.errors.is_empty() else 1)
