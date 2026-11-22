extends SceneTree
## Far-field optimization must be indistinguishable from the old geometry.
func _initialize() -> void:
    call_deferred("_run")
func _fail(message: String) -> void:
    push_error("S8_FAR_TERRAIN_FAIL "+message)
    quit(2)
func _run() -> void:
    var game: Node3D=(load("res://scenes/main.tscn") as PackedScene).instantiate() as Node3D
    root.add_child(game)
    var co: Vector2i=Vector2i(4,2)
    ChunkBakeCache.bypass_disk=true
    game.call("_add_chunk",co)
    ChunkBakeCache.bypass_disk=false
    var chunk: Node3D=game.get_node("Chunk_4_2") as Node3D
    var terrain: MeshInstance3D=chunk.get_node("Terrain") as MeshInstance3D
    var mesh: ArrayMesh=terrain.mesh as ArrayMesh
    var data: Array=mesh.surface_get_arrays(0)
    var vertices: PackedVector3Array=data[Mesh.ARRAY_VERTEX]
    var colors: PackedColorArray=data[Mesh.ARRAY_COLOR]
    var depth: PackedVector2Array=data[Mesh.ARRAY_TEX_UV2]
    var indices: PackedInt32Array=data[Mesh.ARRAY_INDEX]
    var profile: RiverProfile=game.get("river_profile") as RiverProfile
    var substrate: ShoreSubstrate=game.get("shore_substrate") as ShoreSubstrate
    if vertices.size()<1000 or indices.size()%6!=0:
        _fail("far triangle array malformed")
        return
    var compared: int=0
    for i in range(0,vertices.size(),maxi(1,vertices.size()/67)):
        var p: Vector3=vertices[i]+chunk.global_position
        if absf(p.x)<=45.0:
            continue
        var legacy: Dictionary=profile.ground_sample(Vector2(p.x,p.z),float(game.call("_base_height",p.x,p.z)))
        var old_colors: Dictionary=substrate.sample(legacy,Vector2(p.x,p.z))
        var actual: Color=colors[i]
        var expected_y: float=float(legacy["terrain_y"])
        # ArrayMesh vertex positions use single-precision coordinates.
        # At ~200m world X, a few 1e-5 m units of rounding are expected.
        if absf(expected_y-p.y)>0.0005:
            _fail("fast path terrain height diverged at "+str(p)+" expected_y="+str(expected_y)+" delta="+str(p.y-expected_y))
            return
        # ArrayMesh stores COLOR as quantized channel data on the GPU.
        # A ~1/255 difference is not a change to the underlying substrate
        # formula; compare within one channel step instead of float epsilon.
        var cover_expected: float=float(old_colors["forest"])
        if absf(cover_expected-actual.a)>0.005 or absf(actual.r)+absf(actual.g)+absf(actual.b)>0.005:
            _fail("fast path material mismatch at "+str(p)+" expected="+str(cover_expected)+" actual="+str(actual))
            return
        if depth[i].x>0.00001:
            _fail("far world unexpectedly contains river depth")
            return
        compared+=1
    if compared<30:
        _fail("not enough far terrain equivalence samples")
        return
    print("S8_FAR_TERRAIN_OK compared=",compared," mesh_vertices=",vertices.size()," index_allocations=removed")
    quit(0)
