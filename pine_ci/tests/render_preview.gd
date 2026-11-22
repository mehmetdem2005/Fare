extends SceneTree

func _initialize() -> void:
	call_deferred("_render")

func _render() -> void:
	var shape: int = 0
	for argument in OS.get_cmdline_user_args():
		if argument.begins_with("--shape="):
			shape = int(argument.get_slice("=", 1))
	if shape < 0 or shape > 2:
		push_error("Invalid shape")
		quit(1)
		return
	root.size = Vector2i(1280, 900)
	var stage := Node3D.new()
	root.add_child(stage)
	var sky := WorldEnvironment.new()
	sky.environment = Environment.new()
	sky.environment.background_mode = Environment.BG_COLOR
	sky.environment.background_color = Color(0.66, 0.79, 0.86)
	sky.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	sky.environment.ambient_light_color = Color(0.88, 0.90, 1.0)
	sky.environment.ambient_light_energy = 0.85
	stage.add_child(sky)

	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-43.0, -37.0, 0.0)
	sun.light_energy = 1.9
	sun.light_color = Color(1.0, 0.95, 0.82)
	sun.shadow_enabled = true
	stage.add_child(sun)

	var fill := DirectionalLight3D.new()
	fill.rotation_degrees = Vector3(-28.0, 130.0, 0.0)
	fill.light_energy = 0.35
	fill.light_color = Color(0.72, 0.82, 1.0)
	stage.add_child(fill)

	var floor_mesh := PlaneMesh.new()
	floor_mesh.size = Vector2(80.0, 80.0)
	var ground := MeshInstance3D.new()
	ground.mesh = floor_mesh
	var ground_mat := StandardMaterial3D.new()
	ground_mat.albedo_color = Color(0.32, 0.40, 0.29)
	ground_mat.roughness = 0.99
	ground.material_override = ground_mat
	stage.add_child(ground)

	var pine_script: Script = load("res://PineTreeGenerator.gd")
	if pine_script == null or not pine_script.can_instantiate():
		push_error("Cannot instantiate PineTreeGenerator")
		quit(1)
		return
	var pine: Node3D = pine_script.new()
	pine.set("crown_shape", shape)
	pine.set("wind_enabled", false)
	stage.add_child(pine)
	var camera := Camera3D.new()
	camera.position = Vector3(11.0, 9.0, 19.0)
	camera.fov = 45.0
	camera.near = 0.1
	camera.far = 150.0
	stage.add_child(camera)
	camera.look_at(Vector3(0.0, 6.2, 0.0), Vector3.UP)
	camera.current = true

	await process_frame
	await process_frame
	await process_frame
	print("RENDER_DEBUG height=", pine.get("height"), " trunk=", pine.get_node("Geometry/Wood/Trunk").mesh.get_aabb(), " foliage=", pine.get_node("Geometry/Crown/Foliage_LOD0").mesh.get_aabb(), " camera=", camera.global_transform)
	await RenderingServer.frame_post_draw
	var screenshot: Image = root.get_texture().get_image()
	if screenshot == null or screenshot.is_empty() or screenshot.get_width() < 100:
		push_error("PINE_RENDER_FAIL no image")
		quit(1)
		return
	var name: String = ["conical", "oval", "umbrella"][shape]
	var file: String = "res://out/pine_%s.png" % name
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path("res://out"))
	var err: Error = screenshot.save_png(file)
	if err != OK:
		push_error("PINE_RENDER_FAIL %s" % error_string(err))
		quit(1)
		return
	print("PINE_RENDER_OK ", name, " ", screenshot.get_size(), " ", file)
	quit(0)
