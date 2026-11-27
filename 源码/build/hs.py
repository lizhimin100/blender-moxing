"""
hs.py —— 硬边几何库（v5）

v3/v4 的构件全是轴对齐长方体，屋面只能拿"阶梯盒子"近似坡面 ——
这就是"厚积木"的直接原因。v5 允许楔形 / 棱柱 / 锥台 / 任意角度斜撑，
所以本模块提供"任意平面围合体"的构件原型，全部满足：

  · 每个面是平面多边形（导出时按面重算法线 → flat shading）
  · 顶点不共享（导出器为每个面生成独立顶点，法线永不跨面平均）
  · 可带 role 标签：roof / rafter / duty / bevel …… 供 check_hardsurface.py 判定

part 结构统一为：
    {"stage", "mat", "tile", "verts": [(x,y,z)...], "faces": [(i,j,k,...)...],
     "box": (cx,cy,cz,sx,sy,sz), "role": str|None}
box 只是 AABB，供切块 / 连通性 / 光栅化快速剔除使用。
"""
import math

import numpy as np

# 细部倒角宽度（m）。v5 §2.1：细部 1.5–3 mm，大体量转角 15–40 mm。
BEVEL_FINE = 0.0025
BEVEL_BIG = 0.030


# ------------------------------------------------------------------ 基础
def _aabb(verts):
    a = np.asarray(verts, np.float64)
    lo, hi = a.min(0), a.max(0)
    c = (lo + hi) / 2
    s = np.maximum(hi - lo, 1e-4)
    return tuple(round(float(v), 4) for v in (*c, *s))


def _face_normal(pts):
    """Newell 法（对非严格平面的四边形也稳定）。"""
    n = np.zeros(3)
    for i in range(len(pts)):
        a, b = np.asarray(pts[i]), np.asarray(pts[(i + 1) % len(pts)])
        n[0] += (a[1] - b[1]) * (a[2] + b[2])
        n[1] += (a[2] - b[2]) * (a[0] + b[0])
        n[2] += (a[0] - b[0]) * (a[1] + b[1])
    ln = np.linalg.norm(n)
    return n / ln if ln > 1e-12 else np.array([0.0, 1.0, 0.0])


def add(p, st, mat, verts, faces, tile=None, role=None, extra=None):
    """登记一个多面体。faces 的绕向由"面心 − 体心"自动校正（凸体安全）。"""
    V = [(float(x), float(y), float(z)) for x, y, z in verts]
    C = np.mean(np.asarray(V), axis=0)
    fixed = []
    for f in faces:
        pts = [V[i] for i in f]
        n = _face_normal(pts)
        fc = np.mean(np.asarray(pts), axis=0)
        if float(np.dot(n, fc - C)) < 0:
            f = tuple(reversed(f))
        fixed.append(tuple(f))
    part = {
        "stage": st, "mat": mat,
        "tile": float(tile if tile is not None else 1.0),
        "verts": V, "faces": fixed, "box": _aabb(V),
    }
    if role:
        part["role"] = role
    if extra:
        part.update(extra)
    p.append(part)
    return part


# ------------------------------------------------------------------ 原型
def box_v(cx, cy, cz, sx, sy, sz):
    x0, x1 = cx - sx / 2, cx + sx / 2
    y0, y1 = cy - sy / 2, cy + sy / 2
    z0, z1 = cz - sz / 2, cz + sz / 2
    V = [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1),
         (x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)]
    F = [(0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5),
         (2, 3, 7, 6), (3, 0, 4, 7)]
    return V, F


