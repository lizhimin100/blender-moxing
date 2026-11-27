"""
bslib.py —— 铁匠铺 v6 的几何 / 材质构造库（在 Blender 进程内运行）

设计约束（本轮）：
  * **低模优先**：所有形体只用少量四边面 / 端点面拼，不做雕刻、不加贴图细节。
  * **曲面细分是最后一步**：Builder 只产出低模；平滑版由 `finalize()` 里的
    Bevel + Subdivision 修改器栈塌出来，低模版保留原拓扑。
  * 不出现任何 uv_sphere / ico_sphere —— 圆一律用「少量边的回转体」表达，
    靠细分把棱磨圆，而不是靠堆球。
坐标系：X 右、Y 前（+Y 是正面 → 导出 glTF 后是 Godot 的 −Z）、Z 上；
原点在占地中心，z = 0 是地面。
"""
import math

import bmesh
import bpy
from mathutils import Euler, Vector

TAU = math.tau


# ── 颜色与材质 ────────────────────────────────────────────────────────────────
def srgb(hexstr):
    """#RRGGBB(sRGB) → 线性 RGB（Blender 的 Base Color 走线性）。"""
    h = hexstr.lstrip("#")
    out = []
    for i in range(3):
        c = int(h[i * 2:i * 2 + 2], 16) / 255.0
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return tuple(out)


