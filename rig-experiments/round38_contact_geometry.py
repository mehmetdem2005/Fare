"""R38: actual triangle-triangle BVH penetration-pair oriented-plane proposals.

This is an *experimental deterministic* collision-constraint search, not a
claim that nearest-centroid distance alone is a contact witness. BVH overlap
is recomputed after every proposal using real triangles. Candidate vertex
displacements are never accepted without full signed-area and normal guards.
Input is real Blender evaluated frame14 coords, not a synthetic rig.
"""
import numpy as np
from mathutils.bvhtree import BVHTree


def bvh_pairs(points, triangles):
    mesh = BVHTree.FromPolygons(points.tolist(), triangles,
                                all_triangles=True, epsilon=1e-7)
    indices = [set(x) for x in triangles]
    return {(int(a), int(b)) for a, b in mesh.overlap(mesh)
            if a < b and not indices[a].intersection(indices[b])}


def oriented_area(points, tri, rest_area, rest_normal_world):
    idx = np.asarray(tri, dtype=np.int64)
    cross = np.cross(points[idx[:, 1]]-points[idx[:, 0]],
                     points[idx[:, 2]]-points[idx[:, 0]])
    area = np.linalg.norm(cross, axis=1) / rest_area
    signed = np.einsum("ij,ij->i", cross, rest_normal_world) / rest_area
    return area, signed


def geometric_proposal(pts, rest, triangles, new_pairs, editable, contact_gap=.00022):
    """Translate offending *triangle vertices* into the source-verified half-space.

    Compared to moving two arbitrary centroids, each option computes the
    signed distances of all three vertices from the opposing triangle plane.
    The source v8 frame chooses which side is anatomically preserved.
    Only completely movable triangle vertices may undergo a plane-side push;
    no resting outside-ROI vertex is moved. A collision pair may yield no
    feasible proposal: such a result must NOT be labelled repaired.
    """
    d = {}
    reasons = {"uneditable": 0, "mixed_source_halfspace": 0,
               "degenerate_plane": 0, "feasible_contacts": 0}
    for a, b in sorted(new_pairs):
        tr_a = triangles[a]
        tr_b = triangles[b]
        options = []
        for source_face, plane_face in ((tr_a, tr_b), (tr_b, tr_a)):
            i, j, k = plane_face
            surface = np.cross(pts[j]-pts[i], pts[k]-pts[i])
            mag = float(np.linalg.norm(surface))
            if mag < 1e-10:
                reasons["degenerate_plane"] += 1
                continue
            normal = surface/mag
            source_surface = np.cross(rest[j]-rest[i],rest[k]-rest[i])
            source_mag = float(np.linalg.norm(source_surface))
            if source_mag < 1e-10:
                reasons["degenerate_plane"] += 1
                continue
            source_n = source_surface/source_mag
            source_distances = np.array([
                float(np.dot(rest[v]-rest[i],source_n)) for v in source_face])
            # Need the entire triangle on a single source-preserving side.
            if np.max(source_distances) > 1e-6 and np.min(source_distances) < -1e-6:
                reasons["mixed_source_halfspace"] += 1
                continue
            side = 1. if np.mean(source_distances) >= 0 else -1.
            cur = np.array([side*float(np.dot(pts[v]-pts[i],normal))
                            for v in source_face])
            deficiencies=np.maximum(0,contact_gap-cur)
            if np.max(deficiencies)<1e-6:
                continue
            if any(v not in editable and insuff>1e-6
                   for v,insuff in zip(source_face,deficiencies)):
                reasons["uneditable"]+=1
                continue
            cost=float(np.linalg.norm(deficiencies))
            options.append((cost,source_face,normal*side,deficiencies))
        if not options:
            continue
        _,verts,normal,miss=min(options,key=lambda x:x[0])
        reasons["feasible_contacts"]+=1
        for vertex,required in zip(verts,miss):
            if required<=1e-6:continue
            old=d.get(vertex, (np.zeros(3),0))
            d[vertex]=(old[0]+normal*required,old[1]+1)
    if not d:return {},reasons
    proposal={}
    for vertex,(disp,count) in d.items():
        move=disp/count
        length=float(np.linalg.norm(move))
        if length>0:
            move*=min(0.0012/length,1.)
            proposal[vertex]=move
    return proposal,reasons


