"""Diagnose belly deformation on actual Blender run_sprint_v2 evaluated mesh.
Read-only baseline + controlled pose/driver/modifier ablations.
NO automatic weights, NO permanent changes to source .blend.
"""
import bpy, argparse, json, math, sys, statistics, traceback
from pathlib import Path
from mathutils import Vector
def cli():
    p=argparse.ArgumentParser()
    p.add_argument("--source",required=True)
    p.add_argument("--out",required=True)
    return p.parse_args(sys.argv[sys.argv.index("--")+1:])
def getweight(g,v):
    try:return g.weight(v)
    except RuntimeError:return 0.0
def evalpts(mesh):
    deps=bpy.context.evaluated_depsgraph_get()
    obj=mesh.evaluated_get(deps)
    me=obj.to_mesh(preserve_all_data_layers=False,depsgraph=deps)
    try:
        mat=obj.matrix_world.copy()
        return [tuple(mat@v.co) for v in me.vertices]
    finally:obj.to_mesh_clear()
def percentile(vals,t):
    if not vals:return 0.
    x=sorted(vals);return x[min(len(x)-1,int(t*(len(x)-1)))]
def metrics(base,now,roi,edges):
    cx=sum(now[i][0] for i in roi)/max(len(roi),1)
    cy=sum(now[i][1] for i in roi)/max(len(roi),1)
    cz=sum(now[i][2] for i in roi)/max(len(roi),1)
    lens=[]
    for a,b in edges:
        d0=math.dist(base[a],base[b])
        if d0>1e-7:lens.append(abs(math.dist(now[a],now[b])/d0-1))
    return {"mean_z":cz,"min_z":min(now[i][2] for i in roi),
            "z_p10":percentile([now[i][2] for i in roi],.1),
            "z_p90":percentile([now[i][2] for i in roi],.9),
            "centroid":(cx,cy,cz),
            "edge_p95":percentile(lens,.95),
            "edge_p99":percentile(lens,.99),
            "max_disp_vs_rest":max(math.dist(now[i],base[i]) for i in roi),
            "mean_disp_vs_rest":sum(math.dist(now[i],base[i]) for i in roi)/len(roi)}
def delta(a,b,roi):
    if not roi:return {}
    dis=[math.dist(a[i],b[i]) for i in roi]
    avg=sum(dis)/len(dis)
    return {"mean":avg,"p95":percentile(dis,.95),"max":max(dis)}
def render_camera(scene,center,scale):
    d=bpy.data.cameras.new("Belly_Probe_Camera")
    c=bpy.data.objects.new("Belly_Probe_Camera",d)
    scene.collection.objects.link(c)
    c.location=center+Vector((scale*1.7,-scale*.14,scale*.25))
    c.rotation_euler=(center-c.location).to_track_quat("-Z","Y").to_euler()
    d.type="ORTHO";d.ortho_scale=scale*1.2
    scene.camera=c
    scene.render.engine="BLENDER_WORKBENCH"
    scene.render.resolution_x=640
    scene.render.resolution_y=430
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format="PNG"
    scene.display.shading.light="STUDIO"
    scene.display.shading.color_type="MATERIAL"
    scene.display.shading.show_shadows=True
