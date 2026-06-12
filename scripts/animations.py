"""Tarla faresi oyun animasyon seti — 7 seamless loop (24fps, in-place).
Faz-tabanli formul ornekleme => baslangic==bitis, kusursuz dongu."""
import sys, math
import numpy as np
sys.path.append("/tmp/rig/td"); sys.path.append("/tmp/rig")
import skinlib as SL
import bpy

S = SL.Skin("/tmp/rig/mouse_rig_td.blend")
C, D = bpy.context, bpy.data
arm = S.arm
R = math.radians
TAU = 2 * math.pi

for b in arm.pose.bones:
    for con in b.constraints:
        if con.type == 'IK':
            con.influence = 0.0

arm.animation_data_create()
# eski actionlari sil (dup onleme)
for nm in ("idle","walk","run","sniff","look_around","eat","alert"):
    old = D.actions.get(nm)
    if old:
        D.actions.remove(old)

def make_action(name, nframes, sampler, step=2):
    act = D.actions.new(name)
    arm.animation_data.action = act
    for f in range(1, nframes + 1, step):
        p = (f - 1) / nframes          # faz 0..1 (f=nframes+1 == f=1)
        S.reset_pose()
        sampler(p)
        for pb in arm.pose.bones:
            if any(abs(v) > 1e-6 for v in pb.rotation_euler) or any(abs(v) > 1e-6 for v in pb.location):
                pb.keyframe_insert("rotation_euler", frame=f)
                pb.keyframe_insert("location", frame=f)
    # dongu kapanisi: son kare = ilk kare
    S.reset_pose()
    sampler(0.0)
    for pb in arm.pose.bones:
        pb.keyframe_insert("rotation_euler", frame=nframes + 1)
        pb.keyframe_insert("location", frame=nframes + 1)
    act.use_fake_user = True
    print(f"ACTION {name}: {nframes}f")
    return act

def rot(bn, rx=0.0, ry=0.0, rz=0.0):
    pb = arm.pose.bones[bn]
    pb.rotation_mode = 'XYZ'
    e = pb.rotation_euler
    pb.rotation_euler = (e[0] + rx, e[1] + ry, e[2] + rz)

def loc(bn, x=0.0, y=0.0, z=0.0):
    pb = arm.pose.bones[bn]
    l = pb.location
    pb.location = (l[0] + x, l[1] + y, l[2] + z)

def spine(rx=0.0, rz=0.0):
    prof = (0.16, 0.21, 0.26, 0.21, 0.16)
    for k in range(5):
        rot(f"spine_{k+1:02d}", rx * prof[k], 0, rz * prof[k])

def sq(x):   # tek yonlu sinus (0..1)
    return max(0.0, math.sin(x))

# ---------------- IDLE (96f / 4s) ----------------
def idle(p):
    br = math.sin(TAU * 2 * p)                       # 2 nefes / dongu
    spine(R(3.0) * br)
    rot("neck", R(0.8) * br)
    rot("head", R(2.0) * math.sin(TAU * p + 1.3), 0, R(3.0) * math.sin(TAU * p * 0.5 + 0.4))
    # kulak segirmeleri (iki kisa flick)
    f1 = math.exp(-((p - 0.22) / 0.025) ** 2)
    f2 = math.exp(-((p - 0.68) / 0.03) ** 2)
    rot("ear.L", R(12) * f1); rot("ear_02.L", R(6) * f1)
    rot("ear.R", R(14) * f2, R(6) * f2)
    # burun koklama patlamalari (biyiklar snout'u takip eder)
    sn = (math.exp(-((p - 0.35) / 0.06) ** 2) + math.exp(-((p - 0.85) / 0.05) ** 2))
    rot("snout", R(3.5) * math.sin(TAU * 12 * p) * sn)
    # kuyruk ucu salinimi
    for i in range(1, 7):
        rot(f"tail_{i:02d}", 0, 0, R(2.2 + 0.9 * i) * math.sin(TAU * p - i * 0.55))
    loc("hips", 0, 0, 0.0012 * br)

# ---------------- WALK (32f) ----------------
def leg_hind(side, ph, A=1.0):
    c = math.cos(TAU * ph); s = math.sin(TAU * ph)
    rot(f"thigh.{side}", R(-17 * A) * c)
    rot(f"shin.{side}", R(-24 * A) * sq(TAU * ph))           # swing'de bukul
    rot(f"foot.{side}", R(13 * A) * sq(TAU * ph + 0.5) - R(4 * A) * c)
    rot(f"toes.{side}", R(-10 * A) * sq(TAU * ph + 2.6))

def leg_front(side, ph, A=1.0):
    c = math.cos(TAU * ph)
    rot(f"upper_arm.{side}", R(-20 * A) * c)
    rot(f"forearm.{side}", R(20 * A) * sq(TAU * ph))
    rot(f"hand.{side}", R(-12 * A) * sq(TAU * ph + 0.6) + R(5 * A) * c)

def walk(p):
    # lateral sekans: LH 0, LF .25, RH .5, RF .75
    leg_hind("L", p); leg_front("L", p - 0.25)
    leg_hind("R", p - 0.5); leg_front("R", p - 0.75)
    sway = math.sin(TAU * p)
    rot("hips", 0, 0, R(3.0) * sway)
    spine(R(2.4) * math.sin(TAU * 2 * p), R(-3.2) * sway)
    rot("neck", R(2.0) * math.sin(TAU * 2 * p + 0.8))
    rot("head", R(-2.2) * math.sin(TAU * 2 * p + 0.8), 0, R(-2.0) * sway)
    for i in range(1, 7):
        rot(f"tail_{i:02d}", 0, 0, R(-2.5 - 0.8 * i) * math.sin(TAU * p - i * 0.4))
    loc("hips", 0, 0, 0.003 * abs(math.sin(TAU * 2 * p)))

