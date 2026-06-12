"""GERCEK tek parca: govde panellerinin bitisken kenarlarini kaynakla
(remove_doubles 1.5mm, yalniz body adasi; UV'ler loop-bazli => doku korunur).
Shape keyler oncesinde silinir (correctives.py yeniden kurar)."""
import sys
import numpy as np
sys.path.append("/tmp/rig/td"); sys.path.append("/tmp/rig")
import skinlib as SL
import bpy, bmesh

S = SL.Skin("/tmp/rig/mouse_rig_td.blend")
mouse = S.mouse
me = S.me

# shape keyleri kaldir (weld sonrasi yeniden kurulacak)
if me.shape_keys:
    for kb in list(me.shape_keys.key_blocks):
        try:
            kb.driver_remove("value")
        except Exception:
            pass
    mouse.shape_key_clear()
    print("shape keyler temizlendi")

NV0 = len(me.vertices)
import plan_data as P
IDS = {n: i for i, n in enumerate(P.MESH_RENAME.values())}
pid = np.empty(NV0, dtype=np.int32)
me.attributes["part_id"].data.foreach_get("value", pid)

bm = bmesh.new()
bm.from_mesh(me)
bm.verts.ensure_lookup_table()
lay = bm.verts.layers.int.get("part_id")
body_verts = [v for v in bm.verts if v[lay] == IDS["body"]] if lay else \
             [v for i, v in enumerate(bm.verts) if pid[i] == IDS["body"]]
print(f"body verts: {len(body_verts)}")
bmesh.ops.remove_doubles(bm, verts=body_verts, dist=0.0015)
bm.to_mesh(me)
bm.free()
me.update()
NV1 = len(me.vertices)
print(f"WELD: {NV0} -> {NV1} vert ({NV0-NV1} kaynaklandi)")

# komponent sayisi (body)
pid2 = np.empty(NV1, dtype=np.int32)
me.attributes["part_id"].data.foreach_get("value", pid2)
body2 = np.where(pid2 == IDS["body"])[0]
iset = {int(v): k for k, v in enumerate(body2)}
uf = list(range(len(body2)))
def find(a):
    while uf[a] != a:
        uf[a] = uf[uf[a]]; a = uf[a]
    return a
for e in me.edges:
    a, b = iset.get(int(e.vertices[0])), iset.get(int(e.vertices[1]))
    if a is not None and b is not None:
        ra, rb = find(a), find(b)
        if ra != rb:
            uf[ra] = rb
print("body komponent:", len({find(k) for k in range(len(body2))}))

bpy.ops.wm.save_as_mainfile(filepath="/tmp/rig/mouse_rig_td.blend")
print("SAVED")