def box(p, st, mat, cx, cy, cz, sx, sy, sz, tile=None, role=None, bevel=0.0):
    """长方体；bevel>0 时做 45° 单段倒角（仍全部是平面）。"""
    if bevel <= 0:
        V, F = box_v(cx, cy, cz, sx, sy, sz)
        return add(p, st, mat, V, F, tile=tile, role=role)
    b = min(bevel, min(sx, sy, sz) * 0.3)
    hx, hy, hz = sx / 2, sy / 2, sz / 2
    # 倒角盒 = 12 面体（每轴两端各收 b）—— 用"缩角"法：上下两面内缩 b，四个侧面变 8 个梯形
    x0, x1, y0, y1, z0, z1 = -hx, hx, -hy, hy, -hz, hz
    V = [
        (x0, y0 + b, z0 + b), (x1, y0 + b, z0 + b), (x1, y0 + b, z1 - b), (x0, y0 + b, z1 - b),
        (x0, y1 - b, z0 + b), (x1, y1 - b, z0 + b), (x1, y1 - b, z1 - b), (x0, y1 - b, z1 - b),
        (x0 + b, y0, z0 + b), (x1 - b, y0, z0 + b), (x1 - b, y0, z1 - b), (x0 + b, y0, z1 - b),
        (x0 + b, y1, z0 + b), (x1 - b, y1, z0 + b), (x1 - b, y1, z1 - b), (x0 + b, y1, z1 - b),
        (x0 + b, y0 + b, z0), (x1 - b, y0 + b, z0), (x1 - b, y1 - b, z0), (x0 + b, y1 - b, z0),
        (x0 + b, y0 + b, z1), (x1 - b, y0 + b, z1), (x1 - b, y1 - b, z1), (x0 + b, y1 - b, z1),
    ]
    F = [(0, 1, 2, 3), (4, 5, 6, 7),
         (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7),
         (8, 9, 1, 0), (9, 10, 2, 1), (10, 11, 3, 2), (11, 8, 0, 3),
         (12, 13, 5, 4), (13, 14, 6, 5), (14, 15, 7, 6), (15, 12, 4, 7),
         (16, 17, 9, 8), (17, 18, 13, 12), (18, 19, 15, 14), (19, 16, 11, 10),
         (20, 21, 17, 16), (21, 22, 18, 17), (22, 23, 19, 18), (23, 20, 16, 19)]
    V = [(cx + x, cy + y, cz + z) for x, y, z in V]
    return add(p, st, mat, V, F, tile=tile, role=role)


def bar(p, st, mat, A, B, w, h, up=(0, 1, 0), tile=None, role=None):
    """任意方向方条（斜撑 / 椽 / 拉杆）。截面 w × h，沿 A→B 挤出。"""
    A = np.asarray(A, float)
    Bp = np.asarray(B, float)
    d = Bp - A
    L = float(np.linalg.norm(d))
    if L < 1e-6:
        return None
    d /= L
    u = np.asarray(up, float)
    if abs(float(np.dot(u, d))) > 0.985:
        u = np.array([1.0, 0.0, 0.0])
    r = np.cross(u, d)
    r /= np.linalg.norm(r)
    v = np.cross(d, r)
    r *= w / 2
    v *= h / 2
    C = [A + r + v, A - r + v, A - r - v, A + r - v,
         Bp + r + v, Bp - r + v, Bp - r - v, Bp + r - v]
    F = [(0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5),
         (2, 3, 7, 6), (3, 0, 4, 7)]
    return add(p, st, mat, C, F, tile=tile, role=role)


def hexa(p, st, mat, bottom4, top4, tile=None, role=None):
    """8 点六面体：楔形、坡道、锥台收分都走这里。"""
    V = list(bottom4) + list(top4)
    F = [(0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5),
         (2, 3, 7, 6), (3, 0, 4, 7)]
    return add(p, st, mat, V, F, tile=tile, role=role)


def frustum(p, st, mat, cx, cz, s0, s1, y0, y1, tile=None, role=None):
    """上下不同截面的锥台（方形）。s0→s1 可以是数或 (sx, sz)。"""
    def pair(s):
        return (s, s) if isinstance(s, (int, float)) else (s[0], s[1])
    a, b = pair(s0), pair(s1)
    bottom = [(cx - a[0] / 2, y0, cz - a[1] / 2), (cx + a[0] / 2, y0, cz - a[1] / 2),
              (cx + a[0] / 2, y0, cz + a[1] / 2), (cx - a[0] / 2, y0, cz + a[1] / 2)]
    top = [(cx - b[0] / 2, y1, cz - b[1] / 2), (cx + b[0] / 2, y1, cz - b[1] / 2),
           (cx + b[0] / 2, y1, cz + b[1] / 2), (cx - b[0] / 2, y1, cz + b[1] / 2)]
    return hexa(p, st, mat, bottom, top, tile=tile, role=role)


