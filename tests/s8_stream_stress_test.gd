extends SceneTree
## Headless deterministic route through baked + generated + revisited chunks.
## Do NOT treat CPU timing from Linux runner as measured Android FPS.
func _initialize() -> void:
    call_deferred("_run")

func _fail(message: String) -> void:
    push_error("S8_STREAM_FAIL "+message)
    quit(2)

func _run() -> void:
    var game: Node3D=(load("res://scenes/main.tscn") as PackedScene).instantiate() as Node3D
    root.add_child(game)
    game.set_process(false)
    game.set_physics_process(false)
    var player: CharacterBody3D=game.get_node("MousePlayer") as CharacterBody3D
    var waypoints: Array[Vector2]=[
        Vector2(20.0,16.0),
        Vector2(20.0,136.0),
        Vector2(20.0,-104.0),
        Vector2(20.0,16.0)
    ]
    var loaded_count: int=0
    var peak_active: int=0
    var saved_count: int=0
    var started_usec: int=Time.get_ticks_usec()
    for point in waypoints:
        player.global_position=Vector3(point.x,float(game.call("_height",point.x,point.y))+3.5,point.y)
        game.call("_queue_chunks")
        var local_q: Array=game.get("queue") as Array
        var guard: int=0
        while not local_q.is_empty():
            guard+=1
            if guard>65:
                _fail("unbounded streaming queue")
                return
            var co: Vector2i=local_q.pop_front()
            var chunk_dict: Dictionary=game.get("chunks") as Dictionary
            if not chunk_dict.has(co) and bool(game.call("_near",co)):
                game.call("_add_chunk",co)
                loaded_count+=1
        game.call("_update_chunk_lod")
        game.call("_save_one_cache_chunk")
        saved_count=int(game.get("cache_saves"))
        var active: int=(game.get("chunks") as Dictionary).size()
        peak_active=maxi(active,peak_active)
        if active>25 or active<9:
            _fail("invalid resident chunk count "+str(active))
            return
        await process_frame
        if (game.get("chunks") as Dictionary).size()>25:
            _fail("queued node cleanup retained too many chunks")
            return
    var elapsed_ms: float=float(Time.get_ticks_usec()-started_usec)*0.001
    if int(game.get("chunk_cache_hit_count"))<9:
        _fail("prebaked spawn chunks not read")
        return
    if int(game.get("chunk_cache_miss_count"))<1:
        _fail("stream never generated uncached chunk")
        return
    if saved_count<1:
        _fail("user:// streaming cache never persisted")
        return
    var max_ms: float=float(game.get("max_chunk_load_ms"))
    if max_ms<=0.0 or elapsed_ms<=0.0:
        _fail("chunk timing instrumentation missing")
        return
    print("S8_STREAM_OK waypoints=",waypoints.size()," loaded=",loaded_count," resident_max=",peak_active,
        " hits=",game.get("chunk_cache_hit_count")," generated=",game.get("chunk_cache_miss_count"),
        " saved=",saved_count," duration_linux_ms=",snappedf(elapsed_ms,0.1),
        " max_chunk_linux_ms=",snappedf(max_ms,0.1),
        " NOT_ANDROID_FPS")
    quit(0)
