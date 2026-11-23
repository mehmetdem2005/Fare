extends SceneTree

func _initialize() -> void:
    call_deferred("_test_scene")

func _fail(reason: String) -> void:
    push_error("SMOKE_FAIL " + reason)
    quit(2)

func _test_scene() -> void:
    var scene: PackedScene = load("res://scenes/main.tscn") as PackedScene
    if scene == null:
        _fail("scene load")
        return
    var game: Node3D = scene.instantiate() as Node3D
    if game == null:
        _fail("scene instance")
        return
    root.add_child(game)
    await physics_frame
    await physics_frame
    var actor: CharacterBody3D = game.get_node_or_null("MousePlayer") as CharacterBody3D
    var camera: Camera3D = game.get("view_camera") as Camera3D
    var chunk: Node3D = game.get_node_or_null("Chunk_0_0") as Node3D
    if actor == null or camera == null or chunk == null:
        _fail("missing player camera or chunk")
        return
    var assets: Array[String] = ["grass.jpg", "forest.jpg", "rock.jpg", "pebbles.jpg"]
    for name in assets:
        if not ResourceLoader.exists("res://assets/ground/" + name):
            _fail("real Poly Haven image not bundled: " + name)
            return
    var rig: Skeleton3D = game.get("rig") as Skeleton3D
    if rig == null or rig.get_bone_count() != 49:
        _fail("rigged mouse did not import as Skeleton3D")
        return
    var mouse_animation: AnimationPlayer = game.get("mouse_animation") as AnimationPlayer
    if mouse_animation == null or not mouse_animation.has_animation("MouseRig"):
        _fail("49-bone corrective motion clip MouseRig not available")
        return
    # Ground must have an upward face, with backface raycasts disabled.
    var spawn_x: float = 20.0
    var spawn_z: float = 16.0
    var expected_y: float = game.call("_height", spawn_x, spawn_z)
    var spawn_y: float = actor.global_position.y
    if spawn_y - expected_y < 3.0:
        _fail("spawn must be airborne, height=" + str(spawn_y-expected_y))
        return
    var ray: PhysicsRayQueryParameters3D = PhysicsRayQueryParameters3D.create(
        Vector3(spawn_x, expected_y + 20.0, spawn_z),
        Vector3(spawn_x, expected_y - 10.0, spawn_z))
    ray.collision_mask = 1
    ray.hit_back_faces = false
    var hit: Dictionary = game.get_world_3d().direct_space_state.intersect_ray(ray)
    if hit.is_empty():
        _fail("no front-facing terrain collision from above")
        return
    var ground_normal: Vector3 = hit["normal"]
    if ground_normal.dot(Vector3.UP) < 0.6:
        _fail("ground normal not upward: " + str(ground_normal))
        return
    var ray_ground_y: float = (hit["position"] as Vector3).y
    if absf(ray_ground_y - expected_y) > 0.55:
        _fail("ground hit mismatch " + str(ray_ground_y) + " != " + str(expected_y))
        return
    for i in range(180):
        if actor.is_on_floor():
            break
        await physics_frame
    if not actor.is_on_floor():
        _fail("mouse never landed on the terrain")
        return
    var landing_y: float = actor.global_position.y
    if absf(landing_y - expected_y) > 1.1:
        _fail("mouse landed at wrong altitude: " + str(landing_y))
        return
    # S1: physics collision must agree with analytic river bed and both banks.
    var profile: RiverProfile = game.get("river_profile") as RiverProfile
    if profile == null:
        _fail("RiverProfile instance not connected to world")
        return
    for z in [14.0, 18.0, 32.0]:
        var banks: Vector2 = profile.banks_at_z(z)
        var probes: Array[float] = [banks.x-0.65, banks.x+0.65, banks.y-0.65, banks.y+0.65]
        for x in probes:
            var expected_bed: float = game.call("_height", x, z)
            var shore_ray: PhysicsRayQueryParameters3D = PhysicsRayQueryParameters3D.create(
                Vector3(x, expected_bed + 14.0, z),
                Vector3(x, expected_bed - 8.0, z))
            shore_ray.collision_mask = 1
            shore_ray.hit_back_faces = false
            var shore_hit: Dictionary = game.get_world_3d().direct_space_state.intersect_ray(shore_ray)
            if shore_hit.is_empty():
                _fail("riverbank collider missing at " + str(Vector2(x,z)))
                return
            var actual_bed: float = (shore_hit["position"] as Vector3).y
            if absf(actual_bed - expected_bed) > 0.24:
                _fail("riverbank collision differs from render height at " + str(Vector2(x,z)) + ": " + str(actual_bed-expected_bed))
                return
    # V1 control regression: no fixed joystick center and no legacy _input orbit.
    var router: FareTouchInputRouter = game.get("mobile_input") as FareTouchInputRouter
    var camera_rig: FareThirdPersonCamera = game.get("mobile_camera_rig") as FareThirdPersonCamera
    if router == null or camera_rig == null:
        _fail("new independent camera and router not installed")
        return
    if camera_rig.get_parent() == actor or camera_rig.arm.collision_mask != 1:
        _fail("camera rig must stay independent of player and collide with terrain")
        return
    var origin: Vector3 = actor.global_position
    var center: Vector2 = router.movement_region().get_center()
    var press: InputEventScreenTouch = InputEventScreenTouch.new()
    press.pressed = true
    press.index = 0
    press.position = center
    router._input(press)
    var motion: InputEventScreenDrag = InputEventScreenDrag.new()
    motion.index = 0
    motion.position = center + Vector2(0, -60)
    motion.screen_relative = Vector2(0, -60)
    router._input(motion)
    var axis: Vector2 = router.movement()
    if axis.y > -0.30:
        _fail("floating joystick did not register forward touch")
        return
    for i in range(22):
        await physics_frame
    var traveled: float = Vector2(actor.global_position.x - origin.x, actor.global_position.z - origin.z).length()
    if traveled < 0.1:
        _fail("floating joystick did not move the mouse: " + str(traveled))
        return
    if not mouse_animation.is_playing():
        _fail("mouse animation not triggered by new joystick")
        return
    var release: InputEventScreenTouch = InputEventScreenTouch.new()
    release.index = 0
    release.pressed = false
    release.position = motion.position
    router._input(release)
    if router.movement().length() > 0.01:
        _fail("floating joystick release fails")
        return
    var cam_start: float = camera_rig.yaw_angle
    var camera_press: InputEventScreenTouch = InputEventScreenTouch.new()
    camera_press.pressed = true
    camera_press.index = 1
    camera_press.position = Vector2(800.0, 350.0)
    router._input(camera_press)
    var swipe: InputEventScreenDrag = InputEventScreenDrag.new()
    swipe.index = 1
    swipe.position = Vector2(850.0, 360.0)
    swipe.screen_relative = Vector2(65.0, 10.0)
    router._input(swipe)
    # SceneTree.process_frame resumes before Node._process; step the render-camera explicitly.
    camera_rig._process(1.0/60.0)
    if absf(camera_rig.yaw_angle - cam_start) < 0.08:
        _fail("new physical-pixel camera drag did not orbit")
        return
    print("SMOKE_OK rig=", rig.get_bone_count(), " touch_walk=", traveled,
        " independent_camera=ok spring_arm=ok animation=ok terrain=ok")
    quit(0)
