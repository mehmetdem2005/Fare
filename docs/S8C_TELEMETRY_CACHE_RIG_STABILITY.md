# S8-C — Long-frame measurement, far-field height, and versioned mouse asset

Date: 2026-11-22. Work branch: feat/river-s0-s1-geomorphology; main game branch protected by workflow discipline.

## Verified repairs
- Previous performance probe ignored _process(delta) > 0.5 seconds. It now retains every positive frame delta, longest observed frame, >50ms and >=500ms event counts. Counters are session-wide; percentiles use a rolling 1,800-frame window. App resume can also produce a large delta and should not be diagnosed as GPU time.
- _height() now bypasses river profile calculations outside world x +/-45m, where the existing S8-B equivalent-height test proves no bank deformation. This also shortens far-away vegetation sampling and border-normal evaluation. The S8 far-terrain regression compares its helper against the original river profile.
- CI uses a committed and Git-blob-pinned 49-bone model instead of downloading an expiring previous workflow artifact. GLB UV/skin tests and actual runtime rig smoke remain mandatory. No mouse mesh, UV, skin or animation asset is edited.

## Not yet solved
- New chunk collider/mesh/foliage generation is still synchronous on the main thread; avoid claiming hitch-free loading. Real cold-cache phone traces and p95/p99 still required before introducing threading/incremental stream changes.
- Real Android 11 Mali Vulkan screenshots, waterline, swimming animation, low/high water LOD, thermal, RAM and sound quality require device testing.
- The diagnostics APK is test-only. Keep PR #2 draft; leave the original game branch untouched.
