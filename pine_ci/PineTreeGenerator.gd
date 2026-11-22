@tool
class_name PineTreeGenerator
extends Node3D
## Procedural pine tree generator - Godot 4.7.2 (Mobile renderer compatible).
## No imported assets. Generates wood geometry, foliage, textures, LOD and collision.
## All random streams are seeded for repeatable results.

const CROWN_CONICAL: int = 0
const CROWN_OVAL: int = 1
const CROWN_UMBRELLA: int = 2

const FOLIAGE_SHADER: String = """
shader_type spatial;
render_mode cull_disabled, specular_schlick_ggx;

uniform sampler2D needle_tex : source_color, filter_linear_mipmap_anisotropic;
uniform vec3 tint : source_color = vec3(1.0);
uniform float alpha_scissor : hint_range(0.0, 1.0) = 0.35;
uniform float roughness_value : hint_range(0.0, 1.0) = 0.85;
uniform float wind_strength = 0.0;
uniform float wind_speed = 1.2;
uniform float tree_height = 12.0;
uniform float crown_radius = 3.0;
uniform vec3 backlight_color : source_color = vec3(0.10, 0.16, 0.06);

void vertex() {
    float h = clamp(VERTEX.y / max(tree_height, 0.001), 0.0, 1.0);
    float radial = clamp(length(VERTEX.xz) / max(crown_radius, 0.001), 0.0, 1.0);
    float weight = h * h * mix(0.3, 1.0, radial);
    vec3 wp = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
    float phase = wp.x * 0.35 + wp.z * 0.27;
    float gust = sin(TIME * wind_speed + phase)
               + 0.5 * sin(TIME * wind_speed * 2.33 + phase * 1.7);
    VERTEX.x += gust * wind_strength * weight;
    VERTEX.z += cos(TIME * wind_speed * 0.81 + phase)
                * wind_strength * 0.6 * weight;
    VERTEX.y += sin(TIME * wind_speed * 1.7 + phase * 2.1)
                * wind_strength * 0.15 * weight;
}

void fragment() {
    vec4 tex = texture(needle_tex, UV);
    // Opaque + discard: cheaper than alpha blending on mobile GPUs.
    if (tex.a < alpha_scissor) {
        discard;
    }
    ALBEDO = tex.rgb * COLOR.rgb * tint;
    ROUGHNESS = roughness_value;
    SPECULAR = 0.2;
    BACKLIGHT = backlight_color;
}
"""


#region Exported settings
@export_group("Seed & Generation")
@export var seed_value: int = 1337:
    set(value):
        seed_value = value
        _queue_rebuild()

@export var auto_rebuild: bool = true
@export_tool_button("Rebuild Pine Tree") var _btn_rebuild: Callable = _build_tree
@export_tool_button("Random Seed") var _btn_seed: Callable = _randomize_seed
@export_tool_button("Export to res://Generated") var _btn_export: Callable = _export_assets

@export_group("Trunk")
@export_range(2.0, 40.0, 0.1, "or_greater", "suffix:m") var height: float = 12.0:
    set(value):
        height = value
        _queue_rebuild()
@export_range(0.05, 1.5, 0.01, "suffix:m") var radius_bottom: float = 0.32:
    set(value):
        radius_bottom = value
        _queue_rebuild()
@export_range(0.01, 0.5, 0.005, "suffix:m") var radius_top: float = 0.05:
    set(value):
        radius_top = value
        _queue_rebuild()
@export_range(5, 24, 1) var trunk_sides: int = 10:
    set(value):
        trunk_sides = value
        _queue_rebuild()
@export_range(4, 48, 1) var trunk_segments: int = 16:
    set(value):
        trunk_segments = value
        _queue_rebuild()
@export_range(0.0, 0.2, 0.005) var lean: float = 0.03:
    set(value):
        lean = value
        _queue_rebuild()
@export_range(0.0, 0.6, 0.01, "suffix:m") var gnarl: float = 0.12:
    set(value):
        gnarl = value
        _queue_rebuild()
@export_range(0.0, 1.0, 0.01) var root_flare: float = 0.4:
    set(value):
        root_flare = value
        _queue_rebuild()

@export_group("Branches")
@export_range(3, 24, 1) var whorl_count: int = 9:
    set(value):
        whorl_count = value
        _queue_rebuild()
@export_range(2, 12, 1) var branches_min: int = 4:
    set(value):
        branches_min = value
        _queue_rebuild()
@export_range(2, 14, 1) var branches_max: int = 7:
    set(value):
        branches_max = value
        _queue_rebuild()
@export_range(0.01, 0.2, 0.005, "suffix:m") var branch_radius: float = 0.045:
    set(value):
        branch_radius = value
        _queue_rebuild()
@export_range(3, 16, 1) var branch_segments: int = 7:
    set(value):
        branch_segments = value
        _queue_rebuild()
@export_range(3, 12, 1) var branch_sides: int = 6:
    set(value):
        branch_sides = value
        _queue_rebuild()
