import bpy, math, sys
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils import kdtree

sys.path.append("/tmp/rig")
import plan_data as P

bpy.ops.wm.open_mainfile(filepath="/tmp/rig/mouse_imported.blend")
C, D = bpy.context, bpy.data

def select_only(obs, active):
    bpy.ops.object.select_all(action='DESELECT')
    for o in obs:
        o.select_set(True)
    C.view_layer.objects.active = active

# ============ 1. cleanup, center, rename, tag, join ============
ico = D.objects.get("Icosphere")
if ico:
    D.objects.remove(ico, do_unlink=True)

meshes = [o for o in D.objects if o.type == 'MESH']
select_only(meshes, meshes[0])
bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
for nm in ("Armature", "ParentNode"):
    ob = D.objects.get(nm)
    if ob:
        D.objects.remove(ob, do_unlink=True)

PART_IDS = {}
for ob in meshes:
    ob.vertex_groups.clear()
    for m in list(ob.modifiers):
        ob.modifiers.remove(m)
    ob.location.x += P.MESH_SHIFT_X

select_only(meshes, meshes[0])
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

for i, (old, new) in enumerate(P.MESH_RENAME.items()):
    ob = D.objects[old]
    ob.name = new
    ob.data.name = new
    PART_IDS[new] = i
    attr = ob.data.attributes.new("part_id", 'INT', 'POINT')
    attr.data.foreach_set("value", [i] * len(ob.data.vertices))

join_list = [D.objects[n] for n in P.MESH_RENAME.values()]
select_only(join_list, D.objects["body"])
bpy.ops.object.join()
mouse = D.objects["body"]
mouse.name = "Mouse"
mouse.data.name = "Mouse"
me = mouse.data
NV = len(me.vertices)
pid = np.empty(NV, dtype=np.int32)
me.attributes["part_id"].data.foreach_get("value", pid)
CO = np.empty(NV * 3)
me.vertices.foreach_get("co", CO)
CO = CO.reshape(NV, 3)
ISLAND = {n: np.where(pid == i)[0] for n, i in PART_IDS.items()}
print(f"JOIN OK: {NV} vert, adalar: " + ", ".join(f"{n}:{len(v)}" for n, v in ISLAND.items()))

# ============ 2. containment infrastructure (rest mesh) ============
polys = [tuple(p.vertices) for p in me.polygons]
BVH = BVHTree.FromPolygons([tuple(v) for v in CO], polys)
body_polys = [pv for pv in polys if all(pid[i] == PART_IDS["body"] for i in pv)]
BODY_BVH = BVHTree.FromPolygons([tuple(v) for v in CO], body_polys)

RAY_DIRS = [Vector((0.57735, 0.57736, 0.57737)), Vector((-0.32, 0.84, 0.44)), Vector((0.1, -0.62, 0.78))]
def inside(p, bvh=None):
    bvh = bvh or BVH
    votes = 0
    for d in RAY_DIRS:
        cnt = 0
        o = Vector(p)
        hit = bvh.ray_cast(o, d)
        while hit[0] is not None:
            cnt += 1
            o = hit[0] + d * 1e-5
            hit = bvh.ray_cast(o, d)
        votes += cnt % 2
    return votes >= 2

def pull_inside(p, margin=0.005):
    p = Vector(p)
    for _ in range(5):
        if inside(p):
            return p, True
        co, n, _, _ = BVH.find_nearest(p)
        out = (p - co).dot(n) > 0
        p = co - n * margin if out else co + n * margin
    return p, inside(p)

# ============ 3. joints: nudge ends + translate-fix mids ============
# joint graph: shared points move together
joints = {}   # key -> Vector ; bones reference keys
bone_pts = {} # bone -> (hkey, tkey)
def jkey(p):
    return (round(p[0], 5), round(p[1], 5), round(p[2], 5))

for name, b in P.BONES.items():
    hk, tk = jkey(b["head"]), jkey(b["tail"])
    bone_pts[name] = (hk, tk)
    if not b["deform"]:
        continue  # root etc. stays exactly where planned (origin/ground)
    joints.setdefault(hk, Vector(b["head"]))
    joints.setdefault(tk, Vector(b["tail"]))

log = []
for k, v in list(joints.items()):
    nv, ok = pull_inside(v)
    if (nv - v).length > 1e-6:
        log.append(f"  nudge joint {k} -> {tuple(round(x,4) for x in nv)} ({'ok' if ok else 'FAIL'})")
    joints[k] = nv

