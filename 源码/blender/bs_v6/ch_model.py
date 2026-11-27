"""
ch_model.py —— 第十座资产：块面剑士（Warcraft III 人族步兵读感）

不是体素人 —— 是「分段块面人」：
  每条肢体是一块**独立的实体块**（不是一堆小方块拼出来的体素），每块单独倒角，
  关节处留 35–50 mm 的缝，缝里塞一根明显更细的深色「关节轴」。
  远看是一个有体积的人，近看每一块都能数出来 —— 这是"分段"和"体素"的区别。

识别四件套：单手剑（右手）+ 圆盾（左手）+ 桶盔（带盔缨）+ 大护肩（弧壳 + 叠片 + 包边）。
头身比 1 : 3.9 —— H = 2.42 m；头（下颌 1.80 → 盔顶 2.42）= 0.6205 = 2.42 / 3.9。

管线冲突（本座独有，必须处理）：
  左右不对称（盾左剑右），**不能**让 finalize() 沿 X 镜像收尾 —— 镜像会出两面盾两把剑。
  做法：build() 只产对称体；finalize() 先镜像对称体（镜像的同时把 .L / .R 的骨名互换，
  保证"建模期 +X 的那只手"在成品里仍然是同一只手），**镜像之后**才单独生成盾与剑，
  各挂一根专用骨 shield.L / weapon.R —— 盾剑从来没进过镜像管线，所以不可能翻倍。

材质：独立 char_atlas（4×4 / 512² / 内缩 22），不与建筑 ATLAS_ORDER 共用 ——
  为了加一个 skin 色重出九座建筑不划算。甲片用 steel（新起一档中灰钢），
  skin / cloth 是要求新增的两色，束带 / 靴借 earth，剑柄 / 盾背借 wood_dark，
  关节 / 铆钉借 iron。

坐标：X 右、Y 前（+Y = 正面）、Z 上；原点在双足中间，z = 0 地面。
阵营色只染四处大块：盾面（最大）、护肩包边、盔缨、腰带。
"""
import math
from math import tau as TAU

import bmesh
import bpy
from mathutils import Euler, Vector

import bslib as L
from bslib import box, extrude, mesh_obj, revolve

# ── 尺寸表（m；改高度必须重算头身比）─────────────────────────────────────────
H_TOTAL = 2.42
HEAD_H = H_TOTAL / 3.9            # 0.6205
Z_CHIN = H_TOTAL - HEAD_H         # 1.7995

# 腿：靴 / 踝缝 / 胫甲 / 膝 / 腿甲 五段
Z_BOOT1 = 0.245
Z_ANKLE = 0.286
Z_KNEE_LO, Z_KNEE_HI = 0.730, 0.792
Z_THIGH1 = 1.060
LEG_X = 0.118

# 臂（约 8.5° 的 A-pose；肩 / 肘 / 腕三处留缝）
Z_ELBOW = 1.404
Z_WRIST = 1.160

# 护肩：绕肩关节的一段椭圆弧壳（4 段 = 4 个块面），内径贴着上臂
PD_CX, PD_CZ = 0.268, 1.672
PD_RXO, PD_RZO = 0.252, 0.208
PD_RXI, PD_RZI = 0.108, 0.086
PD_A0, PD_A1 = 126.0, -32.0

# 桶盔：下沿压到下颌线，头身比才读得对
HELM_Z0, HELM_Z1 = 1.815, 2.335
HELM_W0, HELM_D0 = 0.478, 0.450
HELM_W1, HELM_D1 = 0.412, 0.394
HELM_CH = 0.092
HELM_FRONT = HELM_D0 * 0.5        # 0.221
FACE_Y = 0.146
OPEN_U = 0.78                     # 面窗半宽（占前脸半宽的比例）
OPEN_V0, OPEN_V1 = 0.268, 0.775   # → z 1.955 / 2.218

# 盾（局部：+Y 是盾面法线，原点在盾背平面中心）
SH_PROF = [(0.300, 0.000), (0.250, 0.012), (0.160, 0.030), (0.075, 0.041), (0.020, 0.045)]


def sh_face_y(r):
    """盾面在半径 r 处的高度（线性插值 SH_PROF）—— 金线要贴着面走，不能是一条平圈。"""
    for i in range(len(SH_PROF) - 1):
        r0, y0 = SH_PROF[i]
        r1, y1 = SH_PROF[i + 1]
        if r1 <= r <= r0:
            t = (r0 - r) / max(r0 - r1, 1e-6)
            return y0 + (y1 - y0) * t
    return SH_PROF[-1][1]


SH_R = 0.338
SH_POS = (-0.366, 0.098, 1.206)
SH_RZ = 20.0

# 剑（局部：+Z 是握把向上，−Z 是剑尖；原点在握把中心）
SW_POS = (0.352, 0.030, 1.072)
SW_RX, SW_RY = 24.0, -10.0


# ── 骨架（交付空间；角色朝 +Y，所以 .L = −X）─────────────────────────────────
def _swap_side(name):
    if not name:
        return name
    if name.endswith(".L"):
        return name[:-2] + ".R"
    if name.endswith(".R"):
        return name[:-2] + ".L"
    return name


