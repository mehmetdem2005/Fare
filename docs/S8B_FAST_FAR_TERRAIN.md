# S8-B — Cheap deterministic far terrain CPU path

The world currently generates unseen distant chunks on-demand. A Linux CI stress test measured as high as 409ms in one chunk creation; this is NOT an Android timing but warns of main-thread hitching.

We added a precise shortcut for world x outside +/-45m. All riverbanks, bank transitions and erosion are within that coordinate range; original ground_sample() would have returned base terrain with no river masks there. We now compute the exact same base height and the same far-forest vertex-color mask directly, without repeated expensive spline/SDF/per-vertex sediment evaluations. A test samples actual generated mesh against the old exact formula.

Pine and grass placement now skips RiverProfile.shore_distance() for far x as well (same original selection). Terrain and water triangle index buffers now use six direct appends per cell, not one temporary PackedInt32Array allocation per quad.

This keeps the original 25 baked chunk resources, 49-bone rig, S3 v2 flow atlas and all LOD thresholds intact; only uncached new generation is optimized. Chunk collider and scene attachment still require main-thread work; true zero-stutter streaming is NOT claimed. Compare cold-cache Android frame p95/p99 before declaring improved performance.
