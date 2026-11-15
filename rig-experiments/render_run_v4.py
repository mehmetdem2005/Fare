"""Render the saved sprint in Blender Workbench, separately from the GLB build.
The build and L3 validation remain valid even if software OpenGL is unavailable.
"""
import argparse
import json
import sys
from pathlib import Path
import bpy
from mathutils import Vector

def cli():
    p=argparse.ArgumentParser()
    p.add_argument("--source",required=True)
    p.add_argument("--out",required=True)
    return p.parse_args(sys.argv[sys.argv.index("--")+1:])

def main():
    c=cli()
    root=Path(c.out).resolve();root.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(Path(c.source).resolve()))
    action=bpy.data.actions.get("run_sprint_v4")
    if not action:raise RuntimeError("run_sprint_v4 action missing")
    mesh=max([o for o in bpy.data.objects if o.type=="MESH" and any(m.type=="ARMATURE" and m.object for m in o.modifiers)],key=lambda o:len(o.data.vertices))
    arm=next(m.object for m in mesh.modifiers if m.type=="ARMATURE" and m.object)
    arm.animation_data_create()
    arm.animation_data.action=action
    if arm.animation_data:
        for track in arm.animation_data.nla_tracks:track.mute=True
    vertices=[mesh.matrix_world @ Vector(corner) for corner in mesh.bound_box]
    mid=sum(vertices,Vector((0,0,0)))/8
    width=max(max(v.y for v in vertices)-min(v.y for v in vertices),max(v.z for v in vertices)-min(v.z for v in vertices))
    camdata=bpy.data.cameras.new("RunPreview_Ortho")
    camera=bpy.data.objects.new("RunPreview_Ortho",camdata)
    bpy.context.scene.collection.objects.link(camera)
    camera.location=mid+Vector((width*1.7,-width*.70,width*.60))
    camera.rotation_euler=(mid-camera.location).to_track_quat("-Z","Y").to_euler()
    camdata.type="ORTHO";camdata.ortho_scale=width*1.6
    scene=bpy.context.scene;scene.camera=camera
    scene.render.engine="BLENDER_WORKBENCH"
    scene.display.shading.light="STUDIO"
    scene.display.shading.color_type="MATERIAL"
    scene.display.shading.show_shadows=True
    scene.render.resolution_x=640
    scene.render.resolution_y=420
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format="PNG"
    frame_folder=root/"preview_frames";frame_folder.mkdir(exist_ok=True)
    for i,f in enumerate(range(1,25,2)):
        scene.frame_set(f)
        scene.render.filepath=str(frame_folder/("frame_%02d.png"%i))
        bpy.ops.render.render(write_still=True)
    (root/"preview_qa.json").write_text(json.dumps({"status":"PASS","frames_rendered":12,"engine":"BLENDER_WORKBENCH","source":str(c.source)},indent=2))
    print("SPRINT_PREVIEW_RENDERED=12")

if __name__=="__main__":
    main()
