import sys, math, os
import numpy as np
sys.path.append("/tmp/rig/td"); sys.path.append("/tmp/rig")
import skinlib as SL

OUT = "/tmp/rig/td/z1_ear"
os.makedirs(OUT, exist_ok=True)
S = SL.Skin("/tmp/rig/mouse_rig.blend")
scene = SL.setup_render()
cams = SL.make_cams()
R = math.radians

def ear_pose():
    S.reset_pose()
    S.rot("ear.L", R(35))
    S.rot("ear_02.L", R(20))
    S.rot("ear.R", 0, R(30), 0)   # twist testi

def gap_metric(isl_name):
    from mathutils import kdtree
    from mathutils import Vector
    body = S.island("body")
    kd = kdtree.KDTree(len(body))
    for j, vi in enumerate(body):
        kd.insert(Vector(S.CO[vi]), j)
    kd.balance()
    pairs = []
    for vi in S.island(isl_name):
        co, j, dist = kd.find(Vector(S.CO[vi]))
        if dist < 0.008:
            pairs.append((int(vi), int(body[j]), float(dist)))
    pc = S.posed_coords()
    inc = [float(np.linalg.norm(pc[a] - pc[b]) - d) for a, b, d in pairs]
    return max(inc) * 1000 if inc else 0.0

# ---- BEFORE ----
ear_pose()
m = S.zone_mask(["ear.L", "ear_02.L", "ear_03.L", "ear_04.L"], 0.2) & (S.pid == S.IDS["ear_L"])
p99_b, max_b = S.stretch((S.pid == S.IDS["ear_L"]))
gapL_b = gap_metric("ear_L"); gapR_b = gap_metric("ear_R")
SL.render(f"{OUT}/before_pose.png", cams["ear_L"])
print(f"ONCE: stretch p99={p99_b:.2f} max={max_b:.2f} | gap L={gapL_b:.1f}mm R={gapR_b:.1f}mm")

# ---- FIX ----
for side, isl_name in (("L", "ear_L"), ("R", "ear_R")):
    chain = [b.name for b in S.arm.data.bones if b.name.startswith("ear") and b.name.endswith("." + side)]
    chain.sort(key=lambda n: (0 if n == f"ear.{side}" else int(n.split("_")[1].split(".")[0])))
    isl = S.island(isl_name)
    poly = []
    for i, bn in enumerate(chain):
        h, t = S.bone_pts(bn)
        poly.append(h)
        if i == len(chain) - 1:
            poly.append(t)
    s, d = S.chain_param(poly, isl)
    L = sum(np.linalg.norm(np.array(b) - np.array(a)) for a, b in zip(poly, poly[1:]))
    base_band = 0.42 * L
    f = SL.Skin.smoothstep(s / base_band)
    ear_sum = np.zeros(len(isl))
    for bn in chain:
        ear_sum += S.GW[bn][isl]
    headw = S.GW["head"][isl]
    tot = ear_sum + headw
    new_ear = tot * f
    S.GW["head"][isl] = tot - new_ear
    scale = np.where(ear_sum > 1e-9, new_ear / np.maximum(ear_sum, 1e-9), 0.0)
    for bn in chain:
        S.GW[bn][isl] = S.GW[bn][isl] * scale
    zero = (ear_sum <= 1e-9) & (new_ear > 1e-6)
    S.GW[chain[0]][isl[zero]] += new_ear[zero]
    # segmentler arasi yumusak gecis
    isl_mask = np.zeros(S.NV, bool); isl_mask[isl] = True
    for a, b in zip(chain, chain[1:]):
        n = S.band(a, b, width=0.017, sel=isl_mask)
    print(f"EAR {side}: {len(chain)} kemik, taban bandi={base_band*1000:.0f}mm")

S.write_weights()

# ---- AFTER ----
ear_pose()
p99_a, max_a = S.stretch((S.pid == S.IDS["ear_L"]))
gapL_a = gap_metric("ear_L"); gapR_a = gap_metric("ear_R")
SL.render(f"{OUT}/after_pose.png", cams["ear_L"])
S.reset_pose()
SL.render(f"{OUT}/after_rest.png", cams["ear_L"])
print(f"SONRA: stretch p99={p99_a:.2f} max={max_a:.2f} | gap L={gapL_a:.1f}mm R={gapR_a:.1f}mm")

S.save("/tmp/rig/mouse_rig_td.blend")
print("SAVED mouse_rig_td.blend")
