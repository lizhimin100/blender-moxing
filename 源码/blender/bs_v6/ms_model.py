"""
ms_model.py —— 神秘圣地（Mystic Sanctuary）v3：穹顶圣所 + 环列巨晶 + 发光门庭

第七座。六座的屋顶类型已经两两不同（gable_cross / flat_crenel / crown_eave /
gable_steep / mono_pitch / open_shed），这一座补的是**穹顶**：
`dome_ring` —— 十二边形鼓座上的**鼓形穹顶** + 采光亭 + 晶尖，外加一圈环列的巨型水晶。

为什么是"圆"：
  ① 六座全是矩形平面，俯视时都是一堆平行线。圣地必须是**同心圆** ——
     台基三级 / 圣所十二边形 / 鼓座 / 穹顶 / 采光亭，五个同心环。
     这不是装饰选择，是"一眼能从六座里分出来"的唯一办法。
  ② 硬边管线的"圆"是**分面圆**：12 条边、7 圈环、全部平着色。棱角在斜阳下是一条条
     竖亮的细线 —— 越看越像一块切出来的宝石，这正是"圣地"要的质感。

三件必须同时成立的事（缺一件就读成"石头凉亭"）：
  ① **一条 1.4 m 深的拱洞，尽头是一整块发光的门**。门廊不做"柱廊"而做**实心山门**：
     柱廊在这个尺度上会读成一堆细杆，实心体块才有"进不去的地方"那种分量；
     而 1.4 m 的进深让发光门只露出一部分 —— 越看不全越神秘。
  ② **环列巨晶**：场地上四簇水晶，三立一断。断的那一簇倒在台阶旁 ——
     一个"曾经被打断过、还在用"的圣地，比完整的更神秘。
  ③ **穹顶的十二根亮脊**：近黑的深板岩穹顶上铺 `roof_pale` 棱线，俯视时才读得出
     "这是穹顶"而不是"一个深色圆盘"（伐木场踩过的同一个坑：深色面上要用亮脊）。

明度秩序（这是"干净、克制、有层次"的全部来源）：
     暖棕场地 → 中灰台基 → **亮**台基压顶 → 中灰墙身（暗色盲拱）→ **亮**檐口
   → 中灰鼓座（紫窗）→ **近黑**穹顶（亮脊）→ **亮**采光亭 → **近黑**锥顶
   → 金箍 → 紫晶尖。
  一条"中 → 亮 → 中 → 亮 → 近黑"的节拍，每一层只做一件事。

坐标：X 右、Y 前（+Y = 正面）、Z 上；原点在占地中心，z = 0 地面。
交付前整体沿 X 镜像一次（与另六座一致），所以建模期的 +X 在成品里是 −X。
"""
import math
from math import tau as TAU

import bpy
from mathutils import Vector

import bslib as L
import br_model as BR
from bslib import (arch_band, beam, box, extrude, mesh_obj, revolve, tube_band)
from br_model import mirror_x

# ── 场地 ────────────────────────────────────────────────────────────────────
YARD_X0, YARD_X1 = -6.85, 6.85
YARD_Y0, YARD_Y1 = -6.45, 7.50
G_Z = 0.22                       # 夯土面
RUNE_R = 6.16                    # 地面符文圈半径

# ── 台基（十二边形；一律用 apothem 表达，边长 = 2·a·tan15°）───────────────────
A1, A2, A3 = 5.30, 4.80, 4.32    # 三级台身 apothem
C1, C2, C3 = 5.37, 4.87, 4.39    # 三级压顶 apothem（外挑 70 mm）
Z1A, Z1B = 0.22, 0.46
Z2A, Z2B = 0.50, 0.74
Z3A, Z3B = 0.78, 1.00
CP1, CP2, CP3 = (0.44, 0.52), (0.72, 0.80), (0.98, 1.06)
DECK = 1.06

# ── 圣所（十二边形，外 apothem 3.66）────────────────────────────────────────
CA = 3.66
WALL_T = 0.30
CZ0, CZ1 = 1.04, 6.10
FACE_W = 2.0 * CA * math.tan(math.pi / 12)      # 1.961
FACE_A = [30 * k for k in range(12)]            # 面心；90 = 正面
VERT_A = [15 + 30 * k for k in range(12)]       # 棱线
CZ_TOP = 6.46

# ── 门廊（实心山门，从地面砌起）─────────────────────────────────────────────
BAY_X = 2.02                     # 体块半宽
BAY_Y0, BAY_Y1 = 3.46, 5.62      # 后沿埋进墙 0.20；前沿比台基正面多出 0.32
BAY_Z1 = 4.38                    # 体块顶
BAY_HW = 0.95                    # 拱洞半宽
BAY_SPRING = 3.10
BAY_APEX = BAY_SPRING + BAY_HW   # 4.05
CORN_Z0, CORN_Z1 = 4.38, 4.56    # 门廊挑檐
PED_HW = 2.16                    # 山花半宽
PED_Z = 5.78                     # 山花顶（离圣所檐口还有 0.30 的缝）
PIL_X = 1.82                     # 门廊正面两根壁柱

# ── 门洞 ────────────────────────────────────────────────────────────────────
DOOR_HW = 0.78
DOOR_SPRING = 3.14
DOOR_APEX = DOOR_SPRING + DOOR_HW

# ── 台阶 ────────────────────────────────────────────────────────────────────
STEP_N = 4
STEP_T = 0.34
STEP_R = (DECK - G_Z) / (STEP_N + 1)      # 0.168

# ── 鼓座 / 穹顶 ─────────────────────────────────────────────────────────────
DR_AP = 2.70
DR_Z0, DR_Z1 = 6.44, 8.70
DR_BAND = (8.28, 8.46)
DR_CORN = (8.70, 8.96)
# 穹顶母线：(apothem, z)。鼓形 —— 起脚 2.72，鼓到 2.84 再收；七段环。
DOME = [(2.72, 8.96), (2.84, 9.40), (2.80, 9.96), (2.58, 10.56),
        (2.16, 11.18), (1.52, 11.80), (0.76, 12.36), (0.28, 12.62)]
DOME_TOP = 12.62

# ── 采光亭 / 尖顶 ───────────────────────────────────────────────────────────
LAN_AP = 0.84
LAN_Z0, LAN_Z1 = 12.42, 13.94
SPIRE_TOP = 15.20
FINIAL_TOP = 16.18


# ── 通用构造 ────────────────────────────────────────────────────────────────
def circ(a, sides=12):
    """apothem → 外接圆半径。"""
    return a / math.cos(math.pi / sides)


def ng_prism(name, a, z0, z1, mat, sides=12, phase=None, a_top=None):
    """正多边形棱柱（竖直）。a = 底 apothem；a_top 给定时收分。"""
    if phase is None:
        phase = math.pi / sides
    a_top = a if a_top is None else a_top
    r0, r1 = circ(a, sides), circ(a_top, sides)
    verts, faces = [], []
    for (r, z) in ((r0, z0), (r1, z1)):
        for s in range(sides):
            ang = phase + TAU * s / sides
            verts.append((r * math.cos(ang), r * math.sin(ang), z))
    m = sides
    for s in range(sides):
        i, j = s, (s + 1) % sides
        faces.append((i, j, m + j, m + i))
    faces.append(tuple(range(m - 1, -1, -1)))
    faces.append(tuple(range(m, 2 * m)))
    return mesh_obj(name, verts, faces, mat)


