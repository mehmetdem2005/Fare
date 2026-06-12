"""RIG DUZELTMESI + voxel yeniden cozum.
1) Omurga zinciri hacim merkez hattina tasinir (dorsal -> centroid)
2) Voxel heat yeniden cozulur
3) Anatomik yasaklar: ventral orta serit, L/R capraz, kol-on (cene), gogus-head
4) Iade core'a (1/d^2, neck z<0.20 alici degil), top-4, dither relax
"""
import sys, math, time
import numpy as np
sys.path.append("/tmp/rig/td"); sys.path.append("/tmp/rig")
import skinlib as SL
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

S = SL.Skin("/tmp/rig/mouse_rig_td.blend")
C, D = bpy.context, bpy.data
t0 = time.time()

# ---------- 1. omurga merkez hatti ----------
NEW = {
    "hips":     ((0, 0.215, 0.205), (0, 0.292, 0.075)),
    "spine_01": ((0, 0.215, 0.205), (0, 0.105, 0.222)),
    "spine_02": ((0, 0.105, 0.222), (0, -0.012, 0.237)),
    "spine_03": ((0, -0.012, 0.237), (0, -0.125, 0.245)),
    "neck":     ((0, -0.125, 0.245), (0, -0.205, 0.287)),
}
arm_ob = S.arm
bpy.ops.object.select_all(action='DESELECT')
arm_ob.select_set(True)
C.view_layer.objects.active = arm_ob
bpy.ops.object.mode_set(mode='EDIT')
ebs = arm_ob.data.edit_bones
for bn, (h, t) in NEW.items():
    ebs[bn].head = h
    ebs[bn].tail = t
    ebs[bn].align_roll(Vector((0, 0, 1)))
bpy.ops.object.mode_set(mode='OBJECT')
print("OMURGA merkez hatta tasindi (hips/spine_01-03/neck)")

# ---------- 2. voxel resolve (govde) ----------
body = S.island("body")
body_mask = np.zeros(S.NV, bool); body_mask[body] = True
polys = [tuple(p.vertices) for p in S.me.polygons]
keep_polys = [pv for pv in polys if not any(S.wh_mask[q] for q in pv)]
BVH = BVHTree.FromPolygons([tuple(v) for v in S.CO], keep_polys)

H = 0.0055
pad = 0.012
lo = S.CO[~S.wh_mask].min(0) - pad
hi = S.CO[~S.wh_mask].max(0) + pad
dims = np.ceil((hi - lo) / H).astype(int) + 1
interior = np.zeros(dims, dtype=bool)
dvec = Vector((0, 0, 1))
for ix in range(dims[0]):
    x = lo[0] + (ix + 0.5) * H
    for iy in range(dims[1]):
        y = lo[1] + (iy + 0.5) * H
        o = Vector((x, y, lo[2] - 0.005))
        hits = []
        hit = BVH.ray_cast(o, dvec)
        guard = 0
        while hit[0] is not None and guard < 64:
            hits.append(hit[0].z)
            o = hit[0] + dvec * 1e-5
            hit = BVH.ray_cast(o, dvec)
            guard += 1
        for k in range(0, len(hits) - 1, 2):
            i0 = int(np.ceil((hits[k] - lo[2]) / H - 0.5))
            i1 = int(np.floor((hits[k + 1] - lo[2]) / H - 0.5))
            if i1 >= i0:
                interior[ix, iy, max(i0, 0):min(i1, dims[2] - 1) + 1] = True
print(f"interior {interior.sum()/1e3:.0f}k ({time.time()-t0:.0f}s)")

BONES = ["hips", "spine_01", "spine_02", "spine_03", "neck", "head", "snout",
         "tail_01", "tail_02"] + \
        [f"{n}.{s}" for n in ("shoulder", "upper_arm", "forearm", "hand", "front_toes",
                              "thigh", "shin", "foot", "toes") for s in ("L", "R")]
labels = np.full(dims, -1, dtype=np.int16)

def cell_of(p):
    return tuple(np.clip(((np.array(p) - lo) / H - 0.5).round().astype(int), 0, dims - 1))

def nearest_interior(c):
    if interior[c]:
        return c
    for r in (1, 2, 3):
        for dx in range(-r, r + 1):
            for dy in range(-r, r + 1):
                for dz in range(-r, r + 1):
                    cc = (c[0]+dx, c[1]+dy, c[2]+dz)
                    if 0 <= cc[0] < dims[0] and 0 <= cc[1] < dims[1] and 0 <= cc[2] < dims[2] and interior[cc]:
                        return cc
    return None

