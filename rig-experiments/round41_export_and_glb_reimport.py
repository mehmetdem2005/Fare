"""Round41 experimental GLB export and re-import of independently L3-passed
Round39 corrected 49-bone rig. NEVER touches deliver/ nor promotes production.
Requires morph weights, 24+1 gait sampling and actual Blender re-import.
Godot runtime/Android is a separate L5 approval step.
"""
import bpy,sys,json,struct,hashlib,traceback,math
from pathlib import Path

EXPECTED="bf24c3c00367790af976e5f407cb9c3b20ad11754845bd0eb63d5cbe4042d07b"
ACT="run_sprint_v8_ik_phase_NUMERIC_REVIEW"

def cli():
 import argparse
 p=argparse.ArgumentParser()
 for k in ("--candidate","--out"):p.add_argument(k,required=True)
 return p.parse_args(sys.argv[sys.argv.index("--")+1:])

def load_glb_json(path):
 data=path.read_bytes()
 if len(data)<28 or data[:4]!=b"glTF":raise RuntimeError("Not a valid binary glTF header")
 magic,version,length=struct.unpack_from("<4sII",data)
 if version!=2 or length!=len(data):raise RuntimeError("glTF size/version mismatch")
 offset=12;payload=None
 while offset<len(data):
  n,tag=struct.unpack_from("<II",data,offset);offset+=8
  chunk=data[offset:offset+n];offset+=n
  if tag==0x4e4f534a:payload=json.loads(chunk.decode("utf-8").rstrip(" \x00"))
 if not payload:raise RuntimeError("No readable glTF binary JSON scene")
 return payload

