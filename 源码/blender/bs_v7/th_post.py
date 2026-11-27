# -*- coding: utf-8 -*-
"""th_post.py —— 图标 / 卡牌合成（系统 Python + PIL，Blender 自带 Python 没有 PIL）

输入：docs/_tmp/v7/shots/icon_{1,2,3}.png（带地面 1024 渲染）
      docs/_tmp/v7/shots/sprite_{1,2,3}.png（透明 1600 渲染）
输出：assets/建筑/联盟/城镇大厅_微缩/ 下的图标与卡牌

构图两条硬规矩（v1 栽过）：
  1. 裁切必须用**投影框**，不是渲染画布。四周那圈空地面会把 128 px 上的建筑吃掉 30%。
  2. 卡牌不要"硬地平线"。一条水平线会让底座读成悬在半空，
     改成舞台光池 —— 底座整个泡在光里，边缘一路糊进暗部。
"""
import json
import math
import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
RAW = os.path.join(ROOT, "docs", "_tmp", "v7", "shots")
BST = os.path.join(RAW, "bbox.json")
BOXES = json.load(open(BST, encoding="utf-8")) if os.path.exists(BST) else {}
if not BOXES:
    print("[warn] 没有 bbox.json —— 先跑 th_shots.py，否则落位会退化成估算值")
OUT = os.path.join(ROOT, "assets", "建筑", "联盟", "城镇大厅_微缩")

GOLD = (201, 162, 74)
GOLD_L = (232, 199, 126)
NAVY = (16, 26, 42)
CREAM = (242, 235, 220)

F_CJK = "C:/Windows/Fonts/msyhbd.ttc"
F_CJK_R = "C:/Windows/Fonts/msyh.ttc"
F_SER = "C:/Windows/Fonts/georgia.ttf"


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


def grade(im, contrast=1.07, warm=(1.015, 1.0, 0.972), lift=2):
    im = Image.eval(im, lambda v: max(0, min(255, int((v - 128) * contrast + 128 + lift))))
    r, g, b = im.split()
    f = lambda v, k: min(255, int(v * k))
    return Image.merge("RGB", (r.point(lambda v: f(v, warm[0])),
                               g.point(lambda v: f(v, warm[1])),
                               b.point(lambda v: f(v, warm[2]))))


def crop_to_bbox(im, bb, factor=1.04, anchor=0.50):
    """按投影框裁正方形；anchor 控制建筑在方框里的竖直位置（0.5 = 居中）。"""
    if not bb:
        return im
    x0, y0, x1, y1 = bb
    cw, ch = x1 - x0, y1 - y0
    side = min(im.size[0], max(cw, ch) * factor)
    cx = (x0 + x1) / 2
    cy = y0 + ch * anchor + (0.5 - anchor) * side * 0.0
    cx = min(max(side / 2, cx), im.size[0] - side / 2)
    # 竖直方向：让建筑底边落在 y = cy + side/2 附近，留一点地面
    cy = min(max(side / 2, cy), im.size[1] - side / 2)
    return im.crop((int(cx - side / 2), int(cy - side / 2),
                    int(cx + side / 2), int(cy + side / 2)))


# ------------------------------------------------------------------ 图标

