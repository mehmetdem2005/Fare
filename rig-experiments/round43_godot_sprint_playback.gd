extends SceneTree

# Round43: real Godot 4.7.2 AnimationPlayer SEEK playback of the imported GLB.
# Verifies actual frame14 weight 0.90 (not merely shape existence), animated
# bone movement, and periodic frame1/frame25 seam. This remains Linux headless;
# Mali/Android device gameplay is a separate physical test.

func _initialize() -> void:
    var report: Dictionary = {"status":"STARTED","sampled":{},
        "bone_count":0,"active_animation":"","animation_length":0.0,"errors":[]}
    var resource: Resource = load("res://R41_FARE_49BONE_SPRINT_CORRECTED_REVIEW_ONLY.glb")
    if resource == null or not (resource is PackedScene):
        report["errors"].append("GLB PackedScene could not load")
        _finish(report)
        return
    var root: Node = (resource as PackedScene).instantiate()
    get_root().add_child(root)
    var queue: Array[Node] = [root]
    var player: AnimationPlayer = null
    var skeleton: Skeleton3D = null
    var body: MeshInstance3D = null
    var morph_index: int = -1
    while not queue.is_empty():
        var node: Node = queue.pop_back()
        for child: Node in node.get_children():
            queue.append(child)
        if node is AnimationPlayer:
            player = node as AnimationPlayer
        if node is Skeleton3D:
            skeleton = node as Skeleton3D
        if node is MeshInstance3D:
            var test_mesh: MeshInstance3D = node as MeshInstance3D
            if test_mesh.mesh != null:
                for i in range(test_mesh.mesh.get_blend_shape_count()):
                    if str(test_mesh.mesh.get_blend_shape_name(i)) == "R39_F14_ORIGINAL_REFERENCE":
                        morph_index = i
                        body = test_mesh
    if player == null or skeleton == null or body == null:
        report["errors"].append("Missing AnimationPlayer/Skeleton3D/f14 morph-bearing MeshInstance3D")
        _finish(report)
        return
    report["bone_count"] = skeleton.get_bone_count()
    report["reference_morph_index"] = morph_index
    var names: PackedStringArray = player.get_animation_list()
    if names.is_empty():
        report["errors"].append("No imported animation actions")
        _finish(report)
        return
    var anim_name: StringName = StringName("MouseRig")
    if not player.has_animation(anim_name):
        report["errors"].append("MouseRig animation missing")
        _finish(report)
        return
    var anim: Animation = player.get_animation(anim_name)
    report["animation_length"] = anim.length
    report["active_animation"] = str(anim_name)
    # Blender exporter used source frame1 at t=1/24, frame25 at t=25/24;
    # don't incorrectly map frame1 to imported t=0.
    player.play(anim_name)
    var sample_frames: Array[int] = [1,9,10,14,15,17,25]
    var hip_index: int = skeleton.find_bone("hips")
    if hip_index < 0:
        report["errors"].append("Godot lost hips bone")
        _finish(report)
        return
    for frame: int in sample_frames:
        var time_value: float = float(frame) / 24.0
        player.seek(time_value, true)
        player.advance(0.0)
        var weight: float = body.get_blend_shape_value(morph_index)
        var q: Quaternion = skeleton.get_bone_pose_rotation(hip_index)
        report["sampled"][str(frame)] = {
            "time_seconds": time_value, "reference_morph_weight": weight,
            "hips_rotation_xyzw": [q.x,q.y,q.z,q.w]
        }
        print("ROUND43_POSE",frame,"time",time_value,"f14 weight",weight,
            "hips_quat",q)
    var f1: float = report["sampled"]["1"]["reference_morph_weight"]
    var f14: float = report["sampled"]["14"]["reference_morph_weight"]
    var f15: float = report["sampled"]["15"]["reference_morph_weight"]
    var f25: float = report["sampled"]["25"]["reference_morph_weight"]
    report["f14_reference_weight_error"] = absf(f14 - 0.9)
    report["frame1_25_reference_seam"] = absf(f25-f1)
    if absf(f14 - 0.9) > 0.04:
        report["errors"].append("Godot runtime did not apply frame14 anatomical shape animation")
    if absf(f1) > 0.03 or absf(f25) > 0.03:
        report["errors"].append("Reference shape correction remains active at running seam")
    if absf(f15) > 0.04:
        report["errors"].append("f14 reference morph bleeds into adjacent stride beyond safe window")
    var first: Array = report["sampled"]["1"]["hips_rotation_xyzw"]
    var middle: Array = report["sampled"]["14"]["hips_rotation_xyzw"]
    var diff: float = 0.0
    for i in range(4):
        diff = max(diff,absf(first[i]-middle[i]))
    report["hips_pose_movement_difference"] = diff
    if diff <= 0.00001:
        report["errors"].append("No actual skeletal hips pose movement during exported animation")
    var last: Array = report["sampled"]["25"]["hips_rotation_xyzw"]
    var seam: float = 0.0
    for i in range(4):
        seam=max(seam,absf(first[i]-last[i]))
    report["hips_frame1_25_quaternion_seam"] = seam
    if seam > 0.003:
        report["errors"].append("Imported hips skeletal cycle does not close at 1/25")
    if report["bone_count"] != 49:
        report["errors"].append("Expected exactly 49 skeletal bones")
    _finish(report)

func _finish(report: Dictionary) -> void:
    report["status"] = "PASS_GODOT_472_REAL_HEADLESS_PLAYBACK_ANDROID_NOT_VERIFIED" if report["errors"].is_empty() else "REJECT_GODOT_ANIMATION_PLAYBACK"
    var file: FileAccess = FileAccess.open("res://round43_godot_playback.json",FileAccess.WRITE)
    if file == null:
        push_error("Cannot write Godot playback evidence")
        quit(1)
        return
    file.store_string(JSON.stringify(report,"\t"))
    file.close()
    print("ROUND43_STATUS ",JSON.stringify(report))
    quit(0 if report["errors"].is_empty() else 1)
