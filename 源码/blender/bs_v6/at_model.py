"""
at_model.py —— 箭塔（Arrow Spire）v2：收分石塔 · 挑出战棚 · **整顶攒尖亭** · 剪影箭

**第九座独立资产，不是哨塔的替换**：`wt_model.py` 一个字都没改。
箭塔是哨塔的升级型，共用同一套语言（石基真拱门、隅石、木构外露、燕尾窗、
三档木色、同一套明度秩序），但形体语言换了一整套，三秒内必须能分出是哪一座：

  哨塔 = 往上"叠"：石基 → 木塔下段 → 挑台 → 木塔上段 → 挑台 → 双坡瞭望棚
  箭塔 = 往上"收"：石基 → **收分塔身（两级退台 + 石线脚 + 隅石）** →
        **一圈挑出的木战棚** → **整顶攒尖亭（8 柱 · 环绕栏板 · 单段四面坡）** →
        **剪影箭（铁箭身 + 蓝羽 + 金束，尖 17.46）**

v2 相对 v1 的三处硬改动（用户明确要求）：
  ① 攒尖顶从"后右角的小亭"升级成**整个塔顶**——屋面 5.40 见方、几乎与栏板齐平，
     盖住整个顶面，顶层是一座通体敞开的亭；
  ② **弩炮整组删除**（连同底座 / 绞盘 / 弩床 / 石弹 / 备用弩矢），平台上不再摆
     任何"展示道具"；
  ③ "箭"不再靠弩炮表达，而是**做进攒尖顶的外形**：单段四面坡在宝顶收束，往上
     长出一支剪影箭。四片绕轴的羽从任何水平方向看都会合成对称梭形（做过三方案
     对照），所以箭是**两片互成 90° 的箭形板**，转到 45° / 135° 对齐两条戗脊。

明度秩序（与前八座同一套节拍）：
  夯土场地 → 中灰台基 → **亮**压顶 → **中**石墙 → **亮**石线脚 / 退台 / 隅石 →
  **暗**木战棚 / 斜撑 → **中**木栏板 → **近黑**亭顶 → 铁 / 金 / 队色点睛。

队色只染四条"结构线"：门扇下板 + 门楣横匾（低）、战棚封檐板（中，冠部最宽的一圈）、
檐口漆线（高，水平面）、箭羽（顶）；另在亭内挂两面燕尾旗补中段色。
**扶手走深木** —— 三道蓝横箍连排会读成包装带，两道 + 中间一层空的暗部才对。

坐标：X 右、Y 前（+Y = 正面）、Z 上；原点在占地中心，z = 0 地面。
交付前整体沿 X 镜像一次（与前八座一致）→ 相机看到的近侧是**建模期 +X**。
"""
import math

import bpy
from mathutils import Vector

import bslib as L
import br_model as BR
import wt_model as WT
from bslib import (arch_band, beam, box, cone, extrude, mesh_obj, revolve,
                   ring_y, tube_band)
from br_model import mirror_x
from wt_model import frame_ring

# ── 场地 ────────────────────────────────────────────────────────────────────
YARD_X, YARD_Y0, YARD_Y1 = 3.54, -3.30, 3.54
G_Z = 0.16                       # 夯土面
PLX = 2.80                       # 台基下层半宽

# ── 石基（4.76 × 4.76，0.42 → 3.90）────────────────────────────────────────
SBX = 2.38
SB0, SB1 = 0.42, 3.90
DW = 0.32                        # 前墙厚（门洞真实深度）
GW = 0.62                        # 门洞半宽 1.24
SPRING = 2.18
ARCH = SPRING + GW               # 2.80

# ── 收分塔身：两级（4.28 → 3.80）───────────────────────────────────────────
S1X, S1A, S1B = 2.14, 3.90, 6.25
S2X, S2A, S2B = 1.90, 6.25, 8.85
LINE0, LINE1 = 5.12, 5.26        # 下段石线脚

# ── 冠部：石挑檐 + 木战棚 ───────────────────────────────────────────────────
LEDGE0, LEDGE1, LEDGEX = 8.85, 9.09, 2.06
DECK0, DECK1, DECKX = 9.35, 9.79, 2.86
FLOOR0, FLOOR1 = 9.79, 9.83      # 亭内木地板（比平台板亮一档）
FAS0, FAS1, FASX = 9.38, 9.58, 2.92      # 封檐板（队色细线）
DECK = FLOOR1                             # 可站立面

# ── 环绕栏板（整顶亭的护身，不是垛口）──────────────────────────────────────
RB0, RB1, RBX = 9.83, 10.03, 2.80        # 下横档
RP0, RP1, RPX = 10.03, 10.53, 2.76       # 中部实板（与下横档基本齐平）
RC0, RC1, RCX = 10.53, 10.65, 2.84       # 扶手（**队色**细线）

# ── 亭柱 / 檐梁 ────────────────────────────────────────────────────────────
POST_C = 2.54
POST_W = 0.28                            # 角柱
POST_W2 = 0.22                           # 中柱
POST0, POST1 = 9.83, 11.65
HEAD0, HEAD1, HEADX = 11.41, 11.67, 2.60

# ── 攒尖顶：单段四面坡（檐口 5.20 → 宝顶 14.90，48°）──────────────────────
EF0, EF1, EFX = 11.65, 11.97, 2.76       # 檐口封板（暖木）
EX0, EX1, EXX = 11.825, 11.975, 2.775    # 檐口压线（队色，漆在封板外立面上）
ROOF_X = 2.70                            # 屋面底边半宽
ROOF0 = 12.01
ROOF1 = 14.60                            # 宝顶尖

