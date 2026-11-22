shader_type spatial;
render_mode cull_disabled, diffuse_burley, specular_schlick_ggx;
// V3 low-end water: opaque near-1 alpha was previously paying for the
// transparent pass. Packed flow atlas remains authoritative for horizontal
// current and foam; two crossed surface waves avoid the motionless plane.
uniform sampler2D flow_atlas : filter_linear, repeat_disable;
uniform sampler2D wave_map : filter_linear_mipmap, repeat_enable;
uniform vec2 chunk_origin = vec2(0.0);
uniform float chunk_size = 40.0;
uniform float max_flow_mps = 2.5;
uniform vec3 sky_reflection_horizon = vec3(0.64,0.69,0.66);
uniform vec3 sky_reflection_zenith = vec3(0.34,0.50,0.63);
uniform vec3 sun_direction = vec3(0.30,0.80,0.48);
uniform float sun_glint_strength = 0.25;
// Disabled for river: ocean tides must be coupled to physics and coast.
uniform float tide_amplitude = 0.0;
uniform float tide_period_seconds = 3600.0;
varying vec3 world_position;
void vertex(){
    vec2 p=(MODEL_MATRIX*vec4(VERTEX,1.0)).xz;
    float wave1=sin(dot(p,vec2(1.8,0.75))+TIME*1.45);
    float wave2=sin(dot(p,vec2(-1.0,2.2))+TIME*1.11);
    float tide=tide_amplitude*sin(TIME*6.2831853/max(tide_period_seconds,60.0));
    VERTEX.y+=0.011*wave1+0.008*wave2+tide;
    world_position=(MODEL_MATRIX*vec4(VERTEX,1.0)).xyz;
}
void fragment(){
    vec2 p=clamp((world_position.xz-chunk_origin)/max(chunk_size,0.01),vec2(0.0),vec2(1.0));
    vec4 f=texture(flow_atlas,p);
    vec2 current=(f.rg*2.0-1.0)*max_flow_mps;
    vec4 w1=texture(wave_map,world_position.xz*0.31-current*TIME*0.22);
    vec4 w2=texture(wave_map,world_position.xz*0.17+current*TIME*0.08+vec2(TIME*0.025,-TIME*0.04));
    vec2 detail=(w1.rg*2.0-1.0)*0.28+(w2.rg*2.0-1.0)*0.18;
    detail+=vec2(cos(dot(world_position.xz,vec2(1.8,0.75))+TIME*1.45)*0.020,
        cos(dot(world_position.xz,vec2(-1.0,2.2))+TIME*1.11)*0.022);
    vec3 nw=normalize(vec3(detail.x,1.0,detail.y));
    vec3 nv=normalize((VIEW_MATRIX*vec4(nw,0.0)).xyz);
    NORMAL=nv;
    float fresnel=0.04+0.96*pow(1.0-clamp(dot(nv,normalize(VIEW)),0.0,1.0),5.0);
    vec3 rw=normalize((INV_VIEW_MATRIX*vec4(reflect(-normalize(VIEW),nv),0.0)).xyz);
    vec3 sky=mix(sky_reflection_horizon,sky_reflection_zenith,smoothstep(-0.15,0.85,rw.y));
    vec3 water=mix(vec3(0.05,0.19,0.20),vec3(0.16,0.35,0.34),w1.a*0.5+w2.a*0.2);
    vec3 col=mix(water,sky,0.28+fresnel*0.43);
    float foam=clamp(f.a,0.0,1.0)*smoothstep(0.43,0.77,w1.a*0.6+w2.a*0.4)*0.62;
    ALBEDO=mix(col,vec3(0.82,0.88,0.82),foam);
    ROUGHNESS=mix(0.16,0.32,clamp(f.b,0.0,1.0));
    SPECULAR=0.55;
}
