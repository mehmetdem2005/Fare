class_name RiverObstacles
extends RefCounted
## S3 physically grounded deterministic boulders. Same world positions are used
## for geometry, obstacle flow deflection and local foam. NEVER seed per chunk.

const ROCK_SPACING_M: float = 34.0

func obstacle_at(index: int, profile: RiverProfile) -> Dictionary:
    var f: float = float(index)
    var z: float = f * ROCK_SPACING_M + 4.0*sin(f*1.91+0.37)
    var sample_center: Dictionary = profile.sample(Vector2(profile.center_x(z),z))
    var half_width: float = minf(float(sample_center["width_left"]),float(sample_center["width_right"]))
    var offset: float = half_width * 0.39 * sin(f*2.31+0.7)
    var x: float = profile.center_x(z) + offset
    var radius: float = 0.84 + 0.43*(0.5+0.5*sin(f*4.87))
    return {"index":index,"xz":Vector2(x,z),"radius":radius}

func near(point: Vector2, profile: RiverProfile) -> Array[Dictionary]:
    var output: Array[Dictionary] = []
    var center: int = floori(point.y / ROCK_SPACING_M)
    for i in range(center-2,center+3):
        var rock: Dictionary = obstacle_at(i,profile)
        if point.distance_squared_to(rock["xz"]) < 140.0:
            output.append(rock)
    return output

func in_chunk(co: Vector2i, cell: float, profile: RiverProfile) -> Array[Dictionary]:
    var output: Array[Dictionary] = []
    var z_min: float = float(co.y) * cell
    var z_max: float = z_min+cell
    var index_min: int = floori((z_min-5.0)/ROCK_SPACING_M)-1
    var index_max: int = ceili((z_max+5.0)/ROCK_SPACING_M)+1
    for i in range(index_min,index_max+1):
        var rock: Dictionary = obstacle_at(i,profile)
        var point: Vector2 = rock["xz"]
        if point.y < z_min or point.y >= z_max:
            continue
        if point.x < float(co.x)*cell or point.x >= float(co.x+1)*cell:
            continue
        output.append(rock)
    return output
