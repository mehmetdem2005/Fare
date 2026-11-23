extends Node3D
## Playable landscape control laboratory, built completely independently of the static pine camera.
## Real mouse model can replace the proxy without changing the input/camera architecture.

var player: FareCharacterMotor
var camera_rig: FareThirdPersonCamera
var controls: FareTouchInputRouter
var overlay: FareTouchHUD

func _ready() -> void:
    _create_environment()
    _create_level()
    controls = FareTouchInputRouter.new()
    controls.name = "TouchInputRouter"
    add_child(controls)
    player = FareCharacterMotor.new()
    player.name = "MouseCharacter"
    player.position = Vector3(0.0, 0.08, 0.0)
    add_child(player)
    camera_rig = FareThirdPersonCamera.new()
    camera_rig.name = "IndependentCameraRig"
    camera_rig.body_height = player.height_m
    add_child(camera_rig)
    player.attach_input(controls, camera_rig)
    camera_rig.connect_controls(player, controls)
    var hud_layer := CanvasLayer.new()
    hud_layer.name = "TouchHUDLayer"
    hud_layer.layer = 10
    add_child(hud_layer)
    overlay = FareTouchHUD.new()
    overlay.name = "FloatingJoystickAndActionOverlay"
    overlay.router = controls
    overlay.mouse_filter = Control.MOUSE_FILTER_IGNORE
    hud_layer.add_child(overlay)
    overlay.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)

func _create_environment() -> void:
    var env := WorldEnvironment.new()
    env.name = "OutdoorEnvironment"
    var settings := Environment.new()
    settings.background_mode = Environment.BG_COLOR
    settings.background_color = Color(0.69, 0.79, 0.86)
    settings.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
    settings.ambient_light_color = Color(0.87, 0.93, 1.0)
    settings.ambient_light_energy = 0.76
    env.environment = settings
    add_child(env)
    var sun := DirectionalLight3D.new()
    sun.name = "Sun"
    sun.rotation_degrees = Vector3(-51.0, -31.0, 0.0)
    sun.light_energy = 1.7
    sun.light_color = Color(1.0, 0.94, 0.82)
    sun.shadow_enabled = true
    add_child(sun)

func _create_box(position_3d: Vector3, box_size: Vector3, color: Color,
        object_name: String) -> void:
    var physics := StaticBody3D.new()
    physics.name = object_name
    physics.collision_layer = 1
    physics.collision_mask = 2
    physics.position = position_3d
    add_child(physics)
    var collision := CollisionShape3D.new()
    var shape := BoxShape3D.new()
    shape.size = box_size
    collision.shape = shape
    physics.add_child(collision)
    var mesh_instance := MeshInstance3D.new()
    var mesh := BoxMesh.new()
    mesh.size = box_size
    mesh_instance.mesh = mesh
    var material := StandardMaterial3D.new()
    material.albedo_color = color
    material.roughness = 0.94
    mesh_instance.material_override = material
    physics.add_child(mesh_instance)

func _create_level() -> void:
    _create_box(Vector3(0, -0.13, 0), Vector3(70, 0.26, 70), Color(0.29, 0.37, 0.25), "WalkableGround")
    _create_box(Vector3(0.6, 0.72, 2.4), Vector3(1.2, 1.44, 0.35), Color(0.42, 0.38, 0.32), "CameraCollisionWall")
    _create_box(Vector3(-1.7, 0.54, -2.7), Vector3(0.32, 1.08, 3.8), Color(0.47, 0.40, 0.33), "NarrowCorridorWall")
    _create_box(Vector3(-3.0, 0.54, -2.7), Vector3(0.32, 1.08, 3.8), Color(0.46, 0.40, 0.34), "NarrowCorridorWallB")
    _create_box(Vector3(1.4, 0.21, -1.8), Vector3(0.7, 0.42, 0.7), Color(0.45, 0.46, 0.45), "JumpObstacle")
    # Pine visual assets from the previous project stay untouched.
    var tree_script: Script = load("res://scripts/sapling_mobile_tree.gd") if ResourceLoader.exists("res://scripts/sapling_mobile_tree.gd") else null
    if tree_script != null:
        for placement in [Vector3(4.7, 0, -5.2), Vector3(-6.5, 0, -8.0), Vector3(7.0, 0, 4.0)]:
            var tree: Node3D = tree_script.new()
            tree.position = placement
            tree.name = "OriginalPineVisual"
            add_child(tree)
