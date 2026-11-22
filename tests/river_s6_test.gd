extends SceneTree
# S6 actual RiverProfile probes, kinematic integration, camera threshold
# hysteresis, pooled ripple and original animation controls.
func _initialize() -> void:
    call_deferred("_run")
func _fail(s: String) -> void:
    push_error("WATER_S6_FAIL "+s)
    quit(2)

func _run() -> void:
    var profile: RiverProfile = RiverProfile.new()
    var flow: RiverFlowField = RiverFlowField.new()
    var water: MouseWaterInteraction = MouseWaterInteraction.new()
    var z_shoal: float = 20.0
    var x_shoal: float = profile.center_x(z_shoal)
    var shoal: Dictionary = profile.sample(Vector2(x_shoal,z_shoal))
    var shoal_pos: Vector3 = Vector3(x_shoal,float(shoal["bed_y"])+0.42,z_shoal)
    water.update(profile,flow,shoal_pos,0.02)
    if water.state != MouseWaterInteraction.SHALLOW or water.wetness<=0.01:
        _fail("shoal must wade with wetness and no swimming")
        return
    var z_pool: float = 100.0
    var x_pool: float = profile.center_x(z_pool)
    var deep: Dictionary = profile.sample(Vector2(x_pool,z_pool))
    var pos: Vector3 = Vector3(x_pool,float(deep["bed_y"])+0.42,z_pool)
    water.update(profile,flow,pos,0.02)
    if water.state != MouseWaterInteraction.SWIMMING:
        _fail("deep water does not enter swimming; depth="+str(deep["depth"])+" chest="+str(water.chest_depth))
        return
    var character: CharacterBody3D = CharacterBody3D.new()
    root.add_child(character)
    character.global_position=pos
    character.velocity=Vector3.ZERO
    for i in range(120):
        water.update(profile,flow,character.global_position,1.0/60.0)
        water.apply_velocity(character,Vector3.ZERO,false,false,1.0/60.0,3.4,5.9,4.8)
        character.global_position+=character.velocity/60.0
    var final_depth: float = float(deep["water_y"])-character.global_position.y
    if water.state != MouseWaterInteraction.SWIMMING or absf(final_depth)>0.24:
        _fail("buoyancy did not stabilize around water surface: "+str(final_depth))
        return
    if Vector2(character.velocity.x,character.velocity.z).length()<0.08:
        _fail("idle swimming does not drift with physical current")
        return
    # Exit is hysteretic: shallow not produced by 1 cm head oscillations.
    var fx: UnderwaterCameraFX = UnderwaterCameraFX.new()
    fx.surface_profile=profile
    root.add_child(fx)
    fx.update_camera(Vector3(x_pool,float(deep["water_y"])-0.2,z_pool),0.2)
    if not fx.submerged or fx.fade<0.01:
        _fail("camera not underwater")
        return
    fx.update_camera(Vector3(x_pool,float(deep["water_y"])+0.025,z_pool),0.2)
    if not fx.submerged:
        _fail("camera hysteresis broken near surface")
        return
    fx.update_camera(Vector3(x_pool,float(deep["water_y"])+0.12,z_pool),0.2)
    if fx.submerged:
        _fail("camera fails to surface")
        return
    var rings: WaterRipplePool = WaterRipplePool.new()
    root.add_child(rings)
    rings.splash(Vector2(x_pool,z_pool),float(deep["water_y"]),0.9)
    if rings.rings.size()!=12 or rings.count_active()!=1:
        _fail("ripple pool capacity/contact failed")
        return
    for i in range(24):
        rings.splash(Vector2(x_pool+float(i)*0.01,z_pool),float(deep["water_y"]),0.5)
    if rings.count_active()>WaterRipplePool.CAPACITY:
        _fail("ripple allocation exceeded pool")
        return
    var game: Node3D = (load("res://scenes/main.tscn") as PackedScene).instantiate()
    root.add_child(game)
    await physics_frame
    var actor: CharacterBody3D = game.get_node("MousePlayer") as CharacterBody3D
    if game.get("camera_water")==null or game.get("ripple_pool")==null:
        _fail("underwater camera and ripples not integrated into game")
        return
    var rig: Skeleton3D = game.get("rig")
    if rig==null or rig.get_bone_count()!=49:
        _fail("original 49-bone mouse changed")
        return
    if water.wetness<0.01:
        _fail("water wetness never updated")
        return
    # S6 true gameplay acceptance: warp the ACTUAL rigged mouse over a deep
    # 3D river region, then let CharacterBody3D move_and_slide and the whole
    # game's _physics_process run. A RefCounted math-only test is insufficient.
    var center_chunk_x: int = floori(x_pool/40.0)
    var center_chunk_z: int = floori(z_pool/40.0)
    for dx in range(-1,2):
        for dz in range(-1,2):
            game.call("_add_chunk",Vector2i(center_chunk_x+dx,center_chunk_z+dz))
    actor.global_position = Vector3(x_pool,float(deep["water_y"])+0.7,z_pool)
    actor.velocity = Vector3.ZERO
    var start_xz: Vector2 = Vector2(actor.global_position.x,actor.global_position.z)
    var ever_swimming: bool = false
    for tick in range(170):
        await physics_frame
        var in_game_water: MouseWaterInteraction = game.get("mouse_water") as MouseWaterInteraction
        if in_game_water.state == MouseWaterInteraction.SWIMMING:
            ever_swimming = true
    var actual_water: MouseWaterInteraction = game.get("mouse_water") as MouseWaterInteraction
    var error_y: float = absf(actor.global_position.y - profile.surface_height(actor.global_position.z))
    var moved_xz: float = start_xz.distance_to(Vector2(actor.global_position.x,actor.global_position.z))
    if not ever_swimming or actual_water.state != MouseWaterInteraction.SWIMMING:
        _fail("live CharacterBody never entered/preserved swimming state")
        return
    if error_y>0.36:
        _fail("live CharacterBody buoyancy failed, height error="+str(error_y))
        return
    if moved_xz<0.23:
        _fail("live mouse not carried by current after releasing joystick, drift="+str(moved_xz))
        return
    var live_pool: WaterRipplePool = game.get("ripple_pool") as WaterRipplePool
    if live_pool.count_active() <= 0:
        _fail("real swim movement did not create wake rings")
        return
    if actual_water.wetness<0.5:
        _fail("live mouse fur never became wet")
        return
    print("S6_LIVE_PHYSICS_OK drift=",moved_xz," surface_error=",error_y," wake=",live_pool.count_active())
    print("WATER_S6_OK shoal=",shoal["depth"]," pool=",deep["depth"]," float_error=",final_depth," current=",water.flow_xz.length()," camera_hysteresis=ok ripples=12 rig=",rig.get_bone_count())
    quit(0)
