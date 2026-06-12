"""Bitirme v2 — KOPRULU grafik (parcali mesh icin):
- ada ici sanal kopruler (0.9/1.6/2.5mm) -> tek bagli geodezik
- pati/ayak: kaynak = bilek/topuk girisi; kuyruk: govde temas halkasi
- kulaklar yeniden (koprulu geodezik partition)
- rijit uclar, biyik resync, 0.5mm yariçapli parca-siniri konsensusu
"""
import sys, math, heapq
import numpy as np
sys.path.append("/tmp/rig/td"); sys.path.append("/tmp/rig")
import skinlib as SL
from mathutils import Vector
from mathutils import kdtree
from mathutils.bvhtree import BVHTree

S = SL.Skin("/tmp/rig/mouse_rig_td.blend")
# eksik deform gruplari sifirla olustur (onceki hijyen silmis olabilir)
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

def sample_body(p):
    co, n, fidx, dist = BODY_BVH.find_nearest(Vector(p))
    pvs = body_polys[fidx]
    ds = np.array([1.0 / (np.linalg.norm(S.CO[q] - np.array(co)) + 1e-6) for q in pvs])
    ds /= ds.sum()
    return {g: float(sum(S.GW[g][q] * w for q, w in zip(pvs, ds))) for g in S.GW}, dist

# ---------- koprulu ada grafigi ----------
def bridged_adj(isl):
    n = len(isl)
    iset = {int(v): k for k, v in enumerate(isl)}
    adj = [[] for _ in range(n)]
    for (a, b), L in zip(S.EV, S.rest_len):
        ia, ib = iset.get(int(a)), iset.get(int(b))
        if ia is not None and ib is not None:
            adj[ia].append((ib, L)); adj[ib].append((ia, L))
    # bagli mi?
    def comp_count(adj):
        uf = list(range(n))
        def find(a):
            while uf[a] != a:
                uf[a] = uf[uf[a]]; a = uf[a]
            return a
        for u in range(n):
            for v, _ in adj[u]:
                ra, rb = find(u), find(v)
                if ra != rb:
                    uf[ra] = rb
        return len({find(k) for k in range(n)})
    kd = kdtree.KDTree(n)
    for k, vi in enumerate(isl):
        kd.insert(Vector(S.CO[vi]), k)
    kd.balance()
    for rad in (0.0009, 0.0016, 0.0025, 0.004):
        cc = comp_count(adj)
        if cc == 1:
            break
        for k, vi in enumerate(isl):
            for co, j, dist in kd.find_range(Vector(S.CO[vi]), rad):
                if j != k:
                    adj[k].append((j, max(dist, 1e-4)))
    return adj, comp_count(adj)

def geodesic_adj(adj, n, src):
    dist = np.full(n, np.inf)
    h = []
    for k in src:
        dist[k] = 0.0; heapq.heappush(h, (0.0, int(k)))
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

def telescope(isl, g, chain, jpos, base_field=None, base_band=0.02):
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

def joint_g(isl, g, p):
    k = int(np.linalg.norm(S.CO[isl] - np.array(p), axis=1).argmin())
    return float(g[k])

def rim_field(isl, src, cap=30):
    rw = {}
    for v in isl[src[:cap]]:
        fld, _ = sample_body(S.CO[v])
        for gn, w in fld.items():
            rw[gn] = rw.get(gn, 0.0) + w
    ssum = sum(rw.values())
    return {gn: w / ssum for gn, w in rw.items() if w / ssum > 0.02}

# ============ 1. pati/ayak (giris-kaynakli koprulu geodezik) ============
SPECS = [
    ("paw_front_L", ["forearm.L", "hand.L", "front_toes.L"], "hand.L"),
    ("paw_front_R", ["forearm.R", "hand.R", "front_toes.R"], "hand.R"),
    ("foot_hind_L", ["shin.L", "foot.L", "toes.L"], "foot.L"),
    ("foot_hind_R", ["shin.R", "foot.R", "toes.R"], "foot.R"),
]
for isl_name, chain, entry_bone in SPECS:
    isl = S.island(isl_name)
    adj, cc = bridged_adj(isl)
    bd = np.array([sample_body(S.CO[v])[1] for v in isl])
    entry = np.array(S.bone_pts(entry_bone)[0])   # bilek/topuk eklemi
    d_entry = np.linalg.norm(S.CO[isl] - entry, axis=1)
    src = np.where((bd < 0.008) & (d_entry < 0.042))[0]
    if len(src) < 4:
        src = np.argsort(d_entry)[:15]
    g = geodesic_adj(adj, len(isl), list(src))
    jp = [0.0]
    for bn in chain[1:]:
        jp.append(joint_g(isl, g, S.bone_pts(bn)[0]))
    jp.append(joint_g(isl, g, S.bone_pts(chain[-1])[1]))
    jp = np.array(jp)
    for i in range(1, len(jp)):
        jp[i] = max(jp[i], jp[i - 1] + 0.010)
    rw = rim_field(isl, src)
    telescope(isl, g, chain, jp, base_field=rw, base_band=0.016)
    tip = g > (jp[-1] - 0.30 * (jp[-1] - jp[-2]))
    for gname in S.GW:
        S.GW[gname][isl[tip]] = 0.0
    S.GW[chain[-1]][isl[tip]] = 1.0
    print(f"{isl_name}: comp1={cc} jpos={[round(x*1000) for x in jp]}mm rim={list(rw)} tip={int(tip.sum())}v")

