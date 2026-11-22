extends SceneTree
## S8-A: actual saved .res chunk resources + near/far Mobile water.
func _initialize() -> void:
    call_deferred("_run")
func _fail(reason: String) -> void:
    push_error("CACHE_S8A_FAIL "+reason)
    quit(2)
func _run() -> void:
    var cache: ChunkBakeCache = ChunkBakeCache.new()
    var count: int = 0
    for x in range(-2,3):
        for z in range(-2,3):
            var co: Vector2i = Vector2i(x,z)
            var item: Dictionary = cache.load_chunk(co)
            if item.get("source","") != "pack":
                _fail("not prebaked "+str(co))
                return
            var terrain: ArrayMesh = item["terrain"] as ArrayMesh
            if terrain.get_surface_count() != 1 or not item.has("collision"):
                _fail("broken mesh or collider "+str(co))
                return
            if x==0 or x==-1:
                if not item.has("water") or not item.has("flow"):
                    _fail("missing prebaked water "+str(co))
                    return
                var flow: Image = item["flow"] as Image
                if flow.get_width()!=32 or flow.get_height()!=32:
                    _fail("flow atlas wrong resolution")
                    return
            count+=1
    var scene: PackedScene = load("res://scenes/main.tscn") as PackedScene
    var game: Node3D = scene.instantiate() as Node3D
    root.add_child(game)
    await physics_frame
    if int(game.get("chunk_cache_hit_count")) < 9:
        _fail("initial chunks still rebuilt on startup")
        return
    var chunk: Node3D = game.get_node_or_null("Chunk_0_0") as Node3D
    if chunk==null:
        _fail("missing starting terrain")
        return
    var origin_mesh: MeshInstance3D = chunk.get_node("Terrain") as MeshInstance3D
    var packed: Dictionary = cache.load_chunk(Vector2i(0,0))
    if (origin_mesh.mesh as ArrayMesh).surface_get_arrays(0)[Mesh.ARRAY_VERTEX].size() != (packed["terrain"] as ArrayMesh).surface_get_arrays(0)[Mesh.ARRAY_VERTEX].size():
        _fail("runtime loaded mesh vertex count differs from pack")
        return
    var near: MeshInstance3D = chunk.get_node_or_null("FlowingWater") as MeshInstance3D
    if near==null:
        _fail("missing near water")
        return
    if not (near.material_override as ShaderMaterial).shader.code.contains("uniform sampler2D opaque_depth"):
        _fail("near water lost real S4 refraction")
        return
    game.call("_add_chunk",Vector2i(0,2))
    game.call("_update_chunk_lod")
    var remote: Node3D = game.get_node_or_null("Chunk_0_2") as Node3D
    var far: MeshInstance3D = remote.get_node_or_null("FlowingWater") as MeshInstance3D
    if far==null or (far.material_override as ShaderMaterial).shader.code.contains("uniform sampler2D opaque_screen"):
        _fail("far water still uses expensive screen copies")
        return
    var actor: CharacterBody3D = game.get_node("MousePlayer") as CharacterBody3D
    actor.global_position=Vector3(20.0,5.0,96.0)
    game.call("_update_chunk_lod")
    if not (far.material_override as ShaderMaterial).shader.code.contains("uniform sampler2D opaque_depth"):
        _fail("near water detail not restored after approach")
        return
    actor.global_position=Vector3(20.0,5.0,16.0)
    game.call("_update_chunk_lod")
    game.call("_queue_chunks")
    if (game.get("chunks") as Dictionary).size()>25:
        _fail("RAM chunk window larger than 25")
        return
    # A newly explored chunk can be saved to phone storage and loaded again.
    var explore: Vector2i = Vector2i(4,4)
    game.call("_add_chunk",explore)
    var fresh: Node3D = game.get_node_or_null("Chunk_4_4") as Node3D
    if fresh==null or not cache.save_chunk(explore,fresh,false):
        _fail("runtime-generated chunk cannot persist to user://")
        return
    var loaded: Dictionary = cache.load_chunk(explore)
    if loaded.get("source","") != "user":
        _fail("user:// revisit does not load persisted chunk")
        return
    print("CACHE_S8A_OK precompiled=",count," startup_hits=",game.get("chunk_cache_hit_count")," distant=no_screen_reads near=S4 restoration=ok user_persist=ok window=25")
    quit(0)
