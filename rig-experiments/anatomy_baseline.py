"""Read-only Blender diagnosis for the Fare sprint. Writes evidence outside the input."""
import argparse
import hashlib
import json
import runpy
import sys
from collections import Counter
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import intersect_ray_tri

HERE = Path(__file__).resolve().parent
ACTION = "run_sprint_v8_ik_phase_NUMERIC_REVIEW"
VIEWS = {
    "left": (1, 0, 0), "right": (-1, 0, 0), "front": (0, -1, 0),
    "back": (0, 1, 0), "top": (0, 0, 1), "bottom": (0, 0, -1),
    "three_quarter": (1, -1, .55),
}
SENTINELS = {
    216: (2018, 1402, 1389), 351: (1317, 703, 980), 434: (218, 270, 586),
    465: (774, 586, 879), 467: (671, 774, 731), 809: (7231, 7045, 7390),
    812: (7562, 7390, 7772),
}


def array(points):
    return np.asarray(points, dtype=np.float64)


def normals(points, tris):
    a, b, c = points[tris].transpose(1, 0, 2)
    return np.cross(b - a, c - a)


def crossing(triangle_a, triangle_b):
    """Witness a non-coplanar intersection on a finite triangle edge."""
    for source, target in ((triangle_a, triangle_b), (triangle_b, triangle_a)):
        for index, start in enumerate(source):
            edge = source[(index + 1) % 3] - start
            if edge.length_squared < 1e-18:
                continue
            point = intersect_ray_tri(*target, edge, start, True)
            if point is not None:
                fraction = (point - start).dot(edge) / edge.length_squared
                if -1e-6 <= fraction <= 1 + 1e-6:
                    return list(point)
    return None


