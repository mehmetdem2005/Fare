"""Single-bone certified positional sweep and IK stretch ablation.
Target: 49-bone GitHub Fare rig, existing experimental run_sprint_v4+flank.65.
Read-only bpy evaluated mesh, 2 hard phases + full 24-frame IK stretch tests.
Each scenario restores full original action, constraints, driver & pose state.
"""
import bpy, sys, argparse, math, json, traceback, hashlib
from mathutils import Vector
from pathlib import Path
R=math.radians
def args():
 p=argparse.ArgumentParser();p.add_argument("--source",required=True);p.add_argument("--out",required=True);return p.parse_args(sys.argv[sys.argv.index("--")+1:])
def q(vals,f):
 if not vals:return 0.
 vals.sort();return vals[int((len(vals)-1)*f)]
def pt(mesh):
 dg=bpy.context.evaluated_depsgraph_get()
 ev=mesh.evaluated_get(dg)
 me=ev.to_mesh(preserve_all_data_layers=False,depsgraph=dg)
 try:
  w=ev.matrix_world.copy();return [tuple(w@v.co) for v in me.vertices]
 finally:ev.to_mesh_clear()
def main():
 a=args();out=Path(a.out).resolve();out.mkdir(exist_ok=True,parents=True)
 report={"source":a.source,"status":"STARTED","blender":bpy.app.version_string}
 try:
  bpy.ops.wm.open_mainfile(filepath=str(Path(a.source).resolve()))
  me=max([ob for ob in bpy.data.objects if ob.type=="MESH" and any(m.type=="ARMATURE" and m.object for m in ob.modifiers)],key=lambda ob:len(ob.data.vertices))
  arm=next(m.object for m in me.modifiers if m.type=="ARMATURE" and m.object);B=arm.pose.bones;sc=bpy.context.scene
  action=bpy.data.actions.get("run_sprint_v4")
  if not action:raise RuntimeError("run_sprint_v4 action missing")
  arm.animation_data_create()
  arm.animation_data.action=None
  for track in arm.animation_data.nla_tracks:track.mute=True
  bones=['hips','spine_01','spine_02','spine_03','spine_04','spine_05','neck',
         'shoulder.L','upper_arm.L','forearm.L','hand.L','thigh.L','shin.L',
         'shoulder.R','upper_arm.R','forearm.R','hand.R','thigh.R','shin.R']
  bones=[x for x in bones if x in B]
  ik={"fore_L":"forearm.L","fore_R":"forearm.R","hind_L":"shin.L","hind_R":"shin.R"}
  ik_con={n:next((c for c in B[bone].constraints if c.type=="IK"),None) for n,bone in ik.items()}
  if not all(ik_con.values()):raise RuntimeError("IK constraint missing")
  initial_c={(b.name,c.name):(c.influence,c.use_stretch) for b in B for c in b.constraints if c.type=="IK"}
  part=me.data.attributes.get("part_id")
  V=me.data.vertices
  if not part:raise RuntimeError("No part_id")
  ids={
   "front":set(i for i,v in enumerate(V) if part.data[i].value==6 and -.27<=v.co.y<=.055 and abs(v.co.x)<.17 and .045<=v.co.z<=.285),
   "interleg":set(i for i,v in enumerate(V) if part.data[i].value==6 and -.1<=v.co.y<=.055 and abs(v.co.x)<.165 and .045<=v.co.z<=.16),
   "central":set(i for i,v in enumerate(V) if part.data[i].value==6 and -.27<=v.co.y<=.055 and abs(v.co.x)<.06 and .045<=v.co.z<=.285),
   "rear":set(i for i,v in enumerate(V) if part.data[i].value==6 and .055<=v.co.y<=.33 and abs(v.co.x)<.17 and .06<=v.co.z<=.3),
   "front_leg":set(i for i,v in enumerate(V) if v.co.y<-.18 and v.co.z<.15 and abs(v.co.x)>.09),
  }
  for pb in B:pb.matrix_basis.identity()
  sc.frame_set(1)
  rest=pt(me)
  EE={}
  for name,I in ids.items():
   pairs=[tuple(e.vertices) for e in me.data.edges if e.vertices[0] in I and e.vertices[1] in I]
   EE[name]=[(u,v,math.dist(rest[u],rest[v])) for u,v in pairs if math.dist(rest[u],rest[v])>=.001]
  report["roi"]={n:{"vertices":len(ids[n]),"edges":len(EE[n])} for n in ids}
  def metric(coords):
   return {n:q([abs(math.dist(coords[u],coords[v])/d-1) for u,v,d in E],.95) for n,E in EE.items()}
  def normalize():
   for pb in B:
    for c in pb.constraints:
     k=(pb.name,c.name)
     if k in initial_c:c.influence,c.use_stretch=initial_c[k]
   arm.animation_data.action=action
  def pose(f):
   normalize()
   sc.frame_set(f+1 if f==1 else f-1);sc.frame_set(f)
   bpy.context.view_layer.update()
  # IK stretching and raw bone length throughout source cycle
  reference=[]
  for f in range(1,25):
   pose(f);cp=pt(me)
   ikstats={}
   for name,bname in ik.items():
    bone=B[bname];parent=B["upper_arm."+name[-1]] if name.startswith("fore") else B["thigh."+name[-1]]
    target=B["ik_hand."+name[-1]] if name.startswith("fore") else B["ik_foot."+name[-1]]
    lim=arm.data.bones[bname].length+arm.data.bones[parent.name].length
    rdist=(target.head-parent.head).length
    ikstats[name]={"reach_ratio":rdist/lim,
                   "parent_len_ratio":(parent.tail-parent.head).length/arm.data.bones[parent.name].length,
                   "child_len_ratio":(bone.tail-bone.head).length/arm.data.bones[bname].length,
                   "reach_error":(bone.tail-target.head).length}
   reference.append({"frame":f,"metrics":metric(cp),"ik":ikstats})
  report["reference"]=reference
  # For each IK independently disable use_stretch, run entire cycle, compare all ROIs.
  tests={}
  for case,bones_to_disable in [
      ("none",[]),("front_L_only",["fore_L"]),("front_R_only",["fore_R"]),
      ("hind_L_only",["hind_L"]),("hind_R_only",["hind_R"]),
      ("front_both",["fore_L","fore_R"]),("hind_both",["hind_L","hind_R"]),
      ("all_four",list(ik.keys()))]:
   res=[]
   for f in range(1,25):
    pose(f)
    for n in bones_to_disable:ik_con[n].use_stretch=False
    bpy.context.view_layer.update()
    cp=pt(me)
    reach={}
    for name,bname in ik.items():
     target=B["ik_hand."+name[-1]] if name.startswith("fore") else B["ik_foot."+name[-1]]
     reach[name]=(B[bname].tail-target.head).length
    res.append({"frame":f,"p95":metric(cp),"reach_error":reach})
   tests[case]={"frames":res,"mean_p95":{n:sum(x["p95"][n] for x in res)/24 for n in ids},
                "worst_p95":{n:max(x["p95"][n] for x in res) for n in ids},
                "max_target_error":{n:max(x["reach_error"][n] for x in res) for n in ik}}
  report["ik_stretch_ablation"]=tests
  for f in range(24):
   for roi in ids:
    if abs(tests["none"]["frames"][f]["p95"][roi]-reference[f]["metrics"][roi])>1e-5:
     raise RuntimeError("independent full-pose mismatch: %d %s"%(f+1,roi))
  # Bone-by-bone rotation audit: IK remains ON; only one bone axis/angle changes.
  # Verify realized angle after constraints; disclose bone override if IK swallows it.
  directions=[("x",R(12)),("x",-R(12)),("x",R(25)),("x",-R(25)),
              ("z",R(12)),("z",-R(12))]
  sweep=[]
  for frame in (3,15):
   pose(frame);base=pt(me);basep=metric(base)
   for n in bones:
    for axis,ang in directions:
     pose(frame);pb=B[n]
     old=pb.matrix.copy()
     pb.rotation_mode="XYZ"
     rot=list(pb.rotation_euler);rot[{"x":0,"y":1,"z":2}[axis]]+=ang;pb.rotation_euler=rot
     bpy.context.view_layer.update()
     cp=pt(me)
     realized=(old.to_quaternion().rotation_difference(pb.matrix.to_quaternion()).angle)
     m=metric(cp)
     changed=[math.dist(base[i],cp[i]) for i in ids["interleg"]]
     sweep.append({"frame":frame,"bone":n,"axis":axis,"angle_deg":round(math.degrees(ang),3),
                   "evaluated_angle_deg":round(math.degrees(realized),5),
                   "belly_mean_displacement":sum(changed)/len(changed),
                   "metrics":m,"delta_p95":{r:m[r]-basep[r] for r in ids}})
  report["per_bone_pose_sweep"]=sweep
  report["status"]="PASS"
 except Exception as ex:
  report["status"]="FAIL";report["error"]=str(ex);report["traceback"]=traceback.format_exc()
 (out/"individual_bone_ik_sweep.json").write_text(json.dumps(report,indent=2))
 print("INDIVIDUAL_BONE_STATUS",report["status"])
 if report["status"]=="PASS":
  print("IK_NOSTRETCH",json.dumps({k:v["mean_p95"] for k,v in report["ik_stretch_ablation"].items()}))
  print("BONE_SWEEP_SAMPLES",len(report["per_bone_pose_sweep"]))
 else:print(report.get("error"))
 if report["status"]!="PASS":raise SystemExit(1)
if __name__=="__main__":main()