@export_range(0.0, 0.8, 0.01) var droop: float = 0.22:
    set(value):
        droop = value
        _queue_rebuild()
@export_range(0.0, 1.0, 0.01) var upturn: float = 0.30:
    set(value):
        upturn = value
        _queue_rebuild()
@export_range(0, 6, 1) var twig_count: int = 3:
    set(value):
        twig_count = value
        _queue_rebuild()

@export_group("Crown")
@export_enum("Conical", "Oval", "Umbrella") var crown_shape: int = CROWN_CONICAL:
    set(value):
        crown_shape = value
        _queue_rebuild()
@export_range(0.5, 12.0, 0.1, "or_greater", "suffix:m") var crown_radius: float = 3.0:
    set(value):
        crown_radius = value
        _queue_rebuild()
@export_range(0.05, 0.8, 0.01) var crown_start: float = 0.28:
    set(value):
        crown_start = value
        _queue_rebuild()
@export_range(0.0, 1.0, 0.01) var layer_pattern: float = 0.7:
    set(value):
        layer_pattern = value
        _queue_rebuild()
@export_range(0.0, 1.0, 0.01) var inner_fill: float = 0.25:
    set(value):
        inner_fill = value
        _queue_rebuild()

@export_group("Needle Foliage")
@export_range(0.15, 1.5, 0.01, "suffix:m") var tuft_size: float = 0.5:
    set(value):
        tuft_size = value
        _queue_rebuild()
@export_range(2, 24, 1) var tufts_per_branch: int = 10:
    set(value):
        tufts_per_branch = value
        _queue_rebuild()
@export_range(1, 6, 1) var cards_per_tuft: int = 3:
    set(value):
        cards_per_tuft = value
        _queue_rebuild()
@export_range(40, 240, 1) var needle_count: int = 120:
    set(value):
        needle_count = value
        _queue_rebuild()
@export_enum("128:128", "256:256", "512:512") var needle_tex_size: int = 256:
    set(value):
        needle_tex_size = value
        _queue_rebuild()
@export var needle_color: Color = Color(0.13, 0.26, 0.10):
    set(value):
        needle_color = value
        _queue_rebuild()
@export var needle_color_tip: Color = Color(0.32, 0.48, 0.18):
    set(value):
        needle_color_tip = value
        _queue_rebuild()
@export_range(0.0, 1.0, 0.01) var color_variation: float = 0.25:
    set(value):
        color_variation = value
        _queue_rebuild()
@export_range(0.05, 0.9, 0.01) var alpha_scissor: float = 0.35:
    set(value):
        alpha_scissor = value
        _apply_foliage_params()

@export_group("Bark")
@export var bark_color: Color = Color(0.30, 0.22, 0.16):
    set(value):
        bark_color = value
        _queue_rebuild()
@export_enum("128:128", "256:256", "512:512") var bark_tex_size: int = 256:
    set(value):
        bark_tex_size = value
        _queue_rebuild()

@export_group("Wind")
@export var wind_enabled: bool = true:
    set(value):
        wind_enabled = value
        _apply_foliage_params()
@export_range(0.0, 0.4, 0.005) var wind_strength: float = 0.07:
    set(value):
        wind_strength = value
        _apply_foliage_params()
@export_range(0.1, 4.0, 0.05) var wind_speed: float = 1.2:
    set(value):
        wind_speed = value
        _apply_foliage_params()

@export_group("LOD & Collision")
@export_range(10.0, 300.0, 1.0, "suffix:m") var lod_distance: float = 45.0:
    set(value):
        lod_distance = value
        _queue_rebuild()
@export var cast_shadows: bool = true:
    set(value):
        cast_shadows = value
        _queue_rebuild()
@export var collision_enabled: bool = true:
    set(value):
        collision_enabled = value
        _queue_rebuild()
#endregion


#region Internal state
var _rng: RandomNumberGenerator = RandomNumberGenerator.new()
var _noise: FastNoiseLite = FastNoiseLite.new()
var _lean_dir: Vector3 = Vector3.RIGHT
var _rebuild_pending: bool = false
var _branch_vertex_count: int = 0
var _spots: Array[Dictionary] = []

var _bark_mat: StandardMaterial3D
var _foliage_mat: ShaderMaterial
var _needle_tex: ImageTexture
var _bark_alb_tex: ImageTexture
var _bark_nrm_tex: ImageTexture
var _trunk_mesh: ArrayMesh
var _branches_mesh: ArrayMesh
var _foliage_lod0: ArrayMesh
var _foliage_lod1: ArrayMesh
var _bark_cache_key: int = 0
var _needle_cache_key: int = 0
#endregion


#region Lifecycle
func _ready() -> void:
    # Always build once with loaded Inspector values, even if auto_rebuild is off.
    _rebuild_pending = true
    call_deferred("_run_queued_rebuild")


func _queue_rebuild() -> void:
    if not is_inside_tree() or not is_node_ready():
        return
    if Engine.is_editor_hint() and not auto_rebuild:
        return
    if _rebuild_pending:
        return
    _rebuild_pending = true
    call_deferred("_run_queued_rebuild")


