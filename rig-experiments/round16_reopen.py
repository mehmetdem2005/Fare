"""Independent saved-and-reopened Blender v8 -> v9 (gait-only belly morph) test.
Verifies original rest, deform weights, existing 14 shape-key targets, constraints
and original v8 animation still match. New morph must be saved and evaluated.
"""
import bpy,sys,json,math,struct,hashlib,argparse,statistics,traceback
from pathlib import Path
from mathutils import Vector
ACTION="run_sprint_v8_ik_phase_NUMERIC_REVIEW"
KE=("R16_BELLY_EXTENSION_GAIT_ONLY","R16_BELLY_COMPRESSION_GAIT_ONLY")
def cli():
 p=argparse.ArgumentParser()
 for x in ("--source","--candidate","--expected","--out"):p.add_argument(x,required=True)
 return p.parse_args(sys.argv[sys.argv.index("--")+1:])
def obj():
 m=max((x for x in bpy.data.objects if x.type=="MESH" and any(md.type=="ARMATURE" and md.object for md in x.modifiers)),key=lambda x:len(x.data.vertices))
 arm=next(md.object for md in m.modifiers if md.type=="ARMATURE" and md.object)
 if len(m.data.vertices)!=19466 or len(arm.data.bones)!=49:raise RuntimeError("wrong source")
 return m,arm
def points(m):
 dg=bpy.context.evaluated_depsgraph_get();ev=m.evaluated_get(dg)
 tmp=ev.to_mesh(preserve_all_data_layers=False,depsgraph=dg)
 try:
  M=ev.matrix_world.copy();return [Vector(M@v.co) for v in tmp.vertices]
 finally:ev.to_mesh_clear()
def signature(m,arm):
 h=hashlib.sha256()
 deform={b.name for b in arm.data.bones if b.use_deform}
 for v in m.data.vertices:
  for a in v.co:h.update(struct.pack("<f",float(a)))
  entries=sorted((m.vertex_groups[x.group].name,x.weight) for x in v.groups if m.vertex_groups[x.group].name in deform)
  for name,w in entries:h.update(name.encode());h.update(struct.pack("<f",float(w)))
  h.update(b"\x00")
 for e in m.data.edges:h.update(struct.pack("<ii",*tuple(e.vertices)))
 for key in m.data.shape_keys.key_blocks:
  if key.name in KE:continue
  h.update(key.name.encode())
  for x in key.data:
   for c in x.co:h.update(struct.pack("<f",float(c)))
 for b in arm.data.bones:h.update((b.name+":"+(b.parent.name if b.parent else "")).encode())
 for pb in arm.pose.bones:
  for c in pb.constraints:
   h.update((pb.name+":"+c.type+":"+c.name).encode())
   h.update(struct.pack("<f",c.influence))
 return h.hexdigest()
def q(v,p):
 return sorted(v)[round((len(v)-1)*p)] if v else 0
def pose(arm,act,f):
 arm.animation_data.action=None
 for b in arm.pose.bones:b.matrix_basis.identity()
 bpy.context.scene.frame_set(1)
 arm.animation_data.action=act
 bpy.context.scene.frame_set(f-1 if f>1 else 2)
 bpy.context.scene.frame_set(f);bpy.context.view_layer.update()
