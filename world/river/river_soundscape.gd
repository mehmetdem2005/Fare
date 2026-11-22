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
var update_clock: float = 0.0
var filter_hz: float = 16000.0
var active: bool = true

func _ready() -> void:
    name="RiverSoundscape"
    bus_index=AudioServer.get_bus_index(AUDIO_BUS)
    if bus_index<0:
        AudioServer.add_bus()
        bus_index=AudioServer.bus_count-1
        AudioServer.set_bus_name(bus_index,AUDIO_BUS)
    # Only our river bus is filtered; never modify the user's Master bus.
    low_pass=AudioEffectLowPassFilter.new()
    low_pass.cutoff_hz=filter_hz
    AudioServer.add_bus_effect(bus_index,low_pass)
    calm=_make_player("CalmCurrent","res://assets/audio/river_calm.wav")
    rapids=_make_player("RockRapids","res://assets/audio/river_rapids.wav")

func _make_player(label: String, resource_path: String) -> AudioStreamPlayer3D:
    var player: AudioStreamPlayer3D = AudioStreamPlayer3D.new()
    player.name=label
    player.max_distance=35.0
    player.unit_size=2.5
    player.bus=AUDIO_BUS
    player.volume_db=-40.0
    var clip: AudioStreamWAV = load(resource_path) as AudioStreamWAV
    if clip != null:
        clip.loop_mode=AudioStreamWAV.LOOP_FORWARD
        player.stream=clip
    else:
        push_error("S7 missing generated river audio: "+resource_path)
    add_child(player)
    if clip!=null and active:
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
    var p: Vector2 = Vector2(center,z)
    var river: Dictionary = profile.sample(p)
    var current: Dictionary = flow.sample(profile,p)
    var y: float = float(river["water_y"])+0.05
    calm.global_position=Vector3(center,y,z)
    rapids.global_position=Vector3(center+1.2,y,z+3.0)
    var distance: float = maxf(0.0,absf(eye.x-center)-float(river["width"]))
    var attenuation: float = clampf(distance/26.0,0.0,1.0)
    var rapids_gain: float = clampf(float(current["turbulence"])*0.70+float(current["speed"])*0.26,0.0,1.0)
    calm.volume_db=lerpf(calm.volume_db,-16.0-attenuation*29.0,0.34)
    rapids.volume_db=lerpf(rapids.volume_db,-26.0+8.0*rapids_gain-attenuation*28.0,0.34)
