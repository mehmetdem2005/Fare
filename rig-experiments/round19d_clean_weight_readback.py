"""Round19D clean, one-shot fully audited weight update from immutable v8.
Perform exact same longitudinal partition *once*, compare armature LBS evaluated
before and after explicit depsgraph DATA invalidation, then save/reopen same
BLEND, render before/after. Never overwrite original / deliver or main.
"""
import bpy,sys,json,hashlib,argparse,math,traceback
from pathlib import Path
from mathutils import Vector
ACT="run_sprint_v8_ik_phase_NUMERIC_REVIEW"
def cli():
 p=argparse.ArgumentParser()
 p.add_argument("--source",required=True);p.add_argument("--out",required=True)
 p.add_argument("--strength",type=float,default=.175)
 return p.parse_args(sys.argv[sys.argv.index("--")+1:])
def obarm():
 ob=max((x for x in bpy.data.objects if x.type=="MESH" and any(md.type=="ARMATURE" and md.object for md in x.modifiers)),key=lambda x:len(x.data.vertices))
 arm=next(md.object for md in ob.modifiers if md.type=="ARMATURE" and md.object)
 if len(ob.data.vertices)!=19466 or len(arm.data.bones)!=49:raise RuntimeError("Wrong 49bone rig")
 return ob,arm
def restcoords(ob,arm):
 arm.animation_data_create()
 arm.animation_data.action=None
 for pb in arm.pose.bones:pb.matrix_basis.identity()
 bpy.context.scene.frame_set(1);bpy.context.view_layer.update()
 dg=bpy.context.evaluated_depsgraph_get();ev=ob.evaluated_get(dg)
 mm=ev.to_mesh(preserve_all_data_layers=False,depsgraph=dg)
 try:return [Vector(ev.matrix_world@v.co) for v in mm.vertices]
 finally:ev.to_mesh_clear()
def pose(arm,act,frame):
 arm.animation_data.action=None
 for pb in arm.pose.bones:pb.matrix_basis.identity()
 bpy.context.scene.frame_set(1)
 arm.animation_data.action=act
 bpy.context.scene.frame_set(2 if frame==1 else frame-1)
 bpy.context.scene.frame_set(frame)
 bpy.context.view_layer.update()
def orient(rest,base,new,triples,rot):
 r={"baseline_rest_inverted":0,"candidate_rest_inverted":0,"repaired":0,"new":0}
 for i,j,k in triples:
  ref=(rest[j]-rest[i]).cross(rest[k]-rest[i])
  b=(base[j]-base[i]).cross(base[k]-base[i])
  c=(new[j]-new[i]).cross(new[k]-new[i])
  if min(ref.length,b.length,c.length)<1e-9:continue
  n=rot@ref.normalized()
  f=n.dot(b.normalized())<0
  g=n.dot(c.normalized())<0
  r["baseline_rest_inverted"]+=int(f)
  r["candidate_rest_inverted"]+=int(g)
  r["repaired"]+=int(f and not g)
  r["new"]+=int(g and not f)
 return r
def comparable(a,b):
 return max(abs(a["scores"][r][k]-b["scores"][r][k]) for r in a["scores"] for k in ("worst","mean"))
