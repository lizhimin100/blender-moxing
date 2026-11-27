"""tr_tex.py —— 地形底材（Albedo）：草地 / 泥土，512²，无缝平铺

为什么单独一层
--------------
九座建筑的材质是"每格纯色钉图集"，地面不能也这么干：一整块纯色草地铺 100 m，
俯视时读成一张色纸，建筑的体积感全被"底板"吃掉。地面需要的是**大色块 + 极低频
的明暗起伏**，而不是细节 —— 它必须在任何镜头距离下都退到建筑后面去。

三条硬约束（本文件所有参数都是为它们服务的）
--------------------------------------------
1. **无缝**：Blender 的 Noise / Voronoi 都有自己的坐标空间，UV 在 0/1 处不连续。
   这里把 UV 映射到 4D 圆环（torus）上再采样：
       x = R·cos(2πu), y = R·sin(2πu), z = R·cos(2πv), w = R·sin(2πv)
   取 R = 1/(2π)，圆环的**弧长正好等于 1 个 tile**，所以 Noise 的 Scale 直接就是
   "一个 tile 里有几个周期"。圆环局部等距于平面（没有拉伸），4D 噪声切出来的
   就是一张各向同性的二维噪声，边界处天然对齐 —— 不需要 offset 缝合、不会留硬边。
2. **平涂**：Noise 的 Scale 大、Detail 低（1 左右），再过一道 **ColorRamp** 切成
   3 个平顶色阶（两个同色相邻色标 = 平涂段，中间那段斜坡 = 软边）。
   不做高频细节，不做照片级叠加。
3. **能被二次打光**：输出是纯 Albedo —— 场景里没有任何灯光，材质是 Emission，
   色彩管理 Standard。渲出来的像素 = 节点里的颜色，引擎拿到之后自己乘光照，
   不会出现"烘焙进去的假阴影"。

单位：1 tile = 8 m（512 px → 64 px/m）。建筑的占地是 5–18 m，8 m 的重复周期
在 RTS 机位下读不出 repetition（6 m 试过，40 m 视野里能看出格子节奏）；
grass clump 的直径约 10 cm，正好是"小草点"。

用法
----
    blender.exe -b --factory-startup --python blender/bs_v6/tr_tex.py
    blender.exe -b --factory-startup --python blender/bs_v6/tr_tex.py -- calib   # 测分布
"""
import json
import math
import os
import sys

import bpy
import numpy as np

# ── 全局规格 ────────────────────────────────────────────────────────────────
SIZE = 512                  # 交付尺寸
SS = 2                      # 超采样倍数（渲 1024 再 2×2 盒式降采样）
TILE_M = 8.0                # 一个 tile 覆盖的世界尺寸（米）
OUT_DIR = "D:/测试一/assets/地形"
SRC_DIR = "D:/测试一/blender/_源文件/地形"   # .blend 是源文件，不进 assets
DOC_DIR = "D:/测试一/docs/地形"
RAW_DIR = "D:/测试一/docs/地形/_raw"
CALIB = "calib" in sys.argv

# ── 配色 ────────────────────────────────────────────────────────────────────
# 全部从 bslib.PALETTE 里"借"出来再抬一档明度：
#   草地 ← moss(#51603B) 提亮 + 往黄偏          → 暖黄绿，比墙体(#9C968C)暗 20%
#   泥土 ← earth(#7B654C) / sand(#AD9166) 之间   → 底座边缘的踩实土色
# 三条色阶的差值刻意压在 3–5% 明度内：远看是一块干净的绿/土，近看才分得出层次。
GRASS = {
    "dark":  "#818B4D",
    "base":  "#869050",
    "light": "#8C9657",
    "clump": "#55602E",
}
DIRT = {
    "dark":  "#73614A",
    "base":  "#78664E",
    "light": "#7D6B53",
    "crack": "#655440",
}
# 3D 地块专用：模型本身有 1.2 m 的大裂板，贴图只负责"更细一档的裂纹"，
# 所以底色比 泥土 略亮（板顶被晒白），裂纹更细更淡。
DIRT_FINE = {
    "dark":  "#66543E",
    "base":  "#6B5941",
    "light": "#705E46",
    "crack": "#524230",
}

# 噪声归一化区间：calib 量出来的 p2 / p98。
# 直接把阈值写成 0.5 一定会切偏 —— Blender 的 FBM 噪声**线性值**集中在 0.31–0.69
# （PNG 里看到的 sRGB 值是 0.56–0.86，别拿它当阈值），而且这个区间随
# Scale/Detail/Roughness 变，所以每层都先归一化再切。
NORM = {
    "草_big": (0.309, 0.694),
    "草_mid": (0.270, 0.694),
    "土_big": (0.292, 0.680),
    "土_fine": (0.279, 0.701),
}

