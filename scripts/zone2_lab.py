import sys, math, os, copy
import numpy as np
sys.path.append("/tmp/rig/td"); sys.path.append("/tmp/rig")
import skinlib as SL
from mathutils import Vector

OUT = "/tmp/rig/td/z2_elbow"
os.makedirs(OUT, exist_ok=True)
S = SL.Skin("/tmp/rig/mouse_rig_td_z1.blend")
scene = SL.setup_render(samples=20, res=760)
import bpy
clay = bpy.data.materials.new("clay")
clay.use_nodes = True
b = clay.node_tree.nodes["Principled BSDF"]
b.inputs["Base Color"].default_value = (0.75, 0.73, 0.70, 1)
b.inputs["Roughness"].default_value = 0.65
bpy.context.view_layer.material_override = clay
R = math.radians

hFA, tFA = S.bone_pts("forearm.L")   # dirsek = hFA
cam = SL.look_cam("c_elbow", (hFA[0] + 0.34, hFA[1] - 0.20, hFA[2] + 0.10),
                  tuple(hFA), lens=80)

near = np.linalg.norm(S.CO - hFA, axis=1) < 0.05
em_local = near[S.EV[:, 0]] & near[S.EV[:, 1]] & ~(S.wh_mask[S.EV[:, 0]])

def local_stretch():
    pc = S.posed_coords()
    plen = np.linalg.norm(pc[S.EV[:, 0]] - pc[S.EV[:, 1]], axis=1)
    r = (plen / np.maximum(S.rest_len, 1e-9))[em_local]
    return float(np.quantile(r, 0.99)), float(r.max())

GW0 = {g: a.copy() for g, a in S.GW.items()}

def apply_band(width):
    for g in S.GW:
        S.GW[g][:] = GW0[g]
    if width is None:
        S.write_weights(); return
    for side, xs in (("L", 1), ("R", -1)):
        ua, fa = f"upper_arm.{side}", f"forearm.{side}"
        hUA, _ = S.bone_pts(ua)
        h2, t2 = S.bone_pts(fa)
        s, d = S.chain_param([hUA, h2, t2], np.arange(S.NV))
        sel = (~S.wh_mask) & (S.CO[:, 0] * xs > 0.02) & (d < 0.085) & \
              ((S.pid == S.IDS["body"]) | (S.pid == S.IDS["paw_front_L" if side == "L" else "paw_front_R"]))
        S.band(ua, fa, width=width, sel=sel)
    S.write_weights()

for name, w in (("v0_none", None), ("v1_w25", 0.025), ("v2_w35", 0.035), ("v3_w50", 0.050)):
    apply_band(w)
    S.reset_pose()
    S.rot("forearm.L", R(90))
    p99, mx = local_stretch()
    SL.render(f"{OUT}/lab_{name}.png", cam)
    print(f"{name}: lokal p99={p99:.2f} max={mx:.2f}")
S.reset_pose()
print("LAB DONE")
