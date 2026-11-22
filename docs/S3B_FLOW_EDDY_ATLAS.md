# S3-B — Flow v2, recirculation and binary atlas coherence

- Old flow contained bow turbulence and foam behind stones but no local return stream. Two weak, bounded counter-rotating vortices now form behind deterministic boulders. Local downstream drift may briefly reverse in the narrow wake, never across the whole channel.
- Velocity is clamped to 2.5 m/s and turbulence/foam receive wake-based contributions. The same CPU flow field moves S6 mouse physics, S7 floating leaves, S7 rapids audio and the S3 GPU shader.
- IMPORTANT: Existing 25 terrain/collision packs are version v3 and already contain OLD v1 flow images. No full 25-chunk rebake. RiverFlowAtlasCache prefers separate res://assets/river_flow_v2/ for 10 river chunks in 5x5 spawn region, otherwise user://river_flow_v2/ for later exploration; on a true cache miss, builds deterministically once then writes.
- Old v3 terrain/collision and water mesh assets are reused; they still save an embedded flow image, but the runtime renderer explicitly ignores that old field in favor of flow v2. User flow cache limited to 100 resources.
- CI verifies actual 10 packed v2 images, CPU atlas pixel agreement and active river GPU material image matches v2. Still requires real mobile water appearance/performance testing.
