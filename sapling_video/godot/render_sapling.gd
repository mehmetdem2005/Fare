extends SceneTree

func _initialize() -> void:
    call_deferred("_go")

func _go() -> void:
    var roots_closeup: bool = OS.get_cmdline_user_args().has("--roots-closeup")
    root.size = Vector2i(1200, 1000)
    var stage := Node3D.new()
    root.add_child(stage)
    var environment := WorldEnvironment.new()
    environment.environment = Environment.new()
    environment.environment.background_mode = Environment.BG_COLOR
    environment.environment.background_color = Color(0.70, 0.79, 0.81)
    environment.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
    environment.environment.ambient_light_color = Color(0.86, 0.92, 1.0)
    environment.environment.ambient_light_energy = 0.72
    stage.add_child(environment)
    var sun := DirectionalLight3D.new()
    sun.rotation_degrees = Vector3(-42, -35, 0)
    sun.light_color = Color(1, 0.92, 0.8)
    sun.light_energy = 1.75
    sun.shadow_enabled = true
    stage.add_child(sun)
    var ground := MeshInstance3D.new()
    var ground_mesh := PlaneMesh.new()
    ground_mesh.size = Vector2(45, 45)
    ground.mesh = ground_mesh
    var ground_mat := StandardMaterial3D.new()
    ground_mat.albedo_color = Color(0.28, 0.37, 0.27)
    ground_mat.roughness = 0.96
    ground.material_override = ground_mat
    stage.add_child(ground)
    var source: PackedScene = load("res://sapling_pine.glb")
    if source == null:
        push_error("VIDEO_SAPLING_RENDER_FAIL: no imported GLB")
        quit(1)
        return
    var tree: Node3D = source.instantiate()
    tree.name = "SaplingSmallPine"
    stage.add_child(tree)
    var box: AABB = AABB()
    var has_geo := false
    var count := 0
    var queue: Array[Node] = [tree]
    while not queue.is_empty():
        var node: Node = queue.pop_back()
        if node is MeshInstance3D:
            var instance: MeshInstance3D = node as MeshInstance3D
            if instance.mesh != null:
                if roots_closeup and "needle" in instance.name.to_lower():
                    instance.visible = false
                var bounds: AABB = instance.global_transform * instance.mesh.get_aabb()
                if has_geo:
                    box = box.merge(bounds)
                else:
                    box = bounds
                    has_geo = true
                count += 1
        for child in node.get_children():
            queue.append(child)
    if not has_geo:
        push_error("VIDEO_SAPLING_RENDER_FAIL: GLB has no mesh")
        quit(1)
        return
    var tree_height := box.size.y
    if tree_height < 0.1 or tree_height > 100:
        push_error("VIDEO_SAPLING_RENDER_FAIL: bad geometry height " + str(tree_height))
        quit(1)
        return
    var camera := Camera3D.new()
    stage.add_child(camera)
    camera.position = Vector3(1.65, 0.82, 2.65) if roots_closeup else Vector3(tree_height * 1.35, tree_height * 0.8, tree_height * 2.5)
    camera.fov = 42 if roots_closeup else 47
    camera.near = 0.03
    camera.far = 200
    camera.look_at(Vector3(0.0, 0.21, 0.0) if roots_closeup else box.get_center(), Vector3.UP)
    camera.current = true
    await process_frame
    await process_frame
    await process_frame
    await RenderingServer.frame_post_draw
    var image: Image = root.get_texture().get_image()
    if image == null or image.is_empty():
        push_error("VIDEO_SAPLING_RENDER_FAIL: no framebuffer")
        quit(1)
        return
    DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path("res://out"))
    var path := "res://out/sapling_roots_closeup_godot472.png" if roots_closeup else "res://out/sapling_video_exact_godot472.png"
    var error := image.save_png(path)
    if error != OK:
        push_error("VIDEO_SAPLING_RENDER_FAIL: " + error_string(error))
        quit(1)
        return
    print("VIDEO_SAPLING_RENDER_OK meshes=",count," bounds=",box," screenshot=",path)
    quit(0)
