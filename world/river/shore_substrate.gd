class_name ShoreSubstrate
extends RefCounted
## S2: hydrology-driven substrate weights. One FastNoiseLite per world, not
## independently seeded per chunk. Output values are for WORLD-SPACE samples.
## R/G/B/A of vertex color: gravel, wetness, silt, forest-cover respectively.

var macro: FastNoiseLite = FastNoiseLite.new()
var patches: FastNoiseLite = FastNoiseLite.new()

func _init() -> void:
    macro.seed = 97117
    macro.noise_type = FastNoiseLite.TYPE_SIMPLEX_SMOOTH
    macro.frequency = 0.075
    patches.seed = 42281
    patches.noise_type = FastNoiseLite.TYPE_SIMPLEX_SMOOTH
    patches.frequency = 0.23

func sample(profile: Dictionary, world_xz: Vector2) -> Dictionary:
    var sdf: float = float(profile["shore_sdf"])
    var curvature: float = absf(float(profile["curvature"]))
    var n: float = macro.get_noise_2d(world_xz.x,world_xz.y)
    var fine: float = patches.get_noise_2d(world_xz.x,world_xz.y)
    var is_outer: bool = bool(profile["outer_bank"])
    var inside: float = 1.0 - smoothstep(-0.3,0.15,sdf)
    var edge: float = 1.0 - smoothstep(-0.4,3.0+1.4*n,sdf)
    var bars: float = 1.0 if not is_outer else 0.35
    var gravel: float = clampf((0.30+0.34*bars+0.24*n+0.12*fine)*edge,0.0,0.95)
    gravel=lerpf(gravel,clampf(0.35+0.28*n+0.15*fine,0.1,0.9),inside*0.60)
    var silt: float = clampf((0.15+0.22*n)*(0.8 if is_outer else 1.0)*(1.0-smoothstep(0.2,2.6,sdf)),0.0,0.53)
    var soil_wetness: float = 1.0-smoothstep(0.0,1.1+0.48*n,maxf(0.0,sdf))
    var wetness: float = clampf(soil_wetness*(0.83+0.13*fine),0.0,1.0)
    if sdf <= 0.0:
        wetness=1.0
    var forest: float = clampf((0.31+0.15*n)*(smoothstep(2.0,6.2,sdf)),0.0,0.52)
    # Favor larger stones where current is faster and outer bends erode;
    # small and medium gravel persist around inner sediment bars.
    var rough: float = clampf(0.25+curvature*16.0+0.3*float(is_outer),0.0,0.92)
    var stone_density: float = clampf((0.20+0.5*gravel+0.23*rough+0.17*n)*edge,0.0,0.9)
    return {
        "gravel":gravel,"wetness":wetness,"silt":silt,"forest":forest,
        "stone_density":stone_density,"rockiness":rough,"macro_noise":n
    }