for bi, bn in enumerate(BONES):
    h, t = S.bone_pts(bn)
    n = max(int(np.linalg.norm(t - h) / (H * 0.5)), 2)
    for k in range(n + 1):
        c = nearest_interior(cell_of(h + (t - h) * (k / n)))
        if c is not None:
            labels[c] = bi
src_any = labels >= 0

def shifts(a, fill=0.0):
    out = []
    for ax in (0, 1, 2):
        for sgn in (1, -1):
            sh = np.roll(a, sgn, axis=ax)
            sl = [slice(None)] * 3
            sl[ax] = 0 if sgn == 1 else -1
            sh[tuple(sl)] = fill
            out.append(sh)
    return out

nbr_count = np.zeros(dims, dtype=np.float32)
for sh in shifts(interior.astype(np.float32)):
    nbr_count += sh
nbr_count[~interior] = 0
nbr_safe = np.maximum(nbr_count, 1)

vn = np.empty(S.NV * 3)
S.me.vertices.foreach_get("normal", vn)
vn = vn.reshape(S.NV, 3)
vc = []
for vi in body:
    p = S.CO[vi]
    c = cell_of(p)
    if not interior[c]:
        for step in (0.5, 1.0, 1.8, 2.6):
            c2 = cell_of(p - vn[vi] * (H * step))
            if interior[c2]:
                c = c2; break
        else:
            c2 = nearest_interior(c)
            c = c2 if c2 is not None else c
    vc.append(c)
vc = np.array(vc)

NVb = len(body)
W = np.zeros((len(BONES), NVb), dtype=np.float32)
ITERS = 300
for bi, bn in enumerate(BONES):
    f = np.zeros(dims, dtype=np.float32)
    own = labels == bi
    other = src_any & ~own
    f[own] = 1.0
    for it in range(ITERS):
        acc = np.zeros(dims, dtype=np.float32)
        for sh in shifts(f * interior):
            acc += sh
        f = acc / nbr_safe
        f[~interior] = 0.0
        f[own] = 1.0
        f[other] = 0.0
    W[bi] = f[vc[:, 0], vc[:, 1], vc[:, 2]]
print(f"VOXEL OK ({time.time()-t0:.0f}s)")

ssum = W.sum(0)
dead = ssum < 1e-6
W = W / np.maximum(ssum, 1e-9)

# ---------- 3. anatomik yasaklar ----------
def smooth01(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)

bx, by, bz = S.CO[body, 0], S.CO[body, 1], S.CO[body, 2]
bidx = {bn: i for i, bn in enumerate(BONES)}
LIMB = {"L": [f"{n}.L" for n in ("shoulder","upper_arm","forearm","hand","front_toes","thigh","shin","foot","toes")],
        "R": [f"{n}.R" for n in ("shoulder","upper_arm","forearm","hand","front_toes","thigh","shin","foot","toes")]}
removed = np.zeros(NVb, dtype=np.float32)

# (a) L/R capraz yasak
for s, sgn in (("L", 1), ("R", -1)):
    fac = smooth01((sgn * bx + 0.012) / 0.025)
    for bn in LIMB[s]:
        i = bidx[bn]
        d = W[i] * (1 - fac)
        removed += d; W[i] -= d

# (b) ventral orta serit: uzuv yasak (genis, alcak)
fac_v = np.maximum(smooth01((np.abs(bx) - 0.020) / 0.050), smooth01((bz - 0.085) / 0.05))
for s in ("L", "R"):
    for bn in LIMB[s]:
        i = bidx[bn]
        d = W[i] * (1 - fac_v)
        removed += d; W[i] -= d

# (c) kol zinciri cene/yanak hizasinda yasak (y<-0.30 VE z>0.13; bacagin kendisi muaf)
fac_arm = np.maximum(smooth01((by + 0.30) / 0.06), smooth01((0.13 - bz) / 0.04))
for s in ("L", "R"):
    for bn in (f"shoulder.{s}", f"upper_arm.{s}", f"forearm.{s}", f"hand.{s}", f"front_toes.{s}"):
        i = bidx[bn]
        d = W[i] * (1 - fac_arm)
        removed += d; W[i] -= d

# (d) gogus head/snout yasak (collar z-ramp; cene alti y<-0.30 MUAF)
collar = (by > -0.30) & (by < -0.08)
zgate = smooth01((bz - 0.135) / 0.085)
for bn in ("head", "snout"):
    i = bidx[bn]
    d = np.where(collar, W[i] * (1 - zgate), 0.0)
    removed += d; W[i] -= d

# (e) distal kemikler kapsul-mesafe kapisi: et kemigin uzerinde kalir,
#     uzaga sizan pay AYNI bacagin proksimal kemigine gider (core'a degil!)
def seg_dist_local(pts, a, b):
    a = np.array(a); b = np.array(b)
    ab = b - a
    t = np.clip(((pts - a) @ ab) / max(ab @ ab, 1e-12), 0, 1)
    return np.linalg.norm(pts - (a + t[:, None] * ab[None]), axis=1)

pts_body = S.CO[body]
DISTAL = {
    "front": dict(bones=("forearm", "hand", "front_toes"), recv="upper_arm", dmax=0.042, ramp=0.020),
    "hind":  dict(bones=("shin", "foot", "toes"), recv="thigh", dmax=0.048, ramp=0.020),
}
for s in ("L", "R"):
    for kind, spec in DISTAL.items():
        dmin = np.full(NVb, 1e9)
        for nm in spec["bones"]:
            h, t = S.bone_pts(f"{nm}.{s}")
            dmin = np.minimum(dmin, seg_dist_local(pts_body, h, t))
        keep = 1.0 - smooth01((dmin - spec["dmax"]) / spec["ramp"])
        moved = np.zeros(NVb, dtype=np.float32)
        for nm in spec["bones"]:
            i = bidx[f"{nm}.{s}"]
            d = W[i] * (1 - keep)
            moved += d; W[i] -= d
        W[bidx[f"{spec['recv']}.{s}"]] += moved

# (f) kuyruk govdede yalniz gercek kok civari (y>0.24 rampa)
tgate = smooth01((by - 0.24) / 0.05)
for bn in ("tail_01", "tail_02"):
    i = bidx[bn]
    d = W[i] * (1 - tgate)
    removed += d; W[i] -= d

# (g) skapula kapsul kapisi: omuz kemigi kafatasi tepesine tirmanamaz
for s in ("L", "R"):
    h, t = S.bone_pts(f"shoulder.{s}")
    dsh = seg_dist_local(pts_body, h, t)
    keep = 1.0 - smooth01((dsh - 0.055) / 0.022)
    i = bidx[f"shoulder.{s}"]
    d = W[i] * (1 - keep)
    removed += d; W[i] -= d

# iade: 2 en yakin core (neck z<0.20 yasak)
def seg_dist(pts, a, b):
    a = np.array(a); b = np.array(b)
    ab = b - a
    t = np.clip(((pts - a) @ ab) / max(ab @ ab, 1e-12), 0, 1)
    return np.linalg.norm(pts - (a + t[:, None] * ab[None]), axis=1)
COREN = ["hips", "spine_01", "spine_02", "spine_03", "neck"]
pts3 = S.CO[body]
Dm = np.stack([seg_dist(pts3, *S.bone_pts(b)) for b in COREN])
# neck yalniz GOBEKTE yasak (y>-0.10 & z<0.22); girtlakta mesru alici
Dm[COREN.index("neck")][(by > -0.10) & (bz < 0.22)] = 1e6
order = np.argsort(Dm, axis=0)
n1, n2 = order[0], order[1]
d1 = Dm[n1, np.arange(NVb)]; d2 = Dm[n2, np.arange(NVb)]
w1 = 1 / np.maximum(d1, 1e-4) ** 2
w2 = 1 / np.maximum(d2, 1e-4) ** 2
sw = w1 + w2
for k, bn in enumerate(COREN):
    i = bidx[bn]
    W[i] += np.where(n1 == k, removed * w1 / sw, 0) + np.where(n2 == k, removed * w2 / sw, 0)
print(f"yasaklar: {removed.sum():.0f} birim core'a tasindi")

# top-4 + normalize
W = W / np.maximum(W.sum(0), 1e-9)
top4 = np.argsort(-W, axis=0)[:4]
Wc = np.zeros_like(W)
for r in range(4):
    Wc[top4[r], np.arange(NVb)] = W[top4[r], np.arange(NVb)]
Wc = Wc / np.maximum(Wc.sum(0), 1e-9)

for g in S.GW:
    S.GW[g][body[~dead]] = 0.0
for bi, bn in enumerate(BONES):
    S.GW[bn][body[~dead]] = Wc[bi][~dead]
print(f"dead(eski korunur): {dead.sum()}")

# dither relax x2
nbr = [[] for _ in range(S.NV)]
for a, b in S.EV:
    nbr[a].append(b); nbr[b].append(a)
for _ in range(2):
    snap = {g: S.GW[g].copy() for g in S.GW}
    for vi in body:
        ns = [u for u in nbr[vi] if body_mask[u]]
        if not ns:
            continue
        for g in S.GW:
            S.GW[g][vi] = 0.6 * snap[g][vi] + 0.4 * float(np.mean([snap[g][u] for u in ns]))
S.normalize(body)

S.save("/tmp/rig/mouse_rig_td.blend")
print(f"SAVED ({time.time()-t0:.0f}s)")
