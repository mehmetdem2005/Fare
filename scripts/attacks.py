"""8 saldiri animasyonu — poz-to-poz keyframe, Bezier easing.
Hepsi rest'ten baslar rest'te biter (idle'a temiz blend)."""
import sys, math
import numpy as np
sys.path.append("/tmp/rig/td"); sys.path.append("/tmp/rig")
import skinlib as SL
import bpy
from mathutils import Vector

S = SL.Skin("/tmp/rig/mouse_rig_td.blend")
C, D = bpy.context, bpy.data
arm = S.arm
R = math.radians

for b in arm.pose.bones:
    for con in b.constraints:
        if con.type == 'IK':
            con.influence = 0.0
arm.animation_data_create()

# hips dunya-uzayi ofseti -> bone-lokal
hips_rest = arm.data.bones["hips"].matrix_local.to_3x3()
hips_inv = hips_rest.inverted()
def wloc(wx=0.0, wy=0.0, wz=0.0):
    l = hips_inv @ Vector((wx, wy, wz))
    arm.pose.bones["hips"].location = l

def rot(bn, rx=0.0, ry=0.0, rz=0.0):
    pb = arm.pose.bones[bn]
    pb.rotation_mode = 'XYZ'
    e = pb.rotation_euler
    pb.rotation_euler = (e[0] + rx, e[1] + ry, e[2] + rz)

def spine(rx=0.0, rz=0.0):
    prof = (0.16, 0.21, 0.26, 0.21, 0.16)
    for k in range(5):
        rot(f"spine_{k+1:02d}", rx * prof[k], 0, rz * prof[k])

def tail(rz=0.0, rx=0.0, lag=0.0):
    for i in range(1, 7):
        rot(f"tail_{i:02d}", rx, 0, rz * (1.0 + lag * i))

def arms(ua=0.0, fa=0.0, ha=0.0, side="LR"):
    for s in side:
        rot(f"upper_arm.{s}", ua); rot(f"forearm.{s}", fa); rot(f"hand.{s}", ha)

def legs_crouch(a=1.0):
    for s in "LR":
        rot(f"thigh.{s}", R(22) * a); rot(f"shin.{s}", -R(30) * a); rot(f"foot.{s}", R(16) * a)

def make_attack(name, nframes, keys):
    old = D.actions.get(name)
    if old:
        D.actions.remove(old)
    act = D.actions.new(name)
    arm.animation_data.action = act
    for f, fn in keys:
        S.reset_pose()
        if fn:
            fn()
        for pb in arm.pose.bones:
            pb.keyframe_insert("rotation_euler", frame=f)
            pb.keyframe_insert("location", frame=f)
    act.use_fake_user = True
    print(f"ATTACK {name}: {nframes}f / {len(keys)} key")

# ================= atk_bite (24f) =================
make_attack("atk_bite", 24, [
    (1, None),
    (7, lambda: (spine(R(5)), rot("neck", R(7)), rot("head", R(5)), wloc(0, 0.012, 0.002), tail(rz=R(6)))),
    (11, lambda: (spine(-R(7)), rot("neck", -R(14)), rot("head", -R(12)), rot("snout", -R(9)),
                  wloc(0, -0.065, -0.006), arms(ua=R(10)), tail(rz=-R(4)))),
    (13, lambda: (spine(-R(6)), rot("neck", -R(12)), rot("head", -R(9)), rot("snout", R(5)),
                  wloc(0, -0.055, -0.005), tail(rz=-R(5)))),
    (18, lambda: (spine(-R(2)), rot("neck", -R(4)), rot("head", -R(2)), wloc(0, -0.008, 0))),
    (24, None),
])

# ================= atk_swipe_R / L (20f) =================
def mk_swipe(side, other, sgn):
    make_attack(f"atk_swipe_{side}", 20, [
        (1, None),
        (6, lambda: (rot("root", 0, 0, R(10) * sgn), spine(0, R(7) * sgn),
                     rot(f"upper_arm.{side}", R(28)), rot(f"forearm.{side}", R(20)),
                     rot("neck", 0, 0, R(6) * sgn), wloc(0, 0.008, 0.002), tail(rz=R(10) * sgn))),
        (10, lambda: (rot("root", 0, 0, -R(13) * sgn), spine(0, -R(9) * sgn),
                      rot(f"upper_arm.{side}", -R(55)), rot(f"forearm.{side}", R(8)),
                      rot(f"hand.{side}", -R(25)), rot("neck", 0, 0, -R(8) * sgn),
                      rot("head", 0, 0, -R(6) * sgn), wloc(0, -0.012, 0), tail(rz=-R(12) * sgn))),
        (13, lambda: (rot("root", 0, 0, -R(9) * sgn), spine(0, -R(6) * sgn),
                      rot(f"upper_arm.{side}", -R(38)), rot(f"forearm.{side}", R(25)),
                      tail(rz=-R(8) * sgn))),
        (20, None),
    ])
mk_swipe("R", "L", -1.0)   # sag pence: govde once sola coil (+z saga... sgn=-1 sag swipe)
mk_swipe("L", "R", 1.0)

