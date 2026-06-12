# Canonical rig plan for the mouse model — single source of truth.
# All coordinates in CENTERED space: mesh shifted by +0.035 in X so the
# sagittal midline sits at x=0. Ground plane at z=0. Nose toward -Y.
import math
import colorsys

MESH_SHIFT_X = 0.035  # applied to ParentNode / mesh data before rigging

# Tail centerline knots extracted from tripo_part_9 geometry (centered space)
TAIL_KNOTS = [
    (0.000, 0.295, 0.062),
    (0.004, 0.356, 0.035),
    (0.018, 0.392, 0.033),
    (0.037, 0.423, 0.032),
    (0.061, 0.447, 0.033),
    (0.093, 0.462, 0.030),
    (0.126, 0.474, 0.032),
    (0.166, 0.483, 0.030),
    (0.227, 0.480, 0.025),
    (0.293, 0.466, 0.024),
    (0.321, 0.463, 0.023),
]

def resample(knots, n):
    d = [0.0]
    for a, b in zip(knots, knots[1:]):
        d.append(d[-1] + math.dist(a, b))
    total = d[-1]
    out = []
    for i in range(n + 1):
        t = total * i / n
        for j in range(len(knots) - 1):
            if d[j + 1] >= t or j == len(knots) - 2:
                seg = d[j + 1] - d[j] or 1e-9
                f = min(max((t - d[j]) / seg, 0.0), 1.0)
                out.append(tuple(knots[j][k] + (knots[j + 1][k] - knots[j][k]) * f for k in range(3)))
                break
    return out

_T = resample(TAIL_KNOTS, 6)

def _mirror(p):
    return (-p[0], p[1], p[2])

# name: (head, tail, parent, group, deform)
BONES = {}

def _add(name, head, tail, parent, group, deform=True):
    BONES[name] = dict(head=head, tail=tail, parent=parent, group=group, deform=deform)

_add("root",      (0, 0.000, 0.000), (0, 0.140, 0.000), None, "core", deform=False)
_add("hips",      (0, 0.245, 0.225), (0, 0.135, 0.297), "root", "core")
_add("spine_01",  (0, 0.135, 0.297), (0, 0.005, 0.325), "hips", "core")
_add("spine_02",  (0, 0.005, 0.325), (0, -0.115, 0.302), "spine_01", "core")
_add("neck",      (0, -0.115, 0.302), (0, -0.205, 0.287), "spine_02", "core")
_add("head",      (0, -0.205, 0.287), (0, -0.345, 0.258), "neck", "head")
_add("snout",     (0, -0.345, 0.258), (0, -0.472, 0.220), "head", "head")

_add("ear.L",     (0.096, -0.250, 0.317), (0.124, -0.236, 0.435), "head", "ear")
_add("ear.R",     _mirror((0.096, -0.250, 0.317)), _mirror((0.124, -0.236, 0.435)), "head", "ear")
_add("whisker.L", (0.048, -0.442, 0.222), (0.098, -0.467, 0.228), "snout", "whisker")
_add("whisker.R", _mirror((0.048, -0.442, 0.222)), _mirror((0.098, -0.467, 0.228)), "snout", "whisker")

_FRONT_L = [
    ("shoulder",   (0.050, -0.150, 0.298), (0.112, -0.205, 0.228)),
    ("upper_arm",  (0.112, -0.205, 0.228), (0.108, -0.180, 0.085)),
    ("forearm",    (0.108, -0.180, 0.085), (0.118, -0.207, 0.045)),
    ("hand",       (0.118, -0.207, 0.045), (0.1095, -0.287, 0.016)),
    ("front_toes", (0.1095, -0.287, 0.016), (0.101, -0.328, 0.007)),
]
_HIND_L = [
    ("thigh", (0.105, 0.165, 0.235), (0.150, 0.048, 0.125)),
    ("shin",  (0.150, 0.048, 0.125), (0.112, 0.156, 0.043)),
    ("foot",  (0.112, 0.156, 0.043), (0.1445, 0.0035, 0.014)),
    ("toes",  (0.1445, 0.0035, 0.014), (0.145, -0.0315, 0.006)),
]

for side, mir, grp in (("L", False, "legL"), ("R", True, "legR")):
    prev = "spine_02"
    for nm, h, t in _FRONT_L:
        h2, t2 = (h, t) if not mir else (_mirror(h), _mirror(t))
        _add(f"{nm}.{side}", h2, t2, prev if prev == "spine_02" else f"{prev}.{side}", grp)
        prev = nm
    prev = "hips"
    for nm, h, t in _HIND_L:
        h2, t2 = (h, t) if not mir else (_mirror(h), _mirror(t))
        _add(f"{nm}.{side}", h2, t2, prev if prev == "hips" else f"{prev}.{side}", grp)
        prev = nm

