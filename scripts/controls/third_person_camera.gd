class_name FareThirdPersonCamera
extends Node3D
## Character-independent camera rig. Rotation reads input once/render frame.
## SpringArm handles near-plane obstruction; player is filtered by collision layer.

@export var body_height: float = 0.45
@export_range(0.5, 20.0, 0.1) var camera_distance_in_body_heights: float = 4.0
@export_range(35.0, 100.0, 1.0) var normal_fov: float = 68.0
@export_range(0.25, 3.0, 0.05) var sensitivity_multiplier: float = 1.0
@export_range(-89.0, -5.0, 1.0) var pitch_min: float = -55.0
@export_range(5.0, 89.0, 1.0) var pitch_max: float = 65.0
@export var invert_y: bool = false
@export var auto_recenter: bool = true

var player: CharacterBody3D
var input_router: FareTouchInputRouter
var yaw_angle: float = 0.0
var pitch_angle: float = deg_to_rad(-12.0)
var camera_idle_seconds: float = 0.0
var shoulder_sign: float = 1.0
var base_distance: float = 1.8
var yaw_pivot: Node3D
var pitch_pivot: Node3D
var shoulder_pivot: Node3D
var arm: SpringArm3D
var view_camera: Camera3D

func _ready() -> void:
    top_level = true
    base_distance = maxf(0.5, body_height * camera_distance_in_body_heights)
    yaw_pivot = Node3D.new()
    yaw_pivot.name = "YawPivot"
    add_child(yaw_pivot)
    pitch_pivot = Node3D.new()
    pitch_pivot.name = "PitchPivot"
    yaw_pivot.add_child(pitch_pivot)
    shoulder_pivot = Node3D.new()
    shoulder_pivot.name = "ShoulderPivot"
    pitch_pivot.add_child(shoulder_pivot)
    arm = SpringArm3D.new()
    arm.name = "CollisionSpringArm"
    arm.spring_length = base_distance
    arm.margin = 0.035
    arm.collision_mask = 1  # Environment only. Player uses collision layer 2.
    shoulder_pivot.add_child(arm)
    view_camera = Camera3D.new()
    view_camera.name = "GameplayCamera"
    view_camera.fov = normal_fov
    view_camera.keep_aspect = Camera3D.KEEP_HEIGHT
    view_camera.near = 0.03
    view_camera.far = 500.0
    arm.add_child(view_camera) # Direct child: Godot casts camera near plane.
    view_camera.current = true
    _update_pivot_transform()

func connect_controls(controlled_player: CharacterBody3D, router: FareTouchInputRouter) -> void:
    player = controlled_player
    input_router = router
    _update_pivot_transform(true)

func _process(delta: float) -> void:
    if player == null or input_router == null:
        return
    var look_delta: Vector2 = input_router.consume_look()
    if look_delta.length_squared() > 0.0:
        camera_idle_seconds = 0.0
        # Normalize by device screen height so landscape resolutions feel consistent.
        var physical_height: float = maxf(float(DisplayServer.screen_get_size().y), 240.0)
        var degree_per_pixel: float = 0.115 * 1080.0 / physical_height * sensitivity_multiplier
        yaw_angle -= deg_to_rad(look_delta.x * degree_per_pixel)
        pitch_angle -= deg_to_rad(look_delta.y * degree_per_pixel * 0.82) * (-1.0 if invert_y else 1.0)
    elif input_router.look_is_active():
        camera_idle_seconds = 0.0
    else:
        camera_idle_seconds += delta
    pitch_angle = clampf(pitch_angle, deg_to_rad(pitch_min), deg_to_rad(pitch_max))
    if input_router.consume_shoulder_swap():
        shoulder_sign = -shoulder_sign
    if input_router.consume_recenter():
        camera_idle_seconds = 999.0
        _recenter(delta, true)
    elif auto_recenter and camera_idle_seconds >= 1.4:
        _recenter(delta)
    _update_pivot_transform(false, delta)
    yaw_pivot.rotation.y = yaw_angle
    pitch_pivot.rotation.x = pitch_angle
    shoulder_pivot.position.x = lerpf(shoulder_pivot.position.x,
        shoulder_sign * body_height * 0.20, 1.0 - exp(-10.0 * delta))
    var fast_movement: bool = player.velocity.length() > 1.8
    view_camera.fov = lerpf(view_camera.fov, normal_fov + (4.0 if fast_movement else 0.0),
        1.0 - exp(-4.0 * delta))

func _recenter(delta: float, forced: bool = false) -> void:
    var vector: Vector2 = input_router.movement()
    if not forced and (vector.y > -0.72 or absf(vector.x) > 0.30):
        return
    if forced:
        # Rotate towards the player's facing direction, without a camera snap.
        yaw_angle = lerp_angle(yaw_angle, player.rotation.y, 1.0 - exp(-7.5 * delta))
    else:
        yaw_angle = lerp_angle(yaw_angle, player.rotation.y, 1.0 - exp(-1.65 * delta))

func _update_pivot_transform(immediate: bool = false, delta: float = 0.0) -> void:
    if player == null:
        return
    var target_pos: Vector3 = player.global_position + Vector3.UP * (body_height * 0.72)
    if immediate or delta <= 0.0:
        global_position = target_pos
    else:
        # Slight vertical damping for jumps, stronger horizontal following.
        var follow_xz: float = 1.0 - exp(-14.0 * delta)
        var follow_y: float = 1.0 - exp(-8.0 * delta)
        global_position.x = lerpf(global_position.x, target_pos.x, follow_xz)
        global_position.z = lerpf(global_position.z, target_pos.z, follow_xz)
        global_position.y = lerpf(global_position.y, target_pos.y, follow_y)

func camera_flat_basis() -> Basis:
    return Basis(Vector3.UP, yaw_angle)
