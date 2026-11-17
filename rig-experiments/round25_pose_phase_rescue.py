"""Round25: time-continuous IK/hips pose rescue based on verified Round23 causal actions.
Both source v8 and independently saved rejected 0.170 candidate are tested
separately; neither is overwritten. 24+1 real Blender frame positions, all
1,069 triangles, six ROIs, rotated reference normals and BVH for fast finalists.
No GLB production export or approval; outputs remain numerical evidence only.
"""
import bpy,sys,json,math,hashlib,traceback,runpy
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ACT="run_sprint_v8_ik_phase_NUMERIC_REVIEW"

# Rotations are degrees; IK translations are Blender armature-space model units.
# Each periodic Gaussian has matched value in f1 and f25 for exact cycle closure.
PARAMS={
 "hipx_w2.8":[("rot","hips","X",-2.,15.5,2.8)],
 "hipx_w4":[("rot","hips","X",-2.,15.5,4.)],
 "hipx_strong":[("rot","hips","X",-3.,15.5,2.8)],
 "hipx_low":[("rot","hips","X",-1.,15.5,2.8)],
 "hipx_all":[("rot","hips","X",-2.,None,None)],
 "hipx_two_peaks":[("rot","hips","X",-1.3,14.,2.),("rot","hips","X",-1.3,17.,2.)],
 "foot_left_y_only":[("ik","ik_foot.L","Y",-.004,7.5,1.8)],
 "hip_y_10_only":[("rot","hips","Y",-2.,10.,1.5)],
 "hipx_and_footL":[("rot","hips","X",-2.,15.5,2.8),("ik","ik_foot.L","Y",-.004,7.5,1.8)],
 "hipx_and_handL":[("rot","hips","X",-2.,15.5,2.8),("ik","ik_hand.L","Z",-.004,7.5,1.8)],
 "hipx_footL_hipY":[("rot","hips","X",-2.,15.5,2.8),("ik","ik_foot.L","Y",-.004,7.5,1.8),("rot","hips","Y",-2.,10.,1.5)],
 "hipx_footL_footX":[("rot","hips","X",-2.,15.5,2.8),("ik","ik_foot.L","Y",-.004,7.5,1.8),("ik","ik_foot.L","X",-.004,10.,1.7)],
 "hipx_footL_spine":[("rot","hips","X",-2.,15.5,2.8),("ik","ik_foot.L","Y",-.004,7.5,1.8),("rot","spine_03","X",2.,17.,1.5)],
 "hipx_footL_handR":[("rot","hips","X",-2.,15.5,2.8),("ik","ik_foot.L","Y",-.004,7.5,1.8),("ik","ik_hand.R","Y",-.004,17.,1.5)],
 "hipx_footL_hipY_17":[("rot","hips","X",-2.,15.5,2.8),("ik","ik_foot.L","Y",-.004,7.5,1.8),("rot","hips","Y",2.,17.,1.5)],
 "hipx_w5_foot":[("rot","hips","X",-2.,15.5,5.),("ik","ik_foot.L","Y",-.004,7.5,1.8)]
}
def cli():
 import argparse
 p=argparse.ArgumentParser()
 for s in ("--baseline","--candidate","--out"):p.add_argument(s,required=True)
 return p.parse_args(sys.argv[sys.argv.index("--")+1:])

def cyc(frame,center,width):
 if center is None:return 1.
 ff=((frame-1)%24)+1
 diff=abs(ff-center);diff=min(diff,24-diff)
 return math.exp(-.5*(diff/width)**2)

def apply(B,arm,frame,recipe):
 for typ,bone,axis,magnitude,center,width in recipe:
  val=magnitude*cyc(frame,center,width)
  pb=B[bone]
  if typ=="rot":
   if pb.rotation_mode!="XYZ":raise RuntimeError("Expected XYZ rig bone rotation mode "+bone)
   e=pb.rotation_euler.copy();e["XYZ".index(axis)]+=math.radians(val);pb.rotation_euler=e
  else:
   v=Vector((val if axis=="X" else 0.,val if axis=="Y" else 0.,val if axis=="Z" else 0.))
   pb.location+=arm.data.bones[bone].matrix_local.to_3x3().inverted()@v
 bpy.context.view_layer.update()

def bvh(coords,triangles):
 tree=BVHTree.FromPolygons(coords.tolist(),triangles,all_triangles=True,epsilon=1e-7)
 pairs=set()
 for a,b in tree.overlap(tree):
  if a>=b or set(triangles[a]).intersection(triangles[b]):continue
  pairs.add((a,b))
 return len(pairs)

def run_model(model_path,recipe,helpers,triangles,rest_area,rest_norm,edge_arrays,base_coords,
              baseline_rot,base_signed,base_area,base_strain,base_bvh=None):
 bpy.ops.wm.open_mainfile(filepath=str(model_path))
 obj,arm=helpers["model"]()
 act=bpy.data.actions.get(ACT)
 arm.animation_data_create()
 for tr in arm.animation_data.nla_tracks:tr.mute=True
 if act is None:raise RuntimeError("Baseline gait action missing from real Blender")
 B=arm.pose.bones
 for typ,name,*_ in recipe:
  if name not in B:raise RuntimeError("Missing independent driver "+name)
 xyz=[];orient=[]
 for f in range(1,26):
  helpers["pose"](arm,act,f)
  apply(B,arm,f,recipe)
  xyz.append(np.asarray([[float(t) for t in v] for v in helpers["pts"](obj)],dtype=np.float64))
  if f<=24:
   orient.append(np.asarray([list(row) for row in (
      arm.matrix_world@B["spine_03"].matrix@
      arm.data.bones["spine_03"].matrix_local.inverted()@
      arm.matrix_world.inverted()).to_quaternion().to_matrix()]))
 seam=float(np.max(np.linalg.norm(xyz[0]-xyz[24],axis=1)))
 coord=np.stack(xyz[:24])
 tri=np.asarray(triangles,dtype=np.int32)
 a,b,c=tri[:,0],tri[:,1],tri[:,2]
 normal=np.cross(coord[:,b]-coord[:,a],coord[:,c]-coord[:,a])
 area=np.linalg.norm(normal,axis=2)/rest_area[None,:]
 oriented=np.einsum("ftk,ftk->ft",normal,np.stack([rest_norm@R.T for R in orient]))
 bad=oriented<0
 new_flips=bad&~base_signed
 reg_min=np.min(area,axis=1)<np.min(base_area,axis=1)-.002
 compressed=np.sum(area<.5,axis=1)-np.sum(base_area<.5,axis=1)
 reg={}
 for name,(i,j,rest_length) in edge_arrays.items():
  strain=np.abs(np.linalg.norm(coord[:,j,:]-coord[:,i,:],axis=2)/rest_length[None,:]-1.)
  reg[name]=np.asarray([np.partition(row,round((len(row)-1)*.95))[round((len(row)-1)*.95)] for row in strain])
 worst=float(np.max(reg["interleg"]))
 baseworst=float(np.max(base_strain["interleg"]))
 worst_side=max(float(np.max(reg[x]-base_strain[x])) for x in ("front","central","rear","foreleg","head"))
 fast=(seam<1e-5 and not np.any(new_flips) and not np.any(reg_min)
       and np.max(compressed)<=0 and worst<baseworst-.01 and worst_side<=.004)
 info={"loop_seam":seam,"strict_fast_pass":bool(fast),
       "worst_p95_interleg":worst,"baseline_worst_p95_interleg":baseworst,
       "worst_p95_improvement":baseworst-worst,
       "worst_other_roi_framewise_p95_regression":worst_side,
       "new_rest_normal_inversions":int(np.sum(new_flips)),
       "new_rest_normal_flip_frames":[int(x+1) for x in np.where(np.any(new_flips,axis=1))[0]],
       "minimum_area_regression_frames":[int(x+1) for x in np.where(reg_min)[0]],
       "worst_minimum_area_loss":float(np.max(np.min(base_area,axis=1)-np.min(area,axis=1))),
       "max_compressed_face_count_increase":int(np.max(compressed)),
       "min_area_per_frame":[float(q) for q in np.min(area,axis=1)]}
 if fast:
  basebvh=base_bvh if base_bvh is not None else [bvh(x,triangles) for x in base_coords]
  candidatebvh=[bvh(x,triangles) for x in coord]
  info.update(bvh_source=basebvh,bvh_candidate=candidatebvh,
              bvh_regression_frames=[i+1 for i in range(24) if candidatebvh[i]>basebvh[i]])
  info["strict_full_L3_pass"]=not info["bvh_regression_frames"]
 else:info["strict_full_L3_pass"]=False
 return info

