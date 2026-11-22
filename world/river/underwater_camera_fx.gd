class_name UnderwaterCameraFX
extends CanvasLayer
## Transparent mobile-friendly color filter. It intentionally DOES NOT read
## screen textures a second time (the S4 water shader already does).
var surface_profile: RiverProfile
var overlay: ColorRect
var overlay_material: ShaderMaterial
var submerged: bool = false
var fade: float = 0.0

func _ready() -> void:
    layer = 6
    overlay = ColorRect.new()
    overlay.name = "UnderwaterOverlay"
    overlay.color = Color.WHITE
    overlay.mouse_filter = Control.MOUSE_FILTER_IGNORE
    overlay.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
    overlay_material = ShaderMaterial.new()
    overlay_material.shader = load("res://shaders/underwater_overlay.gdshader") as Shader
    overlay.material = overlay_material
    overlay.visible = false
    add_child(overlay)

func update_camera(camera_pos: Vector3, delta: float) -> void:
    if surface_profile == null:
        return
    var sample: Dictionary = surface_profile.sample(Vector2(camera_pos.x,camera_pos.z))
    var underwater_column: bool = float(sample["shore_sdf"]) < -0.025 and float(sample["depth"]) > 0.055
    var delta_y: float = float(sample["water_y"])-camera_pos.y
    if not underwater_column:
        submerged = false
    elif submerged:
        if delta_y < -0.08:
            submerged = false
    elif delta_y > 0.055:
        submerged = true
    fade = move_toward(fade,1.0 if submerged else 0.0,delta*3.3)
    overlay.visible = fade > 0.005
    overlay_material.set_shader_parameter("intensity",fade)
    overlay_material.set_shader_parameter("depth_m",clampf(maxf(0.0,delta_y),0.0,3.0))
