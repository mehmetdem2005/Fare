"""Round24 spatially guarded skin weighting hypotheses from exact immutable v8.
Attempt to keep beneficial fore/hind weight redistribution while explicitly
protecting frame-local folds. Exact LBS-linear source/candidate interpolation
is independently validated on known saved Blender files. No BLEND mutation.
Full 24 frames and BVH of all shortlisted variants; NO production claim.
"""
import bpy,sys,math,json,hashlib,traceback,itertools,runpy
from pathlib import Path
import numpy as np
from mathutils.bvhtree import BVHTree

ACT="run_sprint_v8_ik_phase_NUMERIC_REVIEW"
SENTINELS=(434,216,812,467,351)
RELATED=(350,352,349,214,217,223,816,815,470)

def cli():
 import argparse
 p=argparse.ArgumentParser()
 for k in ("--baseline","--candidate","--out"):p.add_argument(k,required=True)
 return p.parse_args(sys.argv[sys.argv.index("--")+1:])

def read_weights(path,helper):
 bpy.ops.wm.open_mainfile(filepath=str(path))
 ob,arm=helper["model"]()
 w=helper["extract"](ob)
 return w,[(float(v.co.x),float(v.co.y),float(v.co.z)) for v in ob.data.vertices]

def eval_arrays(data):
 return np.asarray([[[float(q) for q in pos] for pos in data["poses"][f]] for f in range(1,25)],dtype=np.float64)

def graph_seeds(mode,tris,rest,area_ref,original,candidate,n):
 seeds=set(SENTINELS)
 if mode in ("related","all"):
  seeds.update(RELATED)
 if mode=="all":
  # Additional observed area-collapse candidates, not fitted to a single frame.
  for f in (7,8,9,10,11,14,15,16,17):
   b=original[f-1];c=candidate[f-1]
   aa=np.asarray(tris,dtype=np.int32)
   def area(x):
    v=np.cross(x[aa[:,1]]-x[aa[:,0]],x[aa[:,2]]-x[aa[:,0]])
    return np.linalg.norm(v,axis=1)/area_ref
   old=area(b);new=area(c)
   drop=old-new
   # Both absolute collapse and relative deterioration matter.
   indices=np.where((drop>.02)&(new<.45))[0]
   seeds.update(int(i) for i in indices)
  if len(seeds)>200:
   # Keep the exact fixed sentinel list plus the most serious 100 suspects;
   # record seed count for reproducibility.
   seeds=set(SENTINELS)|set(RELATED)|set(sorted(seeds)[:100])
 ids=set()
 for tid in seeds:
  if tid<0 or tid>=len(tris):raise RuntimeError("Invalid unchanged triangle index")
  ids.update(tris[tid])
 return sorted(seeds),sorted(ids)

def changes_from_saved(source_weights,saved_weights):
 modified=[];bound=0.
 for i,(x,y) in enumerate(zip(source_weights,saved_weights)):
  names=set(x)|set(y)
  delta=max([abs(x.get(k,0.)-y.get(k,0.)) for k in names] or [0.])
  if delta>2e-7:
   modified.append(i)
   bound=max(bound,delta)
 if len(modified)!=290:raise RuntimeError("Saved 0.170 model modified unexpected number of verts: "+str(len(modified)))
 return np.array(modified,dtype=np.int32),bound

def per_frame_bvh(x,triangles):
 # BVH pairs are screening proxies, not volumetric interpenetration proof.
 t=BVHTree.FromPolygons(x.tolist(),triangles,all_triangles=True,epsilon=1e-7)
 pairs=set()
 for a,b in t.overlap(t):
  if a>=b or set(triangles[a]).intersection(triangles[b]):continue
  pairs.add((a,b))
 return len(pairs)

