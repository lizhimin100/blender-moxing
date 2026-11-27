# -*- coding: utf-8 -*-
"""a_farm.py —— 农场 · 三档（非塔类）

母题：**大坡谷仓 + 筒仓 + 风车叶**。
    1★ 半木构农舍 + 麦田 + 木栅栏 + 草捆      占地 0.768  高 0.625
    2★ 大谷仓（山墙朝前、双开大门）+ 筒仓      占地 0.928  高 0.802
    3★ + 风车塔（四叶队色帆）+ 板车 + 稻草人   占地 0.938  高 0.93

三条不动的线：
    · 1★→2★→3★ 是"变宽变厚"：占地 0.77 / 0.93 / 0.94，高度 0.625 / 0.802 / 0.93；
    · 屋顶语法两套：农舍 = 横脊厚檐蓝瓦（tiled_roof），谷仓 = 竖脊大坡（tiled_roof_y），
      筒仓顶与风车帆是队色，麦田是"麦"色 —— 三处队色分布在三个高度上；
    · 96 px 识别件：**大坡谷仓山墙**（1★ 小、2★ 起霸占画面）与 **风车四叶**（3★）。

面数账（1500 硬线）：
    素盒 12 / 倒角盒 44 / 三棱山墙板 12 / 六边盾 20 / 瓦垄一道 12 / 门 detail2 84
    1★ 用"全细节"，2★/3★ 把农舍降为 lean（窗无框、门 detail1、屋面 n=2）——
    省下来的面全给谷仓山墙与风车叶这两个识别件。
"""
import math

import akit
from akit import G, Z0          # noqa: F401


# ================================================================ 局部零件

def plank_wall(B, w, d, z0, h, at=(0.0, 0.0), role="木", batten="木亮",
               n=5, faces="YX", t=0.012):
    """木板墙：木身 + 竖向板条。板条咬进墙 6 mm，绝不与墙面共面。

    板条是"谷仓"和"木盒子"的分界：96 px 上一排竖线就读成"钉起来的板"。
    """
    x, y = at
    B.box("板墙", w, d, h, z0, role, 0.006, at=at)
    if "Y" in faces:
        for i in range(n):
            u = -w / 2 + w * (i + 0.5) / n
            B.box("板条Y%d" % i, w / n * 0.36, t, h * 0.92, z0 + 0.004,
                  batten, 0.0, at=(x + u, y + d / 2))
    if "X" in faces:
        for i in range(n):
            v = -d / 2 + d * (i + 0.5) / n
            B.box("板条X%d" % i, t, d / n * 0.36, h * 0.92, z0 + 0.004,
                  batten, 0.0, at=(x + w / 2, y + v))


def double_door(B, at, w, h, z, lintel="石亮", leaf="木", straps=1,
                surround=True):
    """双开仓门：亮石门套 → 暗洞 → 两扇 → 中梃 → 铁箍 → 石门楣。

    深色木板墙上的门必须靠**亮石套**才读得出来（深门洞 × 深木墙 = 一团黑）；
    中梃（浅木竖条）是"双开"的唯一证据，12 tri 换一个"两扇"。
    """
    x, y = at
    B.plate("仓门洞", [(-w / 2, 0.0), (w / 2, 0.0), (w / 2, h), (-w / 2, h)],
            0.010, "洞", (x, y + 0.004, z), "Y")
    for s in (-1, 1):
        pts = [(s * 0.007, 0.005), (s * w * 0.46, 0.005),
               (s * w * 0.46, h * 0.955), (s * 0.007, h * 0.955)]
        B.plate("仓门扇%d" % s, pts, 0.012, leaf, (x, y + 0.010, z), "Y")
        for k in range(straps):
            B.box("仓门箍%d%d" % (s, k), w * 0.36, 0.005, 0.008,
                  z + h * (0.28 + 0.36 * k), "铁", 0.0,
                  at=(x + s * w * 0.250, y + 0.018))
        if surround:
            B.box("门套%d" % s, 0.024, 0.024, h + 0.034, z - 0.004, "石亮", 0.0,
                  at=(x + s * (w / 2 + 0.012), y + 0.006))
    B.box("门中梃", 0.016, 0.020, h * 0.95, z + 0.004, "木亮", 0.0,
          at=(x, y + 0.012))
    B.box("仓门楣", w + 0.050, 0.022, 0.018, z + h + 0.004, lintel, 0.0,
          at=(x, y + 0.008))


