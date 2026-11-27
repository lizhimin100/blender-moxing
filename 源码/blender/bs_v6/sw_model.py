"""
sw_model.py —— 蒸汽车坊 v3：长坡车间 · 正面三角山墙 · 锅炉房与烟囱 · 双扇全关的大门

v1 被否的两条：
  ① 门前那一整套"龙门吊 + 半成品蒸汽车 + 木车"是**展示**，不是建筑，全部删掉；
  ② 三级采光盒叠成"现代办公楼"，形体太怪。改成 **一条长屋 + 山墙朝前的三角头**
     （WC3 人族车间那种读法）：屋顶是这八座里唯一的一条 45° 长坡，
     正面是一个 7.2 × 3.6 的三角形山墙，山墙里嵌圆窗、挂旗、挑出吊梁。

v3 只改门：
  v2 的左扇向内开 55°，从正面看是门洞里一个黑洞 + 一块歪出来的门板，
  读作"门没做完"。现在双扇全关，用**通长铁箍两道 + 中缝压条 + 门闩 + 对称门环**
  把它读成一扇锁死的车间大门；门厅里的炉光块随之删掉（门关着，谁也看不见）。

形体（四层，从下往上）：
  ① 石台 + 浅色石墙 + 深木压梁：一条 7.2 × 12.0 的长屋，长:宽 = 1.67；
  ② 45° 长坡石板瓦，脊线 12.4 m，屋面上三只平嵌天窗 + 脊上一座排气塔 + 脊端风向标；
  ③ 近侧（建模期 +X，画面右侧）一条 2.25 × 7.0 的**锅炉房**披屋：单坡、比主檐低一级，
     立式铆接锅炉从它的屋面里穿出来，后面接砖石烟囱（本座最高点 9.72）；
  ④ 山墙上的汽笛式圆窗、吊装横梁（滑轮 + 铁链 + 吊钩）、垂旗、金冠盾徽。

蒸汽元素全在"建筑本体"上，不摆道具：
  锅炉（三道铜箍 + 表盘 + 汽笛 + 安全阀）、进车间的蒸汽管（带阀门轮）、
  通烟囱的烟道、炉膛口（铁火箱 + 炉火 + 关着的铁栅门）、三只天窗、排气塔、风向标。

明度秩序（与前七座同一套节拍）：
  夯土场地 → 中灰台基 → **亮**压顶 → **亮**石墙 → **暗**木压梁 / 檐口
  → **近黑**石板瓦 → 铁 / 铜机器 → 队色点睛。
  队色只染五条"结构线"：山墙封檐板 ×2、垂旗、门扇上板、烟囱双箍、锅炉房门楣。

坐标：X 右、Y 前（+Y = 正面）、Z 上；原点在占地中心，z = 0 地面。
交付前整体沿 X 镜像一次（与另七座一致）→ 相机看到的近侧是**建模期 +X**。
"""
import math
from math import tau as TAU

import bpy
from mathutils import Vector

import bslib as L
import br_model as BR
from bslib import (arch_band, beam, box, cyl, extrude, frustum, mesh_obj,
                   revolve, ring_y, taper_box, tube_band)
from br_model import arch_profile, mirror_x, vcyl

# ── 场地 ────────────────────────────────────────────────────────────────────
YX0, YX1 = -4.60, 7.20
YY0, YY1 = -7.05, 7.05
G_Z = 0.20                       # 夯土面
RIM_Z = 0.34                     # 石牙子顶

# ── 主体：7.2 × 12.0 的长屋 ─────────────────────────────────────────────────
HX = 3.60                        # 半宽
HY0, HY1 = -6.60, 5.40           # 后墙 / 前墙（外表面）
WT = 0.26                        # 墙厚
PL_Z1 = 1.06                     # 台基石身顶
PC_Z1 = 1.20                     # 压顶顶 = 墙脚
WZ1 = 5.18                       # 墙顶 = 屋面底面（x = HX 处）

PITCH = 1.0                      # 45°
RIDGE_IN = WZ1 + HX * PITCH      # 8.78  屋面底面的脊
T_ROOF = 0.226                   # 屋面的竖向厚度（垂直厚 0.16）
RIDGE_OUT = RIDGE_IN + T_ROOF    # 9.006 屋面外表面的脊
ROOF_X = HX + 0.42               # 4.02  檐口外挑
ROOF_OY = 0.22                   # 前后出檐
ROOF_Y0 = HY0 - ROOF_OY
ROOF_Y1 = HY1 + ROOF_OY
EAVE_OUT = RIDGE_OUT - ROOF_X    # 4.986
EAVE_IN = RIDGE_IN - ROOF_X      # 4.760

# ── 门（真开洞：墙拆成左右墩 + 拱上，洞内做一个门厅）────────────────────────
DHW = 1.28                       # 半宽
DSPRING = 2.95                   # 起拱线
DAPEX = DSPRING + DHW            # 4.23

# ── 锅炉房（近侧披屋）───────────────────────────────────────────────────────
AX0, AX1 = 3.60, 5.85
AY0, AY1 = -6.00, 1.00
AZ0 = 0.56                       # 墙脚（压顶顶面）
AROOF_X1 = AX1 + 0.20            # 6.05 外檐
AROOF_HI = 4.55                  # 靠主墙一侧的屋面外表面
AROOF_LO = 3.45                  # 外檐屋面外表面
A_SLOPE = (AROOF_HI - AROOF_LO) / (AROOF_X1 - AX0)          # 0.44898
A_T = 0.17                       # 屋面竖向厚度
A_WALL_TOP = 3.37                # 外墙顶 = 屋面底面（x = AX1）

# ── 烟囱 ────────────────────────────────────────────────────────────────────
CHX, CHY = 4.95, -5.15
CH_W = 1.02
CH_TOP = 10.06

# ── 锅炉 ────────────────────────────────────────────────────────────────────
BOX_, BOY = 4.83, -2.45
BOIL_R = 0.70                     # 半径受两道限制：主檐封板外沿 4.06 / 外墙内表面 5.59

# ── 吊装梁 ──────────────────────────────────────────────────────────────────
CR_X = 1.95
CR_Z = 5.60
CR_Y1 = 7.30


def z_roof(x):
    return RIDGE_OUT - abs(x) * PITCH


def z_aroof(x):
    """锅炉房屋面外表面。"""
    return AROOF_HI - (x - AX0) * A_SLOPE


def z_aroof_in(x):
    return z_aroof(x) - A_T


# ── 通用构造 ────────────────────────────────────────────────────────────────
def ring3(name, center, r_in, r_out, thick, seg, mat, normal="Z", phase=0.0):
    """任意朝向的圆环带（法线 = normal）。"""
    cx, cy, cz = center
    if normal == "Z":
        u, v, w = (1, 0, 0), (0, 1, 0), (0, 0, 1)
    elif normal == "Y":
        u, v, w = (1, 0, 0), (0, 0, 1), (0, 1, 0)
    else:
        u, v, w = (0, 1, 0), (0, 0, 1), (1, 0, 0)
    verts, faces = [], []
    for s in range(seg):
        a = phase + TAU * s / seg
        ca, sa = math.cos(a), math.sin(a)
        for (r, dw) in ((r_in, -thick * 0.5), (r_out, -thick * 0.5),
                        (r_out, thick * 0.5), (r_in, thick * 0.5)):
            verts.append((cx + r * ca * u[0] + r * sa * v[0] + dw * w[0],
                          cy + r * ca * u[1] + r * sa * v[1] + dw * w[1],
                          cz + r * ca * u[2] + r * sa * v[2] + dw * w[2]))
    for s in range(seg):
        b, b2 = s * 4, ((s + 1) % seg) * 4
        faces += [(b + 0, b2 + 0, b2 + 1, b + 1), (b + 1, b2 + 1, b2 + 2, b + 2),
                  (b + 2, b2 + 2, b2 + 3, b + 3), (b + 3, b2 + 3, b2 + 0, b + 0)]
    return mesh_obj(name, verts, faces, mat)


