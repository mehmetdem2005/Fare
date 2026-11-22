extends SceneTree
## S9 trace must show CPU stages without changing 49-bone gameplay.
func _initialize() -> void:
    call_deferred("_run")
func _fail(reason: String) -> void:
    push_error("S9_BASELINE_FAIL "+reason)
    quit(2)
func _run() -> void:
    if S9BuildIdentity.BUILD_SHA.is_empty() or S9BuildIdentity.BUILD_TAG.is_empty():
        _fail("build identity missing")
        return
    var collector: S9ChunkTrace=S9ChunkTrace.new()
    for i in range(300):
        collector.record_chunk(Vector2i(i,0),"pack" if i%2==0 else "generated",
            float(i)*0.1,float(i),{"cache_read":float(i),"collider":float(i)*0.2},
            0,Vector3.ZERO)
    var trace: Dictionary=collector.get_report()
    var stats: Dictionary=trace["stage_distributions_ms"]
    if int(trace["jobs_total"])!=300 or int(trace["jobs_in_window"])!=256:
        _fail("bounded 256 job trace failed")
        return
    if float(stats["cache_read"]["max_ms"])<299.0 or (trace["worst_events"] as Array).size()!=5:
        _fail("stage distribution or worst events wrong")
        return
    var game: Node3D=(load("res://scenes/main.tscn") as PackedScene).instantiate() as Node3D
    root.add_child(game)
    var rig: Skeleton3D=game.get("rig") as Skeleton3D
    if rig==null or rig.get_bone_count()!=49:
        _fail("mouse rig changed")
        return
    if bool(game.call("set_s9_fixed_scene",true)):
        _fail("fixed scene cannot activate before all 25 chunks loaded")
        return
    var probe: S8PerformanceProbe=S8PerformanceProbe.new()
    probe.game=game
    root.add_child(probe)
    probe._process(0.042)
    var report: Dictionary=probe.get_report()
    if str(report["format"])!="fare-s9-device-metrics-v1":
        _fail("S9 JSON version lost")
        return
    if str(report["game_build_sha"])!=S9BuildIdentity.BUILD_SHA or not report.has("chunk_trace"):
        _fail("source fingerprint or chunk trace absent")
        return
    if not report.has("quality_level") or not report.has("frame_p99_ms"):
        _fail("S8 backwards-compatible metrics absent")
        return
    print("S9_BASELINE_OK build=",S9BuildIdentity.BUILD_TAG,
        " trace_window=",trace["jobs_in_window"]," rig=49 metrics=s9")
    quit(0)
