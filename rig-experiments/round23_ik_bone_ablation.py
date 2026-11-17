"""Round23: controlled single-actuator sensitivity at nine proven failing-frame sentinel faces.
Loads immutable v8 and saved/reopened, REJECTED 0.170 weight variant solely as an
experimental hypothesis. Never claims a new production fix; never saves a .blend.
Blender evaluated mesh with independent complete pose reset after every trial.
"""
import bpy, sys, json, math, statistics, traceback, runpy
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ACT="run_sprint_v8_ik_phase_NUMERIC_REVIEW"
FRAMES=(7,8,9,10,11,14,15,16,17)
TARGET_TRIANGLES={7:467,8:351,9:434,10:434,11:434,14:216,15:216,16:812,17:812}
IK=("ik_hand.L","ik_hand.R","ik_foot.L","ik_foot.R")
ROT=("hips","spine_03","spine_04","spine_05","neck")

def cli():
 import argparse
 p=argparse.ArgumentParser()
 for flag in ("--baseline","--candidate","--out"):p.add_argument(flag,required=True)
 return p.parse_args(sys.argv[sys.argv.index("--")+1:])

def area_qual(coords,rest,triangles,rest_areas,orient):
 from collections import Counter
 minimum=10.;low=0;new_flip=0
 target_results={}
 for j,(a,b,c) in enumerate(triangles):
  rn=(rest[b]-rest[a]).cross(rest[c]-rest[a])
  now=(coords[b]-coords[a]).cross(coords[c]-coords[a])
  value=now.length/rest_areas[j]
  minimum=min(minimum,value);low+=int(value<.5)
  if min(rn.length,now.length)>1e-10:
   expected=orient@rn.normalized()
   if expected.dot(now.normalized())<0:new_flip+=1
 return {"min":minimum,"under_half":low,"reference_inversions":new_flip}

def full_assess(coords,base_coords,rest,triangles,areas,rot,edges,geometry):
 b=area_qual(base_coords,rest,triangles,areas,rot)
 c=area_qual(coords,rest,triangles,areas,rot)
 before=geometry["normals_overlap"](triangles,base_coords,coords)
 strain={}
 for name in ("interleg","front","central","rear","foreleg","head"):
  arr=[abs((coords[y]-coords[x]).length/d-1.) for x,y,d in edges[name]]
  arr.sort()
  strain[name]=arr[round((len(arr)-1)*.95)]
 return {"area":c,"original_area":b,"new_reference_inversions":max(0,c["reference_inversions"]-b["reference_inversions"]),
         "overlap_count":before["candidate_nonadjacent_overlaps"],
         "original_overlap_count":before["baseline_nonadjacent_overlaps"],
         "strain_p95":strain}

def trial_measure(co,frame,reference,base,triangles,areas,rot,edges,focus):
 # Cheap first-stage metric: whole 1069-face area & reference normal,
 # local sentinel, full 6-region p95; BVH is added to shortlisted options.
 norm=area_qual(co,base["rest"],triangles,areas,rot)
 original=area_qual(reference,base["rest"],triangles,areas,rot)
 idx=focus[frame];a,b,c=triangles[idx]
 area=(co[b]-co[a]).cross(co[c]-co[a]).length/areas[idx]
 before=(reference[b]-reference[a]).cross(reference[c]-reference[a]).length/areas[idx]
 strains={}
 for name,es in edges.items():
  scores=sorted(abs((co[j]-co[i]).length/d-1.) for i,j,d in es)
  strains[name]=scores[round((len(scores)-1)*.95)]
 return {"area":norm,"baseline_area":original,"sentinel_triangle":idx,
         "sentinel_area":area,"baseline_sentinel_area":before,
         "strain_p95":strains}

