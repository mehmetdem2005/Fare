extends SceneTree
# S1 geometry regression on real Godot 4.7.2.

func _initialize() -> void:
    call_deferred("_run")

func _fail(msg: String) -> void:
    push_error("RIVER_S1_FAIL " + msg)
    quit(2)

func _run() -> void:
    var r: RiverProfile = RiverProfile.new()
    var samples: int = 0
    # Intersections and finite depths at the true left and right shoreline.
    for zi in range(-8, 29):
        var z: float = float(zi) * 10.0
        var banks: Vector2 = r.banks_at_z(z)
        if not banks.x < banks.y or banks.y - banks.x < 6.0:
            _fail("invalid river banks at z=" + str(z) + " " + str(banks))
            return
        for x in [banks.x, banks.y]:
            var section: Dictionary = r.sample(Vector2(float(x), z))
            var depth: float = float(section["depth"])
            var sdf: float = float(section["shore_sdf"])
            if depth > 0.004 or absf(sdf) > 0.006:
                _fail("shoreline must be exact: z=" + str(z) + " x=" + str(x) + " depth=" + str(depth) + " sdf=" + str(sdf))
                return
            samples += 1
        var center: Dictionary = r.sample(Vector2(r.center_x(z), z))
        if float(center["depth"]) < 0.04:
            _fail("dry center at z=" + str(z))
            return
        if float(center["water_y"]) <= float(center["bed_y"]):
            _fail("negative depth at z=" + str(z))
            return
    # Explicitly different reaches; do not keep the old flat rectangular trench.
    var shoal: float = float(r.sample(Vector2(r.center_x(20.0),20.0))["depth"])
    var pool: float = float(r.sample(Vector2(r.center_x(100.0),100.0))["depth"])
    if shoal > 0.20 or pool < 0.65 or pool <= shoal * 3.0:
        _fail("riffle/pool depth variation not achieved: " + str(shoal) + " / " + str(pool))
        return
    # World-space heights and bank mask must be continuous through chunk edges.
    for boundary in [0.0, 40.0, 80.0, 120.0]:
        for ix in range(-32, 33):
            var x: float = float(ix) * 0.75
            var z: float = float(boundary)
            var a: float = r.terrain_height(x, z-0.001, 2.0)
            var b: float = r.terrain_height(x, z+0.001, 2.0)
            if absf(a-b) > 0.025:
                _fail("height discontinuity at z=" + str(z) + " x=" + str(x))
                return
            samples += 1
    # Test the water mesh at two neighboring X chunks: both must meet exactly at x=0.
    var builder: RiverSurfaceBuilder = RiverSurfaceBuilder.new()
    var negative: ArrayMesh = builder.build_chunk(r, Vector2i(-1, 0), 40.0)
    var positive: ArrayMesh = builder.build_chunk(r, Vector2i(0, 0), 40.0)
    if negative.get_surface_count() != 1 or positive.get_surface_count() != 1:
        _fail("missing clipped water surfaces")
        return
    var left_v: PackedVector3Array = negative.surface_get_arrays(0)[Mesh.ARRAY_VERTEX]
    var right_v: PackedVector3Array = positive.surface_get_arrays(0)[Mesh.ARRAY_VERTEX]
    var cols: int = RiverSurfaceBuilder.ACROSS_STEPS + 1
    for iz in range(RiverSurfaceBuilder.ALONG_STEPS + 1):
        var idx: int = iz * cols
        var wl: Vector3 = left_v[idx + cols - 1] + Vector3(-40.0, 0.0, 0.0)
        var wr: Vector3 = right_v[idx]
        if wl.distance_to(wr) > 0.004:
            _fail("water chunk side discontinuity at row=" + str(iz) + " " + str(wl) + " " + str(wr))
            return
    print("RIVER_S1_OK samples=", samples, " shoal=", shoal, " pool=", pool, " seam=ok")
    quit(0)
