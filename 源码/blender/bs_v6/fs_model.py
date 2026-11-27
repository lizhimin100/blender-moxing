"""
fs_model.py —— 折壳入口（The Shard Gate）**v2 · 巨壳残片**

v1 的四个问题（用户原话 → 改法）
    "外形太规律平整" → 等距折棱 + 等比缩放 = 帐篷。v2 改成一段**弧墙**：
                       顶边是斜的、破的，两端埋进土里，不再是一个完整的穹顶。
    "高高的，没有深度" → v1 10.1 m 高、正面 14 m 平墙。v2 压到 4.9 m，靠**纵深**：
                       门口到隧道尽头 5.2 m，中间夹一道内拱，正视读到 6 层明度。
    "门太靠内"         → 门扇立在拱洞前缘 0.8 m（v1 1.81 m），门套石凸出墙面 0.3 m。
    "门前横着一根骨头"  → 撑骨整根删掉。骨只做结构：肋骨从土里长出来埋进墙肩，
                       墙口一圈骨钉。**门前一块骨头都没有。**

v2 的一句话：**一片巨壳的残片，半埋在山里；帝国在它弧面上凿了一道门。**
  ① 主体是**一段弧墙**（约 132° 的壳片），不是穹顶：顶边一条斜的破口，
     两端低、中间高，两端直接埋进土里 —— "从地下冒出来"靠的就是这个埋。
  ② 墙后是**土山**（3.35 m 高），墙顶在中间高出山脊，两侧被山吃掉。
     俯视读到三层：石弧（亮） → 土山（暗） → 山后的黑。
  ③ 洞口是**穿透墙身**的拱洞：洞壁 = 墙的厚度，刷浅色；门套石沿拱线砌一圈。
  ④ 门扇在拱洞前缘，右扇开着 11°；门缝、拱顶上方都是黑的。
  ⑤ 前庭是**挖出来的**：两级踏步、两侧挡土石墙，人从院里抬头看门。

明度秩序（从外到内，6 层，这是"深度"的来源）
   土 0.28 → 墙 0.36 → 破口 0.52 → 门套 0.52 → 门扇 0.19 → 隧道 0.03
   极差 17 倍。俯视最亮的是墙顶破口，最暗的是洞口 —— 视线自动被吸进去。

组件化
   PARTS = 8 个方法，各自独立可建：Model(smooth).build(only=("door",)) 只出两扇门。
   所有体量从常量块推导：改 RX/RY/PHI0 换一段壳，改 PHI_M/ARCH_H 换一张嘴。
   骨 / 土山 / 门套都是纯函数式构件，可以整段搬给别的资产。

坐标：X 右、Y 前（+Y = 正面）、Z 上；原点在占地中心，z = 0 地面；交付前沿 X 镜像。
"""
import math

import bpy
from mathutils import Vector

import bslib as L
import dl_kit as K
import dl_parts as P
from bslib import box, beam, extrude, mesh_obj, revolve
from br_model import mirror_x

TAU = math.tau

# 失落帝国通用阵营色（定义在 dl_parts，三座共用）
TEAM_STYLE = P.LE_TEAM_STYLE

# ══ 1. 场地 ══════════════════════════════════════════════════════════════════
PAD_Z = 0.10                    # 土台
COURT_Z = 0.06                  # 前庭
COURT_X0, COURT_X1 = -3.40, 3.40
COURT_Y0, COURT_Y1 = 1.45, 3.95

# ══ 2. 壳片（一段弧墙）═══════════════════════════════════════════════════════
CX, CY = 0.0, -1.55
RX, RY = 5.05, 3.95             # 弧的外轮廓半轴
PHI0 = math.radians(96.0)       # 弧墙张角（±96°：两端沉进土山）
WALL0, WALL1 = 1.08, 0.84       # 墙厚（根 / 顶）
H_REF = 7.20                    # 收分参考高度
LEAN = 0.44                     # 墙整体后仰（顶往后倒）
PHI_M = math.radians(19.0)      # 洞口半角 → 净宽 3.29 m
SPRING = 1.30                   # 拱脚
ARCH_H = 1.62                   # 拱高（拱脚到拱心）

# 拱线：x 用 |sinφ|/sin(PHI_M) 归一，z 从拱脚往上（0–1）。尖拱，不是半圆。
ARCH_P = ((0.00, 1.000), (0.30, 0.975), (0.56, 0.905), (0.74, 0.775),
          (0.87, 0.585), (0.95, 0.345), (1.00, 0.030))

# 墙顶：一条斜的、破的线（角度°, 标高）
TOP_T = ((-96, 0.86), (-84, 1.55), (-74, 2.20), (-66, 2.62),
         (-56, 3.02), (-46, 3.44), (-36, 3.86), (-26, 4.18),
         (-14, 4.42), (-2, 4.54), (10, 4.44), (22, 4.10),
         (34, 3.62), (46, 3.06), (56, 2.55), (66, 2.28),
         (78, 1.90), (88, 1.30), (96, 0.82))

# 门（立在拱洞前缘）
DOOR_Y = CY + RY - 0.62         # 1.78 —— 只比墙面最前点退 0.62 m（墙厚的 57%）
DOOR_HINGE = 1.52
DOOR_T = 0.24

# 土山
HILL_Z = 3.35                   # 山脊
TUN_Y1 = -4.35                  # 隧道尽头


# ══ 工具 ═════════════════════════════════════════════════════════════════════
def h01(*args):
    x = 0.0
    for i, a in enumerate(args):
        x += (a + 1.7) * (12.9898 + i * 7.233)
    return (math.sin(x) * 43758.5453) % 1.0


def s_w(z):
    return max(0.05, 1.0 - (z / H_REF) ** 2) ** 0.32


def lean(z):
    return -LEAN * (z / 4.9) ** 1.7


def w_outer(phi, z, grow=0.0):
    s = s_w(z)
    return (CX + (RX * s + grow) * math.sin(phi),
            CY + (RY * s + grow) * math.cos(phi) + lean(z), z)


def w_inner(phi, z, grow=0.0):
    s = s_w(z)
    t = WALL0 + (WALL1 - WALL0) * min(1.0, z / 4.8)
    return (CX + (RX * s - t - grow) * math.sin(phi),
            CY + (RY * s - t - grow) * math.cos(phi) + lean(z), z)


def _interp(tab, deg):
    d = deg
    while d < -180.0:
        d += 360.0
    while d > 180.0:
        d -= 360.0
    for (d0, z0), (d1, z1) in zip(tab, tab[1:]):
        if d0 <= d <= d1:
            t = 0.0 if d1 == d0 else (d - d0) / (d1 - d0)
            return z0 + (z1 - z0) * t
    return tab[-1][1]


