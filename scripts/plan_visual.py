import bpy, math, os, sys, json
import numpy as np
from mathutils import Vector

sys.path.append("/tmp/rig")
import plan_data as P

OUT = "/tmp/rig/plan"
os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.open_mainfile(filepath="/tmp/rig/mouse_imported.blend")

ico = bpy.data.objects.get("Icosphere")
if ico:
    bpy.data.objects.remove(ico, do_unlink=True)

# Center the model: midline x=-0.035 -> 0
bpy.data.objects["ParentNode"].location.x += P.MESH_SHIFT_X
bpy.context.view_layer.update()

scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.use_denoising = True
scene.render.resolution_x = 1400
scene.render.resolution_y = 1400

world = bpy.data.worlds.new("W")
scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes["Background"]
bg.inputs[0].default_value = (1, 1, 1, 1)
bg.inputs[1].default_value = 0.8

sun_data = bpy.data.lights.new("Sun", 'SUN')
sun_data.energy = 2.2
sun = bpy.data.objects.new("Sun", sun_data)
scene.collection.objects.link(sun)
sun.rotation_euler = (math.radians(45), math.radians(5), math.radians(30))

CZ = 0.227

def make_cam(name, loc, rot, ortho=True, scale=1.25):
    cd = bpy.data.cameras.new(name)
    if ortho:
        cd.type = 'ORTHO'; cd.ortho_scale = scale
    else:
        cd.type = 'PERSP'; cd.lens = 50
    cam = bpy.data.objects.new(name, cd)
    scene.collection.objects.link(cam)
    cam.location = loc; cam.rotation_euler = rot
    return cam

CAMS = {
    "side":  (make_cam("c_side", (3, 0, CZ), (math.radians(90), 0, math.radians(90)), True, 1.25), 1.25),
    "front": (make_cam("c_front", (0, -3, CZ), (math.radians(90), 0, 0), True, 0.9), 0.9),
    "top":   (make_cam("c_top", (0, 0, 3), (0, 0, 0), True, 1.25), 1.25),
}
persp = make_cam("c_persp", (0.95, -1.05, 0.80), (0, 0, 0), False)
d = Vector((0, 0, CZ)) - persp.location
persp.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()

def project(view, p):
    x, y, z = p
    s = CAMS[view][1]
    if view == "side":
        return 0.5 + y / s, 0.5 - (z - CZ) / s
    if view == "front":
        return 0.5 + x / s, 0.5 - (z - CZ) / s
    if view == "top":
        return 0.5 + x / s, 0.5 - y / s

MESHES = [o for o in bpy.data.objects if o.type == 'MESH']

def emis_mat(name, rgb, strength=1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs[0].default_value = (*rgb, 1)
    em.inputs[1].default_value = strength
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(em.outputs[0], out.inputs[0])
    return m

def add_octa(coll, name, head, tail, rgb):
    h = Vector(head); t = Vector(tail)
    L = (t - h).length
    r = max(min(L * 0.14, 0.013), 0.0045)
    z = (t - h).normalized()
    up = Vector((0, 0, 1)) if abs(z.dot(Vector((0, 0, 1)))) < 0.95 else Vector((0, 1, 0))
    x = z.cross(up).normalized(); y = z.cross(x).normalized()
    ring = h + z * (L * 0.18)
    vs = [h, ring + x * r, ring + y * r, ring - x * r, ring - y * r, t]
    fs = [(0, 1, 2), (0, 2, 3), (0, 3, 4), (0, 4, 1), (5, 2, 1), (5, 3, 2), (5, 4, 3), (5, 1, 4)]
    me = bpy.data.meshes.new(name)
    me.from_pydata([v[:] for v in vs], [], fs)
    ob = bpy.data.objects.new(name, me)
    ob.data.materials.append(emis_mat(name + "_m", rgb))
    coll.objects.link(ob)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=8, radius=r * 0.8, location=h)
    sp = bpy.context.active_object
    sp.name = name + "_j"
    sp.data.materials.append(emis_mat(name + "_jm", (1, 1, 1)))
    for c in list(sp.users_collection):
        c.objects.unlink(sp)
    coll.objects.link(sp)

def render(path, cam):
    scene.camera = cam
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)

labels = {"views": {}, "legend_groups": [], "zone_legend": [], "cur": {}}

# ============ textured base passes ============
scene.view_settings.view_transform = 'AgX'
scene.cycles.samples = 48
for v, (cam, _) in CAMS.items():
    render(f"{OUT}/tex_{v}.png", cam)
render(f"{OUT}/tex_persp.png", persp)

# ============ bone-only passes (transparent film) ============
scene.view_settings.view_transform = 'Standard'
scene.render.film_transparent = True
scene.cycles.samples = 24
world.node_tree.nodes["Background"].inputs[1].default_value = 1.0
for ob in MESHES:
    ob.hide_render = True

# --- current tripo rig ---
arm = bpy.data.objects["Armature"]
cur_coll = bpy.data.collections.new("CUR")
scene.collection.children.link(cur_coll)
wm = arm.matrix_world
for b in arm.data.bones:
    h = wm @ b.head_local; t = wm @ b.tail_local
    add_octa(cur_coll, "cur_" + b.name.replace("tripo::", ""), h, t, (0.9, 0.12, 0.1))

def bmid(name):
    b = arm.data.bones[name]
    return (wm @ ((b.head_local + b.tail_local) / 2))[:]

