extends SceneTree
## Real non-headless Vulkan capture, ideally lavapipe under Xvfb on GitHub runner.
## A successful Godot import/headless CI alone cannot compile the real Mobile
## fragment shader or prove that the image has correct colors.

func _initialize() -> void:
    call_deferred("_capture")

func _capture() -> void:
    var main: PackedScene = load("res://scenes/main.tscn") as PackedScene
    if main == null:
        push_error("S4_VISUAL_FAIL unable to load game scene")
        quit(2)
        return
    var game: Node3D = main.instantiate() as Node3D
    root.add_child(game)
    var camera: Camera3D = game.get_node("ThirdPersonCamera") as Camera3D
    if camera == null:
        push_error("S4_VISUAL_FAIL camera missing")
        quit(2)
        return
    # Stable reference shot from mouse eye-level toward the river edge.
    var river: RiverProfile = game.get("river_profile") as RiverProfile
    var z: float = 18.0
    var bank: Vector2 = river.banks_at_z(z)
    var eye: Vector3 = Vector3(bank.y+1.6,river.surface_height(z)+0.56,z+1.1)
    camera.global_position = eye
    camera.look_at(Vector3(river.center_x(z),river.surface_height(z)-0.2,z+4.1),Vector3.UP)
    # Camera tracking script may overwrite this if active; disable after frame.
    game.set_process(false)
    for i in range(18):
        await process_frame
    await RenderingServer.frame_post_draw
    var img: Image = root.get_texture().get_image()
    if img == null or img.get_width()<400 or img.get_height()<250:
        push_error("S4_VISUAL_FAIL image empty or dimensions invalid")
        quit(2)
        return
    var err: Error = img.save_png("/tmp/s4_mobile_vulkan.png")
    if err != OK:
        push_error("S4_VISUAL_FAIL could not save screenshot "+str(err))
        quit(2)
        return
    print("S4_VISUAL_OK ",img.get_width(),"x",img.get_height()," PNG=/tmp/s4_mobile_vulkan.png")
    quit(0)
