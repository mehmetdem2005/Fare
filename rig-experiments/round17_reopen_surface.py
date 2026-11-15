"""Round 17 independent Blender reopened geometry, signed surface normal and
non-adjacent triangle self-overlap checks. L3 morph scores not production L5.
"""
import bpy,sys,json,math,struct,hashlib,argparse,traceback,statistics
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
NAME="R17_AREA_0.85_0.006"
ACT="run_sprint_v8_ik_phase_NUMERIC_REVIEW"
def cli():
 p=argparse.ArgumentParser()
 for arg in ("--source","--candidate","--expected","--out"):p.add_argument(arg,required=True)
 return p.parse_args(sys.argv[sys.argv.index("--")+1:])
def model():
 o=max((m for m in bpy.data.objects if m.type=="MESH" and any(x.type=="ARMATURE" and x.object for x in m.modifiers)),key=lambda x:len(x.data.vertices))
 arm=next(x.object for x in o.modifiers if x.type=="ARMATURE" and x.object)
 if len(o.data.vertices)!=19466 or len(arm.data.bones)!=49:raise RuntimeError("wrong model")
 return o,arm
def pts(o):
 dg=bpy.context.evaluated_depsgraph_get();ev=o.evaluated_get(dg)
 mesh=ev.to_mesh(preserve_all_data_layers=False,depsgraph=dg)
 try:
  mat=ev.matrix_world.copy();return [Vector(mat@v.co) for v in mesh.vertices]
 finally:ev.to_mesh_clear()
def pose(arm,act,f):
 arm.animation_data.action=None
 for b in arm.pose.bones:b.matrix_basis.identity()
 bpy.context.scene.frame_set(1)
 arm.animation_data.action=act
 bpy.context.scene.frame_set(f-1 if f>1 else 2)
 bpy.context.scene.frame_set(f);bpy.context.view_layer.update()
def sig(o,arm):
 h=hashlib.sha256()
 deform={b.name for b in arm.data.bones if b.use_deform}
 for v in o.data.vertices:
  for c in v.co:h.update(struct.pack("<f",float(c)))
  groups=sorted((o.vertex_groups[g.group].name,g.weight) for g in v.groups if o.vertex_groups[g.group].name in deform)
  for name,w in groups:
   h.update(name.encode());h.update(struct.pack("<f",float(w)))
  h.update(b"\x00")
 for ed in o.data.edges:h.update(struct.pack("<ii",*tuple(ed.vertices)))
 if o.data.shape_keys:
  for key in o.data.shape_keys.key_blocks:
   if key.name==NAME:continue
   h.update(key.name.encode())
   for v in key.data:
    for c in v.co:h.update(struct.pack("<f",float(c)))
 for b in arm.data.bones:h.update((b.name+":"+(b.parent.name if b.parent else "")).encode())
 for pb in arm.pose.bones:
  for con in pb.constraints:
   h.update((pb.name+":"+con.type+":"+con.name).encode())
   h.update(struct.pack("<f",float(con.influence)))
 return h.hexdigest()
def quant(xs,p):
 return sorted(xs)[round((len(xs)-1)*p)] if xs else 0.
def metrics(o,arm,disable=False,collect=False):
 arm.animation_data_create()
 for tr in arm.animation_data.nla_tracks:tr.mute=True
 act=bpy.data.actions.get(ACT)
 if not act:raise RuntimeError("Missing animation")
 key=o.data.shape_keys.key_blocks.get(NAME) if o.data.shape_keys else None
 if key:key.mute=True
 arm.animation_data.action=None
 for b in arm.pose.bones:b.matrix_basis.identity()
 bpy.context.scene.frame_set(1)
 ref=pts(o)
 if key:key.mute=disable
 part=o.data.attributes.get("part_id")
 if not part:raise RuntimeError("No part_id")
 vv=o.data.vertices
 rois={
  "interleg":{i for i,v in enumerate(vv) if part.data[i].value==6 and -.1<=v.co.y<=.055 and abs(v.co.x)<=.165 and .045<=v.co.z<=.16},
  "front":{i for i,v in enumerate(vv) if part.data[i].value==6 and -.27<=v.co.y<=.055 and abs(v.co.x)<=.17 and .045<=v.co.z<=.285},
  "central":{i for i,v in enumerate(vv) if part.data[i].value==6 and -.27<=v.co.y<=.055 and abs(v.co.x)<=.06 and .045<=v.co.z<=.285},
  "rear":{i for i,v in enumerate(vv) if part.data[i].value==6 and .055<v.co.y<=.33 and abs(v.co.x)<=.17 and .06<=v.co.z<=.3},
  "foreleg":{i for i,v in enumerate(vv) if v.co.y<-.18 and v.co.z<.15 and abs(v.co.x)>.09},
  "head":{i for i,v in enumerate(vv) if v.co.y<-.30 and v.co.z>.22}}
 edges={name:[(i,j,d) for ed in o.data.edges for i,j in [tuple(ed.vertices)]
          if i in I and j in I for d in [(ref[j]-ref[i]).length] if d>.001] for name,I in rois.items()}
 triangles=[]
 for poly in o.data.polygons:
  ix=tuple(poly.vertices)
  if len(ix)<3 or not all(i in rois["interleg"] for i in ix):continue
  for i in range(1,len(ix)-1):
   a,b,c=ix[0],ix[i],ix[i+1]
   d=(ref[b]-ref[a]).cross(ref[c]-ref[a]).length
   if d>2e-7:triangles.append((a,b,c,d))
 scores=[];body15=None;seam=None
 for f in range(1,26):
  pose(arm,act,f)
  p=pts(o)
  if f==1:first=p
  if f==25:seam=max((x-y).length for x,y in zip(first,p))
  else:
   scores.append({name:quant([abs((p[j]-p[i]).length/d-1) for i,j,d in es],.95) for name,es in edges.items()})
   if f==15:body15=p
 summary={n:{"worst":max(x[n] for x in scores),"mean":statistics.mean(x[n] for x in scores)} for n in edges}
 area=[(body15[j]-body15[i]).cross(body15[k]-body15[i]).length/d for i,j,k,d in triangles]
 obj={"scores":summary,"seam":seam,"area15":{"under_half":sum(x<.5 for x in area)/len(area),
       "p05":quant(area,.05),"min":min(area),"triangles":len(area)}}
 if collect:obj.update(triangles=[(i,j,k) for i,j,k,_ in triangles],points15=body15)
 return obj
