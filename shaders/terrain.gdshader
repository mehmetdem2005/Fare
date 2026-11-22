shader_type spatial;
render_mode cull_back, diffuse_burley, specular_schlick_ggx;

uniform sampler2D grass_tex : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D forest_tex : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D cliff_tex : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D riverbed_tex : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
varying vec3 world_position;
varying vec3 world_normal;

void vertex() {
    world_position = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
    world_normal = normalize(MODEL_NORMAL_MATRIX * NORMAL);
}
void fragment() {
    vec2 uv = world_position.xz * 0.18;
    vec3 grass = texture(grass_tex, uv).rgb;
    vec3 forest = texture(forest_tex, uv * 0.78).rgb;
    vec3 cliff = texture(cliff_tex, uv * 0.68).rgb;
    vec3 pebbles = texture(riverbed_tex, uv * 1.18).rgb;
    float slope = 1.0 - max(0.0, world_normal.y);
    float rock_amount = clamp(smoothstep(0.21, 0.61, slope) + smoothstep(13.0, 34.0, world_position.y) * 0.48, 0.0, 0.93);
    float tree_cover = smoothstep(-0.2, 0.65, sin(world_position.x * 0.04) * sin(world_position.z * 0.06));
    vec3 base = mix(grass, forest, 0.17 + tree_cover * 0.25);
    base = mix(base, cliff, rock_amount);
    float center = sin(world_position.z * 0.012) * 4.2 + sin(world_position.z * 0.031) * 1.6;
    float shore = 1.0 - smoothstep(7.7, 14.0, abs(world_position.x - center));
    base = mix(base, pebbles, shore * 0.99);
    ALBEDO = base;
    ROUGHNESS = 0.89;
    METALLIC = 0.0;
}