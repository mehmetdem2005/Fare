class_name RiverProfile
extends RefCounted
## S1: deterministic river geometry. XZ units are meters, Y is up.
## Single authority for bank positions, water elevation, bed cut and shore SDF.
## Flow/foam fields here are placeholders until S3. Renderer optics remain S4.

const CONTROL_SPACING: float = 48.0
const BANK_TRANSITION: float = 5.2
const SURFACE_GRADE: float = 0.0015
const SURFACE_AT_ORIGIN: float = 0.26
const HALF_WIDTH_FLOOR: float = 4.7
const MAX_BANK_SEARCH: float = 32.0

func _control_x(i: int) -> float:
    var t: float = float(i)
    return 6.6 * sin(t * 0.78 + 0.13) + 2.4 * sin(t * 1.93 + 0.51)

func center_x(z: float) -> float:
    var u: float = z / CONTROL_SPACING
    var n: int = floori(u)
    var t: float = u - float(n)
    var a: float = _control_x(n - 1)
    var b: float = _control_x(n)
    var c: float = _control_x(n + 1)
    var d: float = _control_x(n + 2)
    return 0.5 * ((2.0 * b) + (-a + c) * t + (2.0 * a - 5.0 * b + 4.0 * c - d) * t * t + (-a + 3.0 * b - 3.0 * c + d) * t * t * t)

func _dx_dz(z: float) -> float:
    return (center_x(z + 0.12) - center_x(z - 0.12)) / 0.24

func _curvature(z: float) -> float:
    var v: float = _dx_dz(z)
    var second: float = (center_x(z + 0.25) - 2.0 * center_x(z) + center_x(z - 0.25)) / (0.25 * 0.25)
    return second / pow(1.0 + v * v, 1.5)

func _nearest_z(point: Vector2) -> float:
    # Three local tangent projections; no chunk-dependent inputs.
    var z: float = point.y
    for i in range(3):
        var tangent: Vector2 = Vector2(_dx_dz(z), 1.0).normalized()
        var delta: Vector2 = point - Vector2(center_x(z), z)
        z += clampf(delta.dot(tangent) * tangent.y, -12.0, 12.0)
    return z

func surface_height(z: float) -> float:
    # Monotonic downhill toward +Z; no arbitrary upward-running pools.
    return SURFACE_AT_ORIGIN - z * SURFACE_GRADE

func _center_depth(s: float) -> float:
    # Shallow riffle around z=20; broad deeper pool around z=100.
    var reach: float = 0.5 + 0.5 * sin((s - 62.0) * 0.028 + 0.13 * sin(s * 0.011))
    var depth: float = 0.14 + reach * 1.07 + 0.035 * sin(s * 0.071)
    var shoal: float = exp(-pow((s - 20.0) / 18.0, 2.0))
    return maxf(0.045, depth * (1.0 - 0.75 * shoal))

func _shape(point: Vector2) -> Dictionary:
    var s: float = _nearest_z(point)
    var center: Vector2 = Vector2(center_x(s), s)
    var tangent: Vector2 = Vector2(_dx_dz(s), 1.0).normalized()
    var normal_lateral: Vector2 = Vector2(tangent.y, -tangent.x)
    var lateral: float = (point - center).dot(normal_lateral)
    var curvature: float = _curvature(s)
    var half: float = 7.4 + 1.18 * sin(s * 0.021) + 0.63 * sin(s * 0.054 + 1.1)
    var bend_skew: float = clampf(curvature * 42.0, -0.22, 0.22)
    var width_left: float = maxf(HALF_WIDTH_FLOOR, half * (1.0 - bend_skew) + 0.28 * sin(s * 0.042))
    var width_right: float = maxf(HALF_WIDTH_FLOOR, half * (1.0 + bend_skew) + 0.39 * sin(s * 0.033 + 0.6))
    var width: float = width_right if lateral >= 0.0 else width_left
    var u: float = clampf(absf(lateral) / width, 0.0, 1.0)
    var signed_shore: float = absf(lateral) - width
    # Outer-bank erosion leaves a steep submerged cut. Inner bank is a gravel shelf.
    var is_outer: bool = curvature * lateral < 0.0
    var fade: float = 1.0 - smoothstep(0.15 if is_outer else 0.02, 1.0, u)
    var exponent: float = 0.64 if is_outer else 1.75
    var bed_depth: float = _center_depth(s) * pow(maxf(0.0, fade), exponent)
    # Curvature-specific scour cannot alter the exact waterline: vanishes at u=1.
    var scour: float = minf(absf(curvature) * 32.0, 0.28) * pow(maxf(0.0, 1.0-u), 1.2) if is_outer else 0.0
    bed_depth = maxf(0.0, bed_depth + scour)
    var water_y: float = surface_height(point.y)
    return {
        "s": s, "center": center, "tangent": tangent,
        "normal_lateral": normal_lateral, "curvature": curvature,
        "lateral": lateral, "width_left": width_left, "width_right": width_right,
        "width": width, "shore_sdf": signed_shore, "water_y": water_y,
        "bed_y": water_y - bed_depth, "depth": bed_depth,
        "outer_bank": is_outer,
        "reach": "riffle" if _center_depth(s) < 0.25 else ("pool" if _center_depth(s) > 0.75 else "run")
    }

