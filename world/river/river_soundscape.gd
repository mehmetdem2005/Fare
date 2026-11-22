class_name RiverSoundscape
extends Node3D
## S7: only two spatial river emitters and one dedicated low-pass bus.
## All original sounds are pre-rendered mono WAV, not generated per frame.
const AUDIO_BUS: StringName = &"FareRiver"
var profile: RiverProfile
var flow: RiverFlowField
var camera: Camera3D
var bus_index: int = -1
var underwater: bool = false
var low_pass: AudioEffectLowPassFilter
var calm: AudioStreamPlayer3D
var rapids: AudioStreamPlayer3D
var drops: AudioStreamPlayer3D
var last_water_state: int = MouseWaterInteraction.DRY
var last_contact_ms: int = -100000
var contact_events: int = 0
var rocks: RiverObstacles = RiverObstacles.new()
var update_clock: float = 0.0
var filter_hz: float = 16000.0
var active: bool = true
var owns_bus: bool = false

func _ready() -> void:
    name="RiverSoundscape"
    # Headless GDScript regression has no real audio device: do not start
    # AudioServer buses/voices that outlive SceneTree test shutdown.
    # Mobile/desktop rendering always enables the real spatial sound bus.
    active = DisplayServer.get_name() != "headless"
    low_pass=AudioEffectLowPassFilter.new()
    low_pass.cutoff_hz=filter_hz
    if active:
        bus_index=AudioServer.get_bus_index(AUDIO_BUS)
        if bus_index<0:
            AudioServer.add_bus()
            owns_bus=true
            bus_index=AudioServer.bus_count-1
            AudioServer.set_bus_name(bus_index,AUDIO_BUS)
        AudioServer.add_bus_effect(bus_index,low_pass)
    calm=_make_player("CalmCurrent","res://assets/audio/river_calm.wav")
    rapids=_make_player("RockRapids","res://assets/audio/river_rapids.wav")
    drops=_make_player("ContactDrops","res://assets/audio/river_drops.wav",false)
    drops.max_distance=13.0
    drops.volume_db=-22.0

func _exit_tree() -> void:
    # The headless Godot tests also own an AudioServer; leaving buses behind
    # leaks audio resources at shutdown and hides actual regression errors.
    if calm != null:
        calm.stop()
    if rapids != null:
        rapids.stop()
    if drops != null:
        drops.stop()
    var index: int = AudioServer.get_bus_index(AUDIO_BUS)
    if owns_bus and index>=0:
        AudioServer.remove_bus(index)
    low_pass=null
    bus_index=-1

func _make_player(label: String, resource_path: String, looping: bool = true) -> AudioStreamPlayer3D:
    var player: AudioStreamPlayer3D = AudioStreamPlayer3D.new()
    player.name=label
    player.max_distance=35.0
    player.unit_size=2.5
    player.bus=AUDIO_BUS
    player.volume_db=-40.0
    var clip: AudioStreamWAV = load(resource_path) as AudioStreamWAV
    if clip != null:
        clip.loop_mode=AudioStreamWAV.LOOP_FORWARD if looping else AudioStreamWAV.LOOP_DISABLED
        player.stream=clip
    else:
        push_error("S7 missing generated river audio: "+resource_path)
    add_child(player)
    if clip!=null and active and looping:
        player.play()
    return player

func update_water_sound(camera_submerged: bool, delta: float) -> void:
    underwater=camera_submerged
    filter_hz=lerpf(filter_hz,1150.0 if underwater else 16000.0,minf(1.0,delta*2.5))
    if low_pass!=null:
        low_pass.cutoff_hz=filter_hz
    update_clock+=delta
    if update_clock<0.18 or profile==null or flow==null or camera==null:
        return
    update_clock=0.0
    var eye: Vector3 = camera.global_position
    var z: float = eye.z
    var center: float = profile.center_x(z)
    var river: Dictionary = profile.sample(Vector2(center,z))
    var y: float = float(river["water_y"])+0.05
    calm.global_position=Vector3(center,y,z)
    var distance: float = maxf(0.0,absf(eye.x-center)-float(river["width"]))
    var attenuation: float = clampf(distance/26.0,0.0,1.0)
    calm.volume_db=lerpf(calm.volume_db,-16.0-attenuation*29.0,0.34)
    # Actual nearest S3 obstruction, rather than an imaginary rapid.
    var index: int=roundi(z/RiverObstacles.ROCK_SPACING_M)
    var nearest: Dictionary={}
    var nearest_sq: float=INF
    for i in range(index-1,index+2):
        var rock: Dictionary=rocks.obstacle_at(i,profile)
        var rp: Vector2=rock["xz"]
        var distance_sq: float=rp.distance_squared_to(Vector2(eye.x,eye.z))
        if distance_sq<nearest_sq:
            nearest_sq=distance_sq
            nearest=rock
    if not nearest.is_empty():
        var rock_pos: Vector2=nearest["xz"]
        var radius: float=float(nearest["radius"])
        var downstream: Dictionary=flow.sample(profile,rock_pos+Vector2(0.0,radius*1.0))
        rapids.global_position=Vector3(rock_pos.x,profile.surface_height(rock_pos.y)+0.1,rock_pos.y)
        var gain: float=clampf(float(downstream["turbulence"])*0.8+float(downstream["speed"])*0.18,0.0,1.0)
        var rock_attenuation: float=clampf(sqrt(nearest_sq)/33.0,0.0,1.0)
        rapids.volume_db=lerpf(rapids.volume_db,-25.0+9.0*gain-rock_attenuation*27.0,0.34)

func notify_water_contact(state: int, water_y: float, position: Vector3) -> void:
    if state == last_water_state:
        return
    var old: int=last_water_state
    last_water_state=state
    var now_ms: int=Time.get_ticks_msec()
    if now_ms-last_contact_ms < 320:
        return
    if old == MouseWaterInteraction.DRY or state == MouseWaterInteraction.DRY or state == MouseWaterInteraction.SWIMMING:
        last_contact_ms=now_ms
        contact_events+=1
        if drops != null:
            drops.global_position=Vector3(position.x,water_y,position.z)
            if active and drops.stream != null:
                drops.pitch_scale=0.94 if state == MouseWaterInteraction.SWIMMING else 1.08
                drops.play()
