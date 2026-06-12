"""8 saldiri v4 — TAM VUCUT koordinasyonu:
agirlik aktarimi, adimlama (IK hedef hareketi), kulak pin/perk,
kuyruk karsi-denge + follow-through overshoot, kafa takibi."""
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

def ears(v):  # + perk (one), - pin (yatik)
    rig.rot("ear.L", R(v)); rig.rot("ear.R", R(v))

def keyed(name, nframes, keys, infl_keys):
    def build(act):
        for f, vals in infl_keys:
            rig.key_influences(f, *vals)
        for f, fn in keys:
            rig.reset()
            if fn:
                fn()
            rig.key_all(f)
    AL.make_action(D, arm, name, nframes, build)

# ============ atk_bite 24f: adim + atilim + geri tepme ============
def bite_strike(t=1.0, snout=-9):
    rig.spine(-R(7) * t); rig.rot("neck", -R(14) * t); rig.rot("head", -R(12) * t)
    rig.rot("snout", R(snout))
    rig.wloc("hips", 0, -0.055 * t, -0.004 * t)
    rig.tail(rx=R(8) * t, lag=0.2)          # kuyruk karsi-denge yukari
    ears(-12 * t)                            # kulaklar pin
    rig.t_hand("R", 0, -0.040 * t, 0)        # sag pati one adim
keyed("atk_bite", 24, [
    (1, None),
    (7, lambda: (rig.spine(R(5)), rig.rot("neck", R(7)), rig.rot("head", R(5)),
                 rig.wloc("hips", 0, 0.012, 0.002), rig.tail(rz=R(6), lag=0.2), ears(8),
                 rig.t_hand("R", 0, -0.018, 0.018))),     # pati havada hazirlik
    (11, lambda: bite_strike(1.0, -9)),
    (13, lambda: bite_strike(0.88, 5)),
    (16, lambda: (rig.spine(-R(3)), rig.rot("neck", -R(6)), rig.rot("head", -R(2)),
                  rig.wloc("hips", 0, -0.022, 0), rig.tail(rx=-R(5), lag=0.25), ears(-4),
                  rig.t_hand("R", 0, -0.040, 0))),        # kuyruk overshoot asagi
    (20, lambda: (rig.tail(rx=R(2), lag=0.2), ears(3),
                  rig.t_hand("R", 0, -0.012, 0.008))),    # pati geri donuyor
    (24, None),
], [(1, (1, 1, 1, 1))])

# ============ atk_swipe: tam vucut coil + adim ============
def mk_swipe(side, other, sgn):
    infl = (0, 1, 1, 1) if side == "L" else (1, 0, 1, 1)
    def windup():
        rig.rot("root", 0, 0, R(10) * sgn)
        rig.spine(0, R(7) * sgn)
        rig.rot(f"upper_arm.{side}", R(14)); rig.rot(f"forearm.{side}", R(58)); rig.rot(f"hand.{side}", R(8))
        rig.rot("neck", 0, 0, R(6) * sgn)
        rig.wloc("hips", -0.010 * sgn, 0.006, 0.002)          # agirlik destek tarafina
        rig.t_foot(other, -0.012 * sgn, 0.005, 0)              # destek ayak genis bas
        rig.tail(rz=R(14) * sgn, lag=0.18)
        ears(6)
    def strike():
        rig.rot("root", 0, 0, -R(13) * sgn)
        rig.spine(0, -R(9) * sgn)
        rig.rot(f"upper_arm.{side}", -R(52)); rig.rot(f"forearm.{side}", R(26)); rig.rot(f"hand.{side}", -R(12))
        rig.rot("neck", 0, 0, -R(8) * sgn); rig.rot("head", 0, 0, -R(6) * sgn)
        rig.wloc("hips", 0.007 * sgn, -0.010, 0)
        rig.t_foot(other, -0.012 * sgn, 0.005, 0)
        rig.tail(rz=-R(16) * sgn, lag=0.22)
        ears(-10)
    def follow():
        rig.rot("root", 0, 0, -R(9) * sgn)
        rig.spine(0, -R(6) * sgn)
        rig.rot(f"upper_arm.{side}", -R(34)); rig.rot(f"forearm.{side}", R(34))
        rig.wloc("hips", 0.003 * sgn, -0.004, 0)
        rig.t_foot(other, -0.012 * sgn, 0.005, 0)
        rig.tail(rz=-R(22) * sgn, lag=0.3)                     # kuyruk overshoot
        ears(-4)
    keyed(f"atk_swipe_{side}", 20, [
        (1, None),
        (6, windup),
        (10, strike),
        (13, follow),
        (16, lambda: (rig.tail(rz=R(5) * sgn, lag=0.25), rig.t_foot(other, -0.006 * sgn, 0.002, 0))),
        (20, None),
    ], [(1, infl)])
mk_swipe("R", "L", -1.0)
mk_swipe("L", "R", 1.0)

