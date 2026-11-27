"""
bs_atlas.py —— 手游档：**纯色材质 → 图集 + 合材质**，以及三级 LOD 的构件筛选

为什么要有这一层
----------------
低模版省的是三角面（14.6k vs 52.5k），但**每个材质一个 surface = 一次 draw call**。
这座建筑有 20 个材质，同屏 30 座就是 600 次提交 —— 手机上是 CPU 先死，不是 GPU。

这一层把它们压到 **4 个材质**：

    ① 图集材质     17 个"石/木/瓦/铁/金/煤/地面/草"合并，颜色走 512² 基础色图，
                   粗糙度/金属度走 512² ORM 图（G=rough, B=metal）
    ② team         纯色，保留"改材质即换阵营"
    ③ team_trim    同上
    ④ 自发光       火焰 / 炭 / 窗光合并，颜色走同一布局的自发光图

做法不是"缩图"，而是**每格填一块纯色、把所有面 UV 钉在格心**：
原模型本来就没有贴图细节，钉死之后采样只取一个点，等于零成本拿到"逐材质颜色"。
格心留 24 px 内缩（512/4 = 128 px 一格），mip 掉到 1/8 也不会串到邻格。

三级 LOD
--------
不靠 Decimate（会把硬边磨圆、把 UV 搅烂），而是**按构件筛**：
模型本来就是 552 个独立构件，远景只留"读得出体量"的那些。
三档共用同一张图集与同一套材质，切档不掉材质。
"""
import math
import os

import bpy
from mathutils import Vector

import bslib as L

# ── 图集布局 ─────────────────────────────────────────────────────────────────
# 5 列 × 9 行 = 45 格；512²；色块内缩 PAD，格心采样
COLS, ROWS, SIZE, PAD = 5, 9, 512, 22

# 材质 → 格子序号（顺序固定，改顺序等于改 UV，别随便动）
ATLAS_ORDER = [
    "stone_light", "stone_mid", "stone_dark", "roof", "roof_edge", "roof_pale",
    "roof_wood", "wood_warm", "wood_dark", "iron", "gold",
    "coal", "earth", "earth_dark", "sand", "paving",
    "moss", "glass", "ember", "flame_out", "flame_in",
    "glow", "team", "team_trim", "wood_mid",
    "crystal", "crystal_pale",
    # 27 起是第十/十一/十二座（地牢 / 地下城入口 / 酒馆内部）与火载体系列。
    # **只许往后追加**：前面 27 格的索引是九座建筑 UV 的全部依据。
    "ancient", "ancient_pale", "ancient_dark", "moss_dark",
    "bronze", "bronze_dark", "depth_glow",
    "plaster", "copper", "cloth_cream", "ash",
    # 39/40 是第十四座（折壳入口）的骨。**40 格到此填满**：再加材质必须扩行
    # （5×8 → 5×9），扩行会让所有格的像素高度变一次，重生成图集与重导 GLB 必须成对。
    "bone", "bone_dark",
    # 41 是折壳入口的洞内黑。**40 格满了才扩行**（8 → 9 行）：
    # 列宽与列序不变 → 前 40 格的 (col,row) 一个都没动，旧 GLB 不受影响；
    # 但格高从 64 px 变 56 px，重新生成图集与重导 GLB 必须成对执行。
    "void",
    # 42 是折壳入口的门扇石（第三档明度）。
    "door_stone",
    # 43 是地牢入口 v2 的中间档石。**追加在末尾**，41/42 的索引不动。
    # 只被地牢入口用到，其它资产不重新导出就不受影响。
    "ancient_mid",
]
# 5 列 × 8 行 = 40 格，用 38 格。**改顺序 = 改 UV**。
# 第 25 格 wood_mid 是哨塔加的（木塔身墙板的中棕），追加在末尾，
# 前面 24 格的索引不变 —— 另三座的图集与 UV 不受影响。
# 兵营用到 earth_dark / sand / glass 三个铁匠铺没有的材质，所以从 4×5 扩到 5×5；
# 神秘圣地又加了 crystal / crystal_pale 两档魔法紫（第 26/27 格），行数 5 → 6。
# 地牢 / 地下城入口 / 酒馆 / 火（第 28–38 格）再把行数 6 → 8：
# 格高从 85 px 变 64 px，但**列宽与列序没变**，所有 UV 仍是"格心"采样，
# 重生成图集与重导出 GLB 必须成对执行（旧 GLB 自带旧图，不受影响）。

