# -*- coding: utf-8 -*-
"""mkit.py —— 微缩建筑零件库 v2（1 m 格 / 800–2000 tri 线）

和 v1 的区别只有三件，但都是结构性的：

1. **队色变成"染色系统"**。`team` / `team_trim` 两个槽的顶点色只存*明度遮罩*
   （接近白的灰阶），真实色相来自材质 baseColor（`PALETTES` 里的阵营色）。
   换阵营 = 改两个材质颜色 / 改 GLB 的 baseColorFactor，**不重建模型**。
   这不是省事，是"一栋建筑要出四个阵营"的唯一正确解法：色相归一，明度留在几何上。

2. **细分通道**。`part(..., sub=1)` 先按低模控制笼建面，再上 Catmull-Clark 一级。
   只给**回转件与布料**（钟、顶饰、木桶、铃舌）；平面体量一律硬边。
   低模线里全身上细分 = 面团，只给该圆的地方圆才对。
   预算：细分件 tri 占比 ≤ 20%（`th_check` 会算）。

3. **瓦垄 / 檐口 / 隅石 / 钟面**这些"小而能改轮廓"的件补齐了。
   一片空白的斜面在 512 px 上读不出是屋顶，只会读成"没做完"。

颜色约定：顶点色写**线性**值，`PAL` 里存 sRGB 十六进制，`srgb()` 负责转换。
零件的"坐标系"：全部按**底面中心**给 z0，X/Y 关于原点对称。
"""
import json
import math
import os

import bmesh
import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------- 阵营色

PALETTES = {
    "联盟":     {"team": "#2554A8", "team_trim": "#E4B455", "自发光": "#FFC173"},
    "失落帝国": {"team": "#743A2E", "team_trim": "#A99578", "自发光": "#FFB05A"},
    "中立":     {"team": "#4C6B58", "team_trim": "#B9A87A", "自发光": "#FFD08A"},
    "霜誓":     {"team": "#2F6F86", "team_trim": "#CBD6D8", "自发光": "#A8E4FF"},
}
DEFAULT_PALETTE = "联盟"


# ---------------------------------------------------------------- 主体色板
# 明度秩序：底座 → 台基 → 墙裙 → 墙 → 压顶 → 木 → 屋面(队色) → 金
PAL_HEX = {
    "底座":   "#6D6355",
    "台基":   "#8E8371",
    "石":     "#CFC6B3",   # 结构主材：暖白石灰岩
    "石亮":   "#E4DCC9",
    "石暗":   "#8C8374",
    "石冷":   "#7C7A76",
    "木":     "#6B4A30",
    "木暗":   "#3A2A1C",
    "木亮":   "#8C6239",
    "灰泥":   "#E8DFCB",
    "铁":     "#5A6470",
    "窗":     "#221D18",
    "焰":     "#FFC173",
}


def srgb(hexstr):
    """'#RRGGBB' -> 线性 RGBA。顶点色必须走这一步。"""
    h = hexstr.lstrip("#")
    out = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255.0
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return (out[0], out[1], out[2], 1.0)


PAL = {k: srgb(v) for k, v in PAL_HEX.items()}

# 队色槽的顶点色 = 灰阶遮罩（纯白为 1.0）。色相由材质给，这里只管明度。
GRAY = {
    "T100": (1.000, 1.000, 1.000, 1.0),
    "T094": (0.940, 0.940, 0.940, 1.0),
    "T086": (0.860, 0.860, 0.860, 1.0),
    "T074": (0.740, 0.740, 0.740, 1.0),
    "G100": (1.000, 1.000, 1.000, 1.0),
    "G082": (0.820, 0.820, 0.820, 1.0),
}

SLOTS = ("主体", "team", "team_trim", "自发光")

# ---------------------------------------------------------------- 双槽制（v3，兵营起）
# 《战争原岛》全局规范要求"一栋建筑只准两个材质槽"：Mat_Neutral / Mat_TeamColor。
# 四槽制（主体/team/team_trim/自发光）留给城镇大厅那批历史资产，**两条路互不干扰**：
# twoslot=False 走 ROLE+PAL，twoslot=True 走 ROLE2+PAL2。
#
# 两槽制下"金"不能再靠独立材质提亮，只能烘进顶点色（漆金）；发光通道直接没有 ——
# 3★ 的"微光"改由金色屋脊与盾徽承担。这是规范冲突时的取舍，写进文档。
SLOTS2 = ("Mat_Neutral", "Mat_TeamColor")