_BASE_BONES = [
    ("root",      (0, 0, 0.000),          (0, 0, 0.200),          None),
    ("pelvis",    (0, 0, 1.000),          (0, 0, 1.190),          "root"),
    ("spine",     (0, 0, 1.190),          (0, 0, 1.400),          "pelvis"),
    ("chest",     (0, 0, 1.400),          (0, 0, 1.740),          "spine"),
    ("neck",      (0, 0, 1.740),          (0, 0, 1.880),          "chest"),
    ("head",      (0, 0, 1.880),          (0, 0, 2.420),          "neck"),
    ("clavicle.L", (-0.048, 0, 1.700),    (-0.258, 0, 1.696),     "chest"),
    ("upperarm.L", (-0.266, 0, 1.688),    (-0.302, 0.006, 1.404), "clavicle.L"),
    ("forearm.L", (-0.302, 0.006, 1.404), (-0.344, 0.014, 1.160), "upperarm.L"),
    ("hand.L",    (-0.344, 0.014, 1.160), (-0.350, 0.020, 1.000), "forearm.L"),
    ("shield.L",  (-0.344, 0.020, 1.250), (-0.404, 0.300, 1.250), "forearm.L"),
    ("thigh.L",   (-0.118, 0, 1.030),     (-0.118, 0, 0.762),     "pelvis"),
    ("shin.L",    (-0.118, 0, 0.762),     (-0.118, 0, 0.286),     "thigh.L"),
    ("foot.L",    (-0.118, 0, 0.286),     (-0.118, 0.200, 0.100), "shin.L"),
]


def _mirror_bones(bones):
    out = list(bones)
    for (n, h, t, p) in bones:
        if not (n.endswith(".L") or n.endswith(".R")):
            continue
        out.append((_swap_side(n), (-h[0], h[1], h[2]), (-t[0], t[1], t[2]),
                    _swap_side(p) if p else p))
    return out


BONES = _mirror_bones(_BASE_BONES) + [
    ("weapon.R", (0.352, 0.030, 1.072), (0.432, 0.233, 0.622), "hand.R"),
]


# ── 基础几何 ────────────────────────────────────────────────────────────────
def mk(name, verts, faces, mat, recalc=True):
    """自建网格。

    `recalc=False` 专供**环带（torus）**：`bmesh.ops.recalc_face_normals` 用射线
    判"外面"，对环带会内外打架（实测同一个环，正反两种绕序算出的有符号体积
    都不为零、也不互为相反数 = 朝向不一致），渲染出来是一块黑饼。
    环带的绕序在 `rev_y` 里是构造保证的，直接跳过 recalc 更可靠。
    """
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], [tuple(f) for f in faces])
    me.validate(verbose=False)
    me.update()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    me.materials.append(mat)
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    if recalc:
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        if bm.calc_volume(signed=True) < 0:
            bmesh.ops.reverse_faces(bm, faces=list(bm.faces))
    bm.to_mesh(me)
    bm.free()
    me.update()
    return ob


def poly_rect(w, d, ch=0.0):
    """矩形截面（逆时针）；ch>0 切角成八边形 —— 块面的棱就是这么来的。

    点序固定：0/1 是后面一条边，4/5 是正前面一条边（`FRONT_EDGE` 靠这个）。
    """
    hw, hd = w * 0.5, d * 0.5
    if ch <= 1e-6:
        return [(-hw, -hd), (hw, -hd), (hw, hd), (-hw, hd)]
    c = min(ch, hw * 0.85, hd * 0.85)
    return [(-hw + c, -hd), (hw - c, -hd), (hw, -hd + c), (hw, hd - c),
            (hw - c, hd), (-hw + c, hd), (-hw, hd - c), (-hw, -hd + c)]


FRONT_EDGE = {8: 4, 4: 2}


def loft(name, rows, mat, caps=True, skip_edges=()):
    """等点数截面自下而上缝合。rows = [[(x,y,z), ...], ...]"""
    n = len(rows[0])
    m = len(rows)
    verts = [p for r in rows for p in r]
    faces = []
    for k in range(m - 1):
        b, b2 = k * n, (k + 1) * n
        for i in range(n):
            if i in skip_edges:
                continue
            j = (i + 1) % n
            faces.append((b + i, b + j, b2 + j, b2 + i))
    if caps:
        faces.append(tuple(range(n - 1, -1, -1)))
        faces.append(tuple(range((m - 1) * n, m * n)))
    return mk(name, verts, faces, mat)


def tube(name, stations, mat):
    """竖直分段块体：stations = [(z, cx, cy, w, d, ch), ...] 自下而上。"""
    rows = []
    for (z, cx, cy, w, d, ch) in stations:
        rows.append([(cx + x, cy + y, z) for (x, y) in poly_rect(w, d, ch)])
    return loft(name, rows, mat)


def arc_row(cx, cz, ro, ri, a0, a1, segs, y, s=1.0):
    """护肩的一圈截面：外弧 →（掉头）内弧，是一条"弯板"的闭合截面。"""
    row = []
    for k in range(segs + 1):
        a = math.radians(a0 + (a1 - a0) * k / segs)
        row.append((cx + ro[0] * s * math.cos(a), y, cz + ro[1] * s * math.sin(a)))
    for k in range(segs, -1, -1):
        a = math.radians(a0 + (a1 - a0) * k / segs)
        row.append((cx + ri[0] * s * math.cos(a), y, cz + ri[1] * s * math.sin(a)))
    return row


def arc_plate(name, cx, cz, ro, ri, a0, a1, segs, ys, mat):
    """弧形板：ys = [(y, scale), ...]，沿 Y 逐站缝合（护肩 / 包边 / 叠片）。"""
    return loft(name, [arc_row(cx, cz, ro, ri, a0, a1, segs, y, s) for (y, s) in ys], mat)