def rod(name, p0, p1, r, seg, mat, phase=0.0):
    """任意方向的圆管（沿 p0→p1）。"""
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    ln = d.length
    if ln < 1e-6:
        return None
    prof = [(r * math.cos(phase + TAU * i / seg),
             r * math.sin(phase + TAU * i / seg)) for i in range(seg)]
    ob = extrude(name, prof, "Y", ln, (0.0, 0.0), mat)
    ob.rotation_euler = d.normalized().to_track_quat("Y", "Z").to_euler()
    ob.location = (p0 + p1) * 0.5
    return ob


def ball(name, center, r, mat, seg=8):
    """多面球（管件弯头 / 阀帽）：一个 6 环回转体，平着色。"""
    prof = [(0.0, -r), (0.58 * r, -0.74 * r), (0.96 * r, -0.26 * r),
            (0.96 * r, 0.26 * r), (0.58 * r, 0.74 * r), (0.0, r)]
    return revolve(name, prof, seg, center, mat)


def prism(name, prof, axis, a0, a1, mat):
    """二维多边形沿 axis 从 a0 拉到 a1；prof 的坐标按该轴的另外两轴给。"""
    return extrude(name, prof, axis, a1 - a0, (0.0, 0.0), mat,
                   offset=(a0 + a1) * 0.5)