def main():
    x=cli();out=Path(x.out).resolve();out.mkdir(parents=True,exist_ok=True)
    report={"status":"STARTED","source":x.source,"blender":bpy.app.version_string}
    try:
        bpy.ops.wm.open_mainfile(filepath=str(Path(x.source).resolve()))
        mesh=max([ob for ob in bpy.data.objects if ob.type=="MESH" and any(mod.type=="ARMATURE" and mod.object for mod in ob.modifiers)],key=lambda ob:len(ob.data.vertices))
        arm=next(mod.object for mod in mesh.modifiers if mod.type=="ARMATURE" and mod.object)
        scene=bpy.context.scene
        action=bpy.data.actions.get("run_sprint_v2")
        if action is None:raise RuntimeError("run_sprint_v2 missing")
        arm.animation_data_create()
        arm.animation_data.action=action
        for tr in arm.animation_data.nla_tracks:tr.mute=True
        mods=[mod for mod in mesh.modifiers if mod.type=="ARMATURE"]
        keys=mesh.data.shape_keys
        keynames=[k.name for k in keys.key_blocks] if keys else []
        driver_info=[]
        if keys and keys.animation_data:
            for fc in keys.animation_data.drivers:
                driver_info.append({"path":fc.data_path,"expression":fc.driver.expression,"mute":fc.mute,
                                    "variables":[v.name for v in fc.driver.variables]})
        report["structure"]={"mesh":mesh.name,"vertex_count":len(mesh.data.vertices),
                             "armature_bones":len(arm.pose.bones),
                             "armature_modifiers":[{"name":m.name,"preserve_volume":m.use_deform_preserve_volume} for m in mods],
                             "shape_keys":keynames,"shape_key_drivers":driver_info,
                             "armature_action":action.name,
                             "IK_constraints":[{"bone":p.name,"name":c.name,"influence":c.influence,"type":c.type} for p in arm.pose.bones for c in p.constraints if c.type=="IK"]}
        # Anatomical anterior lower chest / axilla: do NOT confuse with hind belly.
        # Fixed vertex indices, independent of current pose and future weight edits.
        skull=[mesh.vertex_groups.get(n) for n in ("head","snout","ear.L","ear.R")]
        skull=[g for g in skull if g]
        distal=[mesh.vertex_groups.get(n) for n in ("hand.L","hand.R","front_toes.L","front_toes.R")]
        distal=[g for g in distal if g]
        belly=[v.index for v in mesh.data.vertices
               if -.27<=v.co.y<=.045 and .055<=v.co.z<=.285
               and abs(v.co.x)<=.165
               and sum(getweight(g,v.index) for g in skull)<.45
               and sum(getweight(g,v.index) for g in distal)<.60]
        torso=belly
        zcut=max(mesh.data.vertices[i].co.z for i in belly)
        if len(belly)<100:raise RuntimeError("Anterior chest ROI too small")
        belly_ids=set(belly)
        edges=[tuple(e.vertices) for e in mesh.data.edges if e.vertices[0] in belly_ids and e.vertices[1] in belly_ids]
        if len(edges)<100:raise RuntimeError("Not enough anterior chest edges")
        report["ROI"]={"torso_vertices":len(torso),"belly_vertices":len(belly),"belly_local_z_max":zcut,
                       "belly_edges":len(edges),"bounds_local":{"min":[min(mesh.data.vertices[i].co[j] for i in belly) for j in range(3)],
                                                                  "max":[max(mesh.data.vertices[i].co[j] for i in belly) for j in range(3)]}}
        def original(frame):
            scene.frame_set(frame)
            bpy.context.view_layer.update()
        def ablate(kind):
            if kind=="no_spine":
                for b in arm.pose.bones:
                    if b.name.startswith("spine_"):b.rotation_euler=(0,0,0)
            if kind=="no_hips_rotation":
                p=arm.pose.bones["hips"];p.rotation_euler=(0,0,0)
            if kind=="no_hips_translation":
                p=arm.pose.bones["hips"];p.location=(0,0,0)
            if kind=="no_spine_or_hips":
                p=arm.pose.bones["hips"];p.rotation_euler=(0,0,0)
                for b in arm.pose.bones:
                    if b.name.startswith("spine_"):b.rotation_euler=(0,0,0)
            if kind=="no_shape_keys" and keys:
                if keys.animation_data:
                    for drv in keys.animation_data.drivers:drv.mute=True
                for kb in keys.key_blocks:
                    if kb.name!="Basis":kb.value=0.
            if kind=="no_front_ik":
                for b in arm.pose.bones:
                    if b.name.startswith("forearm."):
                        for c in b.constraints:
                            if c.type=="IK":c.influence=0.0
            if kind=="other_skinning":
                for mod in mods:mod.use_deform_preserve_volume=not mod.use_deform_preserve_volume
            bpy.context.view_layer.update()
        def restore_modes():
            if keys and keys.animation_data:
                for fc in keys.animation_data.drivers:fc.mute=False
            for mod,s in zip(mods,modifier_states):mod.use_deform_preserve_volume=s
        modifier_states=[mod.use_deform_preserve_volume for mod in mods]
        original(1)
        # Temporarily disable action for rest, then reset all bones.
        arm.animation_data.action=None
        for pb in arm.pose.bones:
            pb.rotation_mode="QUATERNION";pb.matrix_basis.identity()
        scene.frame_set(1)
        base=evalpts(mesh)
        for pb in arm.pose.bones:
            pb.rotation_mode="XYZ"
        arm.animation_data.action=action
        modes=["full","no_spine","no_hips_rotation","no_hips_translation",
               "no_spine_or_hips","no_shape_keys","no_front_ik","other_skinning"]
        records=[]
        key_value_evolution=[]
        pose_sample_frames=[1,3,5,7,9,11,13,15,17,19,21,23,25]
        for frame in pose_sample_frames:
            original(frame)
            full=evalpts(mesh)
            key_values={k.name:float(k.value) for k in keys.key_blocks} if keys else {}
            key_value_evolution.append({"frame":frame,"values":key_values})
            comparisons={}
            for mode in modes:
                original(frame)
                restore_modes()
                if mode!="full":ablate(mode)
                after=evalpts(mesh)
                comparisons[mode]={"metrics":metrics(base,after,belly,edges),
                                   "delta_from_full":delta(full,after,belly)}
            records.append({"frame":frame,"ablations":comparisons})
        restore_modes()
        # Determine most causally influential components, using fixed ROI and same frame.
        means={m:sum(r["ablations"][m]["delta_from_full"]["mean"] for r in records)/len(records) for m in modes if m!="full"}
        report["ablation_mean_delta_fixed_belly_roi"]=dict(sorted(means.items(),key=lambda kv:-kv[1]))
        report["frames"]=records;report["driver_values"]=key_value_evolution
        report["pose_key_statistics"]={"frame_count":len(records),
                                      "top_ablation":next(iter(report["ablation_mean_delta_fixed_belly_roi"])),
                                      "belly_p95_edge_worst":max(r["ablations"]["full"]["metrics"]["edge_p95"] for r in records)}
        # Generate a focused side-by-side visual for worst deformation and representative frames.
        bb=[mesh.matrix_world@Vector(x) for x in mesh.bound_box]
        center=sum(bb,Vector((0,0,0)))/8
        size=max(max(v.y for v in bb)-min(v.y for v in bb),max(v.z for v in bb)-min(v.z for v in bb))
        render_camera(scene,center,size)
        vis=out/"frames";vis.mkdir(exist_ok=True)
        for frame in (1,5,9,13,17,21):
            for mode in ("full","no_spine","no_hips_rotation","no_shape_keys"):
                original(frame);restore_modes()
                if mode!="full":ablate(mode)
                scene.render.filepath=str(vis/f"{mode}_f{frame:02d}.png")
                bpy.ops.render.render(write_still=True)
        report["renders"]=24
        report["status"]="PASS"
    except Exception as ex:
        report["status"]="FAIL";report["error"]=str(ex);report["traceback"]=traceback.format_exc()
    finally:
        (out/"front_diagnosis.json").write_text(json.dumps(report,ensure_ascii=False,indent=2))
        print("FRONT_DIAGNOSIS",report["status"])
        print("FRONT_ABLATIONS",report.get("ablation_mean_delta_fixed_belly_roi"))
    if report["status"]=="FAIL":raise SystemExit(1)

if __name__=="__main__":
    main()
