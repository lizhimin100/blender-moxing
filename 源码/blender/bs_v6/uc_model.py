"""
uc_model.py —— 地下城入口（Undercity Gate）v1：**崖壁巨门 + 双守卫像 + 符文环**

和"地牢"刻意做成两件事：
  地牢 = 一座**被掏空的石台**，小而破，讲的是"这里关过人"；
  地下城入口 = 一道**刻进崖壁的巨门**，大而静，讲的是"下面埋着一座城"。

体量关系（俯视一眼）：
  ① 后面一整条**暗色崖壁**（14.6 宽），中间凹进一个 4.6 × 5.1 的拱门；
  ② 前面一块**抬起的石台**（1.0 m），台上两个**坐姿守卫像**夹着门，
     一个完好、一个掉了头（头就躺在旁边地上）；
  ③ 台面正中一圈**幽绿符文环**，是俯视的视觉中心；
  ④ 正面一道 6 m 宽的大石梯，把视线送进门里；门内五级下沉，尽头全黑。

明度秩序：土场 → **暗**崖壁（ancient_dark 打底）→ **中**台身 → **亮**压顶/门套 →
**近黑**门洞 → 幽绿两点（符文 / 门内）→ 铜绿守卫像底座 → 队色三条。

队色（远征队）：门前两根旗杆 + 拱门上方一条水平门楣匾 + 台口两段压顶。
全部是**水平或大面**，俯视不掉色。

坐标：X 右、Y 前（+Y = 正面）、Z 上；原点在占地中心，z = 0 地面。
交付前整体沿 X 镜像一次（与九座一致）。
"""
import math

import bpy
from mathutils import Vector

import bslib as L
import dl_kit as K
import dl_parts as P

# 失落帝国通用阵营色（定义在 dl_parts，三座共用）
TEAM_STYLE = P.LE_TEAM_STYLE
from bslib import arch_band, beam, box, extrude, mesh_obj, revolve
from br_model import mirror_x
from wt_model import frame_ring

# ── 场地 ────────────────────────────────────────────────────────────────────
PADX = 7.30
PADY0, PADY1 = -5.55, 6.60
G_Z = 0.14

# ── 崖壁（14.4 × 3.8，0.14 → 8.60）─────────────────────────────────────────
CLX = 7.00
CLY0, CLY1 = -5.20, -1.40
CL_HI = 7.40
CL_TOP = 8.60

# ── 巨门（宽 4.60，拱脚 3.80，拱顶 6.10）──────────────────────────────────
GW = 2.30
SPRING = 3.80
ARCH = SPRING + GW               # 6.10
TUN_Y0, TUN_Y1 = -3.20, -1.40
TUN_Z = 6.00

# ── 台地（10.8 × 5.6，0.14 → 1.00）─────────────────────────────────────────
TX0, TX1 = -5.40, 5.40
TY0, TY1 = -1.40, 4.20
TZ = 1.00

# ── 正面大梯（5 级，宽 6.0）────────────────────────────────────────────────
STX = 3.00
ST_N = 5
ST_RISE = (TZ - G_Z) / ST_N      # 0.172
ST_TREAD = 0.36
ST_Y0 = TY1
ST_Y1 = ST_Y0 + ST_N * ST_TREAD


