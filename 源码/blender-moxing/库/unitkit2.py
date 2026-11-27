"""unitkit2.py —— 精模单位（低模 cage + 曲面细分）的几何 / 材质 / 组件装配。

与 unitkit.py（方块人）**并行存在、互不影响**：

    对比项        unitkit.py（方块人）              unitkit2.py（本文件）
    截面          4 点方截面                       8 / 12 点圆润截面
    着色          平面 smooth=False               细分后 smooth=True
    材质          单人色板图集，统一粗糙度          每材质独立 metallic / roughness
    装配          按材质合并                       **按模块合并**（可整组摘换）
    低模档        去倒角                          **关细分**（cage 本身就是低模）

设计口径沿用资产库老规矩：
  * 1 unit = 1 m；+Y 正面；脚底 z = 0；原点在双足中间。
  * 一块 = 一根骨、权重 1.0（刚性蒙皮）；关节留缝，缝里塞更细的深色套筒。
  * **倒角与细分永不叠加**（倒角后的边再被 CC 乘 4，边会碎）。

造型笔触（`style=`）—— 分**两级语言**，混用比例决定"圆"还是"硬"：

  硬边系（v2 主力，和方块人一家的平面语言）
    facet   纯低模面：不细分不倒角，平面着色 —— 剪影最硬的一档
    chunk   单段倒角 6 mm：面上全是平面，只有棱上一条高光 —— "精致"从这里来
    chunk2  两段倒角 13 mm：大件甲板
    chunk3  两段倒角 24 mm：超大件（傀儡的板甲/靴）
    sharp   薄刃 / 纯几何 —— 完全不处理，用来压住其它面的圆

  圆润系（只在"必须真的圆"的地方用，别整件都 soft）
    soft    Catmull-Clark 1 级 + 平滑
    soft2   2 级（球面/盔顶）
    plate   倒角 2 段 + 平面（旧口径，保留兼容）
    plate2  倒角 3 段 + 平面
    hard    倒角 2 段 + 平面（小五金）

判据（越靠上越"硬"）：`facet > chunk > chunk2 > soft`。
一件单位里 soft 类的前提要控制在 15% 以下，否则整件会读成"软胶玩具"。
"""
import math
import os
import sys

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import unitkit as K  # noqa: E402  （只借它的 box / loft / plate / frame，不动它的材质）

STYLE = {
    #            bevel   seg  sub  smooth
    "facet":   (0.000,  0,   0,   False),
    "chunk":   (0.006,  1,   0,   False),
    "chunk2":  (0.013,  2,   0,   False),
    "chunk3":  (0.024,  2,   0,   False),
    "soft":    (0.000,  0,   1,   True),
    "soft2":   (0.000,  0,   2,   True),
    "plate":   (0.007,  2,   0,   False),
    "plate2":  (0.012,  3,   0,   False),
    "hard":    (0.003,  2,   0,   False),
    "sharp":   (0.000,  0,   0,   False),
}


def srgb(hexstr):
    return K.srgb(hexstr)


def make_mat(name, hexcol, metal=0.0, rough=0.65, emit=None, estr=0.0,
             alpha=1.0, coat=0.0):
    """一件一材质的 Principled：颜色 sRGB → 线性，金属度/粗糙度逐件可调。"""
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    b.inputs["Base Color"].default_value = (*srgb(hexcol), 1.0)
    b.inputs["Metallic"].default_value = metal
    b.inputs["Roughness"].default_value = rough
    if "Coat Weight" in b.inputs:
        b.inputs["Coat Weight"].default_value = coat
        b.inputs["Coat Roughness"].default_value = 0.12
    if emit:
        b.inputs["Emission Color"].default_value = (*srgb(emit), 1.0)
        b.inputs["Emission Strength"].default_value = estr
    if alpha < 1.0:
        b.inputs["Alpha"].default_value = alpha
        try:
            m.surface_render_method = "BLENDED"
        except Exception:
            m.blend_method = "BLEND"
    nt.links.new(b.outputs["BSDF"], out.inputs["Surface"])
    m.diffuse_color = (*srgb(hexcol), alpha)
    return m