def z_top(phi):
    """墙顶：**阶梯**，不是一条平滑斜线。

    一段破墙的顶边是"砌体一块块塌掉"的台阶；写成平滑曲线会读成一顶帽子（踩过）。
    台阶高度从 -66° 到 +66° 一路往下，中间挖两个宽缺口（整块塌掉）。
    """
    z = _interp(TOP_T, math.degrees(phi))
    # 量化成 0.34 m 的台阶（只往下取，不往上 —— 塌只会变矮）
    step = 0.34
    z = step * math.floor(z / step) + 0.06
    for (a, d, w) in ((0.66, 0.52, 0.20), (-0.62, 0.38, 0.15)):
        z -= d * math.exp(-((phi - a) / w) ** 2)
    return z + 0.05 * (h01(round(phi, 3), 7.1) - 0.5)


def z_arch(phi):
    if abs(phi) > PHI_M:
        return 0.0
    u = abs(math.sin(phi)) / math.sin(PHI_M)
    for (u0, z0), (u1, z1) in zip(ARCH_P, ARCH_P[1:]):
        if u0 <= u <= u1:
            t = 0.0 if u1 == u0 else (u - u0) / (u1 - u0)
            return SPRING + ARCH_H * (z0 + (z1 - z0) * t)
    return SPRING + ARCH_H * ARCH_P[-1][1]


def phi_list():
    """不等距采样：口内密（拱线要准），墙身疏（块面要大）；±19° 必须落点。"""
    deg = [-96.0, -86.0, -76.0, -66.0, -54.0, -42.0, -32.0, -24.0]
    deg += [-15.0, -7.5, 0.0, 7.5, 15.0]
    deg += [19.0, 28.0, 38.0, 48.0, 58.0, 66.0, 76.0, 86.0, 96.0]
    return [math.radians(d) for d in deg]


PHI = phi_list()
NP = len(PHI)
ROWS = (0.0, 0.34, 0.68, 1.0)


def strip(name, pfun, zb, zt, mat):
    """一条 (φ, 高度) 的四边形带（墙的内外表面都走这一支）。"""
    verts, faces = [], []
    n = len(PHI)
    for i in range(n):
        for u in ROWS:
            verts.append(pfun(PHI[i], zb[i] + (zt[i] - zb[i]) * u))
    m = len(ROWS)
    for i in range(n - 1):
        for k in range(m - 1):
            faces.append((i * m + k, i * m + k + 1,
                          (i + 1) * m + k + 1, (i + 1) * m + k))
    return mesh_obj(name, verts, faces, mat)


def band(name, pa, pb, mat):
    n = len(pa)
    verts = list(pa) + list(pb)
    faces = [(i, i + 1, n + i + 1, n + i) for i in range(n - 1)]
    return mesh_obj(name, verts, faces, mat)


def bone(name, pts, radii, mat, sides=5, phase=0.0):
    pts = [Vector(p) for p in pts]
    rings = []
    for k, p in enumerate(pts):
        if k == 0:
            d = (pts[1] - pts[0]).normalized()
        elif k == len(pts) - 1:
            d = (pts[-1] - pts[-2]).normalized()
        else:
            d = (pts[k + 1] - pts[k - 1]).normalized()
        up = Vector((0, 0, 1)) if abs(d.z) < 0.92 else Vector((1, 0, 0))
        u = d.cross(up).normalized()
        v = u.cross(d).normalized()
        r = radii[k]
        rings.append([p + u * (r * math.cos(phase + TAU * i / sides))
                        + v * (r * math.sin(phase + TAU * i / sides))
                      for i in range(sides)])
    verts = [tuple(q) for ring in rings for q in ring]
    faces = []
    for k in range(len(rings) - 1):
        for i in range(sides):
            j = (i + 1) % sides
            faces.append((k * sides + i, k * sides + j,
                          (k + 1) * sides + j, (k + 1) * sides + i))
    faces.append(tuple(range(sides - 1, -1, -1)))
    base = (len(rings) - 1) * sides
    faces.append(tuple(base + i for i in range(sides)))
    return mesh_obj(name, verts, faces, mat)


def slab(name, a_in, a_out, b_in, b_out, n, depth, mat):
    n = Vector(n).normalized() * depth
    v = [a_in, a_out, b_out, b_in,
         tuple(Vector(a_in) - n), tuple(Vector(a_out) - n),
         tuple(Vector(b_out) - n), tuple(Vector(b_in) - n)]
    f = [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2),
         (2, 6, 7, 3), (3, 7, 4, 0)]
    return mesh_obj(name, v, f, mat)


def loft(name, foot, top, z0, z1, mat):
    """foot / top 两圈同点数的多边形 → 一个台地（山坡用，不是盒子）。"""
    n = len(foot)
    verts = [(x, y, z0) for (x, y) in foot] + [(x, y, z1) for (x, y) in top]
    faces = []
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, n + j, n + i))
    faces.append(tuple(range(n, 2 * n)))
    return mesh_obj(name, verts, faces, mat)


def merge(name, obs, mat):
    verts, faces = [], []
    for ob in obs:
        b = len(verts)
        verts.extend([tuple(v.co) for v in ob.data.vertices])
        faces.extend([tuple(b + i for i in p.vertices) for p in ob.data.polygons])
    for ob in list(obs):
        bpy.data.objects.remove(ob, do_unlink=True)
    return mesh_obj(name, verts, faces, mat)


def mirror_obj(ob):
    for v in ob.data.vertices:
        v.co.x = -v.co.x
    for p in ob.data.polygons:
        p.flip()
    ob.data.update()
    ob.location.x = -ob.location.x
    ob.rotation_euler.z = -ob.rotation_euler.z


