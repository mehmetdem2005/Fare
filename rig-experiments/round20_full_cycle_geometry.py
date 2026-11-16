"""Round20: independent 24-frame anatomical surface QA for SAVED v8 vs 0.170 one-shot weight candidate.
No topology, weights, bone, mesh, action or production-file modification. Numerical L3 only:
rendered images require human L4 approval; L5 Godot/glTF never inferred.
"""
import bpy, sys, json, math, csv, hashlib, traceback, runpy, statistics
from pathlib import Path

ACT = "run_sprint_v8_ik_phase_NUMERIC_REVIEW"
FRAMES = tuple(range(1,25))

def options():
    import argparse
    p=argparse.ArgumentParser()
    for key in ("--baseline","--candidate","--out"):
        p.add_argument(key,required=True)
    return p.parse_args(sys.argv[sys.argv.index("--")+1:])

def quant(xs, q):
    return sorted(xs)[round((len(xs)-1)*q)] if xs else 0.0

def area(coords, tris, rest_areas):
    vals=[]
    for (a,b,c),ra in zip(tris,rest_areas):
        va=(coords[b]-coords[a]).cross(coords[c]-coords[a]).length
        vals.append(va/ra)
    return {"under_half":sum(v<0.5 for v in vals),
            "p05":quant(vals,.05),"min":min(vals),
            "p95":quant(vals,.95),"count":len(vals)}

def load_and_sample(path, helpers, draw, for_source=False):
    bpy.ops.wm.open_mainfile(filepath=str(path))
    o,arm=helpers["model"]()
    action=bpy.data.actions.get(ACT)
    if action is None:raise RuntimeError("Original v8 gait action unavailable")
    arm.animation_data_create()
    for track in arm.animation_data.nla_tracks:track.mute=True
    scope_hash=helpers["invariant"](o,arm)
    rois=draw["collect"](o,arm)
    arm.animation_data.action=None
    for pb in arm.pose.bones:pb.matrix_basis.identity()
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()
    rest=helpers["pts"](o)
    sample={}
    rotation={}
    for f in FRAMES+(25,):
        helpers["pose"](arm,action,f)
        sample[f]=helpers["pts"](o)
        if f!=25:
            m=(arm.matrix_world @ arm.pose.bones["spine_03"].matrix @
               arm.data.bones["spine_03"].matrix_local.inverted() @
               arm.matrix_world.inverted())
            rotation[f]=m.to_quaternion()
    seam=max((sample[1][i]-sample[25][i]).length for i in range(len(rest)))
    return {"hash":scope_hash,"rest":rest,"poses":sample,"rot":rotation,
            "seam":seam,"rois":rois, "polys":[tuple(p.vertices) for p in o.data.polygons],
            "edges":[tuple(e.vertices) for e in o.data.edges],
            "path":str(path)}

def fixed_topology(b):
    rois=b["rois"]
    xyz=b["rest"]
    edges={}
    for name,ids in rois.items():
        edges[name]=[]
        for a,c in b["edges"]:
            if a in ids and c in ids:
                d=(xyz[c]-xyz[a]).length
                if d>0.001:edges[name].append((a,c,d))
        if not edges[name]:raise RuntimeError("Empty anatomy ROI "+name)
    triangles=[]
    rest_area=[]
    for vertices in b["polys"]:
        if len(vertices)<3 or not all(i in rois["interleg"] for i in vertices):
            continue
        for k in range(1,len(vertices)-1):
            a,c,d=vertices[0],vertices[k],vertices[k+1]
            v=(xyz[c]-xyz[a]).cross(xyz[d]-xyz[a]).length
            if v>2e-7:
                triangles.append((a,c,d));rest_area.append(v)
    if len(triangles)!=1069:raise RuntimeError("Fixed 1069 triangles changed: "+str(len(triangles)))
    return edges,triangles,rest_area

def strain(coords, edges):
    result={}
    for name,links in edges.items():
        arr=[abs((coords[b]-coords[a]).length/rest-1.) for a,b,rest in links]
        result[name]={"p95":quant(arr,.95),"p99":quant(arr,.99),
                      "maximum":max(arr),"sample_edges":len(arr)}
    return result

def render(out,source, frames,helpers,draw,label):
    bpy.ops.wm.open_mainfile(filepath=str(source))
    o,arm=helpers["model"]()
    act=bpy.data.actions.get(ACT)
    arm.animation_data_create()
    for track in arm.animation_data.nla_tracks:track.mute=True
    rois=draw["collect"](o,arm)
    for f in frames:draw["render_pose"](o,arm,act,f,out/(label+"_views"),rois,closeup=True)

