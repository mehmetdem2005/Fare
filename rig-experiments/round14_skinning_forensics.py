"""Round 14 forensic audit: distinguish weight-gradient tearing from singular/blended
bone-transform collapse in the actual 49-bone v8 Blender rig. No model edits.
The proxy LBS is only admissible if checked against Blender evaluated meshes.
"""
import bpy,sys,argparse,traceback,json,math,hashlib,statistics
from mathutils import Vector, Matrix
from pathlib import Path
from collections import Counter,defaultdict
try:
 import numpy as np
except ImportError:
 np=None

ROI_NAMES=("interleg","front","central","rear","foreleg","head")
ACTION="run_sprint_v8_ik_phase_NUMERIC_REVIEW"

def cli():
 p=argparse.ArgumentParser()
 p.add_argument("--source",required=True); p.add_argument("--out",required=True)
 return p.parse_args(sys.argv[sys.argv.index("--")+1:])

def pts(ob):
 dg=bpy.context.evaluated_depsgraph_get()
 ev=ob.evaluated_get(dg)
 m=ev.to_mesh(preserve_all_data_layers=False,depsgraph=dg)
 try:
  mat=ev.matrix_world.copy()
  return [mat@v.co for v in m.vertices]
 finally:ev.to_mesh_clear()

def percentile(v,p):
 if not v:return 0.
 v=sorted(v);return float(v[round((len(v)-1)*p)])

def reset(arm,act,fr):
 arm.animation_data.action=None
 for b in arm.pose.bones:b.matrix_basis.identity()
 bpy.context.scene.frame_set(1)
 arm.animation_data.action=act
 bpy.context.scene.frame_set(fr-1 if fr>1 else 2)
 bpy.context.scene.frame_set(fr)
 bpy.context.view_layer.update()

def get_input(ob,armmod):
 # Evaluated shape keys before armature deformation, in world space.
 was=armmod.show_viewport
 armmod.show_viewport=False
 bpy.context.view_layer.update()
 try:return pts(ob)
 finally:
  armmod.show_viewport=was
  bpy.context.view_layer.update()

def weights(ob,v):
 return {ob.vertex_groups[g.group].name:float(g.weight) for g in ob.data.vertices[v].groups
         if ob.vertex_groups[g.group].name}

def unit_rois(ob):
 a=ob.data.attributes.get("part_id")
 if not a:raise RuntimeError("Missing true body part id")
 return {
 "interleg":{i for i,x in enumerate(ob.data.vertices) if a.data[i].value==6 and -.1<=x.co.y<=.055 and abs(x.co.x)<=.165 and .045<=x.co.z<=.16},
 "front":{i for i,x in enumerate(ob.data.vertices) if a.data[i].value==6 and -.27<=x.co.y<=.055 and abs(x.co.x)<=.17 and .045<=x.co.z<=.285},
 "central":{i for i,x in enumerate(ob.data.vertices) if a.data[i].value==6 and -.27<=x.co.y<=.055 and abs(x.co.x)<=.06 and .045<=x.co.z<=.285},
 "rear":{i for i,x in enumerate(ob.data.vertices) if a.data[i].value==6 and .055<x.co.y<=.33 and abs(x.co.x)<=.17 and .06<=x.co.z<=.30},
 "foreleg":{i for i,x in enumerate(ob.data.vertices) if x.co.y<-.18 and x.co.z<.15 and abs(x.co.x)>.09},
 "head":{i for i,x in enumerate(ob.data.vertices) if x.co.y<-.30 and x.co.z>.22}
 }

def area_stats(ob,base,posed,I):
 # Area change for local body surfaces; avoid vertex-based p95 alone.
 ratios=[]
 for p in ob.data.polygons:
  ids=tuple(p.vertices)
  if len(ids)<3 or any(i not in I for i in ids):continue
  # Triangulate fan, stable paired topology.
  for k in range(1,len(ids)-1):
   i,j,z=ids[0],ids[k],ids[k+1]
   a=(base[j]-base[i]).cross(base[z]-base[i]).length
   b=(posed[j]-posed[i]).cross(posed[z]-posed[i]).length
   if a>1e-7:ratios.append(b/a)
 return {"triangles":len(ratios),"p05_area_ratio":percentile(ratios,.05),
         "p50_area_ratio":percentile(ratios,.5),"p95_area_ratio":percentile(ratios,.95),
         "min_area_ratio":min(ratios) if ratios else None,
         "max_area_ratio":max(ratios) if ratios else None,
         "fraction_area_under_half":sum(x<.5 for x in ratios)/len(ratios) if ratios else None}

