"""7 dongu — IK zemin temasli yeniden yazim.
Bacaklar IK hedefli (sifir kayma, sifir gomulme); govde/kuyruk/kafa FK."""
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
TAU = AL.TAU
arm.animation_data_create()
import math

def sq(x):
    return max(0.0, math.sin(x))

def sampled(name, nframes, fn, infl=(1, 1, 1, 1), step=2):
    def build(act):
        rig.reset()
        rig.key_influences(1, *infl)
        for f in range(1, nframes + 2, step):
            p = ((f - 1) % nframes) / nframes
            rig.reset()
            fn(p)
            rig.key_all(f)
        if (nframes % step) != 0 or True:
            rig.reset()
            fn(0.0)
            rig.key_all(nframes + 1)
    AL.make_action(D, arm, name, nframes, build)

# ---------------- IDLE 96f: ayaklar sabit, govde nefes ----------------
def idle(p):
    br = math.sin(TAU * 2 * p)
    rig.spine(R(3.0) * br)
    rig.rot("neck", R(0.8) * br)
    rig.rot("head", R(2.0) * math.sin(TAU * p + 1.3), 0, R(3.0) * math.sin(TAU * p * 0.5 + 0.4))
    f1 = math.exp(-((p - 0.22) / 0.025) ** 2)
    f2 = math.exp(-((p - 0.68) / 0.03) ** 2)
    rig.rot("ear.L", R(12) * f1); rig.rot("ear_02.L", R(6) * f1)
    rig.rot("ear.R", R(10) * f2, R(5) * f2)
    sn = (math.exp(-((p - 0.35) / 0.06) ** 2) + math.exp(-((p - 0.85) / 0.05) ** 2))
    rig.rot("snout", R(3.5) * math.sin(TAU * 12 * p) * sn)
    rig.tail(rz=R(7) * math.sin(TAU * p - 0.8), lag=0.35)
    rig.wloc("hips", 0, 0, 0.0012 * br)
    # hedefler sabit (0,0,0) -> dizler bob'u emer

sampled("idle", 96, idle)

# ---------------- WALK 32f: tekerlek gait IK ----------------
PH = {"footL": 0.0, "handL": 0.25, "footR": 0.5, "handR": 0.75}
def walk(p):
    yL, zL = AL.gait(p - PH["footL"], 0.095, 0.026)
    yR, zR = AL.gait(p - PH["footR"], 0.095, 0.026)
    rig.t_foot("L", 0, yL, zL); rig.t_foot("R", 0, yR, zR)
    yl, zl = AL.gait(p - PH["handL"], 0.085, 0.020)
    yr, zr = AL.gait(p - PH["handR"], 0.085, 0.020)
    rig.t_hand("L", 0, yl, zl); rig.t_hand("R", 0, yr, zr)
    # parmak aksani (foot/hand IKROT kilitli; toes serbest)
    for s, ph in (("L", PH["footL"]), ("R", PH["footR"])):
        th = TAU * ((p - ph) % 1.0)
        rig.rot(f"toes.{s}", -R(10) * sq(th + 2.7))
    sway = math.sin(TAU * p)
    rig.rot("hips", 0, 0, R(2.5) * sway)
    rig.spine(R(2.2) * math.sin(TAU * 2 * p), R(-3.0) * sway)
    rig.rot("neck", R(2.0) * math.sin(TAU * 2 * p + 0.8))
    rig.rot("head", R(-2.2) * math.sin(TAU * 2 * p + 0.8), 0, R(-2.0) * sway)
    rig.tail(rz=R(-9) * math.sin(TAU * p - 0.5), lag=0.25)
    rig.wloc("hips", 0, 0, 0.0035 * abs(math.sin(TAU * 2 * p)))

sampled("walk", 32, walk, step=1)

# ---------------- RUN 14f: bound, havada kisa faz ----------------
def run(p):
    yL, zL = AL.gait(p - 0.0, 0.15, 0.052)
    yR, zR = AL.gait(p - 0.05, 0.15, 0.052)
    rig.t_foot("L", 0, yL, zL); rig.t_foot("R", 0, yR, zR)
    yl, zl = AL.gait(p - 0.45, 0.13, 0.045)
    yr, zr = AL.gait(p - 0.49, 0.13, 0.045)
    rig.t_hand("L", 0, yl, zl); rig.t_hand("R", 0, yr, zr)
    flex = math.sin(TAU * p + 0.6)
    rig.rot("hips", R(6) * flex)
    rig.spine(R(22) * flex)
    rig.rot("spine_05", R(-4))
    rig.rot("neck", R(-6) * flex - R(3)); rig.rot("head", R(-4) * flex + R(2))
    rig.tail(rx=R(2.5) * math.sin(TAU * p - 1.2), lag=0.3)
    rig.wloc("hips", 0, 0, 0.010 * sq(TAU * p + 1.0) + 0.001)

