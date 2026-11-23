extends Node3D
# Fare Vadisi: Godot 4.7.2 Mobile Vulkan prototype.
# All chunk geometry and river banks use global coordinates for seamless borders.

const CELL: float = 40.0
const GRID: int = 56 # global Z rows shared by every terrain chunk; adaptive X rows
const RADIUS: int = 2
const WALK_SPEED: float = 3.4
const RUN_SPEED: float = 5.9
const JUMP_SPEED: float = 4.8
const SPAWN_X: float = 20.0
const SPAWN_Z: float = 16.0
const SPAWN_HEIGHT_ABOVE_TERRAIN: float = 3.5
const QUALITY_FAST: int = 0
const QUALITY_BALANCED: int = 1
const QUALITY_FULL: int = 2

var river_profile: RiverProfile = RiverProfile.new()
var river_surface_builder: RiverSurfaceBuilder = RiverSurfaceBuilder.new()
var shore_substrate: ShoreSubstrate = ShoreSubstrate.new()
var river_flow_field: RiverFlowField = RiverFlowField.new()
var river_flow_atlas_cache: RiverFlowAtlasCache = RiverFlowAtlasCache.new()
var river_obstacles: RiverObstacles = RiverObstacles.new()
var mouse_water: MouseWaterInteraction = MouseWaterInteraction.new()
var camera_water: UnderwaterCameraFX
var river_soundscape: RiverSoundscape
var river_micro: RiverMicroEffects
var ripple_pool: WaterRipplePool
var wet_fur_material: StandardMaterial3D
var wet_meshes: Array[MeshInstance3D] = []
var wet_overlay_active: bool = false
var last_wet_value: float = -1.0
var ripple_time: float = 0.0
var last_wet_point: Vector2 = Vector2.ZERO
var last_wet_height: float = 0.0
var last_water_state: int = MouseWaterInteraction.DRY
var atmosphere: ForestAtmosphere
var water_quality: WaterQualitySettings = WaterQualitySettings.new()
var wave_texture: Texture2D
var height_noise: FastNoiseLite = FastNoiseLite.new()
var detail_noise: FastNoiseLite = FastNoiseLite.new()
var player: CharacterBody3D
var model_holder: Node3D
var rig: Skeleton3D
var mouse_animation: AnimationPlayer
var view_camera: Camera3D
var mobile_camera_rig: FareThirdPersonCamera
var mobile_input: FareTouchInputRouter
var hud: Control
var terrain_mat: ShaderMaterial
var terrain_lite_mat: ShaderMaterial
var water_mat: ShaderMaterial
var water_lite_mat: ShaderMaterial
# S9.1c: Keep recent water mesh, flow image/texture and material pairs.
# LRU bound prevents unbounded GPU resources in the open world.
const WATER_RESOURCE_CACHE_LIMIT: int = 32
var water_resource_cache: Dictionary = {}
var water_resource_cache_lru: Array[Vector2i] = []
var water_resource_cache_hits: int = 0
var water_resource_cache_misses: int = 0
var chunk_cache: ChunkBakeCache = ChunkBakeCache.new()
var pending_cache_writes: Array[Vector2i] = []
var chunk_cache_hit_count: int = 0
var chunk_cache_miss_count: int = 0
var cache_write_timer: float = 0.0
var lod_update_timer: float = 0.0
var pine_mesh: Mesh
var grass_mesh: Mesh
var pebble_mesh: Mesh
var chunks: Dictionary = {}
var queue: Array[Vector2i] = []
var chunk_timer: float = 0.0
var s8_probe: S8PerformanceProbe
var s9_trace: S9ChunkTrace = S9ChunkTrace.new()
var s9_current_chunk_stages: Dictionary = {}
var s9_queue_requested_usec: Dictionary = {}
var s9_fixed_scene: bool = false
# Player physics/terrain first, non-colliding decorative instances after.
# One short deterministic RNG batch per scheduling turn.
const S9_COSMETIC_BUDGET_US: int = 3000
var cosmetic_jobs: Array[Dictionary] = []
var cosmetic_phase_peak_ms: Dictionary = {}
var cosmetic_completed_chunks: int = 0
# S9.3b CPU-only worker prefetch. Main thread owns every Node/ArrayMesh,
# ImageTexture and collision; no worker may read the active game scene.
const S9_MAX_CPU_WORKERS: int = 2
const S9_MAX_READY_DATA: int = 6
var s9_worker_enabled: bool = true
var s9_worker_tasks: Dictionary = {}
var s9_worker_ready: Dictionary = {}
var s9_worker_started: int = 0
var s9_worker_finished: int = 0
var s9_worker_used: int = 0
var s9_worker_discarded: int = 0
var s9_worker_collision_fallback: int = 0
var s9_worker_deferred_requests: int = 0
var s9_worker_latest_cpu_ms: float = 0.0
var s9_fixed_scene_center: Vector2i = Vector2i.ZERO
var max_chunk_load_ms: float = 0.0
var last_chunk_load_ms: float = 0.0
var max_cache_save_ms: float = 0.0
var cache_saves: int = 0
# Max elapsed time spent in each blocking phase, measured on the actual device.
var chunk_stage_peak_ms: Dictionary = {}
var last_process_work_ms: float = 0.0
var max_process_work_ms: float = 0.0
var last_physics_work_ms: float = 0.0
var max_physics_work_ms: float = 0.0
var mobile_quality_level: int = QUALITY_FULL
var look_yaw: float = 0.0
var look_pitch: float = 0.15
var follow_distance: float = 3.4
var stamina: float = 100.0
var stick: Vector2 = Vector2.ZERO
var stick_pointer: int = -1
var run_pointer: int = -1
var jump_pointer: int = -1
var look_pointer: int = -1
var mouse_action: String = ""
var jump_buffer: bool = false
var running: bool = false
var phase: float = 0.0
var elapsed: float = 0.0

func _ready() -> void:
    height_noise.seed = 49825
    height_noise.noise_type = FastNoiseLite.TYPE_SIMPLEX_SMOOTH
    height_noise.frequency = 0.014
    height_noise.fractal_type = FastNoiseLite.FRACTAL_FBM
    height_noise.fractal_octaves = 4
    detail_noise.seed = 29608
    detail_noise.frequency = 0.054
    _environment()
    _materials()
    # The measured Android phone sustained ~8 FPS at full resolution/4x MSAA.
    # Start in the reversible fast path; HUD retains a full-fidelity option.
    if OS.get_name()=="Android":
        set_mobile_quality(QUALITY_FAST)
    pine_mesh = _pine_mesh()
    grass_mesh = _grass_mesh()
    pebble_mesh = _stone_mesh()
    _create_actor()
    _create_camera()
    _create_hud()
    _setup_water_fx()
    _setup_river_audio_and_micro()
    _setup_performance_probe()
    # Build 3x3 chunks before the first frame; stream the outer ring later.
    var center: Vector2i = _current_chunk()
    for cz in range(-1, 2):
        for cx in range(-1, 2):
            _add_chunk(center + Vector2i(cx, cz))
    _queue_chunks()

func _environment() -> void:
    atmosphere = ForestAtmosphere.new()
    atmosphere.name = "ForestAtmosphere"
    add_child(atmosphere)

func set_atmosphere_preset(preset: int) -> void:
    if atmosphere == null:
        return
    atmosphere.apply_preset(preset)
    if terrain_mat != null:
        terrain_mat.set_shader_parameter("caustic_strength",atmosphere.caustics_energy())
    if water_mat != null:
        atmosphere.configure_river(water_mat)
    if water_lite_mat != null:
        atmosphere.configure_river(water_lite_mat)
    # Every water mesh stores BOTH S4 and distant LOD variants. Update both:
    # merely changing the currently rendered material produces stale sunset
    # color when LOD switches back later.
    for co in chunks.keys():
        var chunk: Node3D = chunks[co]
        var water: MeshInstance3D = chunk.get_node_or_null("FlowingWater") as MeshInstance3D
        if water != null:
            for key in ["high_water_material","low_water_material"]:
                var material: ShaderMaterial = water.get_meta(key,null) as ShaderMaterial
                if material != null:
                    atmosphere.configure_river(material)

