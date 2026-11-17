"""Build the review CSV and matched comparison sheets from measured evidence."""
import argparse
import csv
import json
from pathlib import Path

from PIL import Image, ImageDraw

CASES = {
    "source-rest": "original-rest",
    "source-and-v8-action": "original-with-v8-action",
    "reproduced-v8": "reproduced-v8",
    "reproduced-r39": "reproduced-r39",
    "parent-and-v8-action": "current-with-v8-action",
    "parent-sprint": "current-sprint",
    "knee-narrow": "knee-pose-trial-sprint",
    "knee-broad": "knee-broad-sprint",
    "shoulder": "shoulder-pose-sprint",
    "preview": "taubin-delivery-sprint",
}


def sheet(output, paths, columns, side=256):
    rows = (len(paths) + columns - 1) // columns
    row_height = side + 22
    image = Image.new("RGB", (columns * side, rows * row_height), (32, 32, 32))
    draw = ImageDraw.Draw(image)
    for i, (label, path, overlay) in enumerate(paths):
        x, y = i % columns * side, i // columns * row_height
        with Image.open(path) as panel:
            image.paste(panel.convert("RGB").resize((side, side), Image.Resampling.LANCZOS), (x, y + 20))
        draw.text((x + 6, y + 4), label, fill="white")
        for triangle, color in zip(overlay, ("#f59636", "#39c6ff")):
            pixels = [(x + u * side, y + 20 + (1 - v) * side) for u, v in triangle]
            draw.line(pixels + pixels[:1], fill=color, width=2)
            for a, b in pixels:
                draw.ellipse((a - 2, b - 2, a + 2, b + 2), fill=color)
    image.save(output, quality=90)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    rows, inventory = [], {}
    for case, folder in CASES.items():
        data = json.loads((args.evidence / folder / "baseline.json").read_text())
        inventory[case] = {"source_sha256": data["sha256"], "action": data["action"],
                           "action_source_sha256": data["action_source_sha256"],
                           "endpoint_max_vertex_delta": data["endpoint_max_vertex_delta"], "frames": {}}
        for frame in data["samples"]:
            step = frame["frame"]
            contacts = frame["body_surface"]["noncoplanar_intersection_witnesses"]
            legacy = frame["noncoplanar_intersection_witnesses"]
            rows.append({"case": case, "frame": step, "cycle_closure": step == 25,
                         "part6_pairs": len(contacts), "interleg_pairs": len(legacy),
                         "min_area_ratio": frame["min_area_ratio"],
                         "minimum_paw_z": min(p["lowest_z"] for p in frame["paws"].values()),
                         "sentinel_216_area_ratio": frame["sentinels"]["216"]["area_ratio"],
                         "sentinel_812_area_ratio": frame["sentinels"]["812"]["area_ratio"]})
            inventory[case]["frames"][step] = {"body": contacts, "interleg": legacy, "paws": frame["paws"],
                                               "sentinels": frame["sentinels"]}
    with (args.output / "sprint_frames.csv").open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys(), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    (args.output / "intersection_inventory.json").write_text(json.dumps(inventory, separators=(",", ":")) + "\n")

    current = args.evidence / "current-annotate"
    preview = args.evidence / "taubin-delivery-annotate"
    for region in ("knee", "shoulder", "ankle"):
        paths = []
        for label, folder, mode in (("Parent sprint", current, "sprint"),
                                    ("Preview sprint", preview, "sprint"),
                                    ("Preview Pose Mode", preview, "manual")):
            samples = json.loads((folder / "manual_replay.json").read_text())["samples"]
            for frame in (7, 8, 9):
                overlay = samples[str(frame)][mode]["knee_overlay"] if region == "knee" else []
                paths.append((f"{label} {frame}", folder / f"{mode}_{region}_{frame:02}.png", overlay))
        sheet(args.output / f"{region}_contact_sheet.jpg", paths, 3)

    poses = args.evidence / "taubin-delivery" / "reopened_pose"
    paths = [(path.stem[:-3].replace("_", " "), path, []) for path in sorted(poses.glob("*.png"))]
    sheet(args.output / "pose_sheet.jpg", paths, 5, 220)


if __name__ == "__main__":
    main()