def metric(m,arm,muted=False):
 arm.animation_data_create()
 for t in arm.animation_data.nla_tracks:t.mute=True
 act=bpy.data.actions.get(ACTION)
 if act is None:raise RuntimeError("Expected action missing")
 arm.animation_data.action=None
 for pb in arm.pose.bones:pb.matrix_basis.identity()
 for name in KE:
  key=m.data.shape_keys.key_blocks.get(name)
  if key:key.mute=True
 bpy.context.scene.frame_set(1);bpy.context.view_layer.update()
 reference=points(m)
 for name in KE:
  key=m.data.shape_keys.key_blocks.get(name)
  if key:key.mute=muted
 bpy.context.view_layer.update()
 part=m.data.attributes.get("part_id")
 vv=m.data.vertices
 roi={
  "interleg":{i for i,v in enumerate(vv) if part.data[i].value==6 and -.1<=v.co.y<=.055 and abs(v.co.x)<=.165 and .045<=v.co.z<=.16},
  "front":{i for i,v in enumerate(vv) if part.data[i].value==6 and -.27<=v.co.y<=.055 and abs(v.co.x)<=.17 and .045<=v.co.z<=.285},
  "central":{i for i,v in enumerate(vv) if part.data[i].value==6 and -.27<=v.co.y<=.055 and abs(v.co.x)<=.06 and .045<=v.co.z<=.285},
  "rear":{i for i,v in enumerate(vv) if part.data[i].value==6 and .055<v.co.y<=.33 and abs(v.co.x)<=.17 and .06<=v.co.z<=.3},
  "foreleg":{i for i,v in enumerate(vv) if v.co.y<-.18 and v.co.z<.15 and abs(v.co.x)>.09},
  "head":{i for i,v in enumerate(vv) if v.co.y<-.30 and v.co.z>.22},
 }
 E={n:[(i,j,d) for e in m.data.edges for i,j in [tuple(e.vertices)]
          if i in I and j in I for d in [(reference[j]-reference[i]).length] if d>.001] for n,I in roi.items()}
 rows=[];start=None
 for f in range(1,26):
  pose(arm,act,f);p=points(m)
  if f==1:start=p
  if f==25:seam=max((x-y).length for x,y in zip(p,start))
  else:rows.append({n:q([abs((p[j]-p[i]).length/d-1) for i,j,d in ee],.95) for n,ee in E.items()})
 summary={n:{"worst_p95":max(r[n] for r in rows),"mean_p95":statistics.mean(r[n] for r in rows)} for n in E}
 return summary,seam
def main():
 a=cli();out=Path(a.out).resolve();out.mkdir(parents=True,exist_ok=True)
 rep={"status":"STARTED"}
 try:
  expected=json.loads(Path(a.expected).read_text())
  assert expected["status"]=="PASS_L3_MORPH_NUMERIC_REVIEW_ONLY"
  bpy.ops.wm.open_mainfile(filepath=str(Path(a.source).resolve()))
  m,arm=obj();before=signature(m,arm);base,bseam=metric(m,arm)
  bpy.ops.wm.open_mainfile(filepath=str(Path(a.candidate).resolve()))
  m,arm=obj();after=signature(m,arm)
  if before!=after:raise RuntimeError("Original rest, weight, shape or constraint checksum changed")
  if any(m.data.shape_keys.key_blocks.get(n) is None for n in KE):raise RuntimeError("Missing new corrective shape key")
  base_reopened,sbase=metric(m,arm,muted=True)
  corrected,snew=metric(m,arm,muted=False)
  dbase=max(abs(base[n][key]-base_reopened[n][key]) for n in base for key in ("worst_p95","mean_p95"))
  dnew=max(abs(corrected[n][key]-expected["selection"]["scores"][n][key]) for n in corrected for key in ("worst_p95","mean_p95"))
  rep.update(original_checksum=before,new_checksum=after,baseline_drift=dbase,new_drift=dnew,
             source_seam=bseam,reopened_source_seam=sbase,new_seam=snew,
             original_score=base,corrected_score=corrected)
  if dbase>1e-4 or dnew>1e-4 or max(bseam,sbase,snew)>1e-5:
   raise RuntimeError("Reopened baked morph mismatch or loop failure")
  rep["status"]="PASS_L3_REOPEN_GAIT_SPECIFIC_NOT_PRODUCTION"
 except Exception as e:
  rep.update(status="FAIL",error=str(e),traceback=traceback.format_exc())
 (out/"round16_reopen.json").write_text(json.dumps(rep,indent=2,ensure_ascii=False))
 print("ROUND16_REOPEN",rep["status"],"DRIFT",rep.get("new_drift"))
 if rep["status"]=="FAIL":
  print(rep["error"]);raise SystemExit(1)
if __name__=="__main__":main()
