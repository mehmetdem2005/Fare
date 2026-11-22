extends SceneTree
## S8-D quality switching must restore the original 49-bone game, water and PBR.
func _initialize() -> void:
    call_deferred("_run")
func _fail(reason: String) -> void:
    push_error("S8_MOBILE_RESCUE_FAIL "+reason)
    quit(2)
func _run() -> void:
    var game: Node3D=(load("res://scenes/main.tscn") as PackedScene).instantiate() as Node3D
    root.add_child(game)
    var start: Node3D=game.get_node("Chunk_0_0")
    var water: MeshInstance3D=start.get_node("FlowingWater") as MeshInstance3D
    var terrain: MeshInstance3D=start.get_node("Terrain") as MeshInstance3D
    var rig: Skeleton3D=game.get("rig") as Skeleton3D
    if rig==null or rig.get_bone_count()!=49:
        _fail("original 49-bone mouse lost")
        return
    if terrain==null or water==null:
        _fail("original terrain or water missing")
        return
    game.call("set_mobile_quality",0)
    if absf(get_root().scaling_3d_scale-0.60)>0.01 or get_root().msaa_3d!=Viewport.MSAA_DISABLED:
        _fail("fast render buffer / antialiasing not configured")
        return
    if terrain.material_override!=game.get("terrain_lite_mat") or not bool(water.get_meta("water_lite",false)):
        _fail("fast terrain and water not enabled")
        return
    if (game.get("atmosphere") as ForestAtmosphere).sun.shadow_enabled:
        _fail("fast mode still renders costly sun shadows")
        return
    game.call("set_mobile_quality",1)
    if absf(get_root().scaling_3d_scale-0.75)>0.01 or terrain.material_override!=game.get("terrain_mat"):
        _fail("balanced terrain restoration failed")
        return
    if bool(water.get_meta("water_lite",false)):
        _fail("balanced near water did not restore full optical shader")
        return
    game.call("set_mobile_quality",2)
    if absf(get_root().scaling_3d_scale-1.0)>0.01 or get_root().msaa_3d!=Viewport.MSAA_4X:
        _fail("full resolution / antialiasing not restored")
        return
    if not (game.get("atmosphere") as ForestAtmosphere).sun.shadow_enabled:
        _fail("full mode shadows not restored")
        return
    var stages: Dictionary=game.get("chunk_stage_peak_ms") as Dictionary
    for stage in ["cache_read","terrain_mesh","collider","vegetation","river_fx"]:
        if not stages.has(stage):
            _fail("missing instrumented chunk stage: "+stage)
            return
    if int(game.get("chunk_cache_hit_count"))<9:
        _fail("prebaked 3x3 startup lost")
        return
    print("S8_MOBILE_RESCUE_OK quality=fast/balanced/full rig=49 chunk_stages=5 cache=retained")
    quit(0)