def main():
 a=cli();out=Path(a.out).resolve();out.mkdir(parents=True,exist_ok=True)
 rep={"status":"STARTED","quality":"L3 real 24+1 Blender evaluated mesh trial; L4/L5 not approved"}
 try:
  root="rig-experiments/"
  h=runpy.run_path(root+"round19e_clean_candidate_qa.py",run_name="r25_h")
  d=runpy.run_path(root+"round11_rootcause.py",run_name="r25_d")
  r20=runpy.run_path(root+"round20_full_cycle_geometry.py",run_name="r25_20")
  original=r20["load_and_sample"](Path(a.baseline).resolve(),h,d)
  rejected=r20["load_and_sample"](Path(a.candidate).resolve(),h,d)
  if original["hash"]!=rejected["hash"] or original["polys"]!=rejected["polys"]:
   raise RuntimeError("Saved source provenance or 49 bone rest changed")
  edges,triangles,rest_areas=r20["fixed_topology"](original)
  coords=np.asarray([[[float(q) for q in v] for v in original["poses"][f]] for f in range(1,25)])
  rest=np.asarray([[float(q) for q in v] for v in original["rest"]])
  tt=np.asarray(triangles,dtype=np.int32)
  i,j,k=tt[:,0],tt[:,1],tt[:,2]
  ref=np.cross(rest[j]-rest[i],rest[k]-rest[i])
  ref=ref/np.linalg.norm(ref,axis=1)[:,None]
  n=np.cross(coords[:,j]-coords[:,i],coords[:,k]-coords[:,i])
  orig_area=np.linalg.norm(n,axis=2)/np.asarray(rest_areas)[None,:]
  rotations=np.asarray([np.asarray([list(row) for row in original["rot"][f].to_matrix()]) for f in range(1,25)])
  base_signed=np.einsum("ftk,ftk->ft",n,np.stack([ref@R.T for R in rotations]))<0
  edge_arr={}
  original_strain={}
  for name,ee in edges.items():
   e=np.asarray(ee)
   ia,ib=e[:,0].astype(np.int32),e[:,1].astype(np.int32)
   lengths=e[:,2].astype(float)
   edge_arr[name]=(ia,ib,lengths)
   ss=np.abs(np.linalg.norm(coords[:,ib,:]-coords[:,ia,:],axis=2)/lengths[None,:]-1.)
   original_strain[name]=np.asarray([np.partition(row,round((len(row)-1)*.95))[round((len(row)-1)*.95)] for row in ss])
  results=[];passing=[]
  for origin,path in (("original_v8",Path(a.baseline).resolve()),("rejected_weight_0p170",Path(a.candidate).resolve())):
   for name,recipe in PARAMS.items():
    r=run_model(path,recipe,h,triangles,np.asarray(rest_areas),ref,edge_arr,
       coords,rotations,base_signed,orig_area,original_strain)
    row=dict(source=origin,name=name,recipe=recipe,metrics=r)
    results.append(row)
    if r["strict_full_L3_pass"]:passing.append(row)
    print("ROUND25_CASE",origin,name,"fast",r["strict_fast_pass"],"L3",r["strict_full_L3_pass"],
          "flip",r["new_rest_normal_inversions"],"area",r["minimum_area_regression_frames"],
          "delta_p95",round(r["worst_p95_improvement"],5))
  rep.update(status="PASS_CONTROLLED_24_FRAME_POSE_SCAN_NO_PRODUCTION_APPROVAL",
     attempted=len(results),profiles=len(PARAMS),checked_frames=24,
     numerically_passing=[x["source"]+":"+x["name"] for x in passing],
     source_sha256=hashlib.sha256(Path(a.baseline).read_bytes()).hexdigest(),
     rejected_saved_candidate_sha256=hashlib.sha256(Path(a.candidate).read_bytes()).hexdigest(),
     attempts=results,
     note="NO .blend production deliverable. Even numerical pass still needs independently baked and reopened action, L4 manual render and L5 Godot contact review.")
 except Exception as ex:rep.update(status="FAIL_EXECUTION",error=str(ex),traceback=traceback.format_exc())
 (out/"round25_full_cycle_pose_profiles.json").write_text(json.dumps(rep,indent=2,ensure_ascii=False))
 print("ROUND25_STATUS",rep["status"],"attempts",rep.get("attempted"),
       "numerical_pass",rep.get("numerically_passing"))
 if rep["status"]!="PASS_CONTROLLED_24_FRAME_POSE_SCAN_NO_PRODUCTION_APPROVAL":
  print(rep.get("traceback"));raise SystemExit(1)
if __name__=="__main__":main()