class Model:
    def __init__(self, smooth, unwrap=True):
        self.smooth = smooth
        self.unwrap = unwrap
        self.items = []
        self.M = L.all_materials()

    def add(self, ob, bevel=0.014, sub=0, seg=1):
        self.items.append((ob, bevel, sub, seg))
        return ob

    def put(self, obs, bevel=0.004):
        for ob in obs:
            self.add(ob, bevel)
        return obs

    # ── 1. 场地 ─────────────────────────────────────────────────────────────
    def pad(self):
        M = self.M
        cy = (PADY0 + PADY1) * 0.5
        self.add(box("pad_soil", (0, cy, G_Z * 0.5), (PADX * 2, PADY1 - PADY0, G_Z),
                     M["earth"]), 0.020)
        for sgn in (-1, 1):
            self.add(box("pad_curb", (sgn * (PADX - 0.10), (PADY0 + PADY1) * 0.5,
                                      G_Z + 0.035),
                         (0.20, PADY1 - PADY0, 0.11), M["paving"]), 0.006)
        self.add(box("pad_curb_b", (0, PADY0 + 0.10, G_Z + 0.035),
                     (PADX * 2 - 0.40, 0.20, 0.11), M["paving"]), 0.006)
        # 干裂土块（不同高度）
        for i, (px, py, sx, sy, rz) in enumerate((
                (-4.55, 5.15, 1.95, 1.10, 0.18), (4.60, 4.90, 1.55, 0.95, -0.26),
                (2.85, 5.95, 1.15, 0.72, 0.48), (-3.10, 6.10, 1.05, 0.60, -0.52))):
            self.add(box("pad_crack", (px, py, G_Z + 0.010 + i * 0.004),
                         (sx, sy, 0.026), M["earth_dark"], rot=(0, 0, rz)), 0.004)
        # 一条通向大梯的踩实的路
        self.add(box("pad_path", (0, 6.10, G_Z + 0.008), (5.60, 1.00, 0.024),
                     M["earth_dark"]), 0.004)
        self.put(K.stones("pad_stone", -6.15, 3.95, G_Z, 6, 0.85, 0.24,
                          (M["ancient"], M["ancient_pale"]), seed=101), 0.005)
        self.put(K.stones("pad_stone", 6.05, 3.20, G_Z, 5, 0.70, 0.20,
                          (M["ancient"], M["stone_mid"]), seed=102), 0.004)

    # ── 2. 崖壁 + 巨门 ──────────────────────────────────────────────────────
    def cliff(self):
        M = self.M
        cy = (CLY0 + CLY1) * 0.5
        dy = CLY1 - CLY0
        # 左右两大块（中间留给门洞）+ 门上过梁块
        for sgn in (-1, 1):
            x0, x1 = (sgn * GW, sgn * CLX)
            self.add(box("clf_block", ((x0 + x1) * 0.5, cy, (G_Z + CL_HI) * 0.5),
                         (abs(x1 - x0), dy, CL_HI - G_Z), M["ancient_dark"]), 0.034)
        self.add(box("clf_lintel", (0, cy, (ARCH + CL_HI) * 0.5),
                     (GW * 2, dy, CL_HI - ARCH), M["ancient_dark"]), 0.030)
        # 崖顶：不是平屋顶，是一排错落的碎岩（俯视才读得出"崖"）
        for (cx, cy, cz, sx, sy, sz, ry, mat) in (
                (-5.85, -3.55, 7.55, 2.45, 3.20, 1.35, 0.10, M["ancient"]),
                (-3.75, -3.85, 7.35, 2.05, 2.70, 1.95, -0.06, M["ancient_dark"]),
                (-1.85, -3.45, 7.60, 1.85, 3.30, 1.55, 0.04, M["ancient"]),
                (0.35, -3.95, 7.40, 2.30, 2.60, 1.85, -0.08, M["ancient"]),
                (2.65, -3.50, 7.65, 2.15, 3.25, 1.45, 0.07, M["ancient_dark"]),
                (4.85, -3.80, 7.45, 2.10, 2.85, 1.70, -0.05, M["ancient"]),
                (6.35, -3.60, 7.55, 1.55, 3.10, 1.30, 0.03, M["ancient"])):
            self.add(box("clf_rock", (cx, cy, cz), (sx, sy, sz), mat,
                         rot=(0, ry, 0)), 0.012)
        # 崖面竖向扶壁（把 14 m 的暗墙分段）
        for x in (-6.35, -4.55, 4.55, 6.35):
            self.add(box("clf_butt", (x, CLY1 - 0.10, 3.55), (0.56, 0.30, 6.70),
                         M["ancient"]), 0.012)
            self.add(box("clf_butt_cap", (x, CLY1 - 0.10, 6.98), (0.68, 0.38, 0.18),
                         M["ancient_pale"]), 0.008)
            self.add(box("clf_butt_foot", (x, CLY1 - 0.16, G_Z + 0.35),
                         (0.70, 0.42, 0.60), M["ancient_dark"]), 0.008)
        # 一道通长石线脚（只在崖面，压住 7 m 的空白）
        for (x0, x1) in ((-CLX, -GW), (GW, CLX)):
            self.add(box("clf_line", ((x0 + x1) * 0.5, CLY1 - 0.05, 5.30),
                         (x1 - x0, 0.10, 0.13), M["ancient_pale"]), 0.006)
        # ── 拱门：拱肩墙（从拱脚起算）+ 门套 + 拱心石 ─────────────────────
        self.add(K.arch_wall("clf_arch", 0, SPRING, GW, SPRING, ARCH, 0.36,
                             CLY1 - 0.18, M["ancient"]), 0.012)
        self.add(arch_band("clf_arch_ring", 0, SPRING, GW, GW + 0.26,
                           CLY1 + 0.015, CLY1 + 0.12, M["ancient_pale"], segs=13), 0.010)
        self.add(box("clf_key", (0, CLY1 + 0.03, ARCH - 0.06), (0.36, 0.20, 0.52),
                     M["ancient_pale"]), 0.008)
        for sgn in (-1, 1):
            self.add(box("clf_jamb", (sgn * (GW + 0.16), CLY1 + 0.015, 2.42),
                         (0.32, 0.12, 2.72), M["ancient_pale"]), 0.008)
            # 门柱脚（一整块，从台面砌起）
            self.add(box("clf_jamb_foot", (sgn * (GW + 0.16), CLY1 + 0.06, 1.22),
                         (0.48, 0.22, 0.46), M["ancient_pale"]), 0.008)
            self.add(box("clf_jamb_team", (sgn * (GW + 0.16), CLY1 + 0.06, 1.462),
                         (0.52, 0.26, 0.03), M["team"]), 0.002)
        # 门楣横匾：**队色**（水平面，俯视不掉）
        self.add(box("clf_lintel", (0, CLY1 + 0.03, 6.34), (5.36, 0.16, 0.36),
                     M["team"]), 0.008)
        self.add(box("clf_lintel_t", (0, CLY1 + 0.05, 6.55), (5.36, 0.18, 0.06),
                     M["team_trim"]), 0.005)
        self.add(box("clf_lintel_top", (0, CLY1 - 0.02, 6.525), (5.30, 0.26, 0.03),
                     M["team"]), 0.002)
        # 门洞内：两侧壁 + 顶 + 尽头（近黑）
        for sgn in (-1, 1):
            self.add(box("clf_tun_wall", (sgn * (GW - 0.07), (TUN_Y0 + TUN_Y1) * 0.5,
                                          (G_Z + TUN_Z) * 0.5),
                         (0.14, TUN_Y1 - TUN_Y0, TUN_Z - 0.024 - G_Z),
                         M["ancient_dark"]), 0.004)
        self.add(box("clf_tun_ceil", (0, (TUN_Y0 + TUN_Y1) * 0.5, TUN_Z + 0.02),
                     (GW * 2 - 0.10, TUN_Y1 - TUN_Y0, 0.14), M["coal"]), 0.004)
        self.add(box("clf_tun_end", (0, TUN_Y0 + 0.07, (G_Z + TUN_Z - 0.024) * 0.5),
                     (GW * 2 - 0.10, 0.14, TUN_Z - 0.024 - G_Z), M["ancient_dark"]),
                 0.004)
        # 门内五级下沉（1.00 → 0.16），尽头是幽绿
        for i in range(5):
            y1 = TUN_Y1 - 0.30 - i * 0.34
            y0 = y1 - 0.34
            zt = TZ - (i + 1) * 0.168
            self.add(box("clf_tun_step", (0, (y0 + y1) * 0.5, zt * 0.5),
                         (GW * 2 - 0.18, y1 - y0, zt), M["ancient_dark"]), 0.003)
        self.add(box("clf_glow", (0, TUN_Y0 + 0.16, 0.40), (2.30, 0.04, 0.46),
                     M["depth_glow"]), 0.0)
        self.add(box("clf_glow_floor", (0, TUN_Y0 + 0.46, 0.10), (1.70, 0.36, 0.025),
                     M["depth_glow"]), 0.0)
        self.add(box("clf_glow_lip", (0, TUN_Y0 + 0.20, 0.70), (2.55, 0.22, 0.12),
                     M["ancient_dark"]), 0.0)
        self.add(box("clf_glow_lip2", (0, TUN_Y0 + 0.20, 0.17), (2.55, 0.22, 0.12),
                     M["ancient_dark"]), 0.0)
        # 崖面苔痕 / 裂缝
        for (mx, mz, mw, mh) in ((-5.25, 2.30, 0.85, 1.15), (-3.35, 6.90, 0.55, 0.42),
                                 (5.10, 1.55, 0.70, 0.85), (3.25, 6.55, 0.45, 0.55)):
            self.add(box("clf_moss", (mx, CLY1 + 0.012, mz), (mw, 0.05, mh),
                         M["moss_dark"]), 0.004)
        for (cx, cz, ch, rz) in ((-4.10, 3.10, 1.70, 0.12), (4.85, 4.40, 1.25, -0.15),
                                 (-2.85, 5.85, 0.90, 0.20)):
            self.add(box("clf_crack", (cx, CLY1 + 0.006, cz), (0.06, 0.03, ch),
                         M["coal"], rot=(0, 0, rz)), 0.002)
        # 崖顶残破的雉堞（只在右段留三块，左段塌平）
        for cx in (3.05, 4.15, 5.25):
            self.add(box("clf_merlon", (cx, -2.55, CL_TOP + 0.26), (0.62, 1.55, 0.52),
                         M["ancient"]), 0.008)
            self.add(box("clf_merlon_cap", (cx, -2.55, CL_TOP + 0.55), (0.68, 1.62, 0.06),
                         M["ancient_pale"]), 0.004)

    # ── 3. 台地 + 大梯 + 护栏 ───────────────────────────────────────────────
    def terrace(self):
        M = self.M
        self.add(box("ter_core", (0, (TY0 + TY1) * 0.5, (G_Z + TZ) * 0.5),
                     (TX1 - TX0, TY1 - TY0, TZ - G_Z), M["ancient"]), 0.028)
        self.add(box("ter_base", (0, (TY0 + TY1) * 0.5, G_Z + 0.10),
                     (TX1 - TX0 + 0.28, TY1 - TY0 + 0.28, 0.20), M["ancient_dark"]),
                 0.014)
        self.add(box("ter_cap", (0, (TY0 + TY1) * 0.5, TZ + 0.055),
                     (TX1 - TX0 + 0.16, TY1 - TY0 + 0.16, 0.11), M["ancient_pale"]),
                 0.012)
        # 台面铺石：中间一整块 + 两侧两块（不同高度）
        self.add(box("ter_deck", (0, 1.35, TZ + 0.145), (6.10, 5.40, 0.07),
                     M["paving"]), 0.006)
        for sgn in (-1, 1):
            self.add(box("ter_deck_s", (sgn * 4.55, 1.30, TZ + 0.150),
                         (1.45, 5.35, 0.07), M["ancient"]), 0.006)
        # 门前一条大幅队色毯（水平面：俯视 / 正视都能读到，也是"远征队占了这里"）
        self.add(box("ter_runner", (0, 3.58, TZ + 0.178), (3.90, 0.72, 0.03),
                     M["team"]), 0.002)
        for yy in (3.205, 3.955):
            self.add(box("ter_runner_t", (0, yy, TZ + 0.182), (3.94, 0.05, 0.03),
                         M["team_trim"]), 0.001)
        # 正面大梯（5 级）
        for i in range(ST_N):
            y0 = ST_Y1 - (i + 1) * ST_TREAD
            zt = G_Z + (i + 1) * ST_RISE
            self.add(box("st_tread", (0, y0 + ST_TREAD * 0.5, (G_Z + zt) * 0.5),
                         (STX * 2, ST_TREAD, zt - G_Z), M["ancient"]), 0.010)
        # 梯口两侧的斜压墙（跟着台阶走，不挡门）
        for sgn in (-1, 1):
            for i in range(0, ST_N, 2):
                y0 = ST_Y1 - (i + 1) * ST_TREAD
                zt = G_Z + (i + 2) * ST_RISE
                self.add(box("st_wall", (sgn * (STX + 0.22), y0 + ST_TREAD,
                                         (G_Z + zt) * 0.5),
                             (0.44, ST_TREAD * 2 + 0.02, zt - G_Z + 0.28),
                             M["ancient_dark"]), 0.008)
                self.add(box("st_wall_cap", (sgn * (STX + 0.22), y0 + ST_TREAD,
                                             zt + 0.20),
                             (0.52, ST_TREAD * 2 + 0.05, 0.07), M["ancient_pale"]),
                         0.004)
        # 台口护栏：正面留出 6 m 的梯口，两段队色压顶
        for sgn in (-1, 1):
            x0, x1 = sgn * STX, sgn * TX1
            self.add(box("par_wall", ((x0 + x1) * 0.5, TY1 - 0.10, TZ + 0.44),
                         (abs(x1 - x0), 0.34, 0.88), M["ancient"]), 0.010)
            self.add(box("par_cap", ((x0 + x1) * 0.5, TY1 - 0.10, TZ + 0.91),
                         (abs(x1 - x0) + 0.06, 0.40, 0.09), M["ancient_pale"]), 0.006)
            self.add(box("par_team", ((x0 + x1) * 0.5, TY1 - 0.10, TZ + 0.975),
                         (abs(x1 - x0) - 0.30, 0.42, 0.045), M["team"]), 0.003)
            # 侧护栏
            self.add(box("par_side", (sgn * (TX1 - 0.17), (TY0 + TY1) * 0.5,
                                      TZ + 0.4275),
                         (0.34, TY1 - TY0, 0.855), M["ancient"]), 0.010)
            self.add(box("par_side_cap", (sgn * (TX1 - 0.17), (TY0 + TY1) * 0.5,
                                          TZ + 0.8925),
                         (0.40, TY1 - TY0, 0.09), M["ancient_pale"]), 0.006)

    # ── 4. 守卫像 ×2（一座完整、一座掉头）──────────────────────────────────
    def statue(self, name, x, y, k=1.24, broken=False):
        M = self.M
        z0 = TZ + 0.07

        def bx(tag, c, sz, mat, rot=None, bev=0.006):
            self.add(box(name + tag, (x + c[0] * k, y + c[1] * k, z0 + c[2] * k),
                         (sz[0] * k, sz[1] * k, sz[2] * k), mat, rot=rot), bev)

        # 底座：两级
        bx("_plinth", (0, 0, 0.20), (1.42, 1.42, 0.40), M["ancient_dark"], bev=0.010)
        bx("_plinth2", (0, 0, 0.46), (1.16, 1.16, 0.14), M["ancient_pale"])
        z = 0.53
        # 脚 + 小腿 + 膝（坐姿）
        bx("_feet", (0, 0.12, z + 0.09), (0.92, 0.52, 0.18), M["ancient"])
        for sgn in (-1, 1):
            bx("_shin", (sgn * 0.26, 0.16, z + 0.38), (0.28, 0.46, 0.50), M["ancient"])
        bx("_knee", (0, 0.04, z + 0.74), (0.98, 0.66, 0.26), M["ancient_pale"])
        # 袍 / 躯干 / 肩
        bx("_robe", (0, -0.04, z + 1.16), (0.94, 0.62, 0.62), M["ancient"], bev=0.008)
        bx("_torso", (0, -0.06, z + 1.78), (0.84, 0.56, 0.66), M["ancient"], bev=0.008)
        bx("_shoulder", (0, -0.06, z + 2.14), (1.14, 0.58, 0.20), M["ancient_pale"])
        # 手臂
        for sgn in (-1, 1):
            arm_top = z + 2.06
            arm_bot = z + 1.16 if (broken and sgn > 0) else z + 0.92
            bx("_arm", (sgn * 0.56, 0.02, (arm_top + arm_bot) * 0.5),
               (0.24, 0.30, arm_top - arm_bot), M["ancient"])
        if not broken:
            bx("_hand", (0.56, 0.06, z + 0.82), (0.28, 0.36, 0.22), M["ancient"])
        # 颈 / 头 / 冠
        bx("_neck", (0, -0.06, z + 2.27), (0.26, 0.26, 0.12), M["ancient_dark"], bev=0.004)
        if not broken:
            bx("_head", (0, -0.06, z + 2.52), (0.42, 0.40, 0.42), M["ancient_pale"])
            bx("_crown", (0, -0.06, z + 2.77), (0.50, 0.46, 0.10), M["bronze"], bev=0.004)
            bx("_brow", (0, 0.15, z + 2.55), (0.34, 0.05, 0.09), M["ancient_dark"], bev=0.002)
        else:
            bx("_neck_break", (0, -0.06, z + 2.31), (0.32, 0.30, 0.10),
               M["ancient_dark"], rot=(0.18, 0, 0), bev=0.004)
        # 队色：底座一圈箍（水平面，俯视最有效）+ 肩甲一条窄边
        bx("_team_band", (0, 0, 0.415), (1.46, 1.46, 0.09), M["team"], bev=0.003)
        bx("_team_trim", (0, -0.06, 2.235), (1.16, 0.60, 0.05), M["team_trim"], bev=0.002)

    def statues(self):
        M = self.M
        self.statue("stat_l", -4.15, -0.05, broken=False)
        self.statue("stat_r", 4.15, -0.05, broken=True)
        # 掉下来的头（躺在右像脚边，放大 1.24 倍）
        hx, hy, hz = 2.45, 0.95, TZ + 0.36
        self.add(box("stat_head", (hx, hy, hz), (0.56, 0.52, 0.50),
                     M["ancient_pale"], rot=(0, 0.24, 0.55)), 0.008)
        self.add(box("stat_head_crown", (hx + 0.05, hy - 0.02, hz + 0.30),
                     (0.62, 0.56, 0.12), M["bronze"], rot=(0, 0.24, 0.55)), 0.004)
        self.add(box("stat_head_brow", (hx - 0.05, hy + 0.17, hz + 0.02),
                     (0.40, 0.07, 0.11), M["ancient_dark"], rot=(0, 0.24, 0.55)), 0.002)

    def statues(self):
        M = self.M
        self.statue("stat_l", -3.92, -0.18, broken=False)
        self.statue("stat_r", 3.92, -0.18, broken=True)
        # 掉下来的头（躺在右像脚边）
        hx, hy, hz = 2.45, 1.05, TZ + 0.30
        self.add(box("stat_head", (hx, hy, hz), (0.46, 0.42, 0.40),
                     M["ancient_pale"], rot=(0, 0.24, 0.55)), 0.006)
        self.add(box("stat_head_crown", (hx + 0.04, hy - 0.02, hz + 0.24),
                     (0.50, 0.46, 0.10), M["bronze"], rot=(0, 0.24, 0.55)), 0.004)
        self.add(box("stat_head_brow", (hx - 0.04, hy + 0.14, hz + 0.02),
                     (0.32, 0.06, 0.09), M["ancient_dark"], rot=(0, 0.24, 0.55)), 0.002)

    # ── 5. 符文环（台面正中，俯视的视觉中心）───────────────────────────────
    def runes(self):
        M = self.M
        cx, cy = 0.0, 1.05
        # 深色内盘：让幽绿刻线从浅灰台面上"跳"出来（俯视的焦点）
        self.add(revolve("rune_disc", [(0.0, 0.0), (2.02, 0.0), (2.02, 0.035),
                                       (0.0, 0.035)], 24, (cx, cy, TZ + 0.135),
                         M["ancient_dark"]), 0.004)
        z = TZ + 0.195
        # 两圈弧（缺口故意不等分：读作"刻的"，不是"印的"）
        self.put([K.arc_plate("rune_arc", cx, cy, 1.60, 1.82, a0, a1, z,
                              M["depth_glow"], segs=9, thick=0.022)
                  for (a0, a1) in ((0.18, 1.42), (1.72, 3.02), (3.38, 4.62),
                                   (4.98, 6.05))], 0.0)
        self.put([K.arc_plate("rune_arc_in", cx, cy, 1.08, 1.22, a0, a1, z,
                              M["depth_glow"], segs=6, thick=0.018)
                  for (a0, a1) in ((0.30, 1.30), (2.10, 2.95), (3.90, 4.80),
                                   (5.30, 6.00))], 0.0)
        # 八条放射刻线 + 四块符文块
        for i in range(8):
            a = math.tau * i / 8 + 0.39
            r0, r1 = 1.22, 1.58
            self.add(beam("rune_tick",
                          (cx + r0 * math.cos(a), cy + r0 * math.sin(a), z),
                          (cx + r1 * math.cos(a), cy + r1 * math.sin(a), z),
                          0.055, 0.022, M["depth_glow"]), 0.0)
        for i in range(4):
            a = math.tau * i / 4 + 0.78
            self.add(box("rune_glyph", (cx + 0.78 * math.cos(a),
                                        cy + 0.78 * math.sin(a), z),
                         (0.22, 0.09, 0.025), M["depth_glow"],
                         rot=(0, 0, a + 1.57)), 0.0)

    # ── 6. 旗 / 火把 / 台面道具 ─────────────────────────────────────────────
    def props(self):
        M = self.M
        # 门前两根旗杆（队色垂旗）
        for sgn in (-1, 1):
            x, y = sgn * 2.62, 3.62
            self.add(box("bnr_pole", (x, y, TZ + 1.62), (0.08, 0.08, 3.24),
                         M["wood_dark"]), 0.003)
            self.add(box("bnr_finial", (x, y, TZ + 3.28), (0.14, 0.14, 0.14),
                         M["bronze"]), 0.003)
            self.add(box("bnr_bar", (x, y + 0.03, TZ + 3.08), (0.74, 0.07, 0.07),
                         M["wood_dark"]), 0.003)
            prof = [(-0.33, 0.0), (0.33, 0.0), (0.33, -1.16), (0.10, -1.46),
                    (0.0, -1.22), (-0.10, -1.46), (-0.33, -1.16)]
            cl = extrude("bnr_cloth", prof, "Y", 0.035, (0, 0), M["team"])
            cl.location = (x, y + 0.07, TZ + 3.05)
            self.add(cl, 0.004)
            self.add(box("bnr_trim", (x, y + 0.08, TZ + 2.95), (0.62, 0.05, 0.05),
                         M["team_trim"]), 0.002)
        # 崖面上的两支火把（和火把资产同一套三 tongue 火）
        for sgn in (-1, 1):
            x, z = sgn * 3.25, 4.55
            self.add(box("torch_plate", (x, CLY1 + 0.04, z), (0.24, 0.08, 0.30),
                         M["bronze_dark"]), 0.003)
            self.add(beam("torch_arm", (x, CLY1 + 0.12, z - 0.04),
                          (x, CLY1 + 0.42, z + 0.16), 0.07, 0.07, M["bronze_dark"]), 0.002)
            self.add(revolve("torch_bowl", [(0.06, 0.0), (0.16, 0.04), (0.18, 0.12),
                                            (0.15, 0.16), (0.06, 0.16)], 8,
                             (x, CLY1 + 0.44, z + 0.14), M["bronze"]), 0.003)
            self.put(K.embers("torch_ember", x, CLY1 + 0.44, z + 0.30, 3, 0.10,
                              seed=111 + sgn), 0.001)
            self.put(K.flame("torch_flame", x, CLY1 + 0.44, z + 0.32, 0.34, 0.12,
                             seed=113 + sgn), 0.001)
        # 台面左侧：塌下来的柱鼓 + 碎石
        for (px, py, rz) in ((-4.45, 2.35, 0.4), (-4.05, 2.95, -0.5)):
            ob = revolve("pro_drum", [(0.00, -0.38), (0.40, -0.38), (0.40, 0.38),
                                      (0.00, 0.38)], 8, (0, 0, 0), M["ancient"])
            ob.rotation_euler = (0, math.pi / 2, rz)
            ob.location = (px, py, TZ + 0.47)
            self.add(ob, 0.008)
        self.put(K.stones("pro_rubble", -4.55, 3.55, TZ + 0.07, 5, 0.42, 0.24,
                          (M["ancient"], M["ancient_pale"]), seed=121), 0.004)
        # 台面右侧：远征队的箱桶
        self.put(K.crate("pro_crate", 4.45, 2.55, TZ + 0.07, 0.52, 0.44,
                         M["wood_warm"], M["wood_dark"]), 0.005)
        self.put(K.crate("pro_crate", 4.10, 2.28, TZ + 0.074, 0.36, 0.32,
                         M["wood_mid"], M["wood_dark"]), 0.004)
        self.put(K.barrel("pro_barrel", 4.62, 3.28, TZ + 0.07, 0.26, 0.62,
                          M["wood_mid"], M["bronze_dark"]), 0.004)
        # 前景：半截塌掉的矮墙 + 一块断掉的门楣石（给画面加一层前景）
        self.add(box("pro_wall", (-5.45, 5.30, G_Z + 0.34), (2.60, 0.46, 0.68),
                     M["ancient"]), 0.010)
        self.add(box("pro_wall_cap", (-5.45, 5.30, G_Z + 0.72), (2.72, 0.54, 0.08),
                     M["ancient_pale"]), 0.005)
        self.add(box("pro_wall_break", (-4.05, 5.30, G_Z + 0.30), (0.55, 0.50, 0.60),
                     M["ancient_dark"], rot=(0, 0.16, 0)), 0.006)
        self.add(box("pro_lintel_fall", (4.95, 4.95, G_Z + 0.30), (2.10, 0.62, 0.56),
                     M["ancient_pale"], rot=(0, 0.10, 0.22)), 0.008)
        # 台面两个火盆（暖色点，夹住符文环）
        for sgn in (-1, 1):
            bx0, by0 = sgn * 4.62, 1.55
            self.add(box("pro_braz_base", (bx0, by0, TZ + 0.25), (0.50, 0.50, 0.20),
                         M["ancient_dark"]), 0.006)
            self.add(revolve("pro_braz_bowl", [(0.10, 0.0), (0.30, 0.05), (0.34, 0.15),
                                               (0.30, 0.20), (0.10, 0.20)], 8,
                             (bx0, by0, TZ + 0.365), M["bronze_dark"]), 0.004)
            self.put(K.embers("pro_braz_ember", bx0, by0, TZ + 0.55, 4, 0.17,
                              seed=131 + sgn), 0.002)
            self.put(K.flame("pro_braz_flame", bx0, by0, TZ + 0.56, 0.38, 0.16,
                             seed=133 + sgn), 0.002)
        # 草
        for (px, py, z) in ((-6.55, 5.85, G_Z), (6.45, 5.55, G_Z), (-6.30, -0.35, G_Z),
                            (6.20, -1.10, G_Z), (-4.95, 4.55, G_Z), (4.85, 4.35, G_Z)):
            self.put(K.grass("tuft", px, py, z, 0.26, 5,
                             seed=int(px * 11 + py * 7), mat=M["moss_dark"]), 0.001)

    # ── 7. 组装 / 收尾 ──────────────────────────────────────────────────────
    def build(self):
        for step in (self.pad, self.cliff, self.terrace, self.statues,
                     self.runes, self.props):
            step()
        # 阵营色覆盖必须在所有零件建完之后（dl_kit 会重刷材质）
        P.apply_team_style(TEAM_STYLE)
        return self

    def finalize(self, bevel=True):
        flat_pref = ("rune_", "clf_glow", "clf_crack", "clf_arch", "clf_tun",
                     "clf_moss", "torch_flame", "st_wall")
        cc_ok = ("torch_bowl", "pro_barrel_", "pro_drum", "flame_", "tuft", "stat_head")
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
                L.finalize(ob, bevel=min(max(bev, 0.003), 0.016), seg=1, sub=cc,
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
        out = L.join_by_material(objs, prefix="UC")
        mirror_x(out)
        if self.unwrap:
            L.smart_uv(out)
        return out


def build(smooth=True, unwrap=True, bevel=True):
    m = Model(smooth, unwrap).build()
    P.apply_team_style(TEAM_STYLE)
    objs = m.finalize(bevel=bevel)
    return objs, L.stats(objs)
