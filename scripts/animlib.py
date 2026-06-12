"""Animasyon yardimcilari: IK hedef suruculeri, influence keylama, FK pozlari."""
import sys, math
import numpy as np
sys.path.append("/tmp/rig/td"); sys.path.append("/tmp/rig")
import bpy
from mathutils import Vector

TAU = 2 * math.pi
R = math.radians

class Rig:
    def __init__(self, S):
        self.S = S
        self.arm = S.arm
        self.pb = self.arm.pose.bones
        # bone-lokal donusum matrisleri (dunya ofset -> pose.location)
        self.inv3 = {}
        for bn in ("hips", "ik_hand.L", "ik_hand.R", "ik_foot.L", "ik_foot.R"):
            self.inv3[bn] = self.arm.data.bones[bn].matrix_local.to_3x3().inverted()
        self.ik_cons = {}
        self.rot_cons = {}
        for side in "LR":
            self.ik_cons[f"hand.{side}"] = next(c for c in self.pb[f"forearm.{side}"].constraints if c.type == 'IK')
            self.ik_cons[f"foot.{side}"] = next(c for c in self.pb[f"shin.{side}"].constraints if c.type == 'IK')
            self.rot_cons[f"hand.{side}"] = self.pb[f"hand.{side}"].constraints["IKROT"]
            self.rot_cons[f"foot.{side}"] = self.pb[f"foot.{side}"].constraints["IKROT"]

    def reset(self):
        for b in self.pb:
            b.location = (0, 0, 0)
            b.rotation_mode = 'XYZ'
            b.rotation_euler = (0, 0, 0)
            b.scale = (1, 1, 1)

    def rot(self, bn, rx=0.0, ry=0.0, rz=0.0):
        b = self.pb[bn]
        b.rotation_mode = 'XYZ'
        e = b.rotation_euler
        b.rotation_euler = (e[0] + rx, e[1] + ry, e[2] + rz)

    def wloc(self, bn, wx=0.0, wy=0.0, wz=0.0):
        self.pb[bn].location = self.inv3[bn] @ Vector((wx, wy, wz))

    def spine(self, rx=0.0, rz=0.0):
        prof = (0.16, 0.21, 0.26, 0.21, 0.16)
        for k in range(5):
            self.rot(f"spine_{k+1:02d}", rx * prof[k], 0, rz * prof[k])

    def tail(self, rz=0.0, rx=0.0, lag=0.0):
        for i in range(1, 7):
            self.rot(f"tail_{i:02d}", rx, 0, rz * (1.0 + lag * i))

    def arms_fk(self, ua=0.0, fa=0.0, ha=0.0, side="LR"):
        for s in side:
            self.rot(f"upper_arm.{s}", ua)
            self.rot(f"forearm.{s}", fa)
            self.rot(f"hand.{s}", ha)

    # ---- IK hedefleri ----
    def t_hand(self, side, wx=0.0, wy=0.0, wz=0.0):
        self.wloc(f"ik_hand.{side}", wx, wy, wz)

    def t_foot(self, side, wx=0.0, wy=0.0, wz=0.0):
        self.wloc(f"ik_foot.{side}", wx, wy, wz)

    def key_all(self, f):
        for b in self.pb:
            b.keyframe_insert("rotation_euler", frame=f)
            b.keyframe_insert("location", frame=f)

    def key_influences(self, f, hand_L=1.0, hand_R=1.0, foot_L=1.0, foot_R=1.0):
        vals = {"hand.L": hand_L, "hand.R": hand_R, "foot.L": foot_L, "foot.R": foot_R}
        for k, v in vals.items():
            for con in (self.ik_cons[k], self.rot_cons[k]):
                con.influence = v
                con.keyframe_insert("influence", frame=f)

def gait(ph, S, L):
    """tekerlek yuruyusu: stance'ta geriye kayar (govde sabit), swing'de one tasinir"""
    th = TAU * (ph % 1.0)
    z = L * max(0.0, math.sin(th))
    y = (S / 2) * math.cos(th)
    return y, z

def make_action(D, arm, name, nframes, build, fake=True):
    old = D.actions.get(name)
    if old:
        D.actions.remove(old)
    act = D.actions.new(name)
    arm.animation_data.action = act
    build(act)
    act.use_fake_user = fake
    print(f"ACTION {name}: {nframes}f")
    return act
