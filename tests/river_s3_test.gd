extends SceneTree
func _initialize() -> void:
    call_deferred("_run")
func _fail(reason: String) -> void:
    push_error("RIVER_S3_FAIL "+reason)
    quit(2)
func _run() -> void:
    var profile: RiverProfile = RiverProfile.new()
    var flow: RiverFlowField = RiverFlowField.new()
    var rocks: RiverObstacles = RiverObstacles.new()
    var count: int = 0
    var sampled: int = 0
    for co in [Vector2i(-1,0),Vector2i(0,0),Vector2i(-1,1),Vector2i(0,1)]:
        for rock in rocks.in_chunk(co,40.0,profile):
            var p: Vector2 = rock["xz"]
            var near: Dictionary = flow.sample(profile,p)
            if float(near["turbulence"]) <= 0.08 or float(near["foam"]) <= 0.06:
                _fail("visible boulder lacks physical turbulence/foam "+str(p))
                return
            count+=1
    if count < 1:
        _fail("no boulders generated in test river reaches")
        return
    for zi in range(0,25):
        var z: float = float(zi)*11.0
        for xi in range(-11,12):
            var x: float = profile.center_x(z)+float(xi)*0.95
            var p: Vector2 = Vector2(x,z)
            var state: Dictionary = profile.sample(p)
            var v: Dictionary = flow.sample(profile,p)
            var tangent: Vector2 = state["tangent"]
            if float(state["shore_sdf"]) >= 0.0:
                if (v["velocity"] as Vector2).length() > 0.01:
                    _fail("flow outside river at "+str(p))
                    return
            else:
                if (v["velocity"] as Vector2).dot(tangent) < -0.001:
                    if float(v["eddy"])<0.40 or (v["velocity"] as Vector2).dot(tangent)<-0.45:
                        _fail("unjustified reverse flow outside rock wake at "+str(p))
                        return
            for key in ["speed","foam","turbulence"]:
                var number: float = float(v[key])
                if is_nan(number) or is_inf(number) or number < 0.0 or number > 2.51:
                    _fail("invalid "+key+"="+str(number))
                    return
            sampled+=1
    var observed_eddy: bool=false
    for rock in rocks.in_chunk(Vector2i(0,0),40.0,profile)+rocks.in_chunk(Vector2i(-1,0),40.0,profile):
        var center: Vector2=rock["xz"]
        var downstream: Vector2=profile.sample(center)["tangent"]
        var sample_wake: Dictionary=flow.sample(profile,center+downstream*float(rock["radius"])*1.6)
        if float(sample_wake["eddy"])>0.25:
            observed_eddy=true
    if not observed_eddy:
        _fail("boulders still do not generate recirculation pockets")
        return
    var origin: Vector2 = Vector2(0.0,0.0)
    var atlas: Image = flow.build_atlas(profile,origin,40.0,32)
    if atlas.get_width()!=32 or atlas.get_height()!=32 or atlas.get_format()!=Image.FORMAT_RGBA8:
        _fail("bad mobile atlas format")
        return
    var max_error: float = 0.0
    for i in range(32):
        var p: Vector2 = origin + Vector2(float(i),float(i))*40.0/31.0
        var actual: Vector2 = flow.sample(profile,p)["velocity"]
        var from_atlas: Vector2 = flow.decode_rg(atlas.get_pixel(i,i))
        max_error = maxf(max_error,actual.distance_to(from_atlas))
    if max_error > 0.04:
        _fail("GPU atlas/CPU flow disagree "+str(max_error))
        return
    print("RIVER_S3_OK sample_count=",sampled," boulders=",count," max_atlas_error=",max_error)
    quit(0)
