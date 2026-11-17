"""Round40: independent fresh-Blender-process readback of saved Round39 file.

Only a saved, independently reopened .blend can be called numerical L3.
Compares the exact original 49-bone v8 action, per-frame evaluated geometry,
true shape-key action driver/keyframes, signed-area orientation, BVH collisions,
six anatomical ROI p95, loop seam, and actual rendered anatomy views.
Numerical acceptance is NOT human visual L4 approval or glTF/Godot L5.
"""
import bpy,sys,runpy,hashlib,json,traceback,csv
from pathlib import Path
import numpy as np

ACT="run_sprint_v8_ik_phase_NUMERIC_REVIEW"
EXPECTED_SHA="bf24c3c00367790af976e5f407cb9c3b20ad11754845bd0eb63d5cbe4042d07b"
SOURCE_SHA="984a21447c0217bc8ff91d02f9af1509324aa94dfaf29c543abd3d92f9b12c70"

def cli():
 import argparse
 p=argparse.ArgumentParser()
 for arg in ("--baseline","--candidate","--expected","--out"):p.add_argument(arg,required=True)
 return p.parse_args(sys.argv[sys.argv.index("--")+1:])

def keys_and_bones(path,helper):
 bpy.ops.wm.open_mainfile(filepath=str(path))
 obj,arm=helper["model"]()
 act=bpy.data.actions.get(ACT)
 if not act:raise RuntimeError("Original verified run action was lost")
 arm.animation_data_create()
 for tr in arm.animation_data.nla_tracks:tr.mute=True
 names=sorted(x.name for x in arm.pose.bones)
 bones={}
 values={}
 for f in (1,7,8,9,10,11,13,14,15,17,25):
  helper["pose"](arm,act,f)
  bones[f]=np.asarray([list(row) for name in names
                      for row in arm.pose.bones[name].matrix],dtype=np.float64)
  values[f]={k.name:float(k.value) for k in obj.data.shape_keys.key_blocks
             if k.name.startswith("R39_")}
 return bones,values

def read_static_basis(path,helper):
 # Evaluated unanimated poses can STILL be deformed by active IK constraints
 # and therefore cannot stand in for mesh rest/basis. Use actual datablock
 # coordinates, never a constraint-evaluated mesh, for topology/rest checks.
 bpy.ops.wm.open_mainfile(filepath=str(path))
 obj,arm=helper["model"]()
 vertices=np.asarray([[float(v) for v in point.co] for point in obj.data.vertices])
 bone_rest=np.asarray([list(row) for name in sorted(x.name for x in arm.data.bones)
                        for row in arm.data.bones[name].matrix_local],dtype=np.float64)
 return vertices,bone_rest

