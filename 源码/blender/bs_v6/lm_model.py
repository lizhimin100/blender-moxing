"""
lm_model.py —— 伐木场（Lumber Mill）：open_shed 敞棚 + 立式排锯 + 原木堆 + 轨道

六座里最后一座、也是唯一一座 **open_shed**（敞棚）：

  ① **正面完全开敞**：前檐只有一列柱子，没有前墙。这是它和另五座最本质的区别 ——
     谷仓（农场）虽然有大门，正面仍是"一堵墙 + 一个洞"；这里正面是**一条通长的檐口
     阴影**，柱子把阴影切成 4 个开间，棚内的锯架、木料、工具墙从缝里透出来。
  ② **立式排锯门架**（frame saw）是全座最高点（7.62），也是唯一的"细杆撑大盖"重件：
     两根方柱 + 顶横梁 + 中间 5.6 m 的竖锯条 + 顶部小雨棚。它站在前檐之外，
     从任何角度都完整可见 —— 俯视时是整个剪影里唯一的尖角。
  ③ **原木堆**是俯视的主角：8~10 个 φ0.42 的端面朝 +Y，每个端面三道年轮。
     一根原木在 RTS 尺度上只是 4 px 的圆点，但一垛排开的圆点组是"伐木场"最直接的读法。
  ④ **轨道**从前场一路穿进棚内、正对锯架：两条 11 m 的木轨 + 14 根枕木 + 一辆台车。
     它把"外场 → 锯台 → 成品"的动作线画在俯视图上，也是唯一一组斜向的平行线。
  ⑤ **飞轮**（φ1.70，12 边 + 6 根辐条）立在小屋前，是唯一的"圆"和唯一的铁件大件。

坐标：X 右、Y 前（+Y = 正面）、Z 上；原点在占地中心，z = 0 地面。
交付前整体沿 X 镜像一次（与另五座一致），所以建模期的 +X 在成品里是 −X。
"""
import math
from math import tau as TAU

import bpy
from mathutils import Vector

import bslib as L
import br_model as BR
from bslib import (beam, box, cyl, extrude, frustum, mesh_obj, revolve, ring_y,
                   taper_box, tube_band)
from br_model import mirror_x, vcyl

# ── 场地 ────────────────────────────────────────────────────────────────────
YARD_X0, YARD_X1 = -8.15, 8.15
YARD_Y0, YARD_Y1 = -4.35, 6.35
G_Z = 0.18

# ── 主棚（11.60 × 6.40，单坡 14.9°）────────────────────────────────────────
SX0, SX1 = -5.80, 5.80
SY0 = -2.62                      # 后墙外表面（进深 5.92）
SYC = 3.30                       # 前柱列
SF, SB = 4.30, 6.12              # 前檐 / 后檐（17.2°）
ST = 0.32                        # 屋面板厚
EX = 0.40                        # 左右出檐
EYF, EYB = 1.58, 0.42            # 前 / 后出檐

# ── 小屋（右端封闭隔间）────────────────────────────────────────────────────
HX0, HX1 = 2.92, 5.80
HY0, HY1 = -2.62, 3.10
H_TOP = None                     # 由 roof_z(HY1) 算

# ── 排锯门架 ────────────────────────────────────────────────────────────────
RX, RY = 1.30, 5.62
RH = 7.34                        # 柱顶
RHW = 1.64                       # 半跨

# ── 轨道 ────────────────────────────────────────────────────────────────────
RAIL_X = 1.30
GAUGE = 0.56                     # 半轨距
RAIL_Y0, RAIL_Y1 = -2.16, 6.10

# ── 原木堆 ──────────────────────────────────────────────────────────────────
LOG_X = (-8.10, -7.44, -6.78, -6.12)
LOG_Y0, LOG_Y1 = 0.24, 3.02
LOG_R = 0.25


def roof_z(y):
    """单坡屋面在给定 y 处的**上表面**标高（出檐段按同斜率外推）。"""
    return SF + (SYC - y) / (SYC - SY0) * (SB - SF)


def roof_ang():
    return math.atan2(SB - SF, SYC - SY0)


# ── 通用构件（与农场同一套写法）────────────────────────────────────────────
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


def arch_profile(w, h, segs=7):
    hw = w * 0.5
    pts = [(-hw, 0.0), (hw, 0.0), (hw, h)]
    for s in range(segs - 1, 0, -1):
        a = math.pi * s / segs
        pts.append((hw * math.cos(a), h + hw * math.sin(a)))
    pts.append((-hw, h))
    return pts