def barn(B, at, w, d, wall_h, rise, n_batten=5, door_w=0.176, loft=False,
         corners=2, straps=1):
    """谷仓：石基 + 木板墙 + 角柱 + 双开大门 + 竖脊大坡蓝瓦顶（山墙朝 +Y）。

    corners=2 只做正面两根角柱 —— 后角在 96 px 上永远被屋顶吃掉，省 24 tri。
    """
    x, y = at
    YF = y + d / 2
    B.box("仓基", w + 0.034, d + 0.034, 0.032, G, "石暗", 0.0, at=at)
    z0 = G + 0.030
    plank_wall(B, w, d, z0, wall_h, at=at, role="木", batten="木亮",
               n=n_batten, faces="YX", t=0.012)
    for sx in (-1, 1):
        if corners >= 2:
            B.box("仓角%d" % sx, 0.032, 0.032, wall_h + 0.010, z0, "木暗", 0.0,
                  at=(x + sx * (w / 2 - 0.004), y + d / 2 - 0.004))
        if corners >= 4:
            B.box("仓角后%d" % sx, 0.032, 0.032, wall_h + 0.010, z0, "木暗",
                  0.0, at=(x + sx * (w / 2 - 0.004), y - d / 2 + 0.004))

    dh = min(wall_h * 0.74, 0.212)
    double_door(B, (x, YF), door_w, dh, z0 + 0.004, straps=straps)

    zt = z0 + wall_h
    akit.tiled_roof_y(B, w + 0.094, d + 0.104, zt, zt + rise, at=at, n=2,
                      ridge="木暗", gable="木亮", throat=0.018)
    if loft:
        gy = y + (d + 0.104) / 2 - 0.004
        zl = zt + rise * 0.17
        B.plate("仓楼门", [(-0.030, 0.0), (0.030, 0.0), (0.030, 0.060),
                          (-0.030, 0.060)], 0.010, "洞", (x, gy + 0.004, zl), "Y")
        B.box("仓楼楣", 0.086, 0.016, 0.013, zl + 0.060, "木暗", 0.0,
              at=(x, gy + 0.005))
    return zt + rise


def silo(B, at, r, h, roof_h, sides=10, hoops=2):
    """筒仓：石基座 + 十边仓身 + 铁箍 + 锥形队色顶 + 金顶珠。"""
    B.box("仓座", r * 2 + 0.030, r * 2 + 0.030, 0.024, G, "石暗", 0.0, at=at)
    z0 = G + 0.022
    B.cyl("筒身", r, h, z0, sides, "灰泥", at=at, r_top=r * 0.97)
    for i in range(hoops):
        B.cyl("筒箍%d" % i, r + 0.004, 0.010, z0 + h * (0.20 + 0.64 * i / max(1, hoops - 1)),
              sides, "铁暗", at=at, cap=False)
    B.cyl("筒檐", r + 0.014, 0.014, z0 + h - 0.008, sides, "木暗", at=at)
    B.cyl("筒顶", r + 0.004, roof_h, z0 + h - 0.004, sides, "瓦", at=at,
          r_top=0.016)
    B.cyl("筒珠", 0.014, 0.016, z0 + h - 0.004 + roof_h, 6, "金", at=at,
          r_top=0.008)


def stack(B, at, w, z0, h, role="石", cap="石亮"):
    """石烟囱：下粗上细两段 + 压顶 + 烟口。

    烟口**压在压顶之上 4 mm** —— akit.chimney 的烟口和压顶顶面在 h≈0.6 时
    只差 0.25 mm，体检 ⑥ 会判共面，所以这里自己算高度。
    """
    x, y = at
    B.box("烟囱下", w, w, h * 0.66, z0, role, 0.005, at=at)
    B.box("烟囱上", w * 0.82, w * 0.82, h * 0.34, z0 + h * 0.64, "石暗", 0.0,
          at=at)
    B.box("烟囱帽", w * 0.98, w * 0.98, 0.016, z0 + h * 0.98, cap, 0.0, at=at)
    B.box("烟口", w * 0.50, w * 0.50, 0.010, z0 + h * 0.98 + 0.010, "炭", 0.0,
          at=at)
    return z0 + h * 0.98 + 0.020


