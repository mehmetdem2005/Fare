"""Round18: constrained anatomically informed skin-weight hypotheses on original
verified 49-bone v8. Target bilateral fore/hind limb root BLEED gradients within
the original anatomical mesh region, not arbitrary post-skin geometry inflation.
Always restore exact 7 groups before each test. No Automatic Weights or merges.
All 24 frames and strict L4 local surface (normals/BVH), correct 25 seam.
"""
import bpy,sys,math,json,statistics,hashlib,traceback,argparse,runpy
from pathlib import Path
from mathutils import Vector
ACT="run_sprint_v8_ik_phase_NUMERIC_REVIEW"
GROUPS=("upper_arm.L","thigh.L","upper_arm.R","thigh.R","spine_05","spine_04","hips")
LIMBS=("upper_arm.L","thigh.L","upper_arm.R","thigh.R")
BODY=6
def cli():
 p=argparse.ArgumentParser()
 p.add_argument("--source",required=True);p.add_argument("--out",required=True)
 return p.parse_args(sys.argv[sys.argv.index("--")+1:])
def mesh_points(ob):
 dg=bpy.context.evaluated_depsgraph_get()
 ev=ob.evaluated_get(dg)
 mesh=ev.to_mesh(preserve_all_data_layers=False,depsgraph=dg)
 try:
  M=ev.matrix_world.copy()
  return [Vector(M@v.co) for v in mesh.vertices]
 finally:ev.to_mesh_clear()
def pose(arm,act,f):
 arm.animation_data.action=None
 for b in arm.pose.bones:b.matrix_basis.identity()
 bpy.context.scene.frame_set(1)
 arm.animation_data.action=act
 bpy.context.scene.frame_set(2 if f==1 else f-1)
 bpy.context.scene.frame_set(f)
 bpy.context.view_layer.update()
def percentile(values,p):
 return sorted(values)[round((len(values)-1)*p)] if values else 0.
def smoothstep(a,b,x):
 v=max(0.,min(1.,(x-a)/(b-a)));return v*v*(3-2*v)
def surface(co,triangles,rest):
 areas=[]
 for i,j,k,d in triangles:
  a=(co[j]-co[i]).cross(co[k]-co[i]).length/d
  areas.append(a)
 return {"fraction_under_half":sum(x<.5 for x in areas)/len(areas),
         "p05":percentile(areas,.05),"minimum":min(areas)}
