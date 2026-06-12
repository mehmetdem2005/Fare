"""Final dogrulama: 8 poz x (clay+textured) yakin cekim, kabuk-ayrisma
metrikleri, ROM animasyon kareleri (GIF icin) + action kaydi."""
import sys, math, os, json
import numpy as np
sys.path.append("/tmp/rig/td"); sys.path.append("/tmp/rig")
import skinlib as SL
import bpy
from mathutils import Vector
from mathutils import kdtree

OUT = "/tmp/rig/td/final"
os.makedirs(OUT, exist_ok=True)
os.makedirs(OUT + "/anim", exist_ok=True)
S = SL.Skin("/tmp/rig/mouse_rig_td.blend")
scene = SL.setup_render(samples=22, res=840)
R = math.radians
C, D = bpy.context, bpy.data

clay = D.materials.new("clay")
clay.use_nodes = True
cb = clay.node_tree.nodes["Principled BSDF"]
cb.inputs["Base Color"].default_value = (0.76, 0.74, 0.71, 1)
cb.inputs["Roughness"].default_value = 0.62

CAMS = {
    "arm_L":  SL.look_cam("v_arm", (0.50, -0.60, 0.30), (0.10, -0.19, 0.13), 62),
    "hind_R": SL.look_cam("v_hind", (-0.58, 0.50, 0.32), (-0.13, 0.08, 0.10), 62),
    "head":   SL.look_cam("v_head", (0.52, -0.70, 0.52), (0.0, -0.26, 0.27), 58),
    "tail":   SL.look_cam("v_tail", (0.55, 0.70, 0.36), (0.03, 0.32, 0.06), 62),
    "body":   SL.look_cam("v_body", (1.02, -0.42, 0.52), (0.0, 0.02, 0.22), 40),
    "ear_L":  SL.look_cam("v_ear", (0.42, -0.55, 0.62), (0.10, -0.24, 0.38), 80),
    "persp":  SL.look_cam("v_persp", (0.95, -1.05, 0.80), (0.0, 0.0, 0.227), 50),
}

POSES = {
    "dirsek90": (lambda: S.rot("forearm.L", R(90)), ["arm_L"]),
    "diz90": (lambda: S.rot("shin.R", -R(90)), ["hind_R"]),
    "omuz70": (lambda: S.rot("upper_arm.L", -R(70)), ["arm_L"]),
    "bas_donus": (lambda: (S.rot("neck", 0, 0, R(28)), S.rot("head", 0.1, 0, R(34))), ["head"]),
    "omurga_curl": (lambda: (S.rot("hips", R(12)), S.rot("spine_01", R(17)), S.rot("spine_02", R(17)),
                             S.rot("spine_03", R(17)), S.rot("neck", -R(14))), ["body"]),
    "kuyruk_curl": (lambda: [S.rot(f"tail_{i:02d}", R(4), 0, R(29)) for i in range(1, 7)], ["tail"]),
    "kulak": (lambda: (S.rot("ear.L", R(35)), S.rot("ear_02.L", R(20)), S.rot("ear.R", 0, R(30), 0)), ["ear_L", "head"]),
    "ekstrem": (lambda: (S.rot("hips", R(10)), S.rot("spine_01", R(15)), S.rot("spine_02", R(15)),
                         S.rot("spine_03", R(14)), S.rot("neck", -R(10), 0, R(22)),
                         S.rot("head", 0, 0, R(28)), S.rot("upper_arm.L", -R(55)),
                         S.rot("forearm.L", R(70)), S.rot("thigh.R", R(35)), S.rot("shin.R", -R(60)),
                         [S.rot(f"tail_{i:02d}", 0, 0, R(22)) for i in range(1, 7)]), ["persp", "body"]),
}

# ---- kabuk ayrisma (parcalanma) metrigi ----
body = S.island("body")
kd = kdtree.KDTree(len(body))
for j, vi in enumerate(body):
    kd.insert(Vector(S.CO[vi]), j)
kd.balance()
PAIRS = {}
for isl in ("paw_front_L", "paw_front_R", "foot_hind_L", "foot_hind_R", "tail", "ear_L", "ear_R"):
    prs = []
    for vi in S.island(isl):
        co, j, dist = kd.find(Vector(S.CO[vi]))
        if dist < 0.0055:
            prs.append((int(vi), int(body[j]), float(dist)))
    PAIRS[isl] = prs

gap_report = {}
for pname, (fn, views) in POSES.items():
    S.reset_pose(); fn()
    pc = S.posed_coords()
    worst = {}
    for isl, prs in PAIRS.items():
        if not prs:
            continue
        inc = max(float(np.linalg.norm(pc[a] - pc[b]) - d) for a, b, d in prs)
        worst[isl] = round(inc * 1000, 2)
    gap_report[pname] = worst
    for st, mat in (("tex", None), ("clay", clay)):
        C.view_layer.material_override = mat
        for v in views:
            SL.render(f"{OUT}/{pname}_{v}_{st}.png", CAMS[v])
C.view_layer.material_override = None
S.reset_pose()
SL.render(f"{OUT}/rest_persp_tex.png", CAMS["persp"])

print("GAP RAPORU (mm, yapisma siniri):")
for p, w in gap_report.items():
    mx = max(w.values()) if w else 0
    print(f"  {p}: max={mx} | " + " ".join(f"{k}:{v}" for k, v in sorted(w.items(), key=lambda kv: -kv[1])[:3]))
json.dump(gap_report, open(f"{OUT}/gaps.json", "w"))

# ---- ROM animasyonu: action olustur + kareleri render et ----
arm = S.arm
act = D.actions.new("ROM_test")
arm.animation_data_create()
arm.animation_data.action = act
FPS = 24
def key_at(f):
    for pb in arm.pose.bones:
        pb.keyframe_insert("rotation_euler", frame=f)

S.reset_pose(); key_at(1)
S.rot("neck", 0, 0, R(25)); S.rot("head", 0, 0, R(30)); key_at(12)
S.reset_pose(); S.rot("neck", R(15)); S.rot("head", R(18)); key_at(22)
S.reset_pose(); S.rot("upper_arm.L", -R(60)); S.rot("forearm.L", R(70)); S.rot("hand.L", -R(30)); key_at(34)
S.reset_pose(); S.rot("thigh.R", R(40)); S.rot("shin.R", -R(70)); S.rot("foot.R", R(40)); key_at(46)
S.reset_pose()
S.rot("hips", R(12)); S.rot("spine_01", R(16)); S.rot("spine_02", R(16)); S.rot("spine_03", R(15)); key_at(58)
S.reset_pose()
for i in range(1, 7):
    S.rot(f"tail_{i:02d}", 0, 0, R(28))
key_at(70)
S.reset_pose()
for i in range(1, 7):
    S.rot(f"tail_{i:02d}", 0, 0, -R(28))
key_at(80)
S.reset_pose(); S.rot("ear.L", R(40)); S.rot("ear_02.L", R(22)); S.rot("ear.R", 0, R(30), 0); key_at(90)
S.reset_pose(); key_at(100)

scene.frame_start = 1
scene.frame_end = 100
scene.render.resolution_x = 560
scene.render.resolution_y = 560
scene.cycles.samples = 12
for f in range(1, 101, 3):
    scene.frame_set(f)
    SL.render(f"{OUT}/anim/f{f:03d}.png", CAMS["persp"])

bpy.ops.wm.save_as_mainfile(filepath="/tmp/rig/mouse_rig_td.blend")
print("VALIDATE DONE")
