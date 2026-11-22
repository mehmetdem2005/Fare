extends SceneTree

func _initialize() -> void:
    call_deferred("_test_scene")

func _test_scene() -> void:
    var scene: PackedScene = load("res://scenes/main.tscn") as PackedScene
    if scene == null:
        push_error("SMOKE_FAIL main.tscn not loadable")
        quit(2)
        return
    var instance: Node3D = scene.instantiate() as Node3D
    if instance == null:
        push_error("SMOKE_FAIL main.tscn not a Node3D")
        quit(2)
        return
    root.add_child(instance)
    await process_frame
    await process_frame
    var actor: Node = instance.get_node_or_null("MousePlayer")
    var camera: Node = instance.get_node_or_null("ThirdPersonCamera")
    var chunk: Node = instance.get_node_or_null("Chunk_0_0")
    if actor == null or camera == null or chunk == null:
        push_error("SMOKE_FAIL missing actor / camera / first terrain chunk")
        quit(2)
        return
    var assets: Array[String] = ["grass.jpg", "forest.jpg", "rock.jpg", "pebbles.jpg"]
    for asset in assets:
        if not ResourceLoader.exists("res://assets/ground/" + asset):
            push_error("SMOKE_FAIL missing real Poly Haven texture: " + asset)
            quit(2)
            return
    print("SMOKE_OK actor, camera, terrain, polyhaven textures")
    quit(0)
