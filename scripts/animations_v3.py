"""7 dongu v4 — TAM VUCUT koordinasyonu:
agirlik aktarimi (hips sway), kulak mikro, kuyruk faz-gecikmeli,
olculu gait (fare anatomisi), kafa stabilizasyonu."""
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

def sq(x):
    return max(0.0, math.sin(x))

def g1(p, c, w):
    return math.exp(-((p - c) / w) ** 2)

def sampled(name, nframes, fn, infl=(1, 1, 1, 1), step=2):
    def build(act):
        rig.reset()
        rig.key_influences(1, *infl)
        for f in range(1, nframes + 2, step):
            p = ((f - 1) % nframes) / nframes
            rig.reset()
            fn(p)
            rig.key_all(f)
        rig.reset()
        fn(0.0)
        rig.key_all(nframes + 1)
    AL.make_action(D, arm, name, nframes, build)

# ================ IDLE 96f ================
def idle(p):
    br = math.sin(TAU * 2 * p)
    rig.spine(R(3.0) * br)
    rig.rot("neck", R(0.8) * br)
    # ara sira yana bakis (tam vucut: kafa + kulaklar + hafif omuz)
    gl = g1(p, 0.52, 0.06) - g1(p, 0.62, 0.05) * 0.2
    rig.rot("head", R(2.0) * math.sin(TAU * p + 1.3), 0, R(14) * gl + R(2.0) * math.sin(TAU * p * 0.5))
    rig.rot("neck", 0, 0, R(7) * gl)
    rig.spine(0, R(2.5) * gl)
    f1 = g1(p, 0.22, 0.025)
    f2 = g1(p, 0.68, 0.03)
    rig.rot("ear.L", R(12) * f1 + R(6) * gl); rig.rot("ear_02.L", R(6) * f1)
    rig.rot("ear.R", R(10) * f2 + R(3) * gl, R(5) * f2)
    sn = g1(p, 0.35, 0.06) + g1(p, 0.85, 0.05)
    rig.rot("snout", R(3.5) * math.sin(TAU * 12 * p) * sn)
    rig.tail(rz=R(7) * math.sin(TAU * p - 0.8), lag=0.35)
    rig.wloc("hips", 0.002 * math.sin(TAU * p + 0.4), 0, 0.0012 * br)

sampled("idle", 96, idle)

# ================ WALK 32f: olculu gait + agirlik aktarimi ================
PH = {"footL": 0.0, "handL": 0.25, "footR": 0.5, "handR": 0.75}
def walk(p):
    yL, zL = AL.gait(p - PH["footL"], 0.085, 0.024)
    yR, zR = AL.gait(p - PH["footR"], 0.085, 0.024)
    rig.t_foot("L", 0, yL, zL); rig.t_foot("R", 0, yR, zR)
    yl, zl = AL.gait(p - PH["handL"], 0.075, 0.018)
    yr, zr = AL.gait(p - PH["handR"], 0.075, 0.018)
    rig.t_hand("L", 0, yl, zl); rig.t_hand("R", 0, yr, zr)
    for s, ph in (("L", PH["footL"]), ("R", PH["footR"])):
        th = TAU * ((p - ph) % 1.0)
        rig.rot(f"toes.{s}", -R(10) * sq(th + 2.7))
    sway = math.sin(TAU * p)
    # agirlik aktarimi: govde basan ayagin ustune kayar
    rig.wloc("hips", 0.0045 * math.sin(TAU * p + 2.2), 0, 0.0035 * abs(math.sin(TAU * 2 * p)))
    rig.rot("hips", 0, 0, R(2.5) * sway)
    rig.spine(R(2.2) * math.sin(TAU * 2 * p), R(-3.0) * sway)
    rig.rot("neck", R(2.0) * math.sin(TAU * 2 * p + 0.8))
    rig.rot("head", R(-2.2) * math.sin(TAU * 2 * p + 0.8), 0, R(-2.0) * sway)
    rig.rot("ear.L", R(2.5) * math.sin(TAU * 2 * p + 0.4))
    rig.rot("ear.R", R(2.5) * math.sin(TAU * 2 * p + 1.1))
    rig.tail(rz=R(-9) * math.sin(TAU * p - 0.5), rx=R(1.5) * math.sin(TAU * 2 * p + 1.6), lag=0.28)

sampled("walk", 32, walk, step=1)

