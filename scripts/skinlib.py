"""TD skinning kutuphanesi — anatomiye duyarli bantli agirlik dagitimi.
Korleme blur YOK: her eklem icin smoothstep falloff bandi, bolge filtresi,
rijit bolge korumasi, capraz bulasma temizligi.
"""
import bpy, math
import numpy as np
from mathutils import Vector
from mathutils import kdtree
from mathutils.bvhtree import BVHTree
import sys
sys.path.append("/tmp/rig")
import plan_data as P

C, D = bpy.context, bpy.data

class Skin:
    def __init__(self, blend):
        bpy.ops.wm.open_mainfile(filepath=blend)
        self.mouse = D.objects["Mouse"]
        self.arm = D.objects["MouseRig"]
        self.me = self.mouse.data
        self.NV = len(self.me.vertices)
        self.pid = np.empty(self.NV, dtype=np.int32)
        self.me.attributes["part_id"].data.foreach_get("value", self.pid)
        self.IDS = {n: i for i, n in enumerate(P.MESH_RENAME.values())}
        co = np.empty(self.NV * 3)
        self.me.vertices.foreach_get("co", co)
        self.CO = co.reshape(self.NV, 3)
        self.load_weights()
        ne = len(self.me.edges)
        ev = np.empty(ne * 2, dtype=np.int32)
        self.me.edges.foreach_get("vertices", ev)
        self.EV = ev.reshape(ne, 2)
        self.rest_len = np.linalg.norm(self.CO[self.EV[:, 0]] - self.CO[self.EV[:, 1]], axis=1)
        self.wh_mask = (self.pid == self.IDS["whiskers_L"]) | (self.pid == self.IDS["whiskers_R"])
        for c in [c for b in self.arm.pose.bones for c in b.constraints if c.type == 'IK']:
            c.influence = 0.0

    def load_weights(self):
        gnames = {g.index: g.name for g in self.mouse.vertex_groups}
        self.GW = {gn: np.zeros(self.NV) for gn in gnames.values()}
        for v in self.me.vertices:
            for ge in v.groups:
                self.GW[gnames[ge.group]][v.index] = ge.weight

    def write_weights(self):
        self.mouse.vertex_groups.clear()
        for g, arr in self.GW.items():
            if arr.max() < 0.001:
                continue
            vg = self.mouse.vertex_groups.new(name=g)
            for vi in np.where(arr > 0.0004)[0]:
                vg.add([int(vi)], float(arr[vi]), 'REPLACE')

    def bone_pts(self, name):
        b = self.arm.data.bones[name]
        return np.array(b.head_local), np.array(b.tail_local)

    # ---- chain arclength parameter ----
    def chain_param(self, polyline, idx):
        """polyline: list of 3d pts; joint anchor = polyline[anchor_i] given separately.
        Returns (s, d): arclength param of closest point (from start), radial distance."""
        pts = self.CO[idx]
        segs = []
        acc = 0.0
        for a, b in zip(polyline, polyline[1:]):
            a = np.array(a); b = np.array(b)
            L = np.linalg.norm(b - a)
            segs.append((a, b, acc, L))
            acc += L
        best_s = np.zeros(len(idx))
        best_d = np.full(len(idx), 1e9)
        for a, b, s0, L in segs:
            ab = b - a
            t = np.clip(((pts - a) @ ab) / max(ab @ ab, 1e-12), 0, 1)
            proj = a + t[:, None] * ab[None]
            d = np.linalg.norm(pts - proj, axis=1)
            m = d < best_d
            best_d[m] = d[m]
            best_s[m] = s0 + t[m] * L
        return best_s, best_d

    @staticmethod
    def smoothstep(x):
        x = np.clip(x, 0, 1)
        return x * x * (3 - 2 * x)

    def band(self, A, B, width, sel, soft=1.0, falloff_to=None):
        """A: bone name or list (torso group), B: bone name.
        Joint = head of B. Band along chain [A_head .. B_head .. B_tail].
        sel: boolean mask of candidate verts. soft<1 -> partial redistribution.
        Redistributes (sumA + wB) across the band with smoothstep; A group scaled
        proportionally. Other influences untouched."""
        A_list = [A] if isinstance(A, str) else A
        hB, tB = self.bone_pts(B)
        hA, _ = self.bone_pts(A_list[0])
        poly = [hA, hB, tB]
        s, d = self.chain_param(poly, np.where(sel)[0])
        joint_s = np.linalg.norm(hB - hA)
        idx = np.where(sel)[0]
        inband = np.abs(s - joint_s) < width
        ii = idx[inband]
        if not len(ii):
            return 0
        f = self.smoothstep((s[inband] - joint_s + width) / (2 * width))
        wB = self.GW[B][ii]
        sumA = np.zeros(len(ii))
        for a in A_list:
            sumA += self.GW[a][ii]
        tot = sumA + wB
        newB = tot * f
        newB = wB + (newB - wB) * soft
        newA_total = tot - newB
        scale = np.where(sumA > 1e-9, newA_total / np.maximum(sumA, 1e-9), 0.0)
        for a in A_list:
            self.GW[a][ii] = self.GW[a][ii] * scale
        # if sumA was 0 but newA_total>0, give it to primary A bone
        zero_a = sumA <= 1e-9
        if zero_a.any():
            self.GW[A_list[0]][ii[zero_a]] += newA_total[zero_a]
        self.GW[B][ii] = newB
        return len(ii)

    def rigidify(self, bone, vidx, keep=None):
        """vidx verts -> 100% bone (or keep dict proportions)."""
        for g in self.GW:
            self.GW[g][vidx] = 0.0
        self.GW[bone][vidx] = 1.0

    def zero_groups(self, groups, vidx, renorm=True):
        for g in groups:
            if g in self.GW:
                self.GW[g][vidx] = 0.0
        if renorm:
            s = np.zeros(len(vidx))
            for g in self.GW:
                s += self.GW[g][vidx]
            bad = s <= 1e-9
            s[bad] = 1.0
            for g in self.GW:
                self.GW[g][vidx] = self.GW[g][vidx] / s

    def normalize(self, vidx=None):
        if vidx is None:
            vidx = np.arange(self.NV)
        s = np.zeros(len(vidx))
        for g in self.GW:
            s += self.GW[g][vidx]
        ok = s > 1e-9
        for g in self.GW:
            self.GW[g][vidx[ok]] = self.GW[g][vidx[ok]] / s[ok]

    # ---- island helpers ----
    def island(self, name):
        return np.where(self.pid == self.IDS[name])[0]

    # ---- pose & metrics ----
    def reset_pose(self):
        for b in self.arm.pose.bones:
            b.location = (0, 0, 0)
            b.rotation_mode = 'XYZ'
            b.rotation_euler = (0, 0, 0)
            b.scale = (1, 1, 1)

    def rot(self, bn, rx=0, ry=0, rz=0):
        pb = self.arm.pose.bones[bn]
        pb.rotation_mode = 'XYZ'
        pb.rotation_euler = (rx, ry, rz)

    def posed_coords(self):
        C.view_layer.update()
        dg = C.evaluated_depsgraph_get()
        mev = self.mouse.evaluated_get(dg)
        pc = np.empty(self.NV * 3)
        mev.data.vertices.foreach_get("co", pc)
        return pc.reshape(self.NV, 3)

    def stretch(self, mask):
        pc = self.posed_coords()
        plen = np.linalg.norm(pc[self.EV[:, 0]] - pc[self.EV[:, 1]], axis=1)
        ratio = plen / np.maximum(self.rest_len, 1e-9)
        em = mask[self.EV[:, 0]] & mask[self.EV[:, 1]]
        r = ratio[em]
        return float(np.quantile(r, 0.99)), float(r.max())

    def zone_mask(self, bones, thr=0.3):
        s = np.zeros(self.NV)
        for b in bones:
            if b in self.GW:
                s += self.GW[b]
        return (s > thr) & ~self.wh_mask

    def save(self, path):
        self.write_weights()
        bpy.ops.wm.save_as_mainfile(filepath=path)


