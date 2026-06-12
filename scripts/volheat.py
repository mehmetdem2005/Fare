"""Govde adasi icin HACIMSEL isi difuzyonu (voxel heat skinning).
- 5.5mm izgara, ic hacim ray-parite ile
- her kemik: kendi hucreleri Dirichlet=1, rakip kemik hucreleri Dirichlet=0,
  yuzeyde Neumann (maskeli komsu ortalamasi)
- vertex ornekleme: hucre + ic dogru kacis
Sadece BODY adasinin agirliklarini degistirir.
"""
import sys, math, time
import numpy as np
sys.path.append("/tmp/rig/td"); sys.path.append("/tmp/rig")
import skinlib as SL
from mathutils import Vector
from mathutils.bvhtree import BVHTree

S = SL.Skin("/tmp/rig/mouse_rig_td.blend")
t0 = time.time()

body = S.island("body")
body_mask = np.zeros(S.NV, bool); body_mask[body] = True

# BVH: biyik haric tum kabuklar (govde hacmini tanimlar)
polys = [tuple(p.vertices) for p in S.me.polygons]
keep_polys = [pv for pv in polys if not any(S.wh_mask[q] for q in pv)]
BVH = BVHTree.FromPolygons([tuple(v) for v in S.CO], keep_polys)

H = 0.0055
pad = 0.012
lo = S.CO[~S.wh_mask].min(0) - pad
hi = S.CO[~S.wh_mask].max(0) + pad
dims = np.ceil((hi - lo) / H).astype(int) + 1
print(f"GRID {dims} = {dims.prod()/1e6:.2f}M hucre, h={H*1000:.1f}mm")

interior = np.zeros(dims, dtype=bool)
zmin, zmax = lo[2], hi[2]
d = Vector((0, 0, 1))
for ix in range(dims[0]):
    x = lo[0] + (ix + 0.5) * H
    for iy in range(dims[1]):
        y = lo[1] + (iy + 0.5) * H
        o = Vector((x, y, zmin - 0.005))
        hits = []
        hit = BVH.ray_cast(o, d)
        guard = 0
        while hit[0] is not None and guard < 64:
            hits.append(hit[0].z)
            o = hit[0] + d * 1e-5
            hit = BVH.ray_cast(o, d)
            guard += 1
        for k in range(0, len(hits) - 1, 2):
            z0, z1 = hits[k], hits[k + 1]
            i0 = int(np.ceil((z0 - lo[2]) / H - 0.5))
            i1 = int(np.floor((z1 - lo[2]) / H - 0.5))
            if i1 >= i0:
                interior[ix, iy, max(i0, 0):min(i1, dims[2] - 1) + 1] = True
print(f"interior: {interior.sum()/1e3:.0f}k hucre ({time.time()-t0:.0f}s)")

# ---- kemik hucreleri ----
BONES = ["hips", "spine_01", "spine_02", "spine_03", "neck", "head", "snout",
         "tail_01", "tail_02"] + \
        [f"{n}.{s}" for n in ("shoulder", "upper_arm", "forearm", "hand", "front_toes",
                              "thigh", "shin", "foot", "toes") for s in ("L", "R")]
labels = np.full(dims, -1, dtype=np.int16)

def cell_of(p):
    return tuple(np.clip(((p - lo) / H - 0.5).round().astype(int), 0, dims - 1))

def nearest_interior(c):
    if interior[c]:
        return c
    best = None
    for r in (1, 2, 3):
        for dx in range(-r, r + 1):
            for dy in range(-r, r + 1):
                for dz in range(-r, r + 1):
                    cc = (c[0] + dx, c[1] + dy, c[2] + dz)
                    if 0 <= cc[0] < dims[0] and 0 <= cc[1] < dims[1] and 0 <= cc[2] < dims[2] and interior[cc]:
                        return cc
    return None

