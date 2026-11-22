class_name ForestAtmosphere
extends Node3D
## S5: Mobile-friendly coherent atmosphere. No volumetric fog, SSR or
## expensive per-frame sky updates. All time-of-day presets are deterministic.

const MORNING: int = 0
const MIDDAY: int = 1
const EVENING: int = 2

var current_preset: int = MORNING
var sun: DirectionalLight3D
var environment_node: WorldEnvironment
var environment: Environment
var sky: Sky
var sky_material: ProceduralSkyMaterial
var mist_material: ShaderMaterial

func _ready() -> void:
    sun = DirectionalLight3D.new()
    sun.name = "ForestSun"
    sun.shadow_enabled = true
    sun.directional_shadow_mode = DirectionalLight3D.SHADOW_PARALLEL_2_SPLITS
    sun.directional_shadow_max_distance = 50.0
    sun.directional_shadow_fade_start = 0.80
    add_child(sun)
    sky_material = ProceduralSkyMaterial.new()
    sky_material.use_debanding = true
    sky_material.sky_curve = 0.21
    sky_material.ground_curve = 0.08
    sky_material.sun_angle_max = 20.0
    sky_material.sun_curve = 0.12
    sky = Sky.new()
    sky.sky_material = sky_material
    sky.process_mode = Sky.PROCESS_MODE_INCREMENTAL
    sky.radiance_size = Sky.RADIANCE_SIZE_128
    environment = Environment.new()
    environment.background_mode = Environment.BG_SKY
    environment.sky = sky
    environment.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
    environment.reflected_light_source = Environment.REFLECTION_SOURCE_BG
    environment.ambient_light_sky_contribution = 0.62
    environment.tonemap_mode = Environment.TONE_MAPPER_FILMIC
    environment.tonemap_white = 5.0
    environment.fog_enabled = true
    environment.fog_height = 0.72
    environment.fog_sky_affect = 0.32
    environment.fog_sun_scatter = 0.08
    environment.glow_enabled = false
    environment.sdfgi_enabled = false
    environment.volumetric_fog_enabled = false
    environment_node = WorldEnvironment.new()
    environment_node.name = "ForestWorldEnvironment"
    environment_node.environment = environment
    add_child(environment_node)
    mist_material = ShaderMaterial.new()
    mist_material.shader = load("res://shaders/river_mist.gdshader") as Shader
    apply_preset(MORNING)

func apply_preset(preset: int) -> void:
    current_preset = clampi(preset, MORNING, EVENING)
    var sky_top: Color
    var sky_horizon: Color
    var ground_color: Color
    var sun_color: Color
    var fog_color: Color
    var sun_energy: float
    var fog_density: float
    var mist_density: float
    var shadow_distance: float
    var elevation: float
    if current_preset == MORNING:
        sky_top = Color(0.34,0.50,0.63)
        sky_horizon = Color(0.78,0.73,0.62)
        ground_color = Color(0.30,0.33,0.30)
        sun_color = Color(1.0,0.82,0.63)
        fog_color = Color(0.67,0.73,0.71)
        sun_energy = 1.15
        fog_density = 0.0048
        mist_density = 0.70
        shadow_distance = 48.0
        elevation = -30.0
    elif current_preset == MIDDAY:
        sky_top = Color(0.29,0.50,0.72)
        sky_horizon = Color(0.64,0.76,0.84)
        ground_color = Color(0.31,0.36,0.34)
        sun_color = Color(1.0,0.97,0.89)
        fog_color = Color(0.68,0.76,0.78)
        sun_energy = 1.22
        fog_density = 0.0020
        mist_density = 0.17
        shadow_distance = 56.0
        elevation = -64.0
    else:
        sky_top = Color(0.37,0.42,0.60)
        sky_horizon = Color(0.88,0.58,0.45)
        ground_color = Color(0.28,0.29,0.31)
        sun_color = Color(1.0,0.64,0.40)
        fog_color = Color(0.63,0.60,0.58)
        sun_energy = 0.92
        fog_density = 0.0042
        mist_density = 0.38
        shadow_distance = 43.0
        elevation = -21.0
    sun.rotation_degrees = Vector3(elevation,-42.0,0.0)
    sun.light_color = sun_color
    sun.light_energy = sun_energy
    sun.directional_shadow_max_distance = shadow_distance
    sky_material.sky_top_color = sky_top
    sky_material.sky_horizon_color = sky_horizon
    sky_material.ground_horizon_color = sky_horizon.darkened(0.10)
    sky_material.ground_bottom_color = ground_color
    sky_material.sky_energy_multiplier = 1.0
    environment.ambient_light_energy = 0.65 if current_preset != EVENING else 0.58
    environment.fog_light_color = fog_color
    environment.fog_light_energy = 0.76
    environment.fog_density = fog_density
    environment.fog_height_density = 0.010 if current_preset == MORNING else 0.004
    environment.tonemap_exposure = 0.95 if current_preset == MORNING else (1.04 if current_preset == MIDDAY else 0.86)
    # Keep grading near-neutral; pink/neon colors and extreme bloom do not belong here.
    environment.adjustment_enabled = true
    environment.adjustment_saturation = 0.96
    environment.adjustment_contrast = 1.025
    mist_material.set_shader_parameter("mist_tint", Color(fog_color.r,fog_color.g,fog_color.b,1.0))
    mist_material.set_shader_parameter("mist_density",mist_density)

func sun_toward_surface() -> Vector3:
    # DirectionalLight emits light along -Z; +Z points toward the light source.
    return sun.global_transform.basis.z.normalized()

func configure_river(material: ShaderMaterial) -> void:
    var horizon: Color = sky_material.sky_horizon_color
    var zenith: Color = sky_material.sky_top_color
    material.set_shader_parameter("sky_reflection_horizon",Vector3(horizon.r,horizon.g,horizon.b))
    material.set_shader_parameter("sky_reflection_zenith",Vector3(zenith.r,zenith.g,zenith.b))
    material.set_shader_parameter("sun_direction",sun_toward_surface())
    material.set_shader_parameter("sun_glint_strength",0.25*sun.light_energy)

func caustics_energy() -> float:
    return 0.18 if current_preset == MORNING else (0.29 if current_preset == MIDDAY else 0.11)