func _run_queued_rebuild() -> void:
    if _rebuild_pending:
        _build_tree()


func _randomize_seed() -> void:
    seed_value = randi()
    notify_property_list_changed()
    _build_tree()


func _clear_generated_children() -> void:
    # Do NOT erase manually added lights, sockets or other children.
    for child in get_children():
        if child.has_meta("_pine_generated"):
            remove_child(child)
            child.queue_free()
#endregion


#region Build
func _build_tree() -> void:
    _rebuild_pending = false
    if not is_inside_tree():
        return
    _clear_generated_children()

    _rng.seed = seed_value
    _noise.seed = seed_value
    _noise.noise_type = FastNoiseLite.TYPE_SIMPLEX
    _noise.frequency = 1.0
    _make_materials()

    var angle: float = _rng.randf() * TAU
    _lean_dir = Vector3(cos(angle), 0.0, sin(angle))
    _spots.clear()
    _branch_vertex_count = 0

    _trunk_mesh = _gen_trunk()
    _branches_mesh = _gen_branches()
    _foliage_lod0 = _gen_foliage(1.0, 1.0)
    _foliage_lod1 = _gen_foliage(0.5, 1.55)
    _assemble(self, true)


func _make_materials() -> void:
    var bark_key: int = hash([seed_value, bark_color, bark_tex_size])
    if bark_key != _bark_cache_key or _bark_alb_tex == null or _bark_nrm_tex == null:
        var textures: Array[ImageTexture] = _make_bark_textures()
        _bark_alb_tex = textures[0]
        _bark_nrm_tex = textures[1]
        _bark_cache_key = bark_key

    var needle_key: int = hash([seed_value, needle_count, needle_tex_size])
    if needle_key != _needle_cache_key or _needle_tex == null:
        _needle_tex = _make_needle_texture()
        _needle_cache_key = needle_key

    _bark_mat = StandardMaterial3D.new()
    _bark_mat.albedo_texture = _bark_alb_tex
    _bark_mat.roughness = 0.95
    _bark_mat.normal_enabled = true
    _bark_mat.normal_texture = _bark_nrm_tex
    _bark_mat.normal_scale = 0.9
    _bark_mat.uv1_scale = Vector3(3.0, maxf(height / 1.6, 0.1), 1.0)
    _bark_mat.texture_filter = BaseMaterial3D.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS_ANISOTROPIC

    var shader: Shader = Shader.new()
    shader.code = FOLIAGE_SHADER
    _foliage_mat = ShaderMaterial.new()
    _foliage_mat.shader = shader
    _foliage_mat.set_shader_parameter("needle_tex", _needle_tex)
    _foliage_mat.set_shader_parameter("tree_height", height)
    _foliage_mat.set_shader_parameter("crown_radius", crown_radius)
    _foliage_mat.set_shader_parameter(
        "backlight_color", Vector3(needle_color.r, needle_color.g, needle_color.b) * 0.7
    )
    _apply_foliage_params()


func _apply_foliage_params() -> void:
    if _foliage_mat == null:
        return
    _foliage_mat.set_shader_parameter("wind_strength", wind_strength if wind_enabled else 0.0)
    _foliage_mat.set_shader_parameter("wind_speed", wind_speed)
    _foliage_mat.set_shader_parameter("alpha_scissor", alpha_scissor)
#endregion


#region Trunk
func _trunk_radius(y: float) -> float:
    var t: float = clampf(y / maxf(height, 0.01), 0.0, 1.0)
    var radius: float = lerpf(radius_bottom, radius_top, pow(t, 0.85))
    radius *= 1.0 + root_flare * 1.4 * pow(maxf(0.0, 1.0 - t / 0.06), 2.0)
    return radius


func _trunk_center(y: float) -> Vector3:
    var t: float = y / maxf(height, 0.01)
    var lean_offset: Vector3 = _lean_dir * lean * height * t * t
    var wobble: Vector3 = Vector3(
        _noise.get_noise_2d(y * 0.35, 13.7),
        0.0,
        _noise.get_noise_2d(y * 0.35, 71.3)
    ) * gnarl * t
    return lean_offset + wobble


