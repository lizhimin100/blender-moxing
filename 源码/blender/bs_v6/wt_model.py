"""
wt_model.py —— 哨塔（Watchtower）：石基 + 双段木构 + 双坡瞭望棚

设计取参考图（参考图/哨塔.png）的三层节奏，换成本套资产的硬边语言：

  ① **石基**：4.76 × 4.76、3.10 高的一段直墙石砌，中央真开一个 1.30 宽的拱门，
     两道水平线脚 + 四角隅石 + 压顶下托石 —— 石基是"塔的基座"，不是"一栋石屋"，
     所以只在正面开门，侧面只留箭孔。
  ② **木塔身分两段**：下段 3.90 宽 × 3.66 高、上段 3.40 宽 × 3.26 高，
     中间夹一圈 5.20 的中层挑台、顶上一圈 5.70 的观景台 —— 收 / 放 / 收 / 放，
     俯视是四层同心方，正视是三条水平线，这是"层次"的全部来源。
  ③ **顶部陡坡双坡瞭望棚**（gable_steep，六座唯一）：脊 49.2°，只盖 3.90 × 4.70，
     四角留 0.9 m 环廊；山墙只做上半段三角板 + 三根竖棂，下半敞开 ——
     读作"架在柱子上的顶棚"，不是"给塔扣了顶帽子"，也不与城镇大厅的四坡 / 兵营的平顶重复。
  ④ **外梯**：一道 57° 的木梯从石台右前角斜靠到中层挑台左前角，跨过门洞上方。
     它是整座建筑唯一的斜线，也是"哨塔"最好认的一笔。

坐标：X 右、Y 前（+Y = 正面）、Z 上；原点在占地中心，z = 0 地面。
交付前整体沿 X 镜像一次（与另三座一致），所以建模期的 +X 在成品里是左边的 −X。
"""
import math

import bpy
from mathutils import Vector

import bslib as L
import br_model as BR
from bslib import (arch_band, beam, box, cone, cyl, extrude, frustum, mesh_obj,
                   revolve, ring_y, taper_box)
from br_model import mirror_x

# ── 场地 / 石台 ─────────────────────────────────────────────────────────────
YARD_X, YARD_Y0, YARD_Y1 = 3.54, -3.34, 3.76
G_Z = 0.16                       # 夯土面
PODX, PODY = 2.55, 2.55          # 石台半宽（5.10）
POD_Z = 0.42                     # 石台顶
STEP_Y = 3.00                    # 踏步前沿（两级）

# ── 石基（4.20 × 4.20，0.42 → 4.02）───────────────────────────────────────
SBX = 2.10                       # 半宽
SB0, SB1 = 0.42, 4.02
SBCX = 2.20                      # 压顶半宽（出挑 0.10）
SBC0, SBC1 = 4.02, 4.26
DW = 0.28                        # 前墙厚（门洞真实深度）
GW = 0.60                        # 门洞半宽 1.20
SPRING = 2.45                    # 拱脚
ARCH = SPRING + GW               # 拱顶 3.05

# ── 木塔上 / 下段 ──────────────────────────────────────────────────────────
W1 = 1.80                        # 下段半宽 3.60
T1A, T1B = 4.26, 7.86
W2 = 1.55                        # 上段半宽 3.10
T2A, T2B = 8.16, 11.16

# ── 挑台（中层 5.10 / 顶层 5.30 —— 越往上越大，参考图的倒锥挑台）──────────
MD0, MD1 = 7.86, 8.16
MX = 2.65
TD0, TD1 = 11.16, 11.46
TX = 2.50

# ── 瞭望亭（双坡 44°，3.20 × 3.60，环廊 0.90，净空 0.88）─────────────────
CEAVE = 13.34
CRIDGE = 14.90
CW, CL = 1.60, 1.80              # 半宽 3.20 / 半长 3.60
CPX, CPY = 1.22, 1.42            # 四根柱的平面位置

# ── 旗 ────────────────────────────────────────────────────────────────────
POLE0, POLE1 = 14.20, 17.16
FLAG_W, FLAG_H = 1.58, 0.98

# ── 外梯（跨过门洞，接中层挑台左前角）──────────────────────────────────────
LAD_W = 0.64
LAD_Y = 2.58                     # 梯子中心（前墙 2.20 之外 0.06）
LAD_P0 = (2.42, LAD_Y, 0.44)
LAD_P1 = (-2.06, LAD_Y, 8.14)


# ── 通用构件 ───────────────────────────────────────────────────────────────
def frame_ring(name, x0, x1, y0, y1, z0, z1, t, mat):
    """矩形环（腰线 / 压顶 / 封边）：45° 斜接，四角不留缺口、不叠同高面。"""
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


