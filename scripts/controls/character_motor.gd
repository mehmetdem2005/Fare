class_name FareCharacterMotor
extends CharacterBody3D
## Mouse-scale character motor; collision and movement are physics-clocked.

@export var height_m: float = 0.45
@export var max_speed: float = 2.1
@export var max_acceleration: float = 11.0
@export var jump_velocity: float = 2.0
@export var gravity_magnitude: float = 9.8
@export var visual_turn_sharpness: float = 12.0
var input_router: FareTouchInputRouter
var camera_rig: FareThirdPersonCamera
var visual: Node3D

func _ready() -> void:
    collision_layer = 2
    collision_mask = 1
    var shape_node := CollisionShape3D.new()
    shape_node.name = "CharacterCapsuleCollision"
    var capsule := CapsuleShape3D.new()
    capsule.radius = height_m * 0.21
    capsule.height = height_m * 0.91
    shape_node.shape = capsule
    shape_node.position.y = height_m * 0.50
    add_child(shape_node)
    visual = Node3D.new()
    visual.name = "ReplaceWithMouseGLB"
    add_child(visual)
    # Neutral collision/debug proxy; replace child with mouse model without changing the controls.
    var body_mesh := MeshInstance3D.new()
    body_mesh.name = "DebugBodyProxy"
    var mesh := CapsuleMesh.new()
    mesh.radius = capsule.radius * 1.02
    mesh.height = capsule.height
    body_mesh.mesh = mesh
    body_mesh.position.y = height_m * 0.50
    var mat := StandardMaterial3D.new()
    mat.albedo_color = Color(0.41, 0.36, 0.31)
    mat.roughness = 1.0
    body_mesh.material_override = mat
    visual.add_child(body_mesh)

func attach_input(router: FareTouchInputRouter, rig: FareThirdPersonCamera) -> void:
    input_router = router
    camera_rig = rig

func _physics_process(delta: float) -> void:
    if input_router == null or camera_rig == null:
        return
    var stick: Vector2 = input_router.movement()
    var camera_base: Basis = camera_rig.camera_flat_basis()
    var camera_right: Vector3 = camera_base.x
    var camera_forward: Vector3 = -camera_base.z
    var desired_direction: Vector3 = camera_right * stick.x + camera_forward * (-stick.y)
    if desired_direction.length_squared() > 1.0:
        desired_direction = desired_direction.normalized()
    var target_horizontal: Vector3 = desired_direction * max_speed
    var current_horizontal: Vector2 = Vector2(velocity.x, velocity.z)
    var target_2d: Vector2 = Vector2(target_horizontal.x, target_horizontal.z)
    var motion: Vector2 = current_horizontal.move_toward(target_2d, max_acceleration * delta)
    velocity.x = motion.x
    velocity.z = motion.y
    if is_on_floor():
        if velocity.y < 0.0:
            velocity.y = -0.2
        if input_router.consume_jump() or Input.is_key_pressed(KEY_SPACE):
            velocity.y = jump_velocity
    else:
        velocity.y -= gravity_magnitude * delta
        input_router.consume_jump() # Do not buffer a jump indefinitely in the air.
    if desired_direction.length_squared() > 0.001:
        var target_yaw: float = atan2(-desired_direction.x, -desired_direction.z)
        visual.rotation.y = lerp_angle(visual.rotation.y, target_yaw,
            1.0 - exp(-visual_turn_sharpness * delta))
        # Root yaw is kept in sync with the visual only when the camera asks to recenter.
        rotation.y = visual.rotation.y
    move_and_slide()
