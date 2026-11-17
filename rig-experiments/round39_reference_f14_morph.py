"""R39: Pose-specific inverse-LBS transfer to exact source v8 geometry at f14.
This is not a full global reweight: only the deformed 487-v interleg ROI is
affected, the original 24-frame action remains intact. Target extracted from
physically saved Blender v8, not an algorithmic guess.
"""
import bpy,numpy as np
from mathutils import Matrix,Vector


def build_reference_patch(ob,arm,action,helper,forensic,original,base,
                          body_indices,targets,split,centerkeys,
                          recovery_weight,pulse,shape_basis,invworld,full_coords):
    # Match exactly the fixed Round37/38 profile with 0.95 strength:
    # cap f8=.50, f14 front=.44, rear=.38, f9 restore=.88.
    strength=.95
    width=.32
    for f,key in targets.items():
        key.value=strength*(.5 if f==8 else 1.)*pulse(14,f,width)
    for part,key in split.items():
        key.value=strength*(.44 if part=="front" else .38)*pulse(14,14,width)
    for f,key in centerkeys.items():
        key.value=recovery_weight(14,f,strength,.88)
    helper["pose"](arm,action,14)
    bpy.context.view_layer.update()
    current=full_coords(helper,ob)
    source=base[13]
    delta=np.linalg.norm(source-current,axis=1)
    roi=set(body_indices)
    outliers=[int(i) for i in np.where(delta>1e-5)[0] if int(i) not in roi]
    if outliers:
        raise RuntimeError("v8 source differs outside isolated body ROI: "+str(outliers[:20]))
    key=ob.shape_key_add(name="R39_F14_ORIGINAL_REFERENCE",from_mix=False)
    transforms=forensic["vmat"](ob,arm)
    world=ob.matrix_world.to_3x3()
    affected=0;max_pre=0.;max_local_reconstruction=0.;clipped=0;skip=0
    for i in roi:
        desired=Vector(source[i]-current[i])
        if desired.length<=1e-8:continue
        weights={ob.vertex_groups[g.group].name:float(g.weight)
                 for g in ob.data.vertices[i].groups
                 if ob.vertex_groups[g.group].name in transforms}
        mass=sum(weights.values())
        if mass<=1e-5:skip+=1;continue
        blend=Matrix(((0,0,0),(0,0,0),(0,0,0)))
        for name,wt in weights.items():
            blend+=transforms[name].to_3x3()*(wt/mass)
        det=abs(blend.determinant())
        if det<=.16:skip+=1;continue
        pre=blend.inverted()@(invworld@desired)
        if pre.length>.022:
            clipped+=1;pre*=.022/pre.length
        key.data[i].co=shape_basis.data[i].co+pre
        max_pre=max(max_pre,pre.length)
        max_local_reconstruction=max(max_local_reconstruction,(world@(blend@pre)-desired).length)
        affected+=1
    key.value=1.
    bpy.context.view_layer.update()
    measured=full_coords(helper,ob)
    drift=np.linalg.norm(measured-source,axis=1)
    max_drift=float(np.max(drift))
    rms=float(np.sqrt(np.mean(drift**2)))
    if max_drift>1e-4:
        raise RuntimeError("Frame14 source reconstruction inaccurate: %g, skipped=%d, clipped=%d"%(max_drift,skip,clipped))
    key.value=0.
    bpy.context.view_layer.update()
    result={"source_frame":14,"reconstructed_world_max_error":max_drift,
            "reconstructed_world_rms_error":rms,
            "shape_vertices":affected,"skipped_unstable_vertices":skip,
            "clipped_local_offset_vertices":clipped,
            "max_local_key_offset":max_pre,
            "max_inverse_skin_backprojection_error":max_local_reconstruction,
            "source_provenance":"saved independent v8 Blender actual pose geometry",
            "note":"A temporary inverse LBS pre-skin shape-key correction at f14; final numerical, visual and glTF clearance still required"}
    print("R39_REFERENCE",result)
    return key,result
