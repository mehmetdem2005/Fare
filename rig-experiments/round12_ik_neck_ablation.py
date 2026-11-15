"""Round 12: individual IK target causal ablations and neck-spine skin trial.
Investigative only, no automatic weights, no writes to production model.
Rebuild verified 49-bone v7 before running.
"""
import argparse,bpy,math,sys,json,statistics,runpy,traceback
from pathlib import Path
from mathutils import Vector
H=runpy.run_path("rig-experiments/round11_rootcause.py",run_name="round11_helpers")
points=H["points"];pose=H["pose"];collect=H["collect"]; original_weight=H["original_weight"]
percentile=H["percentile"]; digest=H["digest"]
R=math.radians
REGIONS=("interleg","front","central","rear","foreleg","head")
def cli():
 p=argparse.ArgumentParser();p.add_argument("--source",required=True);p.add_argument("--out",required=True)
 return p.parse_args(sys.argv[sys.argv.index("--")+1:])
def main():
 a=cli();out=Path(a.out).resolve();out.mkdir(exist_ok=True,parents=True)
 report={"status":"STARTED","source_sha256":digest(Path(a.source)), "blender":bpy.app.version_string}
 try:
  bpy.ops.wm.open_mainfile(filepath=str(Path(a.source).resolve()))
  ob=max((o for o in bpy.data.objects if o.type=="MESH" and any(m.type=="ARMATURE" and m.object for m in o.modifiers)),key=lambda o:len(o.data.vertices))
  arm=next(m.object for m in ob.modifiers if m.type=="ARMATURE" and m.object); B=arm.pose.bones
  if len(B)!=49 or len(ob.data.vertices)!=19466:raise RuntimeError("Wrong model")
  action=bpy.data.actions.get("run_sprint_v7_ik_spine_repaired")
  if action is None:raise RuntimeError("Verified v7 source missing")
  arm.animation_data_create()
  for t in arm.animation_data.nla_tracks:t.mute=True
  arm.animation_data.action=None
  for pb in B:pb.matrix_basis.identity()
  bpy.context.scene.frame_set(1)
  rest=points(ob)
  roi=collect(ob,arm)
  edges={}
  for name,ids in roi.items():
   ee=[]
   for e in ob.data.edges:
    i,j=tuple(e.vertices)
    if i not in ids or j not in ids:continue
    d=math.dist(rest[i],rest[j])
    if d>=.001:ee.append((i,j,d))
   edges[name]=ee
  def calc(co):
   result={}
   for name,ee in edges.items():
    ratios=[math.dist(co[i],co[j])/d for i,j,d in ee]
    result[name]={"p95":percentile([abs(v-1) for v in ratios],.95),
                  "p99":percentile([abs(v-1) for v in ratios],.99),
                  "ext95":percentile([max(0.,v-1) for v in ratios],.95),
                  "cmp95":percentile([max(0.,1-v) for v in ratios],.95),
                  "max":max(abs(v-1) for v in ratios)}
   return result
  baseline=[]
  for f in range(1,26):
   pose(arm,action,f);co=points(ob)
   if f==1:first=co
   if f==25:seam=max(math.dist(u,v) for u,v in zip(first,co))
   else:baseline.append(calc(co))
  if seam>1e-4:raise RuntimeError("Baseline seam")
  summary={r:{"mean":statistics.mean(x[r]["p95"] for x in baseline),
              "worst":max(x[r]["p95"] for x in baseline)} for r in REGIONS}
  report["baseline"]=summary;report["loop_seam"]=seam
  frames=(1,15)
  ctrls=("ik_hand.L","ik_hand.R","ik_foot.L","ik_foot.R")
  # The local Euler of IK-driven upper arms is not a valid independent actuator.
  # Perturb each true hand/foot IK target in armature coordinate system.
  single=[]
  for f in frames:
   pose(arm,action,f);base=calc(points(ob))
   for name in ctrls:
    for axis in "XYZ":
     for direction in (-.006,-.003,.003,.006):
      pose(arm,action,f)
      pb=B[name]
      before=pb.head.copy()
      delta=Vector(tuple(direction if axis=="XYZ"[i] else 0 for i in range(3)))
      restinv=arm.data.bones[name].matrix_local.to_3x3().inverted()
      pb.location += restinv@delta
      bpy.context.view_layer.update()
      actual=(pb.head-before).length
      metric=calc(points(ob))
      single.append({"frame":f,"ik_target":name,"axis":axis,"shift_requested":direction,
                     "evaluated_target_distance":actual,
                     "delta_p95":{r:metric[r]["p95"]-base[r]["p95"] for r in REGIONS},
                     "delta_p99":{r:metric[r]["p99"]-base[r]["p99"] for r in REGIONS}})
     pose(arm,action,f)
     check=calc(points(ob))
     if max(abs(check[r]["p95"]-base[r]["p95"]) for r in REGIONS)>1e-6:
      raise RuntimeError("IK state leak at "+name)
  report["single_ik_tests"]=single;report["ik_tests_count"]=len(single)
  # Quantify how much dynamic IK changes could help the whole loop.
  # Not baked as an action, no production claim from numerical sweeps.
  ranks=sorted(single,key=lambda x:x["delta_p95"]["interleg"]+
               .8*max(0,x["delta_p95"]["front"])+max(0,x["delta_p95"]["central"])+
               1.5*max(0,x["delta_p95"]["foreleg"]))
  report["top_single_ik_ablation"]=ranks[:18]
  profiles=[]
  for row in ranks:
   if row["delta_p95"]["interleg"]>=-.025:continue
   if row["delta_p95"]["foreleg"]>.01 or row["delta_p95"]["rear"]>.007:continue
   if all(not(q["frame"]==row["frame"] and q["ik_target"]==row["ik_target"] and
                  q["axis"]==row["axis"]) for q in profiles):
    profiles.append(row)
   if len(profiles)>=8:break
  def pulse(frame,center):
   d=abs(frame-center);d=min(d,24-d)
   return math.exp(-.5*(d/2.5)**2)
  evaluated_profiles=[]
  for p in profiles:
   name=p["ik_target"];axis=p["axis"];center=p["frame"];mag=p["shift_requested"]
   restinv=arm.data.bones[name].matrix_local.to_3x3().inverted()
   delta=Vector(tuple(mag if axis=="XYZ"[i] else 0 for i in range(3)))
   rr=[]
   for f in range(1,25):
    pose(arm,action,f)
    B[name].location += restinv@(delta*pulse(f,center))
    bpy.context.view_layer.update()
    rr.append(calc(points(ob)))
   score={r:{"mean":statistics.mean(x[r]["p95"] for x in rr),
             "worst":max(x[r]["p95"] for x in rr)} for r in REGIONS}
   evaluated_profiles.append({"source":p,"score":score,
                               "delta":{r:{"mean":score[r]["mean"]-summary[r]["mean"],
                                           "worst":score[r]["worst"]-summary[r]["worst"]} for r in REGIONS}})
  report["full_cycle_ik_profile_trials"]=evaluated_profiles
  report["full_cycle_ik_profile_count"]=len(evaluated_profiles)
  # Spine/neck influence on ventral part_id=6 is individually testable.
  # Transfer only neck -> spine_05 in high-strain top 2% connected hotspot,
  # preserving total weight on every affected body vertex.
  pose(arm,action,1);now=points(ob)
  scores=sorted([(abs(math.dist(now[i],now[j])/d-1),i,j) for i,j,d in edges["interleg"]],reverse=True)
  hot=set()
  for _,i,j in scores[:max(1,int(.02*len(scores)))]:
   hot.update((i,j))
  nb={i:set() for i in range(len(ob.data.vertices))}
  for e in ob.data.edges:
   i,j=e.vertices;nb[i].add(j);nb[j].add(i)
  hot |= {j for i in list(hot) for j in nb[i] if j in roi["interleg"]}
  old={i:original_weight(ob,i) for i in hot}
  report["hotspot_rest_position_weight"]=[
   {"id":i,"position":list(ob.data.vertices[i].co),"weights":old[i]}
   for i in sorted(hot) if old[i].get("neck",0)>.1][:120]
  g0=ob.vertex_groups.get("neck");g1=ob.vertex_groups.get("spine_05")
  if not(g0 and g1):raise RuntimeError("Expected neck/spine_05 deform groups")
  trials=[]
  for strength in (.25,.50,.75,1.0):
   changed={}
   for i in hot:
    orig=old[i];w=orig.get("neck",0)
    if w<.05:continue
    current=orig.get("spine_05",0)
    take=w*strength
    g0.add([i],w-take,"REPLACE")
    g1.add([i],current+take,"REPLACE")
    changed[i]={"old_neck":w,"old_spine_05":current,"new_neck":w-take,
                "new_spine_05":current+take}
   rows=[]
   for f in range(1,25):
    pose(arm,action,f);rows.append(calc(points(ob)))
   score={r:{"mean":statistics.mean(x[r]["p95"] for x in rows),
              "worst":max(x[r]["p95"] for x in rows)} for r in REGIONS}
   trial={"strength":strength,"changed_vertices":len(changed),"changes":changed,
          "score":score,"delta":{r:{"mean":score[r]["mean"]-summary[r]["mean"],
                                   "worst":score[r]["worst"]-summary[r]["worst"]} for r in REGIONS}}
   trials.append(trial)
   for i in changed:
    g0.add([i],old[i]["neck"],"REPLACE")
    if old[i].get("spine_05",0)>0:g1.add([i],old[i]["spine_05"],"REPLACE")
    else:g1.remove([i])
   pose(arm,action,1)
   vv=calc(points(ob))
   if max(abs(vv[r]["p95"]-baseline[0][r]["p95"]) for r in REGIONS)>1e-6:
    raise RuntimeError("Skinning reset leak")
  report["neck_to_spine_trials"]=trials
  report["status"]="PASS_CAUSAL_EXPERIMENTS_NOT_A_REPAIR"
 except Exception as ex:
  report.update(status="FAIL",error=str(ex),traceback=traceback.format_exc())
 (out/"round12_ik_neck_ablation.json").write_text(json.dumps(report,indent=2,ensure_ascii=False))
 print("ROUND12_STATUS",report["status"],"IK_TESTS",report.get("ik_tests_count"),"IK_PROFILES",report.get("full_cycle_ik_profile_count"))
 if report["status"]!="FAIL":
  print("ROUND12_IK_TOP",json.dumps(report["top_single_ik_ablation"][:4]))
  print("ROUND12_NECK",json.dumps([{"strength":x["strength"],"changed":x["changed_vertices"],"delta":{k:v["worst"] for k,v in x["delta"].items()}} for x in report["neck_to_spine_trials"]]))
 else:
  print(report.get("error"));raise SystemExit(1)
if __name__=="__main__":main()
