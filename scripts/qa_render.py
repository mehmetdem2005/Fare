import bpy, math, os, sys, json
import numpy as np
from mathutils import Vector

sys.path.append("/tmp/rig")
import plan_data as P

OUT = "/tmp/rig/qa"
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath="/tmp/rig/mouse_rig.blend")
C, D = bpy.context, bpy.data
mouse = D.objects["Mouse"]
arm = D.objects["MouseRig"]

scene = C.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.use_denoising = True
scene.render.resolution_x = 1100
scene.render.resolution_y = 1100

world = D.worlds.new("W")
scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (1, 1, 1, 1)
world.node_tree.nodes["Background"].inputs[1].default_value = 0.8
sun = D.objects.new("Sun", D.lights.new("S", 'SUN'))
sun.data.energy = 2.2
scene.collection.objects.link(sun)
sun.rotation_euler = (math.radians(45), math.radians(5), math.radians(30))

CZ = 0.227
def make_cam(name, loc, rot, ortho=True, scale=1.25):
    cd = D.cameras.new(name)
    if ortho:
        cd.type = 'ORTHO'; cd.ortho_scale = scale
    else:
        cd.type = 'PERSP'; cd.lens = 50
    cam = D.objects.new(name, cd)
    scene.collection.objects.link(cam)
    cam.location = loc; cam.rotation_euler = rot
    return cam

cam_side = make_cam("c_side", (3, 0, CZ), (math.radians(90), 0, math.radians(90)), True, 1.25)
cam_front = make_cam("c_front", (0, -3, CZ), (math.radians(90), 0, 0), True, 0.9)
cam_top = make_cam("c_top", (0, 0, 3), (0, 0, 0), True, 1.25)
cam_persp = make_cam("c_persp", (0.95, -1.05, 0.80), (0, 0, 0), False)
d = Vector((0, 0, CZ)) - cam_persp.location
cam_persp.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()

def render(path, cam, samples=32, transform='AgX'):
    scene.cycles.samples = samples
    scene.view_settings.view_transform = transform
    scene.camera = cam
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)

def project(cam, p, scale):
    x, y, z = p
    if cam is cam_side:
        return 0.5 + y / scale, 0.5 - (z - CZ) / scale
    if cam is cam_front:
        return 0.5 + x / scale, 0.5 - (z - CZ) / scale
    if cam is cam_top:
        return 0.5 + x / scale, 0.5 - y / scale

# ---------- textured base views ----------
render(f"{OUT}/tex_side.png", cam_side, 48)
render(f"{OUT}/tex_front.png", cam_front, 48)
render(f"{OUT}/tex_top.png", cam_top, 48)
render(f"{OUT}/tex_persp.png", cam_persp, 48)

# ---------- skeleton overlay passes (thin proxies from REAL bones) ----------
def emis_mat(name, rgb):
    m = D.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs[0].default_value = (*rgb, 1)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(em.outputs[0], out.inputs[0])
    return m

def group_of(bn):
    if bn.startswith("ear"):
        return "ear"
    if bn in P.BONES:
        return P.BONES[bn]["group"]
    return "core"

proxy_coll = D.collections.new("PROXY")
scene.collection.children.link(proxy_coll)

def add_octa(name, h, t, rgb, rscale=0.10):
    h, t = Vector(h), Vector(t)
    L = (t - h).length
    r = max(min(L * rscale, 0.009), 0.003)
    z = (t - h).normalized()
    up = Vector((0, 0, 1)) if abs(z.dot(Vector((0, 0, 1)))) < 0.95 else Vector((0, 1, 0))
    x = z.cross(up).normalized(); y = z.cross(x).normalized()
    ring = h + z * (L * 0.16)
    vs = [h, ring + x * r, ring + y * r, ring - x * r, ring - y * r, t]
    fs = [(0,1,2),(0,2,3),(0,3,4),(0,4,1),(5,2,1),(5,3,2),(5,4,3),(5,1,4)]
    me2 = D.meshes.new(name)
    me2.from_pydata([v[:] for v in vs], [], fs)
    ob = D.objects.new(name, me2)
    ob.data.materials.append(emis_mat(name + "_m", rgb))
    proxy_coll.objects.link(ob)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=10, ring_count=6, radius=r*0.9, location=h)
    sp = C.active_object
    sp.data.materials.append(emis_mat(name + "_jm", (1, 1, 1)))
    for cc in list(sp.users_collection):
        cc.objects.unlink(sp)
    proxy_coll.objects.link(sp)

