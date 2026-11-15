"""Reopened L3 gates for v7 combined phase + IK repair. Do not allow a
saved action to pass based only on unsaved manual pose measurements.
"""
import bpy,sys,math,json,argparse,traceback
from pathlib import Path
def cli():
 p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--expected',required=True);p.add_argument('--out',required=True)
 return p.parse_args(sys.argv[sys.argv.index('--')+1:])
def q(x,p):
 x.sort();return x[int((len(x)-1)*p)] if x else 0.
def coords(obj):
 dg=bpy.context.evaluated_depsgraph_get();ev=obj.evaluated_get(dg);mesh=ev.to_mesh(preserve_all_data_layers=False,depsgraph=dg)
 try:
  mat=ev.matrix_world.copy();return [tuple(mat@v.co) for v in mesh.vertices]
 finally:ev.to_mesh_clear()
def main():
 a=cli();out=Path(a.out).resolve();out.mkdir(exist_ok=True,parents=True)
 j={"status":"STARTED"}
 try:
  target=json.loads(Path(a.expected).read_text())
  if target["status"]!="BAKED_V7_PENDING_REOPEN_AND_RENDER":raise RuntimeError("Expected independent v7 must pass")
  bpy.ops.wm.open_mainfile(filepath=str(Path(a.source).resolve()))
  mesh=max([o for o in bpy.data.objects if o.type=='MESH' and any(m.type=='ARMATURE' for m in o.modifiers)],key=lambda o:len(o.data.vertices))
  arm=next(m.object for m in mesh.modifiers if m.type=='ARMATURE' and m.object)
  b=bpy.data.actions.get('run_sprint_v7_ik_spine_repaired')
  if not b:raise RuntimeError("Saved v7 action missing")
  arm.animation_data_create();arm.animation_data.action=None
  for tr in arm.animation_data.nla_tracks:tr.mute=True
  for pb in arm.pose.bones:pb.matrix_basis.identity()
  scene=bpy.context.scene;scene.frame_set(1)
  rest=coords(mesh)
  part=mesh.data.attributes.get('part_id');vv=mesh.data.vertices
  regions={
   "interleg":set(i for i,x in enumerate(vv) if part.data[i].value==6 and -.1<=x.co.y<=.055 and .045<=x.co.z<=.16 and abs(x.co.x)<=.165),
   "front":set(i for i,x in enumerate(vv) if part.data[i].value==6 and -.27<=x.co.y<=.055 and .045<=x.co.z<=.285 and abs(x.co.x)<=.17),
   "central":set(i for i,x in enumerate(vv) if part.data[i].value==6 and -.27<=x.co.y<=.055 and .045<=x.co.z<=.285 and abs(x.co.x)<=.06),
   "rear":set(i for i,x in enumerate(vv) if part.data[i].value==6 and .055<x.co.y<=.33 and .06<=x.co.z<=.3 and abs(x.co.x)<=.17),
   "foreleg":set(i for i,x in enumerate(vv) if x.co.y<-.18 and x.co.z<.15 and abs(x.co.x)>.09),
   "head":set(i for i,x in enumerate(vv) if x.co.y<-.30 and x.co.z>.22),
  }
  EE={n:[(i,k,d) for edge in mesh.data.edges for i,k in [tuple(edge.vertices)]
          if i in mask and k in mask for d in [math.dist(rest[i],rest[k])] if d>=.001] for n,mask in regions.items()}
  recorded=[];first=None
  arm.animation_data.action=b
  for f in range(1,26):
   scene.frame_set(f-1 if f>1 else 2);scene.frame_set(f)
   now=coords(mesh)
   if f==1:first=now
   if f==25:seam=max(math.dist(a,b) for a,b in zip(first,now))
   recorded.append({n:q([abs(math.dist(now[i],now[k])/d-1) for i,k,d in e],.95) for n,e in EE.items()})
  scores={n:{"mean":sum(x[n] for x in recorded[:24])/24,"worst":max(x[n] for x in recorded[:24])} for n in EE}
  expected=target["selected"]["score"]
  discrepancy={n:{k:scores[n][k]-expected[n][k] for k in ("mean","worst")} for n in EE}
  mx=max(abs(e) for sub in discrepancy.values() for e in sub.values())
  j.update(metrics=scores,expected=expected,delta=discrepancy,max_abs_discrepancy=mx,loop_seam=seam,
           bone_count=len(arm.pose.bones),vertex_count=len(mesh.data.vertices),action=b.name)
  if mx>3e-4:raise RuntimeError("Saved independent action regression: "+str(mx))
  if seam>1e-5:raise RuntimeError("Seam: "+str(seam))
  if j["bone_count"]!=49 or j["vertex_count"]!=19466:raise RuntimeError("Rig identity mismatch")
  j["status"]="PASS_TRUE_BAKED_SAME_AS_MANUAL"
 except Exception as ex:
  j.update(status="FAIL",error=str(ex),traceback=traceback.format_exc())
 (out/'reopened_v7_test.json').write_text(json.dumps(j,indent=2,ensure_ascii=False))
 print('V7_REOPEN',j["status"],j.get('max_abs_discrepancy'))
 if j["status"]=="FAIL":raise SystemExit(1)
if __name__=="__main__":main()
