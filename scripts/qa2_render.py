import bpy, math, os, sys
from mathutils import Vector

sys.path.append("/tmp/rig")
OUT = "/tmp/rig/qa2"
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath="/tmp/rig/mouse_rig.blend")
C, D = bpy.context, bpy.data
mouse = D.objects["Mouse"]
arm = D.objects["MouseRig"]

scene = C.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 36
scene.cycles.use_denoising = True
scene.render.resolution_x = 1000
scene.render.resolution_y = 1000
scene.view_settings.view_transform = 'AgX'

world = D.worlds.new("W")
scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (1, 1, 1, 1)
world.node_tree.nodes["Background"].inputs[1].default_value = 0.85
sun = D.objects.new("Sun", D.lights.new("S", 'SUN'))
sun.data.energy = 2.3
scene.collection.objects.link(sun)
sun.rotation_euler = (math.radians(50), math.radians(8), math.radians(35))

def look_cam(name, loc, target, lens=60):
    cd = D.cameras.new(name)
    cd.lens = lens
    cam = D.objects.new(name, cd)
    scene.collection.objects.link(cam)
    cam.location = loc
    cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    return cam

CAMS = {
    "arm":  look_cam("c_arm", (0.55, -0.78, 0.30), (0.09, -0.20, 0.13)),
    "hind": look_cam("c_hind", (-0.72, 0.60, 0.32), (-0.13, 0.07, 0.10)),
    "head": look_cam("c_head", (0.55, -0.80, 0.55), (0.0, -0.28, 0.28)),
    "tail": look_cam("c_tail", (0.60, 0.78, 0.38), (0.05, 0.33, 0.06)),
    "body": look_cam("c_body", (1.05, -0.45, 0.50), (0.0, 0.0, 0.22), lens=42),
}

pb = arm.pose.bones
ik_cons = [c for b in pb for c in b.constraints if c.type == 'IK']
for c in ik_cons:
    c.influence = 0.0

def reset_pose():
    for b in pb:
        b.location = (0, 0, 0)
        b.rotation_mode = 'XYZ'
        b.rotation_euler = (0, 0, 0)
        b.scale = (1, 1, 1)

def rot(bn, rx=0, ry=0, rz=0):
    pb[bn].rotation_mode = 'XYZ'
    pb[bn].rotation_euler = (rx, ry, rz)

def render(path, cam):
    scene.camera = cam
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)

TESTS = {
    "arm": (["arm"], lambda: (rot("upper_arm.L", -0.85), rot("forearm.L", 0.75), rot("hand.L", -0.50))),
    "hind": (["hind"], lambda: (rot("thigh.R", 0.60), rot("shin.R", -0.70), rot("foot.R", 0.50), rot("toes.R", -0.30))),
    "head": (["head"], lambda: (rot("neck", 0.10, 0, 0.45), rot("head", 0.15, 0, 0.55),
                                 rot("ear.L", 0.50), rot("ear_02.L", 0.30), rot("ear.R", -0.40))),
    "tail": (["tail"], lambda: ([rot(f"tail_{i:02d}", 0.06, 0, 0.35) for i in range(1, 7)])),
    "body": (["body"], lambda: (rot("spine_01", 0.18), rot("spine_02", 0.16), rot("spine_03", 0.14),
                                 rot("neck", -0.22), rot("hips", -0.15))),
}

# rest renders
reset_pose()
C.view_layer.update()
for vname, cam in CAMS.items():
    render(f"{OUT}/rest_{vname}.png", cam)

for tname, (views, fn) in TESTS.items():
    reset_pose()
    fn()
    C.view_layer.update()
    for v in views:
        render(f"{OUT}/test_{tname}.png", CAMS[v])
reset_pose()
C.view_layer.update()
print("QA2 DONE")
