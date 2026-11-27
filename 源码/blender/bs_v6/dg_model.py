"""
dg_model.py —— 地牢入口 v2「封门」（失落帝国 · 第十二座改版）

v1 为什么被推翻（用户原话）：**"整体风格太像联盟势力的建筑，同时门都没关上。"**
第二轮：**"太方正了，这是从地底冒出来的入口，不要看着像某片废墟残余的门部分。"**

所以 v2 的构成有两条腿：

  **① 往下走**：一整块石壳被凿开一道槽，槽的尽头两扇石门关着，门缝里还有一线火。
  **② 从土里冒出来**：门墙**两端埋在土坡里**（不是立在空地上），顶是**阶梯状断脊**
     （不是三级方台阶），整座向左倾 1.26°，石壳只留槽口一圈、外面全是土。

三秒读法（45° 俯视 20–40 m）：
  ① 左右两座土坡把画面夹住，中间一条**往下的槽**；
  ② 槽尽头一圈**亮门套**框住一块**近黑的门扇**（门关着，锁杠横着）；
  ③ 门墙顶上是一道**塌掉的断脊**：中间 4.84 是唯一的峰，往两边一级一级掉进土里。

明度秩序（七档）：
  土 earth_dark 0.062 → 石壳 ancient_mid 0.076 → 门墙 ancient 0.116
  → **压顶/门套 ancient_pale 0.238** → 门扇 door_stone 0.033
  → 槽内 ancient_dark 0.019 → **门缝 void 0.003**
  另加两处"局部美"：骨 bone 0.553（全图最亮，≤0.4 m²）+ 铜绿 bronze。

队色（只两道，不做旗）：前庭中带（连续跨三级台阶，俯视主力）+ 冠顶漆带 / 门楣横线。
**不是联盟蓝** —— `team` 基色换成氧化铁红，见 `dl_parts.LE_TEAM_STYLE`。

坐标：X 右、Y 前（+Y = 正面）、Z 上；原点在占地中心，z = 0 地面。
交付前整体沿 X 镜像一次（与九座一致）。
尺寸全部走 dg_layout.L；零件走 dl_parts。本文件只负责"装配 + 收尾"。
"""
import math

import bpy
from mathutils import Vector

import bslib as B
import dl_kit as K
import dl_parts as P
from bslib import box, extrude, mesh_obj, beam, revolve
from br_model import mirror_x
from dg_layout import L, RIDGE

TAU = math.tau

# ── 本阵营的色彩覆盖（桌面档 / 手游图集档共用这一份）──────────────────────
TEAM_STYLE = P.LE_TEAM_STYLE

# ── 台前的土坡：**分三片**（左右两坡 + 门口一条矮的），不能横穿台阶口 ────────
APRON_L = [(-4.95, 4.06), (-2.56, 4.06), (-2.56, 4.86), (-3.30, 4.98),
           (-4.45, 4.72)]
APRON_R = [(2.56, 4.06), (4.55, 4.06), (4.60, 4.64), (3.45, 4.96),
           (2.56, 4.86)]
APRON_M = [(-2.62, 4.08), (2.62, 4.08), (2.30, 4.78), (-2.35, 4.82)]


