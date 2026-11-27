"""
th_model.py —— 城镇大厅 v3：三段式山墙市政厅（低模 → 曲面细分）

v2（两段孟莎 + 贯通钟楼 + 前庭台）之后的三条反馈，逐一落到形体上：

  ① **主体窄而高**：v2 是 10.90 宽 × 19.19 高，宽:高 = 0.57，正面只有 3 个开间，
     钟塔从地面通到 13.35 —— 读起来是"一座钟楼带两片裙房"。
     v3 把主楼加宽到 **11.0**、进深压到 **6.4**，两侧各接 2.7 宽的翼楼，
     总宽 **16.9**（含石台）、总高 **15.45**（含旗），宽:高 ≈ **1.09**；
     正立面排 **5 个开间**（3.7 / 3.6 / 3.7 + 2.7 / 2.7），中轴那一间最宽。

  ② **更多主体与组合，但必须是一整个主体**：
     改成**三段式**——中央主楼（檐 6.55）+ 两侧翼楼（檐 4.60，前脸后退 0.80，后墙齐平）。
     三段共用**一条石台、一条墙裙、一条腰线色带、一圈檐口**，
     所以俯视是"凸"字的一个体，不是三座房子拼起来。
     中轴仍然是"拱门 → 山花 → 盾徽 → 钟塔 → 旗"，一条线读到底。

  ③ **屋顶又怪又丑**：v2 的两段孟莎（下段 57° / 上段 42°）在 10.9 m 的窄进深上
     读成"帐篷上扣了一顶帽子"，塔从屋面正中穿过、接缝堆满三角墙。
     v3 换成 **34.6° 缓坡四坡 + 0.42 m 厚石檐口 + 4.6 m 短脊**；
     翼楼各自一座更低更陡的四坡（36°，用深一档的 roof_edge）；
     钟塔改成**骑在屋脊上的方形石座 + 四角小尖塔**，塔只从屋面上冒出 1.4 m，
     不再贯通立面 —— 立面因此完整，"窄高"的观感一半来自这里。
     屋脊在塔座两侧各留 0.9 m，俯视能读出"两条短脊夹一座塔"。

  ④ **入口不要延伸一片平地**：v2 的前庭台 4.5 m 深、带矮墙与铺石分格，
     俯视是一块"名片底座"。v3 只留**石台 + 5 级踏步 + 两侧矮墙端柱**，
     台阶出挑 1.40 m，除此之外一概不铺。

坐标：X 右、Y 前（+Y = 正面）、Z 上；原点在主体中心，z = 0 地面。
交付前整体沿 X 镜像一次。徽记 / 旗帜继承 br_model.Model（同一段几何）。
"""
import math
from math import tau as TAU

import bpy

import bslib as L
import br_model as BR
from bslib import (arch_band, beam, box, cyl, extrude, frustum, mesh_obj,
                   revolve, ring_y)
from br_model import arch_profile, mirror_x

# ── 主楼平面与标高（10.4 × 6.4）─────────────────────────────────────────────
W2 = 5.20                       # 主楼半宽（10.4，一 / 二层）
W3 = 4.75                       # 三层半宽（9.5）—— 从第二道腰线上退 0.45
WCUT = 8.88                     # 退台标高（= 第二道腰线压条顶）
YF, YB = 3.20, -3.20            # 主楼前 / 后墙（进深 6.4）
H0 = 0.55                       # 石台顶 / 室内地面
DADO = 1.55                     # 墙裙顶（1.00 高）
STR0, STR1 = 4.26, 4.70         # 第一道腰线（下）
STR2, STR3 = 8.43, 8.75         # 第二道腰线（中，夹住三层）
WCAP = 12.15                    # 主楼墙顶（三层）
EAVE0, EAVE1 = 12.15, 12.39     # 石檐口（fascia 在其上，不遮石材）
EFX, EFY = 5.30, 3.80           # 主楼出檐（侧 0.55 / 前 0.60，从退台后的墙算起）
RIDGE_Z, RIDGE_X = 16.60, 2.80  # 前坡 49.3°；脊长 5.60（收窄 10.60 → 5.60）
ROOF_T = 0.20

# ── 翼楼（3.2 宽，前脸后退 0.40，后墙齐平；屋面是"披檐"）────────────────────
WXI, WXO = 5.20, 8.40           # 翼的内 / 外墙面
WYF, WYB = 2.45, -3.20          # 翼前 / 后墙（深 5.65；主楼前脸凸出 0.75）
WWC = 8.50                      # 翼墙顶（两层）
WEAVE0, WEAVE1 = 8.50, 8.70     # 翼檐口
WEFX = 8.72                     # 翼外檐
WEFY0, WEFY1 = -3.60, 3.12      # 翼前后檐
WHIGH = 11.95                   # 披檐贴墙一侧（低于主楼檐口 0.20，绝不穿过主屋面）

# ── 石台 / 台阶 ─────────────────────────────────────────────────────────────
POD_X = 8.65
POD_Y0, POD_Y1 = -3.45, 3.45
POD_Z = 0.55
STEP_X = 1.90                   # 台阶半宽（3.8）
STEP_Y0, STEP_Y1 = 3.45, 4.85   # 5 级 × 0.28
STEP_N = 5
APRON = 0.40                    # 散水宽

# ── 钟塔（骑在屋脊上的石座 + 塔身 + 钟亭 + 八角穹顶）────────────────────────
TBX, TBY = 1.55, 1.45           # 塔座半尺寸（3.1 × 2.9）
TB0, TB1 = EAVE1, 17.10         # 塔座 12.39 → 17.10（脊 16.60 之上 0.50）
TWX, TWY = 1.15, 1.12           # 塔身半尺寸（2.3 × 2.24）
TT0, TT1 = 17.10, 19.70         # 塔身
CLK_Z = 18.40                   # 钟心
BFX, BFY = 1.40, 1.35           # 钟亭半尺寸（2.8 × 2.7）
BF0, BF1 = 19.70, 21.70
BFT = 0.20                      # 钟亭石墙厚
BFS = 19.96                     # 钟亭拱脚
DM0, DM1 = 21.70, 21.88         # 穹座
DOME_TOP = 23.25
LANT0, LANT1 = 23.25, 23.63     # 采光亭
BALL_Z = 23.87
POLE_TOP = 25.07
FLAG_TOP = 25.01

# ── 中央拱门 ───────────────────────────────────────────────────────────────
GW = 1.00                       # 门洞半宽（2.0）
SPRING = 2.88                   # 拱脚（一层净高的 78%）
ARCH_TOP = SPRING + GW          # 3.30
DWALL = 0.64                    # 前墙厚（2.56 → 3.20）
DOOR_Y = 3.06                   # 门扇所在（内凹 0.14）

# ── 老虎窗（前坡 x=±3.25 / 后坡 x=±2.40；中央让给山花与塔座）──────────────────
# 前坡是个梯形（四坡的 hip 让可用宽度随 y 收窄），老虎窗必须"离檐口近、
# 进深浅"才坐得进去：x_max(y) = EFX - (EFX - RIDGE_X) * (EFY - y) / EFY。
DORM_W, DORM_D = 1.40, 1.25     # 宽 / 进深
DORM_H = 1.20                   # 露出屋面的正面高度（顶要低于中央山花）
DORM_CAP = 0.38                 # 四坡小帽高（再高就读成"帽子上的帽子"）
DORM_YF = 3.42                  # 前坡正面墙的 |y|（离檐口 0.38）

# ── 中央山花 ───────────────────────────────────────────────────────────────
GBX, GBZ = 1.75, 2.95           # 山花半宽 / 高（12.15 → 15.10，斜率 1.686 = 戗脊）


# ── 通用构件 ───────────────────────────────────────────────────────────────
def frame_ring(name, x0, x1, y0, y1, z0, z1, t, mat):
    """矩形环（墙裙 / 腰线 / 檐口 / 压顶）：45° 斜接，四角不留缺口、不叠同高面。"""
    ox = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    ix = [(x0 + t, y0 + t), (x1 - t, y0 + t), (x1 - t, y1 - t), (x0 + t, y1 - t)]
    verts = []
    for z in (z0, z1):
        verts += [(x, y, z) for (x, y) in ox]
        verts += [(x, y, z) for (x, y) in ix]
    faces = []
    for i in range(4):
        j = (i + 1) % 4
        faces += [(8 + i, 8 + j, 12 + j, 12 + i),
                  (j, i, 4 + i, 4 + j),
                  (i, j, 8 + j, 8 + i),
                  (4 + j, 4 + i, 12 + i, 12 + j)]
    return mesh_obj(name, verts, faces, mat)