# 色块的切点写在各自的 ColorRamp 里（见 build_grass / build_dirt）：
# 两个同色相邻色标 = 平顶段，中间的斜坡 = 软边
TUFT_AMT = 0.52       # 草叶最深处的不透明度（1.0 = 完全用 clump 色）


# ── 颜色工具 ────────────────────────────────────────────────────────────────
def _srgb2lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hex_lin(h):
    h = h.lstrip("#")
    return tuple(_srgb2lin(int(h[i * 2:i * 2 + 2], 16) / 255.0) for i in range(3))


# ── 节点构造小工具 ──────────────────────────────────────────────────────────
def _in(n, name, typ=None):
    for s in n.inputs:
        if s.name == name and (typ is None or s.type == typ):
            return s
    raise KeyError("%s 没有输入 %s/%s" % (n.bl_idname, name, typ))


def _out(n, name, typ=None):
    for s in n.outputs:
        if s.name == name and (typ is None or s.type == typ):
            return s
    raise KeyError("%s 没有输出 %s/%s" % (n.bl_idname, name, typ))


class G:
    """一张 Albedo 的节点图。所有坐标都从同一个 torus 出发，保证无缝。"""

    def __init__(self, name):
        mat = bpy.data.materials.get(name)
        if mat:
            bpy.data.materials.remove(mat)
        self.mat = bpy.data.materials.new(name)
        self.mat.use_nodes = True
        self.nt = self.mat.node_tree
        self.nt.nodes.clear()
        self._x = 0

    # -- 基础 --
    def n(self, bl, dx=180):
        node = self.nt.nodes.new(bl)
        node.location = (self._x, 0)
        self._x += dx
        return node

    def link(self, a, b):
        self.nt.links.new(a, b)

    def feed(self, sock, v):
        if isinstance(v, bpy.types.NodeSocket):
            self.link(v, sock)
        elif isinstance(v, str):
            sock.default_value = (*hex_lin(v), 1.0)
        elif isinstance(v, (tuple, list)):
            sock.default_value = tuple(v) if len(v) == len(sock.default_value) \
                else (*v, 1.0)
        else:
            sock.default_value = v

    def math(self, op, a, b=None, c=None, clamp=False):
        m = self.n("ShaderNodeMath", 130)
        m.operation = op
        m.use_clamp = clamp
        for i, v in enumerate((a, b, c)):
            if v is not None:
                self.feed(m.inputs[i], v)
        return m.outputs[0]

    def vmath(self, op, a, b=None, scale=None):
        m = self.n("ShaderNodeVectorMath", 130)
        m.operation = op
        self.feed(m.inputs[0], a)
        if b is not None:
            self.feed(m.inputs[1], b)
        if scale is not None:
            self.feed(_in(m, "Scale"), scale)
        return _out(m, "Value") if op in ("LENGTH", "DISTANCE", "DOT_PRODUCT") \
            else _out(m, "Vector")

    def combine(self, x, y, z):
        c = self.n("ShaderNodeCombineXYZ", 130)
        for i, v in enumerate((x, y, z)):
            self.feed(c.inputs[i], v)
        return c.outputs[0]

    def sep(self, vec):
        s = self.n("ShaderNodeSeparateXYZ", 130)
        self.link(vec, s.inputs[0])
        return s

    def maprange(self, fac, a, b, c=0.0, d=1.0, interp="SMOOTHSTEP"):
        mr = self.n("ShaderNodeMapRange", 170)
        mr.data_type = "FLOAT"
        mr.interpolation_type = interp
        mr.clamp = True
        self.feed(_in(mr, "Value"), fac)
        self.feed(_in(mr, "From Min"), a)
        self.feed(_in(mr, "From Max"), b)
        self.feed(_in(mr, "To Min"), c)
        self.feed(_in(mr, "To Max"), d)
        return _out(mr, "Result")

    def norm(self, n, key):
        """把噪声压到 0–1（用 calib 的 p2/p98）。之后所有阈值都按"面积比例"读。"""
        lo, hi = NORM[key]
        return self.maprange(n, lo, hi, 0.0, 1.0, interp="LINEAR")

    def mix(self, fac, ca, cb):
        m = self.n("ShaderNodeMix", 170)
        m.data_type = "RGBA"
        m.blend_type = "MIX"
        m.clamp_factor = True
        self.feed(_in(m, "Factor", "VALUE"), fac)
        self.feed(_in(m, "A", "RGBA"), ca)
        self.feed(_in(m, "B", "RGBA"), cb)
        return _out(m, "Result", "RGBA")

    def ramp(self, fac, stops, interp="EASE"):
        """色阶：[(位置, 颜色), ...] → ColorRamp。

        为什么用 ColorRamp 而不是两三个 MapRange+Mix：色标本身就是"这一档从哪开始、
        下一档占多少面积"，调参时直接拖，不用反推归一化阈值；而且平顶段（两个同色
        相邻色标）天然给出"平涂大色块"，中间那段斜坡就是软边。
        """
        cr = self.n("ShaderNodeValToRGB", 190)
        cr.color_ramp.interpolation = interp
        el = cr.color_ramp.elements
        while len(el) > 1:
            el.remove(el[-1])
        el[0].position, el[0].color = stops[0][0], (*hex_lin(stops[0][1]), 1.0)
        for pos, col in stops[1:]:
            e = el.new(pos)
            e.color = (*hex_lin(col), 1.0)
        fac_sock = next((x for x in cr.inputs if x.name in ("Factor", "Fac")), None)
        if fac_sock is None:
            raise KeyError("ColorRamp 没有 Fac/Factor 输入")
        self.feed(fac_sock, fac)
        return _out(cr, "Color")

    def gray(self, v):
        """标量 → 灰度色（calib 用）。"""
        c = self.n("ShaderNodeCombineXYZ", 130)
        for i in range(3):
            self.feed(c.inputs[i], v)
        return c.outputs[0]

    # -- 无缝坐标 --
    def torus(self, uv, radius=None):
        """UV(0..1) → 4D 圆环坐标 (Vector(x,y,z), W)。周期 1，弧长 1。"""
        r = 1.0 / math.tau if radius is None else radius
        s = self.sep(uv)
        comp = {}
        for axis, tag in ((0, "u"), (1, "v")):
            ang = self.math("MULTIPLY", s.outputs[axis], math.tau)
            comp["c" + tag] = self.math("MULTIPLY", self.math("COSINE", ang), r)
            comp["s" + tag] = self.math("MULTIPLY", self.math("SINE", ang), r)
        vec = self.combine(comp["cu"], comp["su"], comp["cv"])
        return vec, comp["sv"]

    # -- 噪声 / 胞元 --
    def noise4(self, vec, w, scale, detail=1.0, rough=0.45, distortion=0.0,
               offset=(0.0, 0.0, 0.0), out="Factor"):
        n = self.n("ShaderNodeTexNoise", 190)
        n.noise_dimensions = "4D"
        n.noise_type = "FBM"
        if any(offset):
            add = self.n("ShaderNodeVectorMath", 110)
            add.operation = "ADD"
            self.link(vec, add.inputs[0])
            add.inputs[1].default_value = offset
            vec = _out(add, "Vector")
        self.link(vec, _in(n, "Vector"))
        self.link(w, _in(n, "W"))
        _in(n, "Scale").default_value = scale
        _in(n, "Detail").default_value = detail
        _in(n, "Roughness").default_value = rough
        _in(n, "Distortion").default_value = distortion
        return _out(n, out)

    def white4(self, vec, w, out="Color"):
        """4D White Noise：逐格哈希（同格同值、跨格独立），输入周期则输出也周期。"""
        n = self.n("ShaderNodeTexWhiteNoise", 160)
        n.noise_dimensions = "4D"
        self.link(vec, _in(n, "Vector"))
        self.link(w, _in(n, "W"))
        return _out(n, out)

    def voronoi4(self, vec, w, scale, feature="DISTANCE_TO_EDGE", randomness=1.0):
        v = self.n("ShaderNodeTexVoronoi", 210)
        v.voronoi_dimensions = "4D"
        v.feature = feature
        v.distance = "EUCLIDEAN"
        self.link(vec, _in(v, "Vector"))
        self.link(w, _in(v, "W"))
        _in(v, "Scale").default_value = scale
        _in(v, "Randomness").default_value = randomness
        return v

    # -- 出口 --
    def emission(self, color, strength=1.0):
        """纯 Emission：场景无灯、无阴影，渲出来即 Albedo。"""
        em = self.n("ShaderNodeEmission", 190)
        out = self.n("ShaderNodeOutputMaterial", 150)
        self.feed(_in(em, "Color"), color)
        _in(em, "Strength").default_value = strength
        self.link(_out(em, "Emission"), _in(out, "Surface"))
        return em


