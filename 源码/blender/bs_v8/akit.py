# -*- coding: utf-8 -*-
"""akit.py —— 《战争原岛》联盟微缩建筑零件库 v8（WC3 人族语法）

和 bs_v7 的 mkit/bk_model 的关系：**不共用零件、不共用验收口径**。
v7 是"沙盘摆件"，v8 是"厚重要塞"，两者唯一的共同点是底座尺寸。

--------------------------------------------------------------------------
一、这一版要解决的两个病
--------------------------------------------------------------------------
病 A：3★ 靠"把中间方块拔高" → 细高、像礼拜堂、像塔楼不像城堡。
     解法：**高度只涨 8~14 cm，占地涨 10 cm**。星级递进靠"占地 + 附属体量
     + 材质从木到石 + 城垛/角塔/金饰"，不靠层数。3★ 非塔类封顶 1.10 m。

病 B：兵营像民房。
     解法：兵营从 1★ 起就是**拱门 + 前庭 + 平顶垛口**，一次三角屋顶都不给。
     七座建筑的屋顶语法两两不同（见 docs/联盟七建筑_造型语法.md）。

--------------------------------------------------------------------------
二、硬约束（体检脚本按这些数字判）
--------------------------------------------------------------------------
| 项 | 值 |
|---|---|
| 底座 | 1.000 × 1.000 × 0.080，底面 z=0，只倒竖边+顶边 |
| 主体 | 所有非底座零件 |x|,|y| ≤ 0.470 |
| 高度 | 非塔 1★0.58–0.74 / 2★0.76–0.90 / 3★0.85–1.10；塔 1★0.90–1.05 / 2★1.08–1.24 / 3★1.25–1.45 |
| 面数 | 800–1500 / 栋（城镇大厅 3★ ≤ 2000） |
| 槽 | 恰好 2：Mat_Neutral（顶点色） / Mat_TeamColor（baseColor，默认 #2554A8） |
| 队色 | 可见面积 11–30%，顶点色纯白 |

--------------------------------------------------------------------------
三、体块纪律（决定"厚重"还是"纸片"）
--------------------------------------------------------------------------
1. **最小厚度**：承重墙 ≥ 0.05 m，装饰条 ≥ 0.012，旗 ≥ 0.006。
   在 1 m 的件上，0.03 的板就是 3 cm 厚的石头 —— 不能再薄。
2. **必倒角**：凡是"一整块石头/一整段木料"的体量，一律 bevel 0.006–0.010。
   倒角是硬表面唯一的"厚度证据"，也是 Weighted Normal 的着力点。
3. **出檐 ≥ 0.045**：屋檐不出挑就永远读成"盒子盖了个盖"。主屋面出檐 5–7 cm。
4. **明度三级**：墙（石/灰泥）→ 檐下暗带（石暗/木暗）→ 压顶（石亮/金）。
   三级少一级就糊成一坨；多一级在 512 px 上就是脏。
5. **一个体量只干一件事**：屋顶就是屋顶，不在屋面上再开窗；旗杆就是旗杆。
6. 共面：任何贴面件与墙面留 2–6 mm，且**中心必须在墙面之外**。
7. 浮空：小件要么咬进大件 3 mm，要么坐在 z=0 / 台基面上。

--------------------------------------------------------------------------
四、坐标系
--------------------------------------------------------------------------
Z 上、+Y 正面（导出后 glTF 朝 −Z，Godot 里正对相机）。
相机 3/4 在 +X/+Y 侧，所以正面与右立面都必须有细节，背面可以省。
"""
import contextlib
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
# mkit 留在 bs_v7（th_/bk_ 那条线还在用），这里只借它的 B 基类 / 材质 / 色板骨架。
# 两条线共用"壳体"，不共用"零件" —— v8 的造型件全部写在本文件里。
_V7 = os.path.join(os.path.dirname(HERE), "bs_v7")
if _V7 not in sys.path:
    sys.path.insert(0, _V7)

import mkit  # noqa: E402

Z0 = 0.080          # 底座顶面
TY = 0.008          # 场地土层
G = Z0 + TY         # 0.088 前庭地面

MAX_XY = 0.470      # 主体半宽上限（0.94 见方）

# 高度窗口：非塔类 3★ 必须 ≤1.10（用户硬约束）
STAR_RANGE = {
    "非塔": {1: (0.58, 0.74), 2: (0.76, 0.90), 3: (0.85, 1.10)},
    "塔":   {1: (0.90, 1.05), 2: (1.08, 1.24), 3: (1.25, 1.45)},
}
TRI_RANGE = {1: (800, 1500), 2: (800, 1500), 3: (800, 1500)}
TRI_RANGE_TH = {1: (800, 1500), 2: (800, 1500), 3: (800, 2000)}

# 占地（线性宽度，不是面积）：1★ 70% / 2★ 82% / 3★ 92%
FOOT = {1: 0.70, 2: 0.82, 3: 0.92}

# ---------------------------------------------------------------- 色板扩展
# 只加联盟这七座需要的四个本色，不动 mkit 的 PAL2（th_/bk_ 那批还在用）。
EXTRA_HEX = {
    "麦":   "#D8A838",   # 麦田金黄（规范锚点）
    "麦暗": "#B4862B",
    "炉":   "#FF6A20",   # 炉火橙红（规范锚点）
    "炭":   "#2A241E",
    "叶":   "#7C8A4A",
    "水":   "#557277",
    "铁亮": "#8A93A0",
    "铜":   "#A9713E",
}

# 队色角色的顶点色必须是纯白：ROLE2 里 T100 已经是 (1,1,1,1)
TEAM_ROLES = ("瓦", "瓦暗", "瓦亮", "旗", "旗暗", "盾", "门饰")


def _build_role_colors():
    role = dict(mkit.ROLE2)
    col = dict(mkit.PAL2)
    for k, v in EXTRA_HEX.items():
        role[k] = (k, "Mat_Neutral")
        col[k] = mkit.srgb(v)
    return role, col


ROLE, COL = _build_role_colors()


# ================================================================ 记账 builder

class A(mkit.B):
    """在 mkit.B 上加三件：分组记账、组件预算、常用组合。

    分组记账不是洁癖：1500 tri 的硬线里，只有"每类件花了多少"能告诉你
    该砍哪一件。靠感觉砍，砍掉的永远是剪影最重要的那件。
    """

    def __init__(self, pal=None):
        super().__init__(twoslot=True, pal=pal)
        self.role = ROLE
        self.colors = COL
        self.groups = []          # [(name, tris)]
        self._g0 = None
        self._gname = None

    @contextlib.contextmanager
    def group(self, name):
        t0 = self.tris()
        yield
        self.groups.append((name, self.tris() - t0))

    def recount(self):
        self.groups = []

    @staticmethod
    def vis_slot_area(ob):
        """可见面积占比：**排除朝下的面**（底面、檐下、零件底）。

        v7 的 team_area() 把底座 1 m² 的底面也算进分母，于是"平顶建筑"天生低：
        兵营 1★ 明明整片屋顶是队色，算出来只有 7%。人眼看不到楼板底，
        这个口径才是"缩到 96 px 能看见多少队色"的近似。
        """
        out = {}
        for p in ob.data.polygons:
            if p.normal.z < -0.25:
                continue
            name = ob.data.materials[p.material_index].name
            out[name] = out.get(name, 0.0) + p.area
        return out


def new(pal=None):
    return A(pal=pal)


# ================================================================ 场地 / 底座

def yard(B, w=0.760, d=0.760, z=Z0, role="土", thick=TY, at=(0.0, 0.0)):
    """场地土台：比主体外扩一圈，把建筑从棋盘格上"托"起来。"""
    B.box("场地", w, d, thick, z, role, 0.0, at=at)