# ══════════════════════════════════════════════════════════════════════════════
class Model:
    def __init__(self, smooth, unwrap=True):
        self.smooth = smooth
        self.unwrap = unwrap
        self.items = []
        self.loose = []
        self.M = L.all_materials()

    def add(self, ob, bevel=0.010, sub=0, seg=1):
        if ob is None:
            return None
        self.items.append((ob, bevel, sub, seg))
        return ob

    def add_loose(self, ob, bevel=0.006):
        if ob is None:
            return None
        self.loose.append((ob, bevel))
        return ob

    def put(self, obs, bevel=0.004):
        for ob in obs or ():
            self.add(ob, bevel)
        return obs

    # ── 1. 土台 ─────────────────────────────────────────────────────────────
    def pad(self):
        M = self.M
        pts = [(-4.55, 4.16), (-5.62, 2.30), (-5.72, -1.15), (-4.92, -4.15),
               (-2.55, -5.58), (2.40, -5.62), (4.95, -4.18), (5.68, -1.10),
               (5.52, 2.40), (4.48, 4.16), (1.60, 4.52), (-1.60, 4.52)]
        self.add(extrude("gd_pad", pts, "Z", PAD_Z, (0, 0), M["earth_dark"],
                         offset=PAD_Z * 0.5), 0.020)

    # ── 2. 土山：墙后一座山，墙的两端被它吃掉 ───────────────────────────────
    def ground(self):
        M = self.M

        def hill(name, cx, cy, rx, ry, hz, seed, mat=None):
            """三层缩放的土丘：脚 → 肩 → 顶。只有一圈会读成"平顶台地"（踩过）。"""
            n = 11
            rings = ((0.10, 1.00), (hz * 0.52, 0.84), (hz * 0.82, 0.58), (hz, 0.20))
            base = []
            for i in range(n):
                a = TAU * i / n
                base.append((cx + math.sin(a) * rx * (1.0 + 0.15 * h01(i, seed + 1)),
                             cy + math.cos(a) * ry * (1.0 + 0.15 * h01(i, seed + 2))))
            verts, faces = [], []
            for (z, sc) in rings:
                for i in range(n):
                    px = cx + (base[i][0] - cx) * sc
                    py = cy + (base[i][1] - cy) * sc
                    verts.append((px, py, z + 0.05 * (h01(i, z) - 0.5)))
            for r in range(len(rings) - 1):
                for i in range(n):
                    j = (i + 1) % n
                    a = r * n + i
                    b = r * n + j
                    faces.append((a, b, b + n, a + n))
            faces.append(tuple(range((len(rings) - 1) * n, len(rings) * n)))
            self.add(mesh_obj(name, verts, faces, mat or M["earth_dark"]), 0.020)

        # 左山 / 右山：把墙的两端埋掉
        hill("md_hill_l", -3.62, -2.85, 2.55, 2.45, 2.72, 21)
        hill("md_hill_r", 3.62, -2.85, 2.55, 2.45, 2.86, 23)
        # 后山：隧道正上方那块（比两侧高，成为画面的"背"）
        hill("md_hill_b", 0.0, -4.05, 2.85, 1.95, 3.22, 25)
        # 从土里拱出来的石头露头（三处）—— 大块棕色土坡必须被石头打断
        for (cx, cy, cz, sx, sy, sz, rx, ry, rz) in (
                (-4.55, -1.35, 1.55, 1.55, 1.05, 1.25, 0.22, 0.10, 0.34),
                (4.35, -2.55, 1.85, 1.30, 0.95, 1.15, -0.18, 0.14, -0.26),
                (2.05, -4.55, 2.35, 1.45, 1.10, 1.05, 0.30, -0.12, 0.18),
                (-1.60, -4.95, 2.20, 1.20, 0.90, 0.95, -0.24, 0.08, 0.42)):
            self.add(box("md_outcrop", (cx, cy, cz), (sx, sy, sz),
                         M["ancient_dark"], rot=(rx, ry, rz)), 0.014)
        # 隧道顶上压的一层土：做成一座**矮土脊**（盒子会在俯视里读成一块盖板）
        n = 10
        rings = ((2.96, 1.00), (3.16, 0.80), (3.30, 0.42))
        tv, tf = [], []
        for (z, sc) in rings:
            for i in range(n):
                a = TAU * i / n
                tv.append((math.sin(a) * 2.25 * sc * (1 + 0.08 * h01(i, 31)),
                           -1.55 + math.cos(a) * 3.05 * sc * (1 + 0.06 * h01(i, 33)),
                           z))
        for r in range(len(rings) - 1):
            for i in range(n):
                j = (i + 1) % n
                tf.append((r * n + i, r * n + j, (r + 1) * n + j, (r + 1) * n + i))
        tf.append(tuple(range((len(rings) - 1) * n, len(rings) * n)))
        self.add(mesh_obj("md_tun_top", tv, tf, M["earth_dark"]), 0.020)
        # 土脊上的三块石（不是草 —— 草在脊上会被判浮空）
        for (ox, oy, oz, sx, sy, sz, rz) in ((-0.72, -2.55, 3.30, 0.62, 0.48, 0.52, 0.38),
                                             (0.85, -1.25, 3.28, 0.54, 0.42, 0.47, -0.24),
                                             (-0.25, -0.20, 3.24, 0.44, 0.36, 0.41, 0.62)):
            self.add(box("md_ridge_rock", (ox, oy, oz), (sx, sy, sz),
                         M["ancient_dark"], rot=(0.08, 0.06, rz)), 0.006)
        # 前庭两侧的土翼
        for sgn in (-1, 1):
            edge = [(sgn * (COURT_X1 - 0.02), 1.30),
                    (sgn * (COURT_X1 + 0.04), 2.55),
                    (sgn * (COURT_X1 + 0.26), COURT_Y1 + 0.30)]
            v, f = [], []
            rr = (0.0, 0.44, 0.76, 1.0)
            for (x, y) in edge:
                for u in rr:
                    v.append((x + sgn * 1.15 * (u ** 0.85), y + 0.08 * u,
                              COURT_Z + (0.74 - COURT_Z) * (u ** 1.25)))
            for (x, y) in edge:
                v.append((x + sgn * 1.55, y + 0.16, PAD_Z + 0.01))
            m2 = len(rr)
            for i in range(len(edge) - 1):
                for k in range(m2 - 1):
                    f.append((i * m2 + k, i * m2 + k + 1,
                              (i + 1) * m2 + k + 1, (i + 1) * m2 + k))
            base = len(edge) * m2
            for i in range(len(edge) - 1):
                f.append((i * m2, base + i, base + i + 1, (i + 1) * m2))
            self.add(mesh_obj("md_wing", v, f, M["earth"]), 0.012)
            # 挡土石墙
            self.add(beam("st_retain", (edge[0][0], edge[0][1], 0.47),
                          (edge[-1][0], edge[-1][1], 0.47), 0.40, 0.92,
                          M["ancient_dark"]), 0.012)
            self.add(beam("st_retain_cap", (edge[0][0], edge[0][1], 0.95),
                          (edge[-1][0], edge[-1][1], 0.95), 0.48, 0.10,
                          M["ancient_pale"]), 0.008)
        # 前庭地面
        court = [(COURT_X0, COURT_Y1), (COURT_X1, COURT_Y1),
                 (COURT_X1 - 0.20, COURT_Y0), (0.0, COURT_Y0 - 0.18),
                 (COURT_X0 + 0.20, COURT_Y0)]
        self.add(extrude("md_court", court, "Z", COURT_Z, (0, 0), M["paving"],
                         offset=COURT_Z * 0.5), 0.012)
        # 山坡上的草簇与碎石（俯视时给大块土坡一点"皮"）
        for (x, y, z, sc, e) in ((-4.05, -5.05, PAD_Z, 0.26, 951),
                                 (-5.45, -1.55, PAD_Z, 0.24, 953),
                                 (4.15, -5.15, PAD_Z, 0.26, 955),
                                 (5.45, -1.35, PAD_Z, 0.22, 957),
                                 (-1.05, -5.60, PAD_Z, 0.24, 959),
                                 (1.85, -5.48, PAD_Z, 0.22, 961)):
            self.put(K.grass("tuft_h", x, y, z, sc, 5, seed=e,
                             mat=M["moss_dark"]), 0.001)
        self.put(K.stones("md_rock", -4.75, -3.60, PAD_Z, 3, 0.55, 0.22,
                          (M["ancient_dark"],), seed=963), 0.006)
        self.put(K.stones("md_rock", 4.45, -3.85, PAD_Z, 3, 0.55, 0.20,
                          (M["ancient_dark"], M["ancient"]), seed=965), 0.006)

        # 坡脚碎石
        self.put(K.stones("gd_stone", -4.95, 2.15, PAD_Z, 4, 0.55, 0.30,
                          (M["ancient_dark"], M["ancient"]), seed=701), 0.008)
        self.put(K.stones("gd_stone", 4.85, 1.75, PAD_Z, 4, 0.55, 0.28,
                          (M["ancient"], M["ancient_dark"]), seed=703), 0.008)
        self.put(K.stones("gd_stone", -0.95, -4.55, PAD_Z, 3, 0.75, 0.24,
                          (M["ancient_dark"],), seed=707), 0.006)

    # ── 3. 墙：外表面 / 内表面 / 顶边 / 拱洞 / 两端断面 ─────────────────────
    def shell(self):
        M = self.M
        zb = [z_arch(p) for p in PHI]
        zt = [z_top(p) for p in PHI]

        self.add(strip("sh_wall", w_outer, zb, zt, M["ancient"]), 0.014)
        self.add(strip("cv_wall", w_inner, [0.02] * NP, zt, M["void"]), 0.004)

        # 顶边：墙的断面（整条斜的浅色带 —— 俯视最亮的一条线）
        pa = [w_outer(PHI[i], zt[i]) for i in range(NP)]
        pb = [w_inner(PHI[i], zt[i] - 0.02) for i in range(NP)]
        self.add(band("sh_topband", pa, pb, M["ancient_pale"]), 0.010)

        # 两端：墙在土里断掉的断面（每端一片竖的浅色梯形）
        for sgn in (-1, 1):
            i = 0 if sgn < 0 else NP - 1
            p = PHI[i]
            a0, a1 = w_outer(p, PAD_Z - 0.02), w_outer(p, zt[i])
            b0, b1 = w_inner(p, PAD_Z - 0.02), w_inner(p, zt[i])
            self.add(mesh_obj("sh_end", [a0, a1, b1, b0], [(0, 1, 2, 3)],
                              M["ancient_pale"]), 0.008)

        # 拱洞洞壁（墙的断面）
        mi = [i for i in range(NP) if abs(math.degrees(PHI[i])) <= 19.01]
        mi.sort()
        ra = [w_outer(PHI[i], max(0.0, z_arch(PHI[i]) - 0.02)) for i in mi]
        rb = [w_inner(PHI[i], max(0.0, z_arch(PHI[i]) - 0.02)) for i in mi]
        self.add(band("sh_soffit", ra, rb, M["ancient_pale"]), 0.010)
        # 门颊
        for sgn in (-1, 1):
            i = mi[0] if sgn < 0 else mi[-1]
            p = PHI[i]
            a0, a1 = w_outer(p, 0.02), w_outer(p, SPRING)
            b0, b1 = w_inner(p, 0.02), w_inner(p, SPRING)
            self.add(mesh_obj("sh_jambface", [a0, a1, b1, b0], [(0, 1, 2, 3)],
                              M["ancient_pale"]), 0.008)

        # 墙面上的竖向扶壁：四道，把 10 m 的弧面切成几段
        for (pd, h0, h1, wd, dep) in ((-0.86, 0.10, 3.05, 0.44, 0.20),
                                      (0.84, 0.10, 2.90, 0.40, 0.18),
                                      (-0.36, 0.10, 4.05, 0.34, 0.14),
                                      (0.38, 0.10, 3.95, 0.32, 0.13)):
            i = min(range(NP), key=lambda q: abs(PHI[q] - pd))
            p0 = Vector(w_outer(PHI[i], h0))
            p1 = Vector(w_outer(PHI[i], h1))
            nrm = Vector((p0.x - CX, p0.y - CY, 0)).normalized()
            c = (p0 + p1) * 0.5 + nrm * (dep * 0.5)
            self.add(box("sh_butt", tuple(c), (wd, dep, (p1 - p0).length),
                         M["ancient"], rot=(0, 0, math.atan2(nrm.x, nrm.y))),
                     0.010)

        # 墙面砌缝：两道通长的暗线（只在洞口两侧，不跨洞）—— 让 10 m 的弧面有"砌"的证据
        for zc in (2.02, 3.34):
            for i in range(NP - 1):
                if abs(math.degrees(PHI[i])) < 21.0 or abs(math.degrees(PHI[i + 1])) < 21.0:
                    continue
                if z_top(PHI[i]) < zc + 0.20 or z_top(PHI[i + 1]) < zc + 0.20:
                    continue
                zz = zc + 0.012 * i                # 每段抬 12 mm：砌缝微微上斜，也不共面
                a = Vector(w_outer(PHI[i], zz, 0.03))
                b = Vector(w_outer(PHI[i + 1], zz, 0.03))
                self.add(beam("sh_course", tuple(a), tuple(b), 0.11, 0.055,
                              M["ancient_dark"]), 0.002)

        # 墙面裂缝（两道）
        for pd in (0.22, -1.62):
            i = min(range(NP), key=lambda q: abs(PHI[q] - pd))
            p = w_outer(PHI[i], 2.15)
            nrm = Vector((p[0] - CX, p[1] - CY, 0)).normalized()
            self.add(box("sh_crack", (p[0], p[1], 2.75), (0.07, 0.09, 2.20),
                         M["ancient_dark"],
                         rot=(0, 0, math.atan2(nrm.x, nrm.y))), 0.002)

        # 土沁环：贴山脊往上 0.34 m 的深色带
        for i in range(NP - 1):
            q = [w_outer(PHI[i], 1.05, 0.025), w_outer(PHI[i], 1.39, 0.025),
                 w_outer(PHI[i + 1], 1.39, 0.025), w_outer(PHI[i + 1], 1.05, 0.025)]
            self.add(mesh_obj("sh_soil", q, [(0, 1, 2, 3)], M["ancient_dark"]),
                     0.003)

        # 墙顶的碎壳片：三片，斜插在顶边上（不挡视线，只破轮廓）
        for (pd, hh, wd, tl) in ((-2.05, 1.05, 1.35, 0.30), (0.55, 0.90, 1.10, -0.22),
                                 (1.62, 0.72, 0.85, 0.18)):
            i = min(range(NP), key=lambda q: abs(PHI[q] - pd))
            p = w_outer(PHI[i], z_top(PHI[i]) - 0.35)
            nrm = Vector((p[0] - CX, p[1] - CY, 0)).normalized()
            self.add(box("sh_shard", (p[0] + nrm.x * 0.20, p[1] + nrm.y * 0.20,
                                      z_top(PHI[i]) + hh * 0.26),
                         (wd, 0.26, hh), M["ancient"],
                         rot=(0.16, tl, math.atan2(nrm.x, nrm.y))), 0.012)

        # 墙脚矮护墙：跟着弧线走，断成三截（给正立面加一层，也掩住墙与土的接缝）
        for (a0, a1, hh) in ((-58.0, -33.0, 0.62), (-27.0, -1.0, 0.50),
                             (6.0, 33.0, 0.56), (40.0, 60.0, 0.44)):
            pts = []
            for k in range(7):
                a = math.radians(a0 + (a1 - a0) * k / 6.0)
                p = w_outer(a, 0.10, 0.62)
                pts.append((p[0], p[1], 0.10))
            for k in range(7):
                a = math.radians(a0 + (a1 - a0) * k / 6.0)
                p = w_outer(a, 0.10, 0.50)
                pts.append((p[0], p[1], hh))
            n = 7
            verts = pts
            faces = []
            for k in range(n - 1):
                faces.append((k, k + 1, n + k + 1, n + k))          # 外面
                faces.append((n + k, n + k + 1, k + 1, k))          # 内面
            faces.append((0, n, n + 1, 1))
            faces.append((n - 2, 2 * n - 2, 2 * n - 1, n - 1))
            self.add(mesh_obj("sh_parapet", verts, faces, M["ancient"]), 0.010)

        # 墙根的落石
        for (cx, cy, sx, sy, sz, rx, rz, mat) in (
                (4.62, -0.25, 1.28, 0.42, 1.46, 0.30, 0.16, M["ancient"]),
                (-4.72, 0.05, 1.16, 0.40, 1.30, 0.26, -0.26, M["ancient_dark"]),
                (-3.65, -3.25, 1.00, 0.36, 1.10, 0.22, -0.10, M["ancient"])):
            cz = PAD_Z + (sz * 0.5) * math.cos(rx) + (sy * 0.5) * math.sin(rx)
            self.add(box("sh_fall", (cx, cy, cz), (sx, sy, sz), mat,
                         rot=(rx, 0.07, rz)), 0.012)

    # ── 4. 门套：沿拱线砌一圈定门石 ─────────────────────────────────────────
    def portal(self):
        M = self.M
        N = 44
        pts = []
        for k in range(N + 1):
            u = -1.0 + 2.0 * k / N
            phi = math.asin(max(-1.0, min(1.0, u * math.sin(PHI_M))))
            p = Vector(w_outer(phi, max(0.0, z_arch(phi) - 0.05)))
            nn = Vector((p.x - CX, p.y - CY, 0)).normalized()
            pts.append((p, nn))
        outs = []
        for k in range(N + 1):
            a = pts[max(0, k - 1)][0]
            b = pts[min(N, k + 1)][0]
            t = (b - a)
            t = t.normalized() if t.length > 1e-6 else Vector((0, 1, 0))
            o = t.cross(Vector((0, 1, 0)))
            outs.append(o.normalized() if o.length > 1e-6 else Vector((0, 0, 1)))
        G = 11
        for g in range(G):
            k0 = int(round(g * N / G))
            k1 = int(round((g + 1) * N / G))
            if k1 - k0 < 1:
                continue
            w = 0.50
            A, B = [], []
            for k in range(k0, k1 + 1):
                p, nn = pts[k]
                o = outs[k]
                t = outs[k].cross(Vector((0, 1, 0))).normalized() * 0.028
                A.append(tuple(p + t))
                B.append(tuple(p + o * w + t))
            n = len(A)
            A2 = [tuple(Vector(A[i]) - pts[k0 + i][1] * 0.36) for i in range(n)]
            B2 = [tuple(Vector(B[i]) - pts[k0 + i][1] * 0.36) for i in range(n)]
            verts = A + B + A2 + B2
            faces = []
            for i in range(n - 1):
                faces.append((i, i + 1, n + i + 1, n + i))
                faces.append((3 * n + i, 3 * n + i + 1, 2 * n + i + 1, 2 * n + i))
                faces.append((2 * n + i, 2 * n + i + 1, n + i + 1, n + i))
                faces.append((i, i + 1, 3 * n + i + 1, 3 * n + i))
            faces.append((0, n, 3 * n, 2 * n))
            faces.append((n - 1, 2 * n - 1, 4 * n - 1, 3 * n - 1))
            self.add(mesh_obj("pt_arch", verts, faces, M["ancient_pale"]), 0.010)
        # 拱心石
        km = N // 2
        p, nn = pts[km]
        o = outs[km]
        t = outs[km].cross(Vector((0, 1, 0))).normalized() * 0.30
        a = p + o * 0.04
        b = p + o * 0.56
        self.add(slab("pt_key", tuple(a - t), tuple(b - t), tuple(b + t),
                      tuple(a + t), nn, 0.42, M["ancient_pale"]), 0.010)
        # ── 方形门楼：两墩 + 过梁 + 檐口 + 三块残垛 ──────────────────────
        for sgn in (-1, 1):
            self.add(box("pt_pier", (sgn * 2.02, 2.24, 1.56),
                         (0.92, 0.86, 3.12), M["ancient_pale"]), 0.012)
            self.add(box("pt_pier_cap", (sgn * 2.02, 2.24, 3.16),
                         (1.04, 0.96, 0.14), M["ancient"]), 0.008)
            # 墩脚的护脚（比墩宽 6 cm，压住地缝）
            self.add(box("pt_pier_foot", (sgn * 2.02, 2.24, 0.24),
                         (1.06, 1.00, 0.30), M["ancient_dark"]), 0.008)
        self.add(box("pt_lintel", (0, 2.24, 3.34), (5.02, 0.88, 0.50),
                     M["ancient_pale"]), 0.012)
        self.add(box("pt_cornice", (0, 2.24, 3.64), (5.52, 1.06, 0.16),
                     M["ancient"]), 0.008)
        # 檐口顶面一条队色漆线（水平面 —— 俯视时唯一一条队色）
        self.add(box("pt_cornice_team", (0, 2.42, 3.733), (5.04, 0.46, 0.026),
                     M["team"]), 0.002)
        # 三块残垛（只留中间一块是正的，两边一高一低）
        for (mx, mh, mz) in ((-1.95, 0.42, 0.21), (0.0, 0.62, 0.31),
                             (1.90, 0.30, 0.15)):
            self.add(box("pt_merlon", (mx, 2.24, 3.74 + mz),
                         (0.66, 0.80, mh), M["ancient_pale"]), 0.008)
        # 队色只留两道：檐口顶面一条漆线（上面已做）+ 门扇一道横带。
        # 试过在门楣挂垂布，2 m 宽的蓝布把门压成一块广告牌，已删。
        # 门前一级踏步（院 0.06 → 基座 0.47，一级 0.24，分两段）
        self.add(box("pt_step", (0, 2.92, 0.17), (3.52, 0.46, 0.22),
                     M["ancient"]), 0.010)
        self.add(box("pt_step2", (0, 3.24, 0.10), (3.20, 0.30, 0.09),
                     M["ancient_dark"]), 0.006)
        # 门楼的基座暗带（把白的门楼"坐"到地上）+ 两块崩角
        self.add(box("pt_plinth", (0, 2.24, 0.27), (5.10, 0.94, 0.40),
                     M["ancient_dark"]), 0.008)
        for (cx, cy, cz, sx, sy, sz, rz) in ((-2.28, 2.60, 3.62, 0.34, 0.36, 0.20, 0.4),
                                             (2.42, 2.22, 3.40, 0.26, 0.30, 0.16, -0.3)):
            self.add(box("pt_chip", (cx, cy, cz), (sx, sy, sz), M["ancient"],
                         rot=(0.2, 0.3, rz)), 0.006)
        # 门颊石
        for sgn in (-1, 1):
            for j in range(2):
                z0 = 0.10 + j * 0.62
                p = Vector(w_outer(sgn * PHI_M, z0 + 0.31))
                nrm = Vector((p.x - CX, p.y - CY, 0)).normalized()
                t = Vector((-nrm.y, nrm.x, 0)).normalized() * 0.35
                a = p - t - Vector((0, 0, 0.30))
                b = p + t + Vector((0, 0, 0.30))
                self.add(slab("pt_jamb", tuple(a), tuple(a + nrm * 0.36),
                              tuple(b + nrm * 0.36), tuple(b), nrm, 0.006,
                              M["ancient_pale"] if j == 0 else M["ancient"]),
                         0.008)

    # ── 5. 门 ───────────────────────────────────────────────────────────────
    def door(self):
        M = self.M
        prof = [(-DOOR_HINGE, 0.0), (-0.04, 0.0), (-0.04, 2.06),
                (-0.34, 2.04), (-0.70, 1.97), (-1.04, 1.83),
                (-1.32, 1.58), (-DOOR_HINGE, 1.22)]
        for sgn, name, ajar in ((1, "dr_leaf_a", math.radians(-11.0)),
                                (-1, "dr_leaf_b", 0.0)):
            p = [(sgn * x, z) for (x, z) in prof]
            if sgn < 0:
                p = p[::-1]
            parts = [extrude(name, p, "Y", DOOR_T, (0, 0), M["door_stone"])]
            for x in (0.46, 1.08):
                parts.append(box(name + "_rib", (sgn * -x, DOOR_T * 0.5 + 0.018, 0.96),
                                 (0.10, 0.08, 1.66), M["door_stone"]))
            parts.append(box(name + "_band", (sgn * -0.78,
                                              DOOR_T * 0.5 + 0.016, 1.26),
                             (1.32, 0.07, 0.12), M["door_stone"]))
            for z in (0.42, 0.92, 1.52):
                parts.append(box(name + "_stud", (sgn * -0.18,
                                                  DOOR_T * 0.5 + 0.030, z),
                                 (0.10, 0.06, 0.10), M["door_stone"]))
            parts.append(box(name + "_team", (sgn * -0.80,
                                              DOOR_T * 0.5 + 0.026, 0.94),
                             (1.38, 0.045, 0.30), M["team"]))
            leaf = merge(name, parts, M["door_stone"])
            leaf.location = (sgn * DOOR_HINGE, DOOR_Y, 0.50)
            leaf.rotation_euler = (0.0, 0.0, sgn * ajar)
            self.add_loose(leaf, 0.008)
        self.add(box("st_thresh", (0, DOOR_Y + 0.06, 0.44), (3.30, 0.84, 0.16),
                     M["ancient_pale"]), 0.010)
        for sgn in (-1, 1):
            self.add(box("st_pivot", (sgn * (DOOR_HINGE + 0.06), DOOR_Y, 0.60),
                         (0.30, 0.40, 0.28), M["ancient_dark"]), 0.008)

    # ── 6. 隧道：四级下沉 + 内拱 + 深处一线暖橙 + 断链 ──────────────────────
    def cave(self):
        M = self.M
        for sgn in (-1, 1):
            self.add(box("cv_side", (sgn * 1.72, -1.52, 1.54), (0.24, 5.60, 2.84),
                         M["void"]), 0.004)
        self.add(box("cv_back", (0, TUN_Y1 + 0.10, 1.50), (3.60, 0.24, 2.74),
                     M["void"]), 0.004)
        self.add(box("cv_ceil", (0, -1.52, 2.945), (3.56, 5.60, 0.19),
                     M["void"]), 0.004)
        fl = [(-1.80, 0.20), (1.80, 0.20), (1.72, TUN_Y1), (-1.72, TUN_Y1)]
        self.add(extrude("cv_floor", fl, "Z", 0.12, (0, 0), M["ancient_dark"],
                         offset=0.16), 0.006)
        for i, (yy, zt) in enumerate(((DOOR_Y + 0.08, 0.50), (DOOR_Y - 0.42, 0.39),
                                      (DOOR_Y - 0.92, 0.28), (DOOR_Y - 1.42, 0.17))):
            self.add(box("cv_step", (0, yy - 0.25, zt * 0.5 + 0.02),
                         (3.20 - i * 0.14, 0.52, zt + 0.04),
                         M["ancient_dark"]), 0.006)
            self.add(box("cv_step_nose", (0, yy - 0.505, zt - 0.035),
                         (3.16 - i * 0.14, 0.06, 0.045), M["ancient_pale"]),
                     0.002)
        rib = [(1.92 * math.cos(math.pi - math.pi * k / 8.0), -0.05,
                0.10 + 1.92 * math.sin(math.pi - math.pi * k / 8.0))
               for k in range(9)]
        for k in range(8):
            self.add(beam("cv_rib", rib[k], rib[k + 1], 0.34, 0.26,
                          M["ancient"]), 0.008)
        self.add(box("cv_ember", (0.20, TUN_Y1 + 0.42, 0.24), (1.22, 0.05, 0.065),
                     M["depth_glow"]), 0.0)
        self.add(box("cv_chain_pin", (-1.18, DOOR_Y - 0.02, 3.02),
                     (0.18, 0.16, 0.16), M["ancient_dark"]), 0.004)
        for i in range(12):
            z = 2.94 - 0.135 * i
            if z < 0.95:
                break
            sz = (0.055, 0.045, 0.150) if i % 2 == 0 else (0.045, 0.055, 0.150)
            self.add(box("cv_chain", (-1.18 + 0.004 * i, DOOR_Y - 0.02, z), sz,
                         M["bronze_dark"], rot=(0, 0, 0.12 * i)), 0.002)

    # ── 7. 骨：肋骨 / 骨钉 / 骨刺 / 碎骨（全部半埋，没有一根挡门）────────────
    def bones(self):
        M = self.M
        for k, (pts, rr) in enumerate((
                ([(4.12, 1.30, 0.30), (4.78, 0.95, 0.82), (4.68, 0.34, 1.58),
                  (4.30, -0.16, 2.18)], (0.245, 0.215, 0.170, 0.110)),
                ([(5.05, 0.20, 0.26), (5.30, -0.45, 0.78), (5.00, -1.12, 1.44)],
                 (0.195, 0.165, 0.095)),
                ([(-4.45, 1.05, 0.27), (-4.95, 0.42, 0.90), (-4.66, -0.24, 1.86)],
                 (0.210, 0.180, 0.100)))):
            self.add(bone("bn_rib", pts, rr, M["bone"], sides=5,
                          phase=0.4 + 0.5 * k), 0.008)
            m = len(pts) // 2
            q = Vector(pts[m])
            d = (Vector(pts[m + 1]) - Vector(pts[m - 1])).normalized()
            self.add(bone("bn_rib_knob", [tuple(q - d * 0.11), tuple(q + d * 0.11)],
                          [rr[m] * 1.28, rr[m] * 1.14], M["bone_dark"], sides=5),
                     0.006)

        for k, (pd, tl) in enumerate(((-2.60, 0.16), (-1.75, -0.10), (-0.98, 0.22),
                                      (0.88, -0.16), (1.62, 0.12), (2.32, -0.06))):
            i = min(range(NP), key=lambda q: abs(PHI[q] - pd))
            p = Vector(w_outer(PHI[i], z_top(PHI[i]) - 0.18))
            nrm = Vector((p.x - CX, p.y - CY, 0)).normalized()
            up = Vector((0.0, 0.0, 1.0))
            a = p - nrm * 0.16
            b = p + nrm * 0.18 + up * (0.24 + tl)
            self.add(bone("bn_peg", [tuple(a), tuple(b)],
                          [0.105, 0.058], M["bone"], sides=5, phase=0.2 * k),
                     0.006)

        self.add(bone("bn_spike", [(2.02, -2.62, 3.30), (2.46, -3.06, 4.02),
                                   (2.72, -3.40, 4.52)],
                      [0.30, 0.215, 0.070], M["bone"], sides=5, phase=0.3), 0.008)
        self.add(bone("bn_callus", [(2.78, -2.92, 3.40), (2.42, -2.58, 3.52)],
                      [0.12, 0.085], M["bone_dark"], sides=5), 0.006)

        for (pts, rr) in (
                ([(-4.92, 3.62, PAD_Z + 0.07), (-4.28, 4.02, PAD_Z + 0.09)],
                 (0.085, 0.060)),
                ([(4.30, -3.72, PAD_Z + 0.06), (4.88, -3.25, PAD_Z + 0.07)],
                 (0.072, 0.050))):
            self.add(bone("bn_drop", pts, rr, M["bone_dark"], sides=5), 0.006)

    # ── 8. 道具 ─────────────────────────────────────────────────────────────
    def props(self):
        M = self.M
        # 右前：木箱 + 小箱 + 木桶（三件一组，读成"远征队在这里扎了营"）
        self.add(box("pro_crate", (2.72, 3.62, COURT_Z + 0.26), (0.62, 0.54, 0.52),
                     M["wood_warm"]), 0.006)
        for (dx, dy) in ((-0.27, -0.23), (0.27, -0.23), (-0.27, 0.23), (0.27, 0.23)):
            self.add(box("pro_crate_rib", (2.72 + dx, 3.62 + dy, COURT_Z + 0.26),
                         (0.09, 0.09, 0.56), M["wood_dark"]), 0.003)
        self.add(box("pro_crate_lid", (2.72, 3.62, COURT_Z + 0.525),
                     (0.66, 0.58, 0.05), M["wood_dark"]), 0.003)
        self.add(box("pro_box", (2.62, 3.44, COURT_Z + 0.19), (0.40, 0.34, 0.36),
                     M["wood_mid"]), 0.005)
        self.add(box("pro_box_lid", (2.62, 3.44, COURT_Z + 0.372),
                     (0.42, 0.36, 0.04), M["wood_dark"]), 0.003)
        # 斜靠的两块木板（木桶的箍与箱面会被判共面，索性换掉）
        self.add(box("pro_plank", (3.20, 2.72, COURT_Z + 0.44), (0.26, 0.07, 0.86),
                     M["wood_mid"], rot=(0.18, 0.06, 0.30)), 0.004)
        self.add(box("pro_plank2", (3.04, 2.52, COURT_Z + 0.34), (0.22, 0.06, 0.66),
                     M["wood_dark"], rot=(0.24, -0.04, 0.52)), 0.004)
        # 火盆：压住右前的冷灰（暖点只此一处）
        self.add(box("pro_braz_base", (-3.02, 2.58, COURT_Z + 0.14),
                     (0.38, 0.38, 0.28), M["ancient_dark"]), 0.006)
        self.add(revolve("pro_braz_bowl", [(0.09, 0.0), (0.26, 0.04),
                                           (0.30, 0.13), (0.26, 0.17),
                                           (0.09, 0.17)], 8,
                         (-3.02, 2.58, COURT_Z + 0.27), M["bronze_dark"]), 0.004)
        self.put(K.embers("pro_braz_ember", -3.02, 2.58, COURT_Z + 0.44, 4, 0.15,
                          seed=811), 0.002)
        self.put(K.flame("pro_braz_flame", -3.02, 2.58, COURT_Z + 0.44, 0.36, 0.15,
                         seed=813), 0.002)
        # 左前：两根塌柱鼓 + 一块断石
        for (px, py, rz) in ((-2.58, 3.46, 0.34),):
            ob = revolve("pro_drum", [(0.00, -0.36), (0.38, -0.36),
                                      (0.38, 0.36), (0.00, 0.36)], 8, (0, 0, 0),
                         M["ancient"])
            ob.rotation_euler = (0, math.pi / 2, rz)
            ob.location = (px, py, COURT_Z + 0.40)
            self.add(ob, 0.010)
        self.add(box("pro_block", (-2.55, 3.68, COURT_Z + 0.16),
                     (0.78, 0.56, 0.34), M["ancient_pale"],
                     rot=(0.04, 0.10, 0.36)), 0.010)
        # 旗：队色的唯一一处（立在左前土台上）
        px, py = -4.98, 3.22
        self.add(box("pro_pole", (px, py, PAD_Z + 1.44), (0.085, 0.085, 2.88),
                     M["wood_dark"]), 0.003)
        self.add(box("pro_finial", (px, py, PAD_Z + 2.90), (0.14, 0.14, 0.14),
                     M["bronze"]), 0.003)
        self.add(box("pro_bar", (px, py + 0.46, PAD_Z + 2.72),
                     (0.062, 0.92, 0.062), M["wood_dark"]), 0.003)
        prof = [(-0.42, 0.0), (0.42, 0.0), (0.42, -1.24), (0.12, -1.56),
                (0.0, -1.32), (-0.12, -1.56), (-0.42, -1.24)]
        cl = extrude("pro_cloth", prof, "Y", 0.034, (0, 0), M["team"])
        cl.location = (px, py + 0.55, PAD_Z + 2.68)
        self.add(cl, 0.004)
        self.add(box("pro_cloth_trim", (px, py + 0.57, PAD_Z + 2.54),
                     (0.80, 0.045, 0.05), M["team_trim"]), 0.002)
        # 院里碎石
        self.put(K.stones("pro_rubble", -2.28, 3.98, COURT_Z, 4, 0.44, 0.18,
                          (M["ancient"], M["ancient_dark"]), seed=821), 0.006)
        self.put(K.stones("pro_rubble", 2.25, 3.90, COURT_Z, 3, 0.36, 0.15,
                          (M["ancient_dark"],), seed=823), 0.005)
        # 草（全部落在土台上）
        for (x, y, s, e) in ((-5.10, 3.55, 0.30, 901), (-5.28, 1.45, 0.26, 903),
                             (5.05, 3.50, 0.28, 905), (5.15, 1.20, 0.24, 907),
                             (-3.05, 4.02, 0.22, 909), (3.18, 3.98, 0.24, 911),
                             (-4.75, 2.55, 0.20, 913), (4.90, 2.05, 0.22, 915),
                             (1.05, -5.15, 0.26, 917), (-2.25, -5.10, 0.22, 919)):
            self.put(K.grass("tuft", x, y, PAD_Z, s, 5, seed=e,
                             mat=M["moss_dark"]), 0.001)
        # 苔：贴在墙脚土线上
        for (a, w, h) in ((-2.42, 1.10, 0.32), (-0.52, 0.82, 0.24),
                          (1.62, 1.02, 0.28), (2.72, 0.70, 0.20)):
            i = min(range(NP), key=lambda q: abs(PHI[q] - a))
            p = w_outer(PHI[i], 0.92)
            nrm = Vector((p[0] - CX, p[1] - CY, 0)).normalized()
            self.add(box("pro_moss", (p[0] + nrm.x * 0.02,
                                      p[1] + nrm.y * 0.02, 0.92),
                         (w, 0.05, h), M["moss_dark"],
                         rot=(0, 0, math.atan2(nrm.x, nrm.y))), 0.003)

    # ── 组装 / 收尾 ─────────────────────────────────────────────────────────
    PARTS = ("pad", "ground", "shell", "portal", "door", "cave", "bones", "props")

    def build(self, only=None):
        for name in (only or self.PARTS):
            getattr(self, name)()
        # 阵营色覆盖必须在所有零件建完之后（dl_kit 会重刷材质）
        P.apply_team_style(TEAM_STYLE)
        return self

    def finalize(self, bevel=True):
        flat_pref = ("sh_wall", "sh_soffit", "sh_topband", "sh_end", "sh_jambface",
                     "sh_crack", "sh_soil", "sh_shard", "cv_", "md_", "gd_",
                     "st_", "pt_", "pro_moss")
        cc_ok = ("bn_", "pro_barrel", "pro_drum", "pro_braz", "tuft",
                 "flame", "pro_crate")
        for (ob, bev, sub, seg) in self.items:
            co = ob.data.vertices
            if not len(co):
                continue
            dims = [max(v.co[i] for v in co) - min(v.co[i] for v in co)
                    for i in range(3)]
            n = ob.name
            is_flat = n.startswith(flat_pref)
            if self.smooth:
                chunky = min(dims) >= 0.09 and dims[0] * dims[1] * dims[2] >= 0.02
                cc = 1 if (chunky and n.startswith(cc_ok)) else 0
                L.finalize(ob, bevel=min(max(bev, 0.003), 0.014),
                           seg=1 if is_flat else 2, sub=cc, flat=is_flat)
            else:
                b = 0.0 if (not bevel or max(dims) < 1.10 or bev < 0.006) else bev
                L.finalize(ob, bevel=b, seg=1, sub=0, flat=True)
        leaves = []
        for (ob, bev) in self.loose:
            if not len(ob.data.vertices):
                continue
            L.finalize(ob, bevel=min(max(bev, 0.003), 0.012),
                       seg=1, sub=0, flat=self.smooth is False)
            leaves.append(ob)

        objs = [it[0] for it in self.items]
        bpy.ops.object.select_all(action="DESELECT")
        for ob in objs:
            ob.select_set(True)
        bpy.context.view_layer.objects.active = objs[0]
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        bpy.ops.object.select_all(action="DESELECT")
        out = L.join_by_material(objs, prefix="FS")
        mirror_x(out)
        for ob in leaves:
            mirror_obj(ob)
        if self.unwrap:
            L.smart_uv(out)
            if leaves:
                L.smart_uv(leaves)
        return out + leaves


def build(smooth=True, unwrap=True, bevel=True):
    m = Model(smooth, unwrap).build()
    P.apply_team_style(TEAM_STYLE)
    objs = m.finalize(bevel=bevel)
    return objs, L.stats(objs)
