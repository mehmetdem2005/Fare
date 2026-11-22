# S7-B — Mouse-scale footprints and hydrodynamic leaf heading

- The earlier wet footprint was a plain rectangular PlaneMesh. The new shared, prebuilt ArrayMesh contains one irregular large palm and four separated toe pads, 8 sectors each. 16 pooled instances reuse this single 40-triangle mesh and one material.
- Each footprint follows the actual land normal and animal heading, not the horizon or global north. No extra textures, decals, particle emitters or per-frame object allocation.
- Water leaves now orient along local v2 stream velocity and gently oscillate on a single low-frequency phase; static leaf headings no longer reveal the fake animation. S3 rocks push leaves around collider footprints.
- The 49-bone original mouse rig, 5x5 RAM chunk window, 25 precompiled meshes and all shader material resource schemas are unchanged.
- Android screenshots still required for scale, alpha, blending and true water interaction acceptance.