def apron(B, w, d, z, role="石暗", at=(0.0, 0.0), t=0.010):
    """门前石铺：一块浅色薄台，压住台阶根部。"""
    B.box("石铺", w, d, t, z, role, 0.0, at=at)


def steps(B, w, n, zb, zt, y0, y1, role="台基"):
    """台阶：每级都从台基边往外长（居中会把最前一级顶出底座，这是老坑）。"""
    tread = (y1 - y0) / n
    hh = (zt - 0.002 - zb) / n
    for i in range(n):
        z = zt - 0.002 - hh * (i + 1)
        B.box("台阶%d" % i, w, tread * (i + 1), hh, z, role, 0.0,
              at=(0.0, y0 + tread * (i + 1) / 2))


# ================================================================ 墙体语法

def stone_wall(B, w, d, z0, h, at=(0.0, 0.0), skirt=0.052, quoins=True,
               cornice=True, plinth=True, bevel=0.008, base_role="台基",
               plinth_h=0.030):
    """石砌体量：台基 → 墙裙 → 墙 → 隅石 → 檐口。

    檐口是"石头房子"和"白盒子"的分界线：一条暗影线 + 一条亮压顶，
    24 tri 换一整圈厚度感。

    `plinth_h` 必须能改：两个体量咬在一起时，台基同厚会同高共面（体检 ⑥）。
    翼楼用 0.024，主厅 0.030 —— 6 mm 的差在画面上看不出来，在体检里是 PASS。
    """
    x, y = at
    zw = z0
    if plinth:
        B.box("台基", w + 0.046, d + 0.046, plinth_h, z0, base_role, 0.008, at=at)
        zw += plinth_h
    if skirt > 0:
        B.box("墙裙", w + 0.020, d + 0.020, skirt, zw, "石暗", 0.006, at=at)
    B.box("墙体", w, d, h, zw, "石", bevel, at=at)
    if quoins:
        # 只做正面两个角：相机在 +Y，后角的隅石一辈子看不见，白花 24 tri
        for sx in (-1, 1):
            B.box("隅石%d" % sx, 0.042, 0.042, min(0.070, h * 0.34),
                  zw, "石亮", 0.0, at=(x + sx * (w / 2 + 0.004), y + d / 2 - 0.021))
    if cornice:
        B.box("檐影", w + 0.030, d + 0.030, 0.012, zw + h - 0.001, "石暗", 0.0, at=at)
        B.box("檐口", w + 0.040, d + 0.040, 0.012, zw + h + 0.011, "石亮", 0.0, at=at)
    return zw + h + (0.023 if cornice else 0.0)


def timber_wall(B, w, d, z0, h, at=(0.0, 0.0), studs=2, brace=True, rail=0.52,
                jetty=0.0, t=0.016, role="木暗", plaster="灰泥"):
    """半木构：灰泥墙 + 角柱 + 腰枋 + 斜撑（+ 可选挑楼）。

    斜撑是"木架"和"木条贴纸"的区别。两根 45° 暗木横在米白墙上，
    96 px 下就是人族农舍的胎记。**所有木料贴在墙外**，绝不与墙面共面。
    """
    x, y = at
    B.box("灰泥墙", w, d, h, z0, plaster, 0.004, at=at)
    ox, oy = w / 2 + t / 2 - 0.002, d / 2 + t / 2 - 0.002
    for sx in (-1, 1):
        for sy in (-1, 1):
            B.box("角柱%d%d" % (sx, sy), t, t, h, z0, role, 0.0,
                  at=(x + sx * ox, y + sy * oy))
    B.box("腰枋", w - t * 0.4, t, t * 0.85, z0 + h * rail, role, 0.0,
          at=(x, y + oy))
    B.box("腰枋后", w - t * 0.4, t, t * 0.85, z0 + h * rail, role, 0.0,
          at=(x, y - oy))
    for i in range(studs):
        u = -w / 2 + w * (i + 1) / (studs + 1)
        B.box("立枋%d" % i, t * 0.8, t, h, z0, role, 0.0, at=(x + u, y + oy))
    if brace:
        # 两根斜撑：从柱脚斜到腰枋上 —— 方向必须一左一右，同向读成"歪了"
        for s in (-1, 1):
            u0 = s * (w / 2 - 0.012)
            u1 = s * (w / 2 - w * 0.30)
            B.beam("斜撑%d" % s, (x + u0, y + oy + 0.002, z0 + 0.004),
                   (x + u1, y + oy + 0.002, z0 + h * rail - 0.004),
                   t * 0.78, t * 0.62, role)
    if jetty > 0.0:
        # 挑楼：上层比下层宽 jetty，底下一圈暗木梁做"挑出的阴影"
        B.box("挑梁", w + jetty * 2 + 0.012, d + jetty * 2 + 0.012, 0.020,
              z0 + h - 0.004, "木暗", 0.0, at=at)
    return z0 + h


# ================================================================ 屋顶语法

def tiled_roof(B, w, d, z0, z1, at=(0.0, 0.0), n=4, ridge="金", gable="灰泥",
               fascia=True, barge=True, barge_back=True, gable_window=0.0,
               throat=0.020, ridge_t=0.030, tile_first=0.0062, tile_step=0.0034):
    """厚檐蓝瓦双坡顶（联盟的母语）。

    和 mkit.roof_tiled 的差别：`throat` 给到 2 cm（屋檐是一块厚板，不是纸）、
    檐下多一条暗木封檐、山墙从檐底起算（否则山墙悬空一条缝）、
    脊压顶按屋面同坡做小三棱柱（方条必然两端翘起，老坑）。

    `barge_back` 只给 1–2★ 关：背面山墙的博风板在 512 px 图标上永远看不见，
    48 tri 省下来就是一面盾。
    """
    x, y = at
    B.roof_tiled("屋顶", w, d, z0, z1, "瓦", at=at, n=n, throat=throat,
                 top_gap=0.052, inset=0.002, first=tile_first, step=tile_step,
                 overlap=0.016)
    rise = z1 - z0
    # 山墙：三角 + 山花窗；必须从 z0-throat 起，否则檐下露缝
    for s in (-1, 1):
        pts = [(-d / 2 + 0.012, -throat - 0.004), (d / 2 - 0.012, -throat - 0.004),
               (0.0, rise - 0.012)]
        B.plate("山墙%d" % s, pts, 0.012, gable, (x + s * (w / 2 - 0.004), y, z0), "X")
        if gable_window > 0.0:
            gw = gable_window
            B.plate("山花窗%d" % s,
                    [(-gw / 2, 0.0), (gw / 2, 0.0), (gw / 2, gw), (-gw / 2, gw)],
                    0.008, "洞", (x + s * (w / 2 + 0.004), y, z0 + rise * 0.30), "X")
        if barge and (s > 0 or barge_back):
            xx = x + s * (w / 2 + 0.006)
            for t in (-1, 1):
                B.beam("博风%d%d" % (s, t), (xx, y + t * (d / 2 - 0.010), z0 - throat),
                       (xx, y, z1 - 0.010), 0.014, 0.010, "木暗")
    if fascia:
        for s in (-1, 1):
            B.box("封檐%d" % s, w + 0.010, 0.026, 0.024, z0 - throat - 0.004,
                  "木暗", 0.0, at=(x, y + s * (d / 2 - 0.013)))
    # 脊压顶：与屋面同坡的小三棱柱（沿 X 的脊）
    slope = rise / (d / 2)
    B.roof_gable("脊压顶", w + 0.006, ridge_t, z1 + 0.004 - slope * ridge_t * 0.5,
                 z1 + 0.004, ridge, 0.0, at=(x, y), fascia=False)