sampled("run", 14, run, step=1)

# ---------------- SNIFF 72f ----------------
def sniff(p):
    if p < 0.18:
        dip = 0.5 - 0.5 * math.cos(math.pi * p / 0.18)
    elif p < 0.72:
        dip = 1.0
    else:
        dip = 0.5 + 0.5 * math.cos(math.pi * (p - 0.72) / 0.28)
    rig.rot("neck", R(-16) * dip); rig.rot("head", R(-18) * dip)
    rig.spine(R(8) * dip)
    burst = 1.0 if 0.2 < p < 0.7 else 0.0
    rig.rot("snout", R(4.2) * math.sin(TAU * 14 * p) * burst * dip)
    rig.rot("ear.L", R(-8) * dip); rig.rot("ear.R", R(-8) * dip)
    rig.rot("head", 0, 0, R(8) * math.sin(TAU * 2 * p) * dip)
    rig.tail(rz=R(1.5) * math.sin(TAU * p))

sampled("sniff", 72, sniff)

# ---------------- LOOK AROUND 120f ----------------
def look(p):
    def ease(t):
        return 0.5 - 0.5 * math.cos(math.pi * min(max(t, 0), 1))
    if p < 0.2:
        yaw = ease(p / 0.2)
    elif p < 0.35:
        yaw = 1.0
    elif p < 0.5:
        yaw = 1.0 - ease((p - 0.35) / 0.15)
    elif p < 0.7:
        yaw = -ease((p - 0.5) / 0.2)
    elif p < 0.85:
        yaw = -1.0
    else:
        yaw = -(1.0 - ease((p - 0.85) / 0.15))
    rig.rot("neck", 0, 0, R(20) * yaw)
    rig.rot("head", R(-3) * abs(yaw), 0, R(26) * yaw)
    rig.rot("ear.L", R(10) * max(yaw, 0) + R(4) * abs(yaw))
    rig.rot("ear.R", R(10) * max(-yaw, 0) + R(4) * abs(yaw))
    rig.spine(0, R(10) * yaw)
    rig.rot("spine_03", R(1.2) * math.sin(TAU * 3 * p))
    rig.tail(rz=R(2.0) * math.sin(TAU * 1.5 * p), lag=0.3)

sampled("look_around", 120, look)

# ---------------- EAT 60f: arka IK sabit, kollar FK ----------------
def eat(p):
    rig.rot("hips", R(-4))
    rig.spine(R(23))
    rig.rot("neck", R(-8)); rig.rot("head", R(-26))
    rig.arms_fk(ua=-R(28), fa=R(40), ha=-R(16))
    rig.rot("snout", R(3.0) * math.sin(TAU * 10 * p))
    rig.rot("head", R(1.2) * math.sin(TAU * 5 * p))
    rig.rot("ear.L", R(6) * math.sin(TAU * 2 * p)); rig.rot("ear.R", R(6) * math.sin(TAU * 2 * p + 1.5))
    rig.tail(rz=R(1.2) * math.sin(TAU * p))
    rig.wloc("hips", 0, 0.004, -0.003)

sampled("eat", 60, eat, infl=(0, 0, 1, 1))

# ---------------- ALERT 48f ----------------
def alert(p):
    rig.rot("hips", R(-3))
    rig.spine(R(-14))
    rig.rot("neck", R(8)); rig.rot("head", R(4))
    rig.rot("ear.L", R(-14)); rig.rot("ear.R", R(-14))
    rig.rot("head", R(0.7) * math.sin(TAU * 9 * p), 0, R(0.9) * math.sin(TAU * 7 * p))
    rig.tail(rx=R(1.5), rz=R(0.8) * math.sin(TAU * 2 * p), lag=0.3)
    rig.wloc("hips", 0, 0.002, 0.0015)

sampled("alert", 48, alert)

arm.animation_data.action = None
rig.reset()
# rig varsayilani: IK acik
rig.key_influences  # (sadece aksiyonlarda keylendi)
for k, con in rig.ik_cons.items():
    con.influence = 1.0
bpy.ops.wm.save_as_mainfile(filepath="/tmp/rig/mouse_rig_td.blend")
print("LOOPS v3 OK")