# ============ 2. kuyruk ============
isl = S.island("tail")
adj, cc = bridged_adj(isl)
bd = np.array([sample_body(S.CO[v])[1] for v in isl])
src = np.where(bd < 0.006)[0]
g = geodesic_adj(adj, len(isl), list(src))
chain = [f"tail_{i:02d}" for i in range(1, 7)]
jp = [0.0]
for bn in chain[1:]:
    jp.append(joint_g(isl, g, S.bone_pts(bn)[0]))
jp.append(joint_g(isl, g, S.bone_pts(chain[-1])[1]))
jp = np.array(jp)
for i in range(1, len(jp)):
    jp[i] = max(jp[i], jp[i - 1] + 0.012)
rw = rim_field(isl, src)
telescope(isl, g, chain, jp, base_field=rw, base_band=0.032)
print(f"tail: comp1={cc} jpos={[round(x*1000) for x in jp]}mm kok={rw}")

# ============ 3. kulaklar (koprulu geodezik yeniden) ============
for side, isl_name in (("L", "ear_L"), ("R", "ear_R")):
    chainE = [b.name for b in S.arm.data.bones if b.name.startswith("ear") and b.name.endswith("." + side)]
    chainE.sort(key=lambda n: (0 if n == f"ear.{side}" else int(n.split("_")[1].split(".")[0])))
    isl = S.island(isl_name)
    adj, cc = bridged_adj(isl)
    bd = np.array([sample_body(S.CO[v])[1] for v in isl])
    zmin = S.CO[isl][:, 2].min()
    src = np.where((bd < 0.007) & (S.CO[isl][:, 2] < zmin + 0.015))[0]
    if len(src) < 4:
        src = np.argsort(S.CO[isl][:, 2])[:25]
    g = geodesic_adj(adj, len(isl), list(src))
    jp = [0.0]
    for bn in chainE[1:]:
        jp.append(joint_g(isl, g, S.bone_pts(bn)[0]))
    jp.append(joint_g(isl, g, S.bone_pts(chainE[-1])[1]))
    jp = np.array(jp)
    for i in range(1, len(jp)):
        jp[i] = max(jp[i], jp[i - 1] + 0.008)
    telescope(isl, g, chainE, jp, base_field={"head": 1.0}, base_band=0.022)
    print(f"{isl_name}: comp1={cc} jpos={[round(x*1000) for x in jp]}mm")

# ============ 4. rijit burun ucu ============
nose = body[(S.CO[body][:, 1] < -0.465)]
for gname in S.GW:
    S.GW[gname][nose] = 0.0
S.GW["snout"][nose] = 1.0

# ============ 5. biyik tupleri resync ============
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
for root, verts_c in comps.items():
    step = max(1, len(verts_c) // 40)
    dists = [(sample_body(S.CO[v])[1], v) for v in verts_c[::step]]
    rootv = min(dists)[1]
    fld, _ = sample_body(S.CO[rootv])
    tot = sum(fld.values())
    for gname in S.GW:
        S.GW[gname][np.array(verts_c)] = fld.get(gname, 0.0) / max(tot, 1e-9)
print(f"biyik: {len(comps)} tup")

# ============ 6. 0.5mm parca-siniri konsensusu (biyik haric) ============
nw = np.where(~S.wh_mask)[0]
kd = kdtree.KDTree(len(nw))
for k, vi in enumerate(nw):
    kd.insert(Vector(S.CO[vi]), k)
kd.balance()
ufc = list(range(len(nw)))
def findc(a):
    while ufc[a] != a:
        ufc[a] = ufc[ufc[a]]; a = ufc[a]
    return a
for k, vi in enumerate(nw):
    for co, j, dist in kd.find_range(Vector(S.CO[vi]), 0.0005):
        if j != k and S.pid[nw[j]] == S.pid[vi]:   # yalniz AYNI ada icinde
            ra, rb = findc(k), findc(j)
            if ra != rb:
                ufc[ra] = rb
groups = {}
for k in range(len(nw)):
    groups.setdefault(findc(k), []).append(k)
multi = [c for c in groups.values() if len(c) > 1]
for c in multi:
    idx = nw[np.array(c)]
    for gname in S.GW:
        S.GW[gname][idx] = S.GW[gname][idx].mean()
print(f"konsensus: {len(multi)} kume / {sum(len(c) for c in multi)} vert")

# ============ 7. hijyen ============
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
print("SAVED")