class Model(BR.Model):

    # ── 1. 场地 / 石台 / 踏步 ───────────────────────────────────────────────
    def plinth(self):
        M = self.M
        cy = (YARD_Y0 + YARD_Y1) * 0.5
        dy = YARD_Y1 - YARD_Y0
        # 夯土场地：一层实体，上面不贴任何薄片（薄片在 RTS 距离就是闪）
        self.add(box("yard_soil", (0, cy, G_Z * 0.5), (YARD_X * 2, dy, G_Z),
                     M["earth"]), 0.020)
        # 牙子：左右 + 后三段（正面留给踏步，不封口）
        for sgn in (-1, 1):
            self.add(box("yard_curb", (sgn * (YARD_X - 0.09), cy - 0.20, G_Z + 0.03),
                         (0.18, dy - 0.40, 0.10), M["paving"]), 0.006)
        self.add(box("yard_curb_b", (0, YARD_Y0 + 0.09, G_Z + 0.03),
                     (YARD_X * 2 - 0.36, 0.18, 0.10), M["paving"]), 0.006)
        # 石台两级
        self.add(box("plinth_lo", (0, 0, 0.10), (PODX * 2 + 0.52, PODY * 2 + 0.52, 0.20),
                     M["stone_mid"]), 0.018)
        self.add(box("plinth_hi", (0, 0, 0.31), (PODX * 2 + 0.14, PODY * 2 + 0.14, 0.22),
                     M["stone_light"]), 0.020)
        # 两级踏步（正面）
        self.add(box("step_0", (0, STEP_Y + 0.30, 0.07), (2.90, 0.60, 0.14),
                     M["stone_mid"]), 0.008)
        self.add(box("step_1", (0, STEP_Y + 0.03, 0.18), (2.90, 0.54, 0.16),
                     M["stone_mid"]), 0.008)
        # 踏口两侧的小石墩（0.28 见方，比台面高 0.26）
        for sgn in (-1, 1):
            self.add(box("step_newel", (sgn * 1.62, STEP_Y + 0.10, 0.50),
                         (0.30, 0.30, 0.16), M["stone_light"]), 0.006)

    # ── 2. 石基（真拱门 + 线脚 + 隅石 + 压顶）────────────────────────────────
    def stone_base(self):
        M = self.M
        hz = (SB0 + SB1) * 0.5
        # 主块：y 从 −2.38 到 2.08（前墙留 0.30 厚单独做，好开门洞）
        self.add(box("sb_core", (0, (-SBX + (SBX - DW)) * 0.5, hz),
                     (SBX * 2, SBX * 2 - DW, SB1 - SB0), M["stone_mid"]), 0.034)
        # 前墙：左 / 右 / 拱上（真挖洞）
        for sgn in (-1, 1):
            x0, x1 = sgn * GW, sgn * SBX
            self.add(box("sb_front_%s" % ("R" if sgn > 0 else "L"),
                         ((x0 + x1) * 0.5, SBX - DW * 0.5, hz),
                         (abs(x1 - x0), DW, SB1 - SB0), M["stone_mid"]), 0.028)
        top = [(-GW, ARCH), (-GW, SB1), (GW, SB1), (GW, ARCH)]
        for s in range(1, 10):
            a = math.pi * s / 10
            top.append((GW * math.cos(a), SPRING + GW * math.sin(a)))
        self.add(extrude("sb_front_T", top, "Y", DW, (0, 0), M["stone_mid"],
                         offset=SBX - DW * 0.5), 0.026)
        # 墙裙 + 一道水平线脚：把 3.60 高的石墙分成"墙脚 / 墙身"两段。
        # 三道横线会把石基读成"三层蛋糕"，两条正好。
        self.add(frame_ring("sb_dado", -SBX - 0.05, SBX + 0.05, -SBX - 0.05, SBX + 0.05,
                            SB0, 0.96, 0.16, M["stone_light"]), 0.010)
        self.add(frame_ring("sb_line0", -SBX - 0.05, SBX + 0.05,
                            -SBX - 0.05, SBX + 0.05, 2.08, 2.16, 0.15,
                            M["stone_light"]), 0.008)
        # 隅石：两层，每层两块交错
        for sx in (-1, 1):
            for sy in (-1, 1):
                for i, zz in enumerate((1.16, 2.62)):
                    for k in range(2):
                        w = 0.54 if k == 0 else 0.44
                        self.add(box("quoin", (sx * (SBX - w * 0.5 + 0.018),
                                               sy * (SBX - w * 0.5 + 0.018),
                                               zz + k * 0.36),
                                     (w, w, 0.34), M["stone_light"]), 0.007)
        # 压顶 + 压顶下的托石
        self.add(box("sb_cap", (0, 0, (SBC0 + SBC1) * 0.5),
                     (SBCX * 2, SBCX * 2, SBC1 - SBC0), M["stone_mid"]), 0.020)
        # 托石：四面各 4 块，顶面压到 3.99（比石基顶 4.02 低 30 mm，避免同高共面）
        n = 4
        for k in range(n):
            f = -1.0 + 2.0 * k / (n - 1)
            for sgn in (-1, 1):
                self.add(box("sb_corbel", (f * 1.52, sgn * (SBX + 0.03), 3.90),
                             (0.26, 0.20, 0.18), M["stone_light"]), 0.005)
                self.add(box("sb_corbel", (sgn * (SBX + 0.03), f * 1.52, 3.90),
                             (0.20, 0.26, 0.18), M["stone_light"]), 0.005)
        # ── 门：门洞内壁就是 sb_core 的前表面（y = 2.08），门扇内凹 0.10 ──
        self.add(box("gate_leaf", (0, SBX - 0.20, 1.42), (1.22, 0.08, 1.94),
                     M["wood_dark"]), 0.010)
        for k in (-1, 1):
            self.add(box("gate_band", (0, SBX - 0.24, 1.42 + k * 0.58),
                         (1.22, 0.04, 0.11), M["iron"]), 0.004)
        self.add(ring_y("gate_ring", (0, SBX - 0.25, 1.30), 0.055, 0.095, 0.045, 10,
                        M["iron"]), 0.003)
        self.add(box("gate_thresh", (0, SBX - 0.10, 0.47), (1.62, 0.52, 0.12),
                     M["stone_dark"]), 0.006)
        # 拱券石（凸出墙面 0.08）+ 两侧门柱石
        self.add(arch_band("gate_arch", 0.0, SPRING, GW, GW + 0.17, SBX + 0.005,
                           SBX + 0.085, M["stone_light"], segs=8), 0.010)
        for sgn in (-1, 1):
            self.add(box("gate_jamb", (sgn * (GW + 0.085), SBX + 0.045, SPRING * 0.5 + 0.30),
                         (0.17, 0.10, SPRING - 0.34), M["stone_light"]), 0.008)
        # 门两侧的队色壁柱：把"门框"这条结构线染出来，低处也有识别色
        for sgn in (-1, 1):
            self.add(box("gate_pilaster", (sgn * (GW + 0.235), SBX + 0.038, 1.62),
                         (0.13, 0.07, 2.30), M["team"]), 0.004)
        # 门楣横匾（阵营色）+ 金线
        self.add(box("gate_plaque", (0, SBX + 0.035, 3.44), (2.10, 0.07, 0.34),
                     M["team"]), 0.006)
        self.add(box("gate_plaque_t", (0, SBX + 0.045, 3.63), (2.10, 0.09, 0.07),
                     M["team_trim"]), 0.004)
        # 箭孔：深色底板 + 更深的窄缝（读作有铁栅的射孔）
        for (axis, u, v, out) in (("X", SBX, -0.95, 1), ("X", SBX, 0.95, 1),
                                  ("Y", 0.0, -SBX, -1), ("X", -SBX, 0.10, -1)):
            if axis == "X":
                self.add(box("slot_", (u + out * 0.02, v, 1.86),
                             (0.05, 0.32, 0.74), M["stone_dark"]), 0.004)
                self.add(box("slot_", (u + out * 0.035, v, 1.86),
                             (0.04, 0.15, 0.56), M["coal"]), 0.002)
            else:
                self.add(box("slot_", (u, v + 0.02, 1.86),
                             (0.32, 0.05, 0.74), M["stone_dark"]), 0.004)
                self.add(box("slot_", (u, v + 0.035, 1.86),
                             (0.15, 0.04, 0.56), M["coal"]), 0.002)

    # ── 3. 木塔下段 ─────────────────────────────────────────────────────────
    def wood_low(self):
        M = self.M
        hz = (T1A + T1B) * 0.5
        self.add(box("w1_wall", (0, 0, hz), (W1 * 2, W1 * 2, T1B - T1A),
                     M["wood_mid"]), 0.030)
        # 墙裙（底部护板）：0.68 高，把木塔分成"深色基脚 + 亮色墙身"两段
        self.add(box("w1_skirt", (0, 0, T1A + 0.34), (W1 * 2 + 0.06, W1 * 2 + 0.06, 0.68),
                     M["wood_dark"]), 0.012)
        # 四角立柱（比墙面凸 0.03）
        for sx in (-1, 1):
            for sy in (-1, 1):
                self.add(box("col1_", (sx * (W1 - 0.10), sy * (W1 - 0.10), hz + 0.03),
                             (0.24, 0.24, T1B - T1A + 0.06), M["wood_dark"]), 0.010)
        # 两道腰梁：X 向比 Y 向高 20 mm，转角处梁头交错（不共面也不会撞）
        for zz, tag in ((5.02, "a"), (7.00, "b")):
            for sy in (-1, 1):
                self.add(box("rail1_%s" % tag, (0, sy * (W1 + 0.03), zz),
                             (W1 * 2 + 0.28, 0.22, 0.20), M["wood_dark"]), 0.008)
            for sx in (-1, 1):
                self.add(box("rail1_%s" % tag, (sx * (W1 + 0.03), 0, zz - 0.025),
                             (0.22, W1 * 2 + 0.04, 0.18), M["wood_dark"]), 0.008)
        # 正面窗（抬到外梯之上：梯子在 x=0.2 处已爬到 4.7）
        self.window("win1_f", 0.20, 5.34, 0.50, 0.86, "Y", 1, W1, wood=True)
        # 侧墙两扇上下错开（读作两级窗）+ 后墙一扇
        for sx in (-1, 1):
            self.window("win1_s", -0.78, 5.26, 0.46, 0.78, "X", sx, sx * W1, wood=True)
            self.window("win1_s", 0.70, 6.24, 0.42, 0.62, "X", sx, sx * W1, wood=True)
        self.window("win1_b", 0.60, 5.34, 0.48, 0.82, "Y", -1, -W1, wood=True)

    # ── 4. 中层挑台（5.20）+ 栏板（三角开口给外梯）────────────────────────────
    def deck_mid(self):
        M = self.M
        # 托梁：X 向比 Y 向高 20 mm
        for sy in (-1, 1):
            self.add(box("d1_joist", (0, sy * 1.62, MD0 + 0.09),
                         (MX * 2 + 0.04, 0.20, 0.18), M["wood_dark"]), 0.010)
        for sx in (-1, 1):
            self.add(box("d1_joist", (sx * 1.62, 0, MD0 + 0.07),
                         (0.20, MX * 2 + 0.04, 0.16), M["wood_dark"]), 0.010)
        # 平台板 0.24 厚 + 5 条铺板 0.06 厚压在它上面（板顶 = MD1）。
        # 铺板必须**抬到平台板之上**，嵌进去的话从任何角度都只剩 4 条缝。
        self.add(box("d1_deck", (0, 0, MD0 + 0.12), (MX * 2, MX * 2, 0.24),
                     M["wood_mid"]), 0.018)
        bw = (MX * 2 - 4 * 0.02) / 5
        for k in range(5):
            x = -MX + bw * 0.5 + k * (bw + 0.02)
            self.add(box("d1_plank", (x, 0, MD0 + 0.27), (bw, MX * 2 - 0.04, 0.06),
                         M["wood_warm"]), 0.004)
        # 封边
        self.add(frame_ring("d1_fascia", -MX - 0.01, MX + 0.01, -MX - 0.01, MX + 0.01,
                            MD0 + 0.02, MD0 + 0.16, 0.09, M["wood_dark"]), 0.005)
        # 斜撑：每面 2 根
        for sx in (-1, 1):
            for sy in (-1, 1):
                self.add(beam("br1_", (sx * (W1 - 0.02), sy * 1.30, 6.86),
                              (sx * (MX - 0.12), sy * 1.30, MD0 + 0.02),
                              0.13, 0.16, M["wood_dark"]), 0.006)
                self.add(beam("br1_", (sx * 1.30, sy * (W1 - 0.02), 6.86),
                              (sx * 1.30, sy * (MX - 0.12), MD0 + 0.02),
                              0.13, 0.16, M["wood_dark"]), 0.006)
        # 角柱先占位，栏板两端各内缩 0.20 让开它（否则端柱与角柱完全重合）
        for (x, y) in ((MX - 0.09, MX - 0.09), (-MX + 0.09, MX - 0.09),
                       (-MX + 0.09, -MX + 0.09), (MX - 0.09, -MX + 0.09)):
            self.add(box("p1_corner", (x, y, MD1 + 0.56), (0.20, 0.20, 1.12),
                         M["wood_dark"]), 0.008)
            self.add(box("p1_corner_cap", (x, y, MD1 + 1.14), (0.26, 0.26, 0.08),
                         M["wood_warm"]), 0.004)
        # 梯口两侧的短柱 + 一道半高护栏（缺口读成"入口"，不是"少做了一块"）
        for x in (-MX + 0.19, -1.62):
            self.add(box("p1_gatepost", (x, MX - 0.09, MD1 + 0.54), (0.18, 0.18, 1.08),
                         M["wood_dark"]), 0.008)
        self.add(box("p1_gateguard", ((-MX + 0.19 - 1.62) * 0.5, MX - 0.09, MD1 + 0.46),
                     (abs(-1.62 - (-MX + 0.19)) + 0.02, 0.11, 0.10),
                     M["wood_dark"]), 0.004)
        # 栏板：正面留角部开口给外梯，其余三面通长
        self.parapet("p1_f", -1.62, MX - 0.20, "X", MX - 0.09, MD1, 1.00)
        self.parapet("p1_b", -MX + 0.20, MX - 0.20, "X", -MX + 0.09, MD1, 1.00, lift=0.006)
        self.parapet("p1_r", -MX + 0.20, MX - 0.20, "Y", MX - 0.09, MD1, 1.00, lift=0.012)
        self.parapet("p1_l", -MX + 0.20, 1.62, "Y", -MX + 0.09, MD1, 1.00, lift=0.018)

    # ── 5. 木塔上段 ─────────────────────────────────────────────────────────
    def wood_up(self):
        M = self.M
        hz = (T2A + T2B) * 0.5
        self.add(box("w2_wall", (0, 0, hz), (W2 * 2, W2 * 2, T2B - T2A),
                     M["wood_mid"]), 0.030)
        self.add(box("w2_skirt", (0, 0, T2A + 0.24), (W2 * 2 + 0.05, W2 * 2 + 0.05, 0.48),
                     M["wood_dark"]), 0.012)
        for sx in (-1, 1):
            for sy in (-1, 1):
                self.add(box("col2_", (sx * (W2 - 0.09), sy * (W2 - 0.09), hz + 0.02),
                             (0.22, 0.22, T2B - T2A + 0.04), M["wood_dark"]), 0.009)
        for sy in (-1, 1):
            self.add(box("rail2_", (0, sy * (W2 + 0.02), 9.02),
                         (W2 * 2 + 0.20, 0.15, 0.14), M["wood_dark"]), 0.008)
        for sx in (-1, 1):
            self.add(box("rail2_", (sx * (W2 + 0.02), 0, 9.00),
                         (0.15, W2 * 2 + 0.02, 0.12), M["wood_dark"]), 0.008)
        # 正面小窗（正对中轴）+ 侧面窗
        self.window("win2_f", 0.0, 9.30, 0.58, 1.06, "Y", 1, W2, wood=True)
        for sx in (-1, 1):
            self.window("win2_s", 0.24, 9.34, 0.52, 0.94, "X", sx, sx * W2, wood=True)

    # ── 6. 顶平台（5.70）+ 栏板 + 瞭望棚柱 ──────────────────────────────────
    def deck_top(self):
        M = self.M
        for sy in (-1, 1):
            self.add(box("d2_joist", (0, sy * 1.80, TD0 + 0.09),
                         (TX * 2 + 0.04, 0.20, 0.18), M["wood_dark"]), 0.010)
        for sx in (-1, 1):
            self.add(box("d2_joist", (sx * 1.80, 0, TD0 + 0.07),
                         (0.20, TX * 2 + 0.04, 0.16), M["wood_dark"]), 0.010)
        self.add(box("d2_deck", (0, 0, TD0 + 0.12), (TX * 2, TX * 2, 0.24),
                     M["wood_mid"]), 0.018)
        bw = (TX * 2 - 4 * 0.02) / 5
        for k in range(5):
            x = -TX + bw * 0.5 + k * (bw + 0.02)
            self.add(box("d2_plank", (x, 0, TD0 + 0.27), (bw, TX * 2 - 0.04, 0.06),
                         M["wood_warm"]), 0.004)
        self.add(frame_ring("d2_fascia", -TX - 0.01, TX + 0.01, -TX - 0.01, TX + 0.01,
                            TD0 + 0.02, TD0 + 0.16, 0.09, M["wood_dark"]), 0.005)
        # 出挑 1.15，双层斜撑
        for sx in (-1, 1):
            for sy in (-1, 1):
                self.add(beam("br2_", (sx * (W2 - 0.02), sy * 1.42, 9.96),
                              (sx * (TX - 0.14), sy * 1.42, TD0 + 0.02),
                              0.14, 0.17, M["wood_dark"]), 0.006)
                self.add(beam("br2_", (sx * 1.42, sy * (W2 - 0.02), 9.96),
                              (sx * 1.42, sy * (TX - 0.14), TD0 + 0.02),
                              0.14, 0.17, M["wood_dark"]), 0.006)
                # 平台底的两根挑梁（压在斜撑上方，撑住出挑的板边）
                for k in (-1, 1):
                    self.add(box("d2_cantilever",
                                 (sx * (W2 + (TX - W2) * 0.5), sy * (1.42 + k * 0.62),
                                  TD0 - 0.06),
                                 (TX - W2 + 0.12, 0.16, 0.18), M["wood_dark"]), 0.006)
        # 四面栏板（两端内缩 0.20 让开角柱）
        self.parapet("p2_f", -TX + 0.20, TX - 0.20, "X", TX - 0.09, TD1, 1.02)
        self.parapet("p2_b", -TX + 0.20, TX - 0.20, "X", -TX + 0.09, TD1, 1.02,
                     lift=0.006)
        self.parapet("p2_r", -TX + 0.20, TX - 0.20, "Y", TX - 0.09, TD1, 1.02,
                     lift=0.012)
        self.parapet("p2_l", -TX + 0.20, TX - 0.20, "Y", -TX + 0.09, TD1, 1.02,
                     lift=0.018)
        # 角柱（比栏板高 0.30，柱头带金球）
        for (x, y) in ((TX - 0.09, TX - 0.09), (-TX + 0.09, TX - 0.09),
                       (-TX + 0.09, -TX + 0.09), (TX - 0.09, -TX + 0.09)):
            self.add(box("p2_corner", (x, y, TD1 + 0.64), (0.24, 0.24, 1.28),
                         M["wood_dark"]), 0.010)
            self.add(box("p2_corner_cap", (x, y, TD1 + 1.32), (0.30, 0.30, 0.10),
                         M["wood_warm"]), 0.004)
            self.add(revolve("p2_finial", [(0.0, 0.0), (0.09, 0.02), (0.115, 0.09),
                                           (0.06, 0.16), (0.0, 0.19)], 8,
                             (x, y, TD1 + 1.37), M["gold"]), 0.0, 1)
        # 瞭望亭四根柱（柱头金 + 柱箍阵营色 + 角撑）
        for sx in (-1, 1):
            for sy in (-1, 1):
                self.add(box("cp_col", (sx * CPX, sy * CPY, (TD1 + CEAVE) * 0.5),
                             (0.26, 0.26, CEAVE - TD1), M["wood_dark"]), 0.012)
                self.add(box("cp_col_base", (sx * CPX, sy * CPY, TD1 + 0.10),
                             (0.36, 0.36, 0.20), M["wood_warm"]), 0.006)
                self.add(box("cp_col_band", (sx * CPX, sy * CPY, TD1 + 1.40),
                             (0.30, 0.30, 0.22), M["team"]), 0.005)
                self.add(box("cp_col_cap", (sx * CPX, sy * CPY, CEAVE - 0.22),
                             (0.36, 0.36, 0.16), M["wood_warm"]), 0.006)
                # 角撑：柱顶到平台面的斜撑，顶棚才不是"浮"在四根杆上
                self.add(beam("cp_brace", (sx * (CPX + 0.02), sy * (CPY + 0.02), CEAVE - 0.62),
                              (sx * (CPX + 0.62), sy * (CPY + 0.62), TD1 + 0.10),
                              0.095, 0.075, M["wood_dark"]), 0.004)
        # 平台上的道具：火盆（左前角）、水桶、箭袋
        self.brazier("braz_", (2.24, 2.24, TD1))
        self.barrel("barrel_t", (2.12, -1.02), 0.28, 0.66, TD1)
        for (x, y) in ((2.34, 0.34), (0.34, 2.34)):
            self.quiver("quiver_", (x, y, TD1))

    # ── 7. 瞭望亭（双坡 38° + 半木构山墙，只占平台中央）─────────────────────
    def canopy(self):
        M = self.M
        # 檐梁（四边）+ 脊梁
        for sy in (-1, 1):
            self.add(box("cp_beam_e", (0, sy * CL, CEAVE + 0.07),
                         (CW * 2 + 0.20, 0.18, 0.18), M["wood_dark"]), 0.008)
        for sx in (-1, 1):
            self.add(box("cp_beam_e", (sx * CW, 0, CEAVE + 0.05),
                         (0.18, CL * 2 + 0.20, 0.18), M["wood_dark"]), 0.008)
        self.add(box("ridge_beam", (0, 0, CRIDGE - 0.08), (0.18, CL * 2 + 0.26, 0.18),
                     M["wood_dark"]), 0.008)
        # 两坡屋面板（每坡出檐 0.20）
        pr = [(CW + 0.36, CL + 0.03, CEAVE - 0.20), (CW + 0.36, -CL - 0.03, CEAVE - 0.20),
              (0.0, -CL - 0.03, CRIDGE), (0.0, CL + 0.03, CRIDGE)]
        pl = [(-CW - 0.36, CL + 0.03, CEAVE - 0.20), (-CW - 0.36, -CL - 0.03, CEAVE - 0.20),
              (0.0, -CL - 0.03, CRIDGE), (0.0, CL + 0.03, CRIDGE)]
        for nm, pp in (("cp_roof_r", pr), ("cp_roof_l", pl)):
            self.add(slab(nm, pp, 0.16, M["roof"]), 0.006)
        # 不铺瓦垄：3 m 的坡上，任何亮脊都会读成"银白条纹板"。
        # 改铺 3 道暗缝（roof_edge 细条，压在坡面上只露出几毫米）——
        # 读作"木板拼接"，远看只是三条若隐若现的线，不抢色。
        for i in range(2):
            f = (i + 0.5) / 2.6
            zz = CRIDGE + (CEAVE - 0.14 - CRIDGE) * f
            for sx in (-1, 1):
                self.add(box("cp_seam", (sx * f * (CW + 0.20), 0, zz + 0.004),
                             (0.035, CL * 2 + 0.02, 0.018), M["roof_edge"]), 0.0)
        # 封檐板（两坡外沿）+ 檐下滴水条：屋顶有厚度，才不像"飘着的板"
        for sx in (-1, 1):
            self.add(box("cp_fascia", (sx * (CW + 0.39), 0, CEAVE - 0.25),
                         (0.09, CL * 2 + 0.10, 0.22), M["roof_edge"]), 0.005)
            self.add(box("cp_drip", (sx * (CW + 0.44), 0, CEAVE - 0.13),
                         (0.06, CL * 2 + 0.12, 0.08), M["roof_edge"]), 0.003)
        # 檐下椽头（每侧 4 个，压在封檐板下沿，读作"椽子挑出来"）
        for sx in (-1, 1):
            for k in range(4):
                yy = -CL + 0.24 + k * (CL * 2 - 0.48) / 3.0
                self.add(box("cp_rafter_end", (sx * (CW + 0.31), yy, CEAVE - 0.30),
                             (0.30, 0.10, 0.11), M["wood_warm"]), 0.003)
        # 脊瓦 + 脊端金饰
        self.add(box("ridge_tile", (0, 0, CRIDGE + 0.05), (0.22, CL * 2 + 0.16, 0.12),
                     M["roof_edge"]), 0.006)
        for sy in (-1, 1):
            self.add(box("ridge_end", (0, sy * (CL + 0.06), CRIDGE + 0.10),
                         (0.18, 0.12, 0.11), M["gold"]), 0.004)
        # 顶棚底面：3 道露明椽（近景抬头能看见）
        for y in (-1.05, 0.0, 1.05):
            self.add(box("cp_rafter", (0, y, CEAVE - 0.02), (CW * 2 - 0.08, 0.11, 0.09),
                         M["wood_dark"]), 0.004)
        # 山墙（前后）：下半敞开（透出后面的天空），只做上三角板 + 三根竖棂
        for sy in (-1, 1):
            yy = sy * (CL + 0.06)
            self.add(box("gab_plate", (0, yy, CEAVE + 0.09),
                         (CW * 2 - 0.10, 0.13, 0.15), M["wood_dark"]), 0.006)
            zb = 13.95
            t = (zb - CEAVE) / (CRIDGE - CEAVE)
            hw = CW * (1.0 - t)
            tri = [(-hw, zb), (hw, zb), (0.0, CRIDGE - 0.08)]
            self.add(extrude("gab_tri", tri, "Y", 0.11, (0, 0),
                             M["wood_mid"], offset=yy), 0.006)
            # 三根竖棂（压在三角板上，凸 0.03）
            for k in (-1, 0, 1):
                xx = k * 0.44
                hh = (CRIDGE - 0.08 - zb) * (1.0 - abs(k) * 0.44)
                self.add(box("gab_mull", (xx, yy + sy * 0.02, zb + hh * 0.5),
                             (0.09, 0.05, hh), M["wood_dark"]), 0.003)
            # 山墙斜撑（从檐口到脊，贴在三角板外侧）
            for sx in (-1, 1):
                self.add(beam("gab_brace", (sx * (CW - 0.04), yy + sy * 0.02, CEAVE + 0.14),
                              (sx * 0.05, yy + sy * 0.02, CRIDGE - 0.14),
                              0.08, 0.06, M["wood_dark"]), 0.003)
        # 前山墙徽记
        self.crest("crest_gable", "Y", 0.0, CL + 0.06 + 0.075, 13.96, 0.46)

    # ── 8. 外梯（57°，跨过门洞上方）─────────────────────────────────────────
    def ladder(self):
        M = self.M
        p0 = Vector(LAD_P0)
        p1 = Vector(LAD_P1)
        d = p1 - p0
        n = d.normalized()
        # 两根斜梁（在梯子两侧）
        for sgn in (-1, 1):
            off = Vector((0, sgn * (LAD_W * 0.5 - 0.05), 0))
            self.add(beam("ldr_", p0 + off - n * 0.12, p1 + off + n * 0.08,
                          0.12, 0.18, M["wood_dark"]), 0.006)
        # 踏档
        cnt = 13
        for i in range(cnt):
            f = (i + 0.5) / cnt
            c = p0 + d * f
            self.add(box("ldr_step", (c.x, c.y, c.z - 0.03),
                         (0.15, LAD_W - 0.03, 0.09), M["wood_warm"]), 0.004)
        # 外侧扶手：斜杆 + 立柱
        rail0 = p0 + Vector((0, LAD_W * 0.5 + 0.02, 0.86))
        rail1 = p1 + Vector((0, LAD_W * 0.5 + 0.02, 0.86))
        self.add(beam("ldr_rail", rail0, rail1, 0.075, 0.085, M["team_trim"]), 0.004)
        for i in range(5):
            f = (i + 0.5) / 5
            c = p0 + d * f
            self.add(box("ldr_post", (c.x, LAD_Y + LAD_W * 0.5 + 0.02, c.z + 0.43),
                         (0.08, 0.08, 0.86), M["team_trim"]), 0.003)
        # 底部接地的两级石踏（在石台上，别让梯脚悬着）
        self.add(box("ldr_foot", (2.42, LAD_Y, 0.50), (0.56, 0.86, 0.16),
                     M["stone_mid"]), 0.006)

    # ── 9. 旗 ───────────────────────────────────────────────────────────────
    def flag(self):
        M = self.M
        self.add(revolve("flag_pole", [(0.088, 0.0), (0.072, POLE1 - POLE0 - 0.18),
                                       (0.060, POLE1 - POLE0)], 8,
                         (0, 0, POLE0), M["wood_dark"]), 0.0, 1)
        self.add(revolve("flag_ball", [(0.0, 0.0), (0.095, 0.03), (0.11, 0.10),
                                       (0.055, 0.16), (0.0, 0.18)], 8,
                         (0, 0, POLE1), M["gold"]), 0.0, 1)
        # 杆上的两只铁箍（穿出屋脊处 + 旗顶下方）
        for zz, r in ((CRIDGE + 0.16, 0.098), (POLE1 - 0.58, 0.078)):
            self.add(revolve("flag_ring", [(r, 0.0), (r + 0.022, 0.0),
                                           (r + 0.022, 0.09), (r, 0.09)], 8,
                             (0, 0, zz), M["iron"]), 0.0, 1)
        # 燕尾旗（与另三座同一形制：上沿平、末端一个 V 形缺口）
        zt = POLE1 - 0.46
        prof = [(0.0, 0.0), (FLAG_W, -0.09), (FLAG_W * 0.80, -FLAG_H * 0.50),
                (FLAG_W, -FLAG_H * 0.92), (0.0, -FLAG_H)]
        self.add(extrude("flag_cloth", prof, "Y", 0.05, (0.0, zt), M["team"],
                         offset=0.0), 0.004)
        self.add(box("flag_trim", (0.0, 0.0, zt + 0.03), (0.07, 0.06, 0.06),
                     M["team_trim"]), 0.002)
        self.crest("crest_flag", "Y", 0.40, 0.027, zt - 0.56, 0.40)

    # ── 10. 场地：围栏 / 木桶 / 柴堆 / 碎石 / 草簇 ───────────────────────────
    def yard(self):
        M = self.M
        # 围栏：正面两侧各一段，再从端头向后折 1.6 m（L 形半围合）
        for sgn in (-1, 1):
            x0, x1 = sgn * 1.92, sgn * (YARD_X - 0.14)
            self.fence("fence_f%s" % ("R" if sgn > 0 else "L"),
                       (x0, YARD_Y1 - 0.16), (x1, YARD_Y1 - 0.16), 1.08)
            self.fence("fence_s%s" % ("R" if sgn > 0 else "L"),
                       (x1, YARD_Y1 - 0.16), (x1, YARD_Y1 - 1.78), 1.08,
                       skip_first=True, lift=0.022)
            # 转角柱（比围栏高，带尖帽）
            self.add(box("fence_corner", (x1, YARD_Y1 - 0.16, 0.72),
                         (0.24, 0.24, 1.44), M["wood_dark"]), 0.008)
            self.add(cone("fence_corner_cap", (x1, YARD_Y1 - 0.16, 1.44),
                          (x1, YARD_Y1 - 0.16, 1.64), 0.18, 4, M["wood_dark"]), 0.0, 1)
        # 木桶 ×2（正面左、侧后）
        self.barrel("barrel_a", (-2.46, 3.30), 0.30, 0.74, G_Z)
        self.barrel("barrel_b", (-3.10, 2.36), 0.26, 0.62, G_Z)
        # 柴堆（靠右后侧，3 层短木）
        # 备用木料：两根原木沿后墙靠着（场地外圈只剩 0.5 m，放不下柴堆）
        for (xx, yy, ln) in ((2.98, -2.44, 1.30), (3.16, -2.34, 1.06)):
            self.add(box("pile_", (xx, yy, G_Z + 0.10), (0.19, ln, 0.19),
                         M["wood_warm"]), 0.006)
            self.add(box("pile_end", (xx, yy - ln * 0.5 + 0.03, G_Z + 0.10),
                         (0.16, 0.06, 0.16), M["wood_dark"]), 0.003)
        # 碎石 ×4 / 草簇 ×3（都是有厚度的实体，不是薄片）
        for (px, py, rz) in ((-3.06, 0.62, 0.4), (3.08, 1.10, -0.3),
                             (2.96, -2.30, 0.9), (-3.04, -1.86, 0.2)):
            self.add(box("pebble_", (px, py, G_Z + 0.05), (0.22, 0.16, 0.10),
                         M["stone_mid"], rot=(0, 0, rz)), 0.004)
        for (px, py) in ((2.56, 3.30), (-1.96, 3.44), (-3.16, -1.10)):
            self.grass((px, py))

    # ── 共用小件 ────────────────────────────────────────────────────────────
    def grass(self, p, h=0.24):
        """草簇：三片薄草叶各向外倾 12°、高低差 2 cm（同高会在叶心闪）。

        br_model.tuft 里的落地高度写死成兵营的 G_Z = 0.40，哨塔场地是 0.16，
        直接复用会让草悬在半空，所以在本地重写一份。
        """
        M = self.M
        x, y = p
        for k in range(3):
            a = math.radians(18 + k * 60)
            hh = h * (0.84 + 0.11 * k)
            self.add(box("tuft_", (x + 0.02 * math.cos(a + 1.1),
                                   y + 0.02 * math.sin(a + 1.1),
                                   G_Z + hh * 0.46), (0.12, 0.02, hh), M["moss"],
                         rot=(0.20 * math.cos(a), 0.20 * math.sin(a), a)), 0.0)

    def window(self, name, u, cz, w, h, axis="Y", out=1, wall=0.0, wood=False):
        """木构窗：木框 + 内凹玻璃 + 中梃（贴片做法，不真开洞 —— 木塔是板墙）。"""
        M = self.M
        hw = w * 0.5
        fr = M["wood_dark"]
        if axis == "Y":
            y0 = wall
            self.add(box(name + "_glass", (u, y0 + out * 0.010, cz + h * 0.5),
                         (w, 0.06, h), M["glass"]), 0.0)
            for sgn in (-1, 1):
                self.add(box(name + "_jamb", (u + sgn * (hw + 0.065),
                                              y0 + out * 0.040, cz + h * 0.5),
                             (0.13, 0.11, h + 0.16), fr), 0.004)
            self.add(box(name + "_head", (u, y0 + out * 0.040, cz + h + 0.07),
                         (w + 0.26, 0.11, 0.14), fr), 0.004)
            self.add(box(name + "_sill", (u, y0 + out * 0.050, cz - 0.055),
                         (w + 0.34, 0.13, 0.11), fr), 0.004)
            self.add(box(name + "_mull", (u, y0 + out * 0.025, cz + h * 0.5),
                         (0.055, 0.045, h - 0.03), fr), 0.002)
        else:
            x0 = wall
            self.add(box(name + "_glass", (x0 + out * 0.010, u, cz + h * 0.5),
                         (0.06, w, h), M["glass"]), 0.0)
            for sgn in (-1, 1):
                self.add(box(name + "_jamb", (x0 + out * 0.040, u + sgn * (hw + 0.065),
                                              cz + h * 0.5),
                             (0.11, 0.13, h + 0.16), fr), 0.004)
            self.add(box(name + "_head", (x0 + out * 0.040, u, cz + h + 0.07),
                         (0.11, w + 0.26, 0.14), fr), 0.004)
            self.add(box(name + "_sill", (x0 + out * 0.050, u, cz - 0.055),
                         (0.13, w + 0.34, 0.11), fr), 0.004)
            self.add(box(name + "_mull", (x0 + out * 0.025, u, cz + h * 0.5),
                         (0.045, 0.055, h - 0.03), fr), 0.002)

    def parapet(self, name, a0, a1, axis, c, z0, h=1.00, team=True, lift=0.0):
        """一段栏板：下横档 + 中部实板（分段阵营色嵌板）+ 空档 + 扶手 + 立柱。

        axis = "X" 时沿 X 展开、c 是 y；axis = "Y" 时沿 Y 展开、c 是 x。
        阵营色不做通长条 —— 每两根立柱之间嵌一块，读作"嵌板"，
        通长的话整圈栏板会变成一道蓝围栏，把木色吃掉。
        """
        M = self.M
        ln = abs(a1 - a0)
        th = 0.14
        n = max(2, int(round(ln / 1.30)))

        def seg(tag, u0, u1, dz, hh, thick, mat, bev=0.005):
            if abs(u1 - u0) < 0.04:
                return
            m = (u0 + u1) * 0.5
            L = abs(u1 - u0)
            if axis == "X":
                self.add(box(name + tag, (m, c, z0 + dz), (L, thick, hh), mat), bev)
            else:
                self.add(box(name + tag, (c, m, z0 + dz), (thick, L, hh), mat), bev)

        # 下横档
        seg("_kick", a0, a1, 0.075 + lift, 0.15, th + 0.02, M["wood_dark"])
        # 中部实板（板面比立柱凹 10 mm）
        seg("_board", a0, a1, 0.36 + lift, 0.44, th - 0.02, M["wood_mid"])
        # 扶手
        seg("_rail", a0, a1, 0.94 + lift, 0.12, th + 0.05, M["wood_dark"])
        # 阵营色嵌板：每格一块，两端留 0.20 木色（team=False 的段留纯木）
        for i in range(n if team else 0):
            u0 = a0 + (a1 - a0) * i / n + 0.14
            u1 = a0 + (a1 - a0) * (i + 1) / n - 0.14
            seg("_band", u0, u1, 0.37 + lift, 0.19, th + 0.03, M["team"], 0.004)
        # 立柱：比扶手高 60 mm（柱头露在扶手之上，也是防同高共面的那 6 cm）
        hh = h + 0.06 + lift
        for i in range(n + 1):
            p = a0 + (a1 - a0) * i / n
            if axis == "X":
                self.add(box(name + "_post", (p, c, z0 + hh * 0.5),
                             (0.13, th + 0.04, hh), M["wood_dark"]), 0.005)
            else:
                self.add(box(name + "_post", (c, p, z0 + hh * 0.5),
                             (th + 0.04, 0.13, hh), M["wood_dark"]), 0.005)

    def fence(self, name, p0, p1, h=1.08, skip_first=False, lift=0.0):
        """板式木栅栏：竖板 + 两道横杆 + 立柱 + 四棱锥帽。"""
        M = self.M
        x0, y0 = p0
        x1, y1 = p1
        ln = math.hypot(x1 - x0, y1 - y0)
        dx = (x1 - x0) / max(ln, 1e-6)
        dy = (y1 - y0) / max(ln, 1e-6)
        n = max(2, int(ln / 0.60))
        for i in range(n + 1):
            if skip_first and i == 0:
                continue
            t = i / n
            px, py = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
            sx = 0.22 * abs(dy) + 0.07 * abs(dx)
            sy = 0.22 * abs(dx) + 0.07 * abs(dy)
            self.add(box(name + "_plank", (px, py, G_Z + h * 0.5), (sx, sy, h),
                         M["wood_warm"]), 0.005)
        for zz in (0.34 + lift, 0.86 + lift):
            self.add(box(name + "_rail", ((x0 + x1) * 0.5, (y0 + y1) * 0.5, G_Z + zz),
                         (abs(x1 - x0) + 0.10, abs(y1 - y0) + 0.10, 0.13),
                         M["wood_dark"]), 0.005)
        m = max(1, int(ln / 2.40))
        for i in range(m + 1):
            if skip_first and i == 0:
                continue
            t = i / m
            px, py = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
            self.add(box(name + "_post", (px, py, G_Z + h * 0.56), (0.20, 0.20, h * 1.12),
                         M["wood_dark"]), 0.007)
            self.add(cone(name + "_cap", (px, py, G_Z + h * 1.12),
                          (px, py, G_Z + h * 1.12 + 0.18), 0.15, 4, M["wood_dark"]), 0.0, 1)

    def brazier(self, name, p):
        """石座 + 铁盆 + 炭 + 火焰（哨塔唯一的光源，也是俯视角的暖色点）。"""
        M = self.M
        x, y, z0 = p
        self.add(box(name + "base", (x, y, z0 + 0.17), (0.52, 0.52, 0.34), M["stone_mid"]), 0.010)
        self.add(box(name + "base2", (x, y, z0 + 0.39), (0.62, 0.62, 0.10), M["stone_light"]), 0.006)
        self.add(revolve(name + "bowl", [(0.12, 0.0), (0.36, 0.07), (0.40, 0.18),
                                         (0.36, 0.22), (0.12, 0.22)], 8,
                         (x, y, z0 + 0.43), M["iron"]), 0.0, 1)
        for i in range(4):
            a = math.tau * i / 4 + 0.4
            self.add(box(name + "leg", (x + 0.28 * math.cos(a), y + 0.28 * math.sin(a),
                                        z0 + 0.34), (0.08, 0.08, 0.32), M["iron"]), 0.003)
        self.add(revolve(name + "coal", [(0.0, 0.0), (0.28, 0.02), (0.23, 0.10),
                                         (0.0, 0.13)], 8, (x, y, z0 + 0.56), M["coal"]), 0.0, 1)
        self.add(revolve(name + "flame", [(0.0, 0.0), (0.26, 0.08), (0.20, 0.32),
                                          (0.09, 0.62), (0.0, 0.82)], 8,
                         (x, y, z0 + 0.62), M["ember"]), 0.0, 1)
        self.add(revolve(name + "flame_c", [(0.0, 0.0), (0.15, 0.06), (0.10, 0.30),
                                            (0.0, 0.54)], 8, (x, y, z0 + 0.64),
                         M["flame_in"]), 0.0, 1)

    def quiver(self, name, p, sx=1):
        """挂在栏板内侧的箭袋：皮筒 + 三支箭（箭羽露在外面）。"""
        M = self.M
        x, y, z0 = p
        self.add(revolve(name + "tube", [(0.0, 0.0), (0.13, 0.02), (0.14, 0.10),
                                         (0.12, 0.52), (0.0, 0.52)], 8,
                         (x, y, z0 + 0.02), M["wood_warm"]), 0.0, 1)
        for k in (-1, 0, 1):
            self.add(box(name + "shaft", (x + k * 0.055, y + k * 0.02, z0 + 0.66),
                         (0.03, 0.03, 0.30), M["wood_dark"]), 0.002)
            self.add(box(name + "fletch", (x + k * 0.055, y + k * 0.02, z0 + 0.80),
                         (0.05, 0.10, 0.10), M["team_trim"]), 0.002)

    # ── 11. 组装 / 收尾 ─────────────────────────────────────────────────────
    def build(self):
        for step in (self.plinth, self.stone_base, self.wood_low, self.ladder,
                     self.deck_mid, self.wood_up, self.deck_top, self.canopy,
                     self.flag, self.yard):
            step()
        return self

    def finalize(self, bevel=True):
        # 细分只磨"小体量件"（斜撑、斗拱、火盆、桶）。
        # 石基 / 木墙 / 平台板 / 屋面板是**大平面**：CC 会把它们的棱磨成一圈渐变的圆，
        # 这正是"塑料感"的来源，也和这套资产的硬边语言冲突（对照城镇大厅 v3 主图）。
        skip_cc = ("tile_", "ridge_", "flag_", "ldr_", "fence_", "pebble_", "tuft_",
                   "win", "p1_", "p2_", "gab_", "crest_", "gate_", "slot_",
                   "quoin", "sb_", "step_", "yard_curb", "plinth",
                   "w1_", "w2_", "col1_", "col2_", "rail1_", "rail2_",
                   "d1_", "d2_", "cp_roof", "cp_fascia", "cp_drip", "cp_seam",
                   "cp_rafter", "cp_beam", "cp_col", "ridge_",
                   "quiver_", "braz_", "barrel_", "pile_")
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
        out = L.join_by_material(objs, prefix="WT")
        mirror_x(out)
        if self.unwrap:
            L.smart_uv(out)
        return out


def build(smooth=True, unwrap=True, bevel=True):
    m = Model(smooth, unwrap).build()
    objs = m.finalize(bevel=bevel)
    return objs, L.stats(objs)
