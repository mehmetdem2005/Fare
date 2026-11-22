class_name S8PerformanceProbe
extends CanvasLayer
## Lightweight opt-in mobile diagnostics. Does not claim GPU timer accuracy.
## FPS and p95/p99 are measured _process frame delta, not hardware GPU times.
const BUFFER: int = 1800
var game: Node3D
var frame_ms: PackedFloat32Array = PackedFloat32Array()
var cursor: int = 0
var samples: int = 0
# These session-wide counters preserve rare stalls beyond the rolling sample ring.
var longest_frame_ms: float = 0.0
var frame_over_50ms_total: int = 0
var long_frame_500ms_total: int = 0
var refresh: float = 0.0
var panel: PanelContainer
var toggle: Button
var label: Label
var quality_selector: OptionButton
var snapshot: Dictionary = {}
var last_save_path: String = ""
var session_start_ms: int = 0

func _ready() -> void:
    name="S8PerformanceProbe"
    layer=15
    session_start_ms=Time.get_ticks_msec()
    frame_ms.resize(BUFFER)
    toggle=Button.new()
    toggle.name="PerfToggle"
    toggle.text="FPS"
    toggle.set_anchors_preset(Control.PRESET_TOP_RIGHT)
    toggle.offset_left=-76.0
    toggle.offset_right=-12.0
    toggle.offset_top=8.0
    toggle.offset_bottom=48.0
    toggle.pressed.connect(_toggle)
    add_child(toggle)
    panel=PanelContainer.new()
    panel.name="PerfPanel"
    panel.set_anchors_preset(Control.PRESET_TOP_RIGHT)
    panel.offset_left=-316.0
    panel.offset_right=-8.0
    panel.offset_top=50.0
    panel.offset_bottom=390.0
    panel.visible=false
    add_child(panel)
    var v: VBoxContainer=VBoxContainer.new()
    panel.add_child(v)
    label=Label.new()
    label.name="PerfText"
    label.add_theme_font_size_override("font_size",13)
    label.autowrap_mode=TextServer.AUTOWRAP_WORD_SMART
    v.add_child(label)
    quality_selector=OptionButton.new()
    quality_selector.name="QualitySelector"
    quality_selector.add_item("AKICI (GPU tasarrufu)",0)
    quality_selector.add_item("DENGELI",1)
    quality_selector.add_item("TAM GORUNTU",2)
    quality_selector.select(int(game.get("mobile_quality_level")))
    quality_selector.item_selected.connect(_change_quality)
    v.add_child(quality_selector)
    var buttons: HBoxContainer=HBoxContainer.new()
    v.add_child(buttons)
    var copy: Button=Button.new()
    copy.text="KOPYALA"
    copy.pressed.connect(_copy_report)
    buttons.add_child(copy)
    var save: Button=Button.new()
    save.text="JSON KAYDET"
    save.pressed.connect(_save_report)
    buttons.add_child(save)
    set_process(true)

func _change_quality(level: int) -> void:
    if game!=null:
        game.call("set_mobile_quality",level)
        _refresh_snapshot()

func _toggle() -> void:
    panel.visible=not panel.visible
    toggle.text="KAPAT" if panel.visible else "FPS"
    if panel.visible:
        _refresh_snapshot()

func _process(delta: float) -> void:
    if game==null or delta<=0.00001:
        return
    # Do not silently discard 500ms+ hitches. App resume can also cause
    # large deltas; the counters show what happened, not which thread caused it.
    var observed_ms: float=delta*1000.0
    longest_frame_ms=maxf(longest_frame_ms,observed_ms)
    if observed_ms>50.0:
        frame_over_50ms_total+=1
    if observed_ms>=500.0:
        long_frame_500ms_total+=1
    frame_ms[cursor]=observed_ms
    cursor=(cursor+1)%BUFFER
    samples=mini(samples+1,BUFFER)
    refresh+=delta
    if refresh>0.85:
        refresh=0.0
        if panel.visible:
            _refresh_snapshot()

func _percentile(sorted_values: Array[float], ratio: float) -> float:
    if sorted_values.is_empty():
        return 0.0
    return sorted_values[clampi(ceili(float(sorted_values.size()-1)*ratio),0,sorted_values.size()-1)]

