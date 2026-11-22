shader_type spatial;
render_mode blend_mix, depth_draw_never, cull_disabled, diffuse_burley, specular_schlick_ggx;

uniform float current_speed : hint_range(0.1, 5.0) = 1.7;
uniform vec4 deep_tint : source_color = vec4(0.06, 0.20, 0.25, 1.0);
uniform vec4 shallow_tint : source_color = vec4(0.24, 0.49, 0.48, 1.0);
uniform vec4 foam_tint : source_color = vec4(0.84, 0.92, 0.82, 1.0);
varying vec3 world_position;
varying float edge;

void vertex() {
    edge = abs(UV.x * 2.0 - 1.0);
    float center = 1.0 - smoothstep(0.54, 0.96, edge);
    VERTEX.y += center * 0.029 * (sin(VERTEX.z * 4.0 - TIME * 4.0 + VERTEX.x * 1.3) + 0.35 * sin(VERTEX.z * 7.7 - TIME * 6.9));
    world_position = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}
void fragment() {
    vec2 p = world_position.xz;
    // All patterns advect toward +Z; the water is not a static color strip.
    vec2 current = vec2(p.x, p.y - TIME * current_speed);
    float l1 = sin(current.y * 5.5 + sin(current.x * 1.8 + current.y * 0.7) * 0.8);
    float l2 = sin(current.y * 12.4 - current.x * 2.0 + sin(current.y * 1.6) * 1.1);
    float l3 = sin(current.y * 19.0 + current.x * 3.4);
    float movement = 0.5 + 0.26 * l1 + 0.16 * l2 + 0.08 * l3;
    float shimmer = pow(max(0.0, l1 * 0.42 + l2 * 0.30 + l3 * 0.20), 4.0);
    float bank_foam = smoothstep(0.72, 0.97, edge) * (0.12 + 0.13 * (l2 * 0.5 + 0.5));
    vec3 color = mix(deep_tint.rgb, shallow_tint.rgb, clamp(movement + edge * 0.30, 0.0, 1.0));
    color = mix(color, foam_tint.rgb, clamp(0.24 * shimmer + bank_foam, 0.0, 0.37));
    ALBEDO = color;
    EMISSION = foam_tint.rgb * (0.08 * shimmer + 0.06 * bank_foam);
    ALPHA = clamp(0.64 + 0.16 * movement + edge * 0.07, 0.64, 0.85);
    ROUGHNESS = 0.19;
    SPECULAR = 0.58;
}