"""KESIN cozum: dilate + trilinear voxel alan projeksiyonu.
Govde+pati+ayak vertexleri TEK surekli 3B alandan ornekler =>
cakisan kabuklar ayni agirligi alir, yirtilma yapisal olarak imkansiz.
Kulak/kuyruk adalari mevcut (geodezik) cozumlerini korur."""
import sys, math, time
import numpy as np
sys.path.append("/tmp/rig/td"); sys.path.append("/tmp/rig")
import skinlib as SL
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils import kdtree

S = SL.Skin("/tmp/rig/mouse_rig_td.blend")
for b in S.arm.data.bones:
    if b.use_deform and b.name not in S.GW:
        S.GW[b.name] = np.zeros(S.NV)
C, D = bpy.context, bpy.data
t0 = time.time()

def smooth01(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)

TARGET_ISL = ["body", "paw_front_L", "paw_front_R", "foot_hind_L", "foot_hind_R"]
tgt_idx = np.concatenate([S.island(n) for n in TARGET_ISL])

polys = [tuple(p.vertices) for p in S.me.polygons]
keep_polys = [pv for pv in polys if not any(S.wh_mask[q] for q in pv)]
BVH = BVHTree.FromPolygons([tuple(v) for v in S.CO], keep_polys)

H = 0.0055
lo = S.CO[~S.wh_mask].min(0) - 0.012
hi = S.CO[~S.wh_mask].max(0) + 0.012
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
        g = 0
        while hit[0] is not None and g < 64:
            hits.append(hit[0].z)
            o = hit[0] + dvec * 1e-5
            hit = BVH.ray_cast(o, dvec)
            g += 1
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
                    if all(0 <= cc[i] < dims[i] for i in range(3)) and interior[cc]:
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

# trilinear ornekleme koordinatlari
gp = (S.CO[tgt_idx] - lo) / H - 0.5
g0 = np.floor(gp).astype(int)
fr = gp - g0
g0 = np.clip(g0, 0, np.array(dims) - 2)

def trilinear(F):
    x0, y0, z0 = g0[:, 0], g0[:, 1], g0[:, 2]
    fx, fy, fz = fr[:, 0], fr[:, 1], fr[:, 2]
    c000 = F[x0, y0, z0]; c100 = F[x0+1, y0, z0]; c010 = F[x0, y0+1, z0]; c110 = F[x0+1, y0+1, z0]
    c001 = F[x0, y0, z0+1]; c101 = F[x0+1, y0, z0+1]; c011 = F[x0, y0+1, z0+1]; c111 = F[x0+1, y0+1, z0+1]
    c00 = c000*(1-fx)+c100*fx; c10 = c010*(1-fx)+c110*fx
    c01 = c001*(1-fx)+c101*fx; c11 = c011*(1-fx)+c111*fx
    return (c00*(1-fy)+c10*fy)*(1-fz) + (c01*(1-fy)+c11*fy)*fz

ITERS = 300
NT = len(tgt_idx)
W = np.zeros((len(BONES), NT), dtype=np.float32)
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
    # disari dolgu (dilation): kabuk disindaki hucreler en yakin ic degerini alir
    filled = interior.copy()
    for _ in range(4):
        fc = np.zeros(dims, dtype=np.float32)
        cn = np.zeros(dims, dtype=np.float32)
        for sh, shf in zip(shifts(f * filled), shifts(filled.astype(np.float32))):
            fc += sh; cn += shf
        newly = (~filled) & (cn > 0)
        f[newly] = fc[newly] / cn[newly]
        filled |= newly
    W[bi] = trilinear(f)
print(f"VOXEL+DILATE+TRILINEAR OK ({time.time()-t0:.0f}s)")

ssum = W.sum(0)
dead = ssum < 1e-6
W = W / np.maximum(ssum, 1e-9)

# ---------- anatomik yasaklar (kalibre edilmis set) ----------
bx, by, bz = S.CO[tgt_idx, 0], S.CO[tgt_idx, 1], S.CO[tgt_idx, 2]
bidx = {bn: i for i, bn in enumerate(BONES)}
LIMB = {"L": [f"{n}.L" for n in ("shoulder","upper_arm","forearm","hand","front_toes","thigh","shin","foot","toes")],
        "R": [f"{n}.R" for n in ("shoulder","upper_arm","forearm","hand","front_toes","thigh","shin","foot","toes")]}
removed = np.zeros(NT, dtype=np.float32)
pid_t = S.pid[tgt_idx]
import plan_data as P
IDS = {n: i for i, n in enumerate(P.MESH_RENAME.values())}
is_body = pid_t == IDS["body"]

def seg_dist(pts, a, b):
    a = np.array(a); b = np.array(b)
    ab = b - a
    t = np.clip(((pts - a) @ ab) / max(ab @ ab, 1e-12), 0, 1)
    return np.linalg.norm(pts - (a + t[:, None] * ab[None]), axis=1)
pts3 = S.CO[tgt_idx]

# L/R capraz (sadece body — patiler kendi tarafinda zaten)
for s, sgn in (("L", 1), ("R", -1)):
    fac = smooth01((sgn * bx + 0.012) / 0.025)
    for bn in LIMB[s]:
        i = bidx[bn]
        d = W[i] * (1 - fac) * is_body
        removed += d; W[i] -= d
