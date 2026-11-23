extends SceneTree

func _initialize() -> void:
    call_deferred("_test")

func _test() -> void:
    for filename in ["res://demo_pine.tscn","res://demo_forest.tscn"]:
        var scene: PackedScene = load(filename)
        if scene == null:
            push_error("Demo scene missing: " + filename)
            quit(1)
            return
        var instance: Node3D = scene.instantiate()
        root.add_child(instance)
        for name in ["DemoCamera","DemoSun","DemoEnvironment","DemoGround"]:
            if instance.get_node_or_null(name) == null:
                push_error("Demo is not playable, missing " + name + " in " + filename)
                quit(1)
                return
        instance.queue_free()
    print("PINE_DEMO_CI_OK playable scene cameras lights and ground")
    quit(0)
