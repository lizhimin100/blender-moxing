# -*- coding: utf-8 -*-
"""a_post.py —— 七座建筑的图标（512）与卡牌（1024×1400），系统 Python + PIL

    python a_post.py                # 全部
    python a_post.py 农场 铁匠铺     # 指定

两条硬规矩沿用（踩过的坑）：
  1. 裁切用**投影框**，不是渲染画布 —— 正交相机居中取景，画布四周全是空白；
  2. 卡牌**不要硬地平线** —— 底座泡在舞台光池里，否则建筑读成"悬空"。
"""
import json
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
RAW = os.path.join(ROOT, "docs", "_tmp", "v8", "shots")
BST = os.path.join(RAW, "bbox.json")
BOXES = json.load(open(BST, encoding="utf-8")) if os.path.exists(BST) else {}
ASSETS = os.path.join(ROOT, "assets", "建筑", "联盟")

GOLD = (201, 162, 74)
GOLD_L = (232, 199, 126)
CREAM = (242, 235, 220)

F_CJK = "C:/Windows/Fonts/msyhbd.ttc"
F_CJK_R = "C:/Windows/Fonts/msyh.ttc"
F_SER = "C:/Windows/Fonts/georgia.ttf"

BOOKS = {
    "城镇大厅": ("TOWN HALL", ["市政厅", "主城", "城堡"]),
    "兵营":     ("BARRACKS", ["木石营棚", "石砌营房", "皇家要塞"]),
    "农场":     ("FARM", ["农舍", "谷仓农场", "风车农场"]),
    "铁匠铺":   ("BLACKSMITH", ["敞棚铁铺", "石砌铁铺", "大师工坊"]),
    "伐木场":   ("LUMBER MILL", ["敞棚锯木", "石基磨坊", "吊木工场"]),
    "哨塔":     ("WATCH TOWER", ["木构哨塔", "石基哨塔", "石砌哨塔"]),
    "箭塔":     ("ARROW TOWER", ["石砌箭塔", "双耳箭塔", "皇家箭塔"]),
}


def font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def pip_star(d, cx, cy, r, fill, outline=None, w=2):
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.42
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    d.polygon(pts, fill=fill, outline=outline)
    if outline:
        d.line(pts + [pts[0]], fill=outline, width=w)


def vignette(im, strength=0.36, power=2.2, cy=0.44):
    w, h = im.size
    mask = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(mask)
    cx = w / 2
    maxr = math.hypot(w / 2, h / 2)
    steps = 96
    for i in range(steps, 0, -1):
        r = maxr * i / steps
        v = int(255 * (1 - strength * (i / steps) ** power))
        d.ellipse([cx - r, cy * h - r * 1.1, cx + r, cy * h + r * 1.1], fill=v)
    mask = mask.filter(ImageFilter.GaussianBlur(w * 0.02))
    return Image.composite(im, Image.new("RGB", (w, h), (0, 0, 0)), mask)


def grade(im, contrast=1.06, warm=(1.015, 1.0, 0.975), lift=1):
    im = Image.eval(im, lambda v: max(0, min(255, int((v - 128) * contrast + 128 + lift))))
    r, g, b = im.split()
    f = lambda v, k: min(255, int(v * k))
    return Image.merge("RGB", (r.point(lambda v: f(v, warm[0])),
                               g.point(lambda v: f(v, warm[1])),
                               b.point(lambda v: f(v, warm[2]))))


def crop_to_bbox(im, bb, factor=1.04, anchor=0.50):
    if not bb:
        return im
    x0, y0, x1, y1 = bb
    cw, ch = x1 - x0, y1 - y0
    side = min(im.size[0], max(cw, ch) * factor)
    cx = (x0 + x1) / 2
    cy = y0 + ch * anchor
    cx = min(max(side / 2, cx), im.size[0] - side / 2)
    cy = min(max(side / 2, cy), im.size[1] - side / 2)
    return im.crop((int(cx - side / 2), int(cy - side / 2),
                    int(cx + side / 2), int(cy + side / 2)))


# ------------------------------------------------------------------ 图标

