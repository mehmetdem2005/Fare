# Canonical rig plan for the mouse model — v2 (user feedback applied).
# All coordinates in CENTERED space: mesh shifted by +0.035 in X so the
# sagittal midline sits at x=0. Ground plane at z=0. Nose toward -Y.
#
# v2 changes:
#  - whisker bones removed (whiskers bound 100% to snout, never move alone)
#  - spine rebuilt: follows dorsal arc naturally, +spine_03; hips descends to tail root
#  - front leg rebuilt: anatomical scapula/humerus/radius proportions, elbow tucked
#  - all chain tips pulled inside the mesh (containment enforced at build time)
import math
import colorsys

MESH_SHIFT_X = 0.035

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
    (0.314, 0.464, 0.0235),   # pulled inside (mesh tip 0.321)
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

BONES = {}

def _add(name, head, tail, parent, group, deform=True, connect=False):
    BONES[name] = dict(head=head, tail=tail, parent=parent, group=group,
                       deform=deform, connect=connect)

# ---- core: spine follows dorsal arc ~0.075 below back surface ----
_add("root",     (0, 0.000, 0.000), (0, 0.140, 0.000), None, "core", deform=False)
_add("hips",     (0, 0.215, 0.310), (0, 0.292, 0.075), "root", "core")   # sacrum -> tail root
_add("spine_01", (0, 0.215, 0.310), (0, 0.105, 0.352), "hips", "core")
_add("spine_02", (0, 0.105, 0.352), (0, -0.010, 0.356), "spine_01", "core", connect=True)
_add("spine_03", (0, -0.010, 0.356), (0, -0.120, 0.318), "spine_02", "core", connect=True)
_add("neck",     (0, -0.120, 0.318), (0, -0.205, 0.295), "spine_03", "core", connect=True)
_add("head",     (0, -0.205, 0.295), (0, -0.345, 0.270), "neck", "head", connect=True)
_add("snout",    (0, -0.345, 0.270), (0, -0.468, 0.224), "head", "head", connect=True)

# NOTE: ear bones are auto-fitted to the ear shell medial line at build time
# (2-3 segment chain, containment-verified) — not statically defined here.

# ---- legs (anatomical: scapula along ribcage, elbow tucked back, knee forward) ----
_FRONT_L = [
    ("shoulder",   (0.045, -0.115, 0.315), (0.103, -0.195, 0.210)),
    ("upper_arm",  (0.103, -0.195, 0.210), (0.112, -0.152, 0.094)),
    ("forearm",    (0.112, -0.152, 0.094), (0.120, -0.203, 0.047)),
    ("hand",       (0.120, -0.203, 0.047), (0.111, -0.284, 0.017)),
    ("front_toes", (0.111, -0.284, 0.017), (0.102, -0.320, 0.010)),
]
_HIND_L = [
    ("thigh", (0.103, 0.168, 0.235), (0.148, 0.050, 0.122)),
    ("shin",  (0.148, 0.050, 0.122), (0.112, 0.152, 0.034)),
    ("foot",  (0.112, 0.152, 0.034), (0.1435, 0.006, 0.0125)),
    ("toes",  (0.1435, 0.006, 0.0125), (0.144, -0.027, 0.0075)),
]

for side, mir, grp in (("L", False, "legL"), ("R", True, "legR")):
    prev = None
    for k, (nm, h, t) in enumerate(_FRONT_L):
        h2, t2 = (h, t) if not mir else (_mirror(h), _mirror(t))
        parent = "spine_03" if k == 0 else f"{prev}.{side}"
        _add(f"{nm}.{side}", h2, t2, parent, grp, connect=(k >= 2))
        prev = nm
    prev = None
    for k, (nm, h, t) in enumerate(_HIND_L):
        h2, t2 = (h, t) if not mir else (_mirror(h), _mirror(t))
        parent = "hips" if k == 0 else f"{prev}.{side}"
        _add(f"{nm}.{side}", h2, t2, parent, grp, connect=(k >= 1))
        prev = nm

for i in range(6):
    _add(f"tail_{i+1:02d}", _T[i], _T[i + 1], "hips" if i == 0 else f"tail_{i:02d}",
         "tail", connect=(i >= 1))

GROUP_COLORS = {
    "core": (0.12, 0.38, 1.00),
    "head": (1.00, 0.72, 0.05),
    "ear":  (0.00, 0.85, 0.95),
    "legL": (0.10, 0.80, 0.18),
    "legR": (0.95, 0.18, 0.10),
    "tail": (0.62, 0.30, 0.95),
}

# Roll hints: bone local +Z aimed at this world direction (hinge => local X)
ROLL_TARGET = {}
for n, b in BONES.items():
    g = b["group"]
    if g in ("legL", "legR"):
        ROLL_TARGET[n] = (0, -1, 0)     # Z forward => X = world X (sagittal hinge)
    else:
        ROLL_TARGET[n] = (0, 0, 1)      # Z up
ROLL_TARGET["hips"] = (0, 0, 1)

# ---- binding spec: which bones each ORIGINAL part may bind to (bone heat) ----
ALL_DEFORM = [n for n, b in BONES.items() if b["deform"]]
BIND = {
    "tripo_part_6": [n for n in ALL_DEFORM if BONES[n]["group"] != "ear"],   # body
    "tripo_part_4": ["ear.L", "head"],
    "tripo_part_5": ["ear.R", "head"],
    "tripo_part_3": ["forearm.L", "hand.L", "front_toes.L"],
    "tripo_part_2": ["forearm.R", "hand.R", "front_toes.R"],
    "tripo_part_8": ["shin.L", "foot.L", "toes.L"],
    "tripo_part_7": ["shin.R", "foot.R", "toes.R"],
    "tripo_part_9": [f"tail_{i:02d}" for i in range(1, 7)] + ["hips"],
    # whiskers: rigid, no heat — direct 100% snout
    "tripo_part_0": ["snout"],
    "tripo_part_1": ["snout"],
}
RIGID = {"tripo_part_0": "snout", "tripo_part_1": "snout"}

# parts whose rim (near-body verts) gets weights sampled FROM the body field
WELD_TO_BODY = ["tripo_part_3", "tripo_part_2", "tripo_part_8", "tripo_part_7", "tripo_part_9"]
WELD_DIST = 0.008

MESH_RENAME = {
    "tripo_part_0": "whiskers_L", "tripo_part_1": "whiskers_R",
    "tripo_part_2": "paw_front_R", "tripo_part_3": "paw_front_L",
    "tripo_part_4": "ear_L", "tripo_part_5": "ear_R",
    "tripo_part_6": "body", "tripo_part_7": "foot_hind_R",
    "tripo_part_8": "foot_hind_L", "tripo_part_9": "tail",
}

# ---- IK setup (control bones, non-deform, .blend only) ----
IK = {
    "front": dict(chain=("upper_arm", "forearm"), target_at="hand", pole_off=(0, 0.10, 0.01)),
    "hind":  dict(chain=("thigh", "shin"), target_at="foot", pole_off=(0, -0.12, 0.02)),
}