class Model(BR.Model):

    # ── 0. 窗（贴面：石窗台 + 深木框 + 玻璃 + 十字棂）─────────────────────
    def win_x(self, name, cy, cz, w, h, x, out=1, mat=None, shutters=False):
        M = self.M
        mat = M["glass"] if mat is None else mat
        self.add(box(name, (x + out * 0.03, cy, cz), (0.06, w, h), mat), 0.0)
        for sgn in (-1, 1):
            self.add(box(name + "_fL", (x + out * 0.07, cy + sgn * (w * 0.5 + 0.07), cz),
                         (0.14, 0.14, h + 0.28), M["wood_dark"]), 0.008)
            self.add(box(name + "_fT", (x + out * 0.07, cy, cz + sgn * (h * 0.5 + 0.08)),
                         (0.14, w + 0.28, 0.15), M["wood_dark"]), 0.008)
        self.add(box(name + "_bar", (x + out * 0.10, cy, cz), (0.06, 0.05, h),
                     M["wood_dark"]), 0.003)
        self.add(box(name + "_sill", (x + out * 0.10, cy, cz - h * 0.5 - 0.10),
                     (0.24, w + 0.40, 0.11), M["stone_light"]), 0.008)
        if shutters:
            for sgn in (-1, 1):
                self.add(box(name + "_shut", (x + out * 0.06,
                                              cy + sgn * (w * 0.5 + 0.34), cz),
                             (0.05, 0.38, h + 0.06), M["team"]), 0.006)
                self.add(box(name + "_shut_b", (x + out * 0.09,
                                                cy + sgn * (w * 0.5 + 0.34), cz),
                             (0.03, 0.30, 0.07), M["team_trim"]), 0.002)

    def win_y(self, name, cx, cz, w, h, y, out=1, mat=None):
        M = self.M
        mat = M["glass"] if mat is None else mat
        self.add(box(name, (cx, y + out * 0.03, cz), (w, 0.06, h), mat), 0.0)
        for sgn in (-1, 1):
            self.add(box(name + "_fL", (cx + sgn * (w * 0.5 + 0.07), y + out * 0.07, cz),
                         (0.14, 0.14, h + 0.28), M["wood_dark"]), 0.008)
            self.add(box(name + "_fT", (cx, y + out * 0.07, cz + sgn * (h * 0.5 + 0.08)),
                         (w + 0.28, 0.14, 0.15), M["wood_dark"]), 0.008)
        self.add(box(name + "_bar", (cx, y + out * 0.10, cz), (0.05, 0.06, h),
                     M["wood_dark"]), 0.003)
        self.add(box(name + "_sill", (cx, y + out * 0.10, cz - h * 0.5 - 0.10),
                     (w + 0.40, 0.24, 0.11), M["stone_light"]), 0.008)

    # ── 1. 场地 ───────────────────────────────────────────────────────────
    def yard(self):
        M = self.M
        self.add(box("yard_soil", ((YX0 + YX1) * 0.5, (YY0 + YY1) * 0.5, G_Z * 0.5),
                     (YX1 - YX0, YY1 - YY0, G_Z), M["earth"]), 0.018)
        # 石牙子：四条，顶面 0.34；左右两条在后端收 0.18，避开后牙子
        yc = (YY0 + YY1) * 0.5
        self.add(box("yard_rim_f", ((YX0 + YX1) * 0.5, YY1 - 0.09, RIM_Z * 0.5),
                     (YX1 - YX0, 0.18, RIM_Z), M["paving"]), 0.006)
        self.add(box("yard_rim_b", ((YX0 + YX1) * 0.5, YY0 + 0.09, RIM_Z * 0.5),
                     (YX1 - YX0, 0.18, RIM_Z), M["paving"]), 0.006)
        self.add(box("yard_rim_l", (YX0 - 0.09, yc, RIM_Z * 0.5),
                     (0.18, YY1 - YY0 - 0.36, RIM_Z), M["paving"]), 0.006)
        self.add(box("yard_rim_r", (YX1 + 0.09, yc, RIM_Z * 0.5),
                     (0.18, YY1 - YY0 - 0.36, RIM_Z), M["paving"]), 0.006)
        # 门前铺石：台阶两侧各一块大板，台阶前横排三块
        for i, (x0, x1, y0, y1) in enumerate((
                (-3.30, -1.98, 5.58, 6.42), (1.98, 4.30, 5.58, 6.42),
                (-3.30, -1.10, 6.46, 6.98), (-1.06, 1.10, 6.46, 6.98),
                (1.10, 3.30, 6.46, 6.98))):
            self.add(box("yard_pave%d" % i, ((x0 + x1) * 0.5, (y0 + y1) * 0.5, 0.235),
                         (x1 - x0, y1 - y0, 0.07), M["paving"]), 0.010)
        # 台阶：三级（0.20 → 0.53 → 0.86 → 1.20），最后一级顶 1.12 让门口石槛压住
        for i, (y0, y1, zt) in enumerate(((6.10, 6.44, 0.53),
                                          (5.74, 6.08, 0.86),
                                          (5.40, 5.72, 1.12))):
            self.add(box("step%d" % i, (0.0, (y0 + y1) * 0.5, (G_Z + zt) * 0.5),
                         (2 * DHW + 0.46, y1 - y0, zt - G_Z), M["stone_mid"]), 0.010)
        # 门槛石：压在墙脚与第一级台阶之上（1.12 → 1.26）
        self.add(box("hall_threshold", (0.0, HY1 - 0.18, 1.19),
                     (2 * DHW + 0.14, 0.62, 0.14), M["stone_mid"]), 0.010)
        # 锅炉房门前一级
        self.add(box("ann_step", ((AX0 + AX1) * 0.5, AY1 + 0.24, 0.30),
                     (AX1 - AX0 - 0.20, 0.48, 0.20), M["stone_light"]), 0.008)

    # ── 2. 主体：台基 / 四墙 / 山墙 ───────────────────────────────────────
    def hall(self):
        M = self.M
        yc = (HY0 + HY1) * 0.5
        self.add(box("hall_plinth", (0.0, yc, PL_Z1 * 0.5),
                     (HX * 2 + 0.12, HY1 - HY0 + 0.12, PL_Z1), M["stone_mid"]), 0.020)
        self.add(box("hall_cap", (0.0, yc, (PL_Z1 + PC_Z1) * 0.5),
                     (HX * 2 + 0.32, HY1 - HY0 + 0.32, PC_Z1 - PL_Z1),
                     M["stone_light"]), 0.012)
        hz = (PC_Z1 + WZ1) * 0.5
        hh = WZ1 - PC_Z1
        # 侧墙 / 后墙 / 前墙左右墩（前墙洞在 doorway 里补齐拱上那块）
        for sgn, tag in ((-1, "l"), (1, "r")):
            self.add(box("hall_wall_s" + tag,
                         (sgn * (HX - WT * 0.5), (HY0 + HY1) * 0.5, hz),
                         (WT, HY1 - HY0 - WT * 2, hh), M["stone_light"]), 0.014)
        self.add(box("hall_wall_b", (0.0, HY0 + WT * 0.5, hz),
                     (HX * 2, WT, hh), M["stone_light"]), 0.014)
        # 前墙：左墩 / 右墩
        for (x0, x1) in ((-HX, -DHW), (DHW, HX)):
            self.add(box("hall_wall_f", ((x0 + x1) * 0.5, HY1 - WT * 0.5, hz),
                         (x1 - x0, WT, hh), M["stone_light"]), 0.014)
        # 前后山墙：三角形（底边压进墙顶 4 cm，顶点比屋面底面低 2 cm）
        gab = [(-HX, WZ1 - 0.04), (HX, WZ1 - 0.04), (HX, WZ1),
               (0.0, RIDGE_IN - 0.02), (-HX, WZ1)]
        self.add(prism("hall_gable_f", gab, "Y", HY1 - WT, HY1,
                       M["stone_light"]), 0.016)
        self.add(prism("hall_gable_b", gab, "Y", HY0, HY0 + WT,
                       M["stone_light"]), 0.016)
        # 压梁：山墙脚下一条通长深木（正面 4 cm 出挑）
        self.add(box("hall_bress_f", (0.0, HY1 + 0.02, WZ1 + 0.17),
                     (HX * 2 + 0.02, 0.38, 0.34), M["wood_dark"]), 0.014)
        self.add(box("hall_bress_b", (0.0, HY0 - 0.02, WZ1 + 0.17),
                     (HX * 2 + 0.02, 0.38, 0.34), M["wood_dark"]), 0.014)
        # 压梁下一条队色饰带（正面的"招牌线"）
        self.add(box("hall_team_board", (0.0, HY1 + 0.02, WZ1 - 0.09),
                     (HX * 2 + 0.02, 0.06, 0.16), M["team"]), 0.004)
        # 檐口封板（两侧通长）
        for sgn, tag in ((-1, "l"), (1, "r")):
            self.add(box("hall_eave" + tag,
                         (sgn * (ROOF_X - 0.01), (ROOF_Y0 + ROOF_Y1) * 0.5,
                          EAVE_IN - 0.10),
                         (0.10, ROOF_Y1 - ROOF_Y0, 0.20), M["wood_dark"]), 0.008)
        # 檐下椽头：一道锯齿状的暗影线，读得出"木构出檐"
        for sgn, tag in ((-1, "l"), (1, "r")):
            for k in range(11):
                yy = ROOF_Y0 + 0.55 + k * 1.14
                self.add(box("hall_rafter" + tag, (sgn * (HX + 0.30), yy, EAVE_IN - 0.02),
                             (0.42, 0.15, 0.13), M["wood_dark"]), 0.002)
        # 门两侧的落地木柱：撑住压梁，把"贴平的立面"撑出前后关系
        #（右柱正压在吊梁下面，读作吊梁的支座）
        for sgn in (-1, 1):
            self.add(box("hall_postbase", (sgn * 1.80, HY1 + 0.15, 1.35),
                         (0.44, 0.32, 0.30), M["stone_light"]), 0.008)
            self.add(box("hall_post", (sgn * 1.80, HY1 + 0.11, (1.50 + WZ1) * 0.5),
                         (0.26, 0.24, WZ1 - 1.50), M["wood_dark"]), 0.010)
            self.add(box("hall_post_head", (sgn * 1.80, HY1 + 0.13, WZ1 - 0.16),
                         (0.36, 0.30, 0.16), M["wood_dark"]), 0.004)
        # 扶壁（两侧各 1 / 2 道）
        for (sgn, tag, yy) in ((1, "r", 3.15), (-1, "l", 3.15), (-1, "l", -2.40)):
            self.add(box("hall_butt" + tag,
                         (sgn * (HX + 0.11), yy, 2.87),
                         (0.22, 0.40, 3.34), M["stone_mid"]), 0.010)
            self.add(frustum("hall_butt_cap" + tag, 4.54, 4.78,
                             0.22, 0.40, 0.10, 0.22, sgn * (HX + 0.11), yy,
                             M["stone_light"]), 0.006)
        # 近侧长墙：两扇高窗；锅炉房顶上三扇铁百叶（不挖洞、不碰屋面）
        self.win_x("win_r1", 4.20, 3.32, 0.90, 1.46, HX, 1, M["glow"])
        self.win_x("win_r2", 2.20, 3.32, 0.90, 1.46, HX, 1, M["glass"])
        for i, yy in enumerate((-1.30, -3.10, -4.90)):
            self.add(box("hall_vent%d" % i, (HX + 0.025, yy, 4.62),
                         (0.05, 0.62, 0.44), M["coal"]), 0.0)
            for k in range(3):
                self.add(box("hall_vent%d_slat" % i, (HX + 0.055, yy, 4.46 + k * 0.16),
                             (0.03, 0.58, 0.07), M["iron"],
                             rot=(math.radians(24), 0, 0)), 0.0)
        # 远侧长墙
        self.win_x("win_l1", -2.05, 3.32, 0.90, 1.46, -HX, -1, M["glass"])
        self.win_x("win_l2", 2.60, 3.32, 0.90, 1.46, -HX, -1, M["glass"])
        # 后墙一扇 + 山墙百叶
        self.win_y("win_b1", 0.0, 3.50, 1.10, 1.40, HY0, -1, M["glass"])
        self.add(box("hall_blouv_frame", (0.0, HY0 - 0.03, 6.42), (1.46, 0.08, 0.86),
                     M["wood_dark"]), 0.006)
        self.add(box("hall_blouv_back", (0.0, HY0 - 0.05, 6.42), (1.24, 0.05, 0.66),
                     M["coal"]), 0.0)
        for k in range(3):
            self.add(box("hall_blouv", (0.0, HY0 - 0.08, 6.20 + k * 0.20),
                         (1.22, 0.04, 0.12), M["iron"],
                         rot=(math.radians(-24), 0, 0)), 0.001)

    # ── 3. 门洞 / 门厅 / 门扇 / 扇形窗 ───────────────────────────────────
    def doorway(self):
        M = self.M
        y0, y1 = HY1 - WT, HY1
        # 拱上那块墙：下边挖掉半圆（凹多边形，耳切三角化没问题）
        prof = [(-DHW, DSPRING)]
        for s in range(1, 8):
            a = math.pi * (1.0 - s / 8.0)
            prof.append((DHW * math.cos(a), DSPRING + DHW * math.sin(a)))
        prof += [(DHW, DSPRING), (DHW, WZ1), (-DHW, WZ1)]
        self.add(prism("hall_arch_head", prof, "Y", y0, y1, M["stone_light"]), 0.012)
        # 拱券环 + 门侧石
        self.add(arch_band("door_arch", 0.0, DSPRING, DHW, DHW + 0.20,
                           HY1, HY1 + 0.12, M["stone_light"], segs=8), 0.010)
        for sgn in (-1, 1):
            self.add(box("door_jamb", (sgn * (DHW + 0.10), HY1 + 0.05, (PC_Z1 + DSPRING) * 0.5),
                         (0.20, 0.10, DSPRING - PC_Z1), M["stone_light"]), 0.010)
        # 门厅：内壁 + 地面（门关着，里面看不见；只保留围合，避免从门缝看进一个空壳）
        self.add(box("door_floor", (0.0, 4.72, PC_Z1 + 0.015), (2 * DHW, 1.30, 0.05),
                     M["stone_dark"]), 0.0)
        self.add(box("door_vest_b", (0.0, 4.10, 2.72), (2 * DHW + 0.30, 0.16, 3.04),
                     M["stone_dark"]), 0.008)
        for sgn in (-1, 1):
            self.add(box("door_vest_s", (sgn * (DHW + 0.12), 4.78, 2.63),
                         (0.12, 1.40, 2.86), M["stone_dark"]), 0.006)
        # ── 双扇大门：全关 ──────────────────────────────────────────────────
        # v3 前左扇向内开 55°，从正面看是一个黑洞，读作"没做完的门"。
        # 现在双扇全关，靠"通长铁箍 + 中缝压条 + 门闩 + 对称门环"把它读成一扇
        # **锁死的车间大门**。四层深度写死，任意两层都不共面（mm）：
        #   门板 5.265–5.355 / 竖板 5.355–5.375 / 队色下板 5.361–5.391
        #   铁箍 5.374–5.402 / 中缝压条 5.357–5.385 / 门闩 5.372–5.422
        lz0, lz1 = 1.258, 3.24
        lz = (lz0 + lz1) * 0.5
        for sgn in (-1, 1):
            tag = "R" if sgn > 0 else "L"
            self.add(box("door_leaf_%s" % tag, (sgn * DHW * 0.5, HY1 - 0.09, lz),
                         (DHW - 0.02, 0.09, lz1 - lz0), M["wood_mid"]), 0.008)
            # 竖向企口板：每扇 5 条，比门板凸 20 mm
            for k in (-2, -1, 0, 1, 2):
                self.add(box("door_leaf_%s_plank" % tag,
                             (sgn * (DHW * 0.5 + k * 0.24), HY1 - 0.035, lz),
                             (0.09, 0.02, lz1 - lz0 - 0.10), M["wood_dark"]), 0.001)
        # 通长铁箍两道：跨过中缝，读作"整扇门被箍住"，而不是两扇各贴一条
        for zz in (lz0 + 0.66, lz1 - 0.26):
            self.add(box("door_leaf_band", (0.0, HY1 - 0.022, zz),
                         (2 * DHW - 0.06, 0.028, 0.11), M["iron"]), 0.003)
        # 队色下板：通长一条（低处的识别色，也是"车间统一涂装"的读法）
        self.add(box("door_leaf_team", (0.0, HY1 - 0.024, lz0 + 0.32),
                     (2 * DHW - 0.06, 0.03, 0.30), M["team"]), 0.004)
        # 中缝压条：盖住两扇之间的 20 mm 缝。用亮木（wood_warm）——
        # 深木压条和门板的竖板同色，关上以后看不出是"两扇"。
        self.add(box("door_leaf_seam", (0.0, HY1 - 0.028, (1.74 + lz1 - 0.03) * 0.5),
                     (0.13, 0.03, lz1 - 0.03 - 1.74), M["wood_warm"]), 0.002)
        # 门闩：一根横在门上的铁杠 + 两端木座（关门的动作写在这一根上）
        self.add(box("door_latch", (0.0, HY1 - 0.003, 2.42), (1.94, 0.05, 0.10),
                     M["iron"]), 0.004)
        for sgn in (-1, 1):
            self.add(box("door_latch_seat", (sgn * 0.86, HY1 - 0.015, 2.42),
                         (0.22, 0.09, 0.19), M["wood_dark"]), 0.004)
        # 双门环：对称、贴近中缝 —— 只有"关着的门"才有这个读法
        for sgn in (-1, 1):
            self.add(box("door_ring_plate", (sgn * 0.34, HY1 - 0.026, 2.14),
                         (0.18, 0.018, 0.18), M["iron"]), 0.002)
            self.add(ring3("door_ring", (sgn * 0.34, HY1 - 0.014, 2.14),
                           0.062, 0.112, 0.03, 8, M["iron"], "Y"), 0.002)
        # 门楣横梁 + 拱内木鼓（竖板拼的"门头"，不是玫瑰花窗）
        self.add(box("door_head", (0.0, HY1 - 0.04, 3.32), (2 * DHW + 0.14, 0.22, 0.18),
                     M["wood_dark"]), 0.008)
        seg = [(-1.198, 3.40)]
        for s in range(1, 7):
            a = (math.pi - 0.36) * (1.0 - s / 7.0) + 0.36 * (s / 7.0)
            seg.append((DHW * math.cos(a), DSPRING + DHW * math.sin(a)))
        seg.append((1.198, 3.40))
        self.add(prism("door_tymp", seg, "Y", HY1 - 0.11, HY1 - 0.02,
                       M["wood_mid"]), 0.006)
        for xx in (-0.62, 0.0, 0.62):
            ztop = DSPRING + math.sqrt(max(DHW * DHW - xx * xx, 0.01)) - 0.10
            self.add(box("door_tymp_plank", (xx, HY1 - 0.010, (3.40 + ztop) * 0.5),
                         (0.10, 0.03, ztop - 3.40), M["wood_dark"]), 0.001)
        self.add(box("door_tymp_strap", (0.0, HY1 - 0.030, 3.72), (2.10, 0.03, 0.10),
                     M["iron"]), 0.002)

    # ── 4. 屋面 / 天窗 / 排气塔 / 风向标 ─────────────────────────────────
    def roof(self):
        M = self.M
        prof = [(-ROOF_X, EAVE_OUT), (0.0, RIDGE_OUT), (ROOF_X, EAVE_OUT),
                (ROOF_X, EAVE_IN), (0.0, RIDGE_IN), (-ROOF_X, EAVE_IN)]
        self.add(prism("roof_main", prof, "Y", ROOF_Y0, ROOF_Y1,
                       M["roof"]), 0.0)
        # 脊：一条小 Λ 压顶
        ridge = [(-0.17, RIDGE_OUT - 0.03), (0.0, RIDGE_OUT + 0.035), (0.17, RIDGE_OUT - 0.03),
                 (0.17, RIDGE_OUT - 0.17), (0.0, RIDGE_OUT - 0.05), (-0.17, RIDGE_OUT - 0.17)]
        self.add(prism("roof_ridge", ridge, "Y", ROOF_Y0, ROOF_Y1,
                       M["team"]), 0.004)
        # 封檐板（深木压条；正面再压一条 5 cm 的队色细线，只描边不刷面）
        for (y, tag) in ((ROOF_Y1 - 0.04, "f"), (ROOF_Y0 + 0.04, "b")):
            for sgn in (-1, 1):
                self.add(beam("roof_rake_%s%d" % (tag, 0 if sgn < 0 else 1),
                              (0.0, y, RIDGE_OUT - 0.09),
                              (sgn * (ROOF_X + 0.02), y, EAVE_OUT - 0.09),
                              0.10, 0.25, M["wood_dark"]), 0.006)
        for sgn in (-1, 1):
            self.add(beam("roof_rake_team%d" % (0 if sgn < 0 else 1),
                          (0.0, ROOF_Y1 + 0.016, RIDGE_OUT - 0.02),
                          (sgn * (ROOF_X + 0.02), ROOF_Y1 + 0.016, EAVE_OUT - 0.02),
                          0.016, 0.05, M["team"]), 0.001)
        # 平嵌天窗：近坡 3 只（4.05 长坡的主节奏）+ 远坡 2 只（错位，俯视时两坡都有东西）
        for (sgn, ys) in ((1, (3.40, 0.60, -2.20)), (-1, (2.00, -1.00))):
            for i, yy in enumerate(ys):
                tag = "roof_sky%s%d" % ("r" if sgn > 0 else "l", i)
                xc = sgn * 2.05
                zc = z_roof(xc)
                nx, nz = sgn * 0.5 ** 0.5, 0.5 ** 0.5      # 屋面法线
                ux, uz = -sgn * 0.5 ** 0.5, 0.5 ** 0.5     # 顺坡向上
                # 框嵌进瓦面 6 cm、只露 4 cm：正面（近水平视角）不会读成一排百叶
                for k in (-1, 1):
                    self.add(box(tag + "_g",
                                 (xc + ux * 0.57 * k - nx * 0.02, yy,
                                  zc + uz * 0.57 * k - nz * 0.02),
                                 (0.12, 1.46, 0.10), M["iron"],
                                 rot=(0, math.radians(45) * sgn, 0)), 0.004)
                    self.add(box(tag + "_h",
                                 (xc - nx * 0.02, yy + 0.70 * k, zc - nz * 0.02),
                                 (1.14, 0.12, 0.10), M["iron"],
                                 rot=(0, math.radians(45) * sgn, 0)), 0.004)
                self.add(box(tag + "_glass",
                             (xc + nx * 0.004, yy, zc + nz * 0.004),
                             (0.96, 1.22, 0.03), M["glass"],
                             rot=(0, math.radians(45) * sgn, 0)), 0.0)
        # 脊端风向标（比烟囱矮一档，不抢最高点）
        vy2 = ROOF_Y1 - 0.34
        self.add(rod("roof_vane_pole", (0.0, vy2, RIDGE_OUT - 0.02),
                     (0.0, vy2, RIDGE_OUT + 0.80), 0.045, 8, M["iron"]), 0.002)
        self.add(ball("roof_vane_ball", (0.0, vy2, RIDGE_OUT + 0.46), 0.075,
                      M["gold"], 8), 0.0)
        self.add(box("roof_vane_ns", (0.0, vy2, RIDGE_OUT + 0.58), (0.70, 0.045, 0.045),
                     M["iron"]), 0.002)
        self.add(box("roof_vane_arrow", (0.0, vy2, RIDGE_OUT + 0.74), (0.045, 0.84, 0.045),
                     M["iron"]), 0.002)
        self.add(box("roof_vane_fin", (0.0, vy2 - 0.38, RIDGE_OUT + 0.78),
                     (0.045, 0.18, 0.16), M["iron"]), 0.002)
        self.add(box("roof_vane_head", (0.0, vy2 + 0.38, RIDGE_OUT + 0.74),
                     (0.06, 0.18, 0.10), M["iron"], rot=(math.radians(45), 0, 0)), 0.002)

    # ── 5. 锅炉房：台基 / 墙 / 单坡 / 机房门 / 炉膛 ──────────────────────
    def annex(self):
        M = self.M
        ayc = (AY0 + AY1) * 0.5
        self.add(box("ann_plinth", ((AX0 + AX1) * 0.5, ayc, 0.22),
                     (AX1 - AX0 + 0.12, AY1 - AY0 + 0.12, 0.44), M["stone_dark"]), 0.014)
        self.add(box("ann_cap", ((AX0 + AX1) * 0.5, ayc, 0.50),
                     (AX1 - AX0 + 0.24, AY1 - AY0 + 0.24, 0.12), M["stone_light"]), 0.008)
        # 外墙
        self.add(box("ann_wall_x", (AX1 - WT * 0.5, ayc, (AZ0 + A_WALL_TOP) * 0.5),
                     (WT, AY1 - AY0, A_WALL_TOP - AZ0), M["stone_light"]), 0.012)
        for (yy, tag) in ((AY1 - WT * 0.5, "f"), (AY0 + WT * 0.5, "b")):
            prof = [(AX0, z_aroof_in(AX0)), (AX1, z_aroof_in(AX1)),
                    (AX1, AZ0), (AX0, AZ0)]
            self.add(prism("ann_wall_" + tag, prof, "Y", yy - WT * 0.5, yy + WT * 0.5,
                           M["stone_light"]), 0.012)
        # 单坡屋面
        rprof = [(AX0, AROOF_HI), (AROOF_X1, AROOF_LO),
                 (AROOF_X1, AROOF_LO - A_T), (AX0, AROOF_HI - A_T)]
        self.add(prism("ann_roof", rprof, "Y", AY0 - 0.20, AY1 + 0.20,
                       M["roof"]), 0.004)
        self.add(box("ann_roof_edge", ((AROOF_X1 - 0.02), ayc, (AROOF_LO - A_T + 0.02)),
                     (0.08, AY1 - AY0 + 0.40, 0.16), M["wood_dark"]), 0.006)
        self.add(box("ann_roof_team", ((AROOF_X1 + 0.005), ayc, (AROOF_LO - A_T + 0.02)),
                     (0.02, AY1 - AY0 + 0.40, 0.05), M["team"]), 0.001)
        # 沿外墙一条保温蒸汽主管：把炉膛、锅炉、烟囱串起来
        self.add(rod("pipe_main", (AX1 + 0.13, AY0 + 0.35, 2.96),
                     (AX1 + 0.13, AY1 - 0.30, 2.96), 0.13, 8, M["iron"]), 0.004)
        for yy in (-5.20, -3.40, -1.60, 0.20):
            self.add(box("pipe_bracket", (AX1 + 0.16, yy, 2.96), (0.30, 0.09, 0.26),
                         M["iron"]), 0.002)
        for yy in (-4.30, -0.70):
            self.add(ring3("pipe_joint", (AX1 + 0.13, yy, 2.96), 0.13, 0.20, 0.09, 8,
                           M["gold"], "Y"), 0.002)
        # 与主墙的泛水
        self.add(box("ann_flash", (AX0 + 0.06, ayc, AROOF_HI + 0.05),
                     (0.20, AY1 - AY0 + 0.40, 0.14), M["iron"]), 0.004)
        # 机房门（拱形，关着）
        dx = (AX0 + AX1) * 0.5
        self.add(extrude("ann_door", arch_profile(1.30, 1.62, segs=8), "Y", 0.09,
                         (dx, AZ0 - 0.06), M["wood_dark"], offset=AY1 + 0.015), 0.008)
        self.add(arch_band("ann_door_arch", dx, AZ0 + 1.62, 0.65, 0.80,
                           AY1, AY1 + 0.12, M["stone_light"], segs=8), 0.008)
        for sgn in (-1, 1):
            self.add(box("ann_door_jamb", (dx + sgn * 0.72, AY1 + 0.05, AZ0 + 0.81),
                         (0.15, 0.10, 1.62), M["stone_light"]), 0.006)
        for zz in (AZ0 + 0.26, AZ0 + 0.94, AZ0 + 1.60):
            self.add(box("ann_door_strap", (dx, AY1 + 0.07, zz),
                         (1.16, 0.035, 0.09), M["iron"]), 0.002)
        self.add(ring3("ann_door_ring", (dx + 0.38, AY1 + 0.09, AZ0 + 0.86),
                       0.06, 0.10, 0.04, 8, M["iron"], "Y"), 0.002)
        self.add(box("ann_door_team", (dx, AY1 + 0.04, AZ0 + 1.94),
                     (1.46, 0.06, 0.16), M["team"]), 0.004)
        # 圆窗（暖光）
        self.add(ring3("ann_port_rim", (AX1 + 0.03, -0.60, 2.42), 0.24, 0.31, 0.10,
                       10, M["gold"], "X"), 0.004)
        self.add(cyl("ann_port_glass", (AX1 + 0.02, -0.60, 2.42), 0.23, 0.05, 10,
                     M["glass"], axis="X"), 0.0)
        for (dy, dz, sy, sz) in ((0.0, 0.0, 0.05, 0.44), (0.0, 0.0, 0.44, 0.05)):
            self.add(box("ann_port_bar", (AX1 + 0.06, -0.60 + dy, 2.42 + dz),
                         (0.04, sy, sz), M["iron"]), 0.0)
        # 炉膛：凸出的铸铁火箱 + 关着的炉门（门上开一张发光的炉栅）
        fx, fy = AX1 + 0.12, BOY
        self.add(box("ann_firebox", (fx, fy, 1.66), (0.40, 1.46, 1.36), M["iron"]), 0.010)
        self.add(box("ann_fire_door", (fx + 0.23, fy, 1.66), (0.06, 1.30, 1.20),
                     M["iron"]), 0.006)
        self.add(box("ann_fire_glow", (fx + 0.262, fy, 1.60), (0.03, 0.74, 0.48),
                     M["ember"]), 0.0)
        self.add(box("ann_fire_glow_core", (fx + 0.268, fy, 1.56), (0.02, 0.40, 0.22),
                     M["flame_in"]), 0.0)
        for k in range(4):
            self.add(box("ann_fire_grate", (fx + 0.276, fy - 0.30 + k * 0.20, 1.60),
                         (0.03, 0.045, 0.54), M["iron"]), 0.001)
        for (yy, zz, ww, hh) in ((0.0, 1.90, 0.86, 0.07), (0.0, 1.30, 0.86, 0.07),
                                 (-0.42, 1.60, 0.07, 0.68), (0.42, 1.60, 0.07, 0.68)):
            self.add(box("ann_fire_bezel", (fx + 0.268, fy + yy, zz), (0.04, ww, hh),
                         M["iron"]), 0.001)
        # 灰门 + 铰 + 门闩 + 上沿铜条
        self.add(box("ann_ash_door", (fx + 0.235, fy, 1.12), (0.05, 0.50, 0.26),
                     M["iron"]), 0.004)
        self.add(box("ann_ash_slot", (fx + 0.262, fy, 1.12), (0.02, 0.30, 0.10),
                     M["ember"]), 0.0)
        for sy in (-1, 1):
            self.add(box("ann_fire_hinge", (fx + 0.245, fy + sy * 0.50, 1.66),
                         (0.10, 0.10, 0.14), M["gold"]), 0.002)
        self.add(box("ann_fire_latch", (fx + 0.275, fy + 0.58, 1.52),
                     (0.05, 0.10, 0.30), M["gold"]), 0.002)
        self.add(box("ann_fire_lip", (fx + 0.20, fy, 2.28), (0.34, 1.30, 0.10),
                     M["gold"]), 0.004)

    # ── 6. 烟囱 ──────────────────────────────────────────────────────────
    def chimney(self):
        M = self.M
        top = CH_TOP                     # 10.06：全座最高点
        self.add(box("chim_base", (CHX, CHY, 0.80), (CH_W + 0.40, CH_W + 0.40, 1.60),
                     M["stone_mid"]), 0.018)
        self.add(box("chim_body", (CHX, CHY, (1.60 + 9.50) * 0.5),
                     (CH_W, CH_W, 9.50 - 1.60), M["stone_mid"]), 0.016)
        # 两道队色箍（下宽上窄）
        self.add(box("chim_band_a", (CHX, CHY, 5.02), (CH_W + 0.09, CH_W + 0.09, 0.54),
                     M["team"]), 0.006)
        self.add(box("chim_band_b", (CHX, CHY, 7.42), (CH_W + 0.09, CH_W + 0.09, 0.26),
                     M["team"]), 0.006)
        # 压顶：两级出檐 + 黑喉（逐级咬合，不留 1 cm 悬空）
        self.add(box("chim_cap1", (CHX, CHY, 9.59), (CH_W + 0.38, CH_W + 0.38, 0.20),
                     M["stone_light"]), 0.008)
        self.add(box("chim_cap2", (CHX, CHY, 9.80), (CH_W + 0.16, CH_W + 0.16, 0.24),
                     M["stone_light"]), 0.008)
        self.add(box("chim_throat", (CHX, CHY, 9.97), (CH_W - 0.30, CH_W - 0.30, 0.14),
                     M["coal"]), 0.0)
        self.add(ring3("chim_iron", (CHX, CHY, 1.94), CH_W * 0.70, CH_W * 0.72, 0.07,
                       8, M["iron"], "Z", phase=TAU / 16), 0.002)

    # ── 7. 锅炉 / 蒸汽管 / 烟道 ───────────────────────────────────────────
    def boiler(self):
        M = self.M
        R = BOIL_R
        self.add(revolve("boil_body",
                         [(0.0, 0.0), (R, 0.0), (R, 4.30), (R * 0.98, 4.50),
                          (R * 0.78, 4.70), (R * 0.44, 4.80), (0.0, 4.84)],
                         12, (BOX_, BOY, 0.58), M["iron"]), 0.012)
        for zz in (1.95, 3.30, 4.50):
            self.add(ring3("boil_hoop", (BOX_, BOY, zz), R - 0.02, R + 0.04,
                           0.13, 12, M["gold"], "Z", phase=TAU / 24), 0.004)
        # 表盘（朝 +Y，落在锅炉外表面上）
        self.add(ring3("boil_gauge_rim", (BOX_, BOY + BOIL_R + 0.02, 4.02),
                       0.19, 0.27, 0.10, 10, M["gold"], "Y"), 0.004)
        self.add(cyl("boil_gauge", (BOX_, BOY + BOIL_R + 0.02, 4.02), 0.19, 0.06, 10,
                     M["stone_light"], axis="Y"), 0.0)
        self.add(box("boil_needle", (BOX_ - 0.05, BOY + BOIL_R + 0.07, 4.06),
                     (0.035, 0.03, 0.20), M["coal"], rot=(0.0, math.radians(26), 0.0)), 0.0)
        # 顶：颈圈 + 汽笛 + 安全阀
        self.add(vcyl("boil_neck", (BOX_, BOY, 5.36), 0.24, 0.18, 10, M["gold"]), 0.003)
        self.add(vcyl("boil_whistle", (BOX_ + 0.16, BOY + 0.10, 5.26), 0.12, 0.60, 8,
                      M["gold"]), 0.004)
        self.add(ring3("boil_whistle_cap", (BOX_ + 0.16, BOY + 0.10, 5.86),
                       0.05, 0.14, 0.06, 8, M["iron"], "Z"), 0.002)
        self.add(vcyl("boil_valve", (BOX_ - 0.24, BOY - 0.14, 5.24), 0.10, 0.32, 8,
                      M["gold"]), 0.003)
        self.add(box("boil_valve_lever", (BOX_ - 0.24, BOY - 0.14, 5.58),
                     (0.50, 0.06, 0.05), M["iron"]), 0.002)
        # 蒸汽管：锅炉 → 主车间墙
        self.add(rod("pipe_steam", (BOX_ - BOIL_R + 0.06, BOY, 4.34),
                     (HX + 0.02, BOY, 4.34), 0.115, 8, M["iron"]), 0.004)
        self.add(ring3("pipe_flange", (HX + 0.05, BOY, 4.34), 0.115, 0.19, 0.08, 8,
                       M["iron"], "X"), 0.002)
        self.add(ring3("pipe_valve", (HX + 0.12, BOY, 4.34), 0.16, 0.23, 0.05, 8,
                       M["gold"], "X"), 0.002)
        for k in range(3):
            a = TAU * k / 3.0
            self.add(beam("pipe_valve_spoke",
                          (HX + 0.15, BOY, 4.34),
                          (HX + 0.15, BOY + 0.21 * math.cos(a), 4.34 + 0.21 * math.sin(a)),
                          0.035, 0.035, M["gold"]), 0.001)
        # 烟道：锅炉 → 烟囱（在锅炉背后，被锅筒挡住大半）
        self.add(rod("pipe_flue", (BOX_, BOY - BOIL_R + 0.06, 4.78),
                     (CHX - 0.10, CHY + CH_W * 0.5, 4.78), 0.20, 8, M["iron"]), 0.006)
        for yy in (BOY - BOIL_R - 0.16, CHY + CH_W * 0.5 + 0.16):
            self.add(ring3("pipe_flue_flange", (BOX_, yy, 4.78), 0.20, 0.30, 0.08, 8,
                           M["iron"], "Y"), 0.002)

    # ── 8. 吊装梁（山墙外挑 + 斜撑 + 滑轮 + 链 + 钩）──────────────────────
    def crane(self):
        M = self.M
        self.add(box("crane_beam", (CR_X, (HY1 + CR_Y1) * 0.5, CR_Z),
                     (0.34, CR_Y1 - HY1 + 0.26, 0.36), M["wood_dark"]), 0.010)
        self.add(box("crane_beam_band", (CR_X, CR_Y1 - 0.30, CR_Z),
                     (0.40, 0.10, 0.42), M["team_trim"]), 0.004)
        self.add(beam("crane_brace", (CR_X, CR_Y1 - 0.42, CR_Z - 0.16),
                      (CR_X, HY1 - 0.16, CR_Z + 0.58), 0.16, 0.16, M["wood_dark"]), 0.006)
        self.add(box("crane_tip", (CR_X, CR_Y1 - 0.02, CR_Z),
                     (0.40, 0.10, 0.42), M["gold"]), 0.004)
        pb_y, pb_z = CR_Y1 - 0.26, CR_Z - 0.36
        self.add(box("crane_block", (CR_X, pb_y, pb_z), (0.28, 0.36, 0.50),
                     M["iron"]), 0.008)
        self.add(ring3("crane_pulley", (CR_X, pb_y, pb_z - 0.04), 0.09, 0.16, 0.12, 8,
                       M["gold"], "X"), 0.002)
        # 铁链 6 环（X / Y 交替）+ 吊钩
        z = pb_z - 0.28
        for i in range(6):
            self.add(ring3("crane_chain", (CR_X, pb_y, z - 0.09 * i),
                           0.052, 0.086, 0.032, 8, M["iron"],
                           "X" if i % 2 else "Y"), 0.001)
        hz = z - 0.09 * 5 - 0.12
        self.add(box("crane_hook_a", (CR_X, pb_y, hz), (0.07, 0.07, 0.22), M["iron"]), 0.002)
        self.add(box("crane_hook_b", (CR_X, pb_y + 0.09, hz - 0.15),
                     (0.07, 0.22, 0.07), M["iron"]), 0.002)
        self.add(box("crane_hook_c", (CR_X, pb_y + 0.17, hz - 0.06),
                     (0.07, 0.07, 0.16), M["iron"]), 0.002)

    # ── 9. 山墙：通风百叶 / 木构 / 冠饰 / 垂旗 ────────────────────────────
    def gable(self):
        M = self.M
        # 中央通风百叶（车间的"呼吸口"，不是玫瑰花窗）
        self.add(box("gab_louv_frame", (0.0, HY1 + 0.03, 6.78), (1.52, 0.10, 0.80),
                     M["wood_dark"]), 0.008)
        self.add(box("gab_louv_back", (0.0, HY1 + 0.05, 6.78), (1.32, 0.05, 0.62),
                     M["coal"]), 0.0)
        for k in range(3):
            self.add(box("gab_louv_slat", (0.0, HY1 + 0.09, 6.58 + k * 0.20),
                         (1.30, 0.05, 0.13), M["iron"],
                         rot=(math.radians(26), 0, 0)), 0.001)
        self.add(box("gab_louv_hood", (0.0, HY1 + 0.17, 7.22), (1.66, 0.34, 0.09),
                     M["wood_dark"], rot=(math.radians(14), 0, 0)), 0.004)
        # 木构：下横梁 + 四条竖棂 + 上横梁 + 中柱
        self.add(box("gab_rail_lo", (0.0, HY1 + 0.05, 6.34), (4.55, 0.10, 0.17),
                     M["wood_dark"]), 0.006)
        for xx in (2.20, 0.92, -0.92, -2.20):
            self.add(box("gab_stud", (xx, HY1 + 0.05, (6.42 + RIDGE_IN - abs(xx) - 0.10) * 0.5),
                         (0.15, 0.10, RIDGE_IN - abs(xx) - 0.10 - 6.42),
                         M["wood_dark"]), 0.006)
        for xx in (-2.20, 2.20):
            self.add(box("gab_stud_lo", (xx, HY1 + 0.05, (WZ1 + 0.34 + 6.26) * 0.5),
                         (0.15, 0.10, 6.26 - WZ1 - 0.34), M["wood_dark"]), 0.006)
        self.add(box("gab_collar", (0.0, HY1 + 0.05, 7.78), (1.86, 0.10, 0.17),
                     M["wood_dark"]), 0.006)
        self.add(box("gab_king", (0.0, HY1 + 0.05, 8.30), (0.15, 0.10, 0.92),
                     M["wood_dark"]), 0.006)
        # 盾徽（挂在压梁上）
        self.kite("her_gable", (0.0, HY1 + 0.02, 5.68), "Y", 0.94, 1.10)
        # 山墙垂旗（左墩）
        self.wallbanner("her_banner", (-2.55, HY1 + 0.04, 3.30), "Y", 1.02, 2.10)

    # ── 10. 道具（只留"有人在干活"的最小一组）────────────────────────────
    def props(self):
        M = self.M
        # 煤堆（炉膛正下方）+ 三块散煤
        self.add(revolve("prop_coal", [(0.58, 0.0), (0.54, 0.16), (0.36, 0.34), (0.0, 0.46)],
                         8, (6.50, BOY, G_Z - 0.02), M["coal"]), 0.010)
        for (dx, dy, s, rz) in ((-0.46, 0.40, 0.20, 0.5), (0.40, -0.36, 0.17, -0.8),
                                (0.10, 0.56, 0.13, 1.2)):
            self.add(box("prop_coal_lump", (6.50 + dx, BOY + dy, G_Z + s * 0.28),
                         (s, s * 0.8, s * 0.6), M["coal"], rot=(0.2, 0.1, rz)), 0.004)
        # 两个麻煤袋
        for i, (x, y, zz) in enumerate(((6.40, -0.86, 0.0), (6.44, -1.24, 0.0))):
            self.add(revolve("prop_sack", [(0.0, 0.0), (0.30, 0.06), (0.33, 0.26),
                                           (0.22, 0.44), (0.10, 0.50), (0.0, 0.52)],
                             8, (x, y, G_Z + zz), M["sand"]), 0.010)
            self.add(box("prop_sack_tie", (x, y, G_Z + 0.50), (0.16, 0.16, 0.07),
                         M["earth_dark"]), 0.003)
        # 两只水桶
        for (x, y) in ((6.46, -1.72), (-4.16, 3.86)):
            self.add(revolve("prop_barrel", [(0.0, 0.0), (0.24, 0.02), (0.27, 0.14),
                                             (0.27, 0.54), (0.24, 0.66), (0.0, 0.68)],
                             10, (x, y, G_Z), M["wood_mid"]), 0.010)
            for zz in (0.16, 0.52):
                self.add(ring3("prop_barrel_hoop", (x, y, G_Z + zz), 0.262, 0.288,
                               0.06, 10, M["iron"], "Z", phase=TAU / 20), 0.002)
            self.add(vcyl("prop_barrel_lid", (x, y, G_Z + 0.645), 0.235, 0.04, 10,
                          M["wood_warm"]), 0.002)
        # 煤仓：靠外墙的矮石槽，里面填满碎煤（把右侧那条空地收住）
        self.add(box("prop_bunker", (6.42, -4.40, 0.51), (0.94, 1.52, 0.62),
                     M["stone_mid"]), 0.010)
        self.add(box("prop_bunker_coal", (6.42, -4.40, 0.80), (0.78, 1.34, 0.16),
                     M["coal"]), 0.004)
        for (dy, s2) in ((-0.30, 0.22), (0.26, 0.18)):
            self.add(box("prop_bunker_lump", (6.42, -4.40 + dy, 0.90),
                         (0.46, s2, 0.14), M["coal"], rot=(0.1, 0.0, 0.4)), 0.004)
        # 铁锹插在煤堆里
        self.add(beam("prop_shovel", (6.30, BOY + 0.30, 0.94),
                      (6.14, BOY + 0.62, 0.26), 0.05, 0.05, M["wood_dark"]), 0.002)
        self.add(box("prop_shovel_blade", (6.13, BOY + 0.65, 0.22),
                     (0.26, 0.32, 0.05), M["iron"],
                     rot=(math.radians(-58), 0.0, 0.0)), 0.002)
        # 木箱 + 散草 + 碎石
        self.add(box("prop_crate", (-3.92, 5.88, G_Z + 0.30), (0.62, 0.56, 0.60),
                     M["wood_warm"], rot=(0.0, 0.0, math.radians(9))), 0.008)
        self.add(box("prop_crate_lid", (-3.92, 5.88, G_Z + 0.62), (0.68, 0.62, 0.06),
                     M["wood_dark"], rot=(0.0, 0.0, math.radians(9))), 0.004)
        for (x, y, h) in ((-4.24, 1.10, 0.20), (-4.30, -2.60, 0.22), (4.32, -6.62, 0.18)):
            for k in range(3):
                a = math.radians(18 + k * 60)
                hh = h * (0.84 + 0.11 * k)
                self.add(box("tuft", (x + 0.014 * math.cos(a + 1.1),
                                      y + 0.014 * math.sin(a + 1.1), G_Z + hh * 0.48),
                             (0.115, 0.018, hh), M["moss"],
                             rot=(0.20 * math.cos(a), 0.20 * math.sin(a), a)), 0.0)
        for (x, y, s, rz) in ((-4.10, -5.40, 0.26, 0.4), (6.86, 6.10, 0.22, -0.6),
                              (-4.34, 6.42, 0.18, 1.1), (4.66, -6.80, 0.20, 0.2)):
            self.add(box("rubble", (x, y, G_Z + s * 0.26), (s, s * 0.76, s * 0.56),
                         M["stone_mid"], rot=(0.26 * s, 0.20 * s, rz)), 0.006)

    # ── 11. 组装 / 收尾 ───────────────────────────────────────────────────
    def build(self):
        for step in (self.yard, self.hall, self.doorway, self.roof,
                     self.annex, self.chimney, self.boiler,
                     self.crane, self.gable, self.props):
            step()
        return self

    def finalize(self, bevel=True):
        # 多边形件（12 / 10 / 8 边回转体、圆窗、天窗、机轮）一律平着色
        flat_pref = ("boil_", "prop_coal", "prop_sack", "prop_barrel", "chim_iron",
                     "gab_ring", "gab_glass", "gab_hub", "ann_port", "ann_door_ring",
                     "door_leaf_r_ring", "crane_pulley", "pipe_flange", "pipe_valve",
                     "roof_vane_ball", "door_arch", "ann_door_arch", "roof_sky",
                     "ann_fire_mouth", "hall_arch_head")
        # 曲面细分只磨"体量件"的小棱；大平面被 CC 磨圆会变成塑料感
        skip_cc = ("hall_", "roof_", "ann_", "yard_", "step", "chim_", "boil_",
                   "prop_", "crane_", "door_", "gab_", "her_", "pipe_", "rubble",
                   "tuft")
        for (ob, bev, sub, seg) in self.items:
            co = ob.data.vertices
            if not len(co):
                continue
            dims = [max(v.co[i] for v in co) - min(v.co[i] for v in co) for i in range(3)]
            chunky = min(dims) >= 0.12 and dims[0] * dims[1] * dims[2] >= 0.14
            n = ob.name
            is_flat = n.startswith(flat_pref)
            if self.smooth:
                cc = 1 if (chunky and not is_flat and not n.startswith(skip_cc)) else 0
                L.finalize(ob, bevel=min(max(bev, 0.008), 0.022), seg=1, sub=cc,
                           flat=is_flat)
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
        out = L.join_by_material(objs, prefix="SW")
        mirror_x(out)
        if self.unwrap:
            L.smart_uv(out)
        return out


def build(smooth=True, unwrap=True, bevel=True):
    m = Model(smooth, unwrap).build()
    objs = m.finalize(bevel=bevel)
    return objs, L.stats(objs)
