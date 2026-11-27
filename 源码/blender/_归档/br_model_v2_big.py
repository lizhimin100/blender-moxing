"""
br_model.py —— 兵营（Barracks）v2：平顶垛口 + 大训练场

v2 改形制：v1 是"双坡 + 左右前突"，与铁匠铺太像。这一版按六座资产包的约定，
兵营改成 **flat_crenel（平顶 + 垛口）**，这是它与其他五座最硬的区分：

  ① 主体是一个 12 × 9 的石砌矩形体量，**平顶**，顶部一圈女儿墙 + 垛口
  ② 前右角凸出一个 3.2 × 2.4 的**角楼**，比主体高 1.8 m，自带垛口 + 旗
  ③ 左侧**外挂折返石梯**，从地面直上屋顶平台
  ④ 中央拱门（简化：一级门槛，不做台阶群）+ 门楣盾
  ⑤ 前场是一个 19 × 11.6 的**训练场**：三面木栅栏半包，里面三具草靶假人、
     两座武器架、一座盔甲架、两个圆靶、桶箱沙袋
  ⑥ 阵营色：女儿墙下的整圈饰带 + 三条大横幅 + 四面盾 + 两面旗 + 门侧墙板

坐标：X 右、Y 前（+Y = 正面）、Z 上；原点在占地中心，z = 0 地面。
建模期左侧（−X）放楼梯，交付前整体沿 X 镜像一次（与铁匠铺一致）。
"""
import math
import random

import bpy

import bslib as L
from bslib import (arch_band, beam, box, cone, cyl, extrude, frustum, kite_shield,
                   lathe, mesh_obj, octa_profile, revolve, ring_y, slab_plate,
                   taper_box, tube_band)

# ── 主体 ──────────────────────────────────────────────────────────────────────
W2 = 6.00                       # 半宽（总宽 12.0）
YF = 4.50                       # 前墙
YB = -4.50                      # 后墙（进深 9.0）
H1 = 4.30                       # 一层顶
H2 = 8.50                       # 二层顶 / 屋顶平台
PARA = 1.35                     # 女儿墙高
PARA_T = 0.45                   # 女儿墙厚
MERLON_H = 0.60                 # 垛口高
MERLON_W = 0.95                 # 垛口宽
MERLON_GAP = 0.80               # 垛口净距

# 角楼（前右）
T_X0, T_X1 = 3.30, 6.00
T_Y1 = 6.90                     # 从前墙 4.50 凸出 2.40
T_TOP = 12.60                   # 含自己的垛口

# 外挂楼梯（左侧，建模期 −X）
ST_X = -3.35                    # 楼梯外侧贴墙（放在背面偏左，正面完全被主体挡住）
ST_W = 1.25                     # 梯段宽
ST_LAND_Y = -5.50               # 中间平台位置（y，楼梯整体移到背面）

# 拱门
GATE_W, GATE_SPRING = 2.10, 2.70   # 拱顶 = 2.70 + 1.05 = 3.75

# 前场训练场
YARD_Y0, YARD_Y1 = 7.00, 18.60
YARD_X = 9.40
FENCE_H = 1.55

# 阵营色标准模块
SHIELD_W, SHIELD_H = 1.26, 1.50
BANNER_W, BANNER_H = 0.62, 1.30


