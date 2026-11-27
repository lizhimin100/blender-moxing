"""unitkit.py —— 方块人 / 豺狼人重建用的几何与材质工具。

设计口径（与《单位资产规范》一致）：
  * 1 unit = 1 m；+Y 正面；脚底 z=0；原点在双足中间。
  * 一块 = 一根骨、权重 1.0（刚性蒙皮）；关节处留缝，不做平滑权重。
  * 硬表面只用倒角，有机体只用 Catmull-Clark，**永不叠加**。
  * 材质名固定：主体 / team / team_trim / M_tribe / M_eye。
    主体 走 256² 纯色图集（每件一格），UV 取格心。
"""
import math
import os
import sys

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import palette  # noqa: E402

ATLAS = os.path.join(HERE, "图集", "单位色板.png")


def srgb(hexstr):
    h = hexstr.lstrip("#")
    out = []
    for i in range(3):
        c = int(h[i * 2:i * 2 + 2], 16) / 255.0
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return tuple(out)


def _bsdf(mat):
    mat.use_nodes = True
    return next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")


def make_materials():
    """建五套材质；重复调用时复用（按名取）。"""
    M = {}

    body = bpy.data.materials.get("主体") or bpy.data.materials.new("主体")
    body.use_nodes = True
    nt = body.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    tex = nt.nodes.new("ShaderNodeTexImage")
    img = bpy.data.images.load(ATLAS, check_existing=True)
    img.colorspace_settings.name = "sRGB"
    tex.image = img
    tex.interpolation = "Closest"
    tex.extension = "EXTEND"
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    bsdf.inputs["Roughness"].default_value = 0.82
    bsdf.inputs["Metallic"].default_value = 0.0
    M["主体"] = body

    def flat(name, hexcol, rough=0.7, metal=0.0, emit=None, estr=0.0):
        m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
        m.use_nodes = True
        b = _bsdf(m)
        b.inputs["Base Color"].default_value = (*srgb(hexcol), 1.0)
        b.inputs["Roughness"].default_value = rough
        b.inputs["Metallic"].default_value = metal
        if emit:
            b.inputs["Emission Color"].default_value = (*srgb(emit), 1.0)
            b.inputs["Emission Strength"].default_value = estr
        m.diffuse_color = (*srgb(hexcol), 1.0)
        M[name] = m
        return m

    flat("team", "#2E5FB4", 0.56, 0.0)
    flat("team_trim", "#F1CD79", 0.44, 0.10)
    flat("M_tribe", "#8C3A2A", 0.72, 0.0)
    flat("M_eye", "#1A1206", 0.35, 0.0, "#FFC24A", 2.0)
    return M


# ── 网格构造 ────────────────────────────────────────────────────────────────
def _obj(name, verts, faces):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], [tuple(f) for f in faces])
    me.validate(verbose=False)
    me.update()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def poly_n(w, d, n=6, phase=0.0):
    """椭圆内接 n 边形（有机截面用 6，硬表面用 4）。"""
    return [(w * 0.5 * math.cos(phase + math.tau * k / n),
             d * 0.5 * math.sin(phase + math.tau * k / n)) for k in range(n)]


def poly_rect(w, d, ch=0.0):
    hw, hd = w * 0.5, d * 0.5
    if ch <= 1e-6:
        return [(-hw, -hd), (hw, -hd), (hw, hd), (-hw, hd)]
    c = min(ch, hw * 0.85, hd * 0.85)
    return [(-hw + c, -hd), (hw - c, -hd), (hw, -hd + c), (hw, hd - c),
            (hw - c, hd), (-hw + c, hd), (-hw, hd - c), (-hw, -hd + c)]


