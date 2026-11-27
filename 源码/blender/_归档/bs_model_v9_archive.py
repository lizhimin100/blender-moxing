"""
bs_model.py —— 铁匠铺 v8 的形体定义（低模）

v8 只做一件事：让它在 RTS 俯视角里一眼就是"铁匠铺"，而不是"带烟囱的民房"。
所有改动都挂在三条主线上：

  ① 屋顶不再是民居双坡
     - 锻造区上方加**独立外伸的作业坡棚**（26°，4.16 m 宽，跨度 3.34 m）：
       厚封檐板 + 两道斜撑 + 9 根露明椽条，形成"作坊前棚"的阴影带；
     - 主屋脊加**铁艺脊饰**：通长铁压条 + **脊上楼阁**（四面百叶排烟阁）+
       山墙尖**锻锤与火钳铁艺立饰**（不再用十字，十字会读成教堂）；
     - 山墙百叶通风口保留并放大。

  ② 烟囱收分
     - 方胸墙 1.50 → 上部收成**八角筒身 0.92 m**，三级石箍 + 铁箍 + 阵营色箍，
       顶部铁烟罩 + 风向标；体量比 v6 窄 45%，不再是一根方柱。

  ③ 前场与火光
     - 中央重型铁砧（树桩 + 砧上锤 + **砧面红热锻件**）、两侧立式工具架、
       左侧战斧 / 右侧长剑靠墙、淬火桶、煤桶 ×2、铁锭筐、磨石、原木堆；
     - 炉膛内加**锥形排烟罩**（火 → 罩 → 屋顶黑铁烟管），火光有出处；
     - 主入口 1.28 → 1.95 m 宽、拱高 2.15 m，门扇内开、门槛里透暖光。

  ④ 阵营色：6 个标准模块 + 5 条构件饰带，尺寸统一、可整套替换。

坐标系：X 右、Y 前（+Y = 正面）、Z 上；原点在占地中心，z = 0 地面。
建模期左侧（−X）放门廊翼、右侧（+X）放炉膛龛与烟囱；交付前整体沿 X 镜像一次。
"""
import math
import random

import bpy

import bslib as L
from bslib import (arch_band, beam, box, cone, cyl, extrude, frustum, kite_shield,
                   lathe, mesh_obj, octa_profile, revolve, ring_y, slab_plate,
                   taper_box, tube_band)

# ── 主尺度 ────────────────────────────────────────────────────────────────────
W2 = 4.00
YF = 3.00
YB = -3.40
EAVE = 4.70
RIDGE_Z = 8.75                       # 45.4°，比 v6 的 41° 更陡
OV = 0.34
SLOPE = (RIDGE_Z - EAVE) / W2
ROOF_T = 0.17

# 炉膛龛（凸出的敞口石龛）
BAY_X0, BAY_X1 = -1.52, 2.30
BAY_CX = (BAY_X0 + BAY_X1) * 0.5     # 0.29
BAY_R = (BAY_X1 - BAY_X0) * 0.5      # 2.01
BAY_Y0 = 2.98
BAY_Y1 = 5.30
BAY_SPRING = 1.80
BAY_TOP = 4.14
BAY_T = 0.30

# 独立作业坡棚（前棚）
CAN_X0, CAN_X1 = -1.80, 2.56
CAN_Y0, CAN_Y1 = 3.06, 5.98      # 后端退到墙面（3.00）之外：坡棚板是"贴墙"而不是插穿墙
CAN_Z0, CAN_Z1 = 5.58, 4.02
CAN_T = 0.17
CAN_ANG = math.atan2(CAN_Z0 - CAN_Z1, CAN_Y1 - CAN_Y0)

# 烟囱：方胸墙 → 八角筒身
CH_X0, CH_X1 = 2.52, 4.02
CH_Y0, CH_Y1 = 3.44, 4.58
CH_CX = (CH_X0 + CH_X1) * 0.5        # 3.27
CH_CY = (CH_Y0 + CH_Y1) * 0.5        # 4.01
CH_BREAST_TOP = 5.72          # 必须高过坡棚板后端（5.58），否则屋面会从墙顶"冒出来"
CH_SHAFT_R = 0.46
CH_SHAFT_TOP = 9.55

# 门廊翼
WING_X0, WING_X1 = -4.16, -1.70
WING_CX = (WING_X0 + WING_X1) * 0.5  # -2.93
WING_Y1 = 5.44
WING_EAVE = 3.52
WING_RIDGE = 6.02          # cross gable：脊高出主屋面 0.24；翼屋面从 y=3.40 起，不进主屋面
PORCH_Y1 = 6.30
DOOR_W, DOOR_ARCH = 1.85, 1.35          # 门宽 / 拱脚高（拱顶 = 拱脚 + 门宽/2 ≈ 2.28 m）

# 脊上楼阁
CUP_Y = -1.55
CUP_W = 0.78

# 阵营色标准模块（形制统一：盾 / 垂旗 / 墙面横幅）
SHIELD_W, SHIELD_H = 1.38, 1.70
SHIELD_S = 0.84, 1.02
BANNER_W, BANNER_H = 0.66, 1.35
WALLBAN_W, WALLBAN_H = 1.95, 2.35


def zroof(x):
    return RIDGE_Z - SLOPE * abs(x)


def can_z(y):
    t = (y - CAN_Y0) / (CAN_Y1 - CAN_Y0)
    return CAN_Z0 + t * (CAN_Z1 - CAN_Z0)