def zroof(x):
    return H2


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

    # ── 1. 基座、门槛、前场夯土 ─────────────────────────────────────────────
    def base(self):
        M = self.M
        self.add(box("plinth_a", (0, -0.10, 0.24), (12.60, 9.60, 0.48), M["stone_dark"]))
        self.add(box("plinth_b", (0, -0.10, 0.09), (12.96, 9.96, 0.18), M["stone_mid"]))
        # 门槛（一级，不做台阶群）
        self.add(box("threshold", (0, YF + 0.30, 0.24), (GATE_W + 0.70, 0.60, 0.48),
                     M["stone_light"]), 0.012)
        # 前场夯土：比石台低一档
        self.add(box("yard", (0.00, (YARD_Y0 + YARD_Y1) * 0.5, 0.10),
                     (YARD_X * 2 + 0.4, YARD_Y1 - YARD_Y0, 0.20), M["stone_mid"]), 0.030)
        self.add(box("yard_kerb", (0.00, YARD_Y1 + 0.10, 0.06), (YARD_X * 2 + 0.4, 0.20, 0.12),
                     M["stone_dark"]), 0.014)
        # 夯土带（三条深浅，破"一整块灰板"）
        for i, (yy, ww, mat) in enumerate(((8.60, 0.34, "stone_light"),
                                           (12.10, 0.26, "stone_dark"),
                                           (15.60, 0.30, "stone_light"))):
            self.add(box("yard_band%d" % i, (0.00, yy, 0.205), (YARD_X * 2, ww, 0.03), M[mat]), 0.004)
        # 场地中线（练兵列队的痕迹）
        self.add(box("yard_axis", (0.00, 12.60, 0.212), (0.16, YARD_Y1 - YARD_Y0 - 0.6, 0.02),
                     M["stone_dark"]), 0.0)

    # ── 2. 主体（矩形 + 平顶）──────────────────────────────────────────────
    def mass(self):
        M = self.M
        gw = GATE_W * 0.5
        z_t = GATE_SPRING + gw
        # 前墙三块（真挖拱洞）
        left = [(-W2, 0.0), (-gw, 0.0), (-gw, H2), (-W2, H2)]
        right = [(gw, 0.0), (W2, 0.0), (W2, H2), (gw, H2)]
        for name, prof in (("mass_front_L", left), ("mass_front_R", right)):
            self.add(extrude(name, prof, "Y", 0.80, (0, 0), M["stone_light"],
                             offset=YF - 0.40), 0.030)
        top = [(-gw, z_t), (-gw, H2), (gw, H2), (gw, z_t)]
        for s in range(1, 10):
            a = math.pi * s / 10
            top.append((gw * math.cos(a), GATE_SPRING + gw * math.sin(a)))
        self.add(extrude("mass_front_T", top, "Y", 0.80, (0, 0), M["stone_light"],
                         offset=YF - 0.40), 0.030)
        # 后段实心
        pent = [(-W2, 0.0), (W2, 0.0), (W2, H2), (-W2, H2)]
        self.add(extrude("mass_back", pent, "Y", YF - 0.80 - YB, (0, 0),
                         M["stone_light"], offset=(YF - 0.80 + YB) * 0.5), 0.035)
        # 石基座（0–1.30）+ 腰线
        self.add(box("dado", (0, (YF + YB) * 0.5, 0.65), (W2 * 2 + 0.10, YF - YB + 0.10, 1.30),
                     M["stone_mid"]), 0.028)
        self.add(box("plinth_band", (0, (YF + YB) * 0.5, 1.36), (W2 * 2 + 0.18, YF - YB + 0.18, 0.14),
                     M["stone_dark"]), 0.014)
        for sgn in (-1, 1):
            x0, x1 = sgn * gw, sgn * (W2 + 0.05)
            self.add(box("dado_front", ((x0 + x1) * 0.5, YF + 0.05, 0.70),
                         (abs(x1 - x0), 0.12, 1.36), M["stone_mid"]), 0.016)
        # 二层腰线（石 / 木构分界）
        self.add(box("string", (0, (YF + YB) * 0.5, H1), (W2 * 2 + 0.20, YF - YB + 0.20, 0.18),
                     M["stone_light"]), 0.016)
        for sgn in (-1, 1):
            x0, x1 = sgn * gw, sgn * (W2 + 0.10)
            self.add(box("string_f", ((x0 + x1) * 0.5, YF + 0.04, H1),
                         (abs(x1 - x0), 0.16, 0.18), M["stone_light"]), 0.012)
        # 隅石（四角）
        for sx in (-1, 1):
            for sy, yface in ((1, YF), (-1, YB)):
                for i in range(3):
                    zz = 0.98 + i * 0.80
                    if zz > 2.9:
                        break
                    self.add(box("quoin", (sx * (W2 - 0.16), yface - sy * 0.20, zz),
                                 (0.50 + (0.06 if i % 2 else 0.0), 0.46, 0.44), M["stone_mid"]))
        # 侧墙扶壁（三条）
        for sx in (-1, 1):
            for yy in (-3.10, -0.60, 1.90):
                self.add(box("buttress", (sx * (W2 + 0.16), yy, 2.10),
                             (0.32, 0.62, 3.90), M["stone_mid"]), 0.024)

    # ── 3. 女儿墙 + 垛口 ────────────────────────────────────────────────────
    def parapet(self):
        M = self.M
        z0, z1 = H2, H2 + PARA
        self.add(box("para_b", (0, YB + PARA_T * 0.5, (z0 + z1) * 0.5),
                     (W2 * 2, PARA_T, PARA), M["stone_light"]), 0.018)
        for sx in (-1, 1):
            self.add(box("para_s", (sx * (W2 - PARA_T * 0.5), (YF + YB) * 0.5, (z0 + z1) * 0.5),
                         (PARA_T, YF - YB, PARA), M["stone_light"]), 0.018)
        # 前墙女儿墙：从左角一直做到角楼左边缘
        fx0, fx1 = -W2, T_X0
        self.add(box("para_f", ((fx0 + fx1) * 0.5, YF - PARA_T * 0.5, (z0 + z1) * 0.5),
                     (fx1 - fx0, PARA_T, PARA), M["stone_light"]), 0.018)
        for (cx, cy, sx_, sy_) in ((0, YB + PARA_T * 0.5, W2 * 2 + 0.12, PARA_T + 0.14),
                                   (-W2 + PARA_T * 0.5, (YF + YB) * 0.5, PARA_T + 0.14, YF - YB),
                                   (W2 - PARA_T * 0.5, (YF + YB) * 0.5, PARA_T + 0.14, YF - YB)):
            self.add(box("para_cap", (cx, cy, z1 + 0.07), (sx_, sy_, 0.14), M["stone_dark"]), 0.012)
        # 垛口：沿后墙、两侧墙、前墙左段
        self.merlon_row("ml_b", (-W2 + 0.5, YB + PARA_T * 0.5), (1, 0), W2 * 2 - 1.0, z1)
        self.merlon_row("ml_l", (-W2 + PARA_T * 0.5, YB + 0.5), (0, 1), YF - YB - 1.0, z1)
        self.merlon_row("ml_r", (W2 - PARA_T * 0.5, YB + 0.5), (0, 1), YF - YB - 1.0, z1)
        self.merlon_row("ml_f", (-W2 + 0.4, YF - PARA_T * 0.5), (1, 0), W2 + T_X0 - 0.8, z1)

    def merlon_row(self, name, p0, d, length, z0):
        M = self.M
        step = MERLON_W + MERLON_GAP
        n = max(2, int(round(length / step)))
        for i in range(n + 1):
            t = i / n
            x = p0[0] + d[0] * (t * length)
            y = p0[1] + d[1] * (t * length)
            sx = MERLON_W * abs(d[1]) + (PARA_T - 0.06) * abs(d[0])
            sy = MERLON_W * abs(d[0]) + (PARA_T - 0.06) * abs(d[1])
            self.add(box(name, (x, y, z0 + MERLON_H * 0.5), (sx, sy, MERLON_H),
                         M["stone_mid"]), 0.012)
            self.add(box(name + "_cap", (x, y, z0 + MERLON_H + 0.04),
                         (sx + 0.06, sy + 0.06, 0.08), M["stone_dark"]), 0.006)

    # ── 4. 前右角楼 ─────────────────────────────────────────────────────────
    def tower(self):
        M = self.M
        cx = (T_X0 + T_X1) * 0.5
        w, d = T_X1 - T_X0, T_Y1 - YF
        cy = (YF + T_Y1) * 0.5
        self.add(box("tw_body", (cx, cy, T_TOP * 0.42), (w, d, T_TOP * 0.84), M["stone_light"]), 0.030)
        self.add(box("tw_dado", (cx, cy, 0.62), (w + 0.10, d + 0.10, 1.24), M["stone_mid"]), 0.024)
        self.add(box("tw_band", (cx, cy, 1.30), (w + 0.18, d + 0.18, 0.14), M["stone_dark"]), 0.012)
        self.add(box("tw_string", (cx, cy, H1), (w + 0.16, d + 0.16, 0.18), M["stone_light"]), 0.014)
        for sx in (-1, 1):
            for sy in (-1, 1):
                for i in range(3):
                    self.add(box("tw_quoin", (cx + sx * (w * 0.5 - 0.14), cy + sy * (d * 0.5 - 0.14),
                                              0.98 + i * 0.80),
                                 (0.46, 0.46, 0.44), M["stone_mid"]))
        # 顶部平台 + 女儿墙 + 垛口
        cap_z = T_TOP - MERLON_H - 0.30
        self.add(box("tw_floor", (cx, cy, cap_z), (w + 0.10, d + 0.10, 0.20), M["stone_dark"]), 0.010)
        for (dx, dy, sx_, sy_) in ((0, -d * 0.5 + 0.16, w, 0.34),
                                   (0, d * 0.5 - 0.16, w, 0.34),
                                   (-w * 0.5 + 0.16, 0, 0.34, d),
                                   (w * 0.5 - 0.16, 0, 0.34, d)):
            self.add(box("tw_para", (cx + dx, cy + dy, cap_z + 0.34), (sx_, sy_, 0.68),
                         M["stone_light"]), 0.014)
        self.merlon_row("tw_merlon_f", (cx - w * 0.5 + 0.4, cy - d * 0.5 + 0.16), (1, 0), w - 0.8,
                        cap_z + 0.68)
        self.merlon_row("tw_merlon_r", (cx + w * 0.5 - 0.16, cy - d * 0.5 + 0.4), (0, 1), d - 0.8,
                        cap_z + 0.68)
        # 角楼正面的窗（暖光）
        self.add(box("tw_win", (cx, T_Y1 + 0.02, 5.60), (0.86, 0.10, 1.30), M["glow"]))
        self.add(box("tw_win_frame", (cx, T_Y1 + 0.08, 5.60), (1.06, 0.14, 1.50), M["wood_dark"]), 0.010)
        self.add(box("tw_win_bar", (cx, T_Y1 + 0.14, 5.60), (0.06, 0.06, 1.40), M["wood_dark"]), 0.004)
        self.add(box("tw_win_lintel", (cx, T_Y1 + 0.10, 6.42), (1.24, 0.14, 0.18), M["stone_light"]), 0.010)
        # 下层箭孔
        self.add(box("tw_slit", (cx, T_Y1 + 0.04, 2.30), (0.20, 0.14, 0.90), M["coal"]), 0.006)
        self.add(box("tw_slit_f", (cx, T_Y1 + 0.01, 2.30), (0.36, 0.12, 1.04), M["stone_mid"]), 0.008)
        # 角楼旗杆
        self.add(revolve("tw_pole", [(0.045, 0.0), (0.040, 1.60)], 6, (cx, cy, cap_z + 1.00),
                         M["wood_dark"]), 0.0, 1)
        self.add(revolve("tw_ball", [(0.06, 0.0), (0.05, 0.04), (0.02, 0.10)], 6,
                         (cx, cy, cap_z + 2.54), M["gold"]), 0.0, 1)
        prof = [(0.0, 0.0), (1.06, -0.08), (0.86, -0.34), (1.06, -0.60), (0.0, -0.62)]
        self.add(extrude("tw_flag", prof, "Y", 0.04, (cx, cap_z + 2.40), M["team"], offset=cy), 0.004)

    # ── 6. 营门（简化：拱券 + 双开门 + 门楣盾 + 门侧阵营色墙板）──────────────
    def gate(self):
        M = self.M
        gw = GATE_W * 0.5
        # 门洞里的暖光（贴在后墙上）
        self.add(box("gate_glow", (0, YF - 0.76, 2.10), (GATE_W - 0.16, 0.04, 3.10), M["glow"]))
        # 拱券石 + 门框 + 拱心石
        self.add(arch_band("gate_arch", 0.0, GATE_SPRING, gw, gw + 0.28,
                           YF - 0.06, YF + 0.14, M["stone_light"], segs=10), 0.020)
        for sgn in (-1, 1):
            self.add(box("gate_jamb", (sgn * (gw + 0.13), YF + 0.04, GATE_SPRING * 0.5 + 0.24),
                         (0.26, 0.26, GATE_SPRING - 0.48), M["stone_light"]), 0.018)
        self.add(box("gate_key", (0.0, YF + 0.10, GATE_SPRING + gw - 0.02),
                     (0.32, 0.28, 0.44), M["stone_mid"]), 0.016)
        # 双开木门（各向里开 20°）
        leaf = (GATE_W - 0.12) * 0.5
        for sgn in (-1, 1):
            a = math.radians(20)
            rot_z = -a if sgn < 0 else math.pi + a
            hx = sgn * (gw - 0.04)
            px = hx + math.cos(rot_z) * leaf * 0.5
            py = (YF - 0.30) + math.sin(rot_z) * leaf * 0.5
            self.add(box("gate_leaf", (px, py, 1.78), (leaf, 0.10, 3.00),
                         M["wood_warm"], rot=(0, 0, rot_z)), 0.014)
            for k in (-1, 1):
                self.add(box("gate_seam", (px + k * 0.19 * math.cos(rot_z),
                                           py + k * 0.19 * math.sin(rot_z), 1.78),
                             (0.04, 0.03, 2.86), M["wood_dark"], rot=(0, 0, rot_z)), 0.002)
            for zz in (1.05, 2.40):
                self.add(box("gate_iron", (px, py, zz), (leaf - 0.10, 0.12, 0.11),
                             M["iron"], rot=(0, 0, rot_z)), 0.006)
        # 门框两侧的阵营色壁柱（0.34 宽，贴石门框外侧，做成"门套"而不是"贴布"）
        for sgn in (-1, 1):
            self.add(box("gate_pilaster", (sgn * 1.42, YF + 0.08, 2.10), (0.34, 0.14, 3.30),
                         M["team"]), 0.010)
            self.add(box("gate_pilaster_t", (sgn * 1.42, YF + 0.10, 3.80), (0.38, 0.16, 0.12),
                         M["team_trim"]), 0.004)
        # 门楣盾
        self.kite("shield_gate", (0.0, YF + 0.20, 5.30), "Y", SHIELD_W * 0.9, SHIELD_H * 0.9)

    # ── 7. 二层半木构 ───────────────────────────────────────────────────────
    def timber(self):
        M = self.M
        yy = YF + 0.055
        z0, z1 = H1 + 0.10, H2 - 0.10
        # 前墙：角楼左侧
        for x in (-5.80, -4.45, -3.10, -1.75, -0.50, 0.50, 1.75, 3.10):
            self.add(box("post", (x, yy, (z0 + z1) * 0.5), (0.20, 0.13, z1 - z0),
                         M["wood_dark"]), 0.009)
        for zz in (z0 + 0.06, (z0 + z1) * 0.5, z1 - 0.06):
            self.add(box("rail", (-1.35, yy, zz), (8.90, 0.14, 0.17), M["wood_dark"]), 0.009)
        for (xa, xb) in ((-5.80, -4.45), (-4.45, -3.10), (-3.10, -1.75),
                         (1.75, 3.10), (-0.50, 0.50)):
            mid = (xa + xb) * 0.5
            self.add(beam("brace", (xa + 0.10, yy, z0 + 0.18), (mid, yy, z0 + 0.78),
                          0.12, 0.09, M["wood_dark"]), 0.005)
            self.add(beam("brace", (xb - 0.10, yy, z0 + 0.18), (mid, yy, z0 + 0.78),
                          0.12, 0.09, M["wood_dark"]), 0.005)
        # 侧墙 + 后墙
        for sx in (-1, 1):
            for yy2 in (-3.70, -2.30, -0.90, 0.50, 1.90, 3.30):
                self.add(box("stud", (sx * (W2 + 0.02), yy2, (z0 + z1) * 0.5),
                             (0.12, 0.20, z1 - z0), M["wood_dark"]), 0.007)
            for zz in (z0 + 0.06, z1 - 0.06):
                self.add(box("rail_side", (sx * (W2 + 0.02), (YB + YF) * 0.5, zz),
                             (0.13, YF - YB - 0.10, 0.17), M["wood_dark"]), 0.007)
        for x in (-5.75, -4.20, -2.65, -1.10, 0.45, 2.00, 3.55, 5.10):
            self.add(box("post_b", (x, YB - 0.055, (z0 + z1) * 0.5), (0.20, 0.13, z1 - z0),
                         M["wood_dark"]), 0.009)
        for zz in (z0 + 0.06, z1 - 0.06):
            self.add(box("rail_b", (0, YB - 0.055, zz), (W2 * 2 - 0.10, 0.14, 0.17),
                         M["wood_dark"]), 0.009)

    # ── 8. 窗 ───────────────────────────────────────────────────────────────
    def windows(self):
        M = self.M
        # 一层前墙（角楼左侧两扇）
        for x in (-5.20, -3.30):
            self.arch_win("win_f", (x, YF + 0.03, 2.30), 0.56, 1.34, "Y")
        # 一层侧墙（每侧两扇，落在扶壁之间）
        for sx in (-1, 1):
            for yy in (-1.85, 0.65):
                self.arch_win("win_s", (sx * (W2 + 0.01), yy, 2.30), 0.58, 1.38, "X", out=sx)
        # 一层后墙
        for x in (-2.10, 0.0, 3.20):
            self.arch_win("win_b", (x, YB - 0.03, 2.30), 0.56, 1.34, "Y", out=-1)
        # 二层前墙（木构层之间的小方窗）
        for x in (-4.60, -2.40, 2.40):
            self.add(box("win2", (x, YF + 0.06, 6.30), (0.62, 0.10, 1.12), M["glow"]))
            self.add(box("win2_frame", (x, YF + 0.12, 6.30), (0.84, 0.16, 1.34), M["wood_dark"]), 0.010)
            self.add(box("win2_bar", (x, YF + 0.20, 6.30), (0.055, 0.05, 1.24), M["wood_dark"]), 0.003)
            self.add(box("win2_bar2", (x, YF + 0.20, 6.30), (0.66, 0.05, 0.055), M["wood_dark"]), 0.003)
            self.add(box("win2_sill", (x, YF + 0.14, 5.60), (0.96, 0.22, 0.12), M["stone_light"]), 0.008)
        # 二层侧墙
        for sx in (-1, 1):
            for yy in (-2.30, 1.00):
                self.add(box("win2s", (sx * (W2 + 0.05), yy, 6.30), (0.10, 0.62, 1.12), M["glow"]))
                self.add(box("win2s_frame", (sx * (W2 + 0.09), yy, 6.30), (0.12, 0.80, 1.30),
                             M["wood_dark"]), 0.008)

    def arch_win(self, name, center, w, h, face, out=1):
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

    # ── 9. 阵营色标准模块 ───────────────────────────────────────────────────
    def kite(self, name, center, face, w, h, out=1):
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

    def wallbanner(self, name, center, face, w=2.00, h=2.40):
        M = self.M
        cx, cy, cz = center
        hw, hh = w * 0.5, h * 0.5
        prof = [(-hw, hh), (hw, hh), (hw, -hh * 0.72), (hw * 0.30, -hh),
                (-hw * 0.30, -hh), (-hw, -hh * 0.72)]
        if face == "Y":
            self.add(extrude(name + "_cloth", prof, "Y", 0.07, (cx, cz), M["team"], offset=cy), 0.012)
            self.add(box(name + "_rod_t", (cx, cy, cz + hh + 0.04), (w + 0.34, 0.11, 0.12),
                         M["wood_dark"]), 0.008)
            self.add(box(name + "_rod_b", (cx, cy, cz - hh - 0.02), (w + 0.12, 0.09, 0.10),
                         M["wood_dark"]), 0.006)
            for sgn in (-1, 1):
                self.add(box(name + "_fringe", (cx + sgn * hw * 0.62, cy, cz - hh - 0.15),
                             (w * 0.13, 0.06, 0.22), M["team_trim"]), 0.004)
            self.emblem(name, "Y", cx, cy + 0.075, cz + h * 0.04, w * 0.74, h * 0.60)
        else:
            self.add(extrude(name + "_cloth", prof, "X", 0.07, (cy, cz), M["team"], offset=cx), 0.012)
            self.add(box(name + "_rod_t", (cx, cy, cz + hh + 0.04), (0.11, w + 0.34, 0.12),
                         M["wood_dark"]), 0.008)
            self.add(box(name + "_rod_b", (cx, cy, cz - hh - 0.02), (0.09, w + 0.12, 0.10),
                         M["wood_dark"]), 0.006)
            for sgn in (-1, 1):
                self.add(box(name + "_fringe", (cx, cy + sgn * hw * 0.62, cz - hh - 0.15),
                             (0.06, w * 0.13, 0.22), M["team_trim"]), 0.004)
            self.emblem(name, "X", cx + 0.075, cy, cz + h * 0.04, w * 0.74, h * 0.60)

    def banner(self, name, x, z_top, w=BANNER_W, h=BANNER_H):
        M = self.M
        y = YF + 0.34
        self.add(box(name + "_rod", (x, y, z_top), (w + 0.18, 0.06, 0.06), M["wood_dark"]), 0.004)
        prof = [(-w * 0.5, 0.0), (w * 0.5, 0.0), (w * 0.5, -h * 0.80),
                (w * 0.10, -h), (-w * 0.10, -h), (-w * 0.5, -h * 0.80)]
        self.add(extrude(name + "_cloth", prof, "Y", 0.05, (x, z_top - 0.05), M["team"],
                         offset=y), 0.008)
        self.add(box(name + "_trim", (x, y, z_top - 0.07), (w + 0.06, 0.062, 0.07),
                     M["team_trim"]), 0.004)

    def heraldry(self):
        M = self.M
        # ① 女儿墙下的整圈阵营色饰带（前 / 左 / 右三面，高 0.44）—— 正视最大的一块
        z_band = H2 - 0.10
        self.add(box("band_f", ((-W2 + T_X0) * 0.5, YF + 0.055, z_band),
                     (W2 + T_X0, 0.13, 0.44), M["team"]), 0.010)
        self.add(box("band_f_t", ((-W2 + T_X0) * 0.5, YF + 0.075, z_band + 0.26),
                     (W2 + T_X0, 0.15, 0.07), M["team_trim"]), 0.004)
        for sx in (-1, 1):
            self.add(box("band_s", (sx * (W2 + 0.055), (YF + YB) * 0.5, z_band),
                         (0.13, YF - YB - 0.2, 0.44), M["team"]), 0.010)
        self.add(box("band_b", (0, YB - 0.055, z_band), (W2 * 2 - 0.2, 0.13, 0.44),
                     M["team"]), 0.010)
        # ② 前墙两条大横幅：左侧 2.30 宽（门与左角之间），右侧 1.50 宽（门与角楼之间）
        self.wallbanner("wbanner_fL", (-4.60, YF + 0.14, 6.15), "Y", 2.30, 2.70)
        self.wallbanner("wbanner_fR", (2.45, YF + 0.14, 6.15), "Y", 1.50, 2.60)
        # ③ 侧墙大横幅
        for sx, tag in ((-1, "L"), (1, "R")):
            self.wallbanner("wbanner_s" + tag, (sx * (W2 + 0.18), -0.20, 6.15), "X", 2.10, 2.50)
        # ④ 后墙横幅
        self.wallbanner("wbanner_b", (0, YB - 0.14, 6.10), "Y", 2.00, 2.30)
        # ⑤ 盾：侧墙 + 角楼
        for sx, tag in ((-1, "L"), (1, "R")):
            self.kite("shield_s" + tag, (sx * (W2 + 0.07), 3.10, 2.55), "X", 1.10, 1.34, out=sx)
        self.kite("shield_tw", ((T_X0 + T_X1) * 0.5, T_Y1 + 0.12, 8.40), "Y", 1.10, 1.34)


    # ── 10. 屋顶平台 ────────────────────────────────────────────────────────
    def roofdeck(self):
        M = self.M
        # 平台铺装（深色石板 + 排水找坡，这里做成平的）
        self.add(box("deck", (0, (YF + YB) * 0.5, H2 - 0.06), (W2 * 2 - 0.9, YF - YB - 0.9, 0.12),
                     M["stone_dark"]), 0.010)
        for i in range(5):
            yy = YB + 1.0 + i * 1.90
            self.add(box("deck_joint", (0, yy, H2 + 0.005), (W2 * 2 - 1.2, 0.08, 0.02),
                         M["stone_mid"]), 0.0)
        # 中央旗杆（全楼最高点之一，11.9）
        self.add(box("pole_base", (0.0, -0.60, H2 + 0.20), (0.50, 0.50, 0.40), M["iron"]), 0.008)
        self.add(revolve("pole", [(0.062, 0.0), (0.052, 3.30)], 8, (0.0, -0.60, H2 + 0.34),
                         M["wood_dark"]), 0.0, 1)
        self.add(revolve("pole_ball", [(0.085, 0.0), (0.065, 0.05), (0.02, 0.13)], 8,
                         (0.0, -0.60, H2 + 3.56), M["gold"]), 0.0, 1)
        fw, fh = 1.50, 0.96
        zt = H2 + 3.32
        prof = [(0.0, 0.0), (fw, -0.10), (fw * 0.82, -fh * 0.5), (fw, -fh * 0.94), (0.0, -fh)]
        self.add(extrude("pole_flag", prof, "Y", 0.04, (0.0, zt), M["team"], offset=-0.58), 0.004)
        # 屋顶楼梯间（替代外挂楼梯：一个 1.5 × 1.5 的小体量 + 单坡顶 + 门）
        sx0, sy0 = -4.60, -3.10
        self.add(box("ph_house", (sx0, sy0, H2 + 0.80), (1.60, 1.50, 1.60), M["stone_light"]), 0.016)
        self.add(box("ph_house_base", (sx0, sy0, H2 + 0.12), (1.76, 1.66, 0.24), M["stone_mid"]), 0.010)
        self.add(slab_plate("ph_roof", M["roof_edge"], sx0 - 1.00, sx0 + 1.00,
                            sy0 - 0.95, sy0 + 0.95, H2 + 1.72, H2 + 1.52, 0.14), 0.012)
        for k in (-1, 1):
            self.add(box("ph_ridge", (sx0, sy0 + k * 0.94, H2 + 1.58), (2.04, 0.08, 0.10),
                         M["roof_edge"]), 0.004)
        self.add(box("ph_door", (sx0, sy0 + 0.78, H2 + 0.52), (0.80, 0.10, 1.04), M["wood_warm"]), 0.008)
        self.add(box("ph_door_f", (sx0, sy0 + 0.84, H2 + 0.52), (0.96, 0.10, 1.20),
                     M["wood_dark"]), 0.006)
        # 屋顶瞭望位：矮墙 + 盾
        self.add(box("deck_wall", (0, YB + 0.90, H2 + 0.42), (4.40, 0.30, 0.84), M["stone_light"]), 0.014)
        self.kite("shield_deck", (0, YB + 1.12, H2 + 0.52), "Y", 0.86, 1.04)
        # 屋顶防御物资：木箱 ×2、桶 ×1、沙袋堆
        for (x, y) in ((-4.40, -2.90), (-4.40, -1.90)):
            self.crate("deck_crate", (x, y), 0.90, 0.68, H2)
        self.barrel("deck_barrel", (4.40, -3.20), 0.44, 0.92, H2)
        for k in range(5):
            self.add(cyl("deck_bag", (3.30 + (k % 3) * 0.34, -2.10 + (k // 3) * 0.36,
                                      H2 + 0.20 + (k // 3) * 0.34),
                         0.18, 0.62, 6, M["roof_wood"], axis="X"), 0.010)

    # ── 11. 训练场 ──────────────────────────────────────────────────────────
    def yard(self):
        M = self.M
        # 三面木栅栏（左 / 右 / 前），前面中间留 3.6 m 开口
        self.fence_run("fence_l", (-YARD_X, YARD_Y0 + 0.20), (0, 1), YARD_Y1 - YARD_Y0 - 0.30)
        self.fence_run("fence_r", (YARD_X, YARD_Y0 + 0.20), (0, 1), YARD_Y1 - YARD_Y0 - 0.30)
        for sgn in (-1, 1):
            self.fence_run("fence_f", (sgn * 1.90, YARD_Y1), (1, 0), YARD_X - 1.90)
        # 开口两侧的门柱
        for sgn in (-1, 1):
            self.add(box("fence_gate_post", (sgn * 1.95, YARD_Y1, 1.10), (0.30, 0.30, 2.20),
                         M["wood_warm"]), 0.012)
            self.add(cone("fence_gate_cap", (sgn * 1.95, YARD_Y1, 2.20), (sgn * 1.95, YARD_Y1, 2.44),
                          0.22, 4, M["wood_warm"]), 0.0, 1)
        # 三具草靶假人
        self.dummy("dummy_a", (-5.60, 11.00))
        self.dummy("dummy_b", (-1.80, 13.60))
        self.dummy("dummy_c", (2.60, 10.60))
        # 两座武器架
        self.weapon_rack("wrack_a", (-7.20, 8.60))
        self.weapon_rack("wrack_b", (7.00, 15.60))
        # 盔甲架
        self.armor_stand("armor", (5.60, 13.20))
        # 两个圆靶
        self.target("target_a", (-7.60, 16.40))
        self.target("target_b", (7.80, 9.40))
        # 桶 / 箱 / 沙袋
        self.barrel("barrel_a", (-8.60, 9.20), 0.42, 0.86, 0.0)
        self.barrel("barrel_b", (8.40, 17.60), 0.38, 0.78, 0.0)
        self.barrel("barrel_c", (0.80, 17.20), 0.40, 0.82, 0.0)
        self.crate("crate_a", (-3.40, 8.00), 0.88, 0.66, 0.0)
        self.crate("crate_b", (5.00, 17.40), 0.72, 0.58, 0.0)
        for k in range(3):
            self.add(box("sandbag", (4.30 + (k % 2) * 0.42, 8.40 + (k // 2) * 0.42, 0.32),
                         (0.54, 0.40, 0.34), M["roof_wood"]), 0.014)
        # 长矛堆 ×2（三支一组斜靠在一起）
        for (px, py) in ((-8.55, 13.40), (4.90, 16.10)):
            for k in range(3):
                ox = (k - 1) * 0.16
                self.add(beam("pike_pile", (px + ox, py, 0.10), (px + ox * 2.4, py + 0.30, 2.70),
                              0.05, 0.05, M["wood_warm"]), 0.003)
                self.add(cone("pike_pile_tip", (px + ox * 2.4, py + 0.30, 2.70),
                              (px + ox * 2.6, py + 0.32, 3.00), 0.065, 4, M["iron"]), 0.0, 1)
        # 盾堆（三面盾靠在木架上）
        self.add(box("shield_stack_rack", (-8.40, 16.90, 0.34), (1.20, 0.16, 0.68), M["wood_dark"]), 0.008)
        for k in range(3):
            self.add(box("shield_stack", (-8.40 + (k - 1) * 0.36, 16.82, 0.56), (0.32, 0.10, 0.72),
                         M["team"]), 0.008)
            self.add(box("shield_stack_b", (-8.40 + (k - 1) * 0.36, 16.78, 0.90), (0.34, 0.12, 0.10),
                         M["team_trim"]), 0.004)
        # 草垛 ×2
        for (px, py) in ((-8.30, 11.20), (8.30, 13.60)):
            self.add(cyl("hay", (px, py, 0.62), 0.76, 1.24, 12, M["roof_wood"]), 0.018)
            for zz in (0.34, 0.92):
                self.add(tube_band("hay_rope", (px, py), 0.78, 0.83, zz, zz + 0.07, 12,
                                   M["wood_dark"]), 0.004)
        # 练剑木桩 ×2
        for (px, py) in ((-4.60, 16.60), (3.60, 15.00)):
            self.add(cyl("pell", (px, py, 0.90), 0.22, 1.80, 8, M["wood_warm"], axis="Z"), 0.008)
            self.add(cyl("pell_top", (px, py, 1.66), 0.30, 0.28, 8, M["roof_wood"]), 0.010)
            self.add(box("pell_arm", (px, py, 1.34), (1.10, 0.14, 0.14), M["wood_dark"]), 0.006)

    def fence_run(self, name, p0, d, length):
        """板式木栅栏：竖板 + 两道横梁 + 立柱。"""
        M = self.M
        n = int(length / 0.44)
        for i in range(n + 1):
            t = i / max(n, 1)
            x = p0[0] + d[0] * t * length
            y = p0[1] + d[1] * t * length
            sx = 0.28 * abs(d[1]) + 0.07 * abs(d[0])
            sy = 0.28 * abs(d[0]) + 0.07 * abs(d[1])
            self.add(box(name + "_plank", (x, y, FENCE_H * 0.5), (sx, sy, FENCE_H),
                         M["wood_warm"]), 0.006)
        for zz in (0.46, 1.16):
            cx = p0[0] + d[0] * length * 0.5
            cy = p0[1] + d[1] * length * 0.5
            sx = abs(d[0]) * length + abs(d[1]) * 0.10
            sy = abs(d[1]) * length + abs(d[0]) * 0.10
            self.add(box(name + "_rail", (cx, cy, zz), (sx + 0.10, sy + 0.10, 0.14),
                         M["wood_dark"]), 0.006)
        # 立柱（每 2.6 m 一根）
        m = max(2, int(length / 2.60))
        for i in range(m + 1):
            t = i / m
            x = p0[0] + d[0] * t * length
            y = p0[1] + d[1] * t * length
            self.add(box(name + "_post", (x, y, FENCE_H * 0.55), (0.24, 0.24, FENCE_H * 1.10),
                         M["wood_dark"]), 0.008)
            self.add(cone(name + "_cap", (x, y, FENCE_H * 1.10), (x, y, FENCE_H * 1.10 + 0.20),
                          0.18, 4, M["wood_dark"]), 0.0, 1)

    def dummy(self, name, p):
        """草靶假人：十字木架 + 方草靶 + 草绳 + 头。"""
        M = self.M
        x, y = p
        # 十字底座
        self.add(box(name + "_foot_x", (x, y, 0.16), (1.30, 0.18, 0.32), M["wood_dark"]), 0.008)
        self.add(box(name + "_foot_y", (x, y, 0.16), (0.18, 1.30, 0.32), M["wood_dark"]), 0.008)
        # 立柱 + 横臂 + 斜撑
        self.add(box(name + "_post", (x, y, 1.10), (0.17, 0.17, 2.00), M["wood_warm"]), 0.008)
        self.add(box(name + "_arm", (x, y, 1.66), (1.52, 0.16, 0.16), M["wood_warm"]), 0.008)
        for sgn in (-1, 1):
            self.add(beam(name + "_strut", (x + sgn * 0.72, y, 1.70), (x + sgn * 0.10, y, 1.24),
                          0.10, 0.09, M["wood_dark"]), 0.004)
        # 草靶身 + 草绳
        self.add(box(name + "_body", (x, y + 0.02, 0.92), (0.58, 0.44, 0.92), M["roof_wood"]), 0.014)
        for zz in (0.62, 1.22):
            self.add(box(name + "_cord", (x, y + 0.02, zz), (0.62, 0.48, 0.08), M["wood_dark"]), 0.004)
        # 头
        self.add(box(name + "_head", (x, y, 1.58), (0.38, 0.36, 0.44), M["roof_wood"]), 0.012)
        self.add(box(name + "_cord_n", (x, y, 1.40), (0.34, 0.32, 0.08), M["wood_dark"]), 0.003)

    def weapon_rack(self, name, p):
        """武器架：两立柱 + 三道横杆 + 四支长矛 + 两把剑。"""
        M = self.M
        x, y = p
        for sgn in (-1, 1):
            self.add(box(name + "_post", (x + sgn * 0.78, y, 0.82), (0.16, 0.16, 1.64),
                         M["wood_dark"]), 0.008)
            self.add(box(name + "_foot", (x + sgn * 0.78, y, 0.10), (0.30, 0.44, 0.20),
                         M["stone_mid"]), 0.008)
        for zz in (0.52, 1.02, 1.48):
            self.add(box(name + "_rail", (x, y, zz), (1.70, 0.13, 0.11), M["wood_dark"]), 0.006)
        # 长矛（斜靠）
        for k in range(4):
            ox = -0.54 + k * 0.36
            self.add(beam(name + "_pike", (x + ox, y - 0.12, 0.30), (x + ox, y - 0.42, 2.60),
                          0.05, 0.05, M["wood_warm"]), 0.003)
            self.add(cone(name + "_tip", (x + ox, y - 0.42, 2.60), (x + ox, y - 0.45, 2.90),
                          0.07, 4, M["iron"]), 0.0, 1)
        # 剑（两把，斜靠在横杆前）
        for sgn in (-1, 1):
            self.add(beam(name + "_sword", (x + sgn * 0.62, y - 0.22, 0.26),
                          (x + sgn * 0.30, y - 0.30, 1.58), 0.09, 0.035, M["iron"]), 0.003)
            self.add(box(name + "_guard", (x + sgn * 0.31, y - 0.30, 1.60), (0.34, 0.06, 0.07),
                         M["gold"]), 0.003)
            self.add(box(name + "_grip", (x + sgn * 0.30, y - 0.30, 1.70), (0.08, 0.08, 0.18),
                         M["wood_dark"]), 0.003)

    def armor_stand(self, name, p):
        """盔甲架：木架 + 胸甲 + 肩甲 + 头盔 + 腿甲 + 阵营色披风。"""
        M = self.M
        x, y = p
        self.add(box(name + "_base", (x, y, 0.12), (0.96, 0.70, 0.24), M["wood_dark"]), 0.010)
        self.add(box(name + "_post", (x, y - 0.06, 1.10), (0.14, 0.14, 2.00), M["wood_dark"]), 0.006)
        self.add(box(name + "_shoulder", (x, y, 1.94), (0.92, 0.14, 0.14), M["wood_dark"]), 0.006)
        # 胸甲（梯形）+ 铁边
        self.add(taper_box(name + "_chest", (x, y + 0.10, 1.58), (x, y + 0.10, 1.10),
                           0.62, 0.44, 0.30, 0.24, M["iron"]), 0.012)
        self.add(box(name + "_chest_band", (x, y + 0.10, 1.14), (0.46, 0.28, 0.08),
                     M["stone_dark"]), 0.004)
        # 肩甲
        for sgn in (-1, 1):
            self.add(box(name + "_pauldron", (x + sgn * 0.38, y + 0.06, 1.86), (0.30, 0.34, 0.22),
                         M["iron"], rot=(0, sgn * 0.22, 0)), 0.010)
        # 头盔（八边回转 + 面罩缝）
        self.add(revolve(name + "_helm", [(0.0, 0.0), (0.20, 0.05), (0.23, 0.20), (0.17, 0.36),
                                          (0.0, 0.42)], 8, (x, y + 0.04, 2.06), M["iron"]), 0.010, 1)
        self.add(box(name + "_visor", (x, y + 0.24, 2.18), (0.34, 0.05, 0.10), M["coal"]), 0.003)
        # 腿甲
        for sgn in (-1, 1):
            self.add(box(name + "_leg", (x + sgn * 0.16, y + 0.06, 0.66), (0.20, 0.22, 0.86),
                         M["iron"]), 0.008)
        # 披风（阵营色）
        self.add(box(name + "_cape", (x, y - 0.24, 1.42), (0.72, 0.06, 1.10), M["team"]), 0.008)
        self.add(box(name + "_cape_t", (x, y - 0.26, 0.86), (0.72, 0.08, 0.10),
                     M["team_trim"]), 0.004)

    def target(self, name, p):
        """圆靶：立柱 + 两根斜撑 + 圆盘 + 同心环 + 靶心。"""
        M = self.M
        x, y = p
        self.add(box(name + "_post", (x, y, 0.86), (0.18, 0.18, 1.72), M["wood_dark"]), 0.008)
        for sgn in (-1, 1):
            self.add(beam(name + "_strut", (x + sgn * 0.62, y + 0.30, 0.10),
                          (x, y, 1.38), 0.10, 0.09, M["wood_dark"]), 0.004)
        # 圆盘（正面朝 +Y）
        self.add(cyl(name + "_face", (x, y + 0.06, 1.46), 0.72, 0.14, 16, M["roof_wood"]), 0.012)
        self.add(tube_band(name + "_ring", (x, y + 0.06), 0.52, 0.60, 1.53, 1.59, 16,
                           M["team"]), 0.006)
        self.add(tube_band(name + "_ring2", (x, y + 0.06), 0.26, 0.34, 1.53, 1.59, 16,
                           M["team_trim"]), 0.006)
        self.add(cyl(name + "_bull", (x, y + 0.14, 1.46), 0.12, 0.06, 12, M["gold"]), 0.004)
        self.add(box(name + "_band", (x, y + 0.06, 1.46), (1.56, 0.10, 0.06), M["iron"]), 0.003)

    def barrel(self, name, p, r, h, z0=0.0):
        M = self.M
        x, y = p
        self.add(lathe(name, [(0.0, z0, x, y), (r * 0.84, z0, x, y), (r, z0 + h * 0.34, x, y),
                              (r, z0 + h * 0.66, x, y), (r * 0.84, z0 + h, x, y),
                              (0.0, z0 + h, x, y)],
                       12, M["wood_warm"]), 0.014, 1)
        for zz in (h * 0.28, h * 0.72):
            self.add(tube_band(name + "_hoop", (x, y), r * 0.97, r * 1.03, z0 + zz, z0 + zz + 0.07,
                               12, M["iron"]), 0.004)
        # 桶板缝（四条）
        for k in range(4):
            a = math.pi * 0.5 * k
            self.add(box(name + "_stave", (x + math.cos(a) * r * 0.99,
                                           y + math.sin(a) * r * 0.99, z0 + h * 0.5),
                         (0.05, 0.05, h * 0.92), M["wood_dark"]), 0.002)

    def crate(self, name, p, w, h, z0=0.0):
        M = self.M
        x, y = p
        self.add(box(name, (x, y, z0 + h * 0.5), (w, w * 0.86, h), M["wood_warm"]), 0.012)
        for k in (-1, 1):
            self.add(box(name + "_band", (x, y, z0 + h * 0.5 + k * h * 0.28), (w + 0.04, w * 0.90, 0.07),
                         M["iron"]), 0.004)
        for k in (-1, 1):
            self.add(box(name + "_brace", (x, y, z0 + h * 0.5), (w + 0.04, w * 0.90, 0.06),
                         M["wood_dark"], rot=(0, k * 0.7, 0)), 0.003)

    # ── 12. 组装 ────────────────────────────────────────────────────────────
    def build(self):
        for step in (self.base, self.mass, self.parapet, self.tower,
                     self.gate, self.timber, self.windows, self.heraldry,
                     self.roofdeck, self.yard):
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