class Model(BR.Model):

    # ── 1. 场地 · 石基 · 轨道 ───────────────────────────────────────────────
    def base(self):
        M = self.M
        cx = (YARD_X0 + YARD_X1) * 0.5
        cy = (YARD_Y0 + YARD_Y1) * 0.5
        # 夯土场地
        self.add(box("yard_soil", (cx, cy, G_Z * 0.5),
                     (YARD_X1 - YARD_X0, YARD_Y1 - YARD_Y0, G_Z), M["earth"]), 0.024)
        # 棚下的夯实地面（比院子高 8 cm，读作"常年踩实的作业面"）
        self.add(box("yard_floor", (0.0, 0.34, G_Z + 0.04),
                     (11.80, 5.92, 0.08), M["earth"]), 0.010)
        # 后墙石基：一条通长，两端各伸出 0.30
        self.add(box("wall_plinth", (0.0, SY0 - 0.08, 0.31),
                     (SX1 - SX0 + 0.60, 0.56, 0.62), M["stone_mid"]), 0.014)
        self.add(box("wall_plinth_cap", (0.0, SY0 - 0.08, 0.65),
                     (SX1 - SX0 + 0.78, 0.70, 0.10), M["stone_light"]), 0.010)
        # 左端角柱的石墩 + 小屋基座
        self.add(box("hut_plinth", ((HX0 + HX1) * 0.5, (HY0 + HY1) * 0.5, 0.32),
                     (HX1 - HX0 + 0.30, HY1 - HY0 + 0.30, 0.64), M["stone_mid"]), 0.014)
        # 场地牙子：右 + 前三面（后侧是墙）
        self.add(box("yard_curb", (YARD_X1 - 0.09, cy - 0.18, G_Z + 0.03),
                     (0.18, YARD_Y1 - YARD_Y0 - 0.44, 0.14), M["paving"]), 0.006)
        for sx in (-1, 1):
            self.add(box("yard_curb_f", (sx * (YARD_X1 - 0.09), YARD_Y1 - 0.11, G_Z + 0.03),
                         (0.18, 0.18, 0.14), M["paving"]), 0.006)
        self.add(box("yard_curb_s", (cx, YARD_Y1 - 0.11, G_Z + 0.03),
                     (YARD_X1 - YARD_X0 - 0.40, 0.18, 0.14), M["paving"]), 0.006)
        # 轨道：两条木轨 + 枕木
        for sx in (-1, 1):
            self.add(box("rail_l", (RAIL_X + sx * GAUGE, (RAIL_Y0 + RAIL_Y1) * 0.5,
                                   G_Z + 0.075),
                         (0.12, RAIL_Y1 - RAIL_Y0, 0.11), M["iron"]), 0.005)
        n = 14
        for i in range(n):
            yy = RAIL_Y0 + 0.28 + i * (RAIL_Y1 - RAIL_Y0 - 0.56) / (n - 1)
            self.add(box("rail_tie", (RAIL_X, yy, G_Z + 0.025),
                         (1.36, 0.18, 0.07), M["wood_dark"]), 0.004)

    # ── 2. 棚架：柱 · 檐梁 · 后墙 ───────────────────────────────────────────
    def frame(self):
        M = self.M
        posts = (-5.50, -2.90, -0.30, 2.30)
        # 五根前柱（0.28²）：柱脚石墩 + 柱身 + 队色箍 + 柱头斜撑
        for px in posts:
            self.add(box("post_foot", (px, SYC, G_Z + 0.13), (0.58, 0.58, 0.26),
                         M["stone_dark"]), 0.008)
            self.add(box("post_body", (px, SYC, (G_Z + 0.26 + 4.16) * 0.5),
                         (0.32, 0.32, 4.16 - G_Z - 0.26), M["wood_dark"]), 0.012)
            # 下半段一道箍 + **上段整段染队色**。檐梁上那道饰条在深出檐下
            # 从任何俯视角都被檐口挡死（hero 视角实测只读到 2.8%），
            # 所以主力染色放在柱子的可见段上。
            self.add(box("post_band", (px, SYC, 1.86), (0.375, 0.375, 0.46),
                         M["team"]), 0.004)
            self.add(box("post_band_t", (px, SYC, 2.14), (0.395, 0.395, 0.075),
                         M["team_trim"]), 0.002)
            self.add(box("post_cap_t", (px, SYC, 3.55), (0.345, 0.345, 1.18),
                         M["team"]), 0.004)
            self.add(box("post_cap_trim", (px, SYC, 3.04), (0.365, 0.365, 0.075),
                         M["team_trim"]), 0.002)
            # 柱头斜撑：从柱身 4.10 斜到檐梁底，两侧各一
            for sx in (-1, 1):
                self.add(beam("post_brace", (px + sx * 0.17, SYC, 3.12),
                              (px + sx * 0.80, SYC, 4.04), 0.14, 0.12,
                              M["wood_dark"]), 0.004)
        # 前檐梁（通长）：檐口阴影就是它压出来的
        self.add(box("beam_eave", (0.0, SYC, 4.18), (SX1 - SX0 + 0.94, 0.26, 0.28),
                     M["wood_dark"]), 0.012)
        # 檐梁下的一道队色饰条 —— 全座最长的染色线（11.9 m）
        self.add(box("beam_eave_band", (0.0, SYC + 0.15, 4.18),
                     (SX1 - SX0 + 0.90, 0.05, 0.22), M["team"]), 0.004)
        # 柱列中段的通长横梁（把五根"电线杆"串成一组开间）
        self.add(box("beam_mid", ((SX0 - 0.15 + HX0) * 0.5, SYC, 2.46),
                     (HX0 - SX0 + 0.15, 0.20, 0.17),
                     M["wood_dark"]), 0.008)
        # 后墙：石基之上是竖板墙，三道横梁 + 六根立柱
        self.add(box("wall_back", (0.0, SY0 + 0.11, (2.10 + SB) * 0.5),
                     (SX1 - SX0, 0.22, SB - 2.10), M["wood_mid"]), 0.024)
        # 下段石砌：敞棚内部唯一的浅色面 —— 檐下没有直射光，全靠这一面墙把
        # 亮度"弹"回来，否则从正面看进去就是一个黑洞。
        self.add(box("wall_stone", (0.0, SY0 + 0.13, (0.70 + 2.10) * 0.5),
                     (SX1 - SX0, 0.26, 1.40), M["stone_mid"]), 0.016)
        for (zz, ww) in ((1.42, 0.09), (2.04, 0.07)):
            self.add(box("wall_course", (0.0, SY0 + 0.28, zz),
                         (SX1 - SX0, 0.04, ww), M["stone_light"]), 0.002)
        for zz in (2.92, 4.28, SB - 0.34):
            self.add(box("wall_rail", (0.0, SY0 + 0.03, zz),
                         (SX1 - SX0, 0.12, 0.17), M["wood_dark"]), 0.006)
        for i in range(7):
            xx = SX0 + 0.14 + i * (SX1 - SX0 - 0.28) / 6.0
            self.add(box("wall_stud", (xx, SY0 + 0.02, (2.10 + SB) * 0.5),
                         (0.17, 0.10, SB - 2.14), M["wood_dark"]), 0.006)
        # 后墙上的工具：锯 / 斧 / 楔（挂在 3.30 的横梁上）
        self.saw_blade("wall_saw", SY0 + 0.24, -3.55, 3.44, 1.30, 0.34)
        for k, xx in enumerate((-2.30, -2.02, -1.74)):
            self.add(box("tool_wedge", (xx, SY0 + 0.22, 3.40), (0.13, 0.12, 0.22),
                         M["wood_warm"], rot=(0, 0, 0.2 * k - 0.2)), 0.003)
        # 斧：柄 + 头
        self.add(beam("tool_axe", (-1.20, SY0 + 0.24, 2.52), (-1.20, SY0 + 0.24, 3.38),
                      0.055, 0.055, M["wood_warm"]), 0.003)
        self.add(box("tool_axe_head", (-1.20, SY0 + 0.26, 3.34), (0.10, 0.24, 0.22),
                     M["iron"]), 0.004)
        # 左端：一根角柱 + 半高挡墙（原木堆从这里进出）
        self.add(box("post_corner", (SX0 - 0.14, SYC, (G_Z + 4.16) * 0.5),
                     (0.34, 0.34, 4.16 - G_Z), M["wood_dark"]), 0.012)
        self.add(box("post_corner_band", (SX0 - 0.13, SYC, 1.86), (0.38, 0.38, 0.38),
                     M["team"]), 0.004)
        for sx, xx in ((-1, SX0 + 0.12), (1, SX1 - 0.12)):
            self.add(box("wall_end", (xx, (SY0 + SYC) * 0.5, 0.70 + 0.62),
                         (0.22, SYC - SY0 - 0.30, 1.24), M["wood_mid"]), 0.014)
        # 棚内的"作业台"（一张粗木台，放工具与图纸）
        self.add(box("bench_top", (-3.30, -1.16, 1.03), (2.06, 0.72, 0.14),
                     M["wood_warm"]), 0.008)
        for sx in (-1, 1):
            for sy in (-1, 1):
                self.add(box("bench_leg", (-3.30 + sx * 0.86, -1.16 + sy * 0.26, 0.49),
                             (0.14, 0.14, 0.94), M["wood_dark"]), 0.004)

    def saw_blade(self, name, wy, cx, cz, ln, hh):
        """挂墙的长锯：一条背板 + 一排锯齿（阶梯小方块）+ 上下木柄。"""
        M = self.M
        self.add(box(name, (cx, wy, cz), (ln, 0.05, hh), M["iron"]), 0.004)
        for i in range(11):
            xx = cx - ln * 0.5 + 0.06 + i * (ln - 0.12) / 10.0
            self.add(box(name + "_tooth", (xx, wy + 0.01, cz - hh * 0.5 - 0.035),
                         (0.055, 0.04, 0.07), M["iron"]), 0.0)
        for sx in (-1, 1):
            self.add(box(name + "_grip", (cx + sx * (ln * 0.5 + 0.11), wy, cz),
                         (0.24, 0.09, 0.13), M["wood_dark"]), 0.004)

    # ── 3. 单坡屋面 ─────────────────────────────────────────────────────────
    def roof(self):
        M = self.M
        ey0, ey1 = SYC + EYF, SY0 - EYB          # 4.62 / -3.46
        ex0, ex1 = SX0 - EX, SX1 + EX            # −6.18 / 6.18
        # 屋面用**深板岩**（roof）而不是农场的暖棕木瓦：
        #   ① 木墙、地面、原木全是暖棕，屋面再用暖棕会整座糊成一块；
        #   ② 六座里"暖棕木瓦"只留给农场，伐木场用深板岩，"这是哪一座"一眼就分开；
        #   ③ 深屋面才压得住下面那条深色的檐口阴影，敞棚的"开口"才读得出来。
        eys = -1.18
        self.add(slab("roof_main", [(ex0, ey0, roof_z(ey0)), (ex1, ey0, roof_z(ey0)),
                                    (ex1, eys, roof_z(eys)), (ex0, eys, roof_z(eys))],
                      ST, M["roof"]), 0.010)
        # 后段同色、整体抬高 60 mm：读作"棚是后来往后接过一跨"。
        # 换成浅一档（roof_pale）会变成"两块屋顶拼起来"，整座建筑像没做完。
        self.add(slab("roof_main_b", [(ex0, eys, roof_z(eys) + 0.060),
                                      (ex1, eys, roof_z(eys) + 0.060),
                                      (ex1, ey1, roof_z(ey1) + 0.060),
                                      (ex0, ey1, roof_z(ey1) + 0.060)],
                      ST, M["roof"]), 0.010)
        # 搭接处的一排椽头（从外面能数出来"这是两跨"）
        for i in range(9):
            xx = ex0 + 0.60 + i * (ex1 - ex0 - 1.20) / 8.0
            self.add(box("roof_seam_end", (xx, eys + 0.20, roof_z(eys) - 0.02),
                         (0.12, 0.34, 0.13), M["wood_dark"]), 0.003)
        self.add(beam("roof_seam", (ex0, eys, roof_z(eys) + 0.026),
                      (ex1, eys, roof_z(eys) + 0.026), 0.17, 0.11, M["wood_dark"]), 0.004)
        # 沿坡的**亮脊**（roof_pale）：深色屋面上铺亮条才有起伏，铺暗缝糊成一片
        n = 7
        for i in range(n):
            xx = ex0 + 0.72 + i * (ex1 - ex0 - 1.44) / (n - 1)
            self.add(beam("roof_rib", (xx, ey0 + 0.10, roof_z(ey0 + 0.10) + 0.030),
                          (xx, ey1 - 0.10, roof_z(ey1 - 0.10) + 0.030),
                          0.085, 0.048, M["roof_pale"]), 0.0)
        # 三片"换过的旧瓦"（横向条带）：打散整片纯色
        ang = roof_ang()
        for (px, py, pw, pl, mat) in ((-2.70, 0.55, 3.20, 0.40, M["stone_dark"]),
                                      (1.85, -1.30, 2.70, 0.40, M["stone_dark"]),
                                      (-0.40, 2.28, 2.10, 0.38, M["stone_dark"])):
            self.add(box("roof_patch", (px, py, roof_z(py) + 0.014),
                         (pw, pl, 0.05), mat, rot=(ang, 0, 0)), 0.004)
        # 屋面下的露明椽条（8 根沿坡）：从檐下抬头能看到一排斜梁 —— 这是木构棚的底
        # 只做出檐这一段：跨过柱列的话，椽条会从柱身里穿出去（柱顶到檐檩，
        # 椽子搭在檩上，两者在 Y 向本来就该错开）
        for i in range(8):
            xx = ex0 + 0.78 + i * (ex1 - ex0 - 1.56) / 7.0
            self.add(beam("roof_rafter",
                          (xx, ey0 - 0.02, roof_z(ey0) - ST - 0.09),
                          (xx, SYC - 0.12, roof_z(SYC - 0.12) - ST - 0.09),
                          0.12, 0.15, M["wood_dark"]), 0.0)
        # 前后檐：封檐板 + 滴水条
        for yy, zz in ((ey0, roof_z(ey0)), (ey1, roof_z(ey1))):
            self.add(box("roof_fascia", (0.0, yy, zz - 0.14),
                         (ex1 - ex0 + 0.06, 0.10, 0.26), M["roof_edge"]), 0.005)
            self.add(box("roof_drip", (0.0, yy + (0.035 if yy > 0 else -0.035), zz + 0.02),
                         (ex1 - ex0 + 0.08, 0.06, 0.08), M["roof_edge"]), 0.003)
        # 前檐封檐板下沿的一道队色（12.3 m 通长，全座唯一条"从外面一定看得见"的横线）
        self.add(box("roof_team", (0.0, ey0 + 0.055, roof_z(ey0) - 0.225),
                     (ex1 - ex0 - 0.12, 0.035, 0.17), M["team"]), 0.002)
        # 两侧山墙封檐（沿坡）
        for xx in (ex0, ex1):
            self.add(beam("roof_barge", (xx, ey0, roof_z(ey0) - 0.03),
                          (xx, ey1, roof_z(ey1) - 0.03),
                          0.10, 0.28, M["roof_edge"]), 0.004)
        # 前檐下的露明椽头：13 个，正是"敞棚"最直白的证据
        for i in range(13):
            xx = ex0 + 0.44 + i * (ex1 - ex0 - 0.88) / 12.0
            self.add(box("rafter_end", (xx, ey0 + 0.15, roof_z(ey0) - 0.34),
                         (0.11, 0.30, 0.13), M["wood_dark"]), 0.003)
        # 屋面上的两个小天窗（浅色采光瓦 + 木框）：俯视时给大屋面两个"呼吸点"
        for (sx, sy) in ((-3.55, 1.62), (3.15, 0.22)):
            zz = roof_z(sy)
            self.add(box("roof_light", (sx, sy, zz + 0.03), (0.92, 0.66, 0.10),
                         M["roof_pale"], rot=(ang, 0, 0)), 0.004)
            for sy2 in (-1, 1):
                self.add(box("roof_light_f", (sx, sy + sy2 * 0.37, zz + 0.02),
                             (1.02, 0.10, 0.12), M["wood_dark"], rot=(ang, 0, 0)), 0.003)

    # ── 4. 右端小屋（封闭隔间：工具房 / 账房）────────────────────────────────
    def hut(self):
        M = self.M
        cx = (HX0 + HX1) * 0.5
        top = roof_z(HY1)                     # 前墙顶（5.62）
        # 前墙（开一扇门 + 一扇窗）
        dw, dh = 0.92, 2.02
        self.add(box("hut_front", (cx + 0.72, HY1 - 0.11, (0.62 + top) * 0.5),
                     (HX1 - HX0 - 1.30, 0.22, top - 0.62), M["wood_mid"]), 0.020)
        self.add(box("hut_front_l", ((HX0 + cx + 0.06) * 0.5, HY1 - 0.11,
                                     (0.62 + top - 0.012) * 0.5),
                     (cx + 0.06 - HX0, 0.22, top - 0.62 - 0.012), M["wood_mid"]), 0.020)
        self.add(box("hut_front_T", ((HX0 + HX1) * 0.5, HY1 - 0.11,
                                     (0.64 + dh + 0.28 + top) * 0.5),
                     (HX1 - HX0, 0.22, top - 0.64 - dh - 0.28), M["wood_mid"]), 0.020)
        # 门套（石砌）+ 木门扇 + 队色嵌板
        dx = HX0 + 0.46 + dw * 0.5
        for sx in (-1, 1):
            self.add(box("hut_jamb", (dx + sx * (dw * 0.5 + 0.10), HY1, 0.62 + dh * 0.5),
                         (0.20, 0.30, dh + 0.16), M["stone_light"]), 0.006)
        self.add(box("hut_head", (dx, HY1, 0.62 + dh + 0.10), (dw + 0.44, 0.30, 0.20),
                     M["stone_light"]), 0.006)
        self.add(box("hut_door", (dx, HY1 - 0.12, 0.62 + dh * 0.5), (dw, 0.10, dh),
                     M["wood_warm"]), 0.008)
        for k in range(3):
            self.add(box("hut_door_plank", (dx - dw * 0.30 + k * dw * 0.30, HY1 - 0.175,
                                            0.62 + dh * 0.5),
                         (0.075, 0.028, dh - 0.12), M["wood_mid"]), 0.002)
        self.add(box("hut_door_panel", (dx, HY1 - 0.19, 0.62 + 1.16),
                     (0.52, 0.04, 0.34), M["team"]), 0.003)
        for zz in (0.98, 2.26):
            self.add(box("hut_door_band", (dx, HY1 - 0.195, zz), (dw - 0.04, 0.04, 0.09),
                         M["iron"]), 0.002)
        self.add(box("hut_ring", (dx + 0.30, HY1 - 0.205, 1.50), (0.07, 0.04, 0.17),
                     M["iron"]), 0.002)
        # 窗（门右侧）
        wx = HX1 - 0.80
        self.add(box("win_hut_glass", (wx, HY1 - 0.09, 2.50), (0.84, 0.10, 0.72),
                     M["glass"]), 0.0)
        for sy in (-1, 1):
            self.add(box("win_hut_f", (wx, HY1, 2.50 + sy * 0.44), (1.04, 0.16, 0.12),
                         M["wood_dark"]), 0.004)
        for sx in (-1, 1):
            self.add(box("win_hut_f", (wx + sx * 0.50, HY1, 2.50), (0.12, 0.16, 0.92),
                         M["wood_dark"]), 0.004)
        self.add(box("win_hut_mull", (wx, HY1 + 0.01, 2.50), (0.06, 0.05, 0.70),
                     M["wood_dark"]), 0.002)
        self.add(box("win_hut_sill", (wx, HY1 + 0.02, 2.08), (1.10, 0.24, 0.11),
                     M["stone_light"]), 0.006)
        # 侧墙：**梯形**，顶边跟着单坡屋面走（直角矩形会在后半段留一个 1.7 m 的三角洞）
        prof = [(HY0, 0.62), (HY1, 0.62), (HY1, top - 0.06), (HY0, roof_z(HY0) - 0.06)]
        for (xx, sgn) in ((HX0 + 0.11, -1), (HX1 - 0.11, 1)):
            self.add(extrude("hut_side", prof, "X", 0.22, (0.0, 0.0),
                             M["wood_mid"], offset=xx), 0.020)
            # 竖向板条 + 一道腰梁，把这块 5.7 × 3.3 的大板墙打散
            for i in range(4):
                yy = HY0 + 0.62 + i * (HY1 - HY0 - 1.24) / 3.0
                self.add(box("hut_stud", (xx + sgn * 0.15, yy, 1.62),
                             (0.09, 0.14, 1.86), M["wood_dark"]), 0.004)
            self.add(box("hut_rail", (xx + sgn * 0.15, (HY0 + HY1) * 0.5, 2.62),
                         (0.10, HY1 - HY0 - 0.30, 0.15), M["wood_dark"]), 0.004)
        for (sx, xx) in ((-1, HX0 + 0.11), (1, HX1 - 0.11)):
            self.add(box("hut_stone", (xx, (HY0 + HY1) * 0.5, 1.30),
                         (0.28, HY1 - HY0 - 0.10, 1.22), M["stone_mid"]), 0.012)
        self.add(box("win_hut_s_glass", (HX1 + 0.01, 1.05, 3.42), (0.10, 0.62, 0.56),
                     M["glass"]), 0.0)
        for sy in (-1, 1):
            self.add(box("win_hut_s_f", (HX1 + 0.03, 1.05 + sy * 0.36, 3.42),
                         (0.09, 0.12, 0.70), M["wood_dark"]), 0.003)
        for sz in (-1, 1):
            self.add(box("win_hut_s_f", (HX1 + 0.03, 1.05, 3.42 + sz * 0.33),
                         (0.09, 0.74, 0.11), M["wood_dark"]), 0.003)
        self.add(box("win_hut_s_sill", (HX1 + 0.05, 1.05, 3.04), (0.13, 0.82, 0.09),
                     M["stone_light"]), 0.004)
        # 石基压顶（绕小屋一圈）
        self.add(box("hut_dado", (cx, (HY0 + HY1) * 0.5, 0.68),
                     (HX1 - HX0 + 0.16, HY1 - HY0 + 0.16, 0.12), M["stone_light"]), 0.008)
        # 小屋墙上的两道队色腰线（低 + 中）
        for zz, hh in ((1.24, 0.26), (3.62, 0.36)):
            self.add(box("hut_band", (cx, HY1 + 0.005, zz),
                         (HX1 - HX0 - 0.10, 0.035, hh), M["team"]), 0.003)
        # 侧墙（朝 +X，hero 视角里最大的一块连续面）的通长腰线
        self.add(box("hut_band_s", (HX1 + 0.035, (HY0 + HY1) * 0.5 + 0.26, 3.12),
                     (0.035, HY1 - HY0 - 0.52, 0.42), M["team"]), 0.003)
        # 屋顶下的一道橡木托（小屋前檐挑出）
        self.add(box("hut_eave", (cx, HY1 + 0.16, top + 0.06), (HX1 - HX0 + 0.36, 0.44, 0.16),
                     M["wood_dark"]), 0.006)

    # ── 5. 立式排锯门架 ─────────────────────────────────────────────────────
    def saw(self):
        M = self.M
        for sx in (-1, 1):
            px = RX + sx * RHW
            self.add(box("saw_foot", (px, RY, G_Z + 0.14), (0.58, 0.58, 0.28),
                         M["stone_dark"]), 0.008)
            self.add(box("saw_post", (px, RY, (G_Z + 0.28 + RH) * 0.5),
                         (0.36, 0.36, RH - G_Z - 0.28), M["wood_dark"]), 0.014)
            # 柱箍（队色）：下段 + 上段各一道
            for zz in (1.62, 5.42):
                self.add(box("saw_band", (px, RY, zz), (0.40, 0.40, 0.26),
                             M["team"]), 0.004)
            # 柱内侧的两道斜撑
            for (za, zb) in ((3.10, 5.10), (5.10, 6.64)):
                self.add(beam("saw_brace", (px - sx * 0.16, RY, za),
                              (px - sx * 0.86, RY, zb), 0.12, 0.10,
                              M["wood_dark"]), 0.004)
        # 顶部两根横梁（前后各一）+ 之间的垫块
        for sy in (-1, 1):
            self.add(box("saw_head", (RX, RY + sy * 0.26, RH - 0.16),
                         (RHW * 2 + 0.44, 0.22, 0.28), M["wood_dark"]), 0.010)
        # 横梁端头的队色色块（从任何角度都能看见的两个点）
        for sx in (-1, 1):
            self.add(box("saw_head_cap", (RX + sx * (RHW + 0.26), RY, RH - 0.16),
                         (0.30, 0.70, 0.42), M["team"]), 0.005)
        # 顶上的小雨棚（双坡，两块斜板 + 脊压条）
        for sy in (-1, 1):
            self.add(box("saw_roof", (RX, RY + sy * 0.32, RH + 0.19),
                         (RHW * 2 + 0.26, 0.70, 0.09), M["roof"],
                         rot=(-sy * 0.34, 0, 0)), 0.005)
        self.add(box("saw_ridge", (RX, RY, RH + 0.34), (RHW * 2 + 0.32, 0.14, 0.09),
                     M["roof_edge"]), 0.004)
        # 中间：竖锯条（iron，5.60 高）+ 夹持它的木框
        self.add(box("saw_blade", (RX, RY, 3.42), (0.11, 0.18, 5.58), M["iron"]), 0.002)
        for i in range(16):
            zz = 0.74 + i * 5.30 / 15.0
            self.add(box("saw_tooth", (RX + 0.045, RY, zz), (0.055, 0.09, 0.09),
                         M["iron"]), 0.0)
        for sx in (-1, 1):
            self.add(box("saw_grip", (RX + sx * 0.27, RY, 3.42),
                         (0.11, 0.13, 5.62), M["wood_warm"]), 0.004)
        for zz in (1.10, 3.42, 5.74):
            self.add(box("saw_tie", (RX, RY, zz), (0.56, 0.15, 0.12),
                         M["wood_dark"]), 0.004)
        # 锯架下的方木（正在被剖的那一根）：树皮外壳 + 两块新切板
        self.add(box("saw_beam", (RX, RY, 0.50), (2.10, 0.46, 0.34), M["wood_mid"]), 0.010)
        self.add(box("saw_beam_cut", (RX, RY + 0.24, 0.50), (2.10, 0.03, 0.30),
                     M["sand"]), 0.004)
        for sy in (-1, 1):
            self.add(box("saw_plank", (RX + sy * 0.34, RY + 0.62, 0.26),
                         (0.72, 0.58, 0.055), M["sand"],
                         rot=(0, 0, 0.12 * sy)), 0.003)
        # 不加"从柱顶斜回檐梁"的撑：柱在出檐之外（y 5.18），檐梁在 y 3.30，
        # 任何一条连线都要从 3.76 的檐口上方越过去 —— 做出来是一根悬空的斜杆。
        # 棚与门架的关系交给轨道（穿过两者）和正对的位置去读。
        # 吊挂的铁钩与队色布条（从横梁挂下来）
        self.add(box("saw_hook", (RX + 0.62, RY - 0.26, RH - 0.80), (0.06, 0.06, 1.34),
                     M["iron"]), 0.002)
        self.add(box("saw_hook_t", (RX + 0.62, RY - 0.26, RH - 1.50), (0.20, 0.07, 0.16),
                     M["iron"]), 0.002)
        for k, (hh, zz) in enumerate(((0.62, RH - 2.06), (0.44, RH - 2.48))):
            self.add(box("saw_rag", (RX + 0.70, RY - 0.26, zz), (0.18, 0.05, hh),
                         M["team"] if k == 0 else M["team_trim"]), 0.002)

    # ── 6. 原木堆（4-3-2-1 金字塔，端面三道年轮）────────────────────────────
    def timber(self):
        M = self.M
        # 底层 4 根 → 二层 3 根 → 三层 2 根 → 顶 1 根；层间错半根
        rows = ((0, 4), (1, 4), (2, 3), (3, 2), (4, 1))
        for (li, cnt) in rows:
            zz = G_Z + LOG_R + li * (LOG_R * 1.74)
            xs = [LOG_X[0] + (3 - cnt) * (LOG_X[1] - LOG_X[0]) * 0.5 + i * (LOG_X[1] - LOG_X[0])
                  for i in range(cnt)]
            for xx in xs:
                self.timber_one(xx, zz)
        # 堆前的挡料杆：两根短桩 + 一道队色横杆（"这片料是有人管的"）
        for sx in (-1, 1):
            self.add(box("timber_guard", (-7.22 + sx * 0.98, LOG_Y1 + 0.26, G_Z + 0.56),
                         (0.17, 0.17, 1.12), M["wood_dark"]), 0.006)
        self.add(box("timber_bar", (-7.22, LOG_Y1 + 0.26, G_Z + 1.02),
                     (2.14, 0.13, 0.22), M["team"]), 0.004)
        # 堆前的两块垫木（原木不能直接滚在土上）
        for sx in (-1, 1):
            self.add(box("timber_sleeper", (-7.11, (LOG_Y0 + LOG_Y1) * 0.5 + sx * 1.32,
                                            G_Z + 0.06),
                         (2.56, 0.18, 0.12), M["wood_dark"]), 0.004)

    def timber_one(self, x, z):
        """一根原木：八边形树皮 + 端面浅色盘 + 三道年轮。"""
        M = self.M
        y0, y1 = LOG_Y0, LOG_Y1
        self.add(cyl("timber_bark", (x, (y0 + y1) * 0.5 - 0.02, z),
                     LOG_R, y1 - y0 - 0.08, 8, M["wood_mid"],
                     axis="Y", phase=math.pi / 8), 0.010)
        self.add(cyl("timber_face", (x, y1 - 0.04, z), LOG_R * 0.94, 0.09, 8,
                     M["sand"], axis="Y", phase=math.pi / 8), 0.004)
        for (rr, ww) in ((0.165, 0.020), (0.115, 0.018), (0.062, 0.016)):
            self.add(ring_y("timber_ring", (x, y1 - 0.002, z), rr - ww, rr,
                            0.014, 8, M["wood_dark"], phase=math.pi / 8), 0.002)
        self.add(cyl("timber_pith", (x, y1 + 0.004, z), 0.030, 0.016, 8,
                     M["wood_dark"], axis="Y", phase=math.pi / 8), 0.0)

    # ── 7. 台车 · 飞轮 · 手推车 ─────────────────────────────────────────────
    def carts(self):
        M = self.M
        # 台车（轨道上，载一根新切方木）
        gy = 4.22
        self.add(box("cart_bed", (RAIL_X, gy, G_Z + 0.34), (1.26, 1.34, 0.16),
                     M["wood_warm"]), 0.008)
        self.add(box("cart_sill", (RAIL_X, gy, G_Z + 0.22), (1.14, 1.26, 0.10),
                     M["wood_dark"]), 0.006)
        for sx in (-1, 1):
            for sy in (-1, 1):
                self.add(cyl("cart_wheel", (RAIL_X + sx * GAUGE, gy + sy * 0.46,
                                            G_Z + 0.15), 0.15, 0.12, 8,
                             M["iron"], axis="X", phase=math.pi / 8), 0.004)
        self.add(box("cart_load", (RAIL_X, gy, G_Z + 0.66), (1.76, 0.50, 0.40),
                     M["sand"]), 0.010)
        self.add(box("cart_load_bark", (RAIL_X, gy, G_Z + 0.66), (1.62, 0.54, 0.29),
                     M["wood_mid"]), 0.008)
        # 飞轮（立在小屋前）：12 边环 + 6 根辐条 + 轴
        wx, wy, wz, wr = 6.42, 3.92, 0.94, 0.88
        self.add(ring_y("wheel_rim", (wx, wy, wz), wr - 0.15, wr, 0.16, 12,
                        M["iron"], phase=math.pi / 12), 0.006)
        self.add(ring_y("wheel_rim_in", (wx, wy, wz), wr - 0.26, wr - 0.17, 0.13, 12,
                        M["wood_dark"], phase=math.pi / 12), 0.004)
        self.add(ring_y("wheel_hub", (wx, wy, wz), 0.10, 0.22, 0.26, 8,
                        M["iron"]), 0.004)
        for k in range(6):
            a = math.pi * 2 * k / 6 + math.pi / 12
            self.add(beam("wheel_spoke",
                          (wx, wy, wz),
                          (wx + math.cos(a) * (wr - 0.18), wy, wz + math.sin(a) * (wr - 0.18)),
                          0.09, 0.11, M["wood_dark"]), 0.004)
        # 飞轮的支架（两根斜柱 + 底梁）
        for sx in (-1, 1):
            self.add(beam("wheel_leg", (wx + sx * 0.62, wy - 0.24, G_Z),
                          (wx + sx * 0.30, wy - 0.12, wz - 0.20),
                          0.11, 0.11, M["wood_dark"]), 0.004)
        self.add(box("wheel_base", (wx, wy - 0.20, G_Z + 0.06), (1.60, 0.42, 0.12),
                     M["wood_mid"]), 0.004)
        # 手推车（左前，装短木）
        hx, hy = -6.58, 5.36
        self.add(box("barrow_box", (hx, hy, G_Z + 0.52), (1.06, 0.66, 0.30),
                     M["wood_warm"]), 0.008)
        for sy in (-1, 1):
            self.add(box("barrow_side", (hx, hy + sy * 0.34, G_Z + 0.66),
                         (1.10, 0.08, 0.34), M["wood_dark"]), 0.005)
        for sx in (-1, 1):
            self.add(cyl("barrow_wheel", (hx + 0.44, hy + sx * 0.36, G_Z + 0.12),
                         0.13, 0.11, 8, M["wood_dark"], axis="Y", phase=math.pi / 8), 0.004)
        for sy in (-1, 1):
            self.add(beam("barrow_shaft", (hx - 0.52, hy + sy * 0.22, G_Z + 0.56),
                          (hx - 1.48, hy + sy * 0.16, G_Z + 0.30),
                          0.07, 0.07, M["wood_dark"]), 0.003)
        self.add(box("barrow_load", (hx, hy, G_Z + 0.76), (0.86, 0.50, 0.26),
                     M["sand"]), 0.008)

    # ── 8. 场院杂物：锯末 / 木楔 / 草 / 石 ──────────────────────────────────
    def props(self):
        M = self.M
        # 锯末堆（浅色沙斑，7 边不规则，压在夯土上）
        for (cx, cy, rx, ry, sd) in ((RX + 2.10, 4.34, 1.04, 0.66, 1.0),
                                     (-0.95, 1.92, 1.55, 0.86, 2.3),
                                     (4.05, 4.65, 0.85, 0.58, 3.1),
                                     (-5.86, -1.34, 0.80, 0.56, 1.7)):
            self.sawdust(cx, cy, rx, ry, sd)
        # 散落的木片 / 木楔
        for (px, py, pw, pl, rz, mat) in ((-1.62, 3.62, 0.86, 0.14, 0.42, M["wood_warm"]),
                                          (-1.20, 0.62, 0.62, 0.13, -0.65, M["sand"]),
                                          (-3.05, 4.24, 0.74, 0.12, 0.18, M["wood_mid"]),
                                          (-2.24, 5.24, 0.55, 0.11, 1.02, M["wood_warm"])):
            self.add(box("plank_loose", (px, py, G_Z + 0.035), (pw, pl, 0.07), mat,
                         rot=(0, 0, rz)), 0.003)
        for (px, py, rz) in ((-2.32, -0.62, 0.5), (0.34, 0.56, -0.8), (2.62, -1.62, 1.3),
                             (-4.62, 3.92, 0.2)):
            self.add(box("tool_wedge", (px, py, G_Z + 0.10), (0.20, 0.14, 0.20),
                         M["wood_warm"], rot=(0, 0, rz)), 0.003)
        # 木桶（屋角）
        self.barrel("barrel_a", (6.86, 4.94), 0.28, 0.66)
        self.barrel("barrel_b", (-3.20, -1.92), 0.24, 0.58)
        # 草簇 / 碎石
        for (px, py) in ((-7.62, -1.30), (7.24, 0.62), (-3.92, 5.62), (6.42, -3.42),
                         (-0.62, -3.62), (3.92, 5.42)):
            self.tuft(px, py)
        for (px, py, s, rz) in ((-3.42, 5.92, 0.26, 0.4), (7.42, 2.14, 0.22, -0.7),
                                (4.32, 5.92, 0.19, 1.0), (-2.10, -3.72, 0.17, 0.2)):
            self.add(box("rubble", (px, py, G_Z + s * 0.26), (s, s * 0.78, s * 0.56),
                         M["stone_mid"], rot=(0.22 * s, 0.18 * s, rz)), 0.004)
        # 立在墙边的木板捆（斜靠）
        for k in range(3):
            self.add(box("plank_stack", (HX0 - 0.32 + k * 0.05, 1.62 - k * 0.03, 1.06),
                         (0.055, 1.44, 1.92), M["wood_warm"],
                         rot=(0.10, 0.02, 0)), 0.004)

    def sawdust(self, cx, cy, rx, ry, seed):
        M = self.M
        prof = []
        for i in range(7):
            a = TAU * i / 7.0 + 0.40 * seed
            k = 0.72 + 0.28 * math.sin(seed * 3.7 + i * 2.1)
            prof.append((cx + math.cos(a) * rx * k, cy + math.sin(a) * ry * k))
        self.add(extrude("sawdust", prof, "Z", 0.045, (0.0, 0.0),
                         M["sand"], offset=G_Z + 0.015), 0.0)

    def tuft(self, x, y, h=0.22):
        M = self.M
        for k in range(3):
            a = math.radians(18 + k * 60)
            hh = h * (0.84 + 0.11 * k)
            self.add(box("tuft", (x + 0.014 * math.cos(a + 1.1),
                                  y + 0.014 * math.sin(a + 1.1), G_Z + hh * 0.48),
                         (0.115, 0.018, hh), M["moss"],
                         rot=(0.20 * math.cos(a), 0.20 * math.sin(a), a)), 0.0)

    def barrel(self, name, p, r, h):
        M = self.M
        x, y = p
        self.add(revolve(name, [(r * 0.86, 0.0), (r, 0.12), (r, h - 0.12), (r * 0.86, h)], 8,
                         (x, y, G_Z - 0.02), M["wood_warm"]), 0.008)
        for zz in (h * 0.22, h * 0.78):
            self.add(tube_band(name + "_hoop", (x, y), r - 0.01, r + 0.035,
                               G_Z + zz, G_Z + zz + 0.10, 8, M["iron"]), 0.003)

    # ── 9. 旗帜 ─────────────────────────────────────────────────────────────
    def banner(self, name, px, py, pz, w, h, out=1, hang="side"):
        """燕尾垂旗：横杆 + 3 段布（递减）+ 末端 V 缺口 + 队色 + 金边。

        hang="side" 时横杆沿 X，布从杆垂下；用于柱子侧挂。
        """
        M = self.M
        self.add(box(name + "_arm", (px, py, pz), (w + 0.34, 0.075, 0.085),
                     M["wood_dark"]), 0.004)
        self.add(box(name + "_brk", (px - w * 0.42, py - 0.17, pz - 0.004), (0.09, 0.38, 0.072),
                     M["wood_dark"]), 0.003)
        for sx in (-1, 1):
            self.add(box(name + "_cap", (px + sx * (w * 0.5 + 0.15), py, pz),
                         (0.10, 0.10, 0.10), M["wood_dark"]), 0.002)
        # 旗布：上段整幅 + 中段收窄 + 末段**分成左右两条**（中间空出 V 缺口）
        zz = pz - 0.04
        for (kw, hh) in ((1.00, 0.58), (0.88, 0.42)):
            self.add(box(name + "_cloth", (px, py + out * 0.02, zz - hh * 0.5),
                         (w * kw, 0.038, hh), M["team"]), 0.003)
            zz -= hh
        for sx in (-1, 1):   # 燕尾两支
            self.add(box(name + "_tail", (px + sx * w * 0.25, py + out * 0.02,
                                          zz - 0.17),
                         (w * 0.38, 0.038, 0.34), M["team"]), 0.003)
        self.add(box(name + "_trim", (px - w * 0.30, py + out * 0.045, pz - 0.15),
                     (w * 0.30, 0.024, 0.055), M["team_trim"]), 0.002)
        # 徽记（缩到旗宽的 0.42，放在上 1/3）
        self.crest(name + "_crest", "Y", px, py + out * 0.055, pz - h * 0.62, w * 0.40)

    def heraldry(self):
        M = self.M
        # 两面垂旗挂在**锯架的两根柱子**外侧（6.30 高）：这里是全座最高点，
        # 旗布在屋面之上，不会穿过檐下的椽条和斜撑；俯视时也是唯一一对飘出剪影的色块。
        for (sx, tag) in ((-1, "l"), (1, "r")):
            px = RX + sx * RHW
            self.banner("flag_" + tag, px + sx * 0.52, RY + 0.36, 6.36, 0.64, 1.42, out=1)
        # 大横幅挂在小屋的**侧墙**（x = HX1，朝 +X）：那是 hero 视角里最大的一块
        # 干净墙面。原方案挂在棚内后墙上，3/4 视角完全看不见（实测染色只有 2.8%）。
        bx, by, bz = HX1 + 0.095, -1.10, 3.58
        self.add(box("banner_arm", (bx, by, bz + 0.70), (0.10, 2.52, 0.11),
                     M["wood_dark"]), 0.004)
        self.add(box("banner_cloth", (bx, by, bz - 0.04), (0.05, 2.44, 1.48),
                     M["team"]), 0.004)
        self.add(box("banner_trim", (bx + 0.01, by, bz - 0.80), (0.03, 2.44, 0.10),
                     M["team_trim"]), 0.002)
        self.crest("banner_crest", "X", bx + 0.04, by, bz - 0.56, 0.78)
        # 小屋门楣上的小盾
        self.crest("hut_crest", "Y", HX0 + 0.40 + 0.46, HY1 + 0.02, 3.06, 0.34)

    # ── 10. 组装 / 收尾 ────────────────────────────────────────────────────
    def build(self):
        for step in (self.base, self.frame, self.roof, self.hut, self.saw,
                     self.timber, self.carts, self.props, self.heraldry):
            step()
        return self

    def finalize(self, bevel=True):
        # 细分只磨小体量件：柱、梁、墙板、屋面、原木都是"大平面"，
        # CC 会把棱磨成一圈渐变的圆（塑料感）；原木的 8 边形一旦细分就变圆柱。
        skip_cc = ("timber_", "log_", "roof_", "rail_", "post_", "beam_", "wall_",
                   "hut_", "saw_blade", "saw_tooth", "saw_post", "saw_head",
                   "wheel_rim", "wheel_rim_in", "wheel_hub", "wheel_spoke",
                   "cart_", "barrow_", "flag_", "banner_", "crest_", "win_",
                   "sawdust", "plank_", "tool_", "tuft", "rubble", "yard_",
                   "bench_", "post_")
        for (ob, bev, sub, seg) in self.items:
            co = ob.data.vertices
            dims = [max(v.co[i] for v in co) - min(v.co[i] for v in co) for i in range(3)]
            vol = dims[0] * dims[1] * dims[2]
            chunky = min(dims) >= 0.12 and vol >= 0.14
            n = ob.name
            if self.smooth:
                cc = 1 if (chunky and not n.startswith(skip_cc)) else 0
                L.finalize(ob, bevel=min(max(bev, 0.008), 0.022), seg=1, sub=cc,
                           flat=False)
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
        out = L.join_by_material(objs, prefix="LM")
        mirror_x(out)
        if self.unwrap:
            L.smart_uv(out)
        return out


def build(smooth=True, unwrap=True, bevel=True):
    m = Model(smooth, unwrap).build()
    objs = m.finalize(bevel=bevel)
    return objs, L.stats(objs)