for b in arm.data.bones:
    if not b.use_deform:
        continue
    add_octa("px_" + b.name, b.head_local, b.tail_local, P.GROUP_COLORS[group_of(b.name)])
# root marker (gray)
rb = arm.data.bones["root"]
add_octa("px_root", rb.head_local, rb.tail_local, (0.45, 0.45, 0.45))

scene.render.film_transparent = True
mouse.hide_render = True
render(f"{OUT}/sk_side.png", cam_side, 20, 'Standard')
render(f"{OUT}/sk_front.png", cam_front, 20, 'Standard')
render(f"{OUT}/sk_top.png", cam_top, 20, 'Standard')
render(f"{OUT}/sk_persp.png", cam_persp, 20, 'Standard')
mouse.hide_render = False
scene.render.film_transparent = False
for ob in list(proxy_coll.objects):
    D.objects.remove(ob, do_unlink=True)

# labels for skeleton sheets
def bone_mid(bn):
    b = arm.data.bones[bn]
    return tuple((Vector(b.head_local) + Vector(b.tail_local)) / 2)

def lblset(cam, scale, names):
    out = []
    for n in names:
        u, v = project(cam, bone_mid(n), scale)
        out.append({"name": n, "u": u, "v": v, "color": P.GROUP_COLORS[group_of(n)]})
    return out

labels = {"views": {}}
labels["views"]["side"] = lblset(cam_side, 1.25, [
    "root", "hips", "spine_01", "spine_02", "spine_03", "neck", "head", "snout",
    "ear.L", "shoulder.L", "upper_arm.L", "forearm.L", "hand.L", "front_toes.L",
    "thigh.L", "shin.L", "foot.L", "toes.L", "tail_01", "tail_03", "tail_06"])
labels["views"]["front"] = lblset(cam_front, 0.9, [
    "ear.L", "ear.R", "head", "snout", "neck", "upper_arm.L", "upper_arm.R",
    "forearm.L", "forearm.R", "hand.L", "hand.R"])
labels["views"]["top"] = lblset(cam_top, 1.25, [
    "head", "neck", "spine_03", "spine_02", "spine_01", "hips",
    "tail_01", "tail_02", "tail_03", "tail_04", "tail_05", "tail_06",
    "ear.L", "ear.R", "shoulder.L", "shoulder.R", "thigh.L", "thigh.R"])
json.dump(labels, open(f"{OUT}/sk_labels.json", "w"))

# ---------- weight heat maps ----------
NVm = len(mouse.data.vertices)
def wmap_colormap(w):
    c = np.zeros((len(w), 4)); c[:, 3] = 1
    t = np.clip(w, 0, 1)
    # blue->cyan->green->yellow->red
    seg = np.clip(t * 4, 0, 4)
    c[:, 0] = np.clip(seg - 2, 0, 1)
    c[:, 1] = np.clip(np.where(seg < 2, seg, 4 - seg + 1), 0, 1) * (t > 0.001)
    c[:, 1] = np.clip(np.where(seg <= 1, seg, np.where(seg <= 3, 1, 4 - seg)), 0, 1)
    c[:, 2] = np.clip(1 - (seg - 1), 0, 1) * (seg < 2)
    base = w <= 0.001
    c[base] = (0.18, 0.18, 0.22, 1)
    return c

orig_mat = mouse.data.materials[0]
attr = mouse.data.color_attributes.new(name="WMap", type='FLOAT_COLOR', domain='POINT')
wmat = D.materials.new("wmap")
wmat.use_nodes = True
nt = wmat.node_tree; nt.nodes.clear()
at = nt.nodes.new("ShaderNodeAttribute"); at.attribute_name = "WMap"
em = nt.nodes.new("ShaderNodeEmission")
outn = nt.nodes.new("ShaderNodeOutputMaterial")
nt.links.new(at.outputs["Color"], em.inputs[0])
nt.links.new(em.outputs[0], outn.inputs[0])

