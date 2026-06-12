#!/usr/bin/env python3
import json, os
from PIL import Image, ImageDraw, ImageFont

QA = "/tmp/rig/qa"
QA2 = "/tmp/rig/qa2"
OUT = "/tmp/rig/final2"
os.makedirs(OUT, exist_ok=True)

F = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
f_title = ImageFont.truetype(FB, 38)
f_sub = ImageFont.truetype(F, 22)
f_lbl = ImageFont.truetype(FB, 21)
f_cap = ImageFont.truetype(FB, 24)
f_small = ImageFont.truetype(F, 18)

def rgb255(c):
    return tuple(int(round(min(1, v) * 255)) for v in c)

def new_canvas(w, h, title, subtitle=""):
    im = Image.new("RGB", (w, h), (250, 250, 250))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, w, 64], fill=(28, 30, 38))
    d.text((22, 12), title, font=f_title, fill=(255, 255, 255))
    if subtitle:
        d.text((22, 72), subtitle, font=f_sub, fill=(70, 70, 70))
    return im, d

def compose(base, over, lighten=0.30):
    b = Image.open(base).convert("RGBA")
    w = Image.new("RGBA", b.size, (255, 255, 255, 255))
    b = Image.blend(b, w, lighten)
    o = Image.open(over).convert("RGBA")
    return Image.alpha_composite(b, o).convert("RGB")

labels = json.load(open(f"{QA}/sk_labels.json"))
R = 1100

def skeleton_sheet(view, title, subtitle, out_name):
    img = compose(f"{QA}/tex_{view}.png", f"{QA}/sk_{view}.png")
    MARG, TOP = 320, 112
    W, H = R + 2 * MARG, R + TOP + 36
    im, d = new_canvas(W, H, title, subtitle)
    im.paste(img, (MARG, TOP))
    items = labels["views"][view]
    left = sorted([it for it in items if it["u"] < 0.5], key=lambda i: i["v"])
    right = sorted([it for it in items if it["u"] >= 0.5], key=lambda i: i["v"])
    def bank(its, side):
        n = len(its)
        if not n:
            return
        y0, y1 = TOP + 50, TOP + R - 50
        for i, it in enumerate(its):
            ty = y0 + (y1 - y0) * (i / max(n - 1, 1))
            ax, ay = MARG + it["u"] * R, TOP + it["v"] * R
            col = rgb255(it["color"])
            tx = MARG - 16 if side == "L" else MARG + R + 16
            anc = "rm" if side == "L" else "lm"
            d.line([(tx + (6 if side == "L" else -6), ty), (ax, ay)], fill=col, width=3)
            d.ellipse([ax - 5, ay - 5, ax + 5, ay + 5], outline=col, width=3)
            d.text((tx, ty), it["name"], font=f_lbl, fill=(20, 20, 20), anchor=anc)
    bank(left, "L"); bank(right, "R")
    im.save(f"{OUT}/{out_name}")
    print("saved", out_name)

skeleton_sheet("side", "FİNAL RIG — Sol profil", "38 deform kemik + root · tüm kemikler mesh İÇİNDE (ışın testiyle doğrulandı) · kulak 4/3 segment zincir", "final_iskelet_1_sol.png")
skeleton_sheet("front", "FİNAL RIG — Ön görünüm", ".L yeşil / .R kırmızı · bıyık kemiği YOK (tüpler yüz derisini takip eder, asla bükülmez)", "final_iskelet_2_on.png")
skeleton_sheet("top", "FİNAL RIG — Üst görünüm", "Omurga tam orta hatta · kuyruk 6 segment, eğriyi takip eder", "final_iskelet_3_ust.png")

# persp beauty
img = compose(f"{QA}/tex_persp.png", f"{QA}/sk_persp.png", 0.22)
W, H = R + 70, R + 200
im, d = new_canvas(W, H, "FİNAL RIG — Perspektif", "")
im.paste(img, (35, 96))
GROUPS = [("core/omurga", (0.12, 0.38, 1.0)), ("kafa+burun", (1.0, 0.72, 0.05)),
          ("kulak", (0.0, 0.85, 0.95)), ("SOL (.L)", (0.10, 0.80, 0.18)),
          ("SAĞ (.R)", (0.95, 0.18, 0.10)), ("kuyruk", (0.62, 0.30, 0.95)),
          ("root", (0.45, 0.45, 0.45))]
gx, gy = 50, R + 120
for nm, c in GROUPS:
    d.rectangle([gx, gy, gx + 24, gy + 24], fill=rgb255(c), outline=(60, 60, 60))
    d.text((gx + 32, gy + 2), nm, font=f_lbl, fill=(20, 20, 20))
    gx += 60 + int(d.textlength(nm, font=f_lbl))
im.save(f"{OUT}/final_iskelet_4_persp.png")
print("saved final_iskelet_4_persp.png")