# ── 截面 ────────────────────────────────────────────────────────────────────
def rrect(w, d, r=0.0, nc=1):
    """圆角矩形环：4×(nc+1) 点。nc=1 → 8 点（细分 cage 的甜点）。"""
    hw, hd = w * 0.5, d * 0.5
    r = min(r, hw * 0.999, hd * 0.999)
    if r <= 1e-6:
        return [(-hw, -hd), (hw, -hd), (hw, hd), (-hw, hd)]
    pts = []
    for cx, cy, a0 in ((hw - r, hd - r, 0), (-(hw - r), hd - r, 90),
                       (-(hw - r), -(hd - r), 180), (hw - r, -(hd - r), 270)):
        for i in range(nc + 1):
            a = math.radians(a0 + 90.0 * i / nc)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def ngon(w, d, n=8, phase=0.0):
    return [(w * 0.5 * math.cos(phase + math.tau * k / n),
             d * 0.5 * math.sin(phase + math.tau * k / n)) for k in range(n)]


def octs(w, d, cw, cd=None):
    """八边倒角矩形（硬边系的主力截面）：四角各切掉 cw × cd。

    cw=0 → 回到 4 点纯方（配 `chunk` 倒角就是"倒角方块"）；
    cw≈0.22w → 读作"磨圆的方管"，法线一翻就是一条棱。
    比 rrect 少一半点，而且**没有圆弧**，细分关了也不会变成管子。
    """
    hw, hd = w * 0.5, d * 0.5
    cd = cw if cd is None else cd
    cw = max(0.0, min(cw, hw * 0.96))
    cd = max(0.0, min(cd, hd * 0.96))
    if cw <= 1e-6 and cd <= 1e-6:
        return [(-hw, -hd), (hw, -hd), (hw, hd), (-hw, hd)]
    return [(hw, -hd + cd), (hw, hd - cd),
            (hw - cw, hd), (-hw + cw, hd),
            (-hw, hd - cd), (-hw, -hd + cd),
            (-hw + cw, -hd), (hw - cw, -hd)]


# ── 放样 ────────────────────────────────────────────────────────────────────
def loft(name, rows, caps=True):
    return K.loft(name, rows, caps)


def tube(name, stations, nc=1):
    """stations = [(z, cx, cy, w, d, r)]，横截面为圆角矩形。"""
    rows = []
    for (z, cx, cy, w, d, r) in stations:
        rows.append([(cx + x, cy + y, z) for (x, y) in rrect(w, d, r, nc)])
    return loft(name, rows)


def limb(name, p0, p1, secs, up=(0, 0, 1), nc=1):
    """沿 p0→p1 的圆润肢体；secs = [(t, w, d, r)]，t 是 0..1 的轴向参数。"""
    p0v, ex, ey, ez = K.frame(p0, p1, up)
    L = (Vector(p1) - p0v).length
    rows = []
    for (t, w, d, r) in secs:
        c = p0v + ez * (L * t)
        rows.append([tuple(c + ex * x + ey * y) for (x, y) in rrect(w, d, r, nc)])
    return loft(name, rows)


def otube(name, stations, cw=0.02, cd=None):
    """八边倒角放样。stations = [(z, cx, cy, w, d)] 或 [(z, cx, cy, w, d, cw, cd)]。"""
    rows = []
    for st in stations:
        z, cx, cy, w, d = st[:5]
        a = st[5] if len(st) > 5 else cw
        b = st[6] if len(st) > 6 else (a if cd is None else cd)
        rows.append([(cx + x, cy + y, z) for (x, y) in octs(w, d, a, b)])
    return loft(name, rows)