def uv_node(g):
    uvn = g.n("ShaderNodeUVMap")
    uvn.uv_map = "UVMap"
    return _out(uvn, "UV")


# ── 草地：场 ────────────────────────────────────────────────────────────────
def grass_fields(g, uv):
    """两个低频场：大色块 / 中频微调。草簇是几何型图案，见 tuft_layer。"""
    vec, w = g.torus(uv)

    # 主色块：Scale 4.6 → 一个 tile 里 4–5 片。
    # 只切 1–2 片的话，每一块拼图里都有一个完整的"疤"，它就成了地标，平铺时一眼看出重复。
    n_big = g.noise4(vec, w, scale=4.6, detail=1.0, rough=0.42, distortion=0.28)

    # 中频微调：换一个 offset 采第二层，避免和主色块同相位
    n_mid = g.noise4(vec, w, scale=7.5, detail=0.5, rough=0.5,
                     offset=(1.7, 3.1, 5.3))
    return n_big, n_mid


# ── 草地：草簇 ──────────────────────────────────────────────────────────────
def tuft_layer(g, uv, vec, w):
    """草簇 = 一丛三片细叶（低模草的标准画法），不是"一坨斑"。

    上一版用"噪声阈值斑块"当草簇，远看像抹布上的污点 —— 它只有轮廓、没有结构。
    草之所以读成草，靠的是**几根从根部张开、梢部散开的细长形状**。所以按几何画：

        UV×N 切格（周期）→ 格心 White Noise 哈希给 位置 / 朝向 / 大小
        → 每格画 3 片椭圆叶（细长比 ≈ 1 : 4.5，绕叶轴张开 ±38°）
        → 三片取 max

    格点必须用 White Noise：相邻格心只隔 1/N，普通噪声在那里是连续的，
    会让整丛草叶同向、退化成规则网格。
    """
    cells = 26
    q = g.vmath("MULTIPLY", uv, (cells, cells, 1.0))
    cell = g.vmath("FLOOR", q)
    cw = g.vmath("MODULO", cell, (float(cells), float(cells), 1.0))
    centre = g.vmath("MULTIPLY",
                     g.vmath("ADD", cw, (0.5, 0.5, 0.0)),
                     (1.0 / cells, 1.0 / cells, 1.0))
    cvec, cw4 = g.torus(centre)
    h = g.white4(cvec, cw4, "Color")
    hs = g.sep(h)

    # 草根位置（格内抖动半格），三片叶都从这里长出去
    off = g.vmath("MULTIPLY", g.vmath("SUBTRACT", h, (0.5, 0.5, 0.0)),
                  (0.52, 0.52, 0.0))
    point = g.vmath("ADD", g.vmath("ADD", cw, (0.5, 0.5, 0.0)), off)
    # 格内坐标要**绕回周期**：草簇如果长在 tile 边上，另一半必须从对面接过来，
    # 否则接缝处会出现"半个草簇"（接缝判据从 1.0 涨到 1.57 就是这么来的）。
    # 注意 Vector Math 的 MODULO 对负数不取正（C 的 fmod 语义），所以先加 3 个周期
    # 保证输入为正，再减掉 —— 不能只加 0.5 个周期。
    hs_ = cells * 0.5
    rel = g.vmath("SUBTRACT", q, point)
    rel = g.vmath("SUBTRACT",
                  g.vmath("MODULO",
                          g.vmath("ADD", rel, (cells * 3 + hs_, cells * 3 + hs_, 0.0)),
                          (float(cells), float(cells), 1.0)),
                  (hs_, hs_, 0.0))
    ps = g.sep(rel)
    px, py = ps.outputs[0], ps.outputs[1]

    # 整丛朝向 ±35°（不采全周：草势大体朝上，读起来"有秩序"）
    ang = g.maprange(_out(hs, "Z"), 0.0, 1.0, -0.61, 0.61, interp="LINEAR")
    ca, sa = g.math("COSINE", ang), g.math("SINE", ang)
    rx = g.math("SUBTRACT", g.math("MULTIPLY", px, ca), g.math("MULTIPLY", py, sa))
    ry = g.math("ADD", g.math("MULTIPLY", px, sa), g.math("MULTIPLY", py, ca))

    # 叶长 0.30–0.46 格（8 m tile 下 ≈ 9–14 px ≈ 14–22 cm），宽 = 长的 21%
    ln = g.maprange(_out(hs, "Y"), 0.0, 1.0, 0.55, 0.88, interp="LINEAR")
    # 叶间张角也随机：三片叶子如果永远同样张开，四丛一看就是同一枚印章
    spread = g.maprange(_out(hs, "Z"), 0.0, 1.0, 0.62, 1.30, interp="LINEAR")

    blade = None
    for a, ch in zip((-1.0, -0.34, 0.34, 1.0), ("Y", "Z", "X", "Y")):
        # 每片叶自己的长度（用不同哈希通道）——"一丛三片不等长"才像活的
        lk = g.math("MULTIPLY", ln, g.maprange(_out(hs, ch), 0.0, 1.0, 0.72, 1.12,
                                               interp="LINEAR"))
        half = g.math("MULTIPLY", lk, 0.5)
        half_w = g.math("MULTIPLY", lk, 0.075)
        ak = g.math("MULTIPLY", spread, 0.66 * a)
        ck, sk = g.math("COSINE", ak), g.math("SINE", ak)
        bx = g.math("SUBTRACT", g.math("MULTIPLY", rx, ck), g.math("MULTIPLY", ry, sk))
        by = g.math("ADD", g.math("MULTIPLY", rx, sk), g.math("MULTIPLY", ry, ck))
        # 叶形：根部最宽、梢部收成尖（只靠椭圆的话两端都是圆的，读成"爪子"不是"叶"）
        taper = g.math("SUBTRACT", 1.0,
                       g.math("MULTIPLY", g.math("DIVIDE", by, lk), 0.80))
        ny = g.math("SUBTRACT", by, half)          # 叶心在轴上离根 half
        e = g.vmath("LENGTH", g.combine(
            g.math("DIVIDE", bx, g.math("MULTIPLY", half_w, taper)),
            g.math("DIVIDE", ny, half), 0.0))
        m = g.maprange(e, 1.0, 0.80, 0.0, 1.0)     # 梢部略收，边缘 ~1 px 软
        blade = m if blade is None else g.math("MAXIMUM", blade, m)

    # 密度：约 1/3 的格长草（每 tile ≈ 230 丛，8 m 下 ≈ 3.6 丛/m²）
    gate = g.maprange(g.math("ADD", g.math("MULTIPLY", _out(hs, "X"), 0.7),
                             g.math("MULTIPLY", _out(hs, "Z"), 0.3)), 0.70, 0.76)
    # 每丛的浓度也随机（0.55–1.0）：一样深的一批草簇排在那里就是"印刷网点"
    amt = g.maprange(_out(hs, "Y"), 0.0, 1.0, 0.55, 1.0, interp="LINEAR")
    return g.math("MULTIPLY", g.math("MULTIPLY", blade, gate), amt)