# 两槽制色板：锚点就是全局规范的六个值（皇家蓝 / 暖金 / 冷铁 / 暖石 / 深橡木 / 灰泥）
PAL2_HEX = {
    "底座":   "#6B6152",
    "台基":   "#8A7E68",
    "土":     "#8F8066",
    "沙":     "#A8997B",
    "石":     "#B8B4A8",   # 结构主材：浅灰暖石（规范锚点）
    "石亮":   "#D2CEC1",
    "石暗":   "#918C7E",
    "石冷":   "#8D8B86",
    "灰泥":   "#E2D8C5",   # 米白灰泥（规范锚点）
    "木":     "#6E4A2E",   # 深橡木（规范锚点）
    "木暗":   "#46301F",
    "木亮":   "#8C6239",
    "铁":     "#5A6470",   # 冷铁（规范锚点）
    "铁暗":   "#3C4450",
    "金":     "#D9A441",   # 暖金（规范锚点）
    "金亮":   "#F0C878",
    "洞":     "#241E19",
    "草":     "#C7A55E",
    "布":     "#E6DECB",
    "布暗":   "#C9BFA6",
}
PAL2 = {k: srgb(v) for k, v in PAL2_HEX.items()}

ROLE2 = {
    "底座": ("底座", "Mat_Neutral"),
    "台基": ("台基", "Mat_Neutral"),
    "土":   ("土", "Mat_Neutral"),
    "沙":   ("沙", "Mat_Neutral"),
    "石":   ("石", "Mat_Neutral"),
    "石亮": ("石亮", "Mat_Neutral"),
    "石暗": ("石暗", "Mat_Neutral"),
    "石冷": ("石冷", "Mat_Neutral"),
    "灰泥": ("灰泥", "Mat_Neutral"),
    "木":   ("木", "Mat_Neutral"),
    "木暗": ("木暗", "Mat_Neutral"),
    "木亮": ("木亮", "Mat_Neutral"),
    "铁":   ("铁", "Mat_Neutral"),
    "铁暗": ("铁暗", "Mat_Neutral"),
    "金":   ("金", "Mat_Neutral"),
    "金亮": ("金亮", "Mat_Neutral"),
    "洞":   ("洞", "Mat_Neutral"),
    "草":   ("草", "Mat_Neutral"),
    "布":   ("布", "Mat_Neutral"),
    "布暗": ("布暗", "Mat_Neutral"),
    # 队色：屋面瓦、旗帜、盾面、门框饰条 —— 顶点色纯白，色相只由 baseColor 给
    "瓦":   ("T100", "Mat_TeamColor"),
    "瓦暗": ("T100", "Mat_TeamColor"),
    "瓦亮": ("T100", "Mat_TeamColor"),
    "旗":   ("T100", "Mat_TeamColor"),
    "旗暗": ("T100", "Mat_TeamColor"),
    "盾":   ("T100", "Mat_TeamColor"),
    "门饰": ("T100", "Mat_TeamColor"),
}

# 角色 -> (颜色键, 材质槽)
ROLE = {
    "底座": ("底座", "主体"),
    "台基": ("台基", "主体"),
    "石":   ("石", "主体"),
    "石亮": ("石亮", "主体"),
    "石暗": ("石暗", "主体"),
    "石冷": ("石冷", "主体"),
    "木":   ("木", "主体"),
    "木暗": ("木暗", "主体"),
    "木亮": ("木亮", "主体"),
    "灰泥": ("灰泥", "主体"),
    "窗":   ("窗", "主体"),
    "焰":   ("焰", "自发光"),
    # 队色：只写灰阶，色相遇材质
    "瓦":   ("T100", "team"),
    "瓦暗": ("T086", "team"),
    "瓦亮": ("T094", "team"),
    "旗":   ("T100", "team"),
    "金":   ("G100", "team_trim"),
    "金暗": ("G082", "team_trim"),
    "铁":   ("G082", "team_trim"),
}


def palette(name=None):
    """取阵营色（sRGB 十六进制）。name 可以是名字，也可以直接是 dict。"""
    if isinstance(name, dict):
        return name
    return PALETTES.get(name or DEFAULT_PALETTE, PALETTES[DEFAULT_PALETTE])


def clear():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for blk in (bpy.data.meshes, bpy.data.materials, bpy.data.cameras,
                bpy.data.lights, bpy.data.worlds, bpy.data.images):
        for it in list(blk):
            try:
                blk.remove(it)
            except Exception:
                pass


# ---------------------------------------------------------------- 材质

def _mat(name, rough, metal, color=None, emit=None):
    """color=None 时走顶点色；给了 color 就走 baseColorFactor（队色槽）。

    为什么队色槽**不接** Color Attribute：接了就是"顶点色 × 材质色"，
    换阵营时两个颜色相乘，蓝 × 红 = 泥。队色只能有一个来源。
    顶点色仍然写进了 mesh（灰阶遮罩），导出时若带上 COLOR_0 就是明度微差，
    不带也不影响色相 —— 两条路都正确。
    """
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    if color is None:
        attr = nt.nodes.new("ShaderNodeAttribute")
        attr.attribute_name = "Col"
        attr.attribute_type = 'GEOMETRY'
        nt.links.new(attr.outputs["Color"], bsdf.inputs["Base Color"])
    else:
        c = srgb(color)
        bsdf.inputs["Base Color"].default_value = c
        m.diffuse_color = c
    if emit is not None:
        attr = nt.nodes.new("ShaderNodeAttribute")
        attr.attribute_name = "Col"
        attr.attribute_type = 'GEOMETRY'
        nt.links.new(attr.outputs["Color"], bsdf.inputs["Emission Color"])
        bsdf.inputs["Emission Strength"].default_value = emit
        bsdf.inputs["Base Color"].default_value = (0.22, 0.13, 0.05, 1)
        m.diffuse_color = srgb(color or "#FFC173")
    m.use_backface_culling = True
    return m