def prism_y(p, st, mat, poly_xz, y0, y1, tile=None, role=None):
    """把 XZ 平面上的凸多边形沿 Y 挤出（阶梯圆盘 / 八边形桶 / 石墩）。"""
    n = len(poly_xz)
    V = [(x, y0, z) for x, z in poly_xz] + [(x, y1, z) for x, z in poly_xz]
    F = [tuple(range(n)), tuple(range(n, 2 * n))]
    for i in range(n):
        j = (i + 1) % n
        F.append((i, j, n + j, n + i))
    return add(p, st, mat, V, F, tile=tile, role=role)


def ngon(cx, cz, r, sides, phase=0.0):
    """圆截面。低模档位统一降到 6 边（见 build/detail.py）。"""
    import detail
    sides = detail.sides(sides)
    return [(cx + r * math.cos(phase + i * math.tau / sides),
             cz + r * math.sin(phase + i * math.tau / sides)) for i in range(sides)]


def slab(p, st, mat, quad, thick, tile=None, role=None):
    """四点多边形 + 沿法线反向的厚度 → 封闭薄板。"""
    Q = [np.asarray(q, float) for q in quad]
    n = _face_normal(Q)
    off = -n * thick
    V = [tuple(q) for q in Q] + [tuple(q + off) for q in Q]
    F = [(0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5),
         (2, 3, 7, 6), (3, 0, 4, 7)]
    return add(p, st, mat, V, F, tile=tile, role=role)


# ------------------------------------------------------------------ 屋面
class Plane:
    """屋面参数面：a0→a1 是檐口线，b0→b1 是脊线；v=0 檐口，v=1 脊。"""

    def __init__(self, a0, a1, b0, b1):
        self.a0 = np.asarray(a0, float)
        self.a1 = np.asarray(a1, float)
        self.b0 = np.asarray(b0, float)
        self.b1 = np.asarray(b1, float)

    def pt(self, u, v):
        e = self.a0 * (1 - u) + self.a1 * u
        r = self.b0 * (1 - u) + self.b1 * u
        return e * (1 - v) + r * v

    def normal(self):
        du = (self.a1 - self.a0)
        dv = (self.b0 - self.a0 + self.b1 - self.a1) / 2
        n = np.cross(du, dv)
        n = n / (np.linalg.norm(n) + 1e-12)
        # 屋面法线永远朝上：否则"往外偏 0.03"会把瓦压到望板下面，
        # 露出来的反而是椽子的顶面（v5 第一版就是这么翻的）。
        return -n if n[1] < 0 else n

    def slope_len(self):
        return float(np.linalg.norm((self.b0 + self.b1) / 2 - (self.a0 + self.a1) / 2))

    def width(self):
        return float(np.linalg.norm(self.a1 - self.a0))


def grid_slab(p, st, mat, plane, thick, nu=6, nv=6, v0=0.0, v1=1.0,
              offset=0.0, tile=None, role=None):
    """把 plane 上 v0→v1 的一段做成封闭薄壳（顶面网格 + 底面 + 四边）。"""
    n = plane.normal()
    base = offset
    P = [[plane.pt(i / nu, v0 + (v1 - v0) * j / nv) + n * base
          for j in range(nv + 1)] for i in range(nu + 1)]
    Q = [[q - n * thick for q in row] for row in P]
    V = []
    idx = {}
    for i in range(nu + 1):
        for j in range(nv + 1):
            idx[(i, j, 0)] = len(V)
            V.append(tuple(P[i][j]))
    for i in range(nu + 1):
        for j in range(nv + 1):
            idx[(i, j, 1)] = len(V)
            V.append(tuple(Q[i][j]))
    F = []
    for i in range(nu):
        for j in range(nv):
            F.append((idx[(i, j, 0)], idx[(i + 1, j, 0)], idx[(i + 1, j + 1, 0)], idx[(i, j + 1, 0)]))
            F.append((idx[(i, j, 1)], idx[(i + 1, j, 1)], idx[(i + 1, j + 1, 1)], idx[(i, j + 1, 1)]))
    for i in range(nu):
        F.append((idx[(i, 0, 0)], idx[(i + 1, 0, 0)], idx[(i + 1, 0, 1)], idx[(i, 0, 1)]))
        F.append((idx[(i, nv, 0)], idx[(i + 1, nv, 0)], idx[(i + 1, nv, 1)], idx[(i, nv, 1)]))
    for j in range(nv):
        F.append((idx[(0, j, 0)], idx[(0, j + 1, 0)], idx[(0, j + 1, 1)], idx[(0, j, 1)]))
        F.append((idx[(nu, j, 0)], idx[(nu, j + 1, 0)], idx[(nu, j + 1, 1)], idx[(nu, j, 1)]))
    return add(p, st, mat, V, F, tile=tile, role=role)


