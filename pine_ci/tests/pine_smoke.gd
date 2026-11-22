extends SceneTree

func _initialize() -> void:
	call_deferred("_check")

func _fail(why: String) -> void:
	push_error("PINE_CI_FAIL " + why)
	quit(1)

func _check() -> void:
	var pine_script: Script = load("res://PineTreeGenerator.gd")
	if pine_script == null or not pine_script.can_instantiate():
		_fail("Script could not be loaded")
		return
	var pine: Node3D = pine_script.new()
	root.add_child(pine)
	await process_frame
	await process_frame
	if not pine.has_node("Geometry/Wood/Trunk"):
		_fail("Missing trunk")
		return
	if not pine.has_node("Geometry/Wood/Branches"):
		_fail("Missing branches")
		return
	if not pine.has_node("Geometry/Crown/Foliage_LOD0"):
		_fail("Missing LOD0")
		return
	if not pine.has_node("Geometry/Crown/Foliage_LOD1"):
		_fail("Missing LOD1")
		return
	if not pine.has_node("Collision/TrunkShape"):
		_fail("Missing collision")
		return
	print("PINE_DEBUG height=", pine.get("height"), " trunk=", pine.get_node("Geometry/Wood/Trunk").mesh.get_aabb(), " branch=", pine.get_node("Geometry/Wood/Branches").mesh.get_aabb(), " crown=", pine.get_node("Geometry/Crown/Foliage_LOD0").mesh.get_aabb())
	var branches: Mesh = pine.get_node("Geometry/Wood/Branches").mesh
	if branches == null or branches.get_surface_count() == 0:
		_fail("Missing branches mesh")
		return
	var arrays: Array = branches.surface_get_arrays(0)
	var verts: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
	var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
	if verts.size() < 100 or indices.size() < 100 or indices.size() % 3 != 0:
		_fail("Invalid geometry sizes")
		return
	for idx in indices:
		if idx < 0 or idx >= verts.size():
			_fail("Out of range branch mesh index %d of %d" % [idx, verts.size()])
			return
	var foliage0: Mesh = pine.get_node("Geometry/Crown/Foliage_LOD0").mesh
	var foliage1: Mesh = pine.get_node("Geometry/Crown/Foliage_LOD1").mesh
	if foliage0 == null or foliage1 == null:
		_fail("Missing foliage meshes")
		return
	if foliage0.surface_get_arrays(0)[Mesh.ARRAY_VERTEX].size() <= foliage1.surface_get_arrays(0)[Mesh.ARRAY_VERTEX].size():
		_fail("LOD1 is not simplified")
		return

	var first_vertices: PackedVector3Array = verts.duplicate()
	pine.call("_build_tree")
	var repeat_vertices: PackedVector3Array = pine.get_node("Geometry/Wood/Branches").mesh.surface_get_arrays(0)[Mesh.ARRAY_VERTEX]
	if first_vertices != repeat_vertices:
		_fail("Same seed produced different branch vertices")
		return
	for shape in [1, 2, 0]:
		pine.set("crown_shape", shape)
		await process_frame
		await process_frame
		if not pine.has_node("Geometry/Crown/Foliage_LOD0"):
			_fail("Crown shape %d did not rebuild" % shape)
			return
	pine.call("_export_assets")
	if not FileAccess.file_exists("res://Generated/PineTrees/seed_1337/pine_tree.tscn"):
		_fail("Export failed")
		return
	print("PINE_CI_OK branches_vertices=%d indices=%d foliage_vertices=%d" % [
		verts.size(), indices.size(), foliage0.surface_get_arrays(0)[Mesh.ARRAY_VERTEX].size()])
	quit(0)
