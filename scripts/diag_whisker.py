import bpy, sys
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.append("/tmp/rig")
bpy.ops.wm.open_mainfile(filepath="/tmp/rig/mouse_rig.blend")
C, D = bpy.context, bpy.data
mouse = D.objects["Mouse"]
arm = D.objects["MouseRig"]
me = mouse.data
NV = len(me.vertices)

pid = np.empty(NV, dtype=np.int32)
me.attributes["part_id"].data.foreach_get("value", pid)
CO = np.empty(NV * 3)
me.vertices.foreach_get("co", CO)
CO = CO.reshape(NV, 3)

gnames = {g.index: g.name for g in mouse.vertex_groups}
def wdict(vi):
    return {gnames[ge.group]: round(ge.weight, 3) for ge in me.vertices[vi].groups if ge.weight > 0.003}

# whisker_L island id? part order: whiskers_L=0 (from MESH_RENAME insertion order)
import plan_data as P
ids = {n: i for i, n in enumerate(P.MESH_RENAME.values())}
wh = np.where(pid == ids["whiskers_L"])[0]
body = np.where(pid == ids["body"])[0]
body_set = set(int(i) for i in body)

polys = [tuple(p.vertices) for p in me.polygons]
body_polys = [pv for pv in polys if all(int(q) in body_set for q in pv)]
BODY_BVH = BVHTree.FromPolygons([tuple(v) for v in CO], body_polys)

# pick 5 whisker verts closest to body (roots)
dists = [(BODY_BVH.find_nearest(Vector(CO[v]))[3], int(v)) for v in wh]
dists.sort()
samples = [v for _, v in dists[:5]]

# pose: head turn (same as test_head)
ik_cons = [c for b in arm.pose.bones for c in b.constraints if c.type == 'IK']
for c in ik_cons:
    c.influence = 0.0
for bn, rot in (("neck", (0.10, 0, 0.45)), ("head", (0.15, 0, 0.55))):
    pb = arm.pose.bones[bn]
    pb.rotation_mode = 'XYZ'
    pb.rotation_euler = rot
C.view_layer.update()
dg = C.evaluated_depsgraph_get()
mev = mouse.evaluated_get(dg)
pco = np.empty(NV * 3)
mev.data.vertices.foreach_get("co", pco)
pco = pco.reshape(NV, 3)

print("=== WHISKER ROOT vs FACE SKIN (posed) ===")
for v in samples:
    co, n, fidx, dist = BODY_BVH.find_nearest(Vector(CO[v]))
    pvs = body_polys[fidx]
    # nearest body vert of that face
    bv = min(pvs, key=lambda q: np.linalg.norm(CO[q] - CO[v]))
    rest_gap = float(np.linalg.norm(CO[v] - CO[bv]))
    posed_gap = float(np.linalg.norm(pco[v] - pco[bv]))
    print(f"wh v{v}: rest_gap={rest_gap*1000:.1f}mm posed_gap={posed_gap*1000:.1f}mm")
    print(f"   wh W: {wdict(v)}")
    print(f"   face W: {wdict(int(bv))}")

# max whisker drift overall
wh_drift = []
for v in wh[::7]:
    co, n, fidx, dist = BODY_BVH.find_nearest(Vector(CO[v]))
    pvs = body_polys[fidx]
    bv = min(pvs, key=lambda q: np.linalg.norm(CO[q] - CO[v]))
    drift = np.linalg.norm((pco[v] - pco[bv]) - (CO[v] - CO[bv]))
    wh_drift.append((float(drift), int(v)))
wh_drift.sort(reverse=True)
print("\nTOP DRIFT (posed offset change vs rest):")
for d, v in wh_drift[:8]:
    print(f"  v{v}: {d*1000:.1f}mm  W={wdict(v)}  nearestdist={BODY_BVH.find_nearest(Vector(CO[v]))[3]*1000:.1f}mm")