# mid fix: translate both joints of a bone inward if mid outside
for _pass in range(3):
    moved = False
    for name, b in P.BONES.items():
        if not b["deform"]:
            continue
        h, t = joints[bone_pts[name][0]], joints[bone_pts[name][1]]
        bad = [f for f in (0.3, 0.5, 0.7) if not inside(h.lerp(t, f))]
        if not bad:
            continue
        f = bad[len(bad)//2]
        mid = h.lerp(t, f)
        co, n, _, _ = BVH.find_nearest(mid)
        delta = (co - n * 0.0045) - mid
        if delta.length > 0.014:
            delta = delta * (0.014 / delta.length)
        nh, nt = h + delta, t + delta
        if inside(nh) and inside(nt):
            joints[bone_pts[name][0]] = nh
            joints[bone_pts[name][1]] = nt
            log.append(f"  midfix {name}: translate {tuple(round(v,4) for v in delta)}")
            moved = True
    if not moved:
        break

print("JOINT FIXES:")
print("\n".join(log) if log else "  yok")

# ============ 4. ear chains auto-fit ============
def fit_ear(island_name, side):
    idx = ISLAND[island_name]
    pts = CO[idx]
    zlo, zhi = pts[:, 2].min(), pts[:, 2].max()
    nb = 7
    knots = []
    for i in range(nb):
        z0 = zlo + (zhi - zlo) * i / nb
        z1 = zlo + (zhi - zlo) * (i + 1) / nb
        s = pts[(pts[:, 2] >= z0) & (pts[:, 2] <= z1)]
        if len(s) > 3:
            knots.append(tuple(s.mean(0)))
    def chain_midfix(kn):
        kn = [Vector(k) for k in kn]
        for _ in range(4):
            moved = False
            for i in range(len(kn) - 1):
                a, b = kn[i], kn[i + 1]
                bad = [f for f in (0.25, 0.5, 0.75) if not inside(a.lerp(b, f))]
                if not bad:
                    continue
                mid = a.lerp(b, bad[len(bad) // 2])
                co, n, _, _ = BVH.find_nearest(mid)
                delta = (co - n * 0.0035) - mid
                if delta.length > 0.01:
                    delta = delta * (0.01 / delta.length)
                kn[i] = kn[i] + delta
                kn[i + 1] = kn[i + 1] + delta
                moved = True
            if not moved:
                break
        return kn

    def chain_ok(kn):
        for a, b in zip(kn, kn[1:]):
            for f in (0.15, 0.4, 0.6, 0.85):
                if not inside(Vector(a).lerp(Vector(b), f)):
                    return False
        return True

    best = None
    for nseg in (2, 3, 4):
        kn = P.resample(knots, nseg)
        kn = [pull_inside(Vector(k), margin=0.0035)[0] for k in kn]
        kn = chain_midfix(kn)
        kn = [pull_inside(Vector(k), margin=0.0035)[0] for k in kn]
        best = (kn, nseg)
        if chain_ok(kn):
            return kn, nseg
    return best

EAR_CHAINS = {}
for island_name, side in (("ear_L", "L"), ("ear_R", "R")):
    kn, nseg = fit_ear(island_name, side)
    EAR_CHAINS[side] = kn
    print(f"EAR {side}: {nseg} segment, knots=" + " ".join(str(tuple(round(v,4) for v in k)) for k in kn))

# ============ 5. build armature ============
arm_data = D.armatures.new("MouseRig")
arm_ob = D.objects.new("MouseRig", arm_data)
C.scene.collection.objects.link(arm_ob)
select_only([arm_ob], arm_ob)
bpy.ops.object.mode_set(mode='EDIT')
ebs = arm_data.edit_bones

DEFORM_BONES = []
for name, b in P.BONES.items():
    eb = ebs.new(name)
    eb.head = joints.get(bone_pts[name][0], Vector(b["head"]))
    eb.tail = joints.get(bone_pts[name][1], Vector(b["tail"]))
    eb.use_deform = b["deform"]
    if b["parent"]:
        eb.parent = ebs[b["parent"]]
        eb.use_connect = b["connect"]
    eb.align_roll(Vector(P.ROLL_TARGET[name]))
    if b["deform"]:
        DEFORM_BONES.append(name)

EAR_BONES = {"L": [], "R": []}
for side, kn in EAR_CHAINS.items():
    prev = "head"
    for i, (a, b) in enumerate(zip(kn, kn[1:])):
        nm = f"ear.{side}" if i == 0 else f"ear_{i+1:02d}.{side}"
        eb = ebs.new(nm)
        eb.head, eb.tail = a, b
        eb.use_deform = True
        eb.parent = ebs[prev]
        eb.use_connect = (i > 0)
        eb.align_roll(Vector((0, -1, 0)))
        EAR_BONES[side].append(nm)
        DEFORM_BONES.append(nm)
        prev = nm

for side in ("L", "R"):
    for kind, spec in P.IK.items():
        joint = Vector(ebs[f"{spec['target_at']}.{side}"].head)
        eb = ebs.new(f"ik_{spec['target_at']}.{side}")
        eb.head = joint
        eb.tail = joint + Vector((0, -0.05, 0))
        eb.parent = ebs["root"]
        eb.use_deform = False
        # pole exactly in the chain bend plane => near-zero rest deviation
        A = Vector(ebs[f"{spec['chain'][0]}.{side}"].head)
        B = Vector(ebs[f"{spec['chain'][1]}.{side}"].head)
        Cp = Vector(ebs[f"{spec['chain'][1]}.{side}"].tail)
        axis = (Cp - A).normalized()
        bend = (B - A) - axis * (B - A).dot(axis)
        if bend.length < 1e-4:
            bend = Vector(spec["pole_off"])
        eb = ebs.new(f"pole_{kind}.{side}")
        eb.head = B + bend.normalized() * 0.13
        eb.tail = eb.head + Vector((0, 0, 0.04))
        eb.parent = ebs["root"]
        eb.use_deform = False

bpy.ops.object.mode_set(mode='OBJECT')
coll_def = arm_data.collections.new("DEF")
coll_ctl = arm_data.collections.new("CTRL")
for b in arm_data.bones:
    (coll_def if b.use_deform else coll_ctl).assign(b)
print(f"ARMATURE: {len(DEFORM_BONES)} deform + {len(arm_data.bones)-len(DEFORM_BONES)} ctrl")

# ============ 6. heat solve (clean-copy trick) ============
def set_deform_subset(allowed):
    for b in arm_data.bones:
        b.use_deform = b.name in allowed

def restore_deform():
    for b in arm_data.bones:
        b.use_deform = b.name in DEFORM_BONES

def heat_solve(src_obj, subset, only_idx=None):
    """returns {bone: np.array(NVsrc)} solved on a cleaned duplicate; only_idx: limit dup to these verts"""
    dup_me = src_obj.data.copy()
    dup = D.objects.new("HEAT_TMP", dup_me)
    C.scene.collection.objects.link(dup)
    if only_idx is not None:
        keep = set(int(i) for i in only_idx)
        import bmesh
        bm = bmesh.new()
        bm.from_mesh(dup_me)
        bm.verts.ensure_lookup_table()
        oi = bm.verts.layers.int.new("oi")
        for i, v in enumerate(bm.verts):
            v[oi] = i
        doomed = [v for i, v in enumerate(bm.verts) if i not in keep]
        bmesh.ops.delete(bm, geom=doomed, context='VERTS')
        bm.to_mesh(dup_me)
        bm.free()
    # cleanup pass for solver stability
    select_only([dup], dup)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles(threshold=1e-6)
    bpy.ops.mesh.dissolve_degenerate(threshold=1e-6)
    bpy.ops.object.mode_set(mode='OBJECT')
    dup.vertex_groups.clear()
    set_deform_subset(subset)
    select_only([dup, arm_ob], arm_ob)
    bpy.ops.object.parent_set(type='ARMATURE_AUTO')
    restore_deform()
    # read weights from dup
    nd = len(dup_me.vertices)
    gidx = {g.index: g.name for g in dup.vertex_groups}
    W = {gn: np.zeros(nd) for gn in gidx.values()}
    for i, v in enumerate(dup_me.vertices):
        for ge in v.groups:
            W[gidx[ge.group]][i] = ge.weight
    # original index mapping
    if only_idx is not None and "oi" in [l.name for l in []]:
        pass
    if only_idx is not None:
        # oi stored as bmesh int layer is lost in to_mesh unless attribute; rebuild map by position
        pass
    kd = kdtree.KDTree(nd)
    for i, v in enumerate(dup_me.vertices):
        kd.insert(v.co, i)
    kd.balance()
    dead = [g for g, arr in W.items() if arr.max() < 0.005]
    D.objects.remove(dup, do_unlink=True)
    D.meshes.remove(dup_me)
    return W, kd, dead

def map_weights(W, kd, target_idx):
    """map dup-space weights to Mouse verts target_idx via nearest position"""
    out = {g: np.zeros(len(target_idx)) for g in W}
    for j, vi in enumerate(target_idx):
        co, di, dist = kd.find(Vector(CO[vi]))
        for g in W:
            out[g][j] = W[g][di]
    return out

# ---- stage 1: whole mesh, all deform except ears (whiskers fixed later) ----
subset1 = [b for b in DEFORM_BONES if not b.startswith("ear")]
W1, kd1, dead1 = heat_solve(mouse, subset1)
print(f"HEAT stage1: {len(subset1)} kemik, dead={dead1 if dead1 else 'yok'}")

GW = {g: np.zeros(NV) for g in subset1}
all_idx = np.arange(NV)
m1 = map_weights(W1, kd1, all_idx)
for g in GW:
    if g in m1:
        GW[g] = m1[g]

# fallback for dead bones: capsule distance on their island chains
def capsule_fill(bones, island_idx):
    eps = 1e-8
    Wd = {}
    for bn in bones:
        b = arm_data.bones[bn]
        a = np.array(b.head_local); t = np.array(b.tail_local)
        ab = t - a
        pts = CO[island_idx]
        tt = np.clip(((pts - a) @ ab) / max(ab @ ab, eps), 0, 1)
        dd = np.linalg.norm(pts - (a + tt[:, None] * ab[None]), axis=1)
        Wd[bn] = 1.0 / (dd + 0.01) ** 2
    S = sum(Wd.values())
    for bn in Wd:
        Wd[bn] = Wd[bn] / S
    return Wd

if dead1:
    # find islands those bones serve
    CHAIN_ISLAND = {
        "paw_front_L": ["forearm.L", "hand.L", "front_toes.L"],
        "paw_front_R": ["forearm.R", "hand.R", "front_toes.R"],
        "foot_hind_L": ["shin.L", "foot.L", "toes.L"],
        "foot_hind_R": ["shin.R", "foot.R", "toes.R"],
        "tail": [f"tail_{i:02d}" for i in range(1, 7)],
    }
    for isl, chain in CHAIN_ISLAND.items():
        if any(b in dead1 for b in chain):
            fb = capsule_fill(chain, ISLAND[isl])
            for bn, arr in fb.items():
                GW[bn][ISLAND[isl]] = arr
            print(f"  fallback capsule: {isl} <- {chain}")

# ---- stage 2: ears (separate solve on ear islands) ----
for side, isl in (("L", "ear_L"), ("R", "ear_R")):
    sub = EAR_BONES[side] + ["head"]
    Wq, kdq, deadq = heat_solve(mouse, sub, only_idx=ISLAND[isl])
    mq = map_weights(Wq, kdq, ISLAND[isl])
    if deadq and any(b.startswith("ear") for b in deadq):
        fb = capsule_fill(EAR_BONES[side], ISLAND[isl])
        for bn in EAR_BONES[side]:
            GW.setdefault(bn, np.zeros(NV))[ISLAND[isl]] = fb[bn]
        print(f"HEAT ears {side}: FALLBACK capsule (dead={deadq})")
    else:
        for g, arr in mq.items():
            GW.setdefault(g, np.zeros(NV))
            GW[g][ISLAND[isl]] = arr
        print(f"HEAT ears {side}: ok ({len(sub)} kemik)")

# ---- whiskers rigid ----
for isl in ("whiskers_L", "whiskers_R"):
    for g in GW:
        GW[g][ISLAND[isl]] = 0.0
    GW.setdefault("snout", np.zeros(NV))
    GW["snout"][ISLAND[isl]] = 1.0
print("WHISKERS: %100 snout (rijit)")

# ---- island masks: ear weights only on ear islands ----
ear_groups = [g for g in GW if g.startswith("ear")]
mask = np.ones(NV, bool)
mask[ISLAND["ear_L"]] = False
mask[ISLAND["ear_R"]] = False
for g in ear_groups:
    GW[g][mask] = 0.0

# ---- coverage guarantee: no vertex may stay weightless ----
sums = np.zeros(NV)
for arr in GW.values():
    sums += arr
empty_idx = np.where(sums < 0.01)[0]
if len(empty_idx):
    good_idx = np.where(sums > 0.5)[0]
    kd_fill = kdtree.KDTree(len(good_idx))
    for j, vi in enumerate(good_idx):
        kd_fill.insert(Vector(CO[vi]), j)
    kd_fill.balance()
    for vi in empty_idx:
        _, j, _ = kd_fill.find(Vector(CO[vi]))
        src = good_idx[j]
        for g in GW:
            GW[g][vi] = GW[g][src]
print(f"COVERAGE: {len(empty_idx)} bos vertex en yakin dolu vertexten dolduruldu")

# ============ 7. write provisional groups + smooth FIRST ============
def write_groups():
    mouse.vertex_groups.clear()
    for g, arr in GW.items():
        if arr.max() < 0.001:
            continue
        vg = mouse.vertex_groups.new(name=g)
        nz = np.where(arr > 0.0005)[0]
        for vi in nz:
            vg.add([int(vi)], float(arr[vi]), 'REPLACE')

def read_groups():
    out = {}
    gnames = {g.index: g.name for g in mouse.vertex_groups}
    for gn in gnames.values():
        out[gn] = np.zeros(NV)
    for v in me.vertices:
        for ge in v.groups:
            out[gnames[ge.group]][v.index] = ge.weight
    return out

write_groups()
mod = mouse.modifiers.new("Armature", 'ARMATURE')
mod.object = arm_ob
mouse.parent = arm_ob

select_only([mouse], mouse)
bpy.ops.object.mode_set(mode='WEIGHT_PAINT')
bpy.ops.object.vertex_group_smooth(group_select_mode='ALL', factor=0.4, repeat=3, expand=0.3)
bpy.ops.object.mode_set(mode='OBJECT')
GW = read_groups()
print("SMOOTH OK (weld oncesi)")

# ============ 8. weld rims to SMOOTHED body field (paws, feet, tail, EARS) ============
poly_arr = body_polys
def sample_body_field(p):
    co, n, fidx, dist = BODY_BVH.find_nearest(Vector(p))
    if dist is None:
        return None, None
    pvs = poly_arr[fidx]
    ds = np.array([1.0 / (np.linalg.norm(CO[q] - np.array(co)) + 1e-6) for q in pvs])
    ds /= ds.sum()
    return {g: float(sum(GW[g][q] * w for q, w in zip(pvs, ds))) for g in GW}, dist

WELD_SPEC = [("paw_front_L", 0.012), ("paw_front_R", 0.012),
             ("foot_hind_L", 0.012), ("foot_hind_R", 0.012),
             ("tail", 0.012), ("ear_L", 0.0075), ("ear_R", 0.0075)]
for isl, maxd in WELD_SPEC:
    cnt = 0
    for vi in ISLAND[isl]:
        fld, dist = sample_body_field(CO[vi])
        if fld is None or dist > maxd:
            continue
        for g in GW:
            GW[g][vi] = fld[g]
        cnt += 1
    print(f"WELD {isl}: {cnt} rim vert (yumusatilmis alandan)")

# ============ 9. whiskers: per-tube CONSTANT weights from face field ============
# each tube = connected component; root = closest point to body; the whole tube
# takes the face's local weight mix -> follows the cheek skin, never bends.
wh_idx = np.concatenate([ISLAND["whiskers_L"], ISLAND["whiskers_R"]])
wh_set = set(int(i) for i in wh_idx)
parent_uf = {int(i): int(i) for i in wh_idx}
def find(a):
    while parent_uf[a] != a:
        parent_uf[a] = parent_uf[parent_uf[a]]
        a = parent_uf[a]
    return a
def union(a, b):
    ra, rb = find(a), find(b)
    if ra != rb:
        parent_uf[ra] = rb
for e in me.edges:
    a, b = e.vertices
    if a in wh_set and b in wh_set:
        union(int(a), int(b))
comps = {}
for i in wh_idx:
    comps.setdefault(find(int(i)), []).append(int(i))
print(f"WHISKERS: {len(comps)} tup bulundu")
for root, verts_c in comps.items():
    dists = [(BODY_BVH.find_nearest(Vector(CO[v]))[3], v) for v in verts_c[::max(1, len(verts_c)//40)]]
    rootv = min(dists)[1]
    fld, _ = sample_body_field(CO[rootv])
    for g in GW:
        GW[g][np.array(verts_c)] = fld.get(g, 0.0)
print("WHISKERS: tup basina sabit agirlik (yuz derisini takip eder, bukulmez)")

# ============ 10. final write + hygiene (weld sonrasi yumusatma YOK) ============
write_groups()
select_only([mouse], mouse)
bpy.ops.object.mode_set(mode='WEIGHT_PAINT')
bpy.ops.object.vertex_group_clean(group_select_mode='ALL', limit=0.004)
bpy.ops.object.vertex_group_limit_total(group_select_mode='ALL', limit=4)
bpy.ops.object.vertex_group_normalize_all(group_select_mode='ALL', lock_active=False)
bpy.ops.object.mode_set(mode='OBJECT')
print("HYGIENE OK (clean .004, max 4 etki, normalize)")

# ============ 10b. seam consistency: UV-dikis duplike vertexleri ayni agirligi paylasir ============
GWF = read_groups()
clusters = {}
for vi in range(NV):
    key = (round(CO[vi][0], 6), round(CO[vi][1], 6), round(CO[vi][2], 6))
    clusters.setdefault(key, []).append(vi)
multi = [c for c in clusters.values() if len(c) > 1]
fixed = 0
for c in multi:
    idx = np.array(c)
    for g in GWF:
        m = GWF[g][idx].mean()
        GWF[g][idx] = m
    fixed += len(c)
GW = GWF
write_groups()
select_only([mouse], mouse)
bpy.ops.object.mode_set(mode='WEIGHT_PAINT')
bpy.ops.object.vertex_group_limit_total(group_select_mode='ALL', limit=4)
bpy.ops.object.vertex_group_normalize_all(group_select_mode='ALL', lock_active=False)
bpy.ops.object.mode_set(mode='OBJECT')
print(f"SEAM FIX: {len(multi)} dikis kumesi / {fixed} vertex esitlendi")

# ============ 9. IK + numeric pole calibration ============
pbs = arm_ob.pose.bones
def chain_dev(names):
    C.view_layer.update()
    dg = C.evaluated_depsgraph_get()
    aev = arm_ob.evaluated_get(dg)
    dev = 0.0
    for n in names:
        pb = aev.pose.bones[n]
        rb = arm_data.bones[n]
        dev += (pb.tail - Vector(rb.tail_local)).length + (pb.head - Vector(rb.head_local)).length
    return dev

for side in ("L", "R"):
    for kind, spec in P.IK.items():
        chain = [f"{spec['chain'][0]}.{side}", f"{spec['chain'][1]}.{side}"]
        con = pbs[chain[1]].constraints.new('IK')
        con.target = arm_ob
        con.subtarget = f"ik_{spec['target_at']}.{side}"
        con.pole_target = arm_ob
        con.pole_subtarget = f"pole_{kind}.{side}"
        con.chain_count = 2
        con.influence = 1.0
        best = (1e9, 0.0)
        for deg in range(-180, 180, 15):
            con.pole_angle = math.radians(deg)
            d = chain_dev(chain)
            if d < best[0]:
                best = (d, deg)
        for deg in np.arange(best[1] - 14, best[1] + 14.1, 2.0):
            con.pole_angle = math.radians(float(deg))
            d = chain_dev(chain)
            if d < best[0]:
                best = (d, float(deg))
        con.pole_angle = math.radians(best[1])
        print(f"IK {kind}.{side}: pole_angle={best[1]:.0f}° sapma={best[0]*1000:.2f}mm")

# ============ 10. final verification ============
C.view_layer.update()
fails = []
for b in arm_data.bones:
    if not b.use_deform:
        continue
    h, t = Vector(b.head_local), Vector(b.tail_local)
    for lbl, f in (("head", 0.0), ("q1", 0.3), ("mid", 0.5), ("q3", 0.7), ("tail", 0.97)):
        p = h.lerp(t, f)
        if not inside(p):
            fails.append(f"{b.name}.{lbl}")
print("CONTAINMENT: " + ("TUM DEFORM KEMIKLER MESH ICINDE ✓" if not fails else "DISARIDA: " + ", ".join(fails)))

# dead group scan
gmax = {g.name: 0.0 for g in mouse.vertex_groups}
for v in me.vertices:
    for ge in v.groups:
        gn = mouse.vertex_groups[ge.group].name
        if ge.weight > gmax[gn]:
            gmax[gn] = ge.weight
dead = [g for g, mx in gmax.items() if mx < 0.1]
print("DEAD GROUPS: " + (str(dead) if dead else "yok ✓") + f" | toplam grup: {len(gmax)}")

bpy.ops.wm.save_as_mainfile(filepath="/tmp/rig/mouse_rig.blend")
print("SAVED /tmp/rig/mouse_rig.blend")