WEIGHT_VIEWS = [
    ("hips", "side"), ("spine_01", "side"), ("spine_02", "side"), ("spine_03", "side"),
    ("neck", "side"), ("head", "side"), ("snout", "side"), ("ear.L", "persp"),
    ("shoulder.L", "side"), ("upper_arm.L", "side"), ("forearm.L", "side"), ("hand.L", "side"),
    ("front_toes.L", "side"), ("thigh.L", "side"), ("shin.L", "side"), ("foot.L", "side"),
    ("toes.L", "side"), ("tail_02", "top"), ("tail_04", "top"), ("snout+whiskers", "persp"),
]
cams = {"side": cam_side, "front": cam_front, "top": cam_top, "persp": cam_persp}

mouse.data.materials[0] = wmat
for bn, view in WEIGHT_VIEWS:
    gname = "snout" if bn == "snout+whiskers" else bn
    vg = mouse.vertex_groups.get(gname)
    w = np.zeros(NVm)
    if vg:
        gi = vg.index
        for v in mouse.data.vertices:
            for ge in v.groups:
                if ge.group == gi:
                    w[v.index] = ge.weight
    cols = wmap_colormap(w)
    attr.data.foreach_set("color", cols.ravel())
    mouse.data.update()
    safe = bn.replace(".", "_").replace("+", "_")
    render(f"{OUT}/w_{safe}.png", cams[view], 10, 'Standard')
mouse.data.materials[0] = orig_mat

# ---------- FK pose tests ----------
pb = arm.pose.bones
ik_cons = []
for b in pb:
    for con in b.constraints:
        if con.type == 'IK':
            ik_cons.append(con)

def reset_pose():
    for b in pb:
        b.location = (0, 0, 0)
        b.rotation_mode = 'XYZ'
        b.rotation_euler = (0, 0, 0)
        b.scale = (1, 1, 1)

def rot(bn, rx=0, ry=0, rz=0):
    pb[bn].rotation_mode = 'XYZ'
    pb[bn].rotation_euler = (rx, ry, rz)

POSES = {
    "P1_bas_cevirme": lambda: (rot("neck", 0, 0, 0.30), rot("head", 0.1, 0, 0.45)),
    "P2_on_bacak_L": lambda: (rot("upper_arm.L", -0.55), rot("forearm.L", 0.45), rot("hand.L", -0.35)),
    "P3_arka_bacak_R": lambda: (rot("thigh.R", 0.5), rot("shin.R", -0.55), rot("foot.R", 0.40)),
    "P4_omurga_kuyruk": lambda: (rot("spine_01", 0.10), rot("spine_02", 0.14), rot("spine_03", 0.12),
                                  rot("neck", -0.15), rot("hips", -0.08),
                                  *[rot(f"tail_{i:02d}", 0, 0, 0.30) for i in range(1, 7)]),
    "P5_kulak_burun": lambda: (rot("ear.L", 0.45), rot("ear.R", -0.35), rot("snout", 0.18)),
}

for con in ik_cons:
    con.influence = 0.0
for name, fn in POSES.items():
    reset_pose()
    fn()
    C.view_layer.update()
    render(f"{OUT}/pose_{name}_persp.png", cam_persp, 28)
    render(f"{OUT}/pose_{name}_side.png", cam_side, 28)
reset_pose()

# ---------- IK test ----------
for con in ik_cons:
    con.influence = 1.0
pb["ik_foot.L"].location = (0, 0.010, 0.060)   # local: lift + slight forward
pb["ik_hand.R"].location = (0, -0.01, 0.050)
C.view_layer.update()
render(f"{OUT}/pose_IK_test_persp.png", cam_persp, 28)
render(f"{OUT}/pose_IK_test_front.png", cam_front, 28)
reset_pose()
C.view_layer.update()

print("QA RENDERS DONE")
