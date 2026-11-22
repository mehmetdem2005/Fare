extends SceneTree
## Stress cancellation and bounded pure-data WorkerThreadPool without creating
## SceneTree or GPU resources from worker threads.
func _initialize() -> void:
    call_deferred("_run")
func _fail(text_value: String) -> void:
    push_error("S9_CPU_PREFETCH_FAIL "+text_value)
    quit(2)
func _run() -> void:
    var game: Node3D=(load("res://scenes/main.tscn") as PackedScene).instantiate() as Node3D
    root.add_child(game)
    game.set_process(false)
    game.set_physics_process(false)
    var rig: Skeleton3D=game.get("rig") as Skeleton3D
    if rig==null or rig.get_bone_count()!=49:
        _fail("rig")
        return
    if not bool(game.call("_s9_start_cpu_task",Vector2i(0,13))):
        _fail("first task not queued")
        return
    if not bool(game.call("_s9_start_cpu_task",Vector2i(-1,13))):
        _fail("second task not queued")
        return
    if bool(game.call("_s9_start_cpu_task",Vector2i(0,14))):
        _fail("unbounded more than two workers")
        return
    var jobs: Dictionary=game.get("s9_worker_tasks") as Dictionary
    if jobs.size()!=2:
        _fail("inflight count")
        return
    var guard: int=0
    while not jobs.is_empty():
        game.call("_s9_poll_cpu_tasks")
        guard+=1
        if guard>600:
            _fail("two workers never finished")
            return
        await process_frame
    if int(game.get("s9_worker_finished"))!=2:
        _fail("not all tasks joined")
        return
    if (game.get("s9_worker_ready") as Dictionary).size()>6:
        _fail("ready memory unbounded")
        return
    if int(game.get("s9_worker_discarded"))!=2:
        _fail("far stale results not discarded")
        return
    # Fully prepared far ring can be published without regenerated geometry.
    var actor: CharacterBody3D=game.get("player") as CharacterBody3D
    actor.global_position=Vector3(20.0,3.0,13.0*40.0)
    game.call("_s9_start_cpu_task",Vector2i(0,14))
    guard=0
    jobs=game.get("s9_worker_tasks") as Dictionary
    while not jobs.is_empty():
        game.call("_s9_poll_cpu_tasks")
        guard+=1
        if guard>600:
            _fail("forward task timeout")
            return
        await process_frame
    var key: Vector2i=Vector2i(0,14)
    if not (game.get("s9_worker_ready") as Dictionary).has(key):
        _fail("forward ready data missing")
        return
    var data: S9PureChunkData=(game.get("s9_worker_ready") as Dictionary)[key] as S9PureChunkData
    var mesh: ArrayMesh=data.create_terrain_mesh()
    if mesh.get_surface_count()!=1:
        _fail("main thread mesh commit failed")
        return
    if not (game.get("s9_worker_ready") as Dictionary).has(key):
        _fail("premature disposal")
        return
    var original_bytes: PackedByteArray=data.flow_rgba8.duplicate()
    game.call("_add_chunk",key,true)
    var node: Node3D=game.get_node_or_null("Chunk_0_14") as Node3D
    if node==null or node.get_node_or_null("TerrainCollider/TerrainCollisionShape")==null:
        _fail("ready worker chunk not published with terrain collision")
        return
    var water: MeshInstance3D=node.get_node_or_null("FlowingWater") as MeshInstance3D
    if water==null or (water.get_meta("flow_image") as Image).get_data()!=original_bytes:
        _fail("ready flow bytes not connected to correct water material")
        return
    if int(game.get("s9_worker_used"))!=1:
        _fail("worker result not used in main-thread publisher")
        return
    if (game.get("s9_worker_ready") as Dictionary).has(key):
        _fail("ready worker data retained after commit")
        return
    print("S9_CPU_PREFETCH_OK task_limit=2 stale_discard=2 ready_bound=6 gpu_resources=main_only published_collision=ready worker_used=1 flow=identical rig=49")
    quit(0)
