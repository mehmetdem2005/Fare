"""Parametric single-bone-informed run repair.
Blender 5.1.2, 49-bone GitHub mouse, tested sprint v4 + 65% flank weight mix.
Never overwrite original model. Try phase-correct hips/spine x offsets per bone,
full 24-frame fixed-ROI strains & head/limb guards. Reject regression.
"""
import bpy,math,sys,json,argparse,traceback,hashlib
from pathlib import Path
from mathutils import Vector
TAU=2*math.pi
def cli():
 p=argparse.ArgumentParser()
 p.add_argument("--source",required=True);p.add_argument("--out",required=True)
 return p.parse_args(sys.argv[sys.argv.index('--')+1:])
def q(a,frac):
 if not a:return 0.
 a.sort();return a[int((len(a)-1)*frac)]
def pts(o):
 deps=bpy.context.evaluated_depsgraph_get()
 e=o.evaluated_get(deps);m=e.to_mesh(preserve_all_data_layers=False,depsgraph=deps)
 try:
  mx=e.matrix_world.copy()
  return [tuple(mx@v.co) for v in m.vertices]
 finally:e.to_mesh_clear()
def main():
 a=cli();out=Path(a.out).resolve();out.mkdir(exist_ok=True,parents=True)
 rep={"status":"STARTED","input":a.source,"blender":bpy.app.version_string,
      "acceptance":"objective multi-ROI gains, no relevant rear/distal/head regressions, no worse overreach"}
 try:
  bpy.ops.wm.open_mainfile(filepath=str(Path(a.source).resolve()))
  mesh=max([o for o in bpy.data.objects if o.type=="MESH" and any(m.type=="ARMATURE" and m.object for m in o.modifiers)],key=lambda o:len(o.data.vertices))
  arm=next(m.object for m in mesh.modifiers if m.type=="ARMATURE" and m.object)
  B=arm.pose.bones;sc=bpy.context.scene
  action=bpy.data.actions.get("run_sprint_v4")
  assert action is not None,"source run_sprint_v4 missing"
  arm.animation_data_create()
  for track in arm.animation_data.nla_tracks:track.mute=True
  arm.animation_data.action=None
  for pb in B:pb.matrix_basis.identity()
  sc.frame_set(1)
  rest=pts(mesh)
  part=mesh.data.attributes.get('part_id')
  if part is None:raise RuntimeError('mesh part_id absent')
  vertices=mesh.data.vertices;N=len(vertices)
  groups={g.name:g for g in mesh.vertex_groups}
  def ispart(i,p):return int(part.data[i].value)==p
  sel={
   "interleg":set(i for i,v in enumerate(vertices) if ispart(i,6) and -.1<=v.co.y<=.055 and .045<=v.co.z<=.16 and abs(v.co.x)<=.165),
   "front":set(i for i,v in enumerate(vertices) if ispart(i,6) and -.27<=v.co.y<=.055 and .045<=v.co.z<=.285 and abs(v.co.x)<=.17),
   "central":set(i for i,v in enumerate(vertices) if ispart(i,6) and -.27<=v.co.y<=.055 and .045<=v.co.z<=.285 and abs(v.co.x)<=.06),
   "rear":set(i for i,v in enumerate(vertices) if ispart(i,6) and .055<v.co.y<=.33 and .06<=v.co.z<=.3 and abs(v.co.x)<=.17),
   "foreleg":set(i for i,v in enumerate(vertices) if v.co.y<-.18 and v.co.z<.15 and abs(v.co.x)>.09),
   "head":set(i for i,v in enumerate(vertices) if v.co.y<-.30 and v.co.z>.22),
  }
  edges={}
  for name,mask in sel.items():
   edges[name]=[(u,v,d) for e in mesh.data.edges for u,v in [tuple(e.vertices)]
                if u in mask and v in mask for d in [math.dist(rest[u],rest[v])] if d>=.001]
  assert len(edges['interleg'])>500
  spines=['spine_%02d'%i for i in range(1,6)]
  body=[x for x in spines if x in B]
  patterns={
   'even':[.2,.2,.2,.2,.2],
   'middle':[.12,.22,.26,.24,.16],
   'front':[.08,.12,.16,.31,.33],
   'rear':[.31,.29,.20,.12,.08],
  }
  def framepos(frame):
   sc.frame_set(frame-1 if frame>1 else 2);sc.frame_set(frame)
   bpy.context.view_layer.update()
  def measure(p):
   obj={}
   for name,E in edges.items():
    # absolute relative change; report stretching separately from compression
    v=[math.dist(p[u],p[w])/l-1 for u,w,l in E]
    obj[name]={
      'p95':q([abs(z) for z in v],.95),
      'stretch':q([max(0,z) for z in v],.95),
      'compression':q([max(0,-z) for z in v],.95)
    }
   return obj
  ref=[]
  for f in range(1,25):
   arm.animation_data.action=action;framepos(f)
   p=pts(mesh)
   ref.append(measure(p))
  def summarize(frames):
   ret={}
   for name in edges:
    ret[name]={'mean':sum(x[name]['p95'] for x in frames)/len(frames),
               'worst':max(x[name]['p95'] for x in frames),
               'stretch_worst':max(x[name]['stretch'] for x in frames),
               'compression_worst':max(x[name]['compression'] for x in frames)}
   return ret
  baseline=summarize(ref)
  rep['roi']={name:{'vertices':len(sel[name]),'edges':len(edges[name])} for name in sel}
  rep['baseline']=baseline
  trials=[]
  combos=[(profile,amp,hip) for profile in patterns for amp in (4,8,12,16,24) for hip in (-3,0,3)]
  for pattern,amp,hip in combos:
   vals=[]; limit=0.
   shape=patterns[pattern]
   for f in range(1,25):
    arm.animation_data.action=action;framepos(f)
    # positive cosine at frame 3, negative at frame 15.
    # single-bone f3 preferred spine negative; f15 preferred spine positive.
    wave=math.cos(TAU*(f-3)/24)
    for bone,part in zip(spines,shape):
     if bone in B:
      pb=B[bone];v=list(pb.rotation_euler);v[0]-=math.radians(amp*part*wave);pb.rotation_euler=v
    if 'hips' in B:
     pb=B['hips'];v=list(pb.rotation_euler);v[0]+=math.radians(hip*wave);pb.rotation_euler=v
    bpy.context.view_layer.update()
    vals.append(measure(pts(mesh)))
   metrics=summarize(vals)
   ratios={name:{'mean':metrics[name]['mean']/baseline[name]['mean'] if baseline[name]['mean'] else 1,
                 'worst':metrics[name]['worst']/baseline[name]['worst'] if baseline[name]['worst'] else 1}
           for name in baseline}
   # hard guards on local injury:
   guard=(ratios['rear']['worst']<=1.05 and ratios['foreleg']['worst']<=1.04
          and ratios['head']['worst']<=1.06 and ratios['central']['worst']<=1.10
          and ratios['front']['worst']<=1.07)
   score=(.60*ratios['interleg']['worst']+.25*ratios['interleg']['mean']
           +.09*ratios['front']['worst']+.06*ratios['central']['worst'])
   trials.append({"pattern":pattern,"amplitude":amp,"hip":hip,
                  "passes_guards":guard,"score":score,"metrics":metrics,"ratios":ratios,
                  "f3_interleg":vals[2]['interleg'],"f15_interleg":vals[14]['interleg']})
  bests=[t for t in trials if t['passes_guards']
         and t['ratios']['interleg']['worst']<.98
         and t['ratios']['interleg']['mean']<.99
         and t['ratios']['front']['worst']<=1.04]
  rep['trials']=sorted(trials,key=lambda x:x['score'])
  rep['trial_count']=len(trials)
  rep['selected']=min(bests,key=lambda x:x['score']) if bests else None
  if rep['selected']:
   win=rep['selected'];pattern,amp,hip=win['pattern'],win['amplitude'],win['hip']
   orig=action
   clone=orig.copy()
   clone.name='run_sprint_v6_spine_phase_repaired'
   clone.use_fake_user=True
   arm.animation_data.action=clone
   for f in range(1,26):
    arm.animation_data.action=orig;framepos(f)
    wave=math.cos(TAU*((f-1)%24-2)/24)
    saved={}
    for bone,part in zip(spines,patterns[pattern]):
     if bone in B:
      pb=B[bone];vec=list(pb.rotation_euler);vec[0]-=math.radians(amp*part*wave)
      saved[bone]=vec
    if 'hips' in B:
     pb=B['hips'];vec=list(pb.rotation_euler);vec[0]+=math.radians(hip*wave);saved['hips']=vec
    arm.animation_data.action=clone
    for bone,vec in saved.items():
     pb=B[bone];pb.rotation_mode='XYZ';pb.rotation_euler=vec
     pb.keyframe_insert(data_path='rotation_euler',frame=f,group=bone)
   arm.animation_data.action=clone;sc.frame_set(1);bpy.context.view_layer.update()
   path=out/'mouse_run_v6_spine_phase_REVIEW.blend'
   bpy.ops.wm.save_as_mainfile(filepath=str(path),compress=True)
   rep['output']=path.name
   rep['status']='CANDIDATE_MEASUREMENT_PASS_PENDING_REAL_REOPEN_EXPORT_VISUAL'
  else:rep['status']='NO_ACCEPTABLE_PHASE_PROFILE'
 except Exception as exc:
  rep['status']='FAIL'
  rep['error']=str(exc)
  rep['traceback']=traceback.format_exc()
 (out/'spine_phase_optimization.json').write_text(json.dumps(rep,indent=2,ensure_ascii=False))
 print('SPINE_PHASE',rep['status'],'BEST',rep.get('selected',{}).get('pattern') if rep.get('selected') else None)
 if rep['status']=='FAIL':raise SystemExit(1)
if __name__=='__main__':main()
