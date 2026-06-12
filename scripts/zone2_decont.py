"""Z2: Anatomik dekontaminasyon — capsule-gated limb weights.
Uzuv agirligi yalniz kendi anatomik kapsul yaricapi icinde yasayabilir;
sokulen agirlik core (omurga/kalca/boyun) zincirine iade edilir.
"""
import sys, math, os
import numpy as np
sys.path.append("/tmp/rig/td"); sys.path.append("/tmp/rig")
import skinlib as SL

S = SL.Skin("/tmp/rig/mouse_rig_td.blend")

def seg_dist(pts, a, b):
    a = np.array(a); b = np.array(b)
    ab = b - a
    t = np.clip(((pts - a) @ ab) / max(ab @ ab, 1e-12), 0, 1)
    return np.linalg.norm(pts - (a + t[:, None] * ab[None]), axis=1)

# anatomik etki yaricaplari (m)
RAD = {
    "shoulder": 0.075, "upper_arm": 0.062, "forearm": 0.045, "hand": 0.035, "front_toes": 0.028,
    "thigh": 0.090, "shin": 0.055, "foot": 0.040, "toes": 0.028,
}
LIMB_BONES = [f"{n}.{s}" for n in RAD for s in ("L", "R")]
CORE = ["hips", "spine_01", "spine_02", "spine_03", "neck"]
TAILS = [f"tail_{i:02d}" for i in range(1, 7)]

body = S.island("body")
pts = S.CO[body]

# capsule distances for limb bones
D = {}
for bn in LIMB_BONES:
    h, t = S.bone_pts(bn)
    D[bn] = seg_dist(pts, h, t)

def smooth01(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)

stripped = np.zeros(len(body))
report = {}
for bn in LIMB_BONES:
    base = bn.split(".")[0]
    r = RAD[base]
    keep = 1.0 - smooth01((D[bn] - r) / (0.6 * r))   # d<r: 1 ; d>1.6r: 0
    w = S.GW[bn][body]
    neww = w * keep
    delta = w - neww
    if delta.sum() > 1e-6:
        report[bn] = (float(delta.sum()), int((delta > 0.01).sum()))
    S.GW[bn][body] = neww
    stripped += delta

# ventral serit: gobek/gogus orta hatti uzuv tasiyamaz
ventral = (np.abs(pts[:, 0]) < 0.05) & (pts[:, 2] < 0.105)
vkeep = smooth01((np.abs(pts[:, 0]) - 0.012) / 0.038)
for bn in LIMB_BONES:
    w = S.GW[bn][body]
    neww = np.where(ventral, w * vkeep, w)
    stripped += w - neww
    S.GW[bn][body] = neww

# gogus/boyun bolgesinde head/snout z-rampasi (cene alti serbest, gogus yasak)
collar = (pts[:, 1] > -0.345) & (pts[:, 1] < -0.08)
zgate = smooth01((pts[:, 2] - 0.135) / 0.085)        # z<=0.135: 0, z>=0.22: 1
for bn in ("head", "snout"):
    w = S.GW[bn][body]
    neww = np.where(collar, w * zgate, w)
    stripped += w - neww
    S.GW[bn][body] = neww

# tail govde uzerinde yalniz sagri bolgesinde (y>0.24)
tail_ok = pts[:, 1] > 0.24
for bn in TAILS:
    w = S.GW[bn][body]
    neww = np.where(tail_ok, w, w * smooth01((pts[:, 1] - 0.16) / 0.08))
    stripped += w - neww
    S.GW[bn][body] = neww

# ---- iade: core zincirine, mevcut core oranlarina gore ----
core_now = np.zeros(len(body))
for bn in CORE:
    core_now += S.GW[bn][body]
core_d = {bn: seg_dist(pts, *S.bone_pts(bn)) for bn in CORE}
nearest_core = np.array([CORE[i] for i in np.argmin(np.stack([core_d[b] for b in CORE]), axis=0)])
need = stripped > 1e-6
for bn in CORE:
    share = np.where(core_now > 1e-6, S.GW[bn][body] / np.maximum(core_now, 1e-9),
                     (nearest_core == bn).astype(float))
    S.GW[bn][body] = S.GW[bn][body] + np.where(need, stripped * share, 0.0)

print("DEKONTAMINASYON (body):")
for bn, (tot, cnt) in sorted(report.items(), key=lambda kv: -kv[1][0])[:12]:
    print(f"  {bn}: {tot:.1f} toplam agirlik sokuldu ({cnt} vert)")
print(f"  toplam iade: {stripped.sum():.1f} -> core zinciri")

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
        S.GW[allowed[0]][isl[bad]] = 1.0
        s[bad] = 1.0
    for g in allowed:
        S.GW[g][isl] = S.GW[g][isl] / s
    print(f"  clamp {isl_name}: {removed:.2f} yabanci agirlik temizlendi")

clamp_island("paw_front_L", ["forearm.L", "hand.L", "front_toes.L"])
clamp_island("paw_front_R", ["forearm.R", "hand.R", "front_toes.R"])
clamp_island("foot_hind_L", ["shin.L", "foot.L", "toes.L"])
clamp_island("foot_hind_R", ["shin.R", "foot.R", "toes.R"])
clamp_island("tail", ["hips"] + TAILS)

# ---- degisen vertexlerde lokal relax (3 iter, yalniz body) ----
changed = np.zeros(S.NV, bool)
changed[body[need | ventral | (collar & (zgate < 0.99))]] = True
# 1-ring genislet
nbr = [[] for _ in range(S.NV)]
for a, b in S.EV:
    nbr[a].append(b); nbr[b].append(a)
ring = changed.copy()
for v in np.where(changed)[0]:
    for u in nbr[v]:
        ring[u] = True
ring &= ~S.wh_mask
body_mask = np.zeros(S.NV, bool); body_mask[body] = True
ring &= body_mask
ridx = np.where(ring)[0]
print(f"  lokal relax: {len(ridx)} vert, 3 iterasyon")
for it in range(3):
    snap = {g: S.GW[g].copy() for g in S.GW}
    for v in ridx:
        ns = [u for u in nbr[v] if body_mask[u]]
        if not ns:
            continue
        for g in S.GW:
            avg = np.mean([snap[g][u] for u in ns])
            S.GW[g][v] = 0.55 * snap[g][v] + 0.45 * avg
S.normalize(np.where(body_mask)[0])

S.save("/tmp/rig/mouse_rig_td.blend")
print("SAVED")
