extends SceneTree
func _initialize() -> void:
    call_deferred("_run")
func _fail(msg: String) -> void:
    push_error("RIVER_S4_FAIL "+msg)
    quit(2)
func _run() -> void:
    var tex: Texture2D = load("res://assets/water/wave_caustics_rgba.png") as Texture2D
    if tex == null or tex.get_width()!=256 or tex.get_height()!=256:
        _fail("missing generated seamless water wave map")
        return
    var shader: Shader = load("res://shaders/river.gdshader") as Shader
    if shader == null:
        _fail("water shader missing")
        return
    var src: String = shader.code
    for must in ["hint_screen_texture","hint_depth_texture","INV_PROJECTION_MATRIX",
                 "exp(-absorption*optical_path)","enable_refraction",
                 "flow_atlas","rock_foam","enable_caustics"]:
        if not src.contains(must):
            _fail("shader contract missing "+must)
            return
    var quality: WaterQualitySettings = WaterQualitySettings.new()
    var material: ShaderMaterial = ShaderMaterial.new()
    material.shader = shader
    quality.configure(material,WaterQualitySettings.LOW)
    if bool(material.get_shader_parameter("enable_refraction")) or bool(material.get_shader_parameter("enable_caustics")):
        _fail("LOW must not pay expensive refraction / caustics cost")
        return
    quality.configure(material,WaterQualitySettings.BALANCED)
    if not bool(material.get_shader_parameter("enable_refraction")) or not bool(material.get_shader_parameter("enable_caustics")):
        _fail("BALANCED should enable controlled optics")
        return
    quality.configure(material,WaterQualitySettings.HIGH)
    if float(material.get_shader_parameter("refraction_strength"))<=0.45:
        _fail("HIGH profile lacks stronger refraction")
        return
    var bed_shader: Shader=load("res://shaders/terrain.gdshader") as Shader
    if bed_shader==null or not bed_shader.code.contains("sunlit_caustics") or not bed_shader.code.contains("EMISSION = vec3(0.0)"):
        _fail("underwater caustics must be shaded by real scene lighting, not emissive glow")
        return
    var scene: PackedScene = load("res://scenes/main.tscn") as PackedScene
    var game: Node3D = scene.instantiate() as Node3D
    root.add_child(game)
    await physics_frame
    var surfaces: int = 0
    var has_depth: bool = false
    for co in [Vector2i(-1,0),Vector2i(0,0)]:
        var chunk: Node3D = game.get_node("Chunk_%d_%d" % [co.x,co.y]) as Node3D
        if chunk == null:
            _fail("missing river chunk")
            return
        var water: MeshInstance3D = chunk.get_node_or_null("FlowingWater") as MeshInstance3D
        if water == null:
            _fail("missing river surface at "+str(co))
            return
        var mat: ShaderMaterial = water.material_override as ShaderMaterial
        if mat == null or mat.get_shader_parameter("wave_map") == null:
            _fail("wave map not assigned to river surface")
            return
        if not bool(mat.get_shader_parameter("enable_refraction")):
            _fail("default BALANCED quality not applied")
            return
        surfaces+=1
        var mesh: MeshInstance3D = chunk.get_node("Terrain") as MeshInstance3D
        var uv2: PackedVector2Array = mesh.mesh.surface_get_arrays(0)[Mesh.ARRAY_TEX_UV2]
        var uv: PackedVector3Array = mesh.mesh.surface_get_arrays(0)[Mesh.ARRAY_VERTEX]
        if uv2.size()!=uv.size():
            _fail("terrain depth metadata missing")
            return
        for meta in uv2:
            if meta.x > 0.02:
                has_depth=true
    if not has_depth:
        _fail("no actual underwater terrain depth supplied to caustics")
        return
    print("RIVER_S4_OK wave=256x256 surface_count=",surfaces," depth_metadata=ok quality=3")
    quit(0)