def make_icon(star, size=1024):
    im = Image.open(os.path.join(RAW, "icon_%d.png" % star)).convert("RGB")
    im = crop_to_bbox(im, BOXES.get("icon_%d.png" % star), 1.03)
    im = im.resize((size, size), Image.LANCZOS)

    # 背后一团暖光：浅石墙 + 浅地面会让建筑"消失"，这团光是分离度
    glow = Image.new("L", (size, size), 0)
    gd = ImageDraw.Draw(glow)
    gd.ellipse([size * 0.18, size * 0.08, size * 0.82, size * 0.76], fill=120)
    glow = glow.filter(ImageFilter.GaussianBlur(size * 0.09))
    im = Image.composite(Image.blend(im, Image.new("RGB", (size, size), (255, 232, 194)), 0.22),
                         im, glow)
    im = grade(im, 1.09, (1.02, 1.0, 0.96))
    im = vignette(im, 0.42, 1.9, 0.46)

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

    # 星级带：一段窄缎带，别用一整块模糊
    band = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    bd = ImageDraw.Draw(band)
    bw = int(118 * s)
    bd.rounded_rectangle([size / 2 - bw, size - 92 * s, size / 2 + bw, size - 38 * s],
                         radius=8 * s, fill=(14, 12, 8, 168), outline=GOLD + (120,),
                         width=max(1, int(1.2 * s)))
    im = Image.alpha_composite(im.convert("RGBA"), band).convert("RGB")
    d = ImageDraw.Draw(im, "RGBA")
    r0 = 17 * s
    gap = 44 * s
    y0 = size - 65 * s
    for i in range(3):
        cx = size / 2 + (i - 1) * gap
        if i < star:
            pip_star(d, cx, y0, r0, GOLD_L, (26, 20, 12, 255), max(1, int(2 * s)))
        else:
            pip_star(d, cx, y0, r0, (0, 0, 0, 0), (122, 108, 86, 200), max(1, int(2 * s)))
    return im


# ------------------------------------------------------------------ 卡牌

