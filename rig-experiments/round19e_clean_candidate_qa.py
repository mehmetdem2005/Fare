"""Round19E independent clean one-shot Blender 5.1.2 saved/reopened skin weight and L4 rendering.
No production release; validate 49bone/19466verts unchanged geometry, morphs,
constraint topology, exact original action, and ONLY 7 allowed changed vgroups
within part_id=6 torso belt. Full 24 frames and f25 closure, real Workbench.
"""
import bpy,sys,argparse,json,hashlib,math,struct,statistics,traceback,runpy
from pathlib import Path
from mathutils import Vector
ACT="run_sprint_v8_ik_phase_NUMERIC_REVIEW"
ALLOWED={"upper_arm.L","thigh.L","upper_arm.R","thigh.R","spine_05","spine_04","hips"}
def cli():
 p=argparse.ArgumentParser()
 for a in ("--baseline","--candidate","--expected","--out"):p.add_argument(a,required=True)
 return p.parse_args(sys.argv[sys.argv.index("--")+1:])
def model():
 ob=max((x for x in bpy.data.objects if x.type=="MESH" and any(m.type=="ARMATURE" and m.object for m in x.modifiers)),key=lambda x:len(x.data.vertices))
 md=next(m for m in ob.modifiers if m.type=="ARMATURE" and m.object);arm=md.object
 if len(arm.data.bones)!=49 or len(ob.data.vertices)!=19466:raise RuntimeError("Original rig identity lost")
 if md.use_deform_preserve_volume:raise RuntimeError("Preserve Volume toggled in candidate")
 return ob,arm
def invariant(o,arm):
 h=hashlib.sha256()
 for v in o.data.vertices:
  for q in v.co:h.update(struct.pack("<f",float(q)))
 for ed in o.data.edges:h.update(struct.pack("<ii",*tuple(ed.vertices)))
 for p in o.data.polygons:
  h.update(struct.pack("<i",len(p.vertices)))
  for vid in p.vertices:h.update(struct.pack("<i",vid))
 part=o.data.attributes.get("part_id")
 if part:
  for x in part.data:h.update(struct.pack("<i",x.value))
 if o.data.shape_keys:
  for key in o.data.shape_keys.key_blocks:
   h.update(key.name.encode())
   for v in key.data:
    for c in v.co:h.update(struct.pack("<f",float(c)))
  ad=o.data.shape_keys.animation_data
  if ad:
   for curve in ad.drivers:
    h.update((curve.data_path+":"+curve.driver.expression).encode())
 for b in arm.data.bones:
  h.update((b.name+"|"+(b.parent.name if b.parent else "")).encode())
  for row in b.matrix_local:
   for value in row:h.update(struct.pack("<f",float(value)))
  h.update(struct.pack("<i",int(b.use_deform)))
 for pb in arm.pose.bones:
  for c in pb.constraints:
   h.update((pb.name+":"+c.type+":"+c.name+":"+(c.subtarget if hasattr(c,"subtarget") else "")).encode())
   h.update(struct.pack("<f",float(c.influence)))
 return h.hexdigest()
def extract(o):
 result=[]
 for vert in o.data.vertices:
  result.append({o.vertex_groups[g.group].name:float(g.weight) for g in vert.groups if g.weight>1e-9})
 return result
def pts(ob):
 dg=bpy.context.evaluated_depsgraph_get();ev=ob.evaluated_get(dg)
 me=ev.to_mesh(preserve_all_data_layers=False,depsgraph=dg)
 try:
  W=ev.matrix_world.copy();return [Vector(W@v.co) for v in me.vertices]
 finally:ev.to_mesh_clear()
def pose(arm,act,frame):
 arm.animation_data.action=None
 for b in arm.pose.bones:b.matrix_basis.identity()
 bpy.context.scene.frame_set(1)
 arm.animation_data.action=act
 bpy.context.scene.frame_set(2 if frame==1 else frame-1)
 bpy.context.scene.frame_set(frame)
 bpy.context.view_layer.update()
def coorient(ref,base,can,triangles,rot):
 vals={"baseline_reference_inverted":0,"candidate_reference_inverted":0,
       "repaired_reference_inversions":0,"new_reference_inversions":0}
 for a,b,c in triangles:
  rn=(ref[b]-ref[a]).cross(ref[c]-ref[a])
  bn=(base[b]-base[a]).cross(base[c]-base[a])
  cn=(can[b]-can[a]).cross(can[c]-can[a])
  if min(rn.length,bn.length,cn.length)<1e-9:continue
  expected=rot@rn.normalized()
  old_bad=expected.dot(bn.normalized())<0
  new_bad=expected.dot(cn.normalized())<0
  if old_bad:vals["baseline_reference_inverted"]+=1
  if new_bad:vals["candidate_reference_inverted"]+=1
  if old_bad and not new_bad:vals["repaired_reference_inversions"]+=1
  if new_bad and not old_bad:vals["new_reference_inversions"]+=1
 return vals