# 色卡对齐参考图：深板岩屋顶 / 暖木 / 冷灰石 / 蓝金纹章 / 炉火橙
# v8：石更暖一档、木更饱和、金更亮 —— 低模无贴图，色相分离就是全部的"材质感"。
PALETTE = {
    #  名称            基色       粗 糙   金属   自发光      强度
    "stone_light":  ("#9C968C", 0.86, 0.00, None, 0.0),
    "stone_mid":    ("#767069", 0.87, 0.00, None, 0.0),
    "stone_dark":   ("#38332E", 0.91, 0.00, None, 0.0),
    "roof":         ("#363B46", 0.64, 0.00, None, 0.0),
    "roof_edge":    ("#232730", 0.58, 0.00, None, 0.0),
    # 浅一档的"石灰石瓦"：城镇大厅的翼楼披檐用它，俯视时主屋面（深板岩）
    # 与两翼（浅瓦）分成三段，不至于糊成一整块。
    "roof_pale":    ("#525A68", 0.62, 0.00, None, 0.0),
    "roof_wood":    ("#7A5B3C", 0.76, 0.00, None, 0.0),   # 作业坡棚的木瓦顶：俯视时和主屋面拉开色温
    "wood_warm":    ("#9B6236", 0.68, 0.00, None, 0.0),
    # 中棕：木塔身的墙板用它。亮木（平台板 / 梯档）与深木（柱 / 梁）之间需要
    # 第三档，否则 3.9 m 宽的墙和柱梁拉不开层次，整座塔会糊成一团棕。
    "wood_mid":     ("#5F3D1F", 0.72, 0.00, None, 0.0),
    "wood_dark":    ("#3E2718", 0.76, 0.00, None, 0.0),
    "iron":         ("#32353B", 0.36, 0.90, None, 0.0),
    "gold":         ("#D6A64A", 0.22, 0.92, None, 0.0),
    "team":         ("#2E5FB4", 0.56, 0.00, None, 0.0),   # ← 阵营主色（Godot 换这一个材质）
    "team_trim":    ("#F1CD79", 0.44, 0.10, None, 0.0),   # ← 阵营辅色
    "ember":        ("#0E0400", 1.00, 0.00, "#FF5410", 1.40),
    "fire_core":    ("#120600", 1.00, 0.00, "#FFDC90", 2.40),
    "flame_out":    ("#120400", 1.00, 0.00, "#FF3C00", 0.85),
    "flame_in":     ("#1A0A02", 1.00, 0.00, "#FFA028", 1.70),
    "glow":         ("#17171A", 0.60, 0.00, "#FFB861", 1.30),
    # 未点灯的窗玻璃：冷调深青灰 + 极弱的冷自发光。
    # 完全不给自发光的话，暗部里窗洞会变成一个纯黑的"洞"；0.35 的冷光只够托出玻璃的质感，
    # 不会读成"屋里有灯"（glow 是 1.30 的暖橙，两者在画面里一眼能分开）。
    "glass":        ("#2B3843", 0.24, 0.10, "#3B5166", 0.55),
    "coal":         ("#24242A", 0.52, 0.16, "#3A1000", 0.45),
    # ── 神秘圣地（第七座）：魔法水晶。全包唯一的"冷紫"发光体，与暖炉火（ember）、
    #    冷窗光（glass）三分天下：ember 是"有人在干活"，glass 是"屋里有灯"，
    #    crystal 是"这里有东西活着"。两档是必须的 —— 单档水晶在平光下是一块紫板，
    #    棱锥尖（crystal_pale，2.6 倍亮度）才把"晶体"读出来。
    "crystal":      ("#2C1F52", 0.20, 0.06, "#7B4DE8", 0.70),
    "crystal_pale": ("#5C459E", 0.16, 0.06, "#C0A2FA", 1.18),
    # ── 地面（v4 兵营）：夯土 / 沙 / 铺石 / 草。地面必须比墙体明显更暖更暗，
    #    否则俯视时整块场地在曝光下"泛白"，建筑浮在一块白板上（第二轮反馈）。
    "earth":        ("#7B654C", 0.96, 0.00, None, 0.0),   # 夯土（场地主面）
    "earth_dark":   ("#55432F", 0.97, 0.00, None, 0.0),   # 踩实的深色土 / 沟槽
    "sand":         ("#AD9166", 0.94, 0.00, None, 0.0),   # 训练圈沙面
    "paving":       ("#8A8378", 0.90, 0.00, None, 0.0),   # 铺石（比 stone_light 低一档）
    "moss":         ("#51603B", 0.95, 0.00, None, 0.0),   # 墙根草簇
    # ── 角色专用（第十座：块面剑士）。九座建筑一个都不用，`bs_atlas.ATLAS_ORDER`
    #    里也没有它们 —— 建筑图集与 UV 完全不受影响。
    #    角色只有 2.4 m 高，甲片不能用 `iron`（#32353B / 金属 0.9）：那个色在建筑上
    #    是"铁件"，在角色上会糊成一整块黑剪影。所以另起一档有色相的中灰钢。
    "skin":         ("#D2A57F", 0.76, 0.00, None, 0.0),   # 面部 / 下颌
    "cloth":        ("#6E6250", 0.90, 0.00, None, 0.0),   # 内衬布甲（袄）
    "cloth_dark":   ("#4A4238", 0.92, 0.00, None, 0.0),   # 关节缝里的衬 / 颈部
    "steel":        ("#8B9099", 0.40, 0.28, None, 0.0),   # 甲片主色（亮）
    "steel_dark":   ("#5E646D", 0.46, 0.24, None, 0.0),   # 甲的暗面 / 次层甲 / 剑格
    "dark":         ("#1D1A17", 0.86, 0.00, None, 0.0),   # 眼缝 / 嘴 / 缝隙（近黑，非金属）
    # ── 失落帝国（地牢 / 地下城入口）：第十/十一座。
    #    九座人族的石色是**暖灰**（stone_mid #767069）。同一个世界里要一眼分出
    #    "这是更古老、更冷、更潮的东西"，靠的是色相往蓝偏 + 明度整体压一档，
    #    而不是靠做旧贴图 —— 低模无贴图，色相差就是全部的"年代感"。
    "ancient":      ("#5B6069", 0.90, 0.00, None, 0.0),   # 帝国主石：冷灰蓝
    # 帝国石的**中间档**（第 44 格，2026-11-05 地牢入口 v2 追加）。
    # 为什么必须补：ancient 与 ancient_dark 在棚灯下差 4 倍，一套只有两档的石头
    # 在俯视里就是"双色块"——大面全亮、缝全黑，没有中间层。这一档给
    # "背光的侧墙 / 台下段 / 台阶踢面"，整座才有第四级明度。
    "ancient_mid":  ("#454B54", 0.91, 0.00, None, 0.0),
    "ancient_pale": ("#868D95", 0.86, 0.00, None, 0.0),   # 受光棱 / 拱券 / 柱头
    "ancient_dark": ("#23262C", 0.93, 0.00, None, 0.0),   # 门洞内壁 / 砌缝 / 阴影石
    "moss_dark":    ("#35452E", 0.96, 0.00, None, 0.0),   # 背阴苔（比 moss 暗两档）
    "bronze":       ("#5E7F6B", 0.52, 0.70, None, 0.0),   # 铜绿：帝国的金属语言
    "bronze_dark":  ("#2F4238", 0.58, 0.64, None, 0.0),   # 铜绿的暗面 / 铁箍
    # 地底幽绿：与暖炉火（ember）、冷窗光（glass）、魔法紫（crystal）四分天下。
    # 它不是"灯"，是"下面有东西在呼吸" —— 只给门洞深处、符文、菌簇。
    "depth_glow":   ("#04120D", 1.00, 0.00, "#2FD9A0", 1.15),
    # ── 酒馆内部（第十二座）：人族室内。墙是石灰抹面（九座建筑全是石/木外皮，
    #    室内必须有一档"被石灰抹过"的暖白，否则分不出内外）。
    "plaster":      ("#C6B49A", 0.94, 0.00, None, 0.0),
    "copper":       ("#B4703C", 0.40, 0.82, None, 0.0),   # 铜锅 / 灯架 / 龙头
    "cloth_cream":  ("#C2B094", 0.95, 0.00, None, 0.0),   # 桌布 / 麻袋 / 帘
    "ash":          ("#8B8880", 0.97, 0.00, None, 0.0),   # 火塘冷灰 / 踩实的灰土
    # ── 折壳入口（第十四座）：骨。
    #    整套资产里第一次出现"生物材料当结构用"。骨不能是纯白（会读成塑料），
    #    要往黄偏一档、明度压在 0.76 —— 它仍是全图最亮的东西，但不刺眼。
    #    第二档 bone_dark 给骨节缝/断口/老骨：没有第二档，一根骨头读成一根管子。
    "bone":         ("#CFC3AC", 0.80, 0.00, None, 0.0),
    "bone_dark":    ("#9C8B72", 0.88, 0.00, None, 0.0),
    # 折壳入口的内腔。**不是"暗灰"**：门洞占满正面，任何 0.14 的反照率在
    # 影棚灯下都会被抬成中灰，"洞里"就没了。0.045 是"看得见轮廓、看不见面"
    # 的那一档 —— 它跟 coal(#24242A) 差 3 倍，这一档必须单独存在。
    "void":         ("#0B0C0E", 1.00, 0.00, None, 0.0),
    # 折壳入口的门扇。**必须是第三档**：门的明度要正好卡在"墙（ancient 0.36）"
    # 与"洞（void 0.03）"之间。用 ancient 门就并进墙里、看不出有门；用 ancient_dark
    # 门又并进洞里、变成一块黑。0.20 这一档才让"一扇门"从墙里跳出来。
    "door_stone":   ("#2E333B", 0.88, 0.00, None, 0.0),
    # ── 状态资产（第十六批：升级态 / 训练态 / 科研态 / 帐篷）。
    #    **不进 ATLAS_ORDER**：状态档走自己的 STATE_LAYOUT（st_atlas.py），
    #    这里只把颜色登记到统一色卡，免得工地件两处各写一份十六进制。
    #    raw_* 是"生料截面"：新断的石 / 木比砌好的亮一档，这是"未完工"最强的一笔；
    #    它必须在明度上高于 wall（stone_mid 0.36），否则截断面读成"屋顶压顶"。
    "raw_stone":    ("#BCAF96", 0.96, 0.00, None, 0.0),
    "raw_wood":     ("#A26B37", 0.86, 0.00, None, 0.0),
    # 帐篷的布。两档：canvas 是受光面，canvas_dark 是背光面 / 内衬 ——
    # 单档布在平光下是一块奶油色板，两层布叠不出体积。
    "canvas":       ("#D3C09B", 0.97, 0.00, None, 0.0),
    "canvas_dark":  ("#A58E6A", 0.97, 0.00, None, 0.0),
    # 状态档专用的一档"门内灯"：比 glow(1.30) 亮一档，专门给"门开着、里面有灯 /
    # 灯下光斑 / 矛尖反光"这三处。用 glow 做这些地方，在白天光下会被读成
    # "一块浅色漆板"（兵营训练态第一版就是这样）。
    "door_light":   ("#140800", 1.00, 0.00, "#FF8A2E", 2.10),
    # 工地六色（与 cs_kit.SITE_PALETTE 同值：套件直接建同名材质，
    # 图集按这里填色，两条路必须一致）
    "site_timber":      ("#9A7E52", 0.82, 0.00, None, 0.0),
    "site_timber_dark": ("#6E5537", 0.86, 0.00, None, 0.0),
    "site_rope":        ("#D9C79B", 0.95, 0.00, None, 0.0),
    "site_stone":       ("#8F8676", 0.90, 0.00, None, 0.0),
    "site_iron":        ("#3E4249", 0.42, 0.85, None, 0.0),
    "site_cloth":       ("#CFBE96", 0.96, 0.00, None, 0.0),
}