func _gen_trunk() -> ArrayMesh:
    var st: SurfaceTool = SurfaceTool.new()
    st.begin(Mesh.PRIMITIVE_TRIANGLES)
    var rings: int = trunk_segments + 1

    for i in range(rings):
        var y: float = height * float(i) / float(trunk_segments)
        var radius: float = _trunk_radius(y)
        var center: Vector3 = _trunk_center(y)
        var delta: float = 0.05
        var next_radius: float = _trunk_radius(minf(y + delta, height))
        var slope: float = (next_radius - radius) / delta
        for j in range(trunk_sides + 1):
            var angle: float = TAU * float(j) / float(trunk_sides)
            var wobble: float = 1.0 + 0.06 * _noise.get_noise_2d(
                cos(angle) * 2.0 + 7.0, y * 1.5 + sin(angle) * 2.0
            )
            st.set_normal(Vector3(cos(angle), -slope, sin(angle)).normalized())
            st.set_uv(Vector2(float(j) / float(trunk_sides), y / height))
            st.add_vertex(center + Vector3(cos(angle) * radius * wobble, 0.0, sin(angle) * radius * wobble))

    for i in range(trunk_segments):
        for j in range(trunk_sides):
            var a: int = i * (trunk_sides + 1) + j
            var b: int = a + trunk_sides + 1
            st.add_index(a)
            st.add_index(b)
            st.add_index(a + 1)
            st.add_index(a + 1)
            st.add_index(b)
            st.add_index(b + 1)

    var apex: int = rings * (trunk_sides + 1)
    st.set_normal(Vector3.UP)
    st.set_uv(Vector2(0.5, 1.0))
    st.add_vertex(_trunk_center(height) + Vector3.UP * 0.02)
    for j in range(trunk_sides):
        var a: int = (rings - 1) * (trunk_sides + 1) + j
        st.add_index(a)
        st.add_index(apex)
        st.add_index(a + 1)

    st.generate_tangents()
    var mesh: ArrayMesh = st.commit()
    mesh.surface_set_material(0, _bark_mat)
    return mesh
#endregion


#region Branches
func _crown_profile(t: float) -> float:
    var radius: float = 0.0
    match crown_shape:
        CROWN_CONICAL:
            radius = crown_radius * pow(1.0 - t, 0.9)
        CROWN_OVAL:
            radius = crown_radius * pow(
                sin(PI * clampf(t * 0.85 + 0.1, 0.0, 1.0)), 0.7
            )
        CROWN_UMBRELLA:
            radius = crown_radius * pow(smoothstep(0.0, 0.55, t), 0.6)
            radius *= 1.0 - 0.25 * smoothstep(0.8, 1.0, t)
    return maxf(radius, crown_radius * 0.06)


func _branch_curve(origin: Vector3, direction: Vector3, length: float,
        segments: int, droop_multiplier: float = 1.0) -> PackedVector3Array:
    var points: PackedVector3Array = PackedVector3Array()
    points.resize(segments + 1)
    var sideways: Vector3 = Vector3.UP.cross(direction)
    if sideways.length_squared() < 0.00001:
        sideways = Vector3.RIGHT
    sideways = sideways.normalized()
    var wiggle: float = _rng.randf_range(-1.0, 1.0)
    for k in range(segments + 1):
        var s: float = float(k) / float(segments)
        var point: Vector3 = origin + direction * (length * s)
        point.y += length * (-droop * droop_multiplier * s * s + upturn * s * s * s)
        point += sideways * wiggle * 0.06 * length * s * s
        points[k] = point
    return points


func _sample_curve(points: PackedVector3Array, s: float) -> Vector3:
    var f: float = clampf(s, 0.0, 1.0) * float(points.size() - 1)
    var i: int = int(f)
    var j: int = mini(i + 1, points.size() - 1)
    return points[i].lerp(points[j], f - float(i))


func _spot_color(position: Vector3, tier_t: float) -> Color:
    var axis: Vector3 = _trunk_center(position.y)
    var radial: float = clampf(
        Vector2(position.x - axis.x, position.z - axis.z).length()
        / maxf(crown_radius, 0.01), 0.0, 1.0
    )
    var shade: float = lerpf(0.5, 1.0, radial) * lerpf(0.82, 1.08, tier_t)
    var jitter: float = 1.0 + _rng.randf_range(-1.0, 1.0) * color_variation
    var base: Color = needle_color.lerp(needle_color_tip, _rng.randf() * 0.5)
    return base * (shade * jitter)


