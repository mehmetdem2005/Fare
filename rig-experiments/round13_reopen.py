"""Round 13 independent Blender reopened v8 gate; numerical, not production.
Compare before/after identical skin groups, geometry, original v7 action,
v8 baked action, 24 independent frames, seam 25.
"""
import bpy,sys,math,json,hashlib,struct,statistics,argparse,traceback,runpy
from pathlib import Path
H=runpy.run_path("rig-experiments/round11_rootcause.py",run_name="round11_helpers")
points=H["points"];pose=H["pose"];collect=H["collect"];percentile=H["percentile"];digest=H["digest"]
REGIONS=("interleg","front","central","rear","foreleg","head")
def cli():
 p=argparse.ArgumentParser();p.add_argument("--baseline",required=True);p.add_argument("--candidate",required=True);p.add_argument("--expected",required=True);p.add_argument("--out",required=True)
 return p.parse_args(sys.argv[sys.argv.index("--")+1:])
def objects():
 ob=max((o for o in bpy.data.objects if o.type=="MESH" and any(m.type=="ARMATURE" and m.object for m in o.modifiers)),key=lambda o:len(o.data.vertices))
 arm=next(m.object for m in ob.modifiers if m.type=="ARMATURE" and m.object)
 if len(ob.data.vertices)!=19466 or len(arm.pose.bones)!=49:raise RuntimeError("wrong rig")
 return ob,arm
def signatures(ob,arm):
 h=hashlib.sha256();k=hashlib.sha256()
 for v in ob.data.vertices:
  for c in v.co:h.update(struct.pack("<f",float(c)))
  h.update(struct.pack("<i",len(v.groups)))
  for g in sorted(v.groups,key=lambda x:x.group):
   h.update(struct.pack("<if",g.group,float(g.weight)))
 for ed in ob.data.edges:
  h.update(struct.pack("<ii",*sorted(tuple(ed.vertices))))
 for b in arm.data.bones:
  k.update((b.name+"|"+(b.parent.name if b.parent else "")+";").encode())
 for pb in arm.pose.bones:
  for c in pb.constraints:
   k.update((pb.name+":"+c.name+":"+c.type).encode())
   k.update(struct.pack("<f",float(c.influence)))
 return h.hexdigest(),k.hexdigest()
def metrics(ob,arm,act):
 arm.animation_data_create()
 for t in arm.animation_data.nla_tracks:t.mute=True
 arm.animation_data.action=None
 for pb in arm.pose.bones:pb.matrix_basis.identity()
 bpy.context.scene.frame_set(1)
 ref=points(ob);roi=collect(ob,arm)
 e={n:[] for n in roi}
 for edge in ob.data.edges:
  i,j=tuple(edge.vertices);d=math.dist(ref[i],ref[j])
  if d<.001:continue
  for n,I in roi.items():
   if i in I and j in I:e[n].append((i,j,d))
 rows=[]
 for f in range(1,26):
  pose(arm,act,f)
  pos=points(ob)
  if f==1:initial=pos
  if f==25:seam=max(math.dist(x,y) for x,y in zip(initial,pos))
  if f<=24:rows.append({n:percentile([abs(math.dist(pos[i],pos[j])/d-1) for i,j,d in ed],.95) for n,ed in e.items()})
 score={n:{"mean":statistics.mean(x[n] for x in rows),"worst":max(x[n] for x in rows)} for n in e}
 return score,seam
def main():
 a=cli();out=Path(a.out).resolve();out.mkdir(exist_ok=True,parents=True)
 report={"status":"STARTED","blender":bpy.app.version_string,"input_baseline":digest(Path(a.baseline)),"input_candidate":digest(Path(a.candidate))}
 try:
  expected=json.loads(Path(a.expected).read_text())
  assert expected["status"]=="PASS_NUMERIC_REVIEW_ONLY" and expected.get("candidate")
  bpy.ops.wm.open_mainfile(filepath=str(Path(a.baseline).resolve()))
  ob,arm=objects()
  basehash,baseconstraints=signatures(ob,arm)
  baseline=bpy.data.actions.get("run_sprint_v7_ik_spine_repaired")
  if baseline is None:raise RuntimeError("original action missing baseline")
  basevalues,baseseam=metrics(ob,arm,baseline)
  bpy.ops.wm.open_mainfile(filepath=str(Path(a.candidate).resolve()))
  ob,arm=objects()
  newhash,newconstraints=signatures(ob,arm)
  if basehash!=newhash:raise RuntimeError("Skin weights or rest mesh/topology changed")
  if baseconstraints!=newconstraints:raise RuntimeError("Constraint structure/influences changed")
  orig=bpy.data.actions.get("run_sprint_v7_ik_spine_repaired")
  new=bpy.data.actions.get("run_sprint_v8_ik_phase_NUMERIC_REVIEW")
  if orig is None or new is None:raise RuntimeError("Original or saved new action missing")
  checkold,oldseam=metrics(ob,arm,orig)
  checknew,newseam=metrics(ob,arm,new)
  report.update(vertex_count=19466,bone_count=49,unchanged_skin_hash=basehash,
    unchanged_constraints_hash=baseconstraints,original_action=orig.name,new_action=new.name,
    base_seam=baseseam,save_original_seam=oldseam,new_seam=newseam,
    new_score=checknew,original_score=checkold,
    expected_score=expected["baked_scores"])
  delta=max(abs(checknew[n][k]-expected["baked_scores"][n][k]) for n in REGIONS for k in ("mean","worst"))
  originaldelta=max(abs(checkold[n][k]-basevalues[n][k]) for n in REGIONS for k in ("mean","worst"))
  report.update(max_new_score_abs_delta=delta,max_original_score_abs_delta=originaldelta)
  if delta>3e-5 or originaldelta>3e-5 or max(baseseam,oldseam,newseam)>1e-5:
   raise RuntimeError("Save-reopen numerical score or seam mismatch")
  report["status"]="PASS_L3_REOPEN_NUMERIC_ONLY_NOT_PRODUCTION"
 except Exception as ex:
  report.update(status="FAIL",error=str(ex),traceback=traceback.format_exc())
 (out/"round13_independent_reopen.json").write_text(json.dumps(report,ensure_ascii=False,indent=2))
 print("ROUND13_REOPEN",report["status"],"DELTA",report.get("max_new_score_abs_delta"),"SOURCE",report.get("input_candidate"))
 if report["status"]=="FAIL":
  print(report["error"]);raise SystemExit(1)
if __name__=="__main__":main()