def rev_y(name, prof, seg, mat, closed=False, phase=0.0):
    """绕 Y 轴回转；prof = [(r, y), ...]。closed=True 时首尾相接（环带）。

    **prof 两端都给 r>0**：收成 r=0 的极点会在 remove_doubles 之后留下
    非流形边（实测 10 条），法线兜底也跟着失灵。收口用 0.012–0.02 的小端面。
    """
    verts, faces = [], []
    m = len(prof)
    # **顶点必须按"角度优先"排**（每个角度一节、节内按截面点走）：
    # 下面的面是按 b = s*m 索引的，写成"截面点优先"两个下标就对不上 ——
    # 表现出来不是报错，而是整块盾面糊成一张黑饼、盾脐揉成一团（踩过）。
    for s in range(seg):
        a = phase + TAU * s / seg
        ca, sa = math.cos(a), math.sin(a)
        for (r, y) in prof:
            verts.append((r * ca, y, r * sa))
    for s in range(seg):
        b, b2 = s * m, ((s + 1) % seg) * m
        for k in range(m if closed else m - 1):
            k2 = (k + 1) % m
            faces.append((b + k, b + k2, b2 + k2, b2 + k))
    if not closed:
        faces.append(tuple(range(0, seg * m, m)))
        faces.append(tuple(range(m - 1, seg * m, m)))
    return mk(name, verts, faces, mat, recalc=not closed)


def helm_shell(name, z0, z1, w0, d0, w1, d1, ch, ou, v0, v1, face_y, mat, socket_mat):
    """桶盔壳：正前方是一个**真开口**（面窗），不是贴片。

    前脸被拆成 4×4 网格去掉中间一格（8 块圈梁），再补 4 块"窗洞侧壁"接到面板
    平面 face_y —— 不然从斜角能直接看进空心的盔里（规则 B13 的复发）。
    侧壁单独一个**深色** object：盔内是暗的，脸才像"在盔里"而不是"贴在窗口上"。
    返回 (盔壳, 窗洞内壁)。
    """
    A0, A1 = w0 * 0.5 - ch, w1 * 0.5 - ch
    Y0, Y1 = d0 * 0.5, d1 * 0.5

    def P(u, v):
        return ((A0 * (1 - v) + A1 * v) * u, Y0 * (1 - v) + Y1 * v, z0 + (z1 - z0) * v)

    verts, faces = [], []
    for (z, w, d) in ((z0, w0, d0), (z1, w1, d1)):
        verts.extend([(x, y, z) for (x, y) in poly_rect(w, d, ch)])
    n = 8
    for i in range(n):
        if i == FRONT_EDGE[n]:
            continue
        j = (i + 1) % n
        faces.append((i, j, n + j, n + i))
    faces.append(tuple(range(n - 1, -1, -1)))
    faces.append(tuple(range(n, 2 * n)))

    us = (-1.0, -ou, ou, 1.0)
    vs = (0.0, v0, v1, 1.0)
    grid = [[P(u, v) for u in us] for v in vs]
    for j in range(3):
        for i in range(3):
            if i == 1 and j == 1:
                continue
            base = len(verts)
            verts.extend([grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]])
            faces.append((base, base + 1, base + 2, base + 3))
    shell = mk(name, verts, faces, mat)

    sv, sf = [], []
    for (a, b) in ((grid[1][1], grid[1][2]), (grid[2][1], grid[2][2]),
                   (grid[1][1], grid[2][1]), (grid[1][2], grid[2][2])):
        base = len(sv)
        sv.extend([a, b, (b[0], face_y, b[2]), (a[0], face_y, a[2])])
        sf.append((base, base + 1, base + 2, base + 3))
    socket = mk(name + "_sock", sv, sf, socket_mat)
    return shell, socket


def side_disc(name, prof, seg, mat, center, out, rz=0.0):
    """朝 ±X 的圆盘（护肘 / 盔耳）。out = ±1。"""
    ob = rev_y(name, prof, seg, mat)
    ob.rotation_euler = Euler((0, 0, math.radians(-90 * out) + rz), "XYZ")
    ob.location = center
    return ob