def main():
 args=cli();out=Path(args.out).resolve();out.mkdir(parents=True,exist_ok=True)
 result={"status":"STARTED","source_kind":"verified v8 original 49bones 19466v",
         "restriction":"no automatic weights; 7 named groups only; no source changes"}
 try:
  bpy.ops.wm.open_mainfile(filepath=str(Path(args.source).resolve()))
  ob=max((x for x in bpy.data.objects if x.type=="MESH" and any(md.type=="ARMATURE" and md.object for md in x.modifiers)),key=lambda x:len(x.data.vertices))
  md=next(x for x in ob.modifiers if x.type=="ARMATURE" and x.object)
  arm=md.object
  act=bpy.data.actions.get(ACT)
  if len(arm.data.bones)!=49 or len(ob.data.vertices)!=19466 or not act:raise RuntimeError("wrong repo baseline")
  if md.use_deform_preserve_volume:raise RuntimeError("LBS baseline unexpectedly changed")
  for name in GROUPS:
   if not ob.vertex_groups.get(name):raise RuntimeError("Missing "+name)
  arm.animation_data_create()
  for t in arm.animation_data.nla_tracks:t.mute=True
  arm.animation_data.action=None
  for b in arm.pose.bones:b.matrix_basis.identity()
  bpy.context.scene.frame_set(1);rest=mesh_points(ob)
  part=ob.data.attributes.get("part_id")
  if not part:raise RuntimeError("Missing anatomical part_id")
  verts=ob.data.vertices
  roi={
   "interleg":{i for i,v in enumerate(verts) if part.data[i].value==6 and -.1<=v.co.y<=.055 and abs(v.co.x)<=.165 and .045<=v.co.z<=.16},
   "front":{i for i,v in enumerate(verts) if part.data[i].value==6 and -.27<=v.co.y<=.055 and abs(v.co.x)<=.17 and .045<=v.co.z<=.285},
   "central":{i for i,v in enumerate(verts) if part.data[i].value==6 and -.27<=v.co.y<=.055 and abs(v.co.x)<=.06 and .045<=v.co.z<=.285},
   "rear":{i for i,v in enumerate(verts) if part.data[i].value==6 and .055<v.co.y<=.33 and abs(v.co.x)<=.17 and .06<=v.co.z<=.3},
   "foreleg":{i for i,v in enumerate(verts) if v.co.y<-.18 and v.co.z<.15 and abs(v.co.x)>.09},
   "head":{i for i,v in enumerate(verts) if v.co.y<-.30 and v.co.z>.22}}
  edges={name:[(i,j,d) for ed in ob.data.edges for i,j in [tuple(ed.vertices)]
          if i in I and j in I for d in [(rest[j]-rest[i]).length] if d>.001] for name,I in roi.items()}
  tris=[]
  for polygon in ob.data.polygons:
   ids=list(polygon.vertices)
   if len(ids)<3 or any(i not in roi["interleg"] for i in ids):continue
   for k in range(1,len(ids)-1):
    i,j,n=ids[0],ids[k],ids[k+1]
    d=(rest[j]-rest[i]).cross(rest[n]-rest[i]).length
    if d>2e-7:tris.append((i,j,n,d))
  if len(tris)!=1069:raise RuntimeError("unexpected fixed triangle count: "+str(len(tris)))
  triple=[(i,j,k) for i,j,k,d in tris]
  surface_fn=runpy.run_path("rig-experiments/round17_reopen_surface.py",run_name="round18_geom_helper")["normals_overlap"]
  def metrics(pos):
   return {n:{"p95":percentile([abs((pos[j]-pos[i]).length/d-1) for i,j,d in ee],.95),
              "p99":percentile([abs((pos[j]-pos[i]).length/d-1) for i,j,d in ee],.99)}
           for n,ee in edges.items()}
  def gather(full=False):
   rows=[];p15=None;p1=None
   for f in range(1,26):
    pose(arm,act,f);co=mesh_points(ob)
    if f==1:p1=co
    if f==15:p15=co
    if f<25:rows.append(metrics(co))
    else:seam=max((x-y).length for x,y in zip(p1,co))
   return {"regions":{n:{"worst_p95":max(x[n]["p95"] for x in rows),
                         "mean_p95":statistics.mean(x[n]["p95"] for x in rows),
                         "worst_p99":max(x[n]["p99"] for x in rows)} for n in edges},
           "f15_area":surface(p15,tris,rest),"seam":seam},p1,p15
  base,f1_base,f15_base=gather()
  result["baseline"]=base
  if base["seam"]>1e-5:raise RuntimeError("original v8 loop mismatch")
  # Topological neighbors, same part_id anatomical surface and chosen belly belt.
  candidate_ids={i for i in roi["interleg"] if -.115<=verts[i].co.y<=.068 and abs(verts[i].co.x)<=.16 and .045<=verts[i].co.z<=.17}
  original_all={}
  for i in candidate_ids:
   original_all[i]={ob.vertex_groups[g.group].name:float(g.weight) for g in verts[i].groups}
  # Only vertices already carrying both fore and hind upper-limb root weights.
  mixed={}
  for i in candidate_ids:
   w=original_all[i]
   ss=[]
   for side in ("L","R"):
    fore=w.get("upper_arm."+side,0.);hind=w.get("thigh."+side,0.)
    if fore>.012 and hind>.012 and fore+hind>.08:ss.append(side)
   if ss:mixed[i]=ss
  result["weight_audit"]={"eligible_body_vertices":len(candidate_ids),"mixed_fore_hind_vertices":len(mixed),
    "left":sum("L" in a for a in mixed.values()),"right":sum("R" in a for a in mixed.values()),
    "critical_weights":{str(i):original_all.get(i) for i in (154,270,731,774,2678,2713,9176,9294)}}
  if len(mixed)<60:raise RuntimeError("Not enough anatomically mixed vertices")
  # Editable weight set restricted to same 7 deform groups. Build symmetric neighbors.
  adjacency={i:set() for i in candidate_ids}
  for e in ob.data.edges:
   i,j=tuple(e.vertices)
   if i in adjacency and j in adjacency:
    if (rest[i]-rest[j]).length<.04:
     adjacency[i].add(j);adjacency[j].add(i)
  groups={name:ob.vertex_groups[name] for name in GROUPS}
  originals={i:{name:original_all[i].get(name,0.) for name in GROUPS} for i in candidate_ids}
  def apply(values):
   touched=0
   for i,w in values.items():
    for name in GROUPS:
     newval=w.get(name,0.)
     grp=groups[name]
     if newval>1e-8:grp.add([i],newval,"REPLACE")
     else:
      try:grp.remove([i])
      except RuntimeError:pass
    touched+=1
   bpy.context.view_layer.update()
   return touched
  def restore():
   apply(originals)
  def ratios_smooth(alpha,passes):
   # Replace only fore/hind split within original per-vertex limb mass; all other
   # weights preserved. Non-mixed boundary vertices are fixed rest anchors.
   v={i:{name:float(we) for name,we in orig.items()} for i,orig in originals.items()}
   for iteration in range(passes):
    new={i:dict(w) for i,w in v.items()}
    for i,sides in mixed.items():
     for side in sides:
      u="upper_arm."+side;th="thigh."+side;pair=v[i][u]+v[i][th]
      if pair<.05:continue
      m=v[i][u]/pair
      ratios=[];denoms=[]
      for j in adjacency[i]:
       wu=originals[j][u] if j not in mixed else v[j][u]
       wh=originals[j][th] if j not in mixed else v[j][th]
       mass=wu+wh
       if mass<.05:continue
       d=(rest[i]-rest[j]).length
       if d<.002 or d>.038:continue
       wt=max(.1,1-d/.05)
       ratios.append(wt*(wu/mass));denoms.append(wt)
      if not denoms:continue
      newratio=(1-alpha)*m+alpha*sum(ratios)/sum(denoms)
      newratio=max(.0,min(1.,newratio))
      new[i][u]=pair*newratio;new[i][th]=pair*(1-newratio)
    v=new
   return {i:v[i] for i in mixed}
  def trunk_offload(alpha,mode):
   v={}
   for i,sides in mixed.items():
    old=originals[i];ww=dict(old)
    Y=verts[i].co.y
    for side in sides:
     u="upper_arm."+side;h="thigh."+side
     mass=old[u]+old[h]
     mix=4*old[u]*old[h]/max(mass*mass,1e-12)
     # Use rest-shape medial taper and mixedness, avoid reducing near limb root.
     local=max(0.,1-abs(Y+.016)/.135)
     off=alpha*mix*local*mass
     if off<1e-7:continue
     ww[u]=old[u]*(mass-off)/mass
     ww[h]=old[h]*(mass-off)/mass
     if mode=="spine05":ww["spine_05"]+=off
     elif mode=="spine04":ww["spine_04"]+=off
     elif mode=="hips":ww["hips"]+=off
     else:
      back=smoothstep(-.055,.035,Y)
      ww["spine_05"]+=off*(1-back);ww["hips"]+=off*back
    v[i]=ww
   return v
  def longitudinal(alpha):
   v={}
   for i,sides in mixed.items():
    old=originals[i];ww=dict(old);Y=verts[i].co.y
    target=1.-smoothstep(-.11,.065,Y)
    for side in sides:
     u="upper_arm."+side;h="thigh."+side
     mass=old[u]+old[h]
     cur=old[u]/mass
     val=(1-alpha)*cur+alpha*target
     ww[u]=mass*val;ww[h]=mass*(1-val)
    v[i]=ww
   return v
  recipes=[]
  for strength in (.2,.4,.6,.8):
   for passes in (1,3,5):
    recipes.append(("smooth_gradient",strength,passes,lambda s=strength,p=passes:ratios_smooth(s,p)))
  for strength in (.10,.25,.40,.60):
   for mode in ("spine05","spine04","hips","blend"):
    recipes.append(("offload_"+mode,strength,1,lambda s=strength,m=mode:trunk_offload(s,m)))
  for strength in (.20,.4,.6,.8):
   recipes.append(("longitudinal_root",strength,1,lambda s=strength:longitudinal(s)))
  report=[]
  for i,(typ,strength,passes,build) in enumerate(recipes):
   restore()
   proposal=build()
   if not proposal:raise RuntimeError("Empty treatment recipe "+typ)
   for vid,values in proposal.items():
    tot_old=sum(originals[vid].values())
    tot_new=sum(values.values())
    if abs(tot_old-tot_new)>3e-5:raise RuntimeError("Weights sum changed in recipe "+typ+" "+str(vid))
   n=apply(proposal)
   stats,p1,p15=gather()
   geom15=surface_fn(triple,f15_base,p15)
   geom1=surface_fn(triple,f1_base,p1)
   delta={name:{"worst_p95":stats["regions"][name]["worst_p95"]-base["regions"][name]["worst_p95"],
                "mean_p95":stats["regions"][name]["mean_p95"]-base["regions"][name]["mean_p95"]}
          for name in roi}
   area_change=stats["f15_area"]["fraction_under_half"]-base["f15_area"]["fraction_under_half"]
   safe=(stats["seam"]<1e-5 and geom15["relative_normal_flips"]==0 and geom1["relative_normal_flips"]==0
     and geom15["candidate_nonadjacent_overlaps"]<=geom15["baseline_nonadjacent_overlaps"]
     and geom1["candidate_nonadjacent_overlaps"]<=geom1["baseline_nonadjacent_overlaps"]
     and area_change<=.005
     and delta["rear"]["worst_p95"]<=.006 and delta["foreleg"]["worst_p95"]<=.006
     and delta["front"]["worst_p95"]<=.01 and delta["central"]["worst_p95"]<=.01
     and delta["head"]["worst_p95"]<=.0001 and
       (delta["interleg"]["worst_p95"]<=-.035 or area_change<=-.025))
   report.append({"recipe":typ,"strength":strength,"passes":passes,"touched_vertices":n,
      "delta":delta,"metrics":stats,"area_collapse_change":area_change,
      "f15_surface":{"normal_flips":geom15["relative_normal_flips"],
          "overlaps":geom15["candidate_nonadjacent_overlaps"],
          "baseline_overlaps":geom15["baseline_nonadjacent_overlaps"]},
      "f1_surface":{"normal_flips":geom1["relative_normal_flips"],
          "overlaps":geom1["candidate_nonadjacent_overlaps"],
          "baseline_overlaps":geom1["baseline_nonadjacent_overlaps"]},
      "safe_numerical":safe})
  restore()
  check,p1,p15=gather()
  drift=max(abs(check["regions"][n][a]-base["regions"][n][a]) for n in roi for a in ("worst_p95","mean_p95"))
  result["return_to_baseline_drift"]=drift
  if drift>3e-5:raise RuntimeError("Trial weights failed to restore original before save")
  result["trials"]=report
  passing=[r for r in report if r["safe_numerical"]]
  if passing:
   best=min(passing,key=lambda x:x["metrics"]["regions"]["interleg"]["worst_p95"]+x["metrics"]["f15_area"]["fraction_under_half"])
   result["numeric_shortlist"]=best
   target=next(build for (typ,strength,passes,build) in recipes if typ==best["recipe"] and strength==best["strength"] and passes==best["passes"])
   applied=target();apply(applied)
   saved=out/"round18_weight_topology_NUMERIC_REVIEW_ONLY.blend"
   bpy.ops.wm.save_as_mainfile(filepath=str(saved),compress=True)
   result["candidate"]={"filename":saved.name,"sha256":hashlib.sha256(saved.read_bytes()).hexdigest(),"valid_for_production":False}
   result["status"]="PASS_NUMERIC_SHORTLIST_REQUIRES_VISUAL_AND_REOPEN"
  else:
   result["status"]="PASS_SCIENCE_32_TRIALS_NO_GEOMETRICALLY_SAFE_FIX"
  # Isolated dual-quaternion mode is diagnostic, never accepted as glTF-ready.
  restore();md.use_deform_preserve_volume=True
  bpy.context.view_layer.update()
  dq,p1,p15=gather()
  g=surface_fn(triple,f15_base,p15)
  result["dual_quaternion_diagnostic"]={"region_scores":dq,"area15":dq["f15_area"],
     "normal_flips":g["relative_normal_flips"],"nonadjacent_overlaps":g["candidate_nonadjacent_overlaps"],
     "note":"Blender-specific alternative deformation; not certified for GLB runtime"}
  md.use_deform_preserve_volume=False
  restore()
  result["trial_count"]=len(report)
 except Exception as e:
  result.update(status="FAIL",error=str(e),traceback=traceback.format_exc())
 (out/"round18_anatomical_weights.json").write_text(json.dumps(result,indent=2,ensure_ascii=False))
 print("ROUND18",result["status"],"TRIALS",result.get("trial_count"),
       "BASELINE_RESTORED",result.get("return_to_baseline_drift"))
 if result["status"]=="FAIL":
  print(result["error"]);raise SystemExit(1)
 else:
  x=sorted(result.get("trials",[]),key=lambda a:a["metrics"]["regions"]["interleg"]["worst_p95"])
  print("ROUND18_TOP",json.dumps([{"name":a["recipe"],"strength":a["strength"],"passes":a["passes"],
         "belly":a["metrics"]["regions"]["interleg"]["worst_p95"],
         "area_under_half":a["metrics"]["f15_area"]["fraction_under_half"],
         "normals":a["f15_surface"]["normal_flips"],"overlaps":a["f15_surface"]["overlaps"],
         "safe":a["safe_numerical"]} for a in x[:8]]))
if __name__=="__main__":main()
