import sys, math, os
import numpy as np
sys.path.append("/tmp/rig/td"); sys.path.append("/tmp/rig")
import skinlib as SL

OUT = "/tmp/rig/td/z2_elbow"
os.makedirs(OUT, exist_ok=True)
S = SL.Skin("/tmp/rig/mouse_rig_td.blend")
scene = SL.setup_render()
cams = SL.make_cams()
R = math.radians

def test_pose(side):
    S.reset_pose()
    S.rot(f"forearm.{side}", R(90))

# BEFORE
test_pose("L")
zL = S.zone_mask(["upper_arm.L", "forearm.L"], 0.3)
p99_b, max_b = S.stretch(zL)
SL.render(f"{OUT}/before_L90.png", cams["arm_L"])
print(f"ONCE dirsek_L: p99={p99_b:.2f} max={max_b:.2f}")

for side, xs in (("L", 1), ("R", -1)):
    ua, fa = f"upper_arm.{side}", f"forearm.{side}"
    hUA, _ = S.bone_pts(ua)
    hFA, tFA = S.bone_pts(fa)
    poly = [hUA, hFA, tFA]
    s, d = S.chain_param(poly, np.arange(S.NV))
    sel = (~S.wh_mask) & (S.pid == S.IDS["body"]) & (S.CO[:, 0] * xs > 0.02) & (d < 0.085)
    n = S.band(ua, fa, width=0.035, sel=sel)
    # pati adasinin arka kismi da dirsek bandina girebilir (forearm tasiyor)
    paw = "paw_front_L" if side == "L" else "paw_front_R"
    selp = (S.pid == S.IDS[paw]) & (d < 0.085)
    n2 = S.band(ua, fa, width=0.035, sel=selp)
    print(f"dirsek {side}: {n}+{n2} vert bantlandi")

S.write_weights()

# AFTER
test_pose("L")
p99_a, max_a = S.stretch(zL)
SL.render(f"{OUT}/after_L90.png", cams["arm_L"])
test_pose("R")
zR = S.zone_mask(["upper_arm.R", "forearm.R"], 0.3)
p99_r, max_r = S.stretch(zR)
S.reset_pose()
print(f"SONRA dirsek_L: p99={p99_a:.2f} max={max_a:.2f} | dirsek_R: p99={p99_r:.2f} max={max_r:.2f}")
S.save("/tmp/rig/mouse_rig_td.blend")
print("SAVED")
