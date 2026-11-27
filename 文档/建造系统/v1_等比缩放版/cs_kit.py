"""cs_kit.py —— 工地套件（Construction Site Kit）

一套只吃 4 个输入的程序化场景件：
    W, D     footprint（占地宽 / 深，米）
    H        建筑总高（米）
    attach    挂点（名字 → 世界坐标）
外加一次离线量出来的本体四边外沿 body=(x0,x1,y0,y1)：脚手架贴墙用。

长出：放线框 / 桩绳 / 两面脚手架 / 料堆 / 吊装三脚架 / 队色旗 / 每层碎屑。
所有件都按"骨"分组：一个骨 = 一个施工动作单位。骨名同时是顶点组名。

设计约束：
  * 只做低模（box / 6-8 边形），不做雕刻；细分档由 detail="hi" 的
    Bevel + Catmull-Clark 塌出来（只对道具，梁柱只加倒角）。
  * 原点在占地中心，+Y 是正面；所有件都在本体外沿之外（体检另有 BVH 兜底）。
  * 色彩只用 6 个工地色 + 建筑的 team / team_trim，不许再加。
"""
import math

import bmesh
import bpy
from mathutils import Matrix, Vector

# ── 工地色板（比建筑石材更"生"：原木偏黄、绳偏灰、铁偏冷） ──────────────────
SITE_PALETTE = {
    #  名称               sRGB      粗糙   金属
    "site_timber":      ("#9A7E52", 0.82, 0.00),
    "site_timber_dark": ("#6E5537", 0.86, 0.00),
    "site_rope":        ("#D9C79B", 0.95, 0.00),
    "site_stone":       ("#8F8676", 0.90, 0.00),
    "site_iron":        ("#3E4249", 0.42, 0.85),
    "site_cloth":       ("#CFBE96", 0.96, 0.00),
}
# 队色两档由建筑提供（同名材质，换阵营一起变）；单独跑套件时按标准色补出来
EXTRA = {
    "team":      ("#2E5FB4", 0.56, 0.00),
    "team_trim": ("#F1CD79", 0.44, 0.10),
}
MAT_ORDER = list(SITE_PALETTE.keys()) + list(EXTRA.keys())

PLOT_M = 1.55       # 放线框最少离本体多远
SCAF_M = 0.30       # 脚手架立柱到本体外沿的距离
LIFT_H = 2.20       # 脚手架一步高
POST = 0.078        # 立杆截面
GATE = 1.90         # 正面大门开口宽


def srgb(hexstr):
    h = hexstr.lstrip("#")
    out = []
    for i in range(3):
        c = int(h[i * 2:i * 2 + 2], 16) / 255.0
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return tuple(out)


def clamp(v, a, b):
    return max(a, min(b, v))


def lin(a, b, n):
    if n <= 0:
        return [a]
    return [a + (b - a) * i / n for i in range(n + 1)]


def mat_site(name):
    """取得（没有就建）一个工地材质。纯色、无贴图，随 GLB 走。"""
    m = bpy.data.materials.get(name)
    if m:
        return m
    if name in SITE_PALETTE:
        col, rough, metal = SITE_PALETTE[name]
    else:
        col, rough, metal = EXTRA[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*srgb(col), 1.0)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if "Specular IOR Level" in b.inputs:
        b.inputs["Specular IOR Level"].default_value = 0.35
    m.diffuse_color = (*srgb(col), 1.0)
    return m