def make_material(name):
    hexcol, rough, metal, emit, estr = PALETTE[name]
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf is None:
        nt.nodes.clear()
        bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
        out = nt.nodes.new("ShaderNodeOutputMaterial")
        nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    col = srgb(hexcol)
    bsdf.inputs["Base Color"].default_value = (*col, 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    if emit:
        bsdf.inputs["Emission Color"].default_value = (*srgb(emit), 1.0)
        bsdf.inputs["Emission Strength"].default_value = estr
        # 自发光面不该再被近处的炉火点光"照亮"：镜面/漫反射一起压掉，
        # 否则火焰会被打成惨白（v8 前几版的粉色就是这里来的）。
        for key, val in (("Specular IOR Level", 0.0), ("Roughness", 1.0)):
            if key in bsdf.inputs:
                try:
                    bsdf.inputs[key].default_value = val
                except Exception:
                    pass
    else:
        bsdf.inputs["Emission Color"].default_value = (0, 0, 0, 1)
        bsdf.inputs["Emission Strength"].default_value = 0.0
    mat.diffuse_color = (*col, 1.0)
    return mat


def all_materials():
    return {k: make_material(k) for k in PALETTE}


# ── 网格基元 ──────────────────────────────────────────────────────────────────
AXES = {
    "X": ((0, 1, 0), (0, 0, 1), (1, 0, 0)),
    "Y": ((1, 0, 0), (0, 0, 1), (0, 1, 0)),
    "Z": ((1, 0, 0), (0, 1, 0), (0, 0, 1)),
}


def mesh_obj(name, verts, faces, mat):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], [tuple(f) for f in faces])
    me.validate(verbose=False)
    me.update()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.data.materials.append(mat)
    recalc_normals(ob)
    return ob


