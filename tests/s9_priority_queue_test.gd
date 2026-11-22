extends SceneTree
## Moving or teleporting must not prioritize outer decorative tiles ahead of
## the player collision safety ring.
func _initialize() -> void:
    call_deferred("_run")
func _fail(t: String) -> void:
    push_error("S9_PRIORITY_QUEUE_FAIL "+t)
    quit(2)
func _assert_sorted(queue: Array,center: Vector2i) -> bool:
    var last_dist: int=-1
    for co_variant in queue:
        var co: Vector2i=co_variant
        var d: int=maxi(absi(co.x-center.x),absi(co.y-center.y))
        if d<last_dist or d>2:
            return false
        last_dist=d
    return true
func _run() -> void:
    var game: Node3D=(load("res://scenes/main.tscn") as PackedScene).instantiate() as Node3D
    root.add_child(game)
    game.set_process(false)
    game.set_physics_process(false)
    if (game.get("rig") as Skeleton3D).get_bone_count()!=49:
        _fail("mouse rig")
        return
    var player: CharacterBody3D=game.get("player") as CharacterBody3D
    player.global_position=Vector3(20.0,4.0,820.0)
    game.call("_queue_chunks")
    var queue: Array=game.get("queue") as Array
    var center: Vector2i=game.call("_current_chunk")
    if queue.size()!=25 or queue[0]!=center or not _assert_sorted(queue,center):
        _fail("teleport center and inner collision tiles not first")
        return
    for co_variant in queue:
        var co: Vector2i=co_variant
        if co.y<18 or co.y>22:
            _fail("stale old spawn request survived teleport")
            return
    player.global_position=Vector3(20.0,4.0,-820.0)
    game.call("_queue_chunks")
    var next: Array=game.get("queue") as Array
    center=game.call("_current_chunk")
    if next.size()!=25 or next[0]!=center or not _assert_sorted(next,center):
        _fail("reverse teleport queued old distant work")
        return
    print("S9_PRIORITY_QUEUE_OK inner_collision_first=true teleport_stale_dropped=true 25_requests=true rig=49")
    quit(0)