def ng_ring(name, a_in, a_out, z0, z1, mat, sides=12, phase=None):
    """正多边形环带（闭合，纯四边面）。"""
    if phase is None:
        phase = math.pi / sides
    ri, ro = circ(a_in, sides), circ(a_out, sides)
    verts, faces = [], []
    for z in (z0, z1):
        for s in range(sides):
            ang = phase + TAU * s / sides
            verts += [(ri * math.cos(ang), ri * math.sin(ang), z),
                      (ro * math.cos(ang), ro * math.sin(ang), z)]
    for s in range(sides):
        b, b2 = s * 4, ((s + 1) % sides) * 4
        faces += [(b + 1, b2 + 1, b2 + 3, b + 3),
                  (b + 0, b + 2, b2 + 2, b2 + 0),
                  (b + 2, b + 3, b2 + 3, b2 + 2),
                  (b + 0, b2 + 0, b2 + 1, b + 1)]
    return mesh_obj(name, verts, faces, mat)


def facet_dir(ang, tilt=0.0):
    a = math.radians(ang)
    return Vector((math.cos(a) * math.cos(tilt),
                   math.sin(a) * math.cos(tilt), math.sin(tilt)))


def facet_tan(ang):
    a = math.radians(ang)
    return Vector((-math.sin(a), math.cos(a), 0.0))


def facet_box(name, size, mat, ang, ap, z, tilt=0.0):
    """面心处的盒子：size = (切向宽, 法向厚, 高)，ap = 盒子中心到原点的法向距离。"""
    a = math.radians(ang)
    return box(name, (ap * math.cos(a), ap * math.sin(a), z), size, mat,
               rot=(tilt, 0, a - math.pi / 2))


def facet_plate(name, prof, thick, mat, ang, ap, z, tilt=0.0, out=0.0):
    """在某个面心处贴一块多边形板。prof 的 u→切向、v→竖直（倾角前）。"""
    ob = extrude(name, prof, "Y", thick, (0.0, 0.0), mat)
    d = facet_dir(ang, tilt)
    base = Vector((ap * math.cos(math.radians(ang)),
                   ap * math.sin(math.radians(ang)), z))
    ob.rotation_euler = (tilt, 0, math.radians(ang) - math.pi / 2)
    ob.location = base + d * out
    return ob


def arch_poly(w, straight, segs=7):
    """半圆拱轮廓：左下 → 右下 → 右直边 → 拱 → 左上。无重复底点（会三角化出黑楔）。"""
    hw = w * 0.5
    pts = [(-hw, 0.0), (hw, 0.0), (hw, straight)]
    for s in range(1, segs):
        a = math.pi * s / segs
        pts.append((hw * math.cos(a), straight + hw * math.sin(a)))
    pts.append((-hw, straight))
    return pts


def panel_with_arch(name, hw, top, hole_hw, spring, mat, y, thick, segs=7):
    """一块矩形墙板，底边挖一个「矩形 + 半圆拱」的洞（门洞要真开，不能贴片）。"""
    pts = [(-hw, spring), (-hole_hw, spring)]
    for s in range(1, segs):
        a = math.pi - math.pi * s / segs
        pts.append((hole_hw * math.cos(a), spring + hole_hw * math.sin(a)))
    pts += [(hole_hw, spring), (hw, spring), (hw, top), (-hw, top)]
    return extrude(name, pts, "Y", thick, (0.0, 0.0), mat, offset=y)


def shard(name, loc, r, h, mat, mat_tip=None, sides=6, tip=0.30, rot=(0.0, 0.0, 0.0)):
    """六棱水晶：柱身 + 棱锥尖。mat_tip 给定时另出一件亮尖。"""
    zt = h * (1.0 - tip)
    verts, faces = [], []
    for z in (0.0, zt):
        for s in range(sides):
            a = TAU * s / sides + math.pi / sides
            verts.append((r * math.cos(a), r * math.sin(a), z))
    for s in range(sides):
        i, j = s, (s + 1) % sides
        faces.append((i, j, sides + j, sides + i))
    faces.append(tuple(range(sides - 1, -1, -1)))
    ob = mesh_obj(name, verts, faces, mat)
    ob.rotation_euler = rot
    ob.location = loc
    out = [ob]
    if mat_tip is not None:
        verts2 = []
        for s in range(sides):
            a = TAU * s / sides + math.pi / sides
            verts2.append((r * 1.004 * math.cos(a), r * 1.004 * math.sin(a), zt - 0.004))
        verts2.append((0.0, 0.0, h))
        faces2 = [(s, (s + 1) % sides, sides) for s in range(sides)]
        faces2.append(tuple(range(sides - 1, -1, -1)))
        ob2 = mesh_obj(name + "_tip", verts2, faces2, mat_tip)
        ob2.rotation_euler = rot
        ob2.location = loc
        out.append(ob2)
    return out


