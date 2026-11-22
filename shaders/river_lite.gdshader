shader_type spatial;
render_mode blend_mix, depth_draw_never, cull_disabled, diffuse_burley, specular_schlick_ggx;
// S8-A distant water: reflection from palette + flow atlas; never samples the opaque framebuffer.
uniform sampler2D flow_atlas : filter_linear, repeat_disable;
uniform sampler2D wave_map : filter_linear_mipmap, repeat_enable;
uniform vec2 chunk_origin = vec2(0.0);
uniform float chunk_size = 40.0;
uniform float max_flow_mps = 2.5;
uniform vec3 sky_reflection_horizon = vec3(0.64,0.69,0.66);
uniform vec3 sky_reflection_zenith = vec3(0.34,0.50,0.63);
uniform vec3 sun_direction = vec3(0.30,0.80,0.48);
uniform float sun_glint_strength = 0.25;
varying vec3 world_position;
void vertex() {
    world_position = (MODEL_MATRIX*vec4(VERTEX,1.0)).xyz;
}
void fragment() {
    vec2 p = clamp((world_position.xz-chunk_origin)/max(chunk_size,0.01),vec2(0.0),vec2(1.0));
    vec4 f=texture(flow_atlas,p);
    vec2 current=(f.rg*2.0-1.0)*max_flow_mps;
    vec4 wave=texture(wave_map,world_position.xz*0.24-current*TIME*0.16);
    vec3 nw=normalize(vec3((wave.r*2.0-1.0)*0.15,1.0,(wave.g*2.0-1.0)*0.15));
    vec3 nv=normalize((VIEW_MATRIX*vec4(nw,0.0)).xyz);
    NORMAL=nv;
    float fresnel=0.02+0.98*pow(1.0-clamp(dot(nv,normalize(VIEW)),0.0,1.0),5.0);
    vec3 rw=normalize((INV_VIEW_MATRIX*vec4(reflect(-normalize(VIEW),nv),0.0)).xyz);
    vec3 sky=mix(sky_reflection_horizon,sky_reflection_zenith,smoothstep(-0.15,0.85,rw.y));
    vec3 col=mix(mix(vec3(0.055,0.20,0.22),vec3(0.17,0.39,0.36),wave.a*0.48+0.20),sky,0.34+fresnel*0.35);
    float foam=clamp(f.a,0.0,1.0)*smoothstep(0.5,0.82,wave.a)*0.31;
    ALBEDO=mix(col,vec3(0.84,0.88,0.81),foam);
    ROUGHNESS=mix(0.18,0.32,clamp(f.b,0.0,1.0));
    SPECULAR=0.45;
    ALPHA=0.98;
}
