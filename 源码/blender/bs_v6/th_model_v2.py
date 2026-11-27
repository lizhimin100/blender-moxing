"""
th_model.py —— 城镇大厅 v2（接手 v1）· 主楼 + 钟楼 + 后附楼（同一主体）

这一版针对三条反馈重做：

  ① **入口不再突出一块**：v1 的钟塔从正立面往前凸 1.0 m，再接一块门廊台，
     俯视像兵营的营门。v2 把塔压回立面（塔前脸与外墙同面，只有 20 mm 石作凸缝），
     门洞是在塔身里 0.55 m 深的拱门；塔是"主楼的中央塔身"，不是外挂门楼。
  ② **主楼 + 钟楼 + 附楼，一整个主体**：主楼 9.6 × 7.2，塔是主楼正中的
     3.8 × 3.4 实体塔身，后附楼 6.4 × 3.6 从后墙长出来、共用石台与一条腰线。
     一层到二层的阵营色带环着整块平面走一圈，钟塔、附楼、主楼由一条腰带绑住。
  ③ **屋面重做**：v1 的四坡大金字塔在正立面上是一块黑面，塔从屋面正中穿过，
     接缝处堆着三角墙，读起来又怪又没职责。v2 改成**两段式孟莎四坡**：
     下段 55° 陡坡压出檐口，上段 30° 缓坡收到一条短正脊，折脊处一圈铅压条；
     钟塔坐在上段屋面上，钟面正好高过屋脊——职责写在"钟"上，不在空尖顶上。
     檐口做石线脚 + 齿饰，屋面做通长瓦垄与戗脊，俯视下是清楚的"冠"。

坐标：X 右、Y 前（+Y = 正面）、Z 上；原点在占地中心，z = 0 地面。
交付前整体沿 X 镜像一次。徽记 / 旗帜 / 木桶木箱继承 br_model.Model（同一段几何）。
"""
import math
from math import tau as TAU

import bpy

import bslib as L
import br_model as BR
from bslib import (arch_band, beam, box, cone, cyl, extrude, frustum, lathe,
                   mesh_obj, revolve, ring_y, tube_band)
from br_model import arch_profile, mirror_x, out_sign

# ── 主楼平面与标高 ─────────────────────────────────────────────────────────
W2 = 4.80                      # 主楼半宽（9.6）
YF, YB = 3.60, -3.60           # 主楼进深 7.2
H0 = 0.72                      # 石台顶 / 室内地面
DADO = 1.48                    # 墙裙顶
STR = 4.18                     # 腰线
B0, B1 = 4.78, 5.35            # 阵营色带（0.57 高）
WALL = 7.58                    # 墙顶
CORN0, CORN1 = 7.56, 7.80      # 石檐口
EAVE_Z = 7.82
EAVE_X, EAVE_Y = 5.18, 3.98    # 屋面出檐
BRK_X, BRK_Y, BRK_Z = 4.28, 3.08, 9.22   # 孟莎折脊
RIDGE_Z, RIDGE_X = 10.98, 2.30          # 上段正脊
ROOF_T = 0.18

# ── 钟塔 ───────────────────────────────────────────────────────────────────
TW = 1.80                      # 塔半宽（3.6）—— 比 v1 宽、比上一稿收，读作"塔身"而不是"门楼"
TY0, TY1 = 0.20, 3.60          # 塔进深 3.4；前脸与主墙同面
T_TOP = 11.05                  # 塔身顶（钟座底）
CLK0, CLK1 = 11.10, 12.95      # 钟座（1.85 高，钟面放得开）
CLKZ = 12.00                   # 钟心
PARA0, PARA1 = 12.95, 13.35    # 塔顶露台女儿墙
BF0, BF1 = 13.35, 15.06        # 钟亭（开放；墙顶藏进 15.10 的上枋）
SP0, SP1 = 15.10, 18.15        # 尖顶（3.05 高，修长）
POLE_Z = 18.20
FLAG_TOP = 19.05

GW = 1.10                      # 拱门半宽（2.2）
SPRING = 3.40                  # 拱脚（下移 10 cm，给色带让出净空）
ARCH_TOP = SPRING + GW        # 4.50
TDOOR = SPRING - H0 - 0.02    # 门扇高 2.66（门顶比拱脚低 20 mm，避免共面）

# ── 后附楼 ─────────────────────────────────────────────────────────────────
AX = 3.20                      # 附楼半宽（6.4）
AY0, AY1 = -7.20, -3.62        # 后附楼进深 3.58（前脸埋进主楼 20 mm）
ATOP = 4.58                    # 附楼墙顶（压在檐口里，避免与檐口顶面共面）
A_E_X, A_E_Y0 = 3.55, -7.55    # 附楼屋面出檐
A_E_Y1 = -3.60                 # 附楼前檐贴着主墙
A_RIDGE = 6.30                 # 附楼脊
A_RY = -5.58                   # 附楼脊的 Y
A_RX = 1.58                    # 附楼脊半长

# ── 石台 / 前庭 ─────────────────────────────────────────────────────────────
POD_X = 5.25
POD_Y0, POD_Y1 = -7.65, 4.05   # 石台：含后附楼与 45 cm 后檐
POD_Z = 0.72
TER_Y0, TER_Y1 = 4.05, 8.55    # 前庭台
TER_Z = 0.42
STEP_Y0, STEP_Y1 = 8.55, 9.42  # 前庭外台阶
PROP_Z = 0.49                  # 侧铺石顶面（道具站这里）
RUN_Z = 0.50                   # 中央仪仗道顶面

# ── 阵营色标准件 ───────────────────────────────────────────────────────────
SHIELD_W, SHIELD_H = 1.10, 1.30


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
    """任意多边形厚板：外表面 + 法向下沉 t 的内表面 + 侧边。"""
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


def rib_quad(name, p0, p1, p3, p2, n, w, t, mat, inset=0.10, lift=0.028):
    """在四坡面上按"从底边到顶边"的插值做瓦垄。p0-p1 底边，p3-p2 顶边。

    返回创建的梁对象列表 —— 调用方必须把它们 add 进模型，否则它们会留在场景里
    却没有进 GLB / 图集（v2 第一版就漏了这一步：.blend 里有 31 根瓦垄、GLB 里没有）。
    """
    out = []
    for i in range(n):
        f = (i + 1) / (n + 1)
        f = inset + f * (1 - 2 * inset)
        a = lerp(p0, p1, f)
        b = lerp(p3, p2, f)
        a = (a[0], a[1], a[2] + lift)
        b = (b[0], b[1], b[2] + lift)
        ob = beam(name, a, b, w, t, mat)
        if ob is not None:
            out.append(ob)
    return out


