"""Round22: trace exact failing belly triangles and bone-weight gradient mechanisms.
Uses two independently saved Blender .blend files; NO edits, no candidate promotion.
Blender 5.1.2 L3: selected failure frames, exact face IDs, 3D coordinates, weights,
bone transforms, validated LBS vs evaluated bpy mesh; BVH pairs are screening only.
"""
import bpy, sys, json, csv, math, hashlib, traceback, runpy
from pathlib import Path
from collections import Counter
from mathutils import Vector
from mathutils.bvhtree import BVHTree
FRAMES=(7,8,9,10,11,14,15,16,17)
ACT="run_sprint_v8_ik_phase_NUMERIC_REVIEW"

def options():
 import argparse
 p=argparse.ArgumentParser()
 for key in ("--baseline","--candidate","--out"):p.add_argument(key,required=True)
 return p.parse_args(sys.argv[sys.argv.index("--")+1:])

def overpairs(tris,xyz):
 tree=BVHTree.FromPolygons(xyz,tris,all_triangles=True,epsilon=1e-7)
 pairs=set()
 for a,b in tree.overlap(tree):
  if a>=b or set(tris[a]).intersection(tris[b]):continue
  pairs.add((a,b))
 return pairs

def signature(tri_idx,tris,rest,rot,b,c,area_ref):
 i,j,k=tris[tri_idx]
 nr=(rest[j]-rest[i]).cross(rest[k]-rest[i])
 nb=(b[j]-b[i]).cross(b[k]-b[i])
 nc=(c[j]-c[i]).cross(c[k]-c[i])
 area_b=nb.length/area_ref[tri_idx]
 area_c=nc.length/area_ref[tri_idx]
 if min(nr.length,nb.length,nc.length)<1e-10:return area_b,area_c,False,False
 ref_rot=rot@nr.normalized()
 bad_b=ref_rot.dot(nb.normalized())<0
 bad_c=ref_rot.dot(nc.normalized())<0
 return area_b,area_c,bad_b,bad_c

def select_hotspots(base,can,tris,restareas,frame):
 b=base["poses"][frame];c=can["poses"][frame]
 rot=base["rot"][frame]
 bpair=overpairs(tris,b);cpair=overpairs(tris,c);newpair=cpair-bpair
 involved={k for a,d in newpair for k in (a,d)}
 rows=[]
 for ti,face in enumerate(tris):
  area_b,area_c,bad_b,bad_c=signature(ti,tris,base["rest"],rot,b,c,restareas)
  new_flip=bad_c and not bad_b
  drop=area_b-area_c
  rows.append({"triangle":ti,"vertices":list(face),
               "area_before":area_b,"area_after":area_c,
               "area_loss":drop,"reference_normal_flipped_before":bad_b,
               "reference_normal_flipped_after":bad_c,
               "new_rest_normal_flip":new_flip,"new_BVH_pair_member":ti in involved,
               "minimum_area_regression":drop>.002})
 # Always capture globally minimal triangles and the worst newly folded ones.
 selected=set(sorted(range(len(rows)),key=lambda i:rows[i]["area_after"])[:6])
 selected.update(sorted(range(len(rows)),key=lambda i:rows[i]["area_loss"],reverse=True)[:6])
 selected.update(i for i,r in enumerate(rows) if r["new_rest_normal_flip"])
 selected.update(i for i,r in enumerate(rows) if r["new_BVH_pair_member"])
 # Keep a bound on sampled faces; retain flagged IDs and worst min-area.
 if len(selected)>40:
  selected=set(sorted(selected,key=lambda i:(
       rows[i]["new_rest_normal_flip"],rows[i]["new_BVH_pair_member"],
       rows[i]["area_loss"],-rows[i]["area_after"]),reverse=True)[:40])
 # A scientific before-vs-after gradient must compare the SAME mesh edge.
 # Determine one canonical, maximally strained edge using the unchanged
 # baseline evaluated geometry, not each candidate's independent ranking.
 for ti in selected:
  vids=rows[ti]["vertices"]
  edge_set=((vids[0],vids[1]),(vids[1],vids[2]),(vids[2],vids[0]))
  edge=max(edge_set,key=lambda ab:abs(
      (b[ab[1]]-b[ab[0]]).length/
      max((base["rest"][ab[1]]-base["rest"][ab[0]]).length,1e-8)-1.))
  rows[ti]["canonical_baseline_edge"]=list(edge)
 return {"frame":frame,"baseline_overlaps":len(bpair),"candidate_overlaps":len(cpair),
         "new_overlap_pairs":[list(x) for x in sorted(newpair)[:50]],
         "new_reference_flips":sum(r["new_rest_normal_flip"] for r in rows),
         "minimum_area_drop_beyond_threshold":sum(r["minimum_area_regression"] for r in rows),
         "worst_minimum_area_before":min(x["area_before"] for x in rows),
         "worst_minimum_area_after":min(x["area_after"] for x in rows),
         "hotspots":[rows[i] for i in sorted(selected)]}