def arch_band_x(name, cy, cz, r_in, r_out, x0, x1, mat, segs=8):
    """朝 ±X 的半圆拱券石（bslib.arch_band 只做 ±Y）。"""
    verts, faces = [], []
    for s in range(segs + 1):
        a = math.pi * s / segs
        ca, sa = math.cos(a), math.sin(a)
        yi, zi = cy + r_in * ca, cz + r_in * sa
        yo, zo = cy + r_out * ca, cz + r_out * sa
        verts += [(x0, yi, zi), (x0, yo, zo), (x1, yo, zo), (x1, yi, zi)]
    for s in range(segs):
        b, b2 = s * 4, (s + 1) * 4
        faces += [(b, b2, b2 + 1, b + 1), (b + 1, b2 + 1, b2 + 2, b + 2),
                  (b + 2, b2 + 2, b2 + 3, b + 3), (b + 3, b2 + 3, b2, b)]
    faces += [(0, 1, 2, 3), (segs * 4 + 3, segs * 4 + 2, segs * 4 + 1, segs * 4)]
    return mesh_obj(name, verts, faces, mat)


def ring_x(name, center, r_in, r_out, length, segments, mat, phase=0.0):
    """竖立圆环，法线沿 X（塔侧钟面用）。"""
    cx, cy, cz = center
    x0, x1 = cx - length * 0.5, cx + length * 0.5
    verts, faces = [], []
    for s in range(segments):
        a = phase + TAU * s / segments
        ca, sa = math.cos(a), math.sin(a)
        verts += [(x0, cy + r_in * ca, cz + r_in * sa),
                  (x0, cy + r_out * ca, cz + r_out * sa),
                  (x1, cy + r_out * ca, cz + r_out * sa),
                  (x1, cy + r_in * ca, cz + r_in * sa)]
    for s in range(segments):
        b, b2 = s * 4, ((s + 1) % segments) * 4
        faces += [(b + 0, b2 + 0, b2 + 1, b + 1), (b + 1, b2 + 1, b2 + 2, b + 2),
                  (b + 2, b2 + 2, b2 + 3, b + 3), (b + 3, b2 + 3, b2 + 0, b + 0)]
    return mesh_obj(name, verts, faces, mat)


def slab(name, pts, t, mat):
    """任意多边形厚板：外表面 + 法向下沉 t 的内表面 + 侧边（只用于朝上的面）。"""
    from mathutils import Vector
    ps = [Vector(p) for p in pts]
    n = (ps[1] - ps[0]).cross(ps[2] - ps[0])
    if n.length < 1e-9:
        n = (ps[2] - ps[0]).cross(ps[3] - ps[0])
    n.normalize()
    if n.z < 0:
        n = -n
    qs = [p - n * t for p in ps]
    m = len(ps)
    verts = [tuple(p) for p in ps] + [tuple(p) for p in qs]
    faces = [tuple(range(m)), tuple(range(m, 2 * m))]
    for i in range(m):
        j = (i + 1) % m
        faces.append((i, j, m + j, m + i))
    return mesh_obj(name, verts, faces, mat)


def lerp(a, b, t):
    return (a[0] + (b[0] - a[0]) * t,
            a[1] + (b[1] - a[1]) * t,
            a[2] + (b[2] - a[2]) * t)


def rib_quad(name, p0, p1, p3, p2, n, w, t, mat, inset=0.07, lift=0.032,
             gapx=None):
    """在坡面上按"从底边到顶边"的插值做瓦垄。p0-p1 底边，p3-p2 顶边。

    返回创建的梁对象列表 —— 调用方必须把它们 add 进模型，否则它们会留在场景里
    却没有进 GLB / 图集（v2 第一版就漏过 31 根瓦垄）。
    """
    out = []
    for i in range(n):
        f = (i + 1) / (n + 1)
        f = inset + f * (1 - 2 * inset)
        a = lerp(p0, p1, f)
        if gapx is not None and abs(a[0]) < gapx:
            continue
        b = lerp(p3, p2, f)
        a = (a[0], a[1], a[2] + lift)
        b = (b[0], b[1], b[2] + lift)
        ob = beam(name, a, b, w, t, mat)
        if ob is not None:
            out.append(ob)
    return out


