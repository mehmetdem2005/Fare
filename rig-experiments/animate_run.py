"""New cyclic sprint for the *existing* GitHub Fare rig.
Does NOT assume the conversation's 41-bone v6 has the same hierarchy.
Run: blender --background --python rig-experiments/animate_run.py -- --source deliver/mouse_rig.blend --out RunOutput
No automatic weights, no mesh edits; separate run_sprint_v2 action, L3 evaluated-mesh QA.
"""
import argparse
import hashlib
import json
import math
import sys
import traceback
from pathlib import Path
import bpy
from mathutils import Vector

FPS = 24
CYCLE = 24
R = math.radians
TAU = 2 * math.pi

def cli():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--out", required=True)
    return parser.parse_args(sys.argv[sys.argv.index("--")+1:])

def reset_pose(arm):
    for p in arm.pose.bones:
        p.rotation_mode = "XYZ"
        p.location = (0, 0, 0)
        p.rotation_euler = (0, 0, 0)
        p.scale = (1, 1, 1)
    bpy.context.view_layer.update()

def evaluated(mesh):
    graph=bpy.context.evaluated_depsgraph_get()
    obj=mesh.evaluated_get(graph)
    me=obj.to_mesh(preserve_all_data_layers=False, depsgraph=graph)
    try:
        matrix=obj.matrix_world.copy()
        return [tuple(matrix @ v.co) for v in me.vertices]
    finally:
        obj.to_mesh_clear()