func _gen_branches() -> ArrayMesh:
    var st: SurfaceTool = SurfaceTool.new()
    st.begin(Mesh.PRIMITIVE_TRIANGLES)
    _branch_vertex_count = 0
    var crown_base: float = crown_start
    if crown_shape == CROWN_UMBRELLA:
        crown_base = maxf(crown_start, 0.45)

    for i in range(whorl_count):
        var t: float = float(i) / float(maxi(whorl_count - 1, 1))
        var height_ratio: float = lerpf(crown_base, 0.985, pow(t, 0.92))
        var level_y: float = height_ratio * height
        level_y += (_rng.randf_range(-1.0, 1.0)
            * (height / float(whorl_count)) * 0.18 * (1.0 - layer_pattern))
        var profile_radius: float = _crown_profile(t)
        var n: int = maxi(2, int(round(
            _rng.randf_range(float(mini(branches_min, branches_max)),
                              float(maxi(branches_min, branches_max)))
            * lerpf(1.0, 0.7, t)
        )))
        var base_angle: float = _rng.randf() * TAU

        for b in range(n):
            var angle: float = (base_angle + TAU * float(b) / float(n)
                + _rng.randf_range(-0.25, 0.25) * (1.0 - layer_pattern * 0.6))
            var direction: Vector3 = Vector3(
                cos(angle),
                lerpf(-0.05, 0.3, t) + _rng.randf_range(-0.08, 0.08),
                sin(angle)
            ).normalized()
            var origin: Vector3 = (_trunk_center(level_y)
                + Vector3(cos(angle), 0.0, sin(angle))
                * _trunk_radius(level_y) * 0.85)
            var length: float = profile_radius * _rng.randf_range(0.85, 1.12)
            if length < 0.15:
                continue

            var points: PackedVector3Array = _branch_curve(
                origin, direction, length, branch_segments
            )
            var radii: PackedFloat32Array = PackedFloat32Array()
            for k in range(branch_segments + 1):
                var s: float = float(k) / float(branch_segments)
                radii.append(branch_radius * pow(1.0 - s, 0.8) + 0.004)
            _add_tube(st, points, radii, branch_sides)

            for k in range(tufts_per_branch):
                var s: float = (lerpf(0.35, 1.0,
                    float(k) / float(maxi(tufts_per_branch - 1, 1)))
                    + _rng.randf_range(-0.03, 0.03))
                var position: Vector3 = (_sample_curve(points, s)
                    + Vector3.UP * tuft_size * 0.12)
                var tangent: Vector3 = (
                    _sample_curve(points, minf(s + 0.08, 1.0))
                    - _sample_curve(points, maxf(s - 0.08, 0.0))
                ).normalized()
                _spots.append({
                    "pos": position,
                    "dir": (tangent + Vector3.UP * 0.55).normalized(),
                    "size": tuft_size * _rng.randf_range(0.8, 1.2) * lerpf(0.85, 1.2, s),
                    "col": _spot_color(position, t)
                })

            for tw in range(twig_count):
                var s: float = _rng.randf_range(0.45, 0.92)
                var position: Vector3 = _sample_curve(points, s)
                var tangent: Vector3 = (
                    _sample_curve(points, minf(s + 0.06, 1.0)) - position
                ).normalized()
                tangent = tangent.rotated(Vector3.UP, _rng.randf_range(-0.9, 0.9))
                tangent = (tangent + Vector3.UP
                    * _rng.randf_range(0.2, 0.55)).normalized()
                var twig_length: float = (length * _rng.randf_range(0.2, 0.38)
                    * (1.0 - s * 0.35))
                var twig_points: PackedVector3Array = _branch_curve(
                    position, tangent, twig_length, 4, 0.5
                )
                var twig_radii: PackedFloat32Array = PackedFloat32Array()
                for k in range(5):
                    twig_radii.append(lerpf(0.014, 0.003, float(k) / 4.0))
                _add_tube(st, twig_points, twig_radii, 4)

                var tip: Vector3 = twig_points[4]
                _spots.append({
                    "pos": tip + Vector3.UP * 0.05,
                    "dir": (tangent + Vector3.UP * 0.6).normalized(),
                    "size": tuft_size * _rng.randf_range(1.0, 1.35),
                    "col": _spot_color(tip, t)
                })
                var mid: Vector3 = _sample_curve(twig_points, 0.55)
                _spots.append({
                    "pos": mid,
                    "dir": (tangent + Vector3.UP * 0.5).normalized(),
                    "size": tuft_size * _rng.randf_range(0.75, 0.95),
                    "col": _spot_color(mid, t)
                })

    var top: Vector3 = _trunk_center(height)
    for k in range(7):
        var angle: float = _rng.randf() * TAU
        var radius: float = _rng.randf_range(0.0, 0.3)
        var position: Vector3 = (top + Vector3(
            cos(angle) * radius,
            _rng.randf_range(-0.15, 0.25),
            sin(angle) * radius
        ))
        _spots.append({
            "pos": position,
            "dir": (Vector3.UP + Vector3(cos(angle), 0.0, sin(angle)) * 0.5).normalized(),
            "size": tuft_size * _rng.randf_range(1.2, 1.5),
            "col": _spot_color(position, 1.0)
        })

    var fill_count: int = int(
        float(whorl_count) * float(branches_min + branches_max) * 0.5 * 3.0 * inner_fill
    )
    for i in range(fill_count):
        var t: float = _rng.randf()
        var level_y: float = lerpf(crown_base, 0.97, pow(t, 0.92)) * height
        var radius: float = _crown_profile(t) * _rng.randf_range(0.25, 0.7)
        var angle: float = _rng.randf() * TAU
        var position: Vector3 = _trunk_center(level_y) + Vector3(
            cos(angle) * radius, _rng.randf_range(-0.2, 0.2), sin(angle) * radius
        )
        _spots.append({
            "pos": position,
            "dir": (Vector3.UP + Vector3(cos(angle), 0.0, sin(angle))).normalized(),
            "size": tuft_size * _rng.randf_range(0.7, 1.0),
            "col": _spot_color(position, t)
        })

    st.generate_tangents()
    var mesh: ArrayMesh = st.commit()
    mesh.surface_set_material(0, _bark_mat)
    return mesh


