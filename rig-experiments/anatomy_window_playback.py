"""Sample timeline playback from a Blender window, at 24 and 8 FPS."""
import json
import sys
import time
from pathlib import Path

import bpy

output = Path(sys.argv[sys.argv.index("--") + 1])
scene = bpy.context.scene
scene.sync_mode = "NONE"
scene.frame_start = 1
scene.frame_end = 24
screens = bpy.context.window_manager.windows
window = screens[0]
view = next(area for area in window.screen.areas if area.type == "VIEW_3D")
region = next(region for region in view.regions if region.type == "WINDOW")
results = {}
rates = (24, 8)
started = None
samples = []


def play():
    global started
    index = len(results)
    if index == len(rates):
        output.write_text(json.dumps(results, indent=2) + "\n")
        bpy.ops.wm.quit_blender()
        return None
    fps = rates[index]
    if started is None:
        scene.render.fps = fps
        scene.frame_set(1)
        with bpy.context.temp_override(window=window, area=view, region=region):
            bpy.ops.view3d.view_axis(type="RIGHT")
            bpy.ops.screen.animation_play()
        started = time.monotonic()
    elapsed = time.monotonic() - started
    if not samples or scene.frame_current != samples[-1][1]:
        samples.append((elapsed, scene.frame_current))
    if elapsed > 4.5:
        with bpy.context.temp_override(window=window, area=view, region=region):
            bpy.ops.screen.animation_cancel(restore_frame=False)
        results[fps] = {"elapsed": elapsed, "unique_frames": sorted({frame for _, frame in samples}),
                        "samples": samples.copy()}
        samples.clear()
        started = None
    return .02


bpy.app.timers.register(play, first_interval=1.0)
