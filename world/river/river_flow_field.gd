class_name RiverFlowField
extends RefCounted
## S3: shared CPU flow state, RGBA8 atlas for mobile GPU.
## RG signed world XZ velocity, B turbulence, A physically justified foam.
const MAX_VECTOR_MPS: float = 2.5

var obstacles: RiverObstacles = RiverObstacles.new()

func sample(profile: RiverProfile, world_xz: Vector2) -> Dictionary:
    var river: Dictionary = profile.sample(world_xz)
    var sdf: float = float(river["shore_sdf"])
    if sdf >= 0.0:
        return {"velocity":Vector2.ZERO, "speed":0.0, "turbulence":0.0, "foam":0.0}
    var tangent: Vector2 = river["tangent"]
    var side: Vector2 = river["normal_lateral"]
    var depth: float = float(river["depth"])
    var width: float = float(river["width"])
    var lateral: float = float(river["lateral"])
    var normalized_lateral: float = clampf(absf(lateral)/maxf(width,0.01),0.0,1.0)
    var friction: float = 0.25+0.75*(1.0-smoothstep(0.64,1.0,normalized_lateral))
    var reach_speed: float = clampf(0.52+0.58*exp(-maxf(depth-0.14,0.0)*1.8),0.42,1.16)
    var main_velocity: Vector2 = tangent*reach_speed*friction
    var side_velocity: Vector2 = Vector2.ZERO
    var wake: float = 0.0
    var bow: float = 0.0
    for obstacle in obstacles.near(world_xz,profile):
        var rp: Vector2 = obstacle["xz"]
        var radius: float = float(obstacle["radius"])
        var delta: Vector2 = world_xz-rp
        var along: float = delta.dot(tangent)
        var across: float = delta.dot(side)
        var around: float = exp(-pow(along/(radius*1.55),2.0)-pow(across/(radius*1.65),2.0))
        var behind: float = exp(-maxf(0.0,along)/(radius*3.1))*(1.0-smoothstep(radius*0.6,radius*1.8,absf(across)))
        if along > 0.0:
            wake = maxf(wake,behind)
        else:
            bow = maxf(bow,around)
        var sign_side: float = 1.0 if across >= 0.0 else -1.0
        side_velocity += side * sign_side * around * 0.28
    main_velocity *= clampf(1.0-0.64*wake-0.34*bow,0.22,1.25)
    var velocity: Vector2 = main_velocity+side_velocity
    if velocity.length() > MAX_VECTOR_MPS:
        velocity = velocity.normalized()*MAX_VECTOR_MPS
    var turbulence: float = clampf(0.70*wake+0.66*bow+0.08*(1.0-normalized_lateral),0.0,1.0)
    var contact: float = (1.0-smoothstep(0.82,0.99,normalized_lateral))*0.06
    var foam: float = clampf(0.55*bow+0.52*wake+contact*turbulence,0.0,1.0)
    return {"velocity":velocity, "speed":velocity.length(),"turbulence":turbulence,"foam":foam}

func build_atlas(profile: RiverProfile, origin: Vector2, cell: float, resolution: int=32) -> Image:
    var img: Image = Image.create(resolution,resolution,false,Image.FORMAT_RGBA8)
    for iy in range(resolution):
        for ix in range(resolution):
            var p: Vector2 = origin + Vector2(float(ix),float(iy)) * (cell/float(resolution-1))
            var data: Dictionary = sample(profile,p)
            var v: Vector2 = data["velocity"]
            var encoded: Color = Color(
                clampf(0.5+v.x/(2.0*MAX_VECTOR_MPS),0.0,1.0),
                clampf(0.5+v.y/(2.0*MAX_VECTOR_MPS),0.0,1.0),
                clampf(float(data["turbulence"]),0.0,1.0),
                clampf(float(data["foam"]),0.0,1.0))
            img.set_pixel(ix,iy,encoded)
    return img

func decode_rg(color: Color) -> Vector2:
    return Vector2(color.r*2.0-1.0,color.g*2.0-1.0)*MAX_VECTOR_MPS
