extends SceneTree
func _initialize() -> void:
    call_deferred("_run")
func _fail(reason: String) -> void:
    push_error("S5_SUN_SYNC_FAIL "+reason)
    quit(2)
func _run() -> void:
    var game: Node3D=(load("res://scenes/main.tscn") as PackedScene).instantiate() as Node3D
    root.add_child(game)
    var atmosphere: ForestAtmosphere=game.get("atmosphere") as ForestAtmosphere
    game.call("_add_chunk",Vector2i(0,2))
    var remote: Node3D=game.get_node("Chunk_0_2") as Node3D
    var water: MeshInstance3D=remote.get_node("FlowingWater") as MeshInstance3D
    game.call("set_atmosphere_preset",ForestAtmosphere.EVENING)
    var expected: Color=atmosphere.sky_material.sky_horizon_color
    for key in ["high_water_material","low_water_material"]:
        var mat: ShaderMaterial=water.get_meta(key) as ShaderMaterial
        if mat==null:
            _fail("missing stored "+key)
            return
        var observed: Vector3=mat.get_shader_parameter("sky_reflection_horizon")
        if absf(observed.x-expected.r)>0.0001 or absf(observed.z-expected.b)>0.0001:
            _fail("stale reflection in "+key)
            return
    var actor: CharacterBody3D=game.get("player") as CharacterBody3D
    actor.global_position=Vector3(20.0,4.0,95.0)
    game.call("_update_chunk_lod")
    var seen: Vector3=(water.material_override as ShaderMaterial).get_shader_parameter("sky_reflection_horizon")
    if absf(seen.x-expected.r)>0.0001:
        _fail("stale active reflection after switching LOD")
        return
    print("S5_SUN_SYNC_OK LOD_variants=2 sunset=coherent")
    quit(0)
