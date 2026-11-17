"""Round26: pose-local *signed* triangle area corrective blendshapes.
Unlike R17's unsigned-area-only trials, use baseline reference orientation,
per-face triangle signed-area barriers and 1-ring protections. Inverse map
each target back through genuine evaluated armature LBS. All pose targets
are applied to an independent saved/reopened 0.170 file, NEVER production.
All 24 frames and seam checked; any actual Blender candidate must pass L3.
NO Automatic Weights, no code path editing source model.
"""
import bpy,sys,math,json,hashlib,traceback,runpy
from pathlib import Path
from mathutils import Vector,Matrix
import numpy as np
from mathutils.bvhtree import BVHTree

ACT="run_sprint_v8_ik_phase_NUMERIC_REVIEW"
TARGETS={7:(467,),8:(351,),9:(434,),10:(434,),11:(434,),14:(216,),17:(812,)}
FRAMES=tuple(range(1,25))
PROFILE=[("narrow",.32,.65),("narrow_strong",.32,1.),
         ("medium",.55,.65),("medium_strong",.55,1.),
         ("broad",.85,.65),("broad_strong",.85,1.),
         ("long",1.15,.70),("long_strong",1.15,1.)]

def cli():
 import argparse
 p=argparse.ArgumentParser()
 for opt in ("--baseline","--candidate","--out"):p.add_argument(opt,required=True)
 return p.parse_args(sys.argv[sys.argv.index("--")+1:])

def full_coords(helper,ob):
 return np.asarray([[float(q) for q in p] for p in helper["pts"](ob)],dtype=np.float64)

def signed(coords,tris,reference_norm,rest_area,rotation):
 m=rotation.to_matrix()
 exp=np.asarray([list(row) for row in m],dtype=float)@reference_norm.T
 rotated=exp.T
 aa=np.asarray(tris,dtype=np.int32)
 x,y,z=aa[:,0],aa[:,1],aa[:,2]
 cross=np.cross(coords[y]-coords[x],coords[z]-coords[x])
 return np.einsum("ij,ij->i",cross,rotated)/rest_area, np.linalg.norm(cross,axis=1)/rest_area

def pulse(f,center,width):
 f=((f-1)%24)+1
 d=abs(f-center);d=min(d,24-d)
 return math.exp(-.5*(d/width)**2)

def count_bvh(coords,tris):
 b=BVHTree.FromPolygons(coords.tolist(),tris,all_triangles=True,epsilon=1e-7)
 result=set()
 facesets=[set(t) for t in tris]
 for i,j in b.overlap(b):
  if i>=j or facesets[i].intersection(facesets[j]):continue
  result.add((i,j))
 return len(result)

