"""Blender 5.1: root-cause audit of sprint v3 anterior abdomen/axilla.
Read-only: no mesh, rig, weights, shape keys, actions or source files are saved.
Check *all* bone weights and high-strain edges jointly with parent/IK motion.
"""
import bpy, json, math, sys, argparse, traceback, collections, statistics
from pathlib import Path
from mathutils import Vector

def args():
    p=argparse.ArgumentParser()
    p.add_argument("--source",required=True)
    p.add_argument("--out",required=True)
    return p.parse_args(sys.argv[sys.argv.index("--")+1:])

def val(g,i):
    try:return g.weight(i)
    except RuntimeError:return 0.

def pts(obj):
    dg=bpy.context.evaluated_depsgraph_get()
    ev=obj.evaluated_get(dg);me=ev.to_mesh(preserve_all_data_layers=False,depsgraph=dg)
    try:
        mat=ev.matrix_world.copy()
        return [tuple(mat@v.co) for v in me.vertices]
    finally:
        ev.to_mesh_clear()

def quant(a,p):
    if not a:return 0.
    b=sorted(a);return b[int((len(b)-1)*p)]

def main():
    a=args();out=Path(a.out).resolve();out.mkdir(exist_ok=True,parents=True)
    report={"status":"STARTED","blender":bpy.app.version_string,"input":a.source,
            "interpretation":"Actual Blender evaluated mesh, fixed anatomical ROI; bone contributions inferred from stored vertex weights and tested toggles"}
    try:
        bpy.ops.wm.open_mainfile(filepath=str(Path(a.source).resolve()))
        mesh=max((o for o in bpy.data.objects if o.type=="MESH" and any(m.type=="ARMATURE" and m.object for m in o.modifiers)),
                 key=lambda ob:len(ob.data.vertices))
        arm=next(m.object for m in mesh.modifiers if m.type=="ARMATURE" and m.object)
        scene=bpy.context.scene
        action=bpy.data.actions.get("run_sprint_v3")
        if not action:raise RuntimeError("Action run_sprint_v3 not present")
        names={g.index:g.name for g in mesh.vertex_groups}
        groups={g.name:g for g in mesh.vertex_groups}
        keys=mesh.data.shape_keys
        report["rig"]={"arm":arm.name,"mesh":mesh.name,"vertices":len(mesh.data.vertices),
            "bones":len(arm.pose.bones),"groups":len(mesh.vertex_groups),
            "modifier_types":[m.type for m in mesh.modifiers],
            "spine_and_shoulder_parents":{b.name:b.parent.name if b.parent else None for b in arm.data.bones
                                            if b.name in ("hips","neck","head") or b.name.startswith(("spine_","shoulder.","upper_arm.","forearm.","hand.","thigh.","shin."))},
            "deform_groups_with_no_bone":sorted(set(groups)-set(arm.pose.bones.keys()))}
        verts=list(mesh.data.vertices)
        skull=[groups.get(n) for n in ('head','snout','ear.L','ear.R') if groups.get(n)]
        distal=[groups.get(n) for n in ('hand.L','hand.R','front_toes.L','front_toes.R') if groups.get(n)]
        ROI=[v.index for v in verts if -.27<=v.co.y<=.045 and .055<=v.co.z<=.285 and abs(v.co.x)<=.165
              and sum(val(g,v.index) for g in skull)<.45 and sum(val(g,v.index) for g in distal)<.60]
        idset=set(ROI)
        E=[tuple(e.vertices) for e in mesh.data.edges if e.vertices[0] in idset and e.vertices[1] in idset]
        if len(ROI)<300 or len(E)<400:raise RuntimeError("ROI unexpectedly small")
        report["roi"]={"name":"anterior lower chest and axilla","vertices":len(ROI),"edges":len(E),
            "vertex_id_hash":__import__('hashlib').sha256(','.join(map(str,ROI)).encode()).hexdigest()}
        # Static deform weight inventory
        WV={i:{names[v.group]:float(v.weight) for v in verts[i].groups if v.group in names and v.weight>1e-8}
            for i in ROI}
        weightsum={i:sum(WV[i].values()) for i in ROI}
        whole_mass=collections.defaultdict(float)
        count=.0
        bone_mismatch=[]
        n4=n8=0
        for i in ROI:
            ww=WV[i]
            n4 += sum(w>.001 for w in ww.values())>4
            n8 += sum(w>.001 for w in ww.values())>8
            for n,w in ww.items():whole_mass[n]+=w
        report["static_weights"]={"sum_min":min(weightsum.values()),"sum_max":max(weightsum.values()),
            "sum_p05":quant(list(weightsum.values()),.05),"sum_p95":quant(list(weightsum.values()),.95),
            "more_than_4_influences":n4,"more_than_8_influences":n8,
            "total_weight_by_group":dict(sorted(whole_mass.items(),key=lambda x:-x[1])),
            "missing_bone_groups":[n for n in whole_mass if n not in arm.pose.bones]}
        # baseline rest vs movement
        arm.animation_data_create()
        arm.animation_data.action=None
        for t in arm.animation_data.nla_tracks:t.mute=True
        saved_modes={p.name:p.rotation_mode for p in arm.pose.bones}
        for pb in arm.pose.bones:pb.matrix_basis.identity()
        scene.frame_set(1)
        rest=pts(mesh)
        # Each sample is fully reloaded from action; never reuse the pose altered by ablation
        arm.animation_data.action=action
        scene.frame_set(2)
        scene.frame_set(1)
        restE={e:math.dist(rest[e[0]],rest[e[1]]) for e in E}
        report["edge_length_distribution"]={"rest_p01":quant(list(restE.values()),.01),
            "rest_p05":quant(list(restE.values()),.05),"rest_p50":quant(list(restE.values()),.50),
            "rest_p95":quant(list(restE.values()),.95),"sub_0_0001":sum(x<.0001 for x in restE.values()),
            "sub_0_001":sum(x<.001 for x in restE.values()),
            "sub_0_005":sum(x<.005 for x in restE.values())}
        freq=collections.Counter()
        rankings=[]
        bone_xforms={}
        for frame in (1,3,5,7,9,11,13,17,21,25):
            scene.frame_set(frame-1 if frame>1 else 2);scene.frame_set(frame)
            bpy.context.view_layer.update()
            pose=pts(mesh)
            # Top stretch edges; support multiple minimum edge lengths, avoid degenerate shadows
            thresholds=(.000001,.0001,.0005,.001,.002,.005)
            frame_m={}
            for th in thresholds:
                strain=[abs(math.dist(pose[e[0]],pose[e[1]])/l-1) for e,l in restE.items() if l>=th]
                frame_m[str(th)]={"edges":len(strain),"p90":quant(strain,.90),"p95":quant(strain,.95),
                                   "p99":quant(strain,.99),"max":max(strain) if strain else 0}
            # Extremes defined using minimum non-pathological base edge 0.001 model units
            worst=sorted(( (abs(math.dist(pose[e[0]],pose[e[1]])/l-1),e,l,math.dist(pose[e[0]],pose[e[1]]))
                            for e,l in restE.items() if l>=.001),reverse=True)
            examples=[]
            for stress,(u,v),L,Lp in worst[:150]:
                wa=WV[u];wb=WV[v]
                influential=set(n for n,w in wa.items() if w>.015)|set(n for n,w in wb.items() if w>.015)
                gw=sorted([(n,round(wa.get(n,0),4),round(wb.get(n,0),4),round(abs(wa.get(n,0)-wb.get(n,0)),4))
                            for n in influential], key=lambda q:-(q[1]+q[2]))
                examples.append({"edge":(u,v),"rest_length":round(L,8),"posed_length":round(Lp,8),
                    "strain":round(stress,5),"a_pos":tuple(round(x,5) for x in mesh.data.vertices[u].co),
                    "b_pos":tuple(round(x,5) for x in mesh.data.vertices[v].co),
                    "weights_both_ends":gw})
                for n,x,y,z in gw:
                    if x+y>.06:freq[n]+=1
            frame_score={"frame":frame,"thresholds":frame_m,
                "worst_edges_0_001":examples[:60],
                "critical_edge_count_gt1":sum(1 for r in worst if r[0]>1),
                "critical_edge_count_gt0_5":sum(1 for r in worst if r[0]>.5)}
            rankings.append(frame_score)
            rotations={}
            for bn in (['hips']+[f'spine_{j:02d}' for j in range(1,6)]+
                      ['shoulder.L','upper_arm.L','forearm.L','hand.L','shoulder.R','upper_arm.R','forearm.R','hand.R','neck','head']):
                if bn not in arm.pose.bones:continue
                pb=arm.pose.bones[bn]
                # Evaluated local transform relative to parent; include IK solution
                if pb.parent:loc=pb.parent.matrix.inverted()@pb.matrix
                else:loc=pb.matrix.copy()
                rotations[bn]={"rotation_euler":tuple(round(x,5) for x in pb.rotation_euler),
                    "pose_matrix_translation":tuple(round(x,5) for x in pb.matrix.translation),
                    "constraint_types":[c.type for c in pb.constraints],
                    "evaluated_local_bone_angle":round(loc.to_quaternion().angle,6)}
            bone_xforms[frame]=rotations
        report["pose_frames"]=rankings
        report["bone_kinematics"]=bone_xforms
        report["top_groups_in_worst_edges"]=freq.most_common(30)
        # Anatomical subregions and individual mesh islands: distinguish flank,
        # inter-leg belly and forelimb skin from the generic rectangular chest ROI.
        attr=mesh.data.attributes.get("part_id")
        part_ids={i:int(attr.data[i].value) if attr else -1 for i in ROI}
        report["mesh_island_attribute"]={"present":bool(attr),
            "roi_counts":dict(collections.Counter(part_ids.values())),
            "example_id_6":"body in this repository (check canonical mapping)"}
        subsets={
            "central_torso":[i for i in ROI if abs(verts[i].co.x)<.060],
            "inner_flank":[i for i in ROI if .060<=abs(verts[i].co.x)<.105],
            "outer_flank":[i for i in ROI if abs(verts[i].co.x)>=.105],
            "interleg_lower_abdomen":[i for i in ROI if -.100<=verts[i].co.y<=.055 and .045<=verts[i].co.z<=.16],
            "anterior_foreleg_skin":[i for i in ROI if verts[i].co.y<-.190 and abs(verts[i].co.x)>.09],
            "body_part_id6":[i for i in ROI if part_ids[i]==6],
        }
        spatial={}
        for label,inds in subsets.items():
            localset=set(inds)
            EE=[e for e in E if e[0] in localset and e[1] in localset]
            ws=collections.defaultdict(float)
            for i in inds:
                for g,w in WV[i].items():ws[g]+=w
            both=sum(1 for i in inds if max(WV[i].get('upper_arm.L',0),WV[i].get('upper_arm.R',0))>.1 and
                     max(WV[i].get('thigh.L',0),WV[i].get('thigh.R',0))>.1)
            spineonly=sum(1 for i in inds if sum(WV[i].get('spine_%02d'%k,0) for k in range(1,6))>.50)
            frm={}
            for f in rankings:
                poses=[x for x in f['worst_edges_0_001'] if x['edge'][0] in localset and x['edge'][1] in localset]
                frm[f['frame']]={"top60_global_count":len(poses)}
            spatial[label]={"vertices":len(inds),"internal_edges":len(EE),
                "high_weight_upperarm_and_thigh_vertices":both,"spine_dominated_vertices":spineonly,
                "mass_top12":sorted(ws.items(),key=lambda x:-x[1])[:12],"examples":frm}
        report["anatomical_subregions"]=spatial
        report["joint_weight_mixing"]={
            "upper_arm_thigh_same_vertex":sum(1 for i in ROI if max(WV[i].get('upper_arm.L',0),WV[i].get('upper_arm.R',0))>.1 and
                                                 max(WV[i].get('thigh.L',0),WV[i].get('thigh.R',0))>.1),
            "upper_arm_forearm_hand":sum(1 for i in ROI if max(WV[i].get('upper_arm.L',0),WV[i].get('upper_arm.R',0))>.2 and
                                            max(WV[i].get('hand.L',0),WV[i].get('hand.R',0))>.1),
            "spine_under_0_1_and_any_two_limbs_over_0_2":sum(
                1 for i in ROI if sum(WV[i].get('spine_%02d'%k,0) for k in range(1,6))<.1 and
                sum(max(WV[i].get('upper_arm.'+side,0),WV[i].get('thigh.'+side,0))>.2 for side in ('L','R'))>=2)
        }
        # Map worst edges' group variation and identify same coordinates / seam proximity
        selected=set()
        for sample in rankings:
            for entry in sample['worst_edges_0_001'][:30]:
                selected.update(entry['edge'])
        report["critical_vertex_weight_maps"]={str(i):sorted(WV[i].items(),key=lambda x:-x[1]) for i in sorted(selected)}
        # Region-specific controlled ablations for single bones and groups of bones; frame re-evaluated every time
        tests={
            "full": [],
            "spine_01_only_off":["spine_01"],"spine_02_only_off":["spine_02"],"spine_03_only_off":["spine_03"],
            "spine_04_only_off":["spine_04"],"spine_05_only_off":["spine_05"],
            "all_spine_off":[f"spine_{j:02d}" for j in range(1,6)],
            "hips_rotation_off":["hips"],
            "shoulder_L_rotation_off":["shoulder.L"],"shoulder_R_rotation_off":["shoulder.R"],
        }
        modifiers=[m for m in mesh.modifiers if m.type=="ARMATURE"]
        modstates=[m.use_deform_preserve_volume for m in modifiers]
        cons=[(c,float(c.influence)) for pb in arm.pose.bones for c in pb.constraints]
        drivers=[(f,bool(f.mute)) for f in keys.animation_data.drivers] if keys and keys.animation_data else []
        scenarios=list(tests)
        scenarios += ["fore_IK_L_off","fore_IK_R_off","fore_IK_both_off","hind_IK_both_off",
                      "all_correctives_off","preserve_volume_flip","all_leg_IK_off"]
        def restore():
            for m,v in zip(modifiers,modstates):m.use_deform_preserve_volume=v
            for c,v in cons:c.influence=v
            for fc,v in drivers:fc.mute=v
        def baseline(frame):
            restore()
            scene.frame_set(frame-1 if frame>1 else frame+1)
            scene.frame_set(frame)
            bpy.context.view_layer.update()
        ablations={}
        for f in (1,5,9,13,17,21):
            baseline(f);full=pts(mesh)
            cases={}
            for case in scenarios:
                baseline(f)
                if case in tests:
                    for bn in tests[case]:
                        if bn not in arm.pose.bones:continue
                        arm.pose.bones[bn].rotation_euler=(0,0,0)
                elif case.startswith("fore_IK") or case in ("hind_IK_both_off","all_leg_IK_off"):
                    sides={'fore_IK_L_off':['L'],'fore_IK_R_off':['R'],
                           'fore_IK_both_off':['L','R'],'hind_IK_both_off':['L','R'],
                           'all_leg_IK_off':['L','R']}[case]
                    prefix=["forearm."] if case.startswith("fore_IK") else ["shin."] if case=="hind_IK_both_off" else ["forearm.","shin."]
                    for pref in prefix:
                        for side in sides:
                            nm=pref+side
                            if nm in arm.pose.bones:
                                for c in arm.pose.bones[nm].constraints:
                                    if c.type=="IK":c.influence=0
                elif case=="all_correctives_off" and keys:
                    for fc in keys.animation_data.drivers:fc.mute=True
                    for kb in keys.key_blocks:
                        if kb.name!="Basis":kb.value=0.
                elif case=="preserve_volume_flip":
                    for m in modifiers:m.use_deform_preserve_volume=not m.use_deform_preserve_volume
                bpy.context.view_layer.update()
                p=pts(mesh)
                strains=[abs(math.dist(p[u],p[v])/L-1) for (u,v),L in restE.items() if L>=.001]
                disp=[math.dist(p[i],full[i]) for i in ROI]
                cases[case]={"p95_strain":quant(strains,.95),"p99_strain":quant(strains,.99),
                             "roi_mean_movement_vs_full":sum(disp)/len(disp),
                             "roi_p95_movement_vs_full":quant(disp,.95)}
            ablations[f]=cases
        restore()
        report["bone_isolation_by_frame"]=ablations
        report["bone_isolation_mean_p95"]={
            name:sum(ablations[f][name]["p95_strain"] for f in ablations)/len(ablations)
            for name in scenarios}
        report["bone_isolation_mean_delta"]={
            name:sum(ablations[f][name]["roi_mean_movement_vs_full"] for f in ablations)/len(ablations)
            for name in scenarios}
        # Full case equals original across independent extract paths if state reset; assert (absolute tolerance)
        for f in ablations:
            from_pose=next(x for x in rankings if x["frame"]==f)
            expected=from_pose["thresholds"]["0.001"]["p95"]
            observed=ablations[f]["full"]["p95_strain"]
            if abs(observed-expected)>1e-5:
                raise RuntimeError("State contamination / independent full-pose mismatch: frame="+str(f)+" expected "+str(expected)+" actual "+str(observed))
        report["state_crosscheck"]="PASS at 6 phases, exact local p95 agreement"
        report["status"]="PASS"
    except Exception as exc:
        report["status"]="FAIL";report["error"]=str(exc);report["traceback"]=traceback.format_exc()
    finally:
        (out/"bone_weight_root_cause.json").write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False))
        print("BONE_WEIGHT_ROOT_CAUSE",report["status"])
        print("BONE_WEIGHT_RANK",report.get("top_groups_in_worst_edges"))
        print("BONE_AUDIT_SUMMARY",json.dumps(report.get("bone_isolation_mean_p95",{}),ensure_ascii=False))
    if report["status"]!="PASS":raise SystemExit(1)

if __name__=="__main__":main()
