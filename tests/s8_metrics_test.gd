extends SceneTree
## Actual Godot snapshot/test of diagnostics without Android rendering.
func _initialize() -> void:
    call_deferred("_run")
func _fail(text_value: String) -> void:
    push_error("S8_METRICS_FAIL "+text_value)
    quit(2)
func _run() -> void:
    var game: Node3D=(load("res://scenes/main.tscn") as PackedScene).instantiate() as Node3D
    root.add_child(game)
    var probe: S8PerformanceProbe=S8PerformanceProbe.new()
    probe.game=game
    root.add_child(probe)
    for frame in range(100):
        probe._process(0.033 if frame!=72 else 0.12)
    var report: Dictionary=probe.get_report()
    if int(report["sample_count"])!=100:
        _fail("sample count unexpected")
        return
    if float(report["frame_p99_ms"])<40.0 or float(report["frame_p95_ms"])>40.0:
        _fail("percentile computation unexpected")
        return
    if int(report["active_chunks"])<9 or int(report["cache_pack_or_user_hits"])<9:
        _fail("real game chunk data absent")
        return
    if float(report["max_chunk_load_ms"])<=0.0:
        _fail("chunk CPU timing not connected")
        return
    # A 750ms hitch must not disappear; a 65ms frame must be counted too.
    probe._process(0.75)
    probe._process(0.065)
    var after_hitch: Dictionary=probe.get_report()
    if int(after_hitch["sample_count"])!=102 or float(after_hitch["longest_frame_ms"])<749.9:
        _fail("long stall omitted from frame samples or max")
        return
    if int(after_hitch["long_frame_500ms_total"])!=1 or int(after_hitch["frame_over_50ms_total"])!=3:
        _fail("slow-frame and long-frame event counters wrong")
        return
    probe._save_report()
    var path: String=probe.last_save_path
    if path.is_empty() or not FileAccess.file_exists(path):
        _fail("JSON file save inaccessible")
        return
    var parsed: Variant=JSON.parse_string(FileAccess.get_file_as_string(path))
    if typeof(parsed)!=TYPE_DICTIONARY or parsed.get("format","")!="fare-s8-device-metrics-v1":
        _fail("telemetry not valid JSON")
        return
    if int(parsed.get("long_frame_500ms_total",-1))!=1 or float(parsed.get("longest_frame_ms",0.0))<749.9:
        _fail("saved JSON lost long-stall information")
        return
    print("S8_METRICS_OK longest_frame_ms=",after_hitch["longest_frame_ms"]," long_stalls=",after_hitch["long_frame_500ms_total"]," frame_p95=",report["frame_p95_ms"]," frame_p99=",report["frame_p99_ms"],
       " chunk_hits=",report["cache_pack_or_user_hits"]," JSON=ok")
    quit(0)
