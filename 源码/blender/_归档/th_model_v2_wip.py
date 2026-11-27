"""
th_model.py —— 城镇大厅（Town Hall）v2 · 主楼 + 钟楼 + 附楼（同一主体）

v2 针对三条反馈重做形体（v1 的代码留档在 `th_model_v1.py`）：

  ① **入口不再向前突出一块**：v1 的钟塔楼台凸出 1.0 m、又接一块独立门廊台，
     读起来像兵营的训练场。v2 把塔压回墙面（只凸 15 mm，属石作上的凸缝），
     入口是墙上的拱门（0.25 m 凹进的门洞）+ 三级踏步，没有外挂体块。
  ② **主楼 + 钟楼 + 附楼，但是一整个主体**：平面是一块 11.0 × 6.4 的矩形，
     附楼与主楼**共用外墙**，只靠屋顶在 5.3 m 处断开、主楼再往上长到 8.35。
     腰线 / 墙裙 / 阵营色带都环着整块平面走一圈 —— 一条腰带把三段绑成一个主体。
  ③ **屋面改成朝前的陡山墙**：v1 的四坡大金字塔 + 细尖顶读成教堂、也没有职责。
     v2 主楼是**山墙面朝前**的双坡屋面（脊沿 Y），三角山墙朝天、钟楼压在三角形正中；
     两翼是低矮的四坡顶；钟楼按"钟面层 + 露台女儿墙 + 四角柱 + 低锥顶"收头，
     职责写在钟面上（三面钟），不再用空钟亭 + 长尖顶。

坐标：X 右、Y 前（+Y = 正面）、Z 上；原点在占地中心，z = 0 地面。
交付前整体沿 X 镜像一次。徽记 / 旗帜 / 木桶木箱继承 `br_model.Model`（同一段几何）。
"""
import math
from math import tau as TAU

import bpy

import bslib as L
import br_model as BR
from bslib import (arch_band, beam, box, cone, cyl, extrude, frustum, lathe,
                   mesh_obj, revolve, ring_y, tube_band)
from br_model import arch_profile, mirror_x, out_sign, vcyl

# ── 平面与标高 ───────────────────────────────────────────────────────────────
W2 = 5.50                       # 总半宽（11.0）
W2C = 3.60                      # 主楼半宽（7.2）
YF, YB = 3.20, -3.20            # 6.4 进深
H0 = 0.72                       # 建筑地面（石台顶）
DADO = 1.62                     # 墙裙顶
STR_Z = 4.28                    # 腰线
B0, B1 = 4.50, 5.18             # 阵营色带（贯穿主楼与附楼的一条腰带）
WALL_W = 5.30                   # 附楼墙顶
CORN_W = 5.44                   # 附楼檐口顶
EAVE_W = 5.45                   # 附楼屋面檐口
RIDGE_W = 6.20                  # 附楼屋脊（与主坡同坡度）
WALL_C = 8.35                   # 主楼墙顶
CORN_C = 8.55                   # 主楼檐口顶
EAVE_C = 8.55                   # 主楼屋面檐口
RIDGE_C = 11.55                 # 主楼屋脊
ROOF_T = 0.18
AX_C = W2C + 0.45               # 主楼檐口半宽（出檐 0.45）

# ── 钟楼 ─────────────────────────────────────────────────────────────────────
TX = 1.70                       # 塔半宽（3.4）
TY0, TY1 = 0.40, 3.48           # 塔进深；前脸凸出墙面 0.28（一个墙厚，不是门廊）
T_CORE_Y = 2.96                 # 塔芯前脸（门洞凹进的底）
T_TOP = 11.20
T_CORN = 11.53
CLK0, CLK1 = 11.53, 13.40       # 钟面层（钟心抬到屋脊之上）
PARA1 = 13.73                   # 露台女儿墙顶
SP_Z0, SP_Z1 = 13.73, 15.20
POLE_Z = 15.22
FLAG_TOP = 16.20

GATE_W, GATE_SPRING = 2.00, 3.10   # 拱顶 = 3.10 + 1.0 = 4.10（外沿 4.36，避开 4.50 的腰带）

# ── 石台与广场 ───────────────────────────────────────────────────────────────
POD_X, POD_YF, POD_YB = 5.62, 4.10, -3.45
PLZ_Y = 9.80
G_BED, G_PLAZA, G_CURB = 0.34, 0.40, 0.46
STEP_Y1 = 4.90

SHIELD_W, SHIELD_H = 1.00, 1.18


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
        faces += [(8 + i, 8 + j, 12 + j, 12 + i),
                  (j, i, 4 + i, 4 + j),
                  (i, j, 8 + j, 8 + i),
                  (4 + j, 4 + i, 12 + i, 12 + j)]
    return mesh_obj(name, verts, faces, mat)


def arch_band_x(name, cy, cz, r_in, r_out, x0, x1, mat, segs=7):
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


