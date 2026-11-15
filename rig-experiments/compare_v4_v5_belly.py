"""Compare two fully exported running animations on the exact same lower-torso
vertex IDs, using Blender's actual evaluated mesh rather than proxy LBS.
No mesh or armature modification.
"""
import bpy, argparse,sys,math,json,hashlib
from pathlib import Path
def arg():
 p=argparse.ArgumentParser()
 p.add_argument('--old',required=True);p.add_argument('--new',required=True);p.add_argument('--out',required=True)
 return p.parse_args(sys.argv[sys.argv.index('--')+1:])
def weight(g,i):
 try:return g.weight(i)
 except RuntimeError:return 0.0
def points(mesh):
 dg=bpy.context.evaluated_depsgraph_get();o=mesh.evaluated_get(dg);m=o.to_mesh(preserve_all_data_layers=False,depsgraph=dg)
 try:
  mat=o.matrix_world.copy()
  return [tuple(mat@v.co) for v in m.vertices]
 finally:o.to_mesh_clear()
def pctl(a,q):
 a.sort();return a[int((len(a)-1)*q)] if a else None
def assess(path,actionname):
 bpy.ops.wm.open_mainfile(filepath=str(Path(path).resolve()))
 mesh=max([o for o in bpy.data.objects if o.type=='MESH' and any(m.type=='ARMATURE' and m.object for m in o.modifiers)],key=lambda o:len(o.data.vertices))
 arm=next(m.object for m in mesh.modifiers if m.type=='ARMATURE' and m.object)
 scene=bpy.context.scene
 act=bpy.data.actions.get(actionname)
 if not act:raise ValueError('Action missing:'+actionname)
 arm.animation_data_create()
 arm.animation_data.action=None
 for tr in arm.animation_data.nla_tracks:tr.mute=True
 for pb in arm.pose.bones:pb.matrix_basis.identity()
 scene.frame_set(1)
 rest=points(mesh)
 candidates=[mesh.vertex_groups.get(n) for n in ('hips','spine_01','spine_02','spine_03','spine_04','spine_05')]
 candidates=[g for g in candidates if g]
 torso=[v.index for v in mesh.data.vertices if sum(weight(g,v.index) for g in candidates)>.54]
 zarr=sorted(mesh.data.vertices[i].co.z for i in torso);cut=zarr[int((len(zarr)-1)*.42)]
 belly=[i for i in torso if mesh.data.vertices[i].co.z<=cut]
 bellyset=set(belly)
 edges=[tuple(e.vertices) for e in mesh.data.edges if e.vertices[0] in bellyset and e.vertices[1] in bellyset]
 assert len(belly)>500 and len(edges)>1000
 length=[math.dist(rest[a],rest[b]) for a,b in edges]
 arm.animation_data.action=act
 data=[]
 previous=None
 for f in range(1,26):
  scene.frame_set(f)
  coords=points(mesh)
  errors=[abs(math.dist(coords[a],coords[b])/den-1.) for (a,b),den in zip(edges,length) if den>1e-7]
  heights=[coords[i][2] for i in belly]
  data.append({'frame':f,'edge_p95':pctl(errors,.95),'edge_p99':pctl(errors,.99),'height_mean':sum(heights)/len(heights),'height_p10':pctl(heights,.1),'height_p90':pctl(heights,.9)})
  if f==1:first=coords
  if f==25: last=coords
 assert len(rest)==len(coords)
 return {'source':str(path),'action':actionname,'vertex_count':len(rest),'belly_vertex_count':len(belly),'belly_edge_count':len(edges),
         'roi_fingerprint':hashlib.sha256(','.join(map(str,belly)).encode()).hexdigest(),
         'frames':data,'max_edge_p95':max(x['edge_p95'] for x in data),'mean_edge_p95':sum(x['edge_p95'] for x in data[:24])/24,
         'belly_height_mean_range':max(x['height_mean'] for x in data)-min(x['height_mean'] for x in data),
         'loop_seam_max':max(math.dist(a,b) for a,b in zip(first,last)),
         'max_vertex_motion_from_first':max(math.dist(a,b) for a,b in zip(first,coords)),
         'peak_frames':[x['frame'] for x in data if x['edge_p95']>.40]}
def main():
 c=arg(); out=Path(c.out);out.mkdir(parents=True,exist_ok=True)
 result={'old':assess(c.old,'run_sprint_v4'),'new':assess(c.new,'run_sprint_v5')}
 a=result['old'];b=result['new']
 assert a['roi_fingerprint']==b['roi_fingerprint'] and a['vertex_count']==b['vertex_count']
 result['comparison']={
  'old_max_p95':a['max_edge_p95'],'new_max_p95':b['max_edge_p95'],
  'max_p95_reduction_pct':100*(1-b['max_edge_p95']/a['max_edge_p95']),
  'old_mean_p95':a['mean_edge_p95'],'new_mean_p95':b['mean_edge_p95'],
  'mean_p95_reduction_pct':100*(1-b['mean_edge_p95']/a['mean_edge_p95']),
  'old_belly_height_mean_range':a['belly_height_mean_range'],
  'new_belly_height_mean_range':b['belly_height_mean_range'],
  'frame9_old_p95':a['frames'][8]['edge_p95'],
  'frame9_new_p95':b['frames'][8]['edge_p95'],
  'frame9_p95_reduction_pct':100*(1-b['frames'][8]['edge_p95']/a['frames'][8]['edge_p95']),
  'loop_seam_new':b['loop_seam_max'],
 }
 result['comparison']['is_regression']=bool(b['max_edge_p95']>a['max_edge_p95']*1.02 or b['mean_edge_p95']>a['mean_edge_p95']*1.02)
 result['status']='MEASURED_DO_NOT_AUTO_PROMOTE' if result['comparison']['is_regression'] else 'MEASURED_CANDIDATE'
 (out/'v4_v5_belly_comparison.json').write_text(json.dumps(result,indent=2,ensure_ascii=False))
 print('SPRINT_COMPARE',json.dumps(result['comparison']))
if __name__=='__main__':main()
