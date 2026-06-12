"""8 saldiri — IK zemin temasli yeniden yazim.
Ayaklar planted (IK), jest kollari aksiyon bazinda FK (influence keyli)."""
import sys, math
sys.path.append("/tmp/rig/td"); sys.path.append("/tmp/rig")
import skinlib as SL
import animlib as AL
import bpy

S = SL.Skin("/tmp/rig/mouse_rig_td.blend")
C, D = bpy.context, bpy.data
rig = AL.Rig(S)
arm = S.arm
R = AL.R
arm.animation_data_create()

def legs_fk_tuck(a=1.0):
    for s in "LR":
        rig.rot(f"thigh.{s}", R(22) * a); rig.rot(f"shin.{s}", -R(30) * a); rig.rot(f"foot.{s}", R(16) * a)

def keyed(name, nframes, keys, infl_keys):
    """keys: [(frame, fn)] poz-to-poz; infl_keys: [(frame, hL,hR,fL,fR)]"""
    def build(act):
        for f, vals in infl_keys:
            rig.key_influences(f, *vals)
        for f, fn in keys:
            rig.reset()
            if fn:
                fn()
            rig.key_all(f)
    AL.make_action(D, arm, name, nframes, build)

# ============ atk_bite 24f: 4 ayak planted, govde atilir ============
keyed("atk_bite", 24, [
    (1, None),
    (7, lambda: (rig.spine(R(5)), rig.rot("neck", R(7)), rig.rot("head", R(5)),
                 rig.wloc("hips", 0, 0.012, 0.002), rig.tail(rz=R(6)))),
    (11, lambda: (rig.spine(-R(7)), rig.rot("neck", -R(14)), rig.rot("head", -R(12)),
                  rig.rot("snout", -R(9)), rig.wloc("hips", 0, -0.055, -0.004), rig.tail(rz=-R(4)))),
    (13, lambda: (rig.spine(-R(6)), rig.rot("neck", -R(12)), rig.rot("head", -R(9)),
                  rig.rot("snout", R(5)), rig.wloc("hips", 0, -0.047, -0.003), rig.tail(rz=-R(5)))),
    (18, lambda: (rig.spine(-R(2)), rig.rot("neck", -R(4)), rig.wloc("hips", 0, -0.008, 0))),
    (24, None),
], [(1, (1, 1, 1, 1))])

# ============ atk_swipe: jest kolu FK, kalan 3 planted ============
def mk_swipe(side, sgn):
    infl = (0, 1, 1, 1) if side == "L" else (1, 0, 1, 1)
    keyed(f"atk_swipe_{side}", 20, [
        (1, None),
        (6, lambda: (rig.rot("root", 0, 0, R(10) * sgn), rig.spine(0, R(7) * sgn),
                     rig.rot(f"upper_arm.{side}", R(14)), rig.rot(f"forearm.{side}", R(58)),
                     rig.rot(f"hand.{side}", R(8)),
                     rig.rot("neck", 0, 0, R(6) * sgn), rig.wloc("hips", 0, 0.006, 0.002),
                     rig.tail(rz=R(10) * sgn))),
        (10, lambda: (rig.rot("root", 0, 0, -R(13) * sgn), rig.spine(0, -R(9) * sgn),
                      rig.rot(f"upper_arm.{side}", -R(52)), rig.rot(f"forearm.{side}", R(26)),
                      rig.rot(f"hand.{side}", -R(12)), rig.rot("neck", 0, 0, -R(8) * sgn),
                      rig.rot("head", 0, 0, -R(6) * sgn), rig.wloc("hips", 0, -0.010, 0),
                      rig.tail(rz=-R(12) * sgn))),
        (13, lambda: (rig.rot("root", 0, 0, -R(9) * sgn), rig.spine(0, -R(6) * sgn),
                      rig.rot(f"upper_arm.{side}", -R(34)), rig.rot(f"forearm.{side}", R(34)),
                      rig.tail(rz=-R(8) * sgn))),
        (20, None),
    ], [(1, infl)])
mk_swipe("R", -1.0)
mk_swipe("L", 1.0)