def vmat(ob,arm):
 # Mesh-space armature bone transform; in world coords the same expression applies
 # if armature and mesh transforms are appropriately conjugated.
 C=ob.matrix_world.inverted()@arm.matrix_world
 Ci=C.inverted()
 return {b.name:C@arm.pose.bones[b.name].matrix@b.matrix_local.inverted()@Ci
         for b in arm.data.bones if b.use_deform and b.name in arm.pose.bones}

def main():
 a=cli();out=Path(a.out).resolve();out.mkdir(exist_ok=True,parents=True)
 report={"status":"STARTED","blender":bpy.app.version_string}
 try:
  bpy.ops.wm.open_mainfile(filepath=str(Path(a.source).resolve()))
  ob=max((x for x in bpy.data.objects if x.type=="MESH" and any(m.type=="ARMATURE" and m.object for m in x.modifiers)),key=lambda x:len(x.data.vertices))
  mod=next(m for m in ob.modifiers if m.type=="ARMATURE" and m.object)
  arm=mod.object
  assert len(arm.pose.bones)==49 and len(ob.data.vertices)==19466
  act=bpy.data.actions.get(ACTION)
  if act is None:raise RuntimeError("Not the verified 49-bone v8, action missing")
  arm.animation_data_create()
  for track in arm.animation_data.nla_tracks:track.mute=True
  arm.animation_data.action=None
  for b in arm.pose.bones:b.matrix_basis.identity()
  bpy.context.scene.frame_set(1)
  bpy.context.view_layer.update()
  rest=pts(ob)
  masks=unit_rois(ob)
  faces={name:[] for name in masks}
  edges={name:[] for name in masks}
  for e in ob.data.edges:
   i,j=tuple(e.vertices);d=(rest[j]-rest[i]).length
   if d<.001:continue
   for name,I in masks.items():
    if i in I and j in I:edges[name].append((i,j,d))
  report["roi"]={k:{"vertices":len(v),"edges":len(edges[k])} for k,v in masks.items()}
  def measures(co):
   return {name:{"p50":percentile([abs((co[j]-co[i]).length/d-1) for i,j,d in es],.5),
                  "p95":percentile([abs((co[j]-co[i]).length/d-1) for i,j,d in es],.95),
                  "p99":percentile([abs((co[j]-co[i]).length/d-1) for i,j,d in es],.99),
                  "max":max(abs((co[j]-co[i]).length/d-1) for i,j,d in es)} for name,es in edges.items()}
  report["modifier_order"]=[{"name":x.name,"type":x.type,"preserve_volume":getattr(x,"use_deform_preserve_volume",None)}
                           for x in ob.modifiers]
  report["mesh_shape_drivers"]=[]
  if ob.data.shape_keys and ob.data.shape_keys.animation_data:
   for fc in ob.data.shape_keys.animation_data.drivers:
    report["mesh_shape_drivers"].append({"data_path":fc.data_path,"expression":fc.driver.expression,
           "variables":[{"name":v.name,"type":v.type} for v in fc.driver.variables]})
  report["critical"]={}
  for frame in (1,15):
   reset(arm,act,frame);actual=pts(ob)
   before=get_input(ob,mod)
   reset(arm,act,frame)
   local_mats=vmat(ob,arm)
   # Convert point in world to mesh local. Matrices take mesh-local vectors.
   world=ob.matrix_world.copy();world_inv=world.inverted()
   test_edges=sorted([(abs((actual[j]-actual[i]).length/d-1),i,j,d) for i,j,d in edges["interleg"]],reverse=True)
   best=test_edges[:100]
   ids={q for _,i,j,_ in best for q in (i,j)}
   # Calculate precise LBS prediction and test it against actual depsgraph first.
   wdict={i:weights(ob,i) for i in ids}
   name2bone={b.name:b for b in arm.data.bones if b.use_deform}
   transformed={}
   predicted={}
   condition=[]
   for i in ids:
    w={k:v for k,v in wdict[i].items() if k in local_mats and v>1e-8}
    total=sum(w.values())
    if total<1e-8:continue
    p=world_inv@before[i]
    terms={k:world@(local_mats[k]@p) for k in w}
    transformed[i]=terms
    estimate=Vector((0,0,0))
    for k,v in w.items():estimate+=terms[k]*(v/total)
    predicted[i]=estimate
    if np is not None:
     mix=sum((local_mats[k].to_3x3() * (v/total) for k,v in w.items()),Matrix(((0,0,0),(0,0,0),(0,0,0))))
     singular=np.linalg.svd(np.array([list(row) for row in mix]),compute_uv=False)
     condition.append({"id":i,"determinant":float(mix.determinant()),"condition_number":float(singular[0]/max(singular[-1],1e-12)),
                       "smallest_singular":float(singular[-1]),"max_error":float((estimate-actual[i]).length)})
   errors=[(predicted[i]-actual[i]).length for i in predicted]
   actual_worst=[(int(i),int(j),float((actual[j]-actual[i]).length/d),float(d),float(err)) for err,i,j,d in best[:12]]
   # If Blender and LBS differ, do not attribute edge distortion to this proxy.
   valid=bool(errors) and max(errors)<1e-4
   hot_rows=[]
   for err,i,j,d in best[:60]:
    if i not in predicted or j not in predicted:continue
    pair=sorted(set(transformed[i])|set(transformed[j]))
    wi=wdict[i];wj=wdict[j]
    si=sum(wi.get(k,0) for k in pair);sj=sum(wj.get(k,0) for k in pair)
    if min(si,sj)<1e-8:continue
    smooth=Vector((0,0,0));jump=Vector((0,0,0))
    # For decomposition, evaluate every bone at BOTH points.
    pi=world_inv@before[i];pj=world_inv@before[j]
    for k in pair:
     if k not in local_mats:continue
     ti=world@(local_mats[k]@pi);tj=world@(local_mats[k]@pj)
     aa=wi.get(k,0)/si;bb=wj.get(k,0)/sj
     smooth+=(tj-ti)*(.5*(aa+bb))
     jump+=(tj+ti)*(.5*(bb-aa))
    predicted_edge=predicted[j]-predicted[i]
    if (predicted_edge-smooth-jump).length>1e-4:raise RuntimeError("Invalid edge identity")
    hot_rows.append({"edge":[i,j],"rest_len":d,"posed_len":float((actual[j]-actual[i]).length),
        "actual_ratio":(actual[j]-actual[i]).length/d,
        "measured_abs_change":err,"predicted_ratio":predicted_edge.length/d,
        "gradient_component_length":jump.length,"common_transform_component_length":smooth.length,
        "gradient_over_rest_length":jump.length/d,
        "gradient_fraction_of_deformed_vector":jump.length/max(predicted_edge.length,1e-8),
        "v_i_weights":wi,"v_j_weights":wj,
        "decomposition_verified":valid})
   keyvals={}
   if ob.data.shape_keys:
    keyvals={x.name:x.value for x in ob.data.shape_keys.key_blocks if x.name.startswith("crv")}
   # Independent modifier ablation: do shape keys actually matter at critical frames?
   original_keys=[(x,x.value,x.mute) for x in ob.data.shape_keys.key_blocks] if ob.data.shape_keys else []
   for key,v,muted in original_keys:
    if key.name!="Basis":key.mute=True
   bpy.context.view_layer.update()
   without=pts(ob)
   for key,v,muted in original_keys:key.mute=muted
   bpy.context.view_layer.update()
   roundtrip=pts(ob)
   if max((roundtrip[i]-actual[i]).length for i in ids)>1e-5:raise RuntimeError("Shape state leaked")
   morph_delta={n:measures(without)[n]["p95"]-measures(actual)[n]["p95"] for n in masks}
   report["critical"][str(frame)]={
     "weight_gradients_vs_skinning":{"proxy_valid":valid,"max_proxy_vertex_error":max(errors) if errors else None,
        "median_proxy_vertex_error":statistics.median(errors) if errors else None,
        "top_worst_edges":hot_rows,
        "matrix_condition":sorted(condition,key=lambda a:a["condition_number"],reverse=True)[:30]},
     "worst_12_edges":actual_worst,
     "full_scores":measures(actual),"shape_keys":keyvals,
     "shape_off_delta_p95":morph_delta,
     "area":area_stats(ob,rest,actual,masks["interleg"])}
  report["status"]="PASS_L3_FORENSICS_NO_REPAIR"
 except Exception as ex:
  report.update(status="FAIL",error=str(ex),traceback=traceback.format_exc())
 (out/"round14_skinning_decomposition.json").write_text(json.dumps(report,ensure_ascii=False,indent=2))
 print("ROUND14",report["status"])
 if report["status"]!="FAIL":
  for k,v in report["critical"].items():
   p=v["weight_gradients_vs_skinning"]
   print("ROUND14_FRAME",k,"PROXY",p["proxy_valid"],"MAX_ERR",p["max_proxy_vertex_error"],
      "EDGE",v["worst_12_edges"][:2],"SHAPE_OFF",v["shape_off_delta_p95"],"AREA",v["area"])
 else:
  print(report.get("error"));raise SystemExit(1)
if __name__=="__main__":main()
