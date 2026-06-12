import bpy, numpy as np
from mathutils import Vector

bpy.ops.wm.open_mainfile(filepath="/tmp/rig/mouse_imported.blend")

def verts(name):
    ob = bpy.data.objects[name]
    n = len(ob.data.vertices)
    a = np.empty(n * 3)
    ob.data.vertices.foreach_get("co", a)
    a = a.reshape(n, 3)
    # apply world matrix
    M = np.array(ob.matrix_world)
    h = np.c_[a, np.ones(n)]
    return (h @ M.T)[:, :3]

body = verts("tripo_part_6")
print(f"BODY n={len(body)} X[{body[:,0].min():.3f},{body[:,0].max():.3f}] Y[{body[:,1].min():.3f},{body[:,1].max():.3f}] Z[{body[:,2].min():.3f},{body[:,2].max():.3f}]")

nose = body[body[:, 1].argmin()]
print(f"NOSE_TIP ({nose[0]:.4f},{nose[1]:.4f},{nose[2]:.4f})")

# --- spine centerline: Y bins on near-midline verts ---
mid = body[np.abs(body[:, 0]) < 0.06]
print("\nSPINE_CENTERLINE (Y-bin: meanX meanZ minZ maxZ n)")
for y0 in np.arange(-0.50, 0.35, 0.05):
    s = mid[(mid[:, 1] >= y0) & (mid[:, 1] < y0 + 0.05)]
    if len(s) > 3:
        print(f"  Y[{y0:+.2f},{y0+0.05:+.2f}] x={s[:,0].mean():+.3f} z={s[:,2].mean():.3f} zmin={s[:,2].min():.3f} zmax={s[:,2].max():.3f} n={len(s)}")

# --- front leg column (left, X>0): Z bins ---
print("\nFRONT_LEG_L column (Z-bin: meanX meanY n)  region X[0.03,0.15] Y[-0.32,-0.10] Z<0.26")
fl = body[(body[:, 0] > 0.03) & (body[:, 0] < 0.15) & (body[:, 1] > -0.32) & (body[:, 1] < -0.10) & (body[:, 2] < 0.26)]
for z0 in np.arange(0.0, 0.26, 0.03):
    s = fl[(fl[:, 2] >= z0) & (fl[:, 2] < z0 + 0.03)]
    if len(s) > 2:
        print(f"  Z[{z0:.2f},{z0+0.03:.2f}] x={s[:,0].mean():+.3f} y={s[:,1].mean():+.3f} xspread={s[:,0].std():.3f} n={len(s)}")

# --- hind leg column (left): Z bins ---
print("\nHIND_LEG_L column (Z-bin: meanX meanY n)  region X[0.05,0.19] Y[-0.02,0.25] Z[0.02,0.30]")
hl = body[(body[:, 0] > 0.05) & (body[:, 0] < 0.19) & (body[:, 1] > -0.02) & (body[:, 1] < 0.25) & (body[:, 2] > 0.02) & (body[:, 2] < 0.30)]
for z0 in np.arange(0.02, 0.30, 0.03):
    s = hl[(hl[:, 2] >= z0) & (hl[:, 2] < z0 + 0.03)]
    if len(s) > 2:
        print(f"  Z[{z0:.2f},{z0+0.03:.2f}] x={s[:,0].mean():+.3f} y={s[:,1].mean():+.3f} yspread={s[:,1].std():.3f} n={len(s)}")

# --- head region cross sections (front) ---
print("\nHEAD cross-sections (Y-bin over ALL body verts: meanZ maxZ width n)")
for y0 in np.arange(-0.50, -0.15, 0.04):
    s = body[(body[:, 1] >= y0) & (body[:, 1] < y0 + 0.04)]
    if len(s) > 3:
        print(f"  Y[{y0:+.2f},{y0+0.04:+.2f}] z={s[:,2].mean():.3f} zmax={s[:,2].max():.3f} zmin={s[:,2].min():.3f} W={s[:,0].max()-s[:,0].min():.3f} n={len(s)}")

