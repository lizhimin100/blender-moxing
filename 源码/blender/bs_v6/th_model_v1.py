"""
th_model.py —— 城镇大厅（Town Hall）v1 · 联盟的议事中枢

设计定调
--------
前两座的语言已经定死：冷灰石墙 + 深蓝黑瓦 + 一条粗阵营色带 + 金线 + 木构 + 徽记。
城镇大厅要在同一套语言里"更庄重一档"，靠三件事而不是靠加东西：

  ① **一条中轴**：前突钟塔 → 拱门 → 三级踏步 → 铺石前庭 → 落地石阶，全压在同一条线上。
     塔从地面长到 16.1 m，是全套资产里唯一的高点（兵营 10.3 / 铁匠铺 11.0）。
  ② **一顶冠**：四坡屋面上立开放的钟亭 + 尖顶 —— "crown_eave" 这一型的读法，
     和铁匠铺的 cross gable、兵营的 flat crenel 不撞型。
  ③ **一层台**：建筑坐 0.72 m 石台上，前面接铺石广场（与基座共用面），
     广场上只放"基地"该有的东西：公告板、长凳、火盆、两支旗杆。不做第二座建筑。

比例：主体 9.6 × 7.2，含台与广场 10.56 × 14.52，与兵营（10.96 × 14.63）、
铁匠铺（10.03 × 11.80）同一量级。总高 16.10。

坐标：X 右、Y 前（+Y = 正面）、Z 上；原点在占地中心，z = 0 地面。
交付前整体沿 X 镜像一次（与另外两座一致）。

徽记 / 旗帜 / 盾 / 木桶木箱**直接继承 br_model.Model** —— 这套资产只有一枚纹章，
不在这座里另画一版（改一处几座一起变）。
"""
import math
from math import tau as TAU

import bpy

import bslib as L
import br_model as BR
from bslib import (arch_band, beam, box, cone, cyl, extrude, frustum, lathe,
                   mesh_obj, revolve, ring_y, tube_band)
from br_model import arch_profile, mirror_x, out_sign, vcyl

# ── 主体与标高 ───────────────────────────────────────────────────────────────
W2 = 4.80                       # 半宽（9.6）
YF, YB = 3.60, -3.60            # 前后墙（7.2 进深）
H0 = 0.72                       # 建筑地面（石台顶）
DADO = 1.68                     # 墙裙顶
STR_Z = 4.45                    # 腰线中心
B0, B1 = 4.65, 5.35             # 阵营色带（正立面最醒目的一条横色）
WALL_TOP = 8.10                 # 墙体顶 / 檐口底
CORN1 = 8.55                    # 檐口顶
EAVE_Z = 8.50                   # 屋面檐口
RIDGE_Z = 11.80                 # 屋脊
ROOF_T = 0.18                   # 檐口可见厚度（椽 0.10 + 望板 0.03 + 瓦 0.05）
AX, AY = 5.30, 4.15             # 屋面出檐半宽 / 半深
RX = 1.60                       # 屋脊半长

# ── 前突钟塔 ─────────────────────────────────────────────────────────────────
TX = 1.55                       # 塔半宽（3.1）
TY0, TY1 = 2.35, 4.60           # 塔的进深：后段埋进主体，前脸凸出 1.0
T_TOP = 10.15                   # 塔身顶
T_CORN = 10.46                  # 塔檐口顶
BF_TOP = 12.40                  # 钟亭顶梁顶
SP_Z0, SP_Z1 = 12.52, 15.00     # 尖顶
POLE_Z = 15.30                  # 旗杆起点
FLAG_TOP = 16.10                # 旗顶

# 拱门
GATE_W, GATE_SPRING = 2.10, 3.07   # 拱顶 = 3.07 + 1.05 = 4.12

# ── 石台与广场 ───────────────────────────────────────────────────────────────
POD_X, POD_Y = 5.10, 4.78       # 石台：前缘 4.78（托住前突的塔）
POD_B = -3.90                   # 石台后缘
PLZ_X, PLZ_Y = 5.10, 9.80       # 广场范围（y 5.56–9.80）
G_BED, G_PLAZA = 0.34, 0.40     # 铺石底 / 铺石面
G_CURB = 0.46                   # 牙子顶
STEP_Y1 = 5.56                  # 台阶终点（广场从此开始）

# 阵营色标准件
SHIELD_W, SHIELD_H = 1.18, 1.42


# ── 通用构件 ─────────────────────────────────────────────────────────────────
def frame_ring(name, x0, x1, y0, y1, z0, z1, t, mat):
    """矩形环（墙裙 / 腰线 / 檐口）：45° 斜接，四角不留缺口、不叠同高面。"""
    ox = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    ix = [(x0 + t, y0 + t), (x1 - t, y0 + t), (x1 - t, y1 - t), (x0 + t, y1 - t)]
    verts = []
    for z in (z0, z1):
        verts += [(x, y, z) for (x, y) in ox]
        verts += [(x, y, z) for (x, y) in ix]
    faces = []
    for i in range(4):
        j = (i + 1) % 4
        faces += [(8 + i, 8 + j, 12 + j, 12 + i),   # 顶
                  (j, i, 4 + i, 4 + j),             # 底
                  (i, j, 8 + j, 8 + i),             # 外
                  (4 + j, 4 + i, 12 + i, 12 + j)]   # 内
    return mesh_obj(name, verts, faces, mat)


def arch_band_x(name, cy, cz, r_in, r_out, x0, x1, mat, segs=7):
    """朝 ±X 的半圆拱券石：拱在 YZ 平面，沿 X 从 x0 拉到 x1。

    bslib.arch_band 只做朝 ±Y 的拱；侧墙的拱窗直接套它会得到一块横躺的方墩
    （1.4 × 1.4 × 0.7，从侧墙里顶出来）—— 兵营的侧窗其实一直是这个错法，
    只是 RTS 距离看不出来。这里单独实现。
    """
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


