"""icon_post.py —— 图标的后期合成（Blender 自带的 Python 没有 PIL，所以拆出来）

    python blender/bs_v6/icon_post.py

输入：`assets/图标/_raw_<建筑>.png`（透明底，icon_shots.py 出的）
输出：
    <建筑>_图标.png        512² 卡面（RTS 图标形态：暗底 + 金线框 + 暖冷对比）
    <建筑>_图标_128.png    建造按钮
    <建筑>_图标_64.png     地图 / 快捷键格
    <建筑>_图标_透明.png   512² 透明底（给 UI 自己画底板的场合）

为什么图标不能直接用透明底那张：一套图标里最要紧的是**剪影从背景里跳出来**。
模型是"冷灰石 + 深蓝瓦"，透明底一旦贴上任意 UI，深蓝屋面就和深色界面糊成一片。
所以图标要自带背景：暖石色底板（冷色建筑的最大对比）+ 中心提亮 + 底部渐隐 + 暗角。
"""

import os
import sys

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter

ROOT = r"D:/测试一"
SRC = os.path.join(ROOT, "docs", "_tmp", "图标原图")
from assets_path import asset_path  # noqa: E402
DOC = os.path.join(ROOT, "docs", "图标")

# 单位图标：和建筑同一张卡面、同一套后期，只是源图由 icon_units.py 出（直接导 GLB）
UNITS = ("剑士", "方块人_农民", "方块人_弩兵", "方块人_矮人火枪手",
         "方块人_联盟步兵", "破法者", "魔金傀儡", "豺狼人战士", "豺狼人斥候",
         "骑士", "豺狼人萨满")

BUILDINGS = ("铁匠铺", "兵营", "城镇大厅", "哨塔", "箭塔", "农场", "伐木场",
             "神秘圣地", "蒸汽车坊",
             "地牢", "地下城入口", "酒馆内部", "营火", "火把", "火炬", "火堆",
             "折壳入口", "城镇大厅二本", "初级帐篷", "中等帐篷", "豪华帐篷")
S = 512

# 背板：暖石色，上浅下深。数值是实拍比出来的（见 docs/图标/底面对照.png）
BG_TOP = (152, 140, 120)
BG_BOT = (22, 18, 14)
VIG = 0.42          # 暗角强度
FADE = 0.13         # 底部渐隐高度（占画面）
SHADOW_OP = 0.42
BLOOM = 0.75
BLOOM_STRENGTH = {"神秘圣地": 0.55, "地下城入口": 0.50, "地牢": 0.42}
SIZES = (128, 64)

# 神秘圣地的自发光是**冷紫**（水晶 / 发光门 / 教堂窗）。用另六座那种暖橙 bloom
# 会把紫水晶糊成脏粉；阈值也要低一档 —— 紫在红通道上本来就偏暗。
BLOOM_COLOR = {"神秘圣地": (150, 108, 255), "地下城入口": (90, 235, 190), "地牢": (90, 235, 190)}
# 只用阈值不行：**被照亮的中灰石墙 r≈0.72，也在阈值之上**，整座建筑会被糊上一层紫。
# 所以神秘圣地额外加一道"蓝多于红"的色度门（chroma）—— 暖石 b−r 是负的，紫水晶是 +0.2。
BLOOM_THRESH = {"神秘圣地": 0.45}
BLOOM_CHROMA = {"神秘圣地": 0.10}

# 单位的自发光只有秘法支线那两件（青 #4FD8FF 的眼缝 / 量纹 / 熔炉口）。
# 暖橙 bloom 会把青糊成脏黄，所以给它们单独一组参数 + 蓝多于红的色度门：
# 傀儡整件是亮金（r 通道很高），不加门的话整块身体都会被算进 bloom。
BLOOM_COLOR_UNIT = {"破法者": (118, 206, 255), "魔金傀儡": (108, 198, 255)}
BLOOM_THRESH_UNIT = {"破法者": 0.55, "魔金傀儡": 0.52}
BLOOM_STR_UNIT = {"破法者": 0.62, "魔金傀儡": 0.55}
BLOOM_CHROMA_UNIT = {"破法者": 0.04, "魔金傀儡": 0.02}


# ── 基础 ────────────────────────────────────────────────────────────────────
def radial(size, center, radius, inner, outer, power=2.0, small=96):
    img = Image.new("RGB", (small, small))
    px = img.load()
    cx, cy = center[0] * small, center[1] * small
    r = radius * small
    for y in range(small):
        for x in range(small):
            d = (((x - cx) ** 2 + (y - cy) ** 2) ** 0.5) / max(r, 1e-6)
            t = min(1.0, d) ** power
            px[x, y] = tuple(int(inner[i] * (1 - t) + outer[i] * t) for i in range(3))
    return img.resize((size, size), Image.BICUBIC)


def vgrad(size, top, bot, power=1.0):
    img = Image.new("RGB", (1, size))
    px = img.load()
    for y in range(size):
        t = (y / (size - 1)) ** power
        px[0, y] = tuple(int(top[i] * (1 - t) + bot[i] * t) for i in range(3))
    return img.resize((size, size), Image.BICUBIC)


