"""Round27: independently inspect real existing pose-driven shape keys in v8,
their in-sprint activation and causal manual activation at exact failure phases.
This audit DOES NOT rewrite scripts/correctives.py or rig. Tests 144 independent
single-key interventions by muting one driver at a time and restoring it, with
explicit baseline pose reset and zero-state-leak comparison.
"""
import bpy,sys,json,math,hashlib,traceback,runpy
from pathlib import Path
from mathutils import Vector

ACT="run_sprint_v8_ik_phase_NUMERIC_REVIEW"
FRAMES=(9,10,11,14,15,17)
SHAPES=("crv_shoulder_L","crv_shoulder_R","crv_hip_L","crv_hip_R",
        "crv_spine_curl","crv_spine_arch","crv_elbow_L","crv_elbow_R")
STRENGTH=(.25,.50,1.0)

def cli():
 import argparse
 p=argparse.ArgumentParser()
 for key in ("--baseline","--out"):p.add_argument(key,required=True)
 return p.parse_args(sys.argv[sys.argv.index("--")+1:])

def measure(pts,area_refs,tris,rest,quat,edge_sets):
 d={}
 ref=area_refs
 refnorm=[(rest[b]-rest[a]).cross(rest[c]-rest[a]) for a,b,c in tris]
 oriented=[quat@n for n in refnorm]
 signed=[];area=[]
 for (a,b,c),r,n in zip(tris,ref,oriented):
  cross=(pts[b]-pts[a]).cross(pts[c]-pts[a])
  signed.append(float(cross.dot(n)) / (r*(n.length or 1)))
  area.append(float(cross.length/r))
 for name,es in edge_sets.items():
  vals=sorted(abs((pts[b]-pts[a]).length/dist-1.) for a,b,dist in es)
  d[name+"_p95"]=vals[round((len(vals)-1)*.95)]
 d.update(min_area=min(area),normal_inverted=sum(v<0 for v in signed),
          under_half=sum(v<.5 for v in area))
 return d

def main():
 a=cli();out=Path(a.out).resolve();out.mkdir(parents=True,exist_ok=True)
 rep={"status":"STARTED","quality":"L3 real Blender activation test only; driver hack is experimental and never saved"}
 try:
  H=runpy.run_path("rig-experiments/round19e_clean_candidate_qa.py",run_name="r27h")
  D=runpy.run_path("rig-experiments/round11_rootcause.py",run_name="r27d")
  R=runpy.run_path("rig-experiments/round20_full_cycle_geometry.py",run_name="r27r")
  srcpath=Path(a.baseline).resolve()
  pre=R["load_and_sample"](srcpath,H,D)
  edges,tris,rest_areas=R["fixed_topology"](pre)
  bpy.ops.wm.open_mainfile(filepath=str(srcpath))
  ob,arm=H["model"]()
  action=bpy.data.actions.get(ACT)
  if not ob.data.shape_keys or not action:raise RuntimeError("Original action and/or corrective shape keys absent")
  keys=ob.data.shape_keys.key_blocks
  drvs=ob.data.shape_keys.animation_data.drivers if ob.data.shape_keys.animation_data else []
  fcurves={x.data_path:x for x in drvs}
  expected=[]
  for keyname in SHAPES:
   if keyname not in keys:raise RuntimeError("Missing original corrective "+keyname)
   path='key_blocks["'+keyname+'"].value'
   if path not in fcurves:raise RuntimeError("Original corrective is not driven "+keyname)
   fc=fcurves[path]
   if not fc.driver.variables:raise RuntimeError("Corrective driver has no variable "+keyname)
   var=fc.driver.variables[0]
   target=var.targets[0]
   expected.append({"name":keyname,"expression":fc.driver.expression,
         "variable_type":var.type,"bone":target.bone_target,"transform_type":target.transform_type,
         "space":target.transform_space,"valid":bool(fc.is_valid)})
  rep["drivers"]=expected
  samples=[];activated={k:0 for k in SHAPES}
  for f in range(1,25):
   H["pose"](arm,action,f)
   line={"frame":f}
   for k in SHAPES:
    line[k]=float(keys[k].value)
    if line[k]>1e-5:activated[k]+=1
   samples.append(line)
  rep["24frame_active_counts"]=activated;rep["24frame_values"]=samples
  rest=pre["rest"]
  perturb=[]
  for f in FRAMES:
   H["pose"](arm,action,f)
   ref=H["pts"](ob)
   Rq=pre["rot"][f]
   basic=measure(ref,rest_areas,tris,rest,Rq,edges)
   for k in SHAPES:
    # Every trial starts from the full untouched driven v8 pose state.
    key=keys[k];path='key_blocks["'+k+'"].value';fc=fcurves[path]
    driver_value=float(key.value)
    fc.mute=True
    bpy.context.view_layer.update()
    for level in STRENGTH:
     key.value=level
     bpy.context.view_layer.update()
     got=H["pts"](ob)
     s=measure(got,rest_areas,tris,rest,Rq,edges)
     baseline_change=max((got[i]-ref[i]).length for i in range(len(ref)))
     perturb.append({"frame":f,"key":k,"value":level,
       "original_driver_value":driver_value,"mesh_max_offset":baseline_change,
       "belly_p95_before":basic["interleg_p95"],"belly_p95_after":s["interleg_p95"],
       "foreleg_p95_change":s["foreleg_p95"]-basic["foreleg_p95"],
       "front_p95_change":s["front_p95"]-basic["front_p95"],
       "min_area_before":basic["min_area"],"min_area_after":s["min_area"],
       "new_normal_count":max(0,s["normal_inverted"]-basic["normal_inverted"]),
       "under_half_change":s["under_half"]-basic["under_half"]})
    fc.mute=False
    key.value=driver_value
    H["pose"](arm,action,f)
    recovered=H["pts"](ob)
    recovery_error=max((recovered[i]-ref[i]).length for i in range(len(ref)))
    if recovery_error>1e-5:
     raise RuntimeError("Driver restore pose-state contamination frame %d key %s displacement %f"%(f,k,recovery_error))
  rep.update(status="PASS_EXISTING_CORRECTIVE_DRIVER_CAUSAL_QA_NOT_A_REPAIR",
             attempted=len(perturb),source_sha256=hashlib.sha256(srcpath.read_bytes()).hexdigest(),
             trials=perturb,
             summary="Only existing corrective drivers were changed temporarily; no production or candidate model saved.")
 except Exception as e:rep.update(status="FAIL_EXECUTION",error=str(e),traceback=traceback.format_exc())
 (out/"round27_driver_activation_and_manual_ablation.json").write_text(json.dumps(rep,indent=2,ensure_ascii=False))
 print("ROUND27_STATUS",rep["status"],"ACTIVATIONS",rep.get("24frame_active_counts"),
       "TRIALS",rep.get("attempted"))
 if rep["status"]!="PASS_EXISTING_CORRECTIVE_DRIVER_CAUSAL_QA_NOT_A_REPAIR":
  print(rep["traceback"]);raise SystemExit(1)
if __name__=="__main__":main()
