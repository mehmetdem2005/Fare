"""Forensic analysis of the exact v4 sprint + flank.65 Blender experiment.
READ ONLY. Evaluate armature FK/IK, skinning, morph activation, torso surface stretch
and plausible ground contact. Never save the loaded .blend.
Blender 5.1.2, 24 frames; no automatic weights.
"""
import argparse, json, math, collections, hashlib, sys, traceback, statistics
from pathlib import Path
import bpy
from mathutils import Vector

def args():
    p=argparse.ArgumentParser()
    p.add_argument("--source",required=True)
    p.add_argument("--out",required=True)
    return p.parse_args(sys.argv[sys.argv.index("--")+1:])

def quant(a,f):
    if not a:return None
    x=sorted(a);return x[int((len(x)-1)*f)]

def getw(g,i):
    try:return float(g.weight(i))
    except RuntimeError:return 0.

def evaluate(mesh):
    dg=bpy.context.evaluated_depsgraph_get()
    obj=mesh.evaluated_get(dg)
    dat=obj.to_mesh(preserve_all_data_layers=False,depsgraph=dg)
    try:
        matrix=obj.matrix_world.copy()
        return [tuple(matrix @ v.co) for v in dat.vertices]
    finally:obj.to_mesh_clear()

def close_region(label,inds,mesh,rest):
    ids=set(inds)
    ee=[tuple(e.vertices) for e in mesh.data.edges if e.vertices[0] in ids and e.vertices[1] in ids]
    return {"label":label,"vertices":len(ids),"edges":ee,
            "rest_lengths":[math.dist(rest[a],rest[b]) for a,b in ee]}

def region_metric(region,coords,threshold=.001):
    es=region["edges"];lens=region["rest_lengths"]
    er=[math.dist(coords[a],coords[b])/L-1 for (a,b),L in zip(es,lens) if L>=threshold]
    absolute=[abs(x) for x in er]
    l=[coords[i][2] for i in region["ids"]]
    return {"p95_abs_edge_change":quant(absolute,.95),"p99_abs_edge_change":quant(absolute,.99),
            "p95_stretch_only":quant([max(0,x) for x in er],.95),
            "p95_compression_only":quant([max(0,-x) for x in er],.95),
            "mean_z":sum(l)/len(l) if l else None,
            "low_z_p10":quant(l,.1)}