# ---------------- RUN / BOUND (14f) ----------------
def run(p):
    # arkalar birlikte faz 0, onler 0.45 — sicramali kosu
    leg_hind("L", p, 1.6); leg_hind("R", p + 0.04, 1.6)
    leg_front("L", p - 0.45, 1.5); leg_front("R", p - 0.41, 1.5)
    flex = math.sin(TAU * p + 0.6)
    rot("hips", R(6) * flex)
    spine(R(24) * flex)
    rot("spine_05", R(-4))            # hafif one egim
    rot("neck", R(-6) * flex - R(3)); rot("head", R(-4) * flex + R(2))
    for i in range(1, 7):
        rot(f"tail_{i:02d}", R(2.5) * math.sin(TAU * p - i * 0.5) - R(2.0), 0, 0)
    loc("hips", 0, 0, 0.008 * sq(TAU * p + 1.0) + 0.001)

# ---------------- SNIFF (72f) ----------------
def sniff(p):
    dip = 0.5 - 0.5 * math.cos(TAU * min(p / 0.18, 1.0)) if p < 0.18 else (1.0 if p < 0.72 else 0.5 - 0.5 * math.cos(TAU * (1 - (p - 0.72) / 0.28) / 2) if p < 1.0 else 0.0)
    dip = min(dip, 1.0)
    rot("neck", R(-16) * dip); rot("head", R(-18) * dip)
    spine(R(8) * dip)
    burst = 1.0 if 0.2 < p < 0.7 else 0.0
    rot("snout", R(4.2) * math.sin(TAU * 14 * p) * burst * dip)
    rot("ear.L", R(-8) * dip); rot("ear.R", R(-8) * dip)   # kulaklar one
    rot("head", 0, 0, R(8) * math.sin(TAU * 2 * p) * dip)  # saga sola kokla
    for i in range(1, 7):
        rot(f"tail_{i:02d}", 0, 0, R(1.5) * math.sin(TAU * p - i * 0.5))

# ---------------- LOOK AROUND (120f) ----------------
def look(p):
    # 0-.2 sola don, .2-.35 tut, .35-.5 merkez, .5-.7 saga, .7-.85 tut, .85-1 merkez
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
    rot("neck", 0, 0, R(20) * yaw)
    rot("head", R(-3) * abs(yaw), 0, R(26) * yaw)
    rot("ear.L", R(10) * max(yaw, 0) + R(4) * abs(yaw))
    rot("ear.R", R(10) * max(-yaw, 0) + R(4) * abs(yaw))
    spine(0, R(10) * yaw)
    br = math.sin(TAU * 3 * p)
    rot("spine_03", R(1.2) * br)
    for i in range(1, 7):
        rot(f"tail_{i:02d}", 0, 0, R(2.0) * math.sin(TAU * 1.5 * p - i * 0.5))

# ---------------- EAT (60f) ----------------
def eat(p):
    sit = 1.0  # tum dongu oturur (giris/cikis oyun tarafinda blend)
    rot("hips", R(-4) * sit)
    spine(R(23) * sit)
    rot("neck", R(-8) * sit); rot("head", R(-26) * sit)
    rot("upper_arm.L", R(-28) * sit); rot("forearm.L", R(40) * sit); rot("hand.L", R(-16) * sit)
    rot("upper_arm.R", R(-28) * sit); rot("forearm.R", R(40) * sit); rot("hand.R", R(-16) * sit)
    nib = math.sin(TAU * 10 * p)
    rot("snout", R(3.0) * nib)
    rot("head", R(1.2) * math.sin(TAU * 5 * p))
    rot("ear.L", R(6) * math.sin(TAU * 2 * p)); rot("ear.R", R(6) * math.sin(TAU * 2 * p + 1.5))
    for i in range(1, 7):
        rot(f"tail_{i:02d}", 0, 0, R(1.2) * math.sin(TAU * p - i * 0.5))

# ---------------- ALERT (48f) ----------------
def alert(p):
    up = 1.0
    rot("hips", R(-3) * up)
    spine(R(-16) * up)          # govde dikles
    rot("neck", R(8) * up); rot("head", R(4) * up)
    rot("ear.L", R(-14) * up); rot("ear.R", R(-14) * up)   # kulaklar dimdik
    tr = math.sin(TAU * 9 * p)
    rot("head", R(0.7) * tr, 0, R(0.9) * math.sin(TAU * 7 * p))
    for i in range(1, 7):
        rot(f"tail_{i:02d}", R(1.5), 0, R(0.8) * math.sin(TAU * 2 * p - i * 0.4))

ACTIONS = [("idle", 96, idle), ("walk", 32, walk), ("run", 14, run),
           ("sniff", 72, sniff), ("look_around", 120, look),
           ("eat", 60, eat), ("alert", 48, alert)]
for nm, nf, fn in ACTIONS:
    make_action(nm, nf, fn, step=2)

arm.animation_data.action = None
S.reset_pose()
bpy.ops.wm.save_as_mainfile(filepath="/tmp/rig/mouse_rig_td.blend")
print("ANIMS OK")