# ============ atk_double_claw 30f: saha + kuyruk denge + hop ============
def rear(t, ua, fa, ha):
    rig.rot("hips", R(12) * t); rig.spine(R(46) * t); rig.rot("neck", -R(11) * t)
    rig.arms_fk(ua=ua, fa=fa, ha=ha)
    rig.wloc("hips", 0, 0.020 * t, 0.009 * t)
    rig.tail(rx=R(16) * t, lag=0.22)                # kuyruk yere bastirir (denge)
    ears(-8 * t)
keyed("atk_double_claw", 30, [
    (1, None),
    (9, lambda: rear(0.84, -R(60), R(48), -R(10))),
    (12, lambda: rear(1.0, -R(80), R(58), -R(18))),
    (16, lambda: (rig.rot("hips", -R(2)), rig.spine(-R(4)), rig.rot("neck", -R(10)),
                  rig.rot("head", -R(8)), rig.arms_fk(ua=R(18), fa=R(15), ha=-R(30)),
                  rig.wloc("hips", 0, -0.028, -0.014),
                  rig.t_foot("L", 0, -0.015, 0), rig.t_foot("R", 0, -0.015, 0),  # carpma ile one hop
                  rig.tail(rx=-R(12), lag=0.3), ears(-14))),
    (20, lambda: (rig.spine(R(5)), rig.rot("neck", -R(5)), rig.arms_fk(ua=R(8), fa=R(20), ha=-R(15)),
                  rig.wloc("hips", 0, -0.012, -0.006),
                  rig.t_foot("L", 0, -0.015, 0), rig.t_foot("R", 0, -0.015, 0),
                  rig.tail(rx=R(6), lag=0.25), ears(-4))),
    (25, lambda: (rig.t_foot("L", 0, -0.006, 0), rig.t_foot("R", 0, -0.006, 0),
                  rig.tail(rx=-R(2), lag=0.2))),
    (30, None),
], [(1, (0, 0, 1, 1))])

# ============ atk_pounce 32f ============
FWD = -0.085
def pounce_t(d, lift=0.0):
    rig.t_foot("L", 0, d, lift); rig.t_foot("R", 0, d, lift)
    rig.t_hand("L", 0, d - 0.01, lift); rig.t_hand("R", 0, d - 0.01, lift)
keyed("atk_pounce", 32, [
    (1, None),
    (9, lambda: (rig.spine(R(8)), rig.rot("neck", -R(4)),
                 rig.wloc("hips", 0, 0.012, -0.022), rig.tail(rz=R(8), rx=R(4), lag=0.2), ears(10))),
    (13, lambda: (rig.spine(-R(9)), rig.rot("neck", R(5)), legs_fk_tuck(-0.4),
                  rig.arms_fk(ua=-R(50), fa=R(10)), rig.wloc("hips", 0, -0.055, 0.055),
                  rig.tail(rx=-R(10), lag=0.25), ears(12), pounce_t(FWD))),
    (17, lambda: (rig.spine(-R(2)), rig.rot("neck", -R(8)), rig.rot("head", -R(8)),
                  rig.rot("snout", -R(7)), rig.arms_fk(fa=R(20)),
                  rig.wloc("hips", 0, FWD - 0.005, 0.004),
                  rig.tail(rx=R(4), lag=0.3), ears(-10), pounce_t(FWD))),
    (21, lambda: (rig.spine(R(7)), rig.rot("neck", -R(4)), rig.rot("snout", R(4)),
                  rig.wloc("hips", 0, FWD, -0.012),
                  rig.tail(rx=R(9), lag=0.32), ears(-6), pounce_t(FWD))),
    (26, lambda: (rig.spine(R(2)), rig.wloc("hips", 0, FWD * 0.4, -0.003),
                  rig.tail(rx=-R(3), lag=0.25), pounce_t(FWD * 0.4))),
    (32, None),
], [(1, (1, 1, 1, 1)), (11, (1, 1, 1, 1)), (14, (0, 0, 0, 0)), (16, (1, 1, 1, 1))])

