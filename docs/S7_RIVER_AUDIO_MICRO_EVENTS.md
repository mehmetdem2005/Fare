# S7 — River soundscape and close-range micro events (first implementation)

## Build-time original sound samples
\`tools/build_river_audio.py\` creates three deterministic, 7-second, 22,050 Hz mono 16-bit WAV loops; no copyright-protected/stock sounds and no per-frame runtime sound synthesis.
- \`river_calm.wav\` flowing current
- \`river_rapids.wav\` rapids around rocks (S3 turbulence affects volume)
- \`river_drops.wav\` reserved for future entry droplets and bite-size transitions

## Spatial sound
\`RiverSoundscape.gd\` places only two AudioStreamPlayer3D emitters near the actual river/stone region in the camera's world slice. Their volume derives from river distance and S3 speed/turbulence. A dedicated FareRiver AudioServer bus holds one AudioEffectLowPassFilter. The camera's S6 waterline/hysteresis signal smoothly changes cutoff from 16kHz to ~1.15kHz underwater. Master bus is unchanged.

## Flow linked micro-life
\`RiverMicroEffects.gd\`: 12 deterministic yellow/green leaves advection by S3 field, one MultiMesh draw; 16 reusable wet footstep circles on real terrain, fading after 5s; 8 reused tiny underwater bubbles/exit droplets in another MultiMesh. No unbounded new MeshInstance allocations during update. Effects follow S6 water/immersion and terrain height.

## Limitations, not done
- The audio is algorithmically generated water-like noise; professional Foley recordings and perceptual listening validation are not included. Dedicated drop sound trigger/crossfades, bird/wind/vegetation beds remain future polish.
- Leaf collisions with individual obstacle mesh aren't simulated; S3 velocity approximation is used.
- Footprints are lightweight planes, not PBR decals or footprint deformation. Android terrain intersection, actual wet fur aesthetics and materials need visual QA.
- Godot headless tests verify logic and source count, NOT audio quality on Android hardware or visual believability.
- S8 Android p95/p99 FPS/heat, sound power usage and shadow cost remain mandatory.