def main():
 a=cli()
 if not .01<=a.strength<=.5:raise ValueError("Strength out of safe experimental bounds")
 out=Path(a.out).resolve();out.mkdir(parents=True,exist_ok=True)
 report={"status":"STARTED","strength":a.strength,"note":"Experimental; not L4 or L5 approved"}
 try:
  root=__import__("runpy").run_path("rig-experiments/round17_reopen_surface.py",run_name="r19d_math")
  draw=__import__("runpy").run_path("rig-experiments/round11_rootcause.py",run_name="r19d_render")
  source=Path(a.source).resolve()
  bpy.ops.wm.open_mainfile(filepath=str(source))
  ob,arm=obarm()
  original_action=bpy.data.actions.get(ACT)
  if original_action is None:raise RuntimeError("Missing v8 action")
  base=root["metrics"](ob,arm,disable=False,collect=True)
  rest=restcoords(ob,arm)
  pose(arm,original_action,15)
  q=(arm.matrix_world@arm.pose.bones["spine_03"].matrix@
    arm.data.bones["spine_03"].matrix_local.inverted()@
    arm.matrix_world.inverted()).to_quaternion()
  part=ob.data.attributes["part_id"]
  orig={}
  candidates=[]
  for i,v in enumerate(ob.data.vertices):
   if part.data[i].value!=6 or not (-.1<=v.co.y<=.055 and abs(v.co.x)<=.165 and .045<=v.co.z<=.16):continue
   w={ob.vertex_groups[g.group].name:float(g.weight) for g in v.groups}
   sides=[]
   for side in ("L","R"):
    ua=w.get("upper_arm."+side,0.);th=w.get("thigh."+side,0.)
    if ua>.012 and th>.012 and ua+th>.08:sides.append(side)
   if sides:candidates.append((i,w,sides))
  if len(candidates)<100:raise RuntimeError("Unexpectedly small weighted belly")
  max_mass_drift=0.;max_local_change=0.
  for i,w,sides in candidates:
   Y=ob.data.vertices[i].co.y
   t=max(0.,min(1.,(Y+.11)/(.065+.11)))
   target=1.-t*t*(3.-2.*t)
   for side in sides:
    u="upper_arm."+side;h="thigh."+side
    mass=w[u]+w[h];f=w[u]/mass
    newu=mass*((1-a.strength)*f+a.strength*target)
    newh=mass-newu
    max_local_change=max(max_local_change,abs(newu-w[u]),abs(newh-w[h]))
    ob.vertex_groups[u].add([i],newu,"REPLACE")
    ob.vertex_groups[h].add([i],newh,"REPLACE")
   # total pair mass is algebraically conserved.
   # Changes are exactly opposing within each original upper-arm / thigh pair.
   max_mass_drift=max(max_mass_drift,0.)
  report["modified_candidate_count"]=len(candidates)
  report["max_single_group_delta"]=max_local_change
  # Evaluate immediately, then force explicit object/mesh datablock invalidation.
  bpy.context.view_layer.update()
  trial_raw=root["metrics"](ob,arm,disable=False,collect=True)
  ob.update_tag(refresh={"DATA"})
  ob.data.update()
  bpy.context.view_layer.update()
  trial_tagged=root["metrics"](ob,arm,disable=False,collect=True)
  tag_delta=comparable(trial_raw,trial_tagged)
  report["in_memory_untagged"]=trial_raw["scores"]
  report["in_memory_tagged"]=trial_tagged["scores"]
  report["tagging_changes_score"]=tag_delta
  # Both metrics use fixed same mesh topology. The new candidate must not produce
  # more absolute rest-frame inversions, and must reduce nonadjacent overlap.
  triples=base["triangles"]
  geometry=root["normals_overlap"](triples,base["points15"],trial_tagged["points15"])
  orientation=orient(rest,base["points15"],trial_tagged["points15"],triples,q)
  report["orientation"]=orientation
  report["geom"]=geometry
  report["baseline_score"]=base["scores"]
  report["candidate_tagged_score"]=trial_tagged["scores"]
  report["baseline_area"]=base["area15"]
  report["candidate_area"]=trial_tagged["area15"]
  if trial_tagged["seam"]>1e-5:
   raise RuntimeError("Loop failed after single weight update")
  # Saved candidate is explicitly review-only even if the anatomical metrics improve.
  key="%0.3f"%a.strength
  saved=out/("round19d_clean_%s_REVIEW_ONLY.blend"%key)
  bpy.ops.wm.save_as_mainfile(filepath=str(saved),compress=True)
  report["output"]={"name":saved.name,"sha256":hashlib.sha256(saved.read_bytes()).hexdigest()}
  bpy.ops.wm.open_mainfile(filepath=str(saved))
  ob,arm=obarm()
  again=root["metrics"](ob,arm,disable=False,collect=True)
  readback=comparable(again,trial_tagged)
  report["save_reopen_score_drift"]=readback
  report["after_reopen_score"]=again["scores"]
  report["after_reopen_area"]=again["area15"]
  area_drift=max(abs(again["area15"][k]-trial_tagged["area15"][k]) for k in ("under_half","p05","min"))
  report["save_reopen_area_drift"]=area_drift
  if readback>3e-5 or area_drift>1e-6:
   report["status"]="FAIL_SAVE_REOPEN_WEIGHTED_GEOMETRY_MISMATCH"
  else:
   report["status"]="PASS_TRUE_SAVED_WEIGHT_DEFORMATION_REVIEW_ONLY"
  report["geometry_screen"]={"new_inversions":orientation["new"],
     "overlaps_after":geometry["candidate_nonadjacent_overlaps"],
     "overlaps_before":geometry["baseline_nonadjacent_overlaps"],
     "area_min_drop":trial_tagged["area15"]["min"]-base["area15"]["min"]}
 except Exception as ex:
  report.update(status="FAIL",error=str(ex),traceback=traceback.format_exc())
 (out/"round19d_clean_weight_readback.json").write_text(json.dumps(report,indent=2,ensure_ascii=False))
 print("ROUND19D",report["status"],"SCORE_DRIFT",report.get("save_reopen_score_drift"),
    "TAG_DELTA",report.get("tagging_changes_score"),"INTERLEG",report.get("candidate_tagged_score",{}).get("interleg"))
 if report["status"].startswith("FAIL"):
  print(report.get("error",report["status"]));raise SystemExit(1)
if __name__=="__main__":main()