TEAM_MATS = ("team", "team_trim")
EMISSIVE_MATS = ("ember", "flame_out", "flame_in", "glow", "coal", "glass",
                 "crystal", "crystal_pale", "depth_glow")
# coal 的自发光很弱（0.45），但它同时用在冠冕宝石、砧面孔上 —— 跟着自发光走，
# 免得为了几块宝石多开一个材质。

EMIT_STRENGTH = 1.8          # 整个自发光材质统一强度，各格颜色按原强度等比缩
TAG_ATLAS = "主体"
TAG_TEAM = "阵营主色"
TAG_TRIM = "阵营辅色"
TAG_EMIT = "自发光"


class Layout:
    """图集布局：列 × 行、边长、色块内缩、材质顺序。

    第十座（角色）是 4×4 / 512² / 内缩 22 —— **与建筑只差行列**，
    所以这一层不复制代码，只把三个常量抽出来。默认布局 `BUILD_LAYOUT`
    与改造前完全一致（5×6，ATLAS_ORDER 顺序不变），九座建筑的图集与 UV 不受影响。
    """

    def __init__(self, cols, rows, size=512, pad=22, order=(), label=""):
        self.cols, self.rows = cols, rows
        self.size, self.pad = size, pad
        self.order = list(order)
        self.label = label
        if len(self.order) > cols * rows:
            raise ValueError("材质数 %d 超过图集格数 %d" % (len(self.order), cols * rows))

    def slot_of(self, name):
        if name not in self.order:
            return None
        i = self.order.index(name)
        return i % self.cols, i // self.cols

    def slot_uv(self, name):
        """格心 UV（0–1）。所有面都钉在这里。"""
        c, r = self.slot_of(name)
        return ((c + 0.5) / self.cols, (r + 0.5) / self.rows)

    def cell(self, name, size=None):
        """该格的像素矩形 (x0, x1, y0, y1)。512/4 = 128 px 一格，内缩 22。"""
        size = size or self.size
        c, r = self.slot_of(name)
        cw, ch = size // self.cols, size // self.rows
        pad = min(self.pad, cw // 4, ch // 4)
        return (c * cw + pad, (c + 1) * cw - pad,
                r * ch + pad, (r + 1) * ch - pad)


BUILD_LAYOUT = Layout(COLS, ROWS, SIZE, PAD, ATLAS_ORDER, "建筑")


def slot_of(name, layout=None):
    """材质名 → (列, 行)；不在表里的返回 None。"""
    return (layout or BUILD_LAYOUT).slot_of(name)


def slot_uv(name, layout=None):
    """格心 UV（0–1）。所有面都钉在这里。"""
    return (layout or BUILD_LAYOUT).slot_uv(name)


def tag_of(mat_name):
    if mat_name in TEAM_MATS:
        return mat_name
    if mat_name in EMISSIVE_MATS:
        return TAG_EMIT
    return TAG_ATLAS


# ── 图集贴图 ─────────────────────────────────────────────────────────────────
def _lin(hexstr):
    """线性值（给材质 default_value 用）。"""
    return L.srgb(hexstr)


def _raw(hexstr):
    """sRGB 原始值（给 image.pixels 用）。

    坑：`image.pixels` 存的是**按该图色彩空间编码后的原始值**，不是线性值。
    往 sRGB 图里写线性值 = 整张图被当成"更暗的 sRGB"解码，渲染出来暗一档。
    """
    h = hexstr.lstrip("#")
    return tuple(int(h[i * 2:i * 2 + 2], 16) / 255.0 for i in range(3))


def build_images(out_dir, size=None, label="铁匠铺", layout=None, include_emit=True):
    """生成图集：基础色 / ORM（/ 自发光）。返回 {tag: filepath}。

    label 决定 Image 数据块的名字（`<label>_图集_主体`）—— 名字会被写进 .blend
    和 GLB，兵营的文件里出现"铁匠铺_图集"会让人以为拿错了文件。

    include_emit=False：角色没有自发光材质，不出那张全黑的图（少一张没用的贴图）。
    """
    lay = layout or BUILD_LAYOUT
    size = size or lay.size
    os.makedirs(out_dir, exist_ok=True)
    n = size * size * 4

    base_px = [0.0] * n
    orm_px = [0.0] * n
    emit_px = [0.0] * n if include_emit else None

    # 先把底填成中性深灰（不被任何格子覆盖的区域不会采样到，但看着干净）
    for i in range(size * size):
        base_px[i * 4 + 3] = 1.0
        orm_px[i * 4 + 0] = 1.0
        orm_px[i * 4 + 1] = 0.9
        orm_px[i * 4 + 2] = 0.0
        orm_px[i * 4 + 3] = 1.0
        if emit_px is not None:
            emit_px[i * 4 + 3] = 1.0

    for name in lay.order:
        hexcol, rough, metal, emit, estr = L.PALETTE[name]
        x0, x1, y0, y1 = lay.cell(name, size)
        col = _raw(hexcol)
        # 自发光色 × 相对强度（统一强度 EMIT_STRENGTH 后仍保持彼此明暗关系）
        if emit and emit_px is not None:
            ec = _raw(emit)
            k = min(1.0, estr / EMIT_STRENGTH)
            ecol = (ec[0] * k, ec[1] * k, ec[2] * k)
        else:
            ecol = (0.0, 0.0, 0.0)
        for y in range(y0, y1):
            row = y * size
            for x in range(x0, x1):
                i = (row + x) * 4
                base_px[i], base_px[i + 1], base_px[i + 2] = col
                orm_px[i + 1] = rough
                orm_px[i + 2] = metal
                if emit_px is not None:
                    emit_px[i], emit_px[i + 1], emit_px[i + 2] = ecol

    out = {}
    tags = [(TAG_ATLAS, base_px, "sRGB"), ("ORM", orm_px, "Non-Color")]
    if emit_px is not None:
        tags.append((TAG_EMIT, emit_px, "sRGB"))
    for tag, px, cs in tags:
        img = bpy.data.images.new("%s_图集_%s" % (label, tag), size, size, alpha=False)
        # 颜色空间必须在写像素**之前**设：image.colorspace_settings.name = ... 会
        # 让 Blender 重新解释缓冲区，先写像素再改色彩空间 = 整张图被清成黑色。
        img.colorspace_settings.name = cs
        img.pixels.foreach_set(px)
        img.update()                      # 不 update() 的话 save() 写出去是全黑
        img.filepath_raw = os.path.join(out_dir, "%s.png" % tag)
        img.file_format = "PNG"
        img.save()
        img.pack()
        out[tag] = img
    return out


# ── 材质 ─────────────────────────────────────────────────────────────────────
def _principled(mat):
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    o = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(b.outputs["BSDF"], o.inputs["Surface"])
    return nt, b


def build_materials(imgs):
    """建材质（建筑 4 个 / 角色 3 个）。返回 {tag: material}。

    **先清掉同名的**：模型自带的 20 个材质里就有 `team` / `team_trim`，
    直接 new 会被 Blender 改名成 `team.001` —— 换色脚本按名字找 `team`，找不到就静默失效。
    这个 bug 在 GLB 回查里表现为材质名带着 `.001` 后缀。

    imgs 里没有 TAG_EMIT 就不建自发光材质 —— 角色档没有发光件，3 个材质就够。
    """
    mats = {}
    # 注意这里要清的是**实际会被创建的材质名**：主体 / 自发光 / team / team_trim。
    # TAG_TEAM 是"阵营主色"（图集里那一格的中文名），不是材质名 —— 拿它去清是清不到的。
    for name in [TAG_ATLAS] + [t for t in (TAG_EMIT,) if t in imgs] + list(TEAM_MATS):
        old = bpy.data.materials.get(name)
        if old is not None:
            bpy.data.materials.remove(old)

    # ① 主体：基础色 + ORM
    m = bpy.data.materials.new(TAG_ATLAS)
    nt, b = _principled(m)
    tb = nt.nodes.new("ShaderNodeTexImage")
    tb.image = imgs[TAG_ATLAS]
    tb.interpolation = "Closest"          # 纯色块，最近邻采样最干净
    nt.links.new(tb.outputs["Color"], b.inputs["Base Color"])
    to = nt.nodes.new("ShaderNodeTexImage")
    to.image = imgs["ORM"]
    to.interpolation = "Closest"
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(to.outputs["Color"], sep.inputs["Color"])
    nt.links.new(sep.outputs["Green"], b.inputs["Roughness"])
    nt.links.new(sep.outputs["Blue"], b.inputs["Metallic"])
    mats[TAG_ATLAS] = m

    # ②③ 阵营色：纯色，保留"改材质即换色"
    for name in TEAM_MATS:
        hexcol, rough, metal, _e, _s = L.PALETTE[name]
        m = bpy.data.materials.new(name)
        nt, b = _principled(m)
        b.inputs["Base Color"].default_value = (*_lin(hexcol), 1.0)
        b.inputs["Roughness"].default_value = rough
        b.inputs["Metallic"].default_value = metal
        m.diffuse_color = (*_lin(hexcol), 1.0)
        mats[name] = m

    # ④ 自发光（没有这张图就不建：角色档）
    if TAG_EMIT in imgs:
        m = bpy.data.materials.new(TAG_EMIT)
        nt, b = _principled(m)
        b.inputs["Base Color"].default_value = (0.02, 0.02, 0.02, 1)
        b.inputs["Roughness"].default_value = 1.0
        b.inputs["Metallic"].default_value = 0.0
        te = nt.nodes.new("ShaderNodeTexImage")
        te.image = imgs[TAG_EMIT]
        te.interpolation = "Closest"
        nt.links.new(te.outputs["Color"], b.inputs["Emission Color"])
        b.inputs["Emission Strength"].default_value = EMIT_STRENGTH
        mats[TAG_EMIT] = m
    return mats


# ── UV 与合并 ────────────────────────────────────────────────────────────────
def pin_uv(objs, layout=None):
    """把每个对象的 UV 全部钉到它材质的格心（先清掉原有 UV 层）。"""
    layt = layout or BUILD_LAYOUT
    for ob in objs:
        if not ob.data.materials:
            continue
        name = ob.data.materials[0].name
        uv = layt.slot_uv(name)
        if uv is None:
            raise KeyError("材质 %s 不在图集布局里（%s）" % (name, layt.label))
        me = ob.data
        while me.uv_layers:
            me.uv_layers.remove(me.uv_layers[0])
        lay = me.uv_layers.new(name="UVMap")
        u, v = uv
        for l in lay.data:
            l.uv = (u, v)


def pack(objs, imgs, prefix="BS"):
    """按目标材质把 20 个对象合并成 4 个。返回新对象列表。

    prefix 是对象名前缀（BS / BR）—— 名字会出现在 .blend 大纲和引擎层级里，
    兵营的文件里出现 "BS-主体" 会误导接手的人。
    """
    # 先按**原材质名**分组，再建新材质：build_materials 会清掉同名的 team/team_trim，
    # 顺序反了就读不到原材质名，所有件都会掉进"主体"。
    groups = {}
    for ob in objs:
        if not ob.data.materials:
            continue
        tag = tag_of(ob.data.materials[0].name)
        groups.setdefault(tag, []).append(ob)
    mats = build_materials(imgs)

    out = []
    for tag, items in groups.items():
        bpy.ops.object.select_all(action="DESELECT")
        for it in items:
            it.select_set(True)
        bpy.context.view_layer.objects.active = items[0]
        if len(items) > 1:
            bpy.ops.object.join()
        ob = bpy.context.view_layer.objects.active
        ob.name = prefix + "-" + tag
        ob.data.materials.clear()
        ob.data.materials.append(mats[tag])
        out.append(ob)
    bpy.ops.object.select_all(action="DESELECT")
    return out


# ── 三级 LOD ─────────────────────────────────────────────────────────────────
# 白名单：整组保留，不按体积拆（拆了就会出现"旗布悬在半空""磨石轮子没有支架"）
LOD_KEEP_1 = ("std_", "shield_", "kite", "banner_", "wbanner_", "cup_",
              "saw_", "timber_", "wheel_", "hut_",
              "ch_breast", "ch_shaft",
              # 城镇大厅 v2：钟亭 / 尖顶 / 旗是一组细杆撑大盖，单件筛会留下悬空件
              "bf_", "sp_", "flag_",
              # 伐木场：门架 / 原木堆 / 飞轮 / 小屋是一组"细杆撑大盖 + 圆端面群"，
              # 单件筛会把它们筛成悬空的散件，必须整组留。
              "saw_", "timber_", "wheel_", "hut_",
              # 箭塔 v2：整顶亭的柱 / 檐梁 / 檐口 / 攒尖顶 / 箭饰 / 军旗是
              # "细杆撑大盖"的结构链与识别主体，按单件体积筛会留下悬空的冠
              "post_", "head_", "rail_", "eave_", "spire_", "arw_", "fl_",
              "banner_", "led_", "bkt_", "deck_",
              # 神秘圣地：采光亭 / 晶尖 / 穹顶亮脊 / 水晶 / 还愿幡 / 台基符文
              # 都是"细杆撑大盖"或"单件太小但整组必需"，必须整组留
              "lan_", "spire_", "finial", "dome_rib", "dome_boss", "domecrys",
              "crys_", "lamp_", "flag_", "bay_", "dais_mark", "dais_glyph",
              "dais_rune", "cella_votive", "portal_glass", "drumwin",
              # 蒸汽车坊：吊链 / 滑车是"细杆吊重物"的那条链，单件筛会断链；
              # 锅炉的箍 / 汽笛 / 阀、山墙木构、天窗、通风百叶、门厅火光同理
              "crane_", "boil_", "roof_sky", "roof_vane", "her_",
              "hall_vent", "hall_blouv", "gab_rail", "gab_stud", "gab_collar",
              "gab_king", "gab_louv", "ann_port", "ann_fire", "door_glow")
LOD_KEEP_2 = ("std_flag", "std_pole", "std_ball", "shield_ch_field", "shield_ch_rim",
              "banner_L_cloth", "banner_R_cloth", "banner_B_cloth",
              # 城镇大厅：钟塔整组必须一起留（角柱只有 0.03 m³，单件筛会留下悬空的顶盖）；
              # 门套 / 盾 / 侧墙垂旗 / 钟面 / 塔顶旗是正立面的"脸"和职责，远景也得在。
              "tw_", "gate_", "shield_", "wbanner", "clock_",
              "bf_", "sp_", "flag_",
              # 哨塔：护栏 / 外梯 / 亭柱 / 斜撑是"细杆撑大盖"的结构链，
              # 按单件体积筛会留下悬空的平台和屋顶（远景整组保留）
              "p1_", "p2_", "ldr_", "cp_col", "br1_", "br2",
              # 箭塔 v2：远景只留"攒尖顶 + 檐口 + 箭饰 + 亭柱 + 军旗"这五组，
              # 栏板 / 战棚地板体积够大，阈值会自动留下
              "spire_", "eave_", "arw_", "fl_", "post_", "rail_", "banner_",
              "gate_",
              # 农场：筒仓 / 板车 / 草垛 / 围栏门是"体量 + 道具"的识别件，
              # 按单件体积筛会把筒仓的箍和爬梯丢掉，留下一个光筒
              "silo_", "cart_", "hay_", "field_gate", "gate_post", "well_",
              # 神秘圣地：远景只留"穹顶亮脊 + 采光亭晶尖 + 发光门 + 队色"这几组。
              # 鼓座 / 穹顶壳 / 山门体块 体积够大，会被阈值自动留下，不用列。
              "dome_rib", "dome_boss", "lan_", "spire_", "finial", "portal_",
              "crys_main", "cella_votive", "dais_mark", "drum_band", "drumwin_glass",
              # 蒸汽车坊：远景只留"队色（脊/旗/盾/烟囱箍）+ 天窗节奏 + 山墙木构 + 门"。
              # 锅炉 / 烟囱 / 屋面 / 台基体积够大，阈值会自动留下。
              "her_", "roof_sky", "gab_rail", "gab_collar", "gab_king", "gab_louv",
              "door_leaf", "door_tymp", "boil_neck", "boil_whistle", "boil_hoop",
              # 地牢：远景只要"门楼 + 断塔 + 外梯 + 吊笼 + 两面旗"
              "gt_", "tw_", "st_", "gib_", "bnr_", "pd_arch", "pd_lintel",
              # 地下城入口：远景要"拱门 + 两尊守卫像 + 符文环 + 火把"
              "clf_arch", "clf_key", "stat_", "rune_", "torch_", "bnr_",
              # 酒馆：远景要"吊灯 + 吧台 + 壁炉 + 楼梯 + 桌椅 + 横幅"（这是一间屋子）
              "chn_", "bar_", "hth_", "stair_", "tbl_", "stl_", "lan_", "bnr_",
              "wall_pier", "prop_",
              # 四件火：整件保留（它们本来就小，删一件就不成火）
              "cf_", "tr_", "bz_", "bf_", "flame_", "pro_braz")

# 道具组：**整组一起走或一起留**。按单个构件筛会把"磨石轮"留下、把支架丢掉，
# 远景就会出现一块浮在空中的圆盘（v1 就踩到了）。
PROP_PREFIXES = ("anvil", "tool", "quench", "bucket", "coal_a", "coal_b", "coal_bin",
                 "coal_lump", "ingots", "grindstone", "gs_", "pot_", "log",
                 # 城镇大厅的广场陈设：远景整组去掉（留一根孤零零的旗杆比没有更糟）
                 "board", "braz", "barrel", "crate", "banner_pole", "banner_arm",
                 "banner_cloth", "banner_trim", "banner_ring",
                 # 蒸汽车坊的道具：煤堆 / 煤袋 / 桶 / 煤仓 / 铁锹 —— 远景整组去掉
                 "prop_")
# 地面碎屑：中景就可以丢（远看只是噪点）
DECOR_PREFIXES = ("tuft", "rubble", "plank_loose", "coal_spill")

# 远景专属剔除：钟面刻度/指针、钟亭拱石、尖顶铅箍等小件。
# 这些件在 30 m 外只剩 1–2 像素，却是远景面数的大头。
LOD2_DROP = ("clock_f_tick", "clock_s_tick", "clock_f_hand", "clock_s_hand",
             "clock_f_pin", "clock_s_pin", "tw_pier", "bf_arch", "bf_jamb",
             "bf_clapper", "bf_bell_top", "bf_bell_chain", "sp_band",
             "sp_hip", "sp_gold", "flag_crest", "tw_band_t",
             # 神秘圣地：远景丢"细杆 / 小边条 / 符文碎片"——它们在 30 m 外
             # 只剩 1–2 像素，却是远景面数的大头
             "drum_col", "drumwin_bar", "cella_jamb", "cella_lintel", "cella_stud",
             "cella_rod", "cella_votive_tail", "niche_jamb", "niche_arch", "step_edge",
             "cornice_shadow", "portal_bar", "portal_arch", "dais_glyph", "bay_frieze_f",
             "bay_frieze_l", "bay_pil_base", "lan_col", "lan_rail", "flag_ring",
             "flag_arm", "flag_tail", "dome_boss_gem")


def _dims(ob):
    co = ob.data.vertices
    if not len(co):
        return [0, 0, 0]
    return sorted(max(v.co[i] for v in co) - min(v.co[i] for v in co) for i in range(3))


def filter_lod(items, level):
    """按构件筛 LOD。

    判据用**包围盒体积**，不用最长边 —— 瓦垄、旗布、横杆这类"又长又薄"的件
    最长边够大，但视觉上只是几条线，占的面却不少。

    0 = 全量（近景，14.6k tri）
    1 = 中景：体积 ≥ 0.012 m³（铆钉、吊环、流苏、草叶、碎石、铰链先走）
    2 = 远景：体积 ≥ 0.22 m³ + 旗/盾白名单（只留体量与阵营旗）
    """
    if level == 0:
        return list(items)
    vol_thr = 0.012 if level == 1 else 0.22
    keep_names = LOD_KEEP_1 if level == 1 else LOD_KEEP_2
    keep, drop = [], []
    for it in items:
        ob = it[0]
        n = ob.name
        if level >= 2 and n.startswith(PROP_PREFIXES):
            drop.append(it)
            continue                     # 远景不要道具
        if level >= 2 and n.startswith(LOD2_DROP):
            drop.append(it)
            continue                     # 远景不要钟/尖顶小件
        if n.startswith(DECOR_PREFIXES):
            drop.append(it)
            continue                     # 中景起就不要地面碎屑
        d = _dims(ob)
        vol = d[0] * d[1] * d[2]
        if vol >= vol_thr or n.startswith(keep_names):
            keep.append(it)
        else:
            drop.append(it)
    # 被筛掉的构件必须从场景里删掉：只是"不 join"的话它们会留在场景里，
    # 而且因为没走 mirror_x，会以镜像前的坐标飘在建筑外面（v1 就飘了一整片）。
    for it in drop:
        try:
            bpy.data.objects.remove(it[0], do_unlink=True)
        except Exception:
            pass
    return keep
