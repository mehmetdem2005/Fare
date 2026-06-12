"""OMURGA YAYI: 3 duz segment -> sirt siluetine paralel ark uzerinde 5 segment.
Cekirdek agirliklar yeni zincirle s-partition olarak yeniden boyanir
(eksen-saf => radyal tutarlilik korunur)."""
import sys, math
import numpy as np
sys.path.append("/tmp/rig/td"); sys.path.append("/tmp/rig")
import skinlib as SL
import bpy
from mathutils import Vector

S = SL.Skin("/tmp/rig/mouse_rig_td.blend")
C, D = bpy.context, bpy.data
arm_ob = S.arm
body = S.island("body")

def smooth01(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)

# ---- mevcut cekirdek toplamini stashla (eski isimlerle) ----
OLD_CORE = ["hips", "spine_01", "spine_02", "spine_03", "neck", "head", "snout"]
core_now = np.zeros(len(body))
for bn in OLD_CORE:
    if bn in S.GW:
        core_now += S.GW[bn][body]

# ---- sirt silueti -> ark ----
P = S.CO[body]
mid = P[np.abs(P[:, 0]) < 0.06]
def zmax_at(y, w=0.014):
    s = mid[np.abs(mid[:, 1] - y) < w]
    return float(s[:, 2].max()) if len(s) else 0.40

Y_HIP, Y_CHEST = 0.225, -0.060
NSEG = 5
ys = np.linspace(Y_HIP, Y_CHEST, NSEG + 1)
OFF = 0.115
zs = np.array([max(zmax_at(y) - OFF, 0.22) for y in ys])
print("ark:", [(round(float(y),3), round(float(z),3)) for y, z in zip(ys, zs)])

# ---- armature duzenle ----
bpy.ops.object.select_all(action='DESELECT')
arm_ob.select_set(True)
C.view_layer.objects.active = arm_ob
bpy.ops.object.mode_set(mode='EDIT')
ebs = arm_ob.data.edit_bones

# eski spine_01..03 sil
for nm in ("spine_01", "spine_02", "spine_03"):
    if nm in ebs:
        ebs.remove(ebs[nm])

ebs["hips"].head = (0, float(ys[0]), float(zs[0]))
# zincir
prev = None
for k in range(NSEG):
    nm = f"spine_{k+1:02d}"
    eb = ebs.new(nm)
    eb.head = (0, float(ys[k]), float(zs[k]))
    eb.tail = (0, float(ys[k+1]), float(zs[k+1]))
    eb.use_deform = True
    if k == 0:
        eb.parent = ebs["hips"]; eb.use_connect = False
    else:
        eb.parent = ebs[prev]; eb.use_connect = True
    eb.align_roll(Vector((0, 0, 1)))
    prev = nm
ebs["neck"].head = (0, float(ys[-1]), float(zs[-1]))
ebs["neck"].parent = ebs[prev]
ebs["neck"].use_connect = True
ebs["neck"].align_roll(Vector((0, 0, 1)))
for s_ in ("L", "R"):
    ebs[f"shoulder.{s_}"].parent = ebs[prev]   # gogus segmentine
bpy.ops.object.mode_set(mode='OBJECT')

# koleksiyon + deform bayragi
coll_def = arm_ob.data.collections.get("DEF")
for k in range(NSEG):
    b = arm_ob.data.bones[f"spine_{k+1:02d}"]
    if coll_def:
        coll_def.assign(b)
print("ARMATURE: 5 segment ark omurga kuruldu")

# ---- GW gruplarini guncelle: yeni isimler ekle ----
NEW_CORE = ["hips"] + [f"spine_{k+1:02d}" for k in range(NSEG)] + ["neck", "head", "snout"]
for bn in NEW_CORE:
    if bn not in S.GW:
        S.GW[bn] = np.zeros(S.NV)

# ---- s-partition (yeni zincir; kuyruk koku -> burun) ----
pts = [np.array(arm_ob.data.bones["hips"].tail_local),
       np.array(arm_ob.data.bones["hips"].head_local)]
for bn in NEW_CORE[1:]:
    pts.append(np.array(arm_ob.data.bones[bn].tail_local))
segs = []
acc = 0.0
jpos = [0.0]
for a, b in zip(pts, pts[1:]):
    L = float(np.linalg.norm(b - a))
    segs.append((a, b, acc, L))
    acc += L
    jpos.append(acc)
print("eksen:", [round(x, 3) for x in jpos])

best_s = np.zeros(len(body)); best_d = np.full(len(body), 1e9)
for a, b, s0, L in segs:
    ab = b - a
    t = np.clip(((P - a) @ ab) / max(ab @ ab, 1e-12), 0, 1)
    proj = a + t[:, None] * ab[None]
    d = np.linalg.norm(P - proj, axis=1)
    m = d < best_d
    best_d[m] = d[m]; best_s[m] = s0 + t[m] * L

nb = len(NEW_CORE)
BANDS = [0.050, 0.045, 0.045, 0.045, 0.045, 0.045, 0.042, 0.038]
def ramp(u, j, band):
    return smooth01((u - (j - band)) / (2 * band))
Wc = []
for k in range(nb):
    lo = np.ones(len(body)) if k == 0 else ramp(best_s, jpos[k], BANDS[k - 1])
    hi = ramp(best_s, jpos[k + 1], BANDS[k]) if k < nb - 1 else np.zeros(len(body))
    Wc.append(np.clip(lo - hi, 0, 1))
sW = sum(Wc); sW[sW <= 1e-9] = 1.0
for k, bn in enumerate(NEW_CORE):
    S.GW[bn][body] = core_now * Wc[k] / sW

# burun ucu rijit
nose = body[S.CO[body][:, 1] < -0.465]
for g in S.GW:
    S.GW[g][nose] = 0.0
S.GW["snout"][nose] = 1.0

# hijyen
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
print("SPINE ARC OK")
