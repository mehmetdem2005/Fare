"""Verify baked spine v6 vs original and make individual-bone safe fore-IK reach v7.
Require exact agreement with optimizer measurements BEFORE accepting any action.
No automatic weights or mesh edits. Export to separate .blend only after 24-frame guards.
"""
import bpy,math,json,sys,traceback,argparse
from pathlib import Path
from mathutils import Vector
def cli():
 p=argparse.ArgumentParser()
 p.add_argument('--source',required=True)
 p.add_argument('--optimizer',required=True)
 p.add_argument('--out',required=True)
 return p.parse_args(sys.argv[sys.argv.index('--')+1:])
def pp(a,fract):
 a.sort();return a[int(fract*(len(a)-1))] if a else 0
def getpts(mesh):
 deps=bpy.context.evaluated_depsgraph_get();ev=mesh.evaluated_get(deps)
 m=ev.to_mesh(preserve_all_data_layers=False,depsgraph=deps)
 try:
  world=ev.matrix_world.copy();return [tuple(world@v.co) for v in m.vertices]
 finally:ev.to_mesh_clear()
def main():
 c=cli();out=Path(c.out).resolve();out.mkdir(exist_ok=True,parents=True)
 report={"status":"STARTED","source":c.source}
 try:
  optimization=json.loads(Path(c.optimizer).read_text())
  expected=optimization["selected"]
  if expected is None:raise RuntimeError('Optimization found no acceptable profile')
  bpy.ops.wm.open_mainfile(filepath=str(Path(c.source).resolve()))
  mesh=max([o for o in bpy.data.objects if o.type=="MESH" and any(m.type=="ARMATURE" and m.object for m in o.modifiers)],key=lambda o:len(o.data.vertices))
  arm=next(m.object for m in mesh.modifiers if m.type=="ARMATURE" and m.object);B=arm.pose.bones;scene=bpy.context.scene
  arm.animation_data_create()
  for t in arm.animation_data.nla_tracks:t.mute=True
  base=bpy.data.actions["run_sprint_v4"];optimized=bpy.data.actions["run_sprint_v6_spine_phase_repaired"]
  arm.animation_data.action=None
  for p in B:p.matrix_basis.identity()
  scene.frame_set(1);ref=getpts(mesh)
  part=mesh.data.attributes.get("part_id")
  v=mesh.data.vertices
  rois={
   "interleg":{i for i,x in enumerate(v) if part.data[i].value==6 and -.1<=x.co.y<=.055 and .045<=x.co.z<=.16 and abs(x.co.x)<=.165},
   "front":{i for i,x in enumerate(v) if part.data[i].value==6 and -.27<=x.co.y<=.055 and .045<=x.co.z<=.285 and abs(x.co.x)<=.17},
   "central":{i for i,x in enumerate(v) if part.data[i].value==6 and -.27<=x.co.y<=.055 and .045<=x.co.z<=.285 and abs(x.co.x)<=.06},
   "rear":{i for i,x in enumerate(v) if part.data[i].value==6 and .055<x.co.y<=.33 and .06<=x.co.z<=.3 and abs(x.co.x)<=.17},
   "foreleg":{i for i,x in enumerate(v) if x.co.y<-.18 and x.co.z<.15 and abs(x.co.x)>.09},
   "head":{i for i,x in enumerate(v) if x.co.y<-.30 and x.co.z>.22},
  }
  pairs={n:[(i,j,math.dist(ref[i],ref[j])) for e in mesh.data.edges for i,j in [tuple(e.vertices)] if i in mask and j in mask and math.dist(ref[i],ref[j])>=.001] for n,mask in rois.items()}
  def meter(coords):
   return {n:pp([abs(math.dist(coords[i],coords[j])/d-1) for i,j,d in ed],.95) for n,ed in pairs.items()}
  def loadpose(action,frame):
   arm.animation_data.action=action
   scene.frame_set(frame-1 if frame>1 else 2);scene.frame_set(frame)
   bpy.context.view_layer.update()
  def score(rows):
   return {n:{"mean":sum(x["metrics"][n] for x in rows)/24,"worst":max(x["metrics"][n] for x in rows[:24])} for n in rois}
  def clamp(limit):
   changes=[];maxdelta=0.;conversion_error=0.
   for side in 'LR':
    root=B['upper_arm.'+side];target=B['ik_hand.'+side]
    end=B['forearm.'+side]
    reach=(arm.data.bones[root.name].length+arm.data.bones[end.name].length)*limit
    vec=target.head-root.head
    if vec.length<=reach:continue
    want=root.head+vec.normalized()*reach
    delta=want-target.head
    before=target.head.copy()
    restinv=arm.data.bones[target.name].matrix_local.to_3x3().inverted()
    target.location=target.location+restinv@delta
    bpy.context.view_layer.update()
    actual=target.head-before
    conversion_error=max(conversion_error,(actual-delta).length)
    maxdelta=max(maxdelta,actual.length)
    changes.append({"side":side,"shift":actual.length})
   return changes,maxdelta,conversion_error
  def evaluated_action(action,limit=None):
   rows=[];delta_max=0.;err_max=0.;targets=0
   for frame in range(1,26):
    loadpose(action,frame)
    movements,dm,err=clamp(limit) if limit else ([],0.,0.)
    delta_max=max(delta_max,dm);err_max=max(err_max,err);targets+=len(movements)
    coords=getpts(mesh)
    if frame==1:initial=coords
    if frame==25:seam=max(math.dist(x,y) for x,y in zip(initial,coords))
    rows.append({"frame":frame,"metrics":meter(coords),"shifted":movements})
   return rows,{"max_target_shift":delta_max,"max_conversion_error":err_max,"changed_targets":targets,"loop_seam":seam}
  org,orgd=evaluated_action(base)
  v6,v6d=evaluated_action(optimized)
  score6=score(v6)
  for r in rois:
   for field in ("mean","worst"):
    target=expected["metrics"][r][field]
    actual=score6[r][field]
    if abs(target-actual)>3e-4:
     raise RuntimeError("saved v6 differs from trial "+r+" "+field+" expected "+str(target)+" got "+str(actual))
  assert v6d["loop_seam"]<1e-5
  report['saved_v6_crosscheck']="PASS: every ROI mean/worst agrees within 0.0003"
  report["v4"]=score(org);report["v6"]=score6;report["v6_loop_seam"]=v6d["loop_seam"]
  variants=[]
  for limit in (.96,.94):
   rows,extra=evaluated_action(optimized,limit)
   scores=score(rows)
   ratios={name:{key:scores[name][key]/score6[name][key] if score6[name][key]>1e-9 else 1. for key in ('mean','worst')}
           for name in rois}
   guards=(extra["loop_seam"]<1e-5 and extra["max_target_shift"]<.015
           and extra["max_conversion_error"]<1e-5
           and ratios["rear"]["worst"]<=1.02 and ratios["foreleg"]["worst"]<=1.035
           and ratios["central"]["worst"]<=1.04 and ratios["head"]["worst"]<=1.05
           and ratios["front"]["worst"]<=1.03 and ratios["interleg"]["worst"]<1.)
   variants.append({"limit":limit,"score":scores,"ratios_vs_v6":ratios,
                    "details":extra,"guards":guards,
                    "frame3":rows[2],"frame15":rows[14]})
  report["clamped_candidates"]=variants
  accepted=[x for x in variants if x["guards"] and x["limit"]>=.96]
  if not accepted:
   report["status"]="V6_BAKED_VERIFIED_CLAMP_NOT_ACCEPTED"
  else:
   best=accepted[0];limit=best["limit"];report["selected"]=best
   # Build a NEW Blender 5.1 action from sampled positions, not a copy:
   # cloned action slots previously failed the independent saved-pose test.
   controller=['hips','neck','head']+[pb.name for pb in B if pb.name.startswith(('spine_','tail_','ear'))]
   controller+=['ik_hand.L','ik_hand.R','ik_foot.L','ik_foot.R']
   controller+=[pb.name for pb in B if pb.name.startswith(('front_toes.','toes.'))]
   controller=list(dict.fromkeys(controller))
   data=[]
   for f in range(1,26):
    loadpose(optimized,f)
    clamp(limit)
    vals={name:(tuple(B[name].rotation_euler),tuple(B[name].location)) for name in controller}
    data.append((f,vals))
   previous=bpy.data.actions.get('run_sprint_v7_ik_spine_repaired')
   if previous:bpy.data.actions.remove(previous)
   repaired=bpy.data.actions.new('run_sprint_v7_ik_spine_repaired')
   repaired.use_fake_user=True
   arm.animation_data.action=repaired
   for f,entries in data:
    scene.frame_set(f)
    for nm,(rot,loc) in entries.items():
     pb=B[nm];pb.rotation_mode='XYZ';pb.rotation_euler=rot;pb.location=loc
     pb.keyframe_insert("rotation_euler",frame=f,group=nm)
     pb.keyframe_insert("location",frame=f,group=nm)
   arm.animation_data.action=repaired
   scene.frame_set(1);bpy.context.view_layer.update()
   path=out/"fare_run_v7_verified_candidate.blend"
   bpy.ops.wm.save_as_mainfile(filepath=str(path),compress=True)
   report["blend"]=path.name
   report["status"]="BAKED_V7_PENDING_REOPEN_AND_RENDER"
 except Exception as ex:
  report["status"]="FAIL";report["error"]=str(ex);report["traceback"]=traceback.format_exc()
 (out/"independent_baked_validation.json").write_text(json.dumps(report,indent=2))
 print("REOPENED_PHASE_REPAIR",report["status"],report.get("saved_v6_crosscheck"))
 if report["status"]=="FAIL":raise SystemExit(1)
if __name__=="__main__":main()