def materials(pal=None):
    """四个槽，顺序固定，全工程共用（同名材质在引擎里也会被合并）。"""
    p = palette(pal)
    return {
        "主体": _mat("主体", 0.80, 0.0),
        "team": _mat("team", 0.62, 0.0, p["team"]),
        "team_trim": _mat("team_trim", 0.46, 0.32, p["team_trim"]),
        "自发光": _mat("自发光", 0.5, 0.0, p.get("自发光", "#FFC173"), emit=3.2),
    }


def materials2(pal=None):
    """两个槽（v3 全局规范）：Mat_Neutral 走顶点色，Mat_TeamColor 走 baseColor。

    队色材质**不接** Color Attribute —— 顶点色对队色件一律写纯白（1.0），
    这样"Blender 里看到的"和"GLB 里乘完 COLOR_0 的"完全一致，
    换阵营只改一个 baseColorFactor，永远不会蓝 × 红 = 泥。
    粗糙度只能整槽一个值：0.78 是石/木/漆金都能接受的中间值。
    """
    p = palette(pal)
    return {
        "Mat_Neutral": _mat("Mat_Neutral", 0.78, 0.0),
        "Mat_TeamColor": _mat("Mat_TeamColor", 0.60, 0.0, p["team"]),
    }


# ---------------------------------------------------------------- 零件工厂