def make_icon(cn, star, size=1024):
    im = Image.open(os.path.join(RAW, "%s_icon%d.png" % (cn, star))).convert("RGB")
    im = crop_to_bbox(im, BOXES.get("%s_icon%d.png" % (cn, star)), 1.085, 0.50)
    im = im.resize((size, size), Image.LANCZOS)

    glow = Image.new("L", (size, size), 0)
    gd = ImageDraw.Draw(glow)
    gd.ellipse([size * 0.16, size * 0.06, size * 0.84, size * 0.78], fill=110)
    glow = glow.filter(ImageFilter.GaussianBlur(size * 0.10))
    im = Image.composite(Image.blend(im, Image.new("RGB", (size, size), (255, 233, 197)), 0.20),
                         im, glow)
    im = grade(im, 1.07, (1.02, 1.0, 0.965))
    im = vignette(im, 0.40, 1.9, 0.46)

    d = ImageDraw.Draw(im, "RGBA")
    s = size / 1024.0
    inset = int(14 * s)
    d.rectangle([inset, inset, size - inset - 1, size - inset - 1],
                outline=(18, 16, 12, 200), width=max(1, int(3 * s)))
    inset2 = int(23 * s)
    d.rectangle([inset2, inset2, size - inset2 - 1, size - inset2 - 1],
                outline=GOLD + (235,), width=max(1, int(2.0 * s)))
    for cx, cy in ((inset2, inset2), (size - inset2, inset2),
                   (inset2, size - inset2), (size - inset2, size - inset2)):
        r = int(7 * s)
        d.rectangle([cx - r, cy - r, cx + r, cy + r], fill=GOLD + (255,),
                    outline=(18, 16, 12, 255), width=max(1, int(1.5 * s)))

    band = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    bd = ImageDraw.Draw(band)
    bw = int(112 * s)
    bd.rounded_rectangle([size / 2 - bw, size - 88 * s, size / 2 + bw, size - 36 * s],
                         radius=8 * s, fill=(14, 12, 8, 170), outline=GOLD + (120,),
                         width=max(1, int(1.2 * s)))
    im = Image.alpha_composite(im.convert("RGBA"), band).convert("RGB")
    d = ImageDraw.Draw(im, "RGBA")
    r0 = 16 * s
    gap = 42 * s
    y0 = size - 62 * s
    for i in range(3):
        cx = size / 2 + (i - 1) * gap
        if i < star:
            pip_star(d, cx, y0, r0, GOLD_L, (26, 20, 12, 255), max(1, int(2 * s)))
        else:
            pip_star(d, cx, y0, r0, (0, 0, 0, 0), (126, 112, 90, 200), max(1, int(2 * s)))
    return im


# ------------------------------------------------------------------ 卡牌