func set_mobile_quality(level: int) -> void:
    mobile_quality_level=clampi(level,QUALITY_FAST,QUALITY_FULL)
    var viewport: Viewport=get_viewport()
    if viewport!=null:
        viewport.scaling_3d_scale=0.60 if mobile_quality_level==QUALITY_FAST else (0.75 if mobile_quality_level==QUALITY_BALANCED else 1.0)
        viewport.msaa_3d=Viewport.MSAA_4X if mobile_quality_level==QUALITY_FULL else Viewport.MSAA_DISABLED
    if atmosphere!=null and atmosphere.sun!=null:
        atmosphere.sun.shadow_enabled=mobile_quality_level!=QUALITY_FAST
    if mobile_quality_level==QUALITY_FAST and terrain_lite_mat==null:
        push_warning("Fast terrain shader is missing; preserving full terrain material")
    _update_chunk_lod()
    if s9_fixed_scene and mobile_quality_level!=QUALITY_FAST:
        # Quality changes reintroduce geometry jobs. The fixed-scene
        # measurement must never silently include their CPU cost.
        s9_fixed_scene=false
    if mobile_quality_level!=QUALITY_FAST:
        # Fast quality avoids constructing invisible river mist altogether.
        # A later quality upgrade schedules its deterministic restoration.
        for co_variant in chunks.keys():
            var co: Vector2i=co_variant
            if co.x>=-1 and co.x<=0:
                var root: Node3D=chunks[co]
                if not root.has_node("NearRiverMist"):
                    var pending: bool=false
                    for item in cosmetic_jobs:
                        if item["co"]==co:
                            pending=true
                            break
                    if not pending:
                        cosmetic_jobs.append({"co":co,"stage":3,"state":{"cursor":0}})

func _record_chunk_stage(name: String, began_usec: int) -> void:
    var elapsed_ms: float=float(Time.get_ticks_usec()-began_usec)*0.001
    chunk_stage_peak_ms[name]=maxf(float(chunk_stage_peak_ms.get(name,0.0)),elapsed_ms)
    s9_current_chunk_stages[name]=elapsed_ms

func set_s9_fixed_scene(enabled: bool) -> bool:
    if enabled and (chunks.size()!=25 or not queue.is_empty() or not cosmetic_jobs.is_empty() or not s9_worker_tasks.is_empty()):
        return false
    s9_fixed_scene=enabled
    s9_fixed_scene_center=_current_chunk() if enabled else Vector2i.ZERO
    return true


func _image_texture(path: String, fallback: Color) -> Texture2D:
    if ResourceLoader.exists(path):
        return load(path) as Texture2D
    var image: Image = Image.create(4, 4, false, Image.FORMAT_RGB8)
    image.fill(fallback)
    return ImageTexture.create_from_image(image)

func _materials() -> void:
    terrain_mat = ShaderMaterial.new()
    terrain_mat.shader = load("res://shaders/terrain.gdshader") as Shader
    terrain_mat.set_shader_parameter("grass_tex", _image_texture("res://assets/ground/grass.jpg", Color(0.29, 0.42, 0.23)))
    terrain_mat.set_shader_parameter("forest_tex", _image_texture("res://assets/ground/forest.jpg", Color(0.28, 0.32, 0.19)))
    terrain_mat.set_shader_parameter("cliff_tex", _image_texture("res://assets/ground/rock.jpg", Color(0.41, 0.40, 0.36)))
    terrain_mat.set_shader_parameter("riverbed_tex", _image_texture("res://assets/ground/pebbles.jpg", Color(0.49, 0.48, 0.42)))
    for label in ["grass", "forest", "rock", "pebbles"]:
        var shader_name: String = "cliff" if label == "rock" else ("riverbed" if label == "pebbles" else label)
        terrain_mat.set_shader_parameter(shader_name + "_nr", load("res://assets/ground/" + label + "_nrough.png") as Texture2D)
    terrain_lite_mat=ShaderMaterial.new()
    terrain_lite_mat.shader=load("res://shaders/terrain_mobile_fast.gdshader") as Shader
    for tex_key in ["grass_tex","forest_tex","cliff_tex","riverbed_tex"]:
        terrain_lite_mat.set_shader_parameter(tex_key,terrain_mat.get_shader_parameter(tex_key))
    water_mat = ShaderMaterial.new()
    water_mat.shader = load("res://shaders/river.gdshader") as Shader
    water_lite_mat = ShaderMaterial.new()
    water_lite_mat.shader = load("res://shaders/river_lite.gdshader") as Shader
    wave_texture = load("res://assets/water/wave_caustics_rgba.png") as Texture2D
    if wave_texture == null:
        push_error("Water wave normal/caustic texture missing. Run tools/build_water_normals.py")
    else:
        water_mat.set_shader_parameter("wave_map",wave_texture)
    water_quality.configure(water_mat,WaterQualitySettings.BALANCED)
    water_lite_mat.set_shader_parameter("wave_map",wave_texture)
    terrain_mat.set_shader_parameter("wave_map",wave_texture)
    terrain_mat.set_shader_parameter("caustic_strength",atmosphere.caustics_energy())
    atmosphere.configure_river(water_mat)

func _create_actor() -> void:
    player = CharacterBody3D.new()
    player.name = "MousePlayer"
    player.position = Vector3(SPAWN_X, _height(SPAWN_X, SPAWN_Z) + SPAWN_HEIGHT_ABOVE_TERRAIN, SPAWN_Z)
    player.floor_snap_length = 0.12
    player.collision_layer = 2
    player.collision_mask = 1
    var collider: CollisionShape3D = CollisionShape3D.new()
    var shape: CapsuleShape3D = CapsuleShape3D.new()
    shape.radius = 0.24
    shape.height = 0.84
    collider.shape = shape
    player.add_child(collider)
    add_child(player)
    model_holder = Node3D.new()
    model_holder.name = "MouseVisual"
    model_holder.position = Vector3(0.0, -0.41, 0.0)
    model_holder.rotation.y = PI
    player.add_child(model_holder)
    # A real Blender-exported GLB from the original rig repository.
    # NO home-made UV reversal, no reconstructed joint matrices.
    var corrected_source: PackedScene = null
    if ResourceLoader.exists("res://assets/mouse/mouse_r39_corrected.glb"):
        corrected_source = load("res://assets/mouse/mouse_r39_corrected.glb") as PackedScene
    var rigged_source: PackedScene = load("res://assets/mouse/mouse_rigged.glb") as PackedScene
    var clean_source: PackedScene = load("res://assets/mouse/mouse_original.glb") as PackedScene
    var imported: Node3D = null
    if corrected_source != null:
        imported = corrected_source.instantiate() as Node3D
    if imported == null and rigged_source != null:
        imported = rigged_source.instantiate() as Node3D
    if imported == null and clean_source != null:
        imported = clean_source.instantiate() as Node3D
    if imported != null:
        model_holder.add_child(imported)
        _setup_wet_fur(imported)
        var skeletons: Array[Node] = imported.find_children("*", "Skeleton3D", true, false)
        if not skeletons.is_empty():
            rig = skeletons[0] as Skeleton3D
        var players: Array[Node] = imported.find_children("*", "AnimationPlayer", true, false)
        for node in players:
            var candidate: AnimationPlayer = node as AnimationPlayer
            if candidate != null and candidate.has_animation("MouseRig"):
                mouse_animation = candidate
                var clip: Animation = mouse_animation.get_animation("MouseRig")
                if clip != null:
                    clip.loop_mode = Animation.LOOP_LINEAR
                break
    else:
        push_error("Mouse GLB missing from the project!")

func _create_camera() -> void:
    # Brand-new controller stack. Camera is independent from player rotation.
    mobile_input = FareTouchInputRouter.new()
    mobile_input.name = "MobileInputRouter"
    add_child(mobile_input)
    mobile_camera_rig = FareThirdPersonCamera.new()
    mobile_camera_rig.name = "MobileThirdPersonCameraRig"
    mobile_camera_rig.body_height = 0.84
    mobile_camera_rig.camera_distance_in_body_heights = 4.1
    mobile_camera_rig.normal_fov = 68.0
    add_child(mobile_camera_rig)
    mobile_camera_rig.connect_controls(player, mobile_input)
    view_camera = mobile_camera_rig.view_camera

func _create_hud() -> void:
    var overlay: CanvasLayer = CanvasLayer.new()
    overlay.name = "GameHUDLayer"
    overlay.layer = 10
    add_child(overlay)
    # Retain existing telemetry API for river/chunk diagnostics, without legacy controls.
    hud = Control.new()
    hud.set_script(load("res://scripts/controls.gd"))
    hud.set("build_tag", S9BuildIdentity.BUILD_TAG)
    overlay.add_child(hud)
    hud.visible = false
    var thumb_overlay: FareTouchHUD = FareTouchHUD.new()
    thumb_overlay.name = "FloatingJoystickHUD"
    thumb_overlay.router = mobile_input
    thumb_overlay.mouse_filter = Control.MOUSE_FILTER_IGNORE
    overlay.add_child(thumb_overlay)
    thumb_overlay.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)

func _setup_river_audio_and_micro() -> void:
    river_soundscape=RiverSoundscape.new()
    river_soundscape.name="RiverSoundscape"
    river_soundscape.profile=river_profile
    river_soundscape.flow=river_flow_field
    river_soundscape.camera=view_camera
    add_child(river_soundscape)
    river_micro=RiverMicroEffects.new()
    river_micro.name="RiverMicroEffects"
    river_micro.profile=river_profile
    river_micro.flow=river_flow_field
    river_micro.actor=player
    river_micro.mouse_water=mouse_water
    river_micro.height_sampler=Callable(self,"_height")
    add_child(river_micro)