def recalc_normals(ob):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()


def extrude(name, prof, axis, length, origin, mat, offset=0.0):
    """闭合二维多边形沿 axis 拉伸。prof = [(u, v), ...]，origin 是 (u0, v0)。"""
    u_ax, v_ax, e_ax = AXES[axis]
    half = length * 0.5
    u0, v0 = origin
    verts, faces = [], []
    n = len(prof)
    for (u, v) in prof:
        p = Vector(u_ax) * (u + u0) + Vector(v_ax) * (v + v0)
        verts.append(p + Vector(e_ax) * (-half + offset))
    for (u, v) in prof:
        p = Vector(u_ax) * (u + u0) + Vector(v_ax) * (v + v0)
        verts.append(p + Vector(e_ax) * (half + offset))
    faces.append(tuple(range(n)))
    faces.append(tuple(range(n, 2 * n)))
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, n + j, n + i))
    return mesh_obj(name, verts, faces, mat)


def box(name, center, size, mat, rot=None):
    """轴对齐盒；rot = (rx, ry, rz) 弧度时先绕自身中心旋转。"""
    sx, sy, sz = size[0] * 0.5, size[1] * 0.5, size[2] * 0.5
    verts = [
        (-sx, -sy, -sz), (sx, -sy, -sz), (sx, sy, -sz), (-sx, sy, -sz),
        (-sx, -sy, sz), (sx, -sy, sz), (sx, sy, sz), (-sx, sy, sz),
    ]
    faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
             (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    verts = [Vector(v) for v in verts]
    if rot:
        m = Euler(rot, "XYZ").to_matrix()
        verts = [m @ v for v in verts]
    verts = [v + Vector(center) for v in verts]
    return mesh_obj(name, verts, faces, mat)


def beam(name, p0, p1, w, t, mat, up="Z"):
    """两点之间的方木：局部 Y 沿 p0→p1，截面 w × t。"""
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    length = d.length
    if length < 1e-6:
        return None
    ob = box(name, (0, 0, 0), (w, length, t), mat)
    ob.rotation_euler = d.normalized().to_track_quat("Y", up).to_euler()
    ob.location = (p0 + p1) * 0.5
    return ob


def plate_beam(name, p0, p1, w, t, mat):
    """同 beam，但 up 轴固定 Z（用于屋架斜撑这类竖直平面内的构件）。"""
    return beam(name, p0, p1, w, t, mat, up="Z")


def revolve(name, profile, segments, center, mat, phase=0.0):
    """回转体（绕 Z）。profile = [(r, h), ...]；r=0 表示极点。侧壁四边面 + 端面多边形。"""
    cx, cy, cz = center
    verts, faces = [], []
    m = len(profile)
    for s in range(segments):
        a = phase + TAU * s / segments
        ca, sa = math.cos(a), math.sin(a)
        for (r, h) in profile:
            verts.append(Vector((cx + r * ca, cy + r * sa, cz + h)))
    for s in range(segments):
        b, b2 = s * m, ((s + 1) % segments) * m
        for k in range(m):
            k2 = (k + 1) % m
            faces.append((b + k, b + k2, b2 + k2, b2 + k))
    if profile[0][0] > 1e-6:
        faces.append(tuple(range(0, segments * m, m)))
    if profile[-1][0] > 1e-6:
        faces.append(tuple(range(m - 1, segments * m, m)))
    return mesh_obj(name, verts, faces, mat)


def cyl(name, center, r, length, segments, mat, axis="Y", phase=0.0):
    """躺倒的圆柱（沿 axis）。剖圆用 segments 段，靠细分磨圆。"""
    prof = [(r * math.cos(phase + TAU * i / segments),
             r * math.sin(phase + TAU * i / segments)) for i in range(segments)]
    if axis == "Y":
        return extrude(name, prof, "Y", length, (center[0], center[2]), mat, offset=center[1])
    if axis == "X":
        return extrude(name, prof, "X", length, (center[1], center[2]), mat, offset=center[0])
    return None


def tube_band(name, center, r_in, r_out, z0, z1, segments, mat, phase=0.0):
    """闭合圆环带（铁箍 / 栏板），纯四边面。"""
    cx, cy = center
    verts, faces = [], []
    for s in range(segments):
        a = phase + TAU * s / segments
        ca, sa = math.cos(a), math.sin(a)
        verts += [Vector((cx + r_in * ca, cy + r_in * sa, z0)),
                  Vector((cx + r_out * ca, cy + r_out * sa, z0)),
                  Vector((cx + r_out * ca, cy + r_out * sa, z1)),
                  Vector((cx + r_in * ca, cy + r_in * sa, z1))]
    for s in range(segments):
        b, b2 = s * 4, ((s + 1) % segments) * 4
        faces += [(b + 1, b2 + 1, b2 + 2, b + 2),
                  (b + 3, b2 + 3, b2 + 2, b + 3),
                  (b + 2, b2 + 2, b2 + 3, b + 3),
                  (b + 0, b2 + 0, b2 + 1, b + 1)]
    return mesh_obj(name, verts, faces, mat)


def ring_y(name, center, r_in, r_out, length, segments, mat, phase=0.0):
    """竖立圆环（环面在 XZ 平面、法线沿 Y）。窗框 / 门环用。"""
    cx, cy, cz = center
    y0, y1 = cy - length * 0.5, cy + length * 0.5
    verts, faces = [], []
    for s in range(segments):
        a = phase + TAU * s / segments
        ca, sa = math.cos(a), math.sin(a)
        verts += [Vector((cx + r_in * ca, y0, cz + r_in * sa)),
                  Vector((cx + r_out * ca, y0, cz + r_out * sa)),
                  Vector((cx + r_out * ca, y1, cz + r_out * sa)),
                  Vector((cx + r_in * ca, y1, cz + r_in * sa))]
    for s in range(segments):
        b, b2 = s * 4, ((s + 1) % segments) * 4
        faces += [(b + 0, b2 + 0, b2 + 1, b + 1),
                  (b + 1, b2 + 1, b2 + 2, b + 2),
                  (b + 2, b2 + 2, b2 + 3, b + 3),
                  (b + 3, b2 + 3, b2 + 0, b + 0)]
    return mesh_obj(name, verts, faces, mat)


def arch_band(name, cx, cz, r_in, r_out, y0, y1, mat, segs=7):
    """半圆拱环带（拱心 (cx, cz)，厚度 r_out−r_in，沿 Y 从 y0 到 y1）。"""
    verts, faces = [], []
    for s in range(segs + 1):
        a = math.pi * s / segs
        ca, sa = math.cos(a), math.sin(a)
        xi, zi = cx + r_in * ca, cz + r_in * sa
        xo, zo = cx + r_out * ca, cz + r_out * sa
        verts += [Vector((xi, y0, zi)), Vector((xo, y0, zo)),
                  Vector((xo, y1, zo)), Vector((xi, y1, zi))]
    for s in range(segs):
        b, b2 = s * 4, (s + 1) * 4
        faces += [(b + 0, b2 + 0, b2 + 1, b + 1),      # 正面 (y0)
                  (b + 1, b2 + 1, b2 + 2, b + 2),      # 外弧
                  (b + 2, b2 + 2, b2 + 3, b + 3),      # 背面 (y1)
                  (b + 3, b2 + 3, b2 + 0, b + 0)]      # 内弧
    faces += [(0, 1, 2, 3), ((segs * 4) + 3, (segs * 4) + 2, (segs * 4) + 1, (segs * 4) + 0)]
    return mesh_obj(name, verts, faces, mat)


def kite_shield(name, center, w, h, thick, mat):
    """筝形盾：上宽下收、底端出尖；轮廓沿 Y 拉伸。center = (x, y_front, z_mid)。"""
    cx, cy, cz = center
    hw, hh = w * 0.5, h * 0.5
    prof = [(-hw, hh), (hw, hh), (hw * 0.90, -hh * 0.12), (0.0, -hh), (-hw * 0.90, -hh * 0.12)]
    return extrude(name, prof, "Y", thick, (cx, cz), mat, offset=cy)


def plate(name, prof2d, cxz, thick, mat, axis="Y"):
    """任意多边形薄板（纹章 / 压顶 / 旗帜）。prof2d 以 (u,v) 相对 cxz。"""
    return extrude(name, prof2d, axis, thick, cxz, mat)


def slab_plate(name, mat, x0, x1, y0, y1, z0, z1, thick):
    """沿 Y 方向倾斜的板：y0 端高 z0，y1 端高 z1（作业坡棚 / 屋面）。"""
    ang = math.atan2(z0 - z1, y1 - y0)
    ln = math.hypot(y1 - y0, z0 - z1)
    ny, nz = math.sin(ang), math.cos(ang)
    cy = (y0 + y1) * 0.5 + ny * thick * 0.5
    cz = (z0 + z1) * 0.5 + nz * thick * 0.5
    return box(name, ((x0 + x1) * 0.5, cy, cz), (x1 - x0, ln, thick), mat, rot=(-ang, 0, 0))


def lathe(name, rings, segments, mat, phase=0.0):
    """带偏移的回转体：rings = [(r, z, dx, dy), ...] 自下而上，r=0 收成一点。

    火舌要"卷"起来 —— 每层环可以单独平移，于是火焰能歪、能勾，
    而不用堆一堆球（v5 的教训）。
    """
    verts, faces = [], []
    m = len(rings)
    for s in range(segments):
        a = phase + TAU * s / segments
        ca, sa = math.cos(a), math.sin(a)
        for (r, z, dx, dy) in rings:
            verts.append(Vector((dx + r * ca, dy + r * sa, z)))
    for s in range(segments):
        b, b2 = s * m, ((s + 1) % segments) * m
        for k in range(m - 1):
            faces.append((b + k, b2 + k, b2 + k + 1, b + k + 1))
    if rings[0][0] > 1e-6:
        faces.append(tuple(range(0, segments * m, m)))
    if rings[-1][0] > 1e-6:
        faces.append(tuple(range(m - 1, segments * m, m)))
    return mesh_obj(name, verts, faces, mat)


def cone(name, base, tip, r, segments, mat, cap=True, phase=0.0):
    """任意轴的圆锥（砧角 / 尖顶 / 喷嘴）。base / tip 是三维点。"""
    b, t = Vector(base), Vector(tip)
    d = t - b
    if d.length < 1e-6:
        return None
    n = d.normalized()
    up = Vector((0, 0, 1)) if abs(n.z) < 0.9 else Vector((1, 0, 0))
    u = n.cross(up).normalized()
    v = n.cross(u).normalized()
    verts = []
    for i in range(segments):
        a = phase + TAU * i / segments
        verts.append(tuple(b + u * (r * math.cos(a)) + v * (r * math.sin(a))))
    verts.append(tuple(t))
    faces = [(segments, i, (i + 1) % segments) for i in range(segments)]
    if cap:
        faces.append(tuple(range(segments)))
    return mesh_obj(name, verts, faces, mat)


def frustum(name, z0, z1, w0, d0, w1, d1, cx, cy, mat):
    """四坡台座（楼阁基座 / 烟囱帽）：底 w0×d0，顶 w1×d1。"""
    verts = [(cx - w0 * .5, cy - d0 * .5, z0), (cx + w0 * .5, cy - d0 * .5, z0),
             (cx + w0 * .5, cy + d0 * .5, z0), (cx - w0 * .5, cy + d0 * .5, z0),
             (cx - w1 * .5, cy - d1 * .5, z1), (cx + w1 * .5, cy - d1 * .5, z1),
             (cx + w1 * .5, cy + d1 * .5, z1), (cx - w1 * .5, cy + d1 * .5, z1)]
    faces = [(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7),
             (4, 5, 6, 7), (0, 3, 2, 1)]
    return mesh_obj(name, verts, faces, mat)


def octa_profile(r):
    """正八边形（烟囱 / 花盆这类"有棱的圆"）。"""
    return [(r * math.cos(math.tau * k / 8 + math.tau / 16),
             r * math.sin(math.tau * k / 8 + math.tau / 16)) for k in range(8)]


def taper_box(name, p0, p1, w0, w1, t0, t1, mat, up="Z"):
    """两点之间的锥形方料（砧角 / 烟管收口 / 旗杆）。"""
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    length = d.length
    if length < 1e-6:
        return None
    verts = []
    for (w, t, s) in ((w0, t0, 0.0), (w1, t1, 1.0)):
        hw, ht = w * 0.5, t * 0.5
        for (a, b) in ((-hw, -ht), (hw, -ht), (hw, ht), (-hw, ht)):
            verts.append(Vector((a, s * length, b)))
    faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    ob = mesh_obj(name, verts, faces, mat)
    ob.rotation_euler = d.normalized().to_track_quat("Y", up).to_euler()
    ob.location = p0
    return ob


# ── 平滑与收尾 ────────────────────────────────────────────────────────────────
def shade_auto(ob, angle_deg=32.0):
    """按面夹角标记锐边：平缓处平滑、转折处保硬边（不依赖 bpy.ops）。"""
    thresh = math.radians(angle_deg)
    me = ob.data
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    bm = bmesh.new()
    bm.from_mesh(me)
    for e in bm.edges:
        if len(e.link_faces) == 2:
            try:
                e.smooth = e.calc_face_angle(0.0) <= thresh
            except ValueError:
                e.smooth = True
        else:
            e.smooth = False
    bm.to_mesh(me)
    bm.free()
    me.update()


def finalize(ob, bevel=0.03, seg=2, sub=1, angle=30.0, flat=False):
    """塌掉「倒角 → 曲面细分」修改器栈，得到最终网格。"""
    def sset(mod, names, val):
        for n in names:
            if hasattr(mod, n):
                try:
                    setattr(mod, n, val)
                    return True
                except Exception:
                    pass
        return False

    if bevel:
        m = ob.modifiers.new("bev", "BEVEL")
        m.width = bevel
        m.segments = seg
        m.limit_method = "ANGLE"
        m.angle_limit = math.radians(angle)
        sset(m, ("use_clamp_overlap", "clamp_overlap"), True)
        sset(m, ("miter_outer",), "MITER_ARC")
        sset(m, ("harden_normals",), False)
    if sub:
        m = ob.modifiers.new("sub", "SUBSURF")
        m.levels = sub
        m.render_levels = sub
        m.use_limit_surface = False
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    new = bpy.data.meshes.new_from_object(ev)
    old = ob.data
    ob.modifiers.clear()
    ob.data = new
    new.name = old.name
    if old.users == 0:
        bpy.data.meshes.remove(old)
    # 倒角/细分偶尔会留下孤立顶点 —— 清掉，拓扑报告里干净
    bm = bmesh.new()
    bm.from_mesh(new)
    loose = [v for v in bm.verts if not v.link_faces]
    if loose:
        bmesh.ops.delete(bm, geom=loose, context="VERTS")
        bm.to_mesh(new)
        new.update()
    bm.free()
    if flat:
        ob.data.polygons.foreach_set("use_smooth", [False] * len(ob.data.polygons))
        for e in ob.data.edges:
            e.use_edge_sharp = True
        ob.data.update()
    else:
        shade_auto(ob, angle_deg=32.0)
    return ob


def smart_uv(objs, angle=66.0, margin=0.02):
    """给每个（已按材质合并的）对象摊一套不重叠 UV。

    本资产目前**不用贴图**，但 UV 是"以后要上图集 / 贴花 / 烘焙 AO"的接口：
    现在摊好，将来烘图集直接可用，不用回头重做拓扑。
    """
    for ob in objs:
        bpy.ops.object.select_all(action="DESELECT")
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        try:
            bpy.ops.uv.smart_project(angle_limit=math.radians(angle), island_margin=margin)
        except Exception:
            bpy.ops.uv.smart_project()
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")
    return objs


def join_by_material(objs, prefix="GEO"):
    """按材质合并 → 每个材质一个对象（Godot 里就是每材质一个 surface）。"""
    groups = {}
    for ob in objs:
        key = ob.data.materials[0].name if ob.data.materials else "none"
        groups.setdefault(key, []).append(ob)
    out = []
    for mat, items in groups.items():
        if len(items) == 1:
            items[0].name = f"{prefix}-{mat}"
            out.append(items[0])
            continue
        bpy.ops.object.select_all(action="DESELECT")
        for it in items:
            it.select_set(True)
        bpy.context.view_layer.objects.active = items[0]
        bpy.ops.object.join()
        ob = bpy.context.view_layer.objects.active
        ob.name = f"{prefix}-{mat}"
        out.append(ob)
    for ob in out:
        ob.select_set(False)
    bpy.context.view_layer.objects.active = None
    return out


def stats(objs):
    """面数据 + 拓扑规范检查项（四边面 / 三角 / 多边面 / UV 层）。"""
    tris = verts = 0
    quads = tri_faces = ngons = 0
    loose = 0
    uv_layers = 0
    for ob in objs:
        me = ob.data
        me.calc_loop_triangles()
        tris += len(me.loop_triangles)
        verts += len(me.vertices)
        uv_layers += len(me.uv_layers)
        used = set()
        for p in me.polygons:
            n = len(p.vertices)
            if n == 4:
                quads += 1
            elif n == 3:
                tri_faces += 1
            else:
                ngons += 1
            used.update(p.vertices)
        loose += max(0, len(me.vertices) - len(used))
    return {"objects": len(objs), "tris": tris, "verts": verts,
            "faces": quads + tri_faces + ngons,
            "quads": quads, "tris_faces": tri_faces, "ngons": ngons,
            "loose_verts": loose, "uv_layers": uv_layers,
            "materials": len({o.data.materials[0].name for o in objs if o.data.materials})}
