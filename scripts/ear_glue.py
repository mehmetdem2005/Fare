"""Kulak yapistirmasi: head payi KAFATASINA MESAFE fonksiyonu.
bd<=6mm: tam head (yapisik bag dokusu) -> bd>=14mm: tam kulak zinciri.
Zincir ici dagilim: geodezik telescoping (mevcut yontem)."""
import sys, heapq
import numpy as np
sys.path.append("/tmp/rig/td"); sys.path.append("/tmp/rig")
import skinlib as SL
from mathutils import Vector
from mathutils.bvhtree import BVHTree

S = SL.Skin("/tmp/rig/mouse_rig_td.blend")
for b in S.arm.data.bones:
    if b.use_deform and b.name not in S.GW:
        S.GW[b.name] = np.zeros(S.NV)

def smooth01(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)

body = S.island("body")
body_set = set(int(v) for v in body)
polys = [tuple(p.vertices) for p in S.me.polygons]
body_polys = [pv for pv in polys if all(int(q) in body_set for q in pv)]
BODY_BVH = BVHTree.FromPolygons([tuple(v) for v in S.CO], body_polys)

def geodesic(isl, src_local):
    iset = {int(v): k for k, v in enumerate(isl)}
    adj = [[] for _ in isl]
    for (a, b), L in zip(S.EV, S.rest_len):
        ia, ib = iset.get(int(a)), iset.get(int(b))
        if ia is not None and ib is not None:
            adj[ia].append((ib, L)); adj[ib].append((ia, L))
    # 2.5mm kopruler (parcali kulak)
    from mathutils import kdtree
    kd = kdtree.KDTree(len(isl))
    for k, vi in enumerate(isl):
        kd.insert(Vector(S.CO[vi]), k)
    kd.balance()
    for k, vi in enumerate(isl):
        for co, j, dist in kd.find_range(Vector(S.CO[vi]), 0.0025):
            if j != k:
                adj[k].append((j, max(dist, 1e-4)))
    dist = np.full(len(isl), np.inf)
    h = []
    for s in src_local:
        dist[s] = 0.0; heapq.heappush(h, (0.0, int(s)))
    while h:
        d, u = heapq.heappop(h)
        if d > dist[u] + 1e-12:
            continue
        for v, L in adj[u]:
            nd = d + L
            if nd < dist[v] - 1e-12:
                dist[v] = nd; heapq.heappush(h, (float(nd), int(v)))
    m = np.isfinite(dist)
    if (~m).any():
        dist[~m] = dist[m].max() if m.any() else 0.0
    return dist

for side, isl_name in (("L", "ear_L"), ("R", "ear_R")):
    chain = [b.name for b in S.arm.data.bones if b.name.startswith("ear") and b.name.endswith("." + side)]
    chain.sort(key=lambda n: (0 if n == f"ear.{side}" else int(n.split("_")[1].split(".")[0])))
    isl = S.island(isl_name)
    bd = np.array([BODY_BVH.find_nearest(Vector(S.CO[v]))[3] for v in isl])
    f_ear = smooth01((bd - 0.006) / 0.008)        # 6mm: head, 14mm: kulak
    # zincir partisyonu (alt halka kaynakli geodezik — sadece zincir ICI dagilim)
    src = np.where(bd < 0.007)[0]
    if len(src) < 4:
        src = np.argsort(bd)[:20]
    g = geodesic(isl, list(src))
    jp = [0.0]
    for bn in chain[1:]:
        h, t = S.bone_pts(bn)
        k = int(np.linalg.norm(S.CO[isl] - np.array(h), axis=1).argmin())
        jp.append(float(g[k]))
    h_l, t_l = S.bone_pts(chain[-1])
    k = int(np.linalg.norm(S.CO[isl] - np.array(t_l), axis=1).argmin())
    jp.append(float(g[k]))
    jp = np.array(jp)
    for i in range(1, len(jp)):
        jp[i] = max(jp[i], jp[i - 1] + 0.008)
    def ramp(u, j, band):
        return smooth01((u - (j - band)) / (2 * band))
    nb = len(chain)
    Wch = []
    for k in range(nb):
        band_hi = 0.35 * max(jp[k + 1] - jp[k], 0.008)
        lo = np.ones(len(isl)) if k == 0 else ramp(g, jp[k], 0.35 * max(jp[k] - jp[k - 1], 0.008))
        hi = ramp(g, jp[k + 1], band_hi) if k < nb - 1 else np.zeros(len(isl))
        Wch.append(np.clip(lo - hi, 0, 1))
    sW = sum(Wch); sW[sW <= 1e-9] = 1.0
    for gname in S.GW:
        S.GW[gname][isl] = 0.0
    S.GW["head"][isl] = 1.0 - f_ear
    for k, bn in enumerate(chain):
        S.GW[bn][isl] += Wch[k] / sW * f_ear
    glued = int((f_ear < 0.05).sum())
    print(f"{isl_name}: yapisik(taban) {glued}v / serbest {int((f_ear>0.95).sum())}v jp={[round(x*1000) for x in jp]}mm")

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
print("EAR GLUE OK")