def tiled_roof_y(B, w, d, z0, z1, at=(0.0, 0.0), n=3, ridge="金", gable="灰泥",
                 throat=0.018):
    """竖脊双坡（山墙面朝 +Y）：门廊 / 抱厦 / 谷仓的三角山花靠它。"""
    x, y = at
    B.roof_gable_y("屋顶Y", w, d, z0 - throat, z1, "瓦", at=at)
    rise = z1 - z0
    for s in (-1, 1):
        pts = [(-w / 2 + 0.012, -throat - 0.004), (w / 2 - 0.012, -throat - 0.004),
               (0.0, rise - 0.012)]
        B.plate("山墙Y%d" % s, pts, 0.012, gable, (x, y + s * (d / 2 - 0.004), z0), "Y")
    slope = rise / (w / 2)
    B.roof_gable_y("脊Y", 0.036, d + 0.006, z1 + 0.003 - slope * 0.018, z1 + 0.003,
                   "木暗", at=(x, y))
    # 瓦垄：竖向两坡各 3 道，读"瓦"而不读"蓝三角"
    for s in (-1, 1):
        for i in range(n):
            t0 = 0.12 + 0.72 * i / n
            t1 = t0 + 0.72 / n * 0.86
            xx0 = x + s * (w / 2 - 0.004) * (1 - t0)
            xx1 = x + s * (w / 2 - 0.004) * (1 - t1)
            zz0 = z0 + rise * t0
            zz1 = z0 + rise * t1
            B.slab4("瓦Y%d%d" % (s, i),
                    [(xx0, y - d / 2 + 0.008, zz0 + 0.006),
                     (xx1, y - d / 2 + 0.008, zz1 + 0.006),
                     (xx1, y + d / 2 - 0.008, zz1 + 0.006),
                     (xx0, y + d / 2 - 0.008, zz0 + 0.006)], 0.006,
                    "瓦暗" if i % 2 else "瓦")


def pyramid_roof(B, name, w, d, z0, h, at=(0.0, 0.0), role="瓦", cap="金",
                 over=0.030, fascia="木暗"):
    """四坡尖顶（角楼 / 筒仓）。一圈暗檐 + 一片队色锥 + 金顶珠。"""
    x, y = at
    # 檐板顶面 = z0 + 2 mm：塔顶面在 z0，留 2 mm 才不会判共面（差 0 就是 0 mm）
    B.box(name + "檐", w + over, d + over, 0.014, z0 - 0.012, fascia, 0.0, at=at)
    B.pyramid(name, w + over * 0.72, d + over * 0.72, h, z0 + 0.002, role, at=at)
    B.cyl(name + "珠", 0.008, 0.014, z0 + h - 0.002, 6, cap, at=at, r_top=0.010)


def hip_roof(B, name, w, d, z0, z1, at=(0.0, 0.0), role="瓦", ridge="金"):
    B.box(name + "檐", w + 0.040, d + 0.040, 0.018, z0 - 0.016, "木暗", 0.0, at=at)
    B.roof_hip(name, w, d, z0, z1, role, 0.004, at)
    B.box(name + "脊", w * 0.34, 0.030, 0.016, z1 - 0.004, ridge, 0.0, at=at)


# ================================================================ 石构 / 防御件

def buttress(B, at, w=0.062, h=0.230, proj=0.052, sgn=1, role="石", cap="石亮",
             steps=2, t=0.028):
    """阶梯状石砌斜撑扶壁（Buttress）—— 兵营 2★ 的"武装感"主要靠它。

    两段台阶 + 斜顶。斜顶不是装饰：直顶的扶壁读成"贴了一块砖"，
    斜顶才读"在受力"。sgn=+1 往 +Y 出挑，-1 往 −Y，±2 表示往 ±X。
    """
    x, y = at
    if abs(sgn) == 2:
        # 侧向扶壁：沿 X 出挑
        s = 1 if sgn > 0 else -1
        for i in range(steps):
            k = 1.0 - i * 0.34
            ww = proj * k + 0.010
            hh = h * (1.0 - i * 0.30)
            B.box("扶壁X%d" % i, ww, w, hh, 0.0, role, 0.0,
                  at=(x + s * (ww / 2 - 0.008), y))
            B.box("扶壁帽X%d" % i, ww * 0.9, w * 0.92, t, hh, cap, 0.0,
                  at=(x + s * (ww / 2 - 0.010), y))
        return
    for i in range(steps):
        k = 1.0 - i * 0.36
        dd = proj * k
        hh = h * (1.0 - i * 0.32)
        B.box("扶壁%d" % i, w, dd + 0.010, hh, 0.0, role, 0.0,
              at=(x, y + sgn * (dd / 2 - 0.006)))
        B.box("扶壁帽%d" % i, w * 0.94, dd * 0.92, t, hh, cap, 0.0,
              at=(x, y + sgn * (dd / 2 - 0.010)))


def crenel(B, name, x0, x1, y, z, n=3, t=0.028, h=0.030, d=0.030, role="石"):
    """一段垛口（沿 X）。垛宽 = 段长/n 的 55%，缝比垛窄 —— 缝太宽读成"断墙"。"""
    for i in range(n):
        x = x0 + (x1 - x0) * (i + 0.5) / n
        B.box("%s%d" % (name, i), (x1 - x0) / n * 0.55, d, h, z, role, 0.0,
              at=(x, y))


def crenel_rect(B, name, w, d, z, n=2, t=0.028, h=0.030, role="石",
                at=(0.0, 0.0)):
    """方形塔顶垛口（四边，每边 n 个）。**必须给 at**，否则整圈落在原点（老坑）。

    垛宽取段长的 44%：取 56% 时相邻两面的垛在转角处顶面相交 → COPLANAR_UP。
    44% 留下 12% 的缝，转角自然脱开，剪影还更"齿"。
    """
    ox, oy = at
    for s in (-1, 1):
        for i in range(n):
            u = -w / 2 + w * (i + 0.5) / n
            B.box("%s_fx%d%d" % (name, s, i), w / n * 0.44, t, h, z, role, 0.0,
                  at=(ox + u, oy + s * (d / 2 - t / 2)))
            v = -d / 2 + d * (i + 0.5) / n
            B.box("%s_fy%d%d" % (name, s, i), t, d / n * 0.44, h, z, role, 0.0,
                  at=(ox + s * (w / 2 - t / 2), oy + v))


def tower_sq(B, at, w, d, z0, h, cap="crenel", merlon=2, role="石", trim="石亮",
            cap_h=0.085, slit=True, corbel=True, cap_role="瓦", at_name="塔",
            merlon_role="石亮", footing=True):
    """方形石塔：塔基 → 塔身 →（腰线）→ 挑檐 → 平台 → 垛口 或 蓝锥顶。

    三件让"白柱子"变成"防御工事"：
      1. **塔基**比塔身宽 3 cm、高 3 cm —— 柱子有了脚，才不像插进去的；
      2. **腰线**（石亮细带）在 2/3 高处横一道，把塔身分成两段；
      3. **托石**（石暗）挑出 3 cm —— 垛口直接坐在塔身上会读成"方糖上摆积木"。
    明度从下到上：塔基暗 → 塔身中 → 腰线亮 → 托石暗 → 平台中 → 垛口亮。
    六级明度是这套零件的全部手艺。
    """
    x, y = at
    if footing:
        B.box(at_name + "基", w + 0.032, d + 0.032, 0.032, z0, "石暗", 0.0, at=at)
        B.box(at_name + "身", w, d, h - 0.026, z0 + 0.026, role, 0.008, at=at)
    else:
        B.box(at_name + "身", w, d, h, z0, role, 0.008, at=at)
    B.box(at_name + "腰", w + 0.016, d + 0.016, 0.010, z0 + h * 0.62, trim, 0.0,
          at=at)
    if corbel:
        B.box(at_name + "托", w + 0.030, d + 0.030, 0.016, z0 + h - 0.006, "石暗",
              0.0, at=at)
    if cap == "crenel":
        B.box(at_name + "台", w + 0.026, d + 0.026, 0.014, z0 + h + 0.010, role,
              0.0, at=at)
        crenel_rect(B, at_name + "垛", w + 0.020, d + 0.020, z0 + h + 0.022,
                    merlon, 0.026, 0.030, merlon_role, at=at)
        return z0 + h + 0.052
    if cap == "pyramid":
        pyramid_roof(B, at_name + "顶", w + 0.020, d + 0.020, z0 + h + 0.012,
                     cap_h, at=at, role=cap_role, cap="金", over=0.030)
        return z0 + h + 0.012 + cap_h
    B.box(at_name + "台", w + 0.026, d + 0.026, 0.014, z0 + h + 0.010, role, 0.0,
          at=at)
    return z0 + h + 0.024


