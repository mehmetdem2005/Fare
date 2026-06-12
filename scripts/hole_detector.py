"""DELIK DEDEKTORU: panel serbest kenarlarindan -normal isiniyla alttaki
yuzeye mesafe; pozda rest'e gore acilma = delik. Tum aksiyonlarda taranir."""
import sys, math
import numpy as np
sys.path.append("/tmp/rig/td"); sys.path.append("/tmp/rig")
import skinlib as SL
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

S = SL.Skin("/tmp/rig/mouse_rig_td.blend")
C = bpy.context
arm = S.arm
me = S.me

VN = np.empty(S.NV * 3)
me.vertices.foreach_get("normal", VN)
VN = VN.reshape(S.NV, 3)
VN = VN / np.maximum(np.linalg.norm(VN, axis=1)[:, None], 1e-9)

# serbest kenarlar (tek yuzlu edge) — biyik haric
from collections import Counter
ec = Counter()
for p in me.polygons:
    vs = list(p.vertices)
    for i in range(len(vs)):
        a, b = vs[i], vs[(i + 1) % len(vs)]
        ec[(min(a, b), max(a, b))] += 1
bverts = set()
for (a, b), c in ec.items():
    if c == 1 and not (S.wh_mask[a] or S.wh_mask[b]):
        bverts.add(a); bverts.add(b)
bverts = np.array(sorted(bverts))
print(f"serbest kenar verti: {len(bverts)}")

polys = [tuple(p.vertices) for p in me.polygons]
np_polys = [pv for pv in polys if not any(S.wh_mask[q] for q in pv)]

def gap_at(coords, normals):
    bvh = BVHTree.FromPolygons([tuple(v) for v in coords], np_polys)
    out = np.full(len(bverts), np.nan)
    for k, vi in enumerate(bverts):
        n = Vector(normals[vi].tolist())
        o = Vector(coords[vi].tolist())
        hit = bvh.ray_cast(o - n * 0.0008, -n, 0.02)
        if hit[0] is not None:
            out[k] = hit[3]
    return out

rest_gap = gap_at(S.CO, VN)

def posed_coords():
    C.view_layer.update()
    dg = C.evaluated_depsgraph_get()
    mev = S.mouse.evaluated_get(dg)
    pc = np.empty(S.NV * 3)
    mev.data.vertices.foreach_get("co", pc)
    pn = np.empty(S.NV * 3)
    mev.data.vertices.foreach_get("normal", pn)
    pn = pn.reshape(S.NV, 3)
    pn = pn / np.maximum(np.linalg.norm(pn, axis=1)[:, None], 1e-9)
    return pc.reshape(S.NV, 3), pn

FRAMES = {"walk": [1, 9, 17, 25], "run": [1, 4, 8, 11], "idle": [24, 66],
          "sniff": [31], "look_around": [24, 84], "eat": [15], "alert": [11]}
print("=== DELIK RAPORU (acilma mm; >2mm sorun) ===")
worst_all = []
for nm, frames in FRAMES.items():
    act = bpy.data.actions[nm]
    arm.animation_data.action = act
    for f in frames:
        C.scene.frame_set(f)
        pc, pn = posed_coords()
        g = gap_at(pc, pn)
        opening = np.where(np.isnan(g) | np.isnan(rest_gap), 0.0, g - rest_gap)
        idx = np.argsort(-opening)[:5]
        mx = float(opening[idx[0]])
        n2 = int((opening > 0.002).sum())
        print(f"{nm} f{f}: max={mx*1000:.1f}mm  >2mm:{n2}")
        for q in idx[:3]:
            if opening[q] > 0.002:
                vi = bverts[q]
                worst_all.append((float(opening[q]), nm, f, int(vi), tuple(round(float(x), 3) for x in S.CO[vi])))
worst_all.sort(reverse=True)
print("--- en kotu 10 nokta ---")
for op, nm, f, vi, co in worst_all[:10]:
    ws = {g: round(S.GW[g][vi], 2) for g in S.GW if S.GW[g][vi] > 0.05}
    print(f"  {op*1000:.1f}mm {nm} f{f} v{vi} co={co} W={ws}")
print("DETECTOR DONE")