func _add_tube(st: SurfaceTool, points: PackedVector3Array,
        radii: PackedFloat32Array, sides: int) -> void:
    # CRITICAL: Offset indices by all vertices previously appended to this SurfaceTool.
    # Otherwise every new branch links back to vertices from the first branch.
    var rings: int = points.size()
    if rings < 2 or radii.size() != rings:
        return
    var base_vertex: int = _branch_vertex_count
    var accumulated_v: float = 0.0

    for i in range(rings):
        var tangent: Vector3 = (
            points[mini(i + 1, rings - 1)] - points[maxi(i - 1, 0)]
        ).normalized()
        var normal: Vector3 = Vector3.UP.cross(tangent)
        if normal.length_squared() < 0.00001:
            normal = Vector3.RIGHT.cross(tangent)
        normal = normal.normalized()
        var binormal: Vector3 = tangent.cross(normal).normalized()
        if i > 0:
            accumulated_v += points[i].distance_to(points[i - 1])

        for j in range(sides + 1):
            var angle: float = TAU * float(j) / float(sides)
            var offset: Vector3 = normal * cos(angle) + binormal * sin(angle)
            st.set_normal(offset)
            st.set_uv(Vector2(
                float(j) / float(sides) / 3.0,
                accumulated_v / maxf(height, 0.01)
            ))
            st.add_vertex(points[i] + offset * radii[i])

    for i in range(rings - 1):
        for j in range(sides):
            var a: int = base_vertex + i * (sides + 1) + j
            var b: int = a + sides + 1
            st.add_index(a)
            st.add_index(b)
            st.add_index(a + 1)
            st.add_index(a + 1)
            st.add_index(b)
            st.add_index(b + 1)

    _branch_vertex_count += rings * (sides + 1)
#endregion


#region Foliage mesh
func _gen_foliage(detail: float, size_multiplier: float) -> ArrayMesh:
    var st: SurfaceTool = SurfaceTool.new()
    st.begin(Mesh.PRIMITIVE_TRIANGLES)
    var cards: int = cards_per_tuft if detail >= 1.0 else maxi(1, cards_per_tuft - 1)
    for i in range(_spots.size()):
        if detail < 1.0 and i % 2 == 1:
            continue
        var spot: Dictionary = _spots[i]
        _add_tuft_cards(
            st, spot["pos"], spot["dir"], spot["size"] * size_multiplier,
            spot["col"], cards
        )
    var mesh: ArrayMesh = st.commit()
    mesh.surface_set_material(0, _foliage_mat)
    return mesh


func _add_tuft_cards(st: SurfaceTool, center: Vector3,
        direction_hint: Vector3, size: float, color: Color, cards: int) -> void:
    for c in range(cards):
        var normal: Vector3 = (direction_hint + Vector3(
            _rng.randf_range(-1.0, 1.0),
            _rng.randf_range(-0.5, 0.9),
            _rng.randf_range(-1.0, 1.0)
        )).normalized()
        if c == cards - 1:
            normal = Vector3.UP.lerp(normal, 0.25).normalized()
        if normal.length_squared() < 0.01:
            normal = Vector3.UP
        var right: Vector3 = Vector3.UP.cross(normal)
        if right.length_squared() < 0.0001:
            right = Vector3.RIGHT
        right = right.normalized()
        var up: Vector3 = normal.cross(right).normalized()
        var angle: float = _rng.randf() * TAU
        var u: Vector3 = (right * cos(angle) + up * sin(angle)) * (size * 0.5)
        var v: Vector3 = (-right * sin(angle) + up * cos(angle)) * (size * 0.5)
        var card_center: Vector3 = center + Vector3(
            _rng.randf_range(-1.0, 1.0),
            _rng.randf_range(-0.5, 0.5),
            _rng.randf_range(-1.0, 1.0)
        ) * size * 0.12
        st.set_normal(normal.lerp(Vector3.UP, 0.35).normalized())
        st.set_color(color * _rng.randf_range(0.9, 1.1))
        var bottom_left: Vector3 = card_center - u - v
        var bottom_right: Vector3 = card_center + u - v
        var top_right: Vector3 = card_center + u + v
        var top_left: Vector3 = card_center - u + v
        st.set_uv(Vector2(0.0, 1.0))
        st.add_vertex(bottom_left)
        st.set_uv(Vector2(1.0, 1.0))
        st.add_vertex(bottom_right)
        st.set_uv(Vector2(1.0, 0.0))
        st.add_vertex(top_right)
        st.set_uv(Vector2(0.0, 1.0))
        st.add_vertex(bottom_left)
        st.set_uv(Vector2(1.0, 0.0))
        st.add_vertex(top_right)
        st.set_uv(Vector2(0.0, 0.0))
        st.add_vertex(top_left)
#endregion


