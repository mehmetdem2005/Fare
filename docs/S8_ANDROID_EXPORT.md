# Fare Vadisi S8 — Android 11 ARM64 Diagnostics APK

This is a **diagnostics debug APK**, not a production or Google Play Store release.

- Engine Godot 4.7.2 stable, Mobile renderer. ARM64-v8a only.
- Official 4.7.2 Android prebuilt export templates on GitHub Actions.
- 25 baked chunks, true 49-bone mouse GLB and PBR sources, S7 sound files.
- A separate test-only app id org.farevadisi.riverdiagnostics avoids normal game installations.
- No Android location, camera, microphone, or Internet permissions are requested by our preset.
- Repo includes export preset, never a private signing key.
- CI generates an **ephemeral debug key**. Debug APKs from different CI runs may not upgrade one another: Android can require uninstalling the previous diagnostics package, which would erase that package's cache and logs. A persistent private signing key is needed for future upgradeable releases.
- CI must verify ZIP integrity, arm64 Godot library, Android manifest, included assets, APK signature, and SHA256.

## Real mobile acceptance
Open the APK on Android 11, wait for chunks, then tap **FPS** in the top-right. Measure p95/p99 frame times and memory with water covering half the screen; cross shallow rapids, swim, return to shore, and walk far enough to force streaming. Repeat after 12 minutes of heat. Tap **KOPYALA** and paste the JSON report into chat. Godot reports frame time and memory, not GPU occupancy or battery temperature.

Do not call the device optimized or the 30 FPS goal met until on-phone measurements and screenshots arrive.
