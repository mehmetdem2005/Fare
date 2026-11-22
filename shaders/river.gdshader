shader_type spatial;
render_mode blend_mix, depth_draw_never, cull_disabled, diffuse_burley, specular_schlick_ggx;

// S4 Mobile Vulkan water. Actual screen/depth reads are deliberately optional.
// No SSR, normal/roughness screen buffer or volumetric fog dependency.
uniform sampler2D flow_atlas : filter_linear, repeat_disable;
uniform sampler2D wave_map : filter_linear_mipmap, repeat_enable;
uniform sampler2D opaque_screen : hint_screen_texture, filter_linear, repeat_disable;
uniform sampler2D opaque_depth : hint_depth_texture, filter_nearest, repeat_disable;
uniform vec2 chunk_origin = vec2(0.0);
uniform float chunk_size = 40.0;
uniform float max_flow_mps = 2.5;
uniform bool enable_refraction = true;
uniform bool enable_caustics = true;
uniform float refraction_strength : hint_range(0.0,1.0) = 0.42;
uniform float wave_strength : hint_range(0.0,2.0) = 0.80;
uniform float caustic_strength : hint_range(0.0,1.0) = 0.22;
uniform float optical_max : hint_range(0.1,10.0) = 4.0;
uniform vec3 absorption = vec3(0.95,0.34,0.19);
uniform vec4 shallow_tint : source_color = vec4(0.16,0.40,0.34,1.0);
uniform vec4 deep_tint : source_color = vec4(0.035,0.14,0.16,1.0);
uniform vec4 foam_tint : source_color = vec4(0.86,0.91,0.84,1.0);
uniform vec3 sky_reflection_horizon = vec3(0.64,0.69,0.66);
uniform vec3 sky_reflection_zenith = vec3(0.34,0.50,0.63);
uniform vec3 sun_direction = vec3(0.30,0.80,0.48);
uniform float sun_glint_strength : hint_range(0.0,1.0) = 0.25;

varying vec3 world_position;
varying float river_edge;

float linear_depth_at(vec2 at_uv, mat4 inv_projection) {
    float raw = texture(opaque_depth, at_uv).r;
    vec4 p = inv_projection * vec4(at_uv*2.0-1.0,raw,1.0);
    return max(0.0,-p.z/max(abs(p.w),0.00001));
}

