"""
br_model.py —— 兵营（Barracks）的形体定义（低模）

参考图：`参考图/兵营.png`（AOE4 风格）。拆出来的形体语言：

  ① 对称的双坡主屋 + 左右两个前突体量
     - 主屋 9.2 宽 / 7.2 进深 / 檐 6.4 / 脊 10.6（坡度 0.913 ≈ 42°）
     - 左前突：卫兵室（小山墙 + 门 + 窗），檐 4.6 / 脊 7.0
     - 右前突：开放训练棚（四根柱 + 单坡顶），不是封闭体量
  ② 竖向三段式立面（参考图的石基 + 灰泥 + 木构）
     - 0–0.70 粗石基座（stone_dark）
     - 0.70–2.60 石墙（stone_mid）+ 窄窗
     - 2.60–6.40 灰泥（stone_light）+ 深色半木构（wood_dark）
  ③ 中央营门：2.2 宽拱门 + 三级台阶 + 门楣盾 + 门侧长矛束
  ④ 屋顶：深色瓦 + 瓦垄 + 脊 + 旗杆红旗 + 两个老虎窗
  ⑤ 前场：木围栏 U 形 + 两个训练假人 + 武器架 + 桶

坐标：X 右、Y 前（+Y = 正面）、Z 上；原点在占地中心，z = 0 地面。
与铁匠铺同一套 bslib 构件库、同一套 17 个材质、同一个导出出口。

与铁匠铺的形制区分（六座资产包要求"屋顶类型两两不同"）：
  铁匠铺 = gable_cross（单侧作业坡棚把檐口打断）
  兵营   = gable_steep（42° 主坡 + 左右对称前突 + 脊上旗杆），主张是"对称 + 陡坡 + 旗"，
           剪影上靠"左右两个小山墙夹一个中央大山墙"与铁匠铺的不对称坡棚区分开。
"""
import math
import random

import bpy

import bslib as L
from bslib import (arch_band, beam, box, cone, cyl, extrude, frustum, kite_shield,
                   lathe, mesh_obj, octa_profile, revolve, ring_y, slab_plate,
                   taper_box, tube_band)

# ── 主尺度 ────────────────────────────────────────────────────────────────────
W2 = 4.60                       # 主屋半宽（总宽 9.2）
YF = 3.20                       # 前墙
YB = -4.00                      # 后墙
EAVE = 7.20                     # 檐口（底层 0–3.90 / 木构层 4.00–7.10）
RIDGE = 10.60                   # 屋脊
OV = 0.40                       # 出檐
SLOPE = (RIDGE - EAVE) / W2     # 0.913
ROOF_T = 0.18

# 中央营门
GATE_W, GATE_SPRING = 2.20, 2.85   # 门宽 / 拱脚高（拱顶 = 2.55 + 1.10 = 3.65）
GATE_Y = YF
STEP_N, STEP_H, STEP_D = 3, 0.16, 0.30

# 左前突（卫兵室）
WL_X0, WL_X1 = -4.60, -2.20
WL_Y1 = 6.40
WL_EAVE, WL_RIDGE = 4.40, 6.40

# 右前突（开放训练棚）
WR_X0, WR_X1 = 2.20, 4.60
WR_Y1 = 6.20
WR_EAVE, WR_RIDGE = 5.30, 4.05      # 单坡：后高前低（落差 1.25）

# 屋顶老虎窗
DOR_Y = 0.90
DOR_W = 0.74

# 旗杆
POLE_X, POLE_TOP = 0.85, 12.60

# 前场
YARD_Y0, YARD_Y1 = 7.20, 13.00
FENCE_X = 6.40

# 阵营色标准模块（与铁匠铺同形制）
SHIELD_W, SHIELD_H = 1.30, 1.60
BANNER_W, BANNER_H = 0.62, 1.30


def zroof(x):
    return RIDGE - SLOPE * abs(x)


def arch_profile(w, h, segs=8):
    hw = w * 0.5
    pts = [(-hw, 0.0), (hw, 0.0), (hw, h)]
    for s in range(segs - 1, 0, -1):
        a = math.pi * s / segs
        pts.append((hw * math.cos(a), h + hw * math.sin(a)))
    pts.append((-hw, h))
    return pts


def mirror_x(objs):
    import bmesh
    for ob in objs:
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        bmesh.ops.scale(bm, vec=(-1.0, 1.0, 1.0), verts=bm.verts)
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
        bm.to_mesh(ob.data)
        bm.free()
        ob.data.update()