def contact_shadow(im, op=SHADOW_OP):
    """接地阴影：图标没有地面，纯剪影会"飘"。"""
    box = im.split()[3].getbbox()
    if not box:
        return im
    x0, y0, x1, y1 = box
    w = x1 - x0
    cx = (x0 + x1) * 0.5
    eh = max(8, int(im.size[0] * 0.05))
    ew = w * 0.90
    cy = y1 - eh * 0.5
    lay = Image.new("L", im.size, 0)
    ImageDraw.Draw(lay).ellipse([cx - ew / 2, cy - eh / 2, cx + ew / 2, cy + eh / 2], fill=255)
    lay = lay.filter(ImageFilter.GaussianBlur(eh * 0.60)).point(lambda v: int(v * op))
    sh = Image.new("RGBA", im.size, (8, 7, 6, 0))
    sh.putalpha(lay)
    return Image.alpha_composite(sh, im)


def bottom_fade(im, frac=FADE):
    """底边渐隐：地台被画框切断时，硬边看起来像"模型被裁了"。

    只削 alpha、不动颜色，所以地台是**淡出到背板里**，不是变暗。
    """
    w, h = im.size
    a = im.split()[3]
    mask = Image.new("L", (w, h), 255)
    d = ImageDraw.Draw(mask)
    y0 = int(h * (1 - frac))
    for y in range(y0, h):
        t = (y - y0) / max(1, h - y0)
        d.line([(0, y), (w, y)], fill=int(255 * (1 - t * 0.92)))
    a = ImageChops.multiply(a, mask)
    out = im.copy()
    out.putalpha(a)
    return out


def back_shadow(im, dy=14, blur=16, op=0.38):
    """建筑投在背板上的影子：把它从"贴图"变成"摆在场景里的物件"。"""
    a = im.split()[3].point(lambda v: int(v * op))
    sh = Image.new("RGBA", im.size, (8, 6, 5, 0))
    sh.putalpha(a)
    sh = sh.transform(im.size, Image.AFFINE, (1, 0, 0, 0, 1, -dy), resample=Image.BILINEAR)
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    return Image.alpha_composite(sh, im)


def bloom(im, thresh=0.60, radius=16, strength=BLOOM, color=(255, 146, 58), chroma=None):
    """炉火自发光在 EEVEE Next 里没有 bloom 了，后期补一层暖光。

    chroma 给定时只让"蓝明显多于红"的像素发光 —— 冷紫自发光要用它，
    否则被照亮的中灰石墙（r 0.72、b 0.68）也会被算进 bloom。
    """
    r, g, b, a = im.split()
    m = ImageChops.multiply(r, a).point(
        lambda v: 0 if v < thresh * 255 else int((v - thresh * 255) * 2.6))
    if chroma is not None:
        cut = int(128 + chroma * 255)
        gate = ImageChops.subtract(b, r, scale=1.0, offset=128).point(
            lambda v: 255 if v > cut else 0)
        m = ImageChops.multiply(m, gate)
    m = ImageChops.multiply(m, a)
    glow = Image.new("RGBA", im.size, tuple(color) + (0,))
    glow.putalpha(m.filter(ImageFilter.GaussianBlur(radius)))
    return Image.alpha_composite(im, ImageEnhance.Brightness(glow).enhance(strength))


def soft_edge(im, px=2, color=(32, 27, 22), op=0.40):
    """卡面用的"软描边"：先膨胀 2 px 再模糊 1.2 px。

    硬描边（1 px MaxFilter）在 512 上看是锯齿线，尤其垛口这种碎边 —— 放大就是瑕疵。
    软边读起来是"边上压了一点暗"，既分得开又不抢主体。
    """
    a = im.split()[3]
    ring = a.filter(ImageFilter.MaxFilter(px * 2 + 1))
    ring = ring.filter(ImageFilter.GaussianBlur(1.2))
    ring = ring.point(lambda v: int(v * op))
    lay = Image.new("RGBA", im.size, color + (0,))
    lay.putalpha(ring)
    return Image.alpha_composite(lay, im)


def outline(im, px=1, color=(22, 26, 34), op=0.42):
    """透明底版本：剪影外侧 1 px 暗边，浅色 UI 上也能分出轮廓。"""
    a = im.split()[3]
    hard = a.point(lambda v: 255 if v > 8 else 0)
    ring = a.filter(ImageFilter.MaxFilter(px * 2 + 1))
    ring = Image.composite(ring, Image.new("L", im.size, 0),
                           Image.eval(hard, lambda v: 255 - v))
    ring = ring.point(lambda v: int(v * op))
    lay = Image.new("RGBA", im.size, color + (0,))
    lay.putalpha(ring)
    return Image.alpha_composite(lay, im)


def frame(rgb):
    """金线卡框：外深边 + 1 px 金 + 内深线。这是"这是 UI 图标"最省事的信号。"""
    d = ImageDraw.Draw(rgb)
    w, h = rgb.size
    for i, col, wd in ((0, (10, 12, 17), 2), (1, (18, 21, 28), 1),
                       (2, (150, 118, 58), 1), (3, (34, 38, 48), 1)):
        d.rounded_rectangle([i, i, w - 1 - i, h - 1 - i], radius=22 - i, outline=col, width=wd)
    return rgb


