"""Torso cekirdek agirliklari = omurga ekseni arclength'inin SAF fonksiyonu.
Radyal sabitlik => ust uste kabuklar ayni kesitte OZDES hareket eder (tup bukumu).
Buyuk spine/neck duzelticileri kaldirilir (artik gereksiz)."""
import sys, math
import numpy as np
sys.path.append("/tmp/rig/td"); sys.path.append("/tmp/rig")
import skinlib as SL
import bpy

S = SL.Skin("/tmp/rig/mouse_rig_td.blend")
C, D = bpy.context, bpy.data
mouse = S.mouse

def smooth01(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)

CORE = ["hips", "spine_01", "spine_02", "spine_03", "neck", "head", "snout"]
body = S.island("body")

# omurga poliline + eklem arclengthleri
# kuyruk kokunden burna: [hips.tail, hips.head, spine_01.tail, ..., snout.tail]
pts = [np.array(S.bone_pts("hips")[1]), np.array(S.bone_pts("hips")[0])]
for bn in CORE[1:]:
    pts.append(np.array(S.bone_pts(bn)[1]))
segs = []
acc = 0.0
jpos = [0.0]
for a, b in zip(pts, pts[1:]):
    L = float(np.linalg.norm(b - a))
    segs.append((a, b, acc, L))
    acc += L
    jpos.append(acc)
total = acc
print("eksen:", [round(x, 3) for x in jpos])

P = S.CO[body]
best_s = np.zeros(len(body)); best_d = np.full(len(body), 1e9)
for a, b, s0, L in segs:
    ab = b - a
    t = np.clip(((P - a) @ ab) / max(ab @ ab, 1e-12), 0, 1)
    proj = a + t[:, None] * ab[None]
    d = np.linalg.norm(P - proj, axis=1)
    m = d < best_d
    best_d[m] = d[m]; best_s[m] = s0 + t[m] * L


# telescoping partition (s uzerinde)
BANDS = [0.055, 0.055, 0.055, 0.050, 0.042, 0.038]   # eklem gecis bantlari
def ramp(u, j, band):
    return smooth01((u - (j - band)) / (2 * band))
nb = len(CORE)
Wc = []
for k in range(nb):
    lo = np.ones(len(body)) if k == 0 else ramp(best_s, jpos[k], BANDS[k - 1])
    hi = ramp(best_s, jpos[k + 1], BANDS[k]) if k < nb - 1 else np.zeros(len(body))
    Wc.append(np.clip(lo - hi, 0, 1))
sW = sum(Wc); sW[sW <= 1e-9] = 1.0

# mevcut cekirdek toplami korunur, ic dagilim s-partition olur
core_now = np.zeros(len(body))
for bn in CORE:
    core_now += S.GW[bn][body]
for k, bn in enumerate(CORE):
    S.GW[bn][body] = core_now * Wc[k] / sW

# burun ucu rijit kalsin
nose = body[S.CO[body][:, 1] < -0.465]
for g in S.GW:
    S.GW[g][nose] = 0.0
S.GW["snout"][nose] = 1.0

# ---- buyuk duzelticileri kaldir ----
DROP = ("crv_spine_curl", "crv_spine_arch", "crv_neck_yawL", "crv_neck_yawR")
if mouse.data.shape_keys:
    for kb in list(mouse.data.shape_keys.key_blocks):
        if kb.name in DROP:
            try:
                kb.driver_remove("value")
            except Exception:
                pass
            nm_ = kb.name
            mouse.shape_key_remove(kb)
            print("kaldirildi:", nm_)

# biyik tupleri yuz alanindan resync (cekirdek degisti)
from mathutils import Vector
from mathutils.bvhtree import BVHTree
body_set = set(int(v) for v in body)
polys = [tuple(p.vertices) for p in S.me.polygons]
body_polys = [pv for pv in polys if all(int(q) in body_set for q in pv)]
BODY_BVH = BVHTree.FromPolygons([tuple(v) for v in S.CO], body_polys)
def sample_body(p):
    co, n, fidx, dist = BODY_BVH.find_nearest(Vector(p))
    pvs = body_polys[fidx]
    ds = np.array([1.0 / (np.linalg.norm(S.CO[q] - np.array(co)) + 1e-6) for q in pvs])
    ds /= ds.sum()
    return {g: float(sum(S.GW[g][q] * w for q, w in zip(pvs, ds))) for g in S.GW}, dist
wh_idx = np.concatenate([S.island("whiskers_L"), S.island("whiskers_R")])
wh_set = set(int(i) for i in wh_idx)
uf = {int(i): int(i) for i in wh_idx}
def find(a):
    while uf[a] != a:
        uf[a] = uf[uf[a]]; a = uf[a]
    return a
for e in S.me.edges:
    a, b = int(e.vertices[0]), int(e.vertices[1])
    if a in wh_set and b in wh_set:
        ra, rb = find(a), find(b)
        if ra != rb:
            uf[ra] = rb
comps = {}
for i in wh_idx:
    comps.setdefault(find(int(i)), []).append(int(i))
for root, vc in comps.items():
    step = max(1, len(vc) // 40)
    rootv = min(((sample_body(S.CO[v])[1], v) for v in vc[::step]))[1]
    fld, _ = sample_body(S.CO[rootv])
    tot = sum(fld.values())
    for g in S.GW:
        S.GW[g][np.array(vc)] = fld.get(g, 0.0) / max(tot, 1e-9)
print(f"biyik resync: {len(comps)} tup")

# hijyen
names = list(S.GW)
Wall = np.stack([S.GW[g] for g in names])
Wall[Wall < 0.004] = 0.0
order = np.argsort(-Wall, axis=0)
keepm = np.zeros_like(Wall, dtype=bool)
for r in range(4):
    keepm[order[r], np.arange(S.NV)] = True
Wall = np.where(keepm, Wall, 0.0)
Wall = Wall / np.maximum(Wall.sum(0), 1e-9)
for i, g in enumerate(names):
    S.GW[g] = Wall[i]

S.save("/tmp/rig/mouse_rig_td.blend")
print("TORSO REPAINT OK")