def solve_frame(initial,comparison,triangles,refs,areas,rotation,
                target_ids,eligible,max_cap=0.009,iteration_limit=95):
 original=initial.copy()
 triarr=np.asarray(triangles,dtype=np.int32)
 nrm=(np.asarray([list(row) for row in rotation.to_matrix()])@refs.T).T
 base_signed,base_area=signed(comparison,triangles,refs,areas,rotation)
 source_signed,source_area=signed(initial,triangles,refs,areas,rotation)
 # Editable vertices: targeted corners and their immediate topology neighbors
 # of body ROI only. Do not change any other part of the mesh.
 adj={i:set() for t in triarr for i in t}
 for a,b,c in triarr:
  adj[a].update((b,c));adj[b].update((a,c));adj[c].update((a,b))
 centers={int(i) for faceid in target_ids for i in triarr[faceid]}
 vertices=set(centers)
 for i in tuple(centers):vertices.update(j for j in adj[i] if j in eligible)
 vertices.intersection_update(eligible)
 if not centers.issubset(vertices):raise RuntimeError("A target correction is outside anatomical interleg mask")
 changed=sorted(vertices)
 affected=[tid for tid,t in enumerate(triarr) if any(i in vertices for i in t)]
 # Preserve original sign (even if baseline reference-normal inverted), and
 # never permit newly reversed faces. This corrects the R17 unsigned-area flaw.
 sign=np.where(base_signed>=0.,1.,-1.)
 bounds={}
 for tid in affected:
  before=source_signed[tid]*sign[tid]
  goal=0.
  if tid in target_ids:
   goal=min(.50,max(.30,abs(base_signed[tid])*.65))
  elif before>.04:
   goal=min(.09,before)
  elif before>=0.:
   goal=max(0.,before*.85)
  # Inverse already-existing rejected face is only targeted if explicitly
  # selected, rather than attempting to flip dozens of unrelated triangles.
  if goal>0.:bounds[tid]=goal
 targetset=set(target_ids)
 x=initial.copy()
 trace=[]
 for iteration in range(iteration_limit):
  # Strong face-target barriers first, followed by adjacent sign protection.
  priorities=sorted(bounds,key=lambda idx:(idx not in targetset,idx))
  changed_this=0
  max_deficit=0.
  for tid in priorities:
   a,b,c=map(int,triarr[tid])
   n=nrm[tid]*sign[tid]
   diff1=x[b]-x[a];diff2=x[c]-x[a]
   score=np.dot(np.cross(diff1,diff2),n)/areas[tid]
   shortage=bounds[tid]-score
   if shortage<=1e-4:continue
   grad=(np.cross(x[b]-x[c],n)/areas[tid],
         np.cross(x[c]-x[a],n)/areas[tid],
         np.cross(x[a]-x[b],n)/areas[tid])
   active=[(i,g) for i,g in zip((a,b,c),grad) if i in vertices]
   denom=sum(float(g@g) for _,g in active)
   if denom<1e-14:continue
   step=.48*shortage/denom
   for i,g in active:
    new=x[i]+step*g
    offset=new-original[i]
    length=np.linalg.norm(offset)
    if length>max_cap:new=original[i]+offset*(max_cap/length)
    x[i]=new
   changed_this+=1
   max_deficit=max(max_deficit,float(shortage))
  if iteration in (0,4,14,34,64,94):
   trace.append({"step":iteration,"active_faces":changed_this,"largest_face_deficit":max_deficit})
  if not changed_this:break
 after_signed,after_area=signed(x,triangles,refs,areas,rotation)
 displacement=np.linalg.norm(x-original,axis=1)
 return x,{"target_faces":[int(t) for t in target_ids],
  "modifiable_vertices":len(vertices),"moved_vertices":int(np.sum(displacement>1e-8)),
  "max_actual_world_displacement":float(np.max(displacement)),
  "face_results":[{"face":int(t),"original_signed":float(source_signed[t]),
        "baseline_signed":float(base_signed[t]),"after_signed":float(after_signed[t]),
        "original_area":float(source_area[t]),"after_area":float(after_area[t]),
        "baseline_area":float(base_area[t]),"target_signed_magnitude":float(bounds.get(t,0))}
     for t in target_ids],
  "new_local_reference_inversions":int(np.sum((after_signed*base_signed<0)&(source_signed*base_signed>=0))),
  "changed_neighbor_faces":len(affected),"trace":trace}