# ── 草地：组装 ──────────────────────────────────────────────────────────────
def build_grass():
    """暖黄绿底 + 低频三阶色块 + 三叶草簇。

    层次（从下到上）：
      ① 三阶色块：Scale=4.6 的噪声 → ColorRamp 切成 暗/中/亮 三段（软边 ≈ 12 px）
      ② 中频微调：Scale=7.5 的噪声，±2.6% 明度，打散"平涂色纸"的塑料感
      ③ 草簇：三片细叶一丛，≈ 3.6 丛/m²
    """
    g = G("terrain_grass")
    uv = uv_node(g)
    n_big, n_mid = grass_fields(g, uv)
    b_big = g.norm(n_big, "草_big")
    b_mid = g.norm(n_mid, "草_mid")

    col = g.ramp(b_big, [
        (0.00, GRASS["dark"]), (0.26, GRASS["dark"]),     # 暗块（平顶）
        (0.34, GRASS["base"]), (0.72, GRASS["base"]),     # 中调
        (0.80, GRASS["light"]), (1.00, GRASS["light"]),   # 亮块
    ])

    f2 = g.maprange(b_mid, 0.15, 0.85, -0.026, 0.026, interp="LINEAR")
    col = g.mix(g.math("ADD", f2, 0.5), GRASS["dark"], col)

    tuft = tuft_layer(g, uv, *g.torus(uv))
    col = g.mix(g.math("MULTIPLY", tuft, TUFT_AMT), col, GRASS["clump"])
    g.emission(col)
    return g.mat


