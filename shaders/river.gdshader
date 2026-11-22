shader_type spatial;
render_mode blend_mix, depth_draw_never, cull_disabled, diffuse_burley, specular_schlick_ggx;

// S3: world-space physical flow, wake turbulence and causal foam.
// S4 will replace temporary water absorption with depth optics.
uniform sampler2D flow_atlas : filter_linear, repeat_disable;
uniform vec2 chunk_origin = vec2(0.0);
uniform float chunk_size = 40.0;
uniform float max_flow_mps = 2.5;
uniform vec4 deep_tint : source_color = vec4(0.06,0.20,0.25,1.0);
uniform vec4 shallow_tint : source_color = vec4(0.20,0.47,0.45,1.0);
uniform vec4 foam_tint : source_color = vec4(0.86,0.91,0.84,1.0);

varying vec3 world_position;
varying float river_edge;

void vertex() {
    river_edge = abs(UV.x*2.0-1.0);
    vec3 world = (MODEL_MATRIX * vec4(VERTEX,1.0)).xyz;
    float calm_wave = sin(world.x*2.7+world.z*3.9-TIME*4.1);
    VERTEX.y += 0.018*(1.0-smoothstep(0.8,1.0,river_edge))*calm_wave;
    world_position = (MODEL_MATRIX * vec4(VERTEX,1.0)).xyz;
}
void fragment() {
    vec2 flow_uv = clamp((world_position.xz-chunk_origin)/max(chunk_size,0.01),vec2(0.0),vec2(1.0));
    vec4 field = texture(flow_atlas,flow_uv);
    vec2 velocity = (field.rg*2.0-1.0)*max_flow_mps;
    float turbulence = clamp(field.b,0.0,1.0);
    float rock_foam = clamp(field.a,0.0,1.0);
    // Advected world-space 2D noise: camera rotation cannot change flow direction.
    vec2 p = world_position.xz-velocity*TIME;
    float coarse = sin(p.x*3.1+p.y*4.8+sin(p.y*0.63)*0.6)*sin(p.x*1.7-p.y*2.2);
    float detail = sin(p.x*8.3-p.y*9.4+sin(p.x*1.1)*1.2)*sin(p.y*6.2+p.x*5.1);
    float surface_motion = 0.5+0.25*coarse+0.18*detail;
    vec3 water_col = mix(deep_tint.rgb,shallow_tint.rgb,clamp(surface_motion+river_edge*0.25,0.0,1.0));
    // Foam needs turbulence/obstacle source. Quiet pools do not turn white.
    float foam_texture = smoothstep(0.05,0.68,0.6*detail+0.4*coarse);
    float foam = rock_foam*foam_texture*(0.28+0.65*turbulence);
    float bank_contact = smoothstep(0.93,0.985,river_edge)*0.035;
    water_col = mix(water_col,foam_tint.rgb,clamp(foam+bank_contact,0.0,0.78));
    ALBEDO = water_col;
    EMISSION = foam_tint.rgb*foam*0.06;
    ALPHA = clamp(0.70+0.12*surface_motion+0.06*river_edge,0.65,0.87);
    ROUGHNESS = mix(0.19,0.38,turbulence);
    SPECULAR = 0.56;
}
