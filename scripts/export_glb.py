import bpy, os

bpy.ops.wm.open_mainfile(filepath="/tmp/rig/mouse_rig.blend")
C, D = bpy.context, bpy.data
os.makedirs("/tmp/rig/deliver", exist_ok=True)

arm = D.objects["MouseRig"]
# guarantee clean rest pose before export
for b in arm.pose.bones:
    b.location = (0, 0, 0)
    b.rotation_mode = 'XYZ'
    b.rotation_euler = (0, 0, 0)
    b.scale = (1, 1, 1)
C.view_layer.update()

bpy.ops.export_scene.gltf(
    filepath="/tmp/rig/deliver/mouse_rigged.glb",
    export_format='GLB',
    export_def_bones=True,
    export_skins=True,
    export_animations=False,
    export_rest_position_armature=True,
    export_materials='EXPORT',
    export_image_format='AUTO',
    export_yup=True,
)
print("GLB OK")

# packed .blend copy for delivery
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath="/tmp/rig/deliver/mouse_rig.blend", compress=True)
print("BLEND OK")