def box(name, center, size, rot=None):
    cx, cy, cz = center
    hx, hy, hz = size[0] * 0.5, size[1] * 0.5, size[2] * 0.5
    pts = [(-hx, -hy, -hz), (hx, -hy, -hz), (hx, hy, -hz), (-hx, hy, -hz),
           (-hx, -hy, hz), (hx, -hy, hz), (hx, hy, hz), (-hx, hy, hz)]
    if rot:
        R = Euler(rot, "XYZ").to_matrix()
        pts = [tuple(R @ Vector(p)) for p in pts]
    verts = [(p[0] + cx, p[1] + cy, p[2] + cz) for p in pts]
    faces = [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1),
             (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
    return _obj(name, verts, faces)


def loft(name, rows, caps=True):
    n = len(rows[0])
    m = len(rows)
    verts = [p for r in rows for p in r]
    faces = []
    for k in range(m - 1):
        b, b2 = k * n, (k + 1) * n
        for i in range(n):
            j = (i + 1) % n
            faces.append((b + i, b + j, b2 + j, b2 + i))
    if caps:
        faces.append(tuple(range(n - 1, -1, -1)))
        faces.append(tuple(range((m - 1) * n, m * n)))
    return _obj(name, verts, faces)


def tube_z(name, stations, caps=True, n=0):
    rows = []
    for (z, cx, cy, w, d, ch) in stations:
        pts = poly_n(w, d, n) if n else poly_rect(w, d, ch)
        rows.append([(cx + x, cy + y, z) for (x, y) in pts])
    return loft(name, rows, caps)


def frame(p0, p1, up=(0, 0, 1)):
    p0, p1 = Vector(p0), Vector(p1)
    z = (p1 - p0)
    if z.length < 1e-8:
        z = Vector((0, 0, 1))
    z.normalize()
    u = Vector(up)
    if abs(z.dot(u)) > 0.96:
        u = Vector((0, 1, 0))
    x = u.cross(z)
    if x.length < 1e-8:
        x = Vector((1, 0, 0))
    x.normalize()
    y = z.cross(x)
    return p0, x, y, z


def limb(name, p0, p1, r0, r1, sides=6, mid=None, depth0=None, depth1=None,
         sections=(0.0, 0.18, 0.82, 1.0), roll=0.0):
    """沿 p0→p1 的锥形肢体；椭圆截面（depth = 前后向半径）。"""
    p0v, x, y, z = frame(p0, p1)
    L = (Vector(p1) - p0v).length
    d0 = r0 if depth0 is None else depth0
    d1 = r1 if depth1 is None else depth1
    if mid is None:
        mid = (r0 + r1) * 0.5
    rows = []
    for t in sections:
        rr = r0 + (r1 - r0) * t
        dd = d0 + (d1 - d0) * t
        if abs(t - 0.5) < 1e-6:
            rr, dd = mid, (d0 + d1) * 0.5
        row = []
        for k in range(sides):
            a = roll + math.tau * k / sides
            row.append(tuple(p0v + z * (L * t) + x * (math.cos(a) * rr) + y * (math.sin(a) * dd)))
        rows.append(row)
    return loft(name, rows, True)


def plate(name, pts, axis="Y", thickness=0.03, offset=0.0, uv_origin=(0.0, 0.0)):
    """2D 多边形沿 axis 挤出。pts 是 (u,v)：axis=Y → (x=u,z=v)，axis=X → (y=u,z=v)。"""
    ou, ov = uv_origin
    front = []
    back = []
    for (u, v) in pts:
        uu, vv = u + ou, v + ov
        if axis == "Y":
            front.append((uu, offset + thickness, vv))
            back.append((uu, offset, vv))
        else:
            front.append((offset + thickness, uu, vv))
            back.append((offset, uu, vv))
    n = len(pts)
    verts = front + back
    faces = [tuple(range(n)), tuple(range(2 * n - 1, n - 1, -1))]
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, n + j, n + i))
    return _obj(name, verts, faces)


def revolve_y(name, prof, seg, phase=0.0):
    """绕 Y 轴回转；prof = [(r, y)]，两端 r>0。"""
    verts, faces = [], []
    m = len(prof)
    for s in range(seg):
        a = phase + math.tau * s / seg
        ca, sa = math.cos(a), math.sin(a)
        for (r, y) in prof:
            verts.append((r * ca, y, r * sa))
    for s in range(seg):
        b, b2 = s * m, ((s + 1) % seg) * m
        for k in range(m - 1):
            faces.append((b + k, b + k + 1, b2 + k + 1, b2 + k))
    faces.append(tuple(range(0, seg * m, m)))
    faces.append(tuple(range(m - 1, seg * m, m)))
    return _obj(name, verts, faces)