for bi, bn in enumerate(BONES):
    h, t = S.bone_pts(bn)
    L = np.linalg.norm(t - h)
    n = max(int(L / (H * 0.5)), 2)
    for k in range(n + 1):
        p = h + (t - h) * (k / n)
        c = nearest_interior(cell_of(p))
        if c is not None:
            labels[c] = bi
src_any = labels >= 0
print(f"kaynak hucre: {src_any.sum()}")

# ---- maskeli Jacobi comsu ortalamasi altyapisi ----
inter = interior
nbr_count = np.zeros(dims, dtype=np.float32)
def shifts(a, fill=0.0):
    out = []
    for ax in (0, 1, 2):
        for sgn in (1, -1):
            sh = np.roll(a, sgn, axis=ax)
            # roll'un sardigi dilimi sifirla
            sl = [slice(None)] * 3
            sl[ax] = 0 if sgn == 1 else -1
            sh[tuple(sl)] = fill
            out.append(sh)
    return out
for sh in shifts(inter.astype(np.float32)):
    nbr_count += sh
nbr_count[~inter] = 0
nbr_safe = np.maximum(nbr_count, 1)

ITERS = 340
NVb = len(body)
verts_cells = []
norms = np.zeros((S.NV, 3))
S.me.calc_normals_split() if hasattr(S.me, 'calc_normals_split') else None
vn = np.empty(S.NV * 3)
S.me.vertices.foreach_get("normal", vn)
vn = vn.reshape(S.NV, 3)
for vi in body:
    p = S.CO[vi]
    c = cell_of(p)
    if not interior[c]:
        for step in (0.5, 1.0, 1.8, 2.6):
            c2 = cell_of(p - vn[vi] * (H * step))
            if interior[c2]:
                c = c2
                break
        else:
            c2 = nearest_interior(c)
            c = c2 if c2 is not None else c
    verts_cells.append(c)
vc = np.array(verts_cells)

W_new = np.zeros((len(BONES), NVb), dtype=np.float32)
for bi, bn in enumerate(BONES):
    f = np.zeros(dims, dtype=np.float32)
    own = labels == bi
    other = src_any & ~own
    f[own] = 1.0
    for it in range(ITERS):
        acc = np.zeros(dims, dtype=np.float32)
        for sh in shifts(f * inter):
            acc += sh
        f = acc / nbr_safe
        f[~inter] = 0.0
        f[own] = 1.0
        f[other] = 0.0
    W_new[bi] = f[vc[:, 0], vc[:, 1], vc[:, 2]]
    print(f"  {bn}: alan max={W_new[bi].max():.2f} ort={W_new[bi].mean():.3f}")

# normalize + top4
ssum = W_new.sum(0)
dead = ssum < 1e-6
print(f"VOXEL OK ({time.time()-t0:.0f}s) bos vert: {dead.sum()}")
W_new = W_new / np.maximum(ssum, 1e-9)
top4 = np.argsort(-W_new, axis=0)[:4]
W_clamped = np.zeros_like(W_new)
for r in range(4):
    idx = top4[r], np.arange(NVb)
    W_clamped[idx] = W_new[idx]
W_clamped = W_clamped / np.maximum(W_clamped.sum(0), 1e-9)

# govdeye yaz (dead vertler eski agirligini korur)
for g in S.GW:
    S.GW[g][body[~dead]] = 0.0
for bi, bn in enumerate(BONES):
    S.GW[bn][body[~dead]] = W_clamped[bi][~dead]

# hafif dither relax (voxel aliasing) — 1 iter, yalniz govde
nbr = [[] for _ in range(S.NV)]
for a, b in S.EV:
    nbr[a].append(b); nbr[b].append(a)
snap = {g: S.GW[g].copy() for g in S.GW}
for vi in body:
    ns = [u for u in nbr[vi] if body_mask[u]]
    if not ns:
        continue
    for g in S.GW:
        S.GW[g][vi] = 0.6 * snap[g][vi] + 0.4 * float(np.mean([snap[g][u] for u in ns]))
S.normalize(body)

S.save("/tmp/rig/mouse_rig_td.blend")
print("SAVED")