def arch_profile(w, h, segs=8):
    hw = w * 0.5
    pts = [(-hw, 0.0), (hw, 0.0), (hw, h)]
    for s in range(1, segs):
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

    # ── 1. 基座与前场石台 ───────────────────────────────────────────────────
    def base(self):
        M = self.M
        self.add(box("plinth_a", (0, -0.20, 0.13), (9.10, 7.10, 0.26), M["stone_dark"]))
        self.add(box("plinth_b", (0, -0.20, 0.06), (9.44, 7.44, 0.12), M["stone_mid"]))
        # 前场石台：从炉膛龛前沿（y=5.28）一直铺到院沿，别与龛内地面打架
        self.add(box("yard", (0.00, 6.52, 0.13), (9.20, 2.50, 0.26), M["stone_mid"]), 0.030)
        self.add(box("yard_kerb", (0.00, 7.79, 0.085), (9.20, 0.18, 0.17), M["stone_dark"]), 0.020)
        # 前场铺装：两条深浅不同的石带，破一破"一整块灰板"
        for i, (yy, ww, mat) in enumerate(((6.00, 0.34, "stone_light"), (7.04, 0.22, "stone_dark"))):
            self.add(box("yard_band%d" % i, (0.00, yy, 0.265), (9.10, ww, 0.03), M[mat]), 0.004)
        # 石板缝：把"一整块灰板"切成铺装
        for i, xx in enumerate((-3.10, -1.55, 0.30, 2.05, 3.55)):
            self.add(box("yard_joint%d" % i, (xx, 6.52, 0.272), (0.06, 2.40, 0.03),
                         M["stone_dark"]), 0.0)
        # 门槛石
        self.add(box("threshold", (WING_CX, 5.42, 0.24), (DOOR_W + 0.30, 0.30, 0.08),
                     M["stone_light"]), 0.010)

    # ── 2. 墙体 ─────────────────────────────────────────────────────────────
    def mass(self):
        M = self.M
        pent = [(-W2, 0.0), (W2, 0.0), (W2, EAVE), (0.0, RIDGE_Z), (-W2, EAVE)]
        self.add(extrude("mass", pent, "Y", YF - YB, (0, 0),
                         M["stone_light"], offset=(YF + YB) * 0.5), 0.035)
        for sx in (-1, 1):
            for sy, yface in ((1, YF), (-1, YB)):
                if sx < 0 and sy > 0:
                    continue          # 正面左角被门廊翼包住，隅石会从翼屋面里戳出来
                for i in range(5):
                    zz = 0.62 + i * 0.88
                    if zz > EAVE - 0.30:
                        break
                    self.add(box("quoin", (sx * (W2 - 0.16), yface - sy * 0.18, zz),
                                 (0.44 + (0.06 if i % 2 else 0.0), 0.42, 0.46), M["stone_mid"]))
        self.add(box("dado", (0, -0.20, 0.90), (8.06, 6.56, 1.32), M["stone_mid"]))
        for zz in (1.58, 3.74):
            self.add(box("string", (0, -0.20, zz), (8.26, 6.76, 0.14), M["stone_mid"]))
        # 侧墙扶壁（背影）
        for sx in (-1, 1):
            for yy in (-2.05, -3.20):
                self.add(box("buttress", (sx * (W2 + 0.13), yy, EAVE * 0.5),
                             (0.26, 0.55, EAVE - 0.35), M["stone_mid"]), 0.024)

    # ── 3. 炉膛龛（石拱敞口）────────────────────────────────────────────────
    def forge_bay(self):
        M = self.M
        cx, r, y1 = BAY_CX, BAY_R, BAY_Y1
        yf = y1 - BAY_T
        # 侧墙：顶面跟着坡棚走
        for sgn in (-1, 1):
            if sgn < 0:
                continue                       # 左侧被门廊翼占住，不重复砌
            prof = [(BAY_Y0, 0.0), (y1 - 0.02, 0.0), (y1 - 0.02, BAY_TOP), (BAY_Y0, can_z(BAY_Y0) - 0.16)]
            self.add(extrude("bay_wall", prof, "X", BAY_T, (0, 0), M["stone_mid"],
                             offset=cx + sgn * (r + BAY_T * 0.5)), 0.026)
        # 正面拱券墙（拱洞 + 拱上墙体）
        segs = 10
        verts, faces = [], []
        for s in range(segs + 1):
            a = math.pi * s / segs
            x = cx + r * math.cos(a)
            z = BAY_SPRING + r * math.sin(a)
            verts += [(x, yf, z), (x, yf, BAY_TOP), (x, y1, BAY_TOP), (x, y1, z)]
        for s in range(segs):
            b, b2 = s * 4, (s + 1) * 4
            faces += [(b + 0, b2 + 0, b2 + 1, b + 1),
                      (b + 1, b2 + 1, b2 + 2, b + 2),
                      (b + 2, b2 + 2, b2 + 3, b + 3)]
        faces.append((0, 1, 2, 3))
        faces.append((segs * 4 + 3, segs * 4 + 2, segs * 4 + 1, segs * 4))
        self.add(mesh_obj("bay_face", verts, faces, M["stone_light"]), 0.026)
        # 拱券石圈 + 拱心石
        self.add(arch_band("bay_arch", cx, BAY_SPRING, r, r + 0.30, y1 - 0.02, y1 + 0.16,
                           M["stone_light"], segs=10), 0.022)
        self.add(box("keystone", (cx, y1 + 0.10, BAY_SPRING + r - 0.04), (0.36, 0.26, 0.46),
                     M["stone_mid"]), 0.018)
        # 拱上阵营色檐带 + 石压顶（v7 的"蓝色月牙"问题：改成竖直的平檐带）
        self.add(box("bay_frieze", (cx, y1 + 0.04, 4.02), (r * 2 + 0.16, 0.14, 0.16),
                     M["team"]), 0.010)
        self.add(box("bay_cornice", (cx, y1 + 0.07, 4.11), (r * 2 + 0.26, 0.20, 0.10),
                     M["stone_light"]), 0.012)
        # 翼与炉膛龛之间的转角石柱：把"翼屋面 / 拱券 / 龛壁"三者的接缝收进石头里
        self.add(box("bay_pier", (-1.68, 5.18, 2.08), (0.36, 0.52, 4.16), M["stone_light"]), 0.020)
        self.add(box("bay_pier_cap", (-1.68, 5.18, 4.16), (0.46, 0.62, 0.16), M["stone_mid"]), 0.012)
        # 龛内
        self.add(box("bay_floor", (cx, (BAY_Y0 + y1) * 0.5, 0.10), (r * 2, y1 - BAY_Y0, 0.20),
                     M["stone_dark"]))
        self.add(box("bay_back", (cx + 0.08, BAY_Y0 + 0.12, BAY_TOP * 0.5), (r * 2 + 0.44, 0.24, BAY_TOP - 0.02),
                     M["stone_dark"]))
        for sgn in (-1, 1):
            self.add(box("bay_cheek", (cx + sgn * (r - 0.11), (BAY_Y0 + y1) * 0.5, 1.98),
                         (0.12, y1 - BAY_Y0, 3.92), M["stone_dark"]), 0.010)

    # ── 4. 独立作业坡棚 ─────────────────────────────────────────────────────
    def work_canopy(self):
        M = self.M
        cx = (CAN_X0 + CAN_X1) * 0.5
        w = CAN_X1 - CAN_X0
        # 棚面比主屋面暗一档 + 细密板缝：俯视时是"另一种屋面"，但不会跳成条纹雨棚
        # 木瓦顶：俯视角下和主屋的冷色板岩形成两个色块 —— 这是"作坊 + 主屋"最省的读法
        self.add(slab_plate("canopy", M["roof_wood"], CAN_X0, CAN_X1, CAN_Y0, CAN_Y1,
                            CAN_Z0, CAN_Z1, CAN_T), 0.024)
        # 瓦垄
        # 木板坡顶：和主屋的板岩屋面拉开材质（俯视时一眼是"作坊棚"，不是第二片屋顶）
        ny, nz = math.sin(CAN_ANG), math.cos(CAN_ANG)
        for i in range(8):
            yy = CAN_Y0 + 0.22 + (CAN_Y1 - CAN_Y0 - 0.44) * i / 7.0
            zz = can_z(yy)
            off = CAN_T + 0.018
            self.add(box("canopy_plank", (cx, yy + ny * off, zz + nz * off),
                         (w - 0.05, 0.115, 0.045), M["wood_dark"], rot=(-CAN_ANG, 0, 0)), 0.005)
        # 露明椽条
        for i in range(9):
            xx = CAN_X0 + 0.22 + i * (w - 0.44) / 8.0
            self.add(beam("canopy_rafter", (xx, CAN_Y0 + 0.04, can_z(CAN_Y0) - 0.14),
                          (xx, CAN_Y1 + 0.10, can_z(CAN_Y1) - 0.22), 0.10, 0.12,
                          M["wood_dark"]), 0.008)
        # 前檐大梁 + 封檐板 + 阵营色饰条
        zf = can_z(CAN_Y1) - 0.16
        self.add(box("canopy_beam", (cx, CAN_Y1 - 0.10, zf), (w + 0.06, 0.24, 0.28),
                     M["wood_warm"]), 0.018)
        self.add(box("canopy_fascia", (cx, CAN_Y1 + 0.06, zf + 0.02), (w + 0.04, 0.15, 0.30),
                     M["wood_warm"]), 0.016)
        self.add(box("canopy_trim", (cx, CAN_Y1 + 0.14, zf - 0.10), (w, 0.05, 0.07),
                     M["team"]), 0.006)
        # 两道斜撑 / 托牙（挂在拱券之上的压顶外沿，绝不横跨炉口）
        for xx in (CAN_X0 + 0.16, CAN_X1 - 0.16):
            self.add(beam("canopy_strut", (xx, BAY_Y1 + 0.06, 4.20),
                          (xx, CAN_Y1 - 0.24, zf - 0.12), 0.16, 0.14, M["wood_dark"]), 0.012)
        # 后檐压条
        self.add(box("canopy_head", (cx, CAN_Y0 - 0.02, CAN_Z0 + 0.02), (w + 0.04, 0.16, 0.18),
                     M["wood_dark"]), 0.014)

    # ── 5. 炉膛排烟罩 + 屋顶黑铁烟管 ────────────────────────────────────────
    def forge_hood(self):
        M = self.M
        cx, cy = 0.29, 4.46
        bz, tz = 2.62, 4.42
        bw, bd = 1.64, 1.34
        tw, td = 0.80, 0.70
        verts = [(cx - bw * .5, cy - bd * .5, bz), (cx + bw * .5, cy - bd * .5, bz),
                 (cx + bw * .5, cy + bd * .5, bz), (cx - bw * .5, cy + bd * .5, bz),
                 (cx - tw * .5, cy - td * .5, tz), (cx + tw * .5, cy - td * .5, tz),
                 (cx + tw * .5, cy + td * .5, tz), (cx - tw * .5, cy + td * .5, tz)]
        faces = [(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7), (4, 5, 6, 7)]
        self.add(mesh_obj("hood", verts, faces, M["stone_dark"]), 0.016)
        # 罩口铁箍 + 内膛黑烟道
        self.add(box("hood_rim", (cx, cy, bz + 0.02), (bw + 0.08, bd + 0.08, 0.10), M["iron"]), 0.010)
        # 罩身中段铁箍：把 1.8 m 的斜面切成两段，读"烟罩"而不是"灯罩"
        mw, md = (bw + tw) * 0.5 + 0.05, (bd + td) * 0.5 + 0.05
        self.add(box("hood_band", (cx, cy, (bz + tz) * 0.5), (mw, md, 0.07), M["iron"]), 0.006)
        self.add(box("hood_throat", (cx, cy, tz - 0.06), (tw - 0.10, td - 0.10, 0.10),
                     M["coal"]), 0.006)
        # 罩口内壁的余温（自发光薄片，引擎里不用补灯也有"热"）
        self.add(box("hood_heat", (cx, cy + 0.30, bz + 0.30), (bw - 0.34, 0.03, 0.34),
                     M["ember"]), 0.0)
        # 黑铁排烟管：穿出坡棚，是"这栋楼在烧火"的最短信号
        self.add(revolve("flue_pipe", [(0.19, 0.0), (0.19, 2.62)], 8, (cx, cy, tz - 0.06),
                         M["iron"]), 0.0, 1)
        self.add(tube_band("flue_collar", (cx, cy), 0.17, 0.28, 4.90, 5.00, 10, M["iron"]), 0.004)
        # 排烟口基座：读"铁件"，不是"火" --------------------------------------------------
        # v8.9 这里是 1.04 × 0.86 的发光顶盖（ember），正面看就是一块橙板 —— 分不清是铁还是火。
        # 现在去掉自发光：铁框（0.88 × 0.78 × 0.22）+ 暗底 + 四角铆钉，烟管从中间穿出。
        vz = can_z(cy) + 0.02
        self.add(box("vent_curb", (cx, cy, vz + 0.07), (0.88, 0.78, 0.22), M["iron"]), 0.010)
        self.add(box("vent_well", (cx, cy, vz + 0.15), (0.70, 0.60, 0.04), M["coal"]), 0.0)
        for sx in (-1, 1):
            for sy in (-1, 1):
                self.add(box("vent_rivet", (cx + sx * 0.36, cy + sy * 0.31, vz + 0.19),
                             (0.07, 0.07, 0.07), M["iron"]), 0.003)
        # 烟管两道铁箍：让 2.1 m 长的黑管读成"烟囱"，不是"一根杆"
        for zz in (5.52, 6.28):
            self.add(tube_band("flue_band", (cx, cy), 0.185, 0.235, zz, zz + 0.08, 8, M["iron"]), 0.004)
        self.add(revolve("flue_cap", [(0.36, 0.0), (0.32, 0.06), (0.05, 0.30)], 8,
                         (cx, cy, 6.98), M["iron"]), 0.0, 1)

    # ── 6. 炉火 ─────────────────────────────────────────────────────────────
    def forge_fire(self):
        M = self.M
        cx, cy = 0.29, 4.40
        z0 = 0.20
        # 石火塘
        self.add(lathe("hearth", [(0.00, 0.00, cx, cy), (0.80, 0.00, cx, cy),
                                  (0.86, 0.18, cx, cy), (0.78, 0.46, cx, cy),
                                  (0.66, 0.56, cx, cy), (0.62, 0.58, cx, cy)],
                       14, M["stone_mid"]), 0.018, 1)
        # 炭床 + 炭块 + 炉栅
        self.add(lathe("coal_bed", [(0.00, 0.00, cx, cy), (0.62, 0.00, cx, cy),
                                    (0.58, 0.10, cx, cy), (0.00, 0.14, cx, cy)],
                       14, M["ember"]), 0.008, 1)
        self.add(tube_band("hearth_rim", (cx, cy), 0.72, 0.80, z0 + 0.50, z0 + 0.56, 14,
                           M["coal"]), 0.004, 1)
        rnd = random.Random(7)
        for i in range(9):
            a = rnd.random() * math.tau
            rr = 0.12 + rnd.random() * 0.42
            self.add(box("coal_lump", (cx + math.cos(a) * rr, cy + math.sin(a) * rr,
                                       z0 + 0.60 + rnd.random() * 0.05),
                         (0.20, 0.18, 0.13), M["coal"],
                         rot=(rnd.random(), rnd.random(), rnd.random())), 0.008)
        for i in range(3):
            self.add(box("grate", (cx, cy - 0.28 + i * 0.28, z0 + 0.70), (1.10, 0.07, 0.07),
                         M["iron"]), 0.004)
        # 火舌：外焰歪、内焰亮，靠 lathe 的逐环偏移"卷"起来
        tongues = (
            # (dx, dy, r, h, lean_x, lean_y, phase)
            (0.00, 0.00, 0.38, 1.62, 0.30, -0.06, 0.0),
            (0.52, -0.20, 0.24, 1.06, -0.16, 0.04, 0.5),
            (-0.46, 0.16, 0.22, 0.92, 0.14, 0.10, 0.9),
            (0.14, 0.42, 0.19, 0.74, -0.08, -0.14, 1.4),
            (-0.18, -0.38, 0.17, 0.58, 0.06, 0.06, 2.0),
        )
        prof = ((1.00, 0.00, 0.00), (0.90, 0.26, 0.06), (0.70, 0.52, 0.22),
                (0.44, 0.74, 0.48), (0.24, 0.90, 0.72), (0.10, 0.98, 0.90), (0.00, 1.00, 1.0))
        # 后层：暗红火体（体积感）
        for i, (dx, dy, rr, hh, lx, ly) in enumerate(
                ((0.00, -0.18, 0.42, 1.34, 0.12, 0.00),
                 (-0.36, -0.08, 0.28, 0.92, 0.10, 0.04),
                 (0.37, -0.02, 0.26, 0.82, -0.09, 0.00))):
            x, y = cx + dx, cy + dy
            rings = [(rr * a, z0 + 0.66 + hh * b, x + lx * c, y + ly * c) for (a, b, c) in prof]
            self.add(lathe("flame_%d" % i, rings, 7, M["flame_out"], phase=i * 0.7), 0.0, 1)
        # 前层：亮黄火舌（整体前移 0.3 m，绝不会被暗焰包住 —— 上一版内焰被吞掉就是这个原因）
        for i, (dx, dy, rr, hh, lx, ly) in enumerate(
                ((0.02, 0.24, 0.14, 1.10, 0.10, 0.00),
                 (-0.22, 0.20, 0.10, 0.78, -0.05, 0.03),
                 (0.24, 0.22, 0.09, 0.68, -0.04, 0.02),
                 (-0.02, 0.32, 0.07, 0.46, 0.03, 0.00))):
            x, y = cx + dx, cy + dy
            rings = [(rr * a, z0 + 0.66 + hh * b, x + lx * c, y + ly * c) for (a, b, c) in prof]
            self.add(lathe("flametip_%d" % i, rings, 6, M["flame_in"], phase=i * 1.1), 0.0, 1)
        # 龛内洗墙（低强度，别做成灯箱）；地面光池交给引擎里的点光，不烘自发光面
        self.add(box("fire_wash", (cx, 3.16, 1.55), (2.40, 0.03, 1.60), M["glow"]))

    # ── 7. 烟囱 ─────────────────────────────────────────────────────────────
    def chimney(self):
        M = self.M
        cx, cy = CH_CX, CH_CY
        w, d = CH_X1 - CH_X0, CH_Y1 - CH_Y0
        # 方胸墙
        self.add(box("ch_breast", (cx, cy, CH_BREAST_TOP * 0.5), (w, d, CH_BREAST_TOP),
                     M["stone_mid"]), 0.030)
        self.add(box("ch_plinth", (cx, cy, 0.56), (w + 0.10, d + 0.10, 1.12), M["stone_light"]), 0.024)
        for zz in (2.05, 3.05, 4.05, 5.05):   # v9：胸墙抬到 5.72 后补一道石带，别让盾上方空一片
            self.add(box("ch_string", (cx, cy, zz), (w + 0.07, d + 0.07, 0.10),
                         M["stone_light"]), 0.010)
        self.add(box("ch_cornice", (cx, cy, CH_BREAST_TOP - 0.09), (w + 0.26, d + 0.26, 0.18),
                     M["stone_light"]), 0.016)
        # 八角筒身（收分 1.50 → 0.92 m）
        self.add(extrude("ch_corbel", octa_profile(0.60), "Z", 0.20, (cx, cy),
                         M["stone_light"], offset=CH_BREAST_TOP + 0.06), 0.014)
        self.add(extrude("ch_shaft", octa_profile(CH_SHAFT_R), "Z",
                         CH_SHAFT_TOP - CH_BREAST_TOP, (cx, cy), M["stone_mid"],
                         offset=(CH_BREAST_TOP + CH_SHAFT_TOP) * 0.5), 0.024)
        self.add(extrude("ch_stage", octa_profile(CH_SHAFT_R + 0.07), "Z", 0.16, (cx, cy),
                         M["stone_light"], offset=8.55), 0.012)
        # 铁箍 + 阵营色箍
        ph = math.tau / 16
        for zz in (6.02, 7.05, 8.10):
            self.add(tube_band("ch_hoop", (cx, cy), CH_SHAFT_R - 0.01, CH_SHAFT_R + 0.05,
                               zz, zz + 0.09, 8, M["iron"], phase=ph), 0.006)
        self.add(tube_band("ch_band", (cx, cy), CH_SHAFT_R - 0.02, CH_SHAFT_R + 0.09,
                           6.38, 6.74, 8, M["team"], phase=ph), 0.010)
        self.add(tube_band("ch_band2", (cx, cy), CH_SHAFT_R - 0.02, CH_SHAFT_R + 0.05,
                           6.74, 6.84, 8, M["team_trim"], phase=ph), 0.008)
        # 铁烟罩
        top = CH_SHAFT_TOP
        self.add(extrude("ch_cap_plate", octa_profile(0.66), "Z", 0.10, (cx, cy),
                         M["iron"], offset=top + 0.05), 0.010)
        for sx in (-1, 1):
            for sy in (-1, 1):
                self.add(box("ch_cap_post", (cx + sx * 0.36, cy + sy * 0.36, top + 0.20),
                             (0.06, 0.06, 0.30), M["iron"]), 0.004)
        self.add(revolve("ch_cowl", [(0.62, 0.0), (0.58, 0.08), (0.10, 0.34)], 4,
                         (cx, cy, top + 0.34), M["iron"], phase=math.pi / 4), 0.0, 1)
        self.add(box("ch_hole", (cx, cy, top + 0.06), (0.62, 0.62, 0.10), M["stone_dark"]), 0.004)
        # 风向杆 + 阵营色小三角旗（比"十字形风标"更不像教堂）
        vz = top + 0.42
        self.add(revolve("vane_rod", [(0.028, 0.0), (0.028, 1.02)], 6, (cx, cy, vz),
                         M["iron"]), 0.0, 1)
        self.add(revolve("vane_ball", [(0.05, 0.0), (0.05, 0.05)], 6, (cx, cy, vz + 1.00),
                         M["iron"]), 0.0, 1)
        pen = [(0.0, 0.0), (0.62, -0.10), (0.0, -0.24)]
        self.add(extrude("vane_pennant", pen, "Y", 0.035, (cx, vz + 0.92),
                         M["team"], offset=cy), 0.004)

    # ── 8. 主屋面 ───────────────────────────────────────────────────────────
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
            xr, xe = 0.0, sgn * (W2 + OV)
            self.roof_slabs("roof_%d" % sgn, sgn, xr, RIDGE_Z, xe, ze, y0, y1, M["roof"])
            for i in range(1, 12):
                t_ = i / 11.6
                x = xr + (xe - xr) * t_
                z = RIDGE_Z + (ze - RIDGE_Z) * t_
                nx, nz = sgn * math.sin(ang), math.cos(ang)
                self.add(box("course", (x + nx * (surf + 0.020), (y0 + y1) * 0.5,
                                        z + nz * (surf + 0.020)),
                             (0.26, y1 - y0 - 0.04, 0.075), M["roof"], rot=(0.0, sgn * ang, 0.0)), 0.010)
        # 屋脊：木脊 + 铁压条
        zc = RIDGE_Z + 0.08
        self.add(box("ridge", (0, (y0 + y1) * 0.5, zc), (0.38, y1 - y0 + 0.06, 0.20),
                     M["roof_edge"]), 0.022)
        self.add(box("ridge_beam", (0, (y0 + y1) * 0.5, zc + 0.15), (0.15, y1 - y0 + 0.02, 0.12),
                     M["wood_dark"]), 0.008)
        # 铁压条要压在木脊梁上（之前悬空 15 mm）
        self.add(box("ridge_iron", (0, (y0 + y1) * 0.5, zc + 0.215), (0.21, y1 - y0 - 0.30, 0.05),
                     M["iron"]), 0.006)
        self.cupola()
        self.anvil_crest(0.0, y1 - 0.10, RIDGE_Z + 0.16, 1.45)
        # 檐口
        for sgn in (-1, 1):
            # 封檐板在两端各收 0.24：把转角让给山墙封边，避免两个构件共面打架（视口里会闪）
            self.add(box("fascia", (sgn * (W2 + OV - 0.05), (y0 + y1) * 0.5, ze + 0.02),
                         (0.19, y1 - y0 - 0.48, 0.28), M["wood_dark"]), 0.016)
            # 檐口顶面的阵营色压条：45° 俯视时是唯一在"水平面"上的阵营色
            self.add(box("eave_tint", (sgn * (W2 + OV - 0.05), (y0 + y1) * 0.5, ze + 0.17),
                         (0.20, y1 - y0 - 0.56, 0.045), M["team_trim"]), 0.004)
        # 山墙封边必须"兜住"屋面板的断面（之前内缩 0.10，露出一条生边，读起来像错位）
        for yy in (y1 - 0.04, y0 + 0.04):
            for sgn in (-1, 1):
                self.add(beam("barge", (0.0, yy, RIDGE_Z + 0.02), (sgn * (W2 + OV), yy, ze - 0.02),
                              0.22, 0.30, M["wood_dark"]), 0.018)
        for sgn in (-1, 1):
            for i in range(10):
                yy = y0 + 0.35 + i * (y1 - y0 - 0.70) / 9.0
                self.add(box("rafter", (sgn * (W2 + OV - 0.24), yy, ze - 0.13),
                             (0.72, 0.12, 0.12), M["wood_dark"]), 0.008)

    def cupola(self):
        """脊上排烟阁：四面百叶 + 铁压顶 —— 民居不会有的"工业顶"信号。"""
        M = self.M
        cx, cy = 0.0, CUP_Y
        hw = CUP_W * 0.5
        base_z = RIDGE_Z + 0.02
        body_z0, body_z1 = base_z + 0.10, base_z + 1.02
        # 四坡台座：底埋进屋面（-0.7），顶托住阁身 —— 不再是"一个方盒子摆在坡面上"
        self.add(frustum("cup_pedestal", base_z - 0.70, body_z0 + 0.02,
                         CUP_W + 0.60, CUP_W + 0.60, CUP_W + 0.08, CUP_W + 0.08,
                         cx, cy, M["wood_dark"]), 0.014)
        self.add(box("cup_body", (cx, cy, (body_z0 + body_z1) * 0.5),
                     (CUP_W, CUP_W, body_z1 - body_z0), M["wood_dark"]), 0.016)
        for i in range(3):
            zz = body_z0 + 0.18 + i * 0.26
            for sy in (-1, 1):
                self.add(box("cup_louver", (cx, cy + sy * (hw - 0.02), zz),
                             (CUP_W - 0.14, 0.06, 0.10), M["iron"]), 0.004)
            for sx in (-1, 1):
                self.add(box("cup_louver2", (cx + sx * (hw - 0.02), cy, zz),
                             (0.06, CUP_W - 0.14, 0.10), M["iron"]), 0.004)
        for sx in (-1, 1):
            for sy in (-1, 1):
                self.add(box("cup_post", (cx + sx * hw, cy + sy * hw,
                                          (body_z0 + body_z1) * 0.5),
                             (0.09, 0.09, body_z1 - body_z0 + 0.10), M["wood_warm"]), 0.006)
        self.add(box("cup_cap", (cx, cy, body_z1 + 0.06), (CUP_W + 0.30, CUP_W + 0.30, 0.10),
                     M["iron"]), 0.012)
        self.add(revolve("cup_roof", [(0.66, 0.0), (0.60, 0.06), (0.10, 0.36)], 4,
                         (cx, cy, body_z1 + 0.11), M["iron"], phase=math.pi / 4), 0.0, 1)
        self.add(revolve("cup_spike", [(0.05, 0.0), (0.0, 0.40)], 5,
                         (cx, cy, body_z1 + 0.44), M["iron"]), 0.0, 1)

    def anvil_crest(self, x, y, z, s=1.0):
        """脊端铁艺立饰：一尊小铁砧（和门口那尊同一个语汇，只是缩到 0.55 m）。"""
        M = self.M
        self.add(box("crest_post", (x, y, z + 0.17 * s), (0.10 * s, 0.10 * s, 0.34 * s),
                     M["iron"]), 0.003)
        self.add(box("crest_collar", (x, y, z + 0.30 * s), (0.20 * s, 0.20 * s, 0.05 * s),
                     M["team_trim"]), 0.003)
        self.anvil_shape("crest", x, y, z + 0.33 * s, 0.34)

    # ── 9. 山墙木构 + 百叶通风口 ────────────────────────────────────────────
    def gable_timber(self):
        """山墙半木构。所有构件宽度都按"该高度处的屋面净宽"收，绝不捅出屋面。"""
        M = self.M
        yy = YF + 0.06
        tz = 5.80
        half_at = lambda z: (RIDGE_Z - z) / SLOPE
        self.add(box("collar", (0, yy, tz), (half_at(tz) * 2 - 0.24, 0.15, 0.30),
                     M["wood_dark"]), 0.016)
        # 山墙腰线的阵营色横带：必须整体高于坡棚板顶（5.665），否则会从板面上"穿出来"
        # v9：抬到 collar 前表面，读作"横梁上的阵营色包边"，正/侧两轴都不与板相交
        self.add(box("gable_band", (0, yy + 0.055, 5.78),
                     (half_at(5.70) * 2 - 0.36, 0.12, 0.10), M["team"]), 0.008)
        # 山墙中段的百叶通风口：木框圈住，读"阁楼排烟口"而不是"窗"
        vz = 6.58
        for sgn in (-1, 1):
            self.add(box("vent_post", (sgn * 0.78, yy + 0.01, (tz + 7.26) * 0.5),
                         (0.17, 0.15, 7.26 - tz), M["wood_dark"]), 0.012)
        self.add(box("vent_lintel", (0, yy, 7.30), (1.78, 0.15, 0.22), M["wood_dark"]), 0.012)
        self.add(box("vent_case", (0, yy + 0.05, vz), (1.38, 0.12, 1.00), M["stone_dark"]), 0.008)
        for k in range(5):
            self.add(box("vent_slat", (0, yy + 0.13, vz + 0.36 - k * 0.18),
                         (1.20, 0.05, 0.10), M["iron"]), 0.004)
        self.add(box("king_post_up", (0, yy, (7.44 + RIDGE_Z) * 0.5),
                     (0.26, 0.15, RIDGE_Z - 7.44), M["wood_dark"]), 0.014)
        for sx in (-1, 1):
            for xr in (1.62, 2.52):
                ztop = zroof(xr) - 0.28
                if ztop <= tz + 0.45:
                    continue
                self.add(box("stud", (sx * xr, yy, (tz + 0.16 + ztop) * 0.5),
                             (0.20, 0.14, ztop - tz - 0.16), M["wood_dark"]), 0.012)
        for sx in (-1, 1):
            self.add(beam("brace", (sx * (half_at(tz + 0.20) - 0.40), yy, tz + 0.18),
                          (sx * 0.60, yy, tz + 1.32), 0.16, 0.12, M["wood_dark"]), 0.010)

    # ── 10. 门廊翼（加宽入口）──────────────────────────────────────────────
    def wing(self):
        M = self.M
        cx = WING_CX
        hw = (WING_X1 - WING_X0) * 0.5
        prof = [(WING_X0, 0.0), (WING_X1, 0.0), (WING_X1, WING_EAVE),
                (cx, WING_RIDGE), (WING_X0, WING_EAVE)]
        self.add(extrude("wing_mass", prof, "Y", WING_Y1 - YF, (0, 0),
                         M["stone_light"], offset=(WING_Y1 + YF) * 0.5), 0.028)
        slope = (WING_RIDGE - WING_EAVE) / hw
        # 翼的屋面只在"外侧"出挑；朝炉膛龛的一侧必须收平，否则屋面板会插进拱券石里
        for sgn in (-1, 1):
            # 外侧照常出挑；朝炉膛龛的一侧不出挑，屋面板收到墙线以内
            xe = hw + (0.26 if sgn < 0 else -0.18)
            ze = WING_RIDGE - slope * xe
            ang = math.atan(slope)
            y1w = WING_Y1 + (0.26 if sgn < 0 else -0.02)
            y0w = 3.40          # 主屋面前檐在 3.34：翼屋面从它后面 0.06 起步，绝不插进主屋面
            # 翼屋面用更深一档的 roof_edge：和主屋面同色时，3/4 视角下两个体量会糊成一片，
            # 那条交线就会被读成"错位"
            self.roof_slabs("wing_roof", sgn, cx, WING_RIDGE, cx + sgn * xe, ze,
                            y0w, y1w, M["roof_edge"], t=0.15)
            for i in range(1, 6):
                t_ = i / 5.5
                x = cx + sgn * xe * t_
                z = WING_RIDGE + (ze - WING_RIDGE) * t_
                self.add(box("wing_course", (x + sgn * math.sin(ang) * 0.13, 4.52,
                                             z + math.cos(ang) * 0.13),
                             (0.16, 2.12, 0.06), M["roof"], rot=(0, sgn * ang, 0)), 0.008)
        self.add(box("wing_ridge", (cx, 4.57, WING_RIDGE + 0.04),
                     (0.30, 2.34, 0.10), M["roof_edge"]), 0.014)
        # 翼屋面与主屋面之间留了 0.06 的缝（避免插进主屋面），缝里会露出翼体块的石顶 ——
        # 在这个机位下就是一条白线，读起来仍像错位。用一条与屋面同色的填缝条把它填实。
        ang_up = math.atan(slope)
        for sgn in (-1, 1):
            x1 = cx + sgn * (hw + 0.18)
            z1 = WING_RIDGE - slope * (hw + 0.18) + 0.02
            self.add(box("wing_gutter", ((cx + x1) * 0.5, 3.37, (WING_RIDGE + z1) * 0.5),
                         (math.hypot(x1 - cx, z1 - WING_RIDGE) + 0.06, 0.17, 0.09),
                         M["roof_edge"], rot=(0, sgn * ang_up, 0)), 0.008)
        for sgn in (-1, 1):
            xe_b = hw + (0.24 if sgn < 0 else -0.18)
            self.add(beam("wing_barge", (cx, WING_Y1 + 0.24, WING_RIDGE - 0.02),
                          (cx + sgn * xe_b, WING_Y1 + 0.24,
                           WING_RIDGE - slope * xe_b - 0.02), 0.14, 0.26, M["wood_dark"]), 0.014)
        # 入口：1.95 宽 / 2.15 拱高的石拱门
        self.add(extrude("door_opening", arch_profile(DOOR_W, DOOR_ARCH, segs=8), "Y", 0.30,
                         (cx, 0.0), M["stone_dark"], offset=WING_Y1 - 0.16), 0.0)
        self.add(arch_band("door_arch", cx, DOOR_ARCH, DOOR_W * 0.5, DOOR_W * 0.5 + 0.24,
                           WING_Y1 + 0.02, WING_Y1 + 0.18, M["stone_light"], segs=8), 0.018)
        for x in (cx - DOOR_W * 0.5 - 0.13, cx + DOOR_W * 0.5 + 0.13):
            self.add(box("door_jamb", (x, WING_Y1 + 0.05, DOOR_ARCH * 0.5),
                         (0.26, 0.22, DOOR_ARCH), M["stone_light"]), 0.016)
        self.add(box("door_key", (cx, WING_Y1 + 0.08, DOOR_ARCH + DOOR_W * 0.5 - 0.02),
                     (0.30, 0.24, 0.40), M["stone_mid"]), 0.014)
        # 双开木门（关着，但门缝与门槛下透暖光 —— 屋里炉子生着）
        leaf_w = (DOOR_W - 0.12) * 0.5
        for sgn in (-1, 1):
            lx = cx + sgn * (leaf_w * 0.5 + 0.03)
            self.add(box("door_leaf", (lx, WING_Y1 - 0.02, DOOR_ARCH * 0.5 + 0.36),
                         (leaf_w, 0.09, DOOR_ARCH + 0.70), M["wood_warm"]), 0.014)
            # 竖板缝
            for k in (-1, 1):
                self.add(box("door_seam", (lx + k * leaf_w * 0.22, WING_Y1 + 0.035,
                                           DOOR_ARCH * 0.5 + 0.36),
                             (0.035, 0.03, DOOR_ARCH + 0.56), M["wood_dark"]), 0.002)
        self.add(box("door_gap", (cx, WING_Y1 + 0.01, 0.30), (DOOR_W - 0.16, 0.04, 0.14),
                     M["glow"]))
        for zz in (0.62, 1.42):
            self.add(box("door_iron", (cx, WING_Y1 + 0.05, zz), (DOOR_W - 0.30, 0.05, 0.09),
                         M["iron"]), 0.006)
        for sgn in (-1, 1):
            self.add(box("door_hinge", (cx + sgn * (DOOR_W * 0.5 - 0.16), WING_Y1 + 0.08, 0.62),
                         (0.20, 0.04, 0.10), M["iron"]), 0.004)
        self.add(ring_y("door_ring", (cx - 0.16, WING_Y1 + 0.005, 1.24), 0.055, 0.105, 0.05, 10,
                        M["iron"]))
        # 翼山墙小拱窗：v9 重新定尺 -------------------------------------------------
        # 山墙是 2.46 宽 / 2.50 高的等腰三角形（坡度 2.03），z>4.8 之后只剩不到 0.7 m 宽。
        # 原来 0.92 宽拱窗（含拱圈顶 5.34）和 1.34 宽的阵营色窗楣（5.32）都宽过山墙轮廓，
        # 于是从坡面上“飘”出来一块蓝片 —— 用户图二那处错位就是这个。
        # 现在改成 0.56 × 0.62 的矮拱窗（拱圈顶 4.44），整体在三角形内，两侧各留 0.4 m 石墙。
        wz = 3.72
        # origin 的 v 必须是 wz —— 原来写 0.0，整块窗玻璃一直贴在地面上（窗洞里永远是石墙）
        self.add(extrude("wing_win", arch_profile(0.56, 0.34, segs=6), "Y", 0.06,
                         (cx, wz), M["glow"], offset=WING_Y1 + 0.04), 0.0)
        self.add(arch_band("wing_win_arch", cx, wz + 0.34, 0.28, 0.38, WING_Y1 + 0.06,
                           WING_Y1 + 0.16, M["stone_light"], segs=6), 0.008)
        for sgn in (-1, 1):
            self.add(box("wing_win_jamb", (cx + sgn * 0.35, WING_Y1 + 0.11, wz + 0.18),
                         (0.13, 0.13, 0.36), M["stone_light"]), 0.008)
        self.add(box("wing_win_bar", (cx, WING_Y1 + 0.12, wz + 0.20), (0.045, 0.08, 0.40),
                     M["wood_dark"]), 0.003)
        self.add(box("wing_win_sill", (cx, WING_Y1 + 0.12, wz - 0.06), (1.02, 0.20, 0.11),
                     M["stone_light"]), 0.010)
        self.add(box("wing_win_lintel", (cx, WING_Y1 + 0.08, wz + 0.84), (0.82, 0.13, 0.14),
                     M["team"]), 0.008)
        self.add(box("wing_string", (cx, WING_Y1 + 0.05, WING_EAVE + 0.10), (2.16, 0.12, 0.12),
                     M["stone_mid"]), 0.008)
        # 斜撑上端外移到 0.60 并抬到 4.60：与窗框留 0.2 m 净距（原来斜撑直接穿过窗洞）
        for sgn in (-1, 1):
            self.add(beam("wing_knee", (cx + sgn * 0.98, WING_Y1 + 0.10, WING_EAVE + 0.16),
                          (cx + sgn * 0.60, WING_Y1 + 0.10, WING_EAVE + 1.08),
                          0.14, 0.10, M["wood_dark"]), 0.008)

    # ── 11. 门廊 ────────────────────────────────────────────────────────────
    def porch(self):
        M = self.M
        x0, x1 = WING_X0 + 0.08, WING_X1 - 0.08
        y0, y1 = WING_Y1, PORCH_Y1
        z0, z1 = 3.32, 3.00          # v9：压低 0.14，给翼山墙窄窗的窗台让净距
        self.add(slab_plate("porch_roof", M["roof"], x0, x1, y0 - 0.04, y1, z0, z1, 0.15), 0.022)
        ang = math.atan2(z0 - z1, y1 - y0)
        for i in range(4):
            yy = y0 + 0.14 + i * (y1 - y0 - 0.24) / 3.0
            zz = z0 + (z1 - z0) * (yy - y0) / (y1 - y0)
            self.add(box("porch_course", ((x0 + x1) * 0.5, yy, zz + 0.06), (x1 - x0, 0.15, 0.05),
                         M["roof"], rot=(-ang, 0, 0)), 0.008)
        self.add(box("porch_beam", ((x0 + x1) * 0.5, y1 - 0.10, z1 - 0.14),
                     (x1 - x0 + 0.12, 0.18, 0.20), M["wood_dark"]), 0.016)
        self.add(box("porch_fascia", ((x0 + x1) * 0.5, y1 + 0.02, z1 - 0.04),
                     (x1 - x0 + 0.06, 0.13, 0.24), M["wood_dark"]), 0.014)
        for xx in (x0 + 0.16, x1 - 0.16):
            self.add(box("porch_post", (xx, y1 - 0.12, z1 * 0.5), (0.20, 0.20, z1),
                         M["wood_warm"]), 0.014)
            self.add(box("porch_foot", (xx, y1 - 0.12, 0.11), (0.32, 0.32, 0.22),
                         M["stone_mid"]), 0.014)
            self.add(beam("porch_brace", (xx, y1 - 0.14, z0 - 0.86), (xx, y1 - 0.92, z0 - 0.12),
                          0.13, 0.11, M["wood_dark"]), 0.010)

    # ── 12. 侧窗 ────────────────────────────────────────────────────────────
    def windows(self):
        self.side_window("winL", (-W2, -1.45, 3.12), -1, 0.74, 1.24)
        self.side_window("winR", (W2, 1.45, 3.12), 1, 0.74, 1.24)
        self.side_window("winR2", (W2, -2.15, 3.12), 1, 0.74, 1.24)

    def side_window(self, name, center, sgn, w, h):
        """侧窗：窗框、玻璃、窗棂全部在墙面**外侧**（之前整扇埋进墙里，只看得见一道石框）。"""
        M = self.M
        cx, cy, cz = center
        self.add(box(name + "_frame", (cx + sgn * 0.05, cy, cz), (0.18, w + 0.24, h + 0.22),
                     M["stone_mid"]), 0.014)
        self.add(box(name + "_glass", (cx + sgn * 0.10, cy, cz), (0.05, w, h), M["glow"]))
        self.add(box(name + "_bar", (cx + sgn * 0.14, cy, cz), (0.05, 0.06, h), M["wood_dark"]), 0.004)
        self.add(box(name + "_bar2", (cx + sgn * 0.14, cy, cz), (0.05, w, 0.06), M["wood_dark"]), 0.004)
        self.add(box(name + "_sill", (cx + sgn * 0.08, cy, cz - h * 0.5 - 0.15),
                     (0.24, w + 0.32, 0.12), M["stone_light"]), 0.010)
        self.add(box(name + "_lintel", (cx + sgn * 0.07, cy, cz + h * 0.5 + 0.20),
                     (0.18, w + 0.46, 0.20), M["team"]), 0.010)

    # ── 13. 阵营色标准模块 ──────────────────────────────────────────────────
    def kite(self, name, center, face, w, h, out=1):
        """标准筝形盾：金边 + 阵营色盾面 + 交叉锻锤纹章。

        out 是"盾面朝外的方向"（X 面墙才有用）：挂在 -X 墙上要传 out=-1，
        否则盾面和纹章会被塞进墙里，只露出一块金边（v8 第一版就是这个 bug）。
        """
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
        """纹章：交叉的锻锤（两条斜杆 + 两个锤头），低模下也读得出。"""
        M = self.M
        a = math.radians(30)
        L_ = min(w, h) * 0.62
        dx, dz = math.cos(a) * L_ * 0.5, math.sin(a) * L_ * 0.5
        if face == "Y":
            for sgn in (-1, 1):
                self.add(beam(name + "_shaft", (cx - sgn * dx, cy, cz - dz + h * 0.02),
                              (cx + sgn * dx, cy, cz + dz + h * 0.02), 0.075, 0.05,
                              M["team_trim"]), 0.004)
                self.add(box(name + "_head", (cx + sgn * dx * 1.04, cy,
                                              cz + dz + h * 0.02), (0.20, 0.05, 0.13),
                             M["team_trim"], rot=(0, -sgn * a, 0)), 0.004)
        else:
            for sgn in (-1, 1):
                self.add(beam(name + "_shaft", (cx, cy - sgn * dx, cz - dz + h * 0.02),
                              (cx, cy + sgn * dx, cz + dz + h * 0.02), 0.05, 0.075,
                              M["team_trim"]), 0.004)
                self.add(box(name + "_head", (cx, cy + sgn * dx * 1.04, cz + dz + h * 0.02),
                             (0.05, 0.20, 0.13), M["team_trim"], rot=(sgn * a, 0, 0)), 0.004)

    def banner(self, name, x, y_front, z_eave):
        """棚口垂旗：L 形铁吊架从檐底垂下，旗杆横挂在吊架下端，整幅旗落在封檐板之外。

        v9 修正（两轮）：
          ① v8 的旗杆画在 z+0.16、布心 y 与封檐板中心重合 —— 杆和布顶都钻进封檐板/檐梁，
             正、侧两轴都读成"旗从梁里长出来"。
          ② 只把旗挂到梁底还不够：0.18 m 的悬挂高度在 RTS 尺度下读不出结构，旗顶与檐口的
             阵营色饰带连成一片。这里改成 **L 形吊架**（竖杆 0.29 + 横臂 0.28），旗顶离梁底
             0.375 m，中间露出木梁 + 铁件，层次才立得住。
        """
        M = self.M
        w, h = BANNER_W, BANNER_H
        z_arm = z_eave - 0.26           # 横臂中心：比梁底低 0.26，给竖杆留出可见长度
        z_pole = z_arm - 0.06           # 旗杆中心
        y_pole = y_front + 0.155        # 杆心在封檐板前表面之外 0.155
        # ① 竖杆（贴封檐板外侧，从梁底垂下，上端嵌进梁 5 mm）
        y_stem = y_front + 0.045
        for sgn in (-1, 1):
            self.add(box(name + "_stem", (x + sgn * w * 0.42, y_stem,
                                          (z_eave + 0.005 + z_arm + 0.02) * 0.5),
                         (0.05, 0.05, z_eave + 0.005 - z_arm - 0.02), M["iron"]), 0.004)
        # ② 横臂（从封檐板外侧挑出到杆心）
        for sgn in (-1, 1):
            y0 = y_front + 0.005
            self.add(box(name + "_arm", (x + sgn * w * 0.42, (y0 + y_pole + 0.035) * 0.5, z_arm),
                         (0.05, y_pole + 0.035 - y0, 0.06), M["iron"]), 0.005)
            self.add(box(name + "_hook", (x + sgn * w * 0.42, y_pole, z_arm - 0.045),
                         (0.042, 0.05, 0.09), M["iron"]), 0.004)
        # ③ 木旗杆：暖木色（和蓝旗拉开），比布宽 0.20，两端各出 0.10
        self.add(box(name + "_pole", (x, y_pole, z_pole), (w + 0.20, 0.07, 0.07),
                     M["wood_warm"]), 0.006)
        # ④ 旗布：顶边挂在杆下 10 mm
        zt = z_pole - 0.055
        prof = [(-w * 0.5, 0.0), (w * 0.5, 0.0), (w * 0.5, -h * 0.80),
                (w * 0.12, -h), (-w * 0.12, -h), (-w * 0.5, -h * 0.80)]
        self.add(extrude(name + "_cloth", prof, "Y", 0.05, (x, zt), M["team"], offset=y_pole), 0.010)
        # ⑤ 旗顶金压条（夹住布顶，与杆留 3 mm 缝）+ 燕尾金边
        self.add(box(name + "_trimT", (x, y_pole, zt - 0.021), (w + 0.08, 0.075, 0.075),
                     M["team_trim"]), 0.006)
        for sgn in (-1, 1):
            self.add(beam(name + "_trimB", (x + sgn * w * 0.07, y_pole, zt - h * 0.96),
                          (x + sgn * w * 0.50, y_pole, zt - h * 0.78), 0.08, 0.05,
                          M["team_trim"]), 0.005)
        # ⑤ 旗心纹章：小铁砧（和脊饰同款，远看是一个"砧"的剪影）
        yf = y_pole + 0.035
        bz = zt - h * 0.40
        self.add(box(name + "_ch_base", (x, yf, bz - h * 0.10), (w * 0.42, 0.04, h * 0.06),
                     M["team_trim"]), 0.004)
        self.add(box(name + "_ch_wst", (x, yf, bz - h * 0.03), (w * 0.20, 0.04, h * 0.05),
                     M["team_trim"]), 0.004)
        self.add(box(name + "_ch_top", (x, yf, bz + h * 0.04), (w * 0.56, 0.04, h * 0.06),
                     M["team_trim"]), 0.004)
        self.add(box(name + "_ch_hrn", (x + w * 0.33, yf, bz + h * 0.02),
                     (w * 0.14, 0.04, h * 0.04), M["team_trim"]), 0.003)

    def wallbanner(self, name, center, face, w=WALLBAN_W, h=WALLBAN_H):
        """墙面横幅（大块染色面）：上下木杆 + 燕尾 + 交叉锻锤。face = 悬挂面法线轴。"""
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
            self.emblem(name, "Y", cx, cy + 0.075, cz + h * 0.06, w * 0.78, h * 0.62)
        else:
            self.add(extrude(name + "_cloth", prof, "X", 0.07, (cy, cz), M["team"], offset=cx), 0.012)
            self.add(box(name + "_rod_t", (cx, cy, cz + hh + 0.03), (0.10, w + 0.28, 0.11),
                         M["wood_dark"]), 0.008)
            self.add(box(name + "_rod_b", (cx, cy, cz - hh - 0.02), (0.09, w + 0.10, 0.09),
                         M["wood_dark"]), 0.006)
            for sgn in (-1, 1):
                self.add(box(name + "_fringe", (cx, cy + sgn * hw * 0.62, cz - hh - 0.13),
                             (0.06, w * 0.13, 0.20), M["team_trim"]), 0.004)
            self.emblem(name, "X", cx + 0.075, cy, cz + h * 0.06, w * 0.78, h * 0.62)

    def heraldry(self):
        # ① 烟囱胸墙大盾
        self.kite("shield_ch", (CH_CX, CH_Y1 + 0.10, 3.34), "Y", SHIELD_W, SHIELD_H)
        # ② 左墙横幅（大块面）
        # 大块染色面：挂在侧墙两扇窗之间（别压住窗）
        self.wallbanner("wbanner_L", (W2 + 0.06, -0.55, 3.24), "X")
        # ③ 右墙盾
        self.kite("shield_R", (-W2 - 0.03, 0.35, 3.10), "X", 1.16, 1.44, out=-1)
        # ④ 门前小盾
        self.kite("shield_door", (WING_CX, WING_Y1 + 0.04, 2.62), "Y", SHIELD_S[0], SHIELD_S[1])
        # ⑤ 作业坡棚口的两面垂旗
        #    x 内移：左旗让开门廊翼坡屋面（-1.78），右旗让开烟囱胸墙（2.52）；
        #    y 取封檐板前表面，z 取檐梁底面 —— 由 banner() 自己往外挑出悬挂
        for tag, xx in (("L", -1.28), ("R", 2.02)):
            self.banner("banner_" + tag, xx, CAN_Y1 + 0.165, can_z(CAN_Y1) - 0.30)

    # ── 14. 细部（招牌 / 提灯 / 挂件）──────────────────────────────────────
    def details(self):
        M = self.M
        for yy, sgn in ((YF + OV - 0.12, 1), (YB - OV + 0.12, -1)):
            for x in (-3.10, -1.05, 1.05, 3.10):
                self.add(beam("corbel", (x, yy - sgn * 0.42, EAVE - 0.88), (x, yy, EAVE - 0.18),
                              0.15, 0.14, M["wood_dark"]), 0.008)
        # 悬挂招牌（门廊翼左端，避开门洞）
        sx, sy = WING_X0 + 0.42, PORCH_Y1 - 0.18
        sz = 2.98
        self.add(beam("sign_arm", (sx, sy - 0.46, sz + 0.12), (sx, sy + 0.22, sz + 0.12),
                      0.07, 0.07, M["iron"]), 0.005)
        self.add(box("sign_hang", (sx, sy + 0.10, sz - 0.14), (0.05, 0.05, 0.34), M["iron"]), 0.004)
        self.add(box("sign_trim", (sx, sy + 0.04, sz - 0.46), (0.98, 0.06, 0.70),
                     M["team_trim"]), 0.006)
        self.add(box("sign_board", (sx, sy, sz - 0.46), (0.88, 0.10, 0.60), M["wood_dark"]), 0.010)
        self.add(box("sign_a", (sx, sy - 0.06, sz - 0.40), (0.52, 0.04, 0.07), M["iron"]), 0.004)
        self.add(box("sign_b", (sx, sy - 0.06, sz - 0.50), (0.26, 0.04, 0.16), M["iron"]), 0.004)
        self.add(box("sign_c", (sx, sy - 0.06, sz - 0.62), (0.42, 0.04, 0.07), M["iron"]), 0.004)
        # 门侧提灯
        lx, ly, lz = -1.90, WING_Y1 + 0.14, 2.58
        self.add(beam("lan_arm", (lx - 0.02, ly - 0.22, lz + 0.26), (lx - 0.02, ly + 0.02, lz + 0.26),
                      0.06, 0.06, M["iron"]), 0.005)
        self.add(box("lan_cage", (lx - 0.02, ly - 0.12, lz), (0.22, 0.22, 0.30), M["glow"]), 0.008)
        self.add(box("lan_top", (lx - 0.02, ly - 0.12, lz + 0.19), (0.28, 0.28, 0.08),
                     M["iron"]), 0.006)
        self.add(box("lan_bot", (lx - 0.02, ly - 0.12, lz - 0.19), (0.26, 0.26, 0.07),
                     M["iron"]), 0.006)
        # 煤槽（靠墙）
        self.add(box("coal_rail", (W2 + 0.30, -2.55, 0.44), (0.10, 1.10, 0.10), M["wood_dark"]), 0.006)
        for sgn in (-1, 1):
            self.add(box("coal_post", (W2 + 0.30, -2.55 + sgn * 0.52, 0.27), (0.10, 0.10, 0.54),
                         M["wood_dark"]), 0.006)

    # ── 15. 前场道具 ────────────────────────────────────────────────────────
    def props(self):
        z = 0.26
        self.anvil((0.10, 6.92, z))                      # 中央重型铁砧（放大 1.35×）
        self.bellows((1.92, 4.16, 0.05))                 # 风箱：喷嘴朝炉膛（落在龛内地面）
        self.tool_rack("rack_L", (-3.88, 6.72, z))       # 左立式工具架（让开主入口）
        self.tool_rack("rack_R", (3.42, 6.40, z))        # 右立式工具架
        self.weapon_sword("sword", (3.16, 6.24, z), (-0.62, -0.72, 2.02))
        self.weapon_axe("axe", (-2.48, 6.22, z), (0.56, -0.72, 1.86))
        self.quench_barrel((1.44, 6.10, z))
        self.bucket("coal_a", (-1.66, 7.18, z), 0.31, 0.46)
        self.bucket("coal_b", (2.58, 7.14, z), 0.29, 0.42)
        self.ingot_basket("ingots", (-2.46, 7.26, z))
        self.grindstone((3.96, 5.60, 0.0))
        self.logs((4.58, -2.35, 0.0))
        self.pot("pot_a", (-4.48, 4.62, 0.0), 0.31, 0.88)
        self.pot("pot_b", (-4.66, 5.34, 0.0), 0.24, 0.68)

    def anvil_shape(self, name, x, y, z, s=1.0):
        """铁砧本体（不含树桩/道具）：外张底座 → 收腰 → 外挑砧面 → 长锥砧角。

        轮廓放在 XZ 平面、沿 Y 挤出 —— 正面看到的就是经典铁砧剪影：
        底宽、腰细、面挑出、角尖，四段缺一不可。s 控制整体尺度。
        """
        M = self.M
        t = 0.40 * s
        zb = z
        base = [(-0.44 * s, 0.00), (0.44 * s, 0.00),
                (0.36 * s, 0.13 * s), (-0.36 * s, 0.13 * s)]
        self.add(extrude(name + "_base", base, "Y", t, (x, zb), M["iron"], offset=y), 0.012)
        waist = [(-0.26 * s, 0.13 * s), (0.26 * s, 0.13 * s),
                 (0.21 * s, 0.34 * s), (-0.21 * s, 0.34 * s)]
        self.add(extrude(name + "_waist", waist, "Y", t * 0.86, (x, zb), M["iron"], offset=y), 0.010)
        body = [(-0.40 * s, 0.34 * s), (0.40 * s, 0.34 * s),
                (0.40 * s, 0.44 * s), (-0.40 * s, 0.44 * s)]
        self.add(extrude(name + "_body", body, "Y", t, (x, zb), M["iron"], offset=y), 0.010)
        # 砧面：比砧身宽出 8%，形成一圈"帽檐"——这是最容易读出来的一笔
        face = [(-0.46 * s, 0.44 * s), (0.46 * s, 0.44 * s),
                (0.46 * s, 0.52 * s), (-0.46 * s, 0.52 * s)]
        self.add(extrude(name + "_face", face, "Y", t * 1.12, (x, zb), M["iron"], offset=y), 0.010)
        # 砧角：长锥，末端微微下垂
        self.add(cone(name + "_horn", (x + 0.42 * s, y, zb + 0.47 * s),
                      (x + 1.00 * s, y, zb + 0.35 * s), 0.155 * s, 8, M["iron"]), 0.004)
        # 砧面上的方孔（hardy）/ 小圆孔（pritchel）
        if s > 0.5:
            self.add(box(name + "_hardy", (x + 0.20 * s, y, zb + 0.52 * s),
                         (0.11 * s, 0.11 * s, 0.02), M["coal"]))
            self.add(box(name + "_pritchel", (x - 0.24 * s, y, zb + 0.52 * s),
                         (0.055 * s, 0.055 * s, 0.02), M["coal"]))

    def anvil(self, p, s=1.1):
        """重型铁砧：粗树桩 + 一个"真砧"的剪影 + 砧面红热锻件 + 斜搭的锤。"""
        M = self.M
        x, y, z = p
        self.add(revolve("anvil_stump", [(0.00, 0.00), (0.62 * s, 0.00), (0.68 * s, 0.16),
                                         (0.60 * s, 0.60), (0.00, 0.66)],
                         12, (x, y, z), M["wood_dark"]), 0.022, 1)
        zb = z + 0.66 * s
        self.anvil_shape("anvil", x, y, zb, s)
        zt = zb + 0.52 * s
        # 砧面红热锻件（发光）—— 一块正在打的铁，不要铺满整个砧面
        self.add(box("billet", (x - 0.10 * s, y + 0.02 * s, zt + 0.035 * s),
                     (0.34 * s, 0.20 * s, 0.07 * s), M["ember"]), 0.004)
        # 砧上锤：手柄落在砧面上（不是悬空）
        self.add(beam("anvil_hammer", (x - 0.56 * s, y - 0.26 * s, zt + 0.055 * s),
                      (x + 0.06 * s, y - 0.26 * s, zt + 0.075 * s),
                      0.08 * s, 0.08 * s, M["wood_warm"]), 0.005)
        self.add(box("anvil_hammer_head", (x + 0.12 * s, y - 0.26 * s, zt + 0.08 * s),
                     (0.16 * s, 0.30 * s, 0.16 * s), M["iron"]), 0.005)

    def tool_rack(self, name, p):
        """立式工具架：背板 + 立柱 + 两道横杆 + 锤/钳/凿，读作"工具墙"。"""
        M = self.M
        x, y, z = p
        self.add(box(name + "_back", (x, y - 0.08, z + 1.02), (1.58, 0.09, 2.04), M["wood_warm"]), 0.010)
        for sgn in (-1, 1):
            self.add(box(name + "_post", (x + sgn * 0.75, y, z + 1.05), (0.17, 0.18, 2.10),
                         M["wood_dark"]), 0.012)
        for zz in (z + 1.88, z + 1.02):
            self.add(box(name + "_rail", (x, y + 0.02, zz), (1.60, 0.10, 0.10), M["wood_dark"]), 0.006)
            for i in range(4):
                self.add(box(name + "_peg%d%d" % (i, int(zz * 10)),
                             (x - 0.54 + i * 0.36, y + 0.10, zz - 0.07), (0.07, 0.10, 0.07),
                             M["iron"]), 0.002)
        # 两把锤
        for i, dx in enumerate((-0.46, 0.30)):
            self.add(box(name + "_hs%d" % i, (x + dx, y + 0.17, z + 1.30), (0.09, 0.09, 0.78),
                         M["wood_dark"]), 0.004)
            self.add(box(name + "_hh%d" % i, (x + dx, y + 0.17, z + 1.76),
                         (0.36, 0.16, 0.17), M["iron"]), 0.004)
        # 火钳（两臂张开 + 顶环），挂在右起第二根
        for sgn in (-1, 1):
            self.add(box(name + "_tg%d" % sgn, (x - 0.10 + sgn * 0.055, y + 0.17, z + 1.28),
                         (0.055, 0.055, 0.78), M["iron"], rot=(0, sgn * 0.06, 0)), 0.003)
        self.add(ring_y(name + "_tgtop", (x - 0.10, y + 0.17, z + 1.68), 0.035, 0.08, 0.06, 8,
                        M["iron"]))
        # 锻造凿 / 冲头
        for dx in (0.52, 0.62):
            self.add(box(name + "_ch", (x + dx, y + 0.105, z + 1.34), (0.08, 0.08, 0.64),
                         M["iron"]), 0.004)
        self.add(box(name + "_bar", (x - 0.10, y + 0.17, z + 0.86), (0.70, 0.06, 0.06),
                     M["iron"]), 0.003)

    def weapon_sword(self, name, p, tip):
        """长剑斜靠墙面：剑身 + 十字护手 + 握柄 + 圆盘柄头。"""
        M = self.M
        x, y, z = p
        tx, ty, tz = x + tip[0], y + tip[1], z + tip[2]
        self.add(beam(name + "_blade", (x, y, z + 0.02), (tx, ty, tz * 0.96), 0.18, 0.06,
                      M["iron"]), 0.004)
        self.add(box(name + "_guard", (tx, ty, tz - 0.06), (0.44, 0.07, 0.07), M["iron"],
                     rot=(0, 0.14, 0)), 0.004)
        self.add(beam(name + "_grip", (tx, ty, tz - 0.02), (tx - 0.02, ty - 0.02, tz + 0.26),
                      0.06, 0.06, M["wood_dark"]), 0.004)
        self.add(box(name + "_pommel", (tx - 0.02, ty - 0.02, tz + 0.30), (0.11, 0.11, 0.09),
                     M["gold"]), 0.004)

    def weapon_axe(self, name, p, tip):
        """战斧斜靠墙：斧柄 + 斧头 + 斧刃 + 背刺。"""
        M = self.M
        x, y, z = p
        tx, ty, tz = x + tip[0], y + tip[1], z + tip[2]
        self.add(beam(name + "_haft", (x, y, z + 0.02), (tx, ty, tz), 0.085, 0.085, M["wood_dark"]), 0.004)
        self.add(box(name + "_head", (tx + 0.18, ty, tz - 0.14), (0.38, 0.09, 0.38), M["iron"]), 0.006)
        self.add(box(name + "_edge", (tx + 0.39, ty, tz - 0.14), (0.09, 0.06, 0.52), M["iron"]), 0.004)
        self.add(box(name + "_spike", (tx - 0.12, ty, tz - 0.06), (0.16, 0.06, 0.07), M["iron"]), 0.004)

    def bellows(self, p):
        """双联风箱：楔形木箱 + 皮革软囊 + 铁喷嘴 + 拉杆。这是"铁匠铺"最直白的第二件道具。"""
        M = self.M
        x, y, z = p
        for i, dz in enumerate((0.0, 0.34)):
            self.add(taper_box("bellows_body", (x + 0.44, y, z + 0.30 + dz),
                               (x - 0.34, y, z + 0.30 + dz),
                               0.40, 0.20, 0.30, 0.12, M["wood_warm"]), 0.010)
            self.add(box("bellows_pleat", (x + 0.06, y, z + 0.30 + dz),
                         (0.52, 0.30, 0.06), M["wood_dark"]), 0.004)
        self.add(cyl("bellows_nozzle", (x - 0.40, y, z + 0.38), 0.075, 0.42, 8, M["iron"]), 0.004)
        self.add(beam("bellows_arm", (x + 0.46, y, z + 0.34), (x + 0.46, y, z + 1.02),
                      0.07, 0.07, M["wood_dark"]), 0.005)
        self.add(box("bellows_grip", (x + 0.46, y, z + 1.05), (0.10, 0.34, 0.09), M["wood_warm"]), 0.005)

    def quench_barrel(self, p):
        """淬火桶：木桶 + 两道铁箍 + 深色水面。"""
        M = self.M
        x, y, z = p
        self.add(revolve("quench", [(0.00, 0.00), (0.36, 0.00), (0.40, 0.12), (0.42, 0.38),
                                    (0.40, 0.62), (0.36, 0.68)],
                         12, (x, y, z), M["wood_warm"]), 0.014, 1)
        for zz in (0.14, 0.54):
            self.add(tube_band("quench_hoop", (x, y), 0.395, 0.435, z + zz, z + zz + 0.07, 12,
                               M["iron"]), 0.006, 1)
        self.add(revolve("quench_water", [(0.00, 0.00), (0.35, 0.00), (0.35, 0.02), (0.00, 0.02)],
                         12, (x, y, z + 0.60), M["iron"]), 0.0, 1)

    def bucket(self, name, p, r, h):
        """煤桶：锥形木桶 + 铁箍 + 提梁 + 满桶碎煤。"""
        M = self.M
        x, y, z = p
        self.add(revolve(name, [(r * 0.78, 0.0), (r * 0.86, 0.04), (r, h), (r * 0.90, h),
                                (r * 0.84, 0.06)], 10, (x, y, z), M["wood_warm"]), 0.010, 1)
        self.add(tube_band(name + "_hoop", (x, y), r * 0.86, r * 1.04, z + h - 0.09, z + h - 0.02,
                           10, M["iron"]), 0.005, 1)
        for sgn in (-1, 1):
            self.add(box(name + "_handle", (x + sgn * r * 0.92, y, z + h + 0.05),
                         (0.04, 0.04, 0.30), M["iron"], rot=(0, 0, sgn * 0.12)), 0.003)
        self.add(box(name + "_grip", (x, y, z + h + 0.18), (r * 1.86, 0.05, 0.05), M["iron"]), 0.003)
        rnd = random.Random(abs(hash(name)) & 0xFFFF)
        for i in range(5):
            a = rnd.random() * math.tau
            rr = rnd.random() * r * 0.45
            self.add(box(name + "_coal%d" % i, (x + math.cos(a) * rr, y + math.sin(a) * rr,
                                                z + h - 0.03),
                         (0.17, 0.15, 0.12), M["coal"],
                         rot=(rnd.random(), rnd.random(), rnd.random())), 0.008)

    def ingot_basket(self, name, p):
        """铁锭筐：木筐 + 立板条 + 四块梯形铁锭。"""
        M = self.M
        x, y, z = p
        self.add(box(name + "_floor", (x, y, z + 0.06), (0.80, 0.58, 0.10), M["wood_dark"]), 0.010)
        for i in range(5):
            xx = x - 0.36 + i * 0.18
            self.add(box(name + "_slat%d" % i, (xx, y, z + 0.30), (0.10, 0.58, 0.48),
                         M["wood_warm"]), 0.006)
        for sy in (-1, 1):
            self.add(box(name + "_side", (x, y + sy * 0.29, z + 0.30), (0.84, 0.06, 0.48),
                         M["wood_warm"]), 0.006)
        for i in range(4):
            self.add(box(name + "_ingot%d" % i, (x - 0.20 + (i % 2) * 0.22, y,
                                                  z + 0.60 + (i // 2) * 0.10),
                         (0.30, 0.17, 0.10), M["iron"], rot=(0, 0, 0.10 * (i - 1.5))), 0.006)

    def grindstone(self, p):
        M = self.M
        x, y, z = p
        for sgn in (-1, 1):
            self.add(box("gs_leg", (x, y + sgn * 0.34, z + 0.28), (0.16, 0.16, 0.56), M["wood_dark"]), 0.010)
        self.add(box("gs_trough", (x, y, z + 0.10), (0.54, 0.92, 0.20), M["wood_warm"]), 0.012)
        self.add(cyl("gs_wheel", (x, y, z + 0.46), 0.44, 0.17, 12, M["stone_light"]), 0.012, 1)
        self.add(cyl("gs_hub", (x, y, z + 0.46), 0.08, 0.46, 8, M["iron"]), 0.004)

    def logs(self, p):
        M = self.M
        x, y, z = p
        for i, (dx, dz) in enumerate(((0.0, 0.0), (0.0, 0.30), (0.30, 0.15), (-0.30, 0.15), (0.0, 0.60))):
            cz = z + dz + 0.19
            self.add(cyl("log%d" % i, (x + dx, y, cz), 0.19, 2.20, 8, M["wood_dark"]), 0.010, 1)
            self.add(cyl("log%d_end" % i, (x + dx, y + 1.11, cz), 0.13, 0.04, 8, M["wood_warm"]))
            self.add(cyl("log%d_rope" % i, (x + dx, y - 0.50, cz), 0.215, 0.10, 8, M["team"]), 0.004)

    def pot(self, name, p, r, h):
        M = self.M
        x, y, z = p
        self.add(revolve(name, [(r * 0.55, z), (r, z), (r * 1.09, z + h * 0.34),
                                (r * 0.92, z + h * 0.82), (r * 0.62, z + h), (r * 0.5, z + h)],
                         10, (x, y, 0), M["wood_warm"]), 0.014, 1)
        self.add(tube_band(name + "_hoop", (x, y), r * 0.98, r * 1.13,
                           z + h * 0.28, z + h * 0.38, 10, M["iron"]), 0.006, 1)

    # ── 组装 ────────────────────────────────────────────────────────────────
    def build(self):
        for step in (self.base, self.mass, self.forge_bay, self.work_canopy,
                     self.forge_hood, self.forge_fire, self.chimney, self.roof,
                     self.gable_timber, self.wing, self.porch, self.windows,
                     self.heraldry, self.details, self.props):
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
        out = L.join_by_material(objs, prefix="BS")
        mirror_x(out)
        if self.unwrap:
            L.smart_uv(out)      # 镜像之后再摊 UV，贴图不会被镜像翻转
        return out


def y1_of_bay():
    return BAY_Y1


def build(smooth=True, unwrap=True):
    m = Model(smooth, unwrap).build()
    objs = m.finalize()
    return objs, L.stats(objs)
