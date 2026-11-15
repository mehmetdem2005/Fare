"""Round 11: isolated anatomically constrained torso root-cause audit.
All geometry numbers come from Blender 5.1.2 depsgraph evaluated meshes.
No automatic weights, no production modifications, no silent promotion.
Input: separately verified 49-bone v7 .blend, created from original repo asset.
"""
import argparse
import bpy
import hashlib
import json
import math
import statistics
import sys
import traceback
from pathlib import Path
from mathutils import Vector

R = math.radians
ACT = "run_sprint_v7_ik_spine_repaired"
BONES = ("hips", "spine_01", "spine_02", "spine_03", "spine_04",
         "spine_05", "neck", "shoulder.L", "shoulder.R", "upper_arm.L",
         "upper_arm.R", "forearm.L", "forearm.R", "hand.L", "hand.R",
         "thigh.L", "thigh.R", "shin.L", "shin.R")
ANGLES = (-12, -6, -3, 3, 6, 12)
REGIONS = ("interleg", "front", "central", "rear", "foreleg", "head")

def cli():
    p = argparse.ArgumentParser()
    p.add_argument("--source", required=True)
    p.add_argument("--out", required=True)
    return p.parse_args(sys.argv[sys.argv.index("--") + 1:])

def digest(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for x in iter(lambda: f.read(1 << 20), b""):
            h.update(x)
    return h.hexdigest()

def points(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    tmp = ev.to_mesh(preserve_all_data_layers=False, depsgraph=dg)
    try:
        world = ev.matrix_world.copy()
        return [tuple(world @ v.co) for v in tmp.vertices]
    finally:
        ev.to_mesh_clear()

def percentile(xs, p):
    if not xs:
        return 0.0
    xs.sort()
    return xs[round((len(xs) - 1) * p)]

def collect(ob, arm):
    part = ob.data.attributes.get("part_id")
    if part is None:
        raise RuntimeError("part_id missing, cannot isolate body surface")
    v = ob.data.vertices
    if len(v) != 19466 or len(arm.data.bones) != 49:
        raise RuntimeError("Wrong rig identity: %d verts / %d bones" % (len(v),len(arm.data.bones)))
    def body(i):
        return part.data[i].value == 6
    rois = {
        "interleg": {i for i,x in enumerate(v) if body(i) and -.1 <= x.co.y <= .055 and abs(x.co.x) <= .165 and .045 <= x.co.z <= .16},
        "front": {i for i,x in enumerate(v) if body(i) and -.27 <= x.co.y <= .055 and abs(x.co.x) <= .17 and .045 <= x.co.z <= .285},
        "central": {i for i,x in enumerate(v) if body(i) and -.27 <= x.co.y <= .055 and abs(x.co.x) <= .06 and .045 <= x.co.z <= .285},
        "rear": {i for i,x in enumerate(v) if body(i) and .055 < x.co.y <= .33 and abs(x.co.x) <= .17 and .06 <= x.co.z <= .30},
        "foreleg": {i for i,x in enumerate(v) if x.co.y < -.18 and x.co.z < .15 and abs(x.co.x) > .09},
        "head": {i for i,x in enumerate(v) if x.co.y < -.30 and x.co.z > .22}
    }
    if any(len(x) < 15 for x in rois.values()):
        raise RuntimeError("Missing expected ROI vertices")
    return rois

def original_weight(ob, vid):
    return {ob.vertex_groups[g.group].name: float(g.weight) for g in ob.data.vertices[vid].groups}

def pose(arm, act, frame):
    ad = arm.animation_data
    ad.action = None
    for pb in arm.pose.bones:
        pb.matrix_basis.identity()
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()
    ad.action = act
    bpy.context.scene.frame_set(frame - 1 if frame > 1 else 2)
    bpy.context.scene.frame_set(frame)
    bpy.context.view_layer.update()

def bone_map(ob, arm, rois):
    mapping = []
    for b in arm.data.bones:
        pb = arm.pose.bones[b.name]
        wsum = {n: 0.0 for n in rois}
        influence = {n: 0 for n in rois}
        for name, mask in rois.items():
            group = ob.vertex_groups.get(b.name)
            if group is None:
                continue
            idx = group.index
            for vid in mask:
                for g in ob.data.vertices[vid].groups:
                    if g.group == idx and g.weight > 1e-5:
                        wsum[name] += g.weight
                        influence[name] += 1
                        break
        mapping.append({
            "bone": b.name, "parent": b.parent.name if b.parent else None,
            "use_deform": bool(b.use_deform), "head_local": list(b.head_local),
            "tail_local": list(b.tail_local), "roll_rad": None, "rest_matrix_local": [list(row) for row in b.matrix_local],
            "length": float(b.length), "influence_count": influence,
            "weight_sum": wsum,
            "constraints": [
                {"name": c.name, "type": c.type, "influence": c.influence,
                 "chain_count": getattr(c, "chain_count", None),
                 "use_stretch": getattr(c, "use_stretch", None),
                 "pole_angle": getattr(c, "pole_angle", None),
                 "target": c.target.name if getattr(c, "target", None) else None,
                 "subtarget": getattr(c, "subtarget", "")}
                for c in pb.constraints]
        })
    return mapping

def render_pose(ob, arm, act, frame, folder, rois, closeup=False):
    folder.mkdir(parents=True, exist_ok=True)
    pose(arm, act, frame)
    sc = bpy.context.scene
    coords = points(ob)
    roi = rois["interleg"] if closeup else set(range(len(coords)))
    xyz = [coords[i] for i in roi]
    center = Vector(tuple((min(x[j] for x in xyz) + max(x[j] for x in xyz)) / 2 for j in range(3)))
    span = max(max(x[j] for x in xyz) - min(x[j] for x in xyz) for j in range(3))
    camera_data = bpy.data.cameras.get("Round11_Camera")
    if camera_data is None:
        camera_data = bpy.data.cameras.new("Round11_Camera")
    camera = bpy.data.objects.get("Round11_Camera")
    if camera is None:
        camera = bpy.data.objects.new("Round11_Camera", camera_data)
        sc.collection.objects.link(camera)
    sc.camera = camera
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = max(span * (2.0 if closeup else 1.5), .16)
    camera_data.clip_start = .001
    camera_data.clip_end = 100
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.render.resolution_x = 840
    sc.render.resolution_y = 720
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    angles = {
        "left": (1,0,.12), "right": (-1,0,.12),
        "front": (0,-1,.12), "back": (0,1,.12),
        "top": (0,0,1), "bottom": (0,0,-1),
        "quarter_front": (1,-1,.7), "quarter_rear": (-1,1,.55)
    }
    names = ("left","right","bottom","quarter_front") if closeup else tuple(angles)
    for name in names:
        direction = Vector(angles[name]).normalized()
        camera.location = center + direction * max(2, span * 5)
        camera.rotation_euler = (center-camera.location).to_track_quat("-Z", "Y").to_euler()
        sc.render.filepath = str(folder / ("%s_f%02d.png" % (name, frame)))
        bpy.ops.render.render(write_still=True)
    return list(names)

def main():
    a = cli()
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    path = Path(a.source).resolve()
    report = {"status": "STARTED", "source_sha256": digest(path),
              "test_engine": "Blender evaluated depsgraph mesh",
              "angles_deg": list(ANGLES), "version": bpy.app.version_string,
              "note": "L3 numerical research; preview generation is not human L4 review"}
    try:
        bpy.ops.wm.open_mainfile(filepath=str(path))
        ob = max((x for x in bpy.data.objects if x.type == "MESH" and any(m.type == "ARMATURE" and m.object for m in x.modifiers)),key=lambda x:len(x.data.vertices))
        arm = next(m.object for m in ob.modifiers if m.type == "ARMATURE" and m.object)
        assert len(ob.data.vertices) == 19466 and len(arm.pose.bones) == 49
        assert "Fore_Shoulder.L" not in arm.pose.bones
        act = bpy.data.actions.get(ACT)
        if not act:
            raise RuntimeError("Verified v7 action missing")
        arm.animation_data_create()
        for track in arm.animation_data.nla_tracks:
            track.mute = True
        arm.animation_data.action = None
        for pb in arm.pose.bones:
            pb.matrix_basis.identity()
        bpy.context.scene.frame_set(1)
        bpy.context.view_layer.update()
        rest = points(ob)
        rois = collect(ob, arm)
        edges = {name: [] for name in rois}
        for ed in ob.data.edges:
            i, j = tuple(ed.vertices)
            d = math.dist(rest[i], rest[j])
            if d < .001:
                continue
            for name, ids in rois.items():
                if i in ids and j in ids:
                    edges[name].append((i, j, d))
        if not all(edges.values()):
            raise RuntimeError("ROI contains no evaluable edges")
        report["roi"] = {n: {"vertices": len(rois[n]), "edges": len(edges[n])} for n in rois}
        report["bone_map"] = bone_map(ob, arm, rois)
        report["modifiers"] = [{"name": m.name, "type": m.type, "preserve_volume": getattr(m, "use_deform_preserve_volume", None)} for m in ob.modifiers]
        report["shape_keys"] = [x.name for x in ob.data.shape_keys.key_blocks] if ob.data.shape_keys else []

        def assess(coords, detail=False):
            metrics = {}
            for name, ee in edges.items():
                stretch = []
                extension = []
                compression = []
                for i,j,d in ee:
                    rat = math.dist(coords[i],coords[j]) / d
                    extension.append(max(0.0, rat-1))
                    compression.append(max(0.0, 1-rat))
                    stretch.append(abs(rat-1))
                metrics[name] = {
                    "p50": percentile(stretch, .50),
                    "p95": percentile(stretch, .95),
                    "p99": percentile(stretch, .99),
                    "max": max(stretch),
                    "extension_p95": percentile(extension, .95),
                    "compression_p95": percentile(compression, .95)}
            return metrics

        baseline = []
        for f in range(1,26):
            pose(arm, act, f)
            v = points(ob)
            if f == 1:
                first = v
            if f == 25:
                seam = max(math.dist(q,r) for q,r in zip(first,v))
            else:
                baseline.append({"frame": f, "metrics": assess(v),
                    "shape_values": {key.name: key.value for key in ob.data.shape_keys.key_blocks if key.name.startswith("crv_")} if ob.data.shape_keys else {},
                    "actual_bones": {nm: {"head": list(arm.pose.bones[nm].head), "tail": list(arm.pose.bones[nm].tail)}
                                     for nm in BONES if nm in arm.pose.bones}})
        report["baseline"] = baseline
        report["loop_seam"] = seam
        if seam > .0001:
            raise RuntimeError("Original v7 loop seam must be exact: %g" % seam)
        ext_frame = max(baseline, key=lambda x: x["metrics"]["interleg"]["extension_p95"])["frame"]
        cmp_frame = max(baseline, key=lambda x: x["metrics"]["interleg"]["compression_p95"])["frame"]
        frames = list(dict.fromkeys((ext_frame, cmp_frame, 3, 15)))
        report["critical_frames"] = {"extension": ext_frame, "compression": cmp_frame, "inspected": frames}

        def edge_audit(frame, region, most=32):
            pose(arm, act, frame)
            v = points(ob)
            item = []
            for i,j,d in edges[region]:
                ratio = math.dist(v[i],v[j]) / d
                item.append((abs(ratio-1),i,j,ratio,d))
            item.sort(reverse=True)
            return [{"v1":i,"v2":j,"ratio":rat,"rest_length":d,
                     "abs_relative_change":err,
                     "weights_v1":original_weight(ob,i),
                     "weights_v2":original_weight(ob,j)}
                    for err,i,j,rat,d in item[:most]]
        report["critical_edges"] = {
            "%s_f%d"%(region,f): edge_audit(f,region)
            for f in frames for region in ("interleg","front","central")
        }

        # Actual solver rotation, not commanded Euler alone. Every case starts
        # from the same action/IK/driver/constraint state.
        sweeps = []
        for f in (ext_frame, cmp_frame):
            pose(arm, act, f)
            original_coords = points(ob)
            original_metrics = assess(original_coords)
            for name in BONES:
                if name not in arm.pose.bones:
                    continue
                pb = arm.pose.bones[name]
                for axis in "XYZ":
                    for angle in ANGLES:
                        pose(arm, act, f)
                        pb = arm.pose.bones[name]
                        old = pb.matrix.copy()
                        old_head = pb.head.copy()
                        pb.rotation_mode = "XYZ"
                        e = pb.rotation_euler.copy()
                        e["XYZ".index(axis)] += R(angle)
                        pb.rotation_euler = e
                        bpy.context.view_layer.update()
                        rotated = pb.matrix.copy()
                        newcoords = points(ob)
                        value = assess(newcoords)
                        sweeps.append({
                            "frame": f,"bone":name,"axis":axis,
                            "command_deg":angle,
                            "evaluated_angle_deg":math.degrees(old.to_quaternion().rotation_difference(rotated.to_quaternion()).angle),
                            "evaluated_head_displacement":(pb.head-old_head).length,
                            "delta_p95":{r:value[r]["p95"]-original_metrics[r]["p95"] for r in REGIONS},
                            "delta_max":{r:value[r]["max"]-original_metrics[r]["max"] for r in REGIONS},
                            "interleg_vertex_max_displacement":max(math.dist(newcoords[i],original_coords[i]) for i in rois["interleg"])})
                # Invariant: no residual influence from other-bone experiments.
                pose(arm,act,f)
                again = assess(points(ob))
                if max(abs(again[r]["p95"]-original_metrics[r]["p95"]) for r in REGIONS)>1e-6:
                    raise RuntimeError("Pose reset leaked for "+name)
        report["per_bone_sweep"] = sweeps
        report["bone_sweep_count"] = len(sweeps)

        # Experimental hypothesis: sharp upper_arm/thigh ratios at measured
        # high-strain body vertices. One side and one strength per isolated trial.
        # No mass transfer to spine or blanket smoothing.
        candidate_frame = ext_frame
        pose(arm,act,candidate_frame)
        vv=points(ob)
        distort = sorted([(abs(math.dist(vv[i],vv[j])/d-1),i,j)
                          for i,j,d in edges["interleg"]],reverse=True)
        cutoff = distort[max(0,int(len(distort)*.02)-1)][0]
        hotspot = {i for err,u,v in distort if err>=cutoff for i in (u,v)}
        neighbors = {i:set() for i in range(len(ob.data.vertices))}
        for e in ob.data.edges:
            i,j=e.vertices
            neighbors[i].add(j)
            neighbors[j].add(i)
        hotspot |= {q for i in tuple(hotspot) for q in neighbors[i] if q in rois["interleg"]}
        snapshot = {i:original_weight(ob,i) for i in rois["interleg"]}
        variants=[]
        based = {n:{"worst":max(x["metrics"][n]["p95"] for x in baseline),
                   "mean":statistics.mean(x["metrics"][n]["p95"] for x in baseline)}
                 for n in REGIONS}
        report["cycle_score_baseline"]=based
        report["hotspot_vertex_ids"] = sorted(hotspot)
        selected=None
        best_score=float("inf")
        for side in ("L","R"):
            a_name,b_name="upper_arm."+side,"thigh."+side
            for strength in (.25,.50,.75):
                changes={}
                for i in sorted(hotspot):
                    old = snapshot[i]
                    mass=old.get(a_name,0)+old.get(b_name,0)
                    if old.get(a_name,0)<.08 or old.get(b_name,0)<.08 or mass<.25:
                        continue
                    ratios=[]
                    for j in neighbors[i]:
                        if j not in rois["interleg"]:
                            continue
                        oth=snapshot[j]
                        denom=oth.get(a_name,0)+oth.get(b_name,0)
                        if denom>.2:
                            ratios.append(oth.get(a_name,0)/denom)
                    if len(ratios)<2:
                        continue
                    target=statistics.median(ratios)
                    a_old=old[a_name]
                    a_new=a_old+max(-.08,min(.08,(target-a_old/mass)*mass*strength))
                    if abs(a_new-a_old)>1e-7:
                        changes[i]=(a_new,mass-a_new)
                ga=ob.vertex_groups.get(a_name)
                gb=ob.vertex_groups.get(b_name)
                for i,(wa,wb) in changes.items():
                    ga.add([i],wa,"REPLACE")
                    gb.add([i],wb,"REPLACE")
                rows=[]
                for f in range(1,25):
                    pose(arm,act,f)
                    m=assess(points(ob))
                    rows.append(m)
                scores={n:{"worst":max(x[n]["p95"] for x in rows),
                           "mean":statistics.mean(x[n]["p95"] for x in rows)}
                        for n in REGIONS}
                deltas={n:{"worst":scores[n]["worst"]-based[n]["worst"],
                           "mean":scores[n]["mean"]-based[n]["mean"]} for n in REGIONS}
                record={"side":side,"strength":strength,"changed_vertices":len(changes),
                        "changed_weight_pairs":{str(i):{"from": [snapshot[i][a_name],snapshot[i][b_name]],"to":list(change)}
                                                for i,change in changes.items()},
                        "scores":scores,"delta":deltas,
                        "status":"EXPERIMENT_REVIEW"}
                variants.append(record)
                # Select numerical shortlist only. THIS IS NOT a visual pass.
                okay=(len(changes)>0 and deltas["interleg"]["worst"]<-.015
                      and all(deltas[n]["worst"]<=.003 for n in ("rear","head","foreleg"))
                      and deltas["front"]["worst"]<=.005
                      and deltas["central"]["worst"]<=.005)
                if okay and scores["interleg"]["worst"]<best_score:
                    selected=(side,strength,dict(changes),scores)
                    best_score=scores["interleg"]["worst"]
                # Restore all changed groups from the verified baseline.
                for i in changes:
                    ga.add([i],snapshot[i][a_name],"REPLACE")
                    gb.add([i],snapshot[i][b_name],"REPLACE")
                pose(arm,act,1)
                restored=assess(points(ob))
                if max(abs(restored[n]["p95"]-baseline[0]["metrics"][n]["p95"]) for n in REGIONS)>1e-6:
                    raise RuntimeError("Weight restore contaminated later trial")
        report["weight_trials"]=variants
        report["numeric_shortlist"]={"side":selected[0],"strength":selected[1],
                                     "changed_vertices":len(selected[2])} if selected else None

        # Baseline renders and optional shortlisted comparison; only the latter
        # is saved to a separate REVIEW asset. Never overwrite deliver/.
        report["baseline_views"]={}
        for f in dict.fromkeys((ext_frame,cmp_frame)):
            report["baseline_views"][f] = render_pose(ob,arm,act,f,out/"baseline_views",rois)
            render_pose(ob,arm,act,f,out/"baseline_closeup",rois,closeup=True)

        if selected:
            side,strength,changes,scores=selected
            ga=ob.vertex_groups["upper_arm."+side]
            gb=ob.vertex_groups["thigh."+side]
            for i,(wa,wb) in changes.items():
                ga.add([i],wa,"REPLACE")
                gb.add([i],wb,"REPLACE")
            for f in dict.fromkeys((ext_frame,cmp_frame)):
                render_pose(ob,arm,act,f,out/"candidate_views",rois)
                render_pose(ob,arm,act,f,out/"candidate_closeup",rois,closeup=True)
            pose(arm,act,1)
            saved=out/"round11_hotspot_weight_NUMERIC_REVIEW.blend"
            bpy.ops.wm.save_as_mainfile(filepath=str(saved),compress=True)
            report["candidate"]={"path":saved.name,"sha256":digest(saved),
                                 "scores":scores,"visual_status":"NOT_REVIEWED",
                                 "approval":"BLOCKED_PENDING_REOPEN_VISUAL_AND_COLLISION"}
        report["status"]="PASS_L3_RESEARCH_NOT_PRODUCTION"
    except Exception as ex:
        report.update(status="FAIL",error=str(ex),traceback=traceback.format_exc())
    (out/"round11_rootcause.json").write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print("ROUND11_STATUS",report["status"])
    print("ROUND11_SUMMARY",json.dumps({k:report.get(k) for k in
        ("critical_frames","bone_sweep_count","cycle_score_baseline","numeric_shortlist","candidate")},ensure_ascii=False))
    if report["status"]=="FAIL":
        print(report["error"])
        raise SystemExit(1)

if __name__=="__main__":
    main()