# ── 模型 ─────────────────────────────────────────────────────────────────────
class Model:
    """items 里每项 = (obj, bone, bevel, seg, sub, smooth)。bone 决定刚性蒙皮。"""

    def __init__(self, smooth=True, level=0):
        self.smooth = smooth
        self.level = level
        self.items = []
        self.M = L.all_materials()

    def add(self, ob, bone, bevel=0.008, seg=2, sub=0, smooth=True):
        self.items.append((ob, bone, bevel, seg, sub, smooth))
        return ob

    # ── 1. 腿 ───────────────────────────────────────────────────────────────
    def legs(self):
        M = self.M
        for s, sd in ((1, "r"), (-1, "l")):
            x = s * LEG_X
            bf = "foot." + sd.upper()
            bs = "shin." + sd.upper()
            th = "thigh." + sd.upper()

            self.add(box("lg_sole_" + sd, (x, 0.040, 0.030), (0.226, 0.382, 0.060),
                         M["earth_dark"]), bf, 0.008, 2, 0, False)
            self.add(tube("lg_boot_" + sd, [
                (0.055, x, 0.026, 0.202, 0.312, 0.034),
                (0.150, x, 0.014, 0.192, 0.296, 0.034),
                (0.245, x, -0.002, 0.176, 0.244, 0.032),
            ], M["earth"]), bf, 0.012, 2, 1, True)
            self.add(tube("lg_toe_" + sd, [
                (0.046, x, 0.152, 0.200, 0.140, 0.030),
                (0.120, x, 0.160, 0.170, 0.104, 0.026),
            ], M["steel_dark"]), bf, 0.006, 2, 0, False)
            self.add(box("lg_strap_" + sd, (x, -0.002, 0.214), (0.200, 0.278, 0.034),
                         M["earth_dark"]), bf, 0.005, 2, 0, False)
            self.add(tube("lg_cuff_" + sd, [
                (0.208, x, -0.002, 0.196, 0.266, 0.036),
                (0.246, x, -0.004, 0.184, 0.250, 0.034),
            ], M["earth_dark"]), bf, 0.005, 2, 0, False)
            self.add(box("lg_strapk_" + sd, (x, 0.132, 0.214), (0.038, 0.030, 0.044),
                         M["iron"]), bf, 0.004, 1, 0, False)

            # 踝缝（关节轴比两端细 25%，缝才读得出来）
            self.add(tube("jt_ankle_" + sd, [
                (0.238, x, 0.000, 0.116, 0.124, 0.022),
                (0.294, x, 0.000, 0.120, 0.128, 0.022),
            ], M["cloth_dark"]), bs, 0.006, 1, 0, False)

            self.add(tube("lg_shin_" + sd, [
                (0.286, x, 0.000, 0.180, 0.192, 0.038),
                (0.520, x, 0.002, 0.198, 0.210, 0.040),
                (0.730, x, 0.004, 0.210, 0.220, 0.042),
            ], M["steel"]), bs, 0.011, 2, 0, True)
            self.add(tube("lg_greave_" + sd, [
                (0.642, x, 0.004, 0.216, 0.226, 0.046),
                (0.740, x, 0.004, 0.224, 0.236, 0.048),
            ], M["steel_dark"]), bs, 0.007, 2, 0, False)

            # 膝：块面护膝（不是圆球 —— 三段折面才跟整体语言一致）
            self.add(tube("lg_poleyn_" + sd, [
                (0.716, x, 0.086, 0.150, 0.078, 0.030),
                (0.762, x, 0.098, 0.176, 0.104, 0.034),
                (0.812, x, 0.082, 0.158, 0.076, 0.030),
            ], M["steel_dark"]), bs, 0.008, 2, 0, False)

            self.add(tube("jt_knee_" + sd, [
                (0.718, x, 0.000, 0.158, 0.168, 0.030),
                (0.800, x, 0.000, 0.160, 0.170, 0.030),
            ], M["cloth_dark"]), th, 0.006, 1, 0, False)

            self.add(tube("lg_thigh_" + sd, [
                (0.792, x, 0.000, 0.214, 0.234, 0.044),
                (0.945, x, 0.000, 0.228, 0.248, 0.046),
                (1.060, x, 0.000, 0.232, 0.256, 0.046),
            ], M["cloth"]), th, 0.012, 2, 1, True)
            # 腿甲钢片：只盖前半，两侧留出布 —— 不然整条腿是一个灰筒
            self.add(tube("lg_cuisse_" + sd, [
                (0.856, x, 0.094, 0.156, 0.066, 0.024),
                (0.966, x, 0.098, 0.168, 0.072, 0.026),
                (1.026, x, 0.100, 0.160, 0.060, 0.024),
            ], M["steel"]), th, 0.007, 2, 0, False)

    # ── 2. 胯 / 腰 / 裙甲 ────────────────────────────────────────────────────
    def hips(self):
        M = self.M
        self.add(tube("bd_pelvis", [
            (0.988, 0, 0.000, 0.372, 0.300, 0.060),
            (1.095, 0, 0.000, 0.398, 0.316, 0.064),
            (1.196, 0, 0.000, 0.384, 0.306, 0.062),
        ], M["cloth_dark"]), "pelvis", 0.013, 2, 1, True)

        # 腰带：全包一圈的队色（四处染色之一）
        self.add(tube("bd_belt", [
            (1.146, 0, 0.000, 0.406, 0.330, 0.064),
            (1.244, 0, 0.000, 0.402, 0.326, 0.064),
        ], M["team"]), "pelvis", 0.006, 2, 0, False)
        self.add(box("bd_buckle", (0, 0.160, 1.195), (0.090, 0.034, 0.076),
                     M["iron"]), "pelvis", 0.005, 1, 0, False)
        self.add(box("bd_buckleg", (0, 0.176, 1.195), (0.048, 0.020, 0.038),
                     M["gold"]), "pelvis", 0.004, 1, 0, False)

        # 裙甲：每侧三片，沿胯部圆弧排开（片间留缝）
        for s, sd in ((1, "r"), (-1, "l")):
            for i, (ang, w, h) in enumerate(((14, 0.088, 0.150), (50, 0.084, 0.142),
                                             (86, 0.076, 0.124))):
                a = math.radians(ang)
                px, py = s * 0.188 * math.sin(a), 0.188 * math.cos(a)
                self.add(box("ts_%s%d" % (sd, i), (px, py, 1.072),
                             (w, 0.026, h), M["steel_dark"],
                             rot=(math.radians(-7), 0, -s * a)),
                         "pelvis", 0.007, 2, 0, False)

    # ── 3. 躯干 ─────────────────────────────────────────────────────────────
    def torso(self):
        M = self.M
        self.add(tube("bd_abdomen", [
            (1.140, 0, 0.000, 0.336, 0.286, 0.052),
            (1.270, 0, 0.004, 0.348, 0.296, 0.054),
            (1.380, 0, 0.006, 0.362, 0.304, 0.056),
        ], M["cloth"]), "spine", 0.012, 2, 0, True)

        # 胸甲：正面一道中脊（截面 9 点），上宽下窄的 V
        def sec(w, d, ridge):
            hw, hd = w * 0.5, d * 0.5
            return [(-hw * 0.88, -hd), (hw * 0.88, -hd), (hw, -hd * 0.42),
                    (hw, hd * 0.62), (hw * 0.70, hd), (0.0, hd + ridge),
                    (-hw * 0.70, hd), (-hw, hd * 0.62), (-hw, -hd * 0.42)]

        rows = []
        for (z, w, d, r) in ((1.300, 0.378, 0.298, 0.008),
                             (1.480, 0.452, 0.342, 0.018),
                             (1.650, 0.504, 0.364, 0.022),
                             (1.788, 0.442, 0.330, 0.014)):
            rows.append([(x, y - 0.004, z) for (x, y) in sec(w, d, r)])
        self.add(loft("bd_chest", rows, M["steel"]), "chest", 0.012, 2, 1, True)

        # 胸甲下缘的 V 尖：第二层甲压在腰带上（"两件甲叠着"的层次）
        vp = [(-0.146, 1.318), (0.146, 1.318), (0.128, 1.208), (0.0, 1.132), (-0.128, 1.208)]
        self.add(extrude("bd_plackart", vp, "Y", 0.026, (0.0, 0.0), M["steel_dark"],
                         offset=0.146), "chest", 0.006, 2, 0, False)

        # 领口铁圈（把头和胸分开）
        self.add(tube("bd_gorget", [
            (1.756, 0, 0.000, 0.286, 0.262, 0.066),
            (1.828, 0, 0.000, 0.250, 0.232, 0.058),
        ], M["steel_dark"]), "chest", 0.007, 2, 0, False)

        for s in (1, -1):
            for (zz, xx) in ((1.468, 0.222), (1.690, 0.240)):
                self.add(box("bd_rivet_%d_%d" % (s, int(zz * 100)),
                             (s * xx, 0.010, zz), (0.026, 0.026, 0.026), M["iron"]),
                         "chest", 0.003, 1, 0, False)
        self.add(tube("jt_neck", [
            (1.726, 0, 0.000, 0.150, 0.146, 0.040),
            (1.900, 0, 0.004, 0.154, 0.150, 0.040),
        ], M["cloth_dark"]), "neck", 0.006, 1, 0, False)

    # ── 4. 臂 + 护肩 ────────────────────────────────────────────────────────
    def arms(self):
        M = self.M
        for s, sd in ((1, "r"), (-1, "l")):
            ua = "upperarm." + sd.upper()
            fa = "forearm." + sd.upper()
            hd = "hand." + sd.upper()

            self.add(tube("jt_shoulder_" + sd, [
                (1.612, s * 0.262, 0.000, 0.144, 0.152, 0.036),
                (1.716, s * 0.258, 0.000, 0.150, 0.156, 0.038),
            ], M["cloth_dark"]), "clavicle." + sd.upper(), 0.006, 1, 0, False)

            self.add(tube("ar_upper_" + sd, [
                (1.424, s * 0.300, 0.006, 0.160, 0.166, 0.038),
                (1.560, s * 0.286, 0.002, 0.170, 0.176, 0.040),
                (1.690, s * 0.270, 0.000, 0.176, 0.182, 0.040),
            ], M["steel_dark"]), ua, 0.011, 2, 0, True)
            # 肩下布环（护肩与护臂之间的一道软衬，压暗一档，别读成裸胳膊）
            self.add(tube("ar_sleeve_" + sd, [
                (1.586, s * 0.284, 0.002, 0.182, 0.188, 0.042),
                (1.634, s * 0.280, 0.001, 0.180, 0.186, 0.042),
            ], M["cloth_dark"]), ua, 0.006, 2, 0, False)

            self.add(tube("jt_elbow_" + sd, [
                (1.370, s * 0.306, 0.006, 0.112, 0.118, 0.026),
                (1.428, s * 0.303, 0.006, 0.114, 0.120, 0.026),
            ], M["cloth_dark"]), fa, 0.005, 1, 0, False)

            self.add(tube("ar_fore_" + sd, [
                (1.158, s * 0.344, 0.016, 0.166, 0.172, 0.038),
                (1.300, s * 0.326, 0.010, 0.180, 0.186, 0.040),
                (1.392, s * 0.312, 0.007, 0.184, 0.190, 0.040),
            ], M["steel"]), fa, 0.010, 2, 0, True)
            self.add(tube("ar_cuff_" + sd, [
                (1.362, s * 0.314, 0.007, 0.196, 0.202, 0.044),
                (1.400, s * 0.310, 0.007, 0.192, 0.198, 0.042),
            ], M["steel_dark"]), fa, 0.006, 2, 0, False)

            self.add(side_disc("ar_couter_" + sd,
                               [(0.060, -0.010), (0.056, 0.022), (0.036, 0.038),
                                (0.012, 0.044)], 8, M["steel_dark"],
                               (s * 0.388, 0.008, 1.398), s), fa, 0.005, 2, 0, True)

            self.add(tube("jt_wrist_" + sd, [
                (1.134, s * 0.346, 0.016, 0.110, 0.116, 0.026),
                (1.174, s * 0.344, 0.016, 0.112, 0.118, 0.026),
            ], M["cloth_dark"]), hd, 0.005, 1, 0, False)
            self.add(tube("ar_hand_" + sd, [
                (1.000, s * 0.348, 0.022, 0.146, 0.168, 0.032),
                (1.070, s * 0.350, 0.020, 0.154, 0.176, 0.034),
                (1.148, s * 0.346, 0.017, 0.144, 0.162, 0.032),
            ], M["steel_dark"]), hd, 0.010, 2, 1, True)
            self.add(box("ar_knuck_" + sd, (s * 0.354, 0.104, 1.070),
                         (0.132, 0.030, 0.054), M["steel"]), hd, 0.005, 2, 0, False)

            # ── 护肩：弧壳（内径贴着上臂）+ 队色包边 + 下叠片 ──
            ys = ((-0.218, 0.58), (-0.152, 0.86), (-0.052, 1.0),
                  (0.052, 1.0), (0.152, 0.86), (0.218, 0.58))
            self.add(arc_plate("pd_shell_" + sd, s * PD_CX, PD_CZ,
                               (PD_RXO, PD_RZO), (PD_RXI, PD_RZI),
                               PD_A0, PD_A1, 4, ys, M["steel"]),
                     ua, 0.011, 2, 0, True)
            # 包边：贴着外缘下沿的一条窄边（不是整块面板 —— 那会读成"奶油色护肩"）
            self.add(arc_plate("pd_trim_" + sd, s * PD_CX, PD_CZ,
                               (PD_RXO + 0.013, PD_RZO + 0.013),
                               (PD_RXO - 0.019, PD_RZO - 0.019),
                               -38.0, -20.0, 2,
                               ((-0.186, 0.60), (-0.132, 0.86), (0.0, 1.0),
                                (0.132, 0.86), (0.186, 0.60)), M["team_trim"]),
                     ua, 0.005, 2, 0, False)
            # 顶脊：护肩上的一道加强肋，把"软面包"压成"甲片"
            self.add(arc_plate("pd_rib_" + sd, s * PD_CX, PD_CZ,
                               (PD_RXO + 0.013, PD_RZO + 0.013),
                               (PD_RXO - 0.020, PD_RZO - 0.020),
                               98.0, 74.0, 2,
                               ((-0.156, 0.86), (-0.060, 1.0), (0.060, 1.0),
                                (0.156, 0.86)), M["steel_dark"]),
                     ua, 0.005, 2, 0, False)
            self.add(arc_plate("pd_lame_" + sd, s * PD_CX, PD_CZ,
                               (PD_RXO - 0.030, PD_RZO - 0.024),
                               (PD_RXI - 0.006, PD_RZI - 0.004),
                               4.0, -36.0, 2,
                               ((-0.184, 0.64), (-0.124, 0.90), (0.0, 1.0),
                                (0.124, 0.90), (0.184, 0.64)), M["steel_dark"]),
                     ua, 0.006, 2, 0, True)

    # ── 5. 头 / 盔 ─────────────────────────────────────────────────────────
    def head(self):
        M = self.M
        # 盔壳（正面真开口）+ 窗洞内壁（暗）
        shell, sock = helm_shell("hm_shell", HELM_Z0, HELM_Z1,
                                 HELM_W0, HELM_D0, HELM_W1, HELM_D1, HELM_CH,
                                 OPEN_U, OPEN_V0, OPEN_V1, FACE_Y,
                                 M["steel"], M["dark"])
        self.add(shell, "head", 0.010, 2, 0, True)
        self.add(sock, "head", 0.003, 1, 0, False)

        # 脸：比窗口小一圈，四周留 20 mm 暗边 —— 脸才像"在盔里"
        self.add(box("hm_face", (0, 0.160, 2.092), (0.176, 0.026, 0.214),
                     M["skin"]), "head", 0.006, 2, 0, True)
        for s in (1, -1):
            self.add(box("hm_eye_%d" % s, (s * 0.046, 0.174, 2.136),
                         (0.040, 0.012, 0.019), M["dark"],
                         rot=(0, s * math.radians(7), 0)), "head", 0.002, 1, 0, False)
        self.add(box("hm_mouth", (0, 0.174, 1.992), (0.050, 0.010, 0.009),
                     M["dark"]), "head", 0.002, 1, 0, False)
        # 下巴通风孔（近看有活气，远看只是三道暗线）
        for i in (-1, 0, 1):
            self.add(box("hm_breath_%d" % i, (i * 0.030, 0.232, 1.918),
                         (0.010, 0.014, 0.040), M["dark"]), "head", 0.002, 1, 0, False)

        # 头盔顶：真圆顶（按圆弧取四环，不是"阶梯塔"）
        self.add(tube("hm_dome", [
            (2.326, 0, 0.010, 0.436, 0.414, 0.088),
            (2.372, 0, 0.010, 0.336, 0.320, 0.068),
            (2.402, 0, 0.010, 0.214, 0.204, 0.044),
            (2.420, 0, 0.010, 0.104, 0.098, 0.020),
        ], M["steel"]), "head", 0.007, 2, 1, True)

        # 眉檐：压在面窗上沿，给眼睛一条硬阴影（后沿埋进盔壳，前沿出挑 22 mm）
        self.add(box("hm_brow", (0, 0.212, 2.232), (0.238, 0.048, 0.042),
                     M["steel_dark"]), "head", 0.006, 2, 0, False)
        # 鼻梁护条：细，从眉檐挂到嘴上方（这一条把"方脸"读成"桶盔"）
        self.add(box("hm_nasal", (0, 0.178, 2.114), (0.026, 0.040, 0.168),
                     M["steel_dark"]), "head", 0.004, 2, 0, False)
        # 盔耳（两侧铰链片，压平一些）
        for s in (1, -1):
            self.add(side_disc("hm_ear_%d" % s,
                               [(0.050, -0.008), (0.046, 0.014), (0.030, 0.024),
                                (0.012, 0.028)], 8, M["steel_dark"],
                               (s * 0.222, 0.014, 2.108), s), "head", 0.004, 2, 0, True)
        # 盔沿
        self.add(tube("hm_rim", [
            (1.812, 0, 0.010, 0.492, 0.468, 0.098),
            (1.858, 0, 0.010, 0.484, 0.460, 0.096),
        ], M["steel_dark"]), "head", 0.006, 2, 0, False)

        # 盔缨：前后向的鳍（队色四处之一），前陡后掠
        crest = [(0.200, 2.300), (0.186, 2.400), (0.136, 2.498), (0.046, 2.560),
                 (-0.048, 2.572), (-0.138, 2.526), (-0.198, 2.442), (-0.224, 2.352),
                 (-0.224, 2.292), (0.200, 2.292)]
        self.add(extrude("hm_crest", crest, "X", 0.092, (0.0, 0.0), M["team"]),
                 "head", 0.008, 2, 0, False)

    # ── 6. 盾（镜像之后才建）────────────────────────────────────────────────
    def shield(self):
        M = self.M
        out = []

        def put(ob, bevel=0.006, seg=2, sub=0, smooth=True):
            out.append((ob, "shield.L", bevel, seg, sub, smooth))
            return ob

        ph = math.pi / 16
        # 盾面：浅碟（队色最大一块）。中心用 20 mm 的小端面收口 —— 收成 r=0 的
        # 极点会在 remove_doubles 之后留下非流形边，法线就再也救不回来。
        put(rev_y("sh_face", SH_PROF, 16, M["team"], phase=ph), 0.004, 2, 0, True)
        # 铁包边（暗一档，把盾面框住）
        put(rev_y("sh_rim", [(SH_R - 0.048, -0.018), (SH_R, 0.004),
                             (SH_R - 0.002, 0.046), (SH_R - 0.046, 0.050)],
                  16, M["steel_dark"], closed=True, phase=ph), 0.005, 2, 0, True)
        # 金线（队色与包边之间的一道细圈）
        lr0, lr1 = 0.214, 0.242
        ly0, ly1 = sh_face_y(lr0), sh_face_y(lr1)
        put(rev_y("sh_line", [(lr0, ly0 - 0.008), (lr1, ly1 - 0.008),
                              (lr1, ly1 + 0.004), (lr0, ly0 + 0.004)],
                  16, M["team_trim"], closed=True, phase=ph), 0.003, 2, 0, False)
        # 中心铁凸 + 脐座
        put(rev_y("sh_boss", [(0.088, 0.024), (0.082, 0.056), (0.054, 0.080),
                              (0.016, 0.090)], 12, M["steel"]), 0.005, 2, 1, True)
        put(rev_y("sh_bosering", [(0.104, 0.022), (0.124, 0.030),
                                  (0.124, 0.041), (0.104, 0.034)],
                  12, M["steel_dark"], closed=True), 0.003, 1, 0, False)
        for i in range(4):
            a = math.pi * 2 * i / 4 + math.pi / 4
            put(box("sh_stud_%d" % i, (0.296 * math.cos(a), 0.040, 0.296 * math.sin(a)),
                    (0.032, 0.036, 0.032), M["gold"]), 0.004, 1, 0, False)
        # 盾背：竖板
        for i, px in enumerate((-0.196, -0.098, 0.0, 0.098, 0.196)):
            hw = 0.048
            hh = math.sqrt(max((SH_R - 0.040) ** 2 - (abs(px) + hw) ** 2, 0.0025))
            put(box("sh_plank_%d" % i, (px, -0.042, 0.0), (hw * 2, 0.024, hh * 2),
                    M["wood_warm"]), 0.004, 2, 0, False)
        # 两道臂带 + 握把（都插进小臂里，读作"绑在手上"）
        for i, zz in ((0, 0.088), (1, -0.088)):
            put(box("sh_strap_%d" % i, (0.0, -0.080, zz), (0.290, 0.070, 0.060),
                    M["earth"]), 0.005, 2, 0, False)
        put(box("sh_grip", (0.0, -0.090, 0.0), (0.070, 0.050, 0.150),
                M["wood_dark"]), 0.004, 1, 0, False)

        rot = Euler((0, 0, math.radians(SH_RZ)), "XYZ")
        for (ob, _b, _be, _sg, _su, _sm) in out:
            ob.location = Vector(SH_POS)
            ob.rotation_euler = rot
        return out

    # ── 7. 剑（镜像之后才建）───────────────────────────────────────────────
    def sword(self):
        M = self.M
        out = []

        def put(ob, bevel=0.005, seg=2, sub=0, smooth=False):
            out.append((ob, "weapon.R", bevel, seg, sub, smooth))
            return ob

        def blade_sec(w, t):
            return [(-w * 0.5, 0.0), (0.0, -t * 0.5), (w * 0.5, 0.0), (0.0, t * 0.5)]

        rows = []
        for (z, w, t) in ((-0.112, 0.092, 0.030), (-0.152, 0.086, 0.027),
                          (-0.360, 0.078, 0.023), (-0.560, 0.064, 0.018),
                          (-0.660, 0.044, 0.014), (-0.706, 0.022, 0.008),
                          (-0.736, 0.008, 0.004)):
            rows.append([(x, y, z) for (x, y) in blade_sec(w, t)])
        put(loft("sw_blade", rows, M["steel"]), 0.004, 2, 0, False)

        put(box("sw_guard", (0, 0, -0.100), (0.256, 0.066, 0.052), M["steel_dark"]),
            0.006, 2, 0, False)
        for s in (1, -1):
            put(box("sw_quillon_%d" % s, (s * 0.136, 0, -0.124), (0.060, 0.054, 0.066),
                    M["steel_dark"]), 0.005, 2, 0, False)
        put(box("sw_grip", (0, 0, 0.012), (0.058, 0.060, 0.198), M["wood_dark"]),
            0.008, 2, 1, True)
        for i, zz in enumerate((-0.040, 0.014, 0.068)):
            put(box("sw_wrap_%d" % i, (0, 0, zz), (0.066, 0.068, 0.020), M["iron"]),
                0.003, 1, 0, False)
        put(rev_y("sw_pommel", [(0.018, 0.114), (0.040, 0.118), (0.050, 0.148),
                                (0.032, 0.172), (0.014, 0.178)], 8, M["gold"]),
            0.004, 2, 0, True)

        rot = Euler((math.radians(SW_RX), math.radians(SW_RY), 0), "XYZ")
        for (ob, _b, _be, _sg, _su, _sm) in out:
            ob.location = Vector(SW_POS)
            ob.rotation_euler = rot
        return out

    # ── 8. 组装 / 收尾 ──────────────────────────────────────────────────────
    def build(self):
        self.legs()
        self.hips()
        self.torso()
        self.arms()
        self.head()
        return self

    def _mirror_body(self):
        """只镜像对称体，并且把 .L / .R 一起互换 —— 否则骨和几何会对调。"""
        body = []
        for (ob, bone, bev, seg, sub, sm) in self.items:
            me = ob.data
            for v in me.vertices:
                v.co.x = -v.co.x
            for p in me.polygons:
                p.flip()
            me.update()
            body.append((ob, _swap_side(bone), bev, seg, sub, sm))
        self.items = body

    def finalize(self, bevel=True, unwrap=False, join=True, rig=True):
        # ① 对称体镜像（盾 / 剑还没生成，镜像不可能把它们翻倍）
        self._mirror_body()
        # ② 倒角 / 细分：块面件只倒角，该圆的件才上细分
        # 低模档倒角只走 1 段：2 段倒角在 19k 面里占了一半，而 2.4 m 高的角色
        # 在手机上倒角只有 1–2 px，1 段看不出差别（建筑那套也是这个口径）。
        def _seg(sg):
            return sg if self.smooth else min(sg, 1)

        for (ob, bone, bev, seg, sub, sm) in self.items:
            L.finalize(ob, bevel=bev if bevel else 0.0, seg=_seg(seg),
                       sub=sub if self.smooth else 0, flat=not sm)
        # ③ 镜像之后才做盾与剑
        props = self.shield() + self.sword()
        for (ob, bone, bev, seg, sub, sm) in props:
            L.finalize(ob, bevel=bev if bevel else 0.0, seg=_seg(seg),
                       sub=sub if self.smooth else 0, flat=not sm)
        allit = self.items + props
        self.bones = {it[0].name: it[1] for it in allit}

        objs = [it[0] for it in allit]
        bpy.ops.object.select_all(action="DESELECT")
        for ob in objs:
            ob.select_set(True)
        bpy.context.view_layer.objects.active = objs[0]
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        bpy.ops.object.select_all(action="DESELECT")

        if not join:
            # 体检用：不合并、不绑骨，逐件检查（合并之后查不出穿模）
            return objs

        for (ob, bone, _b, _s, _u, _m) in allit:
            vg = ob.vertex_groups.new(name=bone)
            vg.add(list(range(len(ob.data.vertices))), 1.0, "REPLACE")

        out = L.join_by_material(objs, prefix="CH")
        if unwrap:
            L.smart_uv(out)
        if rig:
            self.rig = build_armature(out)
        return out


def build_armature(objs):
    """建骨架并把蒙皮挂上去（rest pose = 建模姿势）。"""
    arm = bpy.data.armatures.new("CH_Rig")
    arm_ob = bpy.data.objects.new("CH_Rig", arm)
    bpy.context.scene.collection.objects.link(arm_ob)
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = arm_ob
    arm_ob.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    for (name, head, tail, parent) in BONES:
        b = arm.edit_bones.new(name)
        b.head = Vector(head)
        b.tail = Vector(tail)
        b.use_connect = False
        if parent:
            b.parent = arm.edit_bones[parent]
    bpy.ops.object.mode_set(mode="OBJECT")
    arm_ob.show_in_front = True
    for ob in objs:
        ob.parent = arm_ob
        ob.matrix_parent_inverse = arm_ob.matrix_world.inverted()
        m = ob.modifiers.new("Armature", "ARMATURE")
        m.object = arm_ob
        m.use_vertex_groups = True
    bpy.ops.object.select_all(action="DESELECT")
    return arm_ob


def build(smooth=True, unwrap=False, bevel=True, level=0):
    m = Model(smooth, level).build()
    objs = m.finalize(bevel=bevel, unwrap=unwrap)
    return objs, L.stats(objs)