class Model(BR.Model):
    # ── 1. 石台 / 台阶 / 散水 ───────────────────────────────────────────────
    def base(self):
        """石台 + 5 级踏步 + 两侧矮墙端柱 + 一圈散水。

        v2 的前庭台（4.5 m 深、0.42 高、带矮墙与铺石分格）整块删除 ——
        用户明确"入口可以有台阶，但不需要延伸一片平地"。
        """
        M = self.M
        cy = (POD_Y0 + POD_Y1) * 0.5
        dy = POD_Y1 - POD_Y0
        self.add(box("plinth_low", (0, cy, 0.08),
                     (POD_X * 2 + 0.46, dy + 0.46, 0.16), M["stone_mid"]), 0.014)
        self.add(box("plinth_mid", (0, cy, 0.30),
                     (POD_X * 2 + 0.10, dy + 0.10, 0.28), M["stone_dark"]), 0.020)
        self.add(box("plinth_cap", (0, cy, 0.495),
                     (POD_X * 2 + 0.22, dy + 0.22, 0.12), M["stone_mid"]), 0.012)
        # 散水：石台外一圈 0.08 高的铺石（左 / 右 / 后三段）
        for sx in (-1, 1):
            self.add(box("apron_s", (sx * (POD_X + APRON * 0.5), cy - 0.10, 0.03),
                         (APRON, dy - 0.20, 0.06), M["stone_mid"]), 0.006)
        self.add(box("apron_b", (0, POD_Y0 - APRON * 0.5, 0.03),
                     (POD_X * 2 + APRON * 2, APRON, 0.06), M["stone_mid"]), 0.006)
        # 5 级踏步：实心阶梯（每级从地面起，不会露出空心）
        for i in range(STEP_N):
            zt = POD_Z * (i + 1) / STEP_N
            y1 = STEP_Y1 - 0.28 * i
            y0 = STEP_Y1 - 0.28 * (i + 1)
            if i == STEP_N - 1:
                y0 = STEP_Y0 - 0.06           # 最后一级埋进石台 0.06
            self.add(box("step_%d" % i, (0, (y0 + y1) * 0.5, zt * 0.5),
                         (STEP_X * 2, y1 - y0, zt), M["stone_mid"]), 0.008)
        # 台阶两侧矮墙 + 端柱
        for sx in (-1, 1):
            self.add(box("cheek", (sx * 2.04, (STEP_Y0 + STEP_Y1) * 0.5 - 0.02, 0.34),
                         (0.28, STEP_Y1 - STEP_Y0 - 0.04, 0.68), M["stone_mid"]), 0.010)
            self.add(box("cheek_cap", (sx * 2.04, (STEP_Y0 + STEP_Y1) * 0.5 - 0.02, 0.72),
                         (0.40, STEP_Y1 - STEP_Y0 + 0.06, 0.10), M["stone_light"]), 0.006)
            self.add(box("newel", (sx * 2.04, STEP_Y1 - 0.06, 0.50),
                         (0.46, 0.46, 1.00), M["stone_mid"]), 0.010)
            self.add(box("newel_cap", (sx * 2.04, STEP_Y1 - 0.06, 1.04),
                         (0.56, 0.56, 0.10), M["stone_light"]), 0.005)
            self.add(revolve("newel_ball", [(0.0, 0.0), (0.09, 0.03), (0.125, 0.11),
                                            (0.07, 0.19), (0.0, 0.22)], 8,
                             (sx * 2.04, STEP_Y1 - 0.06, 1.09), M["gold"]), 0.0, 1)
        self.add(box("threshold", (0, YF + 0.20, H0 + 0.035),
                     (2.44, 0.24, 0.07), M["stone_dark"]), 0.004)

    # ── 2. 主楼墙体 ─────────────────────────────────────────────────────────
    def belt(self, tag, z0, z1):
        """一道腰线：石线脚 + 阵营色带 + 金线 + 石压条。

        v3 改成三层后主楼有两道（4.26 / 8.43），翼楼只有一道 —— 层数差靠腰线数读出来。
        """
        M = self.M
        self.add(frame_ring("string" + tag, -W2 - 0.05, W2 + 0.05, YB - 0.05, YF + 0.05,
                            z0 - 0.08, z0, 0.11, M["stone_mid"]), 0.006)
        self.add(frame_ring("band_m" + tag, -W2 - 0.06, W2 + 0.06, YB - 0.06, YF + 0.06,
                            z0 + 0.006, z1, 0.12, M["team"]), 0.008)
        self.add(frame_ring("band_t" + tag, -W2 - 0.09, W2 + 0.09, YB - 0.09, YF + 0.09,
                            z1, z1 + 0.052, 0.15, M["team_trim"]), 0.004)
        self.add(frame_ring("string2" + tag, -W2 - 0.05, W2 + 0.05, YB - 0.05, YF + 0.05,
                            z1 + 0.062, z1 + 0.14, 0.11, M["stone_mid"]), 0.006)

    def mass(self):
        M = self.M
        self.add(box("mass_core", (0, (YB + YF - DWALL) * 0.5, (H0 + WCUT) * 0.5),
                     (W2 * 2, (YF - DWALL) - YB, WCUT - H0), M["stone_light"]), 0.034)
        self.add(box("mass_front_L", (-(W2 + GW) * 0.5, YF - DWALL * 0.5,
                                      (H0 + WCUT) * 0.5),
                     (W2 - GW, DWALL, WCUT - H0), M["stone_light"]), 0.028)
        self.add(box("mass_front_R", ((W2 + GW) * 0.5, YF - DWALL * 0.5,
                                      (H0 + WCUT) * 0.5),
                     (W2 - GW, DWALL, WCUT - H0), M["stone_light"]), 0.028)
        # 门洞上块：矩形 + 底部半圆凹口（比两侧浅 20 mm，避开同面）
        top = [(-GW, SPRING), (-GW, WCUT + 0.02), (GW, WCUT + 0.02), (GW, SPRING)]
        for s in range(1, 10):
            a = math.pi * s / 10
            top.append((GW * math.cos(a), SPRING + GW * math.sin(a)))
        self.add(extrude("mass_front_T", top, "Y", DWALL - 0.02, (0, 0),
                         M["stone_light"], offset=YF - DWALL * 0.5 - 0.01), 0.026)
        # ── 三层退台：从第二道腰线的压条顶上收进 0.45 ──
        # 一/二层 10.4 宽、三层 9.5 宽。这条 0.45 的退台是整栋楼"有没有基座"的分水岭：
        # 直筒墙一直顶到檐口 = 被削了一刀；收一次 = 上层是"坐"在下层上的。
        self.add(box("mass_upper", (0, (YB + YF) * 0.5, (WCUT + WCAP) * 0.5),
                     (W3 * 2, YF - YB, WCAP - WCUT), M["stone_light"]), 0.030)
        # 墙裙 / 腰线 / 色带
        self.add(frame_ring("dado", -W2 - 0.08, W2 + 0.08, YB - 0.08, YF + 0.08,
                            H0, DADO - 0.04, 0.14, M["stone_mid"]), 0.014)
        self.add(frame_ring("dado_cap", -W2 - 0.12, W2 + 0.12, YB - 0.12, YF + 0.12,
                            DADO - 0.08, DADO + 0.02, 0.18, M["stone_dark"]), 0.008)
        self.belt("", STR0, STR1)
        self.belt("_b", STR2, STR3)
        # ── 檐口三件套：托板（出挑 0.30）→ 檐板（0.72）→ 封檐板（0.69）
        # 原来只有一层 0.24 厚的檐板，在 24 m 高的立面上只有 1%，
        # 墙和屋面之间没有过渡层，读起来就是"墙被削了一刀、直接扣了块板"。
        # 古典檐口的厚度 ≈ 墙高的 1/20（这里 11.6 / 20 = 0.58）。
        self.add(frame_ring("corn_lip", -W3 - 0.30, W3 + 0.30, YB - 0.30, YF + 0.30,
                            EAVE0 - 0.27, EAVE0 + 0.01, 0.36, M["stone_mid"]), 0.012)
        for sx in (-1, 1):
            self.add(box("corn_side", (sx * (W3 + 0.36), 0, (EAVE0 + EAVE1) * 0.5),
                         (0.72, EFY * 2 + 0.24, EAVE1 - EAVE0),
                         M["stone_light"]), 0.010)
            self.add(box("corn_front", (sx * (W3 + GBX) * 0.5, YF + 0.36,
                                        (EAVE0 + EAVE1) * 0.5),
                         (W3 - GBX, 0.72, EAVE1 - EAVE0), M["stone_light"]), 0.010)
            # 托架（modillion）：一排小石块撑住挑板。低模上它就是"精致"的来源。
            x = sx * (GBX + 0.85)
            while abs(x) < W3 - 0.22:
                self.add(box("modil", (x, YF + 0.23, EAVE0 - 0.44),
                             (0.26, 0.46, 0.34), M["stone_mid"]), 0.005)
                x += sx * 0.66
            y = -3.30
            while y < 3.30:
                self.add(box("modil_s", (sx * (W3 + 0.23), y, EAVE0 - 0.44),
                             (0.46, 0.26, 0.34), M["stone_mid"]), 0.005)
                y += 0.66
        self.add(box("corn_back", (0, YB - 0.36, (EAVE0 + EAVE1) * 0.5),
                     (W3 * 2, 0.72, EAVE1 - EAVE0), M["stone_light"]), 0.010)
        x = -4.42
        while x < 4.45:
            if abs(x) > 0.55:          # 让开后墙圆窗
                self.add(box("modil_b", (x, YB - 0.23, EAVE0 - 0.44),
                             (0.26, 0.46, 0.34), M["stone_mid"]), 0.005)
            x += 0.66
        # 檐下阵营色饰带：托架之下、隅石之上（隅石顶 11.24）
        self.add(frame_ring("band_eave", -W3 - 0.062, W3 + 0.062, YB - 0.062, YF + 0.062,
                            EAVE0 - 1.07, EAVE0 - 0.85, 0.10, M["team"]), 0.005)
        # 隅石：主楼四角，分两段（上 / 下），中间让给腰线色带
        for sx in (-1, 1):
            for sy in (-1, 1):
                for (z0, cnt, hwx) in ((1.66, 4, W2), (5.05, 5, W2),
                                       (9.20, 4, W3)):
                    for i in range(cnt):
                        zz = z0 + i * 0.56
                        w = 0.54 if i % 2 else 0.60
                        self.add(box("quoin", (sx * (hwx - w * 0.5 + 0.012),
                                               sy * (YF - w * 0.5 + 0.012), zz + 0.18),
                                     (w, w, 0.36), M["stone_mid"]), 0.006)
        # 中央开间壁柱（上下两段，让开色带）
        for sx in (-1, 1):
            for (tag, z0, z1) in (("_lo", H0 + 0.02, STR0 - 0.05),
                                  ("_mid", STR1 + 0.14, STR2 - 0.08),
                                  ("_hi", STR3 + 0.14, EAVE0)):
                self.add(box("pil_g" + tag, (sx * (GBX - 0.12), YF + 0.045,
                                             (z0 + z1) * 0.5),
                             (0.42, 0.09, z1 - z0), M["stone_mid"]), 0.008)
            self.add(box("pil_g_base", (sx * (GBX - 0.12), YF + 0.075, 0.95),
                         (0.52, 0.15, 0.70), M["stone_light"]), 0.005)
            self.add(box("pil_g_cap", (sx * (GBX - 0.12), YF + 0.085, EAVE0 - 0.18),
                         (0.52, 0.17, 0.24), M["stone_light"]), 0.005)

    # ── 3. 翼楼（3.2 宽，单坡披檐）─────────────────────────────────────────────
    def wing(self, sx):
        """翼楼 = 一堵低墙 + 一片向外的披檐。

        v3 第一版给翼楼做了"小四坡"，结果在正立面上是一个尖三角（因为翼窄而深，
        四坡的脊只能沿进深走），俯视又被主屋面遮掉 —— 三段式完全读不出来。
        披檐（单坡、贴主楼墙高、向外落低）在正面是一条明确的斜线，
        俯视是两条朝外的斜带，和主屋面的四坡形成"主 / 从"两种坡向。
        """
        M = self.M
        x0, x1 = sorted((sx * (WXI - 0.06), sx * WXO))
        cy = (WYB + WYF) * 0.5
        self.add(box("wing_mass", ((x0 + x1) * 0.5, cy, (H0 + WWC) * 0.5),
                     (x1 - x0, WYF - WYB, WWC - H0), M["stone_light"]), 0.030)
        # 墙裙 / 腰线 / 色带（环，内侧段埋在主楼墙里）
        self.add(frame_ring("wing_dado", sx * (WXO + 0.07), sx * (WXI - 0.14),
                            WYB - 0.07, WYF + 0.07, H0, DADO - 0.04, 0.11,
                            M["stone_mid"]), 0.012)
        self.add(frame_ring("wing_dado_cap", sx * (WXO + 0.11), sx * (WXI - 0.18),
                            WYB - 0.11, WYF + 0.11, DADO - 0.08, DADO + 0.02,
                            0.15, M["stone_dark"]), 0.008)
        self.add(frame_ring("wing_band", sx * (WXO + 0.05), sx * (WXI - 0.10),
                            WYB - 0.05, WYF + 0.05, STR0 + 0.006, STR1 - 0.02, 0.09,
                            M["team"]), 0.008)
        self.add(frame_ring("wing_trim", sx * (WXO + 0.08), sx * (WXI - 0.14),
                            WYB - 0.08, WYF + 0.08, STR1 - 0.025, STR1 + 0.04, 0.12,
                            M["team_trim"]), 0.004)
        # 翼的檐下饰带（与主楼那条同高关系，但落在翼的墙顶上）
        self.add(frame_ring("wing_band_e", sx * (WXO + 0.03), sx * (WXI - 0.08),
                            WYB - 0.03, WYF + 0.03, WEAVE0 - 0.26, WEAVE0 - 0.14, 0.07,
                            M["team"]), 0.005)
        # 檐口：前 / 外 / 后 三段（外段只到前后段的内边，不叠同高顶面）
        zc = (WEAVE0 + WEAVE1) * 0.5
        zh = WEAVE1 - WEAVE0
        self.add(box("wing_eave_f", (sx * 6.96, WYF + 0.16, zc),
                     (3.52, 0.32, zh), M["stone_light"]), 0.010)
        self.add(box("wing_eave_o", (sx * 8.56, cy - 0.24, zc - 0.006),
                     (0.32, WEFY1 - WEFY0 - 0.64, zh - 0.012),
                     M["stone_light"]), 0.010)
        self.add(box("wing_eave_b", (sx * 6.96, WYB - 0.16, zc),
                     (3.52, 0.32, zh), M["stone_light"]), 0.010)
        # ── 双坡（山墙朝前）────────────────────────────────────────────────
        # 单坡披檐在正面上是一条平线、俯视是一条窄带 —— 上一版就是这样，
        # 三段式读不出来。改成"山墙朝街"的双坡后：正视是两个三角，
        # 俯视是四条朝外的斜带，和主楼的四坡形成"主三坡 / 从双坡"两种坡向。
        WRZ = WEAVE1 + 1.55                 # 翼脊 10.25（44.1°）
        WYR0, WYR1 = WYB + 0.06, WYF - 0.06  # 屋面 y 范围（让开山花的 0.14）
        for (xa, xb, nm) in ((sx * 6.80, sx * 8.40, "wing_roof_o"),
                             (sx * 6.80, sx * 5.20, "wing_roof_i")):
            self.add(slab(nm, [(xa, WYR1, WRZ), (xa, WYR0, WRZ),
                               (xb, WYR0, WEAVE1), (xb, WYR1, WEAVE1)],
                          ROOF_T - 0.02, M["roof_pale"]), 0.0)
            self.rib(nm.replace("roof", "tile"), (xa, WYR0, WRZ + 0.01),
                     (xa, WYR1, WRZ + 0.01), (xb, WYR0, WEAVE1 + 0.01),
                     (xb, WYR1, WEAVE1 + 0.01), 10, 0.09, 0.05,
                     M["roof_edge"], inset=0.05, lift=0.028)
        # 前后山花（三角墙，伸出屋面 0.07）+ 封山檐 + 圆窗
        tri = [(sx * 5.20, WEAVE1), (sx * 8.40, WEAVE1), (sx * 6.80, WRZ)]
        for (yy, tag) in ((WYF + 0.07, "f"), (WYB - 0.07, "b")):
            # 山墙与墙同色 —— 上一版压深一档，正面出现两个黑三角，比中央山花还重。
            # 分离靠檐口的水平线脚和封山檐，不靠色差。
            self.add(extrude("wing_gable_" + tag, tri, "Y", 0.14, (0, 0),
                             M["stone_light"], offset=yy), 0.014)
            for (xa, xb, za, zb2) in ((sx * 5.20, sx * 6.80, WEAVE1, WRZ),
                                      (sx * 6.80, sx * 8.40, WRZ, WEAVE1)):
                self.add(beam("wing_barge_" + tag, (xa, yy, za), (xb, yy, zb2),
                              0.18, 0.16, M["stone_light"]), 0.006)
            self.add(ring_y("wing_oc_" + tag, (sx * 6.80, yy, 9.42), 0.255, 0.365,
                            0.10, 14, M["gold"]), 0.004)
            self.add(cyl("wing_oc2_" + tag, (sx * 6.80, yy, 9.42), 0.26, 0.08, 14,
                         M["coal"], axis="Y"), 0.003)

        # 翼的一层拱窗（前脸 + 外侧面；"X" 轴的 u 是 Y 坐标，不是 X）
        self.win_arch("win_w", sx * 6.80, 1.68, 1.05, 2.45, "Y", 1, WYF)
        self.win_rect("win_w2", sx * 6.80, 5.05, 1.02, 2.20, "Y", 1, WYF)
        self.win_arch("win_wo", -1.05, 1.68, 0.92, 2.35, "X", sx, sx * WXO)
        self.win_rect("win_wo2", -1.05, 5.05, 0.92, 2.10, "X", sx, sx * WXO)
        self.win_arch("win_wo_b", 1.35, 1.68, 0.92, 2.35, "X", sx, sx * WXO)
        self.win_rect("win_wo2_b", 1.35, 5.05, 0.92, 2.10, "X", sx, sx * WXO)
        # 翼外角隅石：墙裙之上三段 + 色带之上一段
        for i in range(4):
            zz = 1.66 + i * 0.62
            w = 0.48 if i % 2 else 0.54
            self.add(box("quoin_w", (sx * (WXO - w * 0.5 + 0.012),
                                     WYF - w * 0.5 + 0.012, zz + 0.17),
                         (w, w, 0.34), M["stone_mid"]), 0.006)
            self.add(box("quoin_wb", (sx * (WXO - w * 0.5 + 0.012),
                                      WYB + w * 0.5 - 0.012, zz + 0.17),
                         (w, w, 0.34), M["stone_mid"]), 0.006)
        w = 0.50
        self.add(box("quoin_w2", (sx * (WXO - w * 0.5 + 0.012),
                                  WYF - w * 0.5 + 0.012, 5.58),
                     (w, w, 0.30), M["stone_mid"]), 0.005)
        self.add(box("quoin_w2b", (sx * (WXO - w * 0.5 + 0.012),
                                   WYB + w * 0.5 - 0.012, 5.58),
                     (w, w, 0.30), M["stone_mid"]), 0.005)

    # ── 4. 拱门 / 门套 / 门扇 ────────────────────────────────────────────────
    def gate(self):
        M = self.M
        # 门洞内壁（深色，给门扇一个背景）
        for sgn in (-1, 1):
            self.add(box("gate_jamb", (sgn * (GW - 0.03), YF - DWALL * 0.5 - 0.01,
                                       (H0 + SPRING) * 0.5),
                         (0.06, DWALL - 0.04, SPRING - H0), M["stone_dark"]), 0.0)
        # 拱券石 / 门柱 / 拱心石
        self.add(arch_band("gate_arch", 0.0, SPRING, GW, GW + 0.24,
                           YF - 0.02, YF + 0.14, M["stone_mid"], segs=10), 0.014)
        for sgn in (-1, 1):
            self.add(box("gate_post", (sgn * (GW + 0.12), YF + 0.06,
                                       (H0 + SPRING) * 0.5),
                         (0.24, 0.14, SPRING - H0), M["stone_mid"]), 0.010)
            self.add(box("gate_post_b", (sgn * (GW + 0.12), YF + 0.10, H0 + 0.36),
                         (0.30, 0.20, 0.22), M["stone_light"]), 0.005)
        self.add(extrude("gate_key", [(-0.17, ARCH_TOP - 0.04), (0.17, ARCH_TOP - 0.04),
                                      (0.11, ARCH_TOP + 0.24), (-0.11, ARCH_TOP + 0.24)],
                         "Y", 0.18, (0, 0), M["stone_mid"], offset=YF + 0.07), 0.006)
        # 门扇：双开（0.55 → 2.30），上方半圆扇窗
        leaf = GW - 0.04
        for sgn in (-1, 1):
            cx = sgn * leaf * 0.5
            yy = DOOR_Y + 0.055
            self.add(box("gate_leaf", (cx, DOOR_Y, (H0 + SPRING) * 0.5),
                         (leaf - 0.015, 0.10, SPRING - H0), M["team"]), 0.010)
            self.add(box("gate_stile", (sgn * (leaf - 0.08), yy, (H0 + SPRING) * 0.5),
                         (0.09, 0.03, SPRING - H0 - 0.10), M["wood_dark"]), 0.002)
            for zz in (H0 + 0.12, SPRING - 0.11):
                self.add(box("gate_rail", (cx, yy, zz),
                             (leaf - 0.09, 0.03, 0.13), M["wood_dark"]), 0.002)
            for zz in (H0 + 0.50, SPRING - 0.45):
                self.add(box("gate_strap", (cx, yy + 0.008, zz),
                             (leaf - 0.14, 0.03, 0.08), M["iron"]), 0.003)
            self.add(box("gate_stud", (cx + sgn * 0.22, yy + 0.008, H0 + 0.92),
                         (0.05, 0.03, 0.05), M["gold"]), 0.002)
            self.add(revolve("gate_ring", [(0.030, 0.0), (0.044, 0.012), (0.030, 0.024)],
                             8, (sgn * 0.30, DOOR_Y + 0.07, H0 + 0.78), M["gold"]), 0.0, 1)
        # 半圆扇窗：玻璃 + 铁艺辐射条 + 横档
        r = GW - 0.06
        glow = [(-r, 0.0), (r, 0.0)]
        for s in range(1, 12):
            a = math.pi * s / 12
            glow.append((r * math.cos(a), r * math.sin(a)))
        self.add(extrude("gate_glow", glow, "Y", 0.06, (0, SPRING),
                         M["glass"], offset=DOOR_Y), 0.0)
        for s in range(1, 4):
            a = math.pi * s / 4
            self.add(beam("gate_bar", (0, DOOR_Y + 0.04, SPRING),
                          (r * math.cos(a), DOOR_Y + 0.04, SPRING + r * math.sin(a)),
                          0.045, 0.045, M["iron"]), 0.002)
        self.add(box("gate_bar2", (0, DOOR_Y + 0.04, SPRING + r * 0.52),
                     (r * 1.5, 0.045, 0.045), M["iron"]), 0.002)
        self.add(box("gate_seam", (0, DOOR_Y + 0.045, (H0 + SPRING) * 0.5),
                     (0.05, 0.02, SPRING - H0 - 0.02), M["wood_dark"]), 0.002)
        # 门洞两侧壁灯
        for sgn in (-1, 1):
            self.add(box("sconce_arm", (sgn * 1.54, YF + 0.07, 3.68),
                         (0.26, 0.08, 0.06), M["iron"]), 0.003)
            self.add(box("sconce_glass", (sgn * 1.54, YF + 0.16, 3.58),
                         (0.18, 0.18, 0.24), M["glow"]), 0.004)
            self.add(box("sconce_cap", (sgn * 1.54, YF + 0.16, 3.73),
                         (0.24, 0.24, 0.05), M["iron"]), 0.003)
            self.add(box("sconce_base", (sgn * 1.54, YF + 0.16, 3.44),
                         (0.22, 0.22, 0.05), M["iron"]), 0.003)

    # ── 5. 中央山花（断檐 + 三角 + 盾徽 + 石球）────────────────────────────
    def gable(self):
        M = self.M
        # 山花必须是"体量"不是"板"：0.26 厚时两侧露出两块三角形阴影，
        # 读作贴在坡上的一块三角板。做成 1.15 厚的楔，背面埋进主屋面。
        self.add(extrude("gable_body",
                         [(-GBX, 0.0), (GBX, 0.0), (0.0, GBZ)], "Y", 1.15,
                         (0, EAVE0), M["stone_light"],
                         offset=YF + 0.075 - 0.575), 0.020)
        # 山花底檐（补上被断开的檐口，只占中央 3.6 m）
        self.add(box("gable_sill", (0, YF + 0.20, EAVE0 - 0.02),
                     (GBX * 2 - 0.02, 0.44, 0.13), M["stone_mid"]), 0.008)
        for sx in (-1, 1):
            self.add(beam("gable_rake", (sx * (GBX + 0.04), YF + 0.22, EAVE0 + 0.02),
                          (0.0, YF + 0.22, EAVE0 + GBZ + 0.03),
                          0.19, 0.15, M["stone_light"]), 0.006)
            self.add(box("gable_sh_b", (sx * (GBX - 0.09), YF + 0.20, EAVE0 + 0.07),
                         (0.36, 0.44, 0.18), M["stone_mid"]), 0.004)
        # 山花里的盾徽（金边蓝底 + 冠）
        self.crest("crest_g", "Y", 0.0, YF + 0.250, EAVE0 + 0.44, 0.58)
        # 顶饰：石座 + 金球
        self.add(box("gable_fin_base", (0, YF + 0.11, EAVE0 + GBZ + 0.09),
                     (0.26, 0.28, 0.15), M["stone_mid"]), 0.004)
        self.add(revolve("gable_fin", [(0.0, 0.0), (0.072, 0.03), (0.100, 0.10),
                                       (0.058, 0.16), (0.0, 0.19)], 8,
                         (0, YF + 0.11, EAVE0 + GBZ + 0.15), M["gold"]), 0.0, 1)

    # ── 6. 钟塔：石座 / 塔身 / 钟面 / 钟亭 / 穹顶 / 旗 ───────────────────────
    def tower(self):
        M = self.M
        # 塔座
        self.add(box("tw_seat", (0, 0, (TB0 + TB1) * 0.5),
                     (TBX * 2, TBY * 2, TB1 - TB0), M["stone_light"]), 0.030)
        self.add(box("tw_seat_skirt", (0, 0, TB0 + 0.24),
                     (TBX * 2 + 0.16, TBY * 2 + 0.16, 0.48), M["stone_mid"]), 0.012)
        self.add(box("tw_seat_cap", (0, 0, TB1 - 0.11),
                     (TBX * 2 + 0.20, TBY * 2 + 0.20, 0.22), M["stone_mid"]), 0.008)
        # 塔座四角壁柱
        for sx in (-1, 1):
            for sy in (-1, 1):
                self.add(box("tw_pil_s", (sx * (TBX - 0.05), sy * (TBY - 0.05),
                                       (TB0 + TB1) * 0.5 + 0.12),
                             (0.14, 0.14, TB1 - TB0 - 0.62), M["stone_mid"]), 0.005)
        # 塔座色带（阵营色：高带）
        self.add(frame_ring("tw_band", -TBX - 0.05, TBX + 0.05, -TBY - 0.05, TBY + 0.05,
                            TB1 - 0.58, TB1 - 0.36, 0.12, M["team"]), 0.006)
        self.add(frame_ring("tw_band_t", -TBX - 0.08, TBX + 0.08, -TBY - 0.08, TBY + 0.08,
                            TB1 - 0.36, TB1 - 0.31, 0.15, M["team_trim"]), 0.003)
        # 四角小尖塔
        for sx in (-1, 1):
            for sy in (-1, 1):
                px, py = sx * (TBX - 0.11), sy * (TBY - 0.11)
                self.add(box("tw_pier", (px, py, TB1 + 0.20),
                             (0.30, 0.30, 0.40), M["stone_light"]), 0.006)
                self.add(frustum("tw_pier_tip", TB1 + 0.40, TB1 + 0.68,
                                 0.30, 0.30, 0.05, 0.05, px, py, M["stone_mid"]), 0.003)
        # 塔身
        self.add(box("tw_body", (0, 0, (TT0 + TT1) * 0.5),
                     (TWX * 2, TWY * 2, TT1 - TT0), M["stone_light"]), 0.028)
        for sx in (-1, 1):
            for sy in (-1, 1):
                self.add(box("tw_pil", (sx * (TWX - 0.09), sy * (TWY - 0.09),
                                        (TT0 + TT1) * 0.5),
                             (0.26, 0.26, TT1 - TT0 - 0.10), M["stone_mid"]), 0.008)
        self.add(frame_ring("tw_str", -TWX - 0.05, TWX + 0.05, -TWY - 0.05, TWY + 0.05,
                            TT0 + 0.04, TT0 + 0.12, 0.10, M["stone_mid"]), 0.005)
        self.add(frame_ring("tw_corn", -TWX - 0.13, TWX + 0.13, -TWY - 0.13, TWY + 0.13,
                            TT1 - 0.18, TT1 - 0.02, 0.20, M["stone_mid"]), 0.010)
        # 三面钟
        self.clock_face("clock_f", (0.0, TWY + 0.13, CLK_Z), "Y")
        for sx in (-1, 1):
            self.clock_face("clock_s", (sx * (TWX + 0.13), 0.0, CLK_Z), "X")
        # 钟亭：四角柱 + 肩墙 + 拱券（开放做法，铜钟从任何角度都看得见）
        # 上一版是"四面石墙各开一拱"，但钟在亭心、墙厚 0.2、开口只有 1.6 m，
        # 3/4 视角下钟被开口边缘整个挡掉 —— 读作"空亭子"。改成拱廊后，
        # 柱间的空隙就是钟的背景，钟才成其为"钟亭"。
        self.add(box("bf_floor", (0, 0, BF0 + 0.05), (BFX * 2 + 0.10, BFY * 2 + 0.10, 0.10),
                     M["stone_mid"]), 0.006)
        self.add(box("bf_deck", (0, 0, BF0 + 0.14), (TWX * 2 + 0.06, TWY * 2 + 0.06, 0.12),
                     M["stone_dark"]), 0.0)
        CX, CY = BFX - 0.13, BFY - 0.13
        for sx in (-1, 1):
            for sy in (-1, 1):
                px, py = sx * CX, sy * CY
                self.add(box("bf_col", (px, py, (BF0 + 0.10 + BF1 - 0.20) * 0.5),
                             (0.32, 0.32, BF1 - 0.20 - BF0 - 0.10),
                             M["stone_light"]), 0.008)
                self.add(box("bf_col_b", (px, py, BF0 + 0.22), (0.40, 0.40, 0.18),
                             M["stone_mid"]), 0.005)
                self.add(box("bf_col_c", (px, py, BF1 - 0.26), (0.40, 0.40, 0.16),
                             M["stone_mid"]), 0.005)
        # 拱券：半径直接等于柱间净距的一半，两端落在柱子上（没有肩墙）
        for sy in (-1, 1):
            self.add(arch_band("bf_arch", 0.0, BFS, CX - 0.16, CX - 0.05,
                               sy * (CY - 0.16), sy * (CY + 0.16),
                               M["stone_mid"], segs=8), 0.005)
        for sx in (-1, 1):
            self.add(arch_band_x("bf_arch_s", 0.0, BFS, CY - 0.16, CY - 0.05,
                                 sx * (CX - 0.16), sx * (CX + 0.16),
                                 M["stone_mid"], segs=8), 0.005)
        # 顶枋 + 压顶
        self.add(frame_ring("bf_corn", -BFX - 0.10, BFX + 0.10, -BFY - 0.10, BFY + 0.10,
                            BF1 - 0.10, BF1, 0.26, M["stone_mid"]), 0.008)
        self.add(frame_ring("bf_cap", -BFX - 0.16, BFX + 0.16, -BFY - 0.16, BFY + 0.16,
                            BF1, BF1 + 0.10, 0.30, M["stone_light"]), 0.006)
        # 吊钟梁 + 铜钟 + 钟舌
        self.add(box("bf_beam", (0, 0, BF1 - 0.34), (CX * 2 - 0.12, 0.12, 0.12),
                     M["wood_dark"]), 0.005)
        self.add(revolve("bf_bell", [(0.42, 0.0), (0.40, 0.06), (0.30, 0.24),
                                     (0.20, 0.42), (0.13, 0.56), (0.08, 0.62)], 12,
                         (0, 0, BF0 + 0.36), M["gold"]), 0.006, 1)
        self.add(box("bf_bell_top", (0, 0, BF0 + 1.02), (0.18, 0.08, 0.08),
                     M["iron"]), 0.003)
        self.add(box("bf_bell_chain", (0, 0, BF0 + 0.95), (0.05, 0.05, 0.16),
                     M["iron"]), 0.002)
        self.add(box("bf_clapper", (0, 0, BF0 + 0.40), (0.06, 0.06, 0.26),
                     M["iron"]), 0.002)
        # 穹座
        self.add(box("dm_base", (0, 0, (DM0 + DM1) * 0.5),
                     (2.96, 2.86, DM1 - DM0), M["stone_light"]), 0.008)
        self.add(frame_ring("dm_band", -1.50, 1.50, -1.45, 1.45, DM0 + 0.02, DM0 + 0.11,
                            0.10, M["gold"]), 0.003)
        # 八边穹顶（阶梯 8 边形 = 硬边语言里的"穹"）
        self.add(revolve("dm_dome",
                         [(1.24, -0.02), (1.21, 0.10), (1.06, 0.34),
                          (0.86, 0.60), (0.62, 0.84), (0.31, 1.04), (0.0, 1.18)],
                         8, (0, 0, DM1), M["roof"]), 0.0)
        for k in range(8):
            a = TAU * k / 8
            self.add(beam("dm_rib", (1.24 * math.cos(a), 1.24 * math.sin(a), DM1 + 0.04),
                          (0.09 * math.cos(a), 0.09 * math.sin(a), DM1 + 1.14),
                          0.05, 0.045, M["roof_edge"]), 0.002)
        # 采光亭
        self.add(revolve("lantern_col", [(0.28, 0.00), (0.26, 0.05), (0.26, 0.24),
                                         (0.30, 0.27)], 8, (0, 0, LANT0 - 0.04),
                         M["stone_light"]), 0.004)
        for k in range(8):
            a = TAU * k / 8 + TAU / 16
            self.add(box("lantern_win", (0.265 * math.cos(a), 0.265 * math.sin(a),
                                         LANT0 + 0.13),
                         (0.08, 0.08, 0.18), M["glow"], rot=(0, 0, a)), 0.002)
        self.add(revolve("lantern_cap", [(0.36, 0.00), (0.32, 0.04), (0.20, 0.14),
                                         (0.07, 0.20), (0.0, 0.24)], 8,
                         (0, 0, LANT1 - 0.05), M["roof_edge"]), 0.0)
        # 顶尖 + 金球
        self.add(revolve("sp_finial", [(0.0, 0.0), (0.07, 0.03), (0.10, 0.11),
                                       (0.06, 0.19), (0.0, 0.23)], 8,
                         (0, 0, BALL_Z - 0.30), M["gold"]), 0.0, 1)
        # 旗杆 + 燕尾旗
        self.add(revolve("flag_pole", [(0.045, 0.0), (0.036, POLE_TOP - BALL_Z)], 6,
                         (0, 0, BALL_Z), M["wood_dark"]), 0.0, 1)
        self.add(revolve("flag_tip", [(0.070, 0.0), (0.050, 0.05), (0.016, 0.10)], 8,
                         (0, 0, POLE_TOP - 0.02), M["gold"]), 0.0, 1)
        fw, fh = 0.98, 0.64
        prof = [(0.0, 0.0), (fw, -0.07), (fw * 0.76, -fh * 0.50),
                (fw, -fh * 0.93), (0.0, -fh)]
        self.add(extrude("flag_cloth", prof, "Y", 0.032, (0.0, FLAG_TOP - 0.05),
                         M["team"], offset=0.0), 0.004)
        self.add(box("flag_hoist", (0.028, 0.0, FLAG_TOP - 0.05 - fh * 0.46),
                     (0.07, 0.055, fh * 0.92), M["team_trim"]), 0.003)
        self.crest("flag_crest", "Y", 0.42, 0.0125, FLAG_TOP - 0.53, 0.32)

    # ── 7. 钟面 ─────────────────────────────────────────────────────────────
    def clock_face(self, name, center, face):
        M = self.M
        cx, cy, cz = center
        if face == "Y":
            self.add(ring_y(name + "_ring", (cx, cy + 0.02, cz), 0.56, 0.68, 0.14, 20,
                            M["gold"]), 0.006)
            self.add(cyl(name + "_disc", (cx, cy + 0.02, cz), 0.57, 0.08, 20,
                         M["coal"], axis="Y"), 0.004)
            for k in range(12):
                a = TAU * k / 12
                self.add(box(name + "_tick", (cx + math.sin(a) * 0.46, cy + 0.075,
                                              cz + math.cos(a) * 0.46),
                             (0.045, 0.025, 0.085), M["gold"], rot=(0, -a, 0)), 0.002)
            for (ang, ln, w) in ((math.radians(-52), 0.40, 0.060),
                                 (math.radians(28), 0.27, 0.048)):
                self.add(box(name + "_hand",
                             (cx + math.sin(ang) * ln * 0.5, cy + 0.082,
                              cz + math.cos(ang) * ln * 0.5),
                             (w, 0.025, ln), M["gold"], rot=(0, -ang, 0)), 0.002)
            self.add(cyl(name + "_pin", (cx, cy + 0.086, cz), 0.045, 0.03, 8,
                         M["gold"], axis="Y"), 0.002)
        else:
            sgn = 1 if cx > 0 else -1
            self.add(ring_x(name + "_ring", (cx - sgn * 0.02, cy, cz), 0.60, 0.72, 0.14,
                            20, M["gold"]), 0.006)
            self.add(cyl(name + "_disc", (cx - sgn * 0.02, cy, cz), 0.57, 0.08, 20,
                         M["coal"], axis="X"), 0.004)
            for k in range(12):
                a = TAU * k / 12
                self.add(box(name + "_tick", (cx - sgn * 0.075, cy + math.sin(a) * 0.46,
                                              cz + math.cos(a) * 0.46),
                             (0.025, 0.045, 0.085), M["gold"], rot=(-a, 0, 0)), 0.002)
            for (ang, ln, w) in ((math.radians(-52), 0.40, 0.060),
                                 (math.radians(28), 0.27, 0.048)):
                self.add(box(name + "_hand",
                             (cx - sgn * 0.082, cy + math.sin(ang) * ln * 0.5,
                              cz + math.cos(ang) * ln * 0.5),
                             (0.025, w, ln), M["gold"], rot=(-ang, 0, 0)), 0.002)
            self.add(cyl(name + "_pin", (cx - sgn * 0.086, cy, cz), 0.045, 0.03, 8,
                         M["gold"], axis="X"), 0.002)

    # ── 8. 窗 ───────────────────────────────────────────────────────────────
    def win_arch(self, name, u, cz, w, h, axis="Y", out=1, wall=None, mat=None):
        M = self.M
        mat = M["glass"] if mat is None else mat
        hw = w * 0.5
        straight = h - hw
        if axis == "Y":
            y0 = YF if wall is None else wall
            self.add(extrude(name + "_glass", arch_profile(w, straight, 8), "Y", 0.09,
                             (u, cz), mat, offset=y0 + out * 0.01), 0.0)
            self.add(arch_band(name + "_arch", u, cz + straight, hw, hw + 0.14,
                               y0 + out * 0.03, y0 + out * 0.14, M["stone_mid"],
                               segs=8), 0.009)
            for sgn in (-1, 1):
                self.add(box(name + "_jamb", (u + sgn * (hw + 0.07),
                                              y0 + out * 0.09, cz + straight * 0.5),
                             (0.14, 0.20, straight), M["stone_mid"]), 0.007)
            self.add(box(name + "_sill", (u, y0 + out * 0.09, cz - 0.03),
                         (w + 0.34, 0.22, 0.09), M["stone_light"]), 0.005)
            self.add(box(name + "_mull", (u, y0 + out * 0.06, cz + straight * 0.5),
                         (0.075, 0.055, straight), M["wood_dark"]), 0.002)
            self.add(box(name + "_trans", (u, y0 + out * 0.055, cz + straight * 0.52),
                         (w - 0.06, 0.05, 0.075), M["wood_dark"]), 0.002)
        else:
            x0 = WXO if wall is None else wall
            self.add(extrude(name + "_glass", arch_profile(w, straight, 8), "X", 0.09,
                             (u, cz), mat, offset=x0 + out * 0.01), 0.0)
            self.add(arch_band_x(name + "_arch", u, cz + straight, hw, hw + 0.14,
                                 x0 + out * 0.03, x0 + out * 0.14, M["stone_mid"],
                                 segs=8), 0.009)
            for sgn in (-1, 1):
                self.add(box(name + "_jamb", (x0 + out * 0.09,
                                              u + sgn * (hw + 0.07), cz + straight * 0.5),
                             (0.20, 0.14, straight), M["stone_mid"]), 0.007)
            self.add(box(name + "_sill", (x0 + out * 0.09, u, cz - 0.03),
                         (0.22, w + 0.34, 0.09), M["stone_light"]), 0.005)
            self.add(box(name + "_mull", (x0 + out * 0.06, u, cz + straight * 0.5),
                         (0.055, 0.055, straight), M["wood_dark"]), 0.002)

    def win_rect(self, name, u, cz, w, h, axis="Y", out=1, wall=None, mat=None):
        M = self.M
        mat = M["glass"] if mat is None else mat
        hw = w * 0.5
        if axis == "Y":
            y0 = YF if wall is None else wall
            self.add(box(name + "_glass", (u, y0 + out * 0.01, cz + h * 0.5),
                         (w, 0.09, h), mat), 0.0)
            for sgn in (-1, 1):
                self.add(box(name + "_side", (u + sgn * (hw + 0.07),
                                              y0 + out * 0.09, cz + h * 0.5),
                             (0.14, 0.19, h + 0.18), M["stone_mid"]), 0.007)
            self.add(box(name + "_top", (u, y0 + out * 0.10, cz + h + 0.07),
                         (w + 0.28, 0.21, 0.14), M["stone_mid"]), 0.005)
            self.add(box(name + "_sill", (u, y0 + out * 0.11, cz - 0.05),
                         (w + 0.34, 0.23, 0.10), M["stone_light"]), 0.005)
            self.add(box(name + "_key", (u, y0 + out * 0.12, cz + h + 0.06),
                         (0.17, 0.25, 0.30), M["stone_light"]), 0.004)
            self.add(box(name + "_mull", (u, y0 + out * 0.06, cz + h * 0.5),
                         (0.075, 0.055, h - 0.04), M["wood_dark"]), 0.002)
            self.add(box(name + "_trans", (u, y0 + out * 0.055, cz + h * 0.60),
                         (w - 0.05, 0.05, 0.075), M["wood_dark"]), 0.002)
        else:
            x0 = WXO if wall is None else wall
            self.add(box(name + "_glass", (x0 + out * 0.01, u, cz + h * 0.5),
                         (0.09, w, h), mat), 0.0)
            for sgn in (-1, 1):
                self.add(box(name + "_side", (x0 + out * 0.09,
                                              u + sgn * (hw + 0.07), cz + h * 0.5),
                             (0.19, 0.14, h + 0.18), M["stone_mid"]), 0.007)
            self.add(box(name + "_top", (x0 + out * 0.10, u, cz + h + 0.07),
                         (0.21, w + 0.28, 0.14), M["stone_mid"]), 0.005)
            self.add(box(name + "_sill", (x0 + out * 0.11, u, cz - 0.05),
                         (0.23, w + 0.34, 0.10), M["stone_light"]), 0.005)
            self.add(box(name + "_key", (x0 + out * 0.12, u, cz + h + 0.06),
                         (0.25, 0.17, 0.30), M["stone_light"]), 0.004)
            self.add(box(name + "_mull", (x0 + out * 0.06, u, cz + h * 0.5),
                         (0.055, 0.055, h - 0.04), M["wood_dark"]), 0.002)

    # ── 9. 主楼立面窗（5 开间）──────────────────────────────────────────────
    def windows(self):
        M = self.M
        self.win_arch("win_c", 0.0, 4.95, 1.62, 3.10, "Y", 1, YF)
        self.win_arch("win_c3", 0.0, 9.30, 1.24, 1.80, "Y", 1, YF)
        for sx in (-1, 1):
            x = sx * 3.60
            self.win_arch("win_f", x, 1.68, 1.35, 2.40, "Y", 1, YF)
            self.win_rect("win_f2", x, 4.95, 1.45, 2.90, "Y", 1, YF)
            self.win_rect("win_f3", sx * 3.15, 9.30, 1.05, 1.75, "Y", 1, YF)
        # 后墙
        for sx in (-1, 1):
            x = sx * 3.20
            self.win_arch("win_b", x, 1.68, 1.30, 2.35, "Y", -1, YB)
            self.win_rect("win_b2", x, 4.95, 1.38, 2.85, "Y", -1, YB)
            self.win_rect("win_b3", sx * 3.15, 9.30, 1.05, 1.75, "Y", -1, YB)
        self.add(ring_y("oculus_b", (0.0, YB - 0.03, 10.42), 0.28, 0.40, 0.10, 16,
                        M["gold"]), 0.005)
        self.add(cyl("oculus_b2", (0.0, YB - 0.01, 10.42), 0.29, 0.06, 16,
                     M["coal"], axis="Y"), 0.003)
        # 主楼侧墙在翼楼之后露出的 0.8 m：一条窄缝窗，避免那块石头是空白的
        for sx in (-1, 1):
            for sy in (-1, 1):
                self.win_rect("win_s3", sy * 1.55, 9.30, 1.05, 1.75, "X", sx, sx * W3)

    # ── 10. 屋面 ────────────────────────────────────────────────────────────
    def roof_z(self, y):
        """主屋面（前 / 后坡）在 |y| 处的上表面标高。"""
        return EAVE1 + (EFY - abs(y)) / EFY * (RIDGE_Z - EAVE1)

    def dormer(self, name, x, side, dy):
        """前 / 后坡上的老虎窗：石框 + 梯形侧墙 + 四坡小帽 + 方窗。

        空屋面是"被砍了一截"的主因 —— 坡面上除了瓦垄什么都没有，
        视线从窗墙直接蹦到塔。老虎窗给坡面加体积：俯视是凸起，
        正视切开坡面，3/4 视角是最有"小镇感"的一层。
        """
        M = self.M
        yf = side * dy
        zr = self.roof_z(dy)
        yb = dy - DORM_D
        zb = self.roof_z(yb)
        z1 = zr + DORM_H
        hw = DORM_W * 0.5
        # 正面墙（下端埋进屋面 0.32，瓦垄会插进来 —— 老虎窗收边本来如此）
        self.add(box(name + "_face", (x, yf, (zr - 0.32 + z1) * 0.5),
                     (DORM_W, 0.16, z1 - zr + 0.32), M["stone_light"]), 0.010)
        # 两块梯形侧墙：底边跟着屋面爬升，顶边水平
        prof = [(side * yb, zb - 0.08), (side * dy, zr - 0.08),
                (side * dy, z1 - 0.02), (side * yb, z1 - 0.02)]
        for sgn in (-1, 1):
            pts = [(x + sgn * hw, yy, zz) for (yy, zz) in prof]
            if sgn < 0:
                pts = list(reversed(pts))
            self.add(slab(name + "_sd", pts, 0.16, M["stone_light"]), 0.008)
        # 四坡小帽：底与正面墙顶齐，向后盖满进深并挑出 0.12
        self.add(frustum(name + "_cap", z1 - 0.02, z1 - 0.02 + DORM_CAP,
                         DORM_W + 0.16, DORM_D + 0.28, 0.24, 0.20,
                         x, side * (dy - DORM_D * 0.5 + 0.05), M["roof"]), 0.008)
        # 方窗（"田"字棂在 RTS 距离上会糊掉，做两扇高窗 + 中梃）
        self.win_rect(name + "_w", x, zr + 0.20, 1.02, DORM_H - 0.62, "Y", side,
                      side * (dy + 0.085))

    def skylight(self, name, x, y, w, l):
        """后坡天窗：石框 + 玻璃，平贴坡面（只填空屋面，不进剪影）。"""
        M = self.M
        ya, yb = y + l * 0.5, y - l * 0.5
        for (nm, hw, mat, lift, th) in ((name + "_rim", w * 0.5 + 0.10,
                                         M["stone_mid"], 0.08, 0.10),
                                        (name + "_gl", w * 0.5,
                                         M["glass"], 0.13, 0.05)):
            pts = [(x - hw, ya, self.roof_z(ya) + lift),
                   (x - hw, yb, self.roof_z(yb) + lift),
                   (x + hw, yb, self.roof_z(yb) + lift),
                   (x + hw, ya, self.roof_z(ya) + lift)]
            self.add(slab(nm, pts, th, mat), 0.004)

    def roofs(self):
        M = self.M
        ez = EAVE1
        # 主楼四坡
        pf = [(-EFX, EFY, ez), (EFX, EFY, ez), (RIDGE_X, 0.0, RIDGE_Z),
              (-RIDGE_X, 0.0, RIDGE_Z)]
        pb = [(-EFX, -EFY, ez), (EFX, -EFY, ez), (RIDGE_X, 0.0, RIDGE_Z),
              (-RIDGE_X, 0.0, RIDGE_Z)]
        pl = [(-EFX, EFY, ez), (-EFX, -EFY, ez), (-RIDGE_X, 0.0, RIDGE_Z)]
        pr = [(EFX, EFY, ez), (EFX, -EFY, ez), (RIDGE_X, 0.0, RIDGE_Z)]
        for nm, pp in (("roof_f", pf), ("roof_b", pb), ("roof_l", pl), ("roof_r", pr)):
            self.add(slab(nm, pp, ROOF_T, M["roof"]), 0.0)
        # 瓦垄用比屋面亮一档的 roof_pale（明暗 1.5:1 → 2.4:1），
        # 屋顶才读得出"坡面起伏"，而不是一整片深灰。
        self.rib("tile_f", pf[0], pf[1], pf[3], pf[2], 15, 0.105, 0.060,
                 M["roof_pale"], gapx=GBX + 0.16)
        self.rib("tile_b", pb[0], pb[1], pb[3], pb[2], 15, 0.105, 0.060,
                 M["roof_pale"])
        self.rib("tile_l", pl[0], pl[1], pl[2], pl[2], 5, 0.100, 0.055,
                 M["roof_pale"])
        self.rib("tile_r", pr[0], pr[1], pr[2], pr[2], 5, 0.100, 0.055,
                 M["roof_pale"])
        # 老虎窗：前坡两个（中央让给山花），后坡两个（让开塔座与烟囱）
        for sx in (-1, 1):
            self.dormer("roof_dorm_f", sx * 2.90, 1, DORM_YF)
            self.skylight("roof_sky", sx * 2.20, -2.30, 0.90, 1.05)
        # 封檐板 + 檐口压条
        # 封檐板：立在石檐口之上、比石材收 0.04（这样石檐口是剪影最外的一条线）
        self.add(frame_ring("eave_fascia", -EFX + 0.03, EFX - 0.03, -EFY + 0.03,
                            EFY - 0.03, ez, ez + 0.18, 0.14,
                            M["roof_edge"]), 0.005)
        # 正脊：塔座两侧各一段
        for sx in (-1, 1):
            self.add(box("ridge_c", (sx * (RIDGE_X + TBX + 0.03) * 0.5, 0,
                                     RIDGE_Z + 0.01),
                         (RIDGE_X - TBX - 0.03, 0.18, 0.13), M["roof_edge"]), 0.004)
        for sx in (-1, 1):
            for sy in (-1, 1):
                self.add(beam("hip", (sx * EFX, sy * EFY, ez + 0.01),
                              (sx * RIDGE_X, 0.0, RIDGE_Z + 0.01),
                              0.10, 0.075, M["roof_edge"]), 0.003)
        # 两个烟囱（后坡上，低于正脊 0.45，不抢中轴）
        for sx in (-1, 1):
            cx = sx * 3.40
            self.add(box("chimney", (cx, -2.05, 14.55), (0.54, 0.54, 1.90),
                         M["stone_mid"]), 0.010)
            self.add(box("chimney_band", (cx, -2.05, 15.18), (0.62, 0.62, 0.14),
                         M["stone_light"]), 0.005)
            self.add(box("chimney_cap", (cx, -2.05, 15.50), (0.70, 0.70, 0.14),
                         M["stone_dark"]), 0.005)
            self.add(box("chimney_flue", (cx, -2.05, 15.58), (0.30, 0.30, 0.10),
                         M["coal"]), 0.003)

    def rib(self, name, p0, p1, p3, p2, n, w, t, mat, inset=0.07, lift=0.032,
            gapx=None):
        for ob in rib_quad(name, p0, p1, p3, p2, n, w, t, mat, inset, lift, gapx):
            self.add(ob, 0.0)

    # ── 11. 台阶旁的碎石（只留 3 块：18 m 宽的立面上，草簇只有 3–4 像素，
    #        读不出语义，反而把包围盒撑宽 0.7 m —— 删掉）──────────────────────
    def props(self):
        M = self.M
        for (px, py) in ((-4.20, 3.92), (4.35, 3.88), (-2.62, 4.36)):
            self.add(box("pebble", (px, py, 0.035), (0.19, 0.13, 0.07),
                         M["stone_mid"], rot=(0, 0.3, 0.4)), 0.004)

    # ── 12. 组装 / 收尾 ─────────────────────────────────────────────────────
    def build(self):
        for step in (self.base, self.mass, self.gate, self.gable, self.tower,
                     self.windows, self.roofs, self.props):
            step()
        for sx in (-1, 1):
            self.wing(sx)
        return self

    def finalize(self, bevel=True):
        skip_cc = ("roof_", "wing_roof", "tile_", "wing_tile", "ridge_", "hip",
                   "wing_hip", "eave_", "corn_", "dado", "string", "band_",
                   "quoin", "dentil", "pil_", "win", "gate_", "clock_", "bf_",
                   "dm_", "lantern_", "sp_", "flag", "gable_", "crest",
                   "step", "plinth", "cheek", "newel", "apron", "threshold",
                   "sconce", "tuft", "pebble", "chimney", "oculus", "wing_band",
                   "wing_trim", "wing_eave", "wing_ridge", "wing_dado")
        for (ob, bev, sub, seg) in self.items:
            co = ob.data.vertices
            dims = [max(v.co[i] for v in co) - min(v.co[i] for v in co) for i in range(3)]
            vol = dims[0] * dims[1] * dims[2]
            chunky = min(dims) >= 0.12 and vol >= 0.14
            n = ob.name
            if self.smooth:
                cc = 1 if (chunky and not n.startswith(skip_cc)) else 0
                L.finalize(ob, bevel=max(bev, 0.008), seg=1, sub=cc, flat=False)
            else:
                b = 0.0 if (not bevel or max(dims) < 1.10 or bev < 0.008) else bev
                L.finalize(ob, bevel=b, seg=1, sub=0, flat=True)
        objs = [it[0] for it in self.items]
        bpy.ops.object.select_all(action="DESELECT")
        for ob in objs:
            ob.select_set(True)
        bpy.context.view_layer.objects.active = objs[0]
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        bpy.ops.object.select_all(action="DESELECT")
        out = L.join_by_material(objs, prefix="TH")
        mirror_x(out)
        if self.unwrap:
            L.smart_uv(out)
        return out


def build(smooth=True, unwrap=True, bevel=True):
    m = Model(smooth, unwrap).build()
    objs = m.finalize(bevel=bevel)
    return objs, L.stats(objs)
