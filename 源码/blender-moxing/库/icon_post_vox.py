"""icon_post_vox.py —— 把 icon_vox 渲出来的透明底 PNG 合成卡面（系统 Python + PIL）

用法：
  python 库/icon_post_vox.py <src_png> <out_png>

v3 的卡面**照抄 `方块人_联盟步兵_图标.png` 的规格**（同一批兵种在界面上必须一样大、一样的边）：

  * 512×512 方图、**不切圆角**（步兵那张就是方的）；
  * 背景：垂直暖灰渐变 + 顶部偏上的一团柔光（采样自步兵：顶部 88/78/65，
    25% 处 96/88/72，底部 25/20/16）；
  * 边：外 2 px 深色(#0A0C11) + 1 px 金线(#96763A) + 1 px 深色；
  * 脚下软阴影；角色水平居中、底边落在 0.935 高度；
  * 出 512 / 128 / 64 三档。
"""
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFilter

W = 512
TOPC = (88, 78, 65)
HIC = (97, 89, 73)        # 25% 高度的柔光
MIDC = (60, 53, 44)
BOTC = (25, 20, 16)


def _lerp(a, b, u):
    return tuple(a[i] + (b[i] - a[i]) * u for i in range(3))


def _ramp(y):
    u = y / (W - 1.0)
    if u < 0.25:
        return _lerp(TOPC, HIC, u / 0.25)
    if u < 0.62:
        return _lerp(HIC, MIDC, (u - 0.25) / 0.37)
    return _lerp(MIDC, BOTC, (u - 0.62) / 0.38)


def card():
    img = Image.new("RGB", (W, W))
    px = img.load()
    cx, cy = W * 0.5, W * 0.30
    for y in range(W):
        base = _ramp(y)
        for x in range(W):
            # 中心柔光 + 四角压暗
            d = math.hypot((x - cx) / (W * 0.62), (y - cy) / (W * 0.75))
            glow = max(0.0, 1.0 - d) ** 2 * 26
            vig = max(0.0, (d - 0.62)) * 46
            px[x, y] = tuple(int(max(0, min(255, base[i] + glow - vig))) for i in range(3))
    return img.convert("RGBA")


def frame(img):
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W - 1, W - 1], outline=(10, 12, 17), width=2)
    d.rectangle([2, 2, W - 3, W - 3], outline=(150, 118, 58), width=1)
    d.rectangle([3, 3, W - 4, W - 4], outline=(34, 38, 48), width=1)
    return img


def shadow(w, h, cy):
    sh = Image.new("L", (W, W), 0)
    ImageDraw.Draw(sh).ellipse([(W - w) / 2, cy - h / 2, (W + w) / 2, cy + h / 2], fill=150)
    sh = sh.filter(ImageFilter.GaussianBlur(W * 0.035))
    out = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    out.putalpha(sh)
    return out


def main():
    src, dst = sys.argv[1], sys.argv[2]
    im = Image.open(src).convert("RGBA")
    base = frame(card())

    # 按"非透明像素"的底边贴到 0.935，水平按**包围盒中心**居中
    bbox = im.getbbox()
    if bbox:
        im = im.crop((max(0, bbox[0] - 4), max(0, bbox[1] - 4),
                      min(im.width, bbox[2] + 4), min(im.height, bbox[3] + 4)))
    foot = int(W * 0.935)
    if im.height > foot - 6:                 # 太高就等比缩，不许裁脚
        k = (foot - 6) / float(im.height)
        im = im.resize((max(1, int(im.width * k)), foot - 6), Image.LANCZOS)
    ox = (W - im.width) // 2
    oy = foot - im.height
    base.alpha_composite(shadow(int(im.width * 0.66), int(W * 0.050), foot - 4))
    base.alpha_composite(im, (ox, oy))

    root, ext = os.path.splitext(dst)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    base.convert("RGB").save(dst)
    for s in (128, 64):
        base.convert("RGB").resize((s, s), Image.LANCZOS).save("%s_%d%s" % (root, s, ext))
    print("[icon]", dst, base.size)


if __name__ == "__main__":
    main()