func _setup_performance_probe() -> void:
    if DisplayServer.get_name()=="headless":
        return
    s8_probe=S8PerformanceProbe.new()
    s8_probe.name="S8PerformanceProbe"
    s8_probe.game=self
    add_child(s8_probe)

func _setup_water_fx() -> void:
    camera_water = UnderwaterCameraFX.new()
    camera_water.name = "UnderwaterCameraFX"
    camera_water.surface_profile = river_profile
    add_child(camera_water)
    ripple_pool = WaterRipplePool.new()
    ripple_pool.name = "WaterRipplePool"
    add_child(ripple_pool)

func _setup_wet_fur(imported: Node3D) -> void:
    # Shared transparent overlay follows the EXISTING skinned mesh; never
    # rewrite original material slots, rig weights, or UV coordinates.
    wet_fur_material = StandardMaterial3D.new()
    wet_fur_material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
    wet_fur_material.shading_mode = BaseMaterial3D.SHADING_MODE_PER_PIXEL
    wet_fur_material.albedo_color = Color(0.075,0.115,0.10,0.10)
    wet_fur_material.roughness = 0.27
    wet_fur_material.metallic = 0.0
    var meshes: Array[Node] = imported.find_children("*","MeshInstance3D",true,false)
    for child in meshes:
        var candidate: MeshInstance3D = child as MeshInstance3D
        if candidate != null and wet_meshes.size() < 4:
            wet_meshes.append(candidate)
    # All overlay draw calls disabled while fully dry.
    wet_overlay_active = false

func _update_fur_wetness() -> void:
    if wet_fur_material == null:
        return
    var damp: float = mouse_water.wetness
    var should_show: bool = damp > 0.02
    if should_show != wet_overlay_active:
        wet_overlay_active = should_show
        for m in wet_meshes:
            m.material_overlay = wet_fur_material if should_show else null
    if should_show and absf(damp-last_wet_value)>0.018:
        wet_fur_material.albedo_color = Color(0.075,0.115,0.10,0.115*damp)
        last_wet_value = damp

func _emit_water_ripples(delta: float) -> void:
    if ripple_pool == null or player == null:
        return
    if mouse_water.state == MouseWaterInteraction.DRY:
        if last_water_state != MouseWaterInteraction.DRY and river_profile.shore_distance(last_wet_point)<-0.005:
            ripple_pool.splash(last_wet_point,last_wet_height,0.31)
        ripple_time = 0.0
        last_water_state = MouseWaterInteraction.DRY
        return
    var body_point: Vector2 = Vector2(player.global_position.x,player.global_position.z)
    if river_profile.shore_distance(body_point)<-0.005:
        last_wet_point=body_point
        last_wet_height=mouse_water.water_y
    ripple_time -= delta
    var speed: float = Vector2(player.velocity.x,player.velocity.z).length()
    var first_contact: bool = last_water_state == MouseWaterInteraction.DRY or last_water_state != mouse_water.state
    if first_contact or (ripple_time <= 0.0 and speed > 0.12):
        var direction: Vector2 = Vector2(player.velocity.x,player.velocity.z).normalized()
        var point: Vector2 = body_point+direction*0.21
        if river_profile.shore_distance(point)>-0.03:
            point=body_point
        # Don't spawn a bright ring on the DRY shoreline from a moving paw.
        if river_profile.shore_distance(point)<-0.005:
            ripple_pool.splash(point,mouse_water.water_y,0.7 if mouse_water.state == MouseWaterInteraction.SWIMMING else 0.43)
        ripple_time = 0.38 if mouse_water.state == MouseWaterInteraction.SWIMMING else 0.56
    last_water_state = mouse_water.state

func _process(delta: float) -> void:
    var script_start_usec: int=Time.get_ticks_usec()
    elapsed += delta
    if OS.get_name()=="Android":
        _s9_poll_cpu_tasks()
    # Fixed-scene A/B mode is for stationary render testing only. Leaving
    # the source chunk automatically restores collision-safe streaming.
    if s9_fixed_scene and _current_chunk()!=s9_fixed_scene_center:
        s9_fixed_scene=false
    chunk_timer += delta
    if chunk_timer > 0.33:
        chunk_timer = 0.0
        if not s9_fixed_scene:
            _queue_chunks()
            if OS.get_name()=="Android":
                _s9_predictive_prefetch()
    lod_update_timer+=delta
    if lod_update_timer>0.40:
        lod_update_timer=0.0
        _update_chunk_lod()
    cache_write_timer+=delta
    # ResourceSaver on the scene thread blocked the reported phone up to 283ms.
    # Postpone Android writes until the mouse is stationary for 8 seconds.
    # Generated chunk data stays live in RAM in the meantime.
    var can_save: bool=queue.is_empty()
    if OS.get_name()=="Android":
        var horizontal_speed: float=Vector2(player.velocity.x,player.velocity.z).length() if player!=null else 0.0
        if horizontal_speed>0.15:
            cache_write_timer=0.0
        can_save=can_save and horizontal_speed<=0.15 and cache_write_timer>8.0
    else:
        can_save=can_save and cache_write_timer>1.1
    if can_save:
        cache_write_timer=0.0
        _save_one_cache_chunk()
    if not s9_fixed_scene:
        _advance_cosmetic_jobs()
    if not s9_fixed_scene and not queue.is_empty():
        var next: Vector2i = queue.pop_front()
        if not chunks.has(next) and _near(next):
            _add_chunk(next,OS.get_name()=="Android")
        else:
            s9_queue_requested_usec.erase(next)
    # New camera rig processes look independently at render-frame frequency.
    if camera_water != null:
        camera_water.update_camera(view_camera.global_position,delta)
    if river_soundscape != null:
        river_soundscape.update_water_sound(camera_water.submerged if camera_water != null else false,delta)
    if river_micro != null:
        river_micro.update_river(delta)
    _update_fur_wetness()
    _animate_mouse(delta)
    if hud != null:
        hud.set("joystick", stick)
        hud.set("stamina", stamina)
        hud.set("speed", Vector2(player.velocity.x, player.velocity.z).length())
        hud.set("chunk_count", chunks.size())
        hud.set("sprinting", running)
        hud.set("jumping", not player.is_on_floor() and mouse_water.state != MouseWaterInteraction.SWIMMING)
        hud.set("message",mouse_water.label())
        hud.set("rig_status", ("%dB ANIM" % rig.get_bone_count()) if mouse_animation != null and rig != null else ("BONES %d" % rig.get_bone_count() if rig != null else "STATIC"))
    last_process_work_ms=float(Time.get_ticks_usec()-script_start_usec)*0.001
    max_process_work_ms=maxf(max_process_work_ms,last_process_work_ms)

func _physics_process(delta: float) -> void:
    var script_start_usec: int=Time.get_ticks_usec()
    if player == null:
        return
    var raw_touch: Vector2 = mobile_input.movement()
    var axis: Vector2 = Vector2(raw_touch.x, -raw_touch.y)
    jump_buffer = mobile_input.consume_jump()
    var keys: Vector2 = Vector2.ZERO
    if Input.is_key_pressed(KEY_A) or Input.is_key_pressed(KEY_LEFT):
        keys.x -= 1.0
    if Input.is_key_pressed(KEY_D) or Input.is_key_pressed(KEY_RIGHT):
        keys.x += 1.0
    if Input.is_key_pressed(KEY_W) or Input.is_key_pressed(KEY_UP):
        keys.y += 1.0
    if Input.is_key_pressed(KEY_S) or Input.is_key_pressed(KEY_DOWN):
        keys.y -= 1.0
    if keys.length() > 0.01:
        axis = keys.normalized()
    var camera_yaw: float = mobile_camera_rig.yaw_angle
    var forward: Vector3 = Vector3(-sin(camera_yaw), 0.0, -cos(camera_yaw))
    var right: Vector3 = Vector3(cos(camera_yaw), 0.0, -sin(camera_yaw))
    var desired: Vector3 = right * axis.x + forward * axis.y
    if desired.length() > 1.0:
        desired = desired.normalized()
    mouse_water.update(river_profile,river_flow_field,player.global_position,delta)
    if river_soundscape != null:
        river_soundscape.notify_water_contact(mouse_water.state,mouse_water.water_y,player.global_position)
    var swimming: bool = mouse_water.state == MouseWaterInteraction.SWIMMING
    var wants_run: bool = not swimming and (axis.length() >= 0.90 or Input.is_key_pressed(KEY_SHIFT)) and desired.length() > 0.08 and stamina > 0.4
    running = wants_run
    stamina = clampf(stamina + (-18.0 if wants_run else (1.0 if swimming and desired.length()>0.08 else 12.0))*delta,0.0,100.0)
    # A midair tap cannot consume stamina without executing a jump.
    var jump_action: bool = jump_buffer and (swimming or player.is_on_floor()) and stamina >= (5.0 if swimming else 15.0)
    if jump_action:
        stamina -= 5.0 if swimming else 15.0
    mouse_water.apply_velocity(player,desired,wants_run,jump_action,delta,WALK_SPEED,RUN_SPEED,JUMP_SPEED)
    jump_buffer = false
    if desired.length() > 0.08:
        player.rotation.y = lerp_angle(player.rotation.y, atan2(-desired.x, -desired.z), minf(delta * 13.0, 1.0))
    player.move_and_slide()
    _emit_water_ripples(delta)
    if player.global_position.y < -18.0:
        player.global_position = Vector3(SPAWN_X, _height(SPAWN_X, SPAWN_Z) + SPAWN_HEIGHT_ABOVE_TERRAIN, SPAWN_Z)
        player.velocity = Vector3.ZERO
    last_physics_work_ms=float(Time.get_ticks_usec()-script_start_usec)*0.001
    max_physics_work_ms=maxf(max_physics_work_ms,last_physics_work_ms)

