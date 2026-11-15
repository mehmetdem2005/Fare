"""Explain v6 saved action vs manual optimized pose discrepancies on EXACT saved file."""
import bpy,json,math,sys,argparse
from pathlib import Path
def cli():
 p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--opt',required=True);p.add_argument('--out',required=True)
 return p.parse_args(sys.argv[sys.argv.index('--')+1:])
def coords(m):
 dg=bpy.context.evaluated_depsgraph_get();ob=m.evaluated_get(dg);me=ob.to_mesh(preserve_all_data_layers=False,depsgraph=dg)
 try:
  mat=ob.matrix_world.copy();return [tuple(mat@v.co) for v in me.vertices]
 finally:ob.to_mesh_clear()
def main():
 a=cli();out=Path(a.out).resolve();out.mkdir(exist_ok=True,parents=True)
 bpy.ops.wm.open_mainfile(filepath=str(Path(a.source).resolve()))
 opt=json.loads(Path(a.opt).read_text())['selected']
 obj=max([o for o in bpy.data.objects if o.type=='MESH' and any(x.type=='ARMATURE' for x in o.modifiers)],key=lambda o:len(o.data.vertices))
 arm=next(x.object for x in obj.modifiers if x.type=='ARMATURE')
 orig=bpy.data.actions['run_sprint_v4'];new=bpy.data.actions['run_sprint_v6_spine_phase_repaired']
 report={'src_bones':len(arm.pose.bones),'src_actions':[(x.name,[(slot.identifier,slot.target_id_type) for slot in x.slots]) for x in bpy.data.actions],'frames':[]}
 B=arm.pose.bones;sc=bpy.context.scene;arm.animation_data_create()
 for t in arm.animation_data.nla_tracks:t.mute=True
 prof={'even':[.2,.2,.2,.2,.2],'middle':[.12,.22,.26,.24,.16],'front':[.08,.12,.16,.31,.33],'rear':[.31,.29,.2,.12,.08]}[opt['pattern']]
 bones=['hips']+['spine_%02d'%n for n in range(1,6)]+['ik_hand.L','ik_hand.R','ik_foot.L','ik_foot.R']
 morph=obj.data.shape_keys.key_blocks
 for frame in (1,2,3,4,5,9,13,15,19,23,24,25):
  item={'frame':frame}
  for mode,action in [('orig',orig),('baked',new),('manual',orig)]:
   arm.animation_data.action=action
   sc.frame_set(frame-1 if frame>1 else 2);sc.frame_set(frame);bpy.context.view_layer.update()
   if mode=='manual':
    wave=math.cos(2*math.pi*(((frame-1)%24)-2)/24)
    for k,bn in enumerate(['spine_01','spine_02','spine_03','spine_04','spine_05']):
     pb=B[bn]
     v=list(pb.rotation_euler)
     v[0]-=math.radians(opt['amplitude']*prof[k]*wave)
     pb.rotation_euler=v
    p=B['hips'];v=list(p.rotation_euler);v[0]+=math.radians(opt['hip']*wave);p.rotation_euler=v
    bpy.context.view_layer.update()
   item[mode]={'pose':{name:{'rot':tuple(float(x) for x in B[name].rotation_euler),
                              'loc':tuple(float(x) for x in B[name].location)} for name in bones},
               'morph':{x.name:float(x.value) for x in morph if x.name.startswith(('crv_shoulder','crv_elbow','crv_spine'))},
               'coords':coords(obj)}
  for tag in ('baked','manual'):
   item[tag+'_vs_orig_max_disp']=max(math.dist(x,y) for x,y in zip(item[tag]['coords'],item['orig']['coords']))
  item['baked_vs_manual_max_disp']=max(math.dist(x,y) for x,y in zip(item['baked']['coords'],item['manual']['coords']))
  for key in ['orig','baked','manual']:del item[key]['coords']
  report['frames'].append(item)
 (out/'baked_action_debug.json').write_text(json.dumps(report,indent=2))
 print('ACTION_DEBUG',{j['frame']:j['baked_vs_manual_max_disp'] for j in report['frames']})
if __name__=='__main__':main()
