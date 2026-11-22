extends SceneTree
func _initialize() -> void:
    call_deferred("_run")
func _fail(s: String) -> void:
    push_error("RIVER_S7_FAIL "+s)
    quit(2)
func _run() -> void:
    for file in ["river_calm.wav","river_rapids.wav","river_drops.wav"]:
        if not ResourceLoader.exists("res://assets/audio/"+file):
            _fail("pre-generated original river audio missing "+file)
            return
    var scene: PackedScene=load("res://scenes/main.tscn") as PackedScene
    var game: Node3D=scene.instantiate() as Node3D
    root.add_child(game)
    await physics_frame
    var sound: RiverSoundscape=game.get("river_soundscape") as RiverSoundscape
    var micro: RiverMicroEffects=game.get("river_micro") as RiverMicroEffects
    if sound==null or micro==null:
        _fail("no integrated S7 systems")
        return
    if AudioServer.get_bus_index(RiverSoundscape.AUDIO_BUS)<0:
        _fail("dedicated river sound bus absent")
        return
    if sound.calm==null or sound.rapids==null or sound.calm.stream==null or sound.rapids.stream==null:
        _fail("spatial audio sources not loaded")
        return
    sound.update_water_sound(true,0.40)
    if sound.low_pass.cutoff_hz>=14500.0:
        _fail("underwater low-pass did not attenuate high frequencies")
        return
    var low_freq: float=sound.low_pass.cutoff_hz
    sound.update_water_sound(false,0.45)
    if sound.low_pass.cutoff_hz<=low_freq:
        _fail("sound stays muffled above water")
        return
    if micro.leaves_mesh.instance_count!=RiverMicroEffects.LEAF_COUNT or micro.footprints.size()!=RiverMicroEffects.FOOTPRINT_COUNT or micro.drop_mesh.instance_count!=RiverMicroEffects.DROP_COUNT:
        _fail("micro effect pooled capacities wrong")
        return
    var actor: CharacterBody3D=game.get_node("MousePlayer") as CharacterBody3D
    var profile: RiverProfile=game.get("river_profile") as RiverProfile
    var z: float=100.0
    var x: float=profile.center_x(z)
    var water_y: float=profile.surface_height(z)
    actor.global_position=Vector3(x,water_y+0.11,z)
    actor.velocity=Vector3(0.6,0.0,0.1)
    var water: MouseWaterInteraction=game.get("mouse_water") as MouseWaterInteraction
    water.update(profile,game.get("river_flow_field"),actor.global_position,0.25)
    micro.update_river(0.22)
    if micro.leaves.size()!=12:
        _fail("leaves do not populate stream")
        return
    var leaf: Vector2=micro.leaves[0]
    micro.update_river(0.25)
    if micro.leaves[0].distance_to(leaf)<0.005:
        _fail("leaf did not move with S3 current")
        return
    # On dry land, recently wet mouse leaves a bounded trail.
    water.state=MouseWaterInteraction.DRY
    water.wetness=0.9
    actor.global_position=Vector3(20.0,float(game.call("_height",20.0,16.0))+0.42,16.0)
    actor.velocity=Vector3(1.3,0.0,0.0)
    micro.update_river(0.3)
    if micro.footprint_count_active()<1:
        _fail("wet animal not leaving paw mark")
        return
    if micro.footprint_count_active()>RiverMicroEffects.FOOTPRINT_COUNT:
        _fail("too many footprint drawables")
        return
    var rig: Skeleton3D=game.get("rig") as Skeleton3D
    if rig==null or rig.get_bone_count()!=49:
        _fail("source 49-bone rig changed")
        return
    print("RIVER_S7_OK sound_sources=2 underwater_cutoff=",int(low_freq)," leaves=12 prints=",micro.footprint_count_active()," droplets=8 rig=49")
    quit(0)