def make_card(star=3, w=1024, h=1400):
    # ---- 1. 背景：深蓝竖向渐变
    bg = Image.new("RGB", (w, h), (0, 0, 0))
    d = ImageDraw.Draw(bg)
    top, mid, bot = (13, 21, 34), (28, 42, 62), (46, 58, 74)
    for y in range(h):
        t = y / (h - 1)
        if t < 0.58:
            k = t / 0.58
            c = tuple(int(top[i] + (mid[i] - top[i]) * k) for i in range(3))
        else:
            k = (t - 0.58) / 0.42
            c = tuple(int(mid[i] + (bot[i] - mid[i]) * k) for i in range(3))
        d.line([0, y, w, y], fill=c)

    # ---- 2. 建筑背后一团暖光
    glow = Image.new("L", (w, h), 0)
    ImageDraw.Draw(glow).ellipse([w * 0.10, h * 0.16, w * 0.90, h * 0.78], fill=120)
    glow = glow.filter(ImageFilter.GaussianBlur(w * 0.12))
    bg = Image.composite(Image.new("RGB", (w, h), (186, 142, 80)), bg,
                         glow.point(lambda v: int(v * 0.58)))

    # ---- 3. 舞台光池（没有地平线）
    pool = Image.new("L", (w, h), 0)
    ImageDraw.Draw(pool).ellipse([-w * 0.22, h * 0.62, w * 1.22, h * 1.28], fill=255)
    pool = pool.filter(ImageFilter.GaussianBlur(w * 0.09))
    bg = Image.composite(Image.new("RGB", (w, h), (92, 84, 68)), bg,
                         pool.point(lambda v: int(v * 0.94)))
    hot = Image.new("L", (w, h), 0)
    ImageDraw.Draw(hot).ellipse([w * 0.16, h * 0.70, w * 0.84, h * 1.02], fill=255)
    hot = hot.filter(ImageFilter.GaussianBlur(w * 0.06))
    bg = Image.composite(Image.new("RGB", (w, h), (138, 124, 100)), bg,
                         hot.point(lambda v: int(v * 0.55)))

    # ---- 4. 建筑：底边落在光池中线，按真实投影框缩放
    sp = Image.open(os.path.join(RAW, "sprite_%d.png" % star)).convert("RGBA")
    bb = BOXES.get("sprite_%d.png" % star)
    sw, sh = sp.size
    base_y = int(h * 0.745)
    if bb:
        cx0, cy0, cx1, cy1 = bb
        cw, chh = cx1 - cx0, cy1 - cy0
        k = min(w * 1.020 / cw, h * 0.585 / chh)
        sp = sp.resize((int(sw * k), int(sh * k)), Image.LANCZOS)
        bx = int(w / 2 - ((cx0 + cx1) / 2) * k)
        by = int(base_y - cy1 * k)
    else:
        k = (w * 0.9) / sw
        sp = sp.resize((int(sw * k), int(sh * k)), Image.LANCZOS)
        bx = (w - sp.size[0]) // 2
        by = int(base_y - sp.size[1] * 0.92)

    # ---- 5. 投影：铺满整个底座投影面
    shadow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    rx, ry = w * 0.34, h * 0.052
    for mul, alpha in ((1.00, 110), (0.68, 105), (0.36, 140)):
        sd.ellipse([w / 2 - rx * mul, base_y - ry * mul,
                    w / 2 + rx * mul, base_y + ry * mul], fill=(0, 0, 0, alpha))
    shadow = shadow.filter(ImageFilter.GaussianBlur(20))
    out = Image.alpha_composite(bg.convert("RGBA"), shadow)

    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    layer.paste(sp, (bx, by), sp)
    out = Image.alpha_composite(out, layer).convert("RGB")

    # ---- 6. 框
    d = ImageDraw.Draw(out, "RGBA")
    d.rectangle([18, 18, w - 19, h - 19], outline=GOLD + (110,), width=2)
    d.rectangle([25, 25, w - 26, h - 26], outline=(9, 13, 21, 170), width=2)
    for cx, cy in ((18, 18), (w - 19, 18), (18, h - 19), (w - 19, h - 19)):
        d.rectangle([cx - 7, cy - 7, cx + 7, cy + 7], fill=GOLD + (240,))
    # 顶部标尺装饰
    d.line([w * 0.30, 82, w * 0.70, 82], fill=GOLD + (70,), width=1)

    f_tag = font(F_CJK_R, 23)
    tag = "联盟   ·   ALLIANCE"
    tw = d.textlength(tag, font=f_tag)
    d.rectangle([(w - tw) / 2 - 22, 48, (w + tw) / 2 + 22, 90], outline=GOLD + (110,), width=1)
    d.text(((w - tw) / 2, 54), tag, font=f_tag, fill=GOLD_L + (230,))

    # ---- 7. 铭牌
    plate_w, plate_h = int(w * 0.70), 178
    px0 = (w - plate_w) // 2
    py0 = h - 236
    d.rounded_rectangle([px0, py0, px0 + plate_w, py0 + plate_h], radius=5,
                        fill=(12, 19, 31, 240), outline=GOLD + (225,), width=2)
    d.rounded_rectangle([px0 + 7, py0 + 7, px0 + plate_w - 7, py0 + plate_h - 7], radius=3,
                        outline=GOLD + (64,), width=1)
    d.line([px0 + 40, py0 + 18, px0 + plate_w - 40, py0 + 18], fill=GOLD + (55,), width=1)

    f_name = font(F_CJK, 74)
    name = "城镇大厅"
    nw = d.textlength(name, font=f_name)
    d.text(((w - nw) / 2, py0 + 28), name, font=f_name, fill=(246, 240, 228))

    f_en = font(F_SER, 25)
    en = " ".join("TOWN HALL")
    ew = d.textlength(en, font=f_en)
    d.text(((w - ew) / 2, py0 + 119), en, font=f_en, fill=GOLD_L + (225,))

    for i in range(3):
        cx = w / 2 + (i - 1) * 50
        cy = py0 - 30
        if i < star:
            pip_star(d, cx, cy, 18, GOLD_L, (16, 12, 7, 255), 2)
        else:
            pip_star(d, cx, cy, 18, (0, 0, 0, 0), (150, 134, 100, 215), 2)
    return out


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for s in (1, 2, 3):
        ic = make_icon(s)
        ic.resize((512, 512), Image.LANCZOS).save(os.path.join(OUT, "城镇大厅_%d星_图标.png" % s))
        ic.resize((128, 128), Image.LANCZOS).save(os.path.join(OUT, "城镇大厅_%d星_图标_128.png" % s))
    Image.open(os.path.join(OUT, "城镇大厅_3星_图标.png")).save(
        os.path.join(OUT, "城镇大厅_图标.png"))
    for s in (1, 2, 3):
        make_card(s).save(os.path.join(OUT, "城镇大厅_%d星_卡牌.png" % s))
    print("done ->", OUT)