def quality(v,ref,trial):
 # This is only a heuristic ranking, NOT a proof of anatomical quality.
 # Strong new-normal penalties; no reward for a degenerate minimum face.
 worse_inversions=max(0,v["area"]["reference_inversions"]-ref["area"]["reference_inversions"])
 min_loss=max(0.,ref["area"]["min"]-v["area"]["min"])
 sentinel_loss=max(0.,ref["sentinel_area"]-v["sentinel_area"])
 delta_p95=max(0.,v["strain_p95"]["interleg"]-ref["strain_p95"]["interleg"])
 fore=max(0.,v["strain_p95"]["foreleg"]-ref["strain_p95"]["foreleg"])
 return 10.*worse_inversions+25.*min_loss+8.*sentinel_loss+3.*delta_p95+3.*fore

def sample(o,helper):
 return helper["pts"](o)

def main():
 args=cli();out=Path(args.out).resolve();out.mkdir(parents=True,exist_ok=True)
 report={"status":"STARTED","quality":"L3 causal perturbation only, no weight/rig edits, no production promotion",
         "frames":list(FRAMES),"sentinels":TARGET_TRIANGLES}
 try:
  repo="rig-experiments/"
  helper=runpy.run_path(repo+"round19e_clean_candidate_qa.py",run_name="r23_h")
  draw=runpy.run_path(repo+"round11_rootcause.py",run_name="r23_draw")
  r20=runpy.run_path(repo+"round20_full_cycle_geometry.py",run_name="r23_r20")
  geometry=runpy.run_path(repo+"round17_reopen_surface.py",run_name="r23_geom")
  baseline=r20["load_and_sample"](Path(args.baseline).resolve(),helper,draw)
  saved=r20["load_and_sample"](Path(args.candidate).resolve(),helper,draw)
  if baseline["hash"]!=saved["hash"] or baseline["edges"]!=saved["edges"] or baseline["polys"]!=saved["polys"]:
   raise RuntimeError("Experimental input changed its rest or bone/morph invariants")
  edges,triangles,areas=r20["fixed_topology"](baseline)
  bpy.ops.wm.open_mainfile(filepath=str(Path(args.candidate).resolve()))
  ob,arm=helper["model"]()
  act=bpy.data.actions.get(ACT)
  if act is None:raise RuntimeError("Missing verified v8 animation")
  arm.animation_data_create()
  for track in arm.animation_data.nla_tracks:track.mute=True
  B=arm.pose.bones
  for name in IK+ROT:
   if name not in B:raise RuntimeError("Required IK/bone missing: "+name)
  measurements=[];shortlist=[]
  for f in FRAMES:
   reference=baseline["poses"][f]
   control_origin=saved["poses"][f]
   # Bone orientations are unchanged by the saved weight-only edit.
   rot=baseline["rot"][f]
   ref=trial_measure(reference,f,reference,baseline,triangles,areas,rot,edges,TARGET_TRIANGLES)
   saved_score=trial_measure(control_origin,f,reference,baseline,triangles,areas,rot,edges,TARGET_TRIANGLES)
   tests=[]
   controls=[]
   for name in IK:
    for axis in "XYZ":
     for change in (-.004,-.002,.002,.004):
      controls.append(("ik",name,axis,change))
   for name in ROT:
    for axis in "XYZ":
     for change in (-2.,2.):
      controls.append(("rot",name,axis,change))
   for typ,name,axis,change in controls:
    helper["pose"](arm,act,f)
    pb=B[name]
    orig_head=pb.head.copy()
    orig_quat=pb.matrix.to_quaternion().copy()
    if typ=="ik":
     shift=Vector((change if axis=="X" else 0.,
                   change if axis=="Y" else 0.,
                   change if axis=="Z" else 0.))
     convert=arm.data.bones[name].matrix_local.to_3x3().inverted()
     pb.location+=convert@shift
    else:
     if pb.rotation_mode!="XYZ":
      raise RuntimeError(name+" bone rotation_mode not Euler XYZ, cannot perturb safely")
     e=pb.rotation_euler.copy()
     e["XYZ".index(axis)]+=math.radians(change)
     pb.rotation_euler=e
    bpy.context.view_layer.update()
    moved=(pb.head-orig_head).length if typ=="ik" else pb.matrix.to_quaternion().rotation_difference(orig_quat).angle
    if moved<1e-8:
     raise RuntimeError("Actuator was ineffective: "+name+" "+axis+" at "+str(f))
    co=sample(ob,helper)
    test=trial_measure(co,f,reference,baseline,triangles,areas,rot,edges,TARGET_TRIANGLES)
    row={"frame":f,"control_type":typ,"bone":name,"axis":axis,
         "delta":change,"actual_bone_response":moved,"result":test,
         "relative_to_original_v8_quality":quality(test,ref,row) if False else quality(test,ref,None),
         "relative_to_saved_candidate_quality":quality(test,saved_score,None)}
    tests.append(row)
   # Independently verify zero state leak after all trials at this frame.
   helper["pose"](arm,act,f)
   check=sample(ob,helper)
   drift=max((check[i]-control_origin[i]).length for i in range(len(check)))
   if drift>1e-5:raise RuntimeError("Single-actuator reset failed at frame %d, error %.8g"%(f,drift))
   best=sorted(tests,key=lambda r:(r["relative_to_original_v8_quality"],
                                    r["relative_to_saved_candidate_quality"]))[:8]
   # Re-run selected controls with an accurate BVH non-adjacent overlap proxy,
   # while preserving exactly the same reset semantics.
   for row in best:
    helper["pose"](arm,act,f)
    pb=B[row["bone"]]
    if row["control_type"]=="ik":
     pos=Vector((row["delta"] if row["axis"]=="X" else 0.,
                 row["delta"] if row["axis"]=="Y" else 0.,
                 row["delta"] if row["axis"]=="Z" else 0.))
     pb.location+=arm.data.bones[row["bone"]].matrix_local.to_3x3().inverted()@pos
    else:
     e=pb.rotation_euler.copy();e["XYZ".index(row["axis"])]+=math.radians(row["delta"])
     pb.rotation_euler=e
    bpy.context.view_layer.update()
    z=sample(ob,helper)
    areasurface=geometry["normals_overlap"](triangles,reference,z)
    row["bvh_before"]=areasurface["baseline_nonadjacent_overlaps"]
    row["bvh_after"]=areasurface["candidate_nonadjacent_overlaps"]
    row["bvh_new_relative_to_original"]=max(0,row["bvh_after"]-row["bvh_before"])
    row["normal_relative_to_original"]=area_qual(z,baseline["rest"],triangles,areas,rot)["reference_inversions"]-ref["area"]["reference_inversions"]
   shortlisted=[z for z in best if z.get("bvh_new_relative_to_original",999)==0 and
                z.get("normal_relative_to_original",999)<=0 and
                z["result"]["area"]["min"]>=ref["area"]["min"]-.002]
   shortlist.extend(shortlisted)
   measurements.append({"frame":f,"original":ref,"unmodified_saved_0p170":saved_score,
                        "tests":tests,"best_checked":best,"eligible":shortlisted,
                        "reset_max_vertex_drift":drift})
   print("ROUND23_FRAME",f,"eligible",len(shortlisted),"best",
         [(x["control_type"],x["bone"],x["axis"],x["delta"],
           round(x["relative_to_original_v8_quality"],5),x.get("bvh_after")) for x in best[:3]])
  report.update(status="PASS_CONTROLLED_SINGLE_ACTUATOR_SENSITIVITY_NO_REPAIR",
                attempts=sum(len(v["tests"]) for v in measurements),
                anatomical_frames=len(FRAMES),frame_results=measurements,
                independently_checked_shortlist=shortlist,
                note="Each experiment is a momentary perturbation. No continuous animation or saved rig has been approved.")
 except Exception as e:
  report.update(status="FAIL_EXECUTION",error=str(e),traceback=traceback.format_exc())
 (out/"round23_single_actuator_ablation.json").write_text(json.dumps(report,indent=2,ensure_ascii=False))
 print("ROUND23_STATUS",report["status"],"TRIALS",report.get("attempts"),"SHORTLIST",len(report.get("independently_checked_shortlist",[])))
 if report["status"]!="PASS_CONTROLLED_SINGLE_ACTUATOR_SENSITIVITY_NO_REPAIR":
  print(report.get("traceback"));raise SystemExit(1)
if __name__=="__main__":main()