# ── 泥土：场 ────────────────────────────────────────────────────────────────
def dirt_fields(g, uv):
    vec, w = g.torus(uv)
    n_big = g.noise4(vec, w, scale=5.2, detail=1.0, rough=0.40, distortion=0.14)

    # 干裂：先把坐标用一层低频噪声"揉"一下，胞元才不是规整多边形
    warp = g.noise4(vec, w, scale=2.6, detail=1.0, rough=0.5,
                    offset=(4.1, 0.7, 2.9), out="Color")
    wvec = g.vmath("ADD", vec, g.vmath("MULTIPLY", warp, (0.018, 0.018, 0.018)))
    d = _out(g.voronoi4(wvec, w, scale=10.5, randomness=1.0), "Distance")

    n_fine = g.noise4(vec, w, scale=9.0, detail=0.6, rough=0.45,
                      offset=(7.3, 2.2, 1.1))
    return n_big, d, n_fine


def build_dirt():
    """踩实的土：两阶低频块 + 极弱 Voronoi 干裂纹 + 板心微提亮。

    Voronoi 用 DISTANCE_TO_EDGE，一次出两件事：
      · 裂纹：d < 0.05 的窄带压暗 —— 线宽 ≈ 2 px（2.5 cm），像干裂土
      · 板心：d 从 0.06 到 0.46 缓慢提亮 1.5%，让"每一块板"微微鼓起
    两个效果都压到"近看才有"的程度：远看只是一块有结构的地，不是花纹。
    """
    g = G("terrain_dirt")
    uv = uv_node(g)
    n_big, d, n_fine = dirt_fields(g, uv)
    b_big = g.norm(n_big, "土_big")
    b_fine = g.norm(n_fine, "土_fine")

    col = g.ramp(b_big, [
        (0.00, DIRT["dark"]), (0.30, DIRT["dark"]),
        (0.38, DIRT["base"]), (0.78, DIRT["base"]),
        (0.86, DIRT["light"]), (1.00, DIRT["light"]),
    ])

    # 裂纹只占 ~3% 面积：半宽 0.012（≈ 3 px），最深处压 34%
    crack = g.maprange(d, 0.002, 0.024, 1.0, 0.0)
    plate = g.maprange(d, 0.100, 0.450, 0.0, 1.0)
    col = g.mix(g.math("MULTIPLY", plate, 0.16), col, DIRT["light"])
    col = g.mix(g.math("MULTIPLY", crack, 0.55), col, DIRT["crack"])

    f3 = g.maprange(b_fine, 0.15, 0.85, -0.013, 0.013, interp="LINEAR")
    col = g.mix(g.math("ADD", f3, 0.5), DIRT["dark"], col)

    g.emission(col)
    return g.mat