def olimb(name, p0, p1, secs, up=(0, 0, 1)):
    """沿 p0→p1 的八边倒角肢体；secs = [(t, w, d, c)] 或 [(t, w, d, cw, cd)]。"""
    p0v, ex, ey, ez = K.frame(p0, p1, up)
    L = (Vector(p1) - p0v).length
    rows = []
    for st in secs:
        t, w, d = st[:3]
        c = st[3] if len(st) > 3 else 0.02
        c2 = st[4] if len(st) > 4 else c
        cc = p0v + ez * (L * t)
        rows.append([tuple(cc + ex * x + ey * y) for (x, y) in octs(w, d, c, c2)])
    return loft(name, rows)


def rivet(name, center, normal, r=0.014, h=0.010, n=8):
    """铆钉/轴销端盖：一段短棱柱，平面着色下就是一颗硬点。"""
    c = Vector(center)
    ez = Vector(normal).normalized()
    up = Vector((0, 0, 1)) if abs(ez.dot(Vector((0, 0, 1)))) < 0.95 else Vector((0, 1, 0))
    ex = up.cross(ez).normalized()
    ey = ez.cross(ex).normalized()
    rows = []
    for (o, rr) in ((0.0, r * 0.80), (h * 0.55, r), (h, r * 0.78)):
        rows.append([tuple(c + ez * o + ex * (rr * math.cos(math.tau * k / n))
                           + ey * (rr * math.sin(math.tau * k / n))) for k in range(n)])
    return K.loft(name, rows, True)


def capsule(name, p0, p1, r0, r1, nc=2, squash=1.0, end0=0.62, end1=0.62):
    """圆头胶囊：两端各内收一圈，CC 细分后是干净的圆头（不用球）。"""
    secs = [(0.00, r0 * 2 * end0, r0 * 2 * end0 * squash, 0.0),
            (0.10, r0 * 2 * 1.00, r0 * 2 * 1.00 * squash, 0.0),
            (0.55, (r0 * 0.45 + r1 * 0.55) * 2, (r0 * 0.45 + r1 * 0.55) * 2 * squash, 0.0),
            (0.90, r1 * 2 * 1.00, r1 * 2 * 1.00 * squash, 0.0),
            (1.00, r1 * 2 * end1, r1 * 2 * end1 * squash, 0.0)]
    return limb(name, p0, p1, secs, nc=nc)


# ── 曲面壳（甲片的主力）────────────────────────────────────────────────────
def grid_shell(name, grid, thick, inside=(0, 0, 0)):
    """把一张 (nv×nu) 的曲面格子加厚成闭合壳体。

    grid 每行是从一侧到另一侧的一组点（顺序一致即可，法线会自动朝外）。
    inside 是"壳内一点"，用来把法线统一翻到远离它的那一侧。
    """
    nv, nu = len(grid), len(grid[0])
    P = [[Vector(p) for p in row] for row in grid]
    C = Vector(inside)
    N = [[Vector((0, 0, 1)) for _ in range(nu)] for _ in range(nv)]
    for j in range(nv):
        for i in range(nu):
            du = P[j][min(i + 1, nu - 1)] - P[j][max(i - 1, 0)]
            dv = P[min(j + 1, nv - 1)][i] - P[max(j - 1, 0)][i]
            n = du.cross(dv)
            if n.length < 1e-9:
                n = P[j][i] - C
            n.normalize()
            if n.dot(P[j][i] - C) < 0:
                n = -n
            N[j][i] = n

    verts = []
    for layer in (1, -1):
        for j in range(nv):
            for i in range(nu):
                verts.append(tuple(P[j][i] + N[j][i] * (thick * 0.5 * layer)))

    def O(j, i):
        return j * nu + i

    def I(j, i):
        return nv * nu + j * nu + i

    faces = []
    for j in range(nv - 1):
        for i in range(nu - 1):
            faces.append((O(j, i), O(j, i + 1), O(j + 1, i + 1), O(j + 1, i)))
            faces.append((I(j, i), I(j + 1, i), I(j + 1, i + 1), I(j, i + 1)))
    for i in range(nu - 1):                       # 上下边
        faces.append((O(0, i + 1), O(0, i), I(0, i), I(0, i + 1)))
        faces.append((O(nv - 1, i), O(nv - 1, i + 1), I(nv - 1, i + 1), I(nv - 1, i)))
    for j in range(nv - 1):                       # 左右边
        faces.append((O(j, 0), O(j + 1, 0), I(j + 1, 0), I(j, 0)))
        faces.append((O(j + 1, nu - 1), O(j, nu - 1), I(j, nu - 1), I(j + 1, nu - 1)))
    return K._obj(name, verts, faces)


def arc_panel(name, stations, thick, nu=10, inside=None, center=(0.0, 0.0)):
    """绕竖轴的弧形甲片。stations = [(z, a0°, a1°, rx, ry)]（角度 0 = +Y 正前）。

    center 把整片平移到 (cx, cy) —— 左右腿甲必须各自偏移，否则两片会叠在中轴上。
    """
    cx, cy = center
    grid = []
    for st in stations:
        z, a0, a1, rx, ry = st[:5]
        cy_s = st[5] if len(st) > 5 else cy     # 第 6 项 = 该高度上的前后偏移
        row = []
        for i in range(nu + 1):
            a = math.radians(a0 + (a1 - a0) * i / nu)
            row.append((cx + rx * math.sin(a), cy_s + ry * math.cos(a), z))
        grid.append(row)
    return grid_shell(name, grid, thick, inside=inside or (cx, cy, 0))


def plate(name, pts, thickness=0.02, offset=0.0, axis="Y"):
    """2D 多边形挤出（沿用方块人的 plate，坐标约定一致）。"""
    return K.plate(name, pts, axis, thickness, offset)


def arc_band(name, p0, p1, r0, r1, a0, a1, nv=2, nu=6, thick=0.024,
             out_dir=(0, 1, 0), bulge=0.0):
    """绕骨轴的**开口**弧形甲片（护肩/臂甲/护胫的主力）。

    与 arc_panel 的分工：arc_panel 绕**竖轴**（裙甲、腰甲），arc_band 绕**任意骨轴**
    （肩甲、腿甲）。开口角以 out_dir 为 0°，所以 a0/a1 用 ±110 这类对称值即可。
    bulge 是中间外鼓量（0 = 纯锥面，读起来最硬）。
    """
    p0, p1 = Vector(p0), Vector(p1)
    ez = (p1 - p0).normalized()
    out = Vector(out_dir)
    out = (out - ez * out.dot(ez)).normalized()
    perp = ez.cross(out).normalized()
    L = (p1 - p0).length
    grid = []
    for j in range(nv + 1):
        t = j / nv
        r = r0 + (r1 - r0) * t + bulge * math.sin(math.pi * t)
        c = p0 + ez * (L * t)
        row = []
        for i in range(nu + 1):
            a = math.radians(a0 + (a1 - a0) * i / nu)
            row.append(tuple(c + out * (r * math.cos(a)) + perp * (r * math.sin(a))))
        grid.append(row)
    return grid_shell(name, grid, thick, inside=tuple((p0 + p1) * 0.5))


# ── 装配 ────────────────────────────────────────────────────────────────────
class Unit2:
    def __init__(self, name, mat_defs, low=False):
        self.name = name
        self.mat_defs = mat_defs          # {name: dict(hex=..., metal=..., rough=...)}
        self.low = low
        self.parts = []                   # dict(obj, bone, mat, bev, seg, sub, smooth, module)
        self.M = {k: make_mat(k, **v) for k, v in mat_defs.items()}

    # -- 加零件 -------------------------------------------------------------
    def add(self, ob, bone, mat, style="soft", module="body", tag=""):
        if self.low:
            bev, seg, sub, smooth = 0.0, 0, 0, False
        else:
            bev, seg, sub, smooth = STYLE[style]
        assert mat in self.M, "unknown material %s" % mat
        self.parts.append(dict(obj=ob, bone=bone, mat=mat, bev=bev, seg=seg,
                               sub=sub, smooth=smooth, module=module, tag=tag))
        return ob

    def box(self, name, center, size, bone, mat, rot=None, style="plate", module="body", tag=""):
        return self.add(K.box(name, center, size, rot), bone, mat, style, module, tag)

    def loft(self, name, rows, bone, mat, style="soft", module="body", tag=""):
        return self.add(loft(name, rows), bone, mat, style, module, tag)

    def tube(self, name, stations, bone, mat, style="soft", module="body", tag="", nc=1):
        return self.add(tube(name, stations, nc), bone, mat, style, module, tag)

    def limb(self, name, p0, p1, secs, bone, mat, style="soft", module="body", tag="", nc=1):
        return self.add(limb(name, p0, p1, secs, nc=nc), bone, mat, style, module, tag)

    def capsule(self, name, p0, p1, r0, r1, bone, mat, style="soft", module="body",
                tag="", nc=2, squash=1.0):
        return self.add(capsule(name, p0, p1, r0, r1, nc, squash), bone, mat,
                        style, module, tag)

    # -- 硬边系 -------------------------------------------------------------
    def otube(self, name, stations, bone, mat, style="chunk", module="body",
              tag="", cw=0.02, cd=None):
        return self.add(otube(name, stations, cw, cd), bone, mat, style, module, tag)

    def olimb(self, name, p0, p1, secs, bone, mat, style="chunk", module="body", tag=""):
        return self.add(olimb(name, p0, p1, secs), bone, mat, style, module, tag)

    def rivet(self, name, center, normal, bone, mat, style="hard", module="body",
              tag="", r=0.014, h=0.010, n=8):
        return self.add(rivet(name, center, normal, r, h, n), bone, mat,
                        style, module, tag)

    def shell(self, name, grid, thick, bone, mat, style="plate", module="body",
              tag="", inside=(0, 0, 0)):
        return self.add(grid_shell(name, grid, thick, inside), bone, mat, style, module, tag)

    def arc(self, name, stations, thick, bone, mat, style="plate", module="body",
            tag="", nu=10, inside=None, center=(0.0, 0.0)):
        return self.add(arc_panel(name, stations, thick, nu, inside, center), bone, mat,
                        style, module, tag)

    def band(self, name, p0, p1, r0, r1, a0, a1, bone, mat, style="chunk2",
             module="body", tag="", nv=2, nu=6, thick=0.024, out_dir=(0, 1, 0),
             bulge=0.0):
        return self.add(arc_band(name, p0, p1, r0, r1, a0, a1, nv, nu, thick,
                                 out_dir, bulge), bone, mat, style, module, tag)

    def plate(self, name, pts, bone, mat, thickness=0.02, offset=0.0, axis="Y",
              style="plate", module="body", tag=""):
        return self.add(plate(name, pts, thickness, offset, axis), bone, mat,
                        style, module, tag)

    # -- 收尾 ---------------------------------------------------------------
    def _apply(self, ob, bev, seg, sub, smooth):
        bpy.ops.object.select_all(action="DESELECT")
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        if bev and bev > 0:
            m = ob.modifiers.new("bev", "BEVEL")
            m.width = bev
            m.segments = max(1, seg)
            m.limit_method = "ANGLE"
            m.angle_limit = math.radians(58)
            m.harden_normals = False
            try:
                bpy.ops.object.modifier_apply(modifier=m.name)
            except Exception as e:
                print("[warn bevel]", ob.name, e)
        if sub and sub > 0:
            m = ob.modifiers.new("sub", "SUBSURF")
            m.levels = sub
            m.render_levels = sub
            m.use_limit_surface = True
            try:
                bpy.ops.object.modifier_apply(modifier=m.name)
            except Exception as e:
                print("[warn sub]", ob.name, e)
        for p in ob.data.polygons:
            p.use_smooth = smooth

    def finish(self, prefix="unit", join_by="module", verbose=False):
        meta = []
        for p in self.parts:
            ob = p["obj"]
            self._apply(ob, p["bev"], p["seg"], p["sub"], p["smooth"])
            ob.data.calc_loop_triangles()
            n = max(1, len(ob.data.vertices))
            c = sum((Vector(v.co) for v in ob.data.vertices), Vector()) / n
            meta.append(dict(tag=p["tag"] or ob.name, obj=ob.name, module=p["module"],
                             bone=p["bone"], material=p["mat"],
                             tris=len(ob.data.loop_triangles),
                             center=[round(v, 4) for v in c]))
            ob.data.materials.clear()
            ob.data.materials.append(self.M[p["mat"]])
            vg = ob.vertex_groups.new(name=p["bone"])
            vg.add(list(range(len(ob.data.vertices))), 1.0, "REPLACE")

        # 法线兜底（闭合体按体积定朝向）
        for p in self.parts:
            ob = p["obj"]
            bm = bmesh.new()
            bm.from_mesh(ob.data)
            bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
            if bm.calc_volume(signed=True) < 0:
                bmesh.ops.reverse_faces(bm, faces=list(bm.faces))
            bm.to_mesh(ob.data)
            bm.free()
            ob.data.update()

        self.meta = meta
        if join_by == "part":
            return [p["obj"] for p in self.parts]
        if verbose:
            rows = sorted(((m["tris"], m["tag"], m["module"], m["bone"]) for m in meta),
                          reverse=True)
            print("[parts] total %d, top:" % sum(r[0] for r in rows))
            for r in rows[:24]:
                print("   %5d  %-22s %-9s %s" % r)
        buckets = {}
        for p in self.parts:
            key = p["module"] if join_by == "module" else p["mat"]
            buckets.setdefault(key, []).append(p["obj"])
        out = []
        for key, objs in buckets.items():
            bpy.ops.object.select_all(action="DESELECT")
            for o in objs:
                o.select_set(True)
            bpy.context.view_layer.objects.active = objs[0]
            if len(objs) > 1:
                bpy.ops.object.join()
            j = bpy.context.view_layer.objects.active
            j.name = "%s_%s" % (prefix, key)
            j.data.name = j.name
            out.append(j)
        bpy.ops.object.select_all(action="DESELECT")
        return out

    def bind(self, arm, objs):
        for ob in objs:
            ob.parent = arm
            ob.matrix_parent_inverse = arm.matrix_world.inverted()
            m = ob.modifiers.new("Armature", "ARMATURE")
            m.object = arm
            m.use_vertex_groups = True
        return arm


def stats(objs):
    tris = 0
    mn = Vector((1e9,) * 3)
    mx = Vector((-1e9,) * 3)
    for o in objs:
        o.data.calc_loop_triangles()
        tris += len(o.data.loop_triangles)
        for v in o.data.vertices:
            p = o.matrix_world @ v.co
            for i in range(3):
                mn[i] = min(mn[i], p[i])
                mx[i] = max(mx[i], p[i])
    return tris, mn, mx


def build_rig(bones, name):
    arm = bpy.data.armatures.new(name)
    ob = bpy.data.objects.new(name, arm)
    bpy.context.scene.collection.objects.link(ob)
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    for row in bones:
        bn, head, tail, parent = row[0], row[1], row[2], row[3]
        roll = row[4] if len(row) > 4 else 0.0
        eb = arm.edit_bones.new(bn)
        eb.head = Vector(head)
        eb.tail = Vector(tail)
        eb.roll = roll
        eb.use_connect = False
        if parent:
            eb.parent = arm.edit_bones[parent]
    bpy.ops.object.mode_set(mode="OBJECT")
    ob.show_in_front = True
    return ob