# ============ atk_double_claw 30f: kollar FK havada, arka IK planted ============
keyed("atk_double_claw", 30, [
    (1, None),
    (9, lambda: (rig.rot("hips", R(11)), rig.spine(R(46)), rig.rot("neck", -R(10)),
                 rig.arms_fk(ua=-R(60), fa=R(48), ha=-R(10)),
                 rig.wloc("hips", 0, 0.020, 0.012), rig.tail(rz=R(5), rx=R(6)))),
    (12, lambda: (rig.rot("hips", R(14)), rig.spine(R(55)), rig.rot("neck", -R(12)),
                  rig.arms_fk(ua=-R(80), fa=R(58), ha=-R(18)),
                  rig.wloc("hips", 0, 0.024, 0.016), rig.tail(rx=R(8)))),
    (16, lambda: (rig.rot("hips", -R(2)), rig.spine(-R(4)), rig.rot("neck", -R(10)),
                  rig.rot("head", -R(8)), rig.arms_fk(ua=R(18), fa=R(15), ha=-R(30)),
                  rig.wloc("hips", 0, -0.028, -0.014), rig.tail(rz=-R(4)))),
    (20, lambda: (rig.spine(R(5)), rig.rot("neck", -R(5)), rig.arms_fk(ua=R(8), fa=R(20), ha=-R(15)),
                  rig.wloc("hips", 0, -0.012, -0.006))),
    (30, None),
], [(1, (0, 0, 1, 1))])

# ============ atk_pounce 32f: planted -> havada FK -> ileri planted ============
FWD = -0.085
keyed("atk_pounce", 32, [
    (1, None),
    (9, lambda: (rig.spine(R(8)), rig.rot("neck", -R(4)),
                 rig.wloc("hips", 0, 0.012, -0.022), rig.tail(rz=R(8), rx=R(4)))),
    (13, lambda: (rig.spine(-R(9)), rig.rot("neck", R(5)), legs_fk_tuck(-0.4),
                  rig.arms_fk(ua=-R(50), fa=R(10)), rig.wloc("hips", 0, -0.055, 0.055),
                  rig.tail(rx=-R(8), lag=0.15),
                  rig.t_foot("L", 0, FWD, 0), rig.t_foot("R", 0, FWD, 0),
                  rig.t_hand("L", 0, FWD, 0), rig.t_hand("R", 0, FWD, 0))),
    (17, lambda: (rig.spine(-R(2)), rig.rot("neck", -R(8)), rig.rot("head", -R(8)),
                  rig.rot("snout", -R(7)), rig.arms_fk(fa=R(20)),
                  rig.wloc("hips", 0, FWD - 0.005, 0.004),
                  rig.t_foot("L", 0, FWD, 0), rig.t_foot("R", 0, FWD, 0),
                  rig.t_hand("L", 0, FWD - 0.01, 0), rig.t_hand("R", 0, FWD - 0.01, 0))),
    (21, lambda: (rig.spine(R(7)), rig.rot("neck", -R(4)), rig.rot("snout", R(4)),
                  rig.wloc("hips", 0, FWD, -0.012),
                  rig.t_foot("L", 0, FWD, 0), rig.t_foot("R", 0, FWD, 0),
                  rig.t_hand("L", 0, FWD - 0.01, 0), rig.t_hand("R", 0, FWD - 0.01, 0))),
    (26, lambda: (rig.spine(R(2)), rig.wloc("hips", 0, FWD * 0.4, -0.003),
                  rig.t_foot("L", 0, FWD * 0.4, 0), rig.t_foot("R", 0, FWD * 0.4, 0),
                  rig.t_hand("L", 0, FWD * 0.4, 0), rig.t_hand("R", 0, FWD * 0.4, 0))),
    (32, None),
], [(1, (1, 1, 1, 1)), (11, (1, 1, 1, 1)), (14, (0, 0, 0, 0)), (16, (1, 1, 1, 1))])