# ================ RUN 14f: olculu bound ================
def run(p):
    yL, zL = AL.gait(p - 0.0, 0.105, 0.042)
    yR, zR = AL.gait(p - 0.05, 0.105, 0.042)
    rig.t_foot("L", 0, yL, zL); rig.t_foot("R", 0, yR, zR)
    yl, zl = AL.gait(p - 0.45, 0.095, 0.038)
    yr, zr = AL.gait(p - 0.49, 0.095, 0.038)
    rig.t_hand("L", 0, yl, zl); rig.t_hand("R", 0, yr, zr)
    flex = math.sin(TAU * p + 0.6)
    rig.rot("hips", R(5) * flex)
    rig.spine(R(14) * flex)
    rig.rot("spine_05", R(-3))
    rig.rot("neck", R(-5) * flex - R(3)); rig.rot("head", R(-3) * flex + R(2))
    rig.rot("ear.L", -R(9) + R(2) * flex); rig.rot("ear.R", -R(9) + R(2) * flex)  # kulaklar yatik
    rig.tail(rx=R(4) * math.sin(TAU * p - 1.4), lag=0.35)
    rig.wloc("hips", 0, 0, 0.009 * sq(TAU * p + 1.0) + 0.001)

sampled("run", 14, run, step=1)

# ================ SNIFF 72f ================
def sniff(p):
    if p < 0.18:
        dip = 0.5 - 0.5 * math.cos(math.pi * p / 0.18)
    elif p < 0.72:
        dip = 1.0
    else:
        dip = 0.5 + 0.5 * math.cos(math.pi * (p - 0.72) / 0.28)
    rig.rot("neck", R(-16) * dip); rig.rot("head", R(-18) * dip)
    rig.spine(R(8) * dip)
    rig.wloc("hips", 0, 0.004 * dip, -0.002 * dip)     # govde one meyil
    burst = 1.0 if 0.2 < p < 0.7 else 0.0
    rig.rot("snout", R(4.2) * math.sin(TAU * 14 * p) * burst * dip)
    rig.rot("ear.L", R(-8) * dip); rig.rot("ear.R", R(-8) * dip)
    yawk = R(8) * math.sin(TAU * 2 * p) * dip
    rig.rot("head", 0, 0, yawk)
    rig.rot("neck", 0, 0, yawk * 0.4)
    rig.tail(rz=R(2.5) * math.sin(TAU * p), rx=R(1.5) * dip, lag=0.3)

sampled("sniff", 72, sniff)

# ================ LOOK AROUND 120f ================
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
    rig.wloc("hips", -0.004 * yaw, 0, 0)               # bakilan yone agirlik
    rig.rot("spine_03", R(1.2) * math.sin(TAU * 3 * p))
    rig.tail(rz=R(-6) * yaw + R(2.0) * math.sin(TAU * 1.5 * p), lag=0.3)  # kuyruk karsi-denge

sampled("look_around", 120, look)

# ================ EAT 60f ================
def eat(p):
    rig.rot("hips", R(-4))
    rig.spine(R(23))
    rig.rot("neck", R(-8)); rig.rot("head", R(-26))
    nib = math.sin(TAU * 10 * p)
    rig.arms_fk(ua=-R(28), fa=R(40) + R(2.5) * nib, ha=-R(16) - R(2) * nib)  # patiler kemirmeyle oynar
    rig.rot("snout", R(3.0) * nib)
    rig.rot("head", R(1.2) * math.sin(TAU * 5 * p))
    rig.rot("ear.L", R(6) * math.sin(TAU * 2 * p)); rig.rot("ear.R", R(6) * math.sin(TAU * 2 * p + 1.5))
    rig.spine(R(0.8) * math.sin(TAU * 4 * p))
    rig.tail(rz=R(1.8) * math.sin(TAU * p), lag=0.3)
    rig.wloc("hips", 0, 0.004, -0.003)

sampled("eat", 60, eat, infl=(0, 0, 1, 1))

# ================ ALERT 48f ================
def alert(p):
    rig.rot("hips", R(-3))
    rig.spine(R(-14))
    rig.rot("neck", R(8)); rig.rot("head", R(4))
    rig.rot("ear.L", R(-14)); rig.rot("ear.R", R(-14))
    tr = math.sin(TAU * 9 * p)
    rig.rot("head", R(0.7) * tr, 0, R(0.9) * math.sin(TAU * 7 * p))
    rig.tail(rx=R(4), rz=R(0.8) * math.sin(TAU * 6 * p), lag=0.15)  # dik titrek kuyruk
    rig.wloc("hips", 0.0015 * math.sin(TAU * 5 * p), 0.002, 0.0015)

sampled("alert", 48, alert)

arm.animation_data.action = None
rig.reset()
for k, con in rig.ik_cons.items():
    con.influence = 1.0
for k, con in rig.rot_cons.items():
    con.influence = 1.0
bpy.ops.wm.save_as_mainfile(filepath="/tmp/rig/mouse_rig_td.blend")
print("LOOPS v4 OK")