def main():
 a=cli();out=Path(a.out).resolve();out.mkdir(parents=True,exist_ok=True)
 result={"status":"STARTED","quality":"L3 weight-only LBS linearity screen, no model edits; must be independently saved/reopened if candidate exists"}
 try:
  root="rig-experiments/"
  h=runpy.run_path(root+"round19e_clean_candidate_qa.py",run_name="r24_h")
  d=runpy.run_path(root+"round11_rootcause.py",run_name="r24_d")
  r20=runpy.run_path(root+"round20_full_cycle_geometry.py",run_name="r24_20")
  basepath=Path(a.baseline).resolve();canpath=Path(a.candidate).resolve()
  original=r20["load_and_sample"](basepath,h,d)
  saved=r20["load_and_sample"](canpath,h,d)
  if original["hash"]!=saved["hash"] or original["polys"]!=saved["polys"] or original["edges"]!=saved["edges"]:
   raise RuntimeError("Source/candidate rest/rig constraints unexpectedly differ")
  edges,tris,restarea=r20["fixed_topology"](original)
  W0,vertices=read_weights(basepath,h)
  W1,_=read_weights(canpath,h)
  changed,max_delta=changes_from_saved(W0,W1)
  P0=eval_arrays(original);P1=eval_arrays(saved)
  if P0.shape!=(24,19466,3):raise RuntimeError("Wrong evaluated source vertex array shape")
  unchanged=np.ones(19466,dtype=bool);unchanged[changed]=False
  largest_unmodified=float(np.max(np.linalg.norm(P1[:,unchanged,:]-P0[:,unchanged,:],axis=2)))
  if largest_unmodified>2e-5:raise RuntimeError("Weight-only candidate changed original unmodified vertices or action: %.9g"%largest_unmodified)
  delta=(P1-P0)[:,changed,:]
  tris_arr=np.asarray(tris,dtype=np.int32)
  a0=tris_arr[:,0];b0=tris_arr[:,1];c0=tris_arr[:,2]
  inv_rest=1./np.asarray(restarea,dtype=np.float64)[None,:]
  rest=np.asarray([[float(q) for q in p] for p in original["rest"]])
  normals=np.cross(rest[b0]-rest[a0],rest[c0]-rest[a0])
  length=np.linalg.norm(normals,axis=1)
  norm=normals/length[:,None]
  rotated=np.asarray([norm@np.asarray([list(row) for row in original["rot"][f].to_matrix()]).T for f in range(1,25)])
  def get_surface(x):
   cross=np.cross(x[:,b0]-x[:,a0],x[:,c0]-x[:,a0])
   areas=np.linalg.norm(cross,axis=2)*inv_rest
   # The sign test compares each triangle to its co-rotated source rest normal.
   signed=np.einsum("ftk,ftk->ft",cross,rotated)
   return areas,signed
  area_base,signed_base=get_surface(P0)
  base_bad=signed_base<0
  base_min=np.min(area_base,axis=1)
  base_under=np.sum(area_base<.5,axis=1)
  reg_edges={}
  for name,es in edges.items():
   ee=np.asarray(es,dtype=np.float64)
   reg_edges[name]=(ee[:,0].astype(np.int32),ee[:,1].astype(np.int32),ee[:,2])
  def get_p95(x):
   out={}
   for name,(ia,ib,length) in reg_edges.items():
    delta_xyz=x[:,ib,:]-x[:,ia,:]
    strain=np.abs(np.linalg.norm(delta_xyz,axis=2)/length[None,:]-1.)
    out[name]=np.percentile(strain,95,axis=1,method="nearest")
   return out
  strain_base=get_p95(P0)
  results=[];numerical_candidates=[]
  # Deterministic fixed family. Four strengths × three radii × three hotspot
  # seed sets; never optimize to only frame 15.
  for mode,strength,radius in itertools.product(("sentinel","related","all"),(.06,.10,.14,.17),(.012,.025,.045)):
   tids,seed_ids=graph_seeds(mode,tris,rest,np.asarray(restarea),P0,P1,len(changed))
   seeds=rest[seed_ids];coords=rest[changed]
   # At most 290×~1000 coordinates, with exact seed selection from fixed IDs.
   mindist=np.sqrt(np.min(np.sum((coords[:,None,:]-seeds[None,:,:])**2,axis=2),axis=1))
   t=np.clip(mindist/radius,0,1);t=t*t*(3-2*t)
   frac=(strength/.17)*t
   x=P0.copy()
   x[:,changed,:]+=delta*frac[None,:,None]
   ar,ns=get_surface(x)
   new_bad=(ns<0)&~base_bad
   min_area=np.min(ar,axis=1)
   under=np.sum(ar<.5,axis=1)
   strains=get_p95(x)
   max_improvement=float(np.max(strain_base["interleg"])-np.max(strains["interleg"]))
   roi_max_regress=max(float(np.max(strains[name]-strain_base[name])) for name in ("front","central","rear","foreleg","head"))
   failures={
     "new_corotated_normal_inversions":int(np.sum(new_bad)),
     "frames_with_new_inversions":[int(i+1) for i in np.where(np.any(new_bad,axis=1))[0]],
     "worst_min_area_loss":float(np.max(base_min-min_area)),
     "min_area_regressed_frames":[int(i+1) for i in np.where(min_area<base_min-.002)[0]],
     "under_half_face_increase":int(np.max(under-base_under)),
     "worst_auxiliary_roi_p95_framewise_regression":roi_max_regress,
     "global_belly_worst_p95_before":float(np.max(strain_base["interleg"])),
     "global_belly_worst_p95_after":float(np.max(strains["interleg"])),
     "belly_worst_p95_improvement":max_improvement}
   passes_fast=(failures["new_corotated_normal_inversions"]==0
                and not failures["min_area_regressed_frames"]
                and max_improvement>.01 and roi_max_regress<.004
                and failures["under_half_face_increase"]<=0)
   label="%s_%.3f_%.3f"%(mode,strength,radius)
   record={"label":label,"seed_mode":mode,"strength":strength,"radius":radius,
           "seed_triangles":len(tids),"seed_vertices":len(seed_ids),
           "strength_applied_min":float(np.min(frac)),
           "strength_applied_max":float(np.max(frac)),
           "changed_weight_eligible_vertices":len(changed),
           "fast_screen_pass":bool(passes_fast),"metrics":failures}
   if passes_fast:
    # Expensive BVH stage is only run on geometrically plausible candidates.
    bvh_before=[];bvh_after=[]
    for frame in range(24):
     bvh_before.append(per_frame_bvh(P0[frame],tris))
     bvh_after.append(per_frame_bvh(x[frame],tris))
    record["bvh_before"]=bvh_before;record["bvh_after"]=bvh_after
    record["bvh_frames_increased"]=[i+1 for i in range(24) if bvh_after[i]>bvh_before[i]]
    record["full_L3_screen_pass"]=not record["bvh_frames_increased"]
    if record["full_L3_screen_pass"]:numerical_candidates.append(record)
   else:record["full_L3_screen_pass"]=False
   results.append(record)
   print("ROUND24_TEST",label,"fast",passes_fast,"flips",failures["new_corotated_normal_inversions"],
         "area_frames",failures["min_area_regressed_frames"],
         "improvement",round(max_improvement,5))
  selected=sorted(numerical_candidates,key=lambda x:-x["metrics"]["belly_worst_p95_improvement"])
  result.update(status="PASS_HYPOTHESIS_SCREEN_NO_ANATOMY_APPROVAL",count=len(results),
       checked_full_24_frames=True,original_source_sha256=hashlib.sha256(basepath.read_bytes()).hexdigest(),
       saved_comparison_sha256=hashlib.sha256(canpath.read_bytes()).hexdigest(),
       changed_vertices=len(changed),max_single_weight_delta=max_delta,
       unchanged_source_vertex_drift=largest_unmodified,
       original_interleg_worst=float(np.max(strain_base["interleg"])),
       strict_numeric_candidates=[r["label"] for r in selected],
       candidates=results,
       note="This uses exact saved original-vs-0.170 Blender evaluated vertices, linearly interpolated per ORIGINAL weight-change location. Any candidate must be applied to original Blender, explicitly invalidated, freshly saved, reopened and full geometry retested before L3 acceptance.")
 except Exception as ex:
  result.update(status="FAIL_EXECUTION",error=str(ex),traceback=traceback.format_exc())
 (out/"round24_spatial_mask_screen.json").write_text(json.dumps(result,indent=2,ensure_ascii=False))
 print("ROUND24",result["status"],"variants",result.get("count"),"numeric_candidates",result.get("strict_numeric_candidates"))
 if result["status"]!="PASS_HYPOTHESIS_SCREEN_NO_ANATOMY_APPROVAL":
  print(result.get("traceback"));raise SystemExit(1)
if __name__=="__main__":main()
