shader_type canvas_item;
render_mode unshaded;
// Low-overdraw alternative to an extra Mobile framebuffer copy. This is
// underwater atmospheric tint, NOT true 3D volumetric scattering.
uniform float intensity : hint_range(0.0,1.0) = 0.0;
uniform float depth_m : hint_range(0.0,3.0) = 0.0;
void fragment() {
    float depth_fade = clamp(depth_m*0.19,0.0,0.46);
    float waves = 0.5+0.5*sin(UV.x*15.0+TIME*0.93+sin(UV.y*8.0-TIME*0.42));
    float top_sun = pow(1.0-UV.y,2.7)*(0.015+0.012*waves);
    vec3 tint = mix(vec3(0.06,0.24,0.23),vec3(0.018,0.10,0.14),depth_fade);
    float edge = smoothstep(0.75,1.0,length((UV-0.5)*vec2(1.45,1.8)));
    COLOR = vec4(clamp(tint + top_sun,0.0,1.0),intensity*(0.33+0.19*depth_fade+0.07*edge));
}