def arch_gate(B, at, w, h, z0, ring=0.026, role="石亮", dark="洞", keystone=True,
              doors=False, door_role="木", axis="Y"):
    """石砌拱门：亮石拱圈 → 暗洞 → 可选门扇 → 拱心石。

    拱圈比门洞大一圈并且**往后退 1 cm**，读出来才是"墙上的洞"；
    拱圈和门洞同深度会读成"贴了一张半圆纸"。
    """
    x, y = at
    if axis == "Y":
        B.arch_plate("拱圈", w + ring * 2, h + ring, 0.012, role, (x, y - 0.004, z0),
                     n=7, axis="Y")
        B.arch_plate("门洞", w, h, 0.014, dark, (x, y + 0.005, z0), n=7, axis="Y")
        if doors:
            B.arch_plate("门扇", w * 0.86, h * 0.90, 0.012, door_role,
                         (x, y + 0.012, z0 + 0.004), n=6, axis="Y")
        if keystone:
            # 拱心石必须**比拱圈顶点高 8 mm**：拱圈是多段折线，最高那条横棱
            # 和石顶同高就判共面（体检 ⑥ 抓过 270 mm²）。
            B.box("拱心石", 0.030, 0.022, 0.038, z0 + h - 0.006, role, 0.0,
                  at=(x, y + 0.004))
    else:
        B.arch_plate("拱圈X", w + ring * 2, h + ring, 0.012, role,
                     (x - 0.004, y, z0), n=7, axis="X")
        B.arch_plate("门洞X", w, h, 0.014, dark, (x + 0.005, y, z0), n=7, axis="X")


def portcullis(B, at, w, h, z0, bars=3, rails=2, role="铁暗"):
    """铁栅门：竖栅 + 横档。3★ 的"重装"就靠这几根 5 mm 的暗铁线。"""
    x, y = at
    for i in range(bars):
        u = -w / 2 + w * (i + 0.5) / bars
        B.box("铁栅%d" % i, 0.014, 0.012, h * 0.94, z0 + 0.004, role, 0.0,
              at=(x + u, y + 0.004))
    for k in range(rails):
        B.box("横档%d" % k, w * 0.96, 0.013, 0.013, z0 + h * (0.22 + 0.44 * k),
              role, 0.0, at=(x, y + 0.006))
    # 底端尖齿：栅栏门不尖就不是"闸"
    for i in range(bars):
        u = -w / 2 + w * (i + 0.5) / bars
        B.pyramid("栅齿%d" % i, 0.020, 0.016, 0.016, z0 - 0.002, role,
                  at=(x + u, y + 0.004))


def chimney(B, at, w=0.070, d=0.070, z0=G, h=0.30, role="石", cap="石亮",
            root=0.026):
    """石烟囱：身 + 压顶 + 出烟口暗块。上细下粗两段才不会读成柱子。"""
    x, y = at
    B.box("烟囱下", w, d, h * 0.62, z0, role, 0.006, at=at)
    B.box("烟囱上", w * 0.78, d * 0.78, h * 0.40, z0 + h * 0.60, "石暗", 0.005,
          at=at)
    B.box("烟囱帽", w * 0.94, d * 0.94, 0.014, z0 + h * 0.986, cap, 0.0, at=at)
    B.box("烟口", w * 0.52, d * 0.52, 0.008, z0 + h * 0.996, "炭", 0.0, at=at)
    _ = root


# ================================================================ 队色件

def shield(B, at, r=0.036, axis="Y", n=6, trim="金", boss=True):
    """圆盾：金边（大）→ 队色盾面（小、往前 4 mm）→ 金盾钉。

    6 边足够：盾在图标上只有 ~14 px，8 边和 6 边看不出差别，但一面省 16 tri。
    """
    x, y, z = at
    if axis == "Y":
        B.disc("盾边", r, 0.012, (x, y, z), trim, n, "Y")
        B.disc("盾面", r * 0.80, 0.012, (x, y + 0.005, z), "盾", n, "Y")
        if boss:
            B.disc("盾钉", r * 0.26, 0.008, (x, y + 0.011, z), trim, 4, "Y")
    else:
        B.disc("盾边", r, 0.012, (x, y, z), trim, n, "X")
        B.disc("盾面", r * 0.80, 0.012, (x + 0.005, y, z), "盾", n, "X")
        if boss:
            B.disc("盾钉", r * 0.26, 0.008, (x + 0.011, y, z), trim, 4, "X")


def wall_banner(B, at, w=0.054, h=0.108, role="旗", trim="金", axis="Y",
                slope=0.0):
    """墙面挂旗：金挑杆 + 垂旗 + 金底边。

    旗面必须**干净梯形**：中间折褶会读成纸飞机（老坑）。
    """
    x, y, z = at
    if axis == "Y":
        B.beam("挑杆", (x - w / 2 - 0.010, y, z), (x + w / 2 + 0.010, y, z),
               0.010, 0.008, trim)
        pts = [(-w / 2, 0.0), (w / 2, 0.0), (w / 2, -h * 0.72),
               (w * 0.28, -h * 0.87), (0.0, -h), (-w * 0.28, -h * 0.87),
               (-w / 2, -h * 0.72)]
        B.plate("挂旗", pts, 0.008, role, (x, y + 0.004, z - 0.006), "Y")
        band = [(-w * 0.44, -h * 0.72), (w * 0.44, -h * 0.72),
                (w * 0.26, -h * 0.87), (0.0, -h * 0.98), (-w * 0.26, -h * 0.87)]
        B.plate("旗边", band, 0.007, trim, (x, y + 0.009, z - 0.006), "Y")
    else:
        B.beam("挑杆X", (x, y - w / 2 - 0.010, z), (x, y + w / 2 + 0.010, z),
               0.010, 0.008, trim)
        pts = [(-w / 2, 0.0), (w / 2, 0.0), (w / 2, -h * 0.72),
               (w * 0.28, -h * 0.87), (0.0, -h), (-w * 0.28, -h * 0.87),
               (-w / 2, -h * 0.72)]
        B.plate("挂旗X", pts, 0.008, role, (x + 0.004, y, z - 0.006), "X")
        band = [(-w * 0.44, -h * 0.72), (w * 0.44, -h * 0.72),
                (w * 0.26, -h * 0.87), (0.0, -h * 0.98), (-w * 0.26, -h * 0.87)]
        B.plate("旗边X", band, 0.007, trim, (x + 0.009, y, z - 0.006), "X")
    _ = slope


