"""Round 15 independent post-skin Corrective Smooth ablation on true v8.
This is a diagnostic only: Blender post-armature modifiers are NOT carried into
ordinary glTF skinning. Never call this experiment a deployable fix.
"""
import bpy,sys,argparse,math,json,statistics,traceback
from pathlib import Path
from mathutils import Vector
ACTION="run_sprint_v8_ik_phase_NUMERIC_REVIEW"
def cli():
 p=argparse.ArgumentParser();p.add_argument("--source",required=True);p.add_argument("--out",required=True)
 return p.parse_args(sys.argv[sys.argv.index("--")+1:])
def getpts(ob):
 dg=bpy.context.evaluated_depsgraph_get();ev=ob.evaluated_get(dg)
 m=ev.to_mesh(preserve_all_data_layers=False,depsgraph=dg)
 try:
  W=ev.matrix_world.copy();return [W@v.co for v in m.vertices]
 finally:ev.to_mesh_clear()
def q(v,p):
 if not v:return 0.
 return sorted(v)[round((len(v)-1)*p)]
def pose(arm,act,f):
 arm.animation_data.action=None
 for b in arm.pose.bones:b.matrix_basis.identity()
 bpy.context.scene.frame_set(1)
 arm.animation_data.action=act
 bpy.context.scene.frame_set(f-1 if f>1 else 2)
 bpy.context.scene.frame_set(f)
 bpy.context.view_layer.update()
def smoothstep(a,b,v):
 x=max(0.,min(1.,(v-a)/(b-a)))
 return x*x*(3-2*x)