class Model(BR.Model):

    # ── 1. 场地：夯土 + 断环符文 + 残破铺石 ─────────────────────────────────
    def yard(self):
        M = self.M
        cx = (YARD_X0 + YARD_X1) * 0.5
        cy = (YARD_Y0 + YARD_Y1) * 0.5
        self.add(box("yard_soil", (cx, cy, G_Z * 0.5),
                     (YARD_X1 - YARD_X0, YARD_Y1 - YARD_Y0, G_Z), M["earth"]), 0.024)
        # 台基下一圈踩实的深色土：把台基从地面上"托"起来
        self.add(ng_prism("yard_core", 5.86, G_Z - 0.04, G_Z + 0.02, M["earth_dark"], 12), 0.010)
        # 残破的铺石圈：9 块，避开台阶正前方与左后（地面沉了）
        for k, ang in enumerate((18, 48, 108, 140, 172, 232, 262, 296, 330)):
            a = math.radians(ang)
            w = 1.02 if k % 3 else 0.76
            self.add(box("yard_slab", (5.62 * math.cos(a), 5.62 * math.sin(a), G_Z + 0.035),
                         (0.86, w, 0.09), M["paving"], rot=(0, 0, a - math.pi / 2)), 0.006)
        # 场地牙子：三面（正面留口，读作"没有修完的圣域边界"）
        for (px, py, sx, sy) in ((YARD_X1 - 0.10, cy - 0.40, 0.20, YARD_Y1 - YARD_Y0 - 1.00),
                                 (YARD_X0 + 0.10, cy - 0.40, 0.20, YARD_Y1 - YARD_Y0 - 1.00),
                                 (cx, YARD_Y0 + 0.10, YARD_X1 - YARD_X0 - 0.40, 0.20)):
            self.add(box("yard_curb", (px, py, G_Z + 0.04), (sx, sy, 0.14), M["paving"]), 0.005)
        # 三根倒下的柱鼓（八边形，半埋）
        for (px, py, ry, ln) in ((3.30, -5.62, 0.10, 0.96), (-2.16, -5.80, -0.26, 0.82),
                                 (5.72, 6.30, 0.62, 0.74), (-5.60, 5.92, 0.34, 0.88),
                                 (5.62, -2.10, -0.18, 0.70)):
            ob = revolve("yard_drum", [(0.30, 0.0), (0.30, ln)], 8, (0.0, 0.0, 0.0),
                         M["stone_mid"])
            ob.rotation_euler = (math.pi * 0.5, 0.0, ry)
            ob.location = (px, py, G_Z + 0.26)
            self.add(ob, 0.008)
        # 草簇 / 碎石
        for (px, py) in ((-6.02, 5.86), (6.22, 1.96), (-5.72, -2.46), (2.52, 6.92),
                         (-3.36, 6.86), (5.24, -5.06), (1.36, -6.20)):
            self.tuft(px, py)
        for (px, py, s, rz) in ((6.16, -1.70, 0.26, 0.4), (-5.54, 1.46, 0.21, -0.7),
                                (1.52, -6.22, 0.19, 1.0), (-1.94, 7.16, 0.17, 0.2)):
            self.add(box("rubble", (px, py, G_Z + s * 0.26), (s, s * 0.76, s * 0.54),
                         M["stone_mid"], rot=(0.2 * s, 0.16 * s, rz)), 0.004)

    def tuft(self, x, y, h=0.24):
        M = self.M
        for k in range(3):
            a = math.radians(18 + k * 60)
            hh = h * (0.84 + 0.11 * k)
            self.add(box("tuft", (x + 0.014 * math.cos(a + 1.1),
                                  y + 0.014 * math.sin(a + 1.1), G_Z + hh * 0.48),
                         (0.115, 0.018, hh), M["moss"],
                         rot=(0.20 * math.cos(a), 0.20 * math.sin(a), a)), 0.0)

    # ── 2. 三级台基 ─────────────────────────────────────────────────────────
    def dais(self):
        M = self.M
        for (a, cp, z0, z1, cz0, cz1) in ((A1, C1, Z1A, Z1B, CP1[0], CP1[1]),
                                          (A2, C2, Z2A, Z2B, CP2[0], CP2[1]),
                                          (A3, C3, Z3A, Z3B, CP3[0], CP3[1])):
            self.add(ng_prism("dais_shaft", a, z0, z1, M["stone_mid"], 12), 0.012)
            self.add(ng_prism("dais_cap", cp, cz0, cz1, M["stone_light"], 12), 0.010)
        # 二级台身的队色箍：一级是最外那一圈（俯视时最先看到），但把蓝环放在最底下
        # 会读成"蓝色裙边"；放在二级的立面，正好压在亮压顶下面一档
        self.add(ng_prism("dais_band", A2 + 0.03, 0.51, 0.71, M["team"], 12), 0.004)
        # 一级压顶顶面的一圈队色块：**俯视时唯一大面积的横向染色**。
        # 立面染色在 58° 俯角下会被压扁，只有压在水平面上才数得出来
        for k in range(12):
            a0 = TAU * k / 12
            self.add(box("dais_mark", (5.12 * math.cos(a0), 5.12 * math.sin(a0), 0.523),
                         (0.40, 1.28, 0.046), M["team"], rot=(0, 0, a0)), 0.0)
        # 二级压顶上再来一圈（与符文圈错开 0.26 m）：俯视是"双环"，正立面只露一条边
        for k in range(12):
            a0 = TAU * k / 12 + TAU / 24
            self.add(box("dais_mark2", (4.74 * math.cos(a0), 4.74 * math.sin(a0), 0.803),
                         (0.28, 1.06, 0.046), M["team"], rot=(0, 0, a0)), 0.0)
        # 三级台身的 12 枚符文灯（每面中心一枚）
        for ang in FACE_A:
            self.add(facet_box("dais_rune", (0.15, 0.06, 0.17), M["crystal"],
                               ang, A3 + 0.02, 0.89), 0.0)
        # 二级压顶面上的一圈符文：12 个位放 11 段（正面缺 2 段，让山门压着）
        # 俯视时是台基上的第一圈亮线 —— 地面太远看不清，压顶面才是它该在的地方
        for k in range(12):
            if k in (2, 3, 4):
                continue
            a0 = TAU * k / 12
            for j in range(2):
                aa = a0 + (TAU / 12) * 0.22 * (j - 0.5)
                self.add(box("dais_glyph", (4.44 * math.cos(aa), 4.44 * math.sin(aa),
                                          0.815 + 0.008 * j),
                             (0.15, 0.46, 0.056), M["crystal"], rot=(0, 0, aa)), 0.0)
            if k % 3 == 0:
                self.add(box("dais_glyph_head", (4.44 * math.cos(a0), 4.44 * math.sin(a0), 0.830),
                             (0.22, 0.22, 0.086), M["crystal_pale"],
                             rot=(0, 0, a0 + math.pi / 4)), 0.0)

    # ── 3. 门廊：实心山门（从地面砌起）+ 台阶 ──────────────────────────────
    def portico(self):
        M = self.M
        yc = (BAY_Y0 + BAY_Y1) * 0.5
        th = BAY_Y1 - BAY_Y0
        # 两侧墙块 + 门槛块 + 拱上的墙板：四块拼成一个"隧道"，洞是真开的
        for sx in (-1, 1):
            self.add(box("bay_side", (sx * (BAY_X + BAY_HW) * 0.5, yc,
                                      (BAY_Z1 + 0.02) * 0.5),
                         (BAY_X - BAY_HW, th, BAY_Z1 + 0.02), M["stone_mid"]), 0.018)
        self.add(box("bay_sill", (0.0, yc, (0.20 + DECK + 0.02) * 0.5),
                     (BAY_HW * 2, th, DECK + 0.02 - 0.20), M["stone_mid"]), 0.016)
        self.add(panel_with_arch("bay_top", BAY_X, BAY_Z1, BAY_HW, BAY_SPRING,
                                 M["stone_mid"], yc, th), 0.018)
        # 正面两根壁柱（方形，与里面十二边形的圆壁柱区分）+ 金柱头
        for sx in (-1, 1):
            self.add(box("bay_pil", (sx * PIL_X, BAY_Y1 + 0.07, 2.66),
                         (0.34, 0.20, 3.02), M["stone_light"]), 0.010)
            self.add(box("bay_pil_base", (sx * PIL_X, BAY_Y1 + 0.07, 1.30),
                         (0.44, 0.26, 0.36), M["stone_light"]), 0.008)
            self.add(box("bay_pil_cap", (sx * PIL_X, BAY_Y1 + 0.07, 4.10),
                         (0.46, 0.28, 0.30), M["gold"]), 0.008)
        # 队色檐壁：拱顶之上、挑檐之下的一条通长横带（正面最显眼的一块染色）
        self.add(box("bay_frieze", (0.0, BAY_Y1 + 0.05, 4.20), (3.80, 0.12, 0.30),
                     M["team"]), 0.004)
        self.add(box("bay_frieze_f", (0.0, BAY_Y1 + 0.075, 4.36), (3.88, 0.09, 0.05),
                     M["gold"]), 0.002)
        self.add(box("bay_frieze_l", (0.0, BAY_Y1 + 0.075, 4.04), (3.88, 0.09, 0.05),
                     M["gold"]), 0.002)
        # 挑檐
        self.add(box("bay_corn", (0.0, yc + 0.02, (CORN_Z0 + CORN_Z1) * 0.5),
                     (BAY_X * 2 + 0.28, th + 0.16, CORN_Z1 - CORN_Z0),
                     M["stone_light"]), 0.010)
        # 拱洞：石券 + 拱心石 + 一枚晶尖
        self.add(arch_band("bay_arch", 0.0, BAY_SPRING, BAY_HW, BAY_HW + 0.20,
                           BAY_Y1 - 0.06, BAY_Y1 + 0.16, M["stone_light"], segs=7), 0.008)
        for sx in (-1, 1):
            self.add(box("bay_impost", (sx * (BAY_HW + 0.10), BAY_Y1 + 0.05, BAY_SPRING),
                         (0.34, 0.30, 0.16), M["stone_light"]), 0.006)
        self.add(box("bay_key", (0.0, BAY_Y1 + 0.07, BAY_APEX + 0.02),
                     (0.30, 0.32, 0.42), M["stone_light"]), 0.008)
        for ob in shard("bay_key_shard", (0.0, BAY_Y1 + 0.09, BAY_APEX + 0.20),
                        0.11, 0.50, M["crystal"], M["crystal_pale"], sides=6, tip=0.46):
            self.add(ob, 0.002)
        # 台阶：4 级（第 5 级是门槛），逐级加宽 = 神庙的"外撒"
        for i in range(STEP_N):
            top = DECK - STEP_R * (i + 1)
            y1 = BAY_Y1 + STEP_T * (STEP_N - i)
            self.add(box("step", (0.0, (BAY_Y1 + y1) * 0.5, (G_Z + top) * 0.5),
                         (4.10 + i * 0.22, y1 - BAY_Y1, top - G_Z),
                         M["stone_light"]), 0.010)
            self.add(box("step_edge", (0.0, y1 - 0.025, top - 0.014),
                         (4.14 + i * 0.22, 0.05, 0.036), M["stone_mid"]), 0.003)

    # ── 4. 圣所墙体：12 面墙板 + 壁柱 + 檐口 ────────────────────────────────
    def cella(self):
        M = self.M
        # 12 面墙板。**每一面都要真的长出来** —— v1 只做了装饰没做墙，
        # 侧视时能一眼看穿整座建筑。正面那一块拆成左/右/拱上三块（在 portal() 里）。
        for k, ang in enumerate(FACE_A):
            if ang == 90:
                continue
            top = CZ1 + 0.006 * k       # 每面错开 6 mm：顶面藏进檐口，但不再两两共面
            self.add(facet_box("cella_wall", (FACE_W + 0.06, WALL_T, top - CZ0),
                               M["stone_mid"], ang, CA - WALL_T * 0.5,
                               (CZ0 + top) * 0.5), 0.016)
            if ang in (0, 180, 270):
                self.niche(ang)
            else:
                self.blind_panel(ang)
        # 墙根一道暗色收口（十二边形环，凸 4 cm）：墙与天台之间要有一条"缝"
        self.add(ng_prism("cella_shadow", CA + 0.04, CZ0 - 0.02, CZ0 + 0.10,
                          M["stone_dark"], 12), 0.003)
        # 壁柱（棱线上）：柱础 / 柱身 / 金柱头。
        # 正面两个转角（75° / 105°）不放：那里离门套只有 1 cm，正视图会糊成一团，
        # 而且门廊的山门体块正好站在外面。
        for ang in VERT_A:
            if ang in (75, 105):
                continue
            a = math.radians(ang)
            rv = circ(CA, 12)
            px, py = rv * math.cos(a) * 0.958, rv * math.sin(a) * 0.958
            rz = a - math.pi / 2
            self.add(box("pil_shaft", (px, py, (CZ0 + 5.88) * 0.5),
                         (0.32, 0.64, 5.88 - CZ0), M["stone_light"], rot=(0, 0, rz)), 0.012)
            self.add(box("pil_base", (px * 1.004, py * 1.004, CZ0 + 0.22),
                         (0.42, 0.74, 0.34), M["stone_light"], rot=(0, 0, rz)), 0.012)
            self.add(box("pil_cap", (px * 1.004, py * 1.004, 5.965),
                         (0.46, 0.78, 0.25), M["gold"], rot=(0, 0, rz)), 0.010)
        # 檐口三叠
        self.add(ng_prism("cornice_a", 3.74, CZ1 - 0.02, 6.20, M["stone_light"], 12), 0.010)
        self.add(ng_prism("cornice_b", 3.86, 6.18, 6.32, M["stone_mid"], 12), 0.010)
        self.add(ng_prism("cornice_c", 3.98, 6.30, CZ_TOP, M["stone_light"], 12), 0.010)
        self.add(ng_ring("cornice_shadow", CA - 0.06, CA + 0.03, CZ1 - 0.09, CZ1 - 0.055,
                         M["stone_dark"], 12), 0.002)

    def blind_panel(self, ang):
        """八个次面：暗色盲拱 + 亮石框 + 金钉。凹龛用"框比板凸、板比墙暗"读深度。"""
        M = self.M
        d, t = facet_dir(ang), facet_tan(ang)
        c0 = Vector((CA * d.x, CA * d.y, 0.0))
        rz = math.radians(ang) - math.pi / 2
        self.add(facet_box("cella_panel", (1.16, 0.06, 2.66), M["stone_dark"],
                           ang, CA + 0.015, 3.42), 0.004)
        for sgn in (-1, 1):
            c = c0 + t * (sgn * 0.66) + d * 0.09 + Vector((0, 0, 3.42))
            self.add(box("cella_jamb", tuple(c), (0.15, 0.20, 3.12), M["stone_light"],
                         rot=(0, 0, rz)), 0.006)
        c = c0 + d * 0.09 + Vector((0, 0, 4.60))
        self.add(box("cella_lintel", tuple(c), (1.48, 0.20, 0.18), M["stone_light"],
                     rot=(0, 0, rz)), 0.006)
        c = c0 + d * 0.045 + Vector((0, 0, 4.34))
        self.add(box("cella_stud", tuple(c), (0.16, 0.06, 0.16), M["gold"],
                     rot=(0, 0, rz + math.pi / 4)), 0.003)
        # 还愿幡：上段整幅 + 下段收窄 + 燕尾 + 金杆金边（工单里的 A 型燕尾垂旗）
        self.add(box("cella_rod", tuple(c0 + d * 0.085 + Vector((0, 0, 4.00))),
                     (0.72, 0.08, 0.08), M["gold"], rot=(0, 0, rz)), 0.003)
        for sgn in (-1, 1):
            self.add(box("cella_rod_cap",
                         tuple(c0 + t * (sgn * 0.375) + d * 0.085 + Vector((0, 0, 4.00))),
                         (0.10, 0.11, 0.11), M["gold"], rot=(0, 0, rz)), 0.002)
        zz = 3.94
        for (kw, hh) in ((1.00, 0.86), (0.84, 0.56)):
            self.add(box("cella_votive", tuple(c0 + d * 0.055 + Vector((0, 0, zz - hh * 0.5))),
                         (0.55 * kw, 0.05, hh), M["team"], rot=(0, 0, rz)), 0.002)
            zz -= hh
        for sgn in (-1, 1):
            self.add(box("cella_votive_tail",
                         tuple(c0 + t * (sgn * 0.125) + d * 0.055 + Vector((0, 0, zz - 0.17))),
                         (0.17, 0.05, 0.34), M["team"], rot=(0, 0, rz)), 0.002)

    def niche(self, ang):
        """三个正面的拱形龛：拱框 + 暗龛 + 一枚立着的水晶 + 龛顶的冷光条。"""
        M = self.M
        d, t = facet_dir(ang), facet_tan(ang)
        c0 = Vector((CA * d.x, CA * d.y, 0.0))
        rz = math.radians(ang) - math.pi / 2
        self.add(facet_box("cella_panel", (1.16, 0.06, 2.92), M["stone_dark"],
                           ang, CA + 0.015, 3.28), 0.004)
        self.add(facet_box("niche_glow", (0.38, 0.04, 0.16), M["crystal_pale"],
                           ang, CA + 0.05, 4.54), 0.0)
        for sgn in (-1, 1):
            c = c0 + t * (sgn * 0.64) + d * 0.09 + Vector((0, 0, 3.10))
            self.add(box("niche_jamb", tuple(c), (0.15, 0.20, 2.42), M["stone_light"],
                         rot=(0, 0, rz)), 0.006)
        c = c0 + d * 0.09 + Vector((0, 0, 1.94))
        self.add(box("niche_sill", tuple(c), (1.44, 0.24, 0.18), M["stone_light"],
                     rot=(0, 0, rz)), 0.006)
        ob = arch_band("niche_arch", 0.0, 0.0, 0.64, 0.79, -0.10, 0.10,
                       M["stone_light"], segs=6)
        ob.rotation_euler = (0, 0, rz)
        ob.location = tuple(c0 + d * 0.09 + Vector((0, 0, 4.26)))
        self.add(ob, 0.008)
        base = c0 + d * 0.01 + Vector((0, 0, 2.04))
        for ob2 in shard("niche_shard", tuple(base), 0.13, 1.28, M["crystal"],
                         M["crystal_pale"], sides=6, tip=0.34,
                         rot=(d.y * 0.04, -d.x * 0.04, 0.0)):
            self.add(ob2, 0.004)

    # ── 5. 正面：门洞（真开）· 发光门 · 铁栅 ────────────────────────────────
    def portal(self):
        M = self.M
        yc = CA - WALL_T * 0.5               # 墙板中心 y = 3.51
        hw = FACE_W * 0.5 + 0.03             # 0.981
        for (tag, sx, dz) in (("l", -1, 0.080), ("r", 1, 0.086)):
            self.add(box("cella_wall_" + tag, (sx * (DOOR_HW + hw) * 0.5, yc,
                                               (CZ0 + CZ1 + dz) * 0.5),
                         (hw - DOOR_HW, WALL_T, CZ1 + dz - CZ0), M["stone_mid"]), 0.014)
        self.add(panel_with_arch("cella_wall_t", hw, CZ1 + 0.092, DOOR_HW, DOOR_SPRING,
                                 M["stone_mid"], yc, WALL_T), 0.014)
        # 发光门：一整块水晶板嵌在洞里 —— 不是"屋里点灯"，是"门本身在发光"。
        # 门板退到外墙面之内 0.24，前面还有 1.4 m 的山门隧道 —— 越看不全越神秘。
        self.add(extrude("portal_glass", arch_poly(DOOR_HW * 2, DOOR_SPRING - CZ0 - 0.10, 7),
                         "Y", 0.12, (0.0, CZ0 + 0.10), M["crystal"], offset=CA - 0.24), 0.0)
        # 铁栅：3 竖 2 横，压在门板前面
        for xx in (-0.36, 0.0, 0.36):
            hh = DOOR_APEX - 1.10 - abs(xx) * 0.62
            self.add(box("portal_bar", (xx, CA - 0.15, 1.10 + hh * 0.5),
                         (0.06, 0.06, hh), M["iron"]), 0.002)
        for zz in (2.24, 3.02):
            self.add(box("portal_bar", (0.0, CA - 0.15, zz), (1.34, 0.06, 0.06),
                         M["iron"]), 0.002)
        # 内层石券（隧道尽头的一道细边）：让洞里有"第二层门框"
        self.add(arch_band("portal_arch", 0.0, DOOR_SPRING, DOOR_HW, DOOR_HW + 0.14,
                           CA - 0.04, CA + 0.05, M["stone_light"], segs=7), 0.006)

    # ── 6. 山花（门廊顶上）──────────────────────────────────────────────────
    def pediment(self):
        M = self.M
        yp = (BAY_Y0 + BAY_Y1) * 0.5 + 0.02
        for sx in (-1, 1):
            self.add(beam("ped_rake", (sx * PED_HW, yp, CORN_Z1 + 0.02),
                          (0.0, yp, PED_Z - 0.10), 0.78, 0.26, M["stone_light"]), 0.010)
        # 鼓室比斜檐低一档（中灰）：三角才读得出来 —— 全亮的话整块是一坨
        self.add(box("ped_tube", (0.0, yp - 0.04, (CORN_Z1 + PED_Z) * 0.5),
                     (PED_HW * 2 - 0.34, 0.66, PED_Z - CORN_Z1 - 0.20), M["stone_mid"]), 0.012)
        self.add(box("ped_sill", (0.0, yp, CORN_Z1 + 0.04), (PED_HW * 2, 0.80, 0.12),
                     M["stone_light"]), 0.006)
        self.add(box("ped_apex", (0.0, yp, PED_Z - 0.02), (0.28, 0.76, 0.26),
                     M["gold"]), 0.004)
        self.crest("ped_crest", "Y", 0.0, yp + 0.33, PED_Z - 0.76, 0.98)

    # ── 7. 天台 8 盏晶体灯 + 鼓座 + 穹顶 ────────────────────────────────────
    def upper(self):
        M = self.M
        # 天台：8 盏晶体灯（一周冷光点，俯视是穹顶外的一圈"烛台"）
        for k in range(8):
            a = math.radians(45 * k + 22.5)
            px, py = 3.36 * math.cos(a), 3.36 * math.sin(a)
            self.add(box("lamp_base", (px, py, CZ_TOP + 0.05), (0.28, 0.28, 0.10),
                         M["stone_light"], rot=(0, 0, a)), 0.004)
            for ob in shard("lamp_shard", (px, py, CZ_TOP + 0.09), 0.085, 0.44,
                            M["crystal"], M["crystal_pale"], sides=6, tip=0.42):
                self.add(ob, 0.0)
        # 鼓座（中灰）：12 根亮柱 + 6 扇发光窗 + 队色箍
        self.add(ng_prism("drum", DR_AP, DR_Z0, DR_Z1, M["stone_mid"], 12), 0.014)
        for ang in VERT_A:
            a = math.radians(ang)
            rv = circ(DR_AP, 12)
            self.add(box("drum_col", (rv * math.cos(a) * 0.985, rv * math.sin(a) * 0.985,
                                      (DR_Z0 + DR_Z1) * 0.5),
                         (0.22, 0.22, DR_Z1 - DR_Z0), M["stone_light"],
                         rot=(0, 0, a - math.pi / 2)), 0.006)
        for ang in (30, 90, 150, 210, 270, 330):
            self.drum_win(ang)
        self.add(ng_prism("drum_band", DR_AP + 0.05, 8.22, 8.50, M["team"], 12), 0.004)
        self.add(ng_prism("drum_corn_a", DR_AP + 0.10, DR_CORN[0] - 0.02, 8.84,
                          M["stone_light"], 12), 0.008)
        self.add(ng_prism("drum_corn_b", DR_AP + 0.22, 8.82, DR_CORN[1] + 0.02,
                          M["stone_light"], 12), 0.010)
        # 穹顶：十二边形回转体，七段环。**整组平着色**（12 边夹角 30° < shade_auto 的 32°，
        # 走平滑会被磨成一个深色圆盘 —— 农场筒仓踩过同一个坑）
        prof = [(circ(a, 12), z) for (a, z) in DOME]
        self.add(revolve("dome_shell", prof, 12, (0.0, 0.0, 0.0), M["roof_edge"],
                         phase=math.pi / 12), 0.012)
        for k, ang in enumerate(VERT_A):
            self.dome_rib(ang, k)
        # 穹顶脚下的一圈滴水：把深穹顶与亮鼓座"切"开
        self.add(ng_ring("dome_drip", circ(DOME[0][0], 12) - 0.04,
                         circ(DOME[0][0], 12) + 0.12, DOME[0][1] - 0.06, DOME[0][1] + 0.09,
                         M["stone_light"], 12), 0.006)
        for ang in (0, 60, 120, 180, 240, 300):
            self.dome_boss(ang)

    def drum_win(self, ang):
        M = self.M
        a = math.radians(ang)
        d = Vector((math.cos(a), math.sin(a), 0.0))
        t = Vector((-d.y, d.x, 0.0))
        rz = a - math.pi / 2
        base = Vector((DR_AP * d.x, DR_AP * d.y, 0.0))
        z0, zs = 6.92, 0.72          # 玻璃底 / 直边高（拱顶 = z0 + zs + 0.22 = 7.86）
        self.add(box("drumwin_back", tuple(base + d * 0.012 + Vector((0, 0, z0 + 0.50))),
                     (0.66, 0.06, 1.14), M["stone_dark"], rot=(0, 0, rz)), 0.004)
        self.add(facet_plate("drumwin_glass", arch_poly(0.44, zs, 6), 0.07,
                             M["crystal_pale"], ang, DR_AP + 0.055, z0), 0.0)
        for sgn in (-1, 1):
            self.add(box("drumwin_jamb", tuple(base + t * (sgn * 0.31) + d * 0.085
                                              + Vector((0, 0, z0 + zs * 0.5))),
                         (0.12, 0.14, zs), M["stone_light"], rot=(0, 0, rz)), 0.005)
        self.add(box("drumwin_sill", tuple(base + d * 0.085 + Vector((0, 0, z0 - 0.07))),
                     (0.78, 0.19, 0.14), M["stone_light"], rot=(0, 0, rz)), 0.005)
        for (dx, dz, sz) in ((0.0, 0.36, (0.05, 0.06, 0.72)),
                             (-0.11, 0.36, (0.05, 0.06, 0.72)),
                             (0.11, 0.36, (0.05, 0.06, 0.72)),
                             (0.0, 0.20, (0.44, 0.06, 0.05)),
                             (0.0, 0.62, (0.40, 0.06, 0.05))):
            self.add(box("drumwin_bar", tuple(base + t * dx + d * 0.10
                                             + Vector((0, 0, z0 + dz))),
                         sz, M["stone_dark"], rot=(0, 0, rz)), 0.002)
        ob = arch_band("drumwin_arch", 0.0, 0.0, 0.22, 0.34, -0.07, 0.07,
                       M["stone_light"], segs=6)
        ob.rotation_euler = (0, 0, rz)
        ob.location = tuple(base + d * 0.085 + Vector((0, 0, z0 + zs)))
        self.add(ob, 0.005)

    def dome_rib(self, ang, k=0):
        """沿子午线的一根亮脊：外表面 +0.055、内表面埋进穹顶 0.07，端头封口。

        收在倒数第二环（再往上会与穹顶尖的端面同高，12 根端头两两共面），
        并且每根端头沿母线方向错开 8 mm —— 藏在采光亭里，看不见。
        """
        M = self.M
        a = math.radians(ang)
        d = Vector((math.cos(a), math.sin(a), 0.0))
        t = Vector((-d.y, d.x, 0.0))
        w = 0.11
        verts, faces = [], []
        for i, (ap_, z) in enumerate(DOME):
            if i == len(DOME) - 1:
                break
            if i == len(DOME) - 2:
                ap_ -= 0.004 * k
                z -= 0.008 * k
            r = circ(ap_, 12)
            for (off, sgn) in ((0.055, -1), (0.055, 1), (-0.07, -1), (-0.07, 1)):
                verts.append(tuple(d * (r + off) + t * (sgn * w * 0.5) + Vector((0, 0, z))))
        n = len(DOME) - 1
        for i in range(n - 1):
            b, b2 = i * 4, (i + 1) * 4
            faces += [(b + 0, b2 + 0, b2 + 1, b + 1),
                      (b + 2, b + 3, b2 + 3, b2 + 2),
                      (b + 0, b2 + 0, b2 + 2, b + 2),
                      (b + 1, b + 3, b2 + 3, b2 + 1)]
        faces += [(0, 1, 3, 2), ((n - 1) * 4 + 2, (n - 1) * 4 + 3,
                                 (n - 1) * 4 + 1, (n - 1) * 4 + 0)]
        self.add(mesh_obj("dome_rib", verts, faces, M["roof_pale"]), 0.006)

    def dome_boss(self, ang):
        """队色徽牌：金边 + 队色菱形 + 中央一小枚晶体。贴在第四段环上（倾角 25.5°）。"""
        M = self.M
        ap_c, z_c = 2.37, 10.87
        tilt = math.atan2(0.42, 0.62)
        lozenge = [(0.0, 0.36), (0.34, 0.0), (0.0, -0.36), (-0.34, 0.0)]
        rim = [(0.0, 0.41), (0.39, 0.0), (0.0, -0.41), (-0.39, 0.0)]
        self.add(facet_plate("dome_boss_rim", rim, 0.10, M["gold"], ang, ap_c, z_c,
                             tilt=tilt, out=-0.02), 0.006)
        self.add(facet_plate("dome_boss_field", lozenge, 0.09, M["team"], ang, ap_c, z_c,
                             tilt=tilt, out=0.032), 0.004)
        self.add(facet_plate("dome_boss_gem", [(0.0, 0.12), (0.10, 0.0), (0.0, -0.12),
                                               (-0.10, 0.0)], 0.06, M["crystal_pale"],
                             ang, ap_c, z_c, tilt=tilt, out=0.072), 0.0)

    # ── 8. 采光亭 · 锥顶 · 晶尖 ─────────────────────────────────────────────
    def crown(self):
        M = self.M
        self.add(ng_prism("lan_base", LAN_AP, LAN_Z0, LAN_Z0 + 0.26, M["stone_light"], 8), 0.008)
        self.add(ng_prism("lan_base2", LAN_AP + 0.12, LAN_Z0 - 0.08, LAN_Z0 + 0.04,
                          M["stone_mid"], 8), 0.006)
        # 发光核：8 根柱子之间的冷光（从任何方向都能看见"里面有东西"）
        self.add(ng_prism("lan_core", 0.44, LAN_Z0 + 0.14, LAN_Z1 - 0.18, M["crystal_pale"], 8), 0.0)
        rv = circ(LAN_AP, 8)
        for k in range(8):
            a = math.pi / 8 + TAU * k / 8
            self.add(box("lan_col", (rv * 0.93 * math.cos(a), rv * 0.93 * math.sin(a),
                                     (LAN_Z0 + LAN_Z1) * 0.5 + 0.06),
                         (0.16, 0.16, LAN_Z1 - LAN_Z0 - 0.36), M["stone_light"],
                         rot=(0, 0, a - math.pi / 2)), 0.004)
        self.add(ng_ring("lan_rail", 0.66, 0.84, 13.06, 13.20, M["stone_light"], 8), 0.005)
        self.add(ng_prism("lan_top", LAN_AP + 0.12, LAN_Z1 - 0.20, LAN_Z1, M["stone_light"], 8), 0.008)
        # 锥顶（三折）+ 金箍 + 针
        cone = [(LAN_AP + 0.12, LAN_Z1 - 0.02), (0.66, 14.30), (0.38, 14.60), (0.12, 14.86)]
        self.add(revolve("spire_cone", [(circ(a, 8), z) for (a, z) in cone], 8,
                         (0.0, 0.0, 0.0), M["roof_edge"], phase=math.pi / 8), 0.008)
        self.add(ng_ring("spire_collar", 0.09, 0.20, 14.80, 14.94, M["gold"], 8), 0.004)
        self.add(revolve("spire_needle", [(circ(0.12, 8), 14.90), (0.070, 15.02),
                                          (0.028, SPIRE_TOP)], 8, (0.0, 0.0, 0.0),
                         M["gold"], phase=math.pi / 8), 0.003)
        self.add(ng_ring("finial_ring", 0.09, 0.23, SPIRE_TOP - 0.10, SPIRE_TOP + 0.03,
                         M["gold"], 8), 0.003)
        for ob in shard("finial", (0.0, 0.0, SPIRE_TOP - 0.02), 0.19,
                        FINIAL_TOP - SPIRE_TOP + 0.02, M["crystal"], M["crystal_pale"],
                        sides=6, tip=0.46):
            self.add(ob, 0.0)

    # ── 9. 水晶：场地四簇（三立一断）+ 穹顶四簇 ─────────────────────────────
    def crystals(self):
        M = self.M
        # 场地四簇。位置刻意不对称：三立一断，断的那一簇倒在台阶左前方。
        spots = ((-5.12, -4.16, 0.46, 4.18, 0.07, 200),
                 (5.24, -3.86, 0.42, 3.56, 0.05, 26),
                 (5.42, 3.66, 0.36, 3.06, 0.07, 148),
                 (-5.02, 4.06, 0.44, 1.42, 0.05, 318))
        for (px, py, r, h, tilt, az) in spots:
            self.crystal_cluster(px, py, r, h, tilt, az, broken=(h < 2.0))
        # 穹顶基部的四簇小晶（长在滴水圈上，向外上方斜出）
        for ang in (30, 150, 210, 330):
            a = math.radians(ang)
            base = Vector((2.78 * math.cos(a), 2.78 * math.sin(a), 9.04))
            for (k, (rr, hh, tl, da)) in enumerate(((0.16, 1.08, 0.46, -9),
                                                    (0.12, 0.76, 0.56, 12),
                                                    (0.09, 0.52, 0.66, 26))):
                aa = a + math.radians(da)
                d = Vector((math.cos(aa), math.sin(aa), 0.0))
                loc = tuple(base + d * (0.10 + k * 0.06))
                rot = (math.sin(aa) * -tl * 0.55, math.cos(aa) * tl * 0.55, 0.0)
                for ob in shard("domecrys", loc, rr, hh, M["crystal"],
                                M["crystal_pale"], sides=6, tip=0.26, rot=rot):
                    self.add(ob, 0.002)

    def crystal_cluster(self, px, py, r, h, tilt, az, broken=False):
        """一簇巨晶：碎石堆 + 主晶 + 2 根卫星晶（断裂的那簇另加一块倒下的晶块）。"""
        M = self.M
        a = math.radians(az)
        # 碎石堆：三级递减，把水晶"种"进地里（否则像插在地上的贴图）
        self.add(box("crys_mound", (px, py, G_Z + 0.07), (1.56, 1.42, 0.28),
                     M["stone_mid"], rot=(0, 0, a)), 0.010)
        self.add(box("crys_mound2", (px, py, G_Z + 0.20), (1.12, 1.02, 0.12),
                     M["stone_light"], rot=(0, 0, a + 0.2)), 0.008)
        self.add(box("crys_soil", (px, py, G_Z + 0.285), (0.72, 0.64, 0.07),
                     M["earth_dark"], rot=(0, 0, a + 0.4)), 0.004)
        base = Vector((px, py, G_Z + 0.31))
        rot = (math.sin(a) * tilt, math.cos(a) * tilt, 0.0)
        if broken:
            for ob in shard("crys_main", tuple(base), r, h, M["crystal"], None,
                            sides=6, tip=0.02, rot=rot):
                self.add(ob, 0.008)
            # 断口：斜切面上压一块更亮的残晶，读作"崩掉的那一截"
            self.add(box("crys_break", (px + 0.06, py - 0.05, G_Z + 0.31 + h + 0.01),
                         (r * 1.62, r * 1.42, 0.12), M["crystal_pale"],
                         rot=(0.16, -0.12, a)), 0.004)
            for ob in shard("crys_fallen", (px + 1.24, py + 0.56, G_Z + 0.16), r * 0.92,
                            h * 1.34, M["crystal"], M["crystal_pale"], sides=6, tip=0.18,
                            rot=(0.0, math.pi * 0.5 - 0.14, a * 0.5)):
                self.add(ob, 0.006)
            self.add(box("crys_chip", (px + 0.76, py + 1.10, G_Z + 0.10),
                         (0.34, 0.26, 0.16), M["crystal"], rot=(0.2, 0.1, a)), 0.003)
        else:
            for ob in shard("crys_main", tuple(base), r, h, M["crystal"],
                            M["crystal_pale"], sides=6, tip=0.17, rot=rot):
                self.add(ob, 0.008)
        # 两根卫星晶：一高一矮、一前一后
        for (k, (rr, hh, tl, da)) in enumerate(((r * 0.54, h * 0.60, tilt + 0.12, 44),
                                                (r * 0.40, h * 0.38, tilt + 0.18, -62))):
            aa = a + math.radians(da)
            d = Vector((math.cos(aa), math.sin(aa), 0.0))
            loc = base + d * (0.46 + k * 0.06)
            rot2 = (math.sin(aa) * -tl, math.cos(aa) * tl, 0.0)
            for ob in shard("crys_sat", tuple(loc), rr, hh, M["crystal"],
                            M["crystal_pale"], sides=6, tip=0.22, rot=rot2):
                self.add(ob, 0.003)

    # ── 10. 火盆 · 断碑 · 落石 ──────────────────────────────────────────────
    def props(self):
        M = self.M
        for sx in (-1, 1):
            self.brazier(sx * 3.32, 6.36)
        # 场地边上的两块塌石
        for (px, py, s) in ((-1.72, -5.68, 0.36), (4.10, 6.62, 0.30)):
            self.add(box("rubble_big", (px, py, G_Z + s * 0.30), (s, s * 0.82, s * 0.60),
                         M["stone_mid"], rot=(0.12, 0.08, 0.4)), 0.006)

    def brazier(self, px, py):
        M = self.M
        self.add(box("braz_base", (px, py, G_Z + 0.12), (0.84, 0.84, 0.24), M["stone_mid"]), 0.006)
        self.add(box("braz_col", (px, py, G_Z + 0.74), (0.52, 0.52, 1.00), M["stone_light"]), 0.008)
        self.add(box("braz_band", (px, py, G_Z + 0.70), (0.62, 0.62, 0.34), M["team"]), 0.003)
        self.add(box("braz_cap", (px, py, G_Z + 1.32), (0.74, 0.74, 0.20), M["stone_light"]), 0.005)
        self.add(revolve("braz_bowl", [(0.34, 0.0), (0.54, 0.22), (0.58, 0.36)], 8,
                         (px, py, G_Z + 1.40), M["iron"]), 0.006)
        self.add(tube_band("braz_rim", (px, py), 0.53, 0.62, G_Z + 1.72, G_Z + 1.82, 8,
                           M["gold"]), 0.003)
        # 冷焰：**深紫的焰体 + 碗口一圈亮底**。整朵用亮紫会烧成一团白，
        # 在灰石背景上读不出"紫火"，只能读出"曝光过了"
        self.add(L.lathe("braz_flame", [(0.38, G_Z + 1.74, px, py),
                                        (0.34, G_Z + 2.10, px + 0.04, py - 0.02),
                                        (0.18, G_Z + 2.40, px + 0.06, py - 0.04),
                                        (0.0, G_Z + 2.62, px + 0.07, py - 0.05)],
                         7, M["crystal"], phase=0.3), 0.0)
        self.add(L.lathe("braz_core", [(0.30, G_Z + 1.70, px, py),
                                       (0.24, G_Z + 1.80, px, py),
                                       (0.10, G_Z + 1.88, px, py),
                                       (0.0, G_Z + 1.92, px, py)],
                         7, M["crystal_pale"], phase=0.4), 0.0)

    # ── 11. 旗（山门正面两幅垂旗，正面与 3/4 视角都读得到）──────────────────
    def heraldry(self):
        M = self.M
        yf = BAY_Y1 + 0.04                       # 5.66：拱券前沿之外
        for sx in (-1, 1):
            px = sx * 1.40
            self.add(box("flag_arm", (px, yf - 0.02, 4.10), (0.58, 0.10, 0.10),
                         M["wood_dark"]), 0.004)
            for zz in (4.06, 3.99):
                self.add(box("flag_ring", (px, yf, zz), (0.17, 0.07, 0.07),
                             M["iron"]), 0.002)
            # 旗布：上段整幅 + 下段收窄 + 燕尾（与另六座同一形制）
            zz = 4.04
            for (kw, hh) in ((1.00, 0.88), (0.84, 0.62)):
                self.add(box("flag_cloth", (px, yf, zz - hh * 0.5),
                             (0.62 * kw, 0.05, hh), M["team"]), 0.003)
                zz -= hh
            for sgn in (-1, 1):
                self.add(box("flag_tail", (px + sgn * 0.16, yf, zz - 0.18),
                             (0.22, 0.05, 0.36), M["team"]), 0.003)
            self.add(box("flag_trim", (px, yf + 0.032, 4.02), (0.64, 0.03, 0.06),
                         M["team_trim"]), 0.002)
            self.crest("flag_crest", "Y", px, yf + 0.032, 3.02, 0.26)

    # ── 12. 组装 / 收尾 ────────────────────────────────────────────────────
    def build(self):
        for step in (self.yard, self.dais, self.portico, self.cella, self.portal,
                     self.pediment, self.upper, self.crown, self.crystals, self.props,
                     self.heraldry):
            step()
        return self

    def finalize(self, bevel=True):
        # 多边形件（十二 / 八边形棱柱、穹顶、拱）**一律平着色**：
        # 12 边夹角 30° 小于 shade_auto 的 32°，走平滑会被磨成一根水泥筒。
        flat_pref = ("dais_", "deck_", "cornice_", "cella_", "pil_", "niche_",
                     "portal_", "bay_", "step", "drum", "dome_", "lan_", "spire_",
                     "finial", "lamp_", "braz_bowl", "braz_rim", "yard_core",
                     "rune_", "stela", "ped_")
        # 曲面细分只磨"体量件"的小棱：墙板 / 台基 / 穹顶 / 柱身都是大平面，
        # CC 会把棱磨成一圈渐变的圆（塑料感）。真圆只留给小金属件。
        skip_cc = ("yard_", "dais_", "deck_", "cella_", "pil_", "cornice_", "portal_",
                   "bay_", "step", "drum", "dome_", "lan_", "spire_", "finial",
                   "lamp_", "crys_", "domecrys", "flag_", "stela", "rubble", "tuft",
                   "braz_", "niche_", "rune_", "ped_")
        for (ob, bev, sub, seg) in self.items:
            co = ob.data.vertices
            if not len(co):
                continue
            dims = [max(v.co[i] for v in co) - min(v.co[i] for v in co) for i in range(3)]
            chunky = min(dims) >= 0.12 and dims[0] * dims[1] * dims[2] >= 0.14
            n = ob.name
            is_flat = n.startswith(flat_pref)
            if self.smooth:
                cc = 1 if (chunky and not is_flat and not n.startswith(skip_cc)) else 0
                L.finalize(ob, bevel=min(max(bev, 0.008), 0.022), seg=1, sub=cc,
                           flat=is_flat)
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
        out = L.join_by_material(objs, prefix="MS")
        mirror_x(out)
        if self.unwrap:
            L.smart_uv(out)
        return out


def build(smooth=True, unwrap=True, bevel=True):
    m = Model(smooth, unwrap).build()
    objs = m.finalize(bevel=bevel)
    return objs, L.stats(objs)
