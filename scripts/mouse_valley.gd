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

var river_profile: RiverProfile = RiverProfile.new()
var river_surface_builder: RiverSurfaceBuilder = RiverSurfaceBuilder.new()
var shore_substrate: ShoreSubstrate = ShoreSubstrate.new()
var river_flow_field: RiverFlowField = RiverFlowField.new()
var river_obstacles: RiverObstacles = RiverObstacles.new()
var height_noise: FastNoiseLite = FastNoiseLite.new()
var detail_noise: FastNoiseLite = FastNoiseLite.new()
var player: CharacterBody3D
var model_holder: Node3D
var rig: Skeleton3D
var mouse_animation: AnimationPlayer
var view_camera: Camera3D
var hud: Control
var terrain_mat: ShaderMaterial
var water_mat: ShaderMaterial
var pine_mesh: Mesh
var grass_mesh: Mesh
var pebble_mesh: Mesh
var chunks: Dictionary = {}
var queue: Array[Vector2i] = []
var chunk_timer: float = 0.0
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
    pine_mesh = _pine_mesh()
    grass_mesh = _grass_mesh()
    pebble_mesh = _stone_mesh()
    _create_actor()
    _create_camera()
    _create_hud()
    # Build 3x3 chunks before the first frame; stream the outer ring later.
    var center: Vector2i = _current_chunk()
    for cz in range(-1, 2):
        for cx in range(-1, 2):
            _add_chunk(center + Vector2i(cx, cz))
    _queue_chunks()

func _environment() -> void:
    var sun: DirectionalLight3D = DirectionalLight3D.new()
    sun.rotation_degrees = Vector3(-54.0, -30.0, 0.0)
    sun.light_energy = 1.15
    sun.light_color = Color(1.0, 0.96, 0.85)
    sun.shadow_enabled = true
    sun.directional_shadow_max_distance = 70.0
    add_child(sun)
    var env_node: WorldEnvironment = WorldEnvironment.new()
    var env: Environment = Environment.new()
    env.background_mode = Environment.BG_COLOR
    env.background_color = Color(0.58, 0.70, 0.78)
    env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
    env.ambient_light_color = Color(0.70, 0.79, 0.79)
    env.ambient_light_energy = 0.45
    env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
    env.fog_enabled = true
    env.fog_light_color = Color(0.57, 0.67, 0.74)
    env.fog_light_energy = 0.6
    env.fog_density = 0.0021
    env.fog_height_density = 0.0
    env_node.environment = env
    add_child(env_node)

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
    water_mat = ShaderMaterial.new()
    water_mat.shader = load("res://shaders/river.gdshader") as Shader

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
    view_camera = Camera3D.new()
    view_camera.name = "ThirdPersonCamera"
    view_camera.current = true
    view_camera.fov = 65.0
    view_camera.near = 0.055
    view_camera.far = 205.0
    add_child(view_camera)
    _update_camera(1.0)

func _create_hud() -> void:
    var overlay: CanvasLayer = CanvasLayer.new()
    overlay.layer = 10
    add_child(overlay)
    hud = Control.new()
    hud.set_script(load("res://scripts/controls.gd"))
    overlay.add_child(hud)

func _process(delta: float) -> void:
    elapsed += delta
    chunk_timer += delta
    if chunk_timer > 0.33:
        chunk_timer = 0.0
        _queue_chunks()
    if not queue.is_empty():
        var next: Vector2i = queue.pop_front()
        if not chunks.has(next) and _near(next):
            _add_chunk(next)
    _update_camera(delta)
    _animate_mouse(delta)
    if hud != null:
        hud.set("joystick", stick)
        hud.set("stamina", stamina)
        hud.set("speed", Vector2(player.velocity.x, player.velocity.z).length())
        hud.set("chunk_count", chunks.size())
        hud.set("sprinting", running)
        hud.set("jumping", not player.is_on_floor())
        hud.set("rig_status", ("%dB ANIM" % rig.get_bone_count()) if mouse_animation != null and rig != null else ("BONES %d" % rig.get_bone_count() if rig != null else "STATIC"))