def farmhouse(B, at, w, d, wall_h, rise, door_w=0.086, chimney=None,
              lean=False, win_n=2, fascia=True):
    """半木构农舍：石脚 + 灰泥木架墙 + 蓝瓦双坡 + 小门 + 窗（+ 石烟囱）。

    lean=True：屋面 2 道瓦垄 / 无博风 / 无山花窗 / 窗无框 / 门 detail1。
    2★ 起农舍退成配角，省下来的 200 tri 全给谷仓。
    """
    x, y = at
    YF = y + d / 2
    B.box("农舍脚", w + 0.032, d + 0.032, 0.032, G, "石暗",
          0.0 if lean else 0.008, at=at)
    z0 = G + 0.030
    zt = akit.timber_wall(B, w, d, z0, wall_h, at=at, studs=2, brace=True,
                          rail=0.50)
    B.box("农舍檐影", w + 0.026, d + 0.026, 0.011, zt - 0.002, "石暗", 0.0,
          at=at)
    if not lean:
        B.box("农舍檐口", w + 0.034, d + 0.034, 0.010, zt + 0.007, "石亮", 0.0,
              at=at)
    akit.tiled_roof(B, w + 0.086, d + 0.106, zt + 0.017, zt + 0.017 + rise,
                    at=at, n=2 if lean else 3, ridge="木暗", gable="灰泥",
                    gable_window=0.0 if lean else 0.026, fascia=fascia,
                    barge=not lean, barge_back=False)
    akit.door(B, x, YF, z0 + 0.006, door_w, wall_h * 0.64, role="木",
              frame="木暗", studs=1, trim="金", plate=True,
              detail=1 if lean else 2)
    for s in (-1, 1)[:win_n]:
        akit.win(B, w * 0.115, wall_h * 0.26,
                 (x + s * w * 0.33, YF + 0.001, z0 + wall_h * 0.42),
                 "洞", None if lean else "木暗", "Y")
    if win_n > 2:
        akit.win(B, d * 0.16, wall_h * 0.26,
                 (x + w / 2 + 0.001, y, z0 + wall_h * 0.42),
                 "洞", None if lean else "木暗", "X")
    if chimney:
        cx, cy, ch, cw = chimney
        stack(B, (x + cx, y + cy), cw, G, ch)
    return zt + 0.017 + rise


def sails(B, at, r, blades=4, role="旗", spar="木暗", a0=0.18):
    """风车叶：4 片梯形队色帆 + 木龙骨 + 金毂。

    帆必须**成板**：每片从 r=2 cm 长到 r，梢宽 8.6 cm，96 px 下是四道蓝刀；
    细杆只会读成天线。风扇轴在 y 方向，叶片钉在 XZ 平面上。
    """
    x, y, zz = at
    for i in range(blades):
        a = a0 + 2 * math.pi * i / blades
        ca, sa = math.cos(a), math.sin(a)
        px, pz = -sa, ca
        r0, r1 = 0.020, r
        w0, w1 = 0.034, 0.086
        pts = [(px * w0 / 2 + ca * r0, pz * w0 / 2 + sa * r0),
               (px * w1 / 2 + ca * r1, pz * w1 / 2 + sa * r1),
               (-px * w1 / 2 + ca * r1, -pz * w1 / 2 + sa * r1),
               (-px * w0 / 2 + ca * r0, -pz * w0 / 2 + sa * r0)]
        B.plate("帆%d" % i, pts, 0.010, role, (x, y, zz), "Y")
        # 龙骨只在迎风边（画在帆面中线会把蓝帆劈成两半）
        B.beam("帆骨%d" % i,
               (x + ca * 0.008 + px * w0 * 0.5, y - 0.004,
                zz + sa * 0.008 + pz * w0 * 0.5),
               (x + ca * r1 + px * w1 * 0.5, y - 0.004,
                zz + sa * r1 + pz * w1 * 0.5), 0.013, 0.011, spar)
    B.disc("帆毂", 0.026, 0.018, (x, y + 0.006, zz), "金", 8, "Y")


