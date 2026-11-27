"""
fm_model.py —— 农场（Farm）：单坡谷仓 + 阶梯筒仓 + 田垄

六座里剩下的那一格屋顶是 `mono_pitch`（单坡）。农场的做法：

  ① **谷仓是单坡**（前檐 5.00 / 后檐 8.20，26.6°），从正面看是一堵 8.4 m 宽的墙 +
     一扇 2.8 m 的双开大门；从 3/4 看是一条从后往前落的长斜屋面；侧面是一块梯形山墙。
     单坡谷仓在中世纪北欧很常见（lean-to barn），和另五座的交叉山墙 / 平顶垛口 /
     缓坡四坡 / 双坡亭 / 敞棚都不重复。
  ② **阶梯十二边形筒仓**是全座最高的点（11.0），也是唯一的"圆"——用 12 段折线 +
     6 级收分的锥顶表达，不出现任何曲面。它和谷仓左前角咬合 0.1 m（结构关系）。
  ③ **田垄是俯视角的节奏**：三条 0.85 宽的垄、两道 0.55 的沟，垄上按"麦 / 白菜 / 南瓜"
     三种作物交替，黄 / 绿 / 橙三个点色。这是"农场"最直接的读法，也是俯视时唯一
     横向铺开的元素。
  ④ **场院一圈 L 形石座木栏**（左 + 前），正面留 1.8 m 的双开门；水井、水槽、草垛、
     板车按"进门 → 取水 → 装车"的动线摆，不随机撒。

坐标：X 右、Y 前（+Y = 正面）、Z 上；原点在占地中心，z = 0 地面。
交付前整体沿 X 镜像一次（与另四座一致），所以建模期的 +X 在成品里是左边的 −X。
"""
import math
from math import tau as TAU

import bpy
from mathutils import Vector

import bslib as L
import br_model as BR
from bslib import (arch_band, beam, box, cone, cyl, extrude, frustum, mesh_obj,
                   revolve, ring_y, taper_box, tube_band)
from br_model import mirror_x

# ── 场地 ────────────────────────────────────────────────────────────────────
YARD_X0, YARD_X1 = -7.85, 7.45
YARD_Y0, YARD_Y1 = -4.05, 8.65
G_Z = 0.16

# ── 谷仓（单坡，8.4 宽 × 6.4 进深，前低后高）────────────────────────────────
BX0, BX1 = -4.20, 4.20          # 左右外墙（8.40）
BY, BYB = 2.50, -2.50           # 前 / 后墙（5.00）
B0 = 0.62                       # 墙底（石台顶）
BF, BB = 5.40, 7.40             # 前檐 / 后檐（21.8°）
BT = 0.26                       # 屋面厚（木瓦）
GATE_W, GATE_H = 1.80, 3.40     # 大门半宽 / 净高（0.62 → 4.02）

# ── 石砌仓塔（阶梯十二边形 φ3.16，筒身 5.6，木锥顶 1.6）────────────────────
# v2：原来是一座 φ2.9 / 8.0 高的直筒 + 三道蓝钢箍 + 金属爬梯 + 护笼 + 现代通风帽，
#     在俯视角下读作"水泥筒仓"，和这套中世纪硬边语言完全冲突（参考图里的那一座
#     是**石砌圆塔 + 木锥顶 + 小方窗**）。改成石塔之后：矮、粗、有窗、有门、
#     有出檐，和谷仓的木板墙形成"石 vs 木"的材质对位。
SX, SY = 5.66, 1.55
SR = 1.58
S0 = 0.10                       # 石砌基座底（埋进夯土 0.06）
S_BASE = 1.50                   # 筒身起点（基座顶）
S1 = 6.98                       # 筒身顶（檐口下沿）
S_EAVE = 7.22                   # 石檐口顶面
CAP_Z = 9.22                    # 木锥顶尖（锥高 2.00，48° 坡）
FLAG_Z = 9.34                   # 旗顶
PH12 = -math.tau / 24.0         # 让 12 边形的某一条面正对 +Y（正立面是平的）

# ── 披屋（靠谷仓右墙，向外单坡）────────────────────────────────────────────
PX0, PX1 = -6.85, -4.20
PY0, PY1 = -2.90, -0.30
P_IN, P_OUT = 5.20, 4.10        # 贴墙檐 / 外檐
P0 = 0.42                       # 披屋地坪

# ── 田垄（三条 0.85 宽 + 两道 0.55 沟）──────────────────────────────────────
ROW_W, ROW_G = 0.95, 0.50
ROW_X = (-3.72, -2.32, -0.92)
ROW_Y0, ROW_Y1 = 3.55, 8.55
ROW_H = 0.20

# ── 围栏 ────────────────────────────────────────────────────────────────────
FX = 4.72                       # 右段 x（院子右边界）
FY = 4.62                       # 前段 y
F_LEN_BACK = 3.30               # 右段后端点（筒仓前沿，不穿筒仓）
F_GATE_X0, F_GATE_X1 = 0.30, 2.10
FX_START = -0.28                # 前段围栏的左端（贴着田的右边缘）
FH = 1.08                       # 栏高（石座之上）


# ── 通用构件 ───────────────────────────────────────────────────────────────
def frame_ring(name, x0, x1, y0, y1, z0, z1, t, mat):
    """矩形环（腰线 / 压顶 / 封边）：45° 斜接。"""
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


def slab(name, pts, t, mat):
    """任意多边形厚板（朝上的面）：外表面 + 法向下沉 t 的内表面 + 侧边。"""
    ps = [Vector(p) for p in pts]
    n = (ps[1] - ps[0]).cross(ps[2] - ps[0])
    if n.length < 1e-9:
        n = (ps[2] - ps[0]).cross(ps[3] - ps[0])
    n.normalize()
    if n.z < 0:
        n = -n
    qs = [p - n * t for p in ps]
    m = len(ps)
    verts = [tuple(p) for p in ps] + [tuple(q) for q in qs]
    faces = [tuple(range(m)), tuple(range(m, 2 * m))]
    for i in range(m):
        j = (i + 1) % m
        faces.append((i, j, m + j, m + i))
    return mesh_obj(name, verts, faces, mat)


def roof_z(y):
    """单坡屋面在给定 y 处的**上表面**标高（含出檐段按同斜率外推）。"""
    return BF + (BY - y) / (BY - BYB) * (BB - BF)


