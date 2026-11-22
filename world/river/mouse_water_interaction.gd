class_name MouseWaterInteraction
extends RefCounted
## S6: physically motivated, kinematic water interaction, without changing
## the original 49-bone GLB or switching CharacterBody3D to RigidBody3D.
##
## Body is 0.84m tall with feet at its origin -0.42m. Water probes deliberately
## follow its body coordinates, NOT the animated skinned-mesh vertices.
const DRY: int = 0
const SHALLOW: int = 1
const SWIMMING: int = 2
const FEET_OFFSET: float = -0.42
const BELLY_OFFSET: float = -0.23
const CHEST_OFFSET: float = -0.07
const HEAD_OFFSET: float = 0.30
const SWIM_ENTER_DEPTH: float = 0.54
const SWIM_EXIT_DEPTH: float = 0.43
const SWIM_ENTER_CHEST: float = 0.065
const SURFACE_Y_OFFSET: float = 0.10
const GRAVITY: float = 13.0

var state: int = DRY
var wetness: float = 0.0
var immersion: float = 0.0
var column_depth: float = 0.0
var water_y: float = 0.0
var shore_sdf: float = 1000.0
var foot_depth: float = 0.0
var chest_depth: float = 0.0
var head_depth: float = 0.0
var flow_xz: Vector2 = Vector2.ZERO
var wake_intensity: float = 0.0

func update(profile: RiverProfile, flow: RiverFlowField, position: Vector3, delta: float) -> void:
    var point: Vector2 = Vector2(position.x, position.z)
    var river: Dictionary = profile.sample(point)
    water_y = float(river["water_y"])
    column_depth = maxf(0.0,float(river["depth"]))
    shore_sdf = float(river["shore_sdf"])
    foot_depth = water_y - (position.y + FEET_OFFSET)
    chest_depth = water_y - (position.y + CHEST_OFFSET)
    head_depth = water_y - (position.y + HEAD_OFFSET)
    var touches: bool = shore_sdf < -0.025 and column_depth > 0.028 and foot_depth > -0.025
    if not touches:
        state = DRY
        flow_xz = Vector2.ZERO
        immersion = 0.0
        wake_intensity = 0.0
    else:
        var was_swimming: bool = state == SWIMMING
        if was_swimming:
            # Separate thresholds prevent near-surface state oscillation.
            state = SWIMMING if column_depth > SWIM_EXIT_DEPTH and foot_depth > 0.09 else SHALLOW
        else:
            state = SWIMMING if column_depth > SWIM_ENTER_DEPTH and chest_depth > SWIM_ENTER_CHEST else SHALLOW
        immersion = clampf(foot_depth / (HEAD_OFFSET-FEET_OFFSET),0.0,1.0)
        var field: Dictionary = flow.sample(profile,point)
        flow_xz = field["velocity"]
        wake_intensity = clampf(flow_xz.length()/2.0 + float(field["turbulence"])*0.22,0.0,1.0)
    wetness = move_toward(wetness, 1.0 if state != DRY else 0.0, delta*(2.8 if state != DRY else 0.045))

func apply_velocity(actor: CharacterBody3D, desired: Vector3, wants_run: bool, jump: bool, delta: float, walk_speed: float, run_speed: float, jump_speed: float) -> bool:
    var swimming: bool = state == SWIMMING
    actor.floor_snap_length = 0.0 if swimming else 0.12
    if swimming:
        # Relative flow and manual swimming both contribute. Releasing the
        # joystick MUST NOT cancel downstream current.
        var swim_input_speed: float = 1.45
        var target_xz: Vector2 = Vector2(desired.x,desired.z)*swim_input_speed + flow_xz*0.80
        var alpha: float = minf(1.0,delta*3.4)
        actor.velocity.x = lerpf(actor.velocity.x,target_xz.x,alpha)
        actor.velocity.z = lerpf(actor.velocity.z,target_xz.y,alpha)
        # Damped buoyancy/restoring spring about natural floating depth.
        # Numerical acceleration is limited to avoid one-frame launch.
        var target_y: float = water_y+SURFACE_Y_OFFSET
        var acceleration_y: float = clampf((target_y-actor.global_position.y)*12.0-actor.velocity.y*4.0,-14.0,17.0)
        actor.velocity.y = clampf(actor.velocity.y+acceleration_y*delta,-1.9,2.2)
        if jump:
            actor.velocity.y = maxf(actor.velocity.y,0.82)
        return true
    var top_speed: float = run_speed if wants_run else walk_speed
    if state == SHALLOW:
        # Resist wading without abruptly locking player motion.
        top_speed *= 0.89-0.28*immersion
    var target: Vector2 = Vector2(desired.x,desired.z)*top_speed
    if state == SHALLOW:
        target += flow_xz*0.20*immersion
    var interp: float = minf(1.0,delta*(10.0 if actor.is_on_floor() else 4.0))
    actor.velocity.x = lerpf(actor.velocity.x,target.x,interp)
    actor.velocity.z = lerpf(actor.velocity.z,target.y,interp)
    if actor.is_on_floor():
        if actor.velocity.y < 0.0:
            actor.velocity.y = -0.1
        if jump:
            actor.velocity.y = jump_speed*(0.80 if state == SHALLOW else 1.0)
    else:
        actor.velocity.y -= GRAVITY*delta
    return false

func label() -> String:
    if state == SWIMMING:
        return "YUZUYOR"
    if state == SHALLOW:
        return "SIG SU"
    return ""
