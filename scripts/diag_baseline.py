"""S0: Baseline teshis — 90° ROM pozlari altinda parcalanma/yamulma olcumu.
Metrikler:
  - edge stretch: pozlu/rest kenar uzunluk orani (p99, max) bolge bazli
  - shell gap: kabuk adalarinin govdeye gore ayrisma artisi (mm)
Renderlar: her poz icin ilgili bolgenin yakin cekimi.
"""
import bpy, math, os, sys, json
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.append("/tmp/rig")
import plan_data as P

OUT = "/tmp/rig/td/baseline"
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath="/tmp/rig/mouse_rig.blend")
C, D = bpy.context, bpy.data
mouse = D.objects["Mouse"]
arm = D.objects["MouseRig"]
me = mouse.data
NV = len(me.vertices)

pid = np.empty(NV, dtype=np.int32)
me.attributes["part_id"].data.foreach_get("value", pid)
IDS = {n: i for i, n in enumerate(P.MESH_RENAME.values())}
CO = np.empty(NV * 3)
me.vertices.foreach_get("co", CO)
CO = CO.reshape(NV, 3)

# ---- weights ----
gnames = {g.index: g.name for g in mouse.vertex_groups}
GW = {gn: np.zeros(NV) for gn in gnames.values()}
for v in me.vertices:
    for ge in v.groups:
        GW[gnames[ge.group]][v.index] = ge.weight

# ---- edges ----
NE = len(me.edges)
EV = np.empty(NE * 2, dtype=np.int32)
me.edges.foreach_get("vertices", EV)
EV = EV.reshape(NE, 2)
rest_len = np.linalg.norm(CO[EV[:, 0]] - CO[EV[:, 1]], axis=1)

wh_mask = (pid == IDS["whiskers_L"]) | (pid == IDS["whiskers_R"])

def zone_mask(bones, thr=0.3):
    s = np.zeros(NV)
    for b in bones:
        if b in GW:
            s += GW[b]
    return (s > thr) & ~wh_mask

ZONES = {
    "boyun":   zone_mask(["neck", "head"]),
    "omuz_L":  zone_mask(["shoulder.L", "upper_arm.L"]),
    "dirsek_L": zone_mask(["upper_arm.L", "forearm.L"]),
    "bilek_L": zone_mask(["forearm.L", "hand.L"]),
    "kalca_L": zone_mask(["hips", "thigh.L"]) & (CO[:, 0] > 0.02),
    "diz_R":   zone_mask(["thigh.R", "shin.R"]),
    "topuk_R": zone_mask(["shin.R", "foot.R"]),
    "kuyruk_koku": zone_mask(["hips", "tail_01", "tail_02"]) & (CO[:, 1] > 0.2),
    "kulak_L": (pid == IDS["ear_L"]),
    "omurga":  zone_mask(["spine_01", "spine_02", "spine_03"]),
}

# ---- shell gap pairs (rest) ----
body_idx = np.where(pid == IDS["body"])[0]
from mathutils import kdtree
kd = kdtree.KDTree(len(body_idx))
for j, vi in enumerate(body_idx):
    kd.insert(Vector(CO[vi]), j)
kd.balance()
PAIRS = {}
for isl in ("paw_front_L", "paw_front_R", "foot_hind_L", "foot_hind_R", "tail", "ear_L", "ear_R"):
    prs = []
    for vi in np.where(pid == IDS[isl])[0]:
        co, j, dist = kd.find(Vector(CO[vi]))
        if dist < 0.008:
            prs.append((int(vi), int(body_idx[j]), float(dist)))
    PAIRS[isl] = prs

# ---- cams ----
scene = C.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 24
scene.cycles.use_denoising = True
scene.render.resolution_x = 900
scene.render.resolution_y = 900
scene.view_settings.view_transform = 'AgX'
world = D.worlds.new("W"); scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (1, 1, 1, 1)
world.node_tree.nodes["Background"].inputs[1].default_value = 0.85
sun = D.objects.new("Sun", D.lights.new("S", 'SUN'))
sun.data.energy = 2.3
scene.collection.objects.link(sun)
sun.rotation_euler = (math.radians(50), math.radians(8), math.radians(35))

def look_cam(name, loc, target, lens=70):
    cd = D.cameras.new(name); cd.lens = lens
    cam = D.objects.new(name, cd)
    scene.collection.objects.link(cam)
    cam.location = loc
    cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    return cam

CAMS = {
    "arm_L":  look_cam("c1", (0.52, -0.62, 0.28), (0.10, -0.19, 0.12)),
    "hind_R": look_cam("c2", (-0.60, 0.52, 0.30), (-0.13, 0.08, 0.10)),
    "head":   look_cam("c3", (0.52, -0.72, 0.50), (0.0, -0.27, 0.27)),
    "tail":   look_cam("c4", (0.55, 0.70, 0.34), (0.03, 0.32, 0.06)),
    "body":   look_cam("c5", (1.00, -0.40, 0.52), (0.0, 0.02, 0.22), 40),
    "ear_L":  look_cam("c6", (0.42, -0.55, 0.62), (0.10, -0.24, 0.38), 85),
}