def slope_slab(name, p0, p1, y0, y1, t, mat):
    """沿 (x,z) 两点之间的斜板，Y 向从 y0 到 y1 —— 山墙屋面的两片。"""
    (x0, z0), (x1, z1) = p0, p1
    dx, dz = x1 - x0, z1 - z0
    ln = math.hypot(dx, dz)
    nx, nz = -dz / ln, dx / ln
    if nz < 0:
        nx, nz = -nx, -nz
    ox, oz = nx * t * 0.5, nz * t * 0.5
    verts = []
    for (x, z) in ((x0, z0), (x1, z1)):
        for yy in (y0, y1):
            verts += [(x - ox, yy, z - oz), (x + ox, yy, z + oz)]
    faces = [(1, 3, 7, 5), (0, 4, 6, 2), (0, 1, 5, 4),
             (2, 6, 7, 3), (0, 2, 3, 1), (4, 5, 7, 6)]
    return mesh_obj(name, verts, faces, mat)


def hip_shell_y(name, x0, x1, y0, y1, ze, zr, ry, t, mat):
    """四坡屋面板（脊沿 Y，附楼用）：外坡 + 内坡 + 檐口 + 脊面。"""
    cx = (x0 + x1) * 0.5
    outer = [(x0, y0, ze), (x1, y0, ze), (x1, y1, ze), (x0, y1, ze),
             (cx, y0 + ry, zr), (cx, y1 - ry, zr)]
    inner = [(x, y, z - t) for (x, y, z) in outer]
    verts = outer + inner
    faces = [(0, 1, 4), (2, 3, 5), (0, 3, 5, 4), (1, 2, 5, 4),
             (6, 7, 10), (8, 9, 11), (6, 10, 11, 9), (7, 8, 11, 10),
             (0, 1, 7, 6), (1, 2, 8, 7), (2, 3, 9, 8), (3, 0, 6, 9),
             (4, 5, 11, 10)]
    return mesh_obj(name, verts, faces, mat)