def solve_contacts(initial, source, triangles, rest_areas, oriented_rest_norm,
                   editable, base_pairs=None, max_world_change=.007,
                   max_iterations=55):
    """Run reproducible local collision corrections with hard anatomy safety.

    Source refers to the original v8 f14 geometry, not a mesh rest pose.
    Checks the *same* 1069 triangles as the full rig evaluator.
    Refuses to increase source under-half triangles or create new reference
    inversions. Enforces minimum rest-normalized area >= source minimum-.002.
    A later Blender test must still assess every frame, limb strain, seam and
    re-opened saved weight/morph transformations.
    """
    x=np.asarray(initial,dtype=np.float64).copy()
    base=np.asarray(source,dtype=np.float64)
    rest_areas=np.asarray(rest_areas,dtype=np.float64)
    original_pairs=base_pairs if base_pairs is not None else bvh_pairs(base,triangles)
    base_area,base_signed=oriented_area(base,triangles,rest_areas,oriented_rest_norm)
    source_min=float(np.min(base_area))
    source_under=int(np.sum(base_area<.5))
    allowed=set(map(int,editable))
    report={"source_bvh_pairs":len(original_pairs),
            "source_min_triangle_area":source_min,
            "source_underhalf_triangle_count":source_under,
            "editable_vertex_count":len(allowed),"iteration_trace":[]}
    def check(y):
        pairs=bvh_pairs(y,triangles)
        area,signed=oriented_area(y,triangles,rest_areas,oriented_rest_norm)
        inv=int(np.sum((signed<0)&(base_signed>=0)))
        under=int(np.sum(area<.5))
        minimum=float(np.min(area))
        total=len(pairs);added=len(pairs-original_pairs)
        return dict(pairs=pairs,total=total,new=added,flips=inv,
                    under=under,minimum=minimum,
                    area_safe=minimum>=source_min-.002 and under<=source_under)
    current=check(x)
    initial_stats={k:v for k,v in current.items() if k!="pairs"}
    report["before"]=initial_stats
    report["new_pair_ids_before"]=[list(z) for z in sorted(current["pairs"]-original_pairs)]
    accepted=0
    for iteration in range(max_iterations):
        extra=current["pairs"]-original_pairs
        if not extra or (current["total"]<=len(original_pairs) and current["flips"]==0):
            break
        raw,reasons=geometric_proposal(x,base,triangles,extra,allowed)
        if not raw:
            report["search_stopped_reason"]="NO_GEOMETRIC_WITNESS_PROPOSAL"
            break
        chosen=None
        for alpha in (0.25,0.5,0.75,1.,1.5):
            y=x.copy()
            for vertex,increment in raw.items():
                displacement=(y[vertex]-initial[vertex])+alpha*increment
                mag=float(np.linalg.norm(displacement))
                if mag>max_world_change:
                    displacement*=max_world_change/mag
                y[vertex]=initial[vertex]+displacement
            m=check(y)
            if not m["area_safe"] or m["flips"]>0:
                continue
            # Lexicographic objective: first suppress net new collisions,
            # then newly crossed face pairs, then minimize displacement.
            score=(max(0,m["total"]-len(original_pairs)),
                   m["new"],float(np.max(np.linalg.norm(y-initial,axis=1))))
            if score < (max(0,current["total"]-len(original_pairs)),
                        current["new"],float(np.max(np.linalg.norm(x-initial,axis=1)))-1e-8):
                if chosen is None or score<chosen[0]:
                    chosen=(score,y,m,alpha)
        if chosen is None:
            report["search_stopped_reason"]="NO_SAFE_OBJECTIVE_IMPROVEMENT"
            report["last_proposal_reasons"]=reasons
            break
        _,x,current,alpha=chosen
        accepted+=1
        report["iteration_trace"].append({"iteration":iteration,"selected_step":alpha,
                "overlaps":current["total"],"new_pairs":current["new"],
                "minimum_area":current["minimum"],"proposal_reasons":reasons})
    report.update(accepted_steps=accepted,
            after={k:v for k,v in current.items() if k!="pairs"},
            new_pair_ids_after=[list(z) for z in sorted(current["pairs"]-original_pairs)],
            max_actual_world_offset=float(np.max(np.linalg.norm(x-initial,axis=1))),
            improved=(current["total"]<initial_stats["total"] and current["area_safe"]
                      and current["flips"]==0))
    return x,report