def main():
 args=cli();out=Path(args.out).resolve();out.mkdir(parents=True,exist_ok=True)
 report={"status":"STARTED","level":"GLB exporter and Blender reimport check only; Godot/mobile L5 unverified"}
 try:
  path=Path(args.candidate).resolve()
  if hashlib.sha256(path.read_bytes()).hexdigest()!=EXPECTED:
   raise RuntimeError("Saved candidate not the exact independently reopened file")
  bpy.ops.wm.open_mainfile(filepath=str(path))
  meshes=[o for o in bpy.data.objects if o.type=="MESH" and any(
      m.type=="ARMATURE" and m.object and len(m.object.data.bones)==49 for m in o.modifiers)]
  if not meshes:raise RuntimeError("No original 49-bone skinned mesh")
  mesh=max(meshes,key=lambda m:len(m.data.vertices))
  arm=next(m.object for m in mesh.modifiers if m.type=="ARMATURE" and m.object)
  if len(mesh.data.vertices)!=19466 or len(arm.data.bones)!=49:
   raise RuntimeError("Wrong original skinned asset")
  action=bpy.data.actions.get(ACT)
  if action is None:raise RuntimeError("Original v8 action absent")
  shape=mesh.data.shape_keys
  if shape is None or "R39_F14_ORIGINAL_REFERENCE" not in shape.key_blocks:
   raise RuntimeError("Original anatomically repaired R39 key absent")
  arm.animation_data_create()
  for nt in arm.animation_data.nla_tracks:nt.mute=True
  arm.animation_data.action=action
  scene=bpy.context.scene;scene.frame_start=1;scene.frame_end=25
  shape_values={}
  for f in (1,14,15,25):
   scene.frame_set(f)
   shape_values[f]=float(shape.key_blocks["R39_F14_ORIGINAL_REFERENCE"].value)
  if abs(shape_values[14]-.9)>.0005:
   raise RuntimeError("Saved f14 key animation not evaluated at export")
  if abs(shape_values[1])>1e-5 or abs(shape_values[25])>1e-5:
   raise RuntimeError("Saved f14 key animation not cyclic at f1 and f25")
  bpy.ops.object.select_all(action="DESELECT")
  selected={arm,*meshes}
  for o in selected:o.select_set(True)
  bpy.context.view_layer.objects.active=mesh
  glb=out/"R41_FARE_49BONE_SPRINT_CORRECTED_REVIEW_ONLY.glb"
  props=bpy.ops.export_scene.gltf.get_rna_type().properties
  kw=dict(filepath=str(glb),export_format="GLB",use_selection=True)
  candidates={"export_animations":True,"export_skins":True,
              "export_morph":True,"export_frame_range":True,
              "export_frame_step":1,"export_force_sampling":True,
              "export_nla_strips":False,"export_yup":True,
              "export_extras":True,"export_apply":False,
              "export_def_bones":False}
  for k,v in candidates.items():
   if k in props:kw[k]=v
  if "export_animation_mode" in props:
   modes={i.identifier for i in props["export_animation_mode"].enum_items}
   kw["export_animation_mode"]="SCENE" if "SCENE" in modes else "ACTIONS"
  print("ROUND41_EXPORT_OPTIONS",kw)
  bpy.ops.export_scene.gltf(**kw)
  if not glb.exists() or glb.stat().st_size<100000:
   raise RuntimeError("Exporter returned no substantial GLB file")
  obj=load_glb_json(glb)
  names=[a.get("name","") for a in obj.get("animations",[])]
  channels=[x for act in obj.get("animations",[]) for x in act.get("channels",[])]
  targets=[x.get("target",{}).get("path") for x in channels]
  weights=targets.count("weights")
  rotations=targets.count("rotation")
  translations=targets.count("translation")
  if weights<1:raise RuntimeError("GLB lost all animated corrective morph weights")
  if rotations<15:raise RuntimeError("GLB lost most of the animated rig bones")
  names_gltf=[m.get("name") for m in obj.get("meshes",[])]
  targets_names=[mesh.get("extras",{}).get("targetNames",[]) for mesh in obj.get("meshes",[])]
  report.update(exported_glb=glb.name,glb_sha256=hashlib.sha256(glb.read_bytes()).hexdigest(),
      glb_size_bytes=glb.stat().st_size,animation_names=names,
      channels=len(channels),animated_morph_weight_channels=weights,
      animated_rotation_channels=rotations,animated_translation_channels=translations,
      exported_mesh_count=len(obj.get("meshes",[])),exported_node_count=len(obj.get("nodes",[])),
      exported_mesh_names=names_gltf,corrective_names_in_mesh_target_extras=targets_names,
      blender_export_options=kw,original_f14_reference_values=shape_values)
  # Import into an actual separately cleared Blender scene: not a JSON-only
  # validation. Confirms armature, mesh and morph targets survive binary glTF.
  bpy.ops.wm.read_factory_settings(use_empty=True)
  bpy.ops.import_scene.gltf(filepath=str(glb))
  reimport_mesh=[o for o in bpy.data.objects if o.type=="MESH"]
  reimport_arms=[o for o in bpy.data.objects if o.type=="ARMATURE"]
  reimport_shapes=[k.name for ob in reimport_mesh
                   if ob.data.shape_keys
                   for k in ob.data.shape_keys.key_blocks]
  actions=[a.name for a in bpy.data.actions]
  if not reimport_mesh or not reimport_arms:
   raise RuntimeError("Blender glTF reimport lost skin mesh or armature")
  if len(reimport_shapes)<5:
   raise RuntimeError("Blender glTF reimport appears to have lost shape morphs")
  if not actions:
   raise RuntimeError("Blender glTF reimport lost all animation actions")
  report.update(status="PASS_EXPORTED_GLB_AND_REAL_BLENDER_REIMPORT_GODOT_L5_PENDING",
       reimport_mesh_objects=len(reimport_mesh),reimport_armature_objects=len(reimport_arms),
       reimport_shape_key_names=reimport_shapes,
       reimport_action_names=actions,
       caveat="A green GLB/Blender re-import is NOT proof of correct Godot 4 Android runtime animation or human anatomical approval.")
 except Exception as ex:
  report.update(status="FAIL_EXECUTION",error=str(ex),traceback=traceback.format_exc())
 (out/"round41_glb_export_reimport.json").write_text(json.dumps(report,indent=2,ensure_ascii=False))
 print("ROUND41",report["status"],"channels",report.get("channels"),
       "weights",report.get("animated_morph_weight_channels"),
       "size",report.get("glb_size_bytes"))
 if report["status"]!="PASS_EXPORTED_GLB_AND_REAL_BLENDER_REIMPORT_GODOT_L5_PENDING":
  print(report.get("traceback"));raise SystemExit(1)
if __name__=="__main__":main()