#region Procedural images
func _make_bark_textures() -> Array[ImageTexture]:
    var size: int = bark_tex_size
    var noise: FastNoiseLite = FastNoiseLite.new()
    noise.seed = seed_value + 101
    noise.noise_type = FastNoiseLite.TYPE_SIMPLEX

    var albedo: Image = Image.create(size, size, false, Image.FORMAT_RGBA8)
    var normal_image: Image = Image.create(size, size, false, Image.FORMAT_RGBA8)
    var heights: PackedFloat32Array = PackedFloat32Array()
    heights.resize(size * size)
    var dark: Color = bark_color * 0.35
    dark.a = 1.0
    var light: Color = bark_color * 1.7 + Color(0.06, 0.05, 0.04)
    light.a = 1.0

    for y in range(size):
        for x in range(size):
            var u: float = float(x) / float(size)
            var v: float = float(y) / float(size)
            var groove: float = noise.get_noise_2d(u * 36.0, v * 5.0)
            var patch: float = noise.get_noise_2d(u * 7.0 + 31.0, v * 7.0 + 17.0)
            var h: float = groove * 0.5 + 0.5
            if absf(groove) < 0.07:
                h *= 0.35
            h = clampf(h + patch * 0.18, 0.0, 1.0)
            heights[y * size + x] = h
            albedo.set_pixel(x, y, dark.lerp(light, h))

    for y in range(size):
        for x in range(size):
            var left_h: float = heights[y * size + ((x - 1 + size) % size)]
            var right_h: float = heights[y * size + ((x + 1) % size)]
            var upper_h: float = heights[((y - 1 + size) % size) * size + x]
            var lower_h: float = heights[((y + 1) % size) * size + x]
            var n: Vector3 = Vector3(
                (left_h - right_h) * 2.5,
                (lower_h - upper_h) * 2.5,
                1.0
            ).normalized()
            normal_image.set_pixel(x, y, Color(
                n.x * 0.5 + 0.5, n.y * 0.5 + 0.5, n.z * 0.5 + 0.5, 1.0
            ))

    albedo.generate_mipmaps()
    normal_image.generate_mipmaps(true)
    var result: Array[ImageTexture] = [
        ImageTexture.create_from_image(albedo),
        ImageTexture.create_from_image(normal_image)
    ]
    return result


func _make_needle_texture() -> ImageTexture:
    var tex_rng: RandomNumberGenerator = RandomNumberGenerator.new()
    tex_rng.seed = seed_value + 911
    var size: int = needle_tex_size
    var image_data: Image = Image.create(size, size, false, Image.FORMAT_RGBA8)
    image_data.fill(Color(0.0, 0.0, 0.0, 0.0))
    var origin: Vector2 = Vector2(size * 0.5, size * 0.93)

    for k in range(int(size * 0.2)):
        var stem_color: Color = Color(0.4, 0.36, 0.3, 1.0)
        _plot(image_data, int(origin.x), int(origin.y) - k, stem_color)
        _plot(image_data, int(origin.x) + 1, int(origin.y) - k, stem_color)

    for i in range(needle_count):
        var angle: float = tex_rng.randf_range(-1.25, 1.25)
        if tex_rng.randf() < 0.15:
            var sign_value: float = 1.0 if tex_rng.randf() < 0.5 else -1.0
            angle = tex_rng.randf_range(1.25, 2.1) * sign_value
        var needle_length: float = size * tex_rng.randf_range(0.4, 0.8)
        var gray_start: float = tex_rng.randf_range(0.45, 0.7)
        var gray_end: float = minf(gray_start + tex_rng.randf_range(0.15, 0.4), 1.0)
        var position: Vector2 = origin + Vector2(
            tex_rng.randf_range(-2.0, 2.0), tex_rng.randf_range(-3.0, 1.0)
        )
        var steps: int = maxi(int(needle_length), 1)
        for k in range(steps):
            var t: float = float(k) / float(steps)
            var direction: Vector2 = Vector2(sin(angle), -cos(angle)).rotated(
                angle * 0.3 * t * t
            )
            position += direction
            var g: float = lerpf(gray_start, gray_end, t)
            var pixel_color: Color = Color(g, g, g * 0.95, 1.0)
            _plot(image_data, int(position.x), int(position.y), pixel_color)
            if t < 0.55:
                _plot(image_data, int(position.x) + 1, int(position.y), pixel_color)

    image_data.generate_mipmaps()
    return ImageTexture.create_from_image(image_data)


func _plot(image_data: Image, x: int, y: int, color: Color) -> void:
    if x >= 0 and x < image_data.get_width() and y >= 0 and y < image_data.get_height():
        image_data.set_pixel(x, y, color)
#endregion