func _physics_process(delta: float) -> void:
    if player == null:
        return
    var axis: Vector2 = stick
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
    var forward: Vector3 = Vector3(-sin(look_yaw), 0.0, -cos(look_yaw))
    var right: Vector3 = Vector3(cos(look_yaw), 0.0, -sin(look_yaw))
    var desired: Vector3 = right * axis.x + forward * axis.y
    if desired.length() > 1.0:
        desired = desired.normalized()
    var wants_run: bool = (run_pointer >= 0 or mouse_action == "run" or Input.is_key_pressed(KEY_SHIFT)) and desired.length() > 0.08 and stamina > 0.4
    running = wants_run
    stamina = clampf(stamina + (-18.0 if wants_run else 12.0) * delta, 0.0, 100.0)
    var target: Vector3 = desired * (RUN_SPEED if wants_run else WALK_SPEED)
    var acceleration: float = minf(1.0, delta * (10.0 if player.is_on_floor() else 4.0))
    player.velocity.x = lerpf(player.velocity.x, target.x, acceleration)
    player.velocity.z = lerpf(player.velocity.z, target.z, acceleration)
    if player.is_on_floor():
        if player.velocity.y < 0.0:
            player.velocity.y = -0.1
        if jump_buffer and stamina >= 15.0:
            player.velocity.y = JUMP_SPEED
            stamina -= 15.0
    else:
        player.velocity.y -= 13.0 * delta
    jump_buffer = false
    if desired.length() > 0.08:
        player.rotation.y = lerp_angle(player.rotation.y, atan2(-desired.x, -desired.z), minf(delta * 13.0, 1.0))
    player.move_and_slide()
    if player.global_position.y < -18.0:
        player.global_position = Vector3(SPAWN_X, _height(SPAWN_X, SPAWN_Z) + SPAWN_HEIGHT_ABOVE_TERRAIN, SPAWN_Z)
        player.velocity = Vector3.ZERO

func _input(event: InputEvent) -> void:
    if hud == null:
        return
    if event is InputEventScreenTouch:
        var touch: InputEventScreenTouch = event as InputEventScreenTouch
        if touch.pressed:
            if stick_pointer < 0 and touch.position.distance_to(hud.call("stick_center")) < float(hud.call("stick_radius")) * 1.9:
                stick_pointer = touch.index
                _stick_position(touch.position)
            elif touch.position.distance_to(hud.call("jump_center")) < float(hud.call("button_radius")) * 1.6:
                jump_pointer = touch.index
                jump_buffer = true
            elif touch.position.distance_to(hud.call("run_center")) < float(hud.call("button_radius")) * 1.6:
                run_pointer = touch.index
            elif look_pointer < 0:
                look_pointer = touch.index
        else:
            if touch.index == stick_pointer:
                stick_pointer = -1
                stick = Vector2.ZERO
            if touch.index == run_pointer:
                run_pointer = -1
            if touch.index == jump_pointer:
                jump_pointer = -1
            if touch.index == look_pointer:
                look_pointer = -1
    elif event is InputEventScreenDrag:
        var drag: InputEventScreenDrag = event as InputEventScreenDrag
        if drag.index == stick_pointer:
            _stick_position(drag.position)
        elif drag.index == look_pointer:
            _turn_camera(drag.relative)
    elif event is InputEventMouseButton:
        var click: InputEventMouseButton = event as InputEventMouseButton
        if click.button_index == MOUSE_BUTTON_WHEEL_UP and click.pressed:
            follow_distance = maxf(1.8, follow_distance - 0.35)
        elif click.button_index == MOUSE_BUTTON_WHEEL_DOWN and click.pressed:
            follow_distance = minf(6.5, follow_distance + 0.35)
        elif click.button_index == MOUSE_BUTTON_LEFT:
            if click.pressed:
                # Android may synthesize a second mouse event from an existing finger.
                if stick_pointer >= 0 or run_pointer >= 0 or jump_pointer >= 0 or look_pointer >= 0:
                    return
                var pos: Vector2 = click.position
                if pos.distance_to(hud.call("stick_center")) < float(hud.call("stick_radius")) * 1.9:
                    mouse_action = "stick"
                    _stick_position(pos)
                elif pos.distance_to(hud.call("jump_center")) < float(hud.call("button_radius")) * 1.6:
                    mouse_action = "jump"
                    jump_buffer = true
                elif pos.distance_to(hud.call("run_center")) < float(hud.call("button_radius")) * 1.6:
                    mouse_action = "run"
                else:
                    mouse_action = "camera"
            else:
                if mouse_action == "stick":
                    stick = Vector2.ZERO
                mouse_action = ""
        elif click.button_index == MOUSE_BUTTON_RIGHT:
            mouse_action = "camera" if click.pressed else ""
    elif event is InputEventMouseMotion:
        var motion: InputEventMouseMotion = event as InputEventMouseMotion
        if mouse_action == "stick":
            _stick_position(motion.position)
        elif mouse_action == "camera":
            _turn_camera(motion.relative)
    elif event is InputEventKey:
        var key: InputEventKey = event as InputEventKey
        if key.pressed and not key.echo and key.keycode == KEY_SPACE:
            jump_buffer = true