# ── 裂纹泥地（3D 地块的贴图） ───────────────────────────────────────────────
def dirt_fine_fields(g, uv):
    """在"泥土"的骨架上把裂纹换细一档：Voronoi scale 15（胞元 ≈ 0.53 m）。"""
    vec, w = g.torus(uv)
    n_big = g.noise4(vec, w, scale=5.2, detail=1.0, rough=0.40, distortion=0.14)
    warp = g.noise4(vec, w, scale=2.6, detail=1.0, rough=0.5,
                    offset=(4.1, 0.7, 2.9), out="Color")
    wvec = g.vmath("ADD", vec, g.vmath("MULTIPLY", warp, (0.016, 0.016, 0.016)))
    d = _out(g.voronoi4(wvec, w, scale=15.0, randomness=1.0), "Distance")
    n_fine = g.noise4(vec, w, scale=9.0, detail=0.6, rough=0.45,
                      offset=(7.3, 2.2, 1.1))
    return n_big, d, n_fine


def build_dirt_fine():
    """裂纹泥地：泥土的色阶 + 更细的干裂纹，给 3D 地块当板面贴图。"""
    g = G("terrain_mud_cracked")
    uv = uv_node(g)
    n_big, d, n_fine = dirt_fine_fields(g, uv)
    b_big = g.norm(n_big, "土_big")
    b_fine = g.norm(n_fine, "土_fine")

    col = g.ramp(b_big, [
        (0.00, DIRT_FINE["dark"]), (0.30, DIRT_FINE["dark"]),
        (0.38, DIRT_FINE["base"]), (0.78, DIRT_FINE["base"]),
        (0.86, DIRT_FINE["light"]), (1.00, DIRT_FINE["light"]),
    ])

    # 细裂纹：线宽 ≈ 2 px，压暗 40%；板心提亮 12%
    crack = g.maprange(d, 0.0010, 0.022, 1.0, 0.0)
    plate = g.maprange(d, 0.060, 0.400, 0.0, 1.0)
    col = g.mix(g.math("MULTIPLY", plate, 0.12), col, DIRT_FINE["light"])
    col = g.mix(g.math("MULTIPLY", crack, 0.52), col, DIRT_FINE["crack"])

    f3 = g.maprange(b_fine, 0.15, 0.85, -0.012, 0.012, interp="LINEAR")
    col = g.mix(g.math("ADD", f3, 0.5), DIRT_FINE["dark"], col)

    g.emission(col)
    return g.mat


# ── 场景 / 渲染 ─────────────────────────────────────────────────────────────
def build_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene

    # 平面铺 6×6，UV 从 -1 到 2：相机只看中间 2×2（u,v ∈ 0..1），
    # 边缘的像素滤波采样会落到"外面一圈"上 —— UV 是周期延拓的，所以既不会
    # 采到黑底（v1 的边框暗边），又保持 u=0/1 精确对齐 tile 边界。
    me = bpy.data.meshes.new("TX_平面")
    me.from_pydata([(-3, -3, 0), (3, -3, 0), (3, 3, 0), (-3, 3, 0)], [],
                   [(0, 1, 2, 3)])
    me.validate()
    lay = me.uv_layers.new(name="UVMap")
    for i, co in enumerate(((-1, -1), (2, -1), (2, 2), (-1, 2))):
        lay.data[i].uv = co
    ob = bpy.data.objects.new("TX_平面", me)
    sc.collection.objects.link(ob)

    cam_data = bpy.data.cameras.new("TX_正交顶视")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = 2.0            # 平面 2×2 → 画面正好 1 个 tile
    cam = bpy.data.objects.new("TX_正交顶视", cam_data)
    cam.location = (0.0, 0.0, 4.0)
    cam.rotation_euler = (0.0, 0.0, 0.0)  # 绝对垂直的 Top View
    sc.collection.objects.link(cam)
    sc.camera = cam

    # 世界纯黑、无灯：材质是 Emission，画面里只有贴图本身
    world = bpy.data.worlds.new("TX_黑")
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Color"].default_value = (0, 0, 0, 1)
        bg.inputs["Strength"].default_value = 0.0
    sc.world = world

    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = 16                 # 只用来做像素内抗锯齿（无光照噪声）
    sc.cycles.use_adaptive_sampling = False
    sc.cycles.use_denoising = False
    sc.cycles.max_bounces = 2
    sc.cycles.pixel_filter_type = "BLACKMAN_HARRIS"
    sc.cycles.filter_width = 1.5
    sc.render.resolution_x = sc.render.resolution_y = SIZE * SS
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = False
    sc.render.dither_intensity = 0.0       # 8bit 输出的抖动 = 高频噪点，关掉
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGB"
    sc.render.image_settings.color_depth = "8"
    sc.render.image_settings.compression = 30
    sc.view_settings.view_transform = "Standard"   # 不做 filmic / AgX 压缩
    sc.view_settings.look = "None"
    sc.view_settings.exposure = 0.0
    sc.view_settings.gamma = 1.0
    return sc, ob


