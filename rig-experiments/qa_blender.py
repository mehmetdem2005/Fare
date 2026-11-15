"""Headless Blender runtime QA for mouse rig; NO automatic weights."""
import bpy, json, math, argparse, sys, traceback, hashlib
from pathlib import Path

def args():
    p=argparse.ArgumentParser()
    p.add_argument("--source", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--full", action="store_true")
    return p.parse_args(sys.argv[sys.argv.index("--")+1:])

def sha(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for x in iter(lambda:f.read(1024*1024),b""):h.update(x)
    return h.hexdigest()

def reset(arm):
    for p in arm.pose.bones:
        p.rotation_mode="QUATERNION"
        p.matrix_basis.identity()
    bpy.context.view_layer.update()

def eval_mesh(obj):
    deps=bpy.context.evaluated_depsgraph_get()
    ev=obj.evaluated_get(deps)
    mesh=ev.to_mesh(preserve_all_data_layers=False,depsgraph=deps)
    try:
        mat=ev.matrix_world.copy()
        return [tuple(mat@v.co) for v in mesh.vertices]
    finally:ev.to_mesh_clear()

def groupweight(group,index):
    try:return group.weight(index)
    except RuntimeError:return 0.0

def region(mesh,options):
    for parts in options:
        groups=[mesh.vertex_groups.get(name) for name in parts]
        if any(g is None for g in groups):continue
        ids=[v.index for v in mesh.data.vertices if sum(groupweight(g,v.index) for g in groups)>.6]
        if len(ids)>100:return ids
    return []

def audit(arm,mesh,full=False):
    reset(arm)
    rest=eval_mesh(mesh)
    if len(rest)!=len(mesh.data.vertices):raise RuntimeError("Evaluated mesh vertex count changed; cannot compare vertex IDs")
    head=region(mesh,[["Head","Muzzle"],["head","snout"],["Head"],["head"]])
    names=[p.name for p in arm.pose.bones if p.bone.use_deform and (p.name.lower().startswith("spine") or p.name.lower().startswith("fore_") or p.name.lower().startswith(("shoulder.","upper_arm.","forearm.","hand.","front_toes.")))]
    if not names:raise RuntimeError("No forelimb or spine pose bones identified")
    # Never truncate the bone list: distal spine bones must not replace forelimb tests.
    angles=[-45,-30,-15,15,30,45] if full else [-30,15,30]
    edges=[tuple(e.vertices) for e in mesh.data.edges][::2]
    results=[]
    for name in names:
        for axis in ("X","Z"):
            for degree in angles:
                reset(arm)
                pb=arm.pose.bones[name]
                pb.rotation_mode="XYZ"
                pb.rotation_euler["XYZ".index(axis)]=math.radians(degree)
                bpy.context.view_layer.update()
                moved=eval_mesh(mesh)
                strains=[]
                for a,b in edges:
                    before=math.dist(rest[a],rest[b])
                    if before>1e-7:strains.append(abs(math.dist(moved[a],moved[b])/before-1))
                strains.sort()
                hmax=max((math.dist(rest[i],moved[i]) for i in head),default=0.0)
                results.append(dict(bone=name,axis=axis,degree=degree,head_max_displacement=hmax,
                                    edge_p95=strains[int(.95*(len(strains)-1))] if strains else None))
    reset(arm)
    return dict(engine="ACTUAL_BLENDER_DEPSGRAPH",head_roi_count=len(head),test_count=len(results),poses=results)



def distributed_spine_tests(arm,mesh):
    """Apply the SAME total intended bending angle across available spine segments."""
    reset(arm)
    baseline=eval_mesh(mesh)
    segments=[p.name for p in arm.pose.bones if p.bone.use_deform and p.name.lower().startswith("spine")]
    if len(segments)<3:raise RuntimeError("Not enough deform spine segments")
    edges=[tuple(e.vertices) for e in mesh.data.edges][::2]
    groups=[mesh.vertex_groups.get(n) for n in segments]
    groups=[g for g in groups if g]
    core=[v.index for v in mesh.data.vertices if sum(groupweight(g,v.index) for g in groups)>.50]
    output=[]
    for axis in ("X","Z"):
        for bend in (-30,-15,15,30):
            reset(arm)
            for name in segments:
                pb=arm.pose.bones[name]
                pb.rotation_mode="XYZ"
                pb.rotation_euler["XYZ".index(axis)]=math.radians(bend/len(segments))
            bpy.context.view_layer.update()
            moved=eval_mesh(mesh)
            strains=[]
            for a,b in edges:
                old=math.dist(baseline[a],baseline[b])
                if old>1e-7:strains.append(abs(math.dist(moved[a],moved[b])/old-1))
            strains.sort()
            center_disp=[math.dist(baseline[i],moved[i]) for i in core]
            output.append({"axis":axis,"intended_total_degrees":bend,"segment_count":len(segments),
                           "spine_core_count":len(core),
                           "edge_p95":strains[int(.95*(len(strains)-1))] if strains else None,
                           "edge_p99":strains[int(.99*(len(strains)-1))] if strains else None,
                           "spine_core_mean_displacement":sum(center_disp)/len(center_disp) if center_disp else 0})
    reset(arm)
    return output


def combined_pose_tests(arm,mesh):
    """Real depsgraph check of 8 controlled multi-joint examples."""
    reset(arm)
    baseline=eval_mesh(mesh)
    head=region(mesh,[["Head","Muzzle"],["head","snout"],["Head"],["head"]])
    edges=[tuple(e.vertices) for e in mesh.data.edges][::2]
    def find(*names):
        return next((n for n in names if n in arm.pose.bones),None)
    Ls=find("Fore_Shoulder.L","shoulder.L")
    Rs=find("Fore_Shoulder.R","shoulder.R")
    Lu=find("Fore_UpperArm.L","upper_arm.L")
    Ru=find("Fore_UpperArm.R","upper_arm.R")
    Lf=find("Fore_Forearm.L","forearm.L")
    Rf=find("Fore_Forearm.R","forearm.R")
    Lw=find("Fore_Wrist.L","hand.L")
    Rw=find("Fore_Wrist.R","hand.R")
    s2=find("Spine_02","spine_02")
    s3=find("Spine_03","spine_03")
    s4=find("Spine_04","spine_04")
    s5=find("Spine_05","spine_05")
    def form(*motions):
        return [(b,axis,angle) for b,axis,angle in motions if b is not None]
    cases=[
        ("left_shoulder_elbow", form((Ls,"X",15),(Lu,"X",-25))),
        ("right_shoulder_elbow",form((Rs,"X",-15),(Ru,"X",25))),
        ("left_elbow_wrist",form((Lf,"X",30),(Lw,"X",-20))),
        ("right_elbow_wrist",form((Rf,"X",-30),(Rw,"X",20))),
        ("both_shoulders",form((Ls,"Z",15),(Rs,"Z",-15))),
        ("spine_shoulder",form((s4,"X",15),(Ls,"X",15))),
        ("spine_wave",form((s2,"X",8),(s3,"X",-12),(s4,"X",12),(s5,"X",-8))),
        ("spine_lateral",form((s3,"Z",12),(s5,"Z",-12)))
    ]
    results=[]
    for label,motions in cases:
        reset(arm)
        for bone,axis,degree in motions:
            pose=arm.pose.bones[bone]
            pose.rotation_mode="XYZ"
            pose.rotation_euler["XYZ".index(axis)]=math.radians(degree)
        bpy.context.view_layer.update()
        coordinates=eval_mesh(mesh)
        lengths=[]
        for a,b in edges:
            old=math.dist(baseline[a],baseline[b])
            if old>1e-7:lengths.append(abs(math.dist(coordinates[a],coordinates[b])/old-1))
        lengths.sort()
        hmax=max((math.dist(baseline[i],coordinates[i]) for i in head),default=0.0)
        results.append({"case":label,"bones":motions,"head_max":hmax,
                        "edge_p95":lengths[int(.95*(len(lengths)-1))] if lengths else None})
    reset(arm)
    return results


def spine_split(arm,mesh,targets):
    before=[sum(x.weight for x in v.groups) for v in mesh.data.vertices]
    map_to_arm=arm.matrix_world.inverted()@mesh.matrix_world
    data={name:(arm.data.bones[name].head_local.copy(),arm.data.bones[name].tail_local.copy()) for name in targets}
    bpy.context.view_layer.objects.active=arm
    if bpy.context.object.mode!="OBJECT":bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.mode_set(mode="EDIT")
    try:
        eb=arm.data.edit_bones
        for name in targets:
            old=eb[name]
            h,t=data[name];m=h.lerp(t,.5)
            children=[(c,c.head.copy(),c.tail.copy(),c.roll,c.use_connect) for c in old.children]
            for child,*_ in children:child.use_connect=False
            old.tail=m
            new=eb.new(name+"_Distal")
            new.head=m;new.tail=t;new.roll=old.roll
            new.parent=old;new.use_connect=True;new.use_deform=True
            for child,ch,ct,roll,connected in children:
                child.parent=new;child.use_connect=False
                child.head=ch;child.tail=ct;child.roll=roll
                if connected and (ch-t).length<1e-5:child.use_connect=True
    finally:bpy.ops.object.mode_set(mode="OBJECT")
    for name,(h,t) in data.items():
        old=mesh.vertex_groups[name];new=mesh.vertex_groups.new(name=name+"_Distal")
        u=t-h;den=u.length_squared
        for vert in mesh.data.vertices:
            w=groupweight(old,vert.index)
            if w<=1e-8:continue
            f=max(0.,min(1.,(((map_to_arm@vert.co)-h).dot(u)/den-.33)/.34))
            smooth=f*f*(3-2*f)
            old.add([vert.index],w*(1-smooth),"REPLACE")
            if smooth>1e-8:new.add([vert.index],w*smooth,"REPLACE")
    after=[sum(x.weight for x in v.groups) for v in mesh.data.vertices]
    delta=max(abs(x-y) for x,y in zip(before,after))
    if delta>1e-5:raise RuntimeError("Vertex weight total not conserved: "+str(delta))
    return delta

def main():
    cfg=args();out=Path(cfg.out);out.mkdir(parents=True,exist_ok=True)
    source=Path(cfg.source).resolve()
    report=dict(source=str(source),sha256=sha(source),blender=bpy.app.version_string,status="STARTED")
    try:
        bpy.ops.wm.open_mainfile(filepath=str(source))
        meshes=[o for o in bpy.data.objects if o.type=="MESH" and any(m.type=="ARMATURE" and m.object for m in o.modifiers)]
        if not meshes:raise RuntimeError("No skinned mesh")
        mesh=max(meshes,key=lambda o:len(o.data.vertices))
        arm=next(m.object for m in mesh.modifiers if m.type=="ARMATURE" and m.object)
        if arm.animation_data:
            arm.animation_data.action=None
            for tr in arm.animation_data.nla_tracks:tr.mute=True
        arm.data.pose_position="POSE"
        reset(arm)
        report["structure"]=dict(vertices=len(mesh.data.vertices),bones=len(arm.data.bones),groups=len(mesh.vertex_groups),
                                 names=[b.name for b in arm.data.bones if "spine" in b.name.lower()])
        report["baseline"]=audit(arm,mesh,cfg.full)
        report["baseline_combined"]=combined_pose_tests(arm,mesh)
        report["baseline_distributed_spine"]=distributed_spine_tests(arm,mesh)
        is_v6=all(n in arm.data.bones for n in ["Spine_01","Spine_02","Spine_03","Spine_04","Spine_05"])
        repo_schema=all(n in arm.data.bones for n in ["spine_01","spine_02","spine_03","spine_04","spine_05"])
        report["input_kind"]="v6_conversation_schema" if is_v6 else "DIFFERENT_GITHUB_FARE_RIG"
        report["production_approval"]=False
        base_bone_count=len(arm.data.bones)
        if is_v6 or repo_schema:
            prefix="Spine_" if is_v6 else "spine_"
            report["candidates"]=[]
            for label,targets in [("spine7",[prefix+"04",prefix+"05"]),("spine9",[prefix+"02",prefix+"03",prefix+"04",prefix+"05"])]:
                candidate=dict(name=label,status="FAILED",input_kind=report["input_kind"],production_approval=False)
                try:
                    bpy.ops.wm.open_mainfile(filepath=str(source))
                    mesh=max((o for o in bpy.data.objects if o.type=="MESH" and any(m.type=="ARMATURE" for m in o.modifiers)),key=lambda o:len(o.data.vertices))
                    arm=next(m.object for m in mesh.modifiers if m.type=="ARMATURE" and m.object)
                    saved_action=arm.animation_data.action if arm.animation_data else None
                    saved_mutes=[(tr,tr.mute) for tr in arm.animation_data.nla_tracks] if arm.animation_data else []
                    if arm.animation_data:
                        arm.animation_data.action=None
                        for tr in arm.animation_data.nla_tracks:tr.mute=True
                    arm.data.pose_position="POSE";reset(arm)
                    rest=eval_mesh(mesh)
                    candidate["weight_sum_delta"]=spine_split(arm,mesh,targets)
                    if len(arm.data.bones)!=base_bone_count+len(targets):raise RuntimeError("Invalid post-split bone count")
                    if is_v6:
                        for side in ("L","R"):
                            if arm.data.bones["Fore_Shoulder."+side].parent.name!="Spine_04_Distal":
                                raise RuntimeError("Wrong shoulder parent "+side)
                    actual=eval_mesh(mesh)
                    deviation=max(math.dist(a,b) for a,b in zip(rest,actual))
                    candidate["rest_max_deviation"]=deviation
                    if deviation>1e-5:raise RuntimeError("Rest changed by split")
                    candidate["tests"]=audit(arm,mesh,cfg.full)
                    candidate["combined_tests"]=combined_pose_tests(arm,mesh)
                    candidate["distributed_spine_tests"]=distributed_spine_tests(arm,mesh)
                    new_names=[n+"_Distal" for n in targets]
                    tested={r["bone"] for r in candidate["tests"]["poses"]}
                    candidate["added_bones_tested"]=sorted(set(new_names)&tested)
                    if len(candidate["added_bones_tested"])!=len(new_names):raise RuntimeError("New distal bone not individually tested")
                    reset(arm)
                    if arm.animation_data:
                        arm.animation_data.action=saved_action
                        for track,old_state in saved_mutes:track.mute=old_state
                    path=out/(label+"_EXPERIMENT.blend")
                    bpy.ops.wm.save_as_mainfile(filepath=str(path),compress=True)
                    # Blender must be able to reopen the artifact, not just write bytes
                    bpy.ops.wm.open_mainfile(filepath=str(path))
                    check_arm=next(o for o in bpy.data.objects if o.type=="ARMATURE")
                    if len(check_arm.data.bones)!=base_bone_count+len(targets):raise RuntimeError("Reopened model has wrong bone count")
                    if any(n not in check_arm.data.bones for n in new_names):raise RuntimeError("Reopened file missing new distal bone")
                    candidate["saved_reopen_verified"]=True
                    candidate["output"]=path.name
                    candidate["sha256"]=sha(path)
                    candidate["status"]="L3_TESTED_CANDIDATE"
                except Exception as exc:
                    candidate["error"]=str(exc);candidate["traceback"]=traceback.format_exc()
                report["candidates"].append(candidate)
                (out/(label+".json")).write_text(json.dumps(candidate,indent=2),encoding="utf8")
            report["status"]="CANDIDATES_EVALUATED"
        else:report["status"]="L3_BASELINE_ONLY_NOT_V6"
    except Exception as exc:
        report["status"]="FAILED";report["error"]=str(exc);report["traceback"]=traceback.format_exc()
    finally:
        (out/"qa_summary.json").write_text(json.dumps(report,indent=2),encoding="utf8")
        print("FINAL_STATUS",report["status"])
    if report["status"]=="FAILED":raise SystemExit(2)
    if report["status"]=="CANDIDATES_EVALUATED" and not any(c["status"]=="L3_TESTED_CANDIDATE" for c in report["candidates"]):raise SystemExit(3)

if __name__=="__main__":main()