def hip_shell(name, x0, x1, y0, y1, ze, zr, rx, t, mat):
    """四坡屋面板（封闭薄壳）：外坡面 + 内坡面 + 檐口侧面 + 屋脊面。

    薄壳是硬指标：檐口可见厚度 = t（0.18）。壳下面另放内缩的封闭阁楼体块挡视线。
    """
    outer = [(x0, y0, ze), (x1, y0, ze), (x1, y1, ze), (x0, y1, ze),
             (-rx, 0.0, zr), (rx, 0.0, zr)]
    inner = [(x, y, z - t) for (x, y, z) in outer]
    verts = outer + inner
    faces = [
        (0, 1, 5, 4), (2, 3, 4, 5), (1, 2, 5), (3, 0, 4),          # 外坡
        (6, 7, 11, 10), (8, 9, 10, 11), (7, 8, 11), (9, 6, 10),    # 内坡
        (0, 3, 9, 6), (1, 2, 8, 7), (2, 3, 9, 8), (3, 0, 6, 9),    # 檐口
        (4, 5, 11, 10),                                            # 屋脊
    ]
    return mesh_obj(name, verts, faces, mat)


class Model(BR.Model):
    """继承兵营的 Model：crest / emblem / kite / wallbanner / barrel / crate 原样复用。"""

    # ── 1. 石台 / 台阶 / 广场 ───────────────────────────────────────────────
    def base(self):
        M = self.M
        cy = (POD_Y + POD_B) * 0.5
        dy = POD_Y - POD_B
        self.add(box("plinth_c", (0, cy, 0.08), (POD_X * 2 + 0.36, dy + 0.36, 0.16),
                     M["stone_mid"]), 0.012)
        self.add(box("plinth_a", (0, cy, 0.36), (POD_X * 2, dy, 0.60), M["stone_dark"]), 0.024)
        self.add(box("plinth_cap", (0, cy, 0.665), (POD_X * 2 + 0.24, dy + 0.24, 0.11),
                     M["stone_mid"]), 0.012)
        # 门前三级踏步：广场 0.40 → 0.48 / 0.56 / 0.64 → 石台 0.72
        for i, (y0, y1, zt) in enumerate(((5.30, 5.56, 0.48),
                                          (5.04, 5.30, 0.56),
                                          (4.78, 5.04, 0.64))):
            self.add(box("step%d" % i, (0, (y0 + y1) * 0.5, zt * 0.5),
                         (3.60, y1 - y0, zt), M["stone_mid"]), 0.010)
        # 广场底座（深色缝）：一块实体，上面铺大石板，缝里露出 6 cm 底
        self.add(box("plaza_bed", (0, (STEP_Y1 + PLZ_Y) * 0.5, G_BED * 0.5),
                     (PLZ_X * 2, PLZ_Y - STEP_Y1, G_BED), M["earth_dark"]), 0.020)
        # 铺石：3 列 × 2 行；中列是仪仗道。缝加宽到 0.10，深色底露出来才读得清 
        cols = ((-3.15, 2.90, M["paving"]), (0.0, 3.30, M["stone_light"]),
                (3.15, 2.90, M["paving"]))
        rows = ((5.62, 7.62), (7.72, 9.72))
        for (cx, cw, mat) in cols:
            for (y0, y1) in rows:
                self.add(box("pave", (cx, (y0 + y1) * 0.5, 0.37),
                             (cw, y1 - y0, 0.060), mat), 0.0)
        # 广场石界：一圈 0.30 宽的深色石带，把铺石"框"起来（RTS 尺度全靠这条收边）
        for sgn in (-1, 1):
            self.add(box("pave_border", (sgn * 4.75, (STEP_Y1 + PLZ_Y) * 0.5, 0.372),
                         (0.30, PLZ_Y - STEP_Y1 - 0.10, 0.064), M["stone_dark"]), 0.0)
            self.add(box("pave_border_f", (0, PLZ_Y - 0.15, 0.372),
                         (PLZ_X * 2 - 1.00, 0.30, 0.064), M["stone_dark"]), 0.0)
        # 广场中心不放"徽盘"：十边石盘在 RTS 尺度读成一块井盖（试过，删掉更干净）。
        # 层次的活儿交给"深色石界 + 浅色仪仗道"两条线。
        # 三面石牙子：侧牙子做到 y 9.69，前牙子从 x 1.92 起 —— 转角只共边，不叠面
        for sgn in (-1, 1):
            self.add(box("curb_s", (sgn * (PLZ_X - 0.01), (STEP_Y1 + 9.69) * 0.5, G_CURB * 0.5),
                         (0.18, 9.69 - STEP_Y1, G_CURB), M["paving"]), 0.006)
            x0, x1 = sgn * 1.92, sgn * (PLZ_X + 0.08)
            self.add(box("curb_f", ((x0 + x1) * 0.5, PLZ_Y - 0.02, G_CURB * 0.5),
                         (abs(x1 - x0), 0.18, G_CURB), M["paving"]), 0.006)
        # 前沿落地：两级石阶（地面 0 → 广场 0.40）
        self.add(box("land0", (0, 10.20, 0.130), (3.80, 0.28, 0.26), M["stone_mid"]), 0.008)
        self.add(box("land1", (0, 10.48, 0.065), (3.96, 0.28, 0.13), M["stone_mid"]), 0.008)

    # ── 2. 主体 ─────────────────────────────────────────────────────────────
    def mass(self):
        M = self.M
        h = WALL_TOP - H0
        self.add(box("mass", (0, (YF + YB) * 0.5, H0 + h * 0.5),
                     (W2 * 2, YF - YB, h), M["stone_light"]), 0.036)
        # 墙裙 / 腰线 / 檐口：三个矩形环，45° 斜接，转角不留缺口也不叠面
        self.add(frame_ring("dado", -W2 - 0.075, W2 + 0.075, YB - 0.075, YF + 0.075,
                            H0, DADO, 0.095, M["stone_mid"]), 0.018)
        self.add(frame_ring("dado_cap", -W2 - 0.10, W2 + 0.10, YB - 0.10, YF + 0.10,
                            DADO - 0.05, DADO + 0.045, 0.12, M["stone_dark"]), 0.010)
        self.add(frame_ring("string", -W2 - 0.055, W2 + 0.055, YB - 0.055, YF + 0.055,
                            STR_Z - 0.08, STR_Z + 0.08, 0.075, M["stone_light"]), 0.010)
        self.add(frame_ring("cornice", -W2 - 0.18, W2 + 0.18, YB - 0.18, YF + 0.18,
                            WALL_TOP, CORN1, 0.20, M["stone_light"]), 0.016)
        self.add(frame_ring("cornice_lip", -W2 - 0.26, W2 + 0.26, YB - 0.26, YF + 0.26,
                            WALL_TOP - 0.10, WALL_TOP + 0.02, 0.28, M["stone_dark"]), 0.008)
        # 四角隅石：交错出挑，只在前 / 后两面做（侧墙有窗，做了会抢）
        for sx in (-1, 1):
            for (yface, sy) in ((YF, 1), (YB, -1)):
                for i in range(4):
                    zz = 1.98 + i * 0.86
                    self.add(box("quoin", (sx * (W2 - 0.26), yface - sy * 0.26, zz),
                                 (0.54 + (0.06 if i % 2 else 0.0), 0.54, 0.44),
                                 M["stone_mid"]), 0.010)

    # ── 3. 前突钟塔（塔身）──────────────────────────────────────────────────
    def tower_shaft(self):
        M = self.M
        self.add(box("tw_core", (0, (TY0 + 4.35) * 0.5, (H0 + T_TOP) * 0.5),
                     (TX * 2, 4.35 - TY0, T_TOP - H0), M["stone_light"]), 0.034)
        # 前脸薄板：中间挖拱门（左 / 右 / 拱上三块拼）
        dep, off = 0.25, 4.475
        gw = GATE_W * 0.5
        z_t = GATE_SPRING + gw
        self.add(extrude("tw_face_L", [(-TX, H0), (-gw, H0), (-gw, T_TOP), (-TX, T_TOP)],
                         "Y", dep, (0, 0), M["stone_light"], offset=off), 0.030)
        self.add(extrude("tw_face_R", [(gw, H0), (TX, H0), (TX, T_TOP), (gw, T_TOP)],
                         "Y", dep, (0, 0), M["stone_light"], offset=off), 0.030)
        top = [(-gw, z_t), (-gw, T_TOP), (gw, T_TOP), (gw, z_t)]
        for s in range(0, 9):
            a = math.pi * s / 8
            top.append((gw * math.cos(a), GATE_SPRING + gw * math.sin(a)))
        self.add(extrude("tw_face_T", top, "Y", dep, (0, 0), M["stone_light"], offset=off), 0.030)
        # 塔侧墙裙（前脸不做：门洞在正中间，横一条会切门）
        for sgn in (-1, 1):
            self.add(box("tw_dado_s", (sgn * TX, 4.10, (H0 + DADO) * 0.5),
                         (0.07, 1.00, DADO - H0), M["stone_mid"]), 0.018)
            self.add(box("tw_dado_s_cap", (sgn * TX, 4.10, DADO + 0.03),
                         (0.13, 1.06, 0.09), M["stone_dark"]), 0.008)
        # 塔腰线 / 塔身分节线（与主檐口同高，把塔身分成上下两段）
        self.add(frame_ring("tw_string", -TX - 0.05, TX + 0.05, 3.55, 4.65,
                            STR_Z - 0.08, STR_Z + 0.08, 0.07, M["stone_light"]), 0.010)

        self.add(frame_ring("tw_corn", -TX - 0.22, TX + 0.22, TY0 - 0.22, TY1 + 0.22,
                            T_TOP, T_CORN, 0.24, M["stone_light"]), 0.018)
        self.add(frame_ring("tw_corn_lip", -TX - 0.26, TX + 0.26, TY0 - 0.26, TY1 + 0.26,
                            T_CORN - 0.11, T_CORN - 0.01, 0.28, M["stone_dark"]), 0.008)

    # ── 4. 拱门 / 门扇 / 扇形窗 ─────────────────────────────────────────────
    def gate(self):
        M = self.M
        gw = GATE_W * 0.5
        # 门洞暖光：贴在塔核心前脸，从拱洞里透出来
        self.add(extrude("gate_glow", arch_profile(GATE_W - 0.08, 0.0, 8), "Y", 0.06,
                         (0, GATE_SPRING), M["glow"], offset=4.36), 0.0)
        # 拱券石 + 门套（凸出塔面 0.30）
        self.add(arch_band("gate_arch", 0.0, GATE_SPRING, gw, gw + 0.34,
                           4.60, 4.90, M["stone_light"], segs=10), 0.022)
        for sgn in (-1, 1):
            self.add(box("gate_jamb", (sgn * (gw + 0.17), 4.75, (H0 + GATE_SPRING) * 0.5),
                         (0.34, 0.30, GATE_SPRING - H0), M["stone_light"]), 0.020)
            self.add(box("gate_base", (sgn * (gw + 0.17), 4.77, H0 + 0.10),
                         (0.42, 0.34, 0.20), M["stone_mid"]), 0.008)
        # 双开门：阵营主色（正立面最亮的一块蓝）
        leaf = (GATE_W - 0.14) * 0.5
        for sgn in (-1, 1):
            cx = sgn * leaf * 0.5
            self.add(box("gate_leaf", (cx, 4.46, H0 + 1.14), (leaf, 0.09, 2.28),
                         M["team"]), 0.012)
            for zz in (H0 + 0.52, H0 + 1.62):
                self.add(box("gate_strap", (cx, 4.515, zz), (leaf - 0.10, 0.03, 0.10),
                             M["iron"]), 0.004)
            for (dx, dz) in ((0.22, 1.98), (0.22, 0.96), (-0.22, 1.98), (-0.22, 0.96)):
                self.add(box("gate_stud", (cx + dx, 4.517, H0 + dz), (0.055, 0.025, 0.055),
                             M["gold"]), 0.002)
            self.add(ring_y("gate_ring", (cx + sgn * 0.28, 4.494, H0 + 1.20), 0.045, 0.075,
                            0.035, 8, M["gold"]), 0.003)
        self.add(box("gate_seam", (0, 4.512, H0 + 1.14), (0.045, 0.02, 2.24),
                     M["wood_dark"]), 0.002)
        # 门楣 + 扇形窗铁艺
        self.add(box("gate_transom", (0, 4.49, H0 + 2.31), (GATE_W - 0.04, 0.11, 0.10),
                     M["wood_dark"]), 0.006)
        for dx in (-0.42, 0.0, 0.42):
            self.add(box("gate_bar", (dx, 4.44, H0 + 2.86), (0.05, 0.05, 0.96),
                         M["iron"]), 0.002)
        self.add(box("gate_bar2", (0, 4.44, H0 + 2.58), (1.86, 0.05, 0.05), M["iron"]), 0.002)

    # ── 5. 钟面 ─────────────────────────────────────────────────────────────
    def clock(self):
        M = self.M
        cz = 7.05
        # 金圈 + 深盘：钟面在浅石墙上必须靠"金圈"才能读出来（第一版石圈直接糊进墙里）
        self.add(ring_y("clock_ring", (0, 4.66, cz), 0.50, 0.66, 0.18, 12, M["gold"]), 0.010)
        self.add(cyl("clock_face", (0, 4.67, cz), 0.51, 0.10, 12, M["coal"], axis="Y"), 0.004)
        for k in range(4):
            a = TAU * k / 4
            self.add(box("clock_tick", (math.sin(a) * 0.38, 4.735, cz + math.cos(a) * 0.38),
                         (0.065, 0.03, 0.065), M["gold"], rot=(0, -a, 0)), 0.002)
        # 指针 10:10
        for (ang, ln, w) in ((math.radians(-52), 0.34, 0.060), (math.radians(28), 0.24, 0.050)):
            hx = math.sin(ang) * ln * 0.5
            hz = math.cos(ang) * ln * 0.5
            self.add(box("clock_hand", (hx, 4.745, cz + hz), (w, 0.03, ln), M["gold"],
                         rot=(0, -ang, 0)), 0.002)

    # ── 6. 钟亭 + 尖顶 + 旗帜 ───────────────────────────────────────────────
    def belfry(self):
        M = self.M
        cy = (TY0 + TY1) * 0.5
        w, d = 1.30, 0.975
        self.add(box("bf_podium", (0, cy, (T_CORN + 10.70) * 0.5), (w * 2 + 0.16, d * 2 + 0.16, 0.30),
                     M["stone_mid"]), 0.012)
        for sx in (-1, 1):
            for sy in (-1, 1):
                self.add(box("bf_post", (sx * (w - 0.15), cy + sy * (d - 0.15),
                                         (10.70 + BF_TOP - 0.06) * 0.5),
                             (0.30, 0.30, BF_TOP - 10.76), M["stone_light"]), 0.014)
        for sy in (-1, 1):
            self.add(box("bf_sill", (0, cy + sy * (d - 0.15), 10.82), (w * 2 - 0.30, 0.30, 0.24),
                         M["stone_mid"]), 0.010)
        for sx in (-1, 1):
            self.add(box("bf_sill_s", (sx * (w - 0.15), cy, 10.82), (0.30, d * 2 - 0.60, 0.24),
                         M["stone_mid"]), 0.010)
        for sy in (-1, 1):
            self.add(box("bf_beam", (0, cy + sy * (d - 0.15), BF_TOP - 0.16), (w * 2, 0.30, 0.32),
                         M["stone_light"]), 0.012)
        for sx in (-1, 1):
            self.add(box("bf_beam_s", (sx * (w - 0.15), cy, BF_TOP - 0.16), (0.30, d * 2 - 0.90, 0.32),
                         M["stone_light"]), 0.012)
        # 斜撑：把方口读成"拱口"（不画曲线）
        for sy in (-1, 1):
            for sx in (-1, 1):
                self.add(beam("bf_brace", (sx * (w - 0.62), cy + sy * (d - 0.15), BF_TOP - 0.32),
                              (sx * (w - 0.15), cy + sy * (d - 0.15), BF_TOP - 0.88),
                              0.13, 0.10, M["stone_mid"]), 0.005)
        # 钟：八边回转体（零球体）
        # 钟放大到 0.84 口宽：0.6 的钟在 30 m 外只是一个金点，读不出"这是钟"
        self.add(revolve("bf_bell", [(0.42, 0.0), (0.40, 0.07), (0.29, 0.34), (0.19, 0.56),
                                     (0.13, 0.68), (0.0, 0.72)], 8,
                         (0, cy, 11.02), M["gold"]), 0.008)
        self.add(box("bf_bell_yoke", (0, cy, 11.82), (0.12, 0.12, 0.40), M["iron"]), 0.003)
        self.add(box("bf_cap0", (0, cy, BF_TOP + 0.10), (w * 2 + 0.26, d * 2 + 0.26, 0.20),
                     M["stone_light"]), 0.012)
        self.add(box("bf_cap1", (0, cy, BF_TOP + 0.26), (w * 2 + 0.38, d * 2 + 0.38, 0.12),
                     M["stone_dark"]), 0.008)
        # 尖顶：四坡锥台（硬边，不磨圆）
        self.add(frustum("bf_spire", SP_Z0, SP_Z1, 3.24, 2.52, 0.10, 0.09, 0, cy, M["roof"]), 0.020)
        self.add(box("bf_spire_base", (0, cy, SP_Z0 + 0.04), (3.34, 2.62, 0.10), M["roof_edge"]), 0.006)
        for sx in (-1, 1):
            for sy in (-1, 1):
                self.add(beam("bf_spire_hip", (sx * 1.60, cy + sy * 1.24, SP_Z0 + 0.05),
                              (sx * 0.05, cy + sy * 0.04, SP_Z1), 0.10, 0.07,
                              M["roof_edge"]), 0.004)
        for (zz, sc) in ((13.10, 0.78), (13.80, 0.53), (14.45, 0.30)):
            self.add(box("bf_spire_ring", (0, cy, zz), (3.24 * sc + 0.06, 2.52 * sc + 0.06, 0.06),
                         M["roof_edge"]), 0.003)
        # 金顶 + 旗杆 + 联盟旗
        self.add(revolve("bf_finial", [(0.0, 0.0), (0.10, 0.02), (0.135, 0.12), (0.07, 0.26),
                                       (0.0, 0.36)], 8, (0, cy, SP_Z1), M["gold"]), 0.0, 1)
        self.add(revolve("bf_flagpole", [(0.045, 0.0), (0.038, FLAG_TOP - POLE_Z)], 6,
                         (0, cy, POLE_Z), M["wood_dark"]), 0.0, 1)
        self.add(revolve("bf_flagtip", [(0.070, 0.0), (0.050, 0.05), (0.018, 0.11)], 8,
                         (0, cy, FLAG_TOP - 0.02), M["gold"]), 0.0, 1)
        fw, fh = 1.32, 0.86
        prof = [(0.0, 0.0), (fw, -0.10), (fw * 0.80, -fh * 0.50), (fw, -fh * 0.90), (0.0, -fh)]
        self.add(extrude("bf_flag_cloth", prof, "Y", 0.035, (0.0, FLAG_TOP - 0.06),
                         M["team"], offset=cy), 0.004)
        self.add(box("bf_flag_hoist", (0.035, cy, FLAG_TOP - 0.06 - fh * 0.46), (0.09, 0.06, fh * 0.92),
                     M["team_trim"]), 0.003)
        self.crest("bf_flag_crest", "Y", 0.57, cy + 0.0125, FLAG_TOP - 0.66, 0.44)

    # ── 7. 屋面板 / 瓦垄 / 椽头 ─────────────────────────────────────────────
    def roof(self):
        M = self.M
        ze, zr = EAVE_Z, RIDGE_Z
        self.add(hip_shell("roof_shell", -AX, AX, -AY, AY, ze, zr, RX, ROOF_T, M["roof"]), 0.0)
        # 内缩阁楼体块：挡住从檐口看进去的视线
        self.add(box("attic_a", (0, 0, (8.05 + 9.15) * 0.5), (7.20, 5.20, 9.15 - 8.05),
                     M["stone_dark"]), 0.0)
        self.add(box("attic_b", (0, 0, (9.10 + 10.10) * 0.5), (4.20, 2.40, 1.00),
                     M["stone_dark"]), 0.0)
        # 封檐板：X 向通长，Y 向缩短（转角不叠同高面）
        self.add(box("eave_f", (0, AY, ze - 0.10), (AX * 2 + 0.16, 0.14, 0.24), M["roof_edge"]), 0.006)
        self.add(box("eave_b", (0, -AY, ze - 0.10), (AX * 2 + 0.16, 0.14, 0.24), M["roof_edge"]), 0.006)
        for sgn in (-1, 1):
            self.add(box("eave_s", (sgn * AX, 0, ze - 0.10), (0.14, AY * 2 - 0.28, 0.24),
                         M["roof_edge"]), 0.006)
        self.add(box("ridge_cap", (0, 0, zr + 0.03), (RX * 2 + 0.34, 0.26, 0.17),
                     M["roof_edge"]), 0.006)
        for sx in (-1, 1):
            for sy in (-1, 1):
                self.add(beam("hip_ridge", (sx * (AX - 0.04), sy * (AY - 0.04), ze + 0.04),
                              (sx * (RX + 0.02), sy * 0.02, zr + 0.03),
                              0.19, 0.12, M["roof_edge"]), 0.004)
        # 通长瓦垄：每坡 8 / 4 道，中心线压在屋面上（埋一半）。
        # 第一版 0.055 高在 RTS 距离只有 1 px，整片屋面读成一块黑板 —— 加高到 0.09。
        for x in (-4.55, -3.75, -2.95, -2.15, 2.15, 2.95, 3.75, 4.55):
            y0 = AY * (abs(x) - RX) / (AX - RX)
            for sy in (1, -1):
                self.add(beam("tile", (x, sy * (y0 + 0.12), ze + (zr - ze) * (1 - (y0 + 0.12) / AY)),
                              (x, sy * (AY - 0.10), ze + (zr - ze) * (1 - (AY - 0.10) / AY)),
                              0.10, 0.09, M["roof"]), 0.0)
        for y in (0.90, 2.05, 3.20):
            for sy in (1, -1):
                yy = sy * y
                x1 = RX + (AX - RX) * abs(yy) / AY
                for sx in (1, -1):
                    self.add(beam("tile_s", (sx * (AX - 0.10), yy, ze + (zr - ze) * 0.10 / (AX - RX)),
                                  (sx * (x1 + 0.04), yy, ze + (zr - ze) * (AX - x1) / (AX - RX)),
                                  0.10, 0.09, M["roof"]), 0.0)
        # 露明椽头：从前墙外皮挑到封檐板
        for x in (-4.30, -3.58, -2.86, -2.06, 2.06, 2.86, 3.58, 4.30):
            self.add(beam("rafter", (x, 3.64, 8.57), (x, 4.12, 8.19), 0.085, 0.085,
                          M["wood_dark"]), 0.004)

    # ── 7.5 老虎窗：**不做** ────────────────────────────────────────────────
    # 试过两版：1.24 m 宽的老虎窗在这套 1:100 的体量上，3/4 视角里只读成
    # 两个灰色方盒（像烟囱），窗洞不到 15 px —— 读不出语义的细节是负资产。
    # 屋面靠"通长瓦垄 + 四条戗脊 + 深色封檐"三层线脚撑住，和兵营的平顶一个道理。

    # ── 8. 窗 ───────────────────────────────────────────────────────────────
    def windows(self):
        M = self.M
        for x in (-3.22, 3.22):
            self.arch_win("win_f", (x, YF + 0.03, 1.90), 1.15, 1.30, "Y")
        for sx in (-1, 1):
            for yy in (-1.55, 1.55):
                self.arch_win("win_s", (sx * (W2 + 0.01), yy, 1.90), 1.15, 1.30, "X", out=sx)
        for x in (-2.70, 2.70):
            self.arch_win("win_b", (x, YB - 0.03, 1.90), 1.15, 1.30, "Y", out=-1)
        self.win2("win2_f", (-3.22, YF + 0.19, 6.70), 0.98, 1.95)
        self.win2("win2_f", (3.22, YF + 0.19, 6.70), 0.98, 1.95, mat=M["glow"], tag="_lit")
        for x in (-3.22, 3.22):
            self.shutters("shut_f", (x, YF + 0.045, 6.70), 0.98, 1.95, "Y")
        for sx in (-1, 1):
            for yy in (-1.55, 1.55):
                self.add(box("win2s", (sx * (W2 + 0.02), yy, 6.70), (0.10, 0.95, 1.95),
                             M["glass"]))
                for k in (-1, 1):
                    self.add(box("win2s_fL", (sx * (W2 + 0.06), yy + k * 0.545, 6.70),
                                 (0.14, 0.15, 2.20), M["stone_light"]), 0.008)
                    self.add(box("win2s_fT", (sx * (W2 + 0.06), yy, 6.70 + k * 1.045),
                                 (0.14, 1.24, 0.14), M["stone_light"]), 0.008)
                self.add(box("win2s_bar", (sx * (W2 + 0.08), yy, 6.70), (0.05, 0.05, 1.95),
                             M["wood_dark"]), 0.003)
                self.add(box("win2s_sill", (sx * (W2 + 0.07), yy, 5.66), (0.20, 1.24, 0.10),
                             M["stone_light"]), 0.006)
                self.shutters("shut_s", (sx * (W2 + 0.045), yy, 6.70), 0.95, 1.95, "X", out=sx)
        for x in (-2.70, 0.0, 2.70):
            self.win2("win2_b", (x, YB - 0.19, 6.70), 0.98, 1.95)
            self.shutters("shut_b", (x, YB - 0.045, 6.70), 0.98, 1.95, "Y", out=-1)

    def arch_win(self, name, center, w, h, face, out=1, mat=None):
        """一层半圆拱窗：玻璃 + 拱券石 + 两侧窗套 + 中梃 + 窗台。cz = 窗底。"""
        M = self.M
        mat = M["glass"] if mat is None else mat
        cx, cy, cz = center
        hw = w * 0.5
        straight = h - hw
        if face == "Y":
            self.add(extrude(name, arch_profile(w, straight, segs=6), "Y", 0.10, (cx, cz),
                             mat, offset=cy), 0.0)
            self.add(arch_band(name + "_arch", cx, cz + straight, hw, hw + 0.15,
                               cy + out * 0.03, cy + out * 0.13, M["stone_light"], segs=6), 0.010)
            for sgn in (-1, 1):
                self.add(box(name + "_jamb", (cx + sgn * (hw + 0.07), cy + out * 0.07,
                                              cz + straight * 0.5),
                             (0.14, 0.14, straight), M["stone_light"]), 0.008)
            self.add(box(name + "_bar", (cx, cy + out * 0.08, cz + straight * 0.5),
                         (0.05, 0.06, straight), M["wood_dark"]), 0.003)
            self.add(box(name + "_sill", (cx, cy + out * 0.06, cz - 0.06),
                         (w + 0.30, 0.22, 0.10), M["stone_light"]), 0.008)
        else:
            self.add(extrude(name, arch_profile(w, straight, segs=6), "X", 0.10, (cy, cz),
                             mat, offset=cx + out * 0.01), 0.0)
            self.add(arch_band_x(name + "_arch", cy, cz + straight, hw, hw + 0.15,
                                 cx + out * 0.03, cx + out * 0.13, M["stone_light"], segs=6), 0.010)
            for sgn in (-1, 1):
                self.add(box(name + "_jamb", (cx + out * 0.07, cy + sgn * (hw + 0.07),
                                              cz + straight * 0.5),
                             (0.14, 0.14, straight), M["stone_light"]), 0.008)
            self.add(box(name + "_bar", (cx + out * 0.08, cy, cz + straight * 0.5),
                         (0.06, 0.05, straight), M["wood_dark"]), 0.003)
            self.add(box(name + "_sill", (cx + out * 0.06, cy, cz - 0.06),
                         (0.22, w + 0.30, 0.10), M["stone_light"]), 0.008)

    def shutters(self, name, center, w, h, face, out=1):
        """二层窗两侧的木百叶（关着）。

        上半段如果全是石材，摆到兵营 / 铁匠铺旁边就"冷"了一档 —— 另两座都有一大片
        暖木（兵营的二层木构、铁匠铺的坡棚）。这里用 0.24 m 宽的百叶补一条竖向的木色
        节奏，不引入新的构件语言。
        """
        M = self.M
        cx, cy, cz = center
        for sgn in (-1, 1):
            if face == "Y":
                self.add(box(name, (cx + sgn * (w * 0.5 + 0.30), cy + out * 0.02, cz),
                             (0.24, 0.07, h * 0.92), M["wood_dark"]), 0.008)
            else:
                self.add(box(name, (cx + out * 0.02, cy + sgn * (w * 0.5 + 0.30), cz),
                             (0.07, 0.24, h * 0.92), M["wood_dark"]), 0.008)

    def win2(self, name, center, w, h, mat=None, tag=""):
        """二层高窗：玻璃 + 石窗套 + 中梃 + 横档 + 窗台。"""
        M = self.M
        mat = M["glass"] if mat is None else mat
        cx, cy, cz = center
        self.add(box(name + tag, (cx, cy, cz), (w, 0.10, h), mat))
        for sgn in (-1, 1):
            self.add(box(name + "_fL", (cx + sgn * (w * 0.5 + 0.075), cy + 0.055, cz),
                         (0.15, 0.16, h + 0.30), M["stone_light"]), 0.008)
            self.add(box(name + "_fT", (cx, cy + 0.055, cz + sgn * (h * 0.5 + 0.08)),
                         (w + 0.30, 0.16, 0.15), M["stone_light"]), 0.008)
        self.add(box(name + "_bar", (cx, cy + 0.14, cz), (0.055, 0.05, h + 0.02),
                     M["wood_dark"]), 0.003)
        self.add(box(name + "_bar2", (cx, cy + 0.14, cz + h * 0.16), (w + 0.02, 0.05, 0.055),
                     M["wood_dark"]), 0.003)
        self.add(box(name + "_sill", (cx, cy + 0.07, cz - h * 0.5 - 0.09), (w + 0.40, 0.22, 0.11),
                     M["stone_light"]), 0.008)

    # ── 9. 阵营色带 / 盾 / 垂旗 ─────────────────────────────────────────────
    def heraldry(self):
        M = self.M
        BH = B1 - B0
        # 主楼色带：一个环（塔前面那 3.1 m 被塔挡住，看不见）
        self.add(frame_ring("band_m", -W2 - 0.065, W2 + 0.065, YB - 0.065, YF + 0.065,
                            B0, B1, 0.085, M["team"]), 0.010)
        self.add(frame_ring("band_m_t", -W2 - 0.085, W2 + 0.085, YB - 0.085, YF + 0.085,
                            B1 - 0.055, B1 + 0.025, 0.105, M["team_trim"]), 0.004)
        # 塔身色带：正面 + 两侧（两侧从主楼色带外皮起步，接缝在 3.735）
        self.add(box("band_t_f", (0, 4.665, (B0 + B1) * 0.5), (TX * 2 + 0.14, 0.13, BH),
                     M["team"]), 0.010)
        self.add(box("band_t_f_t", (0, 4.685, B1 - 0.015), (TX * 2 + 0.16, 0.15, 0.085),
                     M["team_trim"]), 0.004)
        for sgn in (-1, 1):
            self.add(box("band_t_s", (sgn * TX, (3.735 + TY1) * 0.5, (B0 + B1) * 0.5),
                         (0.13, TY1 - 3.735, BH), M["team"]), 0.010)
            self.add(box("band_t_s_t", (sgn * TX, (3.735 + TY1) * 0.5, B1 - 0.015),
                         (0.15, TY1 - 3.735, 0.085), M["team_trim"]), 0.004)
        # 塔顶一圈窄色带（把视线再往上带一级）
        self.add(box("band_tw_top", (0, (TY0 + TY1) * 0.5, 9.66),
                     (TX * 2 + 0.12, TY1 - TY0 + 0.10, 0.36), M["team"]), 0.010)
        self.add(box("band_tw_top_t", (0, (TY0 + TY1) * 0.5, 9.8775),
                     (TX * 2 + 0.14, TY1 - TY0 + 0.12, 0.075), M["team_trim"]), 0.004)
        # 门楣盾（压在色带上）：做大到 1.40 × 1.66，才不会被同色的色带吃掉轮廓
        self.kite("shield_gate", (0.0, 4.66, 5.06), "Y", 1.40, 1.66)
        # 侧墙垂旗：落在两扇窗之间的 2.1 m 空档里
        for sx, tag in ((-1, "L"), (1, "R")):
            self.wallbanner("wbanner_s" + tag, (sx * (W2 + 0.30), 0.0, 6.35), "X", 1.50, 1.88)

    # ── 10. 广场陈设（基地感，只放读得懂的）────────────────────────────────
    def props(self):
        M = self.M
        z = G_PLAZA
        # 公告板
        bx, by = -3.55, 6.85
        for sgn in (-1, 1):
            self.add(box("board_post", (bx + sgn * 0.82, by, z + 0.78), (0.16, 0.16, 1.56),
                         M["wood_dark"]), 0.008)
        self.add(box("board_face", (bx, by, z + 1.12), (1.78, 0.11, 0.98), M["wood_warm"],
                     rot=(-0.14, 0, 0)), 0.010)
        self.add(box("board_trim", (bx, by, z + 1.62), (1.94, 0.16, 0.11), M["wood_dark"],
                     rot=(-0.14, 0, 0)), 0.006)
        self.add(box("board_foot", (bx, by + 0.06, z + 0.06), (2.02, 0.34, 0.12), M["stone_mid"]), 0.006)
        for (dx, dz, w, h) in ((-0.50, 0.10, 0.34, 0.42), (0.06, 0.02, 0.30, 0.34),
                               (0.50, 0.12, 0.32, 0.38)):
            self.add(box("board_note", (bx + dx, by + 0.068, z + 1.12 + dz),
                         (w, 0.018, h), M["paving"], rot=(-0.14, 0, 0)), 0.002)
        # 长凳不做：RTS 尺度上只是一块棕色板，和木箱撞造型（"简洁不杂乱"）
        # 火盆一对
        for sgn in (-1, 1):
            px = sgn * 2.62
            self.add(box("braz_ped", (px, 5.98, z + 0.36), (0.46, 0.46, 0.72), M["stone_mid"]), 0.010)
            self.add(box("braz_ped_t", (px, 5.98, z + 0.75), (0.54, 0.54, 0.08), M["stone_dark"]), 0.006)
            # 盆口 1.19、盆底沉进压顶 1.5 cm、炭面 1.43 —— 三层高度都不共面
            self.add(revolve("braz_bowl", [(0.16, 0.0), (0.30, 0.10), (0.34, 0.24), (0.32, 0.26)],
                             8, (px, 5.98, z + 0.775), M["iron"]), 0.008)
            self.add(revolve("braz_coal", [(0.0, 0.0), (0.26, 0.02), (0.26, 0.09), (0.0, 0.10)],
                             8, (px, 5.98, z + 1.03), M["coal"]), 0.004)
            # lathe 的 z 是**绝对于地面**，不是相对火盆的偏移（第一版忘了加 z，火焰长在地上）
            self.add(lathe("braz_flame", [(0.0, z + 1.05, px, 5.98), (0.17, z + 1.11, px, 5.98),
                                          (0.12, z + 1.31, px + 0.02, 5.98),
                                          (0.0, z + 1.49, px + 0.04, 5.98)],
                           6, M["flame_out"]), 0.0)
            self.add(lathe("braz_core", [(0.0, z + 1.05, px, 5.98), (0.09, z + 1.10, px, 5.98),
                                         (0.05, z + 1.27, px + 0.01, 5.98),
                                         (0.0, z + 1.37, px + 0.02, 5.98)],
                           6, M["flame_in"]), 0.0)
        # 木桶 / 木箱：贴着右侧墙根（避开 0.30 宽的广场石界，桶底不能压到石界上）
        self.barrel("barrel_a", (4.24, 5.72), 0.32, 0.74, z)
        self.barrel("barrel_b", (3.80, 5.62), 0.29, 0.66, z)
        self.crate("crate_a", (4.24, 6.52), 0.62, 0.56, z)
        # 两支旗杆：压在广场前角，框住入口
        for sgn in (-1, 1):
            px, py = sgn * 4.32, 9.05
            self.add(box("banner_pole_base", (px, py, z + 0.11), (0.46, 0.46, 0.22),
                         M["stone_mid"]), 0.008)
            self.add(revolve("banner_pole", [(0.075, 0.0), (0.060, 3.05)], 8,
                             (px, py, z + 0.18), M["wood_dark"]), 0.0, 1)
            self.add(revolve("banner_pole_tip", [(0.105, 0.0), (0.070, 0.07), (0.02, 0.15)], 8,
                             (px, py, z + 3.22), M["gold"]), 0.0, 1)
            self.add(box("banner_arm", (px - sgn * 0.40, py, z + 3.02), (0.86, 0.07, 0.07),
                         M["wood_dark"]), 0.004)
            self.add(box("banner_cloth", (px - sgn * 0.46, py, z + 2.38), (0.66, 0.05, 1.24),
                         M["team"]), 0.006)
            self.add(box("banner_trim", (px - sgn * 0.46, py, z + 1.80), (0.68, 0.07, 0.08),
                         M["team_trim"]), 0.003)
            for k in (-1, 1):
                self.add(box("banner_ring", (px - sgn * 0.46 + k * 0.24, py, z + 2.99),
                             (0.05, 0.05, 0.09), M["iron"]), 0.002)

    # ── 11. 组装 / 收尾 ─────────────────────────────────────────────────────
    def build(self):
        for step in (self.base, self.mass, self.tower_shaft, self.gate, self.clock,
                     self.windows, self.roof, self.belfry,
                     self.heraldry, self.props):
            step()
        return self

    def finalize(self, bevel=True):
        for (ob, bev, sub, seg) in self.items:
            co = ob.data.vertices
            dims = [max(v.co[i] for v in co) - min(v.co[i] for v in co) for i in range(3)]
            vol = dims[0] * dims[1] * dims[2]
            chunky = min(dims) >= 0.10 and vol >= 0.12
            if self.smooth:
                L.finalize(ob, bevel=max(bev, 0.010), seg=1, sub=1 if chunky else 0, flat=False)
            else:
                b = 0.0 if (not bevel or max(dims) < 1.20 or bev < 0.008) else bev
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