def main():
 a=cli();out=Path(a.out).resolve();out.mkdir(parents=True,exist_ok=True)
 report={"status":"STARTED","quality_level":"Independent L3 and real images L4 not yet human approved"}
 try:
  expected=json.loads(Path(a.expected).read_text())
  if expected["status"]!="PASS_TRUE_SAVED_WEIGHT_DEFORMATION_REVIEW_ONLY":raise RuntimeError("Only clean one-shot saved candidate permitted")
  root=runpy.run_path("rig-experiments/round17_reopen_surface.py",run_name="round19_reopen_helper")
  draw=runpy.run_path("rig-experiments/round11_rootcause.py",run_name="round19_render_helper")
  bpy.ops.wm.open_mainfile(filepath=str(Path(a.baseline).resolve()))
  ob,arm=model();source_checksum=invariant(ob,arm)
  before=extract(ob)
  b=root["metrics"](ob,arm,disable=True,collect=True)
  b_tris=b["triangles"];b_f15=b["points15"]
  act=bpy.data.actions.get(ACT)
  if not act:raise RuntimeError("Missing old v8 action")
  arm.animation_data_create()
  for tr in arm.animation_data.nla_tracks:tr.mute=True
  for f in (1,15):
   draw["render_pose"](ob,arm,act,f,out/"baseline_views",draw["collect"](ob,arm),closeup=True)
  bpy.ops.wm.open_mainfile(filepath=str(Path(a.candidate).resolve()))
  ob,arm=model();candidate_checksum=invariant(ob,arm)
  if source_checksum!=candidate_checksum:
   raise RuntimeError("Original rest mesh/topology/shape key/bone/constraint hash changed")
  after=extract(ob)
  part=ob.data.attributes["part_id"]
  changed=[]
  suspicious=[]
  max_mass_drift=0.;max_entry_delta=0.
  for i,(w0,w1) in enumerate(zip(before,after)):
   names=set(w0)|set(w1)
   deltas={g:abs(w0.get(g,0.)-w1.get(g,0.)) for g in names}
   biggest=max(deltas.values()) if deltas else 0.
   if biggest<=2e-7:continue
   changed.append(i)
   totaldiff=abs(sum(w0.values())-sum(w1.values()))
   max_mass_drift=max(max_mass_drift,totaldiff)
   max_entry_delta=max(max_entry_delta,biggest)
   v=ob.data.vertices[i]
   anatom=(part.data[i].value==6 and -.1<=v.co.y<=.055 and abs(v.co.x)<=.165 and .045<=v.co.z<=.16)
   same_noneditable=all(d<=2e-6 for name,d in deltas.items() if name not in ALLOWED)
   if not anatom or not same_noneditable or totaldiff>2e-6:
    if len(suspicious)<20:suspicious.append({"id":i,"anatom":anatom,"diff":deltas,"mass_drift":totaldiff})
  # Reconstruction of the exact selected longitudinal-only recipe from the
  # ORIGINAL 49-bone vertex weights. This separates file-save errors from
  # Blender mesh evaluation / target-action or cache errors.
  strength=expected["strength"]
  weight_residuals=[]
  for i in changed:
   ori=before[i];now=after[i];Y=ob.data.vertices[i].co.y
   xx=max(0.,min(1.,(Y-(-.11))/(+.065-(-.11))))
   xx=xx*xx*(3.-2.*xx)
   target=1.-xx
   for side in ("L","R"):
    u="upper_arm."+side;th="thigh."+side
    a0=ori.get(u,0.);b0=ori.get(th,0.);mass=a0+b0
    if a0<=.012 or b0<=.012 or mass<=.08:continue
    exp_u=mass*((1-strength)*(a0/mass)+strength*target)
    exp_th=mass-exp_u
    weight_residuals.append((abs(now.get(u,0.)-exp_u),i,u,a0,now.get(u,0.),exp_u))
    weight_residuals.append((abs(now.get(th,0.)-exp_th),i,th,b0,now.get(th,0.),exp_th))
  weight_residuals.sort(reverse=True)
  report["selected_weight_formula_max_drift"]=weight_residuals[:8]
  print("ROUND19_WEIGHT_FORMULA",weight_residuals[:5])
  if suspicious:raise RuntimeError("Weights changed outside anatomical editable groups/belt: "+str(suspicious[:4]))
  if not 1<=len(changed)<=287:raise RuntimeError("Wrong number of changed vertices "+str(len(changed)))
  if max_entry_delta>.24:raise RuntimeError("Excessively large local weight edit")
  c=root["metrics"](ob,arm,disable=False,collect=True)
  expected_scores=expected["after_reopen_score"]
  worst_drift=max(abs(c["scores"][n][key]-expected_scores[n][key])
                  for n in c["scores"] for key in ("worst","mean"))
  original_drift=max(abs(b["scores"][n][key]-expected["baseline_score"][n][key])
                     for n in b["scores"] for key in ("worst","mean"))
  report["preliminary_score_drift"]={"candidate":worst_drift,"baseline":original_drift,
      "actual_candidate":c["scores"],"expected_candidate":expected_scores,
      "actual_baseline":b["scores"],"expected_baseline":expected["baseline_score"]}
  print("ROUND19E_REOPEN_EARLY_DRIFT",worst_drift,original_drift,
        "candidate belly",c["scores"]["interleg"],"expected",expected_scores["interleg"])
  if worst_drift>4e-5 or original_drift>4e-5:
   raise RuntimeError("Independent evaluated mesh diverged: candidate %.8g baseline %.8g"%(worst_drift,original_drift))
  area_drift=max(abs(c["area15"][key]-expected["after_reopen_area"][key])
                 for key in ("under_half","p05","min"))
  if area_drift>4e-5 or max(c["seam"],b["seam"])>1e-5:
   raise RuntimeError("Area score / animation seam mismatch after reopening")
  act=bpy.data.actions.get(ACT)
  pose(arm,act,15)
  # Earlier independent source had torso transform but reset to its f15 state:
  world_motion=arm.matrix_world@arm.pose.bones["spine_03"].matrix@arm.data.bones["spine_03"].matrix_local.inverted()@arm.matrix_world.inverted()
  torso_quat=world_motion.to_quaternion()
  arm.animation_data.action=None
  for pb in arm.pose.bones:pb.matrix_basis.identity()
  bpy.context.scene.frame_set(1);rest=pts(ob)
  signed=coorient(rest,b_f15,c["points15"],b_tris,torso_quat)
  geom=root["normals_overlap"](b_tris,b_f15,c["points15"])
  screen=expected["orientation"]
  if (signed["new_reference_inversions"]!=screen["new"] or
      signed["repaired_reference_inversions"]!=screen["repaired"]):
    raise RuntimeError("signed reference orientation not reproducible")
  if geom["candidate_nonadjacent_overlaps"]!=expected["geom"]["candidate_nonadjacent_overlaps"]:
   raise RuntimeError("BVH overlap count changed on independent reopen")
  # Actually create before/after render images. No L4 acceptance asserted.
  for f in (1,15):
   draw["render_pose"](ob,arm,act,f,out/"candidate_views",draw["collect"](ob,arm),closeup=True)
  report.update(rest_and_constraints_sha256=source_checksum,source_unchanged=True,
       changes={"modified_vertices":len(changed),"max_weight_change":max_entry_delta,
           "max_weight_sum_drift":max_mass_drift,"ids_first":changed[:40]},
       source=b["scores"],candidate=c["scores"],source_area15=b["area15"],candidate_area15=c["area15"],
       candidate_score_readback_drift=worst_drift,source_score_readback_drift=original_drift,
       area_readback_drift=area_drift,source_seam=b["seam"],candidate_seam=c["seam"],
       corotated_rest_orientation=signed,normal_and_BVH=geom,
       note="Minimum local triangle area may worsen despite overall p05 improvement; no anatomical L4 pass")
  report["status"]="PASS_L3_INDEPENDENT_REOPEN_RENDERED_L4_REVIEW_PENDING"
 except Exception as ex:
  report.update(status="FAIL",error=str(ex),traceback=traceback.format_exc())
 (out/"round19e_clean_independent_qa.json").write_text(json.dumps(report,indent=2,ensure_ascii=False))
 print("ROUND19E_REOPEN",report["status"],"CHANGES",report.get("changes"),
     "NORMALS",report.get("corotated_rest_orientation"),"OVERLAP",report.get("normal_and_BVH",{}).get("candidate_nonadjacent_overlaps"))
 if report["status"]=="FAIL":
  print(report["error"]);raise SystemExit(1)
if __name__=="__main__":main()