def main():
 a=cli();output=Path(a.out).resolve();output.mkdir(parents=True,exist_ok=True)
 report={"status":"STARTED","assurance":"Independent actual Blender 5.1.2 L3 readback + L4 render files only"}
 try:
  basepath=Path(a.baseline).resolve();canpath=Path(a.candidate).resolve()
  expected=json.loads(Path(a.expected).read_text())
  if expected["status"]!="PASS_COMPLETED_10_REFERENCE_RESTORE_PROFILES_L3_SCREEN":
   raise RuntimeError("Round39 first-level candidate report is not a completed planned experiment")
  assert hashlib.sha256(basepath.read_bytes()).hexdigest()==SOURCE_SHA
  assert hashlib.sha256(canpath.read_bytes()).hexdigest()==EXPECTED_SHA
  if expected["conditionally_saved_review_model"]["sha256"]!=EXPECTED_SHA:
   raise RuntimeError("Saved source digest and claimed experiment disagree")
  H=runpy.run_path("rig-experiments/round19e_clean_candidate_qa.py",run_name="r40_h")
  D=runpy.run_path("rig-experiments/round11_rootcause.py",run_name="r40_d")
  R=runpy.run_path("rig-experiments/round20_full_cycle_geometry.py",run_name="r40_r")
  G=runpy.run_path("rig-experiments/round17_reopen_surface.py",run_name="r40_g")
  original=R["load_and_sample"](basepath,H,D)
  saved=R["load_and_sample"](canpath,H,D)
  if original["polys"]!=saved["polys"] or original["edges"]!=saved["edges"] or original["rois"]!=saved["rois"]:
   raise RuntimeError("Saved Round39 topology/body ROI/vertex connectivity changed")
  # The 'load_and_sample' reference neutral pose with action=None is NOT
  # a true rest mesh: active IK/constraint matrices may deform it differently
  # when the intended 290 skin weights were changed. Compare immutable
  # datablock Basis + bone rest transforms instead, fail on *actual* changes.
  pseudo_rest_drift=max((p-q).length for p,q in zip(original["rest"],saved["rest"]))
  source_basis,source_bones=read_static_basis(basepath,H)
  candidate_basis,candidate_bones=read_static_basis(canpath,H)
  rest_max=float(np.max(np.linalg.norm(source_basis-candidate_basis,axis=1)))
  bone_rest_drift=float(np.max(np.abs(source_bones-candidate_bones)))
  if rest_max>1e-7:raise RuntimeError("Candidate modified original raw base mesh vertex coordinates")
  if bone_rest_drift>1e-7:raise RuntimeError("Candidate modified original 49-bone rest matrices")
  if max(original["seam"],saved["seam"])>1e-5:raise RuntimeError("Baked original/candidate loop closure failed")
  basebones,_=keys_and_bones(basepath,H)
  newbones,keyvalues=keys_and_bones(canpath,H)
  maximum_bone_matrix_drift=max(float(np.max(np.abs(basebones[f]-newbones[f]))) for f in basebones)
  if maximum_bone_matrix_drift>1e-5:raise RuntimeError("49-bone source gait/IK changed in candidate")
  values14=keyvalues[14]
  if "R39_F14_ORIGINAL_REFERENCE" not in values14:
   raise RuntimeError("Saved f14 repair shape key missing")
  if abs(values14["R39_F14_ORIGINAL_REFERENCE"]-.90)>.0005:
   raise RuntimeError("Frame14 shape key was NOT baked to expected 0.90")
  if abs(keyvalues[1]["R39_F14_ORIGINAL_REFERENCE"])>1e-5 or abs(keyvalues[25]["R39_F14_ORIGINAL_REFERENCE"])>1e-5:
   raise RuntimeError("Baked corrective not truly zero outside the periodic f14 window")
  edges,tris,rest_areas=R["fixed_topology"](original)
  selected=max((t for t in expected["trials"] if t["strict_full_l3_pass"]),
               key=lambda t:t["belly_worst_p95_improvement"])
  if selected["label"]!="reference0.90_width0.20":
   raise RuntimeError("Expected saved best trial selection changed")
  frame_diagnostics=[];fail=[];max_predicted=0.;worst_belly=0.;worst_original=0.
  largest_side=0.;refs=selected["frames"]
  for f in range(1,25):
   prev=original["poses"][f];now=saved["poses"][f]
   old_strain=R["strain"](prev,edges);new_strain=R["strain"](now,edges)
   oa=R["area"](prev,tris,rest_areas);na=R["area"](now,tris,rest_areas)
   actual=G["normals_overlap"](tris,prev,now)
   orientation=H["coorient"](original["rest"],prev,now,tris,original["rot"][f])
   oldbad=actual["baseline_nonadjacent_overlaps"]
   newbad=actual["candidate_nonadjacent_overlaps"]
   worst_belly=max(worst_belly,new_strain["interleg"]["p95"])
   worst_original=max(worst_original,old_strain["interleg"]["p95"])
   for region,stat in new_strain.items():
    if region!="interleg":
     largest_side=max(largest_side,stat["p95"]-old_strain[region]["p95"])
   pr=refs[f-1]
   if pr["frame"]!=f:raise RuntimeError("Authored trial order no longer matches frames")
   discrepancy=max(abs(na["min"]-pr["min_area"]),
                   abs(new_strain["interleg"]["p95"]-pr["interleg_p95"]))
   max_predicted=max(max_predicted,discrepancy)
   if na["under_half"]!=pr["under_half"] or discrepancy>.0003:
    fail.append({"frame":f,"error":"saved_reopen_vs_original_in_memory_trial_drift",
                 "metric_abs_error":discrepancy,"area_under_half_saved":na["under_half"],
                 "area_under_half_planned":pr["under_half"]})
   if orientation["new_reference_inversions"]:
    fail.append({"frame":f,"error":"new_corotated_normal_inversions",
                 "count":orientation["new_reference_inversions"]})
   if newbad>oldbad:
    fail.append({"frame":f,"error":"new_nonadjacent_BVH_overlaps","before":oldbad,"after":newbad})
   if na["min"]<oa["min"]-.002:
    fail.append({"frame":f,"error":"minimum_face_area_regression","before":oa["min"],"after":na["min"]})
   if na["under_half"]>oa["under_half"]:
    fail.append({"frame":f,"error":"half_area_count_regression","before":oa["under_half"],"after":na["under_half"]})
   frame_diagnostics.append({"frame":f,"interleg_p95_before":old_strain["interleg"]["p95"],
       "interleg_p95_saved":new_strain["interleg"]["p95"],"source_bvh":oldbad,
       "saved_bvh":newbad,"minimum_area_before":oa["min"],"minimum_area_saved":na["min"],
       "underhalf_source":oa["under_half"],"underhalf_saved":na["under_half"],
       "new_reference_inversions":orientation["new_reference_inversions"],
       "per_region_p95_original":{k:v["p95"] for k,v in old_strain.items()},
       "per_region_p95_candidate":{k:v["p95"] for k,v in new_strain.items()}})
  if worst_original-worst_belly<=.01:
   fail.append({"error":"insufficient_belly_worst_p95_improvement","before":worst_original,"after":worst_belly})
  if largest_side>.004:
   fail.append({"error":"other_anatomical_region_p95_regression","worst":largest_side})
  report.update(status="PASS_FRESH_REOPEN_L3_CANDIDATE_L4_AND_L5_PENDING" if not fail else "REJECT_FRESH_REOPEN_ANATOMICAL_L3",
     source_sha256=SOURCE_SHA, saved_blend_sha256=EXPECTED_SHA,mesh_restitution_error=rest_max,
     constraint_evaluated_false_rest_max_difference=pseudo_rest_drift,
     rest_bone_local_matrix_max_difference=bone_rest_drift,
     bone_action_all_sampled_matrix_max_drift=maximum_bone_matrix_drift,
     original_seam=original["seam"],candidate_seam=saved["seam"],
     f14_saved_reference_value=values14["R39_F14_ORIGINAL_REFERENCE"],
     predicted_vs_reopened_largest_metric_error=max_predicted,
     original_worst_belly_p95=worst_original,readback_worst_belly_p95=worst_belly,
     max_other_roi_p95_framewise_regression=largest_side,
     frames=frame_diagnostics,issues=fail)
  if not fail:
   # Render actually reopened saved candidate in *independent Blender process*,
   # matching the source side/underside/quarter/body reference cameras.
   frames=(9,10,14,17)
   for label,path in (("original_v8",basepath),("saved_round39",canpath)):
    bpy.ops.wm.open_mainfile(filepath=str(path))
    o,arm=H["model"]()
    act=bpy.data.actions.get(ACT)
    arm.animation_data_create()
    for tr in arm.animation_data.nla_tracks:tr.mute=True
    roi=D["collect"](o,arm)
    for f in frames:
     D["render_pose"](o,arm,act,f,output/(label+"_L4_VIEWS"),roi,closeup=True)
   report["rendered_frames"]=list(frames)
   report["render_quality"]="Generated actual Blender geometry images; not yet human reviewed"
  with (output/"round40_reopened_24frame_evidence.csv").open("w",newline="") as fp:
   cols=("frame","interleg_p95_before","interleg_p95_saved","source_bvh","saved_bvh",
         "minimum_area_before","minimum_area_saved","underhalf_source","underhalf_saved",
         "new_reference_inversions")
   w=csv.DictWriter(fp,fieldnames=cols);w.writeheader()
   for row in frame_diagnostics:w.writerow({k:row[k] for k in cols})
 except Exception as ex:
  report.update(status="FAIL_EXECUTION",error=str(ex),traceback=traceback.format_exc())
 (output/"round40_independent_saved_reopen.json").write_text(json.dumps(report,indent=2,ensure_ascii=False))
 print("ROUND40",report["status"],"f14",report.get("f14_saved_reference_value"),
       "readback",report.get("predicted_vs_reopened_largest_metric_error"),
       "issues",report.get("issues",[])[:10])
 if report["status"]!="PASS_FRESH_REOPEN_L3_CANDIDATE_L4_AND_L5_PENDING":
  print(report.get("traceback"));raise SystemExit(1)
if __name__=="__main__":main()