def claw(name, base, tip, w, thick, up=(0, 0, 1)):
    """四棱锥爪：底面矩形 → 尖。"""
    p0, x, y, z = frame(base, tip, up)
    b = Vector(base)
    t = Vector(tip)
    row = [tuple(b + x * (w * 0.5) + y * (thick * 0.5)),
           tuple(b - x * (w * 0.5) + y * (thick * 0.5)),
           tuple(b - x * (w * 0.5) - y * (thick * 0.5)),
           tuple(b + x * (w * 0.5) - y * (thick * 0.5))]
    tipv = tuple(t)
    verts = row + [tipv]
    faces = [(0, 1, 2, 3), (0, 4, 1), (1, 4, 2), (2, 4, 3), (3, 4, 0)]
    return _obj(name, verts, faces)


def ear(name, root, tip, width, thick, bend=0.0):
    """圆润的兽耳：根部四边形 → 中段最宽 → 尖；用 3 排 loft。"""
    p0, x, y, z = frame(root, tip)
    L = (Vector(tip) - Vector(root)).length
    rows = []
    for t, wf in ((0.0, 0.55), (0.30, 1.0), (0.65, 0.92), (0.90, 0.48), (1.0, 0.10)):
        cx = Vector(root) + z * (L * t) + x * (bend * math.sin(math.pi * t))
        row = []
        for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            row.append(tuple(cx + x * (sx * width * 0.5 * wf) + y * (sy * thick * 0.5 * wf)))
        rows.append(row)
    return loft(name, rows, True)


