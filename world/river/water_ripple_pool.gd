class_name WaterRipplePool
extends Node3D
## Bounded ring pool for S6 water entry/paw contacts and swimming wake.
## Shared mesh and material, no per-frame mesh rebuild, at most 12 drawables.
const CAPACITY: int = 12
var rings: Array[MeshInstance3D] = []
var ages: Array[float] = []
var durations: Array[float] = []
var strengths: Array[float] = []
var pointer: int = 0

func _ready() -> void:
    name = "WaterRipplePool"
    var mesh: TorusMesh = TorusMesh.new()
    mesh.inner_radius = 0.84
    mesh.outer_radius = 1.0
    mesh.rings = 12
    mesh.ring_segments = 16
    var mat: StandardMaterial3D = StandardMaterial3D.new()
    mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
    mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
    mat.albedo_color = Color(0.77,0.87,0.81,0.20)
    mat.no_depth_test = false
    mat.cull_mode = BaseMaterial3D.CULL_DISABLED
    for i in range(CAPACITY):
        var part: MeshInstance3D = MeshInstance3D.new()
        part.name = "Ripple_%d" % i
        part.mesh = mesh
        part.material_override = mat
        part.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
        part.visible = false
        rings.append(part)
        ages.append(10.0)
        durations.append(0.7)
        strengths.append(1.0)
        add_child(part)

func splash(point: Vector2, water_y: float, strength: float=0.7) -> void:
    var slot: int = pointer % CAPACITY
    pointer += 1
    var part: MeshInstance3D = rings[slot]
    part.global_position = Vector3(point.x,water_y+0.015,point.y)
    ages[slot]=0.0
    durations[slot]=0.60+0.35*clampf(strength,0.0,1.0)
    strengths[slot]=clampf(strength,0.15,1.0)
    part.transparency = 0.05
    part.visible = true

func _process(delta: float) -> void:
    for i in range(CAPACITY):
        var node: MeshInstance3D = rings[i]
        if not node.visible:
            continue
        ages[i]+=delta
        var fraction: float = ages[i]/durations[i]
        if fraction >= 1.0:
            node.visible = false
            continue
        var radius: float = (0.12+0.48*fraction)*strengths[i]
        node.scale = Vector3(radius,0.05,radius)
        node.transparency = clampf(fraction*0.93,0.0,0.95)

func count_active() -> int:
    var result: int = 0
    for node in rings:
        if node.visible:
            result+=1
    return result