# ── 箭羽冠 ──────────────────────────────────────────────────────────────────
ARW_TIP = 17.46                          # 箭尖

# ── 门 ──────────────────────────────────────────────────────────────────────
DZ0, DZ1 = 0.56, SPRING - 0.10


# ── 屋面 / 箭羽 构造 ────────────────────────────────────────────────────────
def pyramid(name, cx, cy, half, z0, z1, mat):
    """四面坡攒尖顶的实体（底面封闭）：四条戗脊 + 一个宝顶。"""
    verts = [(cx - half, cy - half, z0), (cx + half, cy - half, z0),
             (cx + half, cy + half, z0), (cx - half, cy + half, z0),
             (cx, cy, z1)]
    faces = [(0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4), (0, 3, 2, 1)]
    return mesh_obj(name, verts, faces, mat)


def vane(name, a_deg, prof, thick, mat, swirl=0.0):
    """箭羽：立在"过轴心、方位角 a"的竖直平面里的一块有厚度薄板。

    prof = [(r, z), ...] 从箭杆侧起描一圈。内缘给到 r=0.02，埋进箭杆里 ——
    这样它和箭杆是真相交，不会判 FLOAT。
    """
    n = len(prof)
    verts = []
    for s in (-0.5, 0.5):
        for (r, z) in prof:
            # 螺旋：半径越大，方位角越滞后 —— 羽尖"甩"在后面，剪影不对称才像羽毛
            a = math.radians(a_deg) + swirl * r
            ex, ey = math.cos(a), math.sin(a)
            tx, ty = -math.sin(a), math.cos(a)
            verts.append((ex * r + tx * thick * s, ey * r + ty * thick * s, z))
    faces = [tuple(range(n)), tuple(range(n, 2 * n))]
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, n + j, n + i))
    return mesh_obj(name, verts, faces, mat)


def disc_y(name, r, thick, segs, mat, phase=0.0):
    """面向 ±Y 的圆盘（局部坐标，圆心在原点）—— 箭靶的靶面。"""
    half = thick * 0.5
    verts, faces = [], []
    for s in range(segs):
        a = phase + math.tau * s / segs
        ca, sa = math.cos(a) * r, math.sin(a) * r
        verts.append((ca, -half, sa))
        verts.append((ca, half, sa))
    for s in range(segs):
        b, b2 = s * 2, ((s + 1) % segs) * 2
        faces.append((b, b2, b2 + 1, b + 1))
    faces.append(tuple(range(0, segs * 2, 2)))
    faces.append(tuple(range(1, segs * 2 + 1, 2)))
    return mesh_obj(name, verts, faces, mat)


def band_ring_gap(name, x0, x1, y0, y1, z0, z1, t, mat, gap):
    """矩形环，但正面的中间留出 |x| < gap 的缺口（门洞 / 拱）。

    frame_ring 会在正立面拉一条通长的横带 —— 石基的墙裙 / 腰线用它就会
    **横穿门扇**（门的下半截被一条 0.16 厚的石带糊住）。这里把正面拆成左右两段。
    """
    out = []
    out.append(box(name + "_b", ((x0 + x1) * 0.5, y0 + t * 0.5, (z0 + z1) * 0.5),
                   (x1 - x0, t, z1 - z0), mat))
    for sgn, tag in ((1, "_r"), (-1, "_l")):
        xa, xb = (x1 - t, x1) if sgn > 0 else (x0, x0 + t)
        out.append(box(name + tag, ((xa + xb) * 0.5, (y0 + t + y1) * 0.5, (z0 + z1) * 0.5),
                       (t, y1 - y0 - t, z1 - z0), mat))
    for sgn, tag in ((1, "_fr"), (-1, "_fl")):
        if sgn > 0:
            xa, xb = gap, x1 - t
        else:
            xa, xb = x0 + t, -gap
        out.append(box(name + tag, ((xa + xb) * 0.5, y1 - t * 0.5, (z0 + z1) * 0.5),
                       (xb - xa, t, z1 - z0), mat))
    return out


