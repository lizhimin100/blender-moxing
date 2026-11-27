"""
bs_model.py —— 铁匠铺 v10 的形体定义（低模优先，曲面细分是最后一步）

v10 的主线只有一条：**把"铁匠铺自己的符号"换成"阵营的符号"，向兵营 v4 看齐。**

  * 徽记：交叉锻锤 / 脊端铁砧 → **盾 + 王冠**（`crest()` / `emblem()` 与 br_model 同源，
    同一段折线、同一套比例：盾 1.00·sz 宽 × 1.05·sz 高，冠带 + 三尖 + 三宝石）。
    铁匠铺的"铁砧"语汇退回道具与招牌（门口的砧、工具架、挂牌），不再当纹章用。
  * 旗帜：燕尾垂旗 / 墙面横幅 全部换成兵营的构形 —— 木杆 + 三只铁吊环 + 底角流苏 +
    金冠徽记；棚口垂旗保留 v9 修好的 L 形铁吊架（解决"旗从梁里长出来"）。
  * 屋顶：脊端那尊 0.55 m 的铁砧立饰在 RTS 尺度上是一根黑柱，换成**旗杆标准**（金球 + 燕尾旗 + 徽记）。

v10 的第二条线：**前场地面按兵营 v4 的教训重做**。原来是一块灰石板压 8 条 2–3 cm 薄贴片，
俯视泛白、拖动会闪。现在是一项一层高度的实体分层：夯土台 0.20 / 4 块大石板 0.26 / 牙子 0.28，
一条薄片都不留；煤堆、废铁堆、草簇、碎石、散板全部是有厚度的实体。

v8 留下来的形体主线（不动）：独立作业坡棚、八角收分烟囱、炉膛排烟罩、前场道具组。

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
CAN_Z0, CAN_Z1 = 5.44, 4.02
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

# 阵营色标准模块（形制与兵营 v4 同源：筝形盾 / 燕尾垂旗 / 墙面横幅）
SHIELD_W, SHIELD_H = 1.22, 1.50
SHIELD_S = 0.84, 1.02
BANNER_W, BANNER_H = 0.80, 1.45          # 棚口垂旗：v9 是 0.66 × 1.35，徽记放不下
WALLBAN_W, WALLBAN_H = 1.95, 2.35

# 前场地面分层（兵营 v4 口径：一项一层高度，不留薄片）
G_EARTH = 0.20                   # 夯土台顶面
G_PAVE = 0.26                    # 铺石顶面（道具站在这一层）
G_CURB = 0.28                    # 牙子顶面（比铺石高 2 cm，收住场地边缘）


def zroof(x):
    return RIDGE_Z - SLOPE * abs(x)


def can_z(y):
    t = (y - CAN_Y0) / (CAN_Y1 - CAN_Y0)
    return CAN_Z0 + t * (CAN_Z1 - CAN_Z0)


def out_sign(x):
    """贴墙件的朝外方向：+X 面为 +1，−X 面为 −1。"""
    return 1 if x > 0 else -1


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
        """只登记，不定最终拓扑。

        v10：`bevel / seg / sub` 三个参数保留在签名里（老调用不用改），但**低模与细分
        的差别不再在建模期决定**，全部压到 `finalize()` 按"体量件 / 小件"分档 ——
        与兵营 v4 同一条管线：形体只定义一次，低模分支不倒角不细分、全平面着色。
        """
        if ob is None:
            return None
        self.items.append((ob, bevel, sub, seg))
        return ob

    # ── 1. 基座与前场地面（兵营 v4 口径：一层一个高度，不留薄片）─────────────
    def base(self):
        M = self.M
        self.add(box("plinth_a", (0, -0.20, 0.13), (9.10, 7.10, 0.26), M["stone_dark"]))
        self.add(box("plinth_b", (0, -0.20, 0.06), (9.44, 7.44, 0.12), M["stone_mid"]))
        # 前场：夯土台，顶面 0.20。v9 是一整块 stone_mid 石板 —— 和墙体只差一档，
        # 俯视时整块场地泛白，建筑像浮在一块水泥板上（兵营 v4 的同一条教训）。
        self.add(box("yard", (0.00, 6.52, G_EARTH * 0.5), (9.20, 2.50, G_EARTH),
                     M["earth"]), 0.024)
        # 4 块 2.2 × 2.36 的大石板：6 cm 厚、顶面 0.26，缝 4.5 cm 直接露出夯土。
        # 缝是**凹进去 6 cm** 的真缝，不是画在上面的线 —— 上一版的 8 条 3 cm 薄贴片
        # 在 RTS 尺度只剩亚像素，拖动视角就是一片闪。
        x0, x1 = -4.52, 4.52
        n, gap = 4, 0.045
        t = G_PAVE - G_EARTH
        w = ((x1 - x0) - (n - 1) * gap) / n
        for i in range(n):
            cx = x0 + w * 0.5 + i * (w + gap)
            self.add(box("pave", (cx, 6.54, G_PAVE - t * 0.5), (w, 2.36, t),
                         M["paving"]), 0.010)
        # 前牙子：收住场地边缘，顶面比铺石高 2 cm
        self.add(box("yard_kerb", (0.00, 7.80, G_CURB * 0.5), (9.20, 0.18, G_CURB),
                     M["stone_dark"]), 0.014)
        # 门槛石：比铺石高一级（0.31），进门要抬脚
        self.add(box("threshold", (WING_CX, 5.42, 0.26), (DOOR_W + 0.30, 0.30, 0.10),
                     M["stone_light"]), 0.010)

    # ── 1.4 前场点缀（全部是有厚度的实体，一片薄贴片都不留）─────────────────
    def ground_detail(self):
        """煤堆 / 煤渣 / 草簇 / 碎石 / 散板。

        审美口径（与兵营 v4 一致）：俯视时场地要有 2–3 个"深色团块"把地面的中间调
        压下去，再靠草簇和碎石把边缘打碎；但不能有任何"一条线"的物件 ——
        细长薄片在 RTS 相机下会闪，也不读信息。
        """
        M = self.M
        # 煤仓：木框 + 满仓碎煤 + 三块滚出来的碎煤。俯视是一块深色方块 + 一圈木边，
        # 比"一坨纯黑的圆堆"读得清 —— 纯黑压在灰铺石上会读成一个洞（第一版就是这个）。
        bx, by = 3.94, 7.16
        self.add(box("coal_bin_floor", (bx, by, G_PAVE + 0.03), (1.04, 0.76, 0.06),
                     M["wood_dark"]), 0.008)
        for sgn in (-1, 1):
            self.add(box("coal_bin_side", (bx + sgn * 0.49, by, G_PAVE + 0.22),
                         (0.06, 0.76, 0.40), M["wood_warm"]), 0.008)
            # 端板做到 0.92 宽（夹在两侧板之间）、矮 4 mm：端板与侧板顶面同高会在四角共面
            self.add(box("coal_bin_end", (bx, by + sgn * 0.35, G_PAVE + 0.218),
                         (0.92, 0.06, 0.392), M["wood_warm"]), 0.008)
        self.add(box("coal_bin_fill", (bx, by, G_PAVE + 0.19), (0.90, 0.62, 0.22),
                     M["coal"]), 0.006)
        rnd = random.Random(23)
        for i in range(3):
            a = rnd.random() * math.tau
            self.add(box("coal_bin_lump", (bx + math.cos(a) * 0.26, by + math.sin(a) * 0.15,
                                       G_PAVE + 0.35), (0.18, 0.16, 0.12), M["coal"],
                         rot=(rnd.random() * 0.5, rnd.random() * 0.5, rnd.random() * 3)),
                     0.008)
        # 煤渣：炉口正前方一片踩开的黑渣。7 边、3.5 cm 厚的实体，压在铺石上（顶面 0.295）
        prof = []
        for i in range(7):
            a = math.tau * i / 7.0 + 0.31
            k = 0.74 + 0.26 * math.sin(2.7 + i * 2.1)
            prof.append((0.30 + math.cos(a) * 0.78 * k, 5.86 + math.sin(a) * 0.40 * k))
        self.add(extrude("coal_spill", prof, "Z", 0.035, (0.0, 0.0), M["coal"],
                         offset=G_PAVE), 0.0)
        # 草簇：长在场地边缘的夯土唇上（不是在铺石上），高度 0.20 左右
        for (x, y) in ((-4.55, 7.56), (4.54, 7.54), (-4.56, 6.02), (4.52, 5.52)):
            self.tuft(x, y, G_EARTH)
        # 碎石：靠牙子和角落，4 块，倾斜 15–25°（立着的方块会读成"随手丢的箱角"）
        for (x, y, s, rz) in ((-4.28, 7.56, 0.26, 0.4), (4.46, 5.30, 0.22, -0.7),
                              (-4.36, 6.88, 0.17, 1.2), (4.42, 6.62, 0.19, 0.2)):
            self.add(box("rubble", (x, y, G_PAVE + s * 0.26), (s, s * 0.78, s * 0.56),
                         M["stone_mid"], rot=(0.24 * s, 0.18 * s, rz)), 0.006)
        # 一块散板：靠着煤堆，读完"这里有人干活"
        self.add(box("plank_loose", (1.56, 7.54, G_PAVE + 0.025), (0.94, 0.16, 0.05),
                     M["wood_dark"], rot=(0.02, 0.02, 0.32)), 0.006)

    def tuft(self, x, y, z0, h=0.21):
        """草簇：三片 1.8 cm 厚的草叶，各向外倾 12°、高低差 2 cm（同高会在叶心闪）。"""
        M = self.M
        for k in range(3):
            a = math.radians(18 + k * 60)
            hh = h * (0.84 + 0.11 * k)
            self.add(box("tuft", (x + 0.014 * math.cos(a + 1.1), y + 0.014 * math.sin(a + 1.1),
                                  z0 + hh * 0.48), (0.115, 0.018, hh), M["moss"],
                         rot=(0.20 * math.cos(a), 0.20 * math.sin(a), a)), 0.0)

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
                    zz = 0.62 + i * 0.82
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
                self.add(box("buttress", (sx * (W2 + 0.13), yy, (EAVE - 0.55) * 0.5),
                             (0.26, 0.55, EAVE - 0.55), M["stone_mid"]), 0.024)

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
        # 柱身顶面压到 4.14（低于檐口石 4.16），压顶石再盖住它 —— 两个顶面同高会共面
        self.add(box("bay_pier", (-1.68, 5.18, 2.07), (0.36, 0.52, 4.14), M["stone_light"]), 0.020)
        self.add(box("bay_pier_cap", (-1.68, 5.18, 4.16), (0.46, 0.62, 0.16), M["stone_mid"]), 0.012)
        # 龛内：地面 0.185（比前场夯土 0.20 低 1.5 cm）—— 两者同高会在龛口那一圈共面闪烁
        self.add(box("bay_floor", (cx, (BAY_Y0 + y1) * 0.5, 0.0925), (r * 2, y1 - BAY_Y0, 0.185),
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

    # ── 5. 炉膛排烟罩 + 屋顶黑铁烟管 ────────────────────────────────────────
    def forge_hood(self):
        M = self.M
        cx, cy = 0.29, 4.46
        bz, tz = 2.62, 4.32
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
        # 排烟：罩子的喉管接到坡棚底面，棚面上只留一个**铁百叶通风口**。
        # v9 是一根升到 6.98 的黑铁管 + 锥形罩：正视时横在山墙木构前面，
        # 缩到棚面之上又读成一盏"黑灯罩"。作坊的排烟口本来就该在棚面上 ——
        # 现在从上面看是一块铁格栅，从正面看什么都不挡。
        self.add(revolve("flue_pipe", [(0.19, 0.0), (0.19, 0.50)], 8, (cx, cy, tz - 0.06),
                         M["iron"]), 0.0, 1)
        vz = can_z(cy) + 0.205
        self.add(box("vent_curb", (cx, cy, vz + 0.06), (0.70, 0.60, 0.18), M["iron"]), 0.010)
        # 顶面做成"盖板 + 五道百叶"：盖板比框大一圈，百叶压在盖板上。
        # 不这么分层的话，百叶会埋进框体里，从上面看只是一块光板。
        self.add(box("vent_plate", (cx, cy, vz + 0.16), (0.80, 0.68, 0.05), M["iron"]), 0.006)
        for i in range(5):
            self.add(box("vent_louver", (cx, cy - 0.24 + i * 0.12, vz + 0.20),
                         (0.68, 0.06, 0.045), M["iron"]), 0.003)
        for sx in (-1, 1):
            for sy in (-1, 1):
                self.add(box("vent_rivet", (cx + sx * 0.36, cy + sy * 0.31, vz + 0.17),
                             (0.06, 0.06, 0.05), M["iron"]), 0.003)

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
        # v10 删掉"龛内洗墙光板"：2.4 × 1.6 的自发光面在拱洞里就是一块橙色屏幕，
        # 正面看把火焰的层次全压平了。火光交给火焰本体 + 引擎里的点光。

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
        self.add(box("ch_cornice", (cx, cy, CH_BREAST_TOP - 0.07), (w + 0.26, d + 0.26, 0.18),
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
        # 风向杆 + 阵营色燕尾小旗（不做十字风标：会被读成教堂）
        vz = top + 0.42
        self.add(revolve("vane_rod", [(0.028, 0.0), (0.028, 1.02)], 6, (cx, cy, vz),
                         M["iron"]), 0.0, 1)
        self.add(revolve("vane_ball", [(0.05, 0.0), (0.05, 0.05)], 6, (cx, cy, vz + 1.00),
                         M["iron"]), 0.0, 1)
        pen = [(0.0, 0.0), (0.68, -0.075), (0.52, -0.165), (0.68, -0.255), (0.0, -0.33)]
        self.add(extrude("vane_pennant", pen, "Y", 0.035, (cx, vz + 0.99),
                         M["team"], offset=cy), 0.004)
        self.add(box("vane_trim", (cx + 0.012, cy, vz + 0.825), (0.05, 0.045, 0.30),
                     M["team_trim"]), 0.003)

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
        self.ridge_standard()
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
                         (cx, cy, body_z1 + 0.09), M["iron"], phase=math.pi / 4), 0.0, 1)
        self.add(revolve("cup_spike", [(0.05, 0.0), (0.0, 0.40)], 5,
                         (cx, cy, body_z1 + 0.44), M["iron"]), 0.0, 1)

    def ridge_standard(self):
        """屋脊旗杆标准：铸铁底座 + 八角木杆 + 金球 + 燕尾旗 + 阵营徽记。

        v9 这里是"脊端铁砧立饰"（0.55 m 铁砧剪影 + 0.34 m 立杆）。在 RTS 距离上它读不出
        "砧"，只是一根黑柱，而且和门口的砧、工具架上的砧重复了三次。换成旗杆之后：

          * 屋顶轮廓多一条竖线，最高处出现一次阵营徽记（俯视也能看见）；
          * 铁砧语汇退回道具与招牌，符号只留一套（与兵营同一枚冠盾）。

        旗底必须高过脊上楼阁的铁尖（10.63）—— 低 5 cm 就会出现"旗面上长出一根铁刺"。
        """
        M = self.M
        y = 3.00
        z0 = RIDGE_Z + 0.29                 # 9.04：底座骑在脊铁压条（顶 9.07）上
        self.add(box("std_base", (0, y, z0), (0.38, 0.42, 0.22), M["iron"]), 0.012)
        self.add(box("std_step", (0, y, z0 + 0.14), (0.28, 0.32, 0.08), M["iron"]), 0.008)
        self.add(revolve("std_pole", [(0.052, 0.0), (0.042, 2.50)], 8, (0, y, z0 + 0.16),
                         M["wood_dark"]), 0.0, 1)
        ztop = z0 + 0.16 + 2.50             # 11.70
        self.add(revolve("std_ball", [(0.082, 0.0), (0.058, 0.05), (0.018, 0.13)], 8,
                         (0, y, ztop), M["gold"]), 0.0, 1)
        # 燕尾旗：与兵营屋顶旗同一个轮廓（迎风边两道缺口），旗底 10.74 —— 压过楼阁尖 0.11
        fw, fh = 1.16, 0.72
        zt = ztop - 0.28                    # 11.42
        prof = [(0.0, 0.0), (fw, -0.085), (fw * 0.82, -0.50 * fh), (fw, -0.94 * fh), (0.0, -fh)]
        self.add(extrude("std_flag", prof, "Y", 0.045, (0.0, zt), M["team"],
                         offset=y + 0.035), 0.004)
        # 旗杆：只做一根素杆夹住布（不做"旗筒"包边 —— 0.085 宽的浅色条会读成一根骨头）
        self.crest("std_crest", "Y", 0.33, y + 0.058, zt - 0.47, 0.40)

    # ── 9. 山墙木构 + 百叶通风口 ────────────────────────────────────────────
    def gable_timber(self):
        """山墙半木构。所有构件宽度都按"该高度处的屋面净宽"收，绝不捅出屋面。"""
        M = self.M
        yy = YF + 0.06
        tz = 5.80
        half_at = lambda z: (RIDGE_Z - z) / SLOPE
        self.add(box("collar", (0, yy, tz - 0.01), (half_at(tz) * 2 - 0.24, 0.15, 0.30),
                     M["wood_dark"]), 0.016)
        # 山墙腰线的阵营色横带：必须整体高于坡棚板顶（5.665），否则会从板面上"穿出来"
        # v9：抬到 collar 前表面，读作"横梁上的阵营色包边"，正/侧两轴都不与板相交
        self.add(box("gable_band", (0, yy + 0.055, 5.78),
                     (half_at(5.70) * 2 - 0.36, 0.12, 0.10), M["team"]), 0.008)
        # 山墙中段的百叶通风口：木框圈住，读"阁楼排烟口"而不是"窗"
        vz = 6.58
        for sgn in (-1, 1):
            self.add(box("vent_post", (sgn * 0.78, yy + 0.01, (5.95 + 7.26) * 0.5),
                         (0.17, 0.15, 7.26 - 5.95), M["wood_dark"]), 0.012)
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
            self.add(box("porch_foot", (xx, y1 - 0.12, G_PAVE + 0.06), (0.32, 0.32, 0.22),
                         M["stone_mid"]), 0.014)
            self.add(beam("porch_brace", (xx, y1 - 0.14, z0 - 0.86), (xx, y1 - 0.92, z0 - 0.12),
                          0.13, 0.11, M["wood_dark"]), 0.010)

    # ── 12. 侧窗 ────────────────────────────────────────────────────────────
    def windows(self):
        self.side_window("winL", (-W2, -1.10, 2.80), -1, 0.74, 1.10)
        self.side_window("winR", (W2, 1.45, 2.80), 1, 0.74, 1.10)
        # v10 删掉 winR2（y −2.15）：后扶壁在 y −2.05、宽 0.55，窗框宽 0.98 ——
        # 两者必然相交（体检里 buttress.002 ↔ winR2_frame 12 个三角形）；
        # 而且它会顶到墙面横幅的布边。侧墙留一扇窗 + 一面旗，够了。

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
        """标准筝形盾：金边 + 阵营色盾面 + 冠盾徽记（`crest(shield=False)`）。

        与兵营 v4 的 `kite()` 逐字同源：盾面本身已经是一面盾，徽记只画王冠，
        避免"盾中盾"。out 是盾面朝外的方向（X 面墙才有用）。
        """
        M = self.M
        cx, cy, cz = center
        if face == "Y":
            self.add(kite_shield(name + "_rim", (cx, cy, cz), w + 0.14, h + 0.14, 0.08,
                                 M["gold"]), 0.012)
            self.add(kite_shield(name + "_field", (cx, cy + 0.05, cz), w, h, 0.09,
                                 M["team"]), 0.012)
            # 盾面厚 0.09、圆心 cy+0.05 → 前表面 cy+0.095。
            # 徽记中心 cy+0.090 → 背面埋 8 mm、正面凸 8 mm（v4 的贴面口径）
            self.emblem(name, "Y", cx, cy + 0.090, cz + h * 0.06, w, h, shield=False)
        else:
            hw, hh = w * 0.5, h * 0.5
            prof = [(-hh, hw), (hh, hw), (hh * 0.90, -hw * 0.12), (0.0, -hw), (-hh * 0.90, -hw * 0.12)]
            pb = [(p[0] - 0.07, p[1] + 0.07) for p in prof]
            self.add(extrude(name + "_rim", pb, "X", 0.08, (cy, cz), M["gold"],
                             offset=cx + out * 0.01), 0.012)
            self.add(extrude(name + "_field", prof, "X", 0.09, (cy, cz), M["team"],
                             offset=cx + out * 0.06), 0.012)
            self.emblem(name, "X", cx + out * 0.090, cy, cz + h * 0.06, w, h, shield=False)

    def crest(self, name, face, cx, cy, cz, sz, out=1, shield=True):
        """阵营徽记：盾牌（金边蓝底）+ 王冠（冠带 + 三尖 + 三宝石）。

        与 br_model 的 `crest()` **同一段几何**（这套资产的"符号只准有一套"）：
        盾是 7 段折线、王冠是矩形 + 三角形、宝石是方点，没有一条曲线。
        cz = 底边（不是中心）；含盾时 1.00·sz 宽 × 1.05·sz 高；
        `shield=False` 只画王冠，用在本身就是一面盾的载体上。
        """
        M = self.M
        dep = 0.028

        def poly(tag, pts, mat, dy=0.0):
            p = [(u * sz, v * sz) for (u, v) in pts]
            if face == "Y":
                self.add(extrude(name + tag, p, "Y", dep, (cx, cz), mat, offset=cy + dy), 0.003)
            else:
                self.add(extrude(name + tag, p, "X", dep, (cy, cz), mat, offset=cx + out * dy), 0.003)

        def crown(du, dv, ch, dy0):
            """王冠：底边中点在 (du, dv)，高 ch、宽 1.30·ch。"""
            w = ch * 0.65
            poly("_band", [(du - w, dv), (du + w, dv), (du + w, dv + ch * 0.21),
                           (du - w, dv + ch * 0.21)], M["gold"], dy=dy0)
            for i, (a, b, top) in enumerate(((-0.94, -0.24, 0.74),
                                             (-0.20, 0.20, 1.00),
                                             (0.24, 0.94, 0.74))):
                poly("_spike%d" % i,
                     [(du + a * w, dv + ch * 0.19), (du + b * w, dv + ch * 0.19),
                      (du + (a + b) * 0.5 * w, dv + ch * top)],
                     M["gold"], dy=dy0 + 0.004)
            for i, uu in enumerate((-0.56, 0.0, 0.56)):
                g = ch * 0.058
                poly("_gem%d" % i, [(du + uu * w - g, dv + ch * 0.045),
                                    (du + uu * w + g, dv + ch * 0.045),
                                    (du + uu * w + g, dv + ch * 0.155),
                                    (du + uu * w - g, dv + ch * 0.155)],
                     M["coal"], dy=dy0 + 0.008)

        if shield:
            edge = [(-0.50, 1.05), (0.50, 1.05), (0.50, 0.40), (0.28, 0.16), (0.0, 0.0),
                    (-0.28, 0.16), (-0.50, 0.40)]
            rim = [(-0.48, 1.03), (0.48, 1.03), (0.48, 0.40), (0.27, 0.18), (0.0, 0.035),
                   (-0.27, 0.18), (-0.48, 0.40)]
            field = [(-0.40, 0.94), (0.40, 0.94), (0.40, 0.38), (0.22, 0.16), (0.0, 0.10),
                     (-0.22, 0.16), (-0.40, 0.38)]
            poly("_edge", edge, M["coal"], dy=0.004)
            poly("_rim", rim, M["gold"], dy=0.008)
            poly("_field", field, M["roof_edge"], dy=0.012)
            crown(0.0, 0.40, 0.46, 0.017)
        else:
            crown(0.0, 0.0, 0.68, 0.0)

    def emblem(self, name, face, cx, cy, cz, w, h, shield=True):
        """把徽记放进纹章框：cz 是框中心，整体上移 5%（与 br_model 一致）。"""
        sz = min(w, h) * (0.80 if shield else 0.74)
        zc = cz + h * 0.05
        zb = zc - sz * (0.525 if shield else 0.34)
        if face == "Y":
            self.crest(name, "Y", cx, cy, zb, sz, shield=shield)
        else:
            self.crest(name, "X", cx, cy, zb, sz, out=(1 if cx > 0 else -1), shield=shield)

    def banner(self, name, x, y_front, z_eave):
        """棚口垂旗：L 形铁吊架 + 木旗杆 + 三只铁吊环 + 底角流苏 + 冠盾徽记。

        悬挂结构沿用 v9 修好的 L 形吊架（竖杆从梁底垂下、横臂挑出 0.28），
        因为 v8 的"旗杆画在梁里"是真错位；**旗面构形换成兵营的垂旗**：
        木杆 + 金端头 + 三只吊环 + 底角流苏 + 贴回布面的徽记。两座建筑的旗
        从此是同一套零件（杆 / 环 / 流苏 / 徽记），只是尺寸不同。
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
        # ② 横臂（从封檐板外侧挑出到杆心）+ 挂钩
        for sgn in (-1, 1):
            y0 = y_front + 0.005
            self.add(box(name + "_arm", (x + sgn * w * 0.42, (y0 + y_pole + 0.035) * 0.5, z_arm),
                         (0.05, y_pole + 0.035 - y0, 0.06), M["iron"]), 0.005)
            self.add(box(name + "_hook", (x + sgn * w * 0.42, y_pole, z_arm - 0.045),
                         (0.042, 0.05, 0.09), M["iron"]), 0.004)
        # ③ 木旗杆 + 两端金端头（比布宽 0.30，两端各出 0.15）
        self.add(box(name + "_pole", (x, y_pole, z_pole), (w + 0.30, 0.07, 0.07),
                     M["wood_warm"]), 0.006)
        for sgn in (-1, 1):
            self.add(box(name + "_fin", (x + sgn * (w * 0.5 + 0.13), y_pole, z_pole),
                         (0.09, 0.10, 0.10), M["gold"]), 0.005)
        # ④ 旗布：顶边挂在杆下；下缘燕尾（与兵营垂旗同轮廓）
        zt = z_pole - 0.055
        prof = [(-w * 0.5, 0.0), (w * 0.5, 0.0), (w * 0.5, -h * 0.80),
                (w * 0.12, -h), (-w * 0.12, -h), (-w * 0.5, -h * 0.80)]
        self.add(extrude(name + "_cloth", prof, "Y", 0.055, (x, zt), M["team"],
                         offset=y_pole), 0.010)
        # ⑤ 三只铁吊环：下沿咬住布顶 2 cm、上沿咬住杆底 1.5 cm
        for k in (-1, 0, 1):
            self.add(box(name + "_ring", (x + k * w * 0.33, y_pole, zt + 0.030),
                         (0.05, 0.05, 0.10), M["iron"]), 0.003)
        # ⑥ 底角流苏：插进布角 2 cm
        for sgn in (-1, 1):
            self.add(box(name + "_tass", (x + sgn * (w * 0.5 - 0.05), y_pole,
                                          zt - h * 0.78 - 0.08),
                         (0.075, 0.075, 0.20), M["team_trim"]), 0.004)
        # ⑦ 徽记：中心 y_pole+0.021 → 背面埋进布 2 cm、正面凸 7 mm
        self.emblem(name, "Y", x, y_pole + 0.021, zt - h * 0.47, w * 0.92, h * 0.52)

    def wallbanner(self, name, center, face, w=WALLBAN_W, h=WALLBAN_H, out=1):
        """墙面垂旗：挑杆 + 三只铁吊环 + 底角流苏 + 冠盾徽记。

        与兵营 v4 的 `wallbanner()` 同一套零件与同一组偏移（徽记中心 = 布心 ± 0.023），
        只把"铁托架"加长到贴住墙 —— 兵营那份的托架离墙 0.28，是因为它的横幅挂在
        木构立柱外面；铁匠铺是石墙，托架不贴墙会读成"旗浮在半空"。
        """
        M = self.M
        cx, cy, cz = center
        hw, hh = w * 0.5, h * 0.5
        prof = [(-hw, hh), (hw, hh), (hw, -hh * 0.78), (hw * 0.34, -hh),
                (-hw * 0.34, -hh), (-hw, -hh * 0.78)]
        rz = cz + hh + 0.140
        if face == "Y":
            self.add(extrude(name + "_cloth", prof, "Y", 0.06, (cx, cz), M["team"], offset=cy), 0.012)
            self.add(box(name + "_rod", (cx, cy, rz), (w + 0.38, 0.09, 0.09), M["wood_dark"]), 0.006)
            for sgn in (-1, 1):
                self.add(box(name + "_fin", (cx + sgn * (hw + 0.19), cy, rz),
                             (0.08, 0.11, 0.11), M["gold"]), 0.005)
                self.add(box(name + "_brk", (cx + sgn * hw * 0.70, cy - 0.11 * out, rz - 0.02),
                             (0.05, 0.26, 0.05), M["iron"]), 0.003)
                self.add(box(name + "_tass", (cx + sgn * (hw - 0.05), cy, cz - hh * 0.78 - 0.10),
                             (0.075, 0.075, 0.20), M["team_trim"]), 0.004)
            for k in (-1, 0, 1):
                self.add(box(name + "_ring", (cx + k * hw * 0.54, cy, cz + hh + 0.055),
                             (0.05, 0.05, 0.11), M["iron"]), 0.003)
            self.emblem(name, "Y", cx, cy + 0.023 * out, cz + h * 0.01, w * 0.78, h * 0.60)
        else:
            self.add(extrude(name + "_cloth", prof, "X", 0.06, (cy, cz), M["team"], offset=cx), 0.012)
            self.add(box(name + "_rod", (cx, cy, rz), (0.09, w + 0.38, 0.09), M["wood_dark"]), 0.006)
            for sgn in (-1, 1):
                self.add(box(name + "_fin", (cx, cy + sgn * (hw + 0.19), rz),
                             (0.11, 0.08, 0.11), M["gold"]), 0.005)
                self.add(box(name + "_brk", (cx - out_sign(cx) * 0.13, cy + sgn * hw * 0.70,
                                            rz - 0.02), (0.38, 0.05, 0.05), M["iron"]), 0.003)
                self.add(box(name + "_tass", (cx, cy + sgn * (hw - 0.05), cz - hh * 0.78 - 0.10),
                             (0.075, 0.075, 0.20), M["team_trim"]), 0.004)
            for k in (-1, 0, 1):
                self.add(box(name + "_ring", (cx, cy + k * hw * 0.54, cz + hh + 0.055),
                             (0.05, 0.05, 0.11), M["iron"]), 0.003)
            self.emblem(name, "X", cx + out_sign(cx) * 0.023 * out, cy, cz + h * 0.01,
                        w * 0.78, h * 0.60)

    def heraldry(self):
        """阵营色五件套：烟囱大盾 / 侧墙垂旗 / 侧墙盾 / 门前盾 / 棚口双垂旗。

        全部使用 `crest()`（盾 + 王冠），与兵营同一枚符号 —— 这套资产里
        **只有一套纹章**，换阵营只换 team / team_trim 两个材质。
        """
        # ① 烟囱胸墙大盾（正立面最醒目的那块）
        self.kite("shield_ch", (CH_CX + 0.04, CH_Y1 + 0.10, 3.34), "Y", SHIELD_W, SHIELD_H)
        # ② 侧墙垂旗：挂在两扇窗之间（不压窗）
        self.wallbanner("wbanner_L", (W2 + 0.22, -0.55, 2.90), "X", 1.95, 2.10)
        # ③ 侧墙盾
        self.kite("shield_R", (-W2 - 0.03, 0.35, 2.86), "X", 1.16, 1.44, out=-1)
        # ④ v10 删掉"门前小盾"：门廊翼正面只有 1.85 m 的拱门 + 拱心石，
        #    盾的底尖必然扎进拱心石里（体检 door_key ↔ shield_door_rim 12 个三角形）。
        #    门头已经有三件东西（拱券、拱心石、提灯），不再加第四件。
        # ⑤ 背墙横幅（1.55 × 1.90）：后墙原本是一片素石，后 3/4 视角没有任何信息。
        #    cy 取 −3.52（离墙 0.12），托架朝 +Y 扎进墙里（out=−1）
        self.wallbanner("wbanner_B", (0, YB - 0.22, 2.48), "Y", 1.55, 1.95, out=-1)
        # ⑥ 作业坡棚口的两面垂旗：x 让开门廊翼坡屋面与烟囱胸墙
        for tag, xx in (("L", -1.26), ("R", 2.00)):
            self.banner("banner_" + tag, xx, CAN_Y1 + 0.165, can_z(CAN_Y1) - 0.30)

    # ── 14. 细部（招牌 / 提灯 / 挂件）──────────────────────────────────────
    def details(self):
        M = self.M
        # v10 删掉檐下托牙：0.15 m 的方料在背墙上只剩一个深色圆点，读成"墙上三个洞"。
        # 檐口已经有封檐板 + 露明椽 + 檐口阵营色压条三层，不需要第四层。
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
        lx, ly, lz = -2.16, WING_Y1 + 0.14, 2.58
        self.add(beam("lan_arm", (lx - 0.02, ly - 0.22, lz + 0.26), (lx - 0.02, ly + 0.02, lz + 0.26),
                      0.06, 0.06, M["iron"]), 0.005)
        self.add(box("lan_cage", (lx - 0.02, ly - 0.12, lz), (0.22, 0.22, 0.30), M["glow"]), 0.008)
        self.add(box("lan_top", (lx - 0.02, ly - 0.12, lz + 0.19), (0.28, 0.28, 0.08),
                     M["iron"]), 0.006)
        self.add(box("lan_bot", (lx - 0.02, ly - 0.12, lz - 0.19), (0.26, 0.26, 0.07),
                     M["iron"]), 0.006)
        # v10 删掉侧墙根的"煤槽"（两根柱 + 一道横杆）：前场已经有煤仓，
        # 而且它和原木堆挤在同一段墙根上（体检里 coal_post ↔ log3 相交）。

    # ── 15. 前场道具 ────────────────────────────────────────────────────────
    def props(self):
        # 站在铺石上：埋 4 mm。正好踩在 0.26 的铺石顶面上会让底面与铺石顶面共面，
        # 俯视拖动时那一圈会闪（兵营 v4 的"同高共面"教训）。
        z = G_PAVE - 0.006
        self.anvil((0.10, 6.92, z))                      # 中央重型铁砧
        self.bellows((1.92, 4.16, 0.05))                 # 风箱：喷嘴朝炉膛（落在龛内地面）
        self.tool_rack("rack_L", (-3.88, 6.72, z))       # 左立式工具架（让开主入口）
        self.tool_rack("rack_R", (3.42, 6.40, z))        # 右立式工具架
        self.quench_barrel((1.44, 6.10, z))
        self.bucket("coal_a", (-1.66, 7.18, z), 0.31, 0.46)
        self.bucket("coal_b", (2.58, 7.14, z), 0.29, 0.42)
        self.ingot_basket("ingots", (-2.46, 7.26, z))
        # v10 删掉"靠墙斜放的长剑 / 战斧"：门廊翼整面都是拱洞，两件兵器只能扎进拱券石里
        # （体检里 door_arch ↔ axe_haft 12 个三角形相交）。武器语汇留给兵营，铁匠铺留工具。
        self.grindstone((3.96, 5.60, z))
        # v10 删掉侧墙根的原木堆：基座外沿到墙面只有 0.55 m，放不下 0.6 m 宽的木堆，
        # 三根原木必然有一根插进墙里（体检 mass ↔ log3 6 个三角形）。燃料语汇交给煤仓。
        self.pot("pot_a", (-4.56, 4.56, 0.0), 0.31, 0.88)
        self.pot("pot_b", (-4.94, 5.34, 0.0), 0.24, 0.68)

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
            self.add(box(name + "_pritchel", (x - 0.34 * s, y, zb + 0.52 * s),
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
        self.add(box("billet", (x - 0.10 * s, y + 0.02 * s, zt + 0.038 * s),
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
                             (x - 0.54 + i * 0.36, y + 0.10, zz - 0.085), (0.07, 0.10, 0.07),
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
            self.add(box(name + "_slat%d" % i, (xx, y, z + 0.28), (0.10, 0.58, 0.44),
                         M["wood_warm"]), 0.006)
        for sy in (-1, 1):
            self.add(box(name + "_side", (x, y + sy * 0.29, z + 0.30), (0.84, 0.06, 0.48),
                         M["wood_warm"]), 0.006)
        # 四块铁锭平铺一层、各自抬 4 mm：层高一致会在顶面连成一片共面，
        # 分层堆又会让上层没有支撑（体检会判悬空）。
        for i in range(4):
            ox = 0.15 if i % 2 else -0.15
            oy = 0.09 if i // 2 else -0.09
            self.add(box(name + "_ingot%d" % i, (x + ox, y + oy, z + 0.537 + i * 0.004),
                         (0.26, 0.15, 0.10), M["iron"], rot=(0, 0, 0.08 * (i - 1.5))), 0.006)

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
        for step in (self.base, self.ground_detail, self.mass, self.forge_bay,
                     self.work_canopy, self.forge_hood, self.forge_fire, self.chimney,
                     self.roof, self.gable_timber, self.wing, self.porch, self.windows,
                     self.heraldry, self.details, self.props):
            step()
        return self

    def finalize(self, bevel=True):
        """低模定形 → 最后一步才细分（与兵营 v4 同一条管线）。

        细分版只给"三个方向都够厚"的体量件上 `Bevel(2 段) + Catmull-Clark(1 级)`：
        墙体、屋面、桶、砧座这些件的棱才真的磨圆；小件（旗布、薄板、铆钉、草叶）
        1 段倒角就够 —— 0.1 m 的倒角在 30 m 外只有半个像素，全量 CC 只会把面数
        推到十万级，与"资产不重"冲突。

        低模版反过来：小件一个倒角都不给（一个 box 从 26 面降到 6 面），
        只给 > 0.55 m 的体量件留 1 段倒角，其余全平面着色 —— 硬边才是低模。
        """
        for (ob, bev, sub, seg) in self.items:
            co = ob.data.vertices
            if not len(co):
                continue
            dims = [max(v.co[i] for v in co) - min(v.co[i] for v in co) for i in range(3)]
            if self.smooth:
                chunky = min(dims) >= 0.10 and dims[0] * dims[1] * dims[2] >= 0.12
                # 倒角 1 段就够：CC 会把这条 0.02 的斜面本身再磨圆，2 段倒角在
                # 30 m 外看不出差别，却把每条棱的面数翻倍（整模 89k → 66k）
                L.finalize(ob, bevel=max(bev, 0.010), seg=1,
                           sub=1 if chunky else 0, flat=False)
            else:
                # 低模只给真正的大体量（> 1.2 m）留 1 段倒角：屋面、墙体、基座。
                # 0.02 的倒角在 RTS 尺度只有 1 像素，但能让最大的几条棱不吃光
                small = max(dims) < 1.20
                b = 0.0 if (not bevel or small or bev < 0.008) else bev
                L.finalize(ob, bevel=b, seg=seg, sub=0, flat=True)
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


def build(smooth=True, unwrap=True, bevel=True):
    m = Model(smooth, unwrap).build()
    objs = m.finalize(bevel=bevel)
    return objs, L.stats(objs)