for i in range(6):
    _add(f"tail_{i+1:02d}", _T[i], _T[i + 1], "hips" if i == 0 else f"tail_{i:02d}", "tail")

GROUP_COLORS = {
    "core":    (0.12, 0.38, 1.00),
    "head":    (1.00, 0.72, 0.05),
    "ear":     (0.00, 0.85, 0.95),
    "whisker": (0.95, 0.25, 0.90),
    "legL":    (0.10, 0.80, 0.18),
    "legR":    (0.95, 0.18, 0.10),
    "tail":    (0.62, 0.30, 0.95),
}

# Per-bone distinct colors for the weight-zone preview
_GROUP_HUE = {"core": 0.60, "head": 0.11, "ear": 0.50, "whisker": 0.86,
              "legL": 0.33, "legR": 0.015, "tail": 0.74}

def zone_colors():
    by_group = {}
    for n, b in BONES.items():
        if not b["deform"]:
            continue
        by_group.setdefault(b["group"], []).append(n)
    out = {}
    for g, names in by_group.items():
        names.sort()
        n = len(names)
        for i, nm in enumerate(names):
            h = (_GROUP_HUE[g] + 0.035 * (i % 3) - 0.02) % 1.0
            v = 0.45 + 0.5 * (i / max(n - 1, 1))
            s = 0.95 - 0.25 * ((i // 3) % 2)
            out[nm] = colorsys.hsv_to_rgb(h, s, v)
    return out

# Heat-falloff-ish dominance radii for the zone preview (bigger = wins more)
RADIUS = {
    "hips": 2.6, "spine_01": 2.8, "spine_02": 2.6, "neck": 1.8,
    "head": 2.2, "snout": 1.7,
    "shoulder.L": 1.1, "shoulder.R": 1.1,
    "upper_arm.L": 1.5, "upper_arm.R": 1.5,
    "forearm.L": 1.0, "forearm.R": 1.0,
    "hand.L": 0.9, "hand.R": 0.9,
    "front_toes.L": 0.8, "front_toes.R": 0.8,
    "thigh.L": 2.0, "thigh.R": 2.0,
    "shin.L": 1.4, "shin.R": 1.4,
    "foot.L": 1.0, "foot.R": 1.0,
    "toes.L": 0.8, "toes.R": 0.8,
}
def radius(n):
    return RADIUS.get(n, 1.0)

# Which deform bones each mesh is allowed to bind to
MESH_BONES = {
    "tripo_part_6": [n for n, b in BONES.items() if b["deform"] and b["group"] not in ("ear", "whisker")],
    "tripo_part_4": ["ear.L"], "tripo_part_5": ["ear.R"],
    "tripo_part_0": ["whisker.L"], "tripo_part_1": ["whisker.R"],
    "tripo_part_3": ["hand.L", "front_toes.L"], "tripo_part_2": ["hand.R", "front_toes.R"],
    "tripo_part_8": ["foot.L", "toes.L"], "tripo_part_7": ["foot.R", "toes.R"],
    "tripo_part_9": [f"tail_{i:02d}" for i in range(1, 7)],
}

# For the real binding step (auto weights), allow blending into neighbours:
BIND_BONES = {
    "tripo_part_6": MESH_BONES["tripo_part_6"],
    "tripo_part_4": ["ear.L", "head"], "tripo_part_5": ["ear.R", "head"],
    "tripo_part_0": ["whisker.L", "snout"], "tripo_part_1": ["whisker.R", "snout"],
    "tripo_part_3": ["forearm.L", "hand.L", "front_toes.L"],
    "tripo_part_2": ["forearm.R", "hand.R", "front_toes.R"],
    "tripo_part_8": ["shin.L", "foot.L", "toes.L"],
    "tripo_part_7": ["shin.R", "foot.R", "toes.R"],
    "tripo_part_9": [f"tail_{i:02d}" for i in range(1, 7)] + ["hips"],
}

MESH_RENAME = {
    "tripo_part_0": "whiskers_L", "tripo_part_1": "whiskers_R",
    "tripo_part_2": "paw_front_R", "tripo_part_3": "paw_front_L",
    "tripo_part_4": "ear_L", "tripo_part_5": "ear_R",
    "tripo_part_6": "body", "tripo_part_7": "foot_hind_R",
    "tripo_part_8": "foot_hind_L", "tripo_part_9": "tail",
}