def bone_weights(ob, vid):
 return {ob.vertex_groups[x.group].name:float(x.weight)
         for x in ob.data.vertices[vid].groups
         if float(x.weight)>1e-9}

def proxy_and_gradient(ob,before,actual,local_mats,vids,faces,helper):
 world=ob.matrix_world.copy(); wi=world.inverted()
 raw={i:bone_weights(ob,i) for i in vids}
 clean={i:{k:v for k,v in raw[i].items() if k in local_mats and v>1e-9} for i in vids}
 norms={i:sum(clean[i].values()) for i in vids}
 if any(v<.9 for v in norms.values()):
  raise RuntimeError("Missing deform weights on investigated vertex")
 pred={};worst=0.
 for i in vids:
  pi=wi@before[i]
  estimated=Vector((0.,0.,0.))
  for bone,weight in clean[i].items():
   estimated+=(world@(local_mats[bone]@pi))*(weight/norms[i])
  err=(estimated-actual[i]).length
  worst=max(worst,err)
  pred[i]=estimated
 pairs=[]
 for h in faces:
  vid=h["vertices"]
  a,b=h["canonical_baseline_edge"]
  if a not in vid or b not in vid or a==b:
   raise RuntimeError("Canonical hotspot edge is not an edge of the selected face")
  w0=clean[a];w1=clean[b]
  names=set(w0)|set(w1)
  smooth=Vector((0,0,0));grad=Vector((0,0,0));causes=[]
  p0=wi@before[a];p1=wi@before[b]
  for name in names:
   mat=local_mats[name]
   t0=world@(mat@p0);t1=world@(mat@p1)
   x=w0.get(name,0.)/norms[a];y=w1.get(name,0.)/norms[b]
   smooth+=(t1-t0)*(.5*(x+y))
   grad+=(t0+t1)*(.5*(y-x))
   causes.append({"bone":name,"weight_at_first":x,"weight_at_second":y,
                  "signed_gradient":y-x,
                  "abs_gradient":abs(y-x)})
  real=actual[b]-actual[a]
  identity=(pred[b]-pred[a]-smooth-grad).length
  if identity>1e-4:raise RuntimeError("Gradient identity invalid at triangle "+str(h["triangle"]))
  causes.sort(key=lambda q:q["abs_gradient"],reverse=True)
  pairs.append({"triangle":h["triangle"],"edge":[a,b],
                "pre_armature_edge_length":(before[b]-before[a]).length,
                "evaluated_edge_length":real.length,
                "smooth_component_length":smooth.length,
                "gradient_component_length":grad.length,
                "gradient_over_rest_edge":grad.length/max((before[b]-before[a]).length,1e-8),
                "gradient_identity_residual":identity,
                "largest_weight_gradients":causes[:8],
                "endpoints_weights":[raw[a],raw[b]]})
 return worst,pairs,raw

def per_file_forensics(path, allhot, r14):
 bpy.ops.wm.open_mainfile(filepath=str(path.resolve()))
 ob=max((o for o in bpy.data.objects if o.type=="MESH" and any(m.type=="ARMATURE" and m.object for m in o.modifiers)),
        key=lambda o:len(o.data.vertices))
 md=next(m for m in ob.modifiers if m.type=="ARMATURE" and m.object)
 arm=md.object
 if len(ob.data.vertices)!=19466 or len(arm.data.bones)!=49:raise RuntimeError("Input is not 49 bone model")
 action=bpy.data.actions.get(ACT)
 if action is None:raise RuntimeError("Missing verified gait")
 arm.animation_data_create()
 for track in arm.animation_data.nla_tracks:track.mute=True
 detail={};errors=[]
 for frame,data in allhot.items():
  r14["reset"](arm,action,frame)
  actual=r14["pts"](ob)
  before=r14["get_input"](ob,md)
  r14["reset"](arm,action,frame)
  transforms=r14["vmat"](ob,arm)
  ids=set(i for h in data["hotspots"] for i in h["vertices"])
  err,pairs,original_weights=proxy_and_gradient(ob,before,actual,transforms,
                                       ids,data["hotspots"],r14)
  detail[str(frame)]={"max_selected_vertex_LBS_vs_blender_error":err,
        "edge_gradient_mechanisms":pairs,
        "selected_vertices":len(ids)}
  errors.append(err)
 return {"worst_selected_vertex_LBS_error":max(errors),"frames":detail}