def flag_pole(B, at, z0, z1, w=0.072, drop=0.070, role="旗", mast="木暗",
              pennant=True):
    """旗桅：杆 + 三角旗 + 金顶珠。**塔顶不用尖顶，用旗** —— 不读教堂。"""
    x, y = at
    B.box("桅杆", 0.010, 0.010, z1 - z0, z0, mast, 0.0, at=(x, y))
    B.cyl("桅顶珠", 0.011, 0.012, z1 - 0.004, 6, "金", at=(x, y), r_top=0.008)
    zt = z1 - 0.014
    if pennant:
        B.plate("桅旗", [(0.004, 0.004), (w, 0.004), (w * 0.55, -drop * 0.34),
                        (0.004, -drop)], 0.006, role, (x, y, zt), "Y")
    else:
        B.plate("桅旗方", [(-w * 0.46, 0.0), (w * 0.46, 0.0), (w * 0.46, -drop * 0.62),
                          (0.0, -drop * 0.76), (-w * 0.46, -drop * 0.62)],
                0.006, role, (x + 0.004, y, zt), "Y")


def crest(B, at, w=0.130, h=0.078, kind="shield"):
    """门楣徽章：金背板 → 队色盾面 → 金纹样。

    kind='shield' 城镇大厅（金竖带 + 横带）
    kind='swords' 兵营（交叉双剑，剑尖朝上）
    kind='anvil'  铁匠铺（金砧剪影）
    kind='wheat'  农场（三束麦）
    kind='saw'    伐木场（圆锯 + 齿）
    """
    x, y, z = at
    B.box("徽板", w, 0.014, h, z, "金", 0.0, at=(x, y))
    B.box("徽板内", w - 0.014, 0.010, h - 0.014, z + 0.007, "金亮", 0.0,
          at=(x, y + 0.003))

    def shield_pts(sw, sh, zz):
        return [(-sw / 2, zz + sh), (sw / 2, zz + sh), (sw / 2, zz + sh * 0.42),
                (sw * 0.30, zz + sh * 0.16), (0.0, zz),
                (-sw * 0.30, zz + sh * 0.16), (-sw / 2, zz + sh * 0.42)]

    sw, sh = w * 0.64, h * 0.72
    B.plate("徽盾", shield_pts(sw, sh, z + h * 0.10), 0.010, "盾",
            (x, y + 0.010, 0.0), "Y")
    if kind == "shield":
        B.box("徽竖带", sw * 0.20, 0.008, sh * 0.86, z + h * 0.16, "金亮", 0.0,
              at=(x, y + 0.017))
        B.box("徽横带", sw * 0.86, 0.008, sh * 0.16, z + h * 0.44, "金亮", 0.0,
              at=(x, y + 0.017))
    elif kind == "swords":
        for s in (-1, 1):
            B.beam("徽剑%d" % s, (x - s * sw * 0.34, y + 0.018, z + h * 0.16),
                   (x + s * sw * 0.34, y + 0.018, z + h * 0.80),
                   0.008, 0.006, "金亮")
            B.beam("徽护手%d" % s, (x - s * sw * 0.22, y + 0.020, z + h * 0.52),
                   (x - s * sw * 0.02, y + 0.020, z + h * 0.60),
                   0.006, 0.005, "金亮")
    elif kind == "anvil":
        B.box("徽砧面", sw * 0.62, 0.010, sh * 0.20, z + h * 0.46, "金亮", 0.0,
              at=(x, y + 0.017))
        B.box("徽砧腰", sw * 0.26, 0.010, sh * 0.22, z + h * 0.28, "金亮", 0.0,
              at=(x, y + 0.017))
        B.box("徽砧底", sw * 0.44, 0.010, sh * 0.14, z + h * 0.16, "金亮", 0.0,
              at=(x, y + 0.017))
    elif kind == "wheat":
        for s in (-1, 0, 1):
            B.beam("徽麦%d" % s, (x + s * sw * 0.20, y + 0.017, z + h * 0.18),
                   (x + s * sw * 0.26, y + 0.017, z + h * 0.74),
                   0.006, 0.005, "金亮")
            for k in range(2):
                B.beam("徽芒%d%d" % (s, k),
                       (x + s * sw * 0.26, y + 0.019, z + h * (0.55 + 0.10 * k)),
                       (x + s * sw * 0.40, y + 0.019, z + h * (0.66 + 0.10 * k)),
                       0.005, 0.004, "金亮")
    elif kind == "saw":
        B.disc("徽锯", sw * 0.34, 0.008, (x, y + 0.017, z + h * 0.46), "金亮",
               12, "Y")
        B.disc("徽锯芯", sw * 0.14, 0.008, (x, y + 0.021, z + h * 0.46), "盾",
               8, "Y")


# ================================================================ 道具（12 tri 级）

def barrel(B, at, z=G, r=0.026, h=0.058, role="木亮", hoop="铁暗"):
    """木桶：两段微锥 + 一道铁箍。**6 边**，8 边在 512 px 上一模一样却贵 40%。"""
    x, y = at
    B.cyl("桶下", r * 0.90, h * 0.50, z, 6, role, at=(x, y), r_top=r)
    B.cyl("桶上", r, h * 0.50, z + h * 0.50, 6, role, at=(x, y), r_top=r * 0.88)
    B.cyl("桶箍", r + 0.002, 0.010, z + h * 0.44, 6, hoop, at=(x, y), cap=False)


def crate(B, at, z=G, s=0.058, h=0.050):
    x, y = at
    B.box("木箱", s, s * 0.92, h, z, "木", 0.0, at=(x, y))
    B.box("箱盖", s + 0.006, s * 0.92 + 0.006, 0.008, z + h - 0.004, "木亮", 0.0,
          at=(x, y))


def sack(B, at, z=G, r=0.026, h=0.044):
    x, y = at
    B.cyl("麻袋", r, h * 0.86, z, 6, "布暗", at=(x, y), r_top=r * 0.55)
    B.cyl("袋口", r * 0.30, h * 0.16, z + h * 0.84, 6, "木暗", at=(x, y))


def hay(B, at, z=G, r=0.036, h=0.056, rot=0.0):
    x, y = at
    B.cyl("草垛", r, h, z, 8, "麦", at=(x, y), r_top=r * 0.86, rotz=rot)
    B.cyl("草绳", r + 0.002, 0.008, z + h * 0.55, 8, "麦暗", at=(x, y), cap=False)


