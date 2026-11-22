extends SceneTree
## Compare CPU-only worker buffers with the unmodified original generator.
## The original scene/49-bone rig/physics remains authoritative.
func _initialize() -> void:
    call_deferred("_run")

func _fail(msg: String) -> void:
    push_error("S9_PURE_WORKER_FAIL "+msg)
    quit(2)

func _arrays_match(a: Array,b: Array,kind: String) -> bool:
    for slot in [Mesh.ARRAY_VERTEX,Mesh.ARRAY_NORMAL,Mesh.ARRAY_TEX_UV,Mesh.ARRAY_TEX_UV2,Mesh.ARRAY_COLOR,Mesh.ARRAY_INDEX]:
        if a[slot]==null and b[slot]==null:
            continue
        if a[slot]==null or b[slot]==null:
            return false
        if (a[slot] as Variant).size()!=(b[slot] as Variant).size():
            return false
        for i in range((a[slot] as Variant).size()):
            if a[slot][i] != b[slot][i]:
                return false
    return true

func _run() -> void:
    var game: Node3D=(load("res://scenes/main.tscn") as PackedScene).instantiate() as Node3D
    root.add_child(game)
    game.set_process(false)
    game.set_physics_process(false)
    if (game.get("rig") as Skeleton3D).get_bone_count()!=49:
        _fail("rig changed")
        return
    var checked: int=0
    for co in [Vector2i(-1,13),Vector2i(0,13),Vector2i(1,-4)]:
        var job: S9PureChunkData=S9PureChunkData.new()
        job.co=co
        var task: int=WorkerThreadPool.add_task(Callable(job,"build"),false,"S9 CPU-only terrain test")
        while not WorkerThreadPool.is_task_completed(task):
            await process_frame
        WorkerThreadPool.wait_for_task_completion(task)
        if not job.completed or job.terrain_arrays.is_empty():
            _fail("worker never completed "+str(co))
            return
        var root_node: Node3D=Node3D.new()
        root_node.position=Vector3(float(co.x)*40.0,0.0,float(co.y)*40.0)
        var original: ArrayMesh=game.call("_generate_terrain_mesh",root_node) as ArrayMesh
        var terrain_arrays: Array=original.surface_get_arrays(0)
        if not _arrays_match(terrain_arrays,job.terrain_arrays,"terrain"):
            _fail("terrain arrays differ from baseline "+str(co))
            return
        if co.x==-1 or co.x==0:
            var original_water: ArrayMesh=(game.get("river_surface_builder") as RiverSurfaceBuilder).build_chunk(game.get("river_profile"),co,40.0)
            if not _arrays_match(original_water.surface_get_arrays(0),job.water_arrays,"water"):
                _fail("water geometry changed "+str(co))
                return
            var expected_flow: Image=(game.get("river_flow_field") as RiverFlowField).build_atlas(game.get("river_profile"),Vector2(float(co.x)*40.0,float(co.y)*40.0),40.0,32)
            if expected_flow.get_data()!=job.flow_rgba8:
                _fail("RGBA atlas bytes differ "+str(co))
                return
        checked+=1
    print("S9_PURE_WORKER_OK coords=",checked," terrain=byte_exact water=byte_exact flow=RGBA_exact rig=49")
    quit(0)
