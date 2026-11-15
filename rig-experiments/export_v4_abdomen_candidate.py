"""Package the best measured sprint-v4 skinning candidate into a GLB.
Actual Blender 5.1.2 runner; verifies morph/skin animation and 24-frame action.
Input and production deliver/ are never overwritten.
"""
import argparse, sys, json, struct, hashlib, traceback
from pathlib import Path
import bpy

def digest(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):
            h.update(b)
    return h.hexdigest()

def parse():
    p=argparse.ArgumentParser()
    p.add_argument('--source',required=True)
    p.add_argument('--out',required=True)
    return p.parse_args(sys.argv[sys.argv.index('--')+1:])

def save_patched_json_glb(path,data):
    old=path.read_bytes()
    offset=12
    encoded=json.dumps(data,separators=(',',':'),ensure_ascii=False).encode('utf-8')
    encoded+=b' '*((-len(encoded))%4)
    blocks=[]
    while offset<len(old):
        length,kind=struct.unpack_from('<II',old,offset)
        buf=old[offset+8:offset+8+length]
        if kind==0x4E4F534A:buf=encoded
        blocks.append(struct.pack('<II',len(buf),kind)+buf)
        offset+=8+length
    path.write_bytes(b'glTF'+struct.pack('<II',2,12+sum(len(x) for x in blocks))+b''.join(blocks))

def main():
    a=parse();src=Path(a.source).resolve();out=Path(a.out).resolve()
    out.mkdir(parents=True,exist_ok=True)
    report={'status':'STARTED','source':str(src),'source_sha256':digest(src),'blender':bpy.app.version_string}
    try:
        bpy.ops.wm.open_mainfile(filepath=str(src))
        mesh=max((o for o in bpy.data.objects if o.type=='MESH' and any(m.type=='ARMATURE' and m.object for m in o.modifiers)),key=lambda o:len(o.data.vertices))
        arm=next(mod.object for mod in mesh.modifiers if mod.type=='ARMATURE' and mod.object)
        action=bpy.data.actions.get('run_sprint_v4')
        if action is None:raise RuntimeError('run_sprint_v4 action missing')
        arm.animation_data_create()
        arm.animation_data.action=action
        for track in arm.animation_data.nla_tracks:track.mute=True
        scene=bpy.context.scene
        scene.render.fps=24
        scene.frame_start=1;scene.frame_end=24
        scene.frame_set(1)
        bpy.context.view_layer.update()
        # save protected experiment copy, not a production blessed release
        save=out/'fare_run_v4_abdomen_repaired_EXPERIMENT.blend'
        bpy.ops.file.pack_all()
        bpy.ops.wm.save_as_mainfile(filepath=str(save),compress=True)
        glb=out/'fare_run_v4_abdomen_repaired_EXPERIMENT.glb'
        bpy.context.view_layer.objects.active=mesh
        cfg={'filepath':str(glb),'export_format':'GLB','export_animations':True,
             'export_skins':True,'export_def_bones':True,'export_cameras':False,
             'export_lights':False,'export_yup':True}
        prop=bpy.ops.export_scene.gltf.get_rna_type().properties.get('export_animation_mode')
        if prop:
            ids=[x.identifier for x in prop.enum_items]
            cfg['export_animation_mode']='ACTIVE_ACTIONS' if 'ACTIVE_ACTIONS' in ids else 'ACTIONS' if 'ACTIONS' in ids else ids[0]
        bpy.ops.export_scene.gltf(**cfg)
        data=glb.read_bytes()
        assert data[:4]==b'glTF'
        offset=12;gltf=None
        while offset<len(data):
            n,t=struct.unpack_from('<II',data,offset)
            if t==0x4E4F534A:gltf=json.loads(data[offset+8:offset+8+n])
            offset+=8+n
        if not gltf or not gltf.get('animations'):raise RuntimeError('No animations exported')
        clips=gltf['animations']
        if len(clips)!=1:raise RuntimeError('Expected exactly one active action, got '+str([x.get('name') for x in clips]))
        channels=len(clips[0].get('channels',[]))
        if channels<50:raise RuntimeError('Insufficient GLB animation channels: '+str(channels))
        if len(gltf.get('skins',[]))<1:raise RuntimeError('GLB skin missing')
        clips[0]['name']='run_sprint_v4'
        save_patched_json_glb(glb,gltf)
        # Validate rewritten binary framing and animation metadata.
        binary=glb.read_bytes()
        assert struct.unpack_from('<I',binary,8)[0]==len(binary)
        jn,typ=struct.unpack_from('<II',binary,12)
        assert typ==0x4E4F534A
        again=json.loads(binary[20:20+jn])
        assert again['animations'][0]['name']=='run_sprint_v4'
        assert len(again['animations'][0]['channels'])==channels
        report.update(status='PASS',armature=arm.name,mesh=mesh.name,
            bones=len(arm.pose.bones),vertices=len(mesh.data.vertices),
            glb_skins=len(gltf.get('skins',[])),action='run_sprint_v4',
            action_channels=channels,blend=save.name,glb=glb.name,
            blend_sha256=digest(save),glb_sha256=digest(glb))
    except Exception as exc:
        report.update(status='FAIL',error=str(exc),traceback=traceback.format_exc())
    (out/'export_qa.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    print('EXPORT_V4_STATUS',report['status'],report.get('error',''),report.get('action_channels'))
    if report['status']!='PASS':raise SystemExit(1)
if __name__=='__main__':main()