pb = arm.pose.bones
for c in [c for b in pb for c in b.constraints if c.type == 'IK']:
    c.influence = 0.0

def reset_pose():
    for b in pb:
        b.location = (0, 0, 0); b.rotation_mode = 'XYZ'
        b.rotation_euler = (0, 0, 0); b.scale = (1, 1, 1)

def rot(bn, rx=0, ry=0, rz=0):
    pb[bn].rotation_mode = 'XYZ'
    pb[bn].rotation_euler = (rx, ry, rz)

R90 = math.radians(90)
POSES = {
    "dirsek90_L": (lambda: rot("forearm.L", R90), ["arm_L"], ["dirsek_L", "bilek_L"]),
    "diz90_R": (lambda: rot("shin.R", -R90), ["hind_R"], ["diz_R", "topuk_R"]),
    "omuz_kaldir_L": (lambda: rot("upper_arm.L", -math.radians(70)), ["arm_L"], ["omuz_L", "dirsek_L"]),
    "omurga_kivrim": (lambda: (rot("hips", math.radians(12)), rot("spine_01", math.radians(17)),
                               rot("spine_02", math.radians(17)), rot("spine_03", math.radians(17)),
                               rot("neck", math.radians(-14))), ["body"], ["omurga", "boyun"]),
    "kuyruk_kivrim": (lambda: [rot(f"tail_{i:02d}", 0, 0, math.radians(29)) for i in range(1, 7)],
                      ["tail"], ["kuyruk_koku"]),
    "bas_donus": (lambda: (rot("neck", 0, 0, math.radians(28)), rot("head", 0, 0, math.radians(34))),
                  ["head"], ["boyun"]),
    "kulak_don": (lambda: (rot("ear.L", math.radians(35)), rot("ear_02.L", math.radians(20)),
                           rot("ear.R", 0, math.radians(30), 0)), ["ear_L", "head"], ["kulak_L"]),
    "ekstrem": (lambda: (rot("hips", math.radians(10)), rot("spine_01", math.radians(15)),
                         rot("spine_02", math.radians(15)), rot("spine_03", math.radians(14)),
                         rot("neck", math.radians(-10), 0, math.radians(22)),
                         rot("head", 0, 0, math.radians(28)),
                         rot("upper_arm.L", -math.radians(55)), rot("forearm.L", math.radians(70)),
                         rot("thigh.R", math.radians(35)), rot("shin.R", -math.radians(60)),
                         [rot(f"tail_{i:02d}", 0, 0, math.radians(22)) for i in range(1, 7)]),
                ["body", "arm_L", "hind_R"], list(ZONES)),
}

def posed_coords():
    C.view_layer.update()
    dg = C.evaluated_depsgraph_get()
    mev = mouse.evaluated_get(dg)
    pc = np.empty(NV * 3)
    mev.data.vertices.foreach_get("co", pc)
    return pc.reshape(NV, 3)

report = {}
for pname, (fn, views, zones) in POSES.items():
    reset_pose()
    fn()
    pc = posed_coords()
    plen = np.linalg.norm(pc[EV[:, 0]] - pc[EV[:, 1]], axis=1)
    ratio = plen / np.maximum(rest_len, 1e-9)
    rep = {"zones": {}, "gaps": {}}
    for z in zones:
        m = ZONES[z]
        em = m[EV[:, 0]] & m[EV[:, 1]]
        if em.sum() < 10:
            continue
        r = ratio[em]
        rep["zones"][z] = {"p99": float(np.quantile(r, 0.99)), "max": float(r.max()),
                           "min": float(r.min()), "edges": int(em.sum())}
    for isl, prs in PAIRS.items():
        if not prs:
            continue
        inc = [float(np.linalg.norm(pc[a] - pc[b]) - d) for a, b, d in prs]
        rep["gaps"][isl] = {"max_mm": max(inc) * 1000, "p95_mm": float(np.quantile(inc, 0.95)) * 1000}
    report[pname] = rep
    scene.camera = None
    for v in views:
        scene.camera = CAMS[v]
        scene.render.filepath = f"{OUT}/{pname}_{v}.png"
        bpy.ops.render.render(write_still=True)

reset_pose()
C.view_layer.update()
for v, cam in CAMS.items():
    scene.camera = cam
    scene.render.filepath = f"{OUT}/rest_{v}.png"
    bpy.ops.render.render(write_still=True)

with open(f"{OUT}/metrics.json", "w") as f:
    json.dump(report, f, indent=1)

print("==== BASELINE METRIKLER ====")
for pname, rep in report.items():
    worst_z = sorted(rep["zones"].items(), key=lambda kv: -kv[1]["max"])[:3]
    zs = " | ".join(f"{z}: p99={d['p99']:.2f} max={d['max']:.2f}" for z, d in worst_z)
    print(f"{pname}: {zs}")
    gaps = sorted(rep["gaps"].items(), key=lambda kv: -kv[1]["max_mm"])[:3]
    gs = " | ".join(f"{i}: max={d['max_mm']:.1f}mm" for i, d in gaps)
    print(f"   GAP: {gs}")
print("BASELINE DONE")
