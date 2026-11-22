# Fare Vadisi — Godot 4.7.2 Mobile

Clean branch in `mehmetdem2005/Fare`. Original mouse GLB assets are copied from the user's existing repository as **unchanged Git objects**; no hand-rolled GLB re-export or double V-flipping.

## Features
- Third-person 3D mouse; 49-bone corrected mouse with real imported Blender sprint animation and corrective shape keys, jumping and stamina.
- Landscape Android on Godot 4.7.2 Mobile renderer; multitouch joystick, camera drag and two action buttons.
- 40m procedural terrain chunks loaded/unloaded around the player, continuous noise-driven valley and mountain ridges.
- Flowing winding river, translucent animated water shader, pebble shore and low-poly pine forest.
- True **Poly Haven CC0** grass, forest ground, rock and river pebbles, downloaded by `tools/fetch_polyhaven.py` or bundled by GitHub Actions.
- Godot scene import and runtime smoke test in Actions.

## How to play
In Godot 4.7.2, import `project.godot`. On Android use joystick on lower left, swipe the right half to orbit, KOS to sprint, ZIPLA to jump. Keyboard: WASD, Shift, Space; left mouse can simulate touch controls.

## Texture origins (CC0)
- [Grass Ground](https://polyhaven.com/a/grass_ground)
- [Grass Path 2](https://polyhaven.com/a/grass_path_2)
- [Rocks Ground 09](https://polyhaven.com/a/rocks_ground_09)
- [River Small Rocks](https://polyhaven.com/a/river_small_rocks)

The `tools/fetch_polyhaven.py` script retrieves official file URLs through `api.polyhaven.com/files/<asset>` and stores 1024x1024 mobile-sized copies. A green workflow means textures were downloaded AND the game scene loaded in headless Godot.

## Asset safety / remaining limits
- The 49-bone GLB is reused from the repository's previously Blender-exported `deliver/mouse_rigged.glb`, NOT the flawed user-facing V2/V3 custom glTF reconstruction. A clean original mesh `source/mouse3dmodel1k.glb` is bundled as fallback.
- The included genuine Blender action is a corrected **sprint** cycle. Walk currently slows this clip; dedicated walk/idle/jump action clips remain future work. Anatomical review still has open issues at extreme poses.
- Android GPU/device playtesting must still be done in the Android Godot editor. Headless CI checks scripts and scene imports, not on-device visual correctness.
- The Godot Mobile renderer uses simple depth fog rather than unsupported volumetric fog.