void vertex() {
    river_edge = abs(UV.x*2.0-1.0);
    // Small GPU wave displacement, no tall procedural bumps that intersect bank.
    vec3 w = (MODEL_MATRIX*vec4(VERTEX,1.0)).xyz;
    float edge_fade = 1.0-smoothstep(0.73,0.985,river_edge);
    float h = sin(w.x*1.93+w.z*2.27-TIME*2.1+sin(w.z*0.63)*0.33);
    VERTEX.y += 0.009*edge_fade*h;
    world_position = (MODEL_MATRIX*vec4(VERTEX,1.0)).xyz;
}
void fragment() {
    vec2 flow_uv = clamp((world_position.xz-chunk_origin)/max(chunk_size,0.01),vec2(0.0),vec2(1.0));
    vec4 field = texture(flow_atlas,flow_uv);
    vec2 velocity = (field.rg*2.0-1.0)*max_flow_mps;
    float turbulence = clamp(field.b,0.0,1.0);
    float rock_foam = clamp(field.a,0.0,1.0);
    // Water normal texture is seamless and deterministic; the two independent
    // rotated frequencies erase legacy parallel sine bands.
    vec2 p = world_position.xz;
    vec2 wuv1 = p*0.31-velocity*TIME*0.19;
    vec2 wuv2 = vec2(p.y*0.61+p.x*0.17,-p.x*0.61+p.y*0.12)
              -velocity.yx*TIME*0.36;
    vec4 wav1 = texture(wave_map,wuv1);
    vec4 wav2 = texture(wave_map,wuv2);
    vec2 slope = ((wav1.rg*2.0-1.0)+0.56*(wav2.rg*2.0-1.0))
               *wave_strength*(0.52+0.36*turbulence);
    // Godot 4.7 Mobile FRONT_FACING allows correct underside shading on
    // the same cull-disabled water mesh without a second rendered surface.
    bool underside = !FRONT_FACING;
    vec3 normal_world = normalize(vec3(slope.x,underside ? -1.0 : 1.0,slope.y));
    vec3 normal_view = normalize((VIEW_MATRIX*vec4(normal_world,0.0)).xyz);
    NORMAL = normal_view;
    float cos_view = clamp(dot(normal_view,normalize(VIEW)),0.0,1.0);
    float fresnel = clamp(0.0204+0.9796*pow(1.0-cos_view,5.0),0.0204,0.92);
    // The underwater surface must not reflect a bright overhead sky like
    // the top face; keep a faint physically suggestive reflection only.
    if (underside) {
        fresnel *= 0.12;
    }

    // Opaque bed depth minus transparent-water fragment depth. For Vulkan
    // NDC depth 0..1, INV_PROJECTION_MATRIX is the documented reconstruction.
    float surface_eye_depth = max(0.0,-VERTEX.z);
    float opaque_eye_depth = linear_depth_at(SCREEN_UV, INV_PROJECTION_MATRIX);
    float optical_path = clamp(max(0.0,opaque_eye_depth-surface_eye_depth),0.0,optical_max);
    float shallow = exp(-optical_path*0.72);
    vec3 tint = mix(deep_tint.rgb,shallow_tint.rgb,shallow);
    vec3 transmittance = exp(-absorption*optical_path);
    vec2 distorted_uv = clamp(SCREEN_UV + slope*0.0065*refraction_strength*clamp(optical_path,0.0,1.0),vec2(0.002),vec2(0.998));
    // Check displaced opaque depth to avoid pulling *foreground* land/rock
    // across the waterline. Fall back to unchanged screen sample on failure.
    if (enable_refraction && refraction_strength > 0.001) {
        float moved_depth = linear_depth_at(distorted_uv, INV_PROJECTION_MATRIX);
        if (moved_depth <= surface_eye_depth+0.08) {
            distorted_uv = SCREEN_UV;
        }
    } else {
        distorted_uv = SCREEN_UV;
    }
    vec3 behind_water = texture(opaque_screen,distorted_uv).rgb;
    vec3 transmission_color = behind_water*transmittance+tint*(vec3(1.0)-transmittance);

    // Mobile approximation of a reflected sky: no invented SSR.
    vec3 reflected_world = normalize((INV_VIEW_MATRIX*vec4(reflect(-normalize(VIEW),normal_view),0.0)).xyz);
    float zenith = smoothstep(-0.15,0.85,reflected_world.y);
    vec3 sky_reflection = mix(sky_reflection_horizon,sky_reflection_zenith,zenith);
    float glint = pow(max(0.0,dot(reflected_world,normalize(sun_direction))),120.0)*sun_glint_strength;
    glint *= underside ? 0.0 : 1.0;
    vec3 color = mix(transmission_color,sky_reflection,fresnel*0.77);
    color += vec3(1.0,0.88,0.66)*glint*clamp(fresnel+0.14,0.0,0.65);

    // Tiny high-frequency caustic shimmer near the shallow *waterline*.
    // Main caustics are projected on the real river BED in terrain.gdshader.
    float caustic = max(0.0,wav1.a*wav2.a-0.28);
    float shallow_caustic = caustic*caustic_strength*shallow*(1.0-river_edge)*float(enable_caustics)*(underside ? 0.0 : 1.0);
    color += vec3(0.12,0.18,0.13)*shallow_caustic;

    // Foam only from S3 obstacle/velocity field, with a tiny edge contact.
    float foam_pattern = smoothstep(0.40,0.77,wav2.a*0.53+wav1.a*0.47);
    float foam = rock_foam*foam_pattern*(0.42+0.45*turbulence)*(underside ? 0.0 : 1.0);
    float edge_contact = smoothstep(0.970,0.997,river_edge)*0.015*(underside ? 0.0 : 1.0);
    color = mix(color,foam_tint.rgb,clamp(foam+edge_contact,0.0,0.69));
    if (underside) {
        // Looking toward the underside: mineral-green transmission and
        // attenuation, without a fake surface sun-glitter/foam ceiling.
        vec3 underwater_tint = behind_water*vec3(0.22,0.43,0.46) + vec3(0.012,0.055,0.062);
        color = mix(color,underwater_tint,0.65);
    }

    ALBEDO = clamp(color,vec3(0.0),vec3(1.5));
    EMISSION = vec3(0.08,0.09,0.07)*foam;
    // Screen background is already in the shaded transmission; keep alpha
    // near opaque to prevent double alpha integration of the same background.
    ALPHA = 0.985;
    ROUGHNESS = mix(0.16,0.35,turbulence);
    SPECULAR = 0.45;
}