class Model(BR.Model):
    # ── 1. 石台 / 前庭 / 台阶 ───────────────────────────────────────────────
    def base(self):
        M = self.M
        cy = (POD_Y0 + POD_Y1) * 0.5
        dy = POD_Y1 - POD_Y0
        self.add(box("plinth_low", (0, cy, 0.08), (POD_X * 2 + 0.40, dy + 0.40, 0.16),
                     M["stone_mid"]), 0.012)
        self.add(box("plinth_mid", (0, cy, 0.36), (POD_X * 2, dy, 0.52),
                     M["stone_dark"]), 0.020)
        self.add(box("plinth_cap", (0, cy, 0.64), (POD_X * 2 + 0.18, dy + 0.18, 0.16),
                     M["stone_mid"]), 0.012)
        # 前庭台（0.42）+ 台帮 + 铺石
        tcy = (TER_Y0 + TER_Y1) * 0.5
        tdy = TER_Y1 - TER_Y0
        self.add(box("terrace_bed", (0, tcy, 0.14), (POD_X * 2, tdy, 0.28),
                     M["stone_dark"]), 0.016)
        self.add(box("terrace_body", (0, tcy, 0.35), (POD_X * 2 - 0.10, tdy - 0.10, 0.14),
                     M["stone_mid"]), 0.012)
        # 铺石：中央仪仗道 2.5 宽 + 两侧大石板（每一块都有厚度、都压在同一条土台上）
        for i, (y0, y1) in enumerate(((4.08, 5.62), (5.66, 7.10), (7.14, 8.52))):
            self.add(box("pave_run", (0, (y0 + y1) * 0.5, 0.46), (2.50, y1 - y0, 0.10),
                         M["stone_light"]), 0.008)
            for sx in (-1, 1):
                x0, x1 = sorted((sx * 1.29, sx * 3.50))
                self.add(box("pave_side", ((x0 + x1) * 0.5, (y0 + y1) * 0.5, 0.455),
                             (x1 - x0, y1 - y0, 0.09), M["paving"]), 0.008)
                x0, x1 = sorted((sx * 3.54, sx * 5.12))
                self.add(box("pave_edge", ((x0 + x1) * 0.5, (y0 + y1) * 0.5, 0.452),
                             (x1 - x0, y1 - y0, 0.084), M["paving"]), 0.008)
        # 前庭台帮：两侧矮墙 + 前缘两段矮墙（中间给外台阶留口）
        for sx in (-1, 1):
            self.add(box("terrace_par", (sx * (POD_X - 0.12), tcy, 0.62),
                         (0.24, tdy - 0.20, 0.40), M["stone_mid"]), 0.010)
            self.add(box("terrace_par_cap", (sx * (POD_X - 0.12), tcy, 0.84),
                         (0.34, tdy - 0.10, 0.10), M["stone_light"]), 0.006)
            x0, x1 = sorted((sx * 1.78, sx * (POD_X - 0.02)))
            self.add(box("terrace_par_f", ((x0 + x1) * 0.5, TER_Y1 - 0.11, 0.60),
                         (x1 - x0, 0.22, 0.36), M["stone_mid"]), 0.010)
            self.add(box("terrace_par_fc", ((x0 + x1) * 0.5, TER_Y1 - 0.11, 0.80),
                         (x1 - x0 + 0.08, 0.32, 0.09), M["stone_light"]), 0.006)
        # 前庭外台阶（三段）+ 两侧颊墙 + 端柱
        for i, (y0, y1, zt) in enumerate(((STEP_Y0, 8.82, 0.30),
                                          (8.82, 9.10, 0.16),
                                          (9.10, STEP_Y1, 0.05))):
            self.add(box("step_out%d" % i, (0, (y0 + y1) * 0.5, zt * 0.5),
                         (3.44, y1 - y0, zt), M["stone_mid"]), 0.008)
        self.add(box("land_out", (0, STEP_Y1 + 0.20, 0.035), (4.20, 0.40, 0.07),
                     M["stone_mid"]), 0.006)
        for sx in (-1, 1):
            self.add(box("step_cheek", (sx * 1.86, (STEP_Y0 + STEP_Y1) * 0.5, 0.26),
                         (0.28, STEP_Y1 - STEP_Y0, 0.52), M["stone_mid"]), 0.008)
            self.add(box("step_cheek_cap", (sx * 1.86, (STEP_Y0 + STEP_Y1) * 0.5, 0.56),
                         (0.38, STEP_Y1 - STEP_Y0 + 0.10, 0.10), M["stone_light"]), 0.006)
            self.add(box("newel", (sx * 1.86, STEP_Y1 + 0.08, 0.64), (0.56, 0.56, 1.28),
                         M["stone_mid"]), 0.010)
            self.add(box("newel_cap", (sx * 1.86, STEP_Y1 + 0.08, 1.32), (0.68, 0.68, 0.12),
                         M["stone_light"]), 0.006)
            self.add(revolve("newel_ball", [(0.0, 0.0), (0.10, 0.03), (0.13, 0.12),
                                            (0.08, 0.21), (0.0, 0.24)], 8,
                             (sx * 1.86, STEP_Y1 + 0.08, 1.38), M["gold"]), 0.0, 1)
        # 主入口三级踏步（从 0.42 上 0.72）
        for i, (y0, y1, zt) in enumerate(((4.05, 4.35, 0.712),
                                          (4.35, 4.65, 0.622),
                                          (4.65, 4.95, 0.542))):
            self.add(box("step_in%d" % i, (0, (y0 + y1) * 0.5, (TER_Z + zt) * 0.5),
                         (3.60, y1 - y0, zt - TER_Z), M["stone_mid"]), 0.010)
        # 门槛
        self.add(box("threshold", (0, 3.55, H0 + 0.035), (2.60, 0.18, 0.07),
                     M["stone_dark"]), 0.004)

    def band_split(self, name, z0, z1, out, gap, mat, bev=0.012):
        """前脸断开的水平线脚：塔身 / 门洞处让开；侧面与背面通长。"""
        h = z1 - z0
        for sx in (-1, 1):
            x0, x1 = sx * gap, sx * (W2 + out)
            self.add(box(name + "_f", ((x0 + x1) * 0.5, YF + out * 0.5, z0 + h * 0.5),
                         (abs(x1 - x0), out, h), mat), bev)
            self.add(box(name + "_s", (sx * (W2 + out * 0.5), 0, z0 + h * 0.5),
                         (out, YF - YB, h), mat), bev)
        self.add(box(name + "_b", (0, YB - out * 0.5, z0 + h * 0.5),
                     (W2 * 2 + out * 2, out, h), mat), bev)

    # ── 2. 主楼墙体 / 墙裙 / 腰线 / 檐口 ──────────────────────────────────────
    def mass(self):
        M = self.M
        self.add(box("mass_back", (0, (YB + TY0) * 0.5, (H0 + WALL) * 0.5),
                     (W2 * 2, TY0 - YB, WALL - H0), M["stone_light"]), 0.036)
        for sx in (-1, 1):
            self.add(box("mass_front", (sx * (TW + W2) * 0.5, (TY0 + YF) * 0.5,
                                        (H0 + WALL) * 0.5),
                         (W2 - TW, YF - TY0, WALL - H0), M["stone_light"]), 0.030)
        # 墙裙 / 腰线（塔身与门洞处断开）
        self.band_split("dado", H0, DADO, 0.07, TW, M["stone_mid"])
        self.band_split("dado_cap", DADO - 0.05, DADO + 0.04, 0.10, TW, M["stone_dark"])
        self.band_split("string", STR - 0.06, STR + 0.06, 0.05, TW, M["stone_light"])
        # 阵营色带：整圈一条，压过塔前脸（塔前脸比外墙面只低 20 mm，不会打架）
        self.add(frame_ring("band_m", -W2 - 0.12, W2 + 0.12, YB - 0.12, YF + 0.12,
                            B0, B1, 0.16, M["team"]), 0.010)
        self.add(frame_ring("band_t", -W2 - 0.14, W2 + 0.14, YB - 0.14, YF + 0.14,
                            B1 - 0.045, B1 + 0.025, 0.20, M["team_trim"]), 0.004)
        # 石檐口：前脸在塔身两侧断开，塔身用一条束带接上
        self.band_split("corn", CORN0, CORN1, 0.30, TW, M["stone_light"])
        self.add(frame_ring("corn_tw", -TW - 0.10, TW + 0.10, TY0 - 0.10, TY1 + 0.10,
                            CORN0, CORN1 - 0.01, 0.12, M["stone_mid"]), 0.012)
        self.add(frame_ring("corn_lip", -W2 - 0.14, W2 + 0.14, YB - 0.14, YF + 0.14,
                            CORN0 - 0.08, CORN0 + 0.005, 0.30, M["stone_dark"]), 0.006)
        # 齿饰：檐口下一排小方块，正立面在塔两侧
        for sx in (-1, 1):
            x = sx * (TW + 0.34)
            while abs(x) < W2 - 0.06:
                self.add(box("dentil", (x, YF + 0.10, CORN0 - 0.09), (0.14, 0.20, 0.14),
                             M["stone_mid"]), 0.003)
                x += sx * 0.34
            y = -3.30
            while y < 3.30:
                self.add(box("dentil", (sx * (W2 + 0.10), y, CORN0 - 0.09),
                             (0.20, 0.14, 0.14), M["stone_mid"]), 0.003)
                y += 0.34
        x = -4.50
        while x < 4.50:
            self.add(box("dentil", (x, YB - 0.10, CORN0 - 0.09), (0.14, 0.20, 0.14),
                         M["stone_mid"]), 0.003)
            x += 0.34
        # 四角隅石（交错凸出 20/30 mm）
        for sx in (-1, 1):
            for sy in (-1, 1):
                for i in range(8):
                    zz = 1.02 + i * 0.86
                    w = 0.56 if i % 2 else 0.62
                    self.add(box("quoin", (sx * (W2 - w * 0.5 + 0.015),
                                           sy * (YF - w * 0.5 + 0.015), zz),
                                 (w, w, 0.44), M["stone_mid"]), 0.006)
        # 塔身壁柱：0.72 → 11.05，把塔与主墙的接缝压住
        for sx in (-1, 1):
            self.add(box("pil_tw", (sx * TW, YF + 0.05, (H0 + T_TOP) * 0.5),
                         (0.30, 0.10, T_TOP - H0), M["stone_mid"]), 0.008)
            self.add(box("pil_tw_base", (sx * TW, YF + 0.08, 1.08),
                         (0.42, 0.16, 0.22), M["stone_light"]), 0.005)
            self.add(box("pil_tw_cap", (sx * TW, YF + 0.09, CORN0 - 0.20),
                         (0.42, 0.18, 0.26), M["stone_light"]), 0.005)

    # ── 3. 钟塔：塔身 / 门洞 / 钟座 / 钟亭 / 尖顶 ───────────────────────────
    def tower(self):
        M = self.M
        # 塔芯（门洞底面在 3.05）
        self.add(box("tw_core", (0, (TY0 + 3.05) * 0.5, (H0 + T_TOP) * 0.5),
                     (TW * 2, 3.05 - TY0, T_TOP - H0), M["stone_light"]), 0.034)
        dep, off = TY1 - 3.05, (TY1 + 3.05) * 0.5
        # 前脸左右墙垛
        self.add(extrude("tw_face_L", [(-TW, H0), (-GW, H0), (-GW, T_TOP), (-TW, T_TOP)],
                         "Y", dep, (0, 0), M["stone_light"], offset=off), 0.028)
        self.add(extrude("tw_face_R", [(GW, H0), (TW, H0), (TW, T_TOP), (GW, T_TOP)],
                         "Y", dep, (0, 0), M["stone_light"], offset=off), 0.028)
        top = [(-GW, SPRING), (-GW, T_TOP), (GW, T_TOP), (GW, SPRING)]
        for s in range(1, 8):
            a = math.pi * s / 8
            top.append((GW * math.cos(a), SPRING + GW * math.sin(a)))
        self.add(extrude("tw_face_T", top, "Y", dep, (0, 0), M["stone_light"],
                         offset=off), 0.028)
        # 拱券石 / 门套 / 拱心石
        self.add(arch_band("gate_arch", 0.0, SPRING, GW, GW + 0.24,
                           TY1, TY1 + 0.15, M["stone_mid"], segs=10), 0.014)
        for sgn in (-1, 1):
            self.add(box("gate_jamb", (sgn * (GW + 0.12), TY1 + 0.07,
                                       (H0 + SPRING) * 0.5),
                         (0.24, 0.14, SPRING - H0), M["stone_mid"]), 0.010)
        # 梯形拱心石（不是一块方砖）
        self.add(extrude("gate_key", [(-0.19, 4.38), (0.19, 4.38),
                                      (0.12, 4.68), (-0.12, 4.68)],
                         "Y", 0.18, (0, 0), M["stone_mid"], offset=TY1 + 0.09), 0.006)
        # 扇形窗发光面 + 铁艺
        # 半圆扇窗：不要用 arch_profile(straight=0)（它的底边有两个重复点，
        # 会三角化出一个黑楔子；v1 的入场近景里就有），手写一个干净半圆。
        gw_glow = (GW * 2 - 0.06) * 0.5
        glow_prof = [(-gw_glow, 0.0), (gw_glow, 0.0)]
        for s in range(1, 12):
            a = math.pi * s / 12
            glow_prof.append((gw_glow * math.cos(a), gw_glow * math.sin(a)))
        self.add(extrude("gate_glow", glow_prof, "Y", 0.05,
                         (0, SPRING), M["glow"], offset=3.07), 0.0)
        for dx in (-0.55, 0.0, 0.55):
            self.add(box("gate_bar", (dx, 3.13, SPRING + 0.48), (0.05, 0.05, 0.96),
                         M["iron"]), 0.002)
        self.add(box("gate_bar2", (0, 3.13, SPRING + 0.45), (1.90, 0.05, 0.05),
                     M["iron"]), 0.002)
        self.add(box("gate_transom", (0, 3.12, TDOOR + 0.06), (GW * 2 - 0.02, 0.10, 0.12),
                     M["wood_dark"]), 0.004)
        # 双开门：木框 + 蓝板 + 铁箍 + 金钉
        leaf = (GW * 2 - 0.18) * 0.5
        for sgn in (-1, 1):
            cx = sgn * leaf * 0.5
            self.add(box("gate_leaf", (cx, 3.10, H0 + TDOOR * 0.5),
                         (leaf, 0.08, TDOOR), M["team"]), 0.010)
            for yy, ww in ((3.145, 0.10),):
                self.add(box("gate_stile", (sgn * (leaf - 0.06), yy, H0 + TDOOR * 0.5),
                             (ww, 0.03, TDOOR - 0.06), M["wood_dark"]), 0.002)
            for zz, hh in ((H0 + 0.10, 0.16), (H0 + TDOOR - 0.075, 0.15)):
                self.add(box("gate_rail", (cx, 3.145, zz), (leaf - 0.03, 0.03, hh),
                             M["wood_dark"]), 0.002)
            for zz in (H0 + 0.52, H0 + 2.55):
                self.add(box("gate_strap", (cx, 3.155, zz), (leaf - 0.08, 0.03, 0.09),
                             M["iron"]), 0.003)
            for (dx, dz) in ((0.22, 0.62), (0.22, 2.45), (-0.22, 0.62), (-0.22, 2.45)):
                self.add(box("gate_stud", (cx + dx, 3.155, H0 + dz), (0.05, 0.03, 0.05),
                             M["gold"]), 0.002)
            self.add(ring_y("gate_ring", (cx + sgn * 0.24, 3.135, H0 + 1.30),
                            0.042, 0.072, 0.035, 8, M["gold"]), 0.003)
        self.add(box("gate_seam", (0, 3.15, H0 + TDOOR * 0.5), (0.05, 0.02, TDOOR - 0.02),
                     M["wood_dark"]), 0.002)
        # 门洞两侧壁灯
        for sgn in (-1, 1):
            self.add(box("lantern_arm", (sgn * 1.52, YF + 0.08, 4.05),
                         (0.28, 0.08, 0.07), M["iron"]), 0.003)
            self.add(box("lantern_glass", (sgn * 1.52, YF + 0.15, 3.95),
                         (0.20, 0.20, 0.26), M["glow"]), 0.004)
            self.add(box("lantern_frame", (sgn * 1.52, YF + 0.15, 4.07),
                         (0.26, 0.26, 0.05), M["iron"]), 0.003)
            self.add(box("lantern_base", (sgn * 1.52, YF + 0.15, 3.80),
                         (0.24, 0.24, 0.05), M["iron"]), 0.003)
        # 塔身徽记
        self.crest("crest_t", "Y", 0.0, YF + 0.014, 5.68, SHIELD_W, out=1)
        # 塔身百叶窗（正面）
        self.win_arch("louv_f", 0.0, 8.55, 1.70, 2.00, "Y", 1, YF, M["coal"], louver=True)

        # 钟座下的挑檐 + 塔身上部阵营色带（把塔和主楼的腰带绑在一起）
        self.add(frame_ring("tw_band", -TW - 0.12, TW + 0.12, TY0 - 0.12, TY1 + 0.12,
                            10.72, 10.90, 0.16, M["team"]), 0.006)
        self.add(frame_ring("tw_band_t", -TW - 0.14, TW + 0.14, TY0 - 0.14, TY1 + 0.14,
                            10.90, 10.945, 0.20, M["team_trim"]), 0.003)
        # 挑檐只向塔前/两侧出挑，后缘压在塔背里 —— 否则会从背后穿过上段屋脊
        self.add(frame_ring("clk_corbel", -TW - 0.20, TW + 0.20, TY0 + 0.02, TY1 + 0.20,
                            10.95, 11.10, 0.20, M["stone_mid"]), 0.010)
        # 钟座（比塔身外扩 0.20）
        self.add(box("tw_clock", (0, (TY0 + TY1) * 0.5, (CLK0 + CLK1) * 0.5),
                     (TW * 2 + 0.40, TY1 - TY0 + 0.40, CLK1 - CLK0),
                     M["stone_light"]), 0.028)
        self.add(frame_ring("clk_band", -TW - 0.22, TW + 0.22, TY0 - 0.22, TY1 + 0.22,
                            CLK0, CLK0 + 0.08, 0.10, M["gold"]), 0.004)
        self.add(frame_ring("clk_corn", -TW - 0.26, TW + 0.26, TY0 - 0.26, TY1 + 0.26,
                            CLK1 - 0.06, CLK1 + 0.10, 0.22, M["stone_mid"]), 0.008)
        # 三面钟（环/盘的后缘埋进钟座）
        self.clock_face("clock_f", (0.0, TY1 + 0.20, CLKZ), "Y")
        for sx in (-1, 1):
            self.clock_face("clock_s", (sx * (TW + 0.20), (TY0 + TY1) * 0.5, CLKZ), "X")
        # 露台女儿墙 + 四角石柱（金色只留给钟、铃、尖顶与旗）
        self.add(frame_ring("tw_para", -TW - 0.30, TW + 0.30, TY0 - 0.25, TY1 + 0.25,
                            PARA0, PARA1, 0.18, M["stone_mid"]), 0.010)
        self.add(frame_ring("tw_para_cap", -TW - 0.37, TW + 0.37, TY0 - 0.32, TY1 + 0.32,
                            PARA1, PARA1 + 0.09, 0.22, M["stone_light"]), 0.006)
        cy = (TY0 + TY1) * 0.5
        for sx in (-1, 1):
            for sy in (-1, 1):
                px, py = sx * (TW + 0.20), cy + sy * ((TY1 - TY0) * 0.5 + 0.16)
                self.add(box("tw_pier", (px, py, (PARA0 + PARA1 + 0.30) * 0.5),
                             (0.46, 0.46, PARA1 + 0.30 - PARA0), M["stone_light"]), 0.008)
                self.add(box("tw_pier_cap", (px, py, PARA1 + 0.36),
                             (0.56, 0.56, 0.12), M["stone_light"]), 0.005)
                self.add(frustum("tw_pier_tip", PARA1 + 0.42, PARA1 + 0.70,
                                 0.22, 0.22, 0.05, 0.05, px, py, M["stone_mid"]), 0.003)
        # 钟亭：四面石墙 + 拱形开口（不是四根孤柱撑一个盖），后面一块实墙当深色背景
        bf_cy = (TY0 + TY1) * 0.5
        BFX, BFY = 1.65, 1.55
        BFT = 0.22
        SILL0, SILL1 = BF0, BF0 + 0.30          # 13.35–13.65
        SPR = 13.80                              # 拱脚
        OPENW = 1.10                             # 拱半径（开口半宽）
        self.add(box("bf_floor", (0, bf_cy, BF0 - 0.05), (BFX * 2, BFY * 2, 0.10),
                     M["stone_dark"]), 0.006)
        # 前墙（开拱窗）；后墙单独做实墙
        for sy in (1,):
            wy = bf_cy + sy * (BFY - BFT * 0.5)
            self.add(box("bf_sill", (0, wy, (SILL0 + SILL1) * 0.5),
                         (BFX * 2, BFT, SILL1 - SILL0), M["stone_light"]), 0.008)
            for sx in (-1, 1):
                self.add(box("bf_jamb", (sx * (OPENW + (BFX - OPENW) * 0.5), wy,
                                        (SILL1 + SPR + 0.01) * 0.5),
                             ((BFX - OPENW), BFT, SPR - SILL1 + 0.01),
                             M["stone_light"]), 0.006)
            top = [(-BFX, SPR), (-BFX, BF1), (BFX, BF1), (BFX, SPR)]
            for s in range(1, 10):
                a = math.pi * s / 10
                top.append((OPENW * math.cos(a), SPR + OPENW * math.sin(a)))
            self.add(extrude("bf_top", top, "Y", BFT, (0, 0), M["stone_light"],
                             offset=wy), 0.010)
            self.add(arch_band("bf_arch", 0.0, SPR, OPENW, OPENW + 0.18,
                               wy + sy * (BFT * 0.5), wy + sy * (BFT * 0.5 + 0.07),
                               M["stone_mid"], segs=10), 0.006)
        # 侧墙（拱朝 ±X）
        for sx in (-1, 1):
            wx = sx * (BFX - BFT * 0.5)
            self.add(box("bf_sill", (wx, bf_cy, (SILL0 + SILL1) * 0.5),
                         (BFT, BFY * 2, SILL1 - SILL0), M["stone_light"]), 0.008)
            for sy in (-1, 1):
                self.add(box("bf_jamb", (wx, bf_cy + sy * (OPENW + (BFY - OPENW) * 0.5),
                                        (SILL1 + SPR) * 0.5),
                             (BFT, (BFY - OPENW), SPR - SILL1), M["stone_light"]), 0.006)
            top = [(bf_cy - BFY, SPR), (bf_cy - BFY, BF1 - 0.02),
                   (bf_cy + BFY, BF1 - 0.02), (bf_cy + BFY, SPR)]
            for s in range(1, 10):
                a = math.pi * s / 10
                top.append((bf_cy + OPENW * math.cos(a), SPR + OPENW * math.sin(a)))
            self.add(extrude("bf_top_s", top, "X", BFT, (0, 0), M["stone_light"],
                             offset=wx), 0.010)
            self.add(arch_band_x("bf_arch_s", bf_cy, SPR, OPENW, OPENW + 0.18,
                                 wx + sx * (BFT * 0.5), wx + sx * (BFT * 0.5 + 0.07),
                                 M["stone_mid"], segs=10), 0.006)
        # 后墙（实墙 + 内侧深色拱形衬板）：让铃有背景
        self.add(box("bf_back", (0, bf_cy - BFY + BFT * 0.5, (BF0 + BF1) * 0.5),
                     (BFX * 2, BFT, BF1 - BF0), M["stone_light"]), 0.008)
        self.add(extrude("bf_back_dark", arch_profile(OPENW * 2, 0.0, 10), "Y", 0.04,
                         (0, SPR), M["stone_dark"], offset=bf_cy - BFY + BFT + 0.02), 0.0)
        # 顶部石枋
        self.add(frame_ring("bf_corn", -BFX - 0.10, BFX + 0.10, bf_cy - BFY - 0.10,
                            bf_cy + BFY + 0.10, BF1, BF1 + 0.04, 0.30,
                            M["stone_mid"]), 0.008)
        # 吊钟梁 + 铜钟 + 钟舌
        self.add(box("bf_beam", (0, bf_cy, BF1 - 0.24), (BFX * 2 - 0.30, 0.16, 0.16),
                     M["wood_dark"]), 0.006)
        self.add(revolve("bf_bell", [(0.48, 0.0), (0.46, 0.08), (0.35, 0.32),
                                     (0.23, 0.56), (0.15, 0.72), (0.10, 0.80)], 12,
                         (0, bf_cy, 13.82), M["gold"]), 0.006, 1)
        self.add(box("bf_bell_top", (0, bf_cy, 14.60), (0.24, 0.10, 0.10),
                     M["iron"]), 0.003)
        self.add(box("bf_bell_chain", (0, bf_cy, 14.74), (0.06, 0.06, 0.26),
                     M["iron"]), 0.002)
        self.add(box("bf_clapper", (0, bf_cy, 14.00), (0.08, 0.08, 0.34),
                     M["iron"]), 0.002)
        # 尖顶：修长的四坡锥体 + 金脚线 + 四条戗脊 + 金顶 + 旗
        self.add(frame_ring("sp_base", -TW - 0.03, TW + 0.03, TY0 + 0.03, TY1 - 0.03,
                            SP0 - 0.06, SP0 + 0.02, 0.14, M["roof_edge"]), 0.005)
        self.add(frustum("tw_spire", SP0, SP1, TW * 2 + 0.10, TY1 - TY0 + 0.02,
                         0.10, 0.09, 0, bf_cy, M["roof"]), 0.018)
        self.add(frame_ring("sp_gold", -TW - 0.01, TW + 0.01, TY0 + 0.05, TY1 - 0.05,
                            SP0 + 0.02, SP0 + 0.07, 0.10, M["gold"]), 0.003)
        # 尖顶两道铅箍：给这块大三角一个尺度，不要读成一块黑锥
        base_w, base_d = TW + 0.05, (TY1 - TY0) * 0.5 + 0.01
        for (zz, tag) in ((16.30, "a"), (17.05, "b")):
            f = (zz - SP0) / (SP1 - SP0)
            hx = base_w + (0.05 - base_w) * f
            hy = base_d + (0.045 - base_d) * f
            self.add(frame_ring("sp_band_" + tag, -hx - 0.015, hx + 0.015,
                                bf_cy - hy - 0.015, bf_cy + hy + 0.015,
                                zz, zz + 0.05, 0.03, M["roof_edge"]), 0.002)
        for sx in (-1, 1):
            for sy in (-1, 1):
                self.add(beam("sp_hip", (sx * (TW + 0.02), bf_cy + sy * ((TY1 - TY0) * 0.5 - 0.02),
                                        SP0 + 0.02),
                              (sx * 0.03, bf_cy + sy * 0.02, SP1), 0.09, 0.06,
                              M["roof_edge"]), 0.003)
        self.add(revolve("sp_finial", [(0.0, 0.0), (0.10, 0.03), (0.14, 0.14),
                                       (0.08, 0.28), (0.0, 0.38)], 8,
                         (0, bf_cy, SP1 - 0.02), M["gold"]), 0.0, 1)
        self.add(revolve("flag_pole", [(0.045, 0.0), (0.038, FLAG_TOP - POLE_Z)], 6,
                         (0, bf_cy, POLE_Z), M["wood_dark"]), 0.0, 1)
        self.add(revolve("flag_tip", [(0.075, 0.0), (0.055, 0.05), (0.018, 0.11)], 8,
                         (0, bf_cy, FLAG_TOP - 0.02), M["gold"]), 0.0, 1)
        fw, fh = 1.06, 0.70
        prof = [(0.0, 0.0), (fw, -0.08), (fw * 0.78, -fh * 0.50),
                (fw, -fh * 0.92), (0.0, -fh)]
        self.add(extrude("flag_cloth", prof, "Y", 0.035, (0.0, FLAG_TOP - 0.06),
                         M["team"], offset=bf_cy), 0.004)
        self.add(box("flag_hoist", (0.030, bf_cy, FLAG_TOP - 0.06 - fh * 0.46),
                     (0.08, 0.06, fh * 0.92), M["team_trim"]), 0.003)
        self.crest("flag_crest", "Y", 0.46, bf_cy + 0.0125, FLAG_TOP - 0.58, 0.35)

    # ── 4. 钟面 ─────────────────────────────────────────────────────────────
    def clock_face(self, name, center, face):
        M = self.M
        cx, cy, cz = center
        if face == "Y":
            self.add(ring_y(name + "_ring", (cx, cy + 0.02, cz), 0.68, 0.84, 0.16, 20,
                            M["gold"]), 0.008)
            self.add(cyl(name + "_disc", (cx, cy + 0.03, cz), 0.69, 0.10, 20, M["coal"],
                         axis="Y"), 0.004)
            for k in range(12):
                a = TAU * k / 12
                self.add(box(name + "_tick", (cx + math.sin(a) * 0.57, cy + 0.095,
                                               cz + math.cos(a) * 0.57),
                             (0.055, 0.03, 0.10), M["gold"], rot=(0, -a, 0)), 0.002)
            for (ang, ln, w) in ((math.radians(-52), 0.48, 0.070),
                                 (math.radians(28), 0.32, 0.056)):
                self.add(box(name + "_hand",
                             (cx + math.sin(ang) * ln * 0.5, cy + 0.105,
                              cz + math.cos(ang) * ln * 0.5),
                             (w, 0.03, ln), M["gold"], rot=(0, -ang, 0)), 0.002)
            self.add(cyl(name + "_pin", (cx, cy + 0.11, cz), 0.055, 0.04, 8, M["gold"],
                         axis="Y"), 0.002)
        else:
            sgn = 1 if cx > 0 else -1
            self.add(ring_x(name + "_ring", (cx, cy, cz), 0.68, 0.84, 0.16, 20,
                            M["gold"]), 0.008)
            self.add(cyl(name + "_disc", (cx, cy, cz), 0.69, 0.10, 20, M["coal"],
                         axis="X"), 0.004)
            for k in range(12):
                a = TAU * k / 12
                self.add(box(name + "_tick", (cx + sgn * 0.095, cy + math.sin(a) * 0.57,
                                               cz + math.cos(a) * 0.57),
                             (0.03, 0.055, 0.10), M["gold"], rot=(-a, 0, 0)), 0.002)
            for (ang, ln, w) in ((math.radians(-52), 0.48, 0.070),
                                 (math.radians(28), 0.32, 0.056)):
                self.add(box(name + "_hand",
                             (cx + sgn * 0.105, cy + math.sin(ang) * ln * 0.5,
                              cz + math.cos(ang) * ln * 0.5),
                             (0.03, w, ln), M["gold"], rot=(-ang, 0, 0)), 0.002)
            self.add(cyl(name + "_pin", (cx + sgn * 0.11, cy, cz), 0.055, 0.04, 8,
                         M["gold"], axis="X"), 0.002)

    # ── 5. 窗 ───────────────────────────────────────────────────────────────
    def win_arch(self, name, u, cz, w, h, axis="Y", out=1, wall=None, mat=None,
                 louver=False):
        M = self.M
        mat = M["glass"] if mat is None else mat
        hw = w * 0.5
        straight = h - hw
        if axis == "Y":
            y0 = YF if wall is None else wall
            self.add(extrude(name + "_glass", arch_profile(w, straight, 8), "Y", 0.09,
                             (u, cz), mat, offset=y0 + out * 0.02), 0.0)
            self.add(arch_band(name + "_arch", u, cz + straight, hw, hw + 0.15,
                               y0 + out * 0.05, y0 + out * 0.16, M["stone_mid"],
                               segs=8), 0.010)
            for sgn in (-1, 1):
                self.add(box(name + "_jamb", (u + sgn * (hw + 0.075),
                                              y0 + out * 0.105, cz + straight * 0.5),
                             (0.15, 0.21, straight), M["stone_mid"]), 0.008)
            self.add(box(name + "_sill", (u, y0 + out * 0.10, cz - 0.03),
                         (w + 0.36, 0.24, 0.10), M["stone_light"]), 0.006)
            self.add(box(name + "_mull", (u, y0 + out * 0.075, cz + straight * 0.5),
                         (0.06, 0.06, straight), M["wood_dark"]), 0.002)
            if louver:
                for zz in (cz + 0.28, cz + 0.58, cz + 0.88, cz + 1.18):
                    self.add(box(name + "_slat", (u, y0 + out * 0.075, zz),
                                 (w - 0.14, 0.06, 0.07), M["wood_dark"]), 0.002)
        else:
            x0 = TW if wall is None else wall
            self.add(extrude(name + "_glass", arch_profile(w, straight, 8), "X", 0.09,
                             (u, cz), mat, offset=x0 + out * 0.02), 0.0)
            self.add(arch_band_x(name + "_arch", u, cz + straight, hw, hw + 0.15,
                                 x0 + out * 0.05, x0 + out * 0.16, M["stone_mid"],
                                 segs=8), 0.010)
            for sgn in (-1, 1):
                self.add(box(name + "_jamb", (x0 + out * 0.105,
                                              u + sgn * (hw + 0.075), cz + straight * 0.5),
                             (0.21, 0.15, straight), M["stone_mid"]), 0.008)
            self.add(box(name + "_sill", (x0 + out * 0.10, u, cz - 0.03),
                         (0.24, w + 0.36, 0.10), M["stone_light"]), 0.006)
            self.add(box(name + "_mull", (x0 + out * 0.075, u, cz + straight * 0.5),
                         (0.06, 0.06, straight), M["wood_dark"]), 0.002)
            if louver:
                for zz in (cz + 0.28, cz + 0.58, cz + 0.88, cz + 1.18):
                    self.add(box(name + "_slat", (x0 + out * 0.075, u, zz),
                                 (0.06, w - 0.14, 0.07), M["wood_dark"]), 0.002)

    def win_rect(self, name, u, cz, w, h, axis="Y", out=1, wall=None, mat=None,
                 big=False):
        M = self.M
        mat = M["glass"] if mat is None else mat
        hw = w * 0.5
        if axis == "Y":
            y0 = YF if wall is None else wall
            self.add(box(name + "_glass", (u, y0 + out * 0.02, cz + h * 0.5),
                         (w, 0.09, h), mat), 0.0)
            for sgn in (-1, 1):
                self.add(box(name + "_side", (u + sgn * (hw + 0.075),
                                              y0 + out * 0.10, cz + h * 0.5),
                             (0.15, 0.20, h + 0.20), M["stone_mid"]), 0.008)
            self.add(box(name + "_top", (u, y0 + out * 0.11, cz + h + 0.075),
                         (w + 0.30, 0.22, 0.15), M["stone_mid"]), 0.006)
            self.add(box(name + "_sill", (u, y0 + out * 0.12, cz - 0.055),
                         (w + 0.36, 0.24, 0.12), M["stone_light"]), 0.006)
            self.add(box(name + "_key", (u, y0 + out * 0.13, cz + h + 0.06),
                         (0.18, 0.26, 0.32), M["stone_light"]), 0.004)
            self.add(box(name + "_mull", (u, y0 + out * 0.075, cz + h * 0.5 - 0.03),
                         (0.06, 0.06, h - 0.06), M["wood_dark"]), 0.002)
            self.add(box(name + "_trans", (u, y0 + out * 0.070, cz + h * 0.62),
                         (w - 0.06, 0.06, 0.06), M["wood_dark"]), 0.002)
        else:
            x0 = TW if wall is None else wall
            self.add(box(name + "_glass", (x0 + out * 0.02, u, cz + h * 0.5),
                         (0.09, w, h), mat), 0.0)
            for sgn in (-1, 1):
                self.add(box(name + "_side", (x0 + out * 0.10,
                                              u + sgn * (hw + 0.075), cz + h * 0.5),
                             (0.20, 0.15, h + 0.20), M["stone_mid"]), 0.008)
            self.add(box(name + "_top", (x0 + out * 0.11, u, cz + h + 0.075),
                         (0.22, w + 0.30, 0.15), M["stone_mid"]), 0.006)
            self.add(box(name + "_sill", (x0 + out * 0.12, u, cz - 0.055),
                         (0.24, w + 0.36, 0.12), M["stone_light"]), 0.006)
            self.add(box(name + "_key", (x0 + out * 0.13, u, cz + h + 0.06),
                         (0.26, 0.18, 0.32), M["stone_light"]), 0.004)
            self.add(box(name + "_mull", (x0 + out * 0.075, u, cz + h * 0.5 - 0.03),
                         (0.06, 0.06, h - 0.06), M["wood_dark"]), 0.002)
            self.add(box(name + "_trans", (x0 + out * 0.070, u, cz + h * 0.62),
                         (0.06, w - 0.06, 0.06), M["wood_dark"]), 0.002)

    def windows(self):
        M = self.M
        # 主楼前脸：塔身两侧各一扇拱窗 + 一扇十字窗
        for sx in (-1, 1):
            x = sx * 3.35
            self.win_arch("win_f", x, 1.62, 1.25, 2.45, "Y", 1, YF)
            self.win_rect("win_f2", x, 5.55, 1.35, 1.60, "Y", 1, YF)
        # 侧墙（X 向的 u 是 Y 坐标）
        for sx in (-1, 1):
            for yy in (-1.65, 1.65):
                self.win_arch("win_sa", yy, 1.62, 1.20, 2.45, "X", sx, sx * W2)
                self.win_rect("win_sb", yy, 5.55, 1.30, 1.60, "X", sx, sx * W2)
        # 侧墙垂旗（两扇高窗之间）
        for sx in (-1, 1):
            self.wallbanner("wbanner_s" + ("R" if sx > 0 else "L"),
                            (sx * (W2 + 0.30), 0.0, 5.95), "X", 1.20, 1.55)
        # 后墙中央圆窗（附楼脊之上，只露在屋脊以上）；后墙两侧留给隅石，不塞窗
        # （后墙窄条只有 1.6 m，窗框会撞隅石 —— 见 v2 体检记录）
        self.add(ring_y("oculus_b_ring", (0.0, YB - 0.04, 6.90), 0.26, 0.38, 0.10, 16,
                        M["gold"]), 0.006)
        self.add(cyl("oculus_b_disc", (0.0, YB - 0.02, 6.90), 0.27, 0.06, 16, M["coal"],
                     axis="Y"), 0.003)

    def rib(self, name, p0, p1, p3, p2, n, w, t, mat, inset=0.10, lift=0.028):
        for ob in rib_quad(name, p0, p1, p3, p2, n, w, t, mat, inset, lift):
            self.add(ob, 0.0)

    # ── 6. 后附楼 ───────────────────────────────────────────────────────────
    def annex(self):
        M = self.M
        cy = (AY0 + AY1) * 0.5
        self.add(box("annex_mass", (0, cy, (H0 + ATOP) * 0.5),
                     (AX * 2, AY1 - AY0, ATOP - H0), M["stone_light"]), 0.030)
        self.add(frame_ring("annex_dado", -AX - 0.05, AX + 0.05, AY0 - 0.05, AY1 + 0.04,
                            H0, DADO - 0.02, 0.10, M["stone_mid"]), 0.008)
        self.add(frame_ring("annex_cap", -AX - 0.08, AX + 0.08, AY0 - 0.08, AY1 + 0.04,
                            DADO - 0.07, DADO + 0.02, 0.11, M["stone_dark"]), 0.006)
        self.add(frame_ring("annex_corn", -AX - 0.16, AX + 0.16, AY0 - 0.16, AY1 + 0.04,
                            ATOP - 0.18, ATOP + 0.02, 0.16, M["stone_mid"]), 0.008)
        # 附楼屋面：四坡（前坡贴主墙，被主楼挡住）
        ze, zr = ATOP + 0.04, A_RIDGE
        p_front = [(-A_E_X, A_E_Y1, ze), (A_E_X, A_E_Y1, ze),
                   (A_RX, A_RY, zr), (-A_RX, A_RY, zr)]
        p_back = [(-A_E_X, A_E_Y0, ze), (A_E_X, A_E_Y0, ze),
                  (A_RX, A_RY, zr), (-A_RX, A_RY, zr)]
        p_l = [(-A_E_X, A_E_Y1, ze), (-A_E_X, A_E_Y0, ze), (-A_RX, A_RY, zr)]
        p_r = [(A_E_X, A_E_Y1, ze), (A_E_X, A_E_Y0, ze), (A_RX, A_RY, zr)]
        for nm, pp in (("annex_roof_f", p_front), ("annex_roof_b", p_back),
                       ("annex_roof_l", p_l), ("annex_roof_r", p_r)):
            self.add(slab(nm, pp, 0.16, M["roof"]), 0.0)
        self.rib("annex_tile", p_back[0], p_back[1], p_back[3], p_back[2], 5,
                 0.065, 0.050, M["roof"], inset=0.08, lift=0.035)
        self.rib("annex_tilef", p_front[0], p_front[1], p_front[3], p_front[2], 5,
                 0.065, 0.050, M["roof"], inset=0.08, lift=0.035)
        self.add(box("annex_ridge", (0, A_RY, zr + 0.02), (A_RX * 2 + 0.10, 0.20, 0.14),
                     M["roof_edge"]), 0.004)
        for sx in (-1, 1):
            self.add(beam("annex_hip", (sx * A_E_X, A_E_Y0, ze + 0.02),
                          (sx * A_RX, A_RY, zr), 0.12, 0.09, M["roof_edge"]), 0.003)
            self.add(beam("annex_hip_f", (sx * A_E_X, A_E_Y1, ze + 0.02),
                          (sx * A_RX, A_RY, zr), 0.12, 0.09, M["roof_edge"]), 0.003)
        self.add(frame_ring("annex_eave", -A_E_X - 0.02, A_E_X + 0.02, A_E_Y0 - 0.02,
                            A_E_Y1, ze - 0.18, ze, 0.22, M["roof_edge"]), 0.004)
        # 附楼后墙：三扇拱窗 + 中央圆窗（盾牌函数只朝 +Y，后墙改用圆窗）
        self.win_arch("a_win_c", 0.0, 1.58, 1.35, 2.05, "Y", -1, AY0)
        for sx in (-1, 1):
            self.win_arch("a_win_s", sx * 1.85, 1.58, 0.95, 1.95, "Y", -1, AY0)
            self.win_arch("a_win_x", -5.35, 1.58, 0.95, 1.95, "X", sx, sx * AX)
        self.add(ring_y("oculus_a_ring", (0.0, AY0 - 0.04, 4.02), 0.20, 0.30, 0.10, 16,
                        M["gold"]), 0.006)
        self.add(cyl("oculus_a_disc", (0.0, AY0 - 0.02, 4.02), 0.21, 0.06, 16, M["coal"],
                     axis="Y"), 0.003)
        # 附楼与主楼交接处的排水沟（一条压在主墙上的铅皮）
        self.add(box("annex_gutter", (0, AY1 - 0.02, ATOP + 0.03), (AX * 2 + 0.10, 0.24, 0.07),
                     M["roof_edge"]), 0.004)
        # 附楼烟囱：给后部一个竖向标点，也解释"议事厅有壁炉"
        self.add(box("annex_chimney", (-2.15, -6.35, 6.30), (0.56, 0.56, 2.30),
                     M["stone_mid"]), 0.010)
        self.add(box("annex_chimney_band", (-2.15, -6.35, 6.98), (0.64, 0.64, 0.16),
                     M["stone_light"]), 0.006)
        self.add(box("annex_chimney_cap", (-2.15, -6.35, 7.50), (0.74, 0.74, 0.16),
                     M["stone_dark"]), 0.006)
        self.add(box("annex_chimney_flue", (-2.15, -6.35, 7.60), (0.34, 0.34, 0.10),
                     M["coal"]), 0.003)

    # ── 7. 主屋面（两段孟莎四坡）────────────────────────────────────────────
    def roofs(self):
        M = self.M
        # 下段四坡
        lf = [(-EAVE_X, EAVE_Y, EAVE_Z), (-TW, EAVE_Y, EAVE_Z),
              (-TW, BRK_Y, BRK_Z), (-BRK_X, BRK_Y, BRK_Z)]
        rf = [(-p[0], p[1], p[2]) for p in lf]
        rb = [(-EAVE_X, -EAVE_Y, EAVE_Z), (EAVE_X, -EAVE_Y, EAVE_Z),
              (BRK_X, -BRK_Y, BRK_Z), (-BRK_X, -BRK_Y, BRK_Z)]
        lh = [(-EAVE_X, EAVE_Y, EAVE_Z), (-EAVE_X, -EAVE_Y, EAVE_Z),
              (-BRK_X, -BRK_Y, BRK_Z), (-BRK_X, BRK_Y, BRK_Z)]
        rh = [(-p[0], p[1], p[2]) for p in lh]
        for nm, pp in (("roof_lo_fL", lf), ("roof_lo_fR", rf), ("roof_lo_b", rb),
                       ("roof_lo_hL", lh), ("roof_lo_hR", rh)):
            self.add(slab(nm, pp, ROOF_T, M["roof"]), 0.0)
        self.rib("tile_lo_fL", lf[0], lf[1], lf[3], lf[2], 2, 0.065, 0.050, M["roof"])
        self.rib("tile_lo_fR", rf[0], rf[1], rf[3], rf[2], 2, 0.065, 0.050, M["roof"])
        self.rib("tile_lo_b", rb[0], rb[1], rb[3], rb[2], 6, 0.065, 0.050, M["roof"])
        self.rib("tile_lo_hL", lh[0], lh[1], lh[3], lh[2], 2, 0.065, 0.050, M["roof"])
        self.rib("tile_lo_hR", rh[0], rh[1], rh[3], rh[2], 2, 0.065, 0.050, M["roof"])
        # 上段四坡（塔身把前坡切成两片）
        ufL = [(-BRK_X, BRK_Y, BRK_Z), (-TW, BRK_Y, BRK_Z),
               (-TW, TY0, 10.86), (-RIDGE_X, 0.0, RIDGE_Z)]
        ufR = [(-p[0], p[1], p[2]) for p in ufL]
        ub = [(-BRK_X, -BRK_Y, BRK_Z), (BRK_X, -BRK_Y, BRK_Z),
              (RIDGE_X, 0.0, RIDGE_Z), (-RIDGE_X, 0.0, RIDGE_Z)]
        uhL = [(-BRK_X, BRK_Y, BRK_Z), (-BRK_X, -BRK_Y, BRK_Z), (-RIDGE_X, 0.0, RIDGE_Z)]
        uhR = [(-p[0], p[1], p[2]) for p in uhL]
        # 塔后的一小条前坡（补齐塔背与正脊之间的 0.20 m）
        us = [(-TW, TY0, 10.86), (TW, TY0, 10.86), (RIDGE_X, 0.0, RIDGE_Z),
              (-RIDGE_X, 0.0, RIDGE_Z)]
        for nm, pp in (("roof_up_fL", ufL), ("roof_up_fR", ufR), ("roof_up_b", ub),
                       ("roof_up_hL", uhL), ("roof_up_hR", uhR), ("roof_up_s", us)):
            self.add(slab(nm, pp, ROOF_T, M["roof"]), 0.0)
        self.rib("tile_up_fL", ufL[0], ufL[1], ufL[3], ufL[2], 1, 0.065, 0.050, M["roof"])
        self.rib("tile_up_fR", ufR[0], ufR[1], ufR[3], ufR[2], 1, 0.065, 0.050, M["roof"])
        self.rib("tile_up_b", ub[0], ub[1], ub[3], ub[2], 4, 0.065, 0.050, M["roof"])
        self.rib("tile_up_hL", uhL[0], uhL[1], uhL[2], uhL[2], 1, 0.065, 0.050, M["roof"])
        self.rib("tile_up_hR", uhR[0], uhR[1], uhR[2], uhR[2], 1, 0.065, 0.050, M["roof"])
        # 折脊铅压条 + 檐口压条
        self.add(frame_ring("break_roll", -BRK_X - 0.03, BRK_X + 0.03,
                            -BRK_Y - 0.03, BRK_Y + 0.03, BRK_Z, BRK_Z + 0.07,
                            0.10, M["roof_edge"]), 0.004)
        self.add(frame_ring("eave_rim", -EAVE_X - 0.02, EAVE_X + 0.02,
                            -EAVE_Y - 0.02, EAVE_Y + 0.02, EAVE_Z - 0.18, EAVE_Z,
                            0.18, M["roof_edge"]), 0.006)
        # 正脊（塔身两侧各一段，中间让塔背墙）
        for sx in (-1, 1):
            self.add(box("ridge_c", (sx * (RIDGE_X + TW) * 0.5, 0, RIDGE_Z + 0.02),
                         (RIDGE_X - TW, 0.20, 0.12), M["roof_edge"]), 0.004)
        # 下段戗脊
        for sx in (-1, 1):
            for sy in (-1, 1):
                self.add(beam("hip_lo", (sx * EAVE_X, sy * EAVE_Y, EAVE_Z + 0.02),
                              (sx * BRK_X, sy * BRK_Y, BRK_Z), 0.11, 0.08,
                              M["roof_edge"]), 0.003)
                self.add(beam("hip_up", (sx * BRK_X, sy * BRK_Y, BRK_Z + 0.02),
                              (sx * RIDGE_X, 0.0, RIDGE_Z), 0.11, 0.08,
                              M["roof_edge"]), 0.003)

    # ── 8. 广场陈设 ─────────────────────────────────────────────────────────
    def props(self):
        M = self.M
        z = PROP_Z
        # 火盆（入口前的暖光）
        for sx in (-1, 1):
            px, py = sx * 2.62, 4.82
            self.add(box("braz_ped", (px, py, z + 0.30), (0.44, 0.44, 0.60),
                         M["stone_mid"]), 0.008)
            self.add(box("braz_ped_t", (px, py, z + 0.63), (0.52, 0.52, 0.08),
                         M["stone_dark"]), 0.005)
            self.add(revolve("braz_bowl", [(0.16, 0.0), (0.30, 0.09), (0.34, 0.22),
                                           (0.32, 0.24)], 8,
                             (px, py, z + 0.65), M["iron"]), 0.006)
            self.add(revolve("braz_coal", [(0.0, 0.0), (0.26, 0.02), (0.26, 0.08),
                                           (0.0, 0.09)], 8,
                             (px, py, z + 0.89), M["coal"]), 0.003)
            self.add(lathe("braz_flame", [(0.0, z + 0.90, px, py),
                                          (0.17, z + 0.96, px, py),
                                          (0.12, z + 1.16, px + 0.02, py),
                                          (0.0, z + 1.34, px + 0.04, py)],
                           6, M["flame_out"]), 0.0)
            self.add(lathe("braz_core", [(0.0, z + 0.90, px, py),
                                         (0.09, z + 0.95, px, py),
                                         (0.05, z + 1.12, px + 0.01, py),
                                         (0.0, z + 1.22, px + 0.02, py)],
                           6, M["flame_in"]), 0.0)
        # 公告板
        bx, by = -4.05, 6.25
        for sgn in (-1, 1):
            self.add(box("board_post", (bx + sgn * 0.80, by, z + 0.76),
                         (0.16, 0.16, 1.52), M["wood_dark"]), 0.006)
        self.add(box("board_face", (bx, by, z + 1.08), (1.76, 0.10, 0.96),
                     M["wood_warm"], rot=(-0.13, 0, 0)), 0.008)
        self.add(box("board_trim", (bx, by, z + 1.56), (1.92, 0.15, 0.10),
                     M["wood_dark"], rot=(-0.13, 0, 0)), 0.004)
        self.add(box("board_foot", (bx, by + 0.06, z + 0.05), (1.90, 0.34, 0.10),
                     M["stone_mid"]), 0.004)
        for (dx, dz, w, h) in ((-0.50, 0.10, 0.32, 0.40), (0.06, 0.02, 0.28, 0.32),
                               (0.50, 0.11, 0.30, 0.36)):
            self.add(box("board_note", (bx + dx, by + 0.063, z + 1.08 + dz),
                         (w, 0.018, h), M["paving"], rot=(-0.13, 0, 0)), 0.002)
        # 木桶 / 木箱
        self.barrel("barrel_a", (4.16, 5.72), 0.32, 0.74, z)
        self.barrel("barrel_b", (4.50, 6.38), 0.29, 0.66, z)
        self.crate("crate_a", (4.42, 5.05), 0.60, 0.55, z)
        # 两支旗杆
        for sx in (-1, 1):
            px, py = sx * 4.58, 7.78
            self.add(box("banner_pole_base", (px, py, z + 0.10), (0.42, 0.42, 0.20),
                         M["stone_mid"]), 0.006)
            self.add(revolve("banner_pole", [(0.075, 0.0), (0.060, 3.05)], 8,
                             (px, py, z + 0.18), M["wood_dark"]), 0.0, 1)
            self.add(revolve("banner_pole_tip", [(0.105, 0.0), (0.070, 0.07),
                                                 (0.02, 0.15)], 8,
                             (px, py, z + 3.22), M["gold"]), 0.0, 1)
            self.add(box("banner_arm", (px - sx * 0.42, py, z + 3.00),
                         (0.90, 0.07, 0.07), M["wood_dark"]), 0.003)
            self.add(box("banner_cloth", (px - sx * 0.48, py, z + 2.36),
                         (0.64, 0.05, 1.22), M["team"]), 0.005)
            self.add(box("banner_trim", (px - sx * 0.48, py, z + 1.78),
                         (0.66, 0.07, 0.08), M["team_trim"]), 0.003)
            for k in (-1, 1):
                self.add(box("banner_ring", (px - sx * 0.48 + k * 0.23, py, z + 2.97),
                             (0.05, 0.05, 0.09), M["iron"]), 0.002)
        # 草簇 / 碎石
        for (gx, gy, gz) in ((-5.02, 4.36, z), (5.02, 4.36, z),
                             (-5.02, 8.18, z), (5.02, 8.18, z),
                             (-4.95, -7.28, H0), (4.95, -7.28, H0)):
            for k in range(4):
                ang = -0.5 + k * 0.33
                self.add(box("grass", (gx + math.sin(ang) * 0.10, gy + math.cos(ang) * 0.08,
                                       gz + 0.17), (0.035, 0.035, 0.34),
                             M["moss"], rot=(0.22, ang, 0.0)), 0.0)
        for (px, py, gz) in ((3.95, 8.16, z), (-3.62, 8.24, z), (4.88, 4.42, z)):
            self.add(box("pebble", (px, py, gz + 0.035), (0.20, 0.14, 0.07),
                         M["stone_mid"], rot=(0, 0.3, 0.4)), 0.004)

    # ── 9. 组装 / 收尾 ──────────────────────────────────────────────────────
    def build(self):
        for step in (self.base, self.mass, self.tower, self.annex, self.windows,
                     self.roofs, self.props):
            step()
        return self

    def finalize(self, bevel=True):
        skip_cc = ("roof_", "tile_", "ridge_", "hip_", "break_", "eave_", "corn_",
                   "dado", "string", "band_", "quoin", "dentil", "pil_", "win",
                   "gate_", "clock_", "louv", "wbanner", "crest", "shield", "flag",
                   "sp_", "bf_", "tw_clock", "tw_para", "tw_pier", "annex_",
                   "step", "pave", "terrace_", "plinth", "newel", "land_", "threshold",
                   "board", "braz", "barrel", "crate", "banner_", "grass", "pebble",
                   "lantern", "a_win")
        for (ob, bev, sub, seg) in self.items:
            co = ob.data.vertices
            dims = [max(v.co[i] for v in co) - min(v.co[i] for v in co) for i in range(3)]
            vol = dims[0] * dims[1] * dims[2]
            chunky = min(dims) >= 0.10 and vol >= 0.12
            n = ob.name
            if self.smooth:
                cc = 1 if (chunky and not n.startswith(skip_cc)) else 0
                L.finalize(ob, bevel=max(bev, 0.008), seg=1, sub=cc, flat=False)
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
