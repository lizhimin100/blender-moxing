"""
tv_model.py —— 酒馆内部（Tavern Interior）v1：**剖切内景 + 吧台 + 壁炉 + 吊灯**

这不是一栋房子，是一个**被剖开的房间**：正面整面墙拿掉，两侧墙从后往前逐段降低，
观众从 26° 俯角直接看进屋里。左右墙的断口做成"切面"（浅色石芯 + 一道暗线），
读作"这是剖面"，而不是"这栋房子没盖完"。

构图（俯视）：
  ① 左后一整条**吧台**（深木台面 + 三个酒桶 + 背墙酒架），是画面的第一层；
  ② 右后一座**石壁炉**（火 + 烟囱胸墙），暖色点；
  ③ 中间三张桌（一张长桌 + 两张方桌）+ 条凳，留出一条从门口到吧台的走道；
  ④ 左前一道**上二楼的木梯**，把画面左下角填满，也给一个"往上"的方向；
  ⑤ 正中一盏**铁环吊灯**（六支蜡烛）—— 俯视时是一圈亮点，压住整个房间。

明度秩序：石基座 → **暗**木地板 → **暖白**石灰墙 → **中**木梁 / 家具 → **暗**吧台立面 →
**近黑**梁底 / 炉膛 → 铜 / 金 / 队色 / 火光。

队色（人族）：后墙横幅（竖直）+ 两条桌旗（水平）+ 吧台立面一条通长色带（水平）。
俯视靠桌旗和吧台带，正视靠横幅。

坐标：X 右、Y 前（+Y = 正面）、Z 上；原点在占地中心，z = 0 地面。
交付前整体沿 X 镜像一次（与九座一致）。
"""
import math

import bpy
from mathutils import Vector

import bslib as L
import dl_kit as K
from bslib import arch_band, beam, box, extrude, mesh_obj, revolve, tube_band
from br_model import mirror_x
from wt_model import frame_ring

# ── 占地 ────────────────────────────────────────────────────────────────────
BX = 5.30                        # 半宽 10.6
BY0, BY1 = -4.40, 4.40           # 8.8 深
G0, G1 = 0.00, 0.16              # 石基
F0, F1 = 0.16, 0.28              # 木地板

# ── 墙 ──────────────────────────────────────────────────────────────────────
WX = 5.00                        # 外墙内表面
WY = -4.05                       # 后墙内表面
WT = 0.30                        # 墙厚
WH_BACK = 3.42
WH_L = (3.38, 2.56, 1.62)        # 左墙三段（后 → 前）
WH_R = (3.38, 2.80, 1.92)        # 右墙三段（故意与左不同高）
SEG = ((-4.05, -1.35), (-1.35, 1.35), (1.35, 4.05))

# ── 梁 ──────────────────────────────────────────────────────────────────────
BM_Z0, BM_Z1 = 3.30, 3.48
BM_Y = (-1.72, 1.38)
BM_FRONT = 3.86

# ── 吧台 ────────────────────────────────────────────────────────────────────
BAR_X0, BAR_X1 = -4.55, -0.75
BAR_Y0, BAR_Y1 = -3.30, -2.52
BAR_H = 1.16

# ── 壁炉 ────────────────────────────────────────────────────────────────────
HB_X0, HB_X1 = 1.55, 4.25
HB_Y0, HB_Y1 = -4.05, -2.55
HB_OPEN = 0.72                   # 半宽
HB_Z = 1.32                      # 炉口高

# ── 楼梯 ────────────────────────────────────────────────────────────────────
ST_X0, ST_X1 = -4.92, -3.86
ST_Y0, ST_Y1 = 0.55, 3.20
ST_N = 6
ST_RISE = (1.68 - F1) / ST_N
ST_TREAD = (ST_Y1 - ST_Y0) / ST_N