#region Scene hierarchy and LOD
func _assemble(root: Node3D, tag_generated: bool) -> void:
    var geometry: Node3D = Node3D.new()
    geometry.name = "Geometry"
    if tag_generated:
        geometry.set_meta("_pine_generated", true)
    root.add_child(geometry)

    var wood: Node3D = Node3D.new()
    wood.name = "Wood"
    geometry.add_child(wood)
    _add_mesh_child(wood, "Trunk", _trunk_mesh)
    _add_mesh_child(wood, "Branches", _branches_mesh)

    var crown: Node3D = Node3D.new()
    crown.name = "Crown"
    geometry.add_child(crown)
    var foliage_0: MeshInstance3D = _add_mesh_child(crown, "Foliage_LOD0", _foliage_lod0)
    var foliage_1: MeshInstance3D = _add_mesh_child(crown, "Foliage_LOD1", _foliage_lod1)
    foliage_0.visibility_range_end = lod_distance
    foliage_0.visibility_range_end_margin = lod_distance * 0.15
    foliage_1.visibility_range_begin = lod_distance
    foliage_1.visibility_range_begin_margin = lod_distance * 0.15
    foliage_0.visibility_range_fade_mode = GeometryInstance3D.VISIBILITY_RANGE_FADE_SELF
    foliage_1.visibility_range_fade_mode = GeometryInstance3D.VISIBILITY_RANGE_FADE_SELF
    foliage_0.extra_cull_margin = tuft_size * 2.0 + wind_strength * 2.0 + 0.8
    foliage_1.extra_cull_margin = tuft_size * 3.0 + wind_strength * 2.0 + 0.8

    if collision_enabled:
        var body: StaticBody3D = StaticBody3D.new()
        body.name = "Collision"
        if tag_generated:
            body.set_meta("_pine_generated", true)
        root.add_child(body)
        var shape_node: CollisionShape3D = CollisionShape3D.new()
        shape_node.name = "TrunkShape"
        body.add_child(shape_node)
        var cylinder: CylinderShape3D = CylinderShape3D.new()
        cylinder.height = height * 0.95
        cylinder.radius = maxf(radius_bottom * 1.15, 0.05)
        shape_node.shape = cylinder
        shape_node.position.y = height * 0.475


func _add_mesh_child(parent: Node3D, node_name: String,
        mesh: ArrayMesh) -> MeshInstance3D:
    var instance: MeshInstance3D = MeshInstance3D.new()
    instance.name = node_name
    instance.mesh = mesh
    instance.cast_shadow = (GeometryInstance3D.SHADOW_CASTING_SETTING_ON
        if cast_shadows else GeometryInstance3D.SHADOW_CASTING_SETTING_OFF)
    parent.add_child(instance)
    return instance
#endregion


#region Save generated assets
func _export_assets() -> void:
    if not is_inside_tree():
        push_error("[PineTree] Add this node to the scene before exporting.")
        return
    # Export must reflect current Inspector values, including auto_rebuild = false.
    _build_tree()

    var relative_path: String = "Generated/PineTrees/seed_%d" % seed_value
    var directory: DirAccess = DirAccess.open("res://")
    if directory == null:
        push_error("[PineTree] Cannot open res://")
        return
    var create_error: Error = directory.make_dir_recursive(relative_path)
    if create_error != OK:
        push_error("[PineTree] Cannot create directory: %s" % error_string(create_error))
        return
    var base: String = "res://%s/" % relative_path

    # Save dependencies before meshes/scene so Godot can reference external paths.
    if not _save_resource(_needle_tex, base + "needle_texture.res"):
        return
    if not _save_resource(_bark_alb_tex, base + "bark_albedo.res"):
        return
    if not _save_resource(_bark_nrm_tex, base + "bark_normal.res"):
        return
    if not _save_resource(_bark_mat, base + "bark_material.tres"):
        return
    if not _save_resource(_foliage_mat.shader, base + "foliage_shader.tres"):
        return
    if not _save_resource(_foliage_mat, base + "foliage_material.tres"):
        return
    if not _save_resource(_trunk_mesh, base + "trunk.res"):
        return
    if not _save_resource(_branches_mesh, base + "branches.res"):
        return
    if not _save_resource(_foliage_lod0, base + "foliage_lod0.res"):
        return
    if not _save_resource(_foliage_lod1, base + "foliage_lod1.res"):
        return

    # A plain, scriptless PackedScene; generation is not repeated in the game.
    var root: Node3D = Node3D.new()
    root.name = "PineTree_seed_%d" % seed_value
    _assemble(root, false)
    _own_recursive(root, root)
    var packed: PackedScene = PackedScene.new()
    var pack_error: Error = packed.pack(root)
    if pack_error != OK:
        push_error("[PineTree] Scene pack failed: %s" % error_string(pack_error))
        root.free()
        return
    _save_resource(packed, base + "pine_tree.tscn")
    root.free()

    if Engine.is_editor_hint():
        EditorInterface.get_resource_filesystem().scan()
    print("[PineTree] Exported to: ", base)


func _save_resource(resource: Resource, path: String) -> bool:
    if resource == null:
        push_error("[PineTree] Null resource: %s" % path)
        return false
    var save_error: Error = ResourceSaver.save(resource, path)
    if save_error != OK:
        push_error("[PineTree] Save failed: %s (%s)" % [path, error_string(save_error)])
        return false
    return true


func _own_recursive(node: Node, scene_owner: Node) -> void:
    for child in node.get_children():
        child.owner = scene_owner
        _own_recursive(child, scene_owner)
#endregion
