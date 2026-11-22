extends SceneTree
# Run: godot --headless --path . -s res://tests/v3_forest_material_test.gd
func _initialize() -> void:
    call_deferred("_run")

func _fail(msg: String) -> void:
    push_error("V3_FOREST_FAIL "+msg)
    quit(2)

func _run() -> void:
    var scene: PackedScene=load("res://scenes/main.tscn") as PackedScene
    var game: Node3D=scene.instantiate() as Node3D
    root.add_child(game)
    var pine: ArrayMesh=game.get("pine_mesh") as ArrayMesh
    if pine==null or pine.get_surface_count()!=2:
        _fail("Bark and needles must be separate opaque material surfaces")
        return
    for i in range(2):
        var m: StandardMaterial3D=pine.surface_get_material(i) as StandardMaterial3D
        if m==null or m.albedo_color.r>0.6 or m.albedo_color.g>0.7:
            _fail("Missing or white pine surface "+str(i))
            return
    var grass: ArrayMesh=game.get("grass_mesh") as ArrayMesh
    if grass==null or grass.get_surface_count()!=1:
        _fail("Grass mesh missing")
        return
    var gm: StandardMaterial3D=grass.surface_get_material(0) as StandardMaterial3D
    if gm==null or gm.transparency!=BaseMaterial3D.TRANSPARENCY_DISABLED:
        _fail("Grass is missing opaque mobile material")
        return
    var ground: ShaderMaterial=game.get("terrain_lite_mat") as ShaderMaterial
    if ground==null or ground.get_shader_parameter("grass_nr")==null:
        _fail("Fast terrain missing packed grass relief map")
        return
    var trees: MultiMeshInstance3D=game.get_node_or_null("Chunk_0_0/Pines") as MultiMeshInstance3D
    var tufts: MultiMeshInstance3D=game.get_node_or_null("Chunk_0_0/Grass") as MultiMeshInstance3D
    if trees==null or tufts==null or trees.multimesh.instance_count<8 or tufts.multimesh.instance_count<400:
        _fail("Sparse vegetation after density/scale patch")
        return
    var water: ShaderMaterial=game.get("water_lite_mat") as ShaderMaterial
    if water==null or water.shader==null or water.shader.code.find("vec4 w2=")<0:
        _fail("Fast water wave normal shader missing")
        return
    var rig: Skeleton3D=game.get("rig") as Skeleton3D
    if rig==null or rig.get_bone_count()!=49:
        _fail("Original mouse skeleton missing")
        return
    print("V3_FOREST_OK pine_surfaces=2 grass_density="+str(tufts.multimesh.instance_count)+" rig=49 packed_normal=ok wave=ok")
    quit(0)