def card(raw_path, out_path, bloom_color=(255, 146, 58), bloom_thresh=0.60,
         bloom_strength=BLOOM, bloom_chroma=None, grad_power=2.10, bg_scale=1.0):
    b = Image.open(raw_path).convert("RGBA")
    b = bottom_fade(b, FADE)
    # 描边要在投影之前：先描建筑，再压阴影，否则阴影椭圆也会被描一圈
    b = soft_edge(b)
    b = contact_shadow(b)
    b = back_shadow(b)
    # 单位的剪影比建筑矮一大截，画面大部分落在渐变的上半段（浅），
    # 直接沿用建筑的 2.10 会显得"发白"。grad_power 提前压暗、bg_scale 再压一档。
    top = tuple(int(c * bg_scale) for c in BG_TOP)
    bg = vgrad(S, top, BG_BOT, grad_power)
    # 中心提亮：让建筑所在区域比四角亮一档，视线自然落在主体上
    # 注意：ImageChops.add 的 scale 是**除法**（(a+b)/scale），早先传 1.6 等于整张背板压暗一半，
    # 结果底板一直是"深棕色"。要提亮就调亮度，不要动 scale。
    lift = radial(S, (0.50, 0.52), 0.66, (34, 29, 22), (0, 0, 0), 1.7)
    bg = ImageChops.add(bg, lift)
    img = Image.alpha_composite(bg.convert("RGBA"), b)
    img = bloom(img, thresh=bloom_thresh, color=bloom_color, strength=bloom_strength,
                chroma=bloom_chroma)
    # 暗角
    m = radial(S, (0.5, 0.46), 0.80, (255, 255, 255), (0, 0, 0), 1.6).convert("L")
    rgb = Image.composite(img.convert("RGB"),
                          Image.blend(img.convert("RGB"),
                                      Image.new("RGB", img.size, (12, 10, 8)), VIG), m)
    rgb = ImageEnhance.Color(rgb).enhance(1.05)
    rgb = ImageEnhance.Contrast(rgb).enhance(1.03)
    rgb = frame(rgb)
    rgb.save(out_path, "PNG", optimize=True)
    return img.size


def unit_dir(key):
    """单位图标写到它自己的资产文件夹（单位/联盟/<名>/<名>_图标.png）。"""
    root = os.path.join(ROOT, "assets", "单位")
    for dirpath, _, files in os.walk(root):
        if key + ".glb" in files:
            return dirpath
    return None


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else ""
    if only in ("单位", "units"):
        for key in UNITS:
            raw = os.path.join(SRC, "_raw_%s.png" % key)
            dst = unit_dir(key)
            if not os.path.exists(raw) or dst is None:
                print("skip", key)
                continue
            master = os.path.join(dst, "%s_图标.png" % key)
            card(raw, master, grad_power=1.55, bg_scale=0.80,
                 bloom_color=BLOOM_COLOR_UNIT.get(key, (255, 146, 58)),
                 bloom_thresh=BLOOM_THRESH_UNIT.get(key, 0.60),
                 bloom_strength=BLOOM_STR_UNIT.get(key, BLOOM),
                 bloom_chroma=BLOOM_CHROMA_UNIT.get(key))
            big = Image.open(master).convert("RGB")
            for s in SIZES:
                small = big.resize((s, s), Image.LANCZOS)
                small = small.filter(ImageFilter.UnsharpMask(radius=1.0, percent=55,
                                                             threshold=2))
                small.save(os.path.join(dst, "%s_图标_%d.png" % (key, s)), "PNG",
                           optimize=True)
            print("[unit icon]", key, os.path.getsize(master))
        return

    for key in BUILDINGS:
        raw = os.path.join(SRC, "_raw_%s.png" % key)
        if not os.path.exists(raw):
            print("skip", key)
            continue
        dst = asset_path(key)
        os.makedirs(dst, exist_ok=True)
        master = os.path.join(dst, "%s_图标.png" % key)
        card(raw, master, BLOOM_COLOR.get(key, (255, 146, 58)),
             BLOOM_THRESH.get(key, 0.60), BLOOM_STRENGTH.get(key, BLOOM),
             BLOOM_CHROMA.get(key))
        big = Image.open(master).convert("RGB")
        for s in SIZES:
            small = big.resize((s, s), Image.LANCZOS)
            # 缩小后再锐化一次：512 上的细节在 64 上会糊
            small = small.filter(ImageFilter.UnsharpMask(radius=1.0, percent=55, threshold=2))
            small.save(os.path.join(SRC, "%s_图标_%d.png" % (key, s)), "PNG", optimize=True)
        flat = outline(Image.open(raw).convert("RGBA"))
        flat.save(os.path.join(SRC, "%s_图标_透明.png" % key), "PNG", optimize=True)
        print("[icon]", key, os.path.getsize(master))


if __name__ == "__main__":
    main()