# ---- weight grid ----
WEIGHTS = [
    ("hips", "w_hips"), ("spine_01", "w_spine_01"), ("spine_02", "w_spine_02"),
    ("spine_03", "w_spine_03"), ("neck", "w_neck"), ("head", "w_head"),
    ("snout", "w_snout"), ("snout + bıyıklar", "w_snout_whiskers"), ("ear.L", "w_ear_L"),
    ("shoulder.L", "w_shoulder_L"), ("upper_arm.L", "w_upper_arm_L"), ("forearm.L", "w_forearm_L"),
    ("hand.L", "w_hand_L"), ("front_toes.L", "w_front_toes_L"), ("thigh.L", "w_thigh_L"),
    ("shin.L", "w_shin_L"), ("foot.L", "w_foot_L"), ("toes.L", "w_toes_L"),
    ("tail_02", "w_tail_02"), ("tail_04", "w_tail_04"),
]
COLS, CELL, CAP = 5, 470, 44
ROWS = (len(WEIGHTS) + COLS - 1) // COLS
W = COLS * CELL + 40
H = 110 + ROWS * (CELL + CAP)
im, d = new_canvas(W, H, "GERÇEK AĞIRLIKLAR — bone heat + dikiş kaynağı + yumuşatma",
                   "mavi=0 · yeşil=0.5 · kırmızı=1.0 · gri=etkisiz · maks 4 etki/vertex, normalize")
for i, (cap, fn) in enumerate(WEIGHTS):
    r, c = divmod(i, COLS)
    x = 20 + c * CELL
    y = 104 + r * (CELL + CAP)
    cell = Image.open(f"{QA}/{fn}.png").convert("RGB")
    # crop center square then resize
    cw = min(cell.size)
    cell = cell.crop(((cell.width - cw) // 2, (cell.height - cw) // 2,
                      (cell.width + cw) // 2, (cell.height + cw) // 2)).resize((CELL - 8, CELL - 8), Image.LANCZOS)
    im.paste(cell, (x + 4, y))
    d.text((x + CELL // 2, y + CELL - 2), cap, font=f_cap, fill=(20, 20, 20), anchor="ma")
im.save(f"{OUT}/final_agirliklar.png")
print("saved final_agirliklar.png")

# ---- pose grid ----
POSES = [
    ("P1 baş çevirme", "pose_P1_bas_cevirme"),
    ("P2 ön bacak .L", "pose_P2_on_bacak_L"),
    ("P3 arka bacak .R", "pose_P3_arka_bacak_R"),
    ("P4 omurga+kuyruk", "pose_P4_omurga_kuyruk"),
    ("P5 kulak+burun", "pose_P5_kulak_burun"),
]
CELL = 560
W = len(POSES) * CELL + 40
H = 110 + 2 * CELL + 70
im, d = new_canvas(W, H, "FK POZ TESTLERİ — deformasyon doğrulaması",
                   "üst sıra: perspektif · alt sıra: sol profil · IK kapalıyken FK rotasyonları")
for i, (cap, base) in enumerate(POSES):
    x = 20 + i * CELL
    for j, suffix in enumerate(("persp", "side")):
        img = Image.open(f"{QA}/{base}_{suffix}.png").convert("RGB").resize((CELL - 8, CELL - 8), Image.LANCZOS)
        im.paste(img, (x + 4, 104 + j * CELL))
    d.text((x + CELL // 2, 104 + 2 * CELL + 6), cap, font=f_cap, fill=(20, 20, 20), anchor="ma")
im.save(f"{OUT}/final_pozlar_fk.png")
print("saved final_pozlar_fk.png")

# ---- IK + stress sheet ----
items = [
    ("IK testi (ön)", f"{QA}/pose_IK_test_front.png"),
    ("IK testi (persp)", f"{QA}/pose_IK_test_persp.png"),
    ("stres: ön bacak", f"{QA2}/test_arm.png"),
    ("stres: arka bacak", f"{QA2}/test_hind.png"),
    ("stres: baş 57°", f"{QA2}/test_head.png"),
    ("stres: kuyruk", f"{QA2}/test_tail.png"),
]
CELL = 560
W = 3 * CELL + 40
H = 110 + 2 * (CELL + 50)
im, d = new_canvas(W, H, "IK + STRES TESTLERİ", "ik_foot.L / ik_hand.R hedefleri kaldırıldı · stres pozları büyük açılarla, çatlak yok")
for i, (cap, fn) in enumerate(items):
    r, c = divmod(i, 3)
    x = 20 + c * CELL
    y = 104 + r * (CELL + 50)
    img = Image.open(fn).convert("RGB").resize((CELL - 8, CELL - 8), Image.LANCZOS)
    im.paste(img, (x + 4, y))
    d.text((x + CELL // 2, y + CELL - 2), cap, font=f_cap, fill=(20, 20, 20), anchor="ma")
im.save(f"{OUT}/final_ik_stres.png")
print("saved final_ik_stres.png")
print("ASSEMBLE2 DONE")