# ---- render kit ----
def setup_render(samples=22, res=820):
    scene = C.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.render.resolution_x = res
    scene.render.resolution_y = res
    scene.view_settings.view_transform = 'AgX'
    world = D.worlds.new("W")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (1, 1, 1, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.85
    sun = D.objects.new("Sun", D.lights.new("S", 'SUN'))
    sun.data.energy = 2.3
    scene.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(50), math.radians(8), math.radians(35))
    return scene

def look_cam(name, loc, target, lens=70):
    cd = D.cameras.new(name)
    cd.lens = lens
    cam = D.objects.new(name, cd)
    C.scene.collection.objects.link(cam)
    cam.location = loc
    cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    return cam

def render(path, cam):
    C.scene.camera = cam
    C.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)

CAM_DEFS = {
    "arm_L":  ((0.52, -0.62, 0.28), (0.10, -0.19, 0.12), 70),
    "hind_R": ((-0.60, 0.52, 0.30), (-0.13, 0.08, 0.10), 70),
    "head":   ((0.52, -0.72, 0.50), (0.0, -0.27, 0.27), 70),
    "tail":   ((0.55, 0.70, 0.34), (0.03, 0.32, 0.06), 70),
    "body":   ((1.00, -0.40, 0.52), (0.0, 0.02, 0.22), 40),
    "ear_L":  ((0.42, -0.55, 0.62), (0.10, -0.24, 0.38), 85),
}
def make_cams():
    return {k: look_cam("cam_" + k, *v[:2], v[2]) for k, v in CAM_DEFS.items()}