class Model:
    """低模构件表。sub>0 的构件才会在平滑版里吃曲面细分（省面数）。"""

    def __init__(self, smooth, unwrap=True):
        self.smooth = smooth
        self.unwrap = unwrap
        self.items = []
        self.M = L.all_materials()

    def add(self, ob, bevel=0.022, sub=0, seg=1):
        if ob is None:
            return None
        if not self.smooth:
            bevel, sub, seg = 0.0, 0, 1
        elif bevel < 0.008:
            bevel = 0.0
        self.items.append((ob, bevel, sub, seg))
        return ob

    # ── 1. 基座、台阶、前场地面 ─────────────────────────────────────────────
    def base(self):
        M = self.M
        # 石台：0.60 m 高，在门洞处断开（±1.72），把台阶让进来
        for sgn in (-1, 1):
            x0, x1 = sgn * 1.72, sgn * 4.98
            self.add(box("plinth_a", ((x0 + x1) * 0.5, -0.35, 0.30),
                         (abs(x1 - x0), 7.80, 0.60), M["stone_dark"]))
        self.add(box("plinth_b", (0, -0.35, 0.07), (10.24, 8.14, 0.14), M["stone_mid"]))
        # 门厅地板：把门洞抬到 0.60，和石台同高
        self.add(box("gate_floor", (0, YF - 0.42, 0.30), (2.34, 0.96, 0.60),
                     M["stone_light"]), 0.014)
        # 三级台阶（实心阶梯，从院子 0.20 上到 0.60）
        for i, (yy, zz) in enumerate(((YF + 1.06, 0.34), (YF + 0.76, 0.47), (YF + 0.46, 0.60))):
            self.add(box("step%d" % i, (0, yy, zz * 0.5), (3.40, 0.32, zz),
                         M["stone_light"]), 0.012)
        for sgn in (-1, 1):
            self.add(box("step_cheek", (sgn * 1.86, YF + 0.76, 0.30), (0.30, 1.10, 0.60),
                         M["stone_mid"]), 0.016)
        # 前场夯土地坪（比石台低一档）
        self.add(box("yard", (0.00, (YARD_Y0 + YARD_Y1) * 0.5, 0.10),
                     (13.40, YARD_Y1 - YARD_Y0, 0.20), M["stone_mid"]), 0.030)
        self.add(box("yard_kerb", (0.00, YARD_Y1 + 0.09, 0.07), (13.40, 0.18, 0.14),
                     M["stone_dark"]), 0.016)
        for i, (yy, ww, mat) in enumerate(((7.90, 0.30, "stone_light"), (10.30, 0.24, "stone_dark"))):
            self.add(box("yard_band%d" % i, (0.00, yy, 0.205), (13.20, ww, 0.03), M[mat]), 0.004)

    # ── 2. 主墙体（三段式立面；前墙真挖 2.2 m 宽的拱形门洞）──────────────────
    def mass(self):
        M = self.M
        pent = [(-W2, 0.0), (W2, 0.0), (W2, EAVE), (0.0, RIDGE), (-W2, EAVE)]
        wall_t = 0.70
        # 后段实心
        self.add(extrude("mass_back", pent, "Y", YF - wall_t - YB, (0, 0),
                         M["stone_light"], offset=(YF - wall_t + YB) * 0.5), 0.035)
        # 前墙三块：左右 + 门洞上方的拱形块（三块拼起来正好是五边形减去拱洞）
        gw = GATE_W * 0.5
        z_t = GATE_SPRING + gw          # 拱顶 3.65
        z_g = zroof(gw)                 # 门洞两侧的墙顶（在屋面斜线上）
        left = [(-W2, 0.0), (-gw, 0.0), (-gw, z_g), (0.0, RIDGE), (-W2, EAVE)]
        right = [(gw, 0.0), (W2, 0.0), (W2, EAVE), (0.0, RIDGE), (gw, z_g)]
        for name, prof in (("mass_front_L", left), ("mass_front_R", right)):
            self.add(extrude(name, prof, "Y", wall_t, (0, 0), M["stone_light"],
                             offset=YF - wall_t * 0.5), 0.030)
        # 顶点顺序必须与 pent 同向（逆时针），否则这块前墙的法线朝内，渲染出来是黑的
        top = [(-gw, z_t), (-gw, z_g), (0.0, RIDGE), (gw, z_g), (gw, z_t)]
        for s in range(1, 10):
            a = math.pi * s / 10
            top.append((gw * math.cos(a), GATE_SPRING + gw * math.sin(a)))
        self.add(extrude("mass_front_T", top, "Y", wall_t, (0, 0), M["stone_light"],
                         offset=YF - wall_t * 0.5), 0.030)
        # 石基座 + 石墙裙（包一圈）
        self.add(box("dado", (0, (YF + YB) * 0.5, 0.90), (W2 * 2 + 0.10, YF - YB + 0.10, 1.40),
                     M["stone_mid"]), 0.028)
        self.add(box("plinth_band", (0, (YF + YB) * 0.5, 0.74), (W2 * 2 + 0.18, YF - YB + 0.18, 0.16),
                     M["stone_dark"]), 0.014)
        # 墙裙在门洞处断开（左右两段），别横穿门洞
        for sgn in (-1, 1):
            x0 = sgn * gw
            x1 = sgn * (W2 + 0.05)
            self.add(box("dado_front", ((x0 + x1) * 0.5, YF + 0.05, 0.98),
                         (abs(x1 - x0), 0.12, 1.32), M["stone_mid"]), 0.016)
        # 隅石（四角）
        for sx in (-1, 1):
            for sy, yface in ((1, YF), (-1, YB)):
                for i in range(3):
                    zz = 0.98 + i * 0.86
                    if zz > 3.1:
                        break
                    self.add(box("quoin", (sx * (W2 - 0.14), yface - sy * 0.19, zz),
                                 (0.46 + (0.06 if i % 2 else 0.0), 0.44, 0.44), M["stone_mid"]))
        # 灰泥腰线（石墙与木构层的分界）；同样在门洞处断开
        for sgn in (-1, 1):
            x0 = sgn * gw
            x1 = sgn * (W2 + 0.10)
            self.add(box("string_f", ((x0 + x1) * 0.5, YF + 0.02, 3.90),
                         (abs(x1 - x0), 0.14, 0.16), M["stone_light"]), 0.012)
        for yy in ((YF + YB) * 0.5,):
            self.add(box("string_s", (0, yy, 3.90), (W2 * 2 + 0.22, 0.14, 0.16),
                         M["stone_light"]), 0.012)
        self.add(box("string2", (0, (YF + YB) * 0.5, 5.26), (W2 * 2 + 0.16, YF - YB + 0.16, 0.12),
                     M["wood_dark"]), 0.010)
        # 侧墙扶壁
        for sx in (-1, 1):
            for yy in (-1.30, -3.10):
                self.add(box("buttress", (sx * (W2 + 0.15), yy, 2.30),
                             (0.30, 0.60, 4.60), M["stone_mid"]), 0.024)

    def banner(self, name, x, z_top, w=0.56, h=1.30):
        """门侧垂旗：横杆 + 燕尾布 + 金顶条 + 吊环。"""
        M = self.M
        y = YF + 0.30
        self.add(box(name + "_rod", (x, y, z_top), (w + 0.18, 0.06, 0.06), M["wood_dark"]), 0.004)
        prof = [(-w * 0.5, 0.0), (w * 0.5, 0.0), (w * 0.5, -h * 0.80),
                (w * 0.10, -h), (-w * 0.10, -h), (-w * 0.5, -h * 0.80)]
        self.add(extrude(name + "_cloth", prof, "Y", 0.05, (x, z_top - 0.05), M["team"],
                         offset=y), 0.008)
        self.add(box(name + "_trim", (x, y, z_top - 0.07), (w + 0.06, 0.062, 0.07),
                     M["team_trim"]), 0.004)
        for sgn in (-1, 1):
            self.add(box(name + "_ring", (x + sgn * w * 0.40, y, z_top + 0.05),
                         (0.03, 0.03, 0.10), M["iron"]), 0.002)

    # ── 3. 中央营门 ─────────────────────────────────────────────────────────
    def gate(self):
        M = self.M
        cx = 0.0
        # 门洞里的暖光（贴在后墙上，做出"屋里有灯"的深度）
        self.add(box("gate_glow", (0, YF - 0.66, 2.00), (GATE_W - 0.18, 0.04, 2.80), M["glow"]))
        # 洞口外圈：拱券石 + 门框石 + 拱心石
        self.add(arch_band("gate_arch", cx, GATE_SPRING, GATE_W * 0.5, GATE_W * 0.5 + 0.30,
                           YF - 0.04, YF + 0.14, M["stone_light"], segs=10), 0.020)
        for sgn in (-1, 1):
            self.add(box("gate_jamb", (sgn * (GATE_W * 0.5 + 0.14), YF + 0.04, GATE_SPRING * 0.5 + 0.60),
                         (0.28, 0.26, GATE_SPRING - 0.60), M["stone_light"]), 0.018)
        self.add(box("gate_key", (cx, YF + 0.10, GATE_SPRING + GATE_W * 0.5 - 0.02),
                     (0.34, 0.28, 0.46), M["stone_mid"]), 0.016)
        self.add(box("gate_sill", (0, YF + 0.05, 0.66), (GATE_W + 0.50, 0.30, 0.14),
                     M["stone_light"]), 0.010)
        # 双开木门（各向里开 18°，露出门缝和里面暖光）
        leaf = (GATE_W - 0.14) * 0.5
        for sgn in (-1, 1):
            a = math.radians(18)
            rot_z = -a if sgn < 0 else math.pi + a
            hx = sgn * (GATE_W * 0.5 - 0.04)
            px = hx + math.cos(rot_z) * leaf * 0.5
            py = (YF - 0.26) + math.sin(rot_z) * leaf * 0.5
            self.add(box("gate_leaf", (px, py, 0.60 + 1.42), (leaf, 0.10, 2.84),
                         M["wood_warm"], rot=(0, 0, rot_z)), 0.014)
            for k in (-1, 1):
                self.add(box("gate_seam", (px + k * 0.20 * math.cos(rot_z),
                                           py + k * 0.20 * math.sin(rot_z), 0.60 + 1.42),
                             (0.04, 0.03, 2.70), M["wood_dark"], rot=(0, 0, rot_z)), 0.002)
            for zz in (1.10, 2.36):
                self.add(box("gate_iron", (px, py, zz), (leaf - 0.10, 0.12, 0.11),
                             M["iron"], rot=(0, 0, rot_z)), 0.006)
        # 门侧长矛束（左右各一束，靠墙斜立）
        for sgn in (-1, 1):
            bx = sgn * 1.86
            for k in range(3):
                ox = (k - 1) * 0.10
                self.add(beam("spear", (bx + ox, YF + 0.16, 1.20),
                              (bx + ox * 1.9, YF + 0.30, 3.92), 0.055, 0.055,
                              M["wood_warm"]), 0.004)
                self.add(cone("spearhead", (bx + ox * 1.9, YF + 0.30, 3.92),
                              (bx + ox * 2.1, YF + 0.32, 4.24), 0.075, 4, M["iron"]),
                         0.0, 1)
            self.add(box("spear_tie", (bx, YF + 0.235, 2.06), (0.42, 0.10, 0.10),
                         M["iron"]), 0.004)
        # 门楣盾（阵营色主模块，压在门洞拱顶与上层木构之间）
        self.kite("shield_gate", (0, YF + 0.22, 5.20), "Y", SHIELD_W * 0.78, SHIELD_H * 0.78)

    # ── 4. 左前突：卫兵室 ───────────────────────────────────────────────────
    def wing_L(self):
        M = self.M
        cx = (WL_X0 + WL_X1) * 0.5
        hw = (WL_X1 - WL_X0) * 0.5
        prof = [(WL_X0, 0.0), (WL_X1, 0.0), (WL_X1, WL_EAVE), (cx, WL_RIDGE), (WL_X0, WL_EAVE)]
        self.add(extrude("wl_mass", prof, "Y", WL_Y1 - YF, (0, 0),
                         M["stone_light"], offset=(WL_Y1 + YF) * 0.5), 0.030)
        self.add(box("wl_dado", (cx, (WL_Y1 + YF) * 0.5, 0.86), (hw * 2 + 0.10, WL_Y1 - YF + 0.10, 1.32),
                     M["stone_mid"]), 0.024)
        # 山墙面：木构 + 门 + 小窗
        self.add(box("wl_door", (cx, WL_Y1 + 0.03, 1.18), (1.10, 0.12, 2.10), M["wood_warm"]), 0.012)
        for k in (-1, 1):
            self.add(box("wl_door_seam", (cx + k * 0.24, WL_Y1 + 0.09, 1.18), (0.04, 0.03, 1.94),
                         M["wood_dark"]), 0.002)
        self.add(box("wl_door_lintel", (cx, WL_Y1 + 0.07, 2.32), (1.34, 0.14, 0.18),
                     M["stone_light"]), 0.010)
        self.add(box("wl_door_glow", (cx, WL_Y1 + 0.00, 0.30), (0.96, 0.04, 0.10), M["glow"]))
        # 小方窗
        wz = 3.62
        self.add(box("wl_win", (cx, WL_Y1 + 0.05, wz), (0.62, 0.08, 0.52), M["glow"]))
        self.add(box("wl_win_frame", (cx, WL_Y1 + 0.10, wz), (0.80, 0.10, 0.66), M["wood_dark"]), 0.008)
        self.add(box("wl_win_bar", (cx, WL_Y1 + 0.15, wz), (0.05, 0.05, 0.62), M["wood_dark"]), 0.003)
        # 屋面（双坡 + 出檐）
        slope = (WL_RIDGE - WL_EAVE) / hw
        ang = math.atan(slope)
        for sgn in (-1, 1):
            xe = hw + 0.26
            ze = WL_RIDGE - slope * xe
            self.roof_slabs("wl_roof", sgn, cx, WL_RIDGE, cx + sgn * xe, ze,
                            YF + 0.02, WL_Y1 + 0.26, M["roof"], t=0.16)
            for i in range(1, 5):
                t_ = i / 4.6
                x = cx + sgn * xe * t_
                z = WL_RIDGE + (ze - WL_RIDGE) * t_
                self.add(box("wl_course", (x + sgn * math.sin(ang) * 0.14,
                                           (YF + WL_Y1) * 0.5 + 0.05, z + math.cos(ang) * 0.14),
                             (0.18, WL_Y1 - YF + 0.30, 0.06), M["roof"], rot=(0, sgn * ang, 0)), 0.006)
        self.add(box("wl_ridge", (cx, (YF + WL_Y1) * 0.5 + 0.05, WL_RIDGE + 0.08),
                     (0.30, WL_Y1 - YF + 0.34, 0.16), M["roof_edge"]), 0.014)
        # 山墙封边
        for sgn in (-1, 1):
            xe_b = hw + 0.24
            self.add(beam("wl_barge", (cx, WL_Y1 + 0.22, WL_RIDGE + 0.02),
                          (cx + sgn * xe_b, WL_Y1 + 0.22, WL_RIDGE - slope * xe_b - 0.02),
                          0.14, 0.26, M["wood_dark"]), 0.012)
        # 山墙小盾（阵营色）
        self.kite("shield_wl", (cx, WL_Y1 + 0.14, 4.16), "Y", 0.68, 0.84)

    # ── 5. 右前突：开放训练棚 ───────────────────────────────────────────────
    def wing_R(self):
        M = self.M
        # 后墙只做 1.2 m 矮墙：棚下要能看见兵器架（原来是 3.2 m 实墙，从正面看就是个方盒子）
        self.add(box("wr_back", ((WR_X0 + WR_X1) * 0.5, YF + 0.12, 0.60),
                     (WR_X1 - WR_X0, 0.24, 1.20), M["stone_mid"]), 0.016)
        # 矮墙上的小方窗（棚下有一点光，别让开口是个黑洞）
        self.add(box("wr_slit", ((WR_X0 + WR_X1) * 0.5, YF + 0.26, 0.62), (0.62, 0.06, 0.44),
                     M["glow"]), 0.004)
        # 四根柱
        for xx in (WR_X0 + 0.22, WR_X1 - 0.22):
            for yy in (YF + 0.40, WR_Y1 - 0.24):
                self.add(box("wr_post", (xx, yy, 2.20), (0.30, 0.30, 4.40), M["wood_warm"]), 0.016)
                self.add(box("wr_foot", (xx, yy, 0.12), (0.38, 0.38, 0.24), M["stone_mid"]), 0.010)
        # 单坡顶（后高前低）
        self.add(slab_plate("wr_roof", M["roof"], WR_X0 - 0.26, WR_X1 + 0.26,
                            YF - 0.10, WR_Y1 + 0.24, WR_EAVE, WR_RIDGE, 0.16), 0.020)
        ang = math.atan2(WR_EAVE - WR_RIDGE, WR_Y1 - YF)
        for i in range(5):
            yy = YF + 0.30 + i * (WR_Y1 - YF - 0.50) / 4.0
            zz = WR_EAVE + (WR_RIDGE - WR_EAVE) * (yy - YF) / (WR_Y1 - YF)
            self.add(box("wr_course", ((WR_X0 + WR_X1) * 0.5, yy, zz + 0.06),
                         (WR_X1 - WR_X0 + 0.50, 0.14, 0.05), M["roof_edge"],
                         rot=(-ang, 0, 0)), 0.005)
        # 前檐梁 + 斜撑
        self.add(box("wr_beam", ((WR_X0 + WR_X1) * 0.5, WR_Y1 - 0.10, WR_RIDGE - 0.14),
                     (WR_X1 - WR_X0 + 0.46, 0.20, 0.22), M["wood_dark"]), 0.014)
        for xx in (WR_X0 + 0.22, WR_X1 - 0.22):
            self.add(beam("wr_brace", (xx, WR_Y1 - 0.24, 3.30), (xx, WR_Y1 - 1.10, WR_RIDGE - 0.30),
                          0.12, 0.10, M["wood_dark"]), 0.008)
        # 棚下的兵器架（靠后墙）
        bx = (WR_X0 + WR_X1) * 0.5
        self.add(box("wr_rack", (bx, YF + 0.34, 1.42), (1.50, 0.14, 0.12), M["wood_dark"]), 0.006)
        for k in range(4):
            ox = -0.54 + k * 0.36
            self.add(beam("wr_pike", (bx + ox, YF + 0.42, 0.32), (bx + ox, YF + 0.40, 2.66),
                          0.05, 0.05, M["wood_warm"]), 0.003)
            self.add(cone("wr_pikehead", (bx + ox, YF + 0.40, 2.66),
                          (bx + ox, YF + 0.40, 2.94), 0.07, 4, M["iron"]), 0.0, 1)


    # ── 6. 屋面 ─────────────────────────────────────────────────────────────
    def roof_slabs(self, prefix, sign, x_ridge, z_ridge, x_eave, z_eave, y0, y1, mat, t=ROOF_T):
        ang = math.atan2(z_ridge - z_eave, abs(x_eave - x_ridge))
        ln = math.hypot(x_eave - x_ridge, z_eave - z_ridge)
        cx = (x_ridge + x_eave) * 0.5
        cz = (z_ridge + z_eave) * 0.5
        nx, nz = math.sin(ang), math.cos(ang)
        off = t * 0.5 + 0.052
        self.add(box(prefix, (cx + sign * nx * off, (y0 + y1) * 0.5, cz + nz * off),
                     (ln + 0.16, y1 - y0, t), mat, rot=(0.0, sign * ang, 0.0)), 0.026)

    def roof(self):
        M = self.M
        y0, y1 = YB - OV, YF + OV
        ze = zroof(W2 + OV)
        ang = math.atan(SLOPE)
        surf = ROOF_T * 1.052
        for sgn in (-1, 1):
            self.roof_slabs("roof_%d" % sgn, sgn, 0.0, RIDGE, sgn * (W2 + OV), ze, y0, y1,
                            M["roof"])
            for i in range(1, 12):
                t_ = i / 11.6
                x = (sgn * (W2 + OV)) * t_
                z = RIDGE + (ze - RIDGE) * t_
                nx, nz = sgn * math.sin(ang), math.cos(ang)
                self.add(box("course", (x + nx * (surf + 0.020), (y0 + y1) * 0.5,
                                        z + nz * (surf + 0.020)),
                             (0.28, y1 - y0 - 0.04, 0.08), M["roof"], rot=(0.0, sgn * ang, 0.0)), 0.010)
        # 屋脊 + 木脊梁 + 铁压条
        zc = RIDGE + 0.09
        self.add(box("ridge", (0, (y0 + y1) * 0.5, zc), (0.40, y1 - y0 + 0.06, 0.22),
                     M["roof_edge"]), 0.022)
        self.add(box("ridge_beam", (0, (y0 + y1) * 0.5, zc + 0.16), (0.16, y1 - y0 + 0.02, 0.12),
                     M["wood_dark"]), 0.008)
        self.add(box("ridge_iron", (0, (y0 + y1) * 0.5, zc + 0.225), (0.22, y1 - y0 - 0.34, 0.05),
                     M["iron"]), 0.006)
        # 檐口：封檐板 + 椽条
        for sgn in (-1, 1):
            self.add(box("fascia", (sgn * (W2 + OV - 0.05), (y0 + y1) * 0.5, ze + 0.02),
                         (0.20, y1 - y0 - 0.52, 0.30), M["wood_dark"]), 0.016)
            self.add(box("eave_tint", (sgn * (W2 + OV - 0.05), (y0 + y1) * 0.5, ze + 0.18),
                         (0.21, y1 - y0 - 0.60, 0.05), M["team_trim"]), 0.004)
            for i in range(9):
                yy = y0 + 0.40 + i * (y1 - y0 - 0.80) / 8.0
                self.add(box("rafter", (sgn * (W2 + OV - 0.26), yy, ze - 0.14),
                             (0.76, 0.13, 0.13), M["wood_dark"]), 0.008)
        # 山墙木构桁架：竖杆 + 两根斜撑（把 9.2 m 宽的三角面撑住）
        yq = y1 - 0.03
        self.add(box("gable_post", (0.0, yq, (EAVE + RIDGE) * 0.5 - 0.20), (0.16, 0.14, RIDGE - EAVE - 0.30),
                     M["wood_dark"]), 0.010)
        self.add(box("gable_tie", (0.0, yq, EAVE + 0.34), (W2 * 2 - 0.30, 0.15, 0.18),
                     M["wood_dark"]), 0.010)
        for sgn in (-1, 1):
            self.add(beam("gable_strut", (sgn * (W2 - 0.34), yq, EAVE + 0.34),
                          (sgn * 0.30, yq, RIDGE - 0.42), 0.15, 0.12, M["wood_dark"]), 0.008)
        # 山墙封边（前后各一对）
        for yy in (y1 - 0.04, y0 + 0.04):
            for sgn in (-1, 1):
                self.add(beam("barge", (0.0, yy, RIDGE + 0.02), (sgn * (W2 + OV), yy, ze - 0.02),
                              0.24, 0.32, M["wood_dark"]), 0.018)
        # 老虎窗 ×2（参考图屋面上那两个小凸起）
        for sx in (-1, 1):
            self.dormer(sx * 2.56, DOR_Y)
        self.flagpole()

    def dormer(self, x, y):
        """屋面老虎窗：小双坡 + 正面窗 + 木框，压在坡面上。"""
        M = self.M
        z0 = zroof(abs(x)) - 0.30          # 座面贴着坡
        w, d = DOR_W, 0.86
        self.add(box("dor_body", (x, y, z0 + 0.52), (w, d, 1.04), M["stone_light"]), 0.018)
        self.add(box("dor_win", (x, y + d * 0.5 + 0.02, z0 + 0.60), (0.44, 0.06, 0.46), M["glow"]))
        self.add(box("dor_frame", (x, y + d * 0.5 + 0.06, z0 + 0.60), (0.58, 0.10, 0.60),
                     M["wood_dark"]), 0.008)
        # 小双坡顶
        slope = 1.05
        for sgn in (-1, 1):
            xe = w * 0.5 + 0.14
            ze = z0 + 1.04 + 0.20 - slope * xe
            self.roof_slabs("dor_roof", sgn, x, z0 + 1.04 + 0.20, x + sgn * xe, ze,
                            y - d * 0.5 - 0.12, y + d * 0.5 + 0.14, M["roof_edge"], t=0.10)
        self.add(box("dor_ridge", (x, y + 0.01, z0 + 1.24), (0.14, d + 0.26, 0.08),
                     M["roof_edge"]), 0.006)

    def flagpole(self):
        """脊上旗杆 + 燕尾红旗：全楼最高的识别物（12.6 m）。"""
        M = self.M
        base_z = RIDGE + 0.20
        self.add(box("pole_base", (POLE_X, 0.0, base_z + 0.06), (0.34, 0.34, 0.16), M["iron"]), 0.006)
        self.add(revolve("pole", [(0.055, 0.0), (0.048, POLE_TOP - base_z)], 8,
                         (POLE_X, 0.0, base_z), M["wood_dark"]), 0.0, 1)
        self.add(revolve("pole_ball", [(0.075, 0.0), (0.060, 0.05), (0.02, 0.12)], 8,
                         (POLE_X, 0.0, POLE_TOP - 0.10), M["gold"]), 0.0, 1)
        # 旗（燕尾，沿 +X 展开）
        fw, fh = 1.30, 0.86
        zt = POLE_TOP - 0.28
        prof = [(0.0, 0.0), (fw, -0.10), (fw * 0.80, -fh * 0.5), (fw, -fh * 0.90), (0.0, -fh)]
        self.add(extrude("pole_flag", prof, "Y", 0.04, (POLE_X, zt), M["team"],
                         offset=0.02), 0.004)
        self.add(box("pole_flag_hoist", (POLE_X + 0.02, 0.0, zt - fh * 0.5), (0.06, 0.06, fh + 0.06),
                     M["iron"]), 0.003)

    # ── 7. 半木构（上层立面）────────────────────────────────────────────────
    def timber(self):
        M = self.M
        yy = YF + 0.055
        z0, z1 = 4.02, EAVE - 0.10
        # 前墙立柱：中间 3.0 m 让给营门
        for x in (-2.10, -1.55, -0.55, 0.55, 1.55, 2.10):
            self.add(box("post", (x, yy, (z0 + z1) * 0.5), (0.22, 0.13, z1 - z0),
                         M["wood_dark"]), 0.010)
        for zz in (z0 + 0.06, z1 - 0.06):
            self.add(box("rail", (0, yy, zz), (3.70, 0.14, 0.18), M["wood_dark"]), 0.010)
        # 斜撑（V 形，落在立柱之间；避开门洞）
        for (xa, xb) in ((-2.10, -1.55), (-1.55, -0.55), (0.55, 1.55), (1.55, 2.10)):
            mid = (xa + xb) * 0.5
            self.add(beam("brace", (xa + 0.12, yy, z0 + 0.20), (mid, yy, z0 + 0.86),
                          0.13, 0.10, M["wood_dark"]), 0.006)
            self.add(beam("brace", (xb - 0.12, yy, z0 + 0.20), (mid, yy, z0 + 0.86),
                          0.13, 0.10, M["wood_dark"]), 0.006)
        # 门洞上方的短撑（把 3.0 m 的开口"托"住）
        self.add(box("gate_header", (0, yy + 0.055, 3.96), (3.10, 0.15, 0.20), M["wood_dark"]), 0.010)
        # 侧墙 + 后墙：稀疏立柱（远看是一圈木框）
        for sx in (-1, 1):
            for yy2 in (-3.60, -2.10, -0.60, 0.90, 2.40):
                self.add(box("stud", (sx * (W2 + 0.02), yy2, (z0 + z1) * 0.5),
                             (0.13, 0.20, z1 - z0), M["wood_dark"]), 0.008)
            for zz in (z0 + 0.06, z1 - 0.06):
                self.add(box("rail_side", (sx * (W2 + 0.02), (YB + YF) * 0.5, zz),
                             (0.14, YF - YB - 0.10, 0.18), M["wood_dark"]), 0.008)
        for x in (-4.34, -2.20, 0.0, 2.20, 4.34):
            self.add(box("post_b", (x, YB - 0.055, (z0 + z1) * 0.5), (0.22, 0.13, z1 - z0),
                         M["wood_dark"]), 0.010)
        for zz in (z0 + 0.06, z1 - 0.06):
            self.add(box("rail_b", (0, YB - 0.055, zz), (W2 * 2 - 0.10, 0.14, 0.18),
                         M["wood_dark"]), 0.010)

    # ── 8. 阵营色标准模块 ───────────────────────────────────────────────────
    def kite(self, name, center, face, w, h, out=1):
        """标准筝形盾：金边 + 阵营色盾面 + 交叉长矛纹章。"""
        M = self.M
        cx, cy, cz = center
        if face == "Y":
            self.add(kite_shield(name + "_rim", (cx, cy, cz), w + 0.14, h + 0.14, 0.08,
                                 M["gold"]), 0.012)
            self.add(kite_shield(name + "_field", (cx, cy + 0.05, cz), w, h, 0.09,
                                 M["team"]), 0.012)
            self.emblem(name, "Y", cx, cy + 0.115, cz, w, h)
        else:
            hw, hh = w * 0.5, h * 0.5
            prof = [(-hh, hw), (hh, hw), (hh * 0.90, -hw * 0.12), (0.0, -hw), (-hh * 0.90, -hw * 0.12)]
            pb = [(p[0] - 0.07, p[1] + 0.07) for p in prof]
            self.add(extrude(name + "_rim", pb, "X", 0.08, (cy, cz), M["gold"],
                             offset=cx + out * 0.01), 0.012)
            self.add(extrude(name + "_field", prof, "X", 0.09, (cy, cz), M["team"],
                             offset=cx + out * 0.06), 0.012)
            self.emblem(name, "X", cx + out * 0.11, cy, cz, w, h)

    def emblem(self, name, face, cx, cy, cz, w, h):
        """纹章：交叉长矛（两杆 + 两个矛尖），比锤更"军营"。"""
        M = self.M
        a = math.radians(32)
        L_ = min(w, h) * 0.66
        dx, dz = math.cos(a) * L_ * 0.5, math.sin(a) * L_ * 0.5
        if face == "Y":
            for sgn in (-1, 1):
                self.add(beam(name + "_shaft", (cx - sgn * dx, cy, cz - dz + h * 0.02),
                              (cx + sgn * dx, cy, cz + dz + h * 0.02), 0.06, 0.05,
                              M["team_trim"]), 0.004)
                self.add(cone(name + "_tip", (cx + sgn * dx * 1.02, cy, cz + dz + h * 0.02),
                              (cx + sgn * dx * 1.22, cy, cz + dz + h * 0.02 + 0.16), 0.07, 4,
                              M["team_trim"]), 0.003)
        else:
            for sgn in (-1, 1):
                self.add(beam(name + "_shaft", (cx, cy - sgn * dx, cz - dz + h * 0.02),
                              (cx, cy + sgn * dx, cz + dz + h * 0.02), 0.05, 0.06,
                              M["team_trim"]), 0.004)
                self.add(cone(name + "_tip", (cx, cy + sgn * dx * 1.02, cz + dz + h * 0.02),
                              (cx, cy + sgn * dx * 1.22, cz + dz + h * 0.02 + 0.16), 0.07, 4,
                              M["team_trim"]), 0.003)

    def wallbanner(self, name, center, face, w=1.80, h=2.20):
        """墙面横幅（大块染色面）：上下木杆 + 燕尾 + 交叉长矛。"""
        M = self.M
        cx, cy, cz = center
        hw, hh = w * 0.5, h * 0.5
        prof = [(-hw, hh), (hw, hh), (hw, -hh * 0.72), (hw * 0.30, -hh),
                (-hw * 0.30, -hh), (-hw, -hh * 0.72)]
        if face == "Y":
            self.add(extrude(name + "_cloth", prof, "Y", 0.07, (cx, cz), M["team"], offset=cy), 0.012)
            self.add(box(name + "_rod_t", (cx, cy, cz + hh + 0.03), (w + 0.28, 0.10, 0.11),
                         M["wood_dark"]), 0.008)
            self.add(box(name + "_rod_b", (cx, cy, cz - hh - 0.02), (w + 0.10, 0.09, 0.09),
                         M["wood_dark"]), 0.006)
            for sgn in (-1, 1):
                self.add(box(name + "_fringe", (cx + sgn * hw * 0.62, cy, cz - hh - 0.13),
                             (w * 0.13, 0.06, 0.20), M["team_trim"]), 0.004)
            self.emblem(name, "Y", cx, cy + 0.075, cz + h * 0.05, w * 0.78, h * 0.62)
        else:
            self.add(extrude(name + "_cloth", prof, "X", 0.07, (cy, cz), M["team"], offset=cx), 0.012)
            self.add(box(name + "_rod_t", (cx, cy, cz + hh + 0.03), (0.10, w + 0.28, 0.11),
                         M["wood_dark"]), 0.008)
            self.add(box(name + "_rod_b", (cx, cy, cz - hh - 0.02), (0.09, w + 0.10, 0.09),
                         M["wood_dark"]), 0.006)
            for sgn in (-1, 1):
                self.add(box(name + "_fringe", (cx, cy + sgn * hw * 0.62, cz - hh - 0.13),
                             (0.06, w * 0.13, 0.20), M["team_trim"]), 0.004)
            self.emblem(name, "X", cx + 0.075, cy, cz + h * 0.05, w * 0.78, h * 0.62)

    def heraldry(self):
        M = self.M
        # ① 门侧两面垂旗（正视里最大的一块阵营色）
        for sgn in (-1, 1):
            self.banner("banner", sgn * 1.35, 4.04)
        # ② 山墙腰线（压在 gable_tie 下的横带）
        self.add(box("gable_band", (0, YF + 0.075, 7.34), (4.20, 0.13, 0.26), M["team"]), 0.008)
        self.add(box("gable_band_t", (0, YF + 0.075, 7.50), (4.20, 0.13, 0.05), M["team_trim"]), 0.004)
        # ③ 侧墙大横幅（每侧一条，落在木构层）
        for sx, tag in ((-1, "L"), (1, "R")):
            self.wallbanner("wbanner_" + tag, (sx * (W2 + 0.17), 0.70, 5.40), "X", 1.70, 1.98)
        # ④ 山墙盾（主屋前山墙尖下）
        self.kite("shield_gable", (0, YF + 0.10, 8.72), "Y", SHIELD_W * 0.92, SHIELD_H * 0.92)
        # ⑤ 侧墙盾
        for sx, tag in ((-1, "L"), (1, "R")):
            self.kite("shield_side_" + tag, (sx * (W2 + 0.06), -2.10, 4.30), "X",
                      1.10, 1.34, out=sx)
        # ⑥ 后墙横幅
        self.wallbanner("wbanner_b", (0, YB - 0.12, 5.10), "Y", 1.76, 2.04)

    # ── 9. 窗 ───────────────────────────────────────────────────────────────
    def windows(self):
        M = self.M
        # 前墙底层：左右都被前突/训练棚占住，没有可开窗的面 —— 窗全部落在侧墙与后墙
        pass
        # 侧墙：每侧两扇（落在木构立柱之间）
        for sx in (-1, 1):
            for yy in (0.10, 1.70):
                self.arch_win("win_s", (sx * (W2 + 0.01), yy, 1.72), 0.58, 1.34, "X", out=sx)
        # 后墙：两扇
        for sgn in (-1, 1):
            self.arch_win("win_b", (sgn * 2.58, YB - 0.03, 1.72), 0.54, 1.28, "Y", out=-1)
        # 前墙最外侧两处箭孔（窄缝，压住大面积素墙）
        for sgn in (-1, 1):
            self.add(box("arrow_slit", (sgn * 3.86, YF + 0.03, 2.10), (0.22, 0.16, 0.86),
                         M["coal"]), 0.006)
            self.add(box("arrow_frame", (sgn * 3.86, YF + 0.01, 2.10), (0.38, 0.14, 1.02),
                         M["stone_mid"]), 0.008)

    def arch_win(self, name, center, w, h, face, out=1):
        """拱顶窄窗：glow 窗洞 + 石框 + 木窗棂 + 窗台。face = 'Y' / 'X'。"""
        M = self.M
        cx, cy, cz = center
        hw = w * 0.5
        straight = h - hw
        if face == "Y":
            self.add(extrude(name, arch_profile(w, straight, segs=6), "Y", 0.10, (cx, cz),
                             M["glow"], offset=cy), 0.0)
            self.add(arch_band(name + "_arch", cx, cz + straight, hw, hw + 0.14,
                               cy + out * 0.04, cy + out * 0.12, M["stone_light"], segs=6), 0.008)
            for sgn in (-1, 1):
                self.add(box(name + "_jamb", (cx + sgn * (hw + 0.06), cy + out * 0.06,
                                              cz + straight * 0.5),
                             (0.13, 0.12, straight), M["stone_light"]), 0.006)
            self.add(box(name + "_bar", (cx, cy + out * 0.08, cz + straight * 0.5),
                         (0.05, 0.06, straight), M["wood_dark"]), 0.003)
            self.add(box(name + "_sill", (cx, cy + out * 0.06, cz - 0.05),
                         (w + 0.30, 0.20, 0.10), M["stone_light"]), 0.008)
        else:
            self.add(extrude(name, arch_profile(w, straight, segs=6), "X", 0.10, (cy, cz),
                             M["glow"], offset=cx + out * 0.01), 0.0)
            self.add(arch_band(name + "_arch", cx, cz + straight, hw, hw + 0.14,
                               cy - hw - 0.14, cy + hw + 0.14, M["stone_light"], segs=6), 0.008)
            for sgn in (-1, 1):
                self.add(box(name + "_jamb", (cx + out * 0.06, cy + sgn * (hw + 0.06),
                                              cz + straight * 0.5),
                             (0.12, 0.13, straight), M["stone_light"]), 0.006)
            self.add(box(name + "_bar", (cx + out * 0.08, cy, cz + straight * 0.5),
                         (0.06, 0.05, straight), M["wood_dark"]), 0.003)
            self.add(box(name + "_sill", (cx + out * 0.06, cy, cz - 0.05),
                         (0.20, w + 0.30, 0.10), M["stone_light"]), 0.008)

    # ── 10. 细部 ────────────────────────────────────────────────────────────
    def details(self):
        M = self.M
        # 门侧提灯
        for sgn in (-1, 1):
            lx = sgn * 1.64
            self.add(beam("lan_arm", (lx, YF + 0.10, 3.12), (lx, YF + 0.48, 3.12),
                          0.06, 0.06, M["iron"]), 0.004)
            self.add(box("lan_cage", (lx, YF + 0.42, 2.86), (0.22, 0.22, 0.30), M["glow"]), 0.008)
            self.add(box("lan_top", (lx, YF + 0.42, 3.04), (0.28, 0.28, 0.08), M["iron"]), 0.006)
            self.add(box("lan_hang", (lx, YF + 0.42, 3.13), (0.05, 0.05, 0.10), M["iron"]), 0.003)
        # 门楣雨棚：把中央大门"压住"，也给立面加一层轮廓
        py0, py1 = YF + 0.02, YF + 1.06
        self.add(slab_plate("gate_awning", M["roof_edge"], -1.92, 1.92, py0, py1, 4.44, 4.10, 0.14), 0.014)
        for sgn in (-1, 1):
            self.add(beam("awning_brace", (sgn * 1.72, YF + 0.10, 3.90), (sgn * 1.72, YF + 0.92, 4.06),
                          0.10, 0.10, M["wood_dark"]), 0.006)
            self.add(box("awning_tip", (sgn * 1.86, py1 - 0.06, 4.10), (0.12, 0.16, 0.20),
                         M["wood_dark"]), 0.006)
        # 后门（小，通后院）
        self.add(box("back_door", (0.0, YB - 0.03, 1.24), (1.06, 0.12, 2.10), M["wood_warm"]), 0.010)
        self.add(box("back_lintel", (0.0, YB - 0.07, 2.38), (1.30, 0.14, 0.18), M["stone_light"]), 0.010)
        # 柴堆（后墙外）
        for i in range(4):
            for j in range(3 - (i % 2)):
                self.add(cyl("firelog", (-3.9 + i * 0.27, YB - 1.05, 0.14 + j * 0.25),
                             0.13, 1.30, 8, M["wood_warm"], axis="Y"), 0.006)
        # 侧墙盾架（三面小盾挂在木架上）
        for sx, tag in ((-1, "L"), (1, "R")):
            by = -2.90
            self.add(box("rack_side", (sx * (W2 + 0.18), by, 1.94), (0.16, 1.90, 0.14),
                         M["wood_dark"]), 0.008)
            for k in range(3):
                self.add(box("buckler", (sx * (W2 + 0.28), by - 0.56 + k * 0.56, 1.76),
                             (0.10, 0.40, 0.44), M["team_trim"]), 0.008)

    # ── 11. 前场训练场 ──────────────────────────────────────────────────────
    def yard(self):
        M = self.M
        # 围栏：U 形（后 + 左右），前面留 4.0 m 开口
        self.fence_run("fence_b", (0, YARD_Y1), (1, 0), 6.30)
        self.fence_run("fence_l", (-FENCE_X, YARD_Y0 + 0.30), (0, 1), 5.60)
        self.fence_run("fence_r", (FENCE_X, YARD_Y0 + 0.30), (0, 1), 5.60)
        # 两个训练假人
        self.dummy("dummy_a", (-3.60, 9.30))
        self.dummy("dummy_b", (2.00, 10.40))
        # 武器架
        self.weapon_rack("wrack", (4.55, 8.10))
        # 桶 / 箱
        self.barrel("barrel_a", (-4.95, 11.30), 0.42, 0.86)
        self.barrel("barrel_b", (3.20, 11.40), 0.38, 0.78)
        self.add(box("crate_a", (-4.70, 7.00, 0.52), (0.86, 0.70, 0.64), M["wood_warm"]), 0.012)
        for k in (-1, 1):
            self.add(box("crate_band", (-4.70, 7.00 + k * 0.24, 0.52), (0.90, 0.08, 0.68),
                         M["iron"]), 0.004)

    def fence_run(self, name, p0, d, length):
        """一段木栅栏：立柱 + 两道横杆。d 是方向单位向量。"""
        M = self.M
        n = int(length / 0.92) + 1
        for i in range(n):
            x = p0[0] + d[0] * i * (length / max(n - 1, 1))
            y = p0[1] + d[1] * i * (length / max(n - 1, 1))
            self.add(box(name + "_post", (x, y, 0.66), (0.20, 0.20, 1.32), M["wood_warm"]), 0.010)
            self.add(cone(name + "_tip", (x, y, 1.32), (x, y, 1.50), 0.14, 4, M["wood_warm"]), 0.0, 1)
        for zz in (0.56, 1.14):
            cx = p0[0] + d[0] * length * 0.5
            cy = p0[1] + d[1] * length * 0.5
            sx = abs(d[0]) * length + abs(d[1]) * 0.10
            sy = abs(d[1]) * length + abs(d[0]) * 0.10
            self.add(box(name + "_rail", (cx, cy, zz), (sx + 0.10, sy + 0.10, 0.14),
                         M["wood_dark"]), 0.006)

    def dummy(self, name, p):
        """训练假人：石座 + 立杆 + 横臂 + 草靶 + 头。"""
        M = self.M
        x, y = p
        self.add(box(name + "_base", (x, y, 0.16), (0.78, 0.78, 0.32), M["stone_mid"]), 0.012)
        self.add(cyl(name + "_post", (x, y, 0.32), 0.14, 1.70, 8, M["wood_warm"]), 0.008)
        self.add(box(name + "_arm", (x, y, 1.52), (1.46, 0.16, 0.16), M["wood_warm"]), 0.008)
        # 草靶（横臂两端各一束）
        for sgn in (-1, 1):
            self.add(cyl(name + "_bale", (x + sgn * 0.60, y, 1.40), 0.26, 0.50, 8,
                         M["roof_wood"]), 0.010)
        # 躯干：方草靶 + 两道草绳 + 方头（原来用回转体，俯视看就是两个蘑菇）
        self.add(box(name + "_body", (x, y, 1.04), (0.52, 0.38, 0.86), M["roof_wood"]), 0.014)
        for zz in (0.78, 1.30):
            self.add(box(name + "_cord", (x, y, zz), (0.56, 0.42, 0.07), M["wood_dark"]), 0.004)
        self.add(box(name + "_head", (x, y, 1.68), (0.34, 0.32, 0.40), M["roof_wood"]), 0.010)
        self.add(box(name + "_cord_n", (x, y, 1.54), (0.30, 0.28, 0.07), M["wood_dark"]), 0.003)

    def weapon_rack(self, name, p):
        """武器架：两根立柱 + 三根横杆 + 靠在上面的长矛。"""
        M = self.M
        x, y = p
        for sgn in (-1, 1):
            self.add(box(name + "_post", (x + sgn * 0.62, y, 0.76), (0.14, 0.14, 1.52),
                         M["wood_dark"]), 0.008)
        for zz in (0.62, 1.10):
            self.add(box(name + "_rail", (x, y, zz), (1.40, 0.12, 0.10), M["wood_dark"]), 0.006)
        for k in range(3):
            ox = -0.30 + k * 0.30
            self.add(beam(name + "_pike", (x + ox, y - 0.10, 0.24), (x + ox, y - 0.34, 2.30),
                          0.05, 0.05, M["wood_warm"]), 0.003)
            self.add(cone(name + "_tip", (x + ox, y - 0.34, 2.30), (x + ox, y - 0.36, 2.56),
                          0.065, 4, M["iron"]), 0.0, 1)

    def barrel(self, name, p, r, h):
        M = self.M
        x, y = p
        self.add(lathe(name, [(0.0, 0.0, x, y), (r * 0.84, 0.0, x, y), (r, h * 0.34, x, y),
                              (r, h * 0.66, x, y), (r * 0.84, h, x, y), (0.0, h, x, y)],
                       12, M["wood_warm"]), 0.014, 1)
        for zz in (h * 0.28, h * 0.72):
            self.add(tube_band(name + "_hoop", (x, y), r * 0.97, r * 1.03, zz, zz + 0.07, 12,
                               M["iron"]), 0.004)

    # ── 12. 组装 ────────────────────────────────────────────────────────────
    def build(self):
        for step in (self.base, self.mass, self.gate, self.wing_L, self.wing_R,
                     self.roof, self.timber, self.windows, self.heraldry,
                     self.details, self.yard):
            step()
        return self

    def finalize(self):
        for (ob, bev, sub, seg) in self.items:
            L.finalize(ob, bevel=bev, seg=seg, sub=sub, flat=not self.smooth)
        objs = [it[0] for it in self.items]
        bpy.ops.object.select_all(action="DESELECT")
        for ob in objs:
            ob.select_set(True)
        bpy.context.view_layer.objects.active = objs[0]
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        bpy.ops.object.select_all(action="DESELECT")
        out = L.join_by_material(objs, prefix="BR")
        mirror_x(out)
        if self.unwrap:
            L.smart_uv(out)
        return out


def build(smooth=True, unwrap=True):
    m = Model(smooth, unwrap).build()
    objs = m.finalize()
    return objs, L.stats(objs)
