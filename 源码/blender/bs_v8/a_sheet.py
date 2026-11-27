# -*- coding: utf-8 -*-
"""a_sheet.py —— 96 px 识别表（七座 × 三档，彩色 + 纯剪影）

    python a_sheet.py

"缩到 96 px 还认不认得出"是这套资产的唯一硬判据。
剪影用**透明底 sprite 的 alpha 通道**直接填黑，不靠阈值抠图 ——
背景色一变，阈值法就会把浅色石墙一起抠掉。
"""
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
RAW = os.path.join(ROOT, "docs", "_tmp", "v8", "shots")
OUT = os.path.join(ROOT, "docs", "20-经验", "七建筑_96px识别表.png")

NAMES = ["城镇大厅", "兵营", "农场", "铁匠铺", "伐木场", "哨塔", "箭塔"]
EN = ["TOWN HALL", "BARRACKS", "FARM", "SMITH", "LUMBER", "WATCH", "ARROW"]
F = "C:/Windows/Fonts/msyhbd.ttc"
FR = "C:/Windows/Fonts/msyh.ttc"

CELL = 150
PAD = 18
LABEL = 46


def main():
    # 左半：彩色 3 列；右半：同一批剪影 3 列。两块分开，格子不打架。
    LEFT = PAD
    RIGHT = PAD + CELL * 3 + 46
    W = PAD * 2 + CELL * 6 + 46
    H = PAD * 2 + (CELL + LABEL) * len(NAMES) + 34
    sheet = Image.new("RGB", (W, H), (24, 30, 40))
    d = ImageDraw.Draw(sheet)
    f_t = ImageFont.truetype(F, 20)
    f_s = ImageFont.truetype(FR, 13)
    d.text((LEFT, 12), "联盟七建筑 · 三档 · 96 px 识别表　（左：彩色　右：纯剪影）",
           font=f_s, fill=(214, 200, 170))
    for c, t in enumerate(("1 星", "2 星", "3 星")):
        for base in (LEFT, RIGHT):
            d.text((base + c * CELL + 46, 34), t, font=f_s, fill=(150, 140, 120))

    for r, cn in enumerate(NAMES):
        y0 = 56 + r * (CELL + LABEL)
        d.text((LEFT, y0 + 4), cn, font=f_t, fill=(240, 232, 216))
        d.text((LEFT + 92, y0 + 8), EN[r], font=f_s, fill=(150, 140, 120))
        for c, s in enumerate((1, 2, 3)):
            p = os.path.join(RAW, "%s_sprite%d.png" % (cn, s))
            if not os.path.exists(p):
                continue
            im = Image.open(p).convert("RGBA")
            im = im.crop(im.getbbox())
            side = max(im.size)
            canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
            canvas.paste(im, ((side - im.size[0]) // 2, side - im.size[1]))
            small = canvas.resize((96, 96), Image.LANCZOS)
            yy = y0 + LABEL + 4
            x = LEFT + c * CELL + (CELL - 96) // 2
            bg = Image.new("RGBA", (96, 96), (206, 198, 180, 255))
            bg.alpha_composite(small)
            sheet.paste(bg.convert("RGB"), (x, yy))
            sil = Image.new("RGBA", (96, 96), (0, 0, 0, 0))
            sil.paste((22, 22, 26, 255), (0, 0), small.split()[3])
            sx = RIGHT + c * CELL + (CELL - 96) // 2
            # 剪影必须垫浅底：黑剪影贴在深蓝底上等于没画
            sbg = Image.new("RGBA", (96, 96), (206, 198, 180, 255))
            sbg.alpha_composite(sil)
            sheet.paste(sbg.convert("RGB"), (sx, yy))
            d.text((x + 40, yy + 98), "\u2605" * s, font=f_s, fill=(214, 176, 90))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    sheet.save(OUT)
    print("sheet ->", OUT, sheet.size)


if __name__ == "__main__":
    main()
