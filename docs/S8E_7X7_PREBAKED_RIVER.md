# S8-E — Expanded prebaked river corridor after Android 8.1 FPS report

The previous Android report at world (21.2, 67.2) recorded 10 generated misses, max chunk 1386.75ms and 283.22ms cache writes. This demonstrates that the original 5x5 **prebaked storage** was too narrow for the explored river corridor; the live 5x5 25-chunk RAM window itself is deliberately not expanded.

- Extend startup offline **packed storage** coordinates from [-2,+2] to [-3,+3], yielding 49 prebuilt 40m chunks. Existing 25 v3 terrain/collision/water/flow resources are kept byte-identical; generate only 24 missing outer coordinates during GitHub CI.
- Extend prepacked new S3 v2 vortex atlases from 10 to 14 x/z river cells so water physics and GPU flow continue to match without runtime baking near outer water.
- Preserve user's persistent disk cache and 25 live chunk window, quality tier, mouse rig, camera, collision, geometry/UVs and texture set.
- On that route, chunk z=3 now loads from res:// pack instead of being generated. Outside [-3,+3], generation may still cause blocking; this is a **bounded prebake improvement**, not an infinite-world async streaming fix.
- CI regression checks every one of the 49 chunk resources and 14 v2 flow atlas fields. APK file size will grow; exact byte size comes from the new Actions artifact. User tests 12-min warm run and cold exploration again; do not call hitch-free or 30 FPS without real Android results.

The actual GPU render scale and main-thread time are independently measured by S8-D. A green CI can verify packed assets but not Mali Vulkan visual quality.
