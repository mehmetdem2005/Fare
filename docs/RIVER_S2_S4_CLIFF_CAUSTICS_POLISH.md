# River S2/S4 polish: shadows, wet rock and steep cliffs

## Implemented
- For steep bank fragments, the rock PBR image uses dominant-world-axis projected UVs (YZ or XY) with slope-driven blending from the existing XZ projection. It avoids the obvious "rubber band" stretch on vertical riverbanks without 3-axis triplanar's 4–6 extra samples per fragment.
- The cliff normal-map perturbation uses a side-projected world tangent frame when dominant-axis projection is active. The same rock packed roughness is still used.
- Underwater caustics are added to lit ALBEDO rather than EMISSION. Godot built-in material shading now darkens them in tree shadows and dim light, instead of producing unshadowed glowing patches.
- Existing terrain UV2.x river depth and UV2.y static shading stay intact, so all pre-baked chunk geometry/collision/flow files remain valid. No rebake is needed.
- This is a cheap 2-plane/dominant-axis approximation, not a continuous full 3-plane triplanar shader. At some diagonal cliff orientations there may be transitions requiring Android screenshots.
- Integration tests validate shader source and texture paths. Device visual acceptance, GPU load and final color balance remain OPEN.
