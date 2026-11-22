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
    // S1 shares exactly the CPU-generated river edge; no old sine center mask.
    // S2 will extend the vertex weights into PBR sediment + wetness layers.
    float shore = clamp(COLOR.r, 0.0, 1.0);
    float wetness = clamp(COLOR.g, 0.0, 1.0);
    float breakup = 0.82 + 0.18 * sin(world_position.x * 0.81 + sin(world_position.z * 0.36) * 2.1);
    base = mix(base, pebbles, shore * breakup);
    base *= 1.0 - 0.16 * wetness;
    ALBEDO = base;
    ROUGHNESS = 0.89;
    METALLIC = 0.0;
}