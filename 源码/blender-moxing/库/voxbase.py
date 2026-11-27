"""voxbase.py —— 格网档单位的唯一几何源（格子是数据源，mesh 是派生物）

口径见 `文档/格网单位规范.md` v1：
  * 格边长 0.1 m；总高 17 格（16/17/18）；头 4 格；躯干 6 格；关节线 0/2/6/9/13/17；
  * **无 UV / 无贴图 / 无图集**，颜色全部走顶点色；材质固定三槽 `主体` / `team` / `team_trim`；
  * 一块 = 一根骨 = 权重 1.0（刚性）；面剔除按部件内部做，跨部件不剔（套筒靠重叠遮缝）；
  * 描边 = 反向外壳 0.02 m（只在预览/图标里加，不进 GLB，见 `outline()`）。

两条实现约定（写在这里省得后来人踩）：

1. **坐标一律"半格"整数（0.05 m）**。对外 API 用**格**（`box/put/cut/tint`，自动 ×2），
   布料这种需要更细台阶的部件用 `fbox/fput`（直接写半格）。这样软硬两种精度落在同一套
   整数坐标里，不会出现"这件是 0.07 那件是 0.1"的错位。
   硬部件必须用偶数格坐标 —— `audit()` 里会查（`OFFGRID`）。

2. **顶点色里 team / team_trim 存的是明度倍数**（0.74 / 1.00 / 1.16），不存颜色本身。
   渲染前调 `bake_preview()` 把它们乘上阵营色，GLB 里保持中性白 —— 引擎按材质名分区染色。
   `主体` 槽存真实颜色（引擎不动它）。
"""
import math
import os
import sys

import bmesh
import bpy
from mathutils import Vector

CELL = 0.1
BASELINE_V = "v1"
HEIGHT_CELLS = 17
JOINT_Z = dict(ground=0, boot=2, knee=6, hip=9, shoulder=13, top=17)

TEAM = {"联盟": ("#2E5FB4", "#F1CD79"),
        "失落帝国": ("#743A2E", "#A99578")}

SLOTS = ("主体", "team", "team_trim")

# ── 色板：name -> (槽, 颜色或明度倍数) ──────────────────────────────────────
PAL = {
    # 布（联盟制式戎装的主色，明度从高到低四档）
    "cloth_pale":  ("主体", "#E8E0D0"),
    "cloth_linen": ("主体", "#F1EADA"),     # 布亮：肩/兜帽受光面
    "cloth":       ("主体", "#D3C8B1"),
    "cloth_dark":  ("主体", "#B0A48A"),
    "cloth_shade": ("主体", "#8B8069"),
    # 钢
    "steel_edge":  ("主体", "#D7DBE1"),     # 刃口 / 盔脊高光
    "steel_pale":  ("主体", "#B8BDC5"),
    "steel":       ("主体", "#949AA4"),
    "steel_dark":  ("主体", "#6B7179"),
    "steel_deep":  ("主体", "#495058"),
    # 铁（最深的一档，做靴尖、枪箍、弓弦）
    "iron":        ("主体", "#33363C"),
    "iron_hi":     ("主体", "#4C5158"),
    "iron_dark":   ("主体", "#1F2228"),
    # 皮革
    "leather_hi":  ("主体", "#9C7550"),
    "leather_warm": ("主体", "#8C6640"),
    "leather":     ("主体", "#7E5C3B"),
    "leather_dark": ("主体", "#4E3826"),
    # 金 / 银
    "gold":        ("主体", "#D6A64A"),
    "gold_dark":   ("主体", "#A87C31"),
    # 肤 / 发 / 眼
    "skin":        ("主体", "#D2A57F"),
    "skin_dark":   ("主体", "#AC7F5C"),
    "hair":        ("主体", "#3B2A1E"),
    "eye":         ("主体", "#1B1512"),
    # 木
    "wood_hi":     ("主体", "#B5793F"),
    "wood":        ("主体", "#9B6236"),
    "wood_dark":   ("主体", "#6C4425"),
    # 队色（顶点色 = 明度倍数）
    "team_deep":   ("team", 0.74),
    "team":        ("team", 1.00),
    "team_hi":     ("team", 1.16),
    # 队色辅（金边）
    "trim_dark":   ("team_trim", 0.78),
    "trim":        ("team_trim", 1.00),
    "trim_hi":     ("team_trim", 1.14),
}


def srgb(hexstr):
    h = hexstr.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def _s2l(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def lin(hexstr):
    return tuple(_s2l(c) for c in srgb(hexstr))


def lin_rgb(rgb):
    return tuple(_s2l(c) for c in rgb)


def shade(hexstr, k):
    """按明度倍数压暗/提亮（sRGB 空间乘，够用且直观）。"""
    return tuple(min(1.0, max(0.0, c * k)) for c in srgb(hexstr))


def darken(color_name, steps=2, k=0.86):
    """把色板里的颜色压暗 n 档（套筒用）。team 槽按倍数压。"""
    slot, val = PAL[color_name]
    if slot == "主体":
        hx = "#%02X%02X%02X" % tuple(int(round(c * 255)) for c in shade(val, k ** steps))
        return _add_tmp(("主体", hx))
    return _add_tmp((slot, round(val * (k ** steps), 3)))


_TMP = {}


def _add_tmp(pair):
    """把临时颜色塞进 PAL（同一 (槽,值) 复用一个名字，颜色表不会被撑爆）。"""
    slot, val = pair
    if isinstance(val, float):
        key = "%s_k%03d" % (slot, int(round(val * 1000)))
    else:
        key = "tmp_" + val.lstrip("#").lower()
    if key not in PAL:
        PAL[key] = (slot, val)
    return key


# ══ 骨架（联盟 24 根，跖行；head/tail 全落在六条关节线或自由关节上）══════════
#   z 线：地面 0 / 靴口 2 / 膝 6 / 胯 9 / 肩颈 13 / 头顶 17（格）
RIG_BONES = [
    #  name,          head,                tail,                parent
    ("root",        (0.00, 0.00, 0.00), (0.00, 0.00, 0.10), None),
    ("hips",        (0.00, 0.00, 0.90), (0.00, 0.00, 1.02), "root"),
    ("spine",       (0.00, 0.00, 1.02), (0.00, 0.00, 1.14), "hips"),
    ("chest",       (0.00, 0.00, 1.14), (0.00, 0.00, 1.28), "spine"),
    ("neck",        (0.00, 0.00, 1.27), (0.00, 0.00, 1.30), "chest"),
    ("head",        (0.00, 0.00, 1.30), (0.00, 0.00, 1.70), "neck"),

    ("shoulder_R",  (0.14, 0.00, 1.30), (0.40, 0.00, 1.30), "chest"),
    ("upperarm_R",  (0.40, 0.00, 1.30), (0.40, 0.00, 1.10), "shoulder_R"),
    ("forearm_R",   (0.40, 0.00, 1.10), (0.40, 0.00, 0.90), "upperarm_R"),
    ("hand_R",      (0.40, 0.00, 0.90), (0.40, 0.00, 0.70), "forearm_R"),
    ("weapon_R",    (0.40, 0.10, 0.80), (0.40, 0.10, 1.00), "hand_R"),

    ("shoulder_L",  (-0.14, 0.00, 1.30), (-0.40, 0.00, 1.30), "chest"),
    ("upperarm_L",  (-0.40, 0.00, 1.30), (-0.40, 0.00, 1.10), "shoulder_L"),
    ("forearm_L",   (-0.40, 0.00, 1.10), (-0.40, 0.00, 0.90), "upperarm_L"),
    ("hand_L",      (-0.40, 0.00, 0.90), (-0.40, 0.00, 0.70), "forearm_L"),
    ("weapon_L",    (-0.40, 0.10, 0.80), (-0.40, 0.10, 1.00), "hand_L"),

    ("thigh_R",     (0.10, 0.00, 0.90), (0.10, 0.00, 0.60), "hips"),
    ("shin_R",      (0.10, 0.00, 0.60), (0.10, 0.00, 0.22), "thigh_R"),
    ("foot_R",      (0.10, 0.00, 0.20), (0.10, 0.12, 0.06), "shin_R"),
    ("toe_R",       (0.10, 0.12, 0.06), (0.10, 0.20, 0.06), "foot_R"),

    ("thigh_L",     (-0.10, 0.00, 0.90), (-0.10, 0.00, 0.60), "hips"),
    ("shin_L",      (-0.10, 0.00, 0.60), (-0.10, 0.00, 0.22), "thigh_L"),
    ("foot_L",      (-0.10, 0.00, 0.20), (-0.10, 0.12, 0.06), "shin_L"),
    ("toe_L",       (-0.10, 0.12, 0.06), (-0.10, 0.20, 0.06), "foot_L"),
]

BONE_PARENT = {b[0]: b[3] for b in RIG_BONES}
BONE_NAMES = [b[0] for b in RIG_BONES]


def _ancestors(bone):
    out = []
    p = BONE_PARENT.get(bone)
    while p:
        out.append(p)
        p = BONE_PARENT.get(p)
    return out


def related(a, b):
    return a == b or a in _ancestors(b) or b in _ancestors(a)


# ══ 部件 ════════════════════════════════════════════════════════════════════
class Part:
    __slots__ = ("name", "bone", "soft", "big", "cells", "extras", "feat",
                 "sleeve_cells", "lofts", "sheets", "step")

    def __init__(self, name, bone, soft=False, big=False, step=1):
        self.name = name
        self.bone = bone
        self.soft = soft
        self.big = big      # 超规格大件（长枪 / 长弓）：不参与总高与脚底判定
        self.step = step    # 每格占几个半格（LOD：2 = 一格抵两格，总尺寸不变）
        self.cells = {}      # (x,y,z) 半格整数 -> 颜色名
        self.extras = []     # (cx,cy,cz, sx,sy,sz, 颜色名) 盒心 + 盒尺寸（米）
        self.lofts = []      # (pts[世界米], 半宽列表, 半厚列表, 法向, 颜色) 连续放样带
        self.sheets = []     # (rows[点阵], 半厚, 法向, 颜色) 布片
        self.feat = []       # 语义标记（eye / mouth / cheek …），给 audit 用
        self.sleeve_cells = set()   # 本件里的套筒格（不做对齐检查）

    def bbox(self):
        if not self.cells and not self.extras and not self.lofts and not self.sheets:
            return None
        h = CELL * 0.5
        xs, ys, zs = [], [], []
        for (x, y, z) in self.cells:
            xs += [x * self.step, (x + 1) * self.step]
            ys += [y * self.step, (y + 1) * self.step]
            zs += [z * self.step, (z + 1) * self.step]
        for (cx, cy, cz, sx, sy, sz, _c) in self.extras:
            xs += [(cx - sx / 2) * 2, (cx + sx / 2) * 2]
            ys += [(cy - sy / 2) * 2, (cy + sy / 2) * 2]
            zs += [(cz - sz / 2) * 2, (cz + sz / 2) * 2]
        for (pts, ws, ts, _n, _c) in self.lofts:
            for p, w, t in zip(pts, ws, ts):
                r = max(w, t)
                xs += [(p[0] - r) / h, (p[0] + r) / h]
                ys += [(p[1] - r) / h, (p[1] + r) / h]
                zs += [(p[2] - r) / h, (p[2] + r) / h]
        for (rows, t, _n, _c) in self.sheets:
            for row in rows:
                for p in row:
                    xs += [(p[0] - t) / h, (p[0] + t) / h]
                    ys += [(p[1] - t) / h, (p[1] + t) / h]
                    zs += [(p[2] - t) / h, (p[2] + t) / h]
        return (min(xs) * h, min(ys) * h, min(zs) * h,
                max(xs) * h, max(ys) * h, max(zs) * h)

    def tri_est(self):
        n = 0
        for (x, y, z) in self.cells:
            for d in _DIRS:
                if (x + d[0], y + d[1], z + d[2]) not in self.cells:
                    n += 2
        n += 12 * len(self.extras)
        for (pts, _ws, _ts, _n, _c) in self.lofts:
            n += 8 * max(1, len(pts) - 1) + 4
        for (rows, _t, _n, _c) in self.sheets:
            n += 4 * max(1, len(rows) - 1) * max(1, len(rows[0]) - 1) + 4
        return n


_DIRS = ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))


class Grid:
    """格子画布。所有 box/put/cut/tint 的坐标都是**格**（半开区间、整数）。"""

    def __init__(self, name, team="联盟"):
        self.name = name
        self.team = team
        self.parts = {}
        self.order = []
        self._cur = None
        self.sleeves = {}      # joint -> (part, color)
        self.sleeve_cells = set()   # 套筒格（允许落在半格：它藏在子件里）
        self.notes = []
        self.zf_detail = []   # zfight 命中明细（部件对 + 首顶点），排查用
        # 本件专属的附加骨（人形基准 25 根之外）：只由需要的兵种填，
        # 例如弓箭手的弓弦上下两段（bow_up / bow_dn）。别的单位不加，
        # 骨架数量与验收口径不变。
        self.extra_bones = []

    def bone_names(self):
        return BONE_NAMES + [b[0] for b in self.extra_bones]

    # -- 部件 ---------------------------------------------------------------
    def part(self, name, bone, soft=False, big=False):
        if name not in self.parts:
            self.parts[name] = Part(name, bone, soft, big)
            self.order.append(name)
        self._cur = name
        return self.parts[name]

    def use(self, name):
        self._cur = name
        return self.parts[name]

    def _p(self, part):
        if part is None:
            assert self._cur, "没有当前部件：先 g.part(...)"
            return self.parts[self._cur]
        return self.parts[part] if isinstance(part, str) else part

    # -- 填 / 挖 / 换色（单位 = 格）------------------------------------------
    def box(self, x0, x1, y0, y1, z0, z1, color, part=None):
        self.fbox(x0 * 2, x1 * 2, y0 * 2, y1 * 2, z0 * 2, z1 * 2, color, part)

    def fbox(self, x0, x1, y0, y1, z0, z1, color, part=None):
        assert color in PAL, "未知颜色 %s" % color
        P = self._p(part)
        for x in range(int(x0), int(x1)):
            for y in range(int(y0), int(y1)):
                for z in range(int(z0), int(z1)):
                    P.cells[(x, y, z)] = color
        return P

    def put(self, x, y, z, color, part=None):
        return self.fput(x * 2, y * 2, z * 2, color, part)

    def fput(self, x, y, z, color, part=None):
        assert color in PAL, "未知颜色 %s" % color
        self._p(part).cells[(int(x), int(y), int(z))] = color

    def cut(self, x0, x1, y0, y1, z0, z1, part=None):
        return self.fcut(x0 * 2, x1 * 2, y0 * 2, y1 * 2, z0 * 2, z1 * 2, part)

    def fcut(self, x0, x1, y0, y1, z0, z1, part=None):
        P = self._p(part)
        for x in range(int(x0), int(x1)):
            for y in range(int(y0), int(y1)):
                for z in range(int(z0), int(z1)):
                    P.cells.pop((x, y, z), None)

    def tint(self, x0, x1, y0, y1, z0, z1, color, part=None):
        return self.ftint(x0 * 2, x1 * 2, y0 * 2, y1 * 2, z0 * 2, z1 * 2, color, part)

    def ftint(self, x0, x1, y0, y1, z0, z1, color, part=None):
        """只改区间内**已有**格的颜色，不增面。"""
        assert color in PAL
        P = self._p(part)
        for x in range(int(x0), int(x1)):
            for y in range(int(y0), int(y1)):
                for z in range(int(z0), int(z1)):
                    if (x, y, z) in P.cells:
                        P.cells[(x, y, z)] = color

    def mirror(self, part_from, part_to=None, bone_to=None, axis="x"):
        """左右镜像一个部件（队伍色左右对称，写完右边抄左边）。"""
        src = self._p(part_from)
        name = part_to or part_from.replace("_R", "_L")
        bone = bone_to or src.bone.replace("_R", "_L")
        dst = self.part(name, bone, src.soft, src.big)
        dst.step = src.step
        for (x, y, z), c in src.cells.items():
            dst.cells[((-x - 1) if axis == "x" else x, y, z)] = c
        for (x, y, z) in src.sleeve_cells:
            dst.sleeve_cells.add(((-x - 1) if axis == "x" else x, y, z))
        for (cx, cy, cz, sx, sy, sz, c) in src.extras:
            dst.extras.append(((-cx) if axis == "x" else cx, cy, cz, sx, sy, sz, c))
        for (pts, ws, ts, nrm, c) in src.lofts:
            mp = [((-p[0]) if axis == "x" else p[0], p[1], p[2]) for p in pts]
            mn = ((-nrm[0]) if axis == "x" else nrm[0], nrm[1], nrm[2])
            dst.lofts.append((mp, list(ws), list(ts), mn, c))
        for (rows, t, nrm, c) in src.sheets:
            mr = [[((-p[0]) if axis == "x" else p[0], p[1], p[2]) for p in row][::-1]
                  for row in rows]
            mn = ((-nrm[0]) if axis == "x" else nrm[0], nrm[1], nrm[2])
            dst.sheets.append((mr, t, mn, c))
        return dst

    # -- 亚格薄片（五官 / 图案 / 弓弦）---------------------------------------
    def slab(self, cx, cy, cz, sx, sy, sz, color, part=None):
        """盒心 + 尺寸，单位**格**（可小数）。只给五官和图案，不承重。"""
        assert color in PAL
        self._p(part).extras.append((cx, cy, cz, sx, sy, sz, color))

    # -- 连续放样带（弓臂 / 枪杆 / 枪刃 / 弓弦）-------------------------------
    def loft(self, pts, w, t, color, part=None, normal=(0.0, 1.0, 0.0), caps=True):
        """沿折线放样一根**连续**的方截面带子 —— 解决"叠盒子叠出鱼骨/闪烁"。

        `pts` 是世界坐标（米），`w` 是带子**面内半宽**（可给一个数或逐点列表），
        `t` 是沿 `normal` 的半厚。相邻环共享顶点，所以不会出现两片共面互相打架。

        为什么必须连续：v2 的弓是 46 片互相重叠的 slab（每片 0.11 高、间距 0.026），
        在浏览器里近共面的侧壁会闪，正视还是一条"木楼梯"。连续放样一次解决两件事。
        """
        assert color in PAL
        P = self._p(part)
        pts = [tuple(float(v) for v in p) for p in pts]
        n = len(pts)
        assert n >= 2
        ws = list(w) if isinstance(w, (list, tuple)) else [w] * n
        ts = list(t) if isinstance(t, (list, tuple)) else [t] * n
        assert len(ws) == n and len(ts) == n
        P.lofts.append((pts, ws, ts, tuple(normal), color))
        return P

    def sheet(self, grid, t, color, part=None, normal=(0.0, 1.0, 0.0)):
        """布片：二维点阵（行 × 列）+ 厚度 → 一张连续曲面。披风 / 旗面用它。

        `grid` = [[(x,y,z), …], …]，行从下到上、列从左到右。厚度沿 `normal`。
        """
        assert color in PAL
        P = self._p(part)
        rows = [[tuple(float(v) for v in p) for p in row] for row in grid]
        P.sheets.append((rows, t, tuple(normal), color))
        return P

    # -- 关节套筒 -----------------------------------------------------------
    def sleeve(self, joint, color, x0, x1, y0, y1, z0, z1, part=None):
        """套筒：父部件朝子件方向多伸出去的一圈，压暗两档。**必须在基准里预埋。**

        套筒允许落在半格（居中的 1 格套筒必然这样），所以它不进 ⑬ 的对齐检查。
        """
        P = self._p(part)
        before = set(P.cells)
        self.box(x0, x1, y0, y1, z0, z1, color, part)
        P.sleeve_cells |= (set(P.cells) - before)
        self.sleeves[joint] = (part or self._cur, color)
        return color

    # -- 网格化 -------------------------------------------------------------
    def _emit(self, P):
        """把一个部件的格子转成 (verts, faces, face_color)。"""
        cells = P.cells
        vmap = {}
        verts, faces, fcol = [], [], []

        def vid(p, c):
            k = (p, c)
            i = vmap.get(k)
            if i is None:
                i = len(verts)
                vmap[k] = i
                verts.append(p)
            return i

        for (x, y, z), c in sorted(cells.items()):
            h = CELL * 0.5
            a = (x * h * P.step, y * h * P.step, z * h * P.step)
            b = ((x + 1) * h * P.step, (y + 1) * h * P.step, (z + 1) * h * P.step)
            # 六个面：法线朝外，绕序交给 bmesh.recalc 兜底
            tab = (
                ((1, 0, 0), ((b[0], a[1], a[2]), (b[0], b[1], a[2]), (b[0], b[1], b[2]), (b[0], a[1], b[2]))),
                ((-1, 0, 0), ((a[0], a[1], a[2]), (a[0], a[1], b[2]), (a[0], b[1], b[2]), (a[0], b[1], a[2]))),
                ((0, 1, 0), ((a[0], b[1], a[2]), (a[0], b[1], b[2]), (b[0], b[1], b[2]), (b[0], b[1], a[2]))),
                ((0, -1, 0), ((a[0], a[1], a[2]), (b[0], a[1], a[2]), (b[0], a[1], b[2]), (a[0], a[1], b[2]))),
                ((0, 0, 1), ((a[0], a[1], b[2]), (b[0], a[1], b[2]), (b[0], b[1], b[2]), (a[0], b[1], b[2]))),
                ((0, 0, -1), ((a[0], a[1], a[2]), (a[0], b[1], a[2]), (b[0], b[1], a[2]), (b[0], a[1], a[2]))),
            )
            for d, quad in tab:
                if (x + d[0], y + d[1], z + d[2]) in cells:
                    continue
                faces.append(tuple(vid(p, c) for p in quad))
                fcol.append(c)

        for (cx, cy, cz, sx, sy, sz, c) in P.extras:
            x0, x1 = (cx - sx / 2) * CELL, (cx + sx / 2) * CELL
            y0, y1 = (cy - sy / 2) * CELL, (cy + sy / 2) * CELL
            z0, z1 = (cz - sz / 2) * CELL, (cz + sz / 2) * CELL
            base = len(verts)
            verts += [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
                      (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
            for q in ((0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1),
                      (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)):
                faces.append(tuple(base + i for i in q))
                fcol.append(c)

        # ── 连续放样带 ────────────────────────────────────────────────────
        for (pts, ws, ts, nrm, c) in P.lofts:
            nrm = Vector(nrm).normalized()
            rings = []
            n = len(pts)
            for i, p in enumerate(pts):
                p = Vector(p)
                if i == 0:
                    tan = Vector(pts[1]) - p
                elif i == n - 1:
                    tan = p - Vector(pts[n - 2])
                else:
                    tan = Vector(pts[i + 1]) - Vector(pts[i - 1])
                if tan.length < 1e-9:
                    tan = Vector((0, 0, 1))
                tan.normalize()
                side = nrm.cross(tan)
                if side.length < 1e-6:
                    side = Vector((1, 0, 0)) if abs(tan.x) < 0.9 else Vector((0, 1, 0))
                side.normalize()
                w, t = ws[i], ts[i]
                rings.append([p - side * w - nrm * t, p + side * w - nrm * t,
                              p + side * w + nrm * t, p - side * w + nrm * t])
            base = len(verts)
            for r in rings:
                verts += [tuple(v) for v in r]
            for i in range(n - 1):
                a0, b0 = base + i * 4, base + (i + 1) * 4
                for k in range(4):
                    k2 = (k + 1) % 4
                    faces.append((a0 + k, a0 + k2, b0 + k2, b0 + k))
                    fcol.append(c)
            # 两端封口（端盖一律塞进母件 1 cm，所以看不见，但封闭壳才能让
            # recalc_face_normals 判对朝外方向）
            faces.append((base + 3, base + 2, base + 1, base + 0))
            fcol.append(c)
            e = base + (n - 1) * 4
            faces.append((e + 0, e + 1, e + 2, e + 3))
            fcol.append(c)
        # ── 布片（二维点阵）──────────────────────────────────────────────
        for (rows, t, nrm, c) in P.sheets:
            nrm = Vector(nrm).normalized()
            R, C = len(rows), len(rows[0])
            base = len(verts)
            for row in rows:
                for p in row:
                    p = Vector(p)
                    verts.append(tuple(p - nrm * t))
                    verts.append(tuple(p + nrm * t))
            for i in range(R - 1):
                for j in range(C - 1):
                    a = base + (i * C + j) * 2
                    b = base + ((i + 1) * C + j) * 2
                    # 正面（-nrm 侧）
                    faces.append((a, a + 2, b + 2, b))
                    fcol.append(c)
                    # 背面（+nrm 侧）
                    faces.append((a + 1, b + 1, b + 3, a + 3))
                    fcol.append(c)
            # 边缘封口（四圈）
            def seal(pairs):
                for a, b in pairs:
                    faces.append((a, a + 1, b + 1, b))
                    fcol.append(c)
            seal([(base + j * 2, base + (j + 1) * 2) for j in range(C - 1)])
            off = base + (R - 1) * C * 2
            seal([(off + j * 2, off + (j + 1) * 2) for j in range(C - 1)])
            for i in range(R - 1):
                a = base + (i * C) * 2
                b = base + ((i + 1) * C) * 2
                seal([(a, b)])
                a = base + (i * C + C - 1) * 2
                b = base + ((i + 1) * C + C - 1) * 2
                seal([(a, b)])
        return verts, faces, fcol

    def build(self, name=None, prefix="unit", parents=True):
        """把所有部件合成**一个** mesh（3 材质槽、POINT 顶点色、刚性顶点组）。"""
        assert self.parts, "空网格"
        verts, faces, fcol, vbone = [], [], [], []
        self.part_v = {}
        for pn in self.order:
            P = self.parts[pn]
            if not P.cells and not P.extras and not P.lofts and not P.sheets:
                continue
            v, f, c = self._emit(P)
            off = len(verts)
            self.part_v[pn] = (off, off + len(v))
            verts += v
            faces += [tuple(i + off for i in q) for q in f]
            fcol += c
            vbone += [P.bone] * len(v)

        me = bpy.data.meshes.new((name or self.name) + "_mesh")
        me.from_pydata(verts, [], faces)
        me.validate(verbose=False)
        for i, poly in enumerate(me.polygons):
            poly.use_smooth = False

        # 法线兜底（每个闭合壳朝外）—— 必须在写颜色之前做，bmesh 往返会重建属性层
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        bm.to_mesh(me)
        bm.free()
        me.update()

        ob = bpy.data.objects.new(name or (prefix + "_body"), me)
        bpy.context.scene.collection.objects.link(ob)

        # 材质三槽（顺序固定，slot 索引 = SLOTS 的索引）
        for mname in SLOTS:
            me.materials.append(get_mat(mname))

        # 面 -> 材质槽
        for i, c in enumerate(fcol):
            me.polygons[i].material_index = SLOTS.index(PAL[c][0])

        # 顶点色（线性空间）
        attr = me.color_attributes.new(name="Col", type="FLOAT_COLOR", domain="POINT")
        self.vinfo = []          # 每个顶点 (槽, 倍数或 None)
        # 逐顶点颜色：用顶点 -> 颜色的表（同一顶点只属于一个面组）
        vcol_name = {}
        for poly, c in zip(me.polygons, fcol):
            for vi in poly.vertices:
                vcol_name.setdefault(vi, c)
        for vi in range(len(me.vertices)):
            c = vcol_name[vi]
            slot, val = PAL[c]
            if slot == "主体":
                attr.data[vi].color = (*lin(val), 1.0)
                self.vinfo.append(("主体", None))
            else:
                k = float(val)
                attr.data[vi].color = (k, k, k, 1.0)
                self.vinfo.append((slot, k))

        # 顶点组（刚性 1.0）
        groups = {}
        for bone in self.bone_names():
            idx = [i for i, b in enumerate(vbone) if b == bone]
            if idx:
                groups[bone] = ob.vertex_groups.new(name=bone)
                groups[bone].add(idx, 1.0, "REPLACE")

        me["vox_team"] = self.team
        ob["vox_parts"] = {k: list(v) for k, v in self.part_v.items()}
        self.ob = ob
        return ob

    # -- 预览上色 -----------------------------------------------------------
    def bake_preview(self, ob=None, team_hex=None, trim_hex=None):
        """把 team / team_trim 的倍数乘上阵营色 —— 只给渲染用，GLB 里保持中性。"""
        ob = ob or self.ob
        tm = lin(team_hex or TEAM[self.team][0])
        tr = lin(trim_hex or TEAM[self.team][1])
        attr = ob.data.color_attributes["Col"]
        for vi, (slot, k) in enumerate(self.vinfo):
            if slot == "主体":
                continue
            base = tm if slot == "team" else tr
            attr.data[vi].color = (base[0] * k, base[1] * k, base[2] * k, 1.0)
        ob.data.update()
        return ob

    # -- 骨架 ---------------------------------------------------------------
    def build_rig(self, name="RIG"):
        arm = bpy.data.armatures.new(name)
        ob = bpy.data.objects.new(name, arm)
        bpy.context.scene.collection.objects.link(ob)
        bpy.context.view_layer.objects.active = ob
        ob.select_set(True)
        bpy.ops.object.mode_set(mode="EDIT")
        for row in RIG_BONES:
            bn, head, tail, parent = row
            eb = arm.edit_bones.new(bn)
            eb.head = Vector(head)
            eb.tail = Vector(tail)
            eb.roll = 0.0
            eb.use_connect = False
        for row in RIG_BONES:
            bn, _h, _t, parent = row
            if parent:
                arm.edit_bones[bn].parent = arm.edit_bones[parent]
        for row in self.extra_bones:
            bn, head, tail, parent = row
            eb = arm.edit_bones.new(bn)
            eb.head = Vector(head)
            eb.tail = Vector(tail)
            eb.roll = 0.0
            eb.use_connect = False
            if parent and parent in arm.edit_bones:
                arm.edit_bones[bn].parent = arm.edit_bones[parent]
        bpy.ops.object.mode_set(mode="OBJECT")
        ob.show_in_front = True
        return ob

    def bind(self, arm, ob=None):
        ob = ob or self.ob
        ob.parent = arm
        ob.matrix_parent_inverse = arm.matrix_world.inverted()
        m = ob.modifiers.new("Armature", "ARMATURE")
        m.object = arm
        m.use_vertex_groups = True
        return arm

    # -- 自检（⑬⑭⑮ 纯整数，不用渲染）--------------------------------------
    def audit(self):
        rep = dict(name=self.name, parts=len(self.order), tris=0, cells=0)
        bad = []
        # ⑬ 包围盒 / 总高
        zs_min, zs_max = 1e9, -1e9
        offgrid = 0
        for pn in self.order:
            P = self.parts[pn]
            if P.big:
                continue
            xs, ys, zc = set(), set(), set()
            for (x, y, z) in P.cells:
                if (x, y, z) in P.sleeve_cells:
                    continue
                zs_min = min(zs_min, z)
                zs_max = max(zs_max, z + 1)
                xs |= {x, x + 1}
                ys |= {y, y + 1}
                zc |= {z, z + 1}
            if P.soft or P.big or not xs:
                continue
            # 硬部件的**外边界**必须落在 0.1 格上（内部 0.05 台阶是装箱用的，看不见）
            if any(v % 2 for v in (min(xs), max(xs), min(ys), max(ys),
                                   min(zc), max(zc))):
                offgrid += 1
                print("   [offgrid] %-12s %s" % (P.name, (min(xs), max(xs),
                                                          min(ys), max(ys),
                                                          min(zc), max(zc))))
        rep["z_cells"] = (zs_max - zs_min) / 2.0
        rep["offgrid"] = offgrid
        if offgrid:
            bad.append("OFFGRID %d" % offgrid)
        if abs(rep["z_cells"] - HEIGHT_CELLS) > 1e-6:
            bad.append("HEIGHT %s" % rep["z_cells"])
        # 脚底 z=0
        rep["ground"] = zs_min == 0
        if not rep["ground"]:
            bad.append("GROUND %s" % zs_min)
        # ⑭ 孤立方块
        iso = 0
        for pn in self.order:
            P = self.parts[pn]
            for c in P.cells:
                if not any((c[0] + d[0], c[1] + d[1], c[2] + d[2]) in P.cells for d in _DIRS):
                    iso += 1
        rep["isolated"] = iso
        if iso:
            bad.append("ISOLATED %d" % iso)
        # ⑮ 非父子部件穿模：**逐格求交**（AABB 会把"擦边"误判成穿模）
        boxes = {}
        for pn in self.order:
            P = self.parts[pn]
            bb = P.bbox()
            if bb:
                boxes[pn] = (bb, P.bone)
        cross = []
        names = list(boxes)
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                a, ba = boxes[names[i]]
                b, bb_ = boxes[names[j]]
                if related(ba, bb_):
                    continue
                ox = min(a[3], b[3]) - max(a[0], b[0])
                oy = min(a[4], b[4]) - max(a[1], b[1])
                oz = min(a[5], b[5]) - max(a[2], b[2])
                if ox <= 1e-4 or oy <= 1e-4 or oz <= 1e-4:
                    continue
                n = self._overlap(names[i], names[j])
                if n:
                    cross.append((names[i], names[j], n))
        rep["cross"] = cross
        if cross:
            bad.append("CROSS %d" % len(cross))
        # 套筒覆盖
        rep["sleeves"] = "%d/4" % len([j for j in ("shoulder", "elbow", "hip", "knee")
                                       if j in self.sleeves])
        if len([j for j in ("shoulder", "elbow", "hip", "knee") if j in self.sleeves]) < 4:
            bad.append("SLEEVE " + rep["sleeves"])
        # 面数 / 格子数
        rep["tris"] = sum(self.parts[p].tri_est() for p in self.order)
        rep["cells"] = sum(len(self.parts[p].cells) for p in self.order)
        rep["bad"] = bad
        return rep

    def _overlap(self, na, nb):
        # 大件（长枪 / 长弓）按规范 v1.2 不参与 ⑮：它们跨在身体外侧，
        # 静止姿态下"枪尖/弓梢擦到腿"不是模型错位，是绑定姿势（每个动作都会摆开）。
        if self.parts[na].big or self.parts[nb].big:
            return 0
        """两个部件真正的重叠格数。

        格×格用精确集合求交；**薄片（extras）改用精确浮点 AABB** ——
        旧版拿"半格粒度"去套薄片，会把 3 cm 的间隙也算成相交（v2 的弓就吃过这个
        假阳性：`CROSS 3` 全是误判）。这里留 5 mm 容差，比"贴住"略严。
        """
        A, B_ = self.parts[na], self.parts[nb]
        n = len(set(A.cells) & set(B_.cells))
        e = 0.10                       # 半格单位 = 5 mm

        def ex(e_):
            cx, cy, cz, sx, sy, sz, _c = e_          # 薄片尺寸用格，格子索引用半格
            return ((cx - sx / 2) * 2, (cx + sx / 2) * 2,
                    (cy - sy / 2) * 2, (cy + sy / 2) * 2,
                    (cz - sz / 2) * 2, (cz + sz / 2) * 2)

        for e_ in A.extras:
            x0, x1, y0, y1, z0, z1 = ex(e_)
            for (x, y, z) in B_.cells:
                if (x0 < x + 1 - e and x1 > x + e and y0 < y + 1 - e and
                        y1 > y + e and z0 < z + 1 - e and z1 > z + e):
                    n += 1
        for e_ in B_.extras:
            x0, x1, y0, y1, z0, z1 = ex(e_)
            for (x, y, z) in A.cells:
                if (x0 < x + 1 - e and x1 > x + e and y0 < y + 1 - e and
                        y1 > y + e and z0 < z + 1 - e and z1 > z + e):
                    n += 1
        return n

    # -- 共面闪烁检测（z-fighting 的唯一真判据）--------------------------------
    def zfight(self, tol=0.0012, margin=0.0012, cap=400):
        """找"两片面几乎共面且互相覆盖"的对数 —— 这就是浏览器里武器乱闪的原因。

        判据：法线夹角 < 1.5°，沿法线的距离 < tol（1.2 mm），且两面在平面内的投影
        互相覆盖 > margin（1.2 mm）。同一部件相邻格之间的面在 `_emit` 里已经剔除，
        所以这里抓到的都是真问题（叠 slab / 放样带穿薄片 / 贴片共面）。

        返回 (总对数, [(部件A, 部件B, 对数), …])，按对数降序。
        """
        ob = self.ob
        me = ob.data
        me.calc_loop_triangles()
        # 埋在其他壳里面的面不可能"闪"（背面剔除一开根本画不出来），
        # 先给每个面做一次"是否在实体表面"的判定，再只比对露在外面的面。
        from mathutils.bvhtree import BVHTree
        tri_v = [tuple(t.vertices) for t in me.loop_triangles]
        co = [v.co.copy() for v in me.vertices]
        bvh = BVHTree.FromPolygons(co, tri_v, all_triangles=True)

        def inside(p):
            n, d = 0, Vector((0.5773, 0.5774, 0.5772))
            q = p.copy()
            for _ in range(9):
                hit = bvh.ray_cast(q, d)
                if hit[0] is None:
                    break
                n += 1
                q = hit[0] + d * 0.0004
            return n % 2 == 1

        parts = self.part_v or {}
        owner = {}
        bone_of = {}
        for pn, (a, b) in parts.items():
            bone_of[pn] = self.parts[pn].bone
            for i in range(int(a), int(b)):
                owner[i] = pn
        polys = []
        for poly in me.polygons:
            n = poly.normal.copy()
            if n.length < 1e-9:
                continue
            n.normalize()
            c = poly.center.copy()
            d = n.dot(c)
            vs = [me.vertices[i].co.copy() for i in poly.vertices]
            buried = inside(c + n * 0.0015)
            polys.append((n, d, vs, owner.get(poly.vertices[0], "?"),
                          set(poly.vertices), buried))
        # 平面哈希：法线量化到 1.5°，距离量化到 tol
        buckets = {}
        for idx, (n, d, _vs, _p, _vi, _b) in enumerate(polys):
            key = (round(n.x, 2), round(n.y, 2), round(n.z, 2), int(round(d / tol)))
            buckets.setdefault(key, []).append(idx)
        hits = {}
        seen = set()
        for idx, (n, d, vs, pn, vi, buried) in enumerate(polys):
            if buried:
                continue
            key = (round(n.x, 2), round(n.y, 2), round(n.z, 2), int(round(d / tol)))
            for kk in (key, (key[0], key[1], key[2], key[3] + 1),
                       (key[0], key[1], key[2], key[3] - 1)):
                for j in buckets.get(kk, ()):
                    if j <= idx:
                        continue
                    n2, d2, vs2, pn2, vi2, b2 = polys[j]
                    if b2:
                        continue
                    if vi & vi2:
                        continue          # 共顶点的相邻面不是闪烁，是同一条带子的邻居
                    if abs(n.dot(n2) - 1.0) > 4e-4:
                        continue
                    if abs(d - d2) > tol:
                        continue
                    # 平面内投影（去掉法线主轴）
                    ax = max(range(3), key=lambda i: abs(n[i]))
                    u, v = [i for i in range(3) if i != ax]
                    p1 = [(p[u], p[v]) for p in vs]
                    p2 = [(p[u], p[v]) for p in vs2]
                    ox = min(max(a[0] for a in p1), max(a[0] for a in p2)) - \
                        max(min(a[0] for a in p1), min(a[0] for a in p2))
                    oy = min(max(a[1] for a in p1), max(a[1] for a in p2)) - \
                        max(min(a[1] for a in p1), min(a[1] for a in p2))
                    if ox > margin and oy > margin:
                        if pn != pn2 and related(bone_of.get(pn), bone_of.get(pn2)):
                            continue      # 父子部件（套筒/握在手里的武器）允许互相含着
                        k = tuple(sorted((pn, pn2)))
                        hits[k] = hits.get(k, 0) + 1
                        seen.add((idx, j))
                        self.zf_detail.append((pn, pn2, tuple(round(v, 3) for v in vs[0]),
                                               tuple(round(v, 3) for v in vs2[0])))
        rows = sorted(((a, b, n) for (a, b), n in hits.items()),
                      key=lambda r: -r[2])
        return len(seen), rows[:cap]

    # -- 队色占比（正视图投影，按 +Y 朝前的外露面算）------------------------
    def team_ratio(self):
        """正视图投影：沿 −Y 方向取每个 (x,z) 列最靠前的那个面，这才是镜头看到的面积。"""
        hw = CELL * 0.5
        mask = {}

        def poke(x, z, y, slot):
            k = (x, z)
            cur = mask.get(k)
            if cur is None or y > cur[0]:
                mask[k] = (y, slot)

        for pn in self.order:
            P = self.parts[pn]
            if P.big:                 # 大件（长枪 / 长弓）不进队色口径：它不参与"兵种识别"
                continue
            for (x, y, z), c in P.cells.items():
                poke(x, z, y, PAL[c][0])
            for (cx, cy, cz, sx, sy, sz, c) in P.extras:
                x0, x1 = (cx - sx / 2) * 2, (cx + sx / 2) * 2
                z0, z1 = (cz - sz / 2) * 2, (cz + sz / 2) * 2
                for x in range(int(math.floor(x0)), int(math.ceil(x1))):
                    for z in range(int(math.floor(z0)), int(math.ceil(z1))):
                        poke(x, z, cy * 2, PAL[c][0])
        tot = len(mask)
        team = sum(1 for v in mask.values() if v[1] in ("team", "team_trim"))
        return team / max(1, tot)

    # -- LOD（从格子降采样，禁止 mesh decimate）-----------------------------
    def lod(self, level=1):
        """level 1：2×2×2 并一块（一格抵两格）；level 2：4×4×4 并一块。

        **总尺寸不变**是这个函数的唯一正确语义 —— v3 的第一版把坐标除以 2 却
        忘了把格子放大，结果中档 LOD 是个半尺寸的小人：骨架还是 1.7 m、贴片
        （extras）和放样件（枪 / 弓 / 披风）保持原尺寸，三样各在各的坐标系里，
        渲染出来就是"一堆漂浮的板片"。现在改成 `Part.step`：

          * 格块合并后索引减半（x//2），但每块**占两个半格**（step=2）；
          * extras / lofts / sheets 是亚格细节，坐标本来就是世界米 / 格，
            一律原样复制，不缩放（它们比一格小，缩放才会错位）。

        细节件的取舍：`step` 越大，格块越"胖"，薄贴片会被吞进格块里。所以
        level 2 丢掉"薄贴片"（五官、缝线、护腕高光这类 1~2 px 的东西），
        保留有体积的（腰扣、箭羽）。

        **两档都用 step=2**：试过 level 2 用 3（0.15 m 格），手臂的格块会胖到
        0.6~0.45 一格，正好把挂在身侧的弓吞进去 —— 远档变成一个"没有弓的弓箭手"。
        远档省面靠丢贴片，不靠把格块再放大。
        """
        step = 2
        out = Grid(self.name + "_L%d" % level, self.team)
        out.extra_bones = list(self.extra_bones)
        for pn in self.order:
            P = self.parts[pn]
            Q = out.part(pn, P.bone, soft=P.soft, big=P.big)
            Q.step = step
            bucket = {}
            for (x, y, z), c in P.cells.items():
                bucket.setdefault((x // step, y // step, z // step), []).append(c)
            for k, cs in bucket.items():
                Q.cells[k] = max(set(cs), key=cs.count)
            for e in P.extras:
                if level >= 2 and min(e[3], e[4], e[5]) < 0.45:
                    continue          # 薄贴片：远档看不见，留着还会和格块打架
                Q.extras.append(e)
            # 弧线件（放样带 / 布片）本来就是低面数的曲线，LOD 不动它；
            # 但它们挂在部件上，不复制就会在降采样里整件消失（弓、披风）。
            Q.lofts += list(P.lofts)
            Q.sheets += list(P.sheets)
            Q.sleeve_cells = set(P.sleeve_cells)
        out.sleeves = dict(self.sleeves)
        return out

    def report(self):
        r = self.audit()
        print("[vox] %-8s parts=%d cells=%d tris≈%d z=%.0f格 sleeves=%s team=%.1f%%"
              % (r["name"], r["parts"], r["cells"], r["tris"], r["z_cells"],
                 r["sleeves"], 100 * self.team_ratio()))
        if r["bad"]:
            print("[vox] !! %s" % r["bad"])
        for c in r["cross"]:
            print("   [cross]", c)
        return r


# ══ 材质 ════════════════════════════════════════════════════════════════════
_MAT_CFG = {"主体": (0.62, 0.22), "team": (0.66, 0.10), "team_trim": (0.44, 0.55)}


def get_mat(name):
    m = bpy.data.materials.get(name)
    if m and "vox" in m.keys():
        return m
    m = m or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    vc = nt.nodes.new("ShaderNodeVertexColor")
    vc.layer_name = "Col"
    nt.links.new(vc.outputs["Color"], b.inputs["Base Color"])
    rough, metal = _MAT_CFG.get(name, (0.6, 0.1))
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    nt.links.new(b.outputs["BSDF"], out.inputs["Surface"])
    m["vox"] = 1
    m.diffuse_color = (0.8, 0.8, 0.8, 1)
    # 封闭体必须背面剔除：不剔的话"眼睛贴片的背面"和"脸的前面"同深度互相打架，
    # 表现就是脸上/武器上一闪一闪的点（v3 查了三天才定位到这一条）。
    m.use_backface_culling = True
    return m


# ══ 描边（反向外壳，只在预览 / 图标里加）════════════════════════════════════
def outline(ob, width=0.02, color="#241C2C", arm=None):
    """复制一份网格、沿顶点法线外推 width、翻面 → Setsuna 式外描边。

    只给渲染：GLB 里不要它（材质固定三槽，多一个材质就多一个 draw call）。
    传了 arm 就一起绑骨架 —— 不绑的话一摆姿势外壳会留在原地（黑刺）。
    """
    me = ob.data.copy()
    ol = bpy.data.objects.new(ob.name + "_oline", me)
    bpy.context.scene.collection.objects.link(ol)
    ol.matrix_world = ob.matrix_world.copy()
    if arm is not None:
        ol.parent = arm
        ol.matrix_parent_inverse = arm.matrix_world.inverted()
        md = ol.modifiers.new("Armature", "ARMATURE")
        md.object = arm
        md.use_vertex_groups = True
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.normal_update()
    for v in bm.verts:
        v.co += v.normal * width
    bmesh.ops.reverse_faces(bm, faces=list(bm.faces))
    bm.to_mesh(me)
    bm.free()
    m = bpy.data.materials.get("vox_outline")
    if m is None:
        m = bpy.data.materials.new("vox_outline")
    m.use_nodes = True
    # 按类型找 BSDF，不按名字 —— 中文界面下节点叫"原理化 BSDF"（老代码在这里炸过）
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*lin(color), 1.0)
    b.inputs["Roughness"].default_value = 1.0
    b.inputs["Metallic"].default_value = 0.0
    try:
        m.use_backface_culling = True
    except Exception:
        pass
    me.materials.clear()
    me.materials.append(m)
    for p in me.polygons:
        p.material_index = 0
    return ol


# ══ 导出 ════════════════════════════════════════════════════════════════════
def export_glb(path, objs, anim=True, extra=()):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    keep = {o.name for o in list(objs) + list(extra)}
    for ob in list(bpy.data.objects):
        if ob.name not in keep:
            bpy.data.objects.remove(ob, do_unlink=True)
    bpy.ops.object.select_all(action="DESELECT")
    for ob in list(objs) + list(extra):
        ob.select_set(True)
    bpy.context.view_layer.objects.active = list(objs)[0]
    bpy.context.scene.render.fps = 30
    bpy.ops.export_scene.gltf(
        filepath=path, export_format="GLB", use_selection=True,
        export_apply=False, export_yup=True, export_texcoords=False,
        export_normals=True, export_materials="EXPORT",
        export_image_format="AUTO", export_skins=True,
        export_animations=anim, export_animation_mode="ACTIONS",
        export_nla_strips=False, export_bake_animation=False,
        export_force_sampling=True, export_anim_slide_to_zero=True,
        export_optimize_animation_size=False, export_anim_single_armature=True,
        export_def_bones=False, export_morph=False,
    )
    bpy.ops.object.select_all(action="DESELECT")
    print("[out]", os.path.basename(path), os.path.getsize(path) // 1024, "KB")
    return os.path.getsize(path)


# ══ 身体最低点（排除武器）════════════════════════════════════════════════════
# 死倒判定要排除的**部件**（不是骨）：武器、披风、箭筒这些"挂件"都是 100% 单骨刚性壳，
# 躯干一俯仰它们就甩到地面以下 —— 但它们戳地只是难看，人不该被它们抬起来。
PROP_PARTS = ("bow", "arrow", "spear", "cape", "quiver", "quiver_arrows", "sack",
              "bowstring_up", "bowstring_dn")


def vert_bone(ob):
    """每个顶点属于哪根骨（取权重最大的组），顺序和 mesh.vertices 一致。"""
    gi = {g.index: g.name for g in ob.vertex_groups}
    out = []
    for v in ob.data.vertices:
        if not v.groups:
            out.append(None)
            continue
        g = max(v.groups, key=lambda x: x.weight)
        out.append(gi.get(g.group))
    return out


def body_min_z(ob, v2b=None, skip=PROP_PARTS):
    """变形后**身体**的最低点 —— 武器和披风不算。

    为什么必须分开：死倒时弓/枪一定会有一头戳进地里，披风又是 100% 单骨刚性壳
    （躯干一俯仰，下摆就甩到地面以下 0.37 m）。拿"全模型最低点"去兜底抬人，
    抬起来的是**人**，于是"倒在地上"变成"悬在半空"——v1 的两个兵种都是这么错的。
    武器戳地 / 披风穿地最多难看，人悬空是错的。
    """
    parts = ob.get("vox_parts") or {}
    bad = set()
    for pn, (a, b) in parts.items():
        if pn in skip:
            bad.update(range(int(a), int(b)))
    dg = bpy.context.evaluated_depsgraph_get()
    oe = ob.evaluated_get(dg)
    me = oe.to_mesh()
    mw = oe.matrix_world
    z = 1e9
    for i, v in enumerate(me.vertices):
        if i in bad:
            continue
        zz = (mw @ v.co).z
        if zz < z:
            z = zz
    oe.to_mesh_clear()
    return z
