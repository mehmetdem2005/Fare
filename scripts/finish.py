"""Bitirme hatti: ada kenarlarini yeni govde alanindan kaynakla,
ayak/pati/kuyruk ic gradyanlari (geodezik partition), rijit uclar,
biyik tup resync, dikis tutarliligi, hijyen."""
import sys, math, heapq
import numpy as np
sys.path.append("/tmp/rig/td"); sys.path.append("/tmp/rig")
import skinlib as SL
from mathutils import Vector
from mathutils import kdtree
from mathutils.bvhtree import BVHTree

S = SL.Skin("/tmp/rig/mouse_rig_td.blend")

def smooth01(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)

# ---- govde yuzey alani ornekleyici ----
body = S.island("body")
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

def geodesic(isl, src_local):
    iset = {int(v): k for k, v in enumerate(isl)}
    adj = [[] for _ in isl]
    for (a, b), L in zip(S.EV, S.rest_len):
        ia, ib = iset.get(int(a)), iset.get(int(b))
        if ia is not None and ib is not None:
            adj[ia].append((ib, L)); adj[ib].append((ia, L))
    dist = np.full(len(isl), np.inf)
    h = []
    for k in src_local:
        dist[k] = 0.0; heapq.heappush(h, (0.0, k))
    while h:
        d, u = heapq.heappop(h)
        if d > dist[u] + 1e-12:
            continue
        for v, L in adj[u]:
            nd = d + L
            if nd < dist[v] - 1e-12:
                dist[v] = nd; heapq.heappush(h, (nd, v))
    m = np.isfinite(dist)
    if (~m).any():
        dist[~m] = dist[m].max()
    return dist

def telescope(isl, g, chain, jpos, base_field=None, base_band=0.02):
    """g: geodezik; chain: kemik adlari; jpos: eklemlerin g konumlari (len=chain+1).
    base_field: g=0'da gecerli olan oransal pay dict'i (proksimal devamlilik)."""
    def ramp(u, j, band):
        return smooth01((u - (j - band)) / (2 * band))
    nb = len(chain)
    Wch = []
    for k in range(nb):
        band_hi = 0.35 * max(jpos[k + 1] - jpos[k], 0.008)
        lo = np.ones(len(isl)) if k == 0 else ramp(g, jpos[k], 0.35 * max(jpos[k] - jpos[k - 1], 0.008))
        hi = ramp(g, jpos[k + 1], band_hi) if k < nb - 1 else np.zeros(len(isl))
        Wch.append(np.clip(lo - hi, 0, 1))
    sW = sum(Wch); sW[sW <= 1e-9] = 1.0
    fb = smooth01(g / base_band) if base_field else np.ones(len(isl))
    for gname in S.GW:
        S.GW[gname][isl] = 0.0
    if base_field:
        for gname, share in base_field.items():
            S.GW[gname][isl] = (1 - fb) * share
    for k, bn in enumerate(chain):
        S.GW[bn][isl] += Wch[k] / sW * fb

# ============ 1. ayak/pati ic gradyanlari ============
SPECS = [
    ("paw_front_L", ["forearm.L", "hand.L", "front_toes.L"], "L"),
    ("paw_front_R", ["forearm.R", "hand.R", "front_toes.R"], "R"),
    ("foot_hind_L", ["shin.L", "foot.L", "toes.L"], "L"),
    ("foot_hind_R", ["shin.R", "foot.R", "toes.R"], "R"),
]
for isl_name, chain, side in SPECS:
    isl = S.island(isl_name)
    bd = np.array([sample_body(S.CO[v])[1] for v in isl])
    src = np.where(bd < 0.006)[0]
    if len(src) < 4:
        src = np.argsort(bd)[:20]
    g = geodesic(isl, list(src))
    jp = []
    for bn in chain:
        h, t = S.bone_pts(bn)
        k = np.linalg.norm(S.CO[isl] - np.array(h), axis=1).argmin()
        jp.append(g[k])
    h_l, t_l = S.bone_pts(chain[-1])
    k = np.linalg.norm(S.CO[isl] - np.array(t_l), axis=1).argmin()
    jp.append(g[k])
    jp = np.array(jp)
    jp[0] = 0.0
    for i in range(1, len(jp)):
        jp[i] = max(jp[i], jp[i - 1] + 0.008)
    # proksimal devamlilik: kok halkasindaki govde alani ortalamasi
    rimW = {}
    for v in isl[src[:30]]:
        fld, _ = sample_body(S.CO[v])
        for gn, w in fld.items():
            rimW[gn] = rimW.get(gn, 0.0) + w
    ssum = sum(rimW.values())
    rimW = {gn: w / ssum for gn, w in rimW.items() if w / ssum > 0.02}
    telescope(isl, g, chain, jp, base_field=rimW, base_band=0.018)
    # rijit pence ucu: son %25 g araliginda saf uc kemigi
    tipzone = g > (jp[-1] - 0.25 * (jp[-1] - jp[-2]))
    for gname in S.GW:
        S.GW[gname][isl[tipzone]] = 0.0
    S.GW[chain[-1]][isl[tipzone]] = 1.0
    print(f"{isl_name}: jpos={[round(x*1000) for x in jp]}mm rim={list(rimW)[:4]} uc_rijit={int(tipzone.sum())}v")