def render(scene, camera, frame, name, direction, center, scale, output):
    camera.location = Vector(center) + Vector(direction).normalized() * 3
    camera.rotation_euler = (Vector(center) - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.ortho_scale = scale
    scene.render.filepath = str(output / f"{name}_{frame:02}.png")
    bpy.ops.render.render(write_still=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--action", default=ACTION)
    parser.add_argument("--action-source", type=Path)
    parser.add_argument("--rest-only", action="store_true")
    parser.add_argument("--full-body-intersections", action="store_true")
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--stage-probes", action="store_true",
                        help="Measure pre-armature samples and sprint half-frames")
    parser.add_argument("--expected-bones", type=int, default=49)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    output = args.out.resolve()
    output.mkdir(parents=True, exist_ok=True)
    helpers = runpy.run_path(str(HERE / "round14_skinning_forensics.py"))
    anatomy = runpy.run_path(str(HERE / "round11_rootcause.py"))
    bpy.ops.wm.open_mainfile(filepath=str(args.source.resolve()))
    obj = bpy.data.objects["Mouse"]
    modifier = next(m for m in obj.modifiers if m.type == "ARMATURE")
    arm = modifier.object
    scene = bpy.context.scene
    arm.animation_data_create()
    for track in arm.animation_data.nla_tracks:
        track.mute = True
    if args.action_source:
        with bpy.data.libraries.load(str(args.action_source.resolve())) as (source, target):
            if args.action not in source.actions:
                raise ValueError(f"Missing action in {args.action_source}")
            target.actions = [args.action]
        action = target.actions[0]
    else:
        action = None if args.rest_only else bpy.data.actions[args.action]
    rois = anatomy["collect"](obj, arm, args.expected_bones)
    rest = array([obj.matrix_world @ v.co for v in obj.data.vertices])
    polygons = []
    tris = []
    for poly in obj.data.polygons:
        ids = tuple(poly.vertices)
        if not all(i in rois["interleg"] for i in ids):
            continue
        for j in range(1, len(ids) - 1):
            tri = (ids[0], ids[j], ids[j + 1])
            if np.linalg.norm(normals(rest, np.array([tri]))[0]) > 2e-7:
                polygons.append(poly.index)
                tris.append(tri)
    for index, expected in SENTINELS.items():
        if tris[index] != expected:
            raise ValueError(f"Legacy triangle {index}: {tris[index]} != {expected}")
    tri = np.array(tris)
    reference = normals(rest, tri)
    areas = np.linalg.norm(reference, axis=1)
    edge_counts = Counter(tuple(sorted(edge)) for poly in obj.data.polygons for edge in poly.edge_keys)
    edges = np.array([tuple(e.vertices) for e in obj.data.edges])
    edge_lengths = np.linalg.norm(rest[edges[:, 1]] - rest[edges[:, 0]], axis=1)
    roi_edges = {name: np.array([i for i, (a, b) in enumerate(edges)
                                if a in ids and b in ids and edge_lengths[i] > .001])
                 for name, ids in rois.items()}
    part = obj.data.attributes["part_id"]
    body_polygons = [p for p in obj.data.polygons if all(part.data[i].value == 6 for i in p.vertices)]
    body_edges = Counter(tuple(sorted(edge)) for p in body_polygons for edge in p.edge_keys)
    body_closed = bool(body_edges) and all(count == 2 for count in body_edges.values())
    obj.data.calc_loop_triangles()
    body_tris = np.array([t.vertices[:] for t in obj.data.loop_triangles
                          if all(part.data[i].value == 6 for i in t.vertices)])
    body_rest_areas = np.linalg.norm(normals(rest, body_tris), axis=1)
    valid_body_areas = body_rest_areas > 2e-7
    body_tri_list = body_tris.tolist()
    def body_intersections(points):
        tree = BVHTree.FromPolygons(points, body_tri_list, all_triangles=True)
        candidate_count = 0
        shared_vertex_count = 0
        witnesses = []
        for i, j in sorted(tree.overlap(tree)):
            if i >= j:
                continue
            a, b = body_tri_list[i], body_tri_list[j]
            if set(a).intersection(b):
                shared_vertex_count += 1
                continue
            candidate_count += 1
            point = crossing([points[v] for v in a], [points[v] for v in b])
            if point is not None:
                witnesses.append({"triangles": [i, j], "vertices": [a, b], "world_point": point})
        return {"bvh_disjoint_candidates": candidate_count, "shared_vertex_overlaps": shared_vertex_count,
                "noncoplanar_intersection_witnesses": witnesses}

    def signed_body_volume(points):
        a, b, c = points[body_tris].transpose(1, 0, 2)
        return float(np.einsum("ij,ij->", a, np.cross(b, c)) / 6)
    rest_volume = signed_body_volume(rest) if body_closed else None
    paw_parts = {label: np.array([v.index for v in obj.data.vertices if part.data[v.index].value == tag])
                 for label, tag in {"fore_right": 2, "fore_left": 3, "hind_right": 7, "hind_left": 8}.items()}
    weights = [helpers["weights"](obj, i) for i in range(len(rest))]
    report = {
        "sha256": hashlib.sha256(args.source.read_bytes()).hexdigest(),
        "action_source_sha256": hashlib.sha256(args.action_source.read_bytes()).hexdigest() if args.action_source else None,
        "blender": bpy.app.version_string,
        "action": action.name if action else None,
        "basis_vertices": len(rest),
        "boundary_edges": sum(c == 1 for c in edge_counts.values()),
        "nonmanifold_edges": sum(c > 2 for c in edge_counts.values()),
        "body_boundary_edges": sum(count == 1 for count in body_edges.values()),
        "body_nonmanifold_edges": sum(count > 2 for count in body_edges.values()),
        "body_basis_signed_volume": rest_volume,
        "legacy_triangles": len(tris),
        "legacy_triangle_vertices": tris,
        "rest_bones": anatomy["bone_map"](obj, arm, rois),
        "sentinels": {
            i: {"polygon": polygons[i], "vertices": ids, "rest_centroid": rest[list(ids)].mean(axis=0).tolist(),
                "regions": [name for name, mask in rois.items() if set(ids) <= mask],
                "weights": {v: weights[v] for v in ids}}
            for i, ids in SENTINELS.items()
        },
        "samples": [],
    }
    (output / "vertex_weights.json").write_text(json.dumps(weights))
    if args.render:
        camera = bpy.data.objects.new("Anatomy inspection camera", bpy.data.cameras.new("Anatomy inspection camera"))
        scene.collection.objects.link(camera)
        scene.camera = camera
        camera.data.type = "ORTHO"
        scene.render.engine = "BLENDER_WORKBENCH"
        scene.render.resolution_x = scene.render.resolution_y = 512
        scene.render.resolution_percentage = 100
        scene.render.image_settings.file_format = "PNG"
        scene.display.render_aa = "FXAA"
        shading = scene.display.shading
        shading.color_type = "SINGLE"
        shading.single_color = (.54, .53, .51)
        shading.light = "STUDIO"
        shading.show_cavity = True
        shading.cavity_type = "WORLD"
        shading.show_shadows = False
    if args.rest_only:
        arm.data.pose_position = "REST"
        for key in list(obj.data.shape_keys.key_blocks)[1:]:
            key.mute = True
    if args.stage_probes:
        report["stage_probes"] = []
    first = None
    for frame in [1] if args.rest_only else range(1, 26):
        helpers["reset"](arm, action, frame)
        points = helpers["pts"](obj)
        xyz = array(points)
        posed_normals = normals(xyz, tri)
        posed_areas = np.linalg.norm(posed_normals, axis=1)
        rotation = arm.matrix_world @ arm.pose.bones["spine_03"].matrix @ arm.data.bones["spine_03"].matrix_local.inverted() @ arm.matrix_world.inverted()
        corotated = reference if args.rest_only else reference @ array(rotation.to_quaternion().to_matrix()).T
        orientation = np.einsum("ij,ij->i", posed_normals, corotated) / np.maximum(areas * posed_areas, 1e-25)
        tree = BVHTree.FromPolygons(points, tris, all_triangles=True)
        pairs = [(i, j) for i, j in tree.overlap(tree) if i < j and not set(tris[i]).intersection(tris[j])]
        crossings = [
            {"triangles": [i, j], "world_point": point}
            for i, j in sorted(pairs)
            if (point := crossing([points[v] for v in tris[i]], [points[v] for v in tris[j]])) is not None
        ]
        strain = np.abs(np.linalg.norm(xyz[edges[:, 1]] - xyz[edges[:, 0]], axis=1) / np.maximum(edge_lengths, 1e-15) - 1)
        if first is None:
            first = xyz
        ratio = posed_areas / areas
        report["samples"].append({
            "frame": frame, "min_area_ratio": float(ratio.min()), "under_half": int((ratio < .5).sum()),
            "worst_triangles": [
                {"triangle": int(i), "vertices": tris[i], "polygon": polygons[i],
                 "rest_centroid": rest[list(tris[i])].mean(axis=0).tolist(), "area_ratio": float(ratio[i])}
                for i in np.argsort(ratio)[:10]
            ],
            "negative_corotated_normal": np.flatnonzero(orientation < 0).tolist(),
            "bvh_pairs": sorted(pairs),
            "noncoplanar_intersection_witnesses": crossings,
            "p95_edge_strain": {n: float(np.quantile(strain[ei], .95)) for n, ei in roi_edges.items()},
            "sentinels": {i: {"area_ratio": float(ratio[i]), "normal_cosine": float(orientation[i])} for i in SENTINELS},
            "body_signed_volume": signed_body_volume(xyz) if body_closed else None,
            "paws": {name: {"lowest_z": float(xyz[ids, 2].min()),
                            "sole_centroid": xyz[ids[np.argsort(xyz[ids, 2])[:max(1, len(ids) // 10)]]].mean(axis=0).tolist()}
                     for name, ids in paw_parts.items()},
            "pose_matrices": {b.name: array(b.matrix).tolist() for b in arm.pose.bones},
            "shape_keys": {k.name: float(k.value) for k in list(obj.data.shape_keys.key_blocks)[1:]},
        })
        if args.full_body_intersections:
            body_areas = np.linalg.norm(normals(xyz, body_tris), axis=1)
            body_ratios = body_areas[valid_body_areas] / body_rest_areas[valid_body_areas]
            report["samples"][-1]["body_surface"] = {
                "min_area_ratio": float(body_ratios.min()),
                "under_half": int((body_ratios < .5).sum()),
                **body_intersections(points),
            }
        if args.stage_probes and not args.rest_only and frame in (1, 7, 8, 9, 10, 14, 16, 17, 18, 19, 20, 25):
            upstream = helpers["get_input"](obj, modifier)
            report["stage_probes"].append({"frame": frame, "subframe": 0, "stage": "before_armature",
                                           **body_intersections(upstream)})
            if frame < 25:
                scene.frame_set(frame, subframe=.5)
                midpoint = helpers["pts"](obj)
                report["stage_probes"].append({"frame": frame, "subframe": .5, "stage": "after_armature",
                                               **body_intersections(midpoint)})
                scene.frame_set(frame)
        if args.render:
            for name, direction in VIEWS.items():
                render(scene, camera, frame, name, direction, (0, -.02, .23), 1.48, output)
            for name, direction, roi in (
                ("chest_left", (1, -.25, -.4), "front"),
                ("chest_right", (-1, -.25, -.4), "front"),
                ("belly", (0, 0, -1), "interleg"),
                ("hip_left", (1, .25, -.4), "rear"),
                ("hip_right", (-1, .25, -.4), "rear"),
            ):
                center = rest[sorted(rois[roi])].mean(axis=0)
                render(scene, camera, frame, name, direction, center, .56, output)
    report["endpoint_max_vertex_delta"] = float(np.linalg.norm(xyz - first, axis=1).max())
    if not args.rest_only:
        scene.frame_set(1, subframe=.01)
        after_start = array(helpers["pts"](obj))
        scene.frame_set(24, subframe=.99)
        before_end = array(helpers["pts"](obj))
        incoming = (xyz - before_end) / .01
        outgoing = (after_start - first) / .01
        report["seam_velocity_max_delta_per_frame"] = float(np.linalg.norm(outgoing - incoming, axis=1).max())
        report["seam_velocity_p95_delta_per_frame"] = float(np.quantile(np.linalg.norm(outgoing - incoming, axis=1), .95))
    (output / "baseline.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