def main():
 args=options()
 out=Path(args.out).resolve();out.mkdir(parents=True,exist_ok=True)
 report={"status":"STARTED","model":"49 bone 19466 vertices","experimental_only":True,
  "note":"Gradient decomposition is a validated mesh mechanism, not proof of biological anatomical correctness. No modified BLEND or GLB."}
 try:
  path0=Path(args.baseline).resolve();path1=Path(args.candidate).resolve()
  helper=runpy.run_path("rig-experiments/round19e_clean_candidate_qa.py",run_name="r22_helpers")
  render=runpy.run_path("rig-experiments/round11_rootcause.py",run_name="r22_render_helpers")
  r20=runpy.run_path("rig-experiments/round20_full_cycle_geometry.py",run_name="r22_24frame")
  r14=runpy.run_path("rig-experiments/round14_skinning_forensics.py",run_name="r22_mechanism")
  base=r20["load_and_sample"](path0,helper,render,True)
  candidate=r20["load_and_sample"](path1,helper,render,False)
  if base["hash"]!=candidate["hash"] or base["polys"]!=candidate["polys"] or base["edges"]!=candidate["edges"]:
   raise RuntimeError("Saved input rest, shapes, rig or topology mismatch")
  if max(base["seam"],candidate["seam"])>1e-5:
   raise RuntimeError("Original gait seam is not repeatable")
  links,tris,rest_area=r20["fixed_topology"](base)
  hotspots={f:select_hotspots(base,candidate,tris,rest_area,f) for f in FRAMES}
  original=per_file_forensics(path0,hotspots,r14)
  changed=per_file_forensics(path1,hotspots,r14)
  if max(original["worst_selected_vertex_LBS_error"],changed["worst_selected_vertex_LBS_error"])>1e-4:
   raise RuntimeError("LBS explanatory proxy mismatch with actual Blender evaluated mesh")
  tallies=Counter()
  comparison=[]
  for frame,h in hotspots.items():
   op=original["frames"][str(frame)]["edge_gradient_mechanisms"]
   cp=changed["frames"][str(frame)]["edge_gradient_mechanisms"]
   if len(op)!=len(cp) or len(op)!=len(h["hotspots"]):
    raise RuntimeError("Original/candidate hotspot identity mismatches")
   for o,c,row in zip(op,cp,h["hotspots"]):
    if o["triangle"]!=c["triangle"] or c["triangle"]!=row["triangle"]:
     raise RuntimeError("Triangle IDs changed")
    for cause in c["largest_weight_gradients"]:
     tallies[cause["bone"]]+=cause["abs_gradient"]
    comparison.append({"frame":frame,"triangle":row["triangle"],
                       "vertices":row["vertices"],
                       "area_before":row["area_before"],"area_after":row["area_after"],
                       "new_reference_flip":row["new_rest_normal_flip"],
                       "new_overlap_pair_member":row["new_BVH_pair_member"],
                       "gradient_before":o["gradient_over_rest_edge"],
                       "gradient_after":c["gradient_over_rest_edge"],
                       "dominating_bones":[q["bone"] for q in c["largest_weight_gradients"][:4]],
                       "edge":c["edge"]})
  with (out/"round22_hotspots.csv").open("w",newline="") as fp:
   cols=["frame","triangle","vertices","area_before","area_after",
         "new_reference_flip","new_overlap_pair_member","gradient_before",
         "gradient_after","dominating_bones","edge"]
   w=csv.DictWriter(fp,fieldnames=cols);w.writeheader()
   for row in comparison:
    d={k:(json.dumps(v) if isinstance(v,list) else v) for k,v in row.items()}
    w.writerow(d)
  report.update(status="PASS_L3_HOTSPOT_MECHANISM_AUDIT_NO_REPAIR",
    baseline_file_sha256=hashlib.sha256(path0.read_bytes()).hexdigest(),
    candidate_file_sha256=hashlib.sha256(path1.read_bytes()).hexdigest(),
    source_invariant_sha256=base["hash"],
     evaluated_LBS_max_error_original=original["worst_selected_vertex_LBS_error"],
    evaluated_LBS_max_error_candidate=changed["worst_selected_vertex_LBS_error"],
    selected_face_samples=len(comparison),top_aggregate_gradient_bones=tallies.most_common(15),
    frame_hotspots=hotspots,baseline_bone_gradients=original["frames"],
    candidate_bone_gradients=changed["frames"],
    qa="Experimental L3 only; no model changes, no anatomy approval, no production output.")
 except Exception as ex:
  report.update(status="FAIL",error=str(ex),traceback=traceback.format_exc())
 (out/"round22_mechanism_trace.json").write_text(json.dumps(report,ensure_ascii=False,indent=2))
 print("ROUND22",report["status"],"Sampled faces",report.get("selected_face_samples"),
       "Original LBS error",report.get("evaluated_LBS_max_error_original"),
       "Candidate LBS error",report.get("evaluated_LBS_max_error_candidate"),
       "Top bones",report.get("top_aggregate_gradient_bones",[])[:8])
 if report["status"]!="PASS_L3_HOTSPOT_MECHANISM_AUDIT_NO_REPAIR":raise SystemExit(1)

if __name__=="__main__":main()