def windmill_tower(B, at, w0, w1, top, blade_r, blade_z):
    """风车塔：石基 → 收分方塔（下粗上细）→ 木帽 + 金珠 → 四片队色帆。

    **收分**是"磨坊"和"烟囱"的区别；帽用木色，队色全部留给帆 ——
    筒仓是蓝锥、风车是蓝扇，两种剪影互不打架。
    """
    x, y = at
    B.box("磨基", w0 + 0.046, w0 + 0.046, 0.032, G, "石暗", 0.0, at=at)
    z0 = G + 0.030
    h = top - z0
    v = [(-w0 / 2, -w0 / 2, 0), (w0 / 2, -w0 / 2, 0),
         (w0 / 2, w0 / 2, 0), (-w0 / 2, w0 / 2, 0),
         (-w1 / 2, -w1 / 2, h), (w1 / 2, -w1 / 2, h),
         (w1 / 2, w1 / 2, h), (-w1 / 2, w1 / 2, h)]
    f = [(0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5),
         (2, 3, 7, 6), (3, 0, 4, 7)]
    B.part("磨身", [(p[0] + x, p[1] + y, p[2] + z0) for p in v], f, "石",
           0.008, 1, "all")
    # 收分塔身的外表面是斜的：贴面件必须按"该高度的塔宽"算，
    # 否则腰箍会被埋进塔里、门板下半截沉进墙里（v1 的坑）。
    wm = w0 + (w1 - w0) * 0.36
    B.box("磨腰箍", wm + 0.014, wm + 0.014, 0.014, z0 + h * 0.36, "木暗", 0.0,
          at=at)
    B.box("磨门", 0.060, 0.030, 0.076, z0 + 0.004, "洞", 0.0,
          at=(x, y + w0 / 2 - 0.004))
    # 木帽 + 金顶珠
    B.box("磨帽檐", w1 + 0.030, w1 + 0.030, 0.014, top - 0.008, "木暗", 0.0, at=at)
    B.pyramid("磨帽", w1 + 0.014, w1 + 0.014, 0.078, top + 0.004, "木", at=at)
    B.cyl("磨珠", 0.009, 0.012, top + 0.080, 6, "金", at=at, r_top=0.005)
    # 帆轴 + 四叶
    sy = y + w1 / 2 + 0.020
    B.box("帆轴", 0.034, 0.070, 0.034, blade_z - 0.017, "木暗", 0.0,
          at=(x, sy - 0.035))
    sails(B, (x, sy, blade_z), blade_r)
    return blade_z + blade_r


def scarecrow(B, at, z=G, h=0.190):
    x, y = at
    B.box("稻杆", 0.014, 0.014, h, z, "木暗", 0.0, at=(x, y))
    B.box("稻臂", 0.120, 0.012, 0.012, z + h * 0.72, "木暗", 0.0, at=(x, y))
    B.box("稻衣", 0.058, 0.034, h * 0.36, z + h * 0.34, "布暗", 0.0, at=(x, y))
    B.box("稻头", 0.036, 0.032, 0.034, z + h * 0.82, "布", 0.0, at=(x, y))
    B.cyl("草帽", 0.034, 0.012, z + h * 0.94, 8, "麦", at=(x, y), r_top=0.008)


# ================================================================ 1★

def s1(B):
    """半木构农舍（左）+ 麦田（右前）+ 木栅栏 + 草捆。蓝瓦双坡，正面小门 + 窗。"""
    B.base()
    with B.group("场地"):
        akit.yard(B, 0.700, 0.680, at=(0.0, 0.010))
        akit.apron(B, 0.160, 0.086, G, "石暗", (-0.100, 0.156))

    with B.group("农舍"):
        farmhouse(B, (-0.100, -0.040), 0.400, 0.300, 0.212, 0.200,
                  door_w=0.086, win_n=3,
                  chimney=(0.090, -0.030, 0.575, 0.058))

    with B.group("麦田"):
        akit.wheat_field(B, 0.230, 0.250, G, rows=4, at=(0.208, 0.176), sheaves=3)

    with B.group("栅栏"):
        akit.fence(B, -0.318, 0.046, 0.318, G, h=0.108, n=3, rails=2)

    with B.group("草捆"):
        akit.hay(B, (-0.238, 0.238), G)
        akit.hay(B, (-0.156, 0.258), G)