func _input(_event: InputEvent) -> void:
    # All touches are now owned by FareTouchInputRouter, independently.
    pass

func _stick_position(_pos: Vector2) -> void:
    # Old API retained only for external integrations; no legacy input handler uses it.
    pass

func _turn_camera(_amount: Vector2) -> void:
    # Camera rotation is handled in FareThirdPersonCamera._process().
    pass

func _update_camera(_delta: float) -> void:
    # SpringArm3D and camera follow run in FareThirdPersonCamera.
    pass

func _pose(name: String, axis: Vector3, angle: float) -> void:
    if rig == null:
        return
    var idx: int = rig.find_bone(name)
    if idx >= 0:
        var rest_axis: Vector3 = (rig.get_bone_global_rest(idx).basis.inverse() * axis).normalized()
        # Very small rotations avoid the silhouette collapse of previous V2/V3's giant procedural poses.
        rig.set_bone_pose_rotation(idx, Quaternion(rest_axis, angle))

func _animate_mouse(delta: float) -> void:
    if model_holder == null or player == null:
        return
    var horizontal_speed: float = Vector2(player.velocity.x, player.velocity.z).length()
    var moving: float = clampf(horizontal_speed / WALK_SPEED, 0.0, 1.0)
    phase += delta * (13.0 if running else 8.1) * moving
    var swimming: bool = mouse_water.state == MouseWaterInteraction.SWIMMING
    model_holder.position.y = -0.41 + (0.014*sin(phase*1.7) if swimming else 0.012*sin(phase*2.0)*moving)
    model_holder.rotation.x = lerpf(model_holder.rotation.x,-0.10 if swimming else 0.0,minf(delta*3.0,1.0))
    # Preserve the genuine 49-bone Blender action AND the corrective morph tracks.
    # Old handmade rotations bypassed corrective shapekeys and bent the abdomen.
    if mouse_animation != null:
        if moving > 0.10 or swimming:
            if not mouse_animation.is_playing():
                mouse_animation.play("MouseRig")
            mouse_animation.speed_scale = 0.54 if swimming else (1.5 if running else 0.80)
        elif mouse_animation.is_playing():
            mouse_animation.stop()
        return
    if rig == null:
        return
    var stride: float = 0.18 * moving
    var a: float = sin(phase)
    var b: float = sin(phase + PI)
    _pose("upper_arm.L", Vector3.RIGHT, stride * a)
    _pose("upper_arm.R", Vector3.RIGHT, stride * b)
    _pose("thigh.L", Vector3.RIGHT, stride * b)
    _pose("thigh.R", Vector3.RIGHT, stride * a)
    _pose("shin.L", Vector3.RIGHT, 0.08 * maxf(0.0, -b) * moving)
    _pose("shin.R", Vector3.RIGHT, 0.08 * maxf(0.0, -a) * moving)
    _pose("forearm.L", Vector3.RIGHT, 0.07 * maxf(0.0, -a) * moving)
    _pose("forearm.R", Vector3.RIGHT, 0.07 * maxf(0.0, -b) * moving)
    for i in range(1, 7):
        _pose("tail_%02d" % i, Vector3.UP, 0.04 * sin(elapsed * 1.8 - float(i) * 0.3))
    _pose("head", Vector3.UP, 0.012 * sin(elapsed * 2.1))

func _river_x(z: float) -> float:
    # Legacy helpers call this: always use the S1 shared profile now.
    return river_profile.center_x(z)

func _base_height(x: float, z: float) -> float:
    var valley: float = 2.0 + height_noise.get_noise_2d(x, z) * 2.5 + detail_noise.get_noise_2d(x, z) * 0.4
    var mountain_factor: float = smoothstep(30.0, 110.0, absf(x))
    var mountain: float = 12.0 * mountain_factor + pow(mountain_factor, 1.55) * (13.0 + absf(height_noise.get_noise_2d(x + 91.0, z)) * 20.0)
    return valley + mountain

func _height(x: float, z: float) -> float:
    var base_y: float=_base_height(x,z)
    # S8-B confirms no river deformation at |world x| > 45m.
    # Foliage placement and perimeter normals now skip this spline hot path.
    if absf(x)>45.0:
        return base_y
    return river_profile.terrain_height(x,z,base_y)

func _terrain_x_grid(chunk_x: float) -> PackedFloat32Array:
    # Perimeter vertices land on exact tile boundaries; fine steps only near
    # the river corridor, cheaper 1.4m ground elsewhere. The result depends
    # on world X, NEVER on load order or the camera position.
    var values: PackedFloat32Array = PackedFloat32Array([0.0])
    var local_x: float = 0.0
    while local_x < CELL - 0.0001:
        var world_x: float = chunk_x + local_x
        var step: float = 0.38 if absf(world_x) <= 22.0 else 1.42
        local_x = minf(CELL, local_x + step)
        values.append(local_x)
    return values

func _current_chunk() -> Vector2i:
    return Vector2i(floori(player.global_position.x / CELL), floori(player.global_position.z / CELL))

func _near(co: Vector2i) -> bool:
    var current: Vector2i = _current_chunk()
    return absi(current.x - co.x) <= RADIUS and absi(current.y - co.y) <= RADIUS

func _queue_chunks() -> void:
    var center: Vector2i=_current_chunk()
    # Clear outdated work immediately after turns and teleports. An outdated
    # queue entry must never hold up current/adjacent collision tiles.
    for i in range(queue.size()-1,-1,-1):
        var co: Vector2i=queue[i]
        if chunks.has(co) or maxi(absi(co.x-center.x),absi(co.y-center.y))>RADIUS:
            queue.remove_at(i)
            s9_queue_requested_usec.erase(co)
    for z in range(-RADIUS,RADIUS+1):
        for x in range(-RADIUS,RADIUS+1):
            var co: Vector2i=center+Vector2i(x,z)
            if not chunks.has(co) and not queue.has(co):
                queue.append(co)
                s9_queue_requested_usec[co]=Time.get_ticks_usec()
    var velocity: Vector2=Vector2(player.velocity.x,player.velocity.z)
    var predicted: Vector2i=Vector2i(
        floori((player.global_position.x+velocity.x*2.0)/CELL),
        floori((player.global_position.z+velocity.y*2.0)/CELL))
    # Inner 3x3 collision ring takes absolute precedence over the outer ring.
    # Within each safety class, predicted movement breaks ties, then stable
    # world-coordinate order prevents queue oscillation.
    queue.sort_custom(func(a: Vector2i,b: Vector2i) -> bool:
        var ad: int=maxi(absi(a.x-center.x),absi(a.y-center.y))
        var bd: int=maxi(absi(b.x-center.x),absi(b.y-center.y))
        if ad!=bd:
            return ad<bd
        var ahead_a: int=absi(a.x-predicted.x)+absi(a.y-predicted.y)
        var ahead_b: int=absi(b.x-predicted.x)+absi(b.y-predicted.y)
        if ahead_a!=ahead_b:
            return ahead_a<ahead_b
        if a.y!=b.y:
            return a.y<b.y
        return a.x<b.x)
    for key in chunks.keys():
        var co: Vector2i=key
        if maxi(absi(co.x-center.x),absi(co.y-center.y))>RADIUS:
            var part: Node3D=chunks[co]
            part.queue_free()
            chunks.erase(co)