class Model(BR.Model):

    # ── 1. 场地 / 小径 / 石台 ───────────────────────────────────────────────
    def base(self):
        M = self.M
        cx = (YARD_X0 + YARD_X1) * 0.5
        cy = (YARD_Y0 + YARD_Y1) * 0.5
        self.add(box("yard_soil", (cx, cy, G_Z * 0.5),
                     (YARD_X1 - YARD_X0, YARD_Y1 - YARD_Y0, G_Z), M["earth"]), 0.024)
        # 石台：谷仓 + 筒仓共用一块（12.0 × 7.0），筒仓从石台上"长出来"
        self.add(box("plinth_lo", (1.45, -0.10, 0.09), (12.10, 6.30, 0.18),
                     M["stone_mid"]), 0.020)
        self.add(box("plinth_hi", (1.45, -0.10, 0.42), (11.64, 5.98, 0.40),
                     M["stone_light"]), 0.024)
        # 披屋地坪（自己一块，比石台低 0.2）
        self.add(box("plinth_shed", ((PX0 + PX1) * 0.5, (PY0 + PY1) * 0.5, 0.21),
                     (PX1 - PX0 + 0.34, PY1 - PY0 + 0.34, 0.42), M["stone_mid"]), 0.018)
        # 门前小径（从大门两级踏跺通到围栏门）：两块渐窄的石板
        for k in range(2):
            self.add(box("path", (0.62 - k * 0.05, BY + 1.02 + k * 0.46, G_Z + 0.05),
                         (1.86 - k * 0.16, 0.44, 0.10), M["paving"]), 0.006)
        # 场地牙子（右 + 后两面；左/前是围栏）
        self.add(box("yard_curb", (YARD_X1 - 0.10, cy - 0.30, G_Z + 0.04),
                     (0.20, YARD_Y1 - YARD_Y0 - 0.60, 0.12), M["paving"]), 0.006)
        self.add(box("yard_curb_b", (cx - 0.60, YARD_Y0 + 0.10, G_Z + 0.04),
                     (YARD_X1 - YARD_X0 - 1.20, 0.20, 0.12), M["paving"]), 0.006)

    # ── 2. 谷仓墙体（单坡：前 5.00 / 后 8.20）──────────────────────────────
    def barn(self):
        M = self.M
        # 门洞 / 门柱 / 门扇的**同一个中心**。v1 的墙上门洞按 x=0 开，门柱和门扇却按
        # x=0.80 摆 —— 门洞左半（−1.80…−1.00）露出一条 0.8 m 的空缝，右半的门扇
        # 又被墙埋掉 0.8 m。所有门相关坐标只准从这里取，不允许再各写一套。
        gx, gw = 0.80, GATE_W
        # 左右两侧梯形山墙（沿 X 拉伸 0.24）—— 单坡的"山墙"就是这块梯形
        prof = [(BY, B0), (BYB, B0), (BYB, BB), (BY, BF)]
        for sgn in (-1, 1):
            x0 = BX1 if sgn > 0 else BX0 - 0.24
            pts = [(x0, p[0], p[1]) for p in prof]
            if sgn < 0:
                pts = [pts[0], pts[3], pts[2], pts[1]]
            self.add(slab("barn_gable", pts, 0.24, M["wood_mid"]), 0.024)
        # 后墙（矩形，8.40 × 7.58）
        self.add(box("barn_back", ((BX0 + BX1) * 0.5, BYB + 0.12, (B0 + BB) * 0.5),
                     (BX1 - BX0, 0.24, BB - B0), M["wood_mid"]), 0.026)
        # 前墙：左块 / 右块（门洞 3.60 宽，中心 gx）
        for sgn in (-1, 1):
            x0, x1 = gx + sgn * GATE_W, (BX1 if sgn > 0 else BX0)
            self.add(box("barn_front", ((x0 + x1) * 0.5, BY - 0.12, (B0 + BF) * 0.5),
                         (abs(x1 - x0), 0.24, BF - B0), M["wood_mid"]), 0.024)
        self.add(box("barn_front_T", ((BX0 + BX1) * 0.5, BY - 0.12,
                                      (B0 + GATE_H + 0.32 + BF + 0.02) * 0.5),
                     (BX1 - BX0, 0.24, BF - (B0 + GATE_H + 0.32) + 0.02),
                     M["wood_mid"]), 0.024)
        # 墙裙（石砌基脚，比墙面凸 40 mm）
        self.add(frame_ring("barn_dado", BX0 - 0.03, BX1 + 0.03, BYB - 0.03, BY + 0.03,
                            B0, B0 + 0.42, 0.16, M["stone_mid"]), 0.012)
        # 两道木构腰梁（X 向比 Y 向高 20 mm，转角梁头交错）
        for zz in (4.46,):
            # 前墙这道腰梁是全座最长的一条水平线 —— 染队色，正面一眼就读到"这是谁的农场"
            # 前墙腰梁在门洞上方**断开**：不断的话，4.34 的腰梁和 4.36 的门楣匾
            # 会连成一条 4.00–4.70 的粗蓝带，门楣和楼层线糊成一条。
            for (xa, xb) in ((BX0 - 0.10, gx - gw - 0.40), (gx + gw + 0.40, BX1 + 0.10)):
                self.add(box("barn_rail", ((xa + xb) * 0.5, BY - 0.02, zz),
                             (xb - xa, 0.18, 0.24), M["team"]), 0.008)
            self.add(box("barn_rail", ((BX0 + BX1) * 0.5, BYB + 0.02, zz),
                         (BX1 - BX0 + 0.20, 0.18, 0.16), M["wood_dark"]), 0.008)
            for sx in (-1, 1):
                xx = BX1 if sx > 0 else BX0
                self.add(box("barn_rail", (xx + sx * 0.02, (BY + BYB) * 0.5, zz - 0.02),
                             (0.18, BY - BYB - 0.04, 0.22), M["team"]), 0.008)
        # 梯形山墙的两道横梁：只做"露出来的那一段"——
        # 左墙被披屋（y −2.9..−0.3）和侧门（y 0.6）占着，右墙被筒仓（y 0.35..3.25）占着。
        for sx in (-1, 1):
            xx = BX1 if sx > 0 else BX0
            y0, y1 = (1.20, 2.42) if sx < 0 else (-2.42, 0.22)
            for zz in (B0 + 1.05, roof_z(0.0) - 1.28):
                yy0 = y0 if zz < 3.0 else (1.20 if sx < 0 else -2.10)
                yy1 = y1 if zz < 3.0 else (2.10 if sx < 0 else 0.10)
                self.add(box("gable_rail", (xx + sx * 0.06, (yy0 + yy1) * 0.5, zz),
                             (0.16, yy1 - yy0, 0.15), M["wood_dark"]), 0.006)
        # 四角立柱
        for sx in (-1, 1):
            for sy in (-1, 1):
                xx = BX1 if sx > 0 else BX0
                yy = BY if sy > 0 else BYB
                self.add(box("barn_col", (xx - sx * 0.11, yy - sy * 0.11, (B0 + 2.55) * 0.5),
                             (0.26, 0.26, 2.55 - B0), M["wood_dark"]), 0.010)
                self.add(box("barn_col_t", (xx - sx * 0.11, yy - sy * 0.11, 3.58),
                             (0.28, 0.28, 2.06), M["team"]), 0.008)
                self.add(box("barn_col_cap", (xx - sx * 0.11, yy - sy * 0.11, 2.52),
                             (0.30, 0.30, 0.08), M["team_trim"]), 0.004)
        # ── 大门：石砌门套 + 半开双扇 + 门外两级踏跺 ──────────────────────
        # v2 的三条改动（用户："没看到门在哪里，或者说不明显"）：
        #   ① 门套从亮木改成**石砌**（宽 0.34 / 凸出墙面 0.17）—— 灰石把门洞描出来；
        #   ② 门扇从 wood_dark 换成**亮木 wood_warm**，配深木横档 + 队色嵌板，
        #      与墙面 wood_mid 拉开三档明度；
        #   ③ 门**半开**（左扇 52° / 右扇 22°）—— 关着的门在俯视角下永远
        #      只读成"墙上的一块深色"，开了才有门洞纵深、才有干草垛露出来。
        for sgn in (-1, 1):
            self.add(box("gate_jamb", (gx + sgn * (gw + 0.17), BY - 0.06,
                                       B0 + (GATE_H + 0.34) * 0.5),
                         (0.34, 0.46, GATE_H + 0.34), M["stone_mid"]), 0.010)
        # 门楣石梁：**分三段，中间一段是队色匾额**。
        # 贴片式的匾（一块 2.42×0.05×0.24 的薄板贴在石梁正面）在这套光照下
        # 完全不显 —— 石梁正面本来就是平的，薄板凸 6 cm 读不出厚度。
        # 做成"石梁中间换一段材质"，凸起 1 cm、上下各高 2 cm，边缘自带一条硬阴影。
        hz = B0 + GATE_H + 0.16
        for (xa, xb, zt, zb, yt, mat) in (
                (gx - gw - 0.34, gx - 1.32, hz - 0.16, hz + 0.16, 0.46, M["stone_mid"]),
                (gx - 1.36, gx + 1.36, hz - 0.18, hz + 0.18, 0.48, M["team"]),
                (gx + 1.32, gx + gw + 0.34, hz - 0.16, hz + 0.16, 0.46, M["stone_mid"])):
            self.add(box("gate_head", ((xa + xb) * 0.5, BY - 0.06, (zt + zb) * 0.5),
                         (xb - xa, yt, zb - zt), mat), 0.010)
        # 匾额上下的金线（读作"镶嵌"而不是"刷漆"）
        self.add(box("gate_plaque_t", (gx, BY - 0.05, hz + 0.215), (2.66, 0.50, 0.030),
                     M["team_trim"]), 0.002)
        # 左右门扇（**关着**：谷仓大门在 RTS 尺度上要"一整块"，不是两片斜板。
        # 半开在这里是错的——两扇各 1.77 宽，往院子一开就压到田垄和作物上）
        self.gate_leaf("gate_l", (gx - gw + 0.008, BY - 0.12), 0.0,
                       gw - 0.03, GATE_H - 0.02, B0)
        self.gate_leaf("gate_r", (gx + gw - 0.008, BY - 0.12), math.pi,
                       gw - 0.03, GATE_H - 0.02, B0)
        # 门柱箍（队色，低处；只箍下半，通天的蓝柱会读成"消防站"）
        for sgn in (-1, 1):
            self.add(box("gate_hoop", (gx + sgn * (gw + 0.17), BY - 0.06, B0 + 1.06),
                         (0.40, 0.52, 0.30), M["team"]), 0.005)
        # 门内的地面与干草：门洞不能是一个黑矩形
        self.add(box("barn_floor_in", (gx, BY - 1.25, B0 + 0.03),
                     (gw * 2 - 0.16, 1.86, 0.06), M["paving"]), 0.004)
        self.add(box("hay_inside", (1.06, BY - 0.88, B0 + 0.74),
                     (2.34, 0.78, 1.48), M["sand"]), 0.014)
        self.add(box("hay_inside_top", (1.06, BY - 0.88, B0 + 1.55),
                     (2.10, 0.66, 0.14), M["sand"]), 0.008)
        # 门外两级踏跺（石台 0.62 → 场地 0.16）
        for i, (yy, zt, wid) in enumerate(((BY + 0.51, 0.42, 3.42),
                                           (BY + 0.75, 0.21, 3.62))):
            self.add(box("gate_step%d" % i, (gx, yy, zt * 0.5), (wid, 0.24, zt),
                         M["stone_light"]), 0.008)
        # 正立面的半木构：门两侧各一竖柱 + 一道从柱脚斜上到门楣的三角撑
        self.add(box("front_stud", (-3.55, BY - 0.02, (B0 + 0.05 + BF - 0.45) * 0.5),
                     (0.20, 0.22, BF - 0.50 - B0), M["wood_dark"]), 0.008)
        self.add(beam("front_brace", (-3.55, BY - 0.03, B0 + 0.90),
                      (-(GATE_W + 0.22), BY - 0.03, B0 + GATE_H + 0.24),
                      0.13, 0.10, M["wood_dark"]), 0.004)
        # 门左侧的空墙：X 交叉撑 + 一道通长横梁（原来的 0.80 宽深色方板
        # "front_mid" 读不出语义，是一块不知名的板 —— 删掉）
        for (p0, p1) in (((-3.95, B0 + 0.78), (-2.20, B0 + GATE_H + 0.62)),
                         ((-3.95, B0 + GATE_H + 0.62), (-2.20, B0 + 0.78))):
            self.add(beam("front_x", (p0[0], BY - 0.03, p0[1]),
                          (p1[0], BY - 0.03, p1[1]), 0.11, 0.095, M["wood_dark"]), 0.004)
        self.add(box("front_rail", (-2.78, BY - 0.03, B0 + 1.62),
                     (2.86, 0.20, 0.17), M["wood_dark"]), 0.006)
        self.window_y("win_front", BY, 3.48, 0.68, 0.78, B0 + 1.75)
        # 侧门（左墙）+ 三扇小窗
        self.add(box("side_door", (BX0 - 0.02, 0.60, B0 + 0.99), (0.10, 1.00, 1.86),
                     M["wood_warm"]), 0.008)
        self.add(box("side_door_f", (BX0 - 0.06, 0.60, B0 + 0.99), (0.08, 1.16, 2.02),
                     M["wood_dark"]), 0.006)
        for sx, yy in ((1, -1.95), (1, -0.75)):
            self.window("win_barn", BX1, yy, 0.76, 0.86, 3.32)
        self.window("win_barn_s", BX0, 1.35, 0.68, 0.78, 3.45, out=-1)
        # 山墙阁楼窗（+X 侧，高处）
        self.window("win_loft", BX1, -0.55, 0.50, 0.40, 5.42)

    def gate_leaf(self, tag, hinge, rot, w, h, z0):
        """一扇谷仓门：铰链在 hinge，沿局部 +X 展开。

        结构：亮木门板 + 5 根中棕竖板条（凹槽）+ 2 道深木横档 + 1 根 Z 形斜撑
              + 一块队色封条 + 3 只铁合页 + 铁环。
        v1 的 X 撑（两根交叉）+ 1.45 m 宽的整块队色嵌板，在 RTS 尺度上把门读成
        "贴了两块蓝板的栅栏" —— 谷仓门只要 Z 撑就够了。

        所有子件都走同一个 (u, v) 变换：u 沿门宽，v 一律沿**世界 +Y**。
        右扇 rot=π 时如果把 v 乘进局部轴，板条会翻到门内侧 —— 门就变成一块光板。
        """
        M = self.M
        ca, sa = math.cos(rot), math.sin(rot)

        def P(u, v):
            return (hinge[0] + u * ca, hinge[1] + u * sa + v)

        cx, cy = P(w * 0.5, 0.0)
        self.add(box(tag + "_leaf", (cx, cy, z0 + h * 0.5), (w, 0.10, h),
                     M["wood_warm"], rot=(0, 0, rot)), 0.010)
        for i in range(5):
            px, py = P(w * (0.10 + 0.20 * i), 0.058)
            self.add(box(tag + "_plank", (px, py, z0 + h * 0.5),
                         (0.085, 0.030, h - 0.10), M["wood_mid"],
                         rot=(0, 0, rot)), 0.002)
        for zz in (z0 + 0.38, z0 + h - 0.40):
            px, py = P(w * 0.5, 0.076)
            self.add(box(tag + "_rail", (px, py, zz), (w - 0.02, 0.055, 0.14),
                         M["wood_dark"], rot=(0, 0, rot)), 0.003)
        p0, p1 = P(0.13, 0.082), P(w - 0.13, 0.082)
        self.add(beam(tag + "_brace", (p0[0], p0[1], z0 + 0.46),
                      (p1[0], p1[1], z0 + h - 0.46), 0.048, 0.115,
                      M["wood_dark"]), 0.003)
        px, py = P(w * 0.5, 0.086)
        self.add(box(tag + "_panel", (px, py, z0 + h * 0.66), (0.64, 0.045, 0.44),
                     M["team"], rot=(0, 0, rot)), 0.004)
        self.add(box(tag + "_panel_t", (px, py + 0.006, z0 + h * 0.66),
                     (0.62, 0.030, 0.060), M["team_trim"], rot=(0, 0, rot)), 0.002)
        px, py = P(w - 0.16, 0.096)
        self.add(box(tag + "_ring", (px, py, z0 + h * 0.42), (0.07, 0.05, 0.20),
                     M["iron"], rot=(0, 0, rot)), 0.002)
        for zz in (z0 + 0.42, z0 + h * 0.5, z0 + h - 0.42):
            px, py = P(0.045, 0.098)
            self.add(box(tag + "_hinge", (px, py, zz), (0.14, 0.045, 0.10),
                         M["iron"], rot=(0, 0, rot)), 0.002)

    def window(self, name, wall_x, cy, w, h, cz, out=1):
        """木框 + 内凹玻璃 + 中梃（贴片做法）。"""
        M = self.M
        fr = M["wood_dark"]
        hw = w * 0.5
        x0 = wall_x
        self.add(box(name + "_glass", (x0 + out * 0.012, cy, cz + h * 0.5),
                     (0.06, w, h), M["glass"]), 0.0)
        self.add(box(name + "_head", (x0 + out * 0.045, cy, cz + h + 0.07),
                     (0.11, w + 0.26, 0.14), fr), 0.004)
        self.add(box(name + "_sill", (x0 + out * 0.050, cy, cz - 0.055),
                     (0.13, w + 0.34, 0.11), fr), 0.004)
        for sgn in (-1, 1):
            self.add(box(name + "_jamb", (x0 + out * 0.040, cy + sgn * (hw + 0.065),
                                          cz + h * 0.5), (0.11, 0.13, h + 0.16), fr), 0.004)
        self.add(box(name + "_mull", (x0 + out * 0.028, cy, cz + h * 0.5),
                     (0.05, 0.055, h - 0.03), fr), 0.002)

    def window_y(self, name, wall_y, cx, w, h, cz, out=1):
        """朝 ±Y 的墙上的窗（正面 / 背面）。"""
        M = self.M
        fr = M["wood_dark"]
        hw = w * 0.5
        self.add(box(name + "_glass", (cx, wall_y + out * 0.012, cz + h * 0.5),
                     (w, 0.06, h), M["glass"]), 0.0)
        self.add(box(name + "_head", (cx, wall_y + out * 0.045, cz + h + 0.07),
                     (w + 0.26, 0.11, 0.14), fr), 0.004)
        self.add(box(name + "_sill", (cx, wall_y + out * 0.050, cz - 0.055),
                     (w + 0.34, 0.13, 0.11), fr), 0.004)
        for sgn in (-1, 1):
            self.add(box(name + "_jamb", (cx + sgn * (hw + 0.065),
                                          wall_y + out * 0.040, cz + h * 0.5),
                         (0.13, 0.11, h + 0.16), fr), 0.004)
        self.add(box(name + "_mull", (cx, wall_y + out * 0.028, cz + h * 0.5),
                     (0.055, 0.05, h - 0.03), fr), 0.002)

    # ── 3. 单坡屋面 + 瓦垄 ─────────────────────────────────────────────────
    def barn_roof(self):
        M = self.M
        ex0, ex1 = BX0 - 0.42, BX1 + 0.42
        ey0, ey1 = BY + 0.36, BYB - 0.36
        ez0, ez1 = roof_z(ey0), roof_z(ey1)
        # 屋面（整块厚板，厚 0.26）
        self.add(slab("roof_main", [(ex0, ey0, ez0), (ex1, ey0, ez0),
                                    (ex1, ey1, ez1), (ex0, ey1, ez1)],
                      BT, M["roof_wood"]), 0.010)
        # 木板缝：沿坡 7 道暗缝（roof_edge 细条压进木瓦），不是亮脊 ——
        # 暖棕屋面上一旦铺亮条，整块屋顶会读成"条纹板"（哨塔也踩过同一个坑）
        n = 7
        for i in range(n):
            x = ex0 + 0.46 + i * (ex1 - ex0 - 0.92) / (n - 1)
            self.add(beam("roof_rib", (x, ey0 + 0.05, ez0 + 0.035),
                          (x, ey1 - 0.05, ez1 + 0.035), 0.050, 0.045,
                          M["wood_dark"]), 0.0)
        # 前后檐：封檐板 + 滴水条（后檐是"高檐"，正面看不到，但侧视是轮廓）
        for yy, zz in ((ey0, ez0), (ey1, ez1)):
            self.add(box("roof_fascia", ((ex0 + ex1) * 0.5, yy, zz - 0.14),
                         (ex1 - ex0 + 0.06, 0.10, 0.24), M["roof_edge"]), 0.005)
            self.add(box("roof_drip", ((ex0 + ex1) * 0.5, yy + (0.03 if yy > 0 else -0.03),
                                       zz + 0.02), (ex1 - ex0 + 0.08, 0.06, 0.08),
                         M["roof_edge"]), 0.003)
        # 两侧山墙收边（沿坡的封檐，把梯形山墙的边压住）
        for sx, xx in ((-1, ex0), (1, ex1)):
            self.add(beam("roof_barge", (xx, ey0, ez0 - 0.02), (xx, ey1, ez1 - 0.02),
                          0.10, 0.26, M["roof_edge"]), 0.004)
        # 后檐的"压脊"（单坡最高处的一条通长压条）
        self.add(box("roof_ridge", ((ex0 + ex1) * 0.5, ey1 + 0.04, ez1 + 0.10),
                     (ex1 - ex0 + 0.10, 0.22, 0.16), M["roof_edge"]), 0.006)
        # 屋面通风百叶 ×2：谷仓必须"会呼吸"，也是打散大屋面的一层体积
        for (vx, vy, vw, vl) in ((-2.15, 0.60, 0.68, 0.52), (1.95, -1.00, 0.62, 0.48)):
            vz = roof_z(vy)
            self.add(box("vent_body", (vx, vy, vz + 0.04), (vw, vl, 0.46),
                         M["wood_mid"]), 0.006)
            self.add(frustum("vent_cap", vz + 0.24, vz + 0.36, vw + 0.12, vl + 0.12,
                             vw - 0.08, vl - 0.08, vx, vy, M["wood_dark"]), 0.005)
            self.add(box("vent_slat", (vx, vy + vl * 0.5 + 0.02, vz + 0.06),
                         (vw * 0.70, 0.05, 0.24), M["coal"]), 0.002)
        # 屋面上的"换过的旧瓦"：4 块深浅不一的补丁。整片 8.4×5.0 的木瓦屋面
        # 在俯视角下是一块纯色大板，补丁是成本最低的"人用过"的证据。
        ang = math.atan2(BB - BF, BY - BYB)
        for (px, py, pw, pl, mat) in ((-2.35, 1.24, 3.10, 0.40, M["wood_mid"]),
                                      (1.45, 0.18, 2.55, 0.40, M["wood_mid"]),
                                      (2.55, -1.42, 2.05, 0.40, M["stone_dark"]),
                                      (-3.05, -1.72, 1.55, 0.40, M["wood_mid"])):
            self.add(box("roof_patch", (px, py, roof_z(py) + 0.015),
                         (pw, pl, 0.05), mat, rot=(-ang, 0, 0)), 0.004)
        # 露明椽头：前檐下一排（农场该有这种"没做完"的木构感）
        for i in range(9):
            x = ex0 + 0.40 + i * (ex1 - ex0 - 0.80) / 8.0
            self.add(box("rafter_end", (x, ey0 + 0.10, ez0 - 0.30),
                         (0.11, 0.34, 0.12), M["wood_dark"]), 0.003)

    # ── 4. 石砌仓塔（十二边形 + 木锥顶 + 小方窗 + 石砌门斗）──────────────────
    def tower_face(self, ang_deg, r):
        """12 边塔某一面法线上的点位与旋转角。

        `ang_deg` 是**面法线**角度（0 = +X，90 = +Y）。PH12 把十二边形的面摆在
        0/30/60/90… 上，所以正立面（90°）是一整块平面，窗与门可以轴对齐地贴上去。
        返回 (x, y, 法线角, box 的 Z 旋转角)：box 的局部 X 取切向、Y 取法向。
        """
        a = math.radians(ang_deg)
        return (SX + math.cos(a) * r, SY + math.sin(a) * r, a, a + math.pi * 0.5)

    def tower_win(self, name, ang_deg, z, w, h):
        """石塔上的小方窗：冷玻璃 + 木框 + 石窗台 + 一根竖棂。"""
        M = self.M
        cx, cy, a, rot = self.tower_face(ang_deg, SR - 0.03)
        ca, sa = math.cos(a), math.sin(a)
        self.add(box(name + "_glass", (cx, cy, z), (w, 0.14, h), M["glass"],
                     rot=(0, 0, rot)), 0.0)
        for sz in (-1, 1):
            self.add(box(name + "_ft", (cx, cy, z + sz * (h * 0.5 + 0.055)),
                         (w + 0.24, 0.15, 0.10), M["wood_dark"], rot=(0, 0, rot)), 0.004)
        for su in (-1, 1):
            self.add(box(name + "_fu", (cx - sa * su * (w * 0.5 + 0.06),
                                        cy + ca * su * (w * 0.5 + 0.06), z),
                         (0.10, 0.15, h + 0.06), M["wood_dark"], rot=(0, 0, rot)), 0.004)
        self.add(box(name + "_mull", (cx + ca * 0.05, cy + sa * 0.05, z),
                     (0.045, 0.06, h - 0.02), M["wood_dark"], rot=(0, 0, rot)), 0.002)
        self.add(box(name + "_sill", (cx + ca * 0.03, cy + sa * 0.03,
                                      z - h * 0.5 - 0.11),
                     (w + 0.26, 0.16, 0.09), M["stone_light"], rot=(0, 0, rot)), 0.006)

    def tower_loop(self, name, ang_deg, z, w=0.19, h=0.25):
        """鸽舍洞：只在石面上凹一块深色，没有木框 —— 远看是一排小黑点。"""
        M = self.M
        cx, cy, a, rot = self.tower_face(ang_deg, SR - 0.02)
        ca, sa = math.cos(a), math.sin(a)
        self.add(box(name + "_hole", (cx, cy, z), (w, 0.12, h), M["coal"],
                     rot=(0, 0, rot)), 0.0)
        self.add(box(name + "_ledge", (cx + ca * 0.02, cy + sa * 0.02, z - h * 0.5 - 0.02),
                     (w + 0.15, 0.18, 0.055), M["stone_light"], rot=(0, 0, rot)), 0.004)

    def silo(self):
        M = self.M
        # ① 石砌基座：从**场地**起（不是从石台）—— 塔基前缘比石台多出 0.4 m，
        #    从石台起会悬空。埋进夯土 0.06，读到的是"石塔压在地里"。
        self.add(revolve("tower_foot", [(SR + 0.13, 0.0), (SR + 0.13, 1.26)], 12,
                         (SX, SY, S0), M["stone_mid"], phase=PH12), 0.014)
        self.add(revolve("tower_foot_cap", [(SR + 0.21, 0.0), (SR + 0.21, 0.09),
                                            (SR + 0.05, 0.14)], 12,
                         (SX, SY, S0 + 1.26), M["stone_light"], phase=PH12), 0.010)
        # ② 筒身
        self.add(revolve("tower_body", [(SR, 0.0), (SR, S1 - S_BASE)], 12,
                         (SX, SY, S_BASE), M["stone_light"], phase=PH12), 0.022)
        # 石砌层线：三道极浅的深色带（砌石分层的唯一线索，近景才读得出）
        for zz in (2.62, 4.30, 5.98):
            self.add(tube_band("tower_course", (SX, SY), SR - 0.03, SR + 0.022,
                               zz, zz + 0.045, 12, M["stone_mid"], phase=PH12), 0.0)
        # ③ 两道深木腰箍（**不做三道**：三道同材质 = 钢箍 = 工业筒仓）
        for zz in (1.66, 3.56):
            self.add(tube_band("tower_hoop", (SX, SY), SR - 0.03, SR + 0.055,
                               zz, zz + 0.19, 12, M["wood_dark"], phase=PH12), 0.004)
        # ④ 队色布带（绑在石塔腰上的一圈布）：全座最高的染色点，宽 0.30
        self.add(tube_band("tower_band", (SX, SY), SR - 0.02, SR + 0.034,
                           5.14, 5.66, 12, M["team"], phase=PH12), 0.003)
        # 石座之上的一道窄腰带：塔基与塔身的交界线，也是俯视时最近的一条染色线
        self.add(tube_band("tower_band_low", (SX, SY), SR - 0.02, SR + 0.030,
                           2.28, 2.48, 12, M["team"], phase=PH12), 0.003)
        for zz in (5.11, 5.67):   # 布带上下两道金线（把"布"钉住，否则一圈纯色＝涂装）
            self.add(tube_band("tower_cord", (SX, SY), SR - 0.02, SR + 0.042,
                               zz, zz + 0.038, 12, M["team_trim"], phase=PH12), 0.002)
        # ⑤ 石檐口（出挑 0.20，压住锥顶）
        self.add(revolve("tower_eave", [(SR + 0.02, 0.0), (SR + 0.20, 0.0),
                                        (SR + 0.20, 0.12), (SR + 0.05, 0.26)], 12,
                         (SX, SY, S1 - 0.02), M["stone_dark"], phase=PH12), 0.008)
        # ⑥ 木锥顶（12 边收成一点）：**坡要够陡**。v1 试过 1.60 高 / 底 1.88 ——
        #    36° 的坡在俯视角下读成"蘑菇帽"；现在 2.00 高 / 底 1.78（48°），
        #    剪影是一条明确的山脊线，中世纪石塔的帽子就该是尖的。
        self.add(revolve("tower_roof", [(SR + 0.20, 0.0), (SR + 0.16, 0.10),
                                        (SR - 0.06, 0.52), (SR - 0.46, 0.98),
                                        (SR - 0.96, 1.50), (0.42, 1.94), (0.0, 2.00)], 12,
                         (SX, SY, S_EAVE), M["roof_wood"], phase=PH12), 0.0, 1)
        # 锥顶的三道瓦缝（环状，随锥面收分）
        for (rr, zz) in ((1.62, 7.40), (1.22, 7.85), (0.82, 8.30)):
            self.add(tube_band("tower_rim", (SX, SY), rr - 0.09, rr + 0.015,
                               zz, zz + 0.065, 12, M["roof_edge"], phase=PH12), 0.002)
        # ⑦ 顶尖：铁座 + 风向标（十字）+ 旗杆 + 队色三角飘带
        self.add(revolve("tower_finial", [(0.22, 0.0), (0.17, 0.09), (0.09, 0.19),
                                          (0.0, 0.24)], 8,
                         (SX, SY, CAP_Z - 0.14), M["iron"]), 0.0, 1)
        self.add(box("tower_rod", (SX, SY, CAP_Z + 0.40), (0.055, 0.055, 0.98),
                     M["iron"]), 0.003)
        self.add(box("tower_vane_x", (SX - 0.30, SY, CAP_Z + 0.58),
                     (0.48, 0.032, 0.09), M["iron"]), 0.002)
        self.add(box("tower_vane_y", (SX - 0.09, SY, CAP_Z + 0.58),
                     (0.032, 0.32, 0.08), M["iron"]), 0.002)
        for (dx, w, h, zz) in ((0.34, 0.62, 0.38, CAP_Z + 0.70),
                               (0.70, 0.40, 0.28, CAP_Z + 0.70),
                               (0.94, 0.20, 0.16, CAP_Z + 0.70)):
            self.add(box("tower_flag", (SX + dx, SY, zz), (w, 0.030, h),
                         M["team"]), 0.002)
        # ⑧ 正门：开在十二边形的 +Y 面上（面宽 0.818，门宽 0.72 正好落在一整块平面上）
        #    不做外凸门斗 —— 门斗必然伸出石台边缘，前面要接一段"悬空的门廊地面"，
        #    在俯视下读作"塔前面粘了一个方盒子"。石塔的门就该是**嵌在塔身里的洞**。
        cx, cy, a_f, _ = self.tower_face(90, SR + 0.02)
        dw, dh, dz = 0.72, 1.70, S0 + 0.52
        # 石砌门套：两侧竖框 + 拱上三块（阶梯拱，不用曲线）
        for su in (-1, 1):
            self.add(box("tower_door_jamb", (cx + su * (dw * 0.5 + 0.09), cy, dz + dh * 0.5),
                         (0.18, 0.20, dh + 0.14), M["stone_light"]), 0.006)
        for k, (ww, zz, hh) in enumerate(((dw + 0.36, dh + 0.10, 0.16),
                                          (dw + 0.12, dh + 0.24, 0.14),
                                          (dw - 0.22, dh + 0.36, 0.13))):
            self.add(box("tower_door_arch%d" % k, (cx, cy, dz + zz),
                         (ww, 0.20, hh), M["stone_light"]), 0.005)
        # 门扇（亮木 + 两道铁带 + 队色嵌板 + 铁环）
        self.add(box("tower_door_leaf", (cx, cy, dz + dh * 0.5), (dw, 0.12, dh),
                     M["team"]), 0.008)
        for k in (-1, 1):
            self.add(box("tower_door_band", (cx, cy + 0.075, dz + (0.40 if k < 0 else dh - 0.34)),
                         (dw - 0.05, 0.05, 0.12), M["iron"]), 0.003)
        self.add(box("tower_door_panel", (cx, cy + 0.078, dz + 1.02),
                     (dw - 0.24, 0.045, 0.74), M["team"]), 0.004)
        self.add(box("tower_door_ring", (cx + 0.22, cy + 0.085, dz + 0.92),
                     (0.08, 0.045, 0.15), M["iron"]), 0.002)
        # 门前两级踏跺（石台 0.62 → 场地 0.16）
        for i, (ddy, zt, wid) in enumerate(((0.02, 0.42, 1.90), (0.26, 0.21, 2.10))):
            self.add(box("tower_step%d" % i, (cx, cy + 0.14 + ddy, zt * 0.5),
                         (wid, 0.24, zt), M["stone_light"]), 0.006)
        # ⑨ 窗：正面 1 + 外侧(+X) 2 + 背面 1 + 斜前方 1
        self.tower_win("twin_f", 90, 4.62, 0.34, 0.50)
        self.tower_win("twin_a", 0, 3.24, 0.34, 0.50)
        self.tower_win("twin_b", 0, 5.96, 0.32, 0.46)
        self.tower_win("twin_c", 270, 4.18, 0.34, 0.50)
        self.tower_win("twin_d", 30, 2.62, 0.30, 0.44)
        # ⑩ 鸽舍洞：上半段的小黑洞。只做**朝外**的四个面 —— 180°/240° 两个面
        #    陷在谷仓墙体与屋面封檐里（塔心 5.66，180° 面在 x=4.13，比谷仓右墙 4.20 还靠里），
        #    做出来等于在墙里挖洞，石台还会顶穿屋面封檐板。
        for ang in (0, 60, 120, 300):
            self.tower_loop("tloop", ang, 6.52)

    # ── 5. 披屋（靠谷仓右墙，向外单坡，半开敞农具棚）────────────────────────
    def shed(self):
        M = self.M
        # 后墙 + 两侧墙（正面开敞，三根柱撑着）
        self.add(box("shed_back", ((PX0 + PX1) * 0.5, PY0 + 0.12, (P0 + P_IN) * 0.5),
                     (PX1 - PX0, 0.24, P_IN - P0), M["wood_mid"]), 0.020)
        self.add(box("shed_side", (PX1 - 0.12, (PY0 + PY1) * 0.5,
                                   (P0 + P_OUT + 0.30) * 0.5),
                     (0.24, PY1 - PY0, P_OUT + 0.30 - P0), M["wood_mid"]), 0.018)
        # 正面半高挡墙（0.90 高）：农具棚的挡土 / 挡草墙，也让棚子有"体积"
        self.add(box("shed_low", (PX1 - 0.16, (PY0 + PY1) * 0.5, P0 + 0.45),
                     (0.12, PY1 - PY0 - 0.10, 0.90), M["stone_mid"]), 0.010)
        # 三根檐柱
        for yy in (PY0 + 0.28, (PY0 + PY1) * 0.5, PY1 - 0.28):
            self.add(box("shed_post", (PX1 - 0.14, yy, (P0 + P_OUT) * 0.5),
                         (0.20, 0.20, P_OUT - P0), M["wood_dark"]), 0.006)
            self.add(box("shed_post_band", (PX1 - 0.14, yy, P0 + 1.00),
                     (0.24, 0.24, 0.44), M["team"]), 0.004)
        # 单坡屋面（贴墙 4.40 → 外檐 3.60）
        ex0, ex1 = PX0 - 0.10, PX1 + 0.10
        ey0, ey1 = PY0 - 0.28, PY1 + 0.28
        self.add(slab("shed_roof", [(ex1, ey0, P_OUT), (ex1, ey1, P_OUT),
                                    (ex0, ey1, P_IN), (ex0, ey0, P_IN)],
                      0.20, M["roof_wood"]), 0.008)
        for i in range(6):
            yy = ey0 + 0.30 + i * (ey1 - ey0 - 0.60) / 5.0
            self.add(beam("shed_rib", (ex1 + 0.02, yy, P_OUT + 0.038),
                          (ex0, yy, P_IN + 0.038), 0.062, 0.042, M["wood_dark"]), 0.0)
        self.add(box("shed_fascia", (ex1 + 0.02, (ey0 + ey1) * 0.5, P_OUT - 0.10),
                     (0.08, ey1 - ey0 + 0.06, 0.20), M["roof_edge"]), 0.005)
        # 棚内：草叉 / 锄头靠墙 + 木桶 + 一堆干草
        for k, yy in enumerate((-1.90, -1.55, -1.20)):
            self.add(beam("tool_shaft", (PX0 + 0.34, yy, P0 + 0.15),
                          (PX0 + 0.34, yy + 0.09, P0 + 2.02), 0.055, 0.055,
                          M["wood_warm"]), 0.003)
            self.add(box("tool_head", (PX0 + 0.34, yy + 0.09, P0 + 2.04),
                         (0.30, 0.07, 0.09), M["iron"]), 0.003)
        self.barrel("barrel_shed", (PX0 + 0.62, PY1 - 0.55), 0.26, 0.62, P0)
        self.add(box("shed_hay", (PX0 + 0.70, PY0 + 0.70, P0 + 0.24),
                     (0.90, 0.80, 0.48), M["sand"]), 0.010)

    # ── 6. 田垄 + 三种作物 ─────────────────────────────────────────────────
    def field(self):
        M = self.M
        # 垄沟底面（整片压暗的土），比垄顶低 0.20
        self.add(box("field_base", (-2.32, (ROW_Y0 + ROW_Y1) * 0.5, G_Z + 0.025),
                     (3.86, ROW_Y1 - ROW_Y0 + 0.30, 0.05), M["earth_dark"]), 0.008)
        # 三条垄（earth 提亮，两端各留 0.25 收头）
        for k, xx in enumerate(ROW_X):
            self.add(box("row", (xx, (ROW_Y0 + ROW_Y1) * 0.5, G_Z + ROW_H * 0.5),
                         (ROW_W, ROW_Y1 - ROW_Y0, ROW_H), M["earth"]), 0.014)
            # 垄头两端的挡土石（读作"这一垄起止"）
            for sy in (-1, 1):
                yy = ROW_Y1 if sy > 0 else ROW_Y0
                self.add(box("row_end", (xx, yy, G_Z + ROW_H * 0.5),
                             (ROW_W + 0.10, 0.16, ROW_H + 0.06), M["stone_mid"]), 0.004)
            # 9 株作物：三条垄分别种麦 / 白菜 / 南瓜
            cnt = 13
            for i in range(cnt):
                yy = ROW_Y0 + 0.42 + i * (ROW_Y1 - ROW_Y0 - 0.84) / (cnt - 1)
                if k == 0:
                    self.wheat((xx, yy))
                elif k == 1:
                    self.cabbage((xx, yy))
                else:
                    self.pumpkin((xx, yy))

    def wheat(self, p):
        """麦：三束递减的窄盒，顶稍偏（风感）。"""
        M = self.M
        x, y = p
        for k, (dz, hh, dx) in enumerate(((0.0, 0.34, 0.0), (0.0, 0.50, 0.03),
                                          (0.0, 0.62, -0.02))):
            self.add(box("wheat", (x + (k - 1) * 0.12 + dx, y,
                                   G_Z + ROW_H + hh * 0.5),
                         (0.075, 0.16, hh), M["sand"], rot=(0, 0.10 - k * 0.10, 0)), 0.002)
        self.add(box("wheat_tip", (x, y, G_Z + ROW_H + 0.64), (0.30, 0.14, 0.05),
                     M["gold"]), 0.002)

    def cabbage(self, p):
        """白菜：两层方盒（外叶 + 心），外面一层 moss 深绿。"""
        M = self.M
        x, y = p
        self.add(box("cabbage", (x, y, G_Z + ROW_H + 0.13), (0.34, 0.34, 0.26),
                     M["moss"]), 0.006)
        self.add(box("cabbage_in", (x, y, G_Z + ROW_H + 0.30), (0.22, 0.22, 0.14),
                     M["moss"]), 0.004)

    def pumpkin(self, p):
        """南瓜：扁盒 + 一道藤。"""
        M = self.M
        x, y = p
        self.add(box("pumpkin", (x, y, G_Z + ROW_H + 0.14), (0.36, 0.30, 0.24),
                     M["gold"]), 0.008)
        self.add(box("pumpkin_stem", (x, y, G_Z + ROW_H + 0.28), (0.07, 0.07, 0.08),
                     M["wood_dark"]), 0.002)
        self.add(box("pumpkin_vine", (x + 0.26, y + 0.05, G_Z + ROW_H + 0.05),
                     (0.30, 0.06, 0.06), M["moss"]), 0.002)

    # ── 7. 水井 ────────────────────────────────────────────────────────────
    def well(self):
        M = self.M
        x, y = 4.25, 6.35
        self.add(revolve("well_wall", [(0.78, 0.0), (0.78, 0.92), (0.66, 0.92),
                                       (0.66, 0.10)], 8, (x, y, G_Z), M["stone_mid"]), 0.014)
        self.add(revolve("well_cap", [(0.86, 0.0), (0.86, 0.14), (0.66, 0.14)], 8,
                         (x, y, G_Z + 0.93), M["stone_light"]), 0.008)
        self.add(revolve("well_water", [(0.64, 0.0), (0.64, 0.02)], 8,
                         (x, y, G_Z + 0.72), M["roof_pale"]), 0.0, 1)
        # 木架 + 横梁 + 辘轳 + 摇把 + 吊桶
        for sx in (-1, 1):
            self.add(box("well_post", (x + sx * 0.72, y, G_Z + 1.42),
                         (0.14, 0.14, 2.36), M["wood_dark"]), 0.006)
        self.add(box("well_beam", (x, y, G_Z + 2.52), (1.74, 0.16, 0.18),
                     M["team"]), 0.006)
        self.add(box("well_beam2", (x, y, G_Z + 2.30), (1.40, 0.12, 0.12),
                     M["wood_warm"]), 0.004)
        self.add(revolve("well_roller", [(0.16, 0.0), (0.16, 0.52)], 8,
                         (x - 0.04, y, G_Z + 2.42), M["wood_warm"]), 0.0, 1)
        self.add(box("well_crank", (x + 0.46, y, G_Z + 2.42), (0.34, 0.06, 0.06),
                     M["iron"]), 0.003)
        self.add(box("well_rope", (x - 0.04, y, G_Z + 1.92), (0.045, 0.045, 0.96),
                     M["wood_dark"]), 0.002)
        self.add(revolve("well_bucket", [(0.16, 0.0), (0.19, 0.06), (0.19, 0.34),
                                         (0.16, 0.36)], 8, (x - 0.04, y, G_Z + 1.44),
                         M["wood_warm"]), 0.0, 1)
        for sx in (-1, 1):
            self.add(box("well_arc", (x + sx * 0.16, y, G_Z + 1.60), (0.04, 0.04, 0.18),
                         M["iron"]), 0.002)

    # ── 8. 场院道具：草垛 / 水槽 / 板车 / 木桶 / 草簇 ────────────────────────
    def props(self):
        M = self.M
        # 草垛 ×2（方形草捆，两道捆绳）
        for (px, py, w, h) in ((1.35, 5.75, 1.36, 0.94), (-5.95, 3.10, 1.20, 0.86)):
            self.add(box("hay_bale", (px, py, G_Z + h * 0.5), (w, w * 0.82, h),
                         M["sand"]), 0.014)
            self.add(box("hay_top", (px, py, G_Z + h + 0.03), (w * 0.86, w * 0.70, 0.10),
                         M["sand"]), 0.008)
            for k in (-1, 1):
                self.add(box("hay_rope", (px + k * w * 0.26, py, G_Z + h * 0.5),
                             (0.07, w * 0.86, h + 0.04), M["wood_dark"]), 0.003)
        # 水槽（石槽 + 水面 + 木架）
        wx, wy = 3.05, 3.95
        self.add(box("trough", (wx, wy, G_Z + 0.24), (1.66, 0.64, 0.48),
                     M["stone_mid"]), 0.012)
        self.add(box("trough_w", (wx, wy, G_Z + 0.40), (1.44, 0.46, 0.08),
                     M["roof_pale"]), 0.004)
        for sx in (-1, 1):
            self.add(box("trough_leg", (wx + sx * 0.62, wy, G_Z + 0.06),
                         (0.16, 0.50, 0.12), M["stone_dark"]), 0.004)
        # 板车（车斗 + 两轮 + 车辕 + 队色车篷）
        cx, cy = -6.55, 1.95
        self.add(box("cart_bed", (cx, cy, G_Z + 0.62), (1.70, 0.96, 0.30),
                     M["wood_warm"]), 0.010)
        for sy in (-1, 1):
            self.add(box("cart_side", (cx, cy + sy * 0.48, G_Z + 0.84),
                         (1.74, 0.10, 0.34), M["wood_dark"]), 0.006)
        for sx in (-1, 1):
            self.add(revolve("cart_wheel", [(0.10, 0.0), (0.42, 0.02), (0.42, 0.14),
                                            (0.10, 0.16)], 8,
                             (cx - 0.30, cy + sx * 0.60, G_Z + 0.22), M["wood_dark"]), 0.0, 1)
            self.add(revolve("cart_hub", [(0.0, 0.0), (0.10, 0.02), (0.10, 0.18)], 8,
                             (cx - 0.30, cy + sx * 0.52, G_Z + 0.22), M["iron"]), 0.0, 1)
        for sy in (-1, 1):
            self.add(beam("cart_shaft", (cx + 0.86, cy + sy * 0.34, G_Z + 0.60),
                          (cx + 1.92, cy + sy * 0.24, G_Z + 0.18), 0.09, 0.09,
                          M["wood_dark"]), 0.004)
        # 车篷：三级阶梯拱 + 队色布（农场唯一的大块阵营色）
        for i, (w, hh, zz) in enumerate(((1.10, 0.20, 1.06), (0.86, 0.22, 1.24),
                                         (0.56, 0.20, 1.42))):
            self.add(box("cart_canopy", (cx - 0.06, cy, G_Z + zz),
                         (w, 1.02 - i * 0.10, hh), M["team"]), 0.006)
        self.add(box("cart_canopy_t", (cx - 0.06, cy, G_Z + 1.56), (0.40, 0.66, 0.08),
                     M["team_trim"]), 0.004)
        # 木桶 ×2 + 农具 + 草簇 + 碎石
        self.barrel("barrel_a", (6.85, 4.45), 0.30, 0.72, G_Z)
        self.barrel("barrel_b", (-4.95, 7.35), 0.26, 0.62, G_Z)
        self.add(box("plank_loose", (2.85, 7.15, G_Z + 0.06), (1.30, 0.24, 0.10),
                     M["wood_warm"], rot=(0, 0.06, 0.5)), 0.004)
        for (px, py) in ((3.05, 7.85), (-7.05, 1.10), (6.55, 7.10), (-4.85, 1.55)):
            self.grass((px, py))
        for (px, py, rz) in ((2.30, 8.05, 0.4), (-7.10, 5.20, -0.3), (0.10, 8.35, 0.9)):
            self.add(box("pebble", (px, py, G_Z + 0.05), (0.22, 0.16, 0.10),
                         M["stone_mid"], rot=(0, 0, rz)), 0.004)

    def grass(self, p, h=0.26):
        M = self.M
        x, y = p
        for k in range(3):
            a = math.radians(18 + k * 60)
            hh = h * (0.84 + 0.11 * k)
            self.add(box("tuft", (x + 0.02 * math.cos(a + 1.1),
                                  y + 0.02 * math.sin(a + 1.1),
                                  G_Z + hh * 0.46), (0.12, 0.02, hh), M["moss"],
                         rot=(0.20 * math.cos(a), 0.20 * math.sin(a), a)), 0.0)

    def barrel(self, name, p, r, h, z0=0.0):
        M = self.M
        x, y = p
        self.add(revolve(name, [(r * 0.86, 0.0), (r, 0.12), (r, h - 0.12), (r * 0.86, h)], 8,
                         (x, y, z0 - 0.02), M["wood_warm"]), 0.008)
        for zz in (h * 0.22, h * 0.76):
            self.add(tube_band(name + "_hoop", (x, y), r - 0.01, r + 0.035,
                               z0 + zz, z0 + zz + 0.10, 8, M["iron"]), 0.003)

    # ── 9. 场院围栏（L 形：左 + 前，正面留 1.80 双开门）─────────────────────
    def fence(self):
        M = self.M
        # 石座（0.34 高 × 0.40 宽）
        self.add(box("fence_base", (FX, (F_LEN_BACK + FY) * 0.5, G_Z + 0.17),
                     (0.40, FY - F_LEN_BACK, 0.34), M["stone_mid"]), 0.012)
        for (a, b) in ((FX_START, F_GATE_X0), (F_GATE_X1, FX)):
            self.add(box("fence_base_f", ((a + b) * 0.5, FY, G_Z + 0.17),
                         (b - a, 0.40, 0.34), M["stone_mid"]), 0.012)
        # 右段（沿 Y）+ 前段两截（沿 X，中间留 1.80 的门）
        self.fence_run("fence_l", (FX, F_LEN_BACK), (FX, FY), 1.62)
        self.fence_run("fence_f1", (FX_START, FY), (F_GATE_X0, FY), 1.62, M["team_trim"])
        self.fence_run("fence_f2", (F_GATE_X1, FY), (FX - 0.22, FY), 1.62, M["team_trim"])
        # 双开木门（1.80 宽）
        for k, sgn in enumerate((-1, 1)):
            x = (F_GATE_X0 + F_GATE_X1) * 0.5 + sgn * 0.45
            self.add(box("field_gate_leaf", (x, FY, G_Z + 0.34 + FH * 0.44),
                         (0.86, 0.10, FH * 0.86), M["wood_warm"]), 0.006)
            for zz in (0.42, 0.78):
                self.add(box("field_gate_rail", (x, FY, G_Z + 0.34 + FH * zz),
                             (0.80, 0.13, 0.11), M["wood_dark"]), 0.003)
            # 斜撑
            self.add(beam("field_gate_brace", (x - 0.34, FY + 0.02, G_Z + 0.40),
                          (x + 0.34, FY + 0.02, G_Z + 0.34 + FH * 0.80),
                          0.07, 0.05, M["wood_dark"]), 0.003)
        # 门柱（比栏高，柱头 + 队色箍）
        for xx in (F_GATE_X0, F_GATE_X1):
            self.add(box("gate_post", (xx, FY, G_Z + 0.34 + FH * 0.60),
                         (0.24, 0.24, FH * 1.20), M["wood_dark"]), 0.008)
            self.add(box("gate_post_band", (xx, FY, G_Z + 0.34 + FH * 0.86),
                         (0.28, 0.28, 0.14), M["team"]), 0.004)
            self.add(revolve("gate_post_cap", [(0.0, 0.0), (0.11, 0.02), (0.13, 0.09),
                                               (0.06, 0.17), (0.0, 0.20)], 8,
                             (xx, FY, G_Z + 0.34 + FH * 1.20), M["gold"]), 0.0, 1)

    def fence_run(self, name, p0, p1, step, rail_mat=None):
        """一段栏：立柱 + 两道横杆 + 柱帽。p0→p1 为轴对齐线段。"""
        M = self.M
        x0, y0 = p0
        x1, y1 = p1
        ln = math.hypot(x1 - x0, y1 - y0)
        n = max(1, int(round(ln / step)))
        for i in range(n + 1):
            t = i / n
            px, py = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
            self.add(box(name + "_post", (px, py, G_Z + 0.34 + FH * 0.52),
                         (0.18, 0.18, FH * 1.04), M["wood_dark"]), 0.006)
            self.add(revolve(name + "_cap", [(0.0, 0.0), (0.10, 0.02), (0.12, 0.08),
                                             (0.05, 0.15), (0.0, 0.17)], 8,
                             (px, py, G_Z + 0.34 + FH * 1.04), M["wood_dark"]), 0.0, 1)
        for zz in (0.34, 0.82):
            self.add(box(name + "_rail", ((x0 + x1) * 0.5, (y0 + y1) * 0.5,
                                          G_Z + 0.34 + FH * zz),
                         (abs(x1 - x0) + 0.12, abs(y1 - y0) + 0.12, 0.14),
                         rail_mat or M["wood_warm"]), 0.005)

    # ── 10. 阵营色收尾：筒仓箍已在 silo()；这里只补山墙徽记 ────────────────
    def heraldry(self):
        # 前墙门楣之上的盾徽。
        # v1 写在 `BY - 0.04`（墙面内侧 4 cm）—— 整枚徽记埋在墙里，主图上一个像素都没有。
        # 贴面件的中心必须在墙面**之外**：cy = BY + 0.02（凸出 3.4 cm）。
        self.crest("crest_barn", "Y", 0.80, BY + 0.02, 4.64, 0.52)

    # ── 11. 组装 / 收尾 ────────────────────────────────────────────────────
    def build(self):
        for step in (self.base, self.barn, self.barn_roof, self.silo, self.shed,
                     self.field, self.well, self.props, self.fence, self.heraldry):
            step()
        return self

    def finalize(self, bevel=True):
        # 细分的取舍和哨塔一致：大平面（墙 / 石台 / 屋面 / 田垄）不倒角磨圆，
        # 只磨小体量件。筒仓是 12 边形，一旦被 CC 就会变成"圆柱"，必须排除。
        # 细分的取舍（v2）：石塔是 12 边形，一旦被 CC 就磨成"圆柱"（现代筒仓的
        # 第二个来源），必须整组排除；窗、门、围栏这类小件也不磨。
        skip_cc = ("tower_", "twin_", "tloop_", "silo_", "roof_", "row", "wheat",
                   "cabbage", "pumpkin", "field_gate", "gate_", "fence_", "win",
                   "hay_", "cart_", "plinth", "yard_", "path", "trough",
                   "well_", "barn_gable", "barn_back", "barn_front", "barn_dado",
                   "barn_floor_in", "crest_", "pebble", "tuft", "plank_loose",
                   "tool_", "shed_rib")
        for (ob, bev, sub, seg) in self.items:
            co = ob.data.vertices
            dims = [max(v.co[i] for v in co) - min(v.co[i] for v in co) for i in range(3)]
            vol = dims[0] * dims[1] * dims[2]
            chunky = min(dims) >= 0.12 and vol >= 0.14
            n = ob.name
            if self.smooth:
                cc = 1 if (chunky and not n.startswith(skip_cc)) else 0
                # 石塔的十二边形必须保持硬棱：相邻面夹角 30° < shade_auto 的 32°，
                # 走平滑会把整座塔磨成一根圆柱（v1"现代筒仓"的第二个来源）。
                hard = n.startswith(("tower_", "twin_", "tloop_"))
                L.finalize(ob, bevel=min(max(bev, 0.008), 0.022), seg=1, sub=cc,
                           flat=hard)
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
        out = L.join_by_material(objs, prefix="FM")
        mirror_x(out)
        if self.unwrap:
            L.smart_uv(out)
        return out


def build(smooth=True, unwrap=True, bevel=True):
    m = Model(smooth, unwrap).build()
    objs = m.finalize(bevel=bevel)
    return objs, L.stats(objs)