# ============ atk_tail_whip 26f: 4 planted, root pivot ============
keyed("atk_tail_whip", 26, [
    (1, None),
    (7, lambda: (rig.rot("root", 0, 0, R(18)), rig.spine(0, R(10)), rig.tail(rz=R(26), lag=0.10),
                 rig.rot("neck", 0, 0, R(8)), rig.wloc("hips", 0, 0.005, 0))),
    (12, lambda: (rig.rot("root", 0, 0, -R(22)), rig.spine(0, -R(12)), rig.tail(rz=-R(20), lag=-0.05),
                  rig.rot("neck", 0, 0, -R(10)), rig.wloc("hips", 0, -0.005, 0))),
    (15, lambda: (rig.rot("root", 0, 0, -R(16)), rig.spine(0, -R(9)), rig.tail(rz=-R(34), lag=0.22),
                  rig.rot("neck", 0, 0, -R(6)))),
    (19, lambda: (rig.rot("root", 0, 0, -R(6)), rig.spine(0, -R(3)), rig.tail(rz=-R(12), lag=0.10))),
    (26, None),
], [(1, (1, 1, 1, 1))])

# ============ atk_spin 28f: 4 planted (root ile doner) ============
def spin_pose(deg):
    rig.rot("root", 0, 0, R(deg))
    rig.arms_fk(ua=-R(8), fa=R(8))
    rig.tail(rz=R(18), lag=0.12)
    rig.spine(R(3))
    rig.wloc("hips", 0, 0, -0.010)
keyed("atk_spin", 28, [
    (1, None),
    (6, lambda: (rig.rot("root", 0, 0, -R(18)), rig.spine(0, -R(6)),
                 rig.tail(rz=-R(14)), rig.wloc("hips", 0, 0, -0.010))),
    (10, lambda: spin_pose(80)),
    (14, lambda: spin_pose(190)),
    (18, lambda: spin_pose(300)),
    (21, lambda: (rig.rot("root", 0, 0, R(360)), rig.tail(rz=R(10), lag=0.1),
                  rig.wloc("hips", 0, 0, -0.005))),
    (28, lambda: rig.rot("root", 0, 0, R(360))),
], [(1, (1, 1, 1, 1))])

# ============ atk_jump_slam 34f ============
keyed("atk_jump_slam", 34, [
    (1, None),
    (9, lambda: (rig.spine(R(7)), rig.rot("neck", -R(5)),
                 rig.wloc("hips", 0, 0.010, -0.026), rig.tail(rz=R(6)))),
    (14, lambda: (rig.spine(-R(11)), legs_fk_tuck(-0.4), rig.arms_fk(ua=-R(70), fa=R(40)),
                  rig.rot("neck", R(8)), rig.wloc("hips", 0, -0.006, 0.065),
                  rig.tail(rx=-R(8), lag=0.15))),
    (18, lambda: (rig.spine(R(6)), rig.rot("neck", -R(6)), rig.rot("head", -R(6)),
                  legs_fk_tuck(0.3), rig.arms_fk(ua=-R(35), fa=R(30)),
                  rig.wloc("hips", 0, -0.016, 0.030))),
    (21, lambda: (rig.spine(R(13)), rig.rot("neck", -R(9)), rig.rot("head", -R(7)),
                  rig.arms_fk(ua=R(20), fa=R(12), ha=-R(25)),
                  rig.wloc("hips", 0, -0.020, -0.020), rig.tail(rz=R(4), rx=R(4)))),
    (25, lambda: (rig.spine(R(6)), rig.arms_fk(ua=R(8), fa=R(18), ha=-R(10)),
                  rig.wloc("hips", 0, -0.010, -0.006))),
    (34, None),
], [(1, (1, 1, 1, 1)), (11, (1, 1, 1, 1)), (14, (0, 0, 0, 0)), (19, (0, 0, 0, 0)), (21, (1, 1, 1, 1))])

arm.animation_data.action = None
rig.reset()
for k, con in rig.ik_cons.items():
    con.influence = 1.0
bpy.ops.wm.save_as_mainfile(filepath="/tmp/rig/mouse_rig_td.blend")
print("ATTACKS v3 OK")