# ============ atk_tail_whip 26f: kafa karsi + pati adimi ============
keyed("atk_tail_whip", 26, [
    (1, None),
    (7, lambda: (rig.rot("root", 0, 0, R(18)), rig.spine(0, R(10)), rig.tail(rz=R(26), lag=0.10),
                 rig.rot("neck", 0, 0, R(8)), rig.rot("head", 0, 0, -R(6)),
                 rig.wloc("hips", -0.008, 0.005, 0), ears(6))),
    (12, lambda: (rig.rot("root", 0, 0, -R(22)), rig.spine(0, -R(12)), rig.tail(rz=-R(20), lag=-0.05),
                  rig.rot("neck", 0, 0, -R(10)), rig.rot("head", 0, 0, R(14)),
                  rig.wloc("hips", 0.008, -0.005, 0), ears(-8),
                  rig.t_hand("L", 0.012, 0.008, 0.020))),     # sol pati kalkar
    (15, lambda: (rig.rot("root", 0, 0, -R(16)), rig.spine(0, -R(9)), rig.tail(rz=-R(34), lag=0.22),
                  rig.rot("neck", 0, 0, -R(6)), rig.rot("head", 0, 0, R(10)),
                  rig.wloc("hips", 0.005, 0, 0), ears(-10),
                  rig.t_hand("L", 0.015, 0.010, 0))),         # pati yere genis basar
    (19, lambda: (rig.rot("root", 0, 0, -R(6)), rig.spine(0, -R(3)), rig.tail(rz=-R(12), lag=0.10),
                  rig.t_hand("L", 0.015, 0.010, 0))),
    (23, lambda: (rig.tail(rz=R(6), lag=0.25), rig.t_hand("L", 0.006, 0.004, 0.008))),
    (26, None),
], [(1, (1, 1, 1, 1))])

# ============ atk_spin 28f: kafa lag + govde lean ============
def spin_pose(deg, head_lag, lean):
    rig.rot("root", 0, 0, R(deg))
    rig.arms_fk(ua=-R(8), fa=R(8))
    rig.tail(rz=R(26), lag=0.3)
    rig.spine(R(3), R(lean))
    rig.rot("neck", 0, 0, R(head_lag) * 0.4)
    rig.rot("head", 0, 0, R(head_lag))
    rig.wloc("hips", 0, 0, -0.010)
    ears(-8)
keyed("atk_spin", 28, [
    (1, None),
    (6, lambda: (rig.rot("root", 0, 0, -R(18)), rig.spine(0, -R(6)),
                 rig.rot("head", 0, 0, -R(12)), rig.tail(rz=-R(14), lag=0.2),
                 rig.wloc("hips", 0, 0, -0.010), ears(4))),
    (10, lambda: spin_pose(80, -22, 8)),
    (14, lambda: spin_pose(190, -28, 9)),
    (18, lambda: spin_pose(300, 18, 7)),
    (21, lambda: (rig.rot("root", 0, 0, R(360)), rig.rot("head", 0, 0, R(10)),
                  rig.tail(rz=R(14), lag=0.28), rig.wloc("hips", 0, 0, -0.005), ears(-4))),
    (25, lambda: (rig.rot("root", 0, 0, R(360)), rig.tail(rz=-R(5), lag=0.2))),
    (28, lambda: rig.rot("root", 0, 0, R(360))),
], [(1, (1, 1, 1, 1))])

# ============ atk_jump_slam 34f ============
keyed("atk_jump_slam", 34, [
    (1, None),
    (9, lambda: (rig.spine(R(7)), rig.rot("neck", -R(5)), rig.rot("head", R(8)),
                 rig.wloc("hips", 0, 0.010, -0.026), rig.tail(rz=R(6), lag=0.2), ears(10))),
    (14, lambda: (rig.spine(-R(11)), legs_fk_tuck(-0.4), rig.arms_fk(ua=-R(70), fa=R(40)),
                  rig.rot("neck", R(8)), rig.wloc("hips", 0, -0.006, 0.065),
                  rig.tail(rx=-R(14), lag=0.25), ears(8))),
    (18, lambda: (rig.spine(R(6)), rig.rot("neck", -R(6)), rig.rot("head", -R(6)),
                  legs_fk_tuck(0.3), rig.arms_fk(ua=-R(35), fa=R(30)),
                  rig.wloc("hips", 0, -0.016, 0.030), rig.tail(rx=-R(4), lag=0.3), ears(-6))),
    (21, lambda: (rig.spine(R(10)), rig.rot("neck", -R(8)), rig.rot("head", -R(6)),
                  rig.arms_fk(ua=R(20), fa=R(12), ha=-R(25)),
                  rig.wloc("hips", 0, -0.020, -0.020),
                  rig.tail(rx=R(12), lag=0.35), ears(-14))),
    (25, lambda: (rig.spine(R(6)), rig.arms_fk(ua=R(8), fa=R(18), ha=-R(10)),
                  rig.wloc("hips", 0, -0.010, -0.004),
                  rig.tail(rx=-R(5), lag=0.28), ears(-6))),
    (29, lambda: (rig.spine(R(2)), rig.wloc("hips", 0, -0.004, -0.001),
                  rig.tail(rx=R(2), lag=0.2))),
    (34, None),
], [(1, (1, 1, 1, 1)), (11, (1, 1, 1, 1)), (14, (0, 0, 0, 0)), (19, (0, 0, 0, 0)), (21, (1, 1, 1, 1))])

arm.animation_data.action = None
rig.reset()
for k, con in rig.ik_cons.items():
    con.influence = 1.0
for k, con in rig.rot_cons.items():
    con.influence = 1.0
bpy.ops.wm.save_as_mainfile(filepath="/tmp/rig/mouse_rig_td.blend")
print("ATTACKS v4 OK")