def main():
 args=cli();out=Path(args.out).resolve();out.mkdir(exist_ok=True,parents=True)
 report={"status":"STARTED","algorithm":"orientation-preserving triangle signed areas + inverse per-vertex skinning",
         "assurance":"real Blender 5.1.2 L3 only; not visually approved; no export"}
 try:
  root="rig-experiments/"
  h=runpy.run_path(root+"round19e_clean_candidate_qa.py",run_name="r26h")
  d=runpy.run_path(root+"round11_rootcause.py",run_name="r26d")
  r20=runpy.run_path(root+"round20_full_cycle_geometry.py",run_name="r26r20")
  r14=runpy.run_path(root+"round14_skinning_forensics.py",run_name="r26r14")
  orig_path=Path(args.baseline).resolve();can_path=Path(args.candidate).resolve()
  original=r20["load_and_sample"](orig_path,h,d)
  saved=r20["load_and_sample"](can_path,h,d)
  if original["hash"]!=saved["hash"] or original["polys"]!=saved["polys"] or original["edges"]!=saved["edges"]:
   raise RuntimeError("Saved candidate changed rest mesh, shape keys, rig or topology")
  if original["seam"]>1e-5 or saved["seam"]>1e-5:raise RuntimeError("Bad original 24-frame loop")
  edges,tris,arealist=r20["fixed_topology"](original)
  if len(tris)!=1069:raise RuntimeError("Unexpected body triangles")
  area_ref=np.asarray(arealist)
  rest=np.asarray([[float(q) for q in v] for v in original["rest"]])
  ti=np.asarray(tris,dtype=np.int32)
  normals=np.cross(rest[ti[:,1]]-rest[ti[:,0]],rest[ti[:,2]]-rest[ti[:,0]])
  norms=np.linalg.norm(normals,axis=1)
  refs=normals/norms[:,None]
  base=np.stack([np.asarray([[float(z) for z in v] for v in original["poses"][f]]) for f in FRAMES])
  saved_xyz=np.stack([np.asarray([[float(z) for z in v] for v in saved["poses"][f]]) for f in FRAMES])
  bpy.ops.wm.open_mainfile(filepath=str(can_path))
  ob,arm=h["model"]()
  action=bpy.data.actions.get(ACT)
  if action is None:raise RuntimeError("Source action not present")
  arm.animation_data_create()
  for tr in arm.animation_data.nla_tracks:tr.mute=True
  if not ob.data.shape_keys:raise RuntimeError("Existing supported pre-skin shape key basis absent")
  basekey=ob.data.shape_keys.key_blocks[0]
  region=set(original["rois"]["interleg"])
  targets={};solvers={};raw_deltas={}
  from mathutils import Matrix
  invworld=ob.matrix_world.to_3x3().inverted()
  for frame,targets_face in TARGETS.items():
   h["pose"](arm,action,frame)
   measured=full_coords(h,ob)
   err=float(np.max(np.linalg.norm(measured-saved_xyz[frame-1],axis=1)))
   if err>1e-5:raise RuntimeError("Blender pose mismatch before inverse skin, frame %d error %.7g"%(frame,err))
   adjusted,details=solve_frame(measured,base[frame-1],tris,refs,area_ref,
                                 original["rot"][frame],targets_face,region)
   mat=r14["vmat"](ob,arm)
   edits={}
   clipped=0;max_error=0.
   for i in np.where(np.linalg.norm(adjusted-measured,axis=1)>1e-7)[0]:
    weights=h["extract"](ob)[i] if False else {ob.vertex_groups[g.group].name:float(g.weight) for g in ob.data.vertices[i].groups}
    deform={name:val for name,val in weights.items() if name in mat}
    mass=sum(deform.values())
    if mass<1e-4:continue
    blended=Matrix(((0,0,0),(0,0,0),(0,0,0)))
    for nm,w in deform.items():blended+=mat[nm].to_3x3()*(w/mass)
    if abs(blended.determinant())<.16:clipped+=1;continue
    vector=Vector(invworld@Vector(adjusted[i]-measured[i]))
    delta=blended.inverted()@vector
    if delta.length>.017:
     clipped+=1;delta*=.017/delta.length
    predicted=ob.matrix_world.to_3x3()@(blended@delta)
    max_error=max(max_error,(predicted-Vector(adjusted[i]-measured[i])).length)
    edits[int(i)]=delta
   name="R26_SIGNED_FRAME_%02d"%frame
   key=ob.shape_key_add(name=name,from_mix=False)
   for i,delta in edits.items():key.data[i].co=basekey.data[i].co+delta
   key.value=0.
   targets[frame]=key;raw_deltas[frame]=edits
   details.update(frame=frame,key=name,shape_key_vertices=len(edits),
                  blend_inverse_reconstruction_error=max_error,clipped_vertices=clipped)
   solvers[frame]=details
   print("R26_LOCAL",frame,"changed",len(edits),"issues",[(x["face"],round(x["after_area"],5),
        round(x["after_signed"],5)) for x in details["face_results"]])
  # Compute actual full-cycle anatomy for every temporal mask profile.
  baseline_faces=[];baseline_min=[];baseline_under=[];base_inv=[];base_p95={}
  for name,links in edges.items():
   ij=np.asarray([(a,b) for a,b,_ in links],dtype=int)
   lengths=np.asarray([d for _,_,d in links])
   m=np.linalg.norm(base[:,ij[:,1]]-base[:,ij[:,0]],axis=2)/lengths[None,:]
   base_p95[name]=np.percentile(np.abs(m-1),95,axis=1,method="nearest")
  for f in FRAMES:
   sn,ar=signed(base[f-1],tris,refs,area_ref,original["rot"][f])
   baseline_min.append(float(np.min(ar)));baseline_under.append(int(np.sum(ar<.5)))
   base_inv.append(sn<0)
  base_inv=np.stack(base_inv)
  experiments=[]
  for label,width,strength in PROFILE:
   rows=[];coord_frames=[];bad_frames=[];area_frames=[];under_frames=[]
   frame_p95={k:[] for k in edges}
   for f in FRAMES+(25,):
    for fr,k in targets.items():k.value=strength*pulse(f,fr,width)
    h["pose"](arm,action,f)
    bpy.context.view_layer.update()
    co=full_coords(h,ob)
    if f==1:first=co
    if f==25:
     seam=float(np.max(np.linalg.norm(first-co,axis=1)))
     continue
    coord_frames.append(co)
    sn,area=signed(co,tris,refs,area_ref,original["rot"][f])
    new_inv=int(np.sum((sn<0)&~base_inv[f-1]))
    min_area=float(np.min(area))
    under_count=int(np.sum(area<.5))
    if new_inv:bad_frames.append(f)
    if min_area<baseline_min[f-1]-.002:area_frames.append(f)
    if under_count>baseline_under[f-1]:under_frames.append(f)
    per={"frame":f,"new_rest_normal_flips":new_inv,"min_area":min_area,
         "baseline_min_area":baseline_min[f-1],"under_half":under_count,
         "baseline_under_half":baseline_under[f-1]}
    for name,links in edges.items():
     strains=sorted(abs((Vector(co[j])-Vector(co[i])).length/d-1.) for i,j,d in links)
     row=strains[round((len(strains)-1)*.95)]
     per[name+"_p95"]=float(row)
     frame_p95[name].append(float(row))
    rows.append(per)
   worst=max(frame_p95["interleg"])
   improvement=float(np.max(base_p95["interleg"])-worst)
   other_regression=max(float(np.max(np.asarray(frame_p95[n])-base_p95[n])) for n in edges if n!="interleg")
   safe_fast=(seam<1e-5 and not bad_frames and not area_frames and not under_frames
              and improvement>.01 and other_regression<.004)
   result={"label":label,"pulse_width":width,"strength":strength,"loop_seam":seam,
       "belly_worst_p95_improvement":improvement,"worst_other_roi_regression":other_regression,
       "new_inversion_frames":bad_frames,"min_area_loss_frames":area_frames,
       "underhalf_increase_frames":under_frames,"strict_fast_gate":safe_fast,"frames":rows}
   if safe_fast:
    before=[count_bvh(base[f-1],tris) for f in FRAMES]
    after=[count_bvh(coord_frames[f-1],tris) for f in FRAMES]
    result.update(bvh_source=before,bvh_test=after,
            bvh_regression_frames=[f for f in FRAMES if after[f-1]>before[f-1]])
    result["strict_full_l3_pass"]=not result["bvh_regression_frames"]
   else:result["strict_full_l3_pass"]=False
   experiments.append(result)
   print("R26_TRIAL",label,"fast",safe_fast,"inv",bad_frames,"area",area_frames,
         "under",under_frames,"p95delta",round(improvement,5))
  approved=[z for z in experiments if z["strict_full_l3_pass"]]
  # No raw local correction is treated as a deliverable by itself.
  if approved:
   best=max(approved,key=lambda z:z["belly_worst_p95_improvement"])
   for f,k in targets.items():k.value=0.
   for f in FRAMES+(25,):
    bpy.context.scene.frame_set(f)
    for fr,k in targets.items():
     k.value=best["strength"]*pulse(f,fr,best["pulse_width"])
     k.keyframe_insert(data_path="value",frame=f)
   h["pose"](arm,action,1)
   saved_path=out/"R26_SAVED_NUMERIC_REVIEW_ONLY.blend"
   bpy.ops.wm.save_as_mainfile(filepath=str(saved_path),compress=True)
   report["conditionally_saved_review_model"]={"filename":saved_path.name,
      "sha256":hashlib.sha256(saved_path.read_bytes()).hexdigest(),
      "promotion":"REQUIRES_FRESH_REOPEN_L3_L4_AND_GLTF_L5"}
  report.update(status="PASS_COMPLETED_8_SIGNED_AREA_POSE_MORPHS_L3_SCREEN",
        expected_source_sha256=hashlib.sha256(orig_path.read_bytes()).hexdigest(),
        rejected_weight_comparison_sha256=hashlib.sha256(can_path.read_bytes()).hexdigest(),
        original_v8_rest_invariant=original["hash"],
        target_frames=list(TARGETS),target_solvers=solvers,trials=experiments,
        l3_numerical_eligible=[v["label"] for v in approved],
        note="Passing execution means signed surface gate assessed all unique frames; 0 eligible remains failure to solve original deform. Any saved model is experimental only.")
 except Exception as e:
  report.update(status="FAIL_EXECUTION",error=str(e),traceback=traceback.format_exc())
 (out/"round26_signed_normal_correctives.json").write_text(json.dumps(report,indent=2,ensure_ascii=False))
 print("ROUND26_STATUS",report["status"],"ELIGIBLE",report.get("l3_numerical_eligible"))
 if report["status"]!="PASS_COMPLETED_8_SIGNED_AREA_POSE_MORPHS_L3_SCREEN":
  print(report["traceback"]);raise SystemExit(1)
if __name__=="__main__":main()
