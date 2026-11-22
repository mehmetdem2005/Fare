extends SceneTree
## The same deterministic terrain and ornaments as the original synchronous
## generator, but on Android the visual-only placement is batched across frames.
func _initialize() -> void:
    call_deferred("_run")
func _fail(t: String) -> void:
    push_error("S9_PROGRESSIVE_CHUNKS_FAIL "+t)
    quit(2)
func _compare_multimesh(expected_root: Node3D, staged_root: Node3D, label: String) -> bool:
    var a: MultiMeshInstance3D=expected_root.get_node_or_null(label) as MultiMeshInstance3D
    var b: MultiMeshInstance3D=staged_root.get_node_or_null(label) as MultiMeshInstance3D
    if (a==null)!=(b==null):
        return false
    if a==null:
        return true
    if a.multimesh.instance_count!=b.multimesh.instance_count:
        return false
    for i in range(a.multimesh.instance_count):
        var left: Transform3D=a.multimesh.get_instance_transform(i)
        var right: Transform3D=b.multimesh.get_instance_transform(i)
        if left.origin.distance_to(right.origin)>0.00001:
            return false
        if left.basis.x.distance_to(right.basis.x)>0.00001:
            return false
    return true
func _run() -> void:
    var game: Node3D=(load("res://scenes/main.tscn") as PackedScene).instantiate() as Node3D
    root.add_child(game)
    game.set_process(false)
    game.call("set_mobile_quality",0)
    if (game.get("rig") as Skeleton3D).get_bone_count()!=49:
        _fail("49-bone mouse rig lost")
        return
    var co: Vector2i=Vector2i(0,4)
    var baseline: Node3D=Node3D.new()
    baseline.name="ExpectedDetails"
    baseline.position=Vector3(0.0,0.0,160.0)
    game.add_child(baseline)
    game.call("_trees",baseline,co)
    game.call("_grass",baseline,co)
    game.call("_rocks",baseline,co)
    game.call("_river_mist",baseline,co)
    game.call("_add_chunk",co,true)
    var staged: Node3D=game.get_node_or_null("Chunk_0_4") as Node3D
    if staged==null or staged.get_node_or_null("TerrainCollider/TerrainCollisionShape")==null:
        _fail("collision not ready before visuals")
        return
    if staged.get_node_or_null("FlowingWater")==null:
        _fail("water still not ready on first frame")
        return
    if staged.has_node("Pines") or staged.has_node("Grass"):
        _fail("cosmetic details were not deferred")
        return
    var loops: int=0
    while not (game.get("cosmetic_jobs") as Array).is_empty():
        game.call("_advance_cosmetic_jobs")
        loops+=1
        if loops>240:
            _fail("progressive queue never drained")
            return
    for label in ["Pines","Grass","FinePebbles","Cobbles"]:
        if not _compare_multimesh(baseline,staged,label):
            _fail("deterministic transform mismatch at "+label)
            return
    if staged.has_node("NearRiverMist"):
        _fail("fast quality created invisible mist")
        return
    game.call("set_mobile_quality",1)
    if (game.get("cosmetic_jobs") as Array).is_empty():
        _fail("balanced quality did not schedule deferred mist")
        return
    loops=0
    while not (game.get("cosmetic_jobs") as Array).is_empty():
        game.call("_advance_cosmetic_jobs")
        loops+=1
        if loops>130:
            _fail("deferred mist not completed")
            return
    if not _compare_multimesh(baseline,staged,"NearRiverMist"):
        _fail("deferred mist not deterministic")
        return
    var co2: Vector2i=Vector2i(0,5)
    game.call("_add_chunk",co2,true)
    var stale: Node3D=game.get_node_or_null("Chunk_0_5") as Node3D
    (game.get("chunks") as Dictionary).erase(co2)
    stale.queue_free()
    for n in range(4):
        game.call("_advance_cosmetic_jobs")
    if int(game.get("cosmetic_completed_chunks"))<1:
        _fail("completed visual job telemetry missing")
        return
    print("S9_PROGRESSIVE_CHUNKS_OK collision=immediate river=immediate foliage=deterministic stones=deterministic mist=restored rig=49 stale=discarded")
    quit(0)