# ventral
fac_v = np.maximum(smooth01((np.abs(bx) - 0.020) / 0.050), smooth01((bz - 0.085) / 0.05))
for s in ("L", "R"):
    for bn in LIMB[s]:
        i = bidx[bn]
        d = W[i] * (1 - fac_v) * is_body
        removed += d; W[i] -= d
# kol-cene
fac_arm = np.maximum(smooth01((by + 0.30) / 0.06), smooth01((0.13 - bz) / 0.04))
for s in ("L", "R"):
    for bn in (f"shoulder.{s}", f"upper_arm.{s}", f"forearm.{s}", f"hand.{s}", f"front_toes.{s}"):
        i = bidx[bn]
        d = W[i] * (1 - fac_arm) * is_body
        removed += d; W[i] -= d
# gogus head/snout
collar = (by > -0.30) & (by < -0.08)
zgate = smooth01((bz - 0.135) / 0.085)
for bn in ("head", "snout"):
    i = bidx[bn]
    d = np.where(collar & is_body, W[i] * (1 - zgate), 0.0)
    removed += d; W[i] -= d
# distal kapsul kapilari (alici: proksimal)
DISTAL = {"front": (("forearm", "hand", "front_toes"), "upper_arm", 0.042, 0.020),
          "hind": (("shin", "foot", "toes"), "thigh", 0.048, 0.020)}
for s in ("L", "R"):
    for kind, (bones, recv, dmax, ramp) in DISTAL.items():
        dmin = np.full(NT, 1e9)
        for nm in bones:
            h, t = S.bone_pts(f"{nm}.{s}")
            dmin = np.minimum(dmin, seg_dist(pts3, h, t))
        keep = 1.0 - smooth01((dmin - dmax) / ramp)
        moved = np.zeros(NT, dtype=np.float32)
        for nm in bones:
            i = bidx[f"{nm}.{s}"]
            d = W[i] * (1 - keep) * is_body   # patilerde distal serbest
            moved += d; W[i] -= d
        W[bidx[f"{recv}.{s}"]] += moved
# kuyruk gate
tgate = smooth01((by - 0.24) / 0.05)
for bn in ("tail_01", "tail_02"):
    i = bidx[bn]
    d = W[i] * (1 - tgate)
    removed += d; W[i] -= d
# skapula kapisi
for s in ("L", "R"):
    h, t = S.bone_pts(f"shoulder.{s}")
    dsh = seg_dist(pts3, h, t)
    keep = 1.0 - smooth01((dsh - 0.055) / 0.022)
    i = bidx[f"shoulder.{s}"]
    d = W[i] * (1 - keep) * is_body
    removed += d; W[i] -= d
# iade: TUM core'a surekli 1/d^2 (Voronoi sicramasi yok); neck uygunlugu yumusak
COREN = ["hips", "spine_01", "spine_02", "spine_03", "neck"]
Dm = np.stack([seg_dist(pts3, *S.bone_pts(b)) for b in COREN])
share = 1.0 / (Dm + 0.012) ** 2
neck_block = smooth01((by + 0.10) / 0.05) * smooth01((0.22 - bz) / 0.06)  # gobek bolgesi
share[COREN.index("neck")] *= (1.0 - neck_block)
share = share / np.maximum(share.sum(0), 1e-12)
for k, bn in enumerate(COREN):
    W[bidx[bn]] += removed * share[k]
print(f"yasaklar: {removed.sum():.0f}")

W = W / np.maximum(W.sum(0), 1e-9)
# yaz (ear/tail gruplarina dokunma; hedef adalarda once sifirla)
for g in S.GW:
    if not g.startswith("ear") and g not in (f"tail_{i:02d}" for i in range(3, 7)):
        S.GW[g][tgt_idx[~dead]] = 0.0
# tail_01/02 govde sagrisinda yasal — W'den gelir; tail_03+ govdede yok ✓
for bi, bn in enumerate(BONES):
    S.GW[bn][tgt_idx[~dead]] = W[bi][~dead]

# ---------- rijit uclar + burun ----------
for isl, bone in (("paw_front_L", "front_toes.L"), ("paw_front_R", "front_toes.R"),
                  ("foot_hind_L", "toes.L"), ("foot_hind_R", "toes.R")):
    iv = S.island(isl)
    h, t = S.bone_pts(bone)
    tipd = np.linalg.norm(S.CO[iv] - np.array(t), axis=1)
    tz = iv[tipd < 0.016]
    for g in S.GW:
        S.GW[g][tz] = 0.0
    S.GW[bone][tz] = 1.0
body = S.island("body")
nose = body[S.CO[body][:, 1] < -0.465]
for g in S.GW:
    S.GW[g][nose] = 0.0
S.GW["snout"][nose] = 1.0

# ---------- biyik resync ----------
body_set = set(int(v) for v in body)
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

# ---------- hijyen ----------
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

# ---------- eski duzelticileri sil (yeni agirliklarla yeniden kurulacak) ----------
mouse = S.mouse
if mouse.data.shape_keys:
    for kb in list(mouse.data.shape_keys.key_blocks):
        if kb.name != "Basis":
            try:
                fc = kb.driver_remove("value")
            except Exception:
                pass
            mouse.shape_key_remove(kb)
    mouse.shape_key_remove(mouse.data.shape_keys.key_blocks["Basis"])
print("eski shape keyler temizlendi")

S.save("/tmp/rig/mouse_rig_td.blend")
print(f"SAVED ({time.time()-t0:.0f}s)")
