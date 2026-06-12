import bpy, math, os, sys
import numpy as np
sys.path.append("/tmp/rig/td"); sys.path.append("/tmp/rig")
import skinlib as SL

OUT = "/tmp/rig/td/final"
S = SL.Skin("/tmp/rig/mouse_rig_td.blend")
C, D = bpy.context, bpy.data

# IK influence geri ac + rest poz
for b in S.arm.pose.bones:
    for con in b.constraints:
        if con.type == 'IK':
            con.influence = 1.0
S.reset_pose()
C.scene.frame_set(1)

# ---- agirlik haritalari (yeni alan) ----
scene = SL.setup_render(samples=10, res=760)
scene.view_settings.view_transform = 'Standard'
cams = SL.make_cams()
NV = S.NV
me = S.me
attr = me.color_attributes.get("WMap") or me.color_attributes.new(name="WMap", type='FLOAT_COLOR', domain='POINT')
wmat = D.materials.new("wmap")
wmat.use_nodes = True
nt = wmat.node_tree; nt.nodes.clear()
at = nt.nodes.new("ShaderNodeAttribute"); at.attribute_name = "WMap"
em = nt.nodes.new("ShaderNodeEmission")
outn = nt.nodes.new("ShaderNodeOutputMaterial")
nt.links.new(at.outputs["Color"], em.inputs[0])
nt.links.new(em.outputs[0], outn.inputs[0])
C.view_layer.material_override = wmat

def wcolor(w):
    c = np.zeros((NV, 4)); c[:, 3] = 1
    t = np.clip(w, 0, 1)
    seg = t * 4
    c[:, 0] = np.clip(seg - 2, 0, 1)
    c[:, 1] = np.clip(np.where(seg <= 1, seg, np.where(seg <= 3, 1, 4 - seg)), 0, 1)
    c[:, 2] = np.clip(1 - (seg - 1), 0, 1) * (seg < 2)
    c[w <= 0.001] = (0.16, 0.16, 0.2, 1)
    return c

WMAPS = [("hips", "side"), ("spine_02", "side"), ("spine_03", "side"), ("neck", "side"),
         ("head", "side"), ("snout", "side"), ("shoulder.L", "side"), ("upper_arm.L", "side"),
         ("forearm.L", "side"), ("hand.L", "side"), ("thigh.L", "side"), ("shin.L", "side"),
         ("foot.L", "side"), ("tail_01", "top"), ("tail_03", "top"), ("ear.L", "persp")]
def ortho(name, loc, rot, sc):
    cd = D.cameras.new(name); cd.type = 'ORTHO'; cd.ortho_scale = sc
    cam = D.objects.new(name, cd)
    C.scene.collection.objects.link(cam)
    cam.location = loc; cam.rotation_euler = rot
    return cam
cmap = {
    "side": ortho("w_side", (3, 0, 0.227), (math.radians(90), 0, math.radians(90)), 1.25),
    "top": ortho("w_top", (0, 0, 3), (0, 0, 0), 1.25),
    "persp": SL.look_cam("wpersp", (0.95, -1.05, 0.80), (0.0, 0.0, 0.227), 50),
}
for bn, view in WMAPS:
    w = S.GW.get(bn, np.zeros(NV))
    attr.data.foreach_set("color", wcolor(w).ravel())
    me.update()
    SL.render(f"{OUT}/w_{bn.replace('.', '_')}.png", cmap[view])
C.view_layer.material_override = None

bpy.ops.wm.save_as_mainfile(filepath="/tmp/rig/mouse_rig_td.blend")

# ---- export ----
os.makedirs("/tmp/rig/deliver", exist_ok=True)
bpy.ops.export_scene.gltf(
    filepath="/tmp/rig/deliver/mouse_rigged.glb",
    export_format='GLB',
    export_def_bones=True,
    export_skins=True,
    export_animations=True,
    export_rest_position_armature=True,
    export_materials='EXPORT',
    export_image_format='AUTO',
    export_yup=True,
)
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath="/tmp/rig/deliver/mouse_rig.blend", compress=True)
print("EXPORT OK")
