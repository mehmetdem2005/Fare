"""Kabuk-yigini esitleme v2: her vertexten +/-normal yonunde isin atilir,
6mm icinde paralel-yuzeyli panel bulunursa agirliklar harmanlanir (2 iter).
Transitif zincir yok — yalniz gercek ust/alt panel ciftleri."""
import sys
import numpy as np
sys.path.append("/tmp/rig/td"); sys.path.append("/tmp/rig")
import skinlib as SL
from mathutils import Vector
from mathutils.bvhtree import BVHTree

S = SL.Skin("/tmp/rig/mouse_rig_td.blend")
for b in S.arm.data.bones:
    if b.use_deform and b.name not in S.GW:
        S.GW[b.name] = np.zeros(S.NV)

VN = np.empty(S.NV * 3)
S.me.vertices.foreach_get("normal", VN)
VN = VN.reshape(S.NV, 3)
VN = VN / np.maximum(np.linalg.norm(VN, axis=1)[:, None], 1e-9)

body = S.island("body")
body_set = set(int(v) for v in body)
polys = [tuple(p.vertices) for p in S.me.polygons]
body_polys = [pv for pv in polys if all(int(q) in body_set for q in pv)]
BVH = BVHTree.FromPolygons([tuple(v) for v in S.CO], body_polys)
names = list(S.GW)

MAXD = 0.006
total_pairs = 0
for it in range(2):
    snap = {g: S.GW[g].copy() for g in names}
    cnt = 0
    for vi in body:
        n = Vector(VN[vi])
        o = Vector(S.CO[vi])
        partners = []
        for sgn in (1.0, -1.0):
            hit = BVH.ray_cast(o + n * (sgn * 0.0006), n * sgn, MAXD)
            if hit[0] is None:
                continue
            hn = hit[1]
            if abs(float(hn.dot(n))) < 0.5:
                continue                          # paralel panel degil
            pvs = body_polys[hit[2]]
            ds = np.array([1.0 / (float((Vector(S.CO[q]) - hit[0]).length) + 1e-6) for q in pvs])
            ds /= ds.sum()
            partners.append({g: float(sum(snap[g][q] * w for q, w in zip(pvs, ds))) for g in names})
        if not partners:
            continue
        cnt += 1
        for g in names:
            pm = float(np.mean([p[g] for p in partners]))
            S.GW[g][vi] = 0.5 * snap[g][vi] + 0.5 * pm
    total_pairs = cnt
    print(f"iter {it+1}: {cnt} vertex panel-esitlendi")

# hijyen
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
print("STACK v2 OK")