def render_tile(sc, ob, mat, name, res=None, samples=None):
    ob.data.materials.clear()
    ob.data.materials.append(mat)
    os.makedirs(RAW_DIR, exist_ok=True)
    raw = os.path.join(RAW_DIR, "%s_%d.png" % (name, res or SIZE * SS))
    if res:
        sc.render.resolution_x = sc.render.resolution_y = res
    if samples:
        sc.cycles.samples = samples
    sc.render.filepath = raw
    bpy.ops.render.render(write_still=True)
    return raw


def load_px(path):
    img = bpy.data.images.load(path, check_existing=False)
    w, h = img.size
    buf = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(buf)
    bpy.data.images.remove(img)
    return buf.reshape(h, w, 4)[:, :, :3].astype(np.float64)


def downsample(raw, out_path):
    """1024 → 512：线性空间 2×2 盒式平均（超采样抗锯齿）。"""
    px = load_px(raw)
    h, w, _ = px.shape
    lin = np.where(px <= 0.04045, px / 12.92, ((px + 0.055) / 1.055) ** 2.4)
    k = h // SIZE
    lin = lin.reshape(SIZE, k, SIZE, k, 3).mean(axis=(1, 3))
    out = np.where(lin <= 0.0031308, lin * 12.92,
                   1.055 * np.power(np.clip(lin, 0, None), 1 / 2.4) - 0.055)
    out = np.clip(out, 0.0, 1.0)

    # 1 LSB 抖动：Albedo 的色差本来就小（泥土总共 7/255 的跨度），
    # 8bit 量化会把柔和的渐变切成 40–70 px 宽的色带。±0.5 LSB 的随机抖动
    # 打散色带，肉眼看不到（0.4% 的幅度），也不会在引擎里被当成噪点。
    rng = np.random.default_rng(20261029)
    out = np.clip(out + rng.uniform(-0.5, 0.5, out.shape) / 255.0, 0.0, 1.0)

    res = bpy.data.images.new(os.path.basename(out_path), SIZE, SIZE, alpha=False)
    res.colorspace_settings.name = "sRGB"
    rgba = np.ones((SIZE, SIZE, 4), dtype=np.float32)
    rgba[:, :, :3] = out
    res.pixels.foreach_set(rgba.ravel())
    res.update()
    res.filepath_raw = out_path
    res.file_format = "PNG"
    res.save()
    clean_png(out_path)
    return out


def clean_png(path, keep=("IHDR", "sRGB", "gAMA", "cHRM", "IDAT", "IEND")):
    """去掉 eXIf / oFFs 这类渲染器元数据：贴图只需要像素。

    不是"洁癖"：部分引擎的 PNG 导入器会把 oFFs（图像偏移）当真，图会错位。
    """
    raw = open(path, "rb").read()
    head = raw[:8]
    out = bytearray(head)
    i = 8
    while i < len(raw):
        ln = int.from_bytes(raw[i:i + 4], "big")
        typ = raw[i + 4:i + 8].decode("latin-1")
        if typ in keep:
            out += raw[i:i + 12 + ln]
        i += 12 + ln
    open(path, "wb").write(bytes(out))