def hay_bale(B, at, z=G, w=0.078, d=0.050, h=0.046, rot=0.0):
    m = Matrix.Rotation(rot, 3, 'Z')
    v = [(-w / 2, -d / 2, 0), (w / 2, -d / 2, 0), (w / 2, d / 2, 0), (-w / 2, d / 2, 0),
         (-w / 2, -d / 2, h), (w / 2, -d / 2, h), (w / 2, d / 2, h), (-w / 2, d / 2, h)]
    f = [(0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    x, y = at
    v = [tuple(m @ Vector(p)) for p in v]
    v = [(p[0] + x, p[1] + y, p[2] + z) for p in v]
    B.part("草捆", v, f, "麦", 0.0, 1, "all")
    B.box("草捆绳1", w * 0.06, d + 0.004, h * 0.96, z, "麦暗", 0.0, at=(x, y))


def log_axis(B, name, p0, p1, r, role="木", sides=8, cap="木亮"):
    """沿任意轴的原木（八边棱柱 + 两端口）。

    **mkit.cyl 只能立着长**：rotz 转的是截面多边形，不是轴。v1 想用
    `cyl(rotz=90°)` 摆横木，结果得到一排立在地上的柱子。所以横木必须
    自己放样 —— 两个八边形环 + 8 个侧面 + 两个端盖 = 28 tri。
    """
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    L = d.length
    if L < 1e-6:
        return
    q = d.to_track_quat('Z', 'Y').to_matrix()
    v = []
    for s in (0.0, L):
        for i in range(sides):
            a = 2 * math.pi * i / sides
            v.append(tuple(p0 + q @ Vector((r * math.cos(a), r * math.sin(a), s))))
    f = []
    for i in range(sides):
        j = (i + 1) % sides
        f.append((i, j, sides + j, sides + i))
    f.append(tuple(range(sides - 1, -1, -1)))
    f.append(tuple(range(sides, 2 * sides)))
    B.part(name, v, f, role, 0.0, 1, "all")
    # 端面年轮：比原木略小的浅色片，贴在两端（各 8 tri）
    for k, p in ((0, p0), (1, p1)):
        sgn = -1 if k == 0 else 1
        # 1.2 mm：露在端面外看得见，又不至于让 AABB 与母体脱开（容差 2 mm）
        off = p + (d.normalized() * 0.0012 * sgn)
        vv = []
        for i in range(sides):
            a = 2 * math.pi * i / sides
            vv.append(tuple(off + q @ Vector((r * 0.62 * math.cos(a),
                                              r * 0.62 * math.sin(a), 0.0))))
        B.part(name + "芯%d" % k, vv, [tuple(range(sides))], cap, 0.0, 1, "all")


def logpile(B, at, z=G, n=3, length=0.170, r=0.020, rot=0.0, layers=2):
    """原木堆：端面朝 +X，逐层收一朵 —— 圆端面就是"木头"的唯一证据。"""
    x, y = at
    m = Matrix.Rotation(rot, 3, 'Z')
    for k in range(layers):
        cnt = n - k
        for i in range(cnt):
            u = (i - (cnt - 1) / 2) * (r * 2.06)
            p = m @ Vector((-length / 2, u, 0))
            p2 = m @ Vector((length / 2, u, 0))
            log_axis(B, "原木%d%d" % (k, i),
                     (x + p.x, y + p.y, z + r + k * r * 1.74),
                     (x + p2.x, y + p2.y, z + r + k * r * 1.74), r, "木", 8)


def fence(B, x0, x1, y, z=G, h=0.118, n=3, rails=2, role="木", cap="木亮",
          t=0.020):
    for i in range(n):
        x = x0 + (x1 - x0) * (i / max(1, n - 1))
        B.box("栅柱", t, t, h, z, role, 0.0, at=(x, y))
        B.box("栅帽", t + 0.008, t + 0.008, 0.008, z + h - 0.002, cap, 0.0,
              at=(x, y))
    for k in range(rails):
        zz = z + h * (0.30 + 0.40 * k)
        B.box("栅横", abs(x1 - x0) + t, 0.012, 0.013, zz, role, 0.0,
              at=((x0 + x1) / 2, y))


def wall_low(B, w, d, z, h=0.062, role="石", cap="石亮", at=(0.0, 0.0)):
    """前庭矮墙：身 + 压顶。压顶必须比墙宽 1.4 cm，否则读成"一道水泥"。

    返回顶面 z —— 城垛要**坐在顶面上再退 2 mm**，否则悬空 2 mm 判 FLOAT。
    """
    B.box("矮墙", w, d, h, z, role, 0.0, at=at)
    B.box("矮墙帽", w + 0.014, d + 0.014, 0.012, z + h - 0.002, cap, 0.0, at=at)
    return z + h + 0.010


def dummy(B, at, z=G, h=0.230):
    """训练木人：十字底座 + 草靶身 + 木盔 + 小盾。"""
    x, y = at
    B.box("木人底", 0.130, 0.022, 0.018, z, "木暗", 0.0, at=(x, y))
    B.box("木人底2", 0.022, 0.130, 0.0165, z, "木暗", 0.0, at=(x, y))
    B.box("木人杆", 0.020, 0.020, h * 0.92, z + 0.018, "木", 0.0, at=(x, y))
    B.box("木人臂", 0.150, 0.018, 0.018, z + h * 0.70, "木", 0.0, at=(x, y))
    B.cyl("草靶", 0.034, h * 0.30, z + h * 0.34, 8, "麦", at=(x, y), r_top=0.030)
    B.box("木人头", 0.044, 0.040, 0.042, z + h * 0.68, "木亮", 0.0, at=(x, y))
    B.pyramid("木人盔", 0.052, 0.048, 0.024, z + h * 0.90, "铁", at=(x, y))


def rack(B, at, z=G, w=0.130, h=0.140, spears=3, crossed=True):
    """武器架：两柱一横 + 立矛 + 一对交叉长矛（兵营第一识别件）。"""
    x, y = at
    for s in (-1, 1):
        B.box("枪架柱%d" % s, 0.015, 0.015, h, z, "木暗", 0.0,
              at=(x + s * (w / 2), y))
    B.box("枪架横", w + 0.020, 0.013, 0.013, z + h - 0.018, "木暗", 0.0, at=(x, y))
    for i in range(spears):
        px = x + (i - (spears - 1) / 2) * (w / max(1, spears - 1) * 0.58)
        B.beam("立矛%d" % i, (px, y + 0.004, z), (px, y + 0.010, z + h + 0.062),
               0.011, 0.011, "木")
        B.cone("矛头%d" % i, 0.008, 0.022, z + h + 0.060, 4, "铁", at=(px, y + 0.007))
    if crossed:
        for s in (-1, 1):
            B.beam("交叉矛%d" % s, (x + s * 0.046, y - 0.016, z),
                   (x - s * 0.026, y + 0.034, z + h + 0.086), 0.010, 0.010, "木亮")
            B.cone("交叉矛头%d" % s, 0.008, 0.020,
                   z + h + 0.084, 4, "铁", at=(x - s * 0.026, y + 0.034))


def anvil(B, at, z=G, h=0.048):
    """铁砧：面 + 腰 + 底 + 角。剪影必须是"上宽下窄，一头尖"。"""
    x, y = at
    B.box("砧底", 0.052, 0.034, h * 0.30, z, "木暗", 0.0, at=(x, y))
    B.box("砧腰", 0.030, 0.024, h * 0.34, z + h * 0.30, "铁", 0.0, at=(x, y))
    B.box("砧面", 0.070, 0.030, h * 0.22, z + h * 0.64, "铁", 0.0, at=(x, y))
    B.pyramid("砧角", 0.032, 0.026, 0.016, z + h * 0.62, "铁", at=(x + 0.030, y),
              rotz=math.radians(90))


def forge(B, at, z=G, w=0.130, h=0.105, mouth=0.062):
    """炉膛：石框 + 橙红炉口 + 炭 + 上方石罩。

    没有自发光槽（两槽制），所以炉火靠**明度**：炉口用 #FF6A20 满饱和，
    周围一圈压暗的炭 —— 512 px 上照样"在烧"。
    """
    x, y = at
    B.box("炉体", w, 0.086, h, z, "石暗", 0.006, at=(x, y))
    B.box("炉口", mouth, 0.020, h * 0.56, z + h * 0.16, "炉", 0.0,
          at=(x, y + 0.040))
    B.box("炉炭", mouth * 0.72, 0.014, h * 0.16, z + h * 0.10, "炭", 0.0,
          at=(x, y + 0.050))
    B.box("炉罩", w * 0.86, 0.024, h * 0.20, z + h * 0.76, "石", 0.0,
          at=(x, y + 0.036))


def saw_blade(B, at, r=0.078, axis="Y", teeth=10):
    """立式圆锯：铁盘 + 齿 + 金轴心。伐木场的第二识别件。

    齿是**贴在盘外缘的方点**（plate，12 tri/2 面），比真的锯齿轮廓便宜一半，
    96 px 上只读"一圈毛边"，那正是要的效果。
    """
    x, y, z = at
    B.disc("锯盘", r, 0.010, (x, y, z), "铁亮", 16, axis)
    if axis == "Y":
        B.disc("锯心", r * 0.30, 0.010, (x, y + 0.004, z), "金", 8, axis)
        for i in range(teeth):
            a = 2 * math.pi * (i + 0.5) / teeth
            cx, cz = r * math.cos(a), r * math.sin(a)
            B.plate("锯齿%d" % i,
                    [(cx - 0.006, cz - 0.006), (cx + 0.006, cz - 0.006),
                     (cx + 0.006, cz + 0.006), (cx - 0.006, cz + 0.006)],
                    0.010, "铁亮", (x, y, z), "Y")
    else:
        B.disc("锯心", r * 0.30, 0.010, (x + 0.004, y, z), "金", 8, axis)
        for i in range(teeth):
            a = 2 * math.pi * (i + 0.5) / teeth
            cy, cz = r * math.cos(a), r * math.sin(a)
            B.plate("锯齿%d" % i,
                    [(cy - 0.006, cz - 0.006), (cy + 0.006, cz - 0.006),
                     (cy + 0.006, cz + 0.006), (cy - 0.006, cz + 0.006)],
                    0.010, "铁亮", (x, y, z), "X")


def windmill(B, at, r=0.155, z=0.0, blades=4, role="木亮", trim="旗"):
    """风车叶：4 片梯形帆 + 中心金毂。农场的 96 px 识别件。

    叶片必须**有宽度**：每片是一块 4 cm 宽的梯形板，读"风车"；
    细杆读"天线"。角点直接在 (x,z) 平面算，**不用矩阵旋对象** ——
    v1 试过"建完再绕 Y 转 obj.matrix_world"，结果只有最后一片被转到。
    """
    x, y, zz = at
    r0, r1 = 0.018, r
    for i in range(blades):
        a = 2 * math.pi * i / blades + math.pi / 4
        ca, sa = math.cos(a), math.sin(a)
        px, pz = -sa, ca
        w0, w1 = 0.018, 0.042
        pts = [(px * w0 / 2 + ca * r0, pz * w0 / 2 + sa * r0),
               (px * w1 / 2 + ca * r1, pz * w1 / 2 + sa * r1),
               (-px * w1 / 2 + ca * r1, -pz * w1 / 2 + sa * r1),
               (-px * w0 / 2 + ca * r0, -pz * w0 / 2 + sa * r0)]
        B.plate("风车叶%d" % i, pts, 0.008, role, (x, y + 0.004, zz), "Y")
        # 帆布：外段一块队色梯形，贴得更前 3 mm
        c0, c1 = r1 * 0.34, r1 * 0.86
        bw = w0 + (w1 - w0) * 0.50
        pts2 = [(px * bw / 2 + ca * c0, pz * bw / 2 + sa * c0),
                (px * w1 * 0.92 / 2 + ca * c1, pz * w1 * 0.92 / 2 + sa * c1),
                (-px * w1 * 0.92 / 2 + ca * c1, -pz * w1 * 0.92 / 2 + sa * c1),
                (-px * bw / 2 + ca * c0, -pz * bw / 2 + sa * c0)]
        B.plate("帆%d" % i, pts2, 0.007, trim, (x, y + 0.010, zz), "Y")
    B.cyl("风车毂", 0.016, 0.014, zz - 0.007, 8, "金", at=(x, y + 0.006))


def wheat_field(B, w, d, z=G, rows=4, at=(0.0, 0.0), sheaves=0):
    """麦田：金色底 + 深色垄沟 + 边缘石牙。远看是一块"熟了的田"。"""
    x, y = at
    B.box("麦田", w, d, 0.014, z, "麦", 0.0, at=at)
    for i in range(rows):
        u = -w / 2 + w * (i + 0.5) / rows
        B.box("垄%d" % i, w / rows * 0.14, d * 0.92, 0.010, z + 0.014, "麦暗",
              0.0, at=(x + u, y))
    B.box("田埂", w + 0.012, d + 0.012, 0.008, z - 0.002, "土", 0.0, at=at)
    # 麦垛：田里必须有两三"束"站起来的东西，否则一整块金色平板读成木托盘
    for i in range(sheaves):
        u = -w / 2 + w * (i + 0.5) / sheaves
        px, py = x + u, y + d * 0.28
        # 一束麦 = 一个 6 tri 的方锥，够读"田里有东西立着"，不要做圆柱+尖顶
        B.pyramid("麦束%d" % i, 0.030, 0.028, 0.044, z + 0.012, "麦", at=(px, py))


def scarecrow(B, at, z=G, h=0.190):
    """稻草人：杆 + 横臂 + 草身 + 布头 + 草帽。农场 3★ 的"人味"。"""
    x, y = at
    B.box("稻杆", 0.014, 0.014, h, z, "木暗", 0.0, at=(x, y))
    B.box("稻臂", 0.120, 0.012, 0.012, z + h * 0.72, "木暗", 0.0, at=(x, y))
    B.box("稻衣", 0.058, 0.034, h * 0.36, z + h * 0.34, "布暗", 0.0, at=(x, y))
    B.box("稻头", 0.036, 0.032, 0.034, z + h * 0.82, "布", 0.0, at=(x, y))
    B.cyl("草帽", 0.032, 0.010, z + h * 0.94, 8, "麦", at=(x, y), r_top=0.008)


def cart(B, at, z=G, w=0.130, d=0.070, rot=0.0):
    """板车：车厢 + 两轮 + 车辕。农场 / 伐木场共用。"""
    x, y = at
    m = Matrix.Rotation(rot, 3, 'Z')
    # 车厢
    v = [(-w / 2, -d / 2, 0.014), (w / 2, -d / 2, 0.014), (w / 2, d / 2, 0.014),
         (-w / 2, d / 2, 0.014), (-w / 2, -d / 2, 0.048), (w / 2, -d / 2, 0.048),
         (w / 2, d / 2, 0.048), (-w / 2, d / 2, 0.048)]
    f = [(0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    v = [tuple(m @ Vector(p)) for p in v]
    v = [(p[0] + x, p[1] + y, p[2] + z) for p in v]
    B.part("车斗", v, f, "木", 0.0, 1, "all")
    for s in (-1, 1):
        p = m @ Vector((0.0, s * (d / 2 + 0.006), 0.0))
        B.cyl("车轮%d" % s, 0.024, 0.012, z + 0.006, 8, "木暗",
              at=(x + p.x, y + p.y), rotz=math.pi / 2)
    # 车辕必须**从车斗边缘起**：起点放在车斗外 3 cm，AABB 与车斗不接触 → FLOAT
    p = m @ Vector((w / 2 - 0.004, 0.0, 0.0))
    B.beam("车辕", (x + p.x, y + p.y, z + 0.034), (x + p.x + 0.062, y + p.y, z + 0.026),
           0.010, 0.010, "木暗")


def ladder(B, at, z0, z1, w=0.030, rungs=4):
    x, y = at
    for s in (-1, 1):
        B.box("梯杆%d" % s, 0.009, 0.009, z1 - z0, z0, "木", 0.0,
              at=(x + s * w / 2, y))
    for i in range(rungs):
        zz = z0 + (z1 - z0) * (i + 0.5) / rungs
        B.box("梯档%d" % i, w, 0.008, 0.008, zz, "木暗", 0.0, at=(x, y))


def pot(B, at, z=G, r=0.020, h=0.030):
    x, y = at
    B.cyl("陶罐", r * 0.72, h, z, 8, "铜", at=(x, y), r_top=r)


def stump(B, at, z=G, r=0.030, h=0.026):
    x, y = at
    B.cyl("树桩", r, h, z, 8, "木", at=(x, y), r_top=r * 0.96)
    B.cyl("年轮", r * 0.74, 0.006, z + h, 8, "木亮", at=(x, y))


def water_trough(B, at, z=G, w=0.090, d=0.042, h=0.034):
    x, y = at
    B.box("水槽", w, d, h, z, "石", 0.0, at=(x, y))
    B.box("水面", w - 0.014, d - 0.014, 0.006, z + h - 0.008, "水", 0.0, at=(x, y))


def grindstone(B, at, z=G, r=0.036):
    x, y = at
    B.disc("磨石", r, 0.016, (x, y, z + r + 0.014), "石", 12, "Y")
    B.box("磨架", 0.020, 0.026, r + 0.014, z, "木暗", 0.0, at=(x, y))
    B.box("磨槽", 0.070, 0.030, 0.012, z, "木", 0.0, at=(x, y))


def tent(B, at, w=0.150, d=0.170, z=G, h=0.135, role="布"):
    """蓝白帐篷：白帆布 + 队色脊条 + 暗门洞。

    "蓝白"不能靠两种白 —— 必须有一条真的队色，否则 96 px 上是一团米白。
    脊条 12 tri 就够，比在斜面上贴一块布条稳（斜面贴片必共面）。
    """
    x, y = at
    B.roof_gable_y("帐篷布", w, d, z, z + h, role, at=at)
    for s in (-1, 1):
        pts = [(-w / 2 + 0.008, 0.002), (w / 2 - 0.008, 0.002), (0.0, h - 0.010)]
        B.plate("帐端%d" % s, pts, 0.010, role, (x, y + s * d / 2, z), "Y")
    B.plate("帐门", [(-w * 0.22, 0.004), (w * 0.22, 0.004), (0.0, h * 0.60)],
            0.008, "洞", (x, y + d / 2 + 0.006, z), "Y")
    B.box("帐篷脊", 0.014, d + 0.006, 0.014, z + h - 0.006, "旗", 0.0, at=(x, y))
    B.box("脊杆", 0.007, d + 0.020, 0.007, z + h - 0.001, "木暗", 0.0, at=(x, y))


def banner_stand(B, at, z=G, h=0.240, w=0.058, drop=0.092, role="旗"):
    x, y = at
    B.box("旗座", 0.040, 0.040, 0.014, z, "石暗", 0.0, at=(x, y))
    B.box("旗杆", 0.009, 0.009, h, z + 0.010, "木暗", 0.0, at=(x, y))
    B.box("旗担", w + 0.012, 0.009, 0.009, z + h - 0.008, "木暗", 0.0, at=(x, y))
    B.cyl("旗顶", 0.007, 0.012, z + h, 6, "金", at=(x, y), r_top=0.009)
    pts = [(-w / 2, 0.0), (w / 2, 0.0), (w / 2, -drop * 0.72),
           (w * 0.28, -drop * 0.87), (0.0, -drop),
           (-w * 0.28, -drop * 0.87), (-w / 2, -drop * 0.72)]
    B.plate("旗面", pts, 0.007, role, (x, y + 0.006, z + h - 0.012), "Y")
    band = [(-w * 0.44, -drop * 0.72), (w * 0.44, -drop * 0.72),
            (w * 0.26, -drop * 0.87), (0.0, -drop * 0.98), (-w * 0.26, -drop * 0.87)]
    B.plate("旗边", band, 0.006, "金", (x, y + 0.011, z + h - 0.012), "Y")


def lantern(B, at, z, drop=0.026):
    x, y = at
    B.beam("灯架", (x, y - 0.004, z + drop), (x, y + 0.024, z + drop),
           0.007, 0.006, "铁")
    B.box("灯罩", 0.018, 0.018, 0.022, z, "炉", 0.0, at=(x, y + 0.020))
    B.pyramid("灯帽", 0.024, 0.024, 0.012, z + 0.022, "铁", at=(x, y + 0.020))


def door(B, x, y, z, w=0.100, h=0.150, role="木", frame="石亮", studs=1,
         trim="金", plate=False, detail=2):
    """平门：暗框洞 → 门扇 → 门框 → 铁箍。不做真开洞（1 m 件上打洞只会破面）。

    detail 0 = 洞 + 扇（24 tri）／1 = + 门框（48）／2 = + 门楣饰 + 铁箍 + 门槛（84）。
    1★ 的门用 detail=0 就够 —— 门在 96 px 上只是一块深色竖条。
    """
    B.plate("门洞", [(-w / 2, 0.0), (w / 2, 0.0), (w / 2, h), (-w / 2, h)],
            0.010, "洞", (x, y + 0.004, z), "Y")
    dw = w * 0.88
    B.plate("门扇", [(-dw / 2, 0.003), (dw / 2, 0.003), (dw / 2, h * 0.95),
                    (-dw / 2, h * 0.95)], 0.010, role, (x, y + 0.010, z), "Y")
    if detail < 1:
        return
    for s in (-1, 1):
        B.box("门框%d" % s, 0.014, 0.020, h + 0.010, z, frame, 0.0,
              at=(x + s * (w / 2 + 0.007), y + 0.010))
    B.box("门楣", w + 0.042, 0.020, 0.014, z + h + 0.004, frame, 0.0,
          at=(x, y + 0.010))
    if detail < 2:
        return
    if trim:
        B.box("门楣饰", w + 0.050, 0.022, 0.009, z + h + 0.018, "门饰", 0.0,
              at=(x, y + 0.011))
    for i in range(studs):
        zz = z + h * (0.28 + 0.34 * i)
        B.box("门箍%d" % i, dw + 0.002, 0.005, 0.007, zz, "铁", 0.0,
              at=(x, y + 0.017))
    if plate:
        B.box("门槛", w + 0.030, 0.026, 0.012, z - 0.004, "石暗", 0.0,
              at=(x, y + 0.012))


def win(B, w, h, at, role="洞", frame=None, axis="Y", bars=0):
    """窗：一块 9 mm 暗板，**at 传墙面坐标**。

    v1 让调用方传"墙面 + 8 mm"，结果板子中心离墙 8 mm、板厚只有 9 mm，
    背后悬空 3.5 mm —— 体检 ⑦ 直接抓出来。这里把 1 mm 咬进墙里，
    对外只暴露"墙面"一个概念，调用方再也不用算厚度。
    """
    x, y, z = at
    if axis == "Y":
        B.plate("窗", [(-w / 2, 0.0), (w / 2, 0.0), (w / 2, h), (-w / 2, h)],
                0.009, role, (x, y + 0.001, z), axis)
    else:
        B.plate("窗", [(-w / 2, 0.0), (w / 2, 0.0), (w / 2, h), (-w / 2, h)],
                0.009, role, (x + 0.001, y, z), axis)
    if frame:
        if axis == "Y":
            B.box("窗台", w + 0.018, 0.014, 0.008, z - 0.008, frame, 0.0,
                  at=(x, y + 0.002))
            B.box("窗楣", w + 0.016, 0.012, 0.007, z + h + 0.001, frame, 0.0,
                  at=(x, y + 0.002))
        else:
            B.box("窗台", 0.014, w + 0.018, 0.008, z - 0.008, frame, 0.0,
                  at=(x + 0.002, y))
            B.box("窗楣", 0.012, w + 0.016, 0.007, z + h + 0.001, frame, 0.0,
                  at=(x + 0.002, y))
    for i in range(bars):
        if axis == "Y":
            B.box("窗栅%d" % i, 0.005, 0.008, h * 0.9, z + h * 0.05, "铁暗", 0.0,
                  at=(x + (i - (bars - 1) / 2) * (w / (bars + 0.6)), y + 0.004))
        else:
            B.box("窗栅%d" % i, 0.008, 0.005, h * 0.9, z + h * 0.05, "铁暗", 0.0,
                  at=(x + 0.004, y + (i - (bars - 1) / 2) * (w / (bars + 0.6))))


def smoke_stack(B, at, z0, h, w=0.020, role="石亮"):
    """烟囱顶的"三道收束"：不是烟（几何烟会读成棉花糖），是石砌收口。"""
    x, y = at
    for i in range(3):
        k = 1.0 - i * 0.18
        B.box("收口%d" % i, w * k, w * k, 0.008, z0 + i * 0.010, role, 0.0,
              at=(x, y))
    _ = h
