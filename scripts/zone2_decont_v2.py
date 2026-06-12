"""Z2 v2: Yuzey-geodezik anatomik dekontaminasyon.
Uzuv agirligi yalniz kendi cilt tohumlarindan geodezik yaricap icinde yasar.
Iade: en yakin 2 core kemige 1/d^2; neck z<0.20'de alici olamaz.
"""
import sys, math, os, heapq
import numpy as np
sys.path.append("/tmp/rig/td"); sys.path.append("/tmp/rig")
import skinlib as SL

S = SL.Skin("/tmp/rig/mouse_rig_td.blend")

def seg_dist(pts, a, b):
    a = np.array(a); b = np.array(b)
    ab = b - a
    t = np.clip(((pts - a) @ ab) / max(ab @ ab, 1e-12), 0, 1)
    return np.linalg.norm(pts - (a + t[:, None] * ab[None]), axis=1)

def smooth01(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)

body = S.island("body")
bset = {int(v): k for k, v in enumerate(body)}
pts = S.CO[body]
NB = len(body)

# body adjacency (bir kez)
adj = [[] for _ in range(NB)]
for (a, b), L in zip(S.EV, S.rest_len):
    ia, ib = bset.get(int(a)), bset.get(int(b))
    if ia is not None and ib is not None:
        adj[ia].append((ib, L)); adj[ib].append((ia, L))

def geodesic(seed_local):
    dist = np.full(NB, np.inf)
    h = []
    for k in seed_local:
        dist[k] = 0.0
        heapq.heappush(h, (0.0, k))
    while h:
        d, u = heapq.heappop(h)
        if d > dist[u] + 1e-12:
            continue
        for v, L in adj[u]:
            nd = d + L
            if nd < dist[v] - 1e-12:
                dist[v] = nd
                heapq.heappush(h, (nd, v))
    return dist

# geodezik izin yaricaplari (m) — TD karari
GRAD = {
    "shoulder": 0.080, "upper_arm": 0.058, "forearm": 0.040, "hand": 0.030, "front_toes": 0.022,
    "thigh": 0.090, "shin": 0.042, "foot": 0.032, "toes": 0.022,
}
LIMBS = [f"{n}.{s}" for n in GRAD for s in ("L", "R")]
CORE = ["hips", "spine_01", "spine_02", "spine_03", "neck"]
TAILS = [f"tail_{i:02d}" for i in range(1, 7)]

stripped = np.zeros(NB)
report = {}
for bn in LIMBS:
    base = bn.split(".")[0]
    G = GRAD[base]
    h, t = S.bone_pts(bn)
    capd = seg_dist(pts, h, t)
    seeds = np.where(capd < max(0.020, 0.022))[0]
    if len(seeds) < 3:
        seeds = np.argsort(capd)[:12]
    g = geodesic(list(seeds))
    keep = 1.0 - smooth01((g - G) / (0.55 * G))
    w = S.GW[bn][body]
    neww = w * keep
    delta = w - neww
    if delta.sum() > 0.5:
        report[bn] = (float(delta.sum()), int((delta > 0.01).sum()))
    S.GW[bn][body] = neww
    stripped += delta

# head/snout z-gate (gogus yasak, cene-bogaz rampali)
collar = (pts[:, 1] > -0.345) & (pts[:, 1] < -0.08)
zgate = smooth01((pts[:, 2] - 0.135) / 0.085)
for bn in ("head", "snout"):
    w = S.GW[bn][body]
    neww = np.where(collar, w * zgate, w)
    stripped += w - neww
    S.GW[bn][body] = neww

# tail govdede yalniz sagri
tgate = smooth01((pts[:, 1] - 0.16) / 0.08)
for bn in TAILS:
    w = S.GW[bn][body]
    neww = w * tgate
    stripped += w - neww
    S.GW[bn][body] = neww

# ---- iade v2: en yakin 2 core'a 1/d^2 ; neck alicisi z>=0.20 ----
core_d = {}
for bn in CORE:
    core_d[bn] = seg_dist(pts, *S.bone_pts(bn))
core_d["neck"] = np.where(pts[:, 2] < 0.20, 1e6, core_d["neck"])
Dm = np.stack([core_d[b] for b in CORE])          # (5, NB)
order = np.argsort(Dm, axis=0)
near1, near2 = order[0], order[1]
d1 = Dm[near1, np.arange(NB)]; d2 = Dm[near2, np.arange(NB)]
w1 = (1 / np.maximum(d1, 1e-4) ** 2)
w2 = (1 / np.maximum(d2, 1e-4) ** 2)
sw = w1 + w2
need = stripped > 1e-6
for k, bn in enumerate(CORE):
    add = np.where(need & (near1 == k), stripped * w1 / sw, 0.0) + \
          np.where(need & (near2 == k), stripped * w2 / sw, 0.0)
    S.GW[bn][body] += add

print("DEKONT v2 (geodezik):")
for bn, (tot, cnt) in sorted(report.items(), key=lambda kv: -kv[1][0])[:12]:
    print(f"  {bn}: {tot:.1f} sokuldu ({cnt} vert)")
print(f"  iade toplam: {stripped.sum():.1f}")

# ---- ada kelepceleri ----
def clamp_island(isl_name, allowed):
    isl = S.island(isl_name)
    removed = 0.0
    for g in S.GW:
        if g not in allowed:
            removed += S.GW[g][isl].sum()
            S.GW[g][isl] = 0.0
    s = np.zeros(len(isl))
    for g in allowed:
        s += S.GW[g][isl]
    bad = s <= 1e-9
    if bad.any():
        S.GW[allowed[0]][isl[bad]] = 1.0; s[bad] = 1.0
    for g in allowed:
        S.GW[g][isl] = S.GW[g][isl] / s
    print(f"  clamp {isl_name}: {removed:.2f}")

clamp_island("paw_front_L", ["forearm.L", "hand.L", "front_toes.L"])
clamp_island("paw_front_R", ["forearm.R", "hand.R", "front_toes.R"])
clamp_island("foot_hind_L", ["shin.L", "foot.L", "toes.L"])
clamp_island("foot_hind_R", ["shin.R", "foot.R", "toes.R"])
clamp_island("tail", ["hips"] + TAILS)

# ---- lokal relax: yalniz degisen vertler (body) ----
changed_local = need | (collar & (zgate < 0.99))
nbr = [[] for _ in range(S.NV)]
for a, b in S.EV:
    nbr[a].append(b); nbr[b].append(a)
body_mask = np.zeros(S.NV, bool); body_mask[body] = True
ring = np.zeros(S.NV, bool)
ring[body[changed_local]] = True
for v in body[changed_local]:
    for u in nbr[v]:
        if body_mask[u]:
            ring[u] = True
ridx = np.where(ring)[0]
print(f"  relax: {len(ridx)} vert x3")
for it in range(3):
    snap = {g: S.GW[g].copy() for g in S.GW}
    for v in ridx:
        ns = [u for u in nbr[v] if body_mask[u]]
        if not ns:
            continue
        for g in S.GW:
            S.GW[g][v] = 0.55 * snap[g][v] + 0.45 * float(np.mean([snap[g][u] for u in ns]))
S.normalize(np.where(body_mask)[0])

S.save("/tmp/rig/mouse_rig_td.blend")
print("SAVED")
