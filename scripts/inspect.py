import bpy, sys, json
from mathutils import Vector

GLB = "/root/.claude/uploads/d8a02c1f-f25d-529e-ade2-5aaae60cb433/555c4f06-mouse3dmodel1k.glb"

# Clean scene
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)

print("=" * 60)
print("SCENE OBJECTS")
print("=" * 60)
for ob in bpy.data.objects:
    parent = ob.parent.name if ob.parent else None
    print(f"- {ob.name} | type={ob.type} | parent={parent}")
    print(f"    loc={tuple(round(v,4) for v in ob.location)} rot={tuple(round(v,3) for v in ob.rotation_euler)} scale={tuple(round(v,4) for v in ob.scale)}")
    if ob.type == 'MESH':
        me = ob.data
        print(f"    verts={len(me.vertices)} edges={len(me.edges)} polys={len(me.polygons)}")
        tris = sum(len(p.vertices) - 2 for p in me.polygons)
        print(f"    tris={tris}")
        print(f"    uv_layers={[l.name for l in me.uv_layers]}")
        print(f"    color_attrs={[a.name for a in me.color_attributes]}")
        print(f"    shape_keys={bool(me.shape_keys)}")
        print(f"    vertex_groups={[g.name for g in ob.vertex_groups]}")
        print(f"    materials={[m.name if m else None for m in me.materials]}")
        mods = [(m.name, m.type) for m in ob.modifiers]
        print(f"    modifiers={mods}")
        # world-space bounding box
        wm = ob.matrix_world
        coords = [wm @ Vector(c) for c in ob.bound_box]
        xs = [c.x for c in coords]; ys = [c.y for c in coords]; zs = [c.z for c in coords]
        print(f"    world bbox X=[{min(xs):.4f},{max(xs):.4f}] Y=[{min(ys):.4f},{max(ys):.4f}] Z=[{min(zs):.4f},{max(zs):.4f}]")
        print(f"    dims: {max(xs)-min(xs):.4f} x {max(ys)-min(ys):.4f} x {max(zs)-min(zs):.4f}")
    if ob.type == 'ARMATURE':
        print(f"    bones={len(ob.data.bones)}")
        for b in ob.data.bones:
            print(f"      bone: {b.name} parent={b.parent.name if b.parent else None}")

print()
print("=" * 60)
print("MATERIALS / TEXTURES")
print("=" * 60)
for mat in bpy.data.materials:
    print(f"- {mat.name}")
    if mat.use_nodes:
        for n in mat.node_tree.nodes:
            if n.type == 'TEX_IMAGE' and n.image:
                print(f"    image: {n.image.name} {n.image.size[0]}x{n.image.size[1]}")

print()
print("ANIMATIONS:", [a.name for a in bpy.data.actions])
print("IMAGES:", [(i.name, i.size[0], i.size[1]) for i in bpy.data.images])

# Save as .blend for later steps
bpy.ops.wm.save_as_mainfile(filepath="/tmp/rig/mouse_imported.blend")
print("SAVED /tmp/rig/mouse_imported.blend")
