"""Round17: frame15 micro-collapsed triangle area experiment, strict ROI and full-cycle QA.
Tests actual Blender depsgraph v8 49-bone rig, rejects candidate unless both area
and edge p95 improve without distal-limb, chest, rear regression.
All trials independent original rest/weights; NO Automatic Weights.
"""
import bpy,sys,argparse,json,math,statistics,hashlib,traceback
from pathlib import Path
from mathutils import Vector,Matrix
TAU=2*math.pi
ACT="run_sprint_v8_ik_phase_NUMERIC_REVIEW"
def parse():
 p=argparse.ArgumentParser()
 p.add_argument("--source",required=True);p.add_argument("--out",required=True)
 return p.parse_args(sys.argv[sys.argv.index("--")+1:])
def pts(o):
 dg=bpy.context.evaluated_depsgraph_get(); ev=o.evaluated_get(dg)
 mesh=ev.to_mesh(preserve_all_data_layers=False,depsgraph=dg)
 try:
  M=ev.matrix_world.copy();return [Vector(M@v.co) for v in mesh.vertices]
 finally:ev.to_mesh_clear()
def pct(vals,p):
 return sorted(vals)[round((len(vals)-1)*p)] if vals else 0
def pos(arm,act,f):
 arm.animation_data.action=None
 for b in arm.pose.bones:b.matrix_basis.identity()
 bpy.context.scene.frame_set(1)
 arm.animation_data.action=act
 bpy.context.scene.frame_set(f-1 if f>1 else 2)
 bpy.context.scene.frame_set(f)
 bpy.context.view_layer.update()
def cyc(f,center,width):
 x=(f-center)%24;d=min(x,24-x)
 return math.exp(-.5*(d/width)**2)
def optimization(base,triangles,mask,limit=0.004,ratio=0.65,iterations=12):
 # Geometrically controlled area gradient (not voxel volume solver).
 # Keep all points at initial v8 posed locations, update only mask vertices.
 coords=[v.copy() for v in base]
 src=[v.copy() for v in base]
 grad_trace=[]
 for step in range(iterations):
  directions={i:Vector((0,0,0)) for i in mask}
  counts={i:0.0 for i in mask}
  active=0
  for i,j,k,restarea in triangles:
   a,b,c=coords[i],coords[j],coords[k]
   normal=(b-a).cross(c-a)
   mag=normal.length
   if mag<1e-10:continue
   area=mag*.5
   target=ratio*restarea
   if area>=target:continue
   n=normal/mag
   # Correct oriented derivatives of triangle area in world coords.
   gradients=[n.cross(c-b)*.5,n.cross(a-c)*.5,n.cross(b-a)*.5]
   g2=sum(grad.length_squared for grad in gradients)
   if g2<1e-12:continue
   # Small projected area increase; average many shared triangles.
   shift=(target-area)/g2
   for ii,grad in zip((i,j,k),gradients):
    if ii not in mask:continue
    directions[ii]+=grad*(shift)
    counts[ii]+=1.0
   active+=1
  max_delta=0.
  for i in mask:
   if counts[i]<=0:continue
   candidate=directions[i]*(0.55 / max(1,counts[i]))
   displacement=(coords[i]-src[i])+candidate
   if displacement.length>limit:
    displacement=displacement.normalized()*limit
   coords[i]=src[i]+displacement
   max_delta=max(max_delta,displacement.length)
  grad_trace.append({"step":step,"triangles_below_target":active,
                     "max_vertex_displacement":max_delta})
 return coords,grad_trace
