"""Controlled ventral torso skinning candidates for the existing 49-bone GitHub rig.
Only vertices anatomically inside a narrow fore-/hind-leg overlap gate may change.
No automatic weights, no bone edits, no original file overwrite.
Report actual Blender-evaluated deformation at 24 sprint frames before promotion.
"""
import bpy,math,sys,argparse,json,hashlib
from pathlib import Path
def args():
 p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--out',required=True)
 return p.parse_args(sys.argv[sys.argv.index('--')+1:])
def gv(g,i):
 try:return g.weight(i)
 except RuntimeError:return 0.
def smooth(lo,hi,x):
 t=max(0,min(1,(x-lo)/(hi-lo)));return t*t*(3-2*t)
def evaluated(mesh):
 graph=bpy.context.evaluated_depsgraph_get();ob=mesh.evaluated_get(graph)
 me=ob.to_mesh(preserve_all_data_layers=False,depsgraph=graph)
 try:
  world=ob.matrix_world.copy()
  return [tuple(world@v.co) for v in me.vertices]
 finally:ob.to_mesh_clear()
def quant(a,p):
 if not a:return 0.
 a.sort();return a[int((len(a)-1)*p)]
def main():
 cfg=args();root=Path(cfg.out).resolve();root.mkdir(exist_ok=True,parents=True)
 report={'source':cfg.source,'candidates':[],'status':'STARTED'}
 try:
  bpy.ops.wm.open_mainfile(filepath=str(Path(cfg.source).resolve()))
  mesh=max([o for o in bpy.data.objects if o.type=='MESH' and any(m.type=='ARMATURE' and m.object for m in o.modifiers)],key=lambda o:len(o.data.vertices))
  arm=next(m.object for m in mesh.modifiers if m.type=='ARMATURE' and m.object)
  scene=bpy.context.scene
  act=bpy.data.actions.get('run_sprint_v3')
  if not act:raise RuntimeError('run_sprint_v3 missing')
  groups={g.name:g for g in mesh.vertex_groups}
  needed=['upper_arm.L','upper_arm.R','thigh.L','thigh.R','spine_04','spine_05']
  if any(x not in groups for x in needed):raise RuntimeError('Missing necessary groups')
  verts=mesh.data.vertices;nn=len(verts);part=mesh.data.attributes.get('part_id')
  if part is None:raise RuntimeError('part_id metadata absent: no safe candidate')
  ws={name:[gv(groups[name],i) for i in range(nn)] for name in needed}
  initial_sum=[sum(g.weight for g in v.groups) for v in verts]
  def group_roi(label,i):
   v=verts[i];x,y,z=v.co
   if label=='interleg':return part.data[i].value==6 and -.1<=y<=.055 and .045<=z<=.16 and abs(x)<=.165
   if label=='chest':return -.27<=y<=.045 and .055<=z<=.285 and abs(x)<=.165
   if label=='core':return -.27<=y<=.045 and .055<=z<=.285 and abs(x)<=.06
   if label=='rear':return -.005<=y<=.331 and .05<=z<=.27 and abs(x)<=.165
   if label=='fore_leg_distal':return y<-.18 and z<.15 and abs(x)>.09
  roi={name:{i for i in range(nn) if group_roi(name,i)} for name in ('interleg','chest','core','rear','fore_leg_distal')}
  edges={name:[tuple(e.vertices) for e in mesh.data.edges if e.vertices[0] in idx and e.vertices[1] in idx] for name,idx in roi.items()}
  arm.animation_data_create()
  for tr in arm.animation_data.nla_tracks:tr.mute=True
  arm.animation_data.action=None
  for pb in arm.pose.bones:pb.matrix_basis.identity()
  scene.frame_set(1)
  rest=evaluated(mesh)
  edge_lengths={name:[math.dist(rest[a],rest[b]) for a,b in ed] for name,ed in edges.items()}
  def take():
   arm.animation_data.action=act
   results={name:[] for name in roi}
   snapshots=[]
   for f in range(1,26):
    scene.frame_set(f)
    coords=evaluated(mesh)
    if f==1:snapshots=coords
    for name,ed in edges.items():
     strains=[abs(math.dist(coords[a],coords[b])/den-1) for (a,b),den in zip(ed,edge_lengths[name]) if den>.001]
     results[name].append({'frame':f,'p95':quant(strains,.95),'p99':quant(strains,.99),
                           'max':max(strains) if strains else 0.})
   arm.animation_data.action=None
   scene.frame_set(1)
   return results,snapshots
  base,reference=take()
  def summary(res):
   return {name:{'mean_p95':sum(x['p95'] for x in rows[:24])/24,
                 'worst_p95':max(x['p95'] for x in rows[:24]),
                 'frame1_p95':rows[0]['p95'],'frame9_p95':rows[8]['p95'],
                 'vertices':len(roi[name]),'edges':len(edges[name])}
           for name,rows in res.items()}
  report['reference']=summary(base)
  # Surface-graph Laplacian over the original upper-arm/thigh mixing field.
  # This test does NOT force limbs into spine; it preserves each vertex's
  # summed arm+thigh mass, deform-bone set and remaining unrelated groups.
  adj={i:[] for i in roi['interleg']}
  for ed in mesh.data.edges:
   i,j=ed.vertices
   if i not in adj or j not in adj:continue
   a=verts[i];b=verts[j]
   if a.co.x*b.co.x<0 or (a.co-b.co).length>.028 or a.normal.dot(b.normal)<.45:continue
   adj[i].append(j);adj[j].append(i)
  candidates={}
  for i in roi['interleg']:
   x,y,z=verts[i].co;side='L' if x>=0 else 'R'
   u=ws['upper_arm.'+side][i];t=ws['thigh.'+side][i]
   if min(u,t)<.015 or u+t<.40:continue
   candidates[i]=u/(u+t)
  smoothed=dict(candidates)
  for _ in range(14):
   nex={}
   for i,r in smoothed.items():
    neighbors=[smoothed[j] for j in adj.get(i,()) if j in smoothed]
    nex[i]=.62*r+.38*(sum(neighbors)/len(neighbors)) if neighbors else r
   smoothed=nex
  for strength in (.60,.95):
   # Every candidate starts from the original source weights.
   for name,arr in ws.items():
    g=groups[name]
    for i,orig in enumerate(arr):
     if abs(gv(g,i)-orig)>1e-6:g.add([i],orig,'REPLACE')
   changed=[];moved_total=0.
   for i in candidates:
    x,y,z=verts[i].co;side='L' if x>=0 else 'R'
    u='upper_arm.'+side;t='thigh.'+side
    wu=ws[u][i];wt=ws[t][i];total=wu+wt
    gate=smooth(-.145,-.08,y)*(1-smooth(.035,.095,y))*smooth(.035,.06,z)*(1-smooth(.15,.195,z))*(1-smooth(.145,.17,abs(x)))
    fraction=min(.95,strength*gate)
    if fraction<.015:continue
    r0=wu/total;rnew=r0+(smoothed[i]-r0)*fraction
    next_u=total*rnew;next_t=total-next_u
    if abs(next_u-wu)<1e-6:continue
    groups[u].add([i],next_u,'REPLACE')
    groups[t].add([i],next_t,'REPLACE')
    moved_total+=abs(next_u-wu);changed.append(i)
   current=[sum(g.weight for g in v.groups) for v in verts]
   maxsum=max(abs(a-b) for a,b in zip(initial_sum,current))
   if maxsum>2e-5:raise RuntimeError('Weight sums not conserved '+str(maxsum))
   # No edits are allowed on non-selected vertices.
   changeset=set(changed)
   for i in range(nn):
    if i not in changeset and abs(initial_sum[i]-current[i])>1e-7:raise RuntimeError('Spurious weight edit '+str(i))
   report_entry={'strength':strength,'changed_vertices':len(changed),'total_redistributed_weight':moved_total,
                 'max_weight_sum_difference':maxsum}
   if not changed:raise RuntimeError('Empty anatomical repair region')
   output,post_reference=take()
   report_entry['after']=summary(output)
   report_entry['roi_improvements_pct']={
    name:{'mean':100*(1-report_entry['after'][name]['mean_p95']/report['reference'][name]['mean_p95']) if report['reference'][name]['mean_p95'] else 0,
          'max':100*(1-report_entry['after'][name]['worst_p95']/report['reference'][name]['worst_p95']) if report['reference'][name]['worst_p95'] else 0}
    for name in roi}
   report_entry['max_frame1_vertex_move_in_changed_region']=max(math.dist(reference[i],post_reference[i]) for i in changed)
   # no safety approval until visual and leg contact / volume assessment. Save separate candidates.
   savepath=root/('mouse_sprint_v3_toposmooth_%02d_EXPERIMENT.blend'%int(round(strength*100)))
   arm.animation_data.action=act
   scene.frame_set(1)
   bpy.ops.wm.save_as_mainfile(filepath=str(savepath),compress=True)
   report_entry['candidate_blend']=savepath.name
   report['candidates'].append(report_entry)
  report['status']='MEASURED_TOPOLOGY_EXPERIMENTS_NEED_VISUAL_ACCEPTANCE'
 except Exception as ex:
  report['status']='FAIL';report['error']=str(ex);report['traceback']=__import__('traceback').format_exc()
 finally:
  (root/'topology_weight_trials.json').write_text(json.dumps(report,indent=2,ensure_ascii=False))
  print('TOPOLOGY_TRIAL_STATUS',report['status'])
  print('TOPOLOGY_TRIALS',[(c['strength'],c['changed_vertices'],c['roi_improvements_pct']) for c in report['candidates']])
 if report['status']=='FAIL':raise SystemExit(1)
if __name__=='__main__':main()
