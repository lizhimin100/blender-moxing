"""
keep_model.py —— 城镇大厅二本「石木戍堡」（族系：台地式 + 塔式混合，一本 v3 的下一等级）

为什么不是"把 v3 加高一层"
--------------------------
v3 是**三段式市政厅**：宽 16.9、高 25.15（高:宽 1.39），一条中轴从拱门读到旗尖，
屋顶是 34.6° 缓坡四坡 + 骑脊钟塔。二本如果也往高里长，读起来就是"同一栋楼又长高了"，
玩家在 RTS 距离上分不出"升级了"。

二本的语法换成**戍堡**（WC3 人族 Keep 的读法）：

  ① **压扁、加宽**：主体 11.2 × 8.6、总高 15.05（高:宽 0.66）。俯视是一块厚实的
     方台，不是一根竖条 —— 与 v3 剪影一眼分开。
  ② **屋顶换成"阶梯金字塔"**：中央方塔 + 两座前角楼，顶上都不是坡屋顶，而是
     4 级/3 级**收分阶台**（每级内缩 0.5、高 0.55）。这是全项目第一次出现这种顶，
     和九座的坡 / 平 / 穹 / 锥都不撞。
  ③ **石木分层**：下段 0.55–5.95 是石砌（隅石 + 腰线 + 盲拱窗），上段 5.95–9.20 是
     木框墙（竖挺 + 斜撑 + 石角柱）。这一条把"二本"和"一本全石砌"分开 ——
     木头出现 = 领地有余力了。
  ④ **铁门**：2.70 宽、拱顶 4.60，两扇铁包木门 + 门楣铁箍 + 闸门齿。一本是木门。

明度秩序（与九座同一套节拍）：
    夯土场地 → 中灰石台 → **亮**台基压顶 → 亮石墙 → **暗**木框层 → 近黑阶台顶
    → 铁 / 金 → 队色。

坐标：X 右、Y 前（+Y = 正面）、Z 上；原点在主体中心，z = 0 地面。
交付前整体沿 X 镜像一次（与九座一致）→ 建模期 +X 在成品里是 −X。
"""
import math
from math import tau as TAU

import bpy

import bslib as L
import br_model as BR
from bslib import arch_band, beam, box, extrude, frustum, mesh_obj, revolve, taper_box
from br_model import mirror_x

# ── 主体平面与标高 ──────────────────────────────────────────────────────────
W2 = 5.60                        # 半宽 11.20
YF, YB = 4.30, -4.30             # 前 / 后墙（进深 8.60）
PL0, PL1 = 0.0, 0.55             # 石台
H1 = 4.65                        # 一层顶（腰线 4.53–4.77）
WT0, H2 = 5.95, 9.20             # 木框层底 / 墙顶
PARA_T, PARA_H = 0.44, 1.02      # 女儿墙
WALL_T = 0.55                    # 外墙厚

# ── 门 ─────────────────────────────────────────────────────────────────────
GW = 1.35                        # 门洞半宽 2.70
GSPR = 3.25                      # 拱脚
GTOP = GSPR + GW                 # 拱顶 4.60
GPORCH = 1.55                    # 门廊出挑（到 Y 5.85）

# ── 中央方塔 ───────────────────────────────────────────────────────────────
TW = 2.40                        # 半宽 4.80
TCX, TCY = 0.0, -0.70
TTOP = 12.55                     # 塔身顶（女儿墙 12.55–13.35）
TT0, TT_STEP, TT_N = 13.35, 0.56, 4   # 阶梯金字塔：4 级、每级 0.56

# ── 前角楼 ─────────────────────────────────────────────────────────────────
PW = 1.22                        # 半宽 2.44
PX, PY = 5.02, 3.78
PTOP = 10.55
PT0, PT_STEP, PT_N = 11.35, 0.58, 3

# ── 场地 ───────────────────────────────────────────────────────────────────
YX, YY0, YY1 = 6.55, -5.05, 6.35
G_Z = 0.22


