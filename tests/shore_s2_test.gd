extends SceneTree
func _initialize() -> void:
    call_deferred("_run")

func _bad(msg: String) -> void:
    push_error("SHORE_S2_FAIL "+msg)
    quit(2)

func _run() -> void:
    var profile: RiverProfile = RiverProfile.new()
    var substrate: ShoreSubstrate = ShoreSubstrate.new()
    for material in ["grass","forest","rock","pebbles"]:
        var packed: String = "res://assets/ground/"+material+"_nrough.png"
        if not ResourceLoader.exists(packed):
            _bad("missing Poly Haven packed map "+packed)
            return
        var texture: Texture2D = load(packed) as Texture2D
        if texture == null or texture.get_width() != 1024 or texture.get_height() != 1024:
            _bad("invalid packed map "+packed)
            return
    var terrain_shader: Shader=load("res://shaders/terrain.gdshader") as Shader
    if terrain_shader==null or not terrain_shader.code.contains("side_world_normal") or not terrain_shader.code.contains("world_position.zy"):
        _bad("steep bank texture projection missing or normal basis not aligned")
        return
    var near_wet: float = 0.0
    var far_wet: float = 0.0
    var min_gravel: float = 2.0
    var max_gravel: float = -1.0
    var samples: int = 0
    for iz in range(-6,35):
        var z: float = float(iz)*8.0
        var banks: Vector2 = profile.banks_at_z(z)
        for side in [-1.0,1.0]:
            var xedge: float = banks.x if side < 0.0 else banks.y
            for offset in [0.1,1.0,2.0,4.0,8.0]:
                var x: float = xedge + side*float(offset)
                var p: Vector2 = Vector2(x,z)
                var state: Dictionary = profile.sample(p)
                var material: Dictionary = substrate.sample(state,p)
                var gr: float = float(material["gravel"])
                var wet: float = float(material["wetness"])
                if gr < 0.0 or gr > 1.0 or wet < 0.0 or wet > 1.0:
                    _bad("out of bounds sediment at "+str(p))
                    return
                if offset == 0.1:
                    near_wet += wet
                    min_gravel = minf(min_gravel,gr)
                    max_gravel = maxf(max_gravel,gr)
                if offset == 8.0:
                    far_wet += wet
                samples += 1
    if near_wet < far_wet+15.0:
        _bad("wet ground does not dry away from banks")
        return
    if max_gravel-min_gravel < 0.12:
        _bad("gravel repeats as constant-width/constant-strength shore band")
        return
    print("SHORE_S2_OK samples=",samples," grayscale_variation=",max_gravel-min_gravel," wet_difference=",near_wet-far_wet," verified_maps=4")
    quit(0)
