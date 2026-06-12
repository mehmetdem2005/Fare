"""Driver'li duzeltici shape key'ler (pozda delta-mush -> rest'e ters-skin).
13 key: dirsek/diz/omuz/kalca/kulak L-R, boyun yaw L-R, omurga curl."""
import sys, math
import numpy as np
sys.path.append("/tmp/rig/td"); sys.path.append("/tmp/rig")
import skinlib as SL
import bpy
from mathutils import Vector, Matrix
from mathutils import kdtree

S = SL.Skin("/tmp/rig/mouse_rig_td.blend")
C, D = bpy.context, bpy.data
VN = np.empty(S.NV * 3)
S.me.vertices.foreach_get("normal", VN)
VN = VN.reshape(S.NV, 3)
mouse, arm = S.mouse, S.arm
R = math.radians

# ---- koprulu komsuluk (ada-ici) ----
nbr = [[] for _ in range(S.NV)]
for a, b in S.EV:
    nbr[int(a)].append(int(b)); nbr[int(b)].append(int(a))
for isl_name in ["body", "paw_front_L", "paw_front_R", "foot_hind_L", "foot_hind_R",
                 "tail", "ear_L", "ear_R"]:
    isl = S.island(isl_name)
    kd = kdtree.KDTree(len(isl))
    for k, vi in enumerate(isl):
        kd.insert(Vector(S.CO[vi]), k)
    kd.balance()
    have = [set(nbr[int(v)]) for v in isl]
    for k, vi in enumerate(isl):
        for co, j, dist in kd.find_range(Vector(S.CO[vi]), 0.006):
            vj = int(isl[j])
            if j == k or vj in have[k]:
                continue
            if dist <= 0.0012 or float(np.dot(VN[int(vi)], VN[vj])) > 0.7:
                nbr[int(vi)].append(vj); nbr[vj].append(int(vi)); have[k].add(vj)

def smooth01(x):
    return np.clip(x, 0, 1) ** 2 * (3 - 2 * np.clip(x, 0, 1))

def posed_coords():
    C.view_layer.update()
    dg = C.evaluated_depsgraph_get()
    mev = mouse.evaluated_get(dg)
    pc = np.empty(S.NV * 3)
    mev.data.vertices.foreach_get("co", pc)
    return pc.reshape(S.NV, 3)

def skin_matrices():
    C.view_layer.update()
    out = {}
    for pb in arm.pose.bones:
        rb = arm.data.bones[pb.name]
        out[pb.name] = np.array(pb.matrix @ rb.matrix_local.inverted())
    return out

# yeniden kurulum: eski crv keyleri sil
if mouse.data.shape_keys:
    for kb in list(mouse.data.shape_keys.key_blocks):
        if kb.name.startswith("crv_"):
            try: kb.driver_remove("value")
            except Exception: pass
            mouse.shape_key_remove(kb)
# Basis
if mouse.data.shape_keys is None:
    mouse.shape_key_add(name="Basis")

gnames = list(S.GW)

SPECS = [
    ("crv_elbow_L",   [("forearm.L", (R(90), 0, 0))], "forearm.L", "rot_x", 1.5708, "forearm.L", "head", 0.075, ["body", "paw_front_L"]),
    ("crv_elbow_R",   [("forearm.R", (R(90), 0, 0))], "forearm.R", "rot_x", 1.5708, "forearm.R", "head", 0.075, ["body", "paw_front_R"]),
    ("crv_knee_L",    [("shin.L", (-R(90), 0, 0))], "shin.L", "rot_x", -1.5708, "shin.L", "head", 0.085, ["body"]),
    ("crv_knee_R",    [("shin.R", (-R(90), 0, 0))], "shin.R", "rot_x", -1.5708, "shin.R", "head", 0.085, ["body"]),
    ("crv_shoulder_L", [("upper_arm.L", (-R(70), 0, 0))], "upper_arm.L", "rot_x", -1.2217, "upper_arm.L", "head", 0.085, ["body"]),
    ("crv_shoulder_R", [("upper_arm.R", (-R(70), 0, 0))], "upper_arm.R", "rot_x", -1.2217, "upper_arm.R", "head", 0.085, ["body"]),
    ("crv_hip_L",     [("thigh.L", (R(40), 0, 0))], "thigh.L", "rot_x", 0.6981, "thigh.L", "mid", 0.095, ["body"]),
    ("crv_hip_R",     [("thigh.R", (R(40), 0, 0))], "thigh.R", "rot_x", 0.6981, "thigh.R", "mid", 0.095, ["body"]),
    ("crv_ear_L",     [("ear.L", (R(40), 0, 0)), ("ear_02.L", (R(20), 0, 0))], "ear.L", "rot_x", 0.6981, "ear.L", "head", 0.055, ["ear_L"]),
    ("crv_ear_R",     [("ear.R", (R(40), 0, 0)), ("ear_02.R", (R(20), 0, 0))], "ear.R", "rot_x", 0.6981, "ear.R", "head", 0.055, ["ear_R"]),
    ("crv_neck_yawL", [("neck", (0, 0, R(25))), ("head", (0, 0, R(35)))], "head", "rot_z", 0.6109, "neck", "mid", 0.20, ["body"]),
    ("crv_neck_yawR", [("neck", (0, 0, -R(25))), ("head", (0, 0, -R(35)))], "head", "rot_z", -0.6109, "neck", "mid", 0.20, ["body"]),
    ("crv_spine_curl", [("hips", (R(12), 0, 0)), ("spine_01", (R(17), 0, 0)),
                        ("spine_02", (R(17), 0, 0)), ("spine_03", (R(17), 0, 0))],
     "spine_02", "rot_x", 0.2967, "spine_02", "tail", 0.30, ["body"]),
    ("crv_spine_arch", [("hips", (-R(10), 0, 0)), ("spine_01", (-R(14), 0, 0)),
                        ("spine_02", (-R(14), 0, 0)), ("spine_03", (-R(12), 0, 0))],
     "spine_02", "rot_x", -0.2443, "spine_02", "tail", 0.30, ["body"]),
]

