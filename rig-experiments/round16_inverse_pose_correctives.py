"""Round16 research: convert a real post-armature, pose-specific torso correction
back into pre-armature shape-key delta using independently verified LBS inverse.
Experimental gait-specific keys; not a general pose-space driver nor production.
No Automatic Weights, no edits to original source, main, or deliver/.
"""
import bpy,sys,argparse,math,json,statistics,hashlib,traceback,runpy
from pathlib import Path
from mathutils import Vector,Matrix
H=runpy.run_path("rig-experiments/round11_rootcause.py",run_name="r16helper")
getpts=H["points"];pose=H["pose"];roi_fn=H["collect"];render=H["render_pose"]
W=runpy.run_path("rig-experiments/round15_corrective_smooth_trial.py",run_name="r16mask")
smoothstep=W["smoothstep"]
A="run_sprint_v8_ik_phase_NUMERIC_REVIEW"
KEY_EXT="R16_BELLY_EXTENSION_GAIT_ONLY"
KEY_CMP="R16_BELLY_COMPRESSION_GAIT_ONLY"
def parse():
 p=argparse.ArgumentParser()
 p.add_argument("--source",required=True);p.add_argument("--smoothing-report",required=True);p.add_argument("--out",required=True)
 return p.parse_args(sys.argv[sys.argv.index("--")+1:])
def pct(arr,p):
 return sorted(arr)[round((len(arr)-1)*p)] if arr else 0
def cyc(f,center,width):
 x=abs(((f-center)%24));d=min(x,24-x)
 return math.exp(-.5*(d/width)**2)
