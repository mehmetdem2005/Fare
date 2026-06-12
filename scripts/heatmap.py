"""Gerilme isi haritasi: pozdaki vertex gerilmesini renkle gosterir,
en sicak noktalarin koordinat + agirlik dokumunu yazar."""
import sys, math, os
import numpy as np
sys.path.append("/tmp/rig/td"); sys.path.append("/tmp/rig")
import skinlib as SL
import bpy

OUT = "/tmp/rig/td/heat"
os.makedirs(OUT, exist_ok=True)
S = SL.Skin("/tmp/rig/mouse_rig_td.blend")
scene = SL.setup_render(samples=14, res=860)
scene.view_settings.view_transform = 'Standard'
R = math.radians

# vert->incident edges
me = S.me
NV = S.NV
inc = [[] for _ in range(NV)]
for ei, (a, b) in enumerate(S.EV):
    inc[a].append(ei); inc[b].append(ei)

attr = me.color_attributes.new(name="Stretch", type='FLOAT_COLOR', domain='POINT')
mat = bpy.data.materials.new("stretchmat")
mat.use_nodes = True
nt = mat.node_tree; nt.nodes.clear()
at = nt.nodes.new("ShaderNodeAttribute"); at.attribute_name = "Stretch"
em = nt.nodes.new("ShaderNodeEmission")
out = nt.nodes.new("ShaderNodeOutputMaterial")
nt.links.new(at.outputs["Color"], em.inputs[0])
nt.links.new(em.outputs[0], out.inputs[0])
bpy.context.view_layer.material_override = mat

def ramp(r):
    """1.0 koyu mavi -> 1.25 yesil -> 1.5 sari -> 2.0+ kirmizi"""
    c = np.zeros((len(r), 4)); c[:, 3] = 1
    t = np.clip((r - 1.0) / 1.0, 0, 1)   # 1..2 -> 0..1
    c[:, 0] = np.clip(t * 2.2 - 0.25, 0, 1)
    c[:, 1] = np.clip(1.6 * (1 - abs(t - 0.42) * 2.2), 0.04, 1) * (t > 0.04)
    c[:, 2] = np.clip(0.9 - t * 2.2, 0, 1)
    c[t <= 0.02] = (0.06, 0.07, 0.22, 1)
    return c

def heat_render(pose_fn, cams_pts, tag, report_n=14):
    S.reset_pose(); pose_fn()
    pc = S.posed_coords()
    plen = np.linalg.norm(pc[S.EV[:, 0]] - pc[S.EV[:, 1]], axis=1)
    er = plen / np.maximum(S.rest_len, 1e-9)
    vr = np.ones(NV)
    for v in range(NV):
        if inc[v]:
            vr[v] = max(er[e] for e in inc[v])
    vr[S.wh_mask] = 1.0
    attr.data.foreach_set("color", ramp(vr).ravel())
    me.update()
    for i, (loc, tgt, lens) in enumerate(cams_pts):
        cam = SL.look_cam(f"hc_{tag}_{i}", loc, tgt, lens)
        SL.render(f"{OUT}/{tag}_{i}.png", cam)
    hot = np.argsort(-vr)[:300]
    seen = []
    print(f"--- {tag}: en sicak noktalar ---")
    for v in hot:
        if any(np.linalg.norm(S.CO[v] - S.CO[u]) < 0.025 for u in seen):
            continue
        seen.append(v)
        ws = {g: round(S.GW[g][v], 2) for g in S.GW if S.GW[g][v] > 0.05}
        part = [n for n, i2 in S.IDS.items() if i2 == S.pid[v]][0]
        print(f"  v{v} r={vr[v]:.2f} co=({S.CO[v][0]:+.3f},{S.CO[v][1]:+.3f},{S.CO[v][2]:.3f}) {part} W={ws}")
        if len(seen) >= report_n:
            break

heat_render(lambda: (S.rot("neck", 0, 0, R(28)), S.rot("head", 0, 0, R(34))),
            [((0.55, -0.65, 0.55), (0.0, -0.20, 0.30), 55), ((-0.55, -0.65, 0.55), (0.0, -0.20, 0.30), 55)],
            "bas_donus")
heat_render(lambda: S.rot("upper_arm.L", -R(70)),
            [((0.50, -0.60, 0.30), (0.10, -0.19, 0.15), 60), ((0.18, -0.75, 0.06), (0.08, -0.22, 0.12), 60)],
            "omuz_kaldir")
heat_render(lambda: S.rot("forearm.L", R(90)),
            [((0.45, -0.55, 0.22), (0.11, -0.18, 0.09), 70), ((0.30, -0.18, 0.55), (0.11, -0.18, 0.08), 60)],
            "dirsek90")
heat_render(lambda: S.rot("shin.R", -R(90)),
            [((-0.55, 0.45, 0.30), (-0.13, 0.08, 0.10), 60), ((-0.30, 0.62, 0.45), (-0.12, 0.10, 0.08), 60)],
            "diz90")
heat_render(lambda: (S.rot("thigh.R", R(35)), S.rot("shin.R", -R(60)), S.rot("foot.R", R(40))),
            [((-0.55, 0.45, 0.30), (-0.13, 0.08, 0.10), 60)],
            "arka_adim")
heat_render(lambda: [S.rot(f"tail_{i:02d}", 0, 0, R(29)) for i in range(1, 7)],
            [((0.45, 0.62, 0.35), (0.02, 0.32, 0.06), 60)],
            "kuyruk")
heat_render(lambda: (S.rot("ear.L", R(35)), S.rot("ear_02.L", R(20)), S.rot("ear.R", 0, R(30), 0)),
            [((0.42, -0.55, 0.62), (0.10, -0.24, 0.38), 85)],
            "kulak")
heat_render(lambda: (S.rot("hips", R(12)), S.rot("spine_01", R(17)), S.rot("spine_02", R(17)),
                     S.rot("spine_03", R(17)), S.rot("neck", -R(14))),
            [((0.95, -0.35, 0.55), (0.0, 0.05, 0.25), 45)],
            "omurga")
S.reset_pose()
print("HEAT DONE")
