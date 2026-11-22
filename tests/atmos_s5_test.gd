extends SceneTree
# S5 forest atmosphere/regression. Headless values are NOT Vulkan visual proof.
func _initialize() -> void:
    call_deferred("_test")
func _fail(msg: String) -> void:
    push_error("ATMOS_S5_FAIL "+msg)
    quit(2)
func _test() -> void:
    var scene: PackedScene = load("res://scenes/main.tscn") as PackedScene
    var game: Node3D = scene.instantiate() as Node3D
    root.add_child(game)
    await physics_frame
    var atmosphere: ForestAtmosphere = game.get("atmosphere") as ForestAtmosphere
    if atmosphere == null:
        _fail("missing central ForestAtmosphere")
        return
    if atmosphere.environment.background_mode != Environment.BG_SKY or atmosphere.environment.sky == null:
        _fail("sky background is not real")
        return
    if atmosphere.sun.directional_shadow_mode != DirectionalLight3D.SHADOW_PARALLEL_2_SPLITS:
        _fail("mobile two-split shadow preset missing")
        return
    if atmosphere.environment.volumetric_fog_enabled:
        _fail("unsupported Mobile volumetric fog enabled")
        return
    if atmosphere.sky.radiance_size > Sky.RADIANCE_SIZE_128:
        _fail("radiance budget too large for target")
        return
    var grid: Array[Node] = game.find_children("Pines","MultiMeshInstance3D",true,false)
    var shadows: int = 0
    for instance in grid:
        if (instance as MultiMeshInstance3D).cast_shadow == GeometryInstance3D.SHADOW_CASTING_SETTING_ON:
            shadows+=1
    if shadows < 1:
        _fail("no real pine shadow casters")
        return
    var mat: ShaderMaterial = game.get("terrain_mat") as ShaderMaterial
    var mist_count: int = 0
    var reflection: Array[float] = []
    var energies: Array[float] = []
    for preset in [ForestAtmosphere.MORNING,ForestAtmosphere.MIDDAY,ForestAtmosphere.EVENING]:
        atmosphere.apply_preset(preset)
        var horizon: Color = atmosphere.sky_material.sky_horizon_color
        if atmosphere.sun.light_energy <= 0.1 or atmosphere.environment.fog_density <= 0.0:
            _fail("sun or fog disabled at preset "+str(preset))
            return
        reflection.append(horizon.r)
        energies.append(atmosphere.caustics_energy())
        var ray: ShaderMaterial = game.get("water_mat") as ShaderMaterial
        atmosphere.configure_river(ray)
        var water_horizon: Vector3 = ray.get_shader_parameter("sky_reflection_horizon")
        if absf(water_horizon.x-horizon.r) > 0.0001:
            _fail("river sky reflection not synced")
            return
    if absf(reflection[1]-reflection[2]) < 0.1 or energies[1] <= energies[2]:
        _fail("time presets indistinguishable or caustic energy wrong")
        return
    atmosphere.apply_preset(ForestAtmosphere.MORNING)
    for co in [Vector2i(-1,0),Vector2i(0,0)]:
        var chunk: Node3D = game.get_node_or_null("Chunk_%d_%d"%[co.x,co.y]) as Node3D
        if chunk == null:
            _fail("missing near river chunk")
            return
        var water: MeshInstance3D = chunk.get_node_or_null("FlowingWater") as MeshInstance3D
        var river_mat: ShaderMaterial = water.material_override as ShaderMaterial
        if river_mat.get_shader_parameter("sun_direction") == null:
            _fail("river shard missing sun synchronization")
            return
        var clouds: MultiMeshInstance3D = chunk.get_node_or_null("NearRiverMist") as MultiMeshInstance3D
        if clouds == null or clouds.multimesh.instance_count < 1:
            _fail("missing shallow near river mist instances")
            return
        if clouds.multimesh.instance_count > 24:
            _fail("mist overdraw limit exceeded")
            return
        mist_count+=clouds.multimesh.instance_count
    if mat.get_shader_parameter("caustic_strength") == null:
        _fail("S4 caustic sunlight disconnected")
        return
    print("ATMOS_S5_OK pine_shadow_groups=",shadows," mist_quads=",mist_count," sun_presets=3 sky_synced=1")
    quit(0)