# --- paws ---
def paw(name, axis_rear='Y+'):
    v = verts(name)
    # rear = max Y side (toward body rear); front toe = min Y
    rear = v[v[:, 1] > v[:, 1].max() - 0.03]
    wrist = rear.mean(0)
    wrist_top = rear[rear[:, 2] > rear[:, 2].mean()].mean(0)
    tip = v[v[:, 1].argmin()]
    print(f"{name}: rear_centroid=({wrist[0]:+.4f},{wrist[1]:+.4f},{wrist[2]:.4f}) rear_top=({wrist_top[0]:+.4f},{wrist_top[1]:+.4f},{wrist_top[2]:.4f}) tip=({tip[0]:+.4f},{tip[1]:+.4f},{tip[2]:.4f})")
    # mid-foot (ball)
    midy = v[(v[:, 1] > v[:, 1].min() + 0.02) & (v[:, 1] < v[:, 1].min() + 0.05)]
    if len(midy):
        b = midy.mean(0)
        print(f"   ball_approx=({b[0]:+.4f},{b[1]:+.4f},{b[2]:.4f})")

print("\nPAWS")
paw("tripo_part_3")  # front L
paw("tripo_part_2")  # front R
paw("tripo_part_8")  # hind L
paw("tripo_part_7")  # hind R

# --- tail polyline ---
print("\nTAIL")
tail = verts("tripo_part_9")
# order by greedy chain from base (closest to body rear point (0,0.30,0.06))
base_ref = np.array([-0.01, 0.295, 0.06])
d2body = np.linalg.norm(tail - base_ref, axis=1)
order_start = tail[d2body.argmin()]
print(f"  base_nearest=({order_start[0]:+.4f},{order_start[1]:+.4f},{order_start[2]:.4f})")
# parameter: use angle around curve — simpler: k-means into 10 clusters, chain them
np.random.seed(1)
K = 10
idx = np.random.choice(len(tail), K, replace=False)
C = tail[idx].copy()
for _ in range(30):
    d = np.linalg.norm(tail[:, None, :] - C[None], axis=2)
    a = d.argmin(1)
    for k in range(K):
        if (a == k).sum():
            C[k] = tail[a == k].mean(0)
# chain order from base
chain = []
left = list(range(K))
cur = min(left, key=lambda k: np.linalg.norm(C[k] - base_ref))
while left:
    chain.append(cur)
    left.remove(cur)
    if not left:
        break
    cur = min(left, key=lambda k: np.linalg.norm(C[k] - C[chain[-1]]))
print("  centers (ordered):")
for k in chain:
    print(f"    ({C[k][0]:+.4f},{C[k][1]:+.4f},{C[k][2]:.4f})")
tip = tail[np.linalg.norm(tail - base_ref, axis=1).argmax()]
print(f"  tip_far=({tip[0]:+.4f},{tip[1]:+.4f},{tip[2]:.4f})")

# --- ears ---
def ear(name):
    v = verts(name)
    zlo = np.quantile(v[:, 2], 0.12)
    base = v[v[:, 2] <= zlo].mean(0)
    zhi = np.quantile(v[:, 2], 0.88)
    top = v[v[:, 2] >= zhi].mean(0)
    print(f"{name}: base=({base[0]:+.4f},{base[1]:+.4f},{base[2]:.4f}) top=({top[0]:+.4f},{top[1]:+.4f},{top[2]:.4f})")

print("\nEARS")
ear("tripo_part_4")  # L
ear("tripo_part_5")  # R

# --- whisker roots: nearest 5% to body ---
print("\nWHISKERS")
for name in ("tripo_part_0", "tripo_part_1"):
    w = verts(name)
    # distance to body subset (decimate body for speed)
    bsub = body[::4]
    d = np.linalg.norm(w[:, None, :] - bsub[None], axis=2).min(1)
    thr = np.quantile(d, 0.05)
    root = w[d <= thr].mean(0)
    far = w[d.argmax()]
    print(f"{name}: root=({root[0]:+.4f},{root[1]:+.4f},{root[2]:.4f}) far=({far[0]:+.4f},{far[1]:+.4f},{far[2]:.4f})")

# ground check
feet = np.vstack([verts("tripo_part_2"), verts("tripo_part_3"), verts("tripo_part_7"), verts("tripo_part_8")])
print(f"\nGROUND minZ={feet[:,2].min():.5f}")
print("DONE")