func _s9_start_cpu_task(co: Vector2i, known_cache_miss: bool=false) -> bool:
    if not s9_worker_enabled:
        return false
    if s9_worker_tasks.has(co) or s9_worker_ready.has(co):
        return true
    if s9_worker_tasks.size()>=S9_MAX_CPU_WORKERS:
        return false
    if not known_cache_miss and (chunk_cache.has_pack(co) or chunk_cache.has_user(co)):
        return false
    var job: S9PureChunkData=S9PureChunkData.new()
    job.co=co
    var task_id: int=WorkerThreadPool.add_task(Callable(job,"build"),false,"Fare terrain river CPU")
    s9_worker_tasks[co]={"task_id":task_id,"job":job}
    s9_worker_started+=1
    return true

func _s9_poll_cpu_tasks() -> void:
    for key in s9_worker_tasks.keys():
        var co: Vector2i=key
        var ticket: Dictionary=s9_worker_tasks[co]
        var id: int=int(ticket["task_id"])
        if not WorkerThreadPool.is_task_completed(id):
            continue
        WorkerThreadPool.wait_for_task_completion(id)
        s9_worker_tasks.erase(co)
        s9_worker_finished+=1
        var job: S9PureChunkData=ticket["job"] as S9PureChunkData
        s9_worker_latest_cpu_ms=job.worker_elapsed_ms
        var center: Vector2i=_current_chunk()
        if not job.completed or maxi(absi(co.x-center.x),absi(co.y-center.y))>4:
            s9_worker_discarded+=1
            continue
        s9_worker_ready[co]=job
    # Bounded CPU buffer cache: prioritise chunks likely to become needed.
    while s9_worker_ready.size()>S9_MAX_READY_DATA:
        var center: Vector2i=_current_chunk()
        var evict: Vector2i=center
        var greatest: int=-1
        for key in s9_worker_ready.keys():
            var co: Vector2i=key
            var distance: int=absi(co.x-center.x)+absi(co.y-center.y)
            if distance>greatest:
                greatest=distance
                evict=co
        s9_worker_ready.erase(evict)
        s9_worker_discarded+=1

func _s9_predictive_prefetch() -> void:
    if not s9_worker_enabled or s9_fixed_scene:
        return
    if s9_worker_tasks.size()>=S9_MAX_CPU_WORKERS or s9_worker_ready.size()>=S9_MAX_READY_DATA:
        return
    if player==null:
        return
    var vel: Vector2=Vector2(player.velocity.x,player.velocity.z)
    if vel.length()<0.4:
        return
    var now: Vector2i=_current_chunk()
    var predicted_x: float=player.global_position.x+vel.x*3.0
    var predicted_z: float=player.global_position.z+vel.y*3.0
    var predicted: Vector2i=Vector2i(floori(predicted_x/CELL),floori(predicted_z/CELL))
    var candidates: Array[Dictionary]=[]
    for z in range(-3,4):
        for x in range(-3,4):
            if maxi(absi(x),absi(z))!=3:
                continue
            var co: Vector2i=now+Vector2i(x,z)
            if absi(co.x-predicted.x)>2 or absi(co.y-predicted.y)>2:
                continue
            if chunks.has(co) or s9_worker_tasks.has(co) or s9_worker_ready.has(co):
                continue
            if chunk_cache.has_pack(co) or chunk_cache.has_user(co):
                continue
            var priority: float=float(absi(co.x-predicted.x)+absi(co.y-predicted.y))*8.0+float(absi(x)+absi(z))*0.25
            candidates.append({"co":co,"priority":priority})
    candidates.sort_custom(func(a: Dictionary,b: Dictionary) -> bool:
        return float(a["priority"])<float(b["priority"]))
    for option in candidates:
        if s9_worker_tasks.size()>=S9_MAX_CPU_WORKERS:
            break
        _s9_start_cpu_task(option["co"])

func _s9_collision_urgent(co: Vector2i) -> bool:
    var center: Vector2i=_current_chunk()
    return maxi(absi(co.x-center.x),absi(co.y-center.y))<=1

func _exit_tree() -> void:
    # Every WorkerThreadPool task MUST be joined eventually.
    # Closing a scene may block while the two remaining CPU jobs terminate.
    for ticket in s9_worker_tasks.values():
        WorkerThreadPool.wait_for_task_completion(int(ticket["task_id"]))
    s9_worker_tasks.clear()
    s9_worker_ready.clear()

func _add_chunk(co: Vector2i, defer_details: bool=false) -> void:
    if chunks.has(co):
        return
    var started_usec: int=Time.get_ticks_usec()
    var queued_usec: int=int(s9_queue_requested_usec.get(co,started_usec))
    var phase_usec: int=Time.get_ticks_usec()
    var cached: Dictionary=chunk_cache.load_chunk(co)
    var prepared: S9PureChunkData=s9_worker_ready.get(co,null) as S9PureChunkData
    if cached.is_empty() and prepared==null and OS.get_name()=="Android" and s9_worker_enabled and not ChunkBakeCache.bypass_disk:
        # For outer two rings, do not block a frame on ~1s CPU generation.
        # Current + adjacent ring always use synchronous safety fallback
        # so teleport/fast travel never leaves a missing ground collider.
        if not _s9_collision_urgent(co):
            # Cache loader already verified files; on a corrupt v4 manifest
            # we MUST regenerate instead of trusting the has_user() file hint.
            _s9_start_cpu_task(co,true)
            if not queue.has(co):
                queue.append(co)
            s9_worker_deferred_requests+=1
            return
        s9_worker_collision_fallback+=1
    s9_queue_requested_usec.erase(co)
    s9_current_chunk_stages={}
    _record_chunk_stage("cache_read",phase_usec)
    var root: Node3D=Node3D.new()
    root.name="Chunk_%d_%d" % [co.x,co.y]
    root.position=Vector3(float(co.x)*CELL,0.0,float(co.y)*CELL)
    add_child(root)
    chunks[co]=root
    phase_usec=Time.get_ticks_usec()
    var mesh: ArrayMesh
    if cached.has("terrain"):
        mesh=cached["terrain"] as ArrayMesh
    elif prepared!=null:
        mesh=prepared.create_terrain_mesh()
        s9_worker_used+=1
        s9_worker_ready.erase(co)
    else:
        mesh=_generate_terrain_mesh(root)
    _record_chunk_stage("terrain_mesh",phase_usec)
    if cached.is_empty():
        chunk_cache_miss_count+=1
        pending_cache_writes.append(co)
    else:
        chunk_cache_hit_count+=1
    var instance: MeshInstance3D = MeshInstance3D.new()
    instance.name = "Terrain"
    instance.mesh = mesh
    instance.material_override = terrain_mat
    root.add_child(instance)
    phase_usec=Time.get_ticks_usec()
    var collider_body: StaticBody3D = StaticBody3D.new()
    collider_body.name = "TerrainCollider"
    collider_body.collision_layer = 1
    var terrain_collision: CollisionShape3D = CollisionShape3D.new()
    terrain_collision.name = "TerrainCollisionShape"
    terrain_collision.shape = cached["collision"] if cached.has("collision") else mesh.create_trimesh_shape()
    collider_body.add_child(terrain_collision)
    root.add_child(collider_body)
    _record_chunk_stage("collider",phase_usec)
    phase_usec=Time.get_ticks_usec()
    if defer_details:
        # Terrain and collision must be in SceneTree before this is resident.
        # The decorative job can lag behind without changing physics.
        cosmetic_jobs.append({"co":co,"stage":0,"state":{"cursor":0}})
    else:
        _trees(root,co)
        _grass(root,co)
    _record_chunk_stage("vegetation",phase_usec)
    phase_usec=Time.get_ticks_usec()
    # River water and obstructing boulders remain in the critical path.
    if co.x >= -1 and co.x <= 0:
        _water(root,co,cached,prepared)
        if not defer_details:
            var rocks_usec: int=Time.get_ticks_usec()
            _rocks(root,co)
            _record_chunk_stage("river_rocks",rocks_usec)
        var major_usec: int=Time.get_ticks_usec()
        _major_rocks(root,co)
        _record_chunk_stage("major_rocks",major_usec)
        if not defer_details and mobile_quality_level!=QUALITY_FAST:
            var mist_usec: int=Time.get_ticks_usec()
            _river_mist(root,co)
            _record_chunk_stage("river_mist",mist_usec)
    _record_chunk_stage("river_fx",phase_usec)
    phase_usec=Time.get_ticks_usec()
    _apply_chunk_lod(co,root)
    _record_chunk_stage("publish",phase_usec)
    last_chunk_load_ms=float(Time.get_ticks_usec()-started_usec)*0.001
    max_chunk_load_ms=maxf(max_chunk_load_ms,last_chunk_load_ms)
    s9_trace.record_chunk(co,str(cached.get("source","generated")),
        float(started_usec-queued_usec)*0.001,last_chunk_load_ms,
        s9_current_chunk_stages,mobile_quality_level,
        player.global_position if player!=null else Vector3.ZERO)

