# S4/S6/S7 waterline polish (Godot 4.7.2 Mobile)

- S4 shader uses verified FRONT_FACING on one cull-disabled river mesh. The underside refracts in muted mineral-green colors without fake upside-down sky Fresnel, top-side glitter, white foam or surface caustic glitter. No second water mesh and no new screen pass.
- S6 paw/wake ripple placement now clamps its final point to the actual signed-shoreline profile; if the actor leaves the river, the final exit ring appears at the last wet point, never a dry bank.
- S7 leaves follow the NEW S3 vortex field and additionally resolve contacts with physical boulders. Wet prints orient to the real terrain normal from a tiny height finite-difference sample, rather than floating parallel to the horizon.
- Existing 12 ring / 12 leaf / 16 footprint / 8 droplet budgets unchanged. Robot-looking repetitive wave motion not reintroduced.
- Device screenshots and Mali GPU timings are still necessary; headless Godot shader import cannot prove transparent-water aesthetics or the actual underwater camera image.
