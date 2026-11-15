"""Create two ORIGINAL candidate quadruped locomotion actions after verified torso repair.
The exact Shorts cannot be accessed by CI (YouTube HTTP 429); these clips are NOT
claimed frame-matched to the user reference. Exports only reviewed candidates.
Input must be independently validated v7 repair action; no manual/auto weights.
"""
import bpy,sys,json,math,argparse,traceback,struct
from pathlib import Path
from mathutils import Vector
TAU=2*math.pi
R=math.radians
def cli():
 p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--out',required=True)
 return p.parse_args(sys.argv[sys.argv.index('--')+1:])
def q(x,p):
 x.sort();return x[int((len(x)-1)*p)] if x else 0
def pts(o):
 dg=bpy.context.evaluated_depsgraph_get(); ev=o.evaluated_get(dg)
 mesh=ev.to_mesh(preserve_all_data_layers=False,depsgraph=dg)
 try:
  mat=ev.matrix_world.copy();return [tuple(mat@v.co) for v in mesh.vertices]
 finally:ev.to_mesh_clear()
def main():
 c=cli();out=Path(c.out).resolve();out.mkdir(exist_ok=True,parents=True)
 report={"status":"STARTED","warning":"Reference YouTube video could not be inspected; original provisional gait animations"}
 try:
  bpy.ops.wm.open_mainfile(filepath=str(Path(c.source).resolve()))
  mesh=max([o for o in bpy.data.objects if o.type=='MESH' and any(m.type=='ARMATURE' and m.object for m in o.modifiers)],key=lambda o:len(o.data.vertices))
  arm=next(m.object for m in mesh.modifiers if m.type=='ARMATURE' and m.object);B=arm.pose.bones;sc=bpy.context.scene
  base=bpy.data.actions.get('run_sprint_v7_ik_spine_repaired')
  if not base:raise RuntimeError('Input is not validated torso repair v7')
  arm.animation_data_create()
  for t in arm.animation_data.nla_tracks:t.mute=True
  before=[(m.name,m.use_deform_preserve_volume) for m in mesh.modifiers if m.type=='ARMATURE']
  for bone in B:bone.matrix_basis.identity()
  arm.animation_data.action=None
  sc.frame_set(1);rest=pts(mesh)
  part=mesh.data.attributes.get('part_id')
  V=mesh.data.vertices
  roi={
   "interleg":{i for i,v in enumerate(V) if part.data[i].value==6 and -.1<=v.co.y<=.055 and .045<=v.co.z<=.16 and abs(v.co.x)<=.165},
   "front":{i for i,v in enumerate(V) if part.data[i].value==6 and -.27<=v.co.y<=.055 and .045<=v.co.z<=.285 and abs(v.co.x)<=.17},
   "central":{i for i,v in enumerate(V) if part.data[i].value==6 and -.27<=v.co.y<=.055 and .045<=v.co.z<=.285 and abs(v.co.x)<=.06},
   "rear":{i for i,v in enumerate(V) if part.data[i].value==6 and .055<v.co.y<=.33 and .06<=v.co.z<=.3 and abs(v.co.x)<=.17},
   "foreleg":{i for i,v in enumerate(V) if v.co.y<-.18 and v.co.z<.15 and abs(v.co.x)>.09}
  }
  E={name:[(u,v,d) for e in mesh.data.edges for u,v in [tuple(e.vertices)]
           if u in mask and v in mask for d in [math.dist(rest[u],rest[v])] if d>.001] for name,mask in roi.items()}
  def metric(coords):
   return {name:q([abs(math.dist(coords[u],coords[v])/d-1) for u,v,d in edges],.95) for name,edges in E.items()}
  def reset():
   for pb in B:
    pb.rotation_mode='XYZ';pb.rotation_euler=(0,0,0);pb.location=(0,0,0);pb.scale=(1,1,1)
   bpy.context.view_layer.update()
  inverses={name:arm.data.bones[name].matrix_local.to_3x3().inverted()
            for name in ['hips','ik_foot.L','ik_foot.R','ik_hand.L','ik_hand.R']}
  keyed=['hips','neck','head']+[pb.name for pb in B if pb.name.startswith(('spine_','tail_','ear'))]
  keyed+=['ik_hand.L','ik_hand.R','ik_foot.L','ik_foot.R']
  keyed+=[pb.name for pb in B if pb.name.startswith(('front_toes.','toes.'))]
  keyed=list(dict.fromkeys(keyed))
  def move(name,x=0,y=0,z=0):
   B[name].location=inverses[name]@Vector((x,y,z))
  def rotate(name,x=0,y=0,z=0):
   if name in B:B[name].rotation_euler=(x,y,z)
  def step(phase,period,stride,lift):
   t=TAU*(phase%1)
   return (stride*.5*math.cos(t), lift*max(0,math.sin(t))**1.4)
  def pose(mode,p):
   reset()
   if mode=="walk":
    phases={'ik_hand.L':0.,'ik_foot.R':.25,'ik_hand.R':.5,'ik_foot.L':.75}
    span=.052;lift=.019;bounce=.0045;spamp=2.4;hip_amp=.75
   else:
    phases={'ik_foot.L':.0,'ik_foot.R':.055,'ik_hand.L':.48,'ik_hand.R':.54}
    span=.085;lift=.027;bounce=.011;spamp=5.4;hip_amp=1.4
   # Individual four-beat walk versus two-pair bounding run.
   for bone,phase in phases.items():
    dy,dz=step(p-phase,1,span,lift)
    move(bone,0,dy,dz)
   flex=math.sin(TAU*p+.5)
   flight=max(0.,math.sin(TAU*p+.75))**2
   move('hips',.0015*math.sin(TAU*p),0,bounce*(.3+.7*flight))
   rotate('hips',x=R(hip_amp)*flex,z=R(.5)*math.sin(TAU*p))
   profile=[.31,.29,.20,.12,.08]
   for i,val in enumerate(profile,1):
    rotate('spine_%02d'%i,x=R(spamp*val)*flex)
   rotate('neck',x=-R(1.5)*flex)
   rotate('head',x=-R(1.1)*flex)
   # Keep each front IK target within 96% of the physical two-bone reach.
   bpy.context.view_layer.update()
   for side in 'LR':
    root=B['upper_arm.'+side];ik=B['ik_hand.'+side]
    lim=.96*(arm.data.bones[root.name].length+arm.data.bones['forearm.'+side].length)
    vec=ik.head-root.head
    if vec.length>lim:
     desired=root.head+vec.normalized()*lim
     ik.location=ik.location+inverses[ik.name]@(desired-ik.head)
   for side in "LR":
    ph=phases['ik_hand.'+side]
    rotate('front_toes.'+side,x=-R(4)*max(0,math.sin(TAU*(p-ph)+2.6)))
    ph=phases['ik_foot.'+side]
    rotate('toes.'+side,x=-R(4)*max(0,math.sin(TAU*(p-ph)+2.6)))
    rotate('ear.'+side,x=-R(3)+R(1.1)*math.sin(TAU*p-(0 if side=='L' else .3)))
   for i in range(1,7):
    rotate('tail_%02d'%i,x=R(1.4)*math.sin(TAU*p-i*.35),z=R(.8)*math.sin(TAU*p-i*.55))
   bpy.context.view_layer.update()
  report['actions']=[]
  for mode,name,period in [('walk','walk_provisional',36),('run2','run2_provisional',24)]:
   new=bpy.data.actions.new(name);new.use_fake_user=True
   arm.animation_data.action=new
   coords=[]
   for f in range(1,period+2):
    p=((f-1)%period)/period
    pose(mode,p)
    for bone in keyed:
     pb=B[bone]
     pb.keyframe_insert('rotation_euler',frame=f,group=bone)
     pb.keyframe_insert('location',frame=f,group=bone)
    sc.frame_set(f)
    coords.append(pts(mesh))
   # sample first and last; require geometry repeat before publishing
   seam=max(math.dist(a,b) for a,b in zip(coords[0],coords[-1]))
   rows=[metric(x) for x in coords[:-1]]
   stats={region:{'mean':sum(f[region] for f in rows)/period,'worst':max(f[region] for f in rows)} for region in E}
   rec={'name':name,'frame_count':period,'fps':24,'loop_seam':seam,'region_metrics':stats}
   # compare to old v7 baseline later via independent QA.
   rec['status']='EXPERIMENT' if seam<.0002 else 'FAIL_LOOP'
   report['actions'].append(rec)
   if rec['status']=='FAIL_LOOP':raise RuntimeError(name+" loop mismatch "+str(seam))
  arm.animation_data.action=base
  sc.frame_set(1)
  save=out/'fare_v7_with_walk_and_run2_PROVISIONAL.blend'
  bpy.ops.wm.save_as_mainfile(filepath=str(save),compress=True)
  report['blend']=save.name;report['status']='PROVISIONAL_ACTIONS_BUILT_LOOP_CHECKED'
 except Exception as ex:
  report.update(status='FAIL',error=str(ex),traceback=traceback.format_exc())
 (out/'additional_gaits_qa.json').write_text(json.dumps(report,indent=2,ensure_ascii=False))
 print('GAITS_STATUS',report['status'],report.get('actions'))
 if report['status']=='FAIL':raise SystemExit(1)
if __name__=='__main__':main()
