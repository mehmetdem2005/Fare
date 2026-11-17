"""Compare local knee weighting and native volume preservation on the same sprint."""
import argparse
import sys
from pathlib import Path

import bpy


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--mode", choices=("weights", "sharpen", "volume"), required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    if args.source.resolve() == args.out.resolve() or args.out.exists():
        raise ValueError("Supply a new output path")
    bpy.ops.wm.open_mainfile(filepath=str(args.source.resolve()))
    mesh = bpy.data.objects["Mouse"]
    armature = next(mod for mod in mesh.modifiers if mod.type == "ARMATURE")
    if args.mode == "volume":
        armature.use_deform_preserve_volume = True
    else:
        thigh, shin = (mesh.vertex_groups[name] for name in ("thigh.R", "shin.R"))
        neighbors = [set() for _ in mesh.data.vertices]
        for edge in mesh.data.edges:
            a, b = edge.vertices
            neighbors[a].add(b)
            neighbors[b].add(a)
        seeds = {10364, 10312, 10533, 10927, 10501, 10258}
        distance = {i: 0 for i in seeds}
        frontier = seeds
        for step in range(1, 6):
            frontier = {j for i in frontier for j in neighbors[i]} - distance.keys()
            distance.update(dict.fromkeys(frontier, step))
        weights = [{g.group: g.weight for g in v.groups} for v in mesh.data.vertices]
        totals = [w.get(thigh.index, 0) + w.get(shin.index, 0) for w in weights]
        fractions = {i: weights[i].get(shin.index, 0) / total
                     for i, total in enumerate(totals) if total > .25}
        region = distance.keys() & fractions.keys()
        smooth = fractions.copy()
        for _ in range(5):
            update = {}
            for i in region:
                values = [smooth[j] for j in sorted(neighbors[i]) if j in fractions]
                if values:
                    strength = .55 * (1 - distance[i] / 5)
                    update[i] = smooth[i] + strength * (sum(values) / len(values) - smooth[i])
            smooth.update(update)
        for i in sorted(region):
            fraction = smooth[i]
            if args.mode == "sharpen":
                fraction = min(1, max(0, 2 * fractions[i] - fraction))
            if fraction != fractions[i]:
                shin.add([i], totals[i] * fraction, "REPLACE")
                thigh.add([i], totals[i] * (1 - fraction), "REPLACE")
    bpy.ops.wm.save_as_mainfile(filepath=str(args.out.resolve()), compress=True)


if __name__ == "__main__":
    main()