func _advance_cosmetic_jobs() -> void:
    var start_usec: int=Time.get_ticks_usec()
    while not cosmetic_jobs.is_empty():
        var job: Dictionary=cosmetic_jobs.pop_front()
        var co: Vector2i=job["co"]
        if not chunks.has(co):
            # Old chunk was evicted before decoration. Never attach stale work.
            if Time.get_ticks_usec()-start_usec>=S9_COSMETIC_BUDGET_US:
                break
            continue
        var root: Node3D=chunks[co]
        var stage: int=int(job["stage"])
        var state: Dictionary=job["state"]
        var phase_usec: int=Time.get_ticks_usec()
        var finished: bool=true
        var label: String=""
        match stage:
            0:
                label="trees"
                finished=_trees(root,co,state)
            1:
                label="grass"
                finished=_grass(root,co,state)
            2:
                label="river_rocks"
                if co.x>=-1 and co.x<=0:
                    finished=_rocks(root,co,state)
            3:
                label="river_mist"
                if co.x>=-1 and co.x<=0 and mobile_quality_level!=QUALITY_FAST and not root.has_node("NearRiverMist"):
                    finished=_river_mist(root,co,state)
            _:
                finished=true
        var phase_ms: float=float(Time.get_ticks_usec()-phase_usec)*0.001
        cosmetic_phase_peak_ms[label]=maxf(float(cosmetic_phase_peak_ms.get(label,0.0)),phase_ms)
        if finished:
            job["stage"]=stage+1
            job["state"]={"cursor":0}
            _apply_chunk_lod(co,root)
        else:
            job["state"]=state
        if int(job["stage"])<=3:
            cosmetic_jobs.append(job)
        else:
            cosmetic_completed_chunks+=1
        if Time.get_ticks_usec()-start_usec>=S9_COSMETIC_BUDGET_US:
            break

func _cosmetic_rng(state: Dictionary, seed_value: int) -> RandomNumberGenerator:
    if state.has("rng"):
        return state["rng"] as RandomNumberGenerator
    var rng: RandomNumberGenerator=RandomNumberGenerator.new()
    rng.seed=seed_value
    if not state.is_empty():
        state["rng"]=rng
    return rng

func _apply_chunk_lod(co: Vector2i, chunk: Node3D) -> void:
    if player == null:
        return
    var center: Vector2 = Vector2(float(co.x)*CELL+CELL*0.5,float(co.y)*CELL+CELL*0.5)
    var distance: float = Vector2(player.global_position.x,player.global_position.z).distance_to(center)
    var river: MeshInstance3D = chunk.get_node_or_null("FlowingWater") as MeshInstance3D
    if river != null:
        var low: bool = bool(river.get_meta("water_lite",false))
        var should_use_lite: bool=mobile_quality_level==QUALITY_FAST or distance>(56.0 if low else 66.0)
        if low!=should_use_lite:
            river.material_override=river.get_meta("low_water_material" if should_use_lite else "high_water_material")
            river.set_meta("water_lite",should_use_lite)
    var ground: MeshInstance3D=chunk.get_node_or_null("Terrain") as MeshInstance3D
    if ground!=null:
        var desired_ground: ShaderMaterial=terrain_lite_mat if mobile_quality_level==QUALITY_FAST else terrain_mat
        if ground.material_override!=desired_ground:
            ground.material_override=desired_ground
    var mist: MultiMeshInstance3D=chunk.get_node_or_null("NearRiverMist") as MultiMeshInstance3D
    if mist!=null:
        mist.visible=mobile_quality_level!=QUALITY_FAST
    var pines: MultiMeshInstance3D = chunk.get_node_or_null("Pines") as MultiMeshInstance3D
    if pines != null:
        var active: bool = pines.cast_shadow == GeometryInstance3D.SHADOW_CASTING_SETTING_ON
        var enable: bool = mobile_quality_level!=QUALITY_FAST and distance<(70.0 if active else 55.0)
        var desired_shadow: GeometryInstance3D.ShadowCastingSetting=GeometryInstance3D.SHADOW_CASTING_SETTING_ON if enable else GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
        if pines.cast_shadow!=desired_shadow:
            pines.cast_shadow=desired_shadow

func _update_chunk_lod() -> void:
    for co in chunks.keys():
        _apply_chunk_lod(co,chunks[co])

func _save_one_cache_chunk() -> void:
    while not pending_cache_writes.is_empty():
        var co: Vector2i = pending_cache_writes.pop_front()
        if chunks.has(co):
            var begin_usec: int=Time.get_ticks_usec()
            var ok: bool=chunk_cache.save_chunk(co,chunks[co],false)
            var took_ms: float=float(Time.get_ticks_usec()-begin_usec)*0.001
            max_cache_save_ms=maxf(max_cache_save_ms,took_ms)
            if ok:
                cache_saves+=1
            break

func _water(root: Node3D, co: Vector2i, cached: Dictionary = {}, prepared: S9PureChunkData = null) -> void:
    var phase_usec: int=Time.get_ticks_usec()
    var reuse: Dictionary=water_resource_cache.get(co,{})
    var water_mesh: ArrayMesh
    if not reuse.is_empty():
        water_mesh=reuse["mesh"] as ArrayMesh
    else:
        if cached.has("water"):
            water_mesh=cached["water"] as ArrayMesh
        elif prepared!=null and not prepared.water_arrays.is_empty():
            water_mesh=prepared.create_water_mesh()
        else:
            water_mesh=river_surface_builder.build_chunk(river_profile,co,CELL)
    _record_chunk_stage("water_mesh",phase_usec)
    if water_mesh==null or water_mesh.get_surface_count()==0:
        return
    var water_instance: MeshInstance3D=MeshInstance3D.new()
    water_instance.name="FlowingWater"
    water_instance.mesh=water_mesh
    var chunk_material: ShaderMaterial
    var lite: ShaderMaterial
    var atlas: Image
    if not reuse.is_empty():
        water_resource_cache_hits+=1
        water_resource_cache_lru.erase(co)
        water_resource_cache_lru.append(co)
        atlas=reuse["flow_image"] as Image
        chunk_material=reuse["high"] as ShaderMaterial
        lite=reuse["low"] as ShaderMaterial
        # Scene lighting can change while a chunk is out of the 5x5 RAM window.
        atmosphere.configure_river(chunk_material)
        atmosphere.configure_river(lite)
    else:
        water_resource_cache_misses+=1
        var origin: Vector2=Vector2(root.position.x,root.position.z)
        phase_usec=Time.get_ticks_usec()
        # V2 atlas is the single flow source for physics and visual shader.
        if prepared!=null and not prepared.flow_rgba8.is_empty():
            atlas=prepared.create_flow_image()
        else:
            atlas=river_flow_atlas_cache.fetch(co,river_profile,river_flow_field,CELL)
        _record_chunk_stage("flow_atlas_fetch",phase_usec)
        phase_usec=Time.get_ticks_usec()
        var atlas_texture: Texture2D=ImageTexture.create_from_image(atlas)
        # Wall time of CPU submit, NOT proven GPU completion time.
        _record_chunk_stage("water_texture_submit",phase_usec)
        phase_usec=Time.get_ticks_usec()
        chunk_material=water_mat.duplicate() as ShaderMaterial
        chunk_material.set_shader_parameter("flow_atlas",atlas_texture)
        chunk_material.set_shader_parameter("chunk_origin",origin)
        chunk_material.set_shader_parameter("chunk_size",CELL)
        chunk_material.set_shader_parameter("wave_map",wave_texture)
        water_quality.configure(chunk_material,WaterQualitySettings.BALANCED)
        atmosphere.configure_river(chunk_material)
        lite=water_lite_mat.duplicate() as ShaderMaterial
        lite.set_shader_parameter("flow_atlas",atlas_texture)
        lite.set_shader_parameter("wave_map",wave_texture)
        lite.set_shader_parameter("chunk_origin",origin)
        lite.set_shader_parameter("chunk_size",CELL)
        atmosphere.configure_river(lite)
        _record_chunk_stage("water_materials",phase_usec)
        water_resource_cache[co]={
            "mesh":water_mesh,"flow_image":atlas,"flow_texture":atlas_texture,
            "high":chunk_material,"low":lite
        }
        water_resource_cache_lru.append(co)
        while water_resource_cache_lru.size()>WATER_RESOURCE_CACHE_LIMIT:
            var expired: Vector2i=water_resource_cache_lru.pop_front()
            water_resource_cache.erase(expired)
    water_instance.set_meta("flow_image",atlas)
    water_instance.set_meta("high_water_material",chunk_material)
    water_instance.set_meta("low_water_material",lite)
    water_instance.material_override=chunk_material
    water_instance.cast_shadow=GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
    phase_usec=Time.get_ticks_usec()
    root.add_child(water_instance)
    _record_chunk_stage("water_scene_attach",phase_usec)

