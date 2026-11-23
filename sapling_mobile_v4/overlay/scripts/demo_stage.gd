@tool
extends Node3D

func _ready() -> void:
    if get_node_or_null("DemoCamera") != null:
        return
    var forest_mode: bool = "Forest" in name
    var camera := Camera3D.new()
    camera.name = "DemoCamera"
    add_child(camera)
    camera.position = Vector3(26, 17, 30) if forest_mode else Vector3(6, 4.7, 11)
    camera.look_at(Vector3(0, 2.7, 0), Vector3.UP)
    camera.fov = 53.0 if forest_mode else 38.0
    camera.current = true
    var sun := DirectionalLight3D.new()
    sun.name = "DemoSun"
    add_child(sun)
    sun.rotation_degrees = Vector3(-46, -32, 0)
    sun.light_color = Color(1.0, 0.93, 0.79)
    sun.light_energy = 1.75
    sun.shadow_enabled = true
    var environment := WorldEnvironment.new()
    environment.name = "DemoEnvironment"
    add_child(environment)
    environment.environment = Environment.new()
    environment.environment.background_mode = Environment.BG_COLOR
    environment.environment.background_color = Color(0.71, 0.79, 0.82)
    environment.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
    environment.environment.ambient_light_color = Color(0.93, 0.94, 1.0)
    environment.environment.ambient_light_energy = 0.65
    var ground := MeshInstance3D.new()
    ground.name = "DemoGround"
    var plane := PlaneMesh.new()
    plane.size = Vector2(100, 100)
    ground.mesh = plane
    var ground_mat := StandardMaterial3D.new()
    ground_mat.albedo_color = Color(0.33, 0.38, 0.29)
    ground_mat.roughness = 0.97
    ground.material_override = ground_mat
    add_child(ground)
