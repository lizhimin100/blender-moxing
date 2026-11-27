# -*- coding: utf-8 -*-
"""style_sheet.py —— 把四张对照图拼成一张 2×2 对照台（带标注）。

    python blender/bs_v6/style_sheet.py [资产名]

产物 docs/审美/对照台_<资产>.png —— 用户只需要在这张图上指。
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "docs", "审美")
CN = sys.argv[1] if len(sys.argv) > 1 else "地牢"

CAP = {
    "A_要塞": ("A · 要塞", "压扁 16% + 加宽 8%　重心压低，压得住地面"),
    "B_神殿": ("B · 神殿", "拉高 18% + 收窄 7%　垂直感、纪念性"),
    "C_遗迹": ("C · 遗迹", "每个构件各自倾斜 ±1.6°　松脱、随时要塌"),
    "D_极简": ("D · 极简", "删掉体积 <12 L 的小件　只留体量，装饰密度降到 1/3"),
}
ORDER = ["A_要塞", "B_神殿", "C_遗迹", "D_极简"]
CELL, PAD, CAPH, TOP = 760, 18, 62, 96


def font(sz):
    for p in (r"C:/Windows/Fonts/msyh.ttc", r"C:/Windows/Fonts/simhei.ttf"):
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, sz)
            except Exception:
                pass
    return ImageFont.load_default()


def main():
    imgs = []
    for tag in ORDER:
        p = os.path.join(OUT, "对照_%s_%s.png" % (CN, tag))
        if not os.path.exists(p):
            print("缺图", p)
            return
        imgs.append(Image.open(p).convert("RGB").resize((CELL, CELL), Image.LANCZOS))
    W = CELL * 2 + PAD * 3
    H = TOP + (CELL + CAPH) * 2 + PAD * 2
    sheet = Image.new("RGB", (W, H), (24, 23, 21))
    d = ImageDraw.Draw(sheet)
    d.text((PAD, 26), "%s · 四个造型方向" % CN, font=font(40), fill=(232, 226, 214))
    d.text((PAD + 2, 70),
           "同一机位、只改造型参数 —— 指一个最接近的，或者说「B 的高矮 + C 的破败」",
           font=font(20), fill=(150, 144, 132))
    for i, (tag, im) in enumerate(zip(ORDER, imgs)):
        cx = PAD + (i % 2) * (CELL + PAD)
        cy = TOP + (i // 2) * (CELL + CAPH + PAD)
        sheet.paste(im, (cx, cy))
        t1, t2 = CAP[tag]
        d.text((cx + 4, cy + CELL + 8), t1, font=font(26), fill=(226, 214, 188))
        d.text((cx + 4, cy + CELL + 38), t2, font=font(18), fill=(146, 140, 128))
    out = os.path.join(OUT, "对照台_%s.png" % CN)
    sheet.save(out, "PNG", optimize=True)
    print("→", out, os.path.getsize(out) // 1024, "KB")


if __name__ == "__main__":
    main()
