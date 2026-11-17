"""Test a localized rest-curvature corrective on a saved weight trial."""
import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from anatomy_torso_weight_trial import smoothstep


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    source = args.source.resolve()
    args.out.mkdir(parents=True, exist_ok=True)
    backup = (args.out / "input_before_corrective_smooth.blend").resolve()
    candidate = (args.out / "VENTRAL_SURFACE_TRIAL_UNAPPROVED.blend").resolve()
    if source in (backup, candidate):
        raise ValueError("Use a separate output directory")
    shutil.copy2(source, backup)
    bpy.ops.wm.open_mainfile(filepath=str(source))
    obj = bpy.data.objects["Mouse"]
    parts = obj.data.attributes["part_id"]
    group = obj.vertex_groups.new(name="trial_ventral_surface")
    mask = {}
    for vertex in obj.data.vertices:
        if parts.data[vertex.index].value != 6:
            continue
        x, y, z = vertex.co
        along = smoothstep(-.29, -.16, y) * (1 - smoothstep(.11, .24, y))
        bottom = smoothstep(.035, .08, z) * (1 - smoothstep(.215, .30, z))
        weight = along * bottom * (1 - smoothstep(.165, .209, abs(x)))
        if weight > 1e-5:
            group.add([vertex.index], weight, "REPLACE")
            mask[vertex.index] = weight
    modifier = obj.modifiers.new("Trial ventral rest-curvature preservation", "CORRECTIVE_SMOOTH")
    modifier.vertex_group = group.name
    modifier.factor = .65
    modifier.iterations = 7
    modifier.smooth_type = "LENGTH_WEIGHTED"
    modifier.use_pin_boundary = True
    modifier.rest_source = "ORCO"
    bpy.ops.wm.save_as_mainfile(filepath=str(candidate), compress=True)
    (args.out / "surface_trial.json").write_text(json.dumps({
        "source_sha256": hashlib.sha256(backup.read_bytes()).hexdigest(),
        "trial_sha256": hashlib.sha256(candidate.read_bytes()).hexdigest(),
        "changed_vertex_mask": mask,
    }, indent=2) + "\n")


if __name__ == "__main__":
    main()
