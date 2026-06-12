import sys, math, os, heapq
import numpy as np
sys.path.append("/tmp/rig/td"); sys.path.append("/tmp/rig")
import skinlib as SL
from mathutils import Vector
from mathutils import kdtree

OUT = "/tmp/rig/td/z1_ear"
os.makedirs(OUT, exist_ok=True)
S = SL.Skin("/tmp/rig/mouse_rig.blend")   # temiz tabandan
scene = SL.setup_render()
cams = SL.make_cams()
R = math.radians

def ear_pose():
    S.reset_pose()
    S.rot("ear.L", R(35)); S.rot("ear_02.L", R(20))
    S.rot("ear.R", 0, R(30), 0)

# ---- geodesic over island ----
def geodesic(isl, sources):
    iset = {int(v): k for k, v in enumerate(isl)}
    adj = [[] for _ in isl]
    for (a, b), L in zip(S.EV, S.rest_len):
        ia, ib = iset.get(int(a)), iset.get(int(b))
        if ia is not None and ib is not None:
            adj[ia].append((ib, L)); adj[ib].append((ia, L))
    dist = np.full(len(isl), np.inf)
    h = []
    for s in sources:
        k = iset[int(s)]
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
    m = np.isfinite(dist)
    if (~m).any():
        dist[~m] = dist[m].max()
    return dist

body = S.island("body")
kd = kdtree.KDTree(len(body))
for j, vi in enumerate(body):
    kd.insert(Vector(S.CO[vi]), j)
kd.balance()

def body_dist(isl):
    return np.array([kd.find(Vector(S.CO[v]))[2] for v in isl])

def tear_metric(isl_name, gthr=0.008):
    isl = S.island(isl_name)
    bd = body_dist(isl)
    att = isl[bd < 0.0055]
    if not len(att):
        return 0.0
    match = [int(body[kd.find(Vector(S.CO[v]))[1]]) for v in att]
    pc = S.posed_coords()
    inc = [float(np.linalg.norm(pc[a] - pc[b]) - np.linalg.norm(S.CO[a] - S.CO[b]))
           for a, b in zip(att, match)]
    return max(inc) * 1000

# ---- BEFORE (sadece metrik; render zaten var) ----
ear_pose()
p99_b, max_b = S.stretch(S.pid == S.IDS["ear_L"])
tearL_b = tear_metric("ear_L"); tearR_b = tear_metric("ear_R")
print(f"ONCE: in-ear stretch p99={p99_b:.2f} max={max_b:.2f} | TEAR(yapisma) L={tearL_b:.1f}mm R={tearR_b:.1f}mm")

# ---- FIX v2: geodezik partition-of-unity ----
for side, isl_name in (("L", "ear_L"), ("R", "ear_R")):
    chain = [b.name for b in S.arm.data.bones if b.name.startswith("ear") and b.name.endswith("." + side)]
    chain.sort(key=lambda n: (0 if n == f"ear.{side}" else int(n.split("_")[1].split(".")[0])))
    isl = S.island(isl_name)
    bd = body_dist(isl)
    sources = isl[bd < 0.006]
    g = geodesic(isl, sources)

    # joint'lerin geodezik konumlari: kemik basina en yakin ear vertinin g degeri
    jpos = []
    for bn in chain:
        h, t = S.bone_pts(bn)
        k = np.linalg.norm(S.CO[isl] - h, axis=1).argmin()
        jpos.append(g[k])
    h_last, t_last = S.bone_pts(chain[-1])
    k = np.linalg.norm(S.CO[isl] - t_last, axis=1).argmin()
    jpos.append(max(g[k], jpos[-1] + 0.01))
    jpos = np.maximum.accumulate(np.array(jpos))  # monoton garanti
    base_band = max(jpos[0], 0.018)               # head->ear.X gecis bandi

    # partition of unity: head + chain
    W = {bn: np.zeros(len(isl)) for bn in chain}
    f_ear = SL.Skin.smoothstep(g / base_band)     # 0=head, 1=ear zinciri
    Whead = 1.0 - f_ear
    u = g
    for k, bn in enumerate(chain):
        lo = jpos[k]; hi = jpos[k + 1]
        span = max(hi - lo, 1e-6)
        t = SL.Skin.smoothstep(np.clip((u - lo) / span, 0, 1))
        if k == 0:
            wk = 1.0 - t
        else:
            lo0 = jpos[k - 1]; span0 = max(lo - lo0, 1e-6)
            t0 = SL.Skin.smoothstep(np.clip((u - lo0) / span0, 0, 1))
            wk = t0 * (1.0 - t)
        if k == len(chain) - 1:
            wk = SL.Skin.smoothstep(np.clip((u - jpos[k - 1]) / max(jpos[k] - jpos[k - 1], 1e-6), 0, 1)) if len(chain) > 1 else np.ones(len(isl))
            # son kemik: oncekinden devralip uca kadar tutar
        W[bn] = wk
    # normalize chain partisyonu
    sW = sum(W.values())
    sW[sW <= 1e-9] = 1.0
    for bn in chain:
        W[bn] = W[bn] / sW * f_ear

    # yaz: ear adasinda sadece head + chain
    for gname in S.GW:
        S.GW[gname][isl] = 0.0
    S.GW["head"][isl] = Whead
    for bn in chain:
        S.GW[bn][isl] = W[bn]
    print(f"EAR {side}: joints_g={[round(x*1000) for x in jpos]}mm taban_band={base_band*1000:.0f}mm")

S.write_weights()

# ---- AFTER ----
ear_pose()
p99_a, max_a = S.stretch(S.pid == S.IDS["ear_L"])
tearL_a = tear_metric("ear_L"); tearR_a = tear_metric("ear_R")
SL.render(f"{OUT}/after2_pose.png", cams["ear_L"])
S.reset_pose()
SL.render(f"{OUT}/after2_rest.png", cams["ear_L"])
print(f"SONRA: in-ear stretch p99={p99_a:.2f} max={max_a:.2f} | TEAR L={tearL_a:.1f}mm R={tearR_a:.1f}mm")

S.save("/tmp/rig/mouse_rig_td.blend")
print("SAVED mouse_rig_td.blend")
