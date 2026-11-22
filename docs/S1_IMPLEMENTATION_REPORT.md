# S1 implementation audit — November 22 2026

## Scope implemented
- Catmull–Rom spline, tangent, signed shore distance and curvature, same global coordinates across all 40m chunks.
- Variable left/right half-widths; shallow reach at z~20, deeper reach around z~100, inner sediment shelf and outer-bank scour.
- Water height decreases monotonically downstream, shoreline depth=0, C1 terrain blending across 5.2m outer bank.
- Terrain height and material mask sourced from the same profile; old fixed sine shoreline texture mask replaced.
- Single water surface clipped into negative-X and positive-X owning chunks to avoid duplicate overlapping geometry.
- River corridor adaptive X terrain samples approximately 0.38m; global Z sample spacing ~0.714m. Far ground coarser.
- Collider created from visible terrain mesh; vertex normals computed from geometry, boundary normals world-sampled to reduce seams.
- Original GLB, rig, animation and input preserved. Poly Haven four diffuse assets remain available.

## Evidence
- CI first geometry test: https://github.com/mehmetdem2005/Fare/actions/runs/45021693424
  S1 334 sampled points passed, MouseRig 49, touch/camera/fall smoke passed.
- CI optimized geometry test: https://github.com/mehmetdem2005/Fare/actions/runs/45021840141
  RIVER_S1_OK samples=1534 shoal=0.0554483m pool=1.195149m seam=ok
  SMOKE_OK rig=49 touch_walk=0.7169m camera_orbit=ok ground_up=ok freefall=3.0746m textures=4
- Approximate smoke elapsed from runner log 7s (initial) to 3s (optimized).
- Additional bank COLLIDER sampling added for follow-up CI: compare render and collision at 12 bank/underwater positions.

## Not implemented — absolutely not claim done
- S0 actual Android golden screenshots, device GPU baseline, thermal.
- S1 final Android visual approval, full near-shore 0.10–0.25m patch target, complex custom overhangs.
- S2 actual polyhaven roughness/normal maps and 3D sediment distributions. Current shoreline gravel color is transitional.
- S3 obstacle-derived physically aligned foam and flow.
- S4 absorption, safe refraction, caustics; existing simple sine water shader remains temporary.
- S5 atmosphere and time-of-day.
- S6 buoyancy/swimming/underwater camera.
- S7 spatial audio/micro events.
- S8 mobile benchmark and release decision.

## Known technical risks to verify on Android
- First-load mesh creation time and memory across 25 chunks.
- Visible shoreline y seams caused by raster tessellation; numeric SDF alone cannot prove visual correctness.
- Old water shader still draws regular parallel sine waves.
- Forest assets are still intentionally low-poly, not final photorealism.
- Android shader derivatives/depth copies remain completely unmeasured.