def rafters(p, st, mat, plane, count, w=0.10, h=0.14, drop=0.02, v0=-0.06, v1=0.99,
            tile=None, role="rafter"):
    """沿坡向的椽：从檐口（可出挑）铺到脊。drop = 椽顶面离屋面底面的间隙。"""
    n = plane.normal()
    for i in range(count):
        u = (i + 0.5) / count
        A = plane.pt(u, v0) + n * (-drop - h / 2)
        Bp = plane.pt(u, v1) + n * (-drop - h / 2)
        bar(p, st, mat, A, Bp, w, h, up=n, tile=tile, role=role)


def courses(p, st, mat, plane, course=0.22, expose=0.16, thick=0.05, lip=0.03,
            v_from=0.0, tile=None, role="shingle", every=3):
    """瓦：沿坡向一皮一皮铺。每皮外侧多出 lip，底沿做出 3 cm 挑唇。"""
    n = plane.normal()
    L = plane.slope_len()
    dv = course / max(L, 1e-6)
    k = 0
    v = v_from
    while v < 1.0 - 1e-6:
        v2 = min(1.0, v + dv)
        off = 0.004 * (k % every)          # 每 3 皮一错，避免完全共面
        grid_slab(p, st, mat, plane, thick, nu=max(2, int(plane.width() / 1.1)),
                  nv=max(1, int((v2 - v) * L / 0.9)), v0=v, v1=v2,
                  offset=0.032 + off, tile=tile, role=role)
        # 挑唇：皮底向外探 3 cm，形成阴影线
        q = [plane.pt(0, v) + n * 0.032, plane.pt(1, v) + n * 0.032,
             plane.pt(1, v) + n * (0.032 + lip), plane.pt(0, v) + n * (0.032 + lip)]
        slab(p, st, mat, q, thick, tile=tile, role=role)
        v = v2
        k += 1


def ridge_cap(p, st_hi, mat_wood, mat_team, a, b, y, width=0.24, team=True):
    """脊：脊木 + 脊瓦（高出两侧瓦面 0.04）。"""
    cx = (a[0] + b[0]) / 2
    cz = (a[2] + b[2]) / 2
    along_x = abs(b[0] - a[0]) > abs(b[2] - a[2])
    L = abs(b[0] - a[0]) if along_x else abs(b[2] - a[2])
    if along_x:
        box(p, st_hi, mat_wood, cx, y, cz, L + 0.10, 0.20, 0.16, tile=0.9, role="ridge")
        box(p, st_hi, "shingle", cx, y + 0.12, cz, L + 0.06, 0.06, width, tile=0.9, role="ridge")
        if team:
            box(p, st_hi, mat_team, cx, y + 0.17, cz, L + 0.02, 0.05, width + 0.02, tile=1.0, role="team")
    else:
        box(p, st_hi, mat_wood, cx, y, cz, 0.16, 0.20, L + 0.10, tile=0.9, role="ridge")
        box(p, st_hi, "shingle", cx, y + 0.12, cz, width, 0.06, L + 0.06, tile=0.9, role="ridge")
        if team:
            box(p, st_hi, mat_team, cx, y + 0.17, cz, width + 0.02, 0.05, L + 0.02, tile=1.0, role="team")


def attic_block(p, st, cx, cz, w, d, y0, y1, mat="plaster"):
    """屋面内侧的封闭阁楼体块：挡住薄壳下面的空腔，本身不参与外观。"""
    return box(p, st, mat, cx, (y0 + y1) / 2, cz, w, y1 - y0, d, tile=1.1, role="attic")
