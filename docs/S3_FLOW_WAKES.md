# S3 flow and causal foam — initial system

## Implemented
- `RiverObstacles`: deterministic world-space boulders, reused for visible/collision stones and water solver; no foam from invisible rocks.
- `RiverFlowField.sample`: downstream tangent motion, velocity attenuation at banks, rock bow stagnation, side acceleration, downstream wake/turbulence and source-based foam intensity.
- 32x32 per-chunk RGBA8 GPU atlas containing signed velocity in RG, turbulence B, foam A; world-space encodings round-trip to CPU.
- `shaders/river.gdshader`: flow-aligned moving surface, locally gated foam, no straight global sine Z bands. Existing simple optical color remains temporary.
- `tests/river_s3_test.gd`: no flow outside banks, downstream motion, matched physical obstacle visuals and atlas color error.

## Not complete
- Water physic force on player deferred to S6; at this stage same flow field is available.
- Near-field true fluid volume/wake simulation deferred, only deterministic analytical representation.
- Rock model quality/LOD and Android GPU metrics not validated.
- S4 depth absorption/Fresnel/refraction/caustics not implemented, intentionally.