func _river_mist(root: Node3D, co: Vector2i, state: Dictionary={}) -> bool:
    # Keep RNG state and exact spatial formula across multiple frames.
    var staged: bool=not state.is_empty()
    var random: RandomNumberGenerator=_cosmetic_rng(state,88973+(co.x*29791+co.y*999983)*19)
    var transforms: Array[Transform3D]=[]
    if staged and state.has("transforms"):
        transforms=state["transforms"]
    var begin: int=int(state.get("cursor",0)) if staged else 0
    var until: int=mini(begin+1,22) if staged else 22
    var origin_x: float=root.position.x
    var origin_z: float=root.position.z
    for i in range(begin,until):
        var z: float=origin_z+random.randf_range(0.7,CELL-0.7)
        var banks: Vector2=river_profile.banks_at_z(z)
        var low_x: float=maxf(banks.x+0.12,origin_x+0.12)
        var high_x: float=minf(banks.y-0.12,origin_x+CELL-0.12)
        if high_x-low_x<0.35:
            continue
        var x: float=random.randf_range(low_x,high_x)
        var height: float=river_profile.surface_height(z)+random.randf_range(0.12,0.32)
        var radius: float=random.randf_range(0.8,1.8)
        transforms.append(Transform3D(Basis(Vector3.UP,random.randf_range(0.0,TAU)).scaled(Vector3(radius,1.0,radius)),Vector3(x-origin_x,height,z-origin_z)))
    if staged:
        state["cursor"]=until
        state["transforms"]=transforms
        if until<22:
            return false
    if transforms.is_empty():
        return true
    var quad: PlaneMesh=PlaneMesh.new()
    quad.size=Vector2(3.6,2.0)
    quad.material=atmosphere.mist_material
    var mm: MultiMesh=MultiMesh.new()
    mm.transform_format=MultiMesh.TRANSFORM_3D
    mm.mesh=quad
    mm.instance_count=transforms.size()
    for i in range(transforms.size()):
        mm.set_instance_transform(i,transforms[i])
    var instance: MultiMeshInstance3D=MultiMeshInstance3D.new()
    instance.name="NearRiverMist"
    instance.multimesh=mm
    instance.cast_shadow=GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
    instance.visibility_range_end=42.0
    root.add_child(instance)
    return true

func _pine_mesh() -> Mesh:
    var st: SurfaceTool = SurfaceTool.new()
    st.begin(Mesh.PRIMITIVE_TRIANGLES)
    var bark: Color = Color(0.36, 0.27, 0.18)
    var needles: Color = Color(0.15, 0.29, 0.20)
    for i in range(7):
        var a: float = float(i) * TAU / 7.0
        var b: float = float(i + 1) * TAU / 7.0
        _tri(st, Vector3(cos(a) * 0.13, 0.0, sin(a) * 0.13), Vector3(cos(b) * 0.13, 0.0, sin(b) * 0.13), Vector3(cos(a) * 0.11, 2.0, sin(a) * 0.11), bark)
        _tri(st, Vector3(cos(a) * 0.11, 2.0, sin(a) * 0.11), Vector3(cos(b) * 0.13, 0.0, sin(b) * 0.13), Vector3(cos(b) * 0.11, 2.0, sin(b) * 0.11), bark)
    for layer in range(3):
        var bot: float = 0.32 + float(layer) * 0.57
        var top: float = 2.5 + float(layer) * 0.35
        var radius: float = 1.13 - float(layer) * 0.26
        var green: Color = needles.lightened(float(layer) * 0.055)
        for k in range(8):
            var a: float = float(k) * TAU / 8.0
            var b: float = float(k + 1) * TAU / 8.0
            _tri(st, Vector3(cos(a) * radius, bot, sin(a) * radius), Vector3(cos(b) * radius, bot, sin(b) * radius), Vector3(0.0, top, 0.0), green)
    st.generate_normals()
    var mesh: ArrayMesh = st.commit()
    var material: StandardMaterial3D = StandardMaterial3D.new()
    material.vertex_color_use_as_albedo = true
    material.cull_mode = BaseMaterial3D.CULL_DISABLED
    material.roughness = 1.0
    mesh.surface_set_material(0, material)
    return mesh

func _grass_mesh() -> Mesh:
    var st: SurfaceTool = SurfaceTool.new()
    st.begin(Mesh.PRIMITIVE_TRIANGLES)
    var green: Color = Color(0.29, 0.48, 0.22)
    for i in range(3):
        var a: float = float(i) * PI / 3.0
        var dir: Vector3 = Vector3(cos(a), 0.0, sin(a))
        _tri(st, dir * -0.15, dir * 0.15, Vector3(0.0, 0.29, 0.0), green)
    st.generate_normals()
    var mesh: ArrayMesh = st.commit()
    var mat: StandardMaterial3D = StandardMaterial3D.new()
    mat.vertex_color_use_as_albedo = true
    mat.cull_mode = BaseMaterial3D.CULL_DISABLED
    mesh.surface_set_material(0, mat)
    return mesh

func _stone_mesh() -> Mesh:
    var mesh: SphereMesh = SphereMesh.new()
    mesh.radius = 0.4
    mesh.height = 0.55
    mesh.radial_segments = 7
    mesh.rings = 4
    var mat: StandardMaterial3D = StandardMaterial3D.new()
    mat.albedo_color = Color(0.43, 0.43, 0.39)
    mat.roughness = 0.9
    mesh.material = mat
    return mesh

func _tri(st: SurfaceTool, a: Vector3, b: Vector3, c: Vector3, color: Color) -> void:
    st.set_color(color)
    st.add_vertex(a)
    st.set_color(color)
    st.add_vertex(b)
    st.set_color(color)
    st.add_vertex(c)

func _trees(root: Node3D, co: Vector2i, state: Dictionary={}) -> bool:
    var staged: bool=not state.is_empty()
    var rng: RandomNumberGenerator=_cosmetic_rng(state,300001+(co.x*1640531513+co.y*805459861)*13)
    var xforms: Array[Transform3D]=[]
    if staged and state.has("xforms"):
        xforms=state["xforms"]
    var begin: int=int(state.get("cursor",0)) if staged else 0
    var until: int=mini(begin+6,46) if staged else 46
    for i in range(begin,until):
        var x: float=rng.randf_range(0.0,CELL)
        var z: float=rng.randf_range(0.0,CELL)
        var wx: float=root.position.x+x
        var wz: float=root.position.z+z
        var y: float=_height(wx,wz)
        var near_bank: bool=absf(wx)<=45.0 and river_profile.shore_distance(Vector2(wx,wz))<6.0
        if near_bank or y>28.0:
            continue
        if Vector2(wx-SPAWN_X,wz-SPAWN_Z).length()<7.0:
            continue
        var scale: float=rng.randf_range(0.76,1.66)
        var basis: Basis=Basis(Vector3.UP,rng.randf_range(0.0,TAU)).scaled(Vector3(scale,scale*rng.randf_range(0.9,1.2),scale))
        xforms.append(Transform3D(basis,Vector3(x,y-0.05,z)))
    if staged:
        state["cursor"]=until
        state["xforms"]=xforms
        if until<46:
            return false
    _multimesh(root,pine_mesh,"Pines",xforms)
    return true

func _grass(root: Node3D, co: Vector2i, state: Dictionary={}) -> bool:
    var staged: bool=not state.is_empty()
    var rng: RandomNumberGenerator=_cosmetic_rng(state,105533+(co.x*122949829+co.y*1000003)*7)
    var xforms: Array[Transform3D]=[]
    if staged and state.has("xforms"):
        xforms=state["xforms"]
    var begin: int=int(state.get("cursor",0)) if staged else 0
    var until: int=mini(begin+15,150) if staged else 150
    for i in range(begin,until):
        var x: float=rng.randf_range(0.0,CELL)
        var z: float=rng.randf_range(0.0,CELL)
        var wx: float=root.position.x+x
        var wz: float=root.position.z+z
        var y: float=_height(wx,wz)
        var near_bank: bool=absf(wx)<=45.0 and river_profile.shore_distance(Vector2(wx,wz))<2.4
        if near_bank or y>18.0:
            continue
        var size: float=rng.randf_range(0.65,1.45)
        xforms.append(Transform3D(Basis(Vector3.UP,rng.randf_range(0.0,TAU)).scaled(Vector3(size,size,size)),Vector3(x,y+0.015,z)))
    if staged:
        state["cursor"]=until
        state["xforms"]=xforms
        if until<150:
            return false
    _multimesh(root,grass_mesh,"Grass",xforms)
    return true