func sample(point: Vector2) -> Dictionary:
    var result: Dictionary = _shape(point)
    var sdf: float = float(result["shore_sdf"])
    var near_water: float = 1.0 - smoothstep(0.0, 2.7, maxf(0.0, sdf))
    result["wetness"] = near_water
    result["shore_gravel"] = 1.0 - smoothstep(-0.4, 3.5, sdf)
    # S3 will replace this placeholder velocity with obstacle-aware 2D flow.
    var speed: float = 0.4 + 0.25 * (1.0 - smoothstep(0.2, 1.25, float(result["depth"])))
    var tangent: Vector2 = result["tangent"]
    result["flow_xz"] = tangent * speed
    result["turbulence"] = 0.0
    return result

func ground_sample(point: Vector2, base_terrain: float) -> Dictionary:
    # For mesh generation: one spline/SDF query supplies bed height and vertex
    # material masks; avoid the prior 5 expensive queries per vertex.
    var data: Dictionary = sample(point)
    var sdf: float = float(data["shore_sdf"])
    data["terrain_y"] = float(data["bed_y"]) if sdf <= 0.0 else lerpf(float(data["water_y"]), base_terrain, smoothstep(0.0, BANK_TRANSITION, sdf))
    return data

func shore_distance(point: Vector2) -> float:
    return float(_shape(point)["shore_sdf"])

func terrain_height(x: float, z: float, original: float) -> float:
    # The river stays inside roughly +/- 30m; skip expensive projections outside.
    if absf(x) > 40.0:
        return original
    var data: Dictionary = _shape(Vector2(x, z))
    var sdf: float = float(data["shore_sdf"])
    if sdf <= 0.0:
        return float(data["bed_y"])
    # Both slopes tend to zero on the shoreline, preventing a hard cut.
    return lerpf(float(data["water_y"]), original, smoothstep(0.0, BANK_TRANSITION, sdf))

func _bank_x_at_z(z: float, side: int) -> float:
    # Solve the real SDF=0 intersection with the horizontal Z row. Never guess
    # that x=center_x +/- width is correct on a curved tangent.
    var center: float = center_x(z)
    if side < 0:
        var low: float = center - MAX_BANK_SEARCH
        var high: float = center
        for i in range(17):
            var mid: float = 0.5 * (low + high)
            if shore_distance(Vector2(mid, z)) <= 0.0:
                high = mid
            else:
                low = mid
        return 0.5 * (low + high)
    var left: float = center
    var right: float = center + MAX_BANK_SEARCH
    for i in range(17):
        var mid: float = 0.5 * (left + right)
        if shore_distance(Vector2(mid, z)) <= 0.0:
            left = mid
        else:
            right = mid
    return 0.5 * (left + right)

func banks_at_z(z: float) -> Vector2:
    return Vector2(_bank_x_at_z(z, -1), _bank_x_at_z(z, 1))