func _stick_position(pos: Vector2) -> void:
    var center: Vector2 = hud.call("stick_center")
    var radius: float = hud.call("stick_radius")
    var offset: Vector2 = (pos - center) / radius
    if offset.length() > 1.0:
        offset = offset.normalized()
    stick = Vector2(offset.x, -offset.y)

func _turn_camera(amount: Vector2) -> void:
    look_yaw -= amount.x * 0.0043
    look_pitch = clampf(look_pitch + amount.y * 0.003, -0.16, 1.06)

func _update_camera(delta: float) -> void:
    if player == null or view_camera == null:
        return
    var focus: Vector3 = player.global_position + Vector3(0.0, 0.23, 0.0)
    var orbit: Vector3 = Vector3(sin(look_yaw) * cos(look_pitch), sin(look_pitch), cos(look_yaw) * cos(look_pitch))
    var goal: Vector3 = focus + orbit * follow_distance
    var query: PhysicsRayQueryParameters3D = PhysicsRayQueryParameters3D.create(focus, goal)
    query.collision_mask = 1
    var hit: Dictionary = get_world_3d().direct_space_state.intersect_ray(query)
    if not hit.is_empty():
        var collision_point: Vector3 = hit["position"]
        goal = focus + (collision_point - focus).normalized() * maxf(0.7, focus.distance_to(collision_point) - 0.2)
    view_camera.global_position = goal if delta >= 1.0 else view_camera.global_position.lerp(goal, minf(delta * 9.0, 1.0))
    view_camera.look_at(focus, Vector3.UP)

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
    model_holder.position.y = -0.41 + 0.012 * sin(phase * 2.0) * moving
    # Preserve the genuine 49-bone Blender action AND the corrective morph tracks.
    # Old handmade rotations bypassed corrective shapekeys and bent the abdomen.
    if mouse_animation != null:
        if moving > 0.10:
            if not mouse_animation.is_playing():
                mouse_animation.play("MouseRig")
            mouse_animation.speed_scale = 1.5 if running else 0.80
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
    return river_profile.terrain_height(x, z, _base_height(x, z))

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
    var center: Vector2i = _current_chunk()
    for z in range(-RADIUS, RADIUS + 1):
        for x in range(-RADIUS, RADIUS + 1):
            var co: Vector2i = center + Vector2i(x, z)
            if not chunks.has(co) and not queue.has(co):
                queue.append(co)
    for key in chunks.keys():
        var co: Vector2i = key
        if not _near(co):
            var part: Node3D = chunks[co]
            part.queue_free()
            chunks.erase(co)