# ================= atk_double_claw (30f) =================
make_attack("atk_double_claw", 30, [
    (1, None),
    (9, lambda: (rot("hips", R(11)), spine(R(46)), rot("neck", -R(10)), arms(ua=-R(60), fa=R(48), ha=-R(10)),
                 legs_crouch(0.6), wloc(0, 0.020, -0.002), tail(rz=R(5), rx=R(6)))),
    (12, lambda: (rot("hips", R(14)), spine(R(55)), rot("neck", -R(12)), arms(ua=-R(80), fa=R(58), ha=-R(18)),
                  legs_crouch(0.65), wloc(0, 0.024, 0.0), tail(rx=R(8)))),
    (16, lambda: (rot("hips", -R(2)), spine(-R(4)), rot("neck", -R(10)), rot("head", -R(8)),
                  arms(ua=R(18), fa=R(15), ha=-R(30)),
                  legs_crouch(0.75), wloc(0, -0.030, -0.016), tail(rz=-R(4)))),
    (20, lambda: (spine(R(5)), rot("neck", -R(5)), arms(ua=R(8), fa=R(20), ha=-R(15)),
                  legs_crouch(0.4), wloc(0, -0.012, -0.006))),
    (30, None),
])

# ================= atk_pounce (32f) =================
make_attack("atk_pounce", 32, [
    (1, None),
    (9, lambda: (spine(R(8)), rot("neck", -R(4)), legs_crouch(1.0),
                 arms(ua=R(18), fa=R(24)), wloc(0, 0.015, -0.020), tail(rz=R(8), rx=R(4)))),
    (14, lambda: (spine(-R(9)), rot("neck", R(5)), legs_crouch(-0.5),
                  arms(ua=-R(50), fa=R(10)), wloc(0, -0.075, 0.060), tail(rx=-R(8), lag=0.15))),
    (18, lambda: (spine(-R(2)), rot("neck", -R(8)), rot("head", -R(8)), rot("snout", -R(7)),
                  arms(ua=-R(22), fa=R(35), ha=-R(12)), wloc(0, -0.100, 0.006),
                  legs_crouch(0.2), tail(rx=R(3)))),
    (22, lambda: (spine(R(7)), rot("neck", -R(4)), rot("snout", R(4)), legs_crouch(0.6),
                  arms(ua=R(5), fa=R(28)), wloc(0, -0.075, -0.015))),
    (27, lambda: (spine(R(2)), wloc(0, -0.028, -0.004), legs_crouch(0.2))),
    (32, None),
])

# ================= atk_tail_whip (26f) =================
make_attack("atk_tail_whip", 26, [
    (1, None),
    (7, lambda: (rot("root", 0, 0, R(18)), spine(0, R(10)), tail(rz=R(26), lag=0.10),
                 rot("neck", 0, 0, R(8)), wloc(0, 0.006, 0))),
    (12, lambda: (rot("root", 0, 0, -R(22)), spine(0, -R(12)), tail(rz=-R(20), lag=-0.05),
                  rot("neck", 0, 0, -R(10)), wloc(0, -0.006, 0))),
    (15, lambda: (rot("root", 0, 0, -R(16)), spine(0, -R(9)), tail(rz=-R(34), lag=0.22),
                  rot("neck", 0, 0, -R(6)))),
    (19, lambda: (rot("root", 0, 0, -R(6)), spine(0, -R(3)), tail(rz=-R(12), lag=0.10))),
    (26, None),
])

# ================= atk_spin (28f) =================
def spin_pose(deg, crouch=0.5, tl=18):
    rot("root", 0, 0, R(deg))
    legs_crouch(crouch)
    arms(ua=-R(20), fa=R(15))
    tail(rz=R(tl), lag=0.12)
    spine(R(3))
    wloc(0, 0, -0.008)
make_attack("atk_spin", 28, [
    (1, None),
    (6, lambda: (rot("root", 0, 0, -R(18)), spine(0, -R(6)), legs_crouch(0.5),
                 tail(rz=-R(14)), wloc(0, 0, -0.008))),
    (10, lambda: spin_pose(80)),
    (14, lambda: spin_pose(190)),
    (18, lambda: spin_pose(300)),
    (21, lambda: (rot("root", 0, 0, R(360)), legs_crouch(0.35), tail(rz=R(10), lag=0.1),
                  wloc(0, 0, -0.005))),
    (28, lambda: rot("root", 0, 0, R(360))),
])

# ================= atk_jump_slam (34f) =================
make_attack("atk_jump_slam", 34, [
    (1, None),
    (9, lambda: (spine(R(7)), legs_crouch(1.1), arms(ua=R(20), fa=R(30)),
                 rot("neck", -R(5)), wloc(0, 0.012, -0.024), tail(rz=R(6)))),
    (14, lambda: (spine(-R(11)), legs_crouch(-0.4), arms(ua=-R(70), fa=R(40)),
                  rot("neck", R(8)), wloc(0, -0.008, 0.065), tail(rx=-R(8), lag=0.15))),
    (18, lambda: (spine(R(6)), rot("neck", -R(6)), rot("head", -R(6)),
                  arms(ua=-R(35), fa=R(30)), wloc(0, -0.020, 0.030), legs_crouch(0.3))),
    (21, lambda: (spine(R(13)), rot("neck", -R(9)), rot("head", -R(7)),
                  arms(ua=R(20), fa=R(12), ha=-R(25)), wloc(0, -0.026, -0.018),
                  legs_crouch(0.8), tail(rz=R(4), rx=R(4)))),
    (25, lambda: (spine(R(6)), arms(ua=R(8), fa=R(18), ha=-R(10)),
                  wloc(0, -0.012, -0.006), legs_crouch(0.4))),
    (34, None),
])

arm.animation_data.action = None
S.reset_pose()
bpy.ops.wm.save_as_mainfile(filepath="/tmp/rig/mouse_rig_td.blend")
print("ATTACKS OK")
