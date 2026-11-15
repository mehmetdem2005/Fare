"""Round 13 combined IK stance/flight target phase ablations and reviewed-action candidate.
All candidates rebuilt from verified original 49-bone v7, not from each other.
No automatic weights. The generated .blend is EXPERIMENT only and requires
independent reopen + visual review + collision/foot contact before acceptance.
"""
import bpy,sys,argparse,math,json,statistics,hashlib,runpy,traceback
from pathlib import Path
from mathutils import Vector
H=runpy.run_path("rig-experiments/round11_rootcause.py",run_name="round11_helpers")
points=H["points"];collect=H["collect"];pose=H["pose"];percentile=H["percentile"]
render_pose=H["render_pose"];digest=H["digest"]
REGIONS=("interleg","front","central","rear","foreleg","head")
A="run_sprint_v7_ik_spine_repaired"
NEW="run_sprint_v8_ik_phase_NUMERIC_REVIEW"
def cli():
 p=argparse.ArgumentParser();p.add_argument("--source",required=True);p.add_argument("--out",required=True)
 return p.parse_args(sys.argv[sys.argv.index("--")+1:])
def main():
 args=cli();out=Path(args.out).resolve();out.mkdir(exist_ok=True,parents=True)
 rep={"status":"STARTED","blender":bpy.app.version_string,"source_sha256":digest(Path(args.source))}
 try:
  bpy.ops.wm.open_mainfile(filepath=str(Path(args.source).resolve()))
  ob=max((o for o in bpy.data.objects if o.type=="MESH" and any(m.type=="ARMATURE" and m.object for m in o.modifiers)),key=lambda o:len(o.data.vertices))
  arm=next(m.object for m in ob.modifiers if m.type=="ARMATURE" and m.object);B=arm.pose.bones
  action=bpy.data.actions.get(A)
  if action is None or len(B)!=49 or len(ob.data.vertices)!=19466:raise RuntimeError("Expected verified 49 bone v7 action only")
  arm.animation_data_create()
  for t in arm.animation_data.nla_tracks:t.mute=True
  arm.animation_data.action=None
  for pb in B:pb.matrix_basis.identity()
  bpy.context.scene.frame_set(1)
  rest=points(ob);roi=collect(ob,arm)
  E={n:[] for n in roi}
  for e in ob.data.edges:
   i,j=tuple(e.vertices);d=math.dist(rest[i],rest[j])
   if d<.001:continue
   for name,I in roi.items():
    if i in I and j in I:E[name].append((i,j,d))
  def meter(coords):
   return {n:percentile([abs(math.dist(coords[i],coords[j])/d-1) for i,j,d in ee],.95) for n,ee in E.items()}
  def scored(rows):
   return {n:{"worst":max(m[n] for m in rows[:24]),"mean":statistics.mean(m[n] for m in rows[:24])} for n in REGIONS}
  baseline=[]
  for f in range(1,26):
   pose(arm,action,f);coords=points(ob)
   if f==1:first=coords
   if f==25:seam=max(math.dist(x,y) for x,y in zip(first,coords))
   baseline.append(meter(coords))
  if seam>1e-5:raise RuntimeError("Original seam not zero")
  old=scored(baseline);rep["baseline"]=old
  # Each group below is one predeclared controlled target perturbation profile.
  modes=[
    ("front_both_006",{"ik_hand.L":.006,"ik_hand.R":.006}),
    ("hind_both_006",{"ik_foot.L":-.006,"ik_foot.R":-.006}),
    ("front_and_hind_006",{"ik_hand.L":.006,"ik_hand.R":.006,"ik_foot.L":-.006,"ik_foot.R":-.006}),
    ("front_and_hind_004",{"ik_hand.L":.004,"ik_hand.R":.004,"ik_foot.L":-.004,"ik_foot.R":-.004}),
    ("front_L_hind_L_006",{"ik_hand.L":.006,"ik_foot.L":-.006}),
    ("front_R_hind_R_006",{"ik_hand.R":.006,"ik_foot.R":-.006}),
    ("front_006_hind_003",{"ik_hand.L":.006,"ik_hand.R":.006,"ik_foot.L":-.003,"ik_foot.R":-.003}),
    ("front_004_hind_006",{"ik_hand.L":.004,"ik_hand.R":.004,"ik_foot.L":-.006,"ik_foot.R":-.006}),
    ("front_only_L_006",{"ik_hand.L":.006}),
    ("front_only_R_006",{"ik_hand.R":.006}),
  ]
  inverses={n:arm.data.bones[n].matrix_local.to_3x3().inverted() for _,comb in modes for n in comb}
  def pulse(f):
   delta=abs(((f-1)%24))
   delta=min(delta,24-delta)
   return math.exp(-.5*(delta/2.5)**2)
  def apply(comb,f):
   for name,dy in comb.items():
    B[name].location+=inverses[name]@Vector((0,dy*pulse(f),0))
   bpy.context.view_layer.update()
  trials=[]
  for title,comb in modes:
   res=[];seam0=None
   for f in range(1,26):
    pose(arm,action,f);apply(comb,f)
    coords=points(ob)
    if f==1:first=coords
    if f==25:seam0=max(math.dist(x,y) for x,y in zip(first,coords))
    res.append(meter(coords))
   score=scored(res)
   delta={n:{key:score[n][key]-old[n][key] for key in ("mean","worst")} for n in REGIONS}
   valid=(seam0<1e-5 and delta["interleg"]["worst"]<-.04 and
          delta["central"]["worst"]<=.006 and delta["front"]["worst"]<=.006 and
          delta["rear"]["worst"]<=.003 and delta["foreleg"]["worst"]<=.003 and
          delta["head"]["worst"]<=.001)
   trials.append({"name":title,"target_y_offsets":comb,"score":score,
                  "delta":delta,"loop_seam":seam0,"numeric_shortlist":valid})
  rep["trials"]=trials
  candidates=[v for v in trials if v["numeric_shortlist"]]
  selected=min(candidates,key=lambda x:(x["score"]["interleg"]["worst"]+.1*x["score"]["central"]["worst"])) if candidates else None
  rep["selected_profile"]=selected["name"] if selected else None
  if selected:
   comb=selected["target_y_offsets"]
   named=[n for n in B if n.name in ("hips","neck","head") or n.name.startswith(("spine_","tail_","ear","front_toes.","toes.")) or n.name in ("ik_hand.L","ik_hand.R","ik_foot.L","ik_foot.R")]
   keyed=[p.name for p in named]
   data=[]
   for f in range(1,26):
    pose(arm,action,f);apply(comb,f)
    v=points(ob)
    data.append(v)
    data_by_bone={name:(B[name].rotation_euler.copy(),B[name].location.copy()) for name in keyed}
    if f==1:cache={}
    cache[f]=data_by_bone
   new=bpy.data.actions.get(NEW)
   if new:bpy.data.actions.remove(new)
   new=bpy.data.actions.new(NEW);new.use_fake_user=True
   arm.animation_data.action=new
   for f in range(1,26):
    bpy.context.scene.frame_set(f)
    for name in keyed:
     pb=B[name];rot,loc=cache[f][name];pb.rotation_mode="XYZ";pb.rotation_euler=rot;pb.location=loc
     pb.keyframe_insert("rotation_euler",frame=f,group=name)
     pb.keyframe_insert("location",frame=f,group=name)
   # Must independently compare actual Blender baked action vs manually perturbed
   mismatches=[];baked=[]
   for f in range(1,26):
    pose(arm,new,f)
    got=points(ob)
    max_dis=max(math.dist(x,y) for x,y in zip(got,data[f-1]))
    mismatches.append(max_dis)
    baked.append(meter(got))
   maxdiff=max(mismatches)
   rep["baked_manual_max_vertex_distance"]=maxdiff
   rep["baked_scores"]=scored(baked)
   rep["baked_seam"]=max(math.dist(x,y) for x,y in zip(data[0],data[24]))
   if maxdiff>.0001:
    raise RuntimeError("Baked action diverges from manually posed mesh, reject: %.8g"%maxdiff)
   for f in (1,15):
    render_pose(ob,arm,action,f,out/"baseline_views",roi)
    render_pose(ob,arm,new,f,out/"candidate_views",roi)
    render_pose(ob,arm,action,f,out/"baseline_closeup",roi,closeup=True)
    render_pose(ob,arm,new,f,out/"candidate_closeup",roi,closeup=True)
   pose(arm,new,1)
   filename=out/"run_sprint_v8_ik_phase_NUMERIC_REVIEW.blend"
   bpy.ops.wm.save_as_mainfile(filepath=str(filename),compress=True)
   rep["candidate"]={"path":filename.name,"sha256":digest(filename),
                     "state":"EXPERIMENT_ONLY_REOPEN_AND_VISUAL_CHECK_REQUIRED",
                     "source_action":A,"candidate_action":NEW,
                     "modified_groups":0,"geometry_rest_changed":False}
  rep["status"]="PASS_NUMERIC_REVIEW_ONLY"
 except Exception as ex:
  rep.update(status="FAIL",error=str(ex),traceback=traceback.format_exc())
 (out/"round13_combined_ik.json").write_text(json.dumps(rep,indent=2,ensure_ascii=False))
 print("ROUND13_STATUS",rep["status"],"SELECTED",rep.get("selected_profile"),"BAKE_MAX",rep.get("baked_manual_max_vertex_distance"))
 print("ROUND13_SCORES",json.dumps([{"name":v["name"],"interleg":v["score"]["interleg"]["worst"],"front":v["score"]["front"]["worst"],"central":v["score"]["central"]["worst"],"foreleg":v["score"]["foreleg"]["worst"],"shortlisted":v["numeric_shortlist"]} for v in rep.get("trials",[])]))
 if rep["status"]=="FAIL":
  print(rep.get("error"));raise SystemExit(1)
if __name__=="__main__":
 main()