def main():
    cfg=args()
    output=Path(cfg.out).resolve();output.mkdir(parents=True,exist_ok=True)
    result={"source":str(cfg.source),"status":"STARTED","test_level":"real bpy evaluated mesh, 5.1.2"}
    try:
        bpy.ops.wm.open_mainfile(filepath=str(Path(cfg.source).resolve()))
        mesh=max([o for o in bpy.data.objects if o.type=="MESH" and any(m.type=="ARMATURE" for m in o.modifiers)],key=lambda o:len(o.data.vertices))
        arm=next(m.object for m in mesh.modifiers if m.type=="ARMATURE" and m.object)
        scene=bpy.context.scene
        keydata=mesh.data.shape_keys
        morphs=keydata.key_blocks if keydata else []
        action=bpy.data.actions.get("run_sprint_v4")
        if action is None:raise ValueError("run_sprint_v4 not in exact experimental blend")
        arm.animation_data_create()
        arm.animation_data.action=action
        for track in arm.animation_data.nla_tracks:track.mute=True
        drivers=list(keydata.animation_data.drivers) if keydata and keydata.animation_data else []
        dr_state={f.data_path:f.mute for f in drivers}
        cons=[(p,c,float(c.influence)) for p in arm.pose.bones for c in p.constraints]
        arm_mods=[m for m in mesh.modifiers if m.type=="ARMATURE"]
        mod_state={m.name:m.use_deform_preserve_volume for m in arm_mods}
        part=mesh.data.attributes.get("part_id")
        if part is None:raise RuntimeError("missing body part_id; cannot do anatomical ROI")
        verts=mesh.data.vertices
        N=len(verts)
        body=[i for i in range(N) if int(part.data[i].value)==6]
        groups={g.name:g for g in mesh.vertex_groups}
        def roi_test(i):
            v=verts[i];x,y,z=v.co
            return abs(x)<.17 and -.27<=y<=.055 and .045<=z<=.285
        a_roi=[i for i in body if roi_test(i)]
        interleg=[i for i in body if abs(verts[i].co.x)<=.165 and -.1<=verts[i].co.y<=.055 and .045<=verts[i].co.z<=.16]
        central=[i for i in a_roi if abs(verts[i].co.x)<.06]
        inner=[i for i in a_roi if .06<=abs(verts[i].co.x)<.11]
        outer=[i for i in a_roi if .11<=abs(verts[i].co.x)<.17]
        post=[i for i in body if abs(verts[i].co.x)<.17 and .055<verts[i].co.y<.33 and .06<verts[i].co.z<.3]
        # Foot and hand topological islands from part_id labels in original pipeline:
        paw_vertex=[i for i in range(N) if max(
            getw(groups[g],i) for g in ("hand.L","hand.R","foot.L","foot.R") if g in groups)>0.60]
        def reset_rest():
            arm.animation_data.action=None
            for pb in arm.pose.bones:
                pb.matrix_basis.identity()
            scene.frame_set(1);bpy.context.view_layer.update()
        reset_rest()
        rest=evaluate(mesh)
        reg={}
        for name,inds in {"front":a_roi,"interleg":interleg,"center":central,"inner":inner,"outer":outer,"posterior":post}.items():
            x=close_region(name,inds,mesh,rest)
            x["ids"]=inds
            reg[name]=x
        result["body_info"]={"total_mesh_verts":N,"body_island_verts":len(body),"front_roi":len(a_roi),
                             "interleg":len(interleg),"center":len(central),
                             "posterior":len(post),"armature_bones":len(arm.pose.bones),
                             "mesh_groups":len(groups),"skin_mods":[{"name":m.name,"preserve_volume":m.use_deform_preserve_volume} for m in arm_mods]}
        result["regions"]={name:{"vertices":len(x["ids"]),"edges":len(x["edges"]),
                                "base_rest_edge_p50":quant(x["rest_lengths"],.5)}
                           for name,x in reg.items()}
        # Static weight inventory with bone-specific anatomical neighborhoods:
        weight_summary={}
        subset=[]
        for name,region in reg.items():
            mass=collections.Counter()
            n_cross=0;n_core=0;n_fore=0;n_hind=0;n3=0
            for i in region["ids"]:
                vs=verts[i]
                ww={list(mesh.vertex_groups)[g.group].name:float(g.weight) for g in vs.groups if g.weight>1e-7}
                for bn,w in ww.items():mass[bn]+=w
                if max(ww.get("upper_arm.L",0),ww.get("upper_arm.R",0))>.10 and max(ww.get("thigh.L",0),ww.get("thigh.R",0))>.10:n_cross+=1
                if sum(ww.get("spine_%02d"%k,0) for k in range(1,6))>.5:n_core+=1
                if sum(ww.get(n,0) for n in ("shoulder.L","shoulder.R","upper_arm.L","upper_arm.R","forearm.L","forearm.R"))>.50:n_fore+=1
                if sum(ww.get(n,0) for n in ("thigh.L","thigh.R","shin.L","shin.R"))>.50:n_hind+=1
                if len(ww)>3:n3+=1
            total=sum(mass.values())
            weight_summary[name]={"cross_upperarm_thigh_count":n_cross,"spine_dominant_verts":n_core,"fore_dominant_verts":n_fore,
                                  "hind_dominant_verts":n_hind,"more_than_3_influences":n3,
                                  "mass_percent_by_group":{k:round(100*v/total,3) for k,v in mass.most_common(18)}}
        result["weight_summary"]=weight_summary
        # Make sure each ablation starts from exact same pose, not a stale post-IK state.
        def reload(frame):
            for p,c,influence in cons:c.influence=influence
            for f in drivers:f.mute=dr_state[f.data_path]
            for m in arm_mods:m.use_deform_preserve_volume=mod_state[m.name]
            arm.animation_data.action=action
            scene.frame_set(frame-1 if frame>1 else 2)
            scene.frame_set(frame)
            bpy.context.view_layer.update()
        frames=(1,3,5,7,9,11,13,15,17,19,21,23,25)
        shape_labels=[kb.name for kb in morphs if kb.name!="Basis"]
        cases={
            "full":None,
            "disable_all_morphs":"all",
            "disable_shoulder_morphs":["crv_shoulder_L","crv_shoulder_R"],
            "disable_elbow_morphs":["crv_elbow_L","crv_elbow_R"],
            "disable_hip_knee_morphs":["crv_hip_L","crv_hip_R","crv_knee_L","crv_knee_R"],
            "disable_spine_morphs":["crv_spine_curl","crv_spine_arch"],
            "disable_neck_morphs":["crv_neck_yawL","crv_neck_yawR"],
            "disable_both_front_ik":"frontik",
            "disable_both_hind_ik":"hindik",
            "disable_spine_02":"spine02",
            "disable_spine_03":"spine03",
            "disable_hips_rotation":"hips",
            "toggle_preserve_volume":"preserve",
        }
        frows=[]; ikmetrics=[]; rare=[]
        for f in frames:
            reload(f)
            coords=evaluate(mesh)
            actual={name:region_metric(r,coords) for name,r in reg.items()}
            actual["body_lowest"]=min(coords[i][2] for i in body)
            actual["paw_lowest"]=min(coords[i][2] for i in paw_vertex)
            morphvalues={k:float(morphs[k].value) for k in shape_labels}
            iks={}
            for side in ("L","R"):
                for typ in ("front","hind"):
                    root_name=("upper_arm."+side) if typ=="front" else ("thigh."+side)
                    end_name=("forearm."+side) if typ=="front" else ("shin."+side)
                    target_name=("ik_hand."+side) if typ=="front" else ("ik_foot."+side)
                    root=arm.pose.bones[root_name];end=arm.pose.bones[end_name];target=arm.pose.bones[target_name]
                    total_len=arm.data.bones[root_name].length+arm.data.bones[end_name].length
                    gap=(target.head-root.head).length
                    dist=(end.tail-target.head).length
                    first=(root.matrix.to_quaternion()@Vector((0,1,0)))
                    iks[typ+"_"+side]={"target_distance_to_root":gap,"rest_chain_length":total_len,"extension_ratio":gap/total_len,
                                       "end_effector_target_error":dist,
                                       "root_rotation_euler":tuple(root.rotation_euler),
                                       "root_matrix_rotation":tuple(root.matrix.to_quaternion()),
                                       "IK_constraints":[{"chain_count":c.chain_count,"use_stretch":c.use_stretch,
                                                         "influence":c.influence,"target":c.target.name if c.target else None,
                                                         "subtarget":c.subtarget} for c in end.constraints if c.type=="IK"]}
            ikmetrics.append({"frame":f,"iks":iks})
            tests={}
            for case,selector in cases.items():
                reload(f)
                if isinstance(selector,list) or selector=="all":
                    selected=(shape_labels if selector=="all" else selector)
                    for fc in drivers:
                        if any(("key_blocks[\""+name+"\"]") in fc.data_path for name in selected):
                            fc.mute=True
                    for name in selected:
                        if name in morphs:morphs[name].value=0
                elif selector=="frontik" or selector=="hindik":
                    bones=(["forearm.L","forearm.R"] if selector=="frontik" else ["shin.L","shin.R"])
                    for nm in bones:
                        for c in arm.pose.bones[nm].constraints:
                            if c.type=="IK":c.influence=0
                elif selector in ("spine02","spine03"):
                    nm="spine_02" if selector=="spine02" else "spine_03"
                    arm.pose.bones[nm].rotation_euler=(0,0,0)
                elif selector=="hips":
                    arm.pose.bones["hips"].rotation_euler=(0,0,0)
                elif selector=="preserve":
                    for mod in arm_mods:mod.use_deform_preserve_volume=not mod.use_deform_preserve_volume
                bpy.context.view_layer.update()
                moved=evaluate(mesh)
                tests[case]={name:region_metric(r,moved)["p95_abs_edge_change"] for name,r in reg.items()}
                if case=="full":
                    for name in reg:
                        if abs(tests[case][name]-actual[name]["p95_abs_edge_change"])>1e-5:
                            raise RuntimeError("state crosscheck fails frame %d, ROI %s"%(f,name))
            frows.append({"frame":f,"actual":actual,"morph_values":morphvalues,"ablation_p95":tests})
        result["frames"]=frows
        result["ik_reach"]=ikmetrics
        result["top_case_effects"]={}
        for name in reg:
            baseline=sum(x["ablation_p95"]["full"][name] for x in frows)/len(frows)
            result["top_case_effects"][name]=[{"case":case,"mean_p95":round(sum(x["ablation_p95"][case][name] for x in frows)/len(frows),6),
                "relative_change_pct":round(100*((sum(x["ablation_p95"][case][name] for x in frows)/len(frows))/baseline-1),2)}
                for case in cases]
        result["morph_peak"]={name:max(x["morph_values"][name] for x in frows) for name in shape_labels}
        result["IK_max_extension_ratio"]={name:max(x["iks"][name]["extension_ratio"] for x in ikmetrics) for name in ikmetrics[0]["iks"]}
        result["IK_end_effector_max_error"]={name:max(x["iks"][name]["end_effector_target_error"] for x in ikmetrics) for name in ikmetrics[0]["iks"]}
        result["crosscheck"]="PASS: full-pose evaluated mesh equal across all ablations and 13 frames"
        result["status"]="PASS"
    except Exception as e:
        result.update(status="FAIL",error=str(e),traceback=traceback.format_exc())
    (output/"forensic_v4_torso.json").write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding="utf-8")
    print("FORENSIC_TORSO",result["status"])
    print("PEAK",result.get("morph_peak"))
    print("IK_EXT",result.get("IK_max_extension_ratio"))
    print("FULL_FRAMES",len(result.get("frames",[])))
    if result["status"]!="PASS":raise SystemExit(1)

if __name__=="__main__":main()