func _refresh_snapshot() -> void:
    var ordered: Array[float]=[]
    var total: float=0.0
    for i in range(samples):
        var v: float=frame_ms[i]
        ordered.append(v)
        total+=v
    ordered.sort()
    var mean: float=total/maxf(1.0,float(samples))
    var fps: float=1000.0/maxf(0.001,mean)
    var chunks: Dictionary=game.get("chunks")
    var cache: ChunkBakeCache=game.get("chunk_cache") as ChunkBakeCache
    var actor: CharacterBody3D=game.get("player") as CharacterBody3D
    var draw_calls: float=Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME)
    var video_mem_mb: float=Performance.get_monitor(Performance.RENDER_VIDEO_MEM_USED)/1048576.0
    var static_mb: float=Performance.get_monitor(Performance.MEMORY_STATIC)/1048576.0
    snapshot={
        "format":"fare-s8-device-metrics-v1",
        "engine":str(Engine.get_version_info().get("string","unknown")),
        "platform":OS.get_name(),
        "renderer":str(ProjectSettings.get_setting("rendering/renderer/rendering_method","unknown")),
        "uptime_seconds":float(Time.get_ticks_msec()-session_start_ms)*0.001,
        "sample_count":samples,
        "fps_estimated":snappedf(fps,0.1),
        "frame_mean_ms":snappedf(mean,0.01),
        "frame_p95_ms":snappedf(_percentile(ordered,0.95),0.01),
        "frame_p99_ms":snappedf(_percentile(ordered,0.99),0.01),
        "longest_frame_ms":snappedf(longest_frame_ms,0.01),
        "frame_over_50ms_total":frame_over_50ms_total,
        "long_frame_500ms_total":long_frame_500ms_total,
        "draw_calls_reported":int(draw_calls),
        "render_memory_reported_mb":snappedf(video_mem_mb,0.1),
        "static_memory_reported_mb":snappedf(static_mb,0.1),
        "quality_level":int(game.get("mobile_quality_level")),
        "render_scale_3d":snappedf(get_viewport().scaling_3d_scale,0.01),
        "script_process_work_ms_last":snappedf(float(game.get("last_process_work_ms")),0.01),
        "script_process_work_ms_peak":snappedf(float(game.get("max_process_work_ms")),0.01),
        "script_physics_work_ms_peak":snappedf(float(game.get("max_physics_work_ms")),0.01),
        "chunk_stage_peak_ms":(game.get("chunk_stage_peak_ms") as Dictionary).duplicate(),
        "active_chunks":chunks.size(),
        "cache_pack_or_user_hits":int(game.get("chunk_cache_hit_count")),
        "cache_generated_misses":int(game.get("chunk_cache_miss_count")),
        "cache_internal_hits":cache.hits if cache!=null else 0,
        "max_chunk_load_ms":snappedf(float(game.get("max_chunk_load_ms")),0.01),
        "max_cache_save_ms":snappedf(float(game.get("max_cache_save_ms")),0.01),
        "cache_saves":int(game.get("cache_saves")),
        "position_x":snappedf(actor.global_position.x,0.1) if actor!=null else 0.0,
        "position_z":snappedf(actor.global_position.z,0.1) if actor!=null else 0.0
    }
    var text_value: String="GODOT 4.7.2 • S8 / TELEFON\n"
    text_value+="FPS ~ %.1f  Ortalama %.2f ms\n" % [fps,mean]
    text_value+="p95 %.2f ms  p99 %.2f ms\n" % [float(snapshot["frame_p95_ms"]),float(snapshot["frame_p99_ms"])]
    text_value+="Max %.0f ms  >50ms %d  >=500ms %d\n" % [longest_frame_ms,frame_over_50ms_total,long_frame_500ms_total]
    text_value+="Draw %d  GPU bellek* %.1f MB\n" % [int(draw_calls),video_mem_mb]
    text_value+="RAM* %.1f MB  Chunk %d\n" % [static_mb,chunks.size()]
    text_value+="Hazir %d  Uretilen %d\n" % [int(snapshot["cache_pack_or_user_hits"]),int(snapshot["cache_generated_misses"])]
    text_value+="Chunk max %.1f ms  Disk max %.1f ms\n" % [float(snapshot["max_chunk_load_ms"]),float(snapshot["max_cache_save_ms"])]
    text_value+="Q%d  3D %.2f  Script max %.0fms\n" % [int(snapshot["quality_level"]),float(snapshot["render_scale_3d"]),float(snapshot["script_process_work_ms_peak"])]
    text_value+="Chunk stages ms: "+str(snapshot["chunk_stage_peak_ms"])+"\n"
    text_value+="* Godot'un raporladigi; GPU zamani degil\n"
    if not last_save_path.is_empty():
        text_value+="Kayit: "+last_save_path.get_file()
    label.text=text_value

func _copy_report() -> void:
    _refresh_snapshot()
    DisplayServer.clipboard_set(JSON.stringify(snapshot,"\t"))

func _save_report() -> void:
    _refresh_snapshot()
    var target: String="user://perf_reports"
    var err: Error=DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(target))
    if err!=OK:
        push_warning("S8 perf report directory creation failed: "+str(err))
        return
    var timestamp: String=Time.get_datetime_string_from_system().replace(":","-")
    var path: String=target+"/fare-s8-"+timestamp+".json"
    var file: FileAccess=FileAccess.open(path,FileAccess.WRITE)
    if file==null:
        push_warning("S8 perf report write failed: "+str(FileAccess.get_open_error()))
        return
    file.store_string(JSON.stringify(snapshot,"\t"))
    file.close()
    last_save_path=path
    label.text+="\n"+path.get_file()

func get_report() -> Dictionary:
    _refresh_snapshot()
    return snapshot.duplicate(true)
