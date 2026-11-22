shader_type spatial;
render_mode cull_back, diffuse_burley, specular_schlick_ggx;

// Real Poly Haven CC0 images; each packed map stores OpenGL tangent NORMAL
// in RGB, linear ROUGHNESS in A. Packed images MUST NOT be source_color.
uniform sampler2D grass_tex : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D forest_tex : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D cliff_tex : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D riverbed_tex : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D grass_nr : filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D forest_nr : filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D cliff_nr : filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D riverbed_nr : filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D wave_map : filter_linear_mipmap, repeat_enable;
uniform float caustic_strength : hint_range(0.0,1.0) = 0.22;

varying vec3 world_position;
varying vec3 world_normal;

void vertex() {
    world_position = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
    world_normal = normalize(MODEL_NORMAL_MATRIX * NORMAL);
}
void fragment() {
    vec3 n = normalize(world_normal);
    vec2 uv = world_position.xz * 0.18;
    // independent scales reduce lockstep tiling without expensive extra passes
    vec2 uv_f = uv * 0.77;
    vec2 uv_r = uv * 0.68;
    vec2 uv_p = uv * 1.14;
    float gravel = clamp(COLOR.r, 0.0, 0.94);
    float wet = clamp(COLOR.g, 0.0, 1.0);
    float silt = clamp(COLOR.b, 0.0, 0.58);
    float forest = clamp(COLOR.a, 0.0, 0.55);
    float slope = 1.0 - clamp(n.y, 0.0, 1.0);
    float cliff = clamp(smoothstep(0.21, 0.58, slope) + smoothstep(14.0, 32.0, world_position.y)*0.44,0.0,0.94);
    // S2 macro modulation is fed from the same CPU terrain RiverProfile/SDF.
    vec3 albedo = mix(texture(grass_tex,uv).rgb*vec3(0.60,0.92,0.58), texture(forest_tex,uv_f).rgb*vec3(0.70,0.89,0.65),forest);
    albedo = mix(albedo, texture(riverbed_tex,uv_p).rgb,gravel);
    // S2 polish: cliffs use a world-aligned side projection rather than
    // stretching the horizontal XZ image vertically up a steep bank.
    // One extra image sample ONLY in sufficiently steep fragments.
    float side_blend = smoothstep(0.26,0.58,cliff);
    bool x_face = abs(n.x) > abs(n.z);
    vec2 side_uv = (x_face ? world_position.zy : world_position.xy) * 0.18 * 0.68;
    vec3 rock_albedo = texture(cliff_tex,uv_r).rgb;
    if (side_blend > 0.01) {
        rock_albedo = mix(rock_albedo,texture(cliff_tex,side_uv).rgb,side_blend);
    }
    albedo = mix(albedo,rock_albedo,cliff);
    albedo = mix(albedo,vec3(0.22,0.19,0.14),silt*0.28);
    albedo *= (1.0-0.22*wet)*(0.94+0.08*sin(world_position.x*0.095)*cos(world_position.z*0.074));
    // ALBEDO is finalized after shadow-aware underwater caustic lighting.
    // Two real PBR channels in a single fetch per material.
    vec4 nr = mix(texture(grass_nr,uv),texture(forest_nr,uv_f),forest);
    nr = mix(nr,texture(riverbed_nr,uv_p),gravel);
    vec4 rock_nr = texture(cliff_nr,uv_r);
    if (side_blend > 0.01) {
        rock_nr = mix(rock_nr,texture(cliff_nr,side_uv),side_blend);
    }
    nr = mix(nr,rock_nr,cliff);
    vec3 tangent_normal = normalize(nr.rgb*2.0-1.0);
    // World XZ projection uses tangent +X and binormal +Z.
    // World normal -> view normal explicitly avoids missing mesh tangent data.
    vec3 t = vec3(1.0,0.0,0.0) - n * dot(n,vec3(1.0,0.0,0.0));
    if (dot(t,t)<0.08) {
        t = vec3(0.0,0.0,1.0) - n * dot(n,vec3(0.0,0.0,1.0));
    }
    t = normalize(t);
    vec3 b = -cross(n,t);
    vec3 perturbed_world_normal = normalize(t*tangent_normal.x + b*tangent_normal.y + n*tangent_normal.z);
    if (side_blend > 0.01) {
        // Match the normal-map tangent basis to the side-projecting axis;
        // simply applying an XZ tangent normal on a cliff gives fake shine.
        vec3 face_t = x_face ? vec3(0.0,0.0,1.0) : vec3(1.0,0.0,0.0);
        face_t = normalize(face_t - n * dot(n,face_t));
        vec3 face_b = -cross(n,face_t);
        vec3 side_world_normal = normalize(face_t*tangent_normal.x + face_b*tangent_normal.y + n*tangent_normal.z);
        perturbed_world_normal = normalize(mix(perturbed_world_normal,side_world_normal,side_blend*cliff));
    }
    NORMAL = normalize((VIEW_MATRIX * vec4(perturbed_world_normal,0.0)).xyz);
    ROUGHNESS = clamp(mix(nr.a,nr.a*0.66,wet),0.22,0.99);
    // UV2.x is actual analytic bed depth from the S1 RiverProfile, not a
    // fake shoreline distance. Caustic light patterns live on the real BED.
    float bed_depth = max(UV2.x,0.0);
    float immersed = smoothstep(0.025,0.095,bed_depth);
    float light_fade = exp(-bed_depth*1.65);
    vec2 water_uv = world_position.xz*0.38;
    vec4 c1 = texture(wave_map,water_uv+vec2(0.041,0.073)*TIME);
    vec4 c2 = texture(wave_map,water_uv*0.71+vec2(-0.031,0.058)*TIME);
    float caustic = pow(max(0.0,c1.a*c2.a-0.24),1.9);
    // Let the built-in PBR lighting and pine shadow map illuminate caustics.
    // Emission would glow through tree shadows and look like radioactive mud.
    vec3 sunlit_caustics = vec3(0.34,0.52,0.39)*caustic*light_fade*immersed*caustic_strength;
    ALBEDO = clamp(albedo + sunlit_caustics,vec3(0.0),vec3(1.5));
    EMISSION = vec3(0.0);
    AO = clamp(UV2.y,0.84,1.0);
    METALLIC=0.0;
}
