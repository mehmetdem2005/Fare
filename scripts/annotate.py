#!/usr/bin/env python3
import json, os, sys
from PIL import Image, ImageDraw, ImageFont

sys.path.append("/tmp/rig")
PLAN = "/tmp/rig/plan"
OUT = "/tmp/rig/final"
os.makedirs(OUT, exist_ok=True)

F = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
f_title = ImageFont.truetype(FB, 40)
f_sub = ImageFont.truetype(F, 24)
f_lbl = ImageFont.truetype(FB, 23)
f_small = ImageFont.truetype(F, 20)

labels = json.load(open(f"{PLAN}/labels.json"))
R = 1400  # render size

def rgb255(c):
    return tuple(int(round(min(1, v) * 255)) for v in c)

def new_canvas(w, h, title, subtitle=""):
    im = Image.new("RGB", (w, h), (250, 250, 250))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, w, 70], fill=(28, 30, 38))
    d.text((24, 14), title, font=f_title, fill=(255, 255, 255))
    if subtitle:
        d.text((24, 78), subtitle, font=f_sub, fill=(70, 70, 70))
    return im, d

def compose(base_name, bones_name, lighten=0.32):
    base = Image.open(f"{PLAN}/{base_name}").convert("RGBA")
    white = Image.new("RGBA", base.size, (255, 255, 255, 255))
    base = Image.blend(base, white, lighten)
    bones = Image.open(f"{PLAN}/{bones_name}").convert("RGBA")
    return Image.alpha_composite(base, bones).convert("RGB")

def annotate_view(view, title, subtitle, out_name):
    img = compose(f"tex_{view}.png", f"plan_{view}.png")
    MARG, TOP = 330, 120
    W, H = R + 2 * MARG, R + TOP + 40
    im, d = new_canvas(W, H, title, subtitle)
    im.paste(img, (MARG, TOP))
    items = labels["views"][view]
    left = sorted([it for it in items if it["u"] < 0.5], key=lambda i: i["v"])
    right = sorted([it for it in items if it["u"] >= 0.5], key=lambda i: i["v"])

    def bank(its, side):
        n = len(its)
        if not n:
            return
        y0, y1 = TOP + 60, TOP + R - 60
        for i, it in enumerate(its):
            ty = y0 + (y1 - y0) * (i / max(n - 1, 1))
            ax = MARG + it["u"] * R
            ay = TOP + it["v"] * R
            col = rgb255(it["color"])
            if side == "L":
                tx = MARG - 18
                anchor = "rm"
                elbow = (MARG - 10, ty)
            else:
                tx = MARG + R + 18
                anchor = "lm"
                elbow = (MARG + R + 10, ty)
            d.line([elbow, (ax, ay)], fill=col, width=3)
            d.ellipse([ax - 5, ay - 5, ax + 5, ay + 5], outline=col, width=3)
            d.text((tx, ty), it["name"], font=f_lbl, fill=(20, 20, 20), anchor=anchor)
            # color chip
            cx = tx + (4 if side == "R" else -4 - d.textlength(it["name"], font=f_lbl))
            d.rectangle([cx - 14 if side == "L" else tx - 14, ty - 8, cx - 0 if side == "L" else tx - 0, ty + 8], fill=col) if False else None
        return

    bank(left, "L")
    bank(right, "R")
    im.save(f"{OUT}/{out_name}")
    print("saved", out_name)

annotate_view("side", "RIG PLANI — Sol profil", "35 kemik (34 deform + root) · oktahedronlar = planlanan kemikler, beyaz toplar = eklemler", "rig_plan_1_sol_profil.png")
annotate_view("front", "RIG PLANI — Ön görünüm", "+X = farenin SOLU (görselde sağ taraf) · .L yeşil / .R kırmızı", "rig_plan_2_on.png")
annotate_view("top", "RIG PLANI — Üst görünüm", "Omurga tam orta hatta (mesh +0.035m X kaydırılıp ortalanacak) · kuyruk 6 segment", "rig_plan_3_ust.png")

# ---- persp beauty with group legend ----
img = compose("tex_persp.png", "plan_persp.png", lighten=0.25)
W, H = R + 80, R + 240
im, d = new_canvas(W, H, "RIG PLANI — Perspektif", "")
im.paste(img, (40, 100))
gx, gy = 60, R + 130
names_tr = {"core": "core / omurga", "head": "kafa + burun", "ear": "kulaklar", "whisker": "bıyıklar",
            "legL": "SOL bacaklar (.L)", "legR": "SAĞ bacaklar (.R)", "tail": "kuyruk (6)"}