def make_card(cn, star, w=1024, h=1400):
    en, tiers = BOOKS[cn]
    bg = Image.new("RGB", (w, h), (0, 0, 0))
    d = ImageDraw.Draw(bg)
    top, mid, bot = (13, 21, 34), (26, 40, 60), (44, 56, 72)
    for y in range(h):
        t = y / (h - 1)
        if t < 0.58:
            k = t / 0.58
            c = tuple(int(top[i] + (mid[i] - top[i]) * k) for i in range(3))
        else:
            k = (t - 0.58) / 0.42
            c = tuple(int(mid[i] + (bot[i] - mid[i]) * k) for i in range(3))
        d.line([0, y, w, y], fill=c)

    glow = Image.new("L", (w, h), 0)
    ImageDraw.Draw(glow).ellipse([w * 0.10, h * 0.14, w * 0.90, h * 0.76], fill=115)
    glow = glow.filter(ImageFilter.GaussianBlur(w * 0.12))
    bg = Image.composite(Image.new("RGB", (w, h), (182, 140, 80)), bg,
                         glow.point(lambda v: int(v * 0.55)))

    pool = Image.new("L", (w, h), 0)
    ImageDraw.Draw(pool).ellipse([-w * 0.22, h * 0.62, w * 1.22, h * 1.28], fill=255)
    pool = pool.filter(ImageFilter.GaussianBlur(w * 0.09))
    bg = Image.composite(Image.new("RGB", (w, h), (90, 82, 66)), bg,
                         pool.point(lambda v: int(v * 0.92)))
    hot = Image.new("L", (w, h), 0)
    ImageDraw.Draw(hot).ellipse([w * 0.16, h * 0.70, w * 0.84, h * 1.02], fill=255)
    hot = hot.filter(ImageFilter.GaussianBlur(w * 0.06))
    bg = Image.composite(Image.new("RGB", (w, h), (134, 120, 98)), bg,
                         hot.point(lambda v: int(v * 0.52)))

    sp = Image.open(os.path.join(RAW, "%s_sprite%d.png" % (cn, star))).convert("RGBA")
    bb = BOXES.get("%s_sprite%d.png" % (cn, star))
    sw, sh = sp.size
    base_y = int(h * 0.742)
    if bb:
        cx0, cy0, cx1, cy1 = bb
        cw, chh = cx1 - cx0, cy1 - cy0
        k = min(w * 0.880 / cw, h * 0.565 / chh)
        sp = sp.resize((int(sw * k), int(sh * k)), Image.LANCZOS)
        bx = int(w / 2 - ((cx0 + cx1) / 2) * k)
        by = int(base_y - cy1 * k)
    else:
        k = (w * 0.9) / sw
        sp = sp.resize((int(sw * k), int(sh * k)), Image.LANCZOS)
        bx = (w - sp.size[0]) // 2
        by = int(base_y - sp.size[1] * 0.92)

    shadow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    rx, ry = w * 0.35, h * 0.054
    for mul, alpha in ((1.00, 105), (0.68, 100), (0.36, 135)):
        sd.ellipse([w / 2 - rx * mul, base_y - ry * mul,
                    w / 2 + rx * mul, base_y + ry * mul], fill=(0, 0, 0, alpha))
    shadow = shadow.filter(ImageFilter.GaussianBlur(20))
    out = Image.alpha_composite(bg.convert("RGBA"), shadow)

    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    layer.paste(sp, (bx, by), sp)
    out = Image.alpha_composite(out, layer).convert("RGB")

    d = ImageDraw.Draw(out, "RGBA")
    d.rectangle([18, 18, w - 19, h - 19], outline=GOLD + (110,), width=2)
    d.rectangle([25, 25, w - 26, h - 26], outline=(9, 13, 21, 170), width=2)
    for cx, cy in ((18, 18), (w - 19, 18), (18, h - 19), (w - 19, h - 19)):
        d.rectangle([cx - 7, cy - 7, cx + 7, cy + 7], fill=GOLD + (240,))
    d.line([w * 0.30, 82, w * 0.70, 82], fill=GOLD + (70,), width=1)

    f_tag = font(F_CJK_R, 23)
    tag = "联盟   ·   ALLIANCE"
    tw = d.textlength(tag, font=f_tag)
    d.rectangle([(w - tw) / 2 - 22, 48, (w + tw) / 2 + 22, 90], outline=GOLD + (110,), width=1)
    d.text(((w - tw) / 2, 54), tag, font=f_tag, fill=GOLD_L + (230,))

    plate_w, plate_h = int(w * 0.72), 190
    px0 = (w - plate_w) // 2
    py0 = h - 244
    d.rounded_rectangle([px0, py0, px0 + plate_w, py0 + plate_h], radius=5,
                        fill=(12, 19, 31, 240), outline=GOLD + (225,), width=2)
    d.rounded_rectangle([px0 + 7, py0 + 7, px0 + plate_w - 7, py0 + plate_h - 7], radius=3,
                        outline=GOLD + (64,), width=1)
    d.line([px0 + 40, py0 + 18, px0 + plate_w - 40, py0 + 18], fill=GOLD + (55,), width=1)

    f_name = font(F_CJK, 70)
    nw = d.textlength(cn, font=f_name)
    d.text(((w - nw) / 2, py0 + 26), cn, font=f_name, fill=CREAM)

    f_tier = font(F_CJK_R, 26)
    tier = "%d★   %s" % (star, tiers[star - 1])
    tw2 = d.textlength(tier, font=f_tier)
    d.text(((w - tw2) / 2, py0 + 110), tier, font=f_tier, fill=GOLD_L + (245,))

    f_en = font(F_SER, 21)
    en2 = " ".join(en)
    ew = d.textlength(en2, font=f_en)
    d.text(((w - ew) / 2, py0 + 152), en2, font=f_en, fill=GOLD_L + (200,))

    for i in range(3):
        cx = w / 2 + (i - 1) * 46
        cy = py0 - 26
        if i < star:
            pip_star(d, cx, cy, 17, GOLD_L, (16, 12, 7, 255), 2)
        else:
            pip_star(d, cx, cy, 17, (0, 0, 0, 0), (150, 134, 100, 215), 2)
    return out


if __name__ == "__main__":
    only = sys.argv[1:]
    if not BOXES:
        print("[warn] 没有 bbox.json —— 先跑 a_shots.py")
    for cn in BOOKS:
        if only and cn not in only:
            continue
        outdir = os.path.join(ASSETS, "%s_微缩" % cn)
        if not os.path.exists(os.path.join(RAW, "%s_icon1.png" % cn)):
            print("[skip] %s 还没底片" % cn)
            continue
        os.makedirs(outdir, exist_ok=True)
        for s in (1, 2, 3):
            ic = make_icon(cn, s)
            ic.resize((512, 512), Image.LANCZOS).save(
                os.path.join(outdir, "%s_%d星_图标.png" % (cn, s)))
            ic.resize((128, 128), Image.LANCZOS).save(
                os.path.join(outdir, "%s_%d星_图标_128.png" % (cn, s)))
            make_card(cn, s).save(os.path.join(outdir, "%s_%d星_卡牌.png" % (cn, s)))
        Image.open(os.path.join(outdir, "%s_3星_图标.png" % cn)).save(
            os.path.join(outdir, "%s_图标.png" % cn))
        # 三阶同框：交付件本身（"同一场景、1.5 m 间距、3/4 俯视"的证据）
        lu = os.path.join(RAW, "%s_三阶同框.png" % cn)
        if os.path.exists(lu):
            Image.open(lu).save(os.path.join(outdir, "%s_三阶同框.png" % cn))
        print("ok  %s" % cn)
    print("done ->", ASSETS)
