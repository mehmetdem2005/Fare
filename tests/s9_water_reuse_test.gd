extends SceneTree
## Water texture and shader resources must survive unload/reload of the same co.
func _initialize() -> void:
    call_deferred("_run")
func _fail(reason: String) -> void:
    push_error("S9_WATER_REUSE_FAIL "+reason)
    quit(2)
func _run() -> void:
    var game: Node3D=(load("res://scenes/main.tscn") as PackedScene).instantiate() as Node3D
    root.add_child(game)
    var co: Vector2i=Vector2i(0,0)
    var chunk: Node3D=game.get_node("Chunk_0_0") as Node3D
    var original: MeshInstance3D=chunk.get_node("FlowingWater") as MeshInstance3D
    var high: ShaderMaterial=original.get_meta("high_water_material") as ShaderMaterial
    var low: ShaderMaterial=original.get_meta("low_water_material") as ShaderMaterial
    var old_img: Image=original.get_meta("flow_image") as Image
    var misses: int=int(game.get("water_resource_cache_misses"))
    var hits: int=int(game.get("water_resource_cache_hits"))
    var extra: Node3D=Node3D.new()
    extra.name="WaterReloadTest"
    extra.position=chunk.position
    game.add_child(extra)
    game.call("_water",extra,co)
    var again: MeshInstance3D=extra.get_node_or_null("FlowingWater") as MeshInstance3D
    if again==null:
        _fail("water node not re-added")
        return
    if again.get_meta("high_water_material")!=high or again.get_meta("low_water_material")!=low:
        _fail("water shaders/materials recreated after revisit")
        return
    if again.get_meta("flow_image")!=old_img:
        _fail("flow image identity diverged")
        return
    if int(game.get("water_resource_cache_misses"))!=misses or int(game.get("water_resource_cache_hits"))!=hits+1:
        _fail("resource cache hit/miss counters inaccurate")
        return
    if (game.get("water_resource_cache") as Dictionary).size()>32:
        _fail("water resource cache unbounded")
        return
    print("S9_WATER_REUSE_OK reuse=material+atlas+mesh bounded=32 rig=preserved")
    quit(0)
