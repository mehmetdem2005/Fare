"""Export independent GLBs for three Blender actions:
run_sprint_v7_ik_spine_repaired, walk_provisional, run2_provisional.
Not a copy of inaccessible YouTube Shorts. Preserve full multiaction .blend.
"""
import bpy,argparse,sys,json,struct,hashlib,traceback
from pathlib import Path
def args():
 p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--out',required=True);return p.parse_args(sys.argv[sys.argv.index('--')+1:])
def checksum(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def label_glb(path,newname):
 buf=path.read_bytes()
 assert buf[:4]==b'glTF' and struct.unpack_from('<I',buf,8)[0]==len(buf)
 p=12;chunks=[];data=None
 while p<len(buf):
  num,typ=struct.unpack_from('<II',buf,p);chunk=buf[p+8:p+8+num]
  if typ==0x4E4F534A:
   data=json.loads(chunk)
   animations=data.get('animations',[])
   if len(animations)!=1:raise RuntimeError('Expected 1 clip, got '+str([a.get('name') for a in animations]))
   data['animations'][0]['name']=newname
   chunk=json.dumps(data,separators=(',',':'),ensure_ascii=False).encode('utf-8')
   chunk+=b' '*((-len(chunk))%4)
  chunks.append(struct.pack('<II',len(chunk),typ)+chunk)
  p+=8+num
 if data is None:raise RuntimeError('GLB JSON not found')
 length=12+sum(len(ch) for ch in chunks)
 path.write_bytes(b'glTF'+struct.pack('<II',2,length)+b''.join(chunks))
 out=path.read_bytes()
 assert struct.unpack_from('<I',out,8)[0]==len(out)
 return data
def main():
 c=args();out=Path(c.out).resolve();out.mkdir(exist_ok=True,parents=True)
 rep={'status':'STARTED','source':str(c.source),'video_reference':'Unaccessible YouTube (429); walk/run2 provisional'}
 try:
  bpy.ops.wm.open_mainfile(filepath=str(Path(c.source).resolve()))
  mesh=max([o for o in bpy.data.objects if o.type=='MESH' and any(m.type=='ARMATURE' and m.object for m in o.modifiers)],key=lambda o:len(o.data.vertices))
  arm=next(m.object for m in mesh.modifiers if m.type=='ARMATURE' and m.object)
  actions=['run_sprint_v7_ik_spine_repaired','walk_provisional','run2_provisional']
  for name in actions:
   if name not in bpy.data.actions:raise RuntimeError('Missing action: '+name)
  arm.animation_data_create()
  for track in arm.animation_data.nla_tracks:track.mute=True
  rep["clips"]=[]
  for name in actions:
   arm.animation_data.action=bpy.data.actions[name]
   bpy.context.scene.frame_set(1)
   bpy.context.view_layer.objects.active=mesh
   p=out/(name+'.glb')
   settings={'filepath':str(p),'export_format':'GLB','export_skins':True,
             'export_animations':True,'export_def_bones':True,
             'export_lights':False,'export_cameras':False,'export_yup':True}
   prop=bpy.ops.export_scene.gltf.get_rna_type().properties.get('export_animation_mode')
   if prop:
    vals=[o.identifier for o in prop.enum_items]
    settings['export_animation_mode']='ACTIVE_ACTIONS' if 'ACTIVE_ACTIONS' in vals else ('ACTIONS' if 'ACTIONS' in vals else vals[0])
   bpy.ops.export_scene.gltf(**settings)
   gltf=label_glb(p,name)
   anim=gltf['animations'][0]
   if len(anim.get('channels',[]))<30 or not gltf.get('skins'):raise RuntimeError(name+' GLB missing valid channels/skin')
   rep["clips"].append({'name':name,'file':p.name,'channels':len(anim['channels']),
                         'skins':len(gltf['skins']),'size_bytes':p.stat().st_size,
                         'sha256':checksum(p)})
  arm.animation_data.action=bpy.data.actions[actions[0]]
  bpy.context.scene.frame_set(1)
  saved=out/'fare_body_repaired_with_three_actions_EXPERIMENT.blend'
  bpy.ops.file.pack_all()
  bpy.ops.wm.save_as_mainfile(filepath=str(saved),compress=True)
  rep['blend']={'file':saved.name,'bytes':saved.stat().st_size,'sha256':checksum(saved)}
  rep["status"]="PASS_THREE_VALID_ANIMATED_GLBS"
 except Exception as ex:
  rep["status"]="FAIL";rep["error"]=str(ex);rep["traceback"]=traceback.format_exc()
 (out/'glb_export_report.json').write_text(json.dumps(rep,indent=2,ensure_ascii=False))
 print('THREE_ANIMATION_EXPORT',rep['status'],[(a['name'],a['channels']) for a in rep.get('clips',[])])
 if rep["status"]=="FAIL":raise SystemExit(1)
if __name__=='__main__':main()
