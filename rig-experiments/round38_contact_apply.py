"""Round38 — attach an f14 collision-constrained inverse-skin shape key to a
separate experimental Blender scene. Never modifies deliver/mouse_rig.blend.
"""
import bpy,runpy
import numpy as np
from mathutils import Matrix,Vector


def build_contact_morph(ob,arm,act,helper,forensic,original,base,refs,tris,
                        rest_area,body_vertex_ids,targets,split,centerkeys,
                        recovery_weight,pulse,basekey,invworld,full_coords):
    strength=.95
    width=.32
    for f,k in targets.items():
        k.value=strength*(.5 if f==8 else 1.)*pulse(14,f,width)
    for part,k in split.items():
        k.value=strength*(.44 if part=="front" else .38)*pulse(14,14,width)
    for f,k in centerkeys.items():
        k.value=recovery_weight(14,f,strength,.88)
    helper["pose"](arm,act,14)
    bpy.context.view_layer.update()
    current=full_coords(helper,ob)
    source=base[13]
    collision=runpy.run_path("rig-experiments/round38_contact_geometry.py",
                             run_name="r38_collision_library")
    original_pairs=collision["bvh_pairs"](source,tris)
    current_pairs=collision["bvh_pairs"](current,tris)
    new_pairs=current_pairs-original_pairs
    incident={int(v) for pair in new_pairs for fid in pair for v in tris[fid]}
    allowed={i for i in incident if i in body_vertex_ids}
    for tri in tris:
        if any(int(v) in incident for v in tri):
            allowed.update(int(v) for v in tri if int(v) in body_vertex_ids)
    if not allowed:
        raise RuntimeError("No editable body vertices at any new R36 overlap")
    rot=np.asarray([list(row) for row in original["rot"][14].to_matrix()])
    oriented=(rot@refs.T).T
    adjusted,info=collision["solve_contacts"](
        current,source,tris,rest_area,oriented,allowed,
        base_pairs=original_pairs,max_world_change=.007,max_iterations=55)
    key=ob.shape_key_add(name="R38_F14_CONTACT_ONLY",from_mix=False)
    mats=forensic["vmat"](ob,arm)
    edited=np.where(np.linalg.norm(adjusted-current,axis=1)>1e-8)[0]
    world_matrix=ob.matrix_world.to_3x3()
    clipped=0;max_backprojection=0.
    for v in edited:
        v=int(v)
        if v not in allowed:
            raise RuntimeError("Contact geometry moved a vertex outside its local repair envelope")
        deform={ob.vertex_groups[g.group].name:float(g.weight)
                for g in ob.data.vertices[v].groups
                if ob.vertex_groups[g.group].name in mats}
        mass=sum(deform.values())
        if mass<1e-5:raise RuntimeError("No skinning mass at contact "+str(v))
        skin=Matrix(((0,0,0),(0,0,0),(0,0,0)))
        for nm,w in deform.items():skin+=mats[nm].to_3x3()*(w/mass)
        if abs(skin.determinant())<.16:
            raise RuntimeError("Contact vertex skin transform noninvertible "+str(v))
        target=Vector(adjusted[v]-current[v])
        pre=skin.inverted()@(invworld@target)
        if pre.length>.017:
            pre*=.017/pre.length
            clipped+=1
        key.data[v].co=basekey.data[v].co+pre
        max_backprojection=max(max_backprojection,
                               (world_matrix@(skin@pre)-target).length)
    key.value=1.
    bpy.context.view_layer.update()
    actual=full_coords(helper,ob)
    max_inverse_readback_error=float(np.max(np.linalg.norm(actual-adjusted,axis=1)))
    if max_inverse_readback_error>2e-4:
        raise RuntimeError("Shape key f14 inverse pose reconstruction invalid: %g"%max_inverse_readback_error)
    key.value=0.
    bpy.context.view_layer.update()
    info.update(shape_vertices=len(edited),candidate_new_pair_ids=[list(x) for x in sorted(new_pairs)],
                editable_vertices=sorted(allowed),inverse_skin_max_error=max_backprojection,
                actual_evaluated_readback_error=max_inverse_readback_error,
                inverse_delta_clipped=clipped,
                note="Contact penalties are half-space approximations; final BVH is based on actual Blender triangles.")
    print("R38_CONTACT_PROBE",info["before"]["total"],"->",info["after"]["total"],
          "new",info["before"]["new"],"->",info["after"]["new"],
          "steps",info["accepted_steps"],"vertex",len(edited),
          "world_delta",info["max_actual_world_offset"])
    return key,info