func _add_chunk(co: Vector2i) -> void:
    if chunks.has(co):
        return
    var root: Node3D = Node3D.new()
    root.name = "Chunk_%d_%d" % [co.x, co.y]
    root.position = Vector3(float(co.x) * CELL, 0.0, float(co.y) * CELL)
    add_child(root)
    chunks[co] = root
    var verts: PackedVector3Array = PackedVector3Array()
    var normals: PackedVector3Array = PackedVector3Array()
    var uv: PackedVector2Array = PackedVector2Array()
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
            var info: Dictionary = river_profile.ground_sample(Vector2(wx, wz), _base_height(wx, wz))
            verts.append(Vector3(lx, float(info["terrain_y"]), lz))
            uv.append(Vector2(wx, wz) * 0.1)
            var sediment: Dictionary = shore_substrate.sample(info, Vector2(wx, wz))
            colors.append(Color(float(sediment["gravel"]), float(sediment["wetness"]), float(sediment["silt"]), float(sediment["forest"])))
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
    for iz in range(GRID):
        for ix in range(columns - 1):
            var a: int = iz * columns + ix
            indices.append_array(PackedInt32Array([a, a + 1, a + columns, a + 1, a + columns + 1, a + columns]))
    var arrays: Array = []
    arrays.resize(Mesh.ARRAY_MAX)
    arrays[Mesh.ARRAY_VERTEX] = verts
    arrays[Mesh.ARRAY_NORMAL] = normals
    arrays[Mesh.ARRAY_TEX_UV] = uv
    arrays[Mesh.ARRAY_COLOR] = colors
    arrays[Mesh.ARRAY_INDEX] = indices
    var mesh: ArrayMesh = ArrayMesh.new()
    mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
    var instance: MeshInstance3D = MeshInstance3D.new()
    instance.name = "Terrain"
    instance.mesh = mesh
    instance.material_override = terrain_mat
    root.add_child(instance)
    var collider_body: StaticBody3D = StaticBody3D.new()
    collider_body.collision_layer = 1
    var terrain_collision: CollisionShape3D = CollisionShape3D.new()
    terrain_collision.shape = mesh.create_trimesh_shape()
    collider_body.add_child(terrain_collision)
    root.add_child(collider_body)
    _trees(root, co)
    _grass(root, co)
    # The actual water is clipped to each owning terrain chunk. No duplicate
    # full-width surfaces and no disappearing negative-X bank.
    if co.x >= -1 and co.x <= 0:
        _water(root, co)
        _rocks(root, co)
        _major_rocks(root, co)

func _water(root: Node3D, co: Vector2i) -> void:
    var water_mesh: ArrayMesh = river_surface_builder.build_chunk(river_profile, co, CELL)
    if water_mesh.get_surface_count() == 0:
        return
    var water_instance: MeshInstance3D = MeshInstance3D.new()
    water_instance.name = "FlowingWater"
    water_instance.mesh = water_mesh
    # Per-chunk RGBA8 flow atlas; CPU/physics and GPU visual sample the same field.
    var chunk_material: ShaderMaterial = water_mat.duplicate() as ShaderMaterial
    var origin: Vector2 = Vector2(root.position.x,root.position.z)
    var atlas: Image = river_flow_field.build_atlas(river_profile,origin,CELL)
    chunk_material.set_shader_parameter("flow_atlas",ImageTexture.create_from_image(atlas))
    chunk_material.set_shader_parameter("chunk_origin",origin)
    chunk_material.set_shader_parameter("chunk_size",CELL)
    water_instance.material_override = chunk_material
    water_instance.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
    root.add_child(water_instance)

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