class Unit:
    def __init__(self, name):
        self.name = name
        self.parts = []      # (obj, bone, mat, bevel, seg, sub, smooth)
        self.M = make_materials()

    def add(self, ob, bone, mat, bevel=0.006, seg=2, sub=0, smooth=False, key=None):
        real = mat if mat in ("主体", "team", "team_trim", "M_tribe", "M_eye") else "主体"
        if real == "主体":
            ob["palette_key"] = key or mat
        self.parts.append((ob, bone, real, bevel, seg, sub, smooth))
        return ob

    # 简写
    def box(self, name, center, size, bone, mat, rot=None, bevel=0.006, seg=2, sub=0, smooth=False, key=None):
        return self.add(box(name, center, size, rot), bone, mat, bevel, seg, sub, smooth, key)

    def loft(self, name, rows, bone, mat, bevel=0.006, seg=2, sub=0, smooth=True, key=None):
        return self.add(loft(name, rows), bone, mat, bevel, seg, sub, smooth, key)

    def tube(self, name, stations, bone, mat, bevel=0.008, seg=2, sub=0, smooth=True, key=None, n=0):
        return self.add(tube_z(name, stations, n=n), bone, mat, bevel, seg, sub, smooth, key)

    def limb(self, name, p0, p1, r0, r1, bone, mat, **kw):
        bevel = kw.pop("bevel", 0.0)
        seg = kw.pop("seg", 1)
        sub = kw.pop("sub", 1)
        smooth = kw.pop("smooth", True)
        key = kw.pop("key", None)
        return self.add(limb(name, p0, p1, r0, r1, **kw), bone, mat, bevel, seg, sub, smooth, key)

    def plate(self, name, pts, bone, mat, axis="Y", thickness=0.03, offset=0.0,
              bevel=0.004, seg=1, sub=0, smooth=False, uv_origin=(0, 0), key=None):
        return self.add(plate(name, pts, axis, thickness, offset, uv_origin), bone, mat,
                        bevel, seg, sub, smooth, key)

    def revolve(self, name, prof, segs, bone, mat, phase=0.0, bevel=0.004, sub=0, smooth=True, key=None):
        return self.add(revolve_y(name, prof, segs, phase), bone, mat, bevel, 2, sub, smooth, key)

    def claw(self, name, base, tip, w, thick, bone, mat, bevel=0.0, sub=0, up=(0, 0, 1), key=None):
        return self.add(claw(name, base, tip, w, thick, up), bone, mat, bevel, 1, sub, False, key)

    def ear(self, name, root, tip, width, thick, bone, mat, bend=0.0, bevel=0.0, sub=1, smooth=True, key=None):
        return self.add(ear(name, root, tip, width, thick, bend), bone, mat, bevel, 1, sub, smooth, key)

    # ── 收尾 ────────────────────────────────────────────────────────────────
    def _apply(self, ob, bevel, seg, sub, smooth):
        # 硬规矩：有机物只用 CC，硬表面只用倒角，**永不叠加**
        # （叠加一件 = 倒角后的边再被 CC 乘 4，实测耳朵从 160 涨到 424）
        if sub and sub > 0:
            bevel = 0.0
        bpy.ops.object.select_all(action="DESELECT")
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        if bevel and bevel > 0:
            m = ob.modifiers.new("bev", "BEVEL")
            m.width = bevel
            m.segments = min(seg, 1)
            m.limit_method = "ANGLE"
            m.angle_limit = math.radians(32)
            try:
                bpy.ops.object.modifier_apply(modifier=m.name)
            except Exception as e:
                print("[warn bevel]", ob.name, e)
        if sub and sub > 0:
            m = ob.modifiers.new("sub", "SUBSURF")
            m.levels = sub
            m.render_levels = sub
            try:
                bpy.ops.object.modifier_apply(modifier=m.name)
            except Exception as e:
                print("[warn sub]", ob.name, e)
        for p in ob.data.polygons:
            p.use_smooth = smooth

    def _uv_palette(self, ob, key):
        me = ob.data
        if "UVMap" not in me.uv_layers:
            me.uv_layers.new(name="UVMap")
        uv = me.uv_layers["UVMap"]
        u, v = palette.uv_of(key)
        for loop in me.loops:
            uv.data[loop.index].uv = (u, v)

    def finish(self, prefix="unit", join=True, verbose=False):
        sizes = []
        for (ob, bone, mat, bevel, seg, sub, smooth) in self.parts:
            self._apply(ob, bevel, seg, sub, smooth)
            ob.data.calc_loop_triangles()
            sizes.append((len(ob.data.loop_triangles), ob.name))
            if mat == "主体":
                key = ob.get("palette_key") or ob.name.split("__")[-1]
                self._uv_palette(ob, key)
            # 材质
            ob.data.materials.clear()
            ob.data.materials.append(self.M[mat])
            # 刚性蒙皮
            vg = ob.vertex_groups.new(name=bone)
            vg.add(list(range(len(ob.data.vertices))), 1.0, "REPLACE")

        if verbose:
            sizes.sort(reverse=True)
            print("[parts] top tris:")
            for n, nm in sizes[:28]:
                print("   %5d  %s" % (n, nm))
            print("   total parts", len(sizes), "sum", sum(n for n, _ in sizes))

        # 双面法线兜底
        for (ob, *_rest) in self.parts:
            bm = bmesh.new(); bm.from_mesh(ob.data)
            bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
            if bm.calc_volume(signed=True) < 0:
                bmesh.ops.reverse_faces(bm, faces=list(bm.faces))
            bm.to_mesh(ob.data); bm.free()
            ob.data.update()

        if not join:
            return [p[0] for p in self.parts]

        buckets = {}
        for (ob, _b, mat, *_r) in self.parts:
            buckets.setdefault(mat, []).append(ob)
        out = []
        names = {"主体": prefix + "_body", "team": prefix + "_team",
                 "team_trim": prefix + "_trim", "M_tribe": prefix + "_tribe",
                 "M_eye": prefix + "_eye"}
        for mat, objs in buckets.items():
            bpy.ops.object.select_all(action="DESELECT")
            for o in objs:
                o.select_set(True)
            bpy.context.view_layer.objects.active = objs[0]
            if len(objs) > 1:
                bpy.ops.object.join()
            joined = bpy.context.view_layer.objects.active
            joined.name = names.get(mat, prefix + "_" + mat)
            joined.data.name = joined.name
            out.append(joined)
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


def set_palette_key(ob, key):
    """在 add() 之前标记该件用哪个色板格（finish 时写 UV）。"""
    ob["palette_key"] = key
    return ob


def part_key(ob, key):
    ob["palette_key"] = key
    return ob


def stats(objs):
    tris = 0
    for o in objs:
        o.data.calc_loop_triangles()
        tris += len(o.data.loop_triangles)
    return tris
