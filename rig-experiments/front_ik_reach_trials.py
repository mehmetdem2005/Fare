"""Per-side IK target reach experiments (24 frames), no original file edits.
All targets in armature object coordinates; convert to pose-bone local via
parent matrix rest orientation, and verify actual target displacement.
Candidate is saved only if 6-ROI metrics improve without limb regressions.
"""
import bpy,math,json,sys,argparse,traceback
from pathlib import Path
from mathutils import Vector
def options():
 p=argparse.ArgumentParser();p.add_argument("--source",required=True);p.add_argument("--out",required=True)
 return p.parse_args(sys.argv[sys.argv.index('--')+1:])
def pctl(values,k):
 values.sort();return values[int(k*(len(values)-1))] if values else 0
def vertices(mesh):
 dg=bpy.context.evaluated_depsgraph_get();o=mesh.evaluated_get(dg);m=o.to_mesh(preserve_all_data_layers=False,depsgraph=dg)
 try:
  world=o.matrix_world.copy();return [tuple(world@v.co) for v in m.vertices]
 finally:o.to_mesh_clear()
def main():
 cfg=options();out=Path(cfg.out).resolve();out.mkdir(parents=True,exist_ok=True)
 rep={"status":"STARTED","source":str(cfg.source)}
 try:
  bpy.ops.wm.open_mainfile(filepath=str(Path(cfg.source).resolve()))
  mesh=max([o for o in bpy.data.objects if o.type=="MESH" and any(m.type=="ARMATURE" for m in o.modifiers)],key=lambda o:len(o.data.vertices))
  arm=next(m.object for m in mesh.modifiers if m.type=="ARMATURE" and m.object);B=arm.pose.bones;sc=bpy.context.scene
  act=bpy.data.actions.get("run_sprint_v4")
  if not act:raise RuntimeError("action missing")
  arm.animation_data_create();arm.animation_data.action=None
  for track in arm.animation_data.nla_tracks:track.mute=True
  for p in B:p.matrix_basis.identity()
  sc.frame_set(1)
  rest=vertices(mesh)
  part=mesh.data.attributes.get('part_id');vs=mesh.data.vertices;N=len(vs)
  rois={
   "interleg":{i for i,v in enumerate(vs) if part.data[i].value==6 and -.1<=v.co.y<=.055 and .045<=v.co.z<=.16 and abs(v.co.x)<=.165},
   "front":{i for i,v in enumerate(vs) if part.data[i].value==6 and -.27<=v.co.y<=.055 and .045<=v.co.z<=.285 and abs(v.co.x)<=.17},
   "central":{i for i,v in enumerate(vs) if part.data[i].value==6 and -.27<=v.co.y<=.055 and .045<=v.co.z<=.285 and abs(v.co.x)<=.06},
   "rear":{i for i,v in enumerate(vs) if part.data[i].value==6 and .055<v.co.y<=.33 and .06<=v.co.z<=.3 and abs(v.co.x)<=.17},
   "foreleg":{i for i,v in enumerate(vs) if v.co.y<-.18 and v.co.z<.15 and abs(v.co.x)>.09},
  }
  edges={name:[(u,v,math.dist(rest[u],rest[v])) for e in mesh.data.edges for u,v in [tuple(e.vertices)] if u in mask and v in mask and math.dist(rest[u],rest[v])>=.001]
         for name,mask in rois.items()}
  def metric(arr):
   return {n:pctl([abs(math.dist(arr[u],arr[v])/d-1) for u,v,d in e],.95) for n,e in edges.items()}
  def reeval(frame):
   arm.animation_data.action=act
   sc.frame_set(frame-1 if frame>1 else 2)
   sc.frame_set(frame);bpy.context.view_layer.update()
  def compute(limit):
   readings=[];corrected_count=0;delta_total=0;max_error=0;max_hand_move=0
   for f in range(1,25):
    reeval(f)
    if limit is not None:
     for side in "LR":
      root=B["upper_arm."+side]
      target=B["ik_hand."+side]
      root_head=root.head.copy();pos=target.head.copy()
      limit_distance=(arm.data.bones["upper_arm."+side].length+arm.data.bones["forearm."+side].length)*limit
      dif=pos-root_head
      if dif.length>limit_distance:
       delta=(root_head+dif.normalized()*limit_distance)-pos
       # convert armature-space offset to control-pose location via control rest
       conversion=arm.data.bones[target.name].matrix_local.to_3x3().inverted()
       target.location=target.location+conversion@delta
       bpy.context.view_layer.update()
       actual=target.head-pos
       max_error=max(max_error,(actual-delta).length)
       max_hand_move=max(max_hand_move,actual.length)
       corrected_count+=1;delta_total+=actual.length
    readings.append({"frame":f,"p95":metric(vertices(mesh))})
   ret={n:{"mean":sum(x["p95"][n] for x in readings)/24,
           "worst":max(x["p95"][n] for x in readings)} for n in edges}
   return ret,{"num_corrected_targets":corrected_count,"total_hand_target_displacement":delta_total,
                "max_target_move":max_hand_move,"max_conversion_error":max_error},readings
  base,_,_=compute(None)
  rep["baseline"]=base
  rep["trials"]=[]
  for limit in (.995,.985,.975,.96,.94):
   m,detail,rows=compute(limit)
   ratio={n:{"mean":m[n]["mean"]/base[n]["mean"],"worst":m[n]["worst"]/base[n]["worst"]} for n in edges}
   # do not admit a target clamp that moves the stance foot too much
   ok=(ratio["interleg"]["worst"]<=.99 and ratio["interleg"]["mean"]<=1.02
       and ratio["front"]["worst"]<=1.01 and ratio["central"]["worst"]<=1.03
       and ratio["rear"]["worst"]<=1.01 and ratio["foreleg"]["worst"]<=1.035
       and detail["max_conversion_error"]<.001)
   rep["trials"].append({"limit":limit,"metric":m,"ratios":ratio,"details":detail,"passes_guard":ok})
  valid=[t for t in rep['trials'] if t['passes_guard']]
  rep["selected"]=min(valid,key=lambda x:x['ratios']['interleg']['worst']) if valid else None
  # Never bake an unverified result.
  rep["status"]="MEASURED_VALID_IK_CLAMP_PENDING_EXPORT" if valid else "NO_ACCEPTABLE_IK_CLAMP"
 except Exception as exc:
  rep["status"]="FAIL";rep["error"]=str(exc);rep["traceback"]=traceback.format_exc()
 (out/"per_limb_target_clamp.json").write_text(json.dumps(rep,indent=2))
 print("IK_CLAMP",rep["status"],rep.get("selected"))
 if rep["status"]=="FAIL":raise SystemExit(1)
if __name__=="__main__":main()