def normals_overlap(triangles,baseline,corrected):
 flipped=0; maxangle=0;angles=[]
 for i,j,k in triangles:
  n0=(baseline[j]-baseline[i]).cross(baseline[k]-baseline[i])
  n1=(corrected[j]-corrected[i]).cross(corrected[k]-corrected[i])
  if n0.length<1e-12 or n1.length<1e-12:continue
  cost=max(-1,min(1,n0.normalized().dot(n1.normalized())))
  if cost<0:flipped+=1
  angle=math.degrees(math.acos(cost))
  angles.append(angle);maxangle=max(maxangle,angle)
 def overlap(coords):
  # Adjacent faces sharing vertices cannot be scored as self-penetrations.
  tree=BVHTree.FromPolygons(coords,triangles,all_triangles=True,epsilon=1e-7)
  hits=tree.overlap(tree)
  results=set()
  for i,j in hits:
   if i>=j or set(triangles[i]).intersection(triangles[j]):continue
   results.add((i,j))
  return len(results),sorted(results)[:30]
 b,bi=overlap(baseline);c,ci=overlap(corrected)
 return {"relative_normal_flips":flipped,"normal_angle_p95":quant(angles,.95),
         "normal_angle_max":maxangle,"baseline_nonadjacent_overlaps":b,
         "candidate_nonadjacent_overlaps":c,
         "candidate_overlap_examples":ci,"baseline_overlap_examples":bi}
def main():
 args=cli();out=Path(args.out).resolve();out.mkdir(parents=True,exist_ok=True)
 r={"status":"STARTED","warning":"BVH overlap is a screening proxy, not watertight volume verification"}
 try:
  expected=json.loads(Path(args.expected).read_text())
  assert expected["status"]=="PASS_NUMERIC_AREA_REVIEW_ONLY" and expected["selection"]["key"]==NAME
  bpy.ops.wm.open_mainfile(filepath=str(Path(args.source).resolve()))
  o,arm=model();source_signature=sig(o,arm)
  b=metrics(o,arm,disable=True,collect=True)
  bpy.ops.wm.open_mainfile(filepath=str(Path(args.candidate).resolve()))
  o,arm=model();candidate_signature=sig(o,arm)
  if source_signature!=candidate_signature:raise RuntimeError("Source rest / weights / old shape keys / bones changed")
  if o.data.shape_keys.key_blocks.get(NAME) is None:raise RuntimeError("Corrective shape key not persisted")
  old=metrics(o,arm,disable=True)
  new=metrics(o,arm,disable=False,collect=True)
  drift_base=max(abs(old["scores"][n][k]-b["scores"][n][k]) for n in b["scores"] for k in ("worst","mean"))
  drift_new=max(abs(new["scores"][n][k]-expected["selection"]["score"][n][k]) for n in new["scores"] for k in ("worst","mean"))
  area_err=abs(new["area15"]["under_half"]-expected["selection"]["area15"]["under_half"])
  if drift_base>2e-4 or drift_new>2e-4 or area_err>1e-5 or max(b["seam"],old["seam"],new["seam"])>1e-5:
   raise RuntimeError("Independent saved action/mesh differs from source/baked results")
  normal=normals_overlap(new["triangles"],b["points15"],new["points15"])
  r.update(original_signature=source_signature,candidate_signature=candidate_signature,original=b["scores"],
           reopened_original=old["scores"],reopened_candidate=new["scores"],source_area=b["area15"],
           candidate_area=new["area15"],normal_and_overlap=normal,
           max_original_drift=drift_base,max_candidate_drift=drift_new,area_error=area_err,
           baseline_seam=b["seam"],new_seam=new["seam"])
  # Do not accept newly flipped face normals / increased nonadjacent interpenetrations,
  # even if unsigned face areas and p95 improved.
  if normal["relative_normal_flips"]>0 or normal["candidate_nonadjacent_overlaps"]>normal["baseline_nonadjacent_overlaps"]:
   r["status"]="PASS_REOPEN_BUT_FAIL_SURFACE_GEOMETRY"
  else:
   r["status"]="PASS_REOPEN_SURFACE_SCREEN_ONLY_NOT_PRODUCTION"
 except Exception as ex:
  r.update(status="FAIL",error=str(ex),traceback=traceback.format_exc())
 (out/"round17_independent_reopen_surface.json").write_text(json.dumps(r,indent=2,ensure_ascii=False))
 print("ROUND17_REOPEN",r["status"],"SOURCE_CHANGE",r.get("max_original_drift"),"CANDIDATE_CHANGE",r.get("max_candidate_drift"),"SURFACE",r.get("normal_and_overlap"))
 if r["status"]=="FAIL":raise SystemExit(1)
if __name__=="__main__":main()