class Kit:
    """把整套工地件堆进一个 mesh；每个件属于一个骨（= 一个动作单位）。"""

    def __init__(self, W, D, H, band_edges, attach=None, body=None):
        self.W, self.D, self.H = W, D, H
        self.edges = band_edges
        self.attach = attach or {}
        self.parts = []
        self.bones = {}
        self.bone_box = {}
        self.meta = {}
        if body:
            self.ex0, self.ex1, self.ey0, self.ey1 = body
        else:
            self.ex0, self.ex1 = -W * 0.5, W * 0.5
            self.ey0, self.ey1 = -D * 0.5, D * 0.5
        # 脚手架：本体四边各外扩 SCAF_M（四边独立，带院子的建筑才不会撞围栏）
        self.sx0, self.sx1 = self.ex0 - SCAF_M, self.ex1 + SCAF_M
        self.sy0, self.sy1 = self.ey0 - SCAF_M, self.ey1 + SCAF_M
        # 放线框：同时包住"场地 + 0.35"和"本体 + PLOT_M"
        self.bx0 = min(-W * 0.5 - 0.35, self.sx0 - 0.60)
        self.bx1 = max(W * 0.5 + 0.35, self.sx1 + 0.60)
        self.by0 = min(-D * 0.5 - 0.35, self.sy0 - 0.60)
        self.by1 = max(D * 0.5 + 0.35, self.sy1 + 0.60)
        self.cx = (self.bx0 + self.bx1) * 0.5

    # ── 基础件 ────────────────────────────────────────────────────────────
    def bone(self, name, head):
        if name in self.bones:
            return
        self.bones[name] = Vector(head)

    def part(self, verts, faces, mat, bone, cc=False):
        self.parts.append((verts, faces, mat, bone, cc))

    def box(self, bone, mat, c, s, rotz=0.0, cc=False):
        cx, cy, cz = c
        hx, hy, hz = s[0] * 0.5, s[1] * 0.5, s[2] * 0.5
        vs = [(-hx, -hy, -hz), (hx, -hy, -hz), (hx, hy, -hz), (-hx, hy, -hz),
              (-hx, -hy, hz), (hx, -hy, hz), (hx, hy, hz), (-hx, hy, hz)]
        if rotz:
            R = Matrix.Rotation(rotz, 3, "Z")
            vs = [tuple(R @ Vector(v)) for v in vs]
        vs = [(v[0] + cx, v[1] + cy, v[2] + cz) for v in vs]
        fs = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
              (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
        self.part(vs, fs, mat, bone, cc)

    @staticmethod
    def _frame(p0, p1):
        d = (Vector(p1) - Vector(p0))
        L = d.length
        if L < 1e-9:
            return Vector((1, 0, 0)), Vector((0, 0, 1)), Vector((0, 0, 1)), 0.0
        d = d / L
        up = Vector((0, 0, 1)) if abs(d.z) < 0.94 else Vector((0, 1, 0))
        r = d.cross(up)
        if r.length < 1e-6:
            r = Vector((1, 0, 0))
        r.normalize()
        u = r.cross(d).normalized()
        return r, u, d, L

    def beam(self, bone, mat, p0, p1, w, h, off=(0, 0, 0), cc=False, extend=0.0):
        r, u, d, L = self._frame(p0, p1)
        if L < 1e-9:
            return
        a = Vector(p0) - d * extend + Vector(off)
        b = Vector(p1) + d * extend + Vector(off)
        w2, h2 = w * 0.5, h * 0.5
        vs = []
        for p in (a, b):
            for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                vs.append(tuple(p + r * (sx * w2) + u * (sy * h2)))
        fs = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
              (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
        self.part(vs, fs, mat, bone, cc)

    def prism(self, bone, mat, c, r0, r1, h, n=8, rot=0.0, cc=False, cap=True):
        cx, cy, cz = c
        bot, top = [], []
        for i in range(n):
            a = rot + math.tau * i / n
            bot.append((cx + math.cos(a) * r0, cy + math.sin(a) * r0, cz))
            top.append((cx + math.cos(a) * r1, cy + math.sin(a) * r1, cz + h))
        vs = bot + top
        fs = []
        if cap:
            fs.append(tuple(range(n - 1, -1, -1)))
            fs.append(tuple(range(n, 2 * n)))
        for i in range(n):
            j = (i + 1) % n
            fs.append((i, j, n + j, n + i))
        self.part(vs, fs, mat, bone, cc)

    def tube(self, bone, mat, p0, p1, r, n=6, cc=False, cap=True):
        rr, uu, d, L = self._frame(p0, p1)
        if L < 1e-9:
            return
        rings = []
        for p in (Vector(p0), Vector(p1)):
            ring = []
            for i in range(n):
                a = math.tau * i / n
                ring.append(tuple(p + rr * (math.cos(a) * r) + uu * (math.sin(a) * r)))
            rings.append(ring)
        vs = rings[0] + rings[1]
        fs = []
        if cap:
            fs.append(tuple(range(n - 1, -1, -1)))
            fs.append(tuple(range(n, 2 * n)))
        for i in range(n):
            j = (i + 1) % n
            fs.append((i, j, n + j, n + i))
        self.part(vs, fs, mat, bone, cc)

    # ── 放线：木框 + 角桩 + 麻绳 ──────────────────────────────────────────
    def build_plot(self):
        bx0, bx1, by0, by1 = self.bx0, self.bx1, self.by0, self.by1
        self.bone("site_plot", (0, 0, 0.05))
        self.bone("site_stake", (0, 0, 0.30))
        self.bone("site_rope", (0, 0, 0.55))
        F, HGT = 0.14, 0.10
        g = min(GATE * 0.5, (bx1 - bx0) * 0.30)
        # 前后通长（正面中间留门）
        for sx in (-1, 1):
            self.box("site_plot", "site_timber", (sx * (bx1 + g) * 0.5, by1, HGT * 0.5),
                     (bx1 - g, F, HGT))
            self.box("site_plot", "site_timber", (sx * (bx1 + g) * 0.5, by0, HGT * 0.5),
                     (bx1 - g, F, HGT))
        for px in (bx0, bx1):
            self.box("site_plot", "site_timber_dark", (px, 0, HGT * 0.5),
                     (F, by1 - by0 - 2 * F, HGT))
        # 门柱 + 队色横梁
        for sx in (-1, 1):
            self.box("site_plot", "site_timber_dark", (sx * g, by1, 0.50), (0.11, 0.11, 1.00))
            self.box("site_plot", "team", (sx * g, by1, 0.86), (0.125, 0.125, 0.10))
            self.box("site_plot", "team_trim", (sx * g, by1, 1.02), (0.14, 0.14, 0.035))
        self.box("site_plot", "site_timber", (0, by1, 1.00), (2 * g + 0.10, 0.10, 0.10))

        # 角板（四角压石，读"这块地定了"）
        for px in (bx0, bx1):
            for py in (by0, by1):
                self.box("site_plot", "site_stone", (px, py, 0.035), (0.40, 0.40, 0.07))
                self.box("site_plot", "site_iron", (px, py, 0.082), (0.07, 0.07, 0.024))

        # 桩：一圈 12 根，正面中间两根是门柱，跳过
        loop = self._stake_loop(g)
        self.meta["stake_loop"] = loop
        for (x, y) in loop:
            if y > 0 and abs(x) < g - 1e-6:
                continue
            self.box("site_stake", "site_timber_dark", (x, y, 0.30), (0.075, 0.075, 0.60))
            self.box("site_stake", "site_cloth", (x, y, 0.455), (0.082, 0.082, 0.055))
            self.box("site_stake", "site_iron", (x, y, 0.615), (0.085, 0.085, 0.035))

        # 绳：桩与桩之间 4 段垂弧，门洞跨跳过
        for i in range(len(loop)):
            a, b = loop[i], loop[(i + 1) % len(loop)]
            if a[1] > 0 and b[1] > 0 and abs(a[0]) < g + 1e-6 and abs(b[0]) < g + 1e-6:
                continue
            n = 4
            pts = []
            for t in range(n + 1):
                f = t / n
                sag = 0.075 * math.sin(math.pi * f)
                pts.append((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f, 0.555 - sag))
            for k in range(n):
                self.beam("site_rope", "site_rope", pts[k], pts[k + 1], 0.032, 0.032)

    def _stake_loop(self, g):
        bx0, bx1, by0, by1 = self.bx0, self.bx1, self.by0, self.by1
        mx = (bx1 - bx0) * 0.21
        my = (by1 - by0) * 0.17
        return [
            (bx0, by1), (-g - 0.26, by1), (g + 0.26, by1), (bx1, by1),
            (bx1, by1 - my), (bx1, by0 + my), (bx1, by0),
            (bx1 - mx, by0), (bx0 + mx, by0),
            (bx0, by0), (bx0, by0 + my), (bx0, by1 - my),
        ]

    # ── 脚手架：正面 + 左侧两面（背面吊装口、右侧留干净剪影） ────────────
    def build_scaffold(self, lifts):
        sx0, sx1, sy0, sy1 = self.sx0, self.sx1, self.sy0, self.sy1
        sw, sd = sx1 - sx0, sy1 - sy0
        nb_x = int(clamp(round(sw / 3.0), 1, 5))
        nb_y = int(clamp(round(sd / 3.0), 1, 3))
        front = [(x, sy1) for x in lin(sx0, sx1, nb_x)]
        back = [(x, sy0) for x in lin(sx0, sx1, nb_x)]
        left = [(sx0, y) for y in lin(sy0, sy1, nb_y)][1:-1]
        right = [(sx1, y) for y in lin(sy0, sy1, nb_y)][1:-1]
        posts = front + back + left + right
        self.meta["scaf"] = {"sx0": sx0, "sx1": sx1, "sy0": sy0, "sy1": sy1,
                             "posts": posts, "lifts": lifts, "nb_x": nb_x,
                             "nb_y": nb_y, "lh": LIFT_H}
        fcx = (sx0 + sx1) * 0.5
        fcy = (sy0 + sy1) * 0.5

        for k in range(lifts):
            z0 = k * LIFT_H
            b = f"site_scaf_{k}"
            self.bone(b, (0, 0, z0))
            top = (k == lifts - 1)
            ph = LIFT_H - 0.03 + (0.55 if top else 0.0)
            for (x, y) in posts:
                self.box(b, "site_timber", (x, y, z0 + ph * 0.5), (POST, POST, ph))
                if k:
                    self.box(b, "site_iron", (x, y, z0 + 0.005), (0.125, 0.125, 0.07))
            # 四面大横杆
            zr = z0 + LIFT_H - 0.10
            for sy in (sy1, sy0):
                self.box(b, "site_timber",
                         (fcx, sy + (POST * 0.5 + 0.030) * (1 if sy > 0 else -1), zr),
                         (sw + 0.06, 0.062, 0.085))
            for sx in (sx0, sx1):
                self.box(b, "site_timber",
                         (sx + (POST * 0.5 + 0.030) * (1 if sx > 0 else -1), fcy, zr),
                         (0.062, sd + 0.06, 0.085))
            # 斜撑：前后各一跨，逐层换向（左右不做，免得成笼子）
            if nb_x >= 2:
                i0 = nb_x // 2
                for face_y, off in ((sy1, 0.075), (sy0, -0.075)):
                    xa, xb = front[i0][0], front[i0 + 1][0]
                    sgn = 1 if k % 2 == 0 else -1
                    if face_y < 0:
                        sgn = -sgn
                    p0 = (xa if sgn > 0 else xb, face_y + off, z0 + 0.06)
                    p1 = (xb if sgn > 0 else xa, face_y + off, z0 + LIFT_H - 0.16)
                    self.beam(b, "site_timber_dark", p0, p1, 0.055, 0.075)
            # 只有顶层是"工作平台"：四面脚手板 + 护栏 + 挡脚板
            if top:
                pz = z0 + LIFT_H - 0.05
                for sy in (sy1, sy0):
                    self.box(b, "site_timber_dark",
                             (fcx, sy + 0.135 * (1 if sy > 0 else -1), pz),
                             (sw, 0.28, 0.045))
                for sx in (sx0, sx1):
                    self.box(b, "site_timber_dark",
                             (sx + 0.135 * (1 if sx > 0 else -1), fcy, pz),
                             (0.28, sd, 0.045))
                for sy in (sy1, sy0):
                    self.box(b, "site_timber",
                             (fcx, sy + 0.075 * (1 if sy > 0 else -1), z0 + LIFT_H + 0.52),
                             (sw, 0.055, 0.065))
                    self.box(b, "site_timber_dark",
                             (fcx, sy + 0.14 * (1 if sy > 0 else -1), z0 + LIFT_H + 0.06),
                             (sw, 0.035, 0.12))
                for sx in (sx0, sx1):
                    self.box(b, "site_timber",
                             (sx + 0.075 * (1 if sx > 0 else -1), fcy, z0 + LIFT_H + 0.52),
                             (0.055, sd, 0.065))
                    self.box(b, "site_timber_dark",
                             (sx + 0.14 * (1 if sx > 0 else -1), fcy, z0 + LIFT_H + 0.06),
                             (0.035, sd, 0.12))
                for s2 in (-1, 1):
                    x2 = sx1 if s2 > 0 else sx0
                    self.box(b, "team", (x2, sy1, z0 + LIFT_H * 0.62), (0.098, 0.098, 0.14))
            # 首层的上人梯
            if k == 0 and len(front) >= 2:
                lx = (front[-2][0] + front[-1][0]) * 0.5
                for s2 in (-1, 1):
                    self.box(b, "site_timber_dark", (lx + s2 * 0.26, sy1 + 0.16, 1.10),
                             (0.045, 0.045, 2.10))
                for i in range(7):
                    self.box(b, "site_timber", (lx, sy1 + 0.16, 0.16 + i * 0.30),
                             (0.56, 0.035, 0.035))
        return posts

    # ── 料堆：石垛 / 原木捆（门外）＋ 桶 / 砂浆槽（门内） ──────────────────
    def build_piles(self):
        bx0, bx1, by1 = self.bx0, self.bx1, self.by1
        # 石垛：门外左侧
        px, py = bx0 - 0.50, by1 - 0.10
        self.bone("site_pile_a", (px, py, 0))
        for i in range(3):
            self.box("site_pile_a", "site_timber_dark", (px - 0.25 + i * 0.25, py, 0.055),
                     (0.10, 0.66, 0.11))
        self.box("site_pile_a", "site_timber_dark", (px, py, 0.115), (0.78, 0.62, 0.04))
        blocks = [(-0.24, -0.14, 0), (0.02, -0.14, 0), (0.26, -0.12, 0),
                  (-0.12, 0.14, 0), (0.16, 0.15, 0), (-0.02, -0.06, 1)]
        for i, (dx, dy, lay) in enumerate(blocks):
            self.box("site_pile_a", "site_stone",
                     (px + dx, py + dy, 0.135 + 0.045 + lay * 0.215 + 0.105),
                     (0.34 + 0.03 * (i % 3), 0.26, 0.205), rotz=0.06 * ((i % 3) - 1), cc=True)

        # 原木捆：门外右侧
        px, py = bx1 + 0.60, by1 - 0.16
        self.bone("site_pile_b", (px, py, 0))
        for i in range(3):
            self.box("site_pile_b", "site_timber_dark", (px, py - 0.26 + i * 0.26, 0.05),
                     (0.70, 0.10, 0.10))
        logs = [(-0.13, 0.13, 0.135), (0.13, 0.13, 0.135), (-0.13, -0.13, 0.135),
                (0.13, -0.13, 0.135), (0.0, 0.0, 0.355)]
        for (dx, dy, z) in logs:
            self.tube("site_pile_b", "site_timber", (px + dx, py - 0.50, z),
                      (px + dx, py + 0.50, z), 0.112, n=6, cc=True)
        for s in (-1, 1):
            self.tube("site_pile_b", "site_rope", (px + s * 0.25, py, 0.02),
                      (px + s * 0.25, py, 0.47), 0.028, n=4)

        # 水桶：门内左
        px, py = bx0 + 0.56, by1 - 0.46
        self.bone("site_barrel", (px, py, 0))
        self.prism("site_barrel", "site_timber", (px, py, 0.0), 0.185, 0.205, 0.30,
                   n=8, cc=True)
        self.prism("site_barrel", "site_timber", (px, py, 0.30), 0.205, 0.185, 0.15,
                   n=8, cc=True)
        for z in (0.10, 0.36):
            self.prism("site_barrel", "site_iron", (px, py, z), 0.203, 0.203, 0.032,
                       n=8, cap=False)
        self.prism("site_barrel", "site_cloth", (px, py, 0.44), 0.165, 0.165, 0.015, n=8)

        # 砂浆槽：门内右
        px, py = bx1 - 0.54, by1 - 0.44
        self.bone("site_tub", (px, py, 0))
        self.prism("site_tub", "site_timber_dark", (px, py, 0.0), 0.29, 0.32, 0.21, n=8, cc=True)
        self.prism("site_tub", "site_cloth", (px, py, 0.18), 0.265, 0.265, 0.02, n=8, cc=True)
        self.beam("site_tub", "site_iron", (px + 0.38, py - 0.08, 0.05),
                  (px + 0.47, py - 0.01, 0.43), 0.032, 0.032)
        self.box("site_tub", "site_iron", (px + 0.48, py, 0.44), (0.12, 0.16, 0.018),
                 rotz=0.5)

    # ── 吊装：场地后左角的悬臂吊杆（一人高的小吊，不跟脚手架抢位置） ──────
    def build_hoist(self):
        hp = Vector(self.attach.get("hoist") or
                    (self.bx0 - 0.55, self.by0 - 0.30, min(3.4, 0.26 * self.H)))
        hx, hy, hz = hp.x, hp.y, max(2.6, hp.z)
        self.bone("site_hoist", (hx, hy, 0))
        # 底盘 + 立杆 + 斜撑
        self.box("site_hoist", "site_timber_dark", (hx, hy, 0.06), (0.62, 0.62, 0.12))
        self.box("site_hoist", "site_timber", (hx, hy, hz * 0.5), (0.105, 0.105, hz))
        self.box("site_hoist", "site_iron", (hx, hy, hz - 0.10), (0.15, 0.15, 0.10))
        # 悬臂：沿 +X 伸到场地内
        ax = hx + 1.85
        self.box("site_hoist", "site_timber", ((hx + ax) * 0.5, hy, hz - 0.26),
                 (ax - hx, 0.085, 0.11))
        self.beam("site_hoist", "site_timber_dark", (hx, hy, hz * 0.56),
                  (hx + 1.05, hy, hz - 0.32), 0.055, 0.07)
        # 绞盘挂在立杆下段
        self.box("site_hoist", "site_timber_dark", (hx, hy + 0.03, 0.55), (0.34, 0.16, 0.34))
        self.tube("site_hoist", "site_iron", (hx - 0.14, hy, 0.62), (hx + 0.14, hy, 0.62),
                  0.055, n=6)
        self.beam("site_hoist", "site_iron", (hx + 0.16, hy, 0.62), (hx + 0.26, hy + 0.10, 0.86),
                  0.036, 0.036)
        # 吊索 + 石块
        self.bone("site_hook", (ax - 0.25, hy, hz - 0.44))
        self.tube("site_hook", "site_rope", (ax - 0.25, hy, hz - 0.44),
                  (ax - 0.25, hy, 0.92), 0.022, n=4)
        self.box("site_hook", "site_stone", (ax - 0.25, hy, 0.74), (0.36, 0.26, 0.28),
                 rotz=0.18, cc=True)
        self.tube("site_hook", "site_rope", (ax - 0.25, hy, 0.90), (ax - 0.25, hy, 0.84),
                  0.040, n=4)

    # ── 队色：立杆挂旗 + 檐下挂幡 ────────────────────────────────────────
    def build_banners(self, lifts):
        zt = lifts * LIFT_H
        bp = self.attach.get("banner")
        px, py = (bp[0], bp[1]) if bp else (self.sx0, self.sy1)
        self.bone("site_flag", (px, py, zt))
        self.box("site_flag", "site_timber_dark", (px, py, zt + 0.80), (0.06, 0.06, 1.60))
        self.box("site_flag", "site_timber_dark",
                 (px + 0.34, py, zt + 1.54), (0.74, 0.05, 0.05))
        self.box("site_flag", "team_trim", (px + 0.70, py, zt + 1.49), (0.05, 0.07, 0.07))
        v = [(-0.30, 0.0, 1.44), (0.36, 0.0, 1.44), (0.36, 0.0, 0.42), (-0.30, 0.0, 0.42)]
        fs = [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
        vs = [(px + a, py + 0.015, zt + c) for (a, _, c) in v]
        vs2 = [(px + a, py + 0.040, zt + c) for (a, _, c) in v]
        self.part(vs + vs2, fs, "team", "site_flag")
        self.box("site_flag", "team_trim", (px + 0.03, py + 0.028, zt + 0.44),
                 (0.62, 0.03, 0.05))
        # 挂幡：正面右角，檐下横杆垂布
        px, py = self.sx1 - 0.06, self.sy1 - 0.34
        self.bone("site_banner", (px, py, zt - 0.02))
        self.box("site_banner", "site_timber_dark", (px, py, zt - 0.02), (0.90, 0.06, 0.06))
        v = [(-0.44, 0, 0), (0.44, 0, 0), (0.44, 0, -0.92), (-0.44, 0, -0.92)]
        vs = [(px + a, py + 0.012, zt - 0.06 + c) for (a, _, c) in v]
        vs2 = [(px + a, py + 0.036, zt - 0.06 + c) for (a, _, c) in v]
        self.part(vs + vs2, fs, "team", "site_banner")
        self.box("site_banner", "team_trim", (px, py + 0.024, zt - 0.98), (0.86, 0.03, 0.05))

    # ── 基座扬土：建筑从地里升起来时，四周被顶起的土块 ────────────────────
    def build_dust(self):
        self.bone("site_dust", (0, 0, 0.04))
        x0, x1, y0, y1 = self.ex0 - 0.16, self.ex1 + 0.16, self.ey0 - 0.16, self.ey1 + 0.16
        n = 6
        pos = []
        for i in range(n):
            f = i / (n - 1) if n > 1 else 0.5
            pos.append((x0 + (x1 - x0) * f, y1 + 0.14))
            pos.append((x0 + (x1 - x0) * f, y0 - 0.14))
        for i in range(1, n - 1):
            f = i / (n - 1)
            pos.append((x0 - 0.14, y0 + (y1 - y0) * f))
            pos.append((x1 + 0.14, y0 + (y1 - y0) * f))
        for i, (x, y) in enumerate(pos):
            s = 0.13 + 0.05 * ((i * 7) % 4)
            self.box("site_dust", "site_stone", (x, y, s * 0.22),
                     (s, s * 0.9, s * 0.34), rotz=0.7 * i, cc=True)
            if i % 3 == 0:
                s2 = s * 0.55
                self.box("site_dust", "site_stone",
                         (x * 1.02 + 0.08, y * 1.02, s2 * 0.2),
                         (s2, s2 * 0.9, s2 * 0.32), rotz=1.1 * i, cc=True)

    # ── 组装 ──────────────────────────────────────────────────────────────
    def build(self):
        H = self.H
        body_top = min(H - 1.3, max(3.0, H * 0.74))
        lifts = int(clamp(round(min(body_top, 11.0, H * 0.62) / LIFT_H), 2, 4))
        self.meta["lifts"] = lifts
        self.meta["body_top"] = body_top
        self.build_plot()
        self.build_scaffold(lifts)
        self.build_piles()
        self.build_hoist()
        self.build_banners(lifts)
        self.build_dust()
        self.bone_box = {}
        for vs, fs, mat, bone, cc in self.parts:
            zs = [v[2] for v in vs]
            lo, hi = min(zs), max(zs)
            b = self.bone_box.get(bone)
            self.bone_box[bone] = (min(b[0], lo), max(b[1], hi)) if b else (lo, hi)
        return self

    @property
    def bands(self):
        return [(self.edges[i], self.edges[i + 1]) for i in range(len(self.edges) - 1)]

    def to_object(self, name="SiteKit", detail="low"):
        mats = [mat_site(m) for m in MAT_ORDER]
        idx = {m: i for i, m in enumerate(MAT_ORDER)}

        def make(parts, obname):
            verts, faces, fmat, vbone = [], [], [], []
            for (vs, fs, mat, bone, cc) in parts:
                off = len(verts)
                verts.extend([tuple(v) for v in vs])
                for f in fs:
                    faces.append(tuple(i + off for i in f))
                    fmat.append(idx[mat])
                vbone.extend([bone] * len(vs))
            me = bpy.data.meshes.new(obname)
            me.from_pydata(verts, [], faces)
            me.update()
            ob = bpy.data.objects.new(obname, me)
            bpy.context.scene.collection.objects.link(ob)
            for m in mats:
                me.materials.append(m)
            for p, mi in zip(me.polygons, fmat):
                p.material_index = mi
                p.use_smooth = False
            groups = {}
            for b in set(vbone):
                groups[b] = ob.vertex_groups.new(name=b)
            for vi, b in enumerate(vbone):
                groups[b].add([vi], 1.0, "REPLACE")
            bm = bmesh.new()
            bm.from_mesh(me)
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
            bm.to_mesh(me)
            bm.free()
            return ob

        if detail == "low":
            ob = make(self.parts, name)
        else:
            crisp = [p for p in self.parts if not p[4]]
            soft = [p for p in self.parts if p[4]]
            # 只磨道具：梁柱保持硬边（规则 F48：大平面 / 长条上 CC 会变成塑料管）
            ob = make(crisp, name)
            if soft:
                ob2 = make(soft, name + "_soft")
                _bevel(ob2, 0.008, 1)
                _cc(ob2, 1)
                for o in bpy.data.objects:
                    if o:
                        o.select_set(False)
                bpy.context.view_layer.objects.active = ob
                ob.select_set(True)
                ob2.select_set(True)
                bpy.ops.object.join()
                ob.select_set(False)
        ob.data.validate()
        return ob


def _bevel(ob, width=0.010, seg=2):
    bpy.context.view_layer.objects.active = ob
    mod = ob.modifiers.new("bev", "BEVEL")
    mod.width = width
    mod.segments = seg
    mod.limit_method = "ANGLE"
    mod.angle_limit = math.radians(35)
    bpy.ops.object.modifier_apply(modifier=mod.name)


def _cc(ob, levels=1):
    bpy.context.view_layer.objects.active = ob
    sub = ob.modifiers.new("cc", "SUBSURF")
    sub.levels = levels
    sub.render_levels = levels
    sub.use_limit_surface = True
    bpy.ops.object.modifier_apply(modifier=sub.name)