# ============ 2. kuyruk: kok coklu karisim + segment partition ============
isl = S.island("tail")
bd = np.array([sample_body(S.CO[v])[1] for v in isl])
src = np.where(bd < 0.006)[0]
g = geodesic(isl, list(src))
chain = [f"tail_{i:02d}" for i in range(1, 7)]
jp = [0.0]
for bn in chain[1:]:
    h, t = S.bone_pts(bn)
    k = np.linalg.norm(S.CO[isl] - np.array(h), axis=1).argmin()
    jp.append(g[k])
h_l, t_l = S.bone_pts(chain[-1])
k = np.linalg.norm(S.CO[isl] - np.array(t_l), axis=1).argmin()
jp.append(g[k])
jp = np.array(jp)
for i in range(1, len(jp)):
    jp[i] = max(jp[i], jp[i - 1] + 0.008)
rimW = {}
for v in isl[src[:30]]:
    fld, _ = sample_body(S.CO[v])
    for gn, w in fld.items():
        rimW[gn] = rimW.get(gn, 0.0) + w
ssum = sum(rimW.values())
rimW = {gn: w / ssum for gn, w in rimW.items() if w / ssum > 0.02}
telescope(isl, g, chain, jp, base_field=rimW, base_band=0.030)
print(f"tail: jpos={[round(x*1000) for x in jp]}mm kok_karisimi={rimW}")

# ============ 3. kulak rim re-weld (govde alani degisti) ============
for isl_name in ("ear_L", "ear_R"):
    isl = S.island(isl_name)
    cnt = 0
    for v in isl:
        fld, dist = sample_body(S.CO[v])
        if dist < 0.0055:
            f = smooth01(dist / 0.0055)
            for gname in S.GW:
                tgt = fld.get(gname, 0.0)
                S.GW[gname][v] = (1 - f) * tgt + f * S.GW[gname][v]
            cnt += 1
    print(f"{isl_name} rim re-weld: {cnt}v")

# ============ 4. rijit burun ucu ============
nose = body[(S.CO[body][:, 1] < -0.465)]
for gname in S.GW:
    S.GW[gname][nose] = 0.0
S.GW["snout"][nose] = 1.0
print(f"burun ucu rijit (snout): {len(nose)}v")

# ============ 5. biyik tupleri resync ============
wh_idx = np.concatenate([S.island("whiskers_L"), S.island("whiskers_R")])
wh_set = set(int(i) for i in wh_idx)
parent_uf = {int(i): int(i) for i in wh_idx}
def find(a):
    while parent_uf[a] != a:
        parent_uf[a] = parent_uf[parent_uf[a]]; a = parent_uf[a]
    return a
for e in S.me.edges:
    a, b = e.vertices
    if int(a) in wh_set and int(b) in wh_set:
        ra, rb = find(int(a)), find(int(b))
        if ra != rb:
            parent_uf[ra] = rb
comps = {}
for i in wh_idx:
    comps.setdefault(find(int(i)), []).append(int(i))
for root, verts_c in comps.items():
    step = max(1, len(verts_c) // 40)
    dists = [(sample_body(S.CO[v])[1], v) for v in verts_c[::step]]
    rootv = min(dists)[1]
    fld, _ = sample_body(S.CO[rootv])
    tot = sum(fld.values())
    for gname in S.GW:
        S.GW[gname][np.array(verts_c)] = fld.get(gname, 0.0) / max(tot, 1e-9)
print(f"biyik: {len(comps)} tup resync")

# ============ 6. dikis tutarliligi + hijyen ============
S.normalize(np.arange(S.NV))
clusters = {}
for vi in range(S.NV):
    key = (round(S.CO[vi][0], 6), round(S.CO[vi][1], 6), round(S.CO[vi][2], 6))
    clusters.setdefault(key, []).append(vi)
multi = [c for c in clusters.values() if len(c) > 1]
for c in multi:
    idx = np.array(c)
    for gname in S.GW:
        S.GW[gname][idx] = S.GW[gname][idx].mean()
print(f"dikis: {len(multi)} kume esitlendi")

# top-4 + normalize (numpy ile, deterministik)
names = list(S.GW)
Wall = np.stack([S.GW[g] for g in names])
order = np.argsort(-Wall, axis=0)
keepmask = np.zeros_like(Wall, dtype=bool)
for r in range(4):
    keepmask[order[r], np.arange(S.NV)] = True
Wall = np.where(keepmask, Wall, 0.0)
Wall = Wall / np.maximum(Wall.sum(0), 1e-9)
for i, g in enumerate(names):
    S.GW[g] = Wall[i]
# dikis kumeleri top-4 sonrasi yine ayni mi: ayni girdi -> ayni cikti ✓

S.save("/tmp/rig/mouse_rig_td.blend")
print("SAVED")