class Model(BR.Model):
    # ── 1. 石台 / 台阶 / 广场 ───────────────────────────────────────────────
    def base(self):
        M = self.M
        cy = (POD_YF + POD_YB) * 0.5
        dy = POD_YF - POD_YB
        self.add(box("plinth_c", (0, cy, 0.08), (POD_X * 2 + 0.36, dy + 0.36, 0.16),
                     M["stone_mid"]), 0.012)
        self.add(box("plinth_a", (0, cy, 0.36), (POD_X * 2, dy, 0.60), M["stone_dark"]), 0.024)
        self.add(box("plinth_cap", (0, cy, 0.665), (POD_X * 2 + 0.24, dy + 0.24, 0.11),
                     M["stone_mid"]), 0.012)
        # 门前三级踏步：广场 0.40 → 0.48 / 0.56 / 0.64 → 石台 0.72
        for i, (y0, y1, zt) in enumerate(((4.63, 4.90, 0.48),
                                          (4.36, 4.63, 0.56),
                                          (4.09, 4.36, 0.64))):
            self.add(box("step%d" % i, (0, (y0 + y1) * 0.5, zt * 0.5),
                         (3.60, y1 - y0, zt), M["stone_mid"]), 0.010)
        # 广场
        self.add(box("plaza_bed", (0, (STEP_Y1 + PLZ_Y) * 0.5, G_BED * 0.5),
                     (POD_X * 2, PLZ_Y - STEP_Y1, G_BED), M["earth_dark"]), 0.020)
        cols = ((-3.51, 3.22, M["paving"]), (0.0, 3.60, M["stone_light"]),
                (3.51, 3.22, M["paving"]))
        rows = ((4.98, 7.18), (7.28, 9.56))
        for (cx, cw, mat) in cols:
            for (y0, y1) in rows:
                self.add(box("pave", (cx, (y0 + y1) * 0.5, 0.37),
                             (cw, y1 - y0, 0.060), mat), 0.0)
        for sgn in (-1, 1):
            self.add(box("pave_border", (sgn * 5.28, (STEP_Y1 + 9.69) * 0.5, 0.372),
                         (0.30, 9.69 - STEP_Y1, 0.064), M["stone_dark"]), 0.0)
            x0, x1 = sgn * 1.92, sgn * 5.13
            self.add(box("pave_border_f", ((x0 + x1) * 0.5, PLZ_Y - 0.17, 0.372),
                         (abs(x1 - x0), 0.30, 0.064), M["stone_dark"]), 0.0)
        for sgn in (-1, 1):
            self.add(box("curb_s", (sgn * (POD_X - 0.01), (STEP_Y1 + 9.69) * 0.5, G_CURB * 0.5),
                         (0.18, 9.69 - STEP_Y1, G_CURB), M["paving"]), 0.006)
            x0, x1 = sgn * 1.92, sgn * (POD_X + 0.08)
            self.add(box("curb_f", ((x0 + x1) * 0.5, PLZ_Y - 0.02, G_CURB * 0.5),
                         (abs(x1 - x0), 0.18, G_CURB), M["paving"]), 0.006)
        self.add(box("land0", (0, 10.20, 0.130), (3.80, 0.28, 0.26), M["stone_mid"]), 0.008)
        self.add(box("land1", (0, 10.48, 0.065), (3.96, 0.28, 0.13), M["stone_mid"]), 0.008)

    def band_split(self, name, z0, z1, out, mat, gap):
        """前脸断开的水平线脚：门洞 / 塔身处让开，其余三面照旧。

        四段各走各的，转角只共边不叠面（左右两段压住前角，背段压住后角）。
        """
        h = z1 - z0
        for sx in (-1, 1):
            x0, x1 = sx * gap, sx * (W2 + out)
            self.add(box(name + "_f", ((x0 + x1) * 0.5, YF + out * 0.5, z0 + h * 0.5),
                         (abs(x1 - x0), out, h), mat), 0.012)
            self.add(box(name + "_s", (sx * (W2 + out * 0.5), 0, z0 + h * 0.5),
                         (out, YF - YB, h), mat), 0.012)
        self.add(box(name + "_b", (0, YB - out * 0.5, z0 + h * 0.5),
                     (W2 * 2 + out * 2, out, h), mat), 0.012)

    # ── 2. 主体：一个矩形平面，三段墙高 ─────────────────────────────────────
    def mass(self):
        M = self.M
        # 主体分两层：后层到门洞底（y=2.96），前层只做塔两侧 —— 中间留真门洞
        self.add(box("mass_lo", (0, (YB + T_CORE_Y) * 0.5, (H0 + WALL_W) * 0.5),
                     (W2 * 2, T_CORE_Y - YB, WALL_W - H0), M["stone_light"]), 0.036)
        for sx in (-1, 1):
            self.add(box("mass_front", (sx * (TX + W2) * 0.5, (T_CORE_Y + YF) * 0.5,
                                        (H0 + WALL_W) * 0.5),
                         (W2 - TX, YF - T_CORE_Y, WALL_W - H0), M["stone_light"]), 0.030)
        self.add(box("mass_hi", (0, 0, (WALL_W + WALL_C) * 0.5),
                     (W2C * 2, YF - YB, WALL_C - WALL_W), M["stone_light"]), 0.036)
        # 墙裙 / 腰线：在门洞与塔身处断开（不然会横在门洞前面）
        self.band_split("dado", H0, DADO, 0.075, M["stone_mid"], 1.28)
        self.band_split("dado_cap", DADO - 0.05, DADO + 0.045, 0.10, M["stone_dark"], 1.28)
        self.band_split("string", STR_Z - 0.07, STR_Z + 0.07, 0.055, M["stone_light"], TX + 0.02)
        # 附楼檐口：只做两翼（前 / 外 / 后三个面），不横过主楼
        for sx in (-1, 1):
            xin, xout = sx * W2C, sx * (W2 + 0.16)
            self.add(box("corn_w_f", ((xin + xout) * 0.5, YF + 0.08, (WALL_W + CORN_W) * 0.5),
                         (abs(xout - xin), 0.18, CORN_W - WALL_W), M["stone_light"]), 0.012)
            self.add(box("corn_w_b", ((xin + xout) * 0.5, YB - 0.08, (WALL_W + CORN_W) * 0.5),
                         (abs(xout - xin), 0.18, CORN_W - WALL_W), M["stone_light"]), 0.012)
            self.add(box("corn_w_s", (sx * (W2 + 0.08), 0, (WALL_W + CORN_W) * 0.5),
                         (0.18, YF - YB - 0.36, CORN_W - WALL_W), M["stone_light"]), 0.012)
            self.add(box("corn_w_lip", (sx * (W2 + 0.12), 0, WALL_W - 0.03),
                         (0.26, YF - YB - 0.30, 0.08), M["stone_dark"]), 0.006)
        # 主楼檐口（三面）
        for sx in (-1, 1):
            x0, x1 = sx * (TX + 0.02), sx * (W2C + 0.15)
            self.add(box("corn_c_f", ((x0 + x1) * 0.5, YF + 0.10, (WALL_C + CORN_C) * 0.5),
                         (abs(x1 - x0), 0.20, CORN_C - WALL_C), M["stone_light"]), 0.014)
        self.add(box("corn_c_b", (0, YB - 0.10, (WALL_C + CORN_C) * 0.5),
                     (W2C * 2 + 0.30, 0.20, CORN_C - WALL_C), M["stone_light"]), 0.014)
        for sx in (-1, 1):
            self.add(box("corn_c_s", (sx * (W2C + 0.10), 0, (WALL_C + CORN_C) * 0.5),
                         (0.20, YF - YB - 0.40, CORN_C - WALL_C), M["stone_light"]), 0.014)
            self.add(box("corn_c_lip", (sx * (W2C + 0.14), 0, WALL_C - 0.03),
                         (0.28, YF - YB - 0.28, 0.08), M["stone_dark"]), 0.006)
        for sx in (-1, 1):
            x0, x1 = sx * (TX + 0.02), sx * (W2C + 0.18)
            self.add(box("corn_c_lip_f", ((x0 + x1) * 0.5, YF + 0.14, WALL_C - 0.03),
                         (abs(x1 - x0), 0.28, 0.08), M["stone_dark"]), 0.006)
        self.add(box("corn_c_lip_b", (0, YB - 0.14, WALL_C - 0.03),
                     (W2C * 2 + 0.36, 0.28, 0.08), M["stone_dark"]), 0.006)
        # 四角隅石
        for sx in (-1, 1):
            for (yface, sy) in ((YF, 1), (YB, -1)):
                for i in range(4):
                    zz = 1.94 + i * 0.84
                    self.add(box("quoin", (sx * (W2 - 0.26), yface - sy * 0.26, zz),
                                 (0.54 + (0.06 if i % 2 else 0.0), 0.54, 0.42),
                                 M["stone_mid"]), 0.010)

    # ── 3. 钟塔（压回墙面，只有 15 mm 凸缝；门洞是真凹进去的）──────────────
    def tower(self):
        M = self.M
        # 塔芯（门洞底就在它的前脸）+ 前脸薄板（挖拱门）
        self.add(box("tw_core", (0, (TY0 + T_CORE_Y) * 0.5, (H0 + T_TOP) * 0.5),
                     (TX * 2, T_CORE_Y - TY0, T_TOP - H0), M["stone_light"]), 0.034)
        gw = GATE_W * 0.5
        z_t = GATE_SPRING + gw
        dep, off = TY1 - T_CORE_Y, (TY1 + T_CORE_Y) * 0.5
        self.add(extrude("tw_face_L", [(-TX, H0), (-gw, H0), (-gw, T_TOP), (-TX, T_TOP)],
                         "Y", dep, (0, 0), M["stone_light"], offset=off), 0.030)
        self.add(extrude("tw_face_R", [(gw, H0), (TX, H0), (TX, T_TOP), (gw, T_TOP)],
                         "Y", dep, (0, 0), M["stone_light"], offset=off), 0.030)
        top = [(-gw, z_t), (-gw, T_TOP), (gw, T_TOP), (gw, z_t)]
        for s in range(0, 9):
            a = math.pi * s / 8
            top.append((gw * math.cos(a), GATE_SPRING + gw * math.sin(a)))
        self.add(extrude("tw_face_T", top, "Y", dep, (0, 0), M["stone_light"], offset=off), 0.030)
        # 塔檐口
        self.add(frame_ring("tw_corn", -TX - 0.22, TX + 0.22, TY0 - 0.22, TY1 + 0.22,
                            T_TOP, T_CORN, 0.24, M["stone_light"]), 0.018)
        self.add(frame_ring("tw_corn_lip", -TX - 0.26, TX + 0.26, TY0 - 0.26, TY1 + 0.26,
                            T_CORN - 0.10, T_CORN - 0.01, 0.28, M["stone_dark"]), 0.008)
        # 钟面层（收 4 cm）
        self.add(box("tw_clock", (0, (TY0 + TY1) * 0.5, (CLK0 + CLK1) * 0.5),
                     (TX * 2 - 0.08, TY1 - TY0 - 0.08, CLK1 - CLK0), M["stone_light"]), 0.030)
        # 露台女儿墙 + 压顶 + 四角柱
        self.add(frame_ring("tw_para", -TX - 0.10, TX + 0.10, TY0 - 0.10, TY1 + 0.10,
                            CLK1, PARA1, 0.16, M["stone_mid"]), 0.010)
        self.add(frame_ring("tw_para_cap", -TX - 0.17, TX + 0.17, TY0 - 0.17, TY1 + 0.17,
                            PARA1, PARA1 + 0.09, 0.20, M["stone_dark"]), 0.006)
        cy = (TY0 + TY1) * 0.5
        for sx in (-1, 1):
            for sy in (-1, 1):
                px = sx * (TX + 0.06)
                py = cy + sy * ((TY1 - TY0) * 0.5 + 0.06)
                self.add(box("tw_pin", (px, py, (PARA1 - 0.04 + 13.34) * 0.5),
                             (0.24, 0.24, 13.34 - PARA1 + 0.04), M["stone_light"]), 0.010)
                self.add(frustum("tw_pin_tip", 13.34, 13.60, 0.30, 0.30, 0.06, 0.06,
                                 px, py, M["stone_dark"]), 0.004)
        # 锥顶
        self.add(frustum("tw_spire", SP_Z0, SP_Z1, 2.86, 2.68, 0.09, 0.08, 0, cy,
                         M["roof"]), 0.018)
        self.add(box("tw_spire_base", (0, cy, SP_Z0 + 0.03), (2.96, 2.78, 0.08),
                     M["roof_edge"]), 0.005)
        for sx in (-1, 1):
            for sy in (-1, 1):
                self.add(beam("tw_spire_hip", (sx * 1.42, cy + sy * 1.33, SP_Z0 + 0.04),
                              (sx * 0.05, cy + sy * 0.04, SP_Z1), 0.09, 0.06,
                              M["roof_edge"]), 0.004)
        for (zz, sc) in ((13.25, 0.72), (13.80, 0.47)):
            self.add(box("tw_spire_ring", (0, cy, zz), (2.86 * sc + 0.05, 2.68 * sc + 0.05, 0.05),
                         M["roof_edge"]), 0.003)
        # 金顶 + 旗
        self.add(revolve("tw_finial", [(0.0, 0.0), (0.10, 0.02), (0.135, 0.12), (0.07, 0.26),
                                       (0.0, 0.36)], 8, (0, cy, SP_Z1), M["gold"]), 0.0, 1)
        self.add(revolve("tw_flagpole", [(0.045, 0.0), (0.038, FLAG_TOP - POLE_Z)], 6,
                         (0, cy, POLE_Z), M["wood_dark"]), 0.0, 1)
        self.add(revolve("tw_flagtip", [(0.070, 0.0), (0.050, 0.05), (0.018, 0.11)], 8,
                         (0, cy, FLAG_TOP - 0.02), M["gold"]), 0.0, 1)
        fw, fh = 1.18, 0.80
        prof = [(0.0, 0.0), (fw, -0.09), (fw * 0.80, -fh * 0.50), (fw, -fh * 0.90), (0.0, -fh)]
        self.add(extrude("tw_flag_cloth", prof, "Y", 0.035, (0.0, FLAG_TOP - 0.06),
                         M["team"], offset=cy), 0.004)
        self.add(box("tw_flag_hoist", (0.032, cy, FLAG_TOP - 0.06 - fh * 0.46),
                     (0.08, 0.06, fh * 0.92), M["team_trim"]), 0.003)
        self.crest("tw_flag_crest", "Y", 0.51, cy + 0.0125, FLAG_TOP - 0.62, 0.40)

    # ── 4. 钟面（正面 + 两侧）────────────────────────────────────────────────
    def clock_face(self, name, center, face):
        M = self.M
        cx, cy, cz = center
        if face == "Y":
            self.add(ring_y(name + "_ring", (cx, cy + 0.02, cz), 0.58, 0.74, 0.18, 12,
                            M["gold"]), 0.010)
            self.add(cyl(name + "_face", (cx, cy + 0.03, cz), 0.59, 0.10, 12, M["coal"],
                         axis="Y"), 0.004)
            for k in range(4):
                a = TAU * k / 4
                self.add(box(name + "_tick", (cx + math.sin(a) * 0.44, cy + 0.095,
                                               cz + math.cos(a) * 0.44),
                             (0.07, 0.03, 0.07), M["gold"], rot=(0, -a, 0)), 0.002)
            for (ang, ln, w) in ((math.radians(-52), 0.40, 0.065),
                                 (math.radians(28), 0.27, 0.052)):
                self.add(box(name + "_hand",
                             (cx + math.sin(ang) * ln * 0.5, cy + 0.105,
                              cz + math.cos(ang) * ln * 0.5),
                             (w, 0.03, ln), M["gold"], rot=(0, -ang, 0)), 0.002)
        else:
            sgn = 1 if cx > 0 else -1
            self.add(ring_x(name + "_ring", (cx, cy, cz), 0.58, 0.74, 0.18, 12, M["gold"]), 0.010)
            self.add(cyl(name + "_face", (cx, cy, cz), 0.59, 0.10, 12, M["coal"], axis="X"), 0.004)
            for k in range(4):
                a = TAU * k / 4
                self.add(box(name + "_tick", (cx + sgn * 0.095, cy + math.sin(a) * 0.44,
                                               cz + math.cos(a) * 0.44),
                             (0.03, 0.07, 0.07), M["gold"], rot=(-a, 0, 0)), 0.002)
            for (ang, ln, w) in ((math.radians(-52), 0.40, 0.065),
                                 (math.radians(28), 0.27, 0.052)):
                self.add(box(name + "_hand",
                             (cx + sgn * 0.105, cy + math.sin(ang) * ln * 0.5,
                              cz + math.cos(ang) * ln * 0.5),
                             (0.03, w, ln), M["gold"], rot=(-ang, 0, 0)), 0.002)

    # ── 5. 拱门 / 门扇 / 扇形窗 ─────────────────────────────────────────────
    def gate(self):
        M = self.M
        gw = GATE_W * 0.5
        # 扇形窗发光面：贴在塔芯前脸（门洞底），从拱洞里透出来
        self.add(extrude("gate_glow", arch_profile(GATE_W - 0.08, 0.0, 8), "Y", 0.06,
                         (0, GATE_SPRING + 0.02), M["glow"], offset=3.05), 0.0)
        # 拱券石 + 门套：只凸 80 mm
        self.add(arch_band("gate_arch", 0.0, GATE_SPRING, gw, gw + 0.26,
                           TY1, TY1 + 0.08, M["stone_light"], segs=10), 0.018)
        for sgn in (-1, 1):
            self.add(box("gate_jamb", (sgn * (gw + 0.13), TY1 + 0.04,
                                       (H0 + GATE_SPRING) * 0.5),
                         (0.26, 0.08, GATE_SPRING - H0), M["stone_light"]), 0.014)
        # 双开门（门洞凹进 0.18）
        leaf = (GATE_W - 0.14) * 0.5
        for sgn in (-1, 1):
            cx = sgn * leaf * 0.5
            self.add(box("gate_leaf", (cx, 3.12, H0 + 1.19), (leaf, 0.09, 2.38),
                         M["team"]), 0.012)
            for zz in (H0 + 0.48, H0 + 1.62):
                self.add(box("gate_strap", (cx, 3.17, zz), (leaf - 0.10, 0.03, 0.10),
                             M["iron"]), 0.004)
            for (dx, dz) in ((0.20, 1.96), (0.20, 0.90), (-0.20, 1.96), (-0.20, 0.90)):
                self.add(box("gate_stud", (cx + dx, 3.172, H0 + dz), (0.05, 0.025, 0.05),
                             M["gold"]), 0.002)
            self.add(ring_y("gate_ring", (cx + sgn * 0.26, 3.147, H0 + 1.16), 0.042, 0.070,
                            0.035, 8, M["gold"]), 0.003)
        self.add(box("gate_seam", (0, 3.168, H0 + 1.19), (0.04, 0.02, 2.34),
                     M["wood_dark"]), 0.002)
        # 门楣 + 扇形窗铁艺
        self.add(box("gate_transom", (0, 3.15, H0 + 2.42), (GATE_W - 0.04, 0.10, 0.09),
                     M["wood_dark"]), 0.006)
        for dx in (-0.38, 0.0, 0.38):
            self.add(box("gate_bar", (dx, 3.14, H0 + 2.66), (0.05, 0.05, 0.58),
                         M["iron"]), 0.002)
        self.add(box("gate_bar2", (0, 3.14, H0 + 2.50), (1.76, 0.05, 0.05), M["iron"]), 0.002)

    # ── 6. 屋面：主楼山墙 + 两翼四坡 ────────────────────────────────────────
    def roofs(self):
        M = self.M
        # 主楼：双坡（脊沿 Y），山墙朝前 / 后
        self.add(slope_slab("roof_c", (-AX_C, EAVE_C), (0.0, RIDGE_C),
                            YB - 0.35, YF + 0.35, ROOF_T, M["roof"]), 0.0)
        self.add(slope_slab("roof_c", (AX_C, EAVE_C), (0.0, RIDGE_C),
                            YB - 0.35, YF + 0.35, ROOF_T, M["roof"]), 0.0)
        self.add(box("ridge_c", (0, (YB - 0.35 + TY0) * 0.5, RIDGE_C + 0.02),
                     (0.26, TY0 - (YB - 0.35), 0.16), M["roof_edge"]), 0.006)
        # 山墙三角（收到屋面内侧，不戳穿瓦面）
        # 山墙拆成塔两侧两片：整块三角形会穿过塔芯，也压在塔的长窗上
        zt = EAVE_C + (RIDGE_C - 0.20 - EAVE_C) * (W2C - TX) / W2C
        for sx in (-1, 1):
            tri = [(sx * W2C, EAVE_C), (sx * TX, EAVE_C), (sx * TX, zt)]
            for yy in (YF - 0.11, YB + 0.11):
                self.add(extrude("gable", tri, "Y", 0.22, (0, 0),
                                 M["stone_light"], offset=yy), 0.020)
        # 山墙封边（barge board）
        # 封边板只做到塔边：整根拉通会横在钟面层前面（v2 第一版的钟被切了一道）
        z_at_tower = EAVE_C + (RIDGE_C - EAVE_C) * (AX_C - TX - 0.02) / AX_C
        for sy in (1, -1):
            yy = sy * (YF + 0.30)
            for sx in (-1, 1):
                self.add(beam("barge", (sx * (AX_C - 0.02), yy, EAVE_C + 0.02),
                              (sx * (TX + 0.02), yy, z_at_tower), 0.16, 0.20,
                              M["wood_dark"]), 0.004)
        # 主楼瓦垄：每坡 7 道，沿坡向（Y 定线、檐口到脊）
        for y in (-2.90, -1.94, -0.98, 0.0, 0.98, 1.94, 2.90):
            for sx in (-1, 1):
                self.add(beam("tile_c", (sx * (AX_C - 0.10), y, EAVE_C + 0.02),
                              (sx * 0.06, y, RIDGE_C + 0.02), 0.095, 0.075, M["roof"]), 0.0)
        # 两翼：四坡（脊沿 Y）
        for sx in (-1, 1):
            x0, x1 = sorted((sx * (W2C - 0.05), sx * (W2 + 0.30)))
            width = x1 - x0
            ry = (YF - YB + 0.60) * 0.5 - width * 0.5
            self.add(hip_shell_y("roof_w", x0, x1, YB - 0.30, YF + 0.30,
                                 EAVE_W, RIDGE_W, ry, 0.16, M["roof"]), 0.0)
            cx = (x0 + x1) * 0.5
            self.add(box("ridge_w", (cx, 0, RIDGE_W + 0.02), (0.20, ry * 2 + 0.30, 0.12),
                         M["roof_edge"]), 0.005)
            # 外坡瓦垄
            for yy in (-2.60, -1.30, 0.0, 1.30, 2.60):
                self.add(beam("tile_w", (cx, yy, RIDGE_W + 0.01),
                              (cx + (0.95 if sx > 0 else -0.95), yy, EAVE_W + 0.02),
                              0.085, 0.065, M["roof"]), 0.0)

    # ── 7. 窗 ───────────────────────────────────────────────────────────────
    def windows(self):
        M = self.M
        # 主楼前墙：两层各两扇（塔两侧）
        for x in (-2.75, 2.75):
            self.arch_win("win_f", (x, YF + 0.03, 1.85), 1.05, 1.55, "Y")
            self.win2("win2_f", (x, YF + 0.19, 6.55), 0.92, 1.95)
            self.shutters("shut_f", (x, YF + 0.045, 6.55), 0.92, 1.95, "Y")
        # 主楼后墙
        for x in (-2.40, 0.0, 2.40):
            self.arch_win("win_b", (x, YB - 0.03, 1.85), 1.05, 1.55, "Y", out=-1)
        for x in (-2.52, 0.0, 2.52):
            self.win2("win2_b", (x, YB - 0.19, 6.55), 0.92, 1.95)
            self.shutters("shut_b", (x, YB - 0.045, 6.55), 0.92, 1.95, "Y", out=-1)
        # 主楼侧墙（附楼屋顶以上那一段）：两扇窗，别让侧面读成一块灰板
        for sx in (-1, 1):
            for yy in (-1.55, 1.55):
                self.arch_win("win_c_s", (sx * (W2C + 0.01), yy, 6.40), 0.85, 1.55, "X", out=sx)
        # 塔身：一枚大盾 + 一扇方窗（长尖窗读成小教堂，换成"徽记 + 钟楼窗"）
        self.kite("shield_t", (0.0, 3.56, 6.95), "Y", 1.50, 1.75)
        self.win2("win_t", (0.0, TY1 + 0.19, 8.95), 1.15, 1.00)
        # 附楼：前 / 后各一扇高拱窗，外侧两扇；色带上一枚小盾
        for sx in (-1, 1):
            self.arch_win("win_w_f", (sx * 4.32, YF + 0.03, 1.85), 0.95, 2.05, "Y")
            self.kite("shield_w", (sx * 4.32, 3.30, 4.62), "Y", 0.82, 0.95)
            self.arch_win("win_w_b", (sx * 4.32, YB - 0.03, 1.85), 0.95, 2.05, "Y", out=-1)
            for yy in (-1.55, 1.55):
                self.arch_win("win_w_s", (sx * (W2 + 0.01), yy, 1.85), 0.95, 2.05, "X", out=sx)
            self.wallbanner("wbanner_w" + ("R" if sx > 0 else "L"),
                            (sx * (W2 + 0.30), 0.0, 3.15), "X", 1.40, 1.70)

    def arch_win(self, name, center, w, h, face, out=1, mat=None):
        M = self.M
        mat = M["glass"] if mat is None else mat
        cx, cy, cz = center
        hw = w * 0.5
        straight = h - hw
        if face == "Y":
            self.add(extrude(name, arch_profile(w, straight, segs=6), "Y", 0.10, (cx, cz),
                             mat, offset=cy), 0.0)
            self.add(arch_band(name + "_arch", cx, cz + straight, hw, hw + 0.14,
                               cy + out * 0.03, cy + out * 0.12,
                               M["stone_light"], segs=6), 0.010)
            for sgn in (-1, 1):
                self.add(box(name + "_jamb", (cx + sgn * (hw + 0.065), cy + out * 0.065,
                                              cz + straight * 0.5),
                             (0.13, 0.13, straight), M["stone_light"]), 0.008)
            self.add(box(name + "_bar", (cx, cy + out * 0.075, cz + straight * 0.5),
                         (0.045, 0.06, straight), M["wood_dark"]), 0.003)
            self.add(box(name + "_sill", (cx, cy + out * 0.055, cz - 0.055),
                         (w + 0.28, 0.20, 0.095), M["stone_light"]), 0.008)
        else:
            self.add(extrude(name, arch_profile(w, straight, segs=6), "X", 0.10, (cy, cz),
                             mat, offset=cx + out * 0.01), 0.0)
            self.add(arch_band_x(name + "_arch", cy, cz + straight, hw, hw + 0.14,
                                 cx + out * 0.03, cx + out * 0.12,
                                 M["stone_light"], segs=6), 0.010)
            for sgn in (-1, 1):
                self.add(box(name + "_jamb", (cx + out * 0.065, cy + sgn * (hw + 0.065),
                                              cz + straight * 0.5),
                             (0.13, 0.13, straight), M["stone_light"]), 0.008)
            self.add(box(name + "_bar", (cx + out * 0.075, cy, cz + straight * 0.5),
                         (0.06, 0.045, straight), M["wood_dark"]), 0.003)
            self.add(box(name + "_sill", (cx + out * 0.055, cy, cz - 0.055),
                         (0.20, w + 0.28, 0.095), M["stone_light"]), 0.008)

    def shutters(self, name, center, w, h, face, out=1):
        M = self.M
        cx, cy, cz = center
        for sgn in (-1, 1):
            if face == "Y":
                self.add(box(name, (cx + sgn * (w * 0.5 + 0.20), cy + out * 0.02, cz),
                             (0.22, 0.14, h * 0.92), M["wood_dark"]), 0.008)
            else:
                self.add(box(name, (cx + out * 0.02, cy + sgn * (w * 0.5 + 0.20), cz),
                             (0.14, 0.22, h * 0.92), M["wood_dark"]), 0.008)

    def win2(self, name, center, w, h, mat=None, tag=""):
        M = self.M
        mat = M["glass"] if mat is None else mat
        cx, cy, cz = center
        self.add(box(name + tag, (cx, cy, cz), (w, 0.10, h), mat))
        for sgn in (-1, 1):
            self.add(box(name + "_fL", (cx + sgn * (w * 0.5 + 0.07), cy + 0.055, cz),
                         (0.14, 0.16, h + 0.28), M["stone_light"]), 0.008)
            self.add(box(name + "_fT", (cx, cy + 0.055, cz + sgn * (h * 0.5 + 0.075)),
                         (w + 0.28, 0.16, 0.14), M["stone_light"]), 0.008)
        self.add(box(name + "_bar", (cx, cy + 0.14, cz), (0.05, 0.05, h + 0.02),
                     M["wood_dark"]), 0.003)
        self.add(box(name + "_bar2", (cx, cy + 0.14, cz + h * 0.16), (w + 0.02, 0.05, 0.05),
                     M["wood_dark"]), 0.003)
        self.add(box(name + "_sill", (cx, cy + 0.07, cz - h * 0.5 - 0.085),
                     (w + 0.38, 0.21, 0.10), M["stone_light"]), 0.008)

    # ── 8. 腰带 ─────────────────────────────────────────────────────────────
    def heraldry(self):
        M = self.M
        self.add(frame_ring("band_m", -W2 - 0.065, W2 + 0.065, YB - 0.065, YF + 0.065,
                            B0, B1, 0.085, M["team"]), 0.010)
        self.add(frame_ring("band_m_t", -W2 - 0.085, W2 + 0.085, YB - 0.085, YF + 0.085,
                            B1 - 0.055, B1 + 0.025, 0.105, M["team_trim"]), 0.004)
        # 塔身那段腰带：跟着塔面向前折一次，让"腰线"不断（也把染色带到塔上）
        BH = B1 - B0
        for sgn in (-1, 1):
            self.add(box("band_t_s", (sgn * TX, (YF + 0.13 + TY1) * 0.5, (B0 + B1) * 0.5),
                         (0.13, TY1 - YF - 0.13, BH), M["team"]), 0.010)
            self.add(box("band_t_s_t", (sgn * TX, (YF + 0.13 + TY1) * 0.5, B1 - 0.015),
                         (0.15, TY1 - YF - 0.13, 0.085), M["team_trim"]), 0.004)
        self.add(box("band_t_f", (0, TY1 + 0.065, (B0 + B1) * 0.5),
                     (TX * 2 + 0.02, 0.13, BH), M["team"]), 0.010)
        self.add(box("band_t_f_t", (0, TY1 + 0.085, B1 - 0.015),
                     (TX * 2 + 0.04, 0.15, 0.085), M["team_trim"]), 0.004)

    # ── 9. 广场陈设 ─────────────────────────────────────────────────────────
    def props(self):
        M = self.M
        z = G_PLAZA
        bx, by = -4.15, 6.55
        for sgn in (-1, 1):
            self.add(box("board_post", (bx + sgn * 0.82, by, z + 0.78), (0.16, 0.16, 1.56),
                         M["wood_dark"]), 0.008)
        self.add(box("board_face", (bx, by, z + 1.12), (1.78, 0.11, 0.98), M["wood_warm"],
                     rot=(-0.14, 0, 0)), 0.010)
        self.add(box("board_trim", (bx, by, z + 1.62), (1.94, 0.16, 0.11), M["wood_dark"],
                     rot=(-0.14, 0, 0)), 0.006)
        self.add(box("board_foot", (bx, by + 0.06, z + 0.06), (1.90, 0.34, 0.12),
                     M["stone_mid"]), 0.006)
        for (dx, dz, w, h) in ((-0.50, 0.10, 0.34, 0.42), (0.06, 0.02, 0.30, 0.34),
                               (0.50, 0.12, 0.32, 0.38)):
            self.add(box("board_note", (bx + dx, by + 0.068, z + 1.12 + dz),
                         (w, 0.018, h), M["paving"], rot=(-0.14, 0, 0)), 0.002)
        for sgn in (-1, 1):
            px = sgn * 2.62
            self.add(box("braz_ped", (px, 5.55, z + 0.36), (0.46, 0.46, 0.72),
                         M["stone_mid"]), 0.010)
            self.add(box("braz_ped_t", (px, 5.55, z + 0.75), (0.54, 0.54, 0.08),
                         M["stone_dark"]), 0.006)
            self.add(revolve("braz_bowl", [(0.16, 0.0), (0.30, 0.10), (0.34, 0.24), (0.32, 0.26)],
                             8, (px, 5.55, z + 0.775), M["iron"]), 0.008)
            self.add(revolve("braz_coal", [(0.0, 0.0), (0.26, 0.02), (0.26, 0.09), (0.0, 0.10)],
                             8, (px, 5.55, z + 1.03), M["coal"]), 0.004)
            self.add(lathe("braz_flame", [(0.0, z + 1.05, px, 5.55), (0.17, z + 1.11, px, 5.55),
                                          (0.12, z + 1.31, px + 0.02, 5.55),
                                          (0.0, z + 1.49, px + 0.04, 5.55)],
                           6, M["flame_out"]), 0.0)
            self.add(lathe("braz_core", [(0.0, z + 1.05, px, 5.55), (0.09, z + 1.10, px, 5.55),
                                         (0.05, z + 1.27, px + 0.01, 5.55),
                                         (0.0, z + 1.37, px + 0.02, 5.55)],
                           6, M["flame_in"]), 0.0)
        self.barrel("barrel_a", (4.72, 5.75), 0.32, 0.74, z)
        self.barrel("barrel_b", (4.28, 5.65), 0.29, 0.66, z)
        self.crate("crate_a", (4.72, 6.55), 0.62, 0.56, z)
        for sgn in (-1, 1):
            px, py = sgn * 4.85, 9.00
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

    # ── 10. 组装 / 收尾 ─────────────────────────────────────────────────────
    def build(self):
        for step in (self.base, self.mass, self.tower, self.gate, self.windows,
                     self.roofs, self.heraldry, self.props):
            step()
        cy = (TY0 + TY1) * 0.5
        self.clock_face("clock_f", (0.0, TY1, 12.465), "Y")
        for sx in (-1, 1):
            self.clock_face("clock_s", (sx * TX, cy, 12.465), "X")
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
