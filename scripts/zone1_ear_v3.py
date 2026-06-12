import sys, math, os, heapq
import numpy as np
sys.path.append("/tmp/rig/td"); sys.path.append("/tmp/rig")
import skinlib as SL
from mathutils import Vector
from mathutils import kdtree

OUT = "/tmp/rig/td/z1_ear"
S = SL.Skin("/tmp/rig/mouse_rig.blend")
scene = SL.setup_render()
cams = SL.make_cams()
R = math.radians

def ear_pose():
    S.reset_pose()
    S.rot("ear.L", R(35)); S.rot("ear_02.L", R(20))
    S.rot("ear.R", 0, R(30), 0)

def geodesic(isl, src_idx):
    iset = {int(v): k for k, v in enumerate(isl)}
    adj = [[] for _ in isl]
    for (a, b), L in zip(S.EV, S.rest_len):
        ia, ib = iset.get(int(a)), iset.get(int(b))
        if ia is not None and ib is not None:
            adj[ia].append((ib, L)); adj[ib].append((ia, L))
    dist = np.full(len(isl), np.inf)
    h = []
    for s in src_idx:
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

for side, isl_name in (("L", "ear_L"), ("R", "ear_R")):
    chain = [b.name for b in S.arm.data.bones if b.name.startswith("ear") and b.name.endswith("." + side)]
    chain.sort(key=lambda n: (0 if n == f"ear.{side}" else int(n.split("_")[1].split(".")[0])))
    isl = S.island(isl_name)
    bd = np.array([kd.find(Vector(S.CO[v]))[2] for v in isl])
    zmin = S.CO[isl][:, 2].min()
    src = isl[(bd < 0.007) & (S.CO[isl][:, 2] < zmin + 0.015)]   # SADECE alt halka
    if len(src) < 4:
        src = isl[np.argsort(S.CO[isl][:, 2])[:25]]
    g = geodesic(isl, src)

    nb = len(chain)
    jpos = []
    for bn in chain:
        h, t = S.bone_pts(bn)
        k = np.linalg.norm(S.CO[isl] - h, axis=1).argmin()
        jpos.append(g[k])
    h_l, t_l = S.bone_pts(chain[-1])
    k = np.linalg.norm(S.CO[isl] - t_l, axis=1).argmin()
    jpos.append(g[k])
    jpos = np.array(jpos)
    for i in range(1, len(jpos)):                # strictly increasing, min 8mm
        jpos[i] = max(jpos[i], jpos[i - 1] + 0.008)

    base_band = 0.022
    f_ear = SL.Skin.smoothstep(g / base_band)

    def ramp(u, j, band):
        return SL.Skin.smoothstep((u - (j - band)) / (2 * band))

    # telescoping partition: bone k = ramp(j_k) - ramp(j_{k+1}) ; bone0 ramp(j_0)=1 zaten g>=0
    Wch = []
    for k in range(nb):
        band_lo = 0.35 * max(jpos[k] - (jpos[k - 1] if k > 0 else 0), 0.008) if k > 0 else 1.0
        band_hi = 0.35 * max(jpos[k + 1] - jpos[k], 0.008)
        lo = np.ones(len(isl)) if k == 0 else ramp(g, jpos[k], band_lo)
        hi = ramp(g, jpos[k + 1], band_hi) if k < nb - 1 else np.zeros(len(isl))
        Wch.append(np.clip(lo - hi, 0, 1))
    sW = sum(Wch)
    sW[sW <= 1e-9] = 1.0
    for gname in S.GW:
        S.GW[gname][isl] = 0.0
    S.GW["head"][isl] = 1.0 - f_ear
    for k, bn in enumerate(chain):
        S.GW[bn][isl] = Wch[k] / sW * f_ear
    print(f"EAR {side}: jpos={[round(x*1000) for x in jpos]}mm src={len(src)}")

S.write_weights()
ear_pose()
p99, mx = S.stretch(S.pid == S.IDS["ear_L"])
SL.render(f"{OUT}/after3_pose.png", cams["ear_L"])
S.reset_pose()
print(f"SONRA v3: in-ear stretch p99={p99:.2f} max={mx:.2f}")
S.save("/tmp/rig/mouse_rig_td.blend")
print("SAVED")