def sha(path):
    digest=hashlib.sha256()
    with open(path,"rb") as f:
        for chunk in iter(lambda:f.read(1024*1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def main():
    cfg=cli()
    out=Path(cfg.out).resolve()
    out.mkdir(parents=True,exist_ok=True)
    source=Path(cfg.source).resolve()
    report={"source":str(source), "source_sha256":sha(source),"status":"STARTED",
            "blender":bpy.app.version_string, "action":"run_sprint_v2", "fps":FPS, "frames":CYCLE}
    try:
        bpy.ops.wm.open_mainfile(filepath=str(source))
        meshes=[obj for obj in bpy.data.objects if obj.type=="MESH" and any(mod.type=="ARMATURE" and mod.object for mod in obj.modifiers)]
        if not meshes: raise RuntimeError("No skinned mesh")
        mesh=max(meshes,key=lambda ob:len(ob.data.vertices))
        arm=next(mod.object for mod in mesh.modifiers if mod.type=="ARMATURE" and mod.object)
        B=arm.pose.bones
        required=["hips","neck","head","ik_hand.L","ik_hand.R","ik_foot.L","ik_foot.R"]
        absent=[name for name in required if name not in B]
        if absent: raise RuntimeError("Rig-specific IK controls missing: "+str(absent))
        report["source_rig"]={"bones":len(B),"vertices":len(mesh.data.vertices),"mesh":mesh.name}
        # Do not animate the other 41-bone v6 by mistake.
        if "Fore_Shoulder.L" in B:raise RuntimeError("Unexpected v6 rig: use a dedicated mapping")
        bpy.context.scene.render.fps=FPS
        bpy.context.scene.frame_start=1
        bpy.context.scene.frame_end=CYCLE
        arm.animation_data_create()
        arm.animation_data.action=None
        for track in arm.animation_data.nla_tracks:track.mute=True
        # IK + IKROT constraints must remain enabled for the game-ready rig.
        for side in "LR":
            for nm in ["forearm."+side,"shin."+side]:
                if nm in B:
                    for con in B[nm].constraints:
                        if con.type=="IK" or con.name=="IKROT":con.influence=1.0
            for nm in ["hand."+side,"foot."+side]:
                if nm in B:
                    for con in B[nm].constraints:
                        if con.name=="IKROT":con.influence=1.0
        reset_pose(arm)
        base=evaluated(mesh)
        # Use existing rig convention: translate each IK control in armature-world axes
        # then convert through its rest matrix to pose-bone location.
        inverses={nm:arm.data.bones[nm].matrix_local.to_3x3().inverted()
                  for nm in ["hips","ik_hand.L","ik_hand.R","ik_foot.L","ik_foot.R"]}
        pose_bones=["hips","neck","head"]+[pb.name for pb in B if pb.name.startswith("spine_")]
        pose_bones += [pb.name for pb in B if pb.name.startswith("tail_")]
        pose_bones += [pb.name for pb in B if pb.name.startswith("ear")]
        pose_bones += ["ik_hand.L","ik_hand.R","ik_foot.L","ik_foot.R"]
        pose_bones += [pb.name for pb in B if pb.name.startswith(("toes.","front_toes."))]
        pose_bones=list(dict.fromkeys(pose_bones))
        def rotate(name,x=0.0,y=0.0,z=0.0):
            if name not in B:return
            bone=B[name]
            bone.rotation_euler=(bone.rotation_euler.x+x,bone.rotation_euler.y+y,bone.rotation_euler.z+z)
        def move(name,x=0.0,y=0.0,z=0.0):
            B[name].location=inverses[name]@Vector((x,y,z))
        def step(p,phase,span,lift):
            t=TAU*((p-phase)%1)
            return (span*.5*math.cos(t),lift*max(0,math.sin(t))**1.35)
        def sample(p):
            reset_pose(arm)
            # Paired hind push, delayed paired forelimb touchdown: bounding gait.
            for side,hph,fph in (("L",0.0,.47),("R",.045,.515)):
                hy,hz=step(p,hph,.110,.041)
                fy,fz=step(p,fph,.105,.039)
                move("ik_foot."+side,0.0,hy,hz)
                move("ik_hand."+side,0.0,fy,fz)
                rotate("toes."+side,x=-R(7)*max(0,math.sin(TAU*(p-hph)+2.6)))
                rotate("front_toes."+side,x=-R(8)*max(0,math.sin(TAU*(p-fph)+2.6)))
            flight=max(0.0, math.sin(TAU*p+.75))**2
            bounce=.002+.014*flight
            flex=math.sin(TAU*p+.5)
            move("hips", .0025*math.sin(TAU*p+.3), 0.0, bounce)
            rotate("hips",x=R(4.5)*flex, z=R(1.0)*math.sin(TAU*p))
            spines=[n for n in ("spine_01","spine_02","spine_03","spine_04","spine_05") if n in B]
            prof=[.17,.24,.26,.20,.13][:len(spines)]
            total=sum(prof)
            for name,k in zip(spines,prof):
                rotate(name,x=R(16)*flex*k/total)
            rotate("neck", x=-R(4.8)*flex-R(1.3))
            rotate("head", x=-R(3)*flex+R(.8),z=R(.8)*math.sin(TAU*p+.9))
            for side,lag in (("L",0.0),("R",.55)):
                rotate("ear."+side, x=-R(7)+R(2)*math.sin(TAU*p-lag))
            for i in range(1,7):
                rotate("tail_%02d"%i,
                       x=R(2.6)*math.sin(TAU*p-i*.34)-R(.8),
                       z=R(1.3)*math.sin(TAU*p-i*.48))
        existing=bpy.data.actions.get("run_sprint_v2")
        if existing: bpy.data.actions.remove(existing)
        action=bpy.data.actions.new("run_sprint_v2")
        action.use_fake_user=True
        arm.animation_data.action=action
        frame_positions=[]
        for f in range(1,CYCLE+2):
            p=((f-1)%CYCLE)/CYCLE
            sample(p)
            for name in pose_bones:
                pb=B[name]
                pb.keyframe_insert("rotation_euler",frame=f,group=name)
                pb.keyframe_insert("location",frame=f,group=name)
            bpy.context.scene.frame_set(f)
            bpy.context.view_layer.update()
            coords=evaluated(mesh)
            frame_positions.append(coords)
        # actual cyclic geometric seam, not only identical user-authored keys
        seam=max(math.dist(a,b) for a,b in zip(frame_positions[0],frame_positions[-1]))
        sample(0)
        arm.animation_data.action=action
        bpy.context.scene.frame_set(1)
        bpy.context.view_layer.update()
        errs=[]
        edges=[tuple(e.vertices) for e in mesh.data.edges][::3]
        for coords in frame_positions[:-1]:
            strains=[]
            for a,b in edges:
                den=math.dist(base[a],base[b])
                if den>1e-7:strains.append(abs(math.dist(coords[a],coords[b])/den-1))
            strains.sort()
            errs.append(strains[int(.95*(len(strains)-1))] if strains else 0)
        movement=max(math.dist(a,b) for a,b in zip(frame_positions[0],frame_positions[6]))
        report["qa"]={"engine":"ACTUAL_BLENDER_DEPSGRAPH", "evaluated_frames":CYCLE+1,
                      "loop_vertex_seam_max":seam,"mesh_movement_quarter_cycle":movement,
                      "edge_stretch_p95_worst_frame":max(errs),
                      "edge_stretch_p95_mean":sum(errs)/len(errs),
                      "bone_names_keyed":pose_bones}
        if seam>1e-4:raise RuntimeError("Loop seam fails: "+str(seam))
        if movement<.003:raise RuntimeError("Movement too small: "+str(movement))
        if max(errs)>1.0:raise RuntimeError("Excessive 95th percentile stretch: "+str(max(errs)))
        # Save a new .blend without overwriting the original.
        blend_out=out/"mouse_run_sprint_v2.blend"
        bpy.ops.file.pack_all()
        bpy.ops.wm.save_as_mainfile(filepath=str(blend_out),compress=True)
        report["blend"]=blend_out.name
        report["blend_sha256"]=sha(blend_out)
        # Animated GLB. Query exporter capabilities instead of assuming enum values.
        glb=out/"mouse_run_sprint_v2.glb"
        bpy.context.view_layer.objects.active=mesh
        settings={"filepath":str(glb),"export_format":"GLB","export_animations":True,
                  "export_skins":True,"export_def_bones":True,"export_cameras":False,
                  "export_lights":False,"export_yup":True}
        prop=bpy.ops.export_scene.gltf.get_rna_type().properties.get("export_animation_mode")
        if prop:
            ids=[i.identifier for i in prop.enum_items]
            settings["export_animation_mode"]="ACTIVE_ACTIONS" if "ACTIVE_ACTIONS" in ids else ("ACTIONS" if "ACTIONS" in ids else ids[0])
        bpy.ops.export_scene.gltf(**settings)
        # Independently parse the GLB animation chunk and assert exported action exists.
        import struct
        buf=glb.read_bytes()
        if buf[:4]!=b"glTF":raise RuntimeError("Invalid GLB")
        offset=12
        gltf=None
        while offset+8<=len(buf):
            length,typ=struct.unpack_from("<II",buf,offset)
            chunk=buf[offset+8:offset+8+length]
            if typ==0x4E4F534A:gltf=json.loads(chunk)
            offset+=8+length
        if not gltf:raise RuntimeError("GLB missing JSON chunk")
        anim_names=[a.get("name","") for a in gltf.get("animations",[])]
        report["glb_animations"]=anim_names
        if not any("run_sprint_v2" in a for a in anim_names):
            # Blender 5.1's ACTIVE_ACTIONS exporter may name a single valid clip
            # "Animation", even though it contains the new action's 124 channels.
            # Relabel only the JSON animation name, preserving binary samples.
            if len(gltf.get("animations",[]))!=1 or len(gltf["animations"][0].get("channels",[]))<10:
                raise RuntimeError("Expected an actual, nonempty sprint clip: "+repr(anim_names))
            gltf["animations"][0]["name"]="run_sprint_v2"
            encoded=json.dumps(gltf,separators=(",",":"),ensure_ascii=False).encode("utf-8")
            encoded+=b" "*((-len(encoded))%4)
            parts=[]
            offset=12
            while offset+8<=len(buf):
                length,typ=struct.unpack_from("<II",buf,offset)
                chunk=buf[offset+8:offset+8+length]
                if typ==0x4E4F534A:chunk=encoded
                parts.append(struct.pack("<II",len(chunk),typ)+chunk)
                offset+=8+length
            new_length=12+sum(map(len,parts))
            glb.write_bytes(b"glTF"+struct.pack("<II",2,new_length)+b"".join(parts))
            anim_names=["run_sprint_v2"]
        report["glb_animations"]=anim_names
        report["glb_channel_count"]=len(gltf["animations"][0]["channels"])
        report["glb"]=glb.name
        report["glb_sha256"]=sha(glb)
        report["preview_frames"]=0
        report["status"]="PASS"
    except Exception as ex:
        report["status"]="FAIL"
        report["error"]=str(ex)
        report["traceback"]=traceback.format_exc()
    (out/"run_qa.json").write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
    print("RUN_SPRINT_STATUS",report["status"])
    print("RUN_SPRINT_REPORT",json.dumps({k:v for k,v in report.items() if k not in ("traceback",)},ensure_ascii=False))
    if report["status"]!="PASS":raise SystemExit(1)

if __name__=="__main__":
    main()
