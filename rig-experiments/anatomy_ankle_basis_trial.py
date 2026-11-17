"""Remove the documented right ankle Basis penetration without changing connectivity."""
import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

import bpy

ANKLE_POCKET = 9440
OPPOSING_TRIANGLE = (9534, 9855, 9335)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    source = args.source.resolve()
    args.out.mkdir(parents=True, exist_ok=True)
    backup = (args.out / "input_before_basis_ankle_trial.blend").resolve()
    output = (args.out / "ANKLE_BASIS_TRIAL_UNAPPROVED.blend").resolve()
    if source in (backup, output):
        raise ValueError("Use a separate output directory")
    shutil.copy2(source, backup)
    bpy.ops.wm.open_mainfile(filepath=str(source))
    mesh = bpy.data.objects["Mouse"].data
    if len(mesh.vertices) != 19466 or not mesh.shape_keys:
        raise ValueError("Expected the Fare Basis and its existing shape keys")
    basis = mesh.shape_keys.key_blocks[0]
    a, b, c = [basis.data[i].co.copy() for i in OPPOSING_TRIANGLE]
    normal = (b - a).cross(c - a).normalized()
    vertex = basis.data[ANKLE_POCKET].co.copy()
    signed_distance = (vertex - a).dot(normal)
    if not -.0001 < signed_distance < 0:
        raise ValueError("Expected the documented vertex just behind the opposing triangle")
    offset = normal * (.00065 - signed_distance)
    original_points = [(key, key.data[ANKLE_POCKET].co.copy()) for key in mesh.shape_keys.key_blocks]
    for key, co in original_points:
        key.data[ANKLE_POCKET].co = co + offset
    mesh.vertices[ANKLE_POCKET].co = vertex + offset
    bpy.ops.wm.save_as_mainfile(filepath=str(output), compress=True)
    (args.out / "ankle_basis_trial.json").write_text(json.dumps({
        "source_sha256": hashlib.sha256(backup.read_bytes()).hexdigest(),
        "trial_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "vertex": ANKLE_POCKET,
        "opposing_triangle": OPPOSING_TRIANGLE,
        "basis_signed_distance_before": signed_distance,
        "basis_signed_distance_after": (vertex + offset - a).dot(normal),
        "offset": list(offset),
    }, indent=2) + "\n")


if __name__ == "__main__":
    main()
