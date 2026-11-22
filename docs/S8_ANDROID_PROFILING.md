# S8 — Android instrumented profiling

## On-phone diagnostics (code implementation)
Tap **FPS** in the upper-right corner of Fare Vadisi. The compact panel shows sampled FPS and 95th/99th percentile frame intervals, current reported draw calls and Godot-reported static/video memory, active chunk count, number of loaded versus generated chunks, and worst observed per-chunk creation / user-cache save durations.

Tap **KOPYALA** to place the report JSON on Android's clipboard and paste it into chat. Tap **JSON KAYDET** to write to user://perf_reports/fare-s8-yyyy-mm-ddThh-mm-ss.json. This data stays on the phone; it is not uploaded automatically.

The panel also reports the longest observed frame and session-wide counts of >50ms and >=500ms intervals. These do not discard long stalls; however, returning from the background can also produce large deltas. p95/p99 still cover the most recent 1,800 render-loop samples.

Important: Godot Performance counters can return zero on release builds. The frame intervals use _process delta, not real GPU timestamps. Do **not** equate these readings with GPU occupancy, power consumption, or thermal throttling. Android screenshots and sustained test are still required.

### Repeatable tests
1. Cold-start and warm-start (without killing the app, walk away from and back to starting area).
2. Wait for all 5×5 chunks to stream; observe max frame time.
3. Stand at near river, slowly rotate the camera so water occupies 50%+ of the frame; record 60s.
4. Cross a rocky shallow area; enter the deep pool; swim upstream and return to shore.
5. Stand under pines in morning and midday; compare shadow visibility and CPU draw calls.
6. Stay for 12 minutes, check p95/p99 and thermal performance; distinguish phone temperature from FPS stutter.
7. Export JSON and provide at least two screenshots with FPS panel visible.

### CI tests (not equivalent to Android)
- \`tests/s8_stream_stress_test.gd\` manually streams to distant z chunks and returns, verifies live 5×5 RAM budget, proper saved/revisited chunk and loading CPU durations.
- \`tests/s8_metrics_test.gd\` checks percentile computation, real game stat plumbing and valid saved JSON.
- Existing S1–S7 physics/shader headless tests still required.

**Do not claim 30 FPS, photorealism, GPU load reduction or acceptable Android temperature without actual hardware measurements.**