def main():
 a=cli();out=Path(a.out).resolve();out.mkdir(exist_ok=True,parents=True)
 report={"status":"STARTED","workflow":"diagnostic post Armature smoothing; not glTF deployable"}
 try:
  bpy.ops.wm.open_mainfile(filepath=str(Path(a.source).resolve()))
  ob=max((o for o in bpy.data.objects if o.type=="MESH" and any(m.type=="ARMATURE" and m.object for m in o.modifiers)),key=lambda o:len(o.data.vertices))
  arm=next(m.object for m in ob.modifiers if m.type=="ARMATURE" and m.object)
  action=bpy.data.actions.get(ACTION)
  if not action or len(ob.data.vertices)!=19466 or len(arm.pose.bones)!=49:raise RuntimeError("wrong source")
  arm.animation_data_create()
  for tr in arm.animation_data.nla_tracks:tr.mute=True
  arm.animation_data.action=None
  for b in arm.pose.bones:b.matrix_basis.identity()
  bpy.context.scene.frame_set(1);rest=getpts(ob)
  part=ob.data.attributes.get("part_id")
  if not part:raise RuntimeError("need real body part_id")
  v=ob.data.vertices
  roi={
    "interleg":{i for i,x in enumerate(v) if part.data[i].value==6 and -.1<=x.co.y<=.055 and abs(x.co.x)<=.165 and .045<=x.co.z<=.16},
    "front":{i for i,x in enumerate(v) if part.data[i].value==6 and -.27<=x.co.y<=.055 and abs(x.co.x)<=.17 and .045<=x.co.z<=.285},
    "central":{i for i,x in enumerate(v) if part.data[i].value==6 and -.27<=x.co.y<=.055 and abs(x.co.x)<=.06 and .045<=x.co.z<=.285},
    "rear":{i for i,x in enumerate(v) if part.data[i].value==6 and .055<x.co.y<=.33 and abs(x.co.x)<=.17 and .06<=x.co.z<=.3},
    "foreleg":{i for i,x in enumerate(v) if x.co.y<-.18 and x.co.z<.15 and abs(x.co.x)>.09},
    "head":{i for i,x in enumerate(v) if x.co.y<-.30 and x.co.z>.22}}
  E={n:[(i,j,d) for ed in ob.data.edges for i,j in [tuple(ed.vertices)]
         if i in I and j in I for d in [(rest[j]-rest[i]).length] if d>.001] for n,I in roi.items()}
  def metric(co):
   return {n:{"p95":q([abs((co[j]-co[i]).length/d-1) for i,j,d in ee],.95),
              "p99":q([abs((co[j]-co[i]).length/d-1) for i,j,d in ee],.99),
              "compression_p95":q([max(0.,1-(co[j]-co[i]).length/d) for i,j,d in ee],.95)}
           for n,ee in E.items()}
  def allframes():
   rows=[];begin=None
   for f in range(1,26):
    pose(arm,action,f);p=getpts(ob)
    if f==1:begin=p
    if f==25:seam=max((p[i]-begin[i]).length for i in range(len(p)))
    else:rows.append(metric(p))
   return ({n:{"mean_p95":statistics.mean(r[n]["p95"] for r in rows),
               "worst_p95":max(r[n]["p95"] for r in rows),
               "worst_p99":max(r[n]["p99"] for r in rows),
               "worst_compression_p95":max(r[n]["compression_p95"] for r in rows)}
            for n in E},seam)
  base,baseseam=allframes()
  report["baseline"]=base;report["seam"]=baseseam
  if baseseam>1e-5:raise RuntimeError("baseline not looping")
  group=ob.vertex_groups.new(name="ROUND15_DIAGNOSTIC_BODY_MASK")
  ww={}
  for i,x in enumerate(v):
   if part.data[i].value!=6:continue
   y=x.co.y;z=x.co.z;xx=abs(x.co.x)
   wy=smoothstep(-.26,-.12,y)*(1-smoothstep(.06,.18,y))
   wz=smoothstep(.01,.06,z)*(1-smoothstep(.18,.28,z))
   wx=1-smoothstep(.13,.18,xx)
   w=wy*wz*wx
   if w>.005:
    group.add([i],w,"REPLACE")
    ww[i]=w
  if len(ww)<50:raise RuntimeError("mask too small")
  report["mask"]={"verts":len(ww),"min_weight":min(ww.values()),"mean_weight":statistics.mean(ww.values()),"max_weight":max(ww.values())}
  original_mods=[m.name for m in ob.modifiers]
  tests=[]
  for ty in ("LENGTH_WEIGHTED","SIMPLE"):
   for factor in (.12,.25,.4):
    for iterations in (2,5):
     mod=ob.modifiers.new(name="R15_TEMP_CORRECTIVE_SMOOTH",type="CORRECTIVE_SMOOTH")
     mod.vertex_group=group.name
     mod.factor=factor
     mod.iterations=iterations
     mod.smooth_type=ty
     mod.use_only_smooth=False
     if hasattr(mod,"use_pin_boundary"):mod.use_pin_boundary=True
     if hasattr(mod,"rest_source"):mod.rest_source="ORCO"
     bpy.context.view_layer.update()
     trial,seam=allframes()
     delta={n:{"mean_p95":trial[n]["mean_p95"]-base[n]["mean_p95"],
               "worst_p95":trial[n]["worst_p95"]-base[n]["worst_p95"],
               "worst_p99":trial[n]["worst_p99"]-base[n]["worst_p99"],
               "compression_p95":trial[n]["worst_compression_p95"]-base[n]["worst_compression_p95"]} for n in E}
     score={"type":ty,"factor":factor,"iterations":iterations,"scores":trial,"delta":delta,"seam":seam,
            "numeric_shortlist":seam<1e-5 and delta["interleg"]["worst_p95"]<-.04 and
               delta["rear"]["worst_p95"]<.008 and delta["foreleg"]["worst_p95"]<.008 and
               delta["front"]["worst_p95"]<.008 and delta["central"]["worst_p95"]<.008}
     tests.append(score)
     ob.modifiers.remove(mod)
     bpy.context.view_layer.update()
     pose(arm,action,1)
     checked=metric(getpts(ob))
     pose(arm,action,1)
     if max(abs(checked[n]["p95"]-metric(getpts(ob))[n]["p95"]) for n in E)>1e-6:
      raise RuntimeError("modifier reset leak")
  report["trials"]=tests
  shortlist=[t for t in tests if t["numeric_shortlist"]]
  best=min(shortlist,key=lambda x:x["scores"]["interleg"]["worst_p95"]) if shortlist else None
  report["best_numeric_diagnostic"]=best
  report["status"]="PASS_DIAGNOSTIC_ONLY_NON_EXPORTABLE"
 except Exception as ex:
  report.update(status="FAIL",error=str(ex),traceback=traceback.format_exc())
 (out/"round15_corrective_smooth.json").write_text(json.dumps(report,indent=2,ensure_ascii=False))
 print("ROUND15",report["status"])
 if report["status"]!="FAIL":
  print("ROUND15_BEST",json.dumps({k:v for k,v in (report.get("best_numeric_diagnostic") or {}).items() if k in ("type","factor","iterations","delta")}))
 else:
  print(report["error"]);raise SystemExit(1)
if __name__=="__main__":main()