def analyze(px):
    """体检：无缝度 / 明度 / 色彩数 / 局部对比。

    接缝判据用 **跨缝差 ÷ 缝内侧紧邻差**：平铺纹理的边缘像素本来就不是"相等"，
    而是"接着往下走"。比值 ≈1 才是无缝；>2.5 才会在拼接处看出线。
    """
    lum = px @ np.array([0.2126, 0.7152, 0.0722])
    dx = np.abs(np.diff(px, axis=1)).mean()
    dy = np.abs(np.diff(px, axis=0)).mean()
    seam_x = np.abs(px[:, 0] - px[:, -1]).mean()
    seam_y = np.abs(px[0, :] - px[-1, :]).mean()
    inner_x = np.abs(px[:, -1] - px[:, -2]).mean()
    inner_y = np.abs(px[-1, :] - px[-2, :]).mean()
    q = np.round(px * 255).astype(np.uint8)
    uniq = len(np.unique(q.reshape(-1, 3), axis=0))
    from numpy.lib.stride_tricks import sliding_window_view
    win = sliding_window_view(lum, (3, 3))
    spread = np.percentile(win.max(axis=(2, 3)) - win.min(axis=(2, 3)), 99.5)
    return {
        "lum_min": round(float(lum.min()), 4),
        "lum_mean": round(float(lum.mean()), 4),
        "lum_max": round(float(lum.max()), 4),
        "unique_colors": int(uniq),
        "adjacent_diff_x": round(float(dx), 5),
        "adjacent_diff_y": round(float(dy), 5),
        "seam_diff_x": round(float(seam_x), 5),
        "seam_diff_y": round(float(seam_y), 5),
        "seam_vs_inner_x": round(float(seam_x / max(inner_x, 1e-9)), 2),
        "seam_vs_inner_y": round(float(seam_y / max(inner_y, 1e-9)), 2),
        "local_spread_p995": round(float(spread), 4),
    }


# ── 标定：把噪声场渲成灰度，量实际分布 ───────────────────────────────────────
def calib(sc, ob):
    """噪声的实际取值范围决定"切几刀"，凭感觉写 0.5 必然切偏。"""
    sc.render.resolution_x = sc.render.resolution_y = 256
    sc.cycles.samples = 4
    out = {}
    probes = [
        ("草_big", lambda g, uv: grass_fields(g, uv)[0]),
        ("草_mid", lambda g, uv: grass_fields(g, uv)[1]),
        ("草_tuft", lambda g, uv: grass_fields(g, uv)[2]),
        ("土_big", lambda g, uv: dirt_fields(g, uv)[0]),
        ("土_crack", lambda g, uv: g.maprange(dirt_fields(g, uv)[1],
                                             0.002, 0.014, 1.0, 0.0)),
        ("土_d", lambda g, uv: dirt_fields(g, uv)[1]),
        ("土_fine", lambda g, uv: dirt_fields(g, uv)[2]),
    ]
    for name, fn in probes:
        g = G("CAL_" + name)
        uv = uv_node(g)
        g.emission(g.gray(fn(g, uv)))
        raw = render_tile(sc, ob, g.mat, "cal_" + name, res=256, samples=4)
        px = load_px(raw)[:, :, 0]
        # 注意：PNG 里的像素已经过 sRGB 编码，而节点里的场是**线性**的。
        # 拿 sRGB 的分位数去写阈值 = 整体偏高 0.25，会把大半个画面夹死（踩过）。
        lin = np.where(px <= 0.04045, px / 12.92, ((px + 0.055) / 1.055) ** 2.4)
        qs = [1, 2, 5, 10, 20, 25, 30, 40, 50, 60, 70, 75, 80, 90, 95, 98, 99]
        out[name] = {"lin": {str(q): round(float(np.percentile(lin, q)), 3)
                             for q in qs},
                     "mean": round(float(lin.mean()), 3)}
        print("[CAL %s] %s" % (name, json.dumps(out[name], ensure_ascii=False)))
    with open(os.path.join(DOC_DIR, "calib.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(DOC_DIR, exist_ok=True)
    sc, ob = build_scene()
    if CALIB:
        calib(sc, ob)
        print("[TX CALIB DONE]")
        return

    report = {}
    for name, builder in (("草地", build_grass), ("泥土", build_dirt),
                          ("裂纹泥地", build_dirt_fine)):
        mat = builder()
        raw = render_tile(sc, ob, mat, name)
        out = os.path.join(OUT_DIR, "%s.png" % name)
        px = downsample(raw, out)
        st = analyze(px)
        st["file"] = out
        st["tile_m"] = TILE_M
        report[name] = st
        print("[TX %s] %s" % (name, json.dumps(st, ensure_ascii=False)))

    with open(os.path.join(DOC_DIR, "tex_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # 留一份可编辑的节点源文件：改配色 / 改密度直接开这个 .blend 拖色标
    for nm in ("terrain_grass", "terrain_dirt", "terrain_mud_cracked"):
        # 无用户的自定义材质块不会被写进 .blend —— 必须挂到对象上或给 fake user
        bpy.data.materials[nm].use_fake_user = True
    ob.data.materials.clear()
    ob.data.materials.append(bpy.data.materials["terrain_grass"])
    bpy.context.preferences.filepaths.save_version = 0   # 不生成 .blend1
    bpy.ops.wm.save_as_mainfile(
        filepath=os.path.join(SRC_DIR, "地形材质.blend"), relative_remap=False)
    print("[TX DONE]", os.path.join(SRC_DIR, "地形材质.blend"))


if __name__ == "__main__":
    main()
