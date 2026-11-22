extends SceneTree
func _initialize() -> void:
    call_deferred("_run")
func _fail(reason: String) -> void:
    push_error("S6_SHORE_RIPPLE_FAIL "+reason)
    quit(2)
func _run() -> void:
    var game: Node3D=(load("res://scenes/main.tscn") as PackedScene).instantiate() as Node3D
    root.add_child(game)
    game.set_physics_process(false)
    var river: RiverProfile=game.get("river_profile") as RiverProfile
    var mouse: CharacterBody3D=game.get("player") as CharacterBody3D
    var water: MouseWaterInteraction=game.get("mouse_water") as MouseWaterInteraction
    var pool: WaterRipplePool=game.get("ripple_pool") as WaterRipplePool
    var z: float=20.0
    var right: float=river.banks_at_z(z).y
    mouse.global_position=Vector3(right-0.07,river.surface_height(z)+0.11,z)
    mouse.velocity=Vector3(3.1,0.0,0.0)
    water.state=MouseWaterInteraction.SHALLOW
    water.water_y=river.surface_height(z)
    game.call("_emit_water_ripples",0.5)
    if pool.count_active()!=1:
        _fail("water contact ring absent")
        return
    var first: MeshInstance3D=pool.rings[0]
    if river.shore_distance(Vector2(first.global_position.x,first.global_position.z))>=0.0:
        _fail("moving ring landed on dry land")
        return
    water.state=MouseWaterInteraction.DRY
    game.call("_emit_water_ripples",0.15)
    if pool.count_active()<2:
        _fail("exit ripples missing")
        return
    var second: MeshInstance3D=pool.rings[1]
    if river.shore_distance(Vector2(second.global_position.x,second.global_position.z))>=0.0:
        _fail("exit ring on dry land")
        return
    print("S6_SHORE_RIPPLE_OK water_only=1 exit=1 pool_cap=",WaterRipplePool.CAPACITY)
    quit(0)
