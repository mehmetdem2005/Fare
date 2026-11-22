extends SceneTree
## Build-time only, not executed on player devices.
const RANGE_MIN: int = -3
const RANGE_MAX: int = 3
const PACK_COUNT: int = 49
func _initialize() -> void:
    call_deferred("_bake")
func _bake() -> void:
    var cache: ChunkBakeCache = ChunkBakeCache.new()
    var ready: int = 0
    for z in range(RANGE_MIN,RANGE_MAX+1):
        for x in range(RANGE_MIN,RANGE_MAX+1):
            if cache.has_pack(Vector2i(x,z)):
                ready+=1
    if ready==PACK_COUNT:
        print("CHUNK_PACK_READY precompiled=49 source=existing_v3")
        quit(0)
        return
    # Existing 25 precompiled resources must stay byte-identical. Generate
    # ONLY the missing outer 24 so GitHub export does not rebake geometry.
    ChunkBakeCache.bypass_disk=false
    var scene: PackedScene = load("res://scenes/main.tscn") as PackedScene
    var game: Node3D = scene.instantiate() as Node3D
    root.add_child(game)
    var made: int = 0
    for z in range(RANGE_MIN,RANGE_MAX+1):
        for x in range(RANGE_MIN,RANGE_MAX+1):
            var co: Vector2i = Vector2i(x,z)
            if cache.has_pack(co):
                continue
            var name: String = "Chunk_%d_%d" % [x,z]
            var chunk: Node3D = game.get_node_or_null(name) as Node3D
            if chunk == null:
                # Never accidentally bake a developer's user:// chunk cache.
                ChunkBakeCache.bypass_disk=true
                game.call("_add_chunk",co)
                ChunkBakeCache.bypass_disk=false
                chunk=game.get_node_or_null(name) as Node3D
            if chunk==null or not cache.save_chunk(co,chunk,true):
                push_error("CHUNK_BAKE_FAIL "+str(co))
                quit(2)
                return
            made+=1
    ChunkBakeCache.bypass_disk=false
    print("CHUNK_PACK_READY precompiled=",ready+made," added=",made," deterministic_version=v3")
    quit(0)