class Model(WT.Model):
    """继承哨塔的箭袋 / 草簇，只换体量与顶层。"""

    # ── 1. 场地 / 台基 / 踏步 ───────────────────────────────────────────────
    def plinth(self):
        M = self.M
        cy = (YARD_Y0 + YARD_Y1) * 0.5
        dy = YARD_Y1 - YARD_Y0
        self.add(box("yard_soil", (0, cy, G_Z * 0.5), (YARD_X * 2, dy, G_Z),
                     M["earth"]), 0.020)
        for sgn in (-1, 1):
            self.add(box("yard_curb", (sgn * (YARD_X - 0.09), cy - 0.18, G_Z + 0.04),
                         (0.18, dy - 0.36, 0.10), M["paving"]), 0.006)
        self.add(box("yard_curb_b", (0, YARD_Y0 + 0.09, G_Z + 0.04),
                     (YARD_X * 2 - 0.36, 0.18, 0.10), M["paving"]), 0.006)
        # 台基两级（上层比下层小 0.18）
        self.add(box("plinth_lo", (0, 0, 0.10), (PLX * 2, PLX * 2, 0.20),
                     M["stone_mid"]), 0.018)
        self.add(box("plinth_hi", (0, 0, 0.31), ((PLX - 0.18) * 2, (PLX - 0.18) * 2, 0.22),
                     M["stone_light"]), 0.020)
        # 两级踏步
        for i, (y0, y1, zt) in enumerate(((2.54, 3.02, 0.22), (2.20, 2.56, 0.34))):
            self.add(box("step%d" % i, (0, (y0 + y1) * 0.5, (G_Z + zt) * 0.5),
                         (2.38, y1 - y0, zt - G_Z), M["stone_mid"]), 0.010)

    # ── 2. 石基：真拱门 + 扶壁 + 线脚 ───────────────────────────────────────
    def stone_base(self):
        M = self.M
        hz = (SB0 + SB1) * 0.5
        self.add(box("sb_core", (0, (-SBX + (SBX - DW)) * 0.5, hz),
                     (SBX * 2, SBX * 2 - DW, SB1 - SB0), M["stone_mid"]), 0.034)
        for sgn in (-1, 1):
            x0, x1 = sgn * GW, sgn * SBX
            self.add(box("sb_front_%s" % ("R" if sgn > 0 else "L"),
                         ((x0 + x1) * 0.5, SBX - DW * 0.5, hz),
                         (abs(x1 - x0), DW, SB1 - SB0), M["stone_mid"]), 0.028)
        # 拱上墙：轮廓必须从**拱脚**起算（不是拱顶），否则拱肩两侧各留一个
        # 0.6 × 0.6 的三角洞，从正面能看进门厅。
        top = []
        for s in range(11):
            a = math.pi * (1.0 - s / 10.0)
            top.append((GW * math.cos(a), SPRING + GW * math.sin(a)))
        top += [(GW, SB1), (-GW, SB1)]
        self.add(extrude("sb_front_T", top, "Y", DW, (0, 0), M["stone_mid"],
                         offset=SBX - DW * 0.5), 0.026)
        # 墙裙 + 一道线脚（两条正好；三条会读成"三层蛋糕"）
        for ob in band_ring_gap("sb_dado", -SBX - 0.05, SBX + 0.05,
                                -SBX - 0.05, SBX + 0.05, SB0, 1.00, 0.16,
                                M["stone_light"], 0.90):
            self.add(ob, 0.010)
        for ob in band_ring_gap("sb_line0", -SBX - 0.05, SBX + 0.05,
                                -SBX - 0.05, SBX + 0.05, 2.12, 2.22, 0.15,
                                M["stone_light"], 0.90):
            self.add(ob, 0.008)
        # 四角扶壁：凸出墙面 0.16，两级（下粗上细），顶上压一块收分石帽
        BW = 0.52
        for sx in (-1, 1):
            for sy in (-1, 1):
                bx, by = sx * (SBX - BW * 0.5 + 0.16), sy * (SBX - BW * 0.5 + 0.16)
                self.add(box("bt_shaft", (bx, by, (SB0 + SB1 - 0.08) * 0.5),
                             (BW, BW, SB1 - SB0 - 0.08),
                             M["stone_mid"]), 0.010)
                self.add(box("bt_foot", (bx, by, SB0 + 0.20), (BW + 0.14, BW + 0.14, 0.40),
                             M["stone_mid"]), 0.008)
                self.add(box("bt_step", (bx, by, 2.22), (BW + 0.08, BW + 0.08, 0.14),
                             M["stone_light"]), 0.006)
                self.add(box("bt_cap", (bx, by, SB1 - 0.12), (BW + 0.14, BW + 0.14, 0.32),
                             M["stone_mid"]), 0.008)
        # 压顶（石基顶，宽出 0.12）
        self.add(box("sb_cap", (0, 0, SB1 + 0.09),
                     ((SBX + 0.12) * 2, (SBX + 0.12) * 2, 0.18), M["stone_mid"]), 0.016)
        # ── 门：真开洞 + 关着的双扇 ────────────────────────────────────────
        # 门洞是半圆拱：门扇做到拱脚，上面用一块木鼓（tympanum）补齐，
        # 这样门扇的方角不会戳进拱石里（戳进去就是 CLIP_CROSS）。
        # 深度分层（m）：门板 / 竖板 / 铁箍 / 中缝压条 / 队色下板 / 门环
        for sgn in (-1, 1):
            tag = "l" if sgn < 0 else "r"
            self.add(box("gate_leaf_" + tag, (sgn * GW * 0.5, SBX - 0.245,
                                              (DZ0 + DZ1) * 0.5),
                         (GW - 0.02, 0.09, DZ1 - DZ0), M["wood_mid"]), 0.008)
            for k in (-2, -1, 0, 1, 2):
                self.add(box("gate_plank", (sgn * (GW * 0.5 + k * 0.12),
                                            SBX - 0.195, (DZ0 + DZ1) * 0.5),
                             (0.065, 0.02, DZ1 - DZ0 - 0.10), M["wood_dark"]), 0.001)
        for zz in (1.00, 1.88):
            self.add(box("gate_band", (0, SBX - 0.170, zz), (GW * 2 - 0.06, 0.03, 0.10),
                         M["iron"]), 0.003)
        self.add(box("gate_team", (0, SBX - 0.170, 0.80), (GW * 2 - 0.06, 0.03, 0.46),
                     M["team"]), 0.004)
        self.add(box("gate_seam", (0, SBX - 0.180, (DZ0 + DZ1) * 0.5 + 0.02),
                     (0.11, 0.028, DZ1 - DZ0 - 0.10), M["wood_warm"]), 0.002)
        self.add(ring_y("gate_ring", (0.26, SBX - 0.192, 1.40), 0.054, 0.094, 0.032, 8,
                        M["iron"]), 0.002)
        # 门楣木梁
        self.add(box("gate_head", (0, SBX - 0.150, SPRING - 0.06),
                     (GW * 2 + 0.06, 0.20, 0.16), M["wood_dark"]), 0.006)
        # 拱内填石（不是木鼓）：拱读成"实心石拱 + 一扇方门"，门楣以上是墙。
        # 木鼓会让门洞里塞着一块木头，和门楣梁糊成一片。
        RT = GW - 0.015
        tym = [(-RT, DZ1)]
        for s in range(11):
            a = math.pi * (1.0 - s / 10.0)
            tym.append((RT * math.cos(a), SPRING + RT * math.sin(a)))
        tym += [(RT, DZ1)]
        self.add(extrude("gate_tymp", tym, "Y", 0.10, (0, 0), M["stone_mid"],
                         offset=SBX - 0.210), 0.006)
        # 拱心石：把石拱在视觉上"咬合"住
        self.add(box("gate_key", (0, SBX + 0.045, SPRING + GW - 0.06),
                     (0.22, 0.17, 0.36), M["stone_light"]), 0.006)
        # 门槛 + 拱券 + 门柱 + 队色壁柱 + 门楣横匾
        self.add(box("gate_thresh", (0, SBX - 0.12, 0.49), (1.80, 0.58, 0.14),
                     M["stone_dark"]), 0.006)
        self.add(arch_band("gate_arch", 0.0, SPRING, GW, GW + 0.20, SBX + 0.005,
                           SBX + 0.10, M["stone_light"], segs=8), 0.010)
        for sgn in (-1, 1):
            self.add(box("gate_jamb", (sgn * (GW + 0.10), SBX + 0.052,
                                       SPRING * 0.5 + 0.28),
                         (0.20, 0.12, SPRING - 0.30), M["stone_light"]), 0.008)
        self.add(box("gate_plaque", (0, SBX + 0.040, 3.10), (1.94, 0.10, 0.30),
                     M["team"]), 0.006)
        self.add(box("gate_plaque_t", (0, SBX + 0.050, 3.28), (1.94, 0.11, 0.06),
                     M["team_trim"]), 0.004)
        # 门套木框：两根立柱 + 一道过梁。石塔正面 3/4 是灰的，门这一圈要给暖木，
        # 否则整座在画面里"发白"（与哨塔并排对比时最明显）。
        for sgn in (-1, 1):
            self.add(box("gate_post", (sgn * 1.24, SBX + 0.075, 1.96),
                         (0.28, 0.15, 2.96), M["wood_dark"]), 0.008)
            self.add(box("gate_post_cap", (sgn * 1.24, SBX + 0.075, 3.50),
                         (0.36, 0.20, 0.12), M["wood_dark"]), 0.005)
        self.add(box("gate_lintel", (0, SBX + 0.075, 3.60), (2.76, 0.20, 0.20),
                     M["wood_dark"]), 0.008)
        for sx in (-1, 1):
            for sz in (-1, 1):
                self.add(box("gate_plaque_bolt", (sx * 0.86, SBX + 0.095, 3.10 + sz * 0.10),
                             (0.07, 0.03, 0.07), M["iron"]), 0.0)
        # ── 箭孔：底层三面各两个（正面是门，不开孔）───────────────────────
        for (axis, u, out) in (("X", SBX, 1), ("X", -SBX, -1), ("Y", -SBX, -1)):
            for v in (-1.16, 1.16):
                self.slit("slot_b", axis, u, v, 2.70, out, 0.78)

    # ── 3. 收分塔身（两级退台 + 隅石 + 箭孔）────────────────────────────────
    def shaft(self):
        M = self.M
        # 下段
        self.add(box("s1_wall", (0, 0, (S1A + S1B) * 0.5),
                     (S1X * 2, S1X * 2, S1B - S1A), M["stone_mid"]), 0.030)
        # 石线脚：把 2.4 m 的空白石墙分成两段（没有这条就是一块灰板）
        self.add(frame_ring("s1_line", -S1X - 0.07, S1X + 0.07,
                            -S1X - 0.07, S1X + 0.07, LINE0, LINE1, 0.16,
                            M["stone_light"]), 0.008)
        # 下段四角壁柱：只在角上做一道竖线，正面才不会是一整块灰墙
        for sx in (-1, 1):
            for sy in (-1, 1):
                self.add(box("s1_pil", (sx * (S1X - 0.11), sy * (S1X - 0.11),
                                        (S1A + S1B) * 0.5 - 0.01),
                             (0.26, 0.26, S1B - S1A - 0.08), M["stone_light"]), 0.008)
        # 退台：一圈向上收的实体，两级墙不能悬空对接
        self.add(box("s1_step", (0, 0, S1B + 0.06), (S1X * 2 + 0.10, S1X * 2 + 0.10, 0.12),
                     M["stone_light"]), 0.010)
        # 上段
        self.add(box("s2_wall", (0, 0, (S2A + S2B) * 0.5),
                     (S2X * 2, S2X * 2, S2B - S2A), M["stone_mid"]), 0.030)
        # 隅石：四角交替长短块（这套石构的"手工感"来源，比通长壁柱耐看）
        for sx in (-1, 1):
            for sy in (-1, 1):
                for i in range(4):
                    z = 6.47 + i * 0.56
                    long_x = (i % 2 == 0)
                    w = (0.44, 0.24) if long_x else (0.24, 0.44)
                    self.add(box("q_stone", (sx * (S2X - w[0] * 0.5 + 0.045),
                                             sy * (S2X - w[1] * 0.5 + 0.045), z),
                                 (w[0] + 0.09, w[1] + 0.09, 0.40),
                                 M["stone_light"]), 0.006)
        # 箭孔：下段四面各一（错开高度），上段正面十字孔 + 三面竖孔
        for (axis, u, out, v) in (("X", S1X, 1, 0.58), ("X", -S1X, -1, -0.58),
                                  ("Y", S1X, 1, -0.58), ("Y", -S1X, -1, 0.58)):
            self.slit("slot_1", axis, u, v, 4.86, out, 0.90)
        self.slit("slot_2", "Y", S2X, 0.0, 7.58, 1, 0.90, cross=True)
        for (axis, u, out) in (("X", S2X, 1), ("X", -S2X, -1), ("Y", -S2X, -1)):
            self.slit("slot_2", axis, u, 0.0, 7.64, out, 0.84)

    # ── 4. 石挑檐 + 木战棚（挑出的一圈防守位）───────────────────────────────
    def gallery(self):
        M = self.M
        # 石挑檐：一圈 0.16 的挑出（塔身 3.80 → 4.12），托住木地板
        self.add(frame_ring("led_ring", -LEDGEX, LEDGEX, -LEDGEX, LEDGEX,
                            LEDGE0, LEDGE1, 0.30, M["stone_light"]), 0.008)
        # 地板（顶面 = 平台面）
        self.add(box("deck_plate", (0, 0, (DECK0 + DECK1) * 0.5),
                     (DECKX * 2, DECKX * 2, DECK1 - DECK0), M["wood_mid"]), 0.018)
        # 亭内木地板：亮一档的条形板（缝里露出下面那块中棕，读作"铺板"）
        for i in range(5):
            self.add(box("deck_plank", (0, -2.08 + i * 1.04, (FLOOR0 + FLOOR1) * 0.5),
                         (5.40, 0.94, FLOOR1 - FLOOR0), M["sand"]), 0.004)
        # 封檐板：包住地板断面，外沿比地板宽 60 mm；深木（队色留给扶手与檐口）
        self.add(frame_ring("deck_fascia", -FASX, FASX, -FASX, FASX,
                            FAS0, FAS1, 0.16, M["team"]), 0.005)
        # 12 根斜撑：从塔身上段斜到地板底，撑出挑出的 0.82
        for sgn in (-1, 1):
            for u in (-1.34, 0.0, 1.34):
                self.add(beam("bkt_", (sgn * (S2X - 0.02), u, 8.58),
                              (sgn * (DECKX - 0.20), u, DECK0 - 0.02),
                              0.22, 0.19, M["wood_warm"]), 0.005)
                self.add(beam("bkt_", (u, sgn * (S2X - 0.02), 8.58),
                              (u, sgn * (DECKX - 0.20), DECK0 - 0.02),
                              0.22, 0.19, M["wood_warm"]), 0.005)

    # ── 5. 整顶亭的下部：环绕栏板 + 8 根亭柱 + 檐梁 ─────────────────────────
    def pavilion(self):
        M = self.M
        # 下横档：把地板边缘收一道深木，板面才不是"一块空棕板"
        self.add(frame_ring("rail_base", -RBX, RBX, -RBX, RBX, RB0, RB1, 0.18,
                            M["wood_dark"]), 0.006)
        # 中部实板
        self.add(frame_ring("rail_panel", -RPX, RPX, -RPX, RPX, RP0, RP1, 0.10,
                            M["wood_warm"]), 0.008)
        # 扶手：**队色**，水平面 —— 俯视角里唯一一圈完整的中层色
        self.add(frame_ring("rail_cap", -RCX, RCX, -RCX, RCX, RC0, RC1, 0.14,
                            M["wood_dark"]), 0.005)
        # 8 根亭柱：柱顶直接顶到檐口封板底面（柱在上、板在下，接口不藏在阴影里）
        for (px, py) in ((POST_C, POST_C), (-POST_C, POST_C),
                         (-POST_C, -POST_C), (POST_C, -POST_C)):
            self.add(box("post_corner", (px, py, (POST0 + POST1) * 0.5),
                         (POST_W, POST_W, POST1 - POST0), M["wood_dark"]), 0.008)
        for (px, py) in ((0.0, POST_C), (0.0, -POST_C),
                         (POST_C, 0.0), (-POST_C, 0.0)):
            self.add(box("post_mid", (px, py, (POST0 + POST1) * 0.5),
                         (POST_W2, POST_W2, POST1 - POST0), M["wood_dark"]), 0.006)
        # 檐梁：柱顶一圈（亭子的"额枋"），顶面直接托住檐口封板
        self.add(frame_ring("head_beam", -HEADX, HEADX, -HEADX, HEADX,
                            HEAD0, HEAD1, 0.22, M["wood_dark"]), 0.008)
        # 柱头小斗：柱和梁的交接才不是"插进去"
        for (px, py) in ((POST_C, POST_C), (-POST_C, POST_C),
                         (-POST_C, -POST_C), (POST_C, -POST_C)):
            self.add(box("post_cap", (px, py, HEAD0 - 0.06), (0.34, 0.34, 0.12),
                         M["wood_dark"]), 0.004)
        for (px, py) in ((0.0, POST_C), (0.0, -POST_C),
                         (POST_C, 0.0), (-POST_C, 0.0)):
            self.add(box("post_cap", (px, py, HEAD0 - 0.05), (0.28, 0.28, 0.10),
                         M["wood_dark"]), 0.004)

    # ── 6. 攒尖顶（覆盖满整个顶面）+ 顶棚 ───────────────────────────────────
    def roof(self):
        M = self.M
        # 檐口封板：近黑，包住屋面断口；外沿比屋面宽 0.06
        self.add(frame_ring("eave_fascia", -EFX, EFX, -EFX, EFX, EF0, EF1, 0.18,
                            M["wood_dark"]), 0.006)
        # 檐口压线：**队色**、薄薄一条水平面（厚了就变成蓝塑料边）
        self.add(frame_ring("eave_flash", -EXX, EXX, -EXX, EXX, EX0, EX1, 0.10,
                            M["team"]), 0.001)
        # 屋面：单段四面坡攒尖（实体、底边 5.20、48°）
        self.add(pyramid("spire_shell", 0, 0, ROOF_X, ROOF0, ROOF1, M["roof"]), 0.010)
        # 四条戗脊：起点收进 0.22、压在屋面上 —— 起在檐口外沿会伸出一截悬空的尖
        for sx in (-1, 1):
            for sy in (-1, 1):
                self.add(beam("spire_hip",
                              (sx * (ROOF_X - 0.22), sy * (ROOF_X - 0.22), ROOF0 + 0.10),
                              (0, 0, ROOF1 + 0.01),
                              0.09, 0.09, M["roof_pale"]), 0.003)
        # 宝顶座：四条戗脊交汇处的一块方斗，箭杆从这里长出去
        self.add(box("spire_boss", (0, 0, ROOF1 - 0.03), (0.34, 0.34, 0.20),
                     M["roof_edge"]), 0.006)
        # 顶棚：从亭内抬头看见的木板 + 四根对角椽 + 金心
        self.add(box("eave_ceil", (0, 0, 11.75), (5.24, 5.24, 0.14),
                     M["wood_mid"]), 0.008)
        for sx in (-1, 1):
            for sy in (-1, 1):
                self.add(beam("eave_rafter", (sx * 2.54, sy * 2.54, 11.60),
                              (sx * 0.30, sy * 0.30, 11.70),
                              0.12, 0.11, M["wood_dark"]), 0.004)
        self.add(revolve("eave_boss", [(0.0, 0.0), (0.22, 0.0), (0.22, 0.07),
                                       (0.15, 0.11), (0.0, 0.11)], 8,
                         (0, 0, 11.66), M["gold"]), 0.0, 1)

    # ── 7. 箭羽冠：剪影箭（铁箭身 + 蓝羽 + 金束）─────────────────────────────
    def arrow(self):
        """箭饰：两片互相垂直的**剪影箭**（45° / 135°，正好接在两条戗脊的延长线上）。

        为什么不做"绕杆一圈的羽"：四片羽从任何水平方向看都会合成一个对称的
        梭形/灯罩，越做越像装饰球。剪影箭是从侧面直接读"箭"的唯一可靠做法 ——
        铁箭身给出镞 + 杆，蓝羽给出尾羽，两片成 90° 保证任何机位都有一片接近正面。
        """
        M = self.M
        # 铁箭身：带倒钩的镞 + 通长箭杆（剪影轮廓，逆时针描）
        body = [(0.000, 17.46),
                (0.300, 16.72), (0.300, 16.54), (0.082, 16.46),
                (0.082, 15.62), (0.070, 14.62),
                (-0.070, 14.62), (-0.082, 15.62),
                (-0.082, 16.46), (-0.300, 16.54), (-0.300, 16.72)]
        # 尾羽：左右各一片，向外下方张开（羽尖朝下，是箭尾的样子）
        fin_r = [(0.072, 15.64), (0.360, 15.28), (0.360, 15.02), (0.072, 14.96)]
        fin_l = [(-u, z) for (u, z) in fin_r]
        for a in (45, 135):
            self.add(vane("arw_body", a, body, 0.058, M["iron"]), 0.004)
            self.add(vane("fl_fin", a, fin_r, 0.072, M["team"]), 0.004)
            self.add(vane("fl_fin", a, fin_l, 0.072, M["team"]), 0.004)
        # 金束 + 铁箍：把两片板在轴心上"绑"成一体（否则是两片插在屋顶上的刀片）
        self.add(revolve("arw_collar", [(0.090, 0.0), (0.122, 0.02),
                                        (0.122, 0.08), (0.090, 0.10)], 8,
                         (0, 0, 16.36), M["gold"]), 0.0, 1)
        self.add(revolve("arw_sleeve", [(0.100, 0.0), (0.140, 0.03),
                                        (0.140, 0.15), (0.100, 0.18)], 8,
                         (0, 0, 14.52), M["roof_edge"]), 0.0, 1)

    # ── 8. 场地：胸墙 / 箭捆架 / 箭靶 / 桶 / 石堆 / 草 ──────────────────────
    def yard(self):
        M = self.M
        # 门两侧的低胸墙：把入口框住，读作"有设防的塔"
        for sgn in (-1, 1):
            x0, x1 = sgn * 1.24, sgn * 2.62
            self.add(box("wall_core", ((x0 + x1) * 0.5, 2.22, 0.86),
                         (abs(x1 - x0), 0.48, 0.88), M["stone_mid"]), 0.010)
            self.add(box("wall_cap", ((x0 + x1) * 0.5, 2.22, 1.34),
                         (abs(x1 - x0) + 0.10, 0.58, 0.12), M["stone_light"]), 0.008)
            self.add(box("wall_end", (x1, 2.22, 0.92), (0.34, 0.58, 1.00),
                         M["stone_light"]), 0.008)
        # 箭捆架（正面左侧）
        self.arrow_rack("rack_a", (-2.48, 3.10))
        # 箭靶（正面右侧，斜对着院心）
        self.target_butt("targ_a", (2.88, 2.94), math.radians(212))
        # 木桶 + 石堆 + 草
        self.barrel("barrel_y", (3.14, 1.30), 0.28, 0.72, G_Z)
        for (px, py, s, rz) in ((3.18, -3.06, 0.28, 0.4), (3.36, -2.52, 0.20, -0.6),
                                (-3.18, -3.02, 0.26, 1.0), (-3.36, -2.36, 0.18, 0.2)):
            self.add(box("pebble_", (px, py, G_Z + s * 0.30), (s, s * 0.78, s * 0.60),
                         M["stone_mid"], rot=(0.20, 0.14, rz)), 0.004)
        for (px, py) in ((3.28, 3.42), (1.22, 3.44), (-3.30, 3.36), (-3.34, -1.10),
                         (3.32, 0.42)):
            self.grass((px, py))

    # ── 9. 亭内道具（轻）：箭袋 / 备用箭 / 火盆 ─────────────────────────────
    def deck_props(self):
        M = self.M
        self.quiver("quiver_a", (-2.18, 0.86, DECK + 0.10))
        self.quiver("quiver_b", (-2.18, -0.36, DECK + 0.10))
        # 备用箭：三支立在栏板内侧（是弓箭手的箭，不是弩矢）
        for k in (-1, 0, 1):
            self.add(box("prop_arrow", (2.06 + k * 0.15, -1.70, DECK + 0.66),
                         (0.042, 0.042, 1.30), M["wood_warm"]), 0.001)
            self.add(box("prop_arrow_head", (2.06 + k * 0.15, -1.70, DECK + 1.35),
                         (0.085, 0.085, 0.12), M["iron"]), 0.002)
            self.add(box("prop_arrow_fletch", (2.06 + k * 0.15, -1.70, DECK + 0.14),
                         (0.075, 0.16, 0.14), M["team_trim"]), 0.001)
        # 火盆（后左角）：亭内唯一暖色点，从正面开口能看见火光
        self.brazier_small("prop_braz_", (-1.86, -1.90, DECK))
        # 燕尾旗 ×2：挂在正面 / 右侧檐梁内侧（横杆埋进檐梁，旗布垂到扶手上方）。
        # 两面互成 90° —— 相机看得到的那两面各有一面，读作"一对军旗"。
        self.pennant("banner_a", 1.20, HEADX - 0.22, 11.55, 0.96, 0.88, axis="Y")
        self.pennant("banner_b", HEADX - 0.22, 1.20, 11.53, 0.96, 0.88, axis="X")

    def pennant(self, name, x, y, z_top, w, h, axis="Y"):
        """小燕尾旗：横杆（埋进檐梁）+ 队色旗布 + 金顶边。"""
        M = self.M
        prof = [(-w * 0.5, 0.0), (w * 0.5, 0.0), (w * 0.5, -h * 0.80),
                (w * 0.24, -h), (0.0, -h * 0.78), (-w * 0.24, -h),
                (-w * 0.5, -h * 0.80)]
        if axis == "Y":
            self.add(box(name + "_bar", (x, y, z_top), (w + 0.14, 0.07, 0.06),
                         M["wood_dark"]), 0.003)
            self.add(extrude(name + "_cloth", prof, "Y", 0.045, (x, z_top - 0.02),
                             M["team"], offset=y), 0.004)
            self.add(box(name + "_trim", (x, y, z_top - 0.09),
                         (w + 0.02, 0.055, 0.05), M["team_trim"]), 0.002)
        else:
            self.add(box(name + "_bar", (x, y, z_top), (0.07, w + 0.14, 0.06),
                         M["wood_dark"]), 0.003)
            self.add(extrude(name + "_cloth", prof, "X", 0.045, (y, z_top - 0.02),
                             M["team"], offset=x), 0.004)
            self.add(box(name + "_trim", (x, y, z_top - 0.09),
                         (0.055, w + 0.02, 0.05), M["team_trim"]), 0.002)

    # ── 10. 构件 ────────────────────────────────────────────────────────────
    def slit(self, name, axis, wall, u, z, out, h=0.86, cross=False):
        """箭孔：深色内衬（凸 20 mm）+ 更深的窄缝（凸 36 mm）+ 可选横缝。

        石墙不开洞（开洞要把塔身拆成十几块，代价不值），靠 16 mm 的深浅差
        把"洞"读出来。所有面都不与墙面共面。
        """
        M = self.M
        if axis == "X":
            self.add(box(name + "_back", (wall + out * 0.020, u, z),
                         (0.05, 0.40, h + 0.16), M["stone_dark"]), 0.004)
            self.add(box(name, (wall + out * 0.036, u, z),
                         (0.04, 0.17, h), M["coal"]), 0.0)
            if cross:
                self.add(box(name + "_h", (wall + out * 0.036, u, z - h * 0.26),
                             (0.04, 0.40, 0.12), M["coal"]), 0.0)
        else:
            self.add(box(name + "_back", (u, wall + out * 0.020, z),
                         (0.40, 0.05, h + 0.16), M["stone_dark"]), 0.004)
            self.add(box(name, (u, wall + out * 0.036, z),
                         (0.17, 0.04, h), M["coal"]), 0.0)
            if cross:
                self.add(box(name + "_h", (u, wall + out * 0.036, z - h * 0.26),
                             (0.40, 0.04, 0.12), M["coal"]), 0.0)

    def brazier_small(self, name, p):
        """矮火盆：石座 0.30 + 铁盆 r0.24 + 三块炭 + 0.33 高的短焰。"""
        M = self.M
        x, y, z0 = p
        self.add(box(name + "base", (x, y, z0 + 0.15), (0.40, 0.40, 0.30),
                     M["stone_mid"]), 0.008)
        self.add(box(name + "base2", (x, y, z0 + 0.32), (0.48, 0.48, 0.08),
                     M["stone_light"]), 0.004)
        self.add(revolve(name + "bowl", [(0.10, 0.0), (0.28, 0.05), (0.31, 0.13),
                                         (0.27, 0.17), (0.10, 0.17)], 8,
                         (x, y, z0 + 0.33), M["iron"]), 0.0, 1)
        for i in range(3):
            a = math.tau * i / 3 + 0.5
            self.add(box(name + "coal", (x + 0.11 * math.cos(a),
                                         y + 0.11 * math.sin(a), z0 + 0.50),
                         (0.12, 0.12, 0.09), M["coal"]), 0.002)
        self.add(revolve(name + "flame", [(0.0, 0.0), (0.115, 0.03), (0.078, 0.12),
                                          (0.028, 0.21), (0.0, 0.27)], 8,
                         (x, y, z0 + 0.52), M["ember"]), 0.0, 1)
        self.add(revolve(name + "flame_c", [(0.0, 0.0), (0.08, 0.03), (0.045, 0.12),
                                            (0.0, 0.20)], 8,
                         (x, y, z0 + 0.54), M["flame_in"]), 0.0, 1)

    def arrow_rack(self, name, p, lift=0.0):
        """箭捆架：两根立柱 + 两道横档 + 四捆箭（每捆 3 支，尾羽队色）。"""
        M = self.M
        x, y = p
        z0 = G_Z + lift
        self.add(box(name + "_foot", (x, y, z0 + 0.06), (1.14, 0.48, 0.12),
                     M["stone_dark"]), 0.006)
        for sgn in (-1, 1):
            self.add(box(name + "_post", (x + sgn * 0.52, y, z0 + 0.64),
                         (0.10, 0.10, 1.18), M["wood_dark"]), 0.004)
        for zz in (0.46, 1.02):
            self.add(box(name + "_rail", (x, y, z0 + zz), (1.10, 0.09, 0.09),
                         M["wood_dark"]), 0.003)
        for i in range(4):
            bx = x - 0.39 + i * 0.26
            for k in range(3):
                ox = (k % 2 - 0.5) * 0.055
                oy = (k // 2 - 0.5) * 0.055
                self.add(box(name + "_shaft", (bx + ox, y + oy, z0 + 0.62),
                             (0.030, 0.030, 1.14), M["wood_warm"]), 0.001)
                self.add(box(name + "_fletch", (bx + ox, y + oy, z0 + 1.16),
                             (0.058, 0.058, 0.12), M["team_trim"]), 0.001)

    def target_butt(self, name, p, yaw):
        """箭靶：三层同心靶面 + 三脚木架 + 一支中靶的箭。

        RTS 距离上它读作"一个带环的亮圆盘"—— 比任何摆件都更直接地说出"弓箭"，
        而且不占体量（去掉弩炮之后，地面上唯一需要"说话"的道具）。
        """
        M = self.M
        x, y = p
        z = G_Z + 0.84
        nx, ny = -math.sin(yaw), math.cos(yaw)     # 靶面法线
        hx, hy = x - nx * 0.16, y - ny * 0.16      # 架心（靶面之后）
        # 三脚架 + 三只小足垫
        for k in range(3):
            a = yaw + math.pi * 0.5 + k * math.tau / 3
            fx = hx + 0.64 * math.cos(a)
            fy = hy + 0.64 * math.sin(a)
            self.add(beam(name + "_leg", (hx, hy, G_Z + 0.60), (fx, fy, G_Z + 0.02),
                          0.10, 0.10, M["wood_dark"]), 0.004)
            self.add(box(name + "_foot", (fx, fy, G_Z + 0.04), (0.17, 0.17, 0.08),
                         M["wood_warm"]), 0.003)
        # 靶面：草垛（sand）+ 两圈 + 靶心
        for (rr, th, off, mat) in ((0.45, 0.16, 0.00, M["sand"]),
                                   (0.30, 0.05, 0.10, M["team_trim"]),
                                   (0.14, 0.05, 0.15, M["team"])):
            d = disc_y(name + "_face", rr, th, 12, mat)
            d.rotation_euler = (0.0, 0.0, yaw)
            d.location = (x + nx * off, y + ny * off, z)
            self.add(d, 0.004)     # ← 必须进 items：否则不合并 / 不进图集 / 不跟镜像
        # 中靶的箭：从靶心斜插出来
        tip = Vector((x + nx * 0.02, y + ny * 0.02, z + 0.02))
        tail = Vector((x + nx * 0.62, y + ny * 0.62, z + 0.28))
        self.add(beam(name + "_arrow", tip, tail, 0.036, 0.036, M["wood_warm"]), 0.001)
        for s in (-1, 1):
            self.add(box(name + "_fletch", (tail.x + s * 0.04, tail.y + s * 0.04,
                                            tail.z + 0.08),
                         (0.02, 0.08, 0.13), M["team_trim"], rot=(0, 0, yaw)), 0.001)

    # ── 11. 组装 / 收尾 ─────────────────────────────────────────────────────
    def build(self):
        for step in (self.plinth, self.stone_base, self.shaft, self.gallery,
                     self.pavilion, self.roof, self.arrow, self.yard,
                     self.deck_props):
            step()
        return self

    def finalize(self, bevel=True):
        # 细分只给"该圆的圆件"（回转体道具）；石墙 / 屋面 / 栏板这些大平面
        # 一旦上 CC 就会被磨成一圈渐变的圆 —— 塑料感就是这么来的。
        flat_pref = ("spire_", "fl_", "arw_", "slot", "pebble_", "eave_",
                     "rail_", "deck_", "targ_a_face", "prop_")
        cc_ok = ("quiver_", "prop_braz_", "barrel_", "targ_a_face")
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
                L.finalize(ob, bevel=min(max(bev, 0.004), 0.018), seg=1, sub=cc,
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
        out = L.join_by_material(objs, prefix="AT")
        mirror_x(out)
        if self.unwrap:
            L.smart_uv(out)
        return out


def build(smooth=True, unwrap=True, bevel=True):
    m = Model(smooth, unwrap).build()
    objs = m.finalize(bevel=bevel)
    return objs, L.stats(objs)