# ================================================================ 2★

def s2(B):
    """农舍退到右前，大谷仓占中（山墙朝前、双开大门），左后筒仓压住天际线。"""
    B.base()
    with B.group("场地"):
        akit.yard(B, 0.840, 0.800, at=(0.0, 0.0))
        akit.apron(B, 0.230, 0.096, G, "石暗", (0.060, 0.140))

    with B.group("谷仓"):
        barn(B, (0.050, -0.100), 0.500, 0.360, 0.300, 0.205, n_batten=5,
             loft=True)

    with B.group("筒仓"):
        # 直径 0.23 / 锥高 0.15（0.65:1）：锥顶比直径高就会读成"魔法帽"。
        # 位置内移：r 变大后 (±0.348 + 0.115 + 0.03) 会顶出 0.470 的占地线。
        silo(B, (-0.322, -0.104), 0.115, 0.506, 0.150)

    with B.group("农舍"):
        farmhouse(B, (0.252, 0.250), 0.240, 0.196, 0.160, 0.140,
                  door_w=0.070, lean=True, win_n=1)

    with B.group("麦田"):
        akit.wheat_field(B, 0.230, 0.150, G, rows=4, at=(-0.158, 0.286), sheaves=3)

    with B.group("栅栏"):
        akit.fence(B, -0.338, -0.060, 0.362, G, h=0.108, n=3, rails=2)

    with B.group("草捆"):
        akit.hay(B, (-0.336, 0.216), G)
        akit.hay_bale(B, (0.196, 0.150), G, 0.074, 0.048, 0.044, 0.26)


# ================================================================ 3★

def s3(B):
    """谷仓再宽 + 筒仓 + **风车塔**（队色四叶）+ 麦田成垄 + 板车 + 稻草人 + 草捆堆。

    布局按相机排（相机在 +X/+Y，画面上 +X 在左）：
        左前 = 风车（识别件放最显眼处，帆面正对相机）
        中后 = 谷仓（山墙朝前）／右后 = 筒仓／右前 = 农舍／中前 = 麦田
    """
    B.base()
    with B.group("场地"):
        akit.yard(B, 0.920, 0.900, at=(0.0, 0.0))

    with B.group("谷仓"):
        barn(B, (0.048, -0.130), 0.480, 0.360, 0.320, 0.210,
             n_batten=5, corners=0, loft=True)

    with B.group("筒仓"):
        silo(B, (-0.318, -0.140), 0.118, 0.452, 0.152, sides=8)

    with B.group("风车"):
        windmill_tower(B, (0.260, 0.272), 0.256, 0.190, 0.780, 0.190, 0.760)

    with B.group("农舍"):
        farmhouse(B, (-0.270, 0.290), 0.260, 0.200, 0.166, 0.146,
                  door_w=0.072, lean=True, win_n=2, fascia=False)

    with B.group("麦田"):
        akit.wheat_field(B, 0.220, 0.150, G, rows=3, at=(-0.020, 0.310), sheaves=3)

    with B.group("板车"):
        akit.cart(B, (0.020, 0.190), G, 0.130, 0.066, 0.10)

    with B.group("稻草人"):
        scarecrow(B, (0.000, 0.300), G, 0.172)

    with B.group("草捆"):
        akit.hay_bale(B, (-0.262, 0.040), G, 0.076, 0.050, 0.044, 0.0)
        akit.hay_bale(B, (-0.262, 0.040), G + 0.044, 0.074, 0.048, 0.042, 0.0)


# ================================================================ 装配

def build(star, pal=None):
    B = akit.new(pal)
    {1: s1, 2: s2, 3: s3}[star](B)
    ob = B.join("农场_%d星" % star)
    return ob, B


STAR_RANGE = akit.STAR_RANGE["非塔"]
TRI_RANGE = akit.TRI_RANGE