def main():
 a=parse();out=Path(a.out).resolve();out.mkdir(exist_ok=True,parents=True)
 report={"status":"STARTED","engine":"real Blender 5.1.2 evaluated geometry and inverse skinning",
         "caveat":"Gait-time keyed research, not reusable pose-space driver"}
 try:
  z=json.loads(Path(a.smoothing_report).read_text())
  if z.get("status")!="PASS_DIAGNOSTIC_ONLY_NON_EXPORTABLE":
   raise RuntimeError("Need completed independent Corrective Smooth experiments")
  trials=z["trials"]
  eligible=[x for x in trials if x["delta"]["rear"]["worst_p95"]<=.008 and x["delta"]["foreleg"]["worst_p95"]<=.008 and x["delta"]["front"]["worst_p95"]<=.008 and x["delta"]["central"]["worst_p95"]<=.008]
  if not eligible:
   report["status"]="SKIPPED_NO_SAFE_POSTSKIN_TARGET"
   return
  best=min(eligible,key=lambda x:x["scores"]["interleg"]["worst_p95"])
  report["postskin_source_trial"]={"type":best["type"],"factor":best["factor"],"iterations":best["iterations"],
                                   "score":best["scores"]["interleg"]["worst_p95"]}
  bpy.ops.wm.open_mainfile(filepath=str(Path(a.source).resolve()))
  ob=max((o for o in bpy.data.objects if o.type=="MESH" and any(m.type=="ARMATURE" and m.object for m in o.modifiers)),key=lambda o:len(o.data.vertices))
  mod=next(m for m in ob.modifiers if m.type=="ARMATURE" and m.object)
  arm=mod.object;act=bpy.data.actions.get(A)
  if not act or len(arm.pose.bones)!=49 or len(ob.data.vertices)!=19466:raise RuntimeError("wrong rig")
  arm.animation_data_create()
  for tr in arm.animation_data.nla_tracks:tr.mute=True
  arm.animation_data.action=None
  for pb in arm.pose.bones:pb.matrix_basis.identity()
  bpy.context.scene.frame_set(1);rest=getpts(ob)
  masks=roi_fn(ob,arm)
  ee={n:[(i,j,d) for edge in ob.data.edges for i,j in [tuple(edge.vertices)]
          if i in I and j in I for d in [(rest[j]-rest[i]).length] if d>.001] for n,I in masks.items()}
  faces=[]
  for pol in ob.data.polygons:
   ix=list(pol.vertices)
   if all(v in masks["interleg"] for v in ix) and len(ix)>=3:
    faces.extend((ix[0],ix[j],ix[j+1]) for j in range(1,len(ix)-1))
  def measure(co):
   return {n:{"p95":pct([abs((co[j]-co[i]).length/d-1) for i,j,d in edges],.95),
              "p99":pct([abs((co[j]-co[i]).length/d-1) for i,j,d in edges],.99)} for n,edges in ee.items()}
  def area(co):
   ratios=[]
   for i,j,k in faces:
    r=(rest[j]-rest[i]).cross(rest[k]-rest[i]).length
    q=(co[j]-co[i]).cross(co[k]-co[i]).length
    if r>1e-7:ratios.append(q/r)
   return {"under_half":sum(x<.5 for x in ratios)/len(ratios),"p05":pct(ratios,.05),"p95":pct(ratios,.95)}
  orig=[]
  for f in range(1,26):
   pose(arm,act,f);p=getpts(ob)
   if f==1:first=p
   if f==25:orig_seam=max((p[i]-first[i]).length for i in range(len(p)))
   else:orig.append({"metric":measure(p),"area":area(p) if f==15 else None})
  if orig_seam>1e-5:raise RuntimeError("source action seam")
  def aggregate(rows):
   return {name:{"worst_p95":max(x["metric"][name]["p95"] for x in rows),
                 "mean_p95":statistics.mean(x["metric"][name]["p95"] for x in rows),
                 "worst_p99":max(x["metric"][name]["p99"] for x in rows)} for name in ee}
  baseline=aggregate(orig);report["baseline"]=baseline;report["area15_baseline"]=orig[14]["area"]
  part=ob.data.attributes.get("part_id")
  group=ob.vertex_groups.new(name="R16_DIAGNOSTIC_BELLY_MASK")
  region={}
  for i,v in enumerate(ob.data.vertices):
   if part.data[i].value!=6:continue
   y=v.co.y;zz=v.co.z;x=abs(v.co.x)
   w=smoothstep(-.26,-.12,y)*(1-smoothstep(.06,.18,y))*smoothstep(.01,.06,zz)*(1-smoothstep(.18,.28,zz))*(1-smoothstep(.13,.18,x))
   if w>.005:group.add([i],w,"REPLACE");region[i]=w
  if len(region)<50:raise RuntimeError("Belly mask empty")
  report["mask_vertices"]=len(region)
  transforms={}
  W3inv=ob.matrix_world.to_3x3().inverted()
  # Preserve new blendshapes as zero before all target extractions.
  planned={}
  for frame,label in ((1,"ext"),(15,"cmp")):
   pose(arm,act,frame)
   baseline_coords=getpts(ob)
   sm=ob.modifiers.new("R16_TEMP_POST_ARMATURE_TARGET","CORRECTIVE_SMOOTH")
   sm.vertex_group=group.name;sm.factor=best["factor"];sm.iterations=best["iterations"]
   sm.smooth_type=best["type"];sm.use_only_smooth=False
   if hasattr(sm,"use_pin_boundary"):sm.use_pin_boundary=True
   if hasattr(sm,"rest_source"):sm.rest_source="ORCO"
   bpy.context.view_layer.update()
   target=getpts(ob)
   ob.modifiers.remove(sm)
   bpy.context.view_layer.update()
   pose(arm,act,frame)
   if max((getpts(ob)[i]-baseline_coords[i]).length for i in (154,270,731,774))>1e-5:
    raise RuntimeError("Postskin modifier test state not restored")
   C=ob.matrix_world.inverted()@arm.matrix_world
   Ci=C.inverted()
   matrix={b.name:C@arm.pose.bones[b.name].matrix@b.matrix_local.inverted()@Ci
           for b in arm.data.bones if b.use_deform and b.name in arm.pose.bones}
   delta={}
   errors=[]
   clips=0
   for i in region:
    weights={ob.vertex_groups[g.group].name:float(g.weight) for g in ob.data.vertices[i].groups}
    deform={k:v for k,v in weights.items() if k in matrix}
    mass=sum(deform.values())
    if mass<.0001:continue
    blend=Matrix(((0,0,0),(0,0,0),(0,0,0)))
    for bone,w in deform.items():blend+=matrix[bone].to_3x3()*(w/mass)
    if abs(blend.determinant())<.15:continue
    diff=target[i]-baseline_coords[i]
    local=W3inv@diff
    source=blend.inverted()@local
    max_local=.012
    if source.length>max_local:
     source=source.normalized()*max_local;clips+=1
    if source.length>1e-7:
     delta[i]=source
     errors.append((ob.matrix_world.to_3x3()@(blend@source)-diff).length)
   planned[label]=delta
   report[label+"_target"]={"modified_vertices":len(delta),"max_inversion_residual":max(errors) if errors else 0.,
     "clipped_vertices":clips,"postskin_target_displacement_max":max((target[i]-baseline_coords[i]).length for i in region)}
  if any(len(v)<20 for v in planned.values()):raise RuntimeError("No useful inverse morph target")
  # New shape keys live only on isolated experimental rig, Basis not touched.
  shape={}
  basis=ob.data.shape_keys.key_blocks[0]
  for label,name in (("ext",KEY_EXT),("cmp",KEY_CMP)):
   key=ob.shape_key_add(name=name,from_mix=False)
   for i,delta in planned[label].items():
    key.data[i].co=basis.data[i].co+delta
   key.value=0
   shape[label]=key
  trials=[]
  manual={}
  def evaluate_variant(strength,width,remember=False):
   rows=[];coords=[]
   for f in range(1,26):
    pose(arm,act,f)
    shape["ext"].value=strength*cyc(f,1,width)
    shape["cmp"].value=strength*cyc(f,15,width)
    bpy.context.view_layer.update()
    pos=getpts(ob)
    coords.append(pos)
    if f<25:rows.append({"metric":measure(pos),"area":area(pos) if f==15 else None})
   seam=max((coords[0][i]-coords[-1][i]).length for i in range(len(coords[0])))
   return aggregate(rows),rows[14]["area"],seam,coords if remember else None
  for strength in (.4,.7,1.0):
   for width in (1.75,2.75,4.0):
    scores,ar,seam,_=evaluate_variant(strength,width)
    delta={name:{k:scores[name][k]-baseline[name][k] for k in ("mean_p95","worst_p95","worst_p99")} for name in ee}
    candidate={"strength":strength,"width":width,"scores":scores,"area15":ar,"seam":seam,"delta":delta,
        "safe_numerical":seam<1e-5 and
          (delta["interleg"]["worst_p95"]<-.025 or (ar["under_half"]<report["area15_baseline"]["under_half"]-.025 and delta["interleg"]["mean_p95"]<-.012)) and
          delta["rear"]["worst_p95"]<=.008 and delta["foreleg"]["worst_p95"]<=.008 and
          delta["central"]["worst_p95"]<=.008 and delta["front"]["worst_p95"]<=.008}
    trials.append(candidate)
  report["trials"]=trials
  safe=[x for x in trials if x["safe_numerical"]]
  if not safe:
   report["status"]="PASS_L3_NO_SAFE_MORPH_CANDIDATE"
  else:
   bestm=min(safe,key=lambda x:x["scores"]["interleg"]["worst_p95"]+1.5*x["area15"]["under_half"])
   report["selection"]=bestm
   scores,ar,seam,manualcoords=evaluate_variant(bestm["strength"],bestm["width"],remember=True)
   for f in range(1,26):
    bpy.context.scene.frame_set(f)
    for tag in ("ext","cmp"):
     key=shape[tag]
     key.value=bestm["strength"]*cyc(f,1 if tag=="ext" else 15,bestm["width"])
     key.keyframe_insert(data_path="value",frame=f)
   # Save/reopen in independent fresh Blender step will verify the numeric state.
   copied=[]
   for f in range(1,26):
    pose(arm,act,f)
    now=getpts(ob)
    copied.append(max((now[i]-manualcoords[f-1][i]).length for i in range(len(now))))
   report["manual_vs_baked_max_error"]=max(copied)
   if max(copied)>1e-4:raise RuntimeError("Baked shape action differs from manual curves")
   # Side/bottom/quarter real Blender image evidence at extension and compression.
   report["rendered_views"]={}
   for f in (1,15):
    for tag in shape:shape[tag].mute=True
    report["rendered_views"]["baseline_"+str(f)]=render(ob,arm,act,f,out/"baseline_views",masks)
    for tag in shape:shape[tag].mute=False
    report["rendered_views"]["candidate_"+str(f)]=render(ob,arm,act,f,out/"candidate_views",masks)
   pose(arm,act,1)
   saved=out/"round16_pre_skin_corrective_GAIT_ONLY_REVIEW.blend"
   bpy.ops.wm.save_as_mainfile(filepath=str(saved),compress=True)
   report["candidate"]={"name":saved.name,"sha256":hashlib.sha256(saved.read_bytes()).hexdigest(),
                        "output_kind":"GAIT_ONLY_NUMERIC_AND_RENDER_REVIEW_NOT_ANATOMICAL_PASS"}
   report["status"]="PASS_L3_MORPH_NUMERIC_REVIEW_ONLY"
 except Exception as ex:
  report.update(status="FAIL",error=str(ex),traceback=traceback.format_exc())
 (out/"round16_inverse_pose_correctives.json").write_text(json.dumps(report,indent=2,ensure_ascii=False))
 print("ROUND16",report["status"])
 if report["status"]!="FAIL":
  print("ROUND16_SELECTION",json.dumps({k:report.get(k) for k in ("postskin_source_trial","area15_baseline","selection","manual_vs_baked_max_error","candidate")}))
  print("ROUND16_TRIALS",json.dumps([{"strength":x["strength"],"width":x["width"],"interleg":x["scores"]["interleg"]["worst_p95"],"area":x["area15"]["under_half"],"shortlist":x["safe_numerical"]} for x in report.get("trials",[])]))
 else:print(report["error"]);raise SystemExit(1)
if __name__=="__main__":main()
