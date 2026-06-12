import bpy, math, os
from mathutils import Vector

OUT = "/tmp/rig/recon"
os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.open_mainfile(filepath="/tmp/rig/mouse_imported.blend")

# Remove junk icosphere
ico = bpy.data.objects.get("Icosphere")
if ico:
    bpy.data.objects.remove(ico, do_unlink=True)

scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 48
scene.cycles.use_denoising = True
scene.render.resolution_x = 1200
scene.render.resolution_y = 1200
scene.render.film_transparent = False

# World light
world = bpy.data.worlds.new("W")
scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes["Background"]
bg.inputs[0].default_value = (1, 1, 1, 1)
bg.inputs[1].default_value = 0.55

# Sun
sun_data = bpy.data.lights.new("Sun", 'SUN')
sun_data.energy = 2.5
sun = bpy.data.objects.new("Sun", sun_data)
scene.collection.objects.link(sun)
sun.rotation_euler = (math.radians(50), math.radians(10), math.radians(25))

CENTER = Vector((0.0, 0.0, 0.227))

def make_cam(name, loc, rot, ortho=True, scale=1.2):
    cd = bpy.data.cameras.new(name)
    if ortho:
        cd.type = 'ORTHO'
        cd.ortho_scale = scale
    else:
        cd.type = 'PERSP'
        cd.lens = 50
    cam = bpy.data.objects.new(name, cd)
    scene.collection.objects.link(cam)
    cam.location = loc
    cam.rotation_euler = rot
    return cam

cams = {
    "front":  make_cam("c_front", (0, -3, 0.227), (math.radians(90), 0, 0), True, 0.85),
    "back":   make_cam("c_back",  (0,  3, 0.227), (math.radians(90), 0, math.radians(180)), True, 0.85),
    "right":  make_cam("c_right", (3, 0, 0.227), (math.radians(90), 0, math.radians(90)), True, 1.25),
    "top":    make_cam("c_top",   (0, 0, 3), (0, 0, 0), True, 1.25),
}
# 3/4 perspective, look at center
pc = make_cam("c_persp", (0.95, -1.05, 0.85), (0,0,0), False)
d = CENTER - pc.location
pc.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()

parts = [ob for ob in bpy.data.objects if ob.type == 'MESH']
parts.sort(key=lambda o: o.name)

# ---- pass 1: textured renders ----
for vname, cam in {**cams, "persp": pc}.items():
    scene.camera = cam
    scene.render.filepath = f"{OUT}/tex_{vname}.png"
    bpy.ops.render.render(write_still=True)

# ---- pass 2: part-ID flat colors ----
PALETTE = [
    (0.90, 0.10, 0.10), (0.10, 0.35, 0.95), (0.10, 0.80, 0.20), (0.95, 0.75, 0.05),
    (0.75, 0.10, 0.85), (0.05, 0.85, 0.85), (0.95, 0.45, 0.05), (0.45, 0.25, 0.05),
    (0.95, 0.45, 0.75), (0.35, 0.95, 0.45), (0.55, 0.55, 0.95),
]
for i, ob in enumerate(parts):
    m = bpy.data.materials.new(f"id_{i}")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs[0].default_value = (*PALETTE[i % len(PALETTE)], 1)
    outn = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(em.outputs[0], outn.inputs[0])
    ob.data.materials.clear()
    ob.data.materials.append(m)
    print(f"PARTCOLOR {ob.name} -> {PALETTE[i % len(PALETTE)]}")

scene.cycles.samples = 8
scene.cycles.use_denoising = False
for vname, cam in {**cams, "persp": pc}.items():
    scene.camera = cam
    scene.render.filepath = f"{OUT}/id_{vname}.png"
    bpy.ops.render.render(write_still=True)

# ---- dump tripo bone positions (reference only) ----
arm = bpy.data.objects.get("Armature")
print("TRIPO_BONES_WORLD")
if arm:
    wm = arm.matrix_world
    for b in arm.data.bones:
        h = wm @ b.head_local
        t = wm @ b.tail_local
        print(f"BONE {b.name} | head=({h.x:.4f},{h.y:.4f},{h.z:.4f}) tail=({t.x:.4f},{t.y:.4f},{t.z:.4f})")
print("DONE")
