"""Kabuk-yigini agirlik esitleme: normal-hizali dikey yigindaki vertexler
(ust uste kurk panelleri) OZDES agirlik paylasir => panel katlanmasi imkansiz.
Yuzey boyunca degisim serbest, derinlik boyunca sabit."""
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

VN = np.empty(S.NV * 3)
S.me.vertices.foreach_get("normal", VN)
VN = VN.reshape(S.NV, 3)
n_norm = np.linalg.norm(VN, axis=1)
VN = VN / np.maximum(n_norm[:, None], 1e-9)

body = S.island("body")
kd = kdtree.KDTree(len(body))
for k, vi in enumerate(body):
    kd.insert(Vector(S.CO[vi]), k)
kd.balance()

# yigin tespiti: offset normal-baskin + normaller paralel
uf = list(range(len(body)))
def find(a):
    while uf[a] != a:
        uf[a] = uf[uf[a]]; a = uf[a]
    return a
pairs = 0
for k, vi in enumerate(body):
    n_i = VN[vi]
    for co, j, dist in kd.find_range(Vector(S.CO[vi]), 0.007):
        if j <= k or dist < 1e-9:
            continue
        vj = int(body[j])
        if float(np.dot(n_i, VN[vj])) < 0.7:
            continue                      # zit/yan yuzey degil, paralel olmali
        off = (S.CO[vj] - S.CO[vi]) / dist
        if abs(float(np.dot(off, n_i))) < 0.6:
            continue                      # yan komsu degil, dikey yigin olmali
        ra, rb = find(k), find(j)
        if ra != rb:
            uf[ra] = rb
        pairs += 1

groups = {}
for k in range(len(body)):
    groups.setdefault(find(k), []).append(k)
multi = [g for g in groups.values() if len(g) > 1]
names = list(S.GW)
tot_v = 0
for g in multi:
    idx = body[np.array(g)]
    tot_v += len(g)
    for gn in names:
        S.GW[gn][idx] = S.GW[gn][idx].mean()
print(f"yigin: {pairs} cift, {len(multi)} yigin / {tot_v} vertex esitlendi")

# hijyen (top-4 + normalize)
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

# yigin tutarliligi top-4 sonrasi: ayni girdi -> ayni cikti ✓
S.save("/tmp/rig/mouse_rig_td.blend")
print("STACK EQ OK")