ID_BY = {n: i for i, n in enumerate(["whiskers_L", "whiskers_R", "paw_front_R", "paw_front_L",
                                     "ear_L", "ear_R", "body", "foot_hind_R", "foot_hind_L", "tail"])}
import plan_data as P
IDS = {n: i for i, n in enumerate(P.MESH_RENAME.values())}

for (kname, pose_set, drv_bone, drv_ch, drv_target, cb, cw, RAD, islands) in SPECS:
    if mouse.data.shape_keys and kname in mouse.data.shape_keys.key_blocks:
        print(kname, "VAR atla"); continue
    S.reset_pose()
    for bn, rot in pose_set:
        S.rot(bn, *rot)
    Ppose = posed_coords()
    Ms = skin_matrices()
    h, t = S.bone_pts(cb)
    center = np.array(h) if cw == "head" else (np.array(h) + np.array(t)) / 2 if cw == "mid" else np.array(t)
    dist = np.linalg.norm(S.CO - center, axis=1)
    allow = np.zeros(S.NV, bool)
    for inm in islands:
        allow[S.island(inm)] = True
    region = (dist < RAD) & allow & ~S.wh_mask
    ridx = np.where(region)[0]
    if not len(ridx):
        print(kname, "BOS REGION"); continue
    f = smooth01((RAD - dist[ridx]) / (0.35 * RAD))
    # laplacian smooth pozlu koordinatlarda
    Pw = Ppose.copy()
    for it in range(8):
        snap = Pw.copy()
        for k, vi in enumerate(ridx):
            ns = [u for u in nbr[vi] if not S.wh_mask[u]]
            if not ns:
                continue
            avg = snap[ns].mean(0)
            Pw[vi] = snap[vi] * 0.45 + avg * 0.55
    d_pose = (Pw[ridx] - Ppose[ridx]) * f[:, None]
    # ters-skin: off = inv(Mv)[:3,:3] @ d
    offs = np.zeros((len(ridx), 3))
    for k, vi in enumerate(ridx):
        Mv = np.zeros((4, 4))
        for g in gnames:
            w = S.GW[g][vi]
            if w > 1e-4 and g in Ms:
                Mv += w * Ms[g]
        if abs(np.linalg.det(Mv[:3, :3])) < 1e-9:
            continue
        offs[k] = np.linalg.inv(Mv[:3, :3]) @ d_pose[k]
    kb = mouse.shape_key_add(name=kname, from_mix=False)
    base = np.empty(S.NV * 3)
    mouse.data.shape_keys.key_blocks["Basis"].data.foreach_get("co", base)
    base = base.reshape(S.NV, 3).copy()
    base[ridx] += offs
    kb.data.foreach_set("co", base.ravel())
    kb.slider_min = 0.0; kb.slider_max = 1.0
    # driver
    fc = kb.driver_add("value")
    drv = fc.driver
    drv.type = 'SCRIPTED'
    var = drv.variables.new()
    var.name = "a"
    var.type = 'TRANSFORMS'
    tgt = var.targets[0]
    tgt.id = arm
    tgt.bone_target = drv_bone
    tgt.transform_type = 'ROT_X' if drv_ch == "rot_x" else 'ROT_Z'
    tgt.transform_space = 'LOCAL_SPACE'
    tgt.rotation_mode = 'XYZ'
    drv.expression = f"max(0.0, min(1.0, a/({drv_target})))"
    mag = float(np.linalg.norm(d_pose, axis=1).max())
    print(f"{kname}: {len(ridx)}v maxfix={mag*1000:.1f}mm")

S.reset_pose()
bpy.ops.wm.save_as_mainfile(filepath="/tmp/rig/mouse_rig_td.blend")
print("CORRECTIVES OK")
