shader_type spatial;
render_mode blend_mix, depth_draw_never, cull_disabled, unshaded;
// S5 local river condensation: sparse horizontal world-space quads.
// This is NOT physically simulated volumetric fog. Keep opacity below 0.1.
uniform vec4 mist_tint : source_color = vec4(0.69,0.74,0.72,1.0);
uniform float mist_density : hint_range(0.0,1.0) = 0.5;
varying vec2 world_xz;
void vertex() {
    vec4 w = MODEL_MATRIX * vec4(VERTEX,1.0);
    world_xz=w.xz;
}
void fragment() {
    vec2 radial = (UV-vec2(0.5))*2.0;
    float ellipse = length(radial*vec2(0.95,1.45));
    float fade = pow(1.0-smoothstep(0.15,1.0,ellipse),2.2);
    float drift = 0.58 + 0.21*sin(world_xz.x*0.47 + TIME*0.15)
                       + 0.21*sin(world_xz.y*0.32 - TIME*0.12);
    ALBEDO = mist_tint.rgb;
    ALPHA = fade * max(drift,0.0) * mist_density * 0.075;
}