class Model:
    def __init__(self, smooth, unwrap=True):
        self.smooth = smooth
        self.unwrap = unwrap
        self.items = []
        self.M = L.all_materials()

    def add(self, ob, bevel=0.010, sub=0, seg=1):
        self.items.append((ob, bevel, sub, seg))
        return ob

    def put(self, obs, bevel=0.004):
        for ob in obs:
            self.add(ob, bevel)
        return obs

    # ── 1. 石基 + 木地板 ───────────────────────────────────────────────────
    def floor(self):
        M = self.M
        self.add(box("base_slab", (0, (BY0 + BY1) * 0.5, (G0 + G1) * 0.5),
                     (BX * 2, BY1 - BY0, G1 - G0), M["stone_mid"]), 0.020)
        self.add(box("base_step", (0, BY1 + 0.14, 0.09), (4.20, 0.28, 0.18),
                     M["stone_light"]), 0.008)
        # 地板：12 条宽板，缝里露出深色垫层（不是画线）
        self.add(box("flr_under", (0, (WY + BY1) * 0.5, F0 + 0.02),
                     (WX * 2, BY1 - WY, 0.04), M["wood_dark"]), 0.006)
        n = 12
        w = (WX * 2 - 0.02) / n
        for i in range(n):
            self.add(box("flr_board", (-WX + w * (i + 0.5), (WY + BY1) * 0.5,
                                       F1 - 0.035 + (i % 3) * 0.0015),
                         (w - 0.022, BY1 - WY - 0.04, 0.07),
                         M["wood_mid"] if i % 4 else M["wood_warm"]), 0.004)

    # ── 2. 墙（三段递降）+ 切面 + 木构 ─────────────────────────────────────
    def walls(self):
        M = self.M
        # 后墙
        self.add(box("wall_back", (0, WY - WT * 0.5, (F1 + WH_BACK) * 0.5),
                     (BX * 2, WT, WH_BACK - F1), M["plaster"]), 0.014)
        self.add(box("wall_back_cap", (0, WY - WT * 0.5, WH_BACK + 0.035),
                     (BX * 2 + 0.04, WT + 0.06, 0.07), M["stone_light"]), 0.004)
        self.add(box("wall_back_line", (0, WY + 0.004, WH_BACK - 0.10),
                     (BX * 2, 0.03, 0.05), M["wood_dark"]), 0.002)
        # 左右墙：三段递降
        for sgn, heights in ((-1, WH_L), (1, WH_R)):
            wx = sgn * (WX + WT * 0.5)
            for k, ((y0, y1), hh) in enumerate(zip(SEG, heights)):
                # 只砌到 4.05（后墙之后交给后墙）
                self.add(box("wall_side", (wx, (y0 + y1) * 0.5, (F1 + hh) * 0.5),
                             (WT, y1 - y0, hh - F1), M["plaster"]), 0.012)
                # 切面：浅石芯 + 一道暗线（读作"剖面"）
                self.add(box("wall_cut", (wx, (y0 + y1) * 0.5, hh + 0.030),
                             (WT + 0.06, y1 - y0 - 0.02, 0.06), M["stone_light"]),
                         0.004)
                self.add(box("wall_cut_line", (wx, (y0 + y1) * 0.5, hh - 0.048),
                             (WT + 0.065, y1 - y0 - 0.02, 0.025), M["wood_dark"]),
                         0.002)
                # 转角柱：每段端头一根（切段的"结束"要有东西收住）
                for yy in (y0 + 0.10, y1 - 0.10):
                    self.add(box("wall_post", (wx, yy, (F1 + hh) * 0.5 - 0.012),
                                 (WT + 0.08, 0.20, hh - F1 - 0.024), M["wood_mid"]),
                             0.004)
        # 中段切口的两根壁柱：既是剖面收口，也真的托住第二根横梁
        for sgn in (-1, 1):
            self.add(box("wall_pier", (sgn * (WX + WT * 0.5), 1.35, (2.55 + 3.38) * 0.5),
                         (WT + 0.10, 0.34, 3.38 - 2.55), M["wood_mid"]), 0.006)
        # 正面两个墙墩（把"缺口"框住）
        for sgn in (-1, 1):
            self.add(box("wall_stub", (sgn * (WX - 0.45), BY1 - WT * 0.5, (F1 + 1.62) * 0.5),
                         (0.90, WT, 1.62 - F1), M["plaster"]), 0.012)
            self.add(box("wall_stub_cap", (sgn * (WX - 0.45), BY1 - WT * 0.5, 1.655),
                         (0.96, WT + 0.06, 0.07), M["stone_light"]), 0.004)
        # 墙裙：一圈深木（只到 0.95，绕开家具）
        for (x0, x1, y) in ((-WX, WX, WY + 0.02),):
            self.add(box("wall_wains", ((x0 + x1) * 0.5, y, (F1 + 0.90) * 0.5),
                         (x1 - x0, 0.05, 0.90 - F1), M["wood_mid"]), 0.004)
        for sgn in (-1, 1):
            self.add(box("wall_wains_s", (sgn * (WX - 0.02), (WY + 3.6) * 0.5,
                                          (F1 + 0.90) * 0.5),
                         (0.05, 3.6 - WY, 0.90 - F1), M["wood_mid"]), 0.004)
        # 墙面竖向木柱（半木构的节奏）
        for xx in (-3.55, -1.10, 1.20, 3.55):
            self.add(box("wall_stud", (xx, WY + 0.03, (F1 + WH_BACK - 0.2) * 0.5),
                         (0.16, 0.08, WH_BACK - 0.2 - F1), M["wood_dark"]), 0.003)

    # ── 3. 梁 + 前柱 ───────────────────────────────────────────────────────
    def frame(self):
        M = self.M
        for yy in BM_Y:
            self.add(box("beam_cross", (0, yy, (BM_Z0 + BM_Z1) * 0.5),
                         (WX * 2, 0.20, BM_Z1 - BM_Z0), M["wood_dark"]), 0.008)
            # 梁头小斗
            for sgn in (-1, 1):
                self.add(box("beam_corbel", (sgn * (WX - 0.12), yy, BM_Z0 - 0.10),
                             (0.30, 0.30, 0.18), M["wood_dark"]), 0.004)
        # 前檐梁 + 两根前柱（把剖面"框"起来，也让梁有支撑）
        self.add(box("beam_front", (0, BM_FRONT, (BM_Z0 + BM_Z1) * 0.5),
                     (WX * 2, 0.22, BM_Z1 - BM_Z0), M["wood_dark"]), 0.008)
        for sgn in (-1, 1):
            self.add(box("post_front", (sgn * 3.55, BM_FRONT, (F1 + BM_Z0) * 0.5),
                         (0.26, 0.26, BM_Z0 - F1), M["wood_dark"]), 0.006)
            self.add(box("post_front_base", (sgn * 3.55, BM_FRONT, F1 + 0.08),
                         (0.40, 0.40, 0.16), M["wood_mid"]), 0.004)
            self.add(box("post_front_cap", (sgn * 3.55, BM_FRONT, BM_Z0 - 0.06),
                         (0.38, 0.38, 0.14), M["wood_mid"]), 0.004)


    # ── 4. 吧台 ────────────────────────────────────────────────────────────
    def bar(self):
        M = self.M
        self.add(box("bar_front", ((BAR_X0 + BAR_X1) * 0.5, BAR_Y1 - 0.06,
                                   (F1 + BAR_H - 0.06) * 0.5),
                     (BAR_X1 - BAR_X0, 0.12, BAR_H - 0.06 - F1), M["wood_mid"]), 0.006)
        # 台面（比立面宽 0.10，出挑）
        self.add(box("bar_top", ((BAR_X0 + BAR_X1) * 0.5, (BAR_Y0 + BAR_Y1) * 0.5,
                                 BAR_H - 0.005),
                     (BAR_X1 - BAR_X0 + 0.14, BAR_Y1 - BAR_Y0 + 0.14, 0.11),
                     M["wood_warm"]), 0.008)
        # 立面竖板条（每 0.34 一条）
        n = 11
        for i in range(n):
            xx = BAR_X0 + 0.14 + (BAR_X1 - BAR_X0 - 0.28) * i / (n - 1)
            self.add(box("bar_plank", (xx, BAR_Y1 + 0.005, (F1 + BAR_H - 0.16) * 0.5),
                         (0.055, 0.02, BAR_H - 0.24 - F1), M["wood_dark"]), 0.001)
        # 队色通长色带（水平面：俯视也读得到）
        self.add(box("bar_team", ((BAR_X0 + BAR_X1) * 0.5, BAR_Y1 - 0.02, BAR_H - 0.16),
                     (BAR_X1 - BAR_X0 - 0.10, 0.14, 0.10), M["team"]), 0.003)
        # 台面前沿一条队色漆线（正视 / 俯视都读得到）
        self.add(box("bar_edge_team", ((BAR_X0 + BAR_X1) * 0.5, BAR_Y1 + 0.02,
                                       BAR_H - 0.015),
                     (BAR_X1 - BAR_X0 + 0.10, 0.03, 0.05), M["team"]), 0.002)
        # 脚踏铜杆
        self.add(box("bar_rail", ((BAR_X0 + BAR_X1) * 0.5, BAR_Y1 + 0.05, F1 + 0.18),
                     (BAR_X1 - BAR_X0 - 0.30, 0.06, 0.06), M["copper"]), 0.002)
        for k in range(3):
            self.add(box("bar_rail_arm", (BAR_X0 + 0.5 + k * 1.3, BAR_Y1 + 0.01,
                                          F1 + 0.18),
                         (0.05, 0.10, 0.05), M["copper"]), 0.002)
        # 背墙酒架两层 + 酒瓶
        for zz in (1.55, 2.02):
            for (sx0, sx1, nb) in ((BAR_X0, -3.92, 2), (-1.82, BAR_X1, 3)):
                self.add(box("bar_shelf", ((sx0 + sx1) * 0.5, WY + 0.14, zz),
                             (sx1 - sx0, 0.26, 0.07), M["wood_warm"]), 0.004)
                for i in range(nb):
                    xx = sx0 + 0.28 + i * ((sx1 - sx0 - 0.50) / max(nb - 1, 1))
                    self.add(revolve("bar_bottle", [(0.0, 0.0), (0.065, 0.0),
                                                    (0.065, 0.16), (0.026, 0.24),
                                                    (0.026, 0.30)], 6,
                                     (xx, WY + 0.15, zz + 0.035), M["glass"]), 0.002)
        # 桶 ×3（吧台后）
        for (px, py, r, hh) in ((BAR_X0 + 0.35, WY + 0.62, 0.30, 0.76),
                                (BAR_X0 + 1.00, WY + 0.66, 0.27, 0.70),
                                (BAR_X1 - 0.42, WY + 0.60, 0.30, 0.76)):
            self.put(K.barrel("bar_keg", px, py, F1, r, hh, M["wood_mid"],
                              M["bronze_dark"]), 0.004)
        # 三个高脚凳（座 + 三腿 + 一道箍）
        for i in range(3):
            sx = BAR_X0 + 0.95 + i * 1.15
            sy = BAR_Y1 + 0.62
            self.add(revolve("stl_seat", [(0.0, 0.0), (0.20, 0.0), (0.20, 0.06)],
                             8, (sx, sy, 0.60), M["wood_warm"]), 0.004)
            for k in range(3):
                a = math.tau * k / 3 + 0.4
                self.add(beam("stl_leg", (sx + 0.14 * math.cos(a),
                                          sy + 0.14 * math.sin(a), 0.62),
                              (sx + 0.19 * math.cos(a), sy + 0.19 * math.sin(a), F1),
                              0.045, 0.045, M["wood_dark"]), 0.002)
            self.add(tube_band("stl_ring", (sx, sy), 0.15, 0.175, 0.30, 0.34, 8,
                               M["iron"]), 0.002)
        # 吧台上的杯 / 壶
        for i in range(3):
            self.put(K.mug("bar_mug", BAR_X0 + 1.05 + i * 0.95, BAR_Y0 + 0.34,
                           BAR_H + 0.06), 0.001)
        self.put(K.pot("bar_pot", BAR_X1 - 0.40, BAR_Y0 + 0.36, BAR_H + 0.045,
                       0.14, 0.18, M["copper"]), 0.001)

    # ── 5. 壁炉 ────────────────────────────────────────────────────────────
    def hearth(self):
        M = self.M
        HX = 2.62
        yc = (HB_Y0 + HB_Y1) * 0.5
        # 炉体：左右 + 上楣（真开口）
        for sgn in (-1, 1):
            self.add(box("hth_pier", (HX + sgn * (HB_OPEN + 0.36), yc, (F1 + 1.95) * 0.5),
                         (0.72, HB_Y1 - HB_Y0, 1.95 - F1), M["stone_mid"]), 0.010)
        self.add(box("hth_lintel", (HX, yc, (HB_Z + 1.95) * 0.5),
                     (HB_OPEN * 2, HB_Y1 - HB_Y0, 1.95 - HB_Z), M["stone_mid"]), 0.010)
        # 炉膛：内壁 / 底 / 顶（近黑）
        for sgn in (-1, 1):
            self.add(box("hth_inner", (HX + sgn * (HB_OPEN - 0.05), yc,
                                       (F1 + HB_Z - 0.036) * 0.5),
                         (0.10, HB_Y1 - HB_Y0 - 0.10, HB_Z - 0.036 - F1),
                         M["ancient_dark"]), 0.003)
        self.add(box("hth_back", (HX, HB_Y0 + 0.05, (F1 + HB_Z - 0.03) * 0.5),
                     (HB_OPEN * 2, 0.10, HB_Z - 0.03 - F1), M["ancient_dark"]), 0.003)
        self.add(box("hth_top", (HX, yc, HB_Z - 0.04),
                     (HB_OPEN * 2, HB_Y1 - HB_Y0 - 0.10, 0.08), M["coal"]), 0.003)
        self.add(box("hth_floor", (HX, yc, F1 + 0.02),
                     (HB_OPEN * 2 - 0.10, HB_Y1 - HB_Y0 - 0.10, 0.05), M["ash"]), 0.003)
        # 炉口石套 + 壁炉台
        for sgn in (-1, 1):
            self.add(box("hth_surround", (HX + sgn * (HB_OPEN + 0.10), HB_Y1 + 0.01,
                                          F1 + 0.90),
                         (0.26, 0.10, 1.80), M["stone_light"]), 0.006)
        self.add(box("hth_surround_t", (HX, HB_Y1 + 0.02, 1.86),
                     (HB_OPEN * 2 + 0.50, 0.14, 0.22), M["stone_light"]), 0.006)
        self.add(box("hth_mantel", (HX, HB_Y1 + 0.10, 1.74), (2.70, 0.30, 0.12),
                     M["wood_warm"]), 0.006)
        # 烟囱胸墙
        self.add(box("hth_breast", (HX, HB_Y0 + 0.55, (1.95 + 3.38) * 0.5),
                     (2.10, 0.90, 3.38 - 1.95), M["stone_mid"]), 0.012)
        self.add(box("hth_breast_cap", (HX, HB_Y0 + 0.55, 3.40), (2.22, 0.98, 0.08),
                     M["stone_light"]), 0.004)
        self.add(box("hth_breast_line", (HX, HB_Y0 + 1.01, 2.55), (2.14, 0.04, 0.10),
                     M["team"]), 0.002)
        # 火：柴 + 炭 + 火舌
        fx, fy = HX, HB_Y1 - 0.55
        self.put(K.embers("hth_ember", fx, fy, F1 + 0.10, 6, 0.46, seed=201), 0.002)
        for i in range(3):
            a = math.tau * i / 3 + 0.2
            self.put(K.log("hth_log",
                           (fx + 0.36 * math.cos(a), fy + 0.36 * math.sin(a), 0.42),
                           (fx - 0.36 * math.cos(a), fy - 0.36 * math.sin(a), 0.46),
                           0.085, M["wood_dark"], M["wood_warm"]), 0.002)
        self.put(K.flame("hth_flame", fx, fy, F1 + 0.22, 0.70, 0.33, seed=202), 0.002)
        # 炉前石台（伸进房间 0.55）+ 火钳
        self.add(box("hth_slab", (HX, HB_Y1 + 0.30, F1 + 0.04),
                     (2.30, 0.60, 0.09), M["stone_light"]), 0.006)
        self.add(box("hth_slab_edge", (HX, HB_Y1 + 0.60, F1 + 0.05),
                     (2.30, 0.06, 0.10), M["stone_mid"]), 0.003)
        self.add(beam("hth_poker", (HX + 0.75, HB_Y1 + 0.28, 0.30),
                      (HX + 0.62, HB_Y1 + 0.30, 1.10), 0.035, 0.035, M["iron"]), 0.002)
        # 炉台上的铜锅 + 旁边的柴堆
        self.put(K.pot("hth_pot", HX - 0.95, HB_Y1 + 0.10, 1.80, 0.17, 0.20, M["copper"]),
                 0.002)
        self.put(K.pot("hth_pot2", HX + 0.95, HB_Y1 + 0.10, 1.82, 0.14, 0.17, M["copper"]),
                 0.002)
        for i in range(4):
            self.put(K.log("hth_wood", (HB_X1 - 0.35 + i * 0.04, -3.30,
                                        0.34 + i * 0.15),
                           (HB_X1 - 0.35 + i * 0.04, -2.55, 0.34 + i * 0.15),
                           0.09, M["wood_mid"], M["wood_warm"]), 0.002)

    # ── 6. 桌 / 凳 / 桌上小件 ───────────────────────────────────────────────
    def table(self, name, x, y, w, d, runner=False, chairs=2):
        M = self.M
        top = 0.78
        self.add(box(name + "_top", (x, y, top), (w, d, 0.09), M["wood_warm"]), 0.006)
        for sx in (-1, 1):
            for sy in (-1, 1):
                self.add(box(name + "_leg", (x + sx * (w * 0.5 - 0.12),
                                             y + sy * (d * 0.5 - 0.12),
                                             (top - 0.03) * 0.5),
                             (0.11, 0.11, top - 0.03), M["wood_dark"]), 0.003)
        self.add(box(name + "_rail", (x, y, 0.22), (w - 0.30, 0.08, 0.08),
                     M["wood_dark"]), 0.002)
        if runner:
            self.add(box(name + "_runner", (x, y, top + 0.055), (w * 0.24, d + 0.05, 0.02),
                         M["team"]), 0.002)
        # 条凳：长边两侧
        for sy in (-1, 1):
            self.add(box(name + "_bench", (x, y + sy * (d * 0.5 + 0.30), 0.44),
                         (w * 0.82, 0.34, 0.07), M["wood_mid"]), 0.004)
            for sx in (-1, 1):
                self.add(box(name + "_benchleg", (x + sx * (w * 0.32),
                                                  y + sy * (d * 0.5 + 0.30), 0.24),
                             (0.09, 0.26, 0.36), M["wood_dark"]), 0.003)
        # 桌上：杯 / 盘 / 蜡烛
        self.put(K.mug(name + "_mug", x - w * 0.24, y + 0.12, top + 0.05), 0.001)
        self.put(K.mug(name + "_mug", x + w * 0.26, y - 0.10, top + 0.05), 0.001)
        self.add(revolve(name + "_plate", [(0.0, 0.0), (0.15, 0.0), (0.15, 0.02)], 8,
                         (x + w * 0.30, y, top + 0.046), M["cloth_cream"]), 0.002)
        self.put(K.candle(name + "_candle", x + 0.05, y - d * 0.22, top + 0.05, 0.14),
                 0.001)

    def tables(self):
        M = self.M
        self.table("tbl_long", -1.35, 1.62, 2.55, 0.98, runner=True)
        self.table("tbl_a", 2.35, 1.20, 1.34, 1.34, runner=True)
        self.table("tbl_b", 3.45, -0.72, 1.30, 1.30, runner=False)

    # ── 7. 楼梯（通往前墙外的二层）──────────────────────────────────────────
    def stair(self):
        M = self.M
        for i in range(ST_N):
            y0 = ST_Y1 - (i + 1) * ST_TREAD
            zt = F1 + (i + 1) * ST_RISE
            self.add(box("stair_tread", ((ST_X0 + ST_X1) * 0.5, y0 + ST_TREAD * 0.5,
                                         (F1 + zt) * 0.5),
                         (ST_X1 - ST_X0, ST_TREAD, zt - F1), M["wood_mid"]), 0.006)
            self.add(box("stair_riser", ((ST_X0 + ST_X1) * 0.5, y0 + 0.012,
                                         (F1 + zt - ST_RISE * 0.5)),
                         (ST_X1 - ST_X0, 0.024, ST_RISE), M["wood_dark"]), 0.002)
        # 斜梁板：把踏步的端头收住，读作"一部楼梯"而不是"一摞板"
        ang = math.atan2(1.52, ST_Y1 - ST_Y0)
        ln = math.hypot(1.52, ST_Y1 - ST_Y0)
        sb = box("stair_string", (ST_X1 - 0.02, (ST_Y0 + ST_Y1) * 0.5,
                                  1.68 - 0.76 + 0.02),
                 (0.06, ln, 0.26), M["wood_dark"], rot=(ang, 0, 0))
        self.add(sb, 0.003)
        # 平台：后侧的"二层"被切掉，只留 1.0 m（读作"上面还有一层"）
        self.add(box("stair_land", ((ST_X0 + ST_X1) * 0.5, ST_Y0 - 0.52, 1.68),
                     (ST_X1 - ST_X0, 1.04, 0.10), M["wood_warm"]), 0.006)
        self.add(box("stair_land_edge", ((ST_X0 + ST_X1) * 0.5, ST_Y0 - 1.05, 1.64),
                     (ST_X1 - ST_X0, 0.06, 0.10), M["wood_dark"]), 0.003)
        # 栏杆：立柱 + 扶手（沿梯斜上）
        self.add(beam("stair_rail", (ST_X1 - 0.04, ST_Y1 - 0.10, F1 + 1.02),
                      (ST_X1 - 0.04, ST_Y0, 2.62), 0.07, 0.07, M["wood_dark"]), 0.003)
        for i in range(4):
            yy = ST_Y0 + 0.30 + i * 0.66
            zz = F1 + 1.52 * (ST_Y1 - yy) / (ST_Y1 - ST_Y0)
            self.add(box("stair_post", (ST_X1 - 0.04, yy, zz + 0.42),
                         (0.08, 0.08, 0.90), M["wood_dark"]), 0.002)
        # 梯下：两只桶 + 一只箱（把死角填满）
        self.put(K.barrel("prop_cask", ST_X1 + 0.42, 2.55, F1, 0.28, 0.70,
                          M["wood_mid"], M["bronze_dark"]), 0.004)
        self.put(K.barrel("prop_cask", ST_X1 + 0.46, 1.85, F1, 0.23, 0.60,
                          M["wood_mid"], M["bronze_dark"]), 0.004)
        self.put(K.crate("prop_crate", ST_X1 + 0.40, 1.20, F1, 0.48, 0.42,
                         M["wood_warm"], M["wood_dark"]), 0.004)

    # ── 8. 吊灯（铁环 + 六支蜡烛 + 三根吊链）───────────────────────────────
    def chandelier(self):
        M = self.M
        cx, cy = 0.35, 1.38
        z = 2.52
        self.add(tube_band("chn_ring", (cx, cy), 0.86, 1.02, z, z + 0.09, 12,
                           M["iron"]), 0.004)
        self.add(tube_band("chn_ring2", (cx, cy), 0.60, 0.68, z + 0.06, z + 0.12, 8,
                           M["iron"]), 0.003)
        for i in range(6):
            a = math.tau * i / 6 + 0.26
            px, py = cx + 0.94 * math.cos(a), cy + 0.94 * math.sin(a)
            self.add(revolve("chn_cup", [(0.0, 0.0), (0.06, 0.0), (0.06, 0.05)], 6,
                             (px, py, z + 0.09), M["copper"]), 0.002)
            self.put(K.candle("chn_candle", px, py, z + 0.14, 0.20), 0.001)
            # 辐条
            self.add(beam("chn_spoke", (cx + 0.18 * math.cos(a), cy + 0.18 * math.sin(a),
                                        z + 0.050 + i * 0.0042),
                          (px, py, z + 0.050 + i * 0.0042), 0.035, 0.035,
                          M["iron"]), 0.001)
        # 三根吊链 + 顶盘
        for i in range(3):
            a = math.tau * i / 3 + 0.5
            self.put(K.chain("chn_chain", cx + 0.94 * math.cos(a),
                             cy + 0.94 * math.sin(a), z + 0.12, BM_Z0 - 0.02,
                             0.05, M["iron"], links=4), 0.001)
        self.add(revolve("chn_hub", [(0.0, 0.0), (0.16, 0.0), (0.16, 0.05)], 8,
                         (cx, cy, z + 0.02), M["iron"]), 0.002)

    # ── 9. 队色横幅 / 灯笼 / 杂物 ──────────────────────────────────────────
    def props(self):
        M = self.M
        # 后墙横幅（吧台正上方）
        bx, bz = -2.85, 3.16
        self.add(box("bnr_bar", (bx, WY + 0.10, bz), (2.10, 0.07, 0.07), M["wood_dark"]),
                 0.003)
        prof = [(-0.95, 0.0), (0.95, 0.0), (0.95, -1.72), (0.30, -2.02),
                (0.0, -1.78), (-0.30, -2.02), (-0.95, -1.72)]
        cl = extrude("bnr_cloth", prof, "Y", 0.035, (0, 0), M["team"])
        cl.location = (bx, WY + 0.12, bz - 0.02)
        self.add(cl, 0.005)
        self.add(box("bnr_trim", (bx, WY + 0.13, bz - 0.12), (1.86, 0.05, 0.07),
                     M["team_trim"]), 0.003)
        self.add(box("bnr_crest", (bx, WY + 0.14, bz - 0.95), (0.42, 0.03, 0.42),
                     M["team_trim"]), 0.002)
        # 两侧墙各一面小横幅（3/4 机位总有一面朝镜头）
        # 左墙那面必须避开楼梯（梯占 y 0.55–3.20），挂在 y=-0.75 的墙面上
        for sgn, yy in ((-1, -1.85), (1, 1.05)):
            bx0 = sgn * (WX - 0.03)
            self.add(box("bnr_side_bar", (bx0 - sgn * 0.05, yy, 2.42),
                         (0.07, 1.26, 0.06), M["wood_dark"]), 0.003)
            prof2 = [(-0.58, 0.0), (0.58, 0.0), (0.58, -1.10), (0.18, -1.34),
                     (0.0, -1.14), (-0.18, -1.34), (-0.58, -1.10)]
            cl2 = extrude("bnr_side_cloth", prof2, "X", 0.08, (0, 0), M["team"])
            cl2.location = (sgn * (WX - 0.04), yy, 2.40)
            self.add(cl2, 0.004)
        # 后墙两盏灯笼（对称）
        for sgn in (-1, 1):
            lx = 2.45 + sgn * 2.92
            self.add(box("lan_bracket", (lx, WY + 0.06, 2.70), (0.06, 0.24, 0.06),
                         M["iron"]), 0.002)
            self.add(box("lan_body", (lx, WY + 0.22, 2.48), (0.22, 0.22, 0.30),
                         M["iron"]), 0.003)
            self.add(box("lan_glass", (lx, WY + 0.22, 2.48), (0.16, 0.16, 0.22),
                         M["glow"]), 0.001)
        # 门边衣帽架
        self.add(box("prop_rack_base", (4.45, 3.65, F1 + 0.06), (0.50, 0.50, 0.08),
                     M["wood_dark"]), 0.003)
        self.add(box("prop_rack_post", (4.45, 3.65, 1.15), (0.09, 0.09, 1.72),
                     M["wood_dark"]), 0.003)
        for i in range(3):
            a = math.tau * i / 3 + 0.4
            self.add(box("prop_rack_arm", (4.45 + 0.20 * math.cos(a),
                                           3.65 + 0.20 * math.sin(a), 1.92),
                         (0.30, 0.06, 0.06), M["wood_dark"],
                         rot=(0, 0, a)), 0.002)
        self.add(box("prop_cloak", (4.45, 3.78, 1.56), (0.34, 0.12, 0.74),
                     M["cloth_cream"]), 0.004)
        # 地上的小件：扫帚 / 水桶 / 麦袋
        self.add(beam("prop_broom", (4.35, -2.10, 0.25), (4.20, -2.35, 1.34),
                      0.05, 0.05, M["wood_warm"]), 0.002)
        self.put(K.barrel("prop_bucket", 4.42, -1.80, F1, 0.20, 0.44,
                          M["wood_dark"], M["iron"]), 0.003)
        self.add(box("prop_sack", (3.95, 2.95, F1 + 0.23), (0.42, 0.32, 0.44),
                     M["cloth_cream"], rot=(0, 0, 0.3)), 0.004)
        # 右前角：两只桶 + 一只箱 + 麻袋（把俯视右下角填住）
        self.put(K.barrel("prop_corner", 4.38, 2.10, F1, 0.30, 0.74,
                          M["wood_mid"], M["bronze_dark"]), 0.004)
        self.put(K.barrel("prop_corner", 4.32, 2.95, F1, 0.24, 0.62,
                          M["wood_mid"], M["bronze_dark"]), 0.004)
        self.put(K.crate("prop_corner", 3.55, 2.95, F1, 0.52, 0.44,
                         M["wood_warm"], M["wood_dark"]), 0.005)
        self.add(box("prop_sack2", (3.60, 2.30, F1 + 0.20), (0.46, 0.34, 0.40),
                     M["cloth_cream"], rot=(0, 0, -0.25)), 0.004)
        # 炉前地毯（暖白 + 队色边）
        self.add(box("prop_rug", (2.62, -1.55, F1 + 0.035), (2.20, 1.30, 0.05),
                     M["cloth_cream"]), 0.003)
        self.add(box("prop_rug_edge", (2.62, -0.96, F1 + 0.045), (2.24, 0.12, 0.05),
                     M["team"]), 0.002)
        # 菜单板（后墙，横幅右侧）
        self.add(box("prop_board", (0.35, WY + 0.06, 2.05), (1.10, 0.08, 0.80),
                     M["wood_dark"]), 0.004)
        for i in range(3):
            self.add(box("prop_board_line", (0.35, WY + 0.11, 2.28 - i * 0.18),
                         (0.82, 0.02, 0.04), M["cloth_cream"]), 0.001)
        # 梁下挂的香草 / 干肉（深色小串，增加"有人住"的密度）
        for xx in (-3.20, -2.75, 2.90):
            self.add(box("prop_hang", (xx, BM_Y[0] + 0.02, BM_Z0 - 0.18),
                         (0.10, 0.10, 0.36), M["wood_dark"]), 0.002)
            self.add(box("prop_hang2", (xx + 0.06, BM_Y[0] + 0.02, BM_Z0 - 0.29),
                         (0.08, 0.08, 0.26), M["moss_dark"]), 0.002)
        # 门内一块地垫（队色，水平）
        self.add(box("prop_mat", (0, BY1 - 0.55, F1 + 0.03), (2.10, 0.70, 0.06),
                     M["cloth_cream"]), 0.003)
        for yy in (BY1 - 0.88, BY1 - 0.22):
            self.add(box("prop_mat_edge", (0, yy, F1 + 0.034), (2.10, 0.06, 0.06),
                         M["team"]), 0.002)

    # ── 10. 组装 / 收尾 ─────────────────────────────────────────────────────
    def build(self):
        for step in (self.floor, self.walls, self.frame, self.bar, self.hearth,
                     self.tables, self.stair, self.chandelier, self.props):
            step()
        return self

    def finalize(self, bevel=True):
        flat_pref = ("flr_", "bar_plank", "wall_stud", "wall_cut", "stair_riser",
                     "lan_glass", "bnr_cloth", "prop_mat", "hth_top")
        cc_ok = ("bar_keg", "bar_bottle", "stl_seat", "stl_ring", "chn_ring",
                 "chn_cup", "hth_pot", "prop_cask", "prop_bucket", "tbl_",
                 "flame_", "candle", "hth_log", "hth_wood", "bar_pot")
        for (ob, bev, sub, seg) in self.items:
            co = ob.data.vertices
            if not len(co):
                continue
            dims = [max(v.co[i] for v in co) - min(v.co[i] for v in co) for i in range(3)]
            n = ob.name
            is_flat = n.startswith(flat_pref)
            if self.smooth:
                chunky = min(dims) >= 0.09 and dims[0] * dims[1] * dims[2] >= 0.02
                cc = 1 if (chunky and n.startswith(cc_ok)) else 0
                L.finalize(ob, bevel=min(max(bev, 0.002), 0.012), seg=1, sub=cc,
                           flat=is_flat)
            else:
                b = 0.0 if (not bevel or max(dims) < 1.10 or bev < 0.006) else bev
                L.finalize(ob, bevel=b, seg=1, sub=0, flat=True)
        objs = [it[0] for it in self.items]
        bpy.ops.object.select_all(action="DESELECT")
        for ob in objs:
            ob.select_set(True)
        bpy.context.view_layer.objects.active = objs[0]
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        bpy.ops.object.select_all(action="DESELECT")
        out = L.join_by_material(objs, prefix="TV")
        mirror_x(out)
        if self.unwrap:
            L.smart_uv(out)
        return out


def build(smooth=True, unwrap=True, bevel=True):
    m = Model(smooth, unwrap).build()
    objs = m.finalize(bevel=bevel)
    return objs, L.stats(objs)
