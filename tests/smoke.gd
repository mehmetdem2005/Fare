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
    var camera: Camera3D = game.get_node_or_null("ThirdPersonCamera") as Camera3D
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
    # Exercise actual controller entry points and physics, not only scene parsing.
    var hud: Control = game.get("hud") as Control
    var origin: Vector3 = actor.global_position
    var press: InputEventScreenTouch = InputEventScreenTouch.new()
    press.pressed = true
    press.index = 0
    var center: Vector2 = hud.call("stick_center")
    press.position = center + Vector2(0.0, -60.0)
    game.call("_input", press)
    var axis: Vector2 = game.get("stick")
    if axis.y < 0.3:
        _fail("joystick does not register touch")
        return
    for i in range(22):
        await physics_frame
    var traveled: float = Vector2(actor.global_position.x - origin.x, actor.global_position.z - origin.z).length()
    if traveled < 0.1:
        _fail("joystick did not move the mouse: " + str(traveled))
        return
    if not mouse_animation.is_playing():
        _fail("real imported mouse animation did not play during movement")
        return
    var release: InputEventScreenTouch = InputEventScreenTouch.new()
    release.index = 0
    release.pressed = false
    release.position = press.position
    game.call("_input", release)
    if (game.get("stick") as Vector2).length() > 0.01:
        _fail("joystick release fails")
        return
    var cam_start: float = game.get("look_yaw")
    var camera_press: InputEventScreenTouch = InputEventScreenTouch.new()
    camera_press.pressed = true
    camera_press.index = 1
    camera_press.position = Vector2(800.0, 350.0)
    game.call("_input", camera_press)
    var swipe: InputEventScreenDrag = InputEventScreenDrag.new()
    swipe.index = 1
    swipe.position = Vector2(850.0, 360.0)
    swipe.relative = Vector2(50.0, 10.0)
    game.call("_input", swipe)
    if absf(float(game.get("look_yaw")) - cam_start) < 0.1:
        _fail("camera drag did not orbit")
        return
    print("SMOKE_OK rig=", rig.get_bone_count(), " touch_walk=", traveled, " camera_orbit=ok corrective_animation=ok textures=4")
    quit(0)