class Model:
    def __init__(self, smooth, unwrap=True, parts=None):
        self.smooth = smooth
        self.unwrap = unwrap
        self.items = []
        self.M = B.all_materials()
        self.parts = parts          # None = 全部；否则只建列出的组（调试用）

    def add(self, ob, bevel=0.010, sub=0, seg=1):
        if ob is not None:
            self.items.append((ob, bevel, sub, seg))
        return ob

    def put(self, obs, bevel=0.006):
        for ob in obs:
            self.add(ob, bevel)
        return obs

    # ── 0. 土坡：一座三层收分的土丘（脚 → 肩 → 顶）─────────────────────────
    def _hill(self, name, pts, z0, z1, seed=1, mat="earth_dark"):
        """土坡：**三层收分**（脚 → 肩 → 顶），轮廓每一层都重新抖一次。

        一层会读成"平顶台地"，两层读成"面包"。三层才像被雨水刷过的土坡。
        顶盖只留一小片（0.44），大片浅土会把整座拉亮、盖过石头。
        """
        M = self.M
        h = z1 - z0
        b = P.jitter_pts(pts, 0.14, seed)
        m1 = P.shrink(P.jitter_pts(pts, 0.11, seed + 1), 0.86)
        m2 = P.shrink(P.jitter_pts(pts, 0.08, seed + 2), 0.66)
        t = P.shrink(m2, 0.74)
        self.add(P.loft2(name + "_b", b, m1, z0, z0 + h * 0.42, M[mat]), 0.018)
        self.add(P.loft2(name + "_m", m1, m2, z0 + h * 0.41, z0 + h * 0.76, M[mat]), 0.018)
        self.add(P.loft2(name + "_t", m2, t, z0 + h * 0.75, z1, M[mat]), 0.018)
        self.add(P.loft2(name + "_cap", P.shrink(t, 0.92), P.shrink(t, 0.44),
                         z1 - 0.01, z1 + 0.06, M["earth"]), 0.012)
        return t

    # ── 1. 台前土坡 ─────────────────────────────────────────────────────────
    def pad(self):
        M = self.M
        self._hill("pd_apL", APRON_L, 0.0, 0.62, seed=7)
        self._hill("pd_apR", APRON_R, 0.0, 0.58, seed=9)
        self._hill("pd_apM", APRON_M, 0.0, 0.20, seed=11)

        for i, (x, y, s) in enumerate(((-3.95, 4.35, 1.0), (3.70, 4.60, 0.9),
                                       (-1.95, 4.86, 0.75))):
            self.put(K.grass("pd_tuft%d" % i, x, y, 0.26, 0.28 * s, 5, seed=31 + i,
                             mat=M["moss_dark"]), 0.002)
        self.put(K.stones("pd_stone", -3.10, 4.72, 0.28, 4, 0.42, 0.24,
                          (M["ancient"], M["ancient_dark"]), seed=11), 0.008)
        self.put(K.stones("pd_stone2", 3.05, 4.42, 0.26, 3, 0.34, 0.20,
                          (M["ancient"], M["ancient_dark"]), seed=13), 0.008)

    # ── 2. 石壳（五块拼 U 形，门墙那一格是真空出来的）──────────────────────
    def shelf(self):
        M = self.M
        x0, x1 = -L.shelf_x, L.shelf_x
        y0, y1 = L.shelf_y0, L.shelf_y1
        nx = L.pit_x
        gx0, gx1 = L.gate_x0 - 0.006, L.gate_x1 + 0.006
        gy1 = L.gate_y1

        cells = (
            ("arml", x0, -nx, L.gate_y0, y1),
            ("armr", nx, x1, L.gate_y0, y1),
            ("bkl", x0, gx0, y0, L.gate_y0),
            ("bkr", gx1, x1, y0, L.gate_y0),
            ("bkm", gx0, gx1, y0, gy1),
        )
        for tag, cx0, cx1, cy0, cy1 in cells:
            for band, (z0, z1, mat) in enumerate(((0.0, L.shelf_band, "ancient_dark"),
                                                  (L.shelf_band, L.shelf_z, "ancient_mid"))):
                self.add(box("sh_%s%d" % (tag, band),
                             ((cx0 + cx1) * 0.5, (cy0 + cy1) * 0.5, (z0 + z1) * 0.5),
                             (cx1 - cx0, cy1 - cy0, z1 - z0), M[mat]), 0.014)

        # 石壳正面：三个土楔把 1.38 m 的竖脸吃掉一半（不然正面还是一块方板）
        for i, (cx, w, d, h) in enumerate(((-1.55, 1.30, 0.62, 0.78),
                                           (1.42, 1.15, 0.55, 0.56),
                                           (0.05, 1.05, 0.48, 0.46))):
            pts = [(cx - w * 0.5, y1 - 0.02), (cx + w * 0.5, y1 - 0.02),
                   (cx + w * 0.34, y1 + d), (cx - w * 0.34, y1 + d)]
            self.add(P.loft2("sh_talus%d" % i, pts, P.shrink(pts, 0.72), 0.0, h,
                             M["earth_dark"]), 0.014)

        # 边缘残石：只留三块，压在土坡外侧，把石壳的直边打断
        for i, (x, y, sx, sy, zt) in enumerate(((-3.86, 3.55, 1.25, 1.10, 0.78),
                                                (3.80, -2.30, 1.10, 1.20, 0.86),
                                                (-3.70, -2.20, 0.95, 1.05, 0.72))):
            self.add(box("sh_spur%d" % i, (x, y, zt * 0.5), (sx, sy, zt),
                         M["ancient_mid"]), 0.012)

        # 石壳面上的三条裂纹（凸 8 mm 的暗条，读作湿缝）
        for i, (ax, ay, bx, by) in enumerate(((-2.85, 3.30, -2.05, 2.72),
                                              (-3.60, 0.55, -2.95, -0.10),
                                              (2.85, -0.55, 3.70, -1.05))):
            ln = math.hypot(bx - ax, by - ay)
            ang = math.atan2(by - ay, bx - ax)
            self.add(box("sh_crack%d" % i, ((ax + bx) * 0.5, (ay + by) * 0.5,
                                            L.shelf_z + 0.004),
                         (ln, 0.056, 0.016), M["ancient_dark"], rot=(0, 0, ang)), 0.002)

    # ── 3. 前庭（槽）────────────────────────────────────────────────────────
    def court(self):
        M = self.M
        self.add(box("pt_floor", (L.gate_cx, (L.pit_y0 + L.pit_y1) * 0.5, 0.05),
                     (L.pit_w, L.pit_y1 - L.pit_y0, 0.10), M["ancient_dark"]), 0.008)

        for i, (cx, cy, sx, sy) in enumerate(((-0.62, 0.34, 1.03, 0.62),
                                              (0.86, 0.32, 1.05, 0.58))):
            self.add(box("pt_pav%d" % i, (cx, cy, L.pave_z - 0.040),
                         (sx, sy, 0.080), M["ancient"]), 0.008)

        self.add(box("tr_drag", (L.gate_cx - 0.22, 0.40, L.pave_z + 0.008),
                     (0.70, 0.66, 0.014), M["earth_dark"]), 0.003)

        # 台阶（三级大踏步：踏高 0.40 / 踏宽 1.10 —— 26° 机位下踏面才露得出来）
        self.put(P.step_run("st_step", L.pit_x, L.pit_y1, L.shelf_z - 0.01,
                            L.step_n, L.step_rise, L.step_tread,
                            M["ancient"], M["ancient_pale"],
                            mat_riser=M["ancient_mid"], nose=(0.13, 0.110)), 0.010)

        # 梯级压边：沿台阶下行的阶梯状女儿墙
        for i in range(L.step_n):
            zt = L.shelf_z - 0.01 - i * L.step_rise
            y_face = L.pit_y1 - i * L.step_tread
            for s_ in (-1, 1):
                self.add(box("sh_cheek%d_%d" % (i, s_ > 0),
                             (s_ * (L.pit_x + L.coping_w * 0.5),
                              y_face - L.step_tread * 0.5, (zt + 0.17) * 0.5),
                             (L.coping_w, L.step_tread, zt + 0.17),
                             M["ancient_mid"]), 0.012)

        # 槽口压边（亮框）
        self.put(P.notch_band("sh_cop", L.pit_x, L.pit_y0, L.pit_floor_y1,
                              L.shelf_z, L.shelf_z + L.coping_h, L.coping_w,
                              M["ancient_pale"], side_inset=0.040), 0.012)

        # 坑壁脚的水线（坑的深度靠这条暗带读出来）
        for s in (-1, 1):
            self.add(box("pt_wet%d" % (s > 0), (s * (L.pit_x - 0.008), 0.42,
                                                L.pave_z + 0.20),
                         (0.016, 0.96, 0.40), M["ancient_dark"]), 0.002)

    # ── 4. 门墙（断脊）──────────────────────────────────────────────────────
    def wall_profile(self):
        """立面轮廓：**阶梯状断脊**。

        每一段是"一皮砌体塌掉后剩下的平台"，两端都低于土坡面 —— 竖边被土吃掉，
        所以从任何角度看都不是一面"墙"，而是土里露出来的一块石头。
        """
        ox0, ox1 = L.open_x0, L.open_x1
        top = []
        for (xa, xb, z) in reversed(RIDGE):
            top.append((xb, z))
            top.append((xa, z))
        return ([(L.gate_x1, 0.0)] + top
                + [(L.gate_x0, 0.0), (ox0, 0.0), (ox0, L.open_top),
                   (ox1, L.open_top), (ox1, 0.0)])

    def gate(self):
        M = self.M
        prof = self.wall_profile()
        yc = (L.gate_y0 + L.gate_y1) * 0.5
        self.add(extrude("gw_body", prof, "Y", L.gate_t, (0.0, 0.0), M["ancient"],
                         offset=yc), 0.012)

        # 门洞的暗背板：门缝 / 上沿那条缝看进去是纯黑
        self.add(box("gw_back", (L.gate_cx, L.gate_y1 + 0.14,
                                 L.open_top * 0.5 + 0.12),
                     (L.open_w, 0.10, L.open_top + 0.16), M["void"]), 0.004)

        # 门套：两柱各三段 + 过梁（凸 0.22 的亮框，压出暗边 = 门是嵌进去的）
        fw, pr = L.frame_w, L.frame_pr
        for s, x_face in ((-1, L.open_x0), (1, L.open_x1)):
            # 右柱少一段：门套是断的，不是画框
            segs = (((0.0, 0.98), (1.01, 2.20), (2.23, L.open_top)) if s < 0
                    else ((0.0, 0.96), (0.99, 2.12)))
            for i, (z0, z1) in enumerate(segs):
                xc = x_face + s * fw * 0.5
                self.add(box("gw_pil%d_%d" % (s, i),
                             (xc, L.gate_y0 - pr * 0.5 + 0.004 * i,
                              (z0 + z1) * 0.5),
                             (fw, pr * 2.0, z1 - z0), M["ancient_pale"]), 0.008)
        self.add(box("gw_lin", (L.gate_cx, L.gate_y0 - pr * 0.5,
                                (L.open_top + L.lintel_z1) * 0.5),
                     (L.open_w + fw * 2, pr * 2.0, L.lintel_h),
                     M["ancient_pale"]), 0.010)

        # 墙脚水线：按门洞左右断开（不能横贯门洞）
        for s_ in (-1, 1):
            xa, xb = ((L.gate_x0, L.open_x0 - 0.02) if s_ < 0
                      else (L.open_x1 + 0.02, L.gate_x1))
            self.add(box("gw_wet%d" % (s_ > 0), ((xa + xb) * 0.5, L.gate_y0 - 0.009,
                                                 L.shelf_z + 0.13),
                         (xb - xa, 0.020, 0.26), M["ancient_dark"]), 0.004)

        # 砌缝：沿断脊的每一段下面来一条横缝（缝就是尺度）
        for i, (xa, xb, z) in enumerate(RIDGE):
            if xb - xa < 0.5 or z < L.lintel_z1:
                continue
            self.add(box("gw_joint%d" % i, ((xa + xb) * 0.5, L.gate_y0 - 0.008,
                                            z - 0.42),
                         (xb - xa - 0.06, 0.016, 0.042), M["ancient_dark"]), 0.002)

        # 两座前凸的扶壁：把 6.4 m 的平面破成三个进深，左右不等高
        for tag, x0, x1, zt, pr2 in (("l", -2.98, -2.16, 3.14, 0.30),
                                     ("r", 2.04, 2.60, 2.52, 0.22)):
            self.add(box("gw_pier%s" % tag, ((x0 + x1) * 0.5,
                                             L.gate_y0 + pr2 * 0.5 - 0.02, zt * 0.5),
                         (x1 - x0, pr2, zt), M["ancient"]), 0.012)
            self.add(box("gw_piercap%s" % tag, ((x0 + x1) * 0.5,
                                                L.gate_y0 + pr2 * 0.5 - 0.02, zt + 0.05),
                         (x1 - x0 + 0.08, pr2 + 0.08, 0.10),
                         M["ancient_mid"]), 0.008)

        # 墙面砌块：四块凸 28 mm 的石（不做整面砖缝）
        for i, (x, z, sx, sz, mat) in enumerate((
                (-2.30, 2.10, 0.74, 0.52, "ancient_mid"), (-1.70, 2.90, 0.62, 0.44, "ancient"),
                (2.02, 2.16, 0.70, 0.48, "ancient"), (2.46, 2.90, 0.56, 0.42, "ancient_mid"))):
            self.add(box("gw_blk%d" % i, (x, L.gate_y0 - 0.014, z),
                         (sx, 0.030, sz), M[mat]), 0.007)

    # ── 5. 门（关着）────────────────────────────────────────────────────────
    def door(self):
        M = self.M
        z0 = L.door_z0
        h = L.door_h
        left = P.door_leaf("dr_l", L.leaf_hinge[0], L.door_hy, z0, L.leaf_w, h,
                           L.door_t, -1, L.door_open, M, bands=2, studs=(0, 0),
                           ring=True, panel=0.20, face=1)
        right = P.door_leaf("dr_r", L.leaf_hinge[1], L.door_hy, z0, L.leaf_w, h,
                            L.door_t, +1, L.door_open, M, bands=2, studs=(0, 0),
                            ring=False, chip=L.door_chip, panel=0.20, face=1)
        self.put(left, 0.009)
        self.put(right, 0.009)

        self.put(P.lock_bar("dr_bar", L.open_x0 + 0.15, L.open_x1 - 0.15,
                            L.door_hy + L.door_t * 0.5 + 0.062, z0 + 1.36, 0.075, M,
                            w=0.072), 0.004)

        # 门槛 0.40 m 高（人的门槛 0.12；这里"不是给你迈的"）
        self.add(box("dr_sill", (L.gate_cx, L.gate_y0 - 0.28, 0.20),
                     (L.open_w + 0.08, 0.62, 0.40), M["ancient"]), 0.010)

        for i, (x, y, s, a) in enumerate(((-0.40, 0.14, 0.34, 0.18),
                                          (0.26, 0.10, 0.30, -0.12),
                                          (0.86, 0.12, 0.26, 0.30))):
            self.add(P.rubble_slab("dr_wedge%d" % i, x, y, z0 + 0.02, s, s * 0.9,
                                   s * 0.72, a, 0.0, M), 0.006)

        # 门缝里的一线火
        self.add(box("fl_seam", (L.gate_cx, L.door_hy + L.door_t * 0.5 + 0.02,
                                 z0 + 0.42), (0.040, 0.02, 0.20), M["ember"]), 0.002)

    # ── 6. 土坡（三座，把门墙两端和后墙吃掉）────────────────────────────────
    def back(self):
        M = self.M
        tops = {}
        for tag, spec, sd in (("l", L.hill_l, 17), ("lf", L.hill_lf, 18),
                              ("r", L.hill_r, 19), ("rf", L.hill_rf, 21),
                              ("b", L.hill_b, 23)):
            tops[tag] = self._hill("bq_%s" % tag, spec[1], 0.0, spec[0], seed=sd)

        # 土坡上不能再是一张光面：每座坡顶撒石、插草、戳两根从土里冒出来的石棱
        for tag, sd in (("l", 41), ("lf", 42), ("r", 43), ("rf", 44), ("b", 47)):
            cx = sum(p[0] for p in tops[tag]) / len(tops[tag])
            cy = sum(p[1] for p in tops[tag]) / len(tops[tag])
            top_z = {"l": L.hill_l[0], "lf": L.hill_lf[0], "r": L.hill_r[0],
                     "rf": L.hill_rf[0], "b": L.hill_b[0]}[tag] + 0.06
            self.put(K.stones("bq_st_%s" % tag, cx, cy, top_z - 0.02, 3, 0.42, 0.24,
                              (M["ancient"], M["ancient_dark"]), seed=sd), 0.008)
            self.put(K.grass("bq_tu_%s" % tag, cx + 0.28, cy + 0.16, top_z,
                             0.24, 4, seed=sd + 1, mat=M["moss_dark"]), 0.002)

        # 后坡顶上的残件：三块倒下的方石 + 两根肋骨 + 碎石
        for i, (cx, cy, sx, sy, sz, a) in enumerate((
                (-2.05, -2.45, 1.65, 0.58, 0.52, 0.36),
                (-0.55, -3.05, 1.22, 0.52, 0.46, -0.42),
                (1.70, -2.60, 1.02, 0.48, 0.44, 0.95))):
            self.add(box("bq_fall%d" % i, (cx, cy, L.hill_b[0] - 0.06),
                         (sx, sy, sz), M["ancient_mid"], rot=(0, 0, a)), 0.010)
        self.put(K.stones("bq_stone", -0.40, -1.90, L.hill_b[0] - 0.16,
                          5, 0.80, 0.32, (M["ancient"], M["ancient_dark"]), seed=29), 0.008)

        # 肋骨：从后坡里斜出来（生物元素只此一类）
        ribs = (((1.30, -2.35, L.hill_b[0] - 0.30), (1.62, -2.10, 3.30),
                 (1.86, -1.94, 3.96)),
                ((-1.05, -2.85, L.hill_b[0] - 0.36), (-0.84, -2.62, 3.02),
                 (-0.70, -2.46, 3.52)))
        for i, (p0, p1, p2) in enumerate(ribs):
            r = 0.078 - i * 0.012
            self.put(P.bone_long("bq_rib%d_a" % i, p0, p1, r, M), 0.006)
            self.put(P.bone_long("bq_rib%d_b" % i, p1, p2, r * 0.82, M,
                                 dark=(i > 0), knuckle=False), 0.006)

    # ── 7. 器物（少而准：全都在槽底或台前，不散在台面上）─────────────────────
    def props(self):
        M = self.M
        # 翻倒的火盆（台前土坡上，灰洒出来）
        self.put(P.brazier_tipped("pr_braz", 3.20, 4.52, 0.26, M, ang=2.35,
                                  mat_bowl="ancient", mat_rim="bronze"), 0.006)

        # 半埋的铁栅（台前左侧）
        self.put(P.ground_grate("pr_grate", -3.30, 4.58, 0.22, M,
                                0.86, 0.62, ang=0.35, tilt=0.22), 0.005)

        # 塌下来的门楣石：斜躺在台前，一半埋进土里（平面图里唯一的强斜线）
        ob = box("pr_fallen", (0.0, 0.0, 0.0), (1.85, 0.72, 0.54), M["ancient"])
        P.spin([ob], (0.0, 0.0, 0.0), 0.62, "Z")
        P.spin([ob], (0.0, 0.0, 0.0), 0.10, "X")
        mn = min(v.co.z for v in ob.data.vertices)
        P.nudge(ob, dz=0.10 - mn, dx=-1.05, dy=4.62)
        self.add(ob, 0.012)

        # 槽底：骨堆（横竖交叉的长骨）+ 两簇落石
        self.put(P.bone_stack("pr_bone", -1.58, 0.34, L.pave_z, M, n=3,
                              seed=19, r=0.040), 0.005)
        self.put(K.stones("pr_rub0", 1.52, 0.40, L.floor_z, 4, 0.34, 0.20,
                          (M["ancient"], M["ancient_dark"]), seed=43), 0.008)
        self.put(K.stones("pr_rub1", -1.62, 1.28, L.shelf_z, 4, 0.36, 0.22,
                          (M["ancient"], M["ancient_mid"]), seed=47), 0.008)

        # 斜靠在槽壁上的断板（左）
        ob = box("pr_lean", (0.0, 0.0, 0.0), (0.86, 1.18, 0.15), M["ancient"])
        P.spin([ob], (0.0, 0.0, 0.0), -0.42, "Y")
        P.spin([ob], (0.0, 0.0, 0.0), 0.08, "X")
        mn = min(v.co.z for v in ob.data.vertices)
        P.nudge(ob, dz=L.pave_z + 0.04 - mn, dx=-1.72, dy=0.58)
        self.add(ob, 0.008)

        # 吊链：从过梁下挂到"脖子高度"，末端一个断钩
        self.put(K.chain("pr_chain", -0.98, L.gate_y0 - 0.44, 1.40,
                         L.open_top - 0.02, 0.105, M["iron"], links=6), 0.004)
        self.add(box("pr_chainhook", (-0.98, L.gate_y0 - 0.44, 1.34),
                     (0.095, 0.095, 0.12), M["iron"]), 0.004)
        self.add(box("pr_chainhook2", (-0.94, L.gate_y0 - 0.40, 1.23),
                     (0.038, 0.12, 0.085), M["iron"], rot=(0, 0, 0.5)), 0.004)

    # ── 8. 痕迹：抓痕 / 苔线 / 垂根 ─────────────────────────────────────────
    def traces(self):
        M = self.M
        for i in range(3):
            x = L.leaf_hinge[1] + 0.28 + i * 0.130
            self.add(box("tr_claw%d" % i,
                         (x, L.door_hy - L.door_t * 0.5 - 0.008,
                          L.door_z0 + 1.04),
                         (0.056, 0.016, 0.76), M["void"], rot=(0, 0, 0.10)), 0.002)

        for s in (-1, 1):
            self.add(box("tr_moss%d" % (s > 0), (s * (L.pit_x - 0.007), 0.44,
                                                 L.pave_z + 0.068),
                         (0.014, 0.98, 0.14), M["moss_dark"]), 0.002)

        self.put(P.root_strands("tr_root", -0.72, L.gate_y0 - 0.16,
                                L.open_top - 0.10, M, n=3, seed=29, length=0.46), 0.003)

    # ── 9. 队色（两道）──────────────────────────────────────────────────────
    def team(self):
        M = self.M
        tm, tr = M["team"], M["team_trim"]
        cxr = L.gate_cx

        # ① 前庭中带：连续跨过三级台阶与槽底（水平面 → 俯视主力）
        for i in range(L.step_n):
            zt = L.shelf_z - 0.01 - i * L.step_rise
            y_face = L.pit_y1 - i * L.step_tread
            self.add(box("tm_tread%d" % i, (cxr, y_face - L.step_tread * 0.5,
                                            zt + 0.014),
                         (L.team_runner_w, L.step_tread - 0.02, 0.030), tm), 0.002)
            self.add(box("tm_riser%d" % i, (cxr, y_face + 0.014, zt - 0.192),
                         (L.team_runner_w, 0.028, 0.36), tm), 0.002)
        self.add(box("tm_floor", (cxr, (L.runner_y0 + L.runner_y1) * 0.5,
                                  L.pave_z + 0.014),
                     (L.team_runner_w, L.runner_y1 - L.runner_y0, 0.030), tm), 0.002)
        self.add(box("tm_trim", (cxr - L.team_runner_w * 0.5 - 0.032,
                                 (L.runner_y0 + L.runner_y1) * 0.5,
                                 L.pave_z + 0.016),
                     (0.050, L.runner_y1 - L.runner_y0 - 0.10, 0.012), tr), 0.002)

        # ② 冠顶漆带（水平面 —— 俯视里唯一一条队色）
        self.add(box("tm_crown", (cxr, (L.gate_y0 + L.gate_y1) * 0.5 - 0.10,
                                  L.crown_top + 0.008),
                     (1.55, 0.30, 0.016), tm), 0.002)

        # 门楣正面一条横线（正视唯一的队色，宽 0.12）
        self.add(box("tm_lin", (cxr, L.gate_y0 - L.frame_pr - 0.008,
                                L.lintel_z1 + 0.26),
                     (L.open_w * 0.70, 0.018, 0.120), tm), 0.002)

    # ── 10. 组装 / 收尾 ─────────────────────────────────────────────────────
    def build(self):
        steps = (("pad", self.pad), ("shelf", self.shelf), ("court", self.court),
                 ("gate", self.gate), ("door", self.door), ("back", self.back),
                 ("props", self.props), ("traces", self.traces), ("team", self.team))
        for name, fn in steps:
            if self.parts and name not in self.parts:
                continue
            fn()
        # 整座门墙 + 门扇向左倾 1.26°：石头沉下去的时候不会保持垂直。
        # 只转这几组（石壳/土坡不动），基准点在门墙底 —— 底座不会脱离石壳。
        if L.do_lean:
            piv = (L.gate_cx, 0.0, L.shelf_z - 0.30)
            obs = [it[0] for it in self.items
                   if it[0].name.startswith(("gw_", "dr_", "tm_lin", "tm_crown", "fl_"))]
            P.spin(obs, piv, L.do_lean, axis="Y")
            # 倾斜会把墙的一端压到地面以下（3.2 × sin1.26° ≈ 7 cm）—— 抬回来
            mn = min(v.co.z for ob in obs for v in ob.data.vertices)
            for ob in obs:
                if mn < 0.0:
                    for v in ob.data.vertices:
                        v.co.z -= mn
                    ob.data.update()
        # **必须放在最后**：dl_kit 里有函数会再调 all_materials()，那一步会按
        # PALETTE 把 team / team_trim 刷回联盟蓝。早改等于白改（踩过一次）。
        P.apply_team_style(TEAM_STYLE)
        return self

    def finalize(self, bevel=True):
        flat_pref = ("pt_", "tr_", "tm_", "dr_wedge", "sh_crack", "dr_sill", "sh_talus")
        cc_ok = ("pr_bone", "bq_rib", "pr_chain", "pr_braz", "tr_root", "pr_grate")
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
                B.finalize(ob, bevel=min(max(bev, 0.003), 0.014), seg=1, sub=cc,
                           flat=is_flat)
            else:
                b = 0.0 if (not bevel or max(dims) < 1.10 or bev < 0.006) else bev
                B.finalize(ob, bevel=b, seg=1, sub=0, flat=True)
        objs = [it[0] for it in self.items]
        bpy.ops.object.select_all(action="DESELECT")
        for ob in objs:
            ob.select_set(True)
        bpy.context.view_layer.objects.active = objs[0]
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        bpy.ops.object.select_all(action="DESELECT")
        out = B.join_by_material(objs, prefix="DG")
        mirror_x(out)
        if self.unwrap:
            B.smart_uv(out)
        return out


def build(smooth=True, unwrap=True, bevel=True, parts=None):
    m = Model(smooth, unwrap, parts).build()
    objs = m.finalize(bevel=bevel)
    return objs, B.stats(objs)