labels["cur"]["top"] = [
    {"text": "Sol arka bacak: 5 kemik", "uv": project("top", bmid("tripo::1_Left_Limb_2"))},
    {"text": "Sağ arka bacak: SADECE 2 kemik (asimetri!)", "uv": project("top", bmid("tripo::1_Right_Limb_0"))},
    {"text": "Anlamsız isimler: bone_6, bone_17...", "uv": project("top", bmid("bone_17"))},
]
labels["cur"]["side"] = [
    {"text": "Ön bacaklar kafa kemiğine bağlı (yanlış hiyerarşi)", "uv": project("side", bmid("bone_9"))},
    {"text": "Pati kemiği zeminin altına taşıyor", "uv": project("side", bmid("tripo::0_Left_Limb_2"))},
    {"text": "Root: gövdeyi delen dev dikey kemik", "uv": project("side", bmid("tripo::Root"))},
]
render(f"{OUT}/cur_top.png", CAMS["top"][0])
render(f"{OUT}/cur_side.png", CAMS["side"][0])
for ob in list(cur_coll.objects):
    bpy.data.objects.remove(ob, do_unlink=True)

# --- planned rig ---
plan_coll = bpy.data.collections.new("PLAN")
scene.collection.children.link(plan_coll)
for name, b in P.BONES.items():
    add_octa(plan_coll, "pl_" + name, b["head"], b["tail"], P.GROUP_COLORS[b["group"]])

def lbl(view, names):
    out = []
    for n in names:
        b = P.BONES[n]
        mid = tuple((b["head"][i] + b["tail"][i]) / 2 for i in range(3))
        u, v = project(view, mid)
        out.append({"name": n, "u": u, "v": v, "color": P.GROUP_COLORS[b["group"]]})
    return out

labels["views"]["side"] = lbl("side", [
    "root", "hips", "spine_01", "spine_02", "neck", "head", "snout",
    "ear.L", "whisker.L", "shoulder.L", "upper_arm.L", "forearm.L", "hand.L",
    "front_toes.L", "thigh.L", "shin.L", "foot.L", "toes.L",
    "tail_01", "tail_03", "tail_06",
])
labels["views"]["front"] = lbl("front", [
    "ear.L", "ear.R", "whisker.L", "whisker.R", "head", "snout", "neck",
    "upper_arm.L", "upper_arm.R", "forearm.L", "forearm.R", "hand.L", "hand.R",
])
labels["views"]["top"] = lbl("top", [
    "head", "neck", "spine_02", "spine_01", "hips",
    "tail_01", "tail_02", "tail_03", "tail_04", "tail_05", "tail_06",
    "ear.L", "ear.R", "shoulder.L", "shoulder.R", "thigh.L", "thigh.R",
])
labels["legend_groups"] = [{"name": g, "color": c} for g, c in P.GROUP_COLORS.items()]

render(f"{OUT}/plan_side.png", CAMS["side"][0])
render(f"{OUT}/plan_front.png", CAMS["front"][0])
render(f"{OUT}/plan_top.png", CAMS["top"][0])
render(f"{OUT}/plan_persp.png", persp)
for ob in list(plan_coll.objects):
    bpy.data.objects.remove(ob, do_unlink=True)

# ============ weight-zone preview (opaque) ============
scene.render.film_transparent = False
for ob in MESHES:
    ob.hide_render = False
ZC = P.zone_colors()

def seg_dist(pts, a, b):
    a = np.array(a); b = np.array(b)
    ab = b - a
    t = np.clip(((pts - a) @ ab) / max(ab @ ab, 1e-12), 0, 1)
    proj = a + t[:, None] * ab[None]
    return np.linalg.norm(pts - proj, axis=1)

for ob in MESHES:
    me = ob.data
    n = len(me.vertices)
    co = np.empty(n * 3)
    me.vertices.foreach_get("co", co)
    co = co.reshape(n, 3)
    M = np.array(ob.matrix_world)
    co = (np.c_[co, np.ones(n)] @ M.T)[:, :3]
    allowed = P.MESH_BONES[ob.name]
    D = np.stack([seg_dist(co, P.BONES[bn]["head"], P.BONES[bn]["tail"]) / P.radius(bn) for bn in allowed])
    idx = D.argmin(0)
    cols = np.array([(*ZC[bn], 1.0) for bn in allowed])
    vcols = cols[idx]
    attr = me.color_attributes.new(name="Zone", type='FLOAT_COLOR', domain='POINT')
    attr.data.foreach_set("color", vcols.ravel())
    m = bpy.data.materials.new("zone_" + ob.name)
    m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    at = nt.nodes.new("ShaderNodeAttribute"); at.attribute_name = "Zone"
    em = nt.nodes.new("ShaderNodeEmission")
    outn = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(at.outputs["Color"], em.inputs[0])
    nt.links.new(em.outputs[0], outn.inputs[0])
    me.materials.clear()
    me.materials.append(m)

labels["zone_legend"] = [{"name": n, "color": ZC[n]} for n in sorted(ZC)]

scene.cycles.samples = 12
render(f"{OUT}/zone_side.png", CAMS["side"][0])
render(f"{OUT}/zone_front.png", CAMS["front"][0])
render(f"{OUT}/zone_top.png", CAMS["top"][0])
render(f"{OUT}/zone_persp.png", persp)

with open(f"{OUT}/labels.json", "w") as f:
    json.dump(labels, f, indent=1)
print("PLAN VISUALS DONE")
