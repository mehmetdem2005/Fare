"""Render multi-action candidate side and frontal preview frames using Blender Workbench."""
import bpy,math,sys,json,argparse,traceback
from mathutils import Vector
from pathlib import Path
def args():
 p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--out',required=True)
 return p.parse_args(sys.argv[sys.argv.index('--')+1:])
def main():
 x=args();out=Path(x.out).resolve();out.mkdir(exist_ok=True,parents=True)
 report={"status":"STARTED"}
 try:
  bpy.ops.wm.open_mainfile(filepath=str(Path(x.source).resolve()))
  mesh=max([o for o in bpy.data.objects if o.type=="MESH" and any(m.type=="ARMATURE" for m in o.modifiers)],key=lambda o:len(o.data.vertices))
  arm=next(m.object for m in mesh.modifiers if m.type=="ARMATURE" and m.object)
  camd=bpy.data.cameras.new("GaitQAOrtho")
  cam=bpy.data.objects.new("GaitQAOrtho",camd)
  bpy.context.scene.collection.objects.link(cam)
  box=[mesh.matrix_world@Vector(pt) for pt in mesh.bound_box]
  center=sum(box,Vector((0,0,0)))/8
  extent=max(max(p.y for p in box)-min(p.y for p in box),max(p.z for p in box)-min(p.z for p in box))
  camd.type="ORTHO";camd.ortho_scale=extent*1.6
  scene=bpy.context.scene
  scene.camera=cam
  scene.render.engine="BLENDER_WORKBENCH"
  scene.display.shading.light="STUDIO";scene.display.shading.color_type="MATERIAL"
  scene.render.resolution_x=680;scene.render.resolution_y=440;scene.render.resolution_percentage=100
  scene.render.image_settings.file_format="PNG"
  arm.animation_data_create()
  for tr in arm.animation_data.nla_tracks:tr.mute=True
  clips=[("run_sprint_v7_ik_spine_repaired",24),("walk_provisional",36),("run2_provisional",24)]
  report["renders"]={}
  for name,nframes in clips:
   if name not in bpy.data.actions:raise RuntimeError('Missing action: '+name)
   folder=out/name;folder.mkdir(exist_ok=True)
   arm.animation_data.action=bpy.data.actions[name]
   cam.location=center+Vector((extent*1.55,-extent*.65,extent*.55))
   cam.rotation_euler=(center-cam.location).to_track_quat("-Z","Y").to_euler()
   frames=[1+int(i*nframes/12) for i in range(12)]
   for idx,f in enumerate(frames):
    scene.frame_set(f)
    scene.render.filepath=str(folder/("frame_%02d.png"%idx))
    bpy.ops.render.render(write_still=True)
   # Four orthographic viewpoint checks at stretch/fold phases of verified run.
   if name.startswith("run_sprint_v7"):
    for label,offset in {
      "left":(1.7,0,.35),"right":(-1.7,0,.35),
      "top":(0,0,1.7),"bottom":(0,0,-1.7),
      "front":(0,-1.7,.2),"rear":(0,1.7,.2)
    }.items():
     cam.location=center+Vector(offset)*extent
     cam.rotation_euler=(center-cam.location).to_track_quat("-Z","Y").to_euler()
     for f in (3,15):
      scene.frame_set(f)
      scene.render.filepath=str(folder/("diagnostic_%s_f%02d.png"%(label,f)))
      bpy.ops.render.render(write_still=True)
   report["renders"][name]={"preview_frames":12,"frame_duration_fps":12}
  report["status"]="PASS"
 except Exception as ex:report.update(status="FAIL",error=str(ex),traceback=traceback.format_exc())
 (out/'render_multi_qa.json').write_text(json.dumps(report,indent=2))
 print("MULTI_RENDER",report["status"])
 if report["status"]=="FAIL":raise SystemExit(1)
if __name__=="__main__":main()