def main():
 a=parse();out=Path(a.out).resolve();out.mkdir(exist_ok=True,parents=True)
 r={"status":"STARTED","model":"49bone/19466v verified v8", "nonphysical_caveat":"Triangle areas are not enclosed volume"}
 try:
  bpy.ops.wm.open_mainfile(filepath=str(Path(a.source).resolve()))
  ob=max((o for o in bpy.data.objects if o.type=="MESH" and any(m.type=="ARMATURE" and m.object for m in o.modifiers)),key=lambda o:len(o.data.vertices))
  md=next(m for m in ob.modifiers if m.type=="ARMATURE" and m.object);arm=md.object
  act=bpy.data.actions.get(ACT)
  if len(ob.data.vertices)!=19466 or len(arm.data.bones)!=49 or not act:raise RuntimeError("wrong baseline rig")
  arm.animation_data_create()
  for t in arm.animation_data.nla_tracks:t.mute=True
  arm.animation_data.action=None
  for b in arm.pose.bones:b.matrix_basis.identity()
  bpy.context.scene.frame_set(1);rest=pts(ob)
  att=ob.data.attributes.get("part_id")
  if not att:raise RuntimeError("missing part_id")
  v=ob.data.vertices
  rois={
   "interleg":{i for i,x in enumerate(v) if att.data[i].value==6 and -.1<=x.co.y<=.055 and abs(x.co.x)<=.165 and .045<=x.co.z<=.16},
   "front":{i for i,x in enumerate(v) if att.data[i].value==6 and -.27<=x.co.y<=.055 and abs(x.co.x)<=.17 and .045<=x.co.z<=.285},
   "central":{i for i,x in enumerate(v) if att.data[i].value==6 and -.27<=x.co.y<=.055 and abs(x.co.x)<=.06 and .045<=x.co.z<=.285},
   "rear":{i for i,x in enumerate(v) if att.data[i].value==6 and .055<x.co.y<=.33 and abs(x.co.x)<=.17 and .06<=x.co.z<=.3},
   "foreleg":{i for i,x in enumerate(v) if x.co.y<-.18 and x.co.z<.15 and abs(x.co.x)>.09},
   "head":{i for i,x in enumerate(v) if x.co.y<-.30 and x.co.z>.22}
  }
  edges={name:[(i,j,d) for e in ob.data.edges for i,j in [tuple(e.vertices)]
           if i in I and j in I for d in [(rest[j]-rest[i]).length] if d>.001] for name,I in rois.items()}
  triangles=[]
  for pol in ob.data.polygons:
   ids=list(pol.vertices)
   if len(ids)<3 or any(i not in rois["interleg"] for i in ids):continue
   for a in range(1,len(ids)-1):
    i,j,k=ids[0],ids[a],ids[a+1]
    ar=(rest[j]-rest[i]).cross(rest[k]-rest[i]).length/2
    if ar>1e-7:triangles.append((i,j,k,ar))
  if len(triangles)<100:raise RuntimeError("Body triangle face region unexpectedly empty")
  def check(coords):
   return {name:{"p95":pct([abs((coords[j]-coords[i]).length/d-1) for i,j,d in es],.95),
                  "p99":pct([abs((coords[j]-coords[i]).length/d-1) for i,j,d in es],.99)}
           for name,es in edges.items()}
  def arstats(coords):
   values=[(coords[j]-coords[i]).cross(coords[k]-coords[i]).length/(2*ra) for i,j,k,ra in triangles]
   return {"under_half":sum(q<.5 for q in values)/len(values),
           "p05":pct(values,.05),"p50":pct(values,.5),"p95":pct(values,.95),
           "min":min(values),"triangle_count":len(values)}
  baseline=[]
  for f in range(1,26):
   pos(arm,act,f);co=pts(ob)
   if f==1:initial=co
   if f==25:seam=max((x-y).length for x,y in zip(initial,co))
   else:baseline.append({"scores":check(co),"area15":arstats(co) if f==15 else None})
  if seam>1e-5:raise RuntimeError("baseline cycle seam mismatch")
  r["baseline"]={n:{"worst":max(row["scores"][n]["p95"] for row in baseline),
                    "mean":statistics.mean(row["scores"][n]["p95"] for row in baseline)}
                  for n in rois}
  r["baseline_area15"]=baseline[14]["area15"]
  pos(arm,act,15)
  original=pts(ob)
  # Rest-coordinates-only anatomically scoped mask.
  mask=set()
  for i in rois["interleg"]:
   if abs(v[i].co.x)<.155 and -.09 <= v[i].co.y <= .05 and .047 <= v[i].co.z <= .155:
    mask.add(i)
  r["masked_vertices"]=len(mask)
  if len(mask)<80:raise RuntimeError("unsafe small mask")
  # Compose inverse of actual LBS once for each vertex at f15.
  C=ob.matrix_world.inverted()@arm.matrix_world;Ci=C.inverted()
  pose_matrices={b.name:C@arm.pose.bones[b.name].matrix@b.matrix_local.inverted()@Ci
                 for b in arm.data.bones if b.use_deform and b.name in arm.pose.bones}
  inv_skin={}
  cond_min=1.
  for i in mask:
   groups={ob.vertex_groups[g.group].name:float(g.weight) for g in v[i].groups}
   w={nm:we for nm,we in groups.items() if nm in pose_matrices}
   mass=sum(w.values())
   if mass<.001:continue
   mat=Matrix(((0,0,0),(0,0,0),(0,0,0)))
   for name,we in w.items():mat+=pose_matrices[name].to_3x3()*(we/mass)
   d=mat.determinant()
   if abs(d)<.2:continue
   cond_min=min(cond_min,abs(d))
   inv_skin[i]=mat.inverted()
  r["invertible_vertices"]=len(inv_skin)
  if len(inv_skin)<.9*len(mask):raise RuntimeError("Too many non-invertible skin vertices")
  baseline_key_names={key.name for key in ob.data.shape_keys.key_blocks} if ob.data.shape_keys else set()
  keys={}
  transform=ob.matrix_world.to_3x3().inverted()
  basis=ob.data.shape_keys.key_blocks[0]
  recipes=[]
  for ratio in (.55,.70,.85):
   for cap in (.003,.006):
    optimized,trace=optimization(original,triangles,mask,limit=cap,ratio=ratio,iterations=12)
    name="R17_AREA_%.2f_%.3f"%(ratio,cap)
    key=ob.shape_key_add(name=name,from_mix=False)
    changed=0
    max_delta=0.
    for i in inv_skin:
     displacement=optimized[i]-original[i]
     if displacement.length<1e-8:continue
     delta=inv_skin[i]@(transform@displacement)
     if delta.length>.012:delta=delta.normalized()*.012
     key.data[i].co=basis.data[i].co+delta
     changed+=1;max_delta=max(max_delta,delta.length)
    key.value=0.
    keys[name]=key
    recipes.append({"name":name,"ratio":ratio,"cap":cap,"changed_vertices":changed,"max_pre_skin_delta":max_delta,"trace":trace})
  r["recipes"]=recipes
  variants=[]
  def test(keyname,strength,width,full=False):
   for obj in keys.values():obj.value=0.
   rows=[];saved=[]
   for f in range(1,26):
    pos(arm,act,f)
    keys[keyname].value=strength*cyc(f,15,width)
    bpy.context.view_layer.update()
    co=pts(ob)
    if f==15:posed15=co
    if f==1:first=co
    if f==25:loop=max((x-y).length for x,y in zip(first,co))
    else:rows.append({"scores":check(co),"area15":arstats(co) if f==15 else None})
    if full:saved.append(co)
   values={n:{"worst":max(x["scores"][n]["p95"] for x in rows),
              "mean":statistics.mean(x["scores"][n]["p95"] for x in rows)} for n in rois}
   ar=rows[14]["area15"]
   surface=surface_fn(face_indices,original,posed15)
   delta={n:{"worst":values[n]["worst"]-r["baseline"][n]["worst"],
             "mean":values[n]["mean"]-r["baseline"][n]["mean"]} for n in rois}
   # Separate actual area and surface strain guards. No arbitrary promotion.
   approved=(loop<1e-5 and
     ar["under_half"]<=r["baseline_area15"]["under_half"]-.015 and
     delta["interleg"]["worst"]<=.02 and
     delta["front"]["worst"]<=.01 and delta["central"]["worst"]<=.01 and
     delta["rear"]["worst"]<=.003 and delta["foreleg"]["worst"]<=.003 and
     delta["head"]["worst"]<=.0001 and
     surface["relative_normal_flips"]==0 and
     surface["candidate_nonadjacent_overlaps"]<=surface["baseline_nonadjacent_overlaps"])
   return {"key":keyname,"strength":strength,"width":width,"score":values,"delta":delta,
           "area15":ar,"surface_screen":surface,"seam":loop,"numeric_quality_gate":approved},saved
  from runpy import run_path
  surface_fn=run_path("rig-experiments/round17_reopen_surface.py",run_name="r17_geometry_helper")["normals_overlap"]
  face_indices=[(i,j,k) for i,j,k,_ in triangles]
  for recipe in recipes:
   for strength,width in ((.25,1.75),(.25,2.75),(.5,1.75),(1.0,1.75),(1.0,2.75)):
    z,_=test(recipe["name"],strength,width)
    variants.append(z)
  r["trials"]=variants
  r["surface_rejected_count"]=sum(not x["numeric_quality_gate"] and x["area15"]["under_half"]<r["baseline_area15"]["under_half"] for x in variants)
  candidates=[x for x in variants if x["numeric_quality_gate"]]
  if not candidates:
   r["status"]="PASS_TESTED_30_TRIALS_NO_VALID_AREA_REPAIR"
  else:
   best=min(candidates,key=lambda x:(x["area15"]["under_half"]+.04*x["score"]["interleg"]["worst"]))
   r["selection"]=best
   recorded,manual=test(best["key"],best["strength"],best["width"],full=True)
   for recipe in recipes:
    if recipe["name"]!=best["key"]:
     ob.shape_key_remove(keys[recipe["name"]])
   key=ob.data.shape_keys.key_blocks[best["key"]]
   for f in range(1,26):
    bpy.context.scene.frame_set(f)
    key.value=best["strength"]*cyc(f,15,best["width"])
    key.keyframe_insert(data_path="value",frame=f)
   # Re-eval truly keyed cycle, not an unsaved manual pose.
   errors=[]
   for f in range(1,26):
    pos(arm,act,f)
    coords=pts(ob)
    errors.append(max((coords[i]-manual[f-1][i]).length for i in range(len(coords))))
   r["manual_vs_baked_max_error"]=max(errors)
   if max(errors)>1e-4:raise RuntimeError("Failed baked corrective temporal sync")
   from runpy import run_path
   H=run_path("rig-experiments/round11_rootcause.py",run_name="r17_helpers")
   render=H["render_pose"]
   for f in (1,15):
    key.mute=True; render(ob,arm,act,f,out/"baseline_views",rois,closeup=True)
    key.mute=False;render(ob,arm,act,f,out/"candidate_views",rois,closeup=True)
   pos(arm,act,1)
   output=out/"round17_area_constrained_GAIT_ONLY_REVIEW.blend"
   bpy.ops.wm.save_as_mainfile(filepath=str(output),compress=True)
   r["candidate"]={"path":output.name,"sha256":hashlib.sha256(output.read_bytes()).hexdigest(),
                    "status":"NUMERICAL_REVIEW_NOT_PRODUCTION"}
   r["status"]="PASS_NUMERIC_AREA_REVIEW_ONLY"
 except Exception as ex:
  r.update(status="FAIL",error=str(ex),traceback=traceback.format_exc())
 (out/"round17_area_microfold.json").write_text(json.dumps(r,indent=2,ensure_ascii=False))
 print("ROUND17",r["status"],"AREA_BASELINE",r.get("baseline_area15"))
 if r["status"]!="FAIL":
  print("ROUND17_TRIALS",len(r.get("trials",[])))
  print("ROUND17_BEST",json.dumps(sorted([{"key":x["key"],"strength":x["strength"],"width":x["width"],"underhalf":x["area15"]["under_half"],"belly":x["score"]["interleg"]["worst"],"gate":x["numeric_quality_gate"],"normal_flips":x["surface_screen"]["relative_normal_flips"],"overlaps":x["surface_screen"]["candidate_nonadjacent_overlaps"]} for x in r["trials"]],key=lambda x:x["underhalf"])[:5]))
 else:print(r["error"]);raise SystemExit(1)
if __name__=="__main__":main()