func _rocks(root: Node3D, co: Vector2i, state: Dictionary={}) -> bool:
    # Small, non-physical stones are computed incrementally, with identical
    # per-coordinate RNG sequence and original shader/geometry.
    var staged: bool=not state.is_empty()
    var rng: RandomNumberGenerator=_cosmetic_rng(state,80333+(co.x*528319+co.y*851111)*3)
    var pebbles: Array[Transform3D]=[]
    var cobbles: Array[Transform3D]=[]
    if staged and state.has("pebbles"):
        pebbles=state["pebbles"]
        cobbles=state["cobbles"]
    var begin: int=int(state.get("cursor",0)) if staged else 0
    var until: int=mini(begin+14,280) if staged else 280
    for i in range(begin,until):
        var x: float=rng.randf_range(0.0,CELL)
        var z: float=rng.randf_range(0.0,CELL)
        var wx: float=root.position.x+x
        var wz: float=root.position.z+z
        var pos: Vector2=Vector2(wx,wz)
        var river: Dictionary=river_profile.sample(pos)
        var sediment: Dictionary=shore_substrate.sample(river,pos)
        var sdf: float=float(river["shore_sdf"])
        if sdf>5.5 or sdf< -4.5:
            continue
        if rng.randf()>float(sediment["stone_density"]):
            continue
        var y: float=_height(wx,wz)
        var spin: float=rng.randf_range(0.0,TAU)
        var basis: Basis=Basis(Vector3.UP,spin)
        if rng.randf()<0.75:
            var size: float=rng.randf_range(0.08,0.27)
            pebbles.append(Transform3D(basis.scaled(Vector3(size*1.45,size*0.47,size)),Vector3(x,y+size*0.10,z)))
        else:
            var size: float=rng.randf_range(0.27,0.78)
            cobbles.append(Transform3D(basis.scaled(Vector3(size*1.20,size*0.55,size)),Vector3(x,y+size*0.18,z)))
    if staged:
        state["cursor"]=until
        state["pebbles"]=pebbles
        state["cobbles"]=cobbles
        if until<280:
            return false
    _multimesh(root,pebble_mesh,"FinePebbles",pebbles)
    _multimesh(root,pebble_mesh,"Cobbles",cobbles)
    return true

func _major_rocks(root: Node3D, co: Vector2i) -> void:
    # Same RiverObstacles contract is sampled in the flow atlas and used to
    # draw and collide the visible rocks. No invisible random foam sources.
    for rock in river_obstacles.in_chunk(co,CELL,river_profile):
        var p: Vector2 = rock["xz"]
        var r: float = float(rock["radius"])
        var local_xz: Vector2 = p-Vector2(root.position.x,root.position.z)
        var body: StaticBody3D = StaticBody3D.new()
        body.name = "RiverBoulder_%d" % int(rock["index"])
        body.collision_layer = 1
        body.position = Vector3(local_xz.x,_height(p.x,p.y)+r*0.34,local_xz.y)
        var rock_visual: MeshInstance3D = MeshInstance3D.new()
        rock_visual.name = "Stone"
        rock_visual.mesh = pebble_mesh
        rock_visual.scale = Vector3(r*1.95,r*2.6,r*1.85)
        rock_visual.rotation.y = float(rock["index"])*1.13
        body.add_child(rock_visual)
        var shape_node: CollisionShape3D = CollisionShape3D.new()
        var shape: SphereShape3D = SphereShape3D.new()
        shape.radius = r*0.67
        shape_node.shape = shape
        body.add_child(shape_node)
        root.add_child(body)

func _multimesh(root: Node3D, source: Mesh, label: String, xforms: Array[Transform3D]) -> void:
    if xforms.is_empty():
        return
    var mm: MultiMesh = MultiMesh.new()
    mm.transform_format = MultiMesh.TRANSFORM_3D
    mm.mesh = source
    mm.instance_count = xforms.size()
    for i in range(xforms.size()):
        mm.set_instance_transform(i, xforms[i])
    var instance: MultiMeshInstance3D = MultiMeshInstance3D.new()
    instance.name = label
    instance.multimesh = mm
    instance.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON if label == "Pines" else GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
    if label == "Grass":
        instance.visibility_range_end = 62.0
    elif label == "FinePebbles":
        instance.visibility_range_end = 38.0
    elif label == "Cobbles":
        instance.visibility_range_end = 55.0
    root.add_child(instance)

func _generate_terrain_mesh(root: Node3D) -> ArrayMesh:
    var verts: PackedVector3Array = PackedVector3Array()
    var normals: PackedVector3Array = PackedVector3Array()
    var uv: PackedVector2Array = PackedVector2Array()
    var uv2: PackedVector2Array = PackedVector2Array()
    var colors: PackedColorArray = PackedColorArray()
    var indices: PackedInt32Array = PackedInt32Array()
    var x_grid: PackedFloat32Array = _terrain_x_grid(root.position.x)
    var columns: int = x_grid.size()
    var rows: int = GRID + 1
    var dz: float = CELL / float(GRID)
    # Generate color + height using ONE RiverProfile sample per vertex.
    # Approximate smooth interior normals from neighboring vertices rather
    # than calling the expensive spline sampler four more times per vertex.
    for iz in range(rows):
        for ix in range(columns):
            var lx: float = x_grid[ix]
            var lz: float = float(iz) * dz
            var wx: float = root.position.x + lx
            var wz: float = root.position.z + lz
            var base_y: float=_base_height(wx,wz)
            if absf(wx)>45.0:
                # >45m is beyond the maximum possible river/soil transition.
                # Preserve EXACT old geomorphology/forest material formula,
                # skip dozens of spline/SDF trig operations per distant vertex.
                verts.append(Vector3(lx,base_y,lz))
                uv.append(Vector2(wx,wz)*0.1)
                uv2.append(Vector2.ZERO)
                var macro: float=shore_substrate.macro.get_noise_2d(wx,wz)
                var forest_cover: float=clampf(0.31+0.15*macro,0.0,0.52)
                colors.append(Color(0.0,0.0,0.0,forest_cover))
            else:
                var info: Dictionary=river_profile.ground_sample(Vector2(wx,wz),base_y)
                verts.append(Vector3(lx,float(info["terrain_y"]),lz))
                uv.append(Vector2(wx,wz)*0.1)
                uv2.append(Vector2(maxf(0.0,float(info["depth"])),0.0))
                var sediment: Dictionary=shore_substrate.sample(info,Vector2(wx,wz))
                colors.append(Color(float(sediment["gravel"]),float(sediment["wetness"]),float(sediment["silt"]),float(sediment["forest"])))
    for iz in range(rows):
        for ix in range(columns):
            var ix0: int = maxi(ix - 1, 0)
            var ix1: int = mini(ix + 1, columns - 1)
            var iz0: int = maxi(iz - 1, 0)
            var iz1: int = mini(iz + 1, rows - 1)
            var dx_vec: Vector3 = verts[iz * columns + ix1] - verts[iz * columns + ix0]
            var dz_vec: Vector3 = verts[iz1 * columns + ix] - verts[iz0 * columns + ix]
            var n: Vector3 = dz_vec.cross(dx_vec).normalized()
            if ix == 0 or ix == columns - 1 or iz == 0 or iz == rows - 1:
                # Use identical world-space finite differences for neighboring
                # chunks so perimeter normal interpolation has no visible seam.
                var v: Vector3 = verts[iz * columns + ix]
                var wx: float = root.position.x + v.x
                var wz: float = root.position.z + v.z
                var slope_x: float = _height(wx + 0.2, wz) - _height(wx - 0.2, wz)
                var slope_z: float = _height(wx, wz + 0.2) - _height(wx, wz - 0.2)
                n = Vector3(-slope_x, 0.4, -slope_z).normalized()
            normals.append(n)
            var metadata: Vector2 = uv2[iz*columns+ix]
            uv2[iz*columns+ix] = Vector2(metadata.x,clampf(0.97-0.10*(1.0-n.y),0.84,1.0))
    for iz in range(GRID):
        for ix in range(columns - 1):
            var a: int = iz * columns + ix
            # Avoid allocating a temporary PackedInt32Array per quad.
            indices.append(a)
            indices.append(a+1)
            indices.append(a+columns)
            indices.append(a+1)
            indices.append(a+columns+1)
            indices.append(a+columns)
    var arrays: Array = []
    arrays.resize(Mesh.ARRAY_MAX)
    arrays[Mesh.ARRAY_VERTEX] = verts
    arrays[Mesh.ARRAY_NORMAL] = normals
    arrays[Mesh.ARRAY_TEX_UV] = uv
    arrays[Mesh.ARRAY_TEX_UV2] = uv2
    arrays[Mesh.ARRAY_COLOR] = colors
    arrays[Mesh.ARRAY_INDEX] = indices
    var mesh: ArrayMesh = ArrayMesh.new()
    mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
    return mesh
