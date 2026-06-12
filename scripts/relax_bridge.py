"""Koprulu agirlik relaxi (ada-ici, parcalar arasi 1.2mm koprulerle).
Parca sinirlarindaki kalan agirlik ayrismalarini uyumlar."""
import sys
import numpy as np
sys.path.append("/tmp/rig/td"); sys.path.append("/tmp/rig")
import skinlib as SL
from mathutils import Vector
from mathutils import kdtree

S = SL.Skin("/tmp/rig/mouse_rig_td.blend")
for b in S.arm.data.bones:
    if b.use_deform and b.name not in S.GW:
        S.GW[b.name] = np.zeros(S.NV)

ISLNAMES = ["body", "paw_front_L", "paw_front_R", "foot_hind_L", "foot_hind_R",
            "tail", "ear_L", "ear_R"]

# global komsuluk: mesh kenarlari + ada-ici 1.2mm kopru
nbr = [[] for _ in range(S.NV)]
for a, b in S.EV:
    nbr[int(a)].append(int(b)); nbr[int(b)].append(int(a))
bridges = 0
for isl_name in ISLNAMES:
    isl = S.island(isl_name)
    kd = kdtree.KDTree(len(isl))
    for k, vi in enumerate(isl):
        kd.insert(Vector(S.CO[vi]), k)
    kd.balance()
    have = [set(nbr[int(v)]) for v in isl]
    for k, vi in enumerate(isl):
        for co, j, dist in kd.find_range(Vector(S.CO[vi]), 0.0012):
            vj = int(isl[j])
            if j != k and vj not in have[k]:
                nbr[int(vi)].append(vj); nbr[vj].append(int(vi))
                have[k].add(vj)
                bridges += 1
print(f"kopru: {bridges} cift")

mask = ~S.wh_mask
names = list(S.GW)
for it in range(2):
    snap = {g: S.GW[g].copy() for g in names}
    for vi in np.where(mask)[0]:
        ns = [u for u in nbr[vi] if mask[u]]
        if not ns:
            continue
        for g in names:
            avg = float(np.mean([snap[g][u] for u in ns]))
            S.GW[g][vi] = 0.7 * snap[g][vi] + 0.3 * avg
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
# biyik tupleri zaten sabit (relax disi) ✓
S.save("/tmp/rig/mouse_rig_td.blend")
print("RELAX OK SAVED")
