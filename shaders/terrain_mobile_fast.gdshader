shader_type spatial;
render_mode cull_back, diffuse_burley, specular_schlick_ggx;
// S8-D Android emergency tier: same UV/vertex substrate masks as full PBR,
// with original Poly Haven albedo but without 8 normal/roughness and water
// caustic texture fetches per terrain fragment. Restores full shader on demand.
uniform sampler2D grass_tex : source_color, filter_linear_mipmap, repeat_enable;
uniform sampler2D grass_nr : filter_linear_mipmap, repeat_enable;
uniform sampler2D forest_tex : source_color, filter_linear_mipmap, repeat_enable;
uniform sampler2D cliff_tex : source_color, filter_linear_mipmap, repeat_enable;
uniform sampler2D riverbed_tex : source_color, filter_linear_mipmap, repeat_enable;
varying vec3 wp;
varying vec3 wn;
void vertex(){
    wp=(MODEL_MATRIX*vec4(VERTEX,1.0)).xyz;
    wn=normalize(MODEL_NORMAL_MATRIX*NORMAL);
}
void fragment(){
    float gravel=clamp(COLOR.r,0.0,0.94);
    float wet=clamp(COLOR.g,0.0,1.0);
    float silt=clamp(COLOR.b,0.0,0.58);
    float forest=clamp(COLOR.a,0.0,0.55);
    float slope=1.0-clamp(wn.y,0.0,1.0);
    float rock=clamp(smoothstep(0.21,0.58,slope)+smoothstep(14.0,32.0,wp.y)*0.44,0.0,0.94);
    vec2 uv=wp.xz*0.18;
    // Existing ground images are brown-biased: green the living substrate,
    // never the sediment, rock, riverbed or wet shoreline masks.
    vec3 meadow=texture(grass_tex,uv).rgb*vec3(0.60,0.92,0.58);
    vec3 litter=texture(forest_tex,uv*0.77).rgb*vec3(0.70,0.89,0.65);
    vec3 c=mix(meadow,litter,forest);
    if(gravel>0.005){
        c=mix(c,texture(riverbed_tex,uv*1.14).rgb,gravel);
    }
    if(rock>0.005){
        vec2 side_uv=(abs(wn.x)>abs(wn.z) ? wp.zy : wp.xy)*0.1224;
        float side=smoothstep(0.26,0.58,rock);
        vec3 rock_color=texture(cliff_tex,uv*0.68).rgb;
        if(side>0.01){
            rock_color=mix(rock_color,texture(cliff_tex,side_uv).rgb,side);
        }
        c=mix(c,rock_color,rock);
    }
    c=mix(c,vec3(0.22,0.19,0.14),silt*0.28);
    float macro=0.94+0.08*sin(wp.x*0.095)*cos(wp.z*0.074);
    ALBEDO=c*(1.0-0.22*wet)*macro;
    // A single packed normal+roughness fetch replaces the eight maps used
    // by full PBR, retaining visible near-ground relief on Android.
    vec4 nr=texture(grass_nr,uv);
    vec3 tangent_normal=normalize(mix(vec3(0.0,0.0,1.0),nr.rgb*2.0-1.0,0.42));
    vec3 n=normalize(wn);
    vec3 t=vec3(1.0,0.0,0.0)-n*n.x;
    if(dot(t,t)<0.08){ t=vec3(0.0,0.0,1.0)-n*n.z; }
    t=normalize(t);
    vec3 b=-cross(n,t);
    NORMAL=normalize((VIEW_MATRIX*vec4(normalize(t*tangent_normal.x+b*tangent_normal.y+n*tangent_normal.z),0.0)).xyz);
    ROUGHNESS=clamp(mix(nr.a,0.61,wet),0.48,0.98);
    AO=clamp(UV2.y,0.84,1.0);
}