class B:
    """收集零件 -> 一次 join 成单件。每个零件留 name/bbox/槽/面积 供体检。"""

    def __init__(self, mats=None, pal=None, twoslot=False):
        self.pal = palette(pal)
        self.twoslot = bool(twoslot)
        self.mats = mats or (materials2(self.pal) if twoslot else materials(self.pal))
        self.role = ROLE2 if twoslot else ROLE
        self.colors = PAL2 if twoslot else PAL
        self.parts = []
        self.info = []       # (name, lo, hi, tris, up, slot, area, sub)
        self.actual = {}     # name -> 细分之后真实 tri（体检要算真账）

    # ---- 底层：任意多面体
    def part(self, name, verts, faces, role="石", bevel=0.0, seg=1, mode="all",
             sub=0, smooth=False):
        color, slot = self.role[role]
        me = bpy.data.meshes.new(name)
        me.from_pydata([tuple(v) for v in verts], [], [tuple(f) for f in faces])
        me.validate(verbose=False)
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        if bevel > 0.0:
            edges = [e for e in bm.edges if self._pick(e, mode)]
            if edges:
                bmesh.ops.bevel(bm, geom=edges, offset=bevel, segments=seg,
                                affect='EDGES', clamp_overlap=True, profile=0.5,
                                miter_outer='SHARP')
        bm.to_mesh(me)
        bm.free()
        ob = bpy.data.objects.new(name, me)
        bpy.context.collection.objects.link(ob)
        me.materials.append(self.mats[slot])
        ca = me.color_attributes.new("Col", 'FLOAT_COLOR', 'POINT')
        c = GRAY[color] if color in GRAY else self.colors[color]
        for d in ca.data:
            d.color = c
        for p in me.polygons:
            p.use_smooth = bool(smooth or sub)
        ob["slot"] = slot
        if sub:
            ob["sub"] = int(sub)
        self.parts.append(ob)
        me.calc_loop_triangles()
        lo = Vector([min(v.co[i] for v in me.vertices) for i in range(3)]) + ob.location
        hi = Vector([max(v.co[i] for v in me.vertices) for i in range(3)]) + ob.location
        ups = [p for p in me.polygons if p.normal.z > 0.9 and p.area > 1e-8]
        up = None
        if ups:
            zt = max(p.center.z for p in ups)
            sel = [p for p in ups if abs(p.center.z - zt) < 0.0005]
            area = sum(p.area for p in sel)
            ux0 = min(min(me.vertices[v].co.x for v in p.vertices) for p in sel)
            ux1 = max(max(me.vertices[v].co.x for v in p.vertices) for p in sel)
            uy0 = min(min(me.vertices[v].co.y for v in p.vertices) for p in sel)
            uy1 = max(max(me.vertices[v].co.y for v in p.vertices) for p in sel)
            up = (zt, ux0, ux1, uy0, uy1, area)
        area_all = sum(p.area for p in me.polygons)
        self.info.append((name, tuple(lo), tuple(hi), len(me.loop_triangles), up,
                          slot, area_all, int(sub)))
        return ob

    @staticmethod
    def _pick(edge, mode):
        z0 = min(v.co.z for v in edge.verts)
        z1 = max(v.co.z for v in edge.verts)
        if mode == "all":
            return True
        if mode == "no_bottom":
            return not (abs(z0) < 1e-6 and abs(z1) < 1e-6)
        if mode == "top":
            return abs(z0 - z1) < 1e-6 and z0 > 0.0
        if mode == "vertical":
            return abs(z1 - z0) > 1e-6
        raise ValueError(mode)

    # ---- 盒：底面在 z0
    def box(self, name, w, d, h, z0, role="石", bevel=0.004, seg=1,
            mode="no_bottom", at=(0.0, 0.0), rot=None, sub=0):
        x, y = at
        v = [(-w / 2, -d / 2, 0), (w / 2, -d / 2, 0), (w / 2, d / 2, 0), (-w / 2, d / 2, 0),
             (-w / 2, -d / 2, h), (w / 2, -d / 2, h), (w / 2, d / 2, h), (-w / 2, d / 2, h)]
        f = [(0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
        if rot is not None:
            m = rot if isinstance(rot, Matrix) else Matrix.Rotation(rot, 3, 'X')
            v = [tuple(m @ Vector(p)) for p in v]
            dz = min(p[2] for p in v)
            v = [(p[0], p[1], p[2] - dz) for p in v]
        v = [(p[0] + x, p[1] + y, p[2] + z0) for p in v]
        return self.part(name, v, f, role, bevel, seg, mode, sub)

    # ---- 正多棱柱 / 圆锥
    def cyl(self, name, r, h, z0, sides=8, role="石", bevel=0.0, seg=1,
            at=(0.0, 0.0), r_top=None, rotz=0.0, cap=True, sub=0):
        x, y = at
        r_top = r if r_top is None else r_top
        v, f = [], []
        for i in range(sides):
            a = rotz + 2 * math.pi * i / sides
            v.append((x + r * math.cos(a), y + r * math.sin(a), z0))
        for i in range(sides):
            a = rotz + 2 * math.pi * i / sides
            v.append((x + r_top * math.cos(a), y + r_top * math.sin(a), z0 + h))
        for i in range(sides):
            j = (i + 1) % sides
            f.append((i, j, sides + j, sides + i))
        if cap:
            f.append(tuple(range(sides - 1, -1, -1)))
            f.append(tuple(range(sides, 2 * sides)))
        return self.part(name, v, f, role, bevel, seg,
                         "vertical" if bevel else "all", sub)

    def cone(self, name, r, h, z0, sides=8, role="瓦", at=(0.0, 0.0), rotz=0.0,
             bevel=0.0, sub=0):
        x, y = at
        v = []
        for i in range(sides):
            a = rotz + 2 * math.pi * i / sides
            v.append((x + r * math.cos(a), y + r * math.sin(a), z0))
        v.append((x, y, z0 + h))
        f = [(i, (i + 1) % sides, sides) for i in range(sides)]
        f.append(tuple(range(sides - 1, -1, -1)))
        return self.part(name, v, f, role, bevel, 1, "all", sub)

    def pyramid(self, name, w, d, h, z0, role="瓦", at=(0.0, 0.0), rotz=0.0,
                bevel=0.0, sub=0):
        x, y = at
        c, s = math.cos(rotz), math.sin(rotz)
        base = [(-w / 2, -d / 2), (w / 2, -d / 2), (w / 2, d / 2), (-w / 2, d / 2)]
        v = [(x + px * c - py * s, y + px * s + py * c, z0) for px, py in base]
        v.append((x, y, z0 + h))
        f = [(0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4), (3, 2, 1, 0)]
        return self.part(name, v, f, role, bevel, 1, "all", sub)

    # ---- 双坡屋顶：脊沿 X，脊线 y=0
    def roof_gable(self, name, w, d, z0, z1, role="瓦", bevel=0.005, at=(0.0, 0.0),
                   fascia=True, throat=0.0):
        """实心三棱柱。throat>0 时屋檐底面比 z0 低一截，做出板厚感。"""
        x, y = at
        zb = z0 - throat
        v = [(x - w / 2, y - d / 2, zb), (x + w / 2, y - d / 2, zb),
             (x + w / 2, y + d / 2, zb), (x - w / 2, y + d / 2, zb),
             (x - w / 2, y, z1), (x + w / 2, y, z1)]
        f = [(0, 1, 5, 4), (3, 2, 5, 4), (0, 3, 4), (1, 2, 5), (0, 1, 2, 3)]
        self.part(name, v, f, role, bevel, 1, "all")
        if fascia:
            fy = d / 2
            for s in (-1, 1):
                self.box(name + "_封檐", w + 0.004, 0.026, 0.030, zb - 0.004,
                         "木暗", 0.0, at=(x, y + s * (fy - 0.013)))

    def roof_gable_y(self, name, w, d, z0, z1, role="瓦", at=(0.0, 0.0), throat=0.0):
        """脊沿 Y 的双坡（山墙面朝 +Y，做门廊/抱厦的三角楣）。"""
        x, y = at
        zb = z0 - throat
        v = [(x - w / 2, y - d / 2, zb), (x + w / 2, y - d / 2, zb),
             (x + w / 2, y + d / 2, zb), (x - w / 2, y + d / 2, zb),
             (x, y - d / 2, z1), (x, y + d / 2, z1)]
        f = [(1, 0, 4), (2, 3, 5), (0, 3, 5, 4), (1, 2, 5, 4), (0, 1, 2, 3)]
        return self.part(name, v, f, role, 0.0, 1, "all")

    def roof_hip(self, name, w, d, z0, z1, role="瓦", bevel=0.005, at=(0.0, 0.0)):
        """四坡：短脊沿 X。窄而深的附属体量不要用它。"""
        x, y = at
        rx = max(w / 2 - d / 2, 0.0)
        v = [(x - w / 2, y - d / 2, z0), (x + w / 2, y - d / 2, z0),
             (x + w / 2, y + d / 2, z0), (x - w / 2, y + d / 2, z0),
             (x - rx, y, z1), (x + rx, y, z1)]
        f = [(0, 1, 5, 4), (1, 2, 5), (2, 3, 4, 5), (3, 0, 4), (0, 1, 2, 3)]
        self.part(name, v, f, role, bevel, 1, "all")

    # ---- 瓦垄屋顶：三棱柱 + 每坡 n 道叠瓦
    def roof_tiled(self, name, w, d, z0, z1, role="瓦", at=(0.0, 0.0), n=4,
                   inset=0.004, first=0.0022, step=0.0013, overlap=0.009, throat=0.0,
                   top_gap=0.055):
        """屋面 + 叠瓦。每道瓦比下面一道多探出 2.2 mm，形成一条硬阴影线。

        空白的斜面在 512 px 上不读作"屋顶"，只读作"没做完"。
        瓦垄是本轮唯一花在"面"上的 tri，8 道 = 96 tri，值。
        """
        x, y = at
        self.roof_gable(name, w - inset, d - inset, z0, z1 - 0.002, role,
                        0.004, (x, y), fascia=False, throat=throat)
        rise = z1 - z0
        half = d / 2
        L = math.hypot(half, rise)
        tt = 1.0 - top_gap          # 瓦垄在脊前收住，把最后 7% 让给金色压顶
        for s in (-1, 1):
            ny, nz = s * rise / L, half / L
            for i in range(n):
                t0, t1 = i * tt / n, (i + 1) * tt / n
                ta = max(0.0, t0 - overlap / L)
                off = first + step * i
                pts = []
                for xx in (-w / 2, w / 2):
                    for t in (ta, t1):
                        py = y + s * half * (1 - t) + ny * off
                        pz = z0 + rise * t + nz * off
                        pts.append((xx, py, pz))
                # pts 顺序: (-w,ta) (-w,t1) (+w,ta) (+w,t1) -> 重排成环
                quad = [pts[0], pts[2], pts[3], pts[1]]
                if s < 0:
                    quad = [pts[0], pts[1], pts[3], pts[2]]
                self.slab4("%s_瓦%d%d" % (name, s, i), quad,
                           off + 0.006, "瓦暗" if i % 2 else role, 0.0)

    # ---- 任意多边形挤出：pts 在 (u,v) 平面，法线沿 axis
    def plate(self, name, pts, thick, role="石", at=(0.0, 0.0, 0.0), axis="Y",
              bevel=0.0, seg=1, sub=0):
        """axis='Y' -> pts 是 (x,z)；axis='X' -> pts 是 (y,z)；axis='Z' -> pts 是 (x,y)。"""
        x, y, z = at
        h = thick / 2
        v = []
        for s in (-1, 1):
            for u, t in pts:
                if axis == "Y":
                    v.append((x + u, y + s * h, z + t))
                elif axis == "X":
                    v.append((x + s * h, y + u, z + t))
                else:
                    v.append((x + u, y + t, z + s * h))
        n = len(pts)
        f = [tuple(range(n)), tuple(range(2 * n - 1, n - 1, -1))]
        for i in range(n):
            j = (i + 1) % n
            f.append((i, j, n + j, n + i))
        return self.part(name, v, f, role, bevel, seg, "all", sub)

    def disc(self, name, r, thick, at, role="金", n=10, axis="Y"):
        pts = [(r * math.cos(2 * math.pi * i / n), r * math.sin(2 * math.pi * i / n))
               for i in range(n)]
        return self.plate(name, pts, thick, role, at, axis)

    def slab4(self, name, pts, thick, role="木暗", bevel=0.0):
        """四个上表面点（3D，XY 逆时针）向下挤出 thick —— 单坡屋面 / 披檐 / 坡道。"""
        v = [tuple(p) for p in pts] + [(p[0], p[1], p[2] - thick) for p in pts]
        f = [(0, 1, 2, 3), (7, 6, 5, 4), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
        return self.part(name, v, f, role, bevel, 1, "all")

    def beam(self, name, p0, p1, w=0.02, t=0.02, role="木暗", bevel=0.0):
        """两点之间的方料（从 p0 指向 p1，截面 w×t）。"""
        p0, p1 = Vector(p0), Vector(p1)
        d = p1 - p0
        L = d.length
        if L < 1e-6:
            return None
        q = d.to_track_quat('Z', 'Y').to_matrix()
        v = []
        for sz in (0.0, L):
            for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                v.append(tuple(p0 + q @ Vector((sx * w / 2, sy * t / 2, sz))))
        f = [(0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
        return self.part(name, v, f, role, bevel, 1, "all")

    # ---- 组合件
    def base(self, w=1.0, d=1.0, h=0.08, bevel=0.018):
        """通用底座：1.0×1.0×0.08，只倒竖边与顶边，底面死死贴 z=0。"""
        self.box("底座", w, d, h, 0.0, "底座", bevel, 1, "no_bottom")

    def plinth(self, w, d, h, z0, role="台基", bevel=0.006):
        self.box("台基", w, d, h, z0, role, bevel, 1, "no_bottom")

    def steps(self, w, n, z_bottom, z_top, y0, y1, role="石"):
        """正面台阶：n 级，从门口 y0 铺到台基边 y1，末级顶面比台基低 4 mm（防共面）。"""
        tread = (y1 - y0) / n
        h = (z_top - z_bottom) / n
        for i in range(n):
            z = z_top - 0.004 - h * (i + 1)
            # 每级都从台基边 y0 往前长，不是"以中点居中" —— 居中会让最前一级
            # 多探出 tread*(n-1)/2，v1 因此把台阶顶出了 1 m 底座。
            self.box("台阶%d" % i, w, tread * (i + 1), h, z, role, 0.0,
                     at=(0.0, y0 + tread * (i + 1) / 2))

    def cornice(self, name, w, d, z0, at=(0.0, 0.0), grow=0.030, h=0.012,
                role="石亮", shade="石暗"):
        """檐口：先一条暗影线，再一条亮压顶。两级就够，多了在 512 px 上糊成一坨。"""
        x, y = at
        self.box(name + "_影", w + grow, d + grow, h, z0, shade, 0.0, at=(x, y))
        self.box(name + "_压", w + grow * 0.62, d + grow * 0.62, h * 0.9,
                 z0 + h, role, 0.0, at=(x, y))

    def arch_plate(self, name, w, h, thick, role="窗", at=(0.0, 0.0, 0.0), n=6, axis="Y"):
        r = w / 2
        pts = [(-w / 2, 0.0), (w / 2, 0.0), (w / 2, h - r)]
        for i in range(1, n + 1):
            a = math.pi * i / n
            pts.append((r * math.cos(a), h - r + r * math.sin(a)))
        return self.plate(name, pts, thick, role, at, axis)

    def window(self, name, w, h, at, role="窗", lintel=False, frame="石亮", axis="Y",
               sill=False):
        """矩形暗窗。1 m 尺度上拱窗只剩 2 px，28 tri 换不来形状，只留洞。"""
        x, y, z = at
        pts = [(-w / 2, 0.0), (w / 2, 0.0), (w / 2, h), (-w / 2, h)]
        self.plate(name, pts, 0.009, role, (x, y, z), axis)
        if lintel:
            if axis == "Y":
                self.box(name + "_楣", w + 0.018, 0.013, 0.009, z + h, frame, 0.0, at=(x, y))
            else:
                self.box(name + "_楣", 0.013, w + 0.018, 0.009, z + h, frame, 0.0, at=(x, y))
        if sill:
            if axis == "Y":
                self.box(name + "_台", w + 0.022, 0.016, 0.010, z - 0.010, frame, 0.0, at=(x, y))
            else:
                self.box(name + "_台", 0.016, w + 0.022, 0.010, z - 0.010, frame, 0.0, at=(x, y))

    def merlons(self, name, w, d, z0, h=0.030, t=0.026, n=3, role="石", at=(0.0, 0.0)):
        """方形塔顶的城垛：每边 n 个。**必须给 at**，否则整圈垛都落在原点。"""
        ox, oy = at
        for s in (-1, 1):
            for i in range(n):
                u = -w / 2 + w * (i + 0.5) / n
                self.box("%s_x%d%d" % (name, s, i), w / n * 0.50, t, h, z0, role, 0.0,
                         at=(ox + u, oy + s * (d / 2 - t / 2)))
            for i in range(max(1, n - 1)):
                u2 = -d / 2 + d * (i + 0.5) / max(1, n - 1)
                self.box("%s_y%d%d" % (name, s, i), t, d / max(1, n - 1) * 0.50, h, z0, role,
                         0.0, at=(ox + s * (w / 2 - t / 2), oy + u2))

    def flag(self, name, z0, h=0.30, at=(0.0, 0.0), role="旗", pole="金", L=0.075, H=0.055):
        x, y = at
        self.cyl(name + "_杆", 0.0055, h, z0, 6, pole, at=(x, y))
        zt = z0 + h
        pts = [(0.0, 0.0), (L, -H * 0.5), (0.0, -H * 0.82)]
        self.plate(name + "_旗", pts, 0.004, role, (x + 0.004, y, zt), "Y")

    def banner(self, name, w, h, at, role="旗", trim="金", axis="Y", thick=0.006):
        """悬垂旗：上宽下尖一整片 + 底边金翻边。

        v1 想在中间折一道做"布褶"，结果两半各成三角，读成纸飞机。
        1 m 尺度上布不需要褶，需要的是**干净的梯形 + 明确的底边**。
        """
        x, y, z = at
        pts = [(-w / 2, 0.0), (w / 2, 0.0), (w / 2, -h * 0.70),
               (w * 0.30, -h * 0.82), (0.0, -h), (-w * 0.30, -h * 0.82),
               (-w / 2, -h * 0.70)]
        self.plate(name, pts, thick, role, (x, y, z), axis)
        # 底边金翻边：同一轮廓的下三分之一，向前 3 mm
        band = [(-w * 0.42, -h * 0.72), (w * 0.42, -h * 0.72), (w * 0.28, -h * 0.83),
                (0.0, -h * 0.99), (-w * 0.28, -h * 0.83)]
        off = 0.004
        if axis == "Y":
            self.plate(name + "_边", band, thick * 0.8, trim, (x, y + off, z), axis)
        else:
            self.plate(name + "_边", band, thick * 0.8, trim, (x + off, y, z), axis)

    def shield(self, name, w, h, at, role="旗", trim="金", axis="Y"):
        x, y, z = at

        def shape(k):
            return [(-w / 2 * k, 0.0), (-w / 2 * k, -h * 0.48), (-w * 0.30 * k, -h * 0.80),
                    (0.0, -h * k), (w * 0.30 * k, -h * 0.80), (w / 2 * k, -h * 0.48),
                    (w / 2 * k, 0.0)]
        self.plate(name + "_底", shape(1.0), 0.012, trim, (x, y, z), axis)
        # 盾面比金边低 2 mm：同高会在大面积朝上共面里被判 COPLANAR_UP
        self.plate(name, shape(0.78), 0.014, role, (x, y + 0.004, z - 0.002), axis)
        oy = y + 0.016 if axis == "Y" else y
        ox = x + 0.016 if axis == "X" else x
        for i in (-1, 1):
            self.beam(name + "_纹%d" % i, (ox - 0.017 * i, oy, z - h * 0.60),
                      (ox + 0.013 * i, oy, z - h * 0.30), 0.007, 0.005, "金")

    def timber(self, name, w, d, z0, h, role="木暗", n_front=3, sides=True, t=0.018,
               rail=0.50):
        """半木构：角柱 + 前脸立枋 + 腰枋。全部**贴在墙外**（咬进 5 mm、凸出 t-5mm），
        绝不与墙面共面 —— 共面在 1 m 尺度上是闪烁的头号来源。"""
        ox, oy = w / 2 + t / 2 - 0.004, d / 2 + t / 2 - 0.004
        for sx in (-1, 1):
            for sy in (-1, 1):
                self.box(name + "_角%d%d" % (sx, sy), t, t, h, z0, role, 0.0,
                         at=(sx * ox, sy * oy))
        for i in range(n_front):
            u = -w / 2 + w * (i + 0.5) / n_front
            self.box(name + "_枋%d" % i, t * 0.85, t, h, z0, role, 0.0, at=(u, oy))
        self.box(name + "_腰枋", w - t * 0.6, t, t * 0.9, z0 + h * rail, role, 0.0,
                 at=(0.0, oy))
        if sides:
            for sx in (-1, 1):
                for i in range(2):
                    v = -d / 2 + d * (i + 1) / 3
                    self.box(name + "_侧枋%d%d" % (sx, i), t, t * 0.85, h, z0, role, 0.0,
                             at=(sx * ox, v))

    def quoin(self, name, w, d, z0, h, at=(0.0, 0.0), t=0.040, n=4, role="石亮"):
        """隅石：四角竖向石条，咬进墙角 6 mm，凸出 10 mm。4 个盒子换一圈"石砌感"。"""
        x, y = at
        for sx in (-1, 1):
            for sy in (-1, 1):
                self.box("%s_%d%d" % (name, sx, sy), t, t, h, z0, role, 0.0,
                         at=(x + sx * (w / 2 - t / 2 + 0.006),
                             y + sy * (d / 2 - t / 2 + 0.006)))

    def clock(self, name, r, at, axis="Y", face="灰泥", rim="金", hands="窗"):
        """钟面：金圈 + 米白盘 + 深色指针 + 顶饰。

        指针必须**画在盘面之前**：v1 把指针埋进盘里，读出来是一个黑洞。
        城镇大厅的市政身份全靠这一件，多花 24 tri 值得。
        """
        x, y, z = at
        h = 0.012
        self.disc(name + "_圈", r, h, (x, y, z), rim, 10, axis)
        if axis == "Y":
            self.disc(name + "_盘", r * 0.79, 0.010, (x, y + h, z), face, 10, axis)
            f = y + h + 0.006
            self.beam(name + "_针", (x, f, z), (x, f, z + r * 0.50), 0.0048, 0.0038, hands)
            self.beam(name + "_针2", (x, f, z), (x + r * 0.38, f, z + r * 0.14),
                      0.0040, 0.0034, hands)
        else:
            self.disc(name + "_盘", r * 0.79, 0.010, (x + h, y, z), face, 10, axis)
            f = x + h + 0.006
            self.beam(name + "_针", (f, y, z), (f, y, z + r * 0.46), 0.0034, 0.0042, hands)
            self.beam(name + "_针2", (f, y, z), (f, y + r * 0.34, z + r * 0.12),
                      0.0032, 0.0036, hands)

    def bell(self, name, r, h, z0, at=(0.0, 0.0), role="金暗", sides=8, sub=1):
        """钟：低模控制笼（三段）→ 一级细分。钟室里的那口钟是"这不是碉堡"的证据。"""
        x, y = at
        # 钟口在下、钟冠在上（v1 写反了，读成"灯泡"）
        rings = [(r * 1.00, 0.0), (r * 0.97, h * 0.10), (r * 0.74, h * 0.55),
                 (r * 0.56, h * 0.86), (r * 0.50, h * 1.00)]
        v, f = [], []
        for rr, hh in rings:
            for i in range(sides):
                a = 2 * math.pi * i / sides
                v.append((x + rr * math.cos(a), y + rr * math.sin(a), z0 + hh))
        for k in range(len(rings) - 1):
            for i in range(sides):
                j = (i + 1) % sides
                a0, a1 = k * sides + i, k * sides + j
                b0, b1 = (k + 1) * sides + i, (k + 1) * sides + j
                f.append((a0, a1, b1, b0))
        f.append(tuple(range(sides - 1, -1, -1)))
        f.append(tuple(range(len(v) - sides, len(v))))
        return self.part(name, v, f, role, 0.0, 1, "all", sub)

    def lantern(self, name, at, z, bracket=0.026, drop=0.030, glass="焰", cap="金"):
        """壁灯：铁支架 + 发光玻璃 + 金帽。唯一的暖光点，别多做。"""
        x, y = at
        self.beam(name + "_架", (x, y - 0.004, z + drop), (x, y + bracket, z + drop),
                  0.008, 0.006, "铁")
        self.box(name + "_玻璃", 0.020, 0.020, 0.026, z, glass, 0.0,
                 at=(x, y + bracket - 0.004))
        self.pyramid(name + "_帽", 0.028, 0.028, 0.014, z + 0.026, cap,
                     at=(x, y + bracket - 0.004), bevel=0.0)
        self.box(name + "_底", 0.024, 0.024, 0.006, z - 0.006, cap, 0.0,
                 at=(x, y + bracket - 0.004))

    # ---- 收尾
    def join(self, name):
        for ob in self.parts:
            if ob.get("sub"):
                bpy.context.view_layer.objects.active = ob
                m = ob.modifiers.new("SUB", 'SUBSURF')
                m.levels = int(ob["sub"])
                m.render_levels = int(ob["sub"])
                bpy.ops.object.modifier_apply(modifier=m.name)
                ob.data.calc_loop_triangles()
                self.actual[ob.name] = len(ob.data.loop_triangles)
        for ob in bpy.context.selected_objects:
            ob.select_set(False)
        host = self.parts[0]
        bpy.context.view_layer.objects.active = host
        for ob in self.parts:
            ob.select_set(True)
        bpy.ops.object.join()
        ob = bpy.context.object
        ob.name = name
        ob.data.name = name
        bpy.ops.object.shade_smooth_by_angle(angle=math.radians(32))
        mod = ob.modifiers.new("WN", 'WEIGHTED_NORMAL')
        mod.keep_sharp = True
        mod.weight = 60
        bpy.ops.object.modifier_apply(modifier="WN")
        ob.data.calc_loop_triangles()
        return ob

    def tris(self):
        n = 0
        for ob in self.parts:
            ob.data.calc_loop_triangles()
            n += len(ob.data.loop_triangles)
        return n

    def team_area(self):
        """队色面积占比（按世界面积；四槽/两槽都认）。"""
        tot = sum(p[6] for p in self.info)
        team = sum(p[6] for p in self.info
                   if p[5] in ("team", "team_trim", "Mat_TeamColor"))
        return team / tot if tot else 0.0

    def slot_area(self):
        """{槽: 面积占比} —— 两槽制体检要看 Mat_Neutral / Mat_TeamColor 的真实配比。"""
        tot = sum(p[6] for p in self.info)
        out = {}
        for p in self.info:
            out[p[5]] = out.get(p[5], 0.0) + p[6]
        return {k: v / tot for k, v in out.items()} if tot else {}

    def tris_true(self):
        return sum(self.actual.get(p[0], p[3]) for p in self.info)

    def soft_ratio(self):
        tot = self.tris_true()
        soft = sum(self.actual.get(p[0], p[3]) for p in self.info if p[7])
        return soft / tot if tot else 0.0

    def bbox(self):
        lo = Vector((1e9, 1e9, 1e9))
        hi = Vector((-1e9, -1e9, -1e9))
        for p in self.info:
            a, b = p[1], p[2]
            for i in range(3):
                lo[i] = min(lo[i], a[i])
                hi[i] = max(hi[i], b[i])
        return lo, hi