def main():
    args=options()
    out=Path(args.out).resolve()
    out.mkdir(parents=True,exist_ok=True)
    report={"status":"STARTED","quality":"L3 numeric / generated L4 images; NOT L4 anatomy-accepted, NOT L5",
            "frames":24,"no_modified_rig":True}
    try:
        helpers=runpy.run_path("rig-experiments/round19e_clean_candidate_qa.py",run_name="round20_helpers")
        draw=runpy.run_path("rig-experiments/round11_rootcause.py",run_name="round20_renderer")
        geo=runpy.run_path("rig-experiments/round17_reopen_surface.py",run_name="round20_geometry")
        base=load_and_sample(Path(args.baseline).resolve(),helpers,draw,True)
        candidate=load_and_sample(Path(args.candidate).resolve(),helpers,draw,False)
        if base["hash"]!=candidate["hash"]:
            raise RuntimeError("Rest/bone/constraint/topology/shape-key fingerprint differs; weight-only hypothesis violated")
        if base["polys"]!=candidate["polys"] or base["edges"]!=candidate["edges"]:
            raise RuntimeError("Topology differs after saving candidate")
        if max(base["seam"],candidate["seam"])>1e-5:
            raise RuntimeError("Animation closure failed")
        edges,tris,rest_areas=fixed_topology(base)
        rows=[];issues=[]
        for f in FRAMES:
            b=base["poses"][f];c=candidate["poses"][f]
            s0=strain(b,edges);s1=strain(c,edges)
            a0=area(b,tris,rest_areas);a1=area(c,tris,rest_areas)
            surface=geo["normals_overlap"](tris,b,c)
            orientation=helpers["coorient"](base["rest"],b,c,tris,base["rot"][f])
            row={"frame":f,"baseline":s0,"candidate":s1,"area_baseline":a0,
                 "area_candidate":a1,"geometry":surface,"reference_orientation":orientation}
            rows.append(row)
            if orientation["new_reference_inversions"]:
                issues.append({"frame":f,"reason":"new_corotated_rest_normal_inversions",
                               "count":orientation["new_reference_inversions"]})
            if surface["candidate_nonadjacent_overlaps"]>surface["baseline_nonadjacent_overlaps"]:
                issues.append({"frame":f,"reason":"new_nonadjacent_BVH_overlaps",
                               "before":surface["baseline_nonadjacent_overlaps"],
                               "after":surface["candidate_nonadjacent_overlaps"]})
            if a1["min"]<a0["min"]-.002:
                issues.append({"frame":f,"reason":"minimum_face_area_ratio_regression",
                               "before":a0["min"],"after":a1["min"]})
        before_worst=max(r["baseline"]["interleg"]["p95"] for r in rows)
        after_worst=max(r["candidate"]["interleg"]["p95"] for r in rows)
        if after_worst>before_worst+0.001:
            issues.append({"reason":"full_cycle_interleg_p95_regression",
                           "before":before_worst,"after":after_worst})
        # Select an actually problematic frame, not just a handpicked nice view.
        worst=max(rows,key=lambda r:(
            r["reference_orientation"]["new_reference_inversions"],
            r["geometry"]["candidate_nonadjacent_overlaps"]-r["geometry"]["baseline_nonadjacent_overlaps"],
            r["area_baseline"]["min"]-r["area_candidate"]["min"],
            r["candidate"]["interleg"]["p95"]))
        render_frames=sorted(set((1,15,worst["frame"])))
        report.update({"source_invariant_sha256":base["hash"],
                       "source_file_sha256":hashlib.sha256(Path(args.baseline).read_bytes()).hexdigest(),
                       "candidate_file_sha256":hashlib.sha256(Path(args.candidate).read_bytes()).hexdigest(),
                       "baseline_seam":base["seam"],"candidate_seam":candidate["seam"],
                       "body_triangles":len(tris),"roi_edges":{k:len(v) for k,v in edges.items()},
                       "interleg_worst_p95":{"baseline":before_worst,"candidate":after_worst},
                       "worst_anatomy_frame":worst["frame"],"render_frames":render_frames,
                       "frames_detail":rows,"issues":issues})
        for label,src in (("baseline",Path(args.baseline).resolve()),("candidate",Path(args.candidate).resolve())):
            render(out,src,render_frames,helpers,draw,label)
        report["renders_generated"]=8*len(render_frames)
        report["status"]="PASS_L3_FULL_CYCLE_L4_HUMAN_REVIEW_REQUIRED" if not issues else "REJECT_L3_FULL_CYCLE_ANATOMICAL_REGRESSION"
        with (out/"round20_frame_metrics.csv").open("w",newline="") as fp:
            fieldnames=("frame","belly_p95_before","belly_p95_after",
                        "overlap_before","overlap_after","new_rest_normal_flips",
                        "min_area_before","min_area_after")
            writer=csv.DictWriter(fp,fieldnames=fieldnames);writer.writeheader()
            for row in rows:
                writer.writerow({"frame":row["frame"],
                   "belly_p95_before":row["baseline"]["interleg"]["p95"],
                   "belly_p95_after":row["candidate"]["interleg"]["p95"],
                   "overlap_before":row["geometry"]["baseline_nonadjacent_overlaps"],
                   "overlap_after":row["geometry"]["candidate_nonadjacent_overlaps"],
                   "new_rest_normal_flips":row["reference_orientation"]["new_reference_inversions"],
                   "min_area_before":row["area_baseline"]["min"],
                   "min_area_after":row["area_candidate"]["min"]})
    except Exception as exc:
        report.update(status="FAIL_EXECUTION",error=str(exc),traceback=traceback.format_exc())
    (out/"round20_full_cycle_anatomy.json").write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print("ROUND20",report["status"],"Belly",report.get("interleg_worst_p95"),
          "Issues",report.get("issues",[])[:15],"Renders",report.get("renders_generated"))
    if report["status"]!="PASS_L3_FULL_CYCLE_L4_HUMAN_REVIEW_REQUIRED":
        raise SystemExit(1)

if __name__=="__main__":main()