func _trees(root: Node3D, co: Vector2i) -> void:
    var rng: RandomNumberGenerator = RandomNumberGenerator.new()
    rng.seed = 300001 + (co.x * 1640531513 + co.y * 805459861) * 13
    var xforms: Array[Transform3D] = []
    for i in range(46):
        var x: float = rng.randf_range(0.0, CELL)
        var z: float = rng.randf_range(0.0, CELL)
        var wx: float = root.position.x + x
        var wz: float = root.position.z + z
        var y: float = _height(wx, wz)
        if river_profile.shore_distance(Vector2(wx, wz)) < 6.0 or y > 28.0:
            continue
        if Vector2(wx - SPAWN_X, wz - SPAWN_Z).length() < 7.0:
            continue
        var scale: float = rng.randf_range(0.76, 1.66)
        var basis: Basis = Basis(Vector3.UP, rng.randf_range(0.0, TAU)).scaled(Vector3(scale, scale * rng.randf_range(0.9, 1.2), scale))
        xforms.append(Transform3D(basis, Vector3(x, y - 0.05, z)))
    _multimesh(root, pine_mesh, "Pines", xforms)

func _grass(root: Node3D, co: Vector2i) -> void:
    var rng: RandomNumberGenerator = RandomNumberGenerator.new()
    rng.seed = 105533 + (co.x * 122949829 + co.y * 1000003) * 7
    var xforms: Array[Transform3D] = []
    for i in range(150):
        var x: float = rng.randf_range(0.0, CELL)
        var z: float = rng.randf_range(0.0, CELL)
        var wx: float = root.position.x + x
        var wz: float = root.position.z + z
        var y: float = _height(wx, wz)
        if river_profile.shore_distance(Vector2(wx, wz)) < 2.4 or y > 18.0:
            continue
        var size: float = rng.randf_range(0.65, 1.45)
        xforms.append(Transform3D(Basis(Vector3.UP, rng.randf_range(0.0, TAU)).scaled(Vector3(size, size, size)), Vector3(x, y + 0.015, z)))
    _multimesh(root, grass_mesh, "Grass", xforms)

func _rocks(root: Node3D, co: Vector2i) -> void:
    # Deterministic regional sediment placement: no continuous gravel bands.
    # Small stones remain instanced and non-physical. S3 will register the
    # large obstructing rocks for flow deflection and localized foam.
    var rng: RandomNumberGenerator = RandomNumberGenerator.new()
    rng.seed = 80333 + (co.x * 528319 + co.y * 851111) * 3
    var pebbles: Array[Transform3D] = []
    var cobbles: Array[Transform3D] = []
    for i in range(280):
        var x: float = rng.randf_range(0.0, CELL)
        var z: float = rng.randf_range(0.0, CELL)
        var wx: float = root.position.x + x
        var wz: float = root.position.z + z
        var p: Vector2 = Vector2(wx, wz)
        var state: Dictionary = river_profile.sample(p)
        var sediment: Dictionary = shore_substrate.sample(state, p)
        var sdf: float = float(state["shore_sdf"])
        if sdf > 5.5 or sdf < -4.5:
            continue
        if rng.randf() > float(sediment["stone_density"]):
            continue
        var y: float = _height(wx, wz)
        var spin: float = rng.randf_range(0.0, TAU)
        var base: Basis = Basis(Vector3.UP,spin)
        if rng.randf() < 0.75:
            var size: float = rng.randf_range(0.08,0.27)
            pebbles.append(Transform3D(base.scaled(Vector3(size*1.45,size*0.47,size)),Vector3(x,y+size*0.10,z)))
        else:
            var size: float = rng.randf_range(0.27,0.78)
            cobbles.append(Transform3D(base.scaled(Vector3(size*1.20,size*0.55,size)),Vector3(x,y+size*0.18,z)))
    _multimesh(root,pebble_mesh,"FinePebbles",pebbles)
    _multimesh(root,pebble_mesh,"Cobbles",cobbles)

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
    instance.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
    root.add_child(instance)