for it in labels["legend_groups"]:
    col = rgb255(it["color"])
    d.rectangle([gx, gy, gx + 26, gy + 26], fill=col, outline=(60, 60, 60))
    t = names_tr[it["name"]]
    d.text((gx + 34, gy + 2), t, font=f_lbl, fill=(20, 20, 20))
    gx += 44 + int(d.textlength(t, font=f_lbl))
    if gx > W - 320:
        gx = 60; gy += 44
im.save(f"{OUT}/rig_plan_4_perspektif.png")
print("saved rig_plan_4_perspektif.png")

# ---- current rig problems sheet (top + side combined) ----
top = compose("tex_top.png", "cur_top.png")
side = compose("tex_side.png", "cur_side.png")
S = 980
top = top.resize((S, S), Image.LANCZOS)
side = side.resize((S, S), Image.LANCZOS)
W, H = S * 2 + 120, S + 320
im, d = new_canvas(W, H, "MEVCUT RIG (Tripo otomatik) — neden sıfırdan yapıyoruz?", "")
im.paste(top, (40, 110))
im.paste(side, (S + 80, 110))
d.text((40 + S // 2, 95), "Üst görünüm", font=f_sub, fill=(60, 60, 60), anchor="mb")
d.text((S + 80 + S // 2, 95), "Sol profil", font=f_sub, fill=(60, 60, 60), anchor="mb")
sc = S / R

def callout(base_x, it, ty):
    u, v = it["uv"]
    ax, ay = base_x + u * S, 110 + v * S
    d.line([(ax, ay), (ax + 14, ty)], fill=(200, 30, 30), width=3)
    d.ellipse([ax - 6, ay - 6, ax + 6, ay + 6], outline=(200, 30, 30), width=3)
    d.text((ax + 20, ty), it["text"], font=f_lbl, fill=(160, 10, 10), anchor="lm")

ys = [H - 170, H - 120, H - 70]
for it, ty in zip(labels["cur"]["top"], ys):
    callout(40, it, ty)
for it, ty in zip(labels["cur"]["side"], ys):
    callout(S + 80, it, ty)
d.text((40, H - 24), "Diğer sorunlar: ölü uç kemikler (bone_26), 'tripo::' önekli/karışık adlandırma, L/R simetrisi yok, kemik eksenleri (roll) düzensiz.",
       font=f_small, fill=(90, 90, 90), anchor="lm")
im.save(f"{OUT}/mevcut_rig_sorunlari.png")
print("saved mevcut_rig_sorunlari.png")

# ---- weight zone sheets with legend bank ----
def zone_sheet(view, title, subtitle, out_name):
    img = Image.open(f"{PLAN}/zone_{view}.png").convert("RGB")
    BANK = 460
    W, H = R + BANK + 60, R + 150
    im, d = new_canvas(W, H, title, subtitle)
    im.paste(img, (30, 120))
    zx, zy = R + 70, 130
    d.text((zx, zy - 6), "Birincil etki bölgesi → kemik", font=f_lbl, fill=(20, 20, 20))
    zy += 40
    for it in labels["zone_legend"]:
        col = rgb255(it["color"])
        d.rectangle([zx, zy, zx + 22, zy + 22], fill=col, outline=(70, 70, 70))
        d.text((zx + 30, zy + 1), it["name"], font=f_small, fill=(25, 25, 25))
        zy += 36
        if zy > H - 50:
            zy = 170; zx += 230
    im.save(f"{OUT}/{out_name}")
    print("saved", out_name)

zone_sheet("side", "AĞIRLIK PLANI — Sol profil", "Renkler = her vertexin BİRİNCİL kemiği (plan). Gerçek skin: otomatik ağırlık + eklemlerde yumuşak geçiş, maks. 4 etki/vertex", "agirlik_plani_1_sol.png")
zone_sheet("persp", "AĞIRLIK PLANI — Perspektif", "Eklem sınırlarında keskin görünen geçişler bağlama sırasında yumuşatılacak (gradient)", "agirlik_plani_2_perspektif.png")
zone_sheet("front", "AĞIRLIK PLANI — Ön görünüm", "L/R ayrımı: sol uzuvlar yeşil tonlar, sağ uzuvlar kırmızı/turuncu tonlar", "agirlik_plani_3_on.png")
zone_sheet("top", "AĞIRLIK PLANI — Üst görünüm", "Kuyruk 6 segment halinde mor tonlarla, omurga zinciri mavi tonlarla", "agirlik_plani_4_ust.png")
print("ALL DONE")