class Model(BR.Model):
    def __init__(self, smooth, unwrap=True):
        BR.Model.__init__(self, smooth, unwrap)

    # ── 1. 场地 / 石台 / 踏步 ────────────────────────────────────────────────
    def base(self):
        M = self.M
        self.add(box("yard_soil", (0, (YY0 + YY1) * 0.5, G_Z * 0.5),
                     (YX * 2, YY1 - YY0, G_Z), M["earth"]), 0.018)
        # 石台两级：压顶比台身出挑 0.12（读"台基"而不是"地面抬高了一点"）
        self.add(box("plinth", (0, 0, (PL1 - 0.10) * 0.5), (W2 * 2 + 1.10, YF - YB + 1.10,
                                                           PL1 - 0.10), M["stone_mid"]), 0.028)
        self.add(box("plinth_cap", (0, 0, PL1 - 0.05), (W2 * 2 + 1.34, YF - YB + 1.34, 0.10),
                     M["stone_light"]), 0.016)
        # 台阶（正面）：三级，**落在门廊之外**（门廊进深到 Y 5.85，
        # 踏步摆在 5.90 起 —— 摆在门廊里面会被门廊的实体整个吃掉，
        # 正视图上就是"一扇落地的门、没有台阶"）。
        for i, (dy, zt) in enumerate(((0.16, 0.415), (0.46, 0.275), (0.76, 0.135))):
            self.add(box("step_%d" % i, (0, YF + GPORCH + dy, zt * 0.5),
                         (4.30 - 0.18 * i, 0.32, zt), M["stone_light"]), 0.010)
        # 门廊内的门槛石（踏面 0.55）
        self.add(box("porch_land", (0, YF - 0.06, PL1 - 0.05), (3.30, 0.86, 0.10),
                     M["paving"]), 0.008)
        # 场地牙子：把夯土收边（前开口，接台阶）
        for sx in (-1, 1):
            self.add(box("yard_curb", (sx * YX, (YY0 + YY1) * 0.5, G_Z - 0.05),
                         (0.16, YY1 - YY0, 0.10), M["paving"]), 0.006)
        self.add(box("yard_curb_b", (0, YY0, G_Z - 0.05), (YX * 2, 0.16, 0.10),
                     M["paving"]), 0.006)

    # ── 2. 石砌下段（0.55–5.95）───────────────────────────────────────────
    def stone_body(self):
        M = self.M
        z0, z1 = PL1, WT0
        # 前墙三块（真开拱洞）
        left = [(-W2, 0.0), (-GW, 0.0), (-GW, z1), (-W2, z1)]
        right = [(GW, 0.0), (W2, 0.0), (W2, z1), (GW, z1)]
        for nm, prof in (("wall_f_l", left), ("wall_f_r", right)):
            self.add(extrude(nm, prof, "Y", WALL_T, (0, PL1 + 0.0), M["stone_mid"],
                             offset=YF - WALL_T * 0.5), 0.030)
        top = [(-GW, GTOP), (-GW, z1), (GW, z1), (GW, GTOP)]
        for s in range(1, 11):
            a = math.pi * s / 10
            top.append((GW * math.cos(a), GSPR + GW * math.sin(a)))
        self.add(extrude("wall_f_t", top, "Y", WALL_T, (0, PL1), M["stone_mid"],
                         offset=YF - WALL_T * 0.5), 0.030)
        # 后墙 / 侧墙
        self.add(box("wall_b", (0, YB + WALL_T * 0.5, (PL1 + z1) * 0.5),
                     (W2 * 2, WALL_T, z1 - PL1), M["stone_mid"]), 0.030)
        for sx in (-1, 1):
            self.add(box("wall_s", (sx * (W2 - WALL_T * 0.5), 0, (PL1 + z1) * 0.5),
                         (WALL_T, YF - YB - WALL_T * 2, z1 - PL1), M["stone_mid"]), 0.030)
        # 墙裙（0.55–1.35，比墙暗一档）
        self.add(box("dado", (0, 0, PL1 + 0.40), (W2 * 2 + 0.12, YF - YB + 0.12, 0.80),
                     M["stone_mid"]), 0.020)
        # 腰线（一层顶）：一圈压顶，正面断开在门廊里
        self.add(box("belt_1", (0, 0, H1), (W2 * 2 + 0.26, YF - YB + 0.26, 0.24),
                     M["stone_mid"]), 0.018)
        self.add(box("belt_1_cap", (0, 0, H1 + 0.15), (W2 * 2 + 0.34, YF - YB + 0.34, 0.07),
                     M["stone_light"]), 0.010)
        # 隅石（四角，五皮，交错出挑 6 cm）
        for sx in (-1, 1):
            for sy in (-1, 1):
                for k in range(5):
                    zz = PL1 + 0.55 + k * 0.98
                    w = 0.62 + (0.07 if k % 2 else 0.0)
                    self.add(box("quoin", (sx * (W2 - 0.30), sy * (YF - 0.30), zz),
                                 (w, w, 0.50), M["stone_mid"]), 0.014)
        # 石墙上的盲拱（侧墙 2 个 / 后墙 3 个）：只做凹进去的框，不开洞
        for sx in (-1, 1):
            for k, yy in enumerate((-1.10, 1.55)):
                # 盲拱：一段凹进去的竖板 + 顶上一道横板（不真开洞，绕开"隧道"）
                self.add(box("blind_s%d" % k, (sx * (W2 + 0.02), yy, 3.10),
                             (0.10, 1.10, 1.80), M["stone_mid"]), 0.012)
                self.add(box("blind_s%dt" % k, (sx * (W2 + 0.02), yy, 4.05),
                             (0.10, 1.10, 0.22), M["stone_mid"]), 0.012)
        for k, xx in enumerate((-3.10, 0.0, 3.10)):
            self.add(box("blind_b%d" % k, (xx, YB - 0.02, 3.15),
                         (1.10, 0.10, 1.90), M["stone_mid"]), 0.012)
        # 石墙的箭孔（窄缝，2 皮）
        for sx in (-1, 1):
            for zz in (2.20, 3.60):
                self.add(box("slot_", (sx * (W2 + 0.03), -3.10, zz),
                             (0.09, 0.22, 0.95), M["stone_dark"]), 0.0)

    # ── 3. 木框上段（5.95–9.20）────────────────────────────────────────────
    def timber_body(self):
        M = self.M
        z0, z1 = WT0, H2
        # 木墙四面：比石墙退 0.06（"木框嵌在石壳里"），墙厚 0.34
        self.add(box("tw_b", (0, YB + 0.24, (z0 + z1) * 0.5), (W2 * 2 - 0.10, 0.34, z1 - z0),
                     M["wood_mid"]), 0.016)
        self.add(box("tw_f", (0, YF - 0.24, (z0 + z1) * 0.5), (W2 * 2 - 0.10, 0.34, z1 - z0),
                     M["wood_mid"]), 0.016)
        for sx in (-1, 1):
            self.add(box("tw_s", (sx * (W2 - 0.23), 0, (z0 + z1) * 0.5),
                         (0.34, YF - YB - 0.30, z1 - z0), M["wood_mid"]), 0.016)
        # 竖挺（每 1.05 m 一根，前后各 10 根 / 侧各 8 根）+ 一道腰梁
        xs = [-W2 + 0.58 + i * 1.05 for i in range(10)]
        for x in xs:
            for sy in (YF - 0.06, YB + 0.06):
                self.add(box("stud_", (x, sy, (z0 + z1) * 0.5),
                             (0.16, 0.10, z1 - z0), M["wood_dark"]), 0.006)
        for sx in (-1, 1):
            for k in range(7):
                yy = YB + 0.60 + k * 1.05
                self.add(box("stud_s", (sx * (W2 - 0.04), yy, (z0 + z1) * 0.5),
                             (0.10, 0.16, z1 - z0), M["wood_dark"]), 0.006)
        for sy in (YF - 0.05, YB + 0.05):
            self.add(box("tw_belt", (0, sy, z0 + 1.62), (W2 * 2 - 0.16, 0.09, 0.16),
                         M["wood_dark"]), 0.006)
        # 石角柱：木框四角仍由石头承重（这一条让"石木"读得通，而不是木盒子套石台）
        for sx in (-1, 1):
            for sy in (-1, 1):
                self.add(box("pier", (sx * (W2 - 0.26), sy * (YF - 0.26), (z0 + z1) * 0.5),
                             (0.52, 0.52, z1 - z0), M["stone_light"]), 0.018)
        # 檐下压梁（木）＋ 石压顶
        self.add(box("eave_beam", (0, 0, z1 - 0.06), (W2 * 2 + 0.24, YF - YB + 0.24, 0.20),
                     M["wood_dark"]), 0.014)
        self.add(box("eave_stone", (0, 0, z1 + 0.10), (W2 * 2 + 0.40, YF - YB + 0.40, 0.20),
                     M["stone_light"]), 0.014)

    # ── 4. 女儿墙 + 成组垛口 ────────────────────────────────────────────────
    def parapet(self):
        M = self.M
        z0 = H2 + 0.20
        z1 = z0 + PARA_H
        # 四段独立（转角由前后两段独占，避免同高顶面）
        self.add(box("para_b", (0, YB + PARA_T * 0.5, (z0 + z1) * 0.5),
                     (W2 * 2, PARA_T, PARA_H), M["stone_light"]), 0.018)
        self.add(box("para_f", (0, YF - PARA_T * 0.5, (z0 + z1) * 0.5),
                     (W2 * 2, PARA_T, PARA_H), M["stone_light"]), 0.018)
        for sx in (-1, 1):
            self.add(box("para_s", (sx * (W2 - PARA_T * 0.5), 0, (z0 + z1) * 0.5),
                         (PARA_T, YF - YB - PARA_T * 2, PARA_H), M["stone_light"]), 0.018)
        # 压顶（暗一档，压住女儿墙顶面）
        self.add(box("para_cap_b", (0, YB + PARA_T * 0.5, z1 + 0.055),
                     (W2 * 2 + 0.14, PARA_T + 0.14, 0.11), M["stone_dark"]), 0.010)
        self.add(box("para_cap_f", (0, YF - PARA_T * 0.5, z1 + 0.057),
                     (W2 * 2 + 0.14, PARA_T + 0.14, 0.11), M["stone_dark"]), 0.010)
        for sx in (-1, 1):
            self.add(box("para_cap_s", (sx * (W2 - PARA_T * 0.5), 0, z1 + 0.059),
                         (PARA_T + 0.14, YF - YB - PARA_T * 2 + 0.14, 0.11),
                         M["stone_dark"]), 0.010)
        # 垛口：每 2 个一组（组内缝 0.12、组间缺口 1.05）
        for (p0, d, ln) in (((-W2 + 0.30, YB + PARA_T * 0.5), (1, 0), W2 * 2 - 0.60),
                            ((-W2 + 0.30, YF - PARA_T * 0.5), (1, 0), W2 * 2 - 0.60),
                            ((-W2 + PARA_T * 0.5, YB + 0.30), (0, 1), YF - YB - 0.60),
                            ((W2 - PARA_T * 0.5, YB + 0.30), (0, 1), YF - YB - 0.60)):
            self.merlon_row("merlon", p0, d, ln, z1 + 0.11)
        # 队色：压顶上一道浅漆线（薄、外凸 5 mm，规则 K91）
        for sy in (YF - PARA_T * 0.5, YB + PARA_T * 0.5):
            self.add(box("team_line_b", (0, sy + (0.19 if sy > 0 else -0.19), z1 - 0.10),
                         (W2 * 2 + 0.02, 0.012, 0.15), M["team"]), 0.0)

    def merlon_row(self, name, p0, d, length, z0, group=2):
        M = self.M
        mw, gap_in, gap_out = 0.80, 0.12, 1.18
        unit = group * mw + (group - 1) * gap_in
        n = max(1, int((length + gap_out) / (unit + gap_out) + 1e-6))
        total = n * unit + (n - 1) * gap_out
        start = (length - total) * 0.5
        for g in range(n):
            gb = start + g * (unit + gap_out)
            for i in range(group):
                off = gb + i * (mw + gap_in) + mw * 0.5
                x = p0[0] + d[0] * off
                y = p0[1] + d[1] * off
                sx = mw * abs(d[1]) + (PARA_T - 0.09) * abs(d[0])
                sy = mw * abs(d[0]) + (PARA_T - 0.09) * abs(d[1])
                self.add(box(name, (x, y, z0 + 0.32), (sx, sy, 0.64), M["stone_mid"]), 0.010)

    # ── 5. 铁门（门廊 + 拱 + 双扇铁包木门 + 闸门齿）─────────────────────────
    def gate(self):
        M = self.M
        # 门廊：从墙面出挑 1.55 的实心体，中间真开一个同宽拱洞
        py0, py1 = YF - 0.05, YF + GPORCH
        for sx in (-1, 1):
            self.add(box("porch_jamb", (sx * (GW + 0.42), (py0 + py1) * 0.5, 2.35),
                         (0.84, py1 - py0, 4.70), M["stone_light"]), 0.024)
        # 门廊顶（拱上墙）
        self.add(box("porch_head", (0, (py0 + py1) * 0.5, GTOP + 0.62),
                     (GW * 2 + 1.68, py1 - py0, 1.24), M["stone_light"]), 0.024)
        self.add(box("porch_cap", (0, (py0 + py1) * 0.5, GTOP + 1.31),
                     (GW * 2 + 1.94, py1 - py0 + 0.18, 0.14), M["stone_mid"]), 0.012)
        # 门廊拱券（正面 + 内侧一圈）
        self.add(arch_band("gate_arch", 0.0, GSPR, GW, GW + 0.34, py1 - 0.16, py1 + 0.02,
                           M["stone_mid"], segs=10), 0.016)
        self.add(arch_band("gate_arch_in", 0.0, GSPR, GW, GW + 0.22, py0 + 0.02, py0 + 0.20,
                           M["stone_dark"], segs=10), 0.010)
        # 门楣铁箍 + 队色横带（第一道队色）
        self.add(box("gate_iron_band", (0, py1 + 0.06, GTOP + 0.34),
                     (GW * 2 + 1.30, 0.10, 0.20), M["iron"]), 0.008)
        self.add(box("gate_team", (0, py1 + 0.10, GTOP + 0.60),
                     (GW * 2 + 1.10, 0.05, 0.24), M["team"]), 0.0)
        self.add(box("gate_team_t", (0, py1 + 0.125, GTOP + 0.76),
                     (GW * 2 + 1.16, 0.03, 0.05), M["team_trim"]), 0.0)
        # 闸门齿（拱上方的铁栅，半落状态）
        for k in range(5):
            x = -GW + 0.27 + k * (GW * 2 - 0.54) / 4.0
            self.add(box("port_", (x, py1 - 0.34, GTOP - 0.22),
                         (0.10, 0.10, 0.66), M["iron"]), 0.0)
        # 双扇铁包木门（关着，各 1.32 宽）
        leaf = GW - 0.03
        for sgn in (-1, 1):
            cx = sgn * leaf * 0.5
            self.add(box("door_leaf", (cx, py1 - 0.42, (PL1 + GSPR) * 0.5 + 0.10),
                         (leaf - 0.01, 0.11, GSPR - PL1 - 0.10), M["wood_dark"]), 0.012)
            for zz in (1.55, 2.72, 3.86):
                self.add(box("door_iron", (cx, py1 - 0.34, zz),
                             (leaf - 0.14, 0.06, 0.14), M["iron"]), 0.004)
            self.add(box("door_stud", (cx - sgn * 0.34, py1 - 0.33, 2.20),
                         (0.10, 0.05, 0.10), M["iron"]), 0.0)
            self.add(box("door_ring", (cx - sgn * 0.18, py1 - 0.30, 2.55),
                         (0.10, 0.05, 0.24), M["gold"]), 0.0)
        self.add(box("door_seam", (0, py1 - 0.36, 2.20), (0.07, 0.12, 4.30),
                     M["iron"]), 0.0)
        # 门洞两侧的队色壁柱
        for sgn in (-1, 1):
            self.add(box("gate_pilaster", (sgn * (GW + 0.94), py1 - 0.02, 2.30),
                         (0.26, 0.16, 4.40), M["team"]), 0.008)
        # 门楣盾徽
        BR.Model.crest(self, "crest_gate", "Y", 0.0, py1 + 0.14, GTOP + 1.02, 0.52)

    # ── 6. 前角楼 ───────────────────────────────────────────────────────────
    def turret(self, sx):
        M = self.M
        x0 = sx * PX
        # 楼身（1.20–PTOP）：比主体出挑 0.55，四角一圈石线脚
        self.add(box("pt_body", (x0, PY, (PL1 + PTOP) * 0.5),
                     (PW * 2, PW * 2, PTOP - PL1), M["stone_mid"]), 0.024)
        for zz in (1.30, 4.72, 7.10):
            self.add(box("pt_band", (x0, PY, zz), (PW * 2 + 0.14, PW * 2 + 0.14, 0.16),
                         M["stone_mid"]), 0.010)
        # 箭孔：正面两道 + 外侧一道
        for zz in (2.55, 5.40):
            self.add(box("pt_slot", (x0, PY + PW + 0.02, zz), (0.20, 0.09, 0.92),
                         M["stone_dark"]), 0.0)
            self.add(box("pt_slot_x", (x0 + sx * (PW + 0.02), PY, zz), (0.09, 0.20, 0.92),
                         M["stone_dark"]), 0.0)
        # 女儿墙 + 压顶 + 3 个垛口
        z0, z1 = PTOP, PTOP + 0.78
        for (dx, dy, w, d) in ((0, PW - 0.15, PW * 2, 0.30), (0, -PW + 0.15, PW * 2, 0.30),
                               (PW - 0.15, 0, 0.30, PW * 2 - 0.60),
                               (-PW + 0.15, 0, 0.30, PW * 2 - 0.60)):
            self.add(box("pt_para", (x0 + dx, PY + dy, (z0 + z1) * 0.5), (w, d, 0.78),
                         M["stone_light"]), 0.016)
        self.add(box("pt_cap", (x0, PY, z1 + 0.05), (PW * 2 + 0.16, PW * 2 + 0.16, 0.10),
                     M["stone_dark"]), 0.010)
        for k, ddx in enumerate((-1.05, 0.0, 1.05)):
            for ddy in (PW - 0.15, -PW + 0.15):
                self.add(box("pt_merlon", (x0 + ddx, PY + ddy, z1 + 0.30),
                             (0.62, 0.28, 0.50), M["stone_mid"]), 0.008)
        # 角楼顶：两级截头金字塔 + 金顶（与中央塔同一套语法，只是更小）
        for (za, zb, wa, wb, mat) in ((PT0, 12.02, PW * 2 - 0.04, 1.58, M["roof"]),
                                      (12.02, 12.74, 1.62, 0.52, M["roof_edge"])):
            self.add(frustum("pt_roof", za, zb, wa, wa, wb, wb, x0, PY, mat), 0.014)
        for sx2 in (-1, 1):
            for sy in (-1, 1):
                self.add(beam("pt_hip", (x0 + sx2 * (PW - 0.02), PY + sy * (PW - 0.02), PT0),
                              (x0 + sx2 * 0.16, PY + sy * 0.16, 12.76),
                              0.10, 0.08, M["roof_pale"]), 0.004)
        self.add(box("pt_finial", (x0, PY, 12.84), (0.30, 0.30, 0.16), M["gold"]), 0.006)

    # ── 7. 中央方塔 ─────────────────────────────────────────────────────────
    def tower(self):
        M = self.M
        z0 = H2 + 0.20
        self.add(box("tw_body", (TCX, TCY, (z0 + TTOP) * 0.5),
                     (TW * 2, TW * 2, TTOP - z0), M["stone_mid"]), 0.026)
        # 竖向壁柱（四角 + 每面中间两根）
        for sx in (-1, 1):
            for k in (-1, 0, 1):
                self.add(box("tw_pier", (TCX + sx * TW - sx * 0.22, TCY + k * 1.45,
                                         (z0 + TTOP) * 0.5),
                             (0.44, 0.30, TTOP - z0), M["stone_mid"]), 0.012)
        for zz in (z0 + 1.10, TTOP - 0.55):
            self.add(box("tw_belt", (TCX, TCY, zz), (TW * 2 + 0.16, TW * 2 + 0.16, 0.18),
                         M["stone_mid"]), 0.010)
        # 窗：每面三扇（拱顶窄窗）
        for k in (-1, 0, 1):
            for sy in (1, -1):
                self.add(box("tw_win", (TCX + k * 1.30, TCY + sy * (TW + 0.02), 11.20),
                             (0.44, 0.09, 1.30), M["stone_dark"]), 0.0)
                self.add(box("tw_win_g", (TCX + k * 1.30, TCY + sy * (TW + 0.03), 11.20),
                             (0.30, 0.07, 1.10), M["glass"]), 0.0)
            for sx in (1, -1):
                self.add(box("tw_win_x", (TCX + sx * (TW + 0.02), TCY + k * 1.30, 11.20),
                             (0.09, 0.44, 1.30), M["stone_dark"]), 0.0)
        # 女儿墙 + 垛口 + 压顶
        z1 = TTOP + 0.80
        for (dx, dy, w, d) in ((0, TW - 0.18, TW * 2, 0.36), (0, -TW + 0.18, TW * 2, 0.36),
                               (TW - 0.18, 0, 0.36, TW * 2 - 0.72),
                               (-TW + 0.18, 0, 0.36, TW * 2 - 0.72)):
            self.add(box("tw_para", (TCX + dx, TCY + dy, (TTOP + z1) * 0.5),
                         (w, d, 0.80), M["stone_light"]), 0.018)
        self.add(box("tw_cap", (TCX, TCY, z1 + 0.05), (TW * 2 + 0.18, TW * 2 + 0.18, 0.10),
                     M["stone_dark"]), 0.010)
        for k, ddx in enumerate((-1.55, -0.52, 0.52, 1.55)):
            for ddy in (TW - 0.18, -TW + 0.18):
                self.add(box("tw_merlon", (TCX + ddx, TCY + ddy, z1 + 0.30),
                             (0.66, 0.34, 0.48), M["stone_mid"]), 0.008)
        # 塔顶：**两级截头金字塔**（不是阶梯台）。
        # 阶梯台在 RTS 距离上读成"婚礼蛋糕"（每一级都是一条水平亮线）；
        # 两级陡坡 + 金顶才是"戍堡"的读法，也和九座的坡 / 平 / 穹 / 攒尖都不撞。
        for (za, zb, wa, wb, mat) in ((TT0, 14.45, TW * 2 - 0.04, 3.18, M["roof"]),
                                      (14.45, 15.52, 3.28, 0.98, M["roof_edge"])):
            self.add(frustum("tw_roof", za, zb, wa, wa, wb, wb, TCX, TCY, mat), 0.016)
        # 四条戗脊（亮脊）：深色屋面上没有这道线，俯视就是一个黑三角
        for sx in (-1, 1):
            for sy in (-1, 1):
                self.add(beam("tw_hip", (TCX + sx * (TW - 0.04), TCY + sy * (TW - 0.04), TT0),
                              (TCX + sx * 0.30, TCY + sy * 0.30, 15.54),
                              0.13, 0.10, M["roof_pale"]), 0.006)
        self.add(box("tw_top", (TCX, TCY, 15.62), (0.54, 0.54, 0.18), M["gold"]), 0.008)
        # 队色：塔身女儿墙压顶下一道（第二道队色）
        self.add(box("tw_team", (TCX, TCY, TTOP + 0.44),
                     (TW * 2 + 0.04, TW * 2 + 0.04, 0.12), M["team"]), 0.0)

    # ── 8. 窗（石层 / 木层）────────────────────────────────────────────────
    def windows(self):
        M = self.M
        # 石砌一层：四扇窄拱窗（前 2 / 侧各 1），开在墙面上（贴片，凸 30 mm）
        for k, x in enumerate((-3.10, 3.10)):
            self.add(box("win1", (x, YF + 0.05, 2.55), (0.52, 0.10, 1.30), M["stone_dark"]), 0.0)
            self.add(box("win1_g", (x, YF + 0.07, 2.55), (0.36, 0.08, 1.12), M["glass"]), 0.0)
            self.add(box("win1_sill", (x, YF + 0.10, 1.86), (0.68, 0.16, 0.10),
                         M["stone_light"]), 0.006)
        for sx in (-1, 1):
            for y in (-1.60, 1.60):
                self.add(box("win1_s", (sx * (W2 + 0.05), y, 2.55),
                             (0.10, 0.52, 1.30), M["stone_dark"]), 0.0)
                self.add(box("win1_sg", (sx * (W2 + 0.07), y, 2.55),
                             (0.08, 0.36, 1.12), M["glass"]), 0.0)
        # 木框层：五扇大窗（前 3 / 侧各 1）
        for k, x in enumerate((-3.30, 0.0, 3.30)):
            self.add(box("win2", (x, YF + 0.02, 7.55), (1.05, 0.10, 1.35), M["glass"]), 0.0)
            for (dx, dz, w, h) in ((0, 0.72, 1.20, 0.10), (0, -0.72, 1.20, 0.10),
                                   (-0.57, 0, 0.10, 1.45), (0.57, 0, 0.10, 1.45)):
                self.add(box("win2_f", (x + dx, YF + 0.07, 7.55 + dz), (w, 0.08, h),
                             M["wood_dark"]), 0.004)
            self.add(box("win2_munt", (x, YF + 0.07, 7.55), (0.06, 0.08, 1.30),
                         M["wood_dark"]), 0.002)
        for sx in (-1, 1):
            for y in (0.0,):
                self.add(box("win2_s", (sx * (W2 - 0.02), y, 7.55),
                             (0.10, 1.00, 1.30), M["glass"]), 0.0)
                for (dy, dz, w, h) in ((0, 0.70, 1.14, 0.10), (0, -0.70, 1.14, 0.10),
                                       (-0.54, 0, 0.10, 1.40), (0.54, 0, 0.10, 1.40)):
                    self.add(box("win2_sf", (sx * (W2 - 0.04), y + dy, 7.55 + dz),
                                 (0.08, w, h), M["wood_dark"]), 0.004)

    # ── 9. 队色 / 旗 / 火盆 ─────────────────────────────────────────────────
    def heraldry(self):
        M = self.M
        # 塔身正面两幅垂旗（队色，竖向构件，只做补充，不做主力色源，规则 K87）
        for sx in (-1, 1):
            cx = TCX + sx * 1.62
            self.add(box("banner_pole", (cx, TCY + TW + 0.10, 11.85), (0.07, 0.07, 1.90),
                         M["wood_dark"]), 0.004)
            self.add(box("banner_arm", (cx, TCY + TW + 0.35, 12.72), (0.06, 0.62, 0.06),
                         M["wood_dark"]), 0.004)
            self.add(box("banner_cloth", (cx, TCY + TW + 0.62, 12.10),
                         (0.72, 0.04, 1.20), M["team"]), 0.004)
            self.add(box("banner_trim", (cx, TCY + TW + 0.64, 11.52),
                         (0.68, 0.03, 0.06), M["team_trim"]), 0.0)
        # 门廊两侧火盆（铁盆 + 炭火）
        for sx in (-1, 1):
            bx = sx * (GW + 1.62)
            self.add(box("braz_base", (bx, YF + 0.70, PL1 + 0.10), (0.46, 0.46, 0.20),
                         M["stone_mid"]), 0.008)
            self.add(revolve("braz_bowl", [(0.30, 0.0), (0.34, 0.10), (0.26, 0.26)],
                             8, (bx, YF + 0.70, PL1 + 0.20), M["iron"]), 0.008)
            self.add(revolve("braz_coal", [(0.22, 0.0), (0.20, 0.06)],
                             8, (bx, YF + 0.70, PL1 + 0.38), M["ember"]), 0.0)
            for k in range(3):
                a = TAU * k / 3
                self.add(taper_box("braz_flame",
                                   (bx + math.cos(a) * 0.08, YF + 0.70 + math.sin(a) * 0.08,
                                    PL1 + 0.40),
                                   (bx + math.cos(a) * 0.03, YF + 0.70 + math.sin(a) * 0.03,
                                    PL1 + 0.86 + 0.08 * k),
                                   0.12, 0.02, 0.12, 0.02, M["flame_in"]), 0.0)

    # ── 组装 ────────────────────────────────────────────────────────────────
    def build(self):
        for step in (self.base, self.stone_body, self.timber_body, self.parapet,
                     self.gate, self.tower, self.windows, self.heraldry):
            step()
        self.turret(-1)
        self.turret(1)
        return self


def build(smooth=True, unwrap=True, bevel=True):
    m = Model(smooth, unwrap).build()
    objs = m.finalize(bevel=bevel)
    return objs, L.stats(objs)
