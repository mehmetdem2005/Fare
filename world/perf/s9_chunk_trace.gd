class_name S9ChunkTrace
extends RefCounted
## Low-frequency 256-job CPU trace. GPU queue/upload latency is NOT captured.
const MAX_JOBS: int = 256
const STAGE_NAMES: Array[String] = [
    "cache_read","terrain_mesh","collider","vegetation","river_fx","publish",
    "water_mesh","flow_atlas_fetch","water_texture_submit","water_materials",
    "water_scene_attach","river_rocks","major_rocks","river_mist"
]
var jobs: Array[Dictionary] = []
var total_jobs: int = 0

func record_chunk(co: Vector2i, source: String, queue_wait_ms: float,
        total_ms: float, stage_ms: Dictionary, quality: int, actor_pos: Vector3) -> void:
    total_jobs+=1
    var stages: Dictionary={}
    for stage in STAGE_NAMES:
        stages[stage]=snappedf(float(stage_ms.get(stage,0.0)),0.01)
    var event: Dictionary={
        "task_id":total_jobs,
        "chunk":[co.x,co.y],
        "source":source,
        "queue_wait_ms":snappedf(maxf(0.0,queue_wait_ms),0.01),
        "total_cpu_ms":snappedf(total_ms,0.01),
        "stage_ms":stages,
        "quality":quality,
        "frame_seq":Engine.get_process_frames(),
        "player_x":snappedf(actor_pos.x,0.1),
        "player_z":snappedf(actor_pos.z,0.1)
    }
    jobs.append(event)
    if jobs.size()>MAX_JOBS:
        jobs.pop_front()

func _percentile(ordered: Array[float], ratio: float) -> float:
    if ordered.is_empty():
        return 0.0
    var index: int=clampi(ceili(float(ordered.size()-1)*ratio),0,ordered.size()-1)
    return ordered[index]

func get_report() -> Dictionary:
    var distributions: Dictionary={}
    for stage in STAGE_NAMES:
        var values: Array[float]=[]
        for event in jobs:
            values.append(float((event["stage_ms"] as Dictionary).get(stage,0.0)))
        values.sort()
        distributions[stage]={
            "count":values.size(),
            "p50_ms":snappedf(_percentile(values,0.50),0.01),
            "p95_ms":snappedf(_percentile(values,0.95),0.01),
            "p99_ms":snappedf(_percentile(values,0.99),0.01),
            "max_ms":values[values.size()-1] if not values.is_empty() else 0.0
        }
    var sources: Dictionary={"pack":0,"user":0,"generated":0}
    for event in jobs:
        var src: String=str(event["source"])
        sources[src]=int(sources.get(src,0))+1
    var sorted: Array[Dictionary]=jobs.duplicate()
    sorted.sort_custom(func(a: Dictionary,b: Dictionary) -> bool:
        return float(a["total_cpu_ms"])>float(b["total_cpu_ms"]))
    var worst: Array[Dictionary]=[]
    for i in range(mini(5,sorted.size())):
        worst.append(sorted[i].duplicate(true))
    return {
        "jobs_total":total_jobs,
        "jobs_in_window":jobs.size(),
        "queue_wait_latest_ms":float(jobs.back()["queue_wait_ms"]) if not jobs.is_empty() else 0.0,
        "stage_distributions_ms":distributions,
        "cache_sources":sources,
        "worst_events":worst
    }
