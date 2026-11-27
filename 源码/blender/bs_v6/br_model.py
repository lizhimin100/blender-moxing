"""
br_model.py —— 兵营（Barracks）v3：平顶垛口 · 成组垛口 · 训练场与主体咬合

v3 针对三条反馈重做：

  ① **垛口成组**：v2 是等距密排（每 1.75 m 一个，全楼一个样），读起来是一圈碎锯齿。
     现在改成"2 个或 4 个连成一垛、垛与垛之间留大缺口"的拼接节奏：
     前墙 2 组 × 3、侧墙 2 组 × 2、后墙 2 组 × 4、角楼 1 组 × 2。
  ② **体量对齐铁匠铺**：v2 是 19.2 × 14.5（铁匠铺 10.03 × 11.8，两倍大）。
     现在主体 10.0 × 7.6，连围栏带场地 10.9 × 14.6 —— 宽向与铁匠铺持平，深向多出的
     就是训练场本身。
  ③ **训练场与建筑咬合**：v2 的场地是建筑前面 2.5 m 处一个独立方框，围栏四面自成一圈。
     现在左右围栏直接从基座侧面长出来（立柱埋进石台），建筑前墙就是场地的第四面；
     中轴铺一条石路从门槛通到围栏开口；靠墙根排一列长矛束 / 盾 / 武器架。
     场地顶面 0.22，道具全部站在场地上（不再陷进夯土）。

坐标：X 右、Y 前（+Y = 正面）、Z 上；原点在占地中心，z = 0 地面。
交付前整体沿 X 镜像一次（与铁匠铺一致），所以建模期的 +X 在成品里是左边的 −X。
"""
import math
from math import tau as TAU

import bpy

import bslib as L
from bslib import (arch_band, beam, box, cone, cyl, extrude, kite_shield,
                   lathe, mesh_obj, revolve, slab_plate, taper_box, tube_band)

# ── 主体：10.0 宽 × 7.6 进深（铁匠铺 10.03 宽，同一量级）───────────────────────
W2 = 5.00                       # 半宽
YF = 3.80                       # 前墙
YB = -3.80                      # 后墙
H1 = 3.80                       # 一层顶（石 / 木构分界）
H2 = 7.40                       # 二层顶 / 屋顶平台
PARA = 1.10                     # 女儿墙高
PARA_T = 0.42                   # 女儿墙厚

# 垛口：成组拼接（组内小缝、组间大缺口）
MERLON_W = 0.72                 # 单垛宽
MERLON_H = 0.58                 # 单垛高
MERLON_GAP_IN = 0.12            # 组内净距（几乎贴在一起，读成"一垛墙"）
MERLON_GAP_OUT = 1.70           # 组间缺口（探身/架弩的位置）

# 前右角楼（建模期 +X，成品镜像后在画面右侧）
T_X0, T_X1 = 2.55, 5.00
T_Y1 = 5.80                     # 从前墙凸出 2.00
T_TOP = 10.30                   # 含角楼自己的垛口

# 拱门（不是重点：一级门槛、不做台阶群）
GATE_W, GATE_SPRING = 1.95, 2.35    # 拱顶 = 2.35 + 0.975 = 3.325

# 训练场：左右围栏直接长在基座侧面上
YARD_X = W2 + 0.30              # = 基座半宽 5.30，围栏板中心埋进基座 0.14
YARD_Y0 = YF + 0.34             # 起点压进基座前脸 0.04
YARD_Y1 = 9.75                  # 前沿（进深 5.61，占地深向不再拖长）
YARD_Z = 0.40                   # 场地顶面：比基座（0.48）只低一级，读成同一块台地
FENCE_H = 1.15

# ── 地面分层（v4）：每个面一个高度，任何两层都不共面 ──────────────────────────
G_Z = YARD_Z                    # 0.400 夯土面（场地主面）
G_WALK = 0.440                  # 墙脚铺石顶面（+40 mm）
G_SAND = 0.450                  # 训练圈沙面（+50 mm）
G_CURB = 0.460                  # 场地牙子顶面（+60 mm）
G_STEP = 0.470                  # 门前石踏顶面（+70 mm）
G_LAND = 0.442                  # 围栏开口的落地石顶面（与墙脚铺石同级）
G_RING = 0.475                  # 训练圈石边顶面（+75 mm）

# 阵营色标准模块
SHIELD_W, SHIELD_H = 1.24, 1.48
BANNER_W, BANNER_H = 0.62, 1.30


def arch_profile(w, h, segs=8):
    hw = w * 0.5
    pts = [(-hw, 0.0), (hw, 0.0), (hw, h)]
    for s in range(segs - 1, 0, -1):
        a = math.pi * s / segs
        pts.append((hw * math.cos(a), h + hw * math.sin(a)))
    pts.append((-hw, h))
    return pts


def vcyl(name, center, r, h, segments, mat, phase=0.0):
    """竖直圆柱：四边侧面 + 上下 n-gon 端面。

    bslib.cyl 只支持 X / Y 两个躺倒方向，axis="Z" 会返回 None（然后 finalize 崩）。
    竖直件统一走这个本地实现，面数比 revolve 的三角扇低一半。
    """
    cx, cy, z0 = center
    verts, faces = [], []
    for s in range(segments):
        a = phase + TAU * s / segments
        verts += [(cx + r * math.cos(a), cy + r * math.sin(a), z0),
                  (cx + r * math.cos(a), cy + r * math.sin(a), z0 + h)]
    for s in range(segments):
        a0, a1 = 2 * s, 2 * ((s + 1) % segments)
        faces.append((a0, a1, a1 + 1, a0 + 1))
    faces.append(tuple(2 * s for s in range(segments - 1, -1, -1)))
    faces.append(tuple(2 * s + 1 for s in range(segments)))
    return mesh_obj(name, verts, faces, mat)


def out_sign(x):
    """贴墙件的朝外方向：+X 面为 +1，−X 面为 −1。"""
    return 1 if x > 0 else -1


def mirror_x(objs):
    for ob in objs:
        me = ob.data
        for v in me.vertices:
            v.co.x = -v.co.x
        for p in me.polygons:
            p.flip()
        me.update()


class Model:
    def __init__(self, smooth, unwrap=True):
        self.smooth = smooth
        self.unwrap = unwrap
        self.items = []
        self.M = L.all_materials()

    def add(self, ob, bevel=0.022, sub=0, seg=1):
        self.items.append((ob, bevel, sub, seg))
        return ob

    # ── 1. 基座、门槛、场地台 ───────────────────────────────────────────────
    def base(self):
        """石台 + 门槛 + 夯土场地台。

        v4 重做地面：上一版把场地做成一块灰色石板，再用 7 条 1.4–3 cm 厚的
        "分格 / 标线 / 铺石"薄片压在上面（顶面互相只差 5–30 mm）。俯视时
        这些薄片在远处只剩亚像素，拖动视角就是一片闪；整块灰石板又把场地
        照成建筑一样亮，读起来是"泛白的水泥板"。

        现在的做法：**一条薄片都不留**。场地是夯土实体台（顶面 0.40），
        铺石是 6 cm 厚的独立石块坐在土上（顶面 0.44，缝里露出 4 cm 的土），
        牙子、踏步、坡道、训练圈全部是有厚度的实体件，任何两个面都不共面。
        """
        M = self.M
        # 石台：主体外扩 0.30。训练场围栏就贴在它的侧面上
        self.add(box("plinth_a", (0, 0.0, 0.24),
                     (W2 * 2 + 0.60, YF - YB + 0.60, 0.48), M["stone_dark"]))
        self.add(box("plinth_b", (0, 0.0, 0.09),
                     (W2 * 2 + 0.96, YF - YB + 0.96, 0.18), M["stone_mid"]))
        # 门槛（一级）
        self.add(box("threshold", (0, YF + 0.26, 0.25), (GATE_W + 0.70, 0.52, 0.50),
                     M["stone_light"]), 0.012)
        # 场地台：夯土。整块场地就是这一个实体，上面不再贴任何薄片
        self.add(box("yard", (0.00, (YARD_Y0 + YARD_Y1) * 0.5, G_Z * 0.5),
                     (YARD_X * 2 + 0.10, YARD_Y1 - YARD_Y0, G_Z), M["earth"]), 0.018)
        # 三面石牙子：16 cm 宽、顶面 0.46，把夯土台收成"建筑的一部分"
        for sgn in (-1, 1):
            # 侧牙子在后端收 0.16，让前牙子独占转角（两块同高的顶面会闪）
            cy = (YARD_Y0 + YARD_Y1 - 0.16) * 0.5
            self.add(box("yard_curb", (sgn * YARD_X, cy, G_CURB - 0.06),
                         (0.16, YARD_Y1 - 0.16 - YARD_Y0, 0.12), M["paving"]), 0.006)
            # 前牙子在入口处断开，接坡道
            x0, x1 = sgn * 1.98, sgn * (YARD_X + 0.08)
            self.add(box("yard_curb_f", ((x0 + x1) * 0.5, YARD_Y1 + 0.01, G_CURB - 0.06),
                         (abs(x1 - x0), 0.16, 0.12), M["paving"]), 0.006)
        # 入口：落地石 + 两级石阶。v3 用楔形坡道，正视时是一块斜插出来的灰板；
        # 两级 14 cm 的踏步才是"营门"的读法，总出挑也只有 0.52 m。
        self.add(box("yard_land", (0, YARD_Y1 + 0.04, G_LAND * 0.5), (3.16, 0.30, G_LAND),
                     M["stone_mid"]), 0.006)
        for i, (dy, zt) in enumerate(((0.28, 0.290), (0.52, 0.145))):
            self.add(box("yard_step%d" % i, (0, YARD_Y1 + dy, zt * 0.5),
                         (3.16, 0.24, zt), M["stone_mid"]), 0.006)
        # 门前石踏（0.47）：夯土 0.40 → 墙脚石铺 0.44 → 石踏 0.47 → 门槛 0.50
        self.add(box("gate_step", (0, 4.58, G_STEP * 0.5), (2.86, 0.56, G_STEP),
                     M["paving"]), 0.010)

    # ── 1.5 墙脚铺石（四块大石板，缝里露出夯土）─────────────────────────────
    def paving(self):
        """墙脚的石铺带。

        v3 是"12 块 0.78 m 小石板 + 5 条 1.4–3 cm 薄贴片"，在 RTS 尺度上读成
        "散落的瓷砖 + 一些细线"；现在改成 **4 块 1.78 × 0.68 的大石板**，
        缝 3.5 cm 直接露出下面的夯土 —— 缝是真的凹进去，不是画上去的线。
        """
        M = self.M
        x0, x1 = -5.10, 2.12
        n, gap = 4, 0.035
        w = ((x1 - x0) - (n - 1) * gap) / n
        for i in range(n):
            cx = x0 + w * 0.5 + i * (w + gap)
            self.add(box("pave", (cx, 4.50, G_WALK - 0.032), (w, 0.68, 0.064),
                         M["paving"]), 0.0)

    # ── 1.6 训练圈（俯视时的场地中心）──────────────────────────────────────
    def drill(self):
        """12 边沙面 + 一圈石砌边。

        场地不能只剩"一片土"：俯视时需要一个视觉中心，否则院子和空地没区别。
        沙圈是低模尺度的"操练位"，石边把它从土里描出来。

        位置在**轴线左侧**（x −3.35）：从营门到围栏开口是进场走廊，中线上一律留空
        （v3.4 的规矩），沙圈压在轴线上会挡门。
        """
        M = self.M
        cx, cy = -2.65, 7.60
        r = 1.28
        ph = math.pi / 12
        self.add(vcyl("drill_sand", (cx, cy, 0.34), r, 0.11, 12, M["sand"], phase=ph), 0.008)
        # 深色石边：r 1.32–1.58、比沙面高 10 mm。用 stone_dark 而不是灰白铺石 ——
        # 沙面和铺石在 AgX 下是同一个明度，浅色石边会把整块沙面糊成一个灰斑；
        # 深色一圈反而把"沙坑"从夯土里切出来，RTS 尺度上才读得清。
        self.add(tube_band("drill_ring", (cx, cy), r - 0.04, r + 0.22, 0.36, 0.460, 12,
                           M["stone_dark"], phase=ph), 0.006)

    # ── 1.7 土斑 / 草簇 / 碎石 / 散板（只做"人踩出来"的点缀）────────────────
    def scatter(self):
        M = self.M
        # 三块踩实的深色土斑：一整片同色夯土在俯视里是"没做完"，土斑给了地面层次，
        # 又没有任何细线（上一版的分格线就是这么闪起来的）。
        for (cx, cy, rx, ry, sd) in ((-3.85, 5.55, 1.25, 0.72, 1.0),
                                     (1.15, 8.45, 1.45, 0.85, 2.3),
                                     (-1.10, 9.05, 0.85, 0.52, 3.1)):
            self.patch(cx, cy, rx, ry, sd)
        for (x, y) in ((-5.06, 5.36), (5.06, 6.66), (-4.94, 8.84), (4.98, 9.12),
                       (-2.34, 5.10), (2.42, 5.12), (-1.26, 9.40), (1.40, 9.44),
                       (-1.22, 6.52), (-4.08, 7.98)):
            self.tuft(x, y)
        # 碎石：靠围栏内角 + 场地里零星几块，不做满地碎石（RTS 尺度上那是噪点）
        for (x, y, s, rz) in ((-4.86, 9.30, 0.30, 0.35), (5.02, 8.30, 0.24, -0.7),
                              (-2.52, 9.44, 0.20, 1.1), (2.66, 9.34, 0.22, 0.2),
                              (0.58, 6.18, 0.16, 0.9), (-1.32, 6.86, 0.13, -0.4),
                              (2.26, 9.02, 0.15, 0.6), (-4.12, 8.86, 0.17, 1.4)):
            # 倾斜 15–25°：立着的方块石头会读成"随手丢的箱角"
            self.add(box("rubble", (x, y, G_Z + s * 0.26), (s, s * 0.76, s * 0.56),
                         M["stone_mid"], rot=(0.26 * s, 0.20 * s, rz)), 0.006)
        # 一块散板：靠着木箱，读完"这里有人干活"（两块交叉会读成散架）
        self.add(box("plank_loose", (-2.26, 5.14, G_Z + 0.026), (0.92, 0.15, 0.050),
                     M["wood_dark"], rot=(0.02, 0.03, 0.30)), 0.006)

    def patch(self, cx, cy, rx, ry, seed):
        """踩实的深色土斑：7 边、3 cm 厚的实体，压在夯土上（顶面高 7 mm，不共面）。"""
        M = self.M
        prof = []
        for i in range(7):
            a = TAU * i / 7.0 + 0.40 * seed
            k = 0.74 + 0.26 * math.sin(seed * 3.7 + i * 2.1)
            prof.append((cx + math.cos(a) * rx * k, cy + math.sin(a) * ry * k))
        self.add(extrude("patch", prof, "Z", 0.030, (0.0, 0.0),
                         M["earth_dark"], offset=G_Z - 0.007), 0.0)

    def tuft(self, x, y, h=0.21):
        """草簇：三片 1.8 cm 厚的草叶，各向外倾 12°、高低差 2 cm（同高会在叶心闪）。"""
        M = self.M
        for k in range(3):
            a = math.radians(18 + k * 60)
            hh = h * (0.84 + 0.11 * k)
            self.add(box("tuft", (x + 0.014 * math.cos(a + 1.1), y + 0.014 * math.sin(a + 1.1),
                                  G_Z + hh * 0.48), (0.115, 0.018, hh), M["moss"],
                         rot=(0.20 * math.cos(a), 0.20 * math.sin(a), a)), 0.0)

    # ── 2. 主体（矩形 + 平顶）──────────────────────────────────────────────
    def mass(self):
        M = self.M
        gw = GATE_W * 0.5
        z_t = GATE_SPRING + gw
        # 前墙三块（真挖拱洞）
        left = [(-W2, 0.0), (-gw, 0.0), (-gw, H2), (-W2, H2)]
        right = [(gw, 0.0), (W2, 0.0), (W2, H2), (gw, H2)]
        for name, prof in (("mass_front_L", left), ("mass_front_R", right)):
            self.add(extrude(name, prof, "Y", 0.80, (0, 0), M["stone_light"],
                             offset=YF - 0.40), 0.030)
        # 拱上那块：顶点顺序必须与 pent 同向（逆时针），否则法线朝内渲染成黑三角
        top = [(-gw, z_t), (-gw, H2), (gw, H2), (gw, z_t)]
        for s in range(1, 10):
            a = math.pi * s / 10
            top.append((gw * math.cos(a), GATE_SPRING + gw * math.sin(a)))
        self.add(extrude("mass_front_T", top, "Y", 0.80, (0, 0), M["stone_light"],
                         offset=YF - 0.40), 0.030)
        # 后段实心
        pent = [(-W2, 0.0), (W2, 0.0), (W2, H2), (-W2, H2)]
        self.add(extrude("mass_back", pent, "Y", YF - 0.80 - YB, (0, 0),
                         M["stone_light"], offset=(YF - 0.80 + YB) * 0.5), 0.035)
        # 石基座（0–1.20）+ 压边
        self.add(box("dado", (0, (YF + YB) * 0.5, 0.60), (W2 * 2 + 0.10, YF - YB + 0.10, 1.20),
                     M["stone_mid"]), 0.028)
        self.add(box("plinth_band", (0, (YF + YB) * 0.5, 1.26), (W2 * 2 + 0.18, YF - YB + 0.18, 0.14),
                     M["stone_dark"]), 0.014)
        for sgn in (-1, 1):
            x0, x1 = sgn * gw, sgn * (W2 + 0.05)
            self.add(box("dado_front", ((x0 + x1) * 0.5, YF + 0.05, 0.65),
                         (abs(x1 - x0), 0.12, 1.26), M["stone_mid"]), 0.016)
        # 二层腰线（石 / 木构分界）
        self.add(box("string", (0, (YF + YB) * 0.5, H1), (W2 * 2 + 0.20, YF - YB + 0.20, 0.18),
                     M["stone_light"]), 0.016)
        for sgn in (-1, 1):
            x0 = sgn * gw
            x1 = sgn * (T_X0 - 0.10) if sgn > 0 else sgn * (W2 + 0.10)
            self.add(box("string_f", ((x0 + x1) * 0.5, YF + 0.04, H1),
                         (abs(x1 - x0), 0.16, 0.18), M["stone_light"]), 0.012)
        # 隅石（四角，三层）
        for sx in (-1, 1):
            for sy, yface in ((1, YF), (-1, YB)):
                for i in range(3):
                    zz = 0.92 + i * 0.78
                    self.add(box("quoin", (sx * (W2 - 0.245), yface - sy * 0.245, zz),
                                 (0.52 + (0.06 if i % 2 else 0.0), 0.52, 0.42), M["stone_mid"]))
        # 侧墙扶壁（三条，落在窗与窗之间）
        for sx in (-1, 1):
            for yy in (-2.78, -0.62, 1.54):
                self.add(box("buttress", (sx * (W2 + 0.15), yy, 1.90),
                             (0.30, 0.56, 3.50), M["stone_mid"]), 0.024)

    # ── 3. 女儿墙 + 成组垛口 ────────────────────────────────────────────────
    def parapet(self):
        M = self.M
        z0, z1 = H2, H2 + PARA
        self.add(box("para_b", (0, YB + PARA_T * 0.5, (z0 + z1) * 0.5),
                     (W2 * 2, PARA_T, PARA), M["stone_light"]), 0.018)
        for sx in (-1, 1):
            # 侧女儿墙在两端各收一个 PARA_T：四角由前/后两段独占。
            # 四段都通长的话，转角处是一块 0.42 × 0.42 的同高顶面 —— 俯视一直在闪。
            self.add(box("para_s", (sx * (W2 - PARA_T * 0.5), (YF + YB) * 0.5, (z0 + z1) * 0.5),
                         (PARA_T, YF - YB - PARA_T * 2, PARA), M["stone_light"]), 0.018)
        # 前墙女儿墙：从左角做到角楼左边缘
        fx0, fx1 = -W2, T_X0
        self.add(box("para_f", ((fx0 + fx1) * 0.5, YF - PARA_T * 0.5, (z0 + z1) * 0.5),
                     (fx1 - fx0, PARA_T, PARA), M["stone_light"]), 0.018)
        for (cx, cy, sx_, sy_) in ((0, YB + PARA_T * 0.5, W2 * 2 + 0.12, PARA_T + 0.14),
                                   (-W2 + PARA_T * 0.5, (YF + YB) * 0.5, PARA_T + 0.14, YF - YB),
                                   (W2 - PARA_T * 0.5, (YF + YB) * 0.5, PARA_T + 0.14, YF - YB)):
            self.add(box("para_cap", (cx, cy, z1 + 0.06), (sx_, sy_, 0.13), M["stone_dark"]), 0.012)
        # 垛口：后墙 4 个一组 ×2，两侧 3 个一组 ×2，前墙 3 个一组 ×2
        self.merlon_row("ml_b", (-W2 + 0.45, YB + PARA_T * 0.5), (1, 0), W2 * 2 - 0.90, z1, group=4)
        # 只有 2 个或 4 个两种组型 —— 全楼没有"3 个一组"，拼接的节奏才统一
        self.merlon_row("ml_l", (-W2 + PARA_T * 0.5, YB + 0.45), (0, 1), YF - YB - 0.90, z1, group=2)
        self.merlon_row("ml_r", (W2 - PARA_T * 0.5, YB + 0.45), (0, 1), YF - YB - 0.90, z1, group=2)
        self.merlon_row("ml_f", (-W2 + 0.40, YF - PARA_T * 0.5), (1, 0), W2 + T_X0 - 0.80, z1, group=2)

    def merlon_row(self, name, p0, d, length, z0, group=3, mw=None, gh=None):
        """成组垛口：group 个连成一垛（组内小缝），垛与垛之间留大缺口。"""
        M = self.M
        mw = MERLON_W if mw is None else mw
        gh = MERLON_H if gh is None else gh
        unit = group * mw + (group - 1) * MERLON_GAP_IN
        # 加 1e-6：length/(unit+gap) 正好整除时，浮点误差会让 int() 少算一组
        n = max(1, int((length + MERLON_GAP_OUT) / (unit + MERLON_GAP_OUT) + 1e-6))
        total = n * unit + (n - 1) * MERLON_GAP_OUT
        start = (length - total) * 0.5
        for g in range(n):
            gbase = start + g * (unit + MERLON_GAP_OUT)
            for i in range(group):
                off = gbase + i * (mw + MERLON_GAP_IN) + mw * 0.5
                x = p0[0] + d[0] * off
                y = p0[1] + d[1] * off
                sx = mw * abs(d[1]) + (PARA_T - 0.06) * abs(d[0])
                sy = mw * abs(d[0]) + (PARA_T - 0.06) * abs(d[1])
                self.add(box(name, (x, y, z0 + gh * 0.5), (sx, sy, gh), M["stone_mid"]), 0.010)
            # 整组一条通长压顶：组内看不出缝，组间是干净的缺口 → 读成"拼接的墙段"
            gm = gbase + unit * 0.5
            gx = p0[0] + d[0] * gm
            gy = p0[1] + d[1] * gm
            # 沿 d 的方向是组的长度，垂直方向才是墙厚 —— 两个 abs 别写反，
            # 写反的结果是压顶变成一条 3.3 m 长的板，从女儿墙里朝外伸出去
            gsx = (unit + 0.06) * abs(d[0]) + (PARA_T + 0.03) * abs(d[1])
            gsy = (unit + 0.06) * abs(d[1]) + (PARA_T + 0.03) * abs(d[0])
            self.add(box(name + "_cap", (gx, gy, z0 + gh + 0.035), (gsx, gsy, 0.07),
                         M["stone_dark"]), 0.005)

    # ── 4. 前右角楼 ─────────────────────────────────────────────────────────
    def tower(self):
        M = self.M
        cx = (T_X0 + T_X1) * 0.5
        w, d = T_X1 - T_X0, T_Y1 - YF
        cy = (YF + T_Y1) * 0.5
        self.add(box("tw_body", (cx, cy, T_TOP * 0.42), (w, d, T_TOP * 0.84), M["stone_light"]), 0.028)
        self.add(box("tw_dado", (cx, cy, 0.58), (w + 0.10, d + 0.10, 1.16), M["stone_mid"]), 0.022)
        self.add(box("tw_band", (cx, cy, 1.22), (w + 0.18, d + 0.18, 0.14), M["stone_dark"]), 0.012)
        self.add(box("tw_string", (cx, cy, H1), (w + 0.16, d + 0.16, 0.18), M["stone_light"]), 0.014)
        for sx in (-1, 1):
            for sy in (-1, 1):
                for i in range(3):
                    self.add(box("tw_quoin", (cx + sx * (w * 0.5 - 0.13), cy + sy * (d * 0.5 - 0.13),
                                              0.92 + i * 0.78),
                                 (0.42, 0.42, 0.40), M["stone_mid"]))
        # 顶部平台 + 女儿墙 + 成组垛口
        cap_z = T_TOP - MERLON_H - 0.28
        self.add(box("tw_floor", (cx, cy, cap_z), (w + 0.10, d + 0.10, 0.18), M["stone_dark"]), 0.010)
        for (dx, dy, sx_, sy_) in ((0, -d * 0.5 + 0.15, w, 0.32),
                                   (0, d * 0.5 - 0.15, w, 0.32),
                                   (-w * 0.5 + 0.15, 0, 0.32, d - 0.64),
                                   (w * 0.5 - 0.15, 0, 0.32, d - 0.64)):
            self.add(box("tw_para", (cx + dx, cy + dy, cap_z + 0.32), (sx_, sy_, 0.64),
                         M["stone_light"]), 0.014)
        # 女儿墙下的一圈阵营色带：和主楼的饰带同一个高度逻辑，让角楼也"染色"
        self.add(box("tw_team", (cx, cy, cap_z - 0.20), (w + 0.06, d + 0.06, 0.34),
                     M["team"]), 0.010)
        self.add(box("tw_team_t", (cx, cy, cap_z - 0.045), (w + 0.08, d + 0.08, 0.06),
                     M["team_trim"]), 0.004)
        # 角楼体积小：垛口用 0.48 宽、2 个一组
        self.merlon_row("tw_merlon_f", (cx - w * 0.5 + 0.30, cy - d * 0.5 + 0.15), (1, 0),
                        w - 0.60, cap_z + 0.64, group=2, mw=0.48, gh=0.46)
        self.merlon_row("tw_merlon_r", (cx + w * 0.5 - 0.15, cy - d * 0.5 + 0.30), (0, 1),
                        d - 0.60, cap_z + 0.64, group=2, mw=0.48, gh=0.46)
        # 角楼正面的窗（暖光）
        self.add(box("tw_win", (cx, T_Y1 + 0.02, 5.05), (0.78, 0.10, 1.18), M["glow"]))
        # 窗框必须拆四条边：原来是一块 (0.96 × 1.36) 的实心板挡在玻璃前面，
        # 塔窗永远是一块深色方板 —— 这就是"窗户都像没点灯"的第二个原因
        for sgn in (-1, 1):
            self.add(box("tw_win_fL", (cx + sgn * 0.45, T_Y1 + 0.09, 5.05),
                         (0.14, 0.16, 1.42), M["wood_dark"]), 0.008)
            self.add(box("tw_win_fT", (cx, T_Y1 + 0.09, 5.05 + sgn * 0.66),
                         (1.02, 0.16, 0.15), M["wood_dark"]), 0.008)
        self.add(box("tw_win_bar", (cx, T_Y1 + 0.15, 5.05), (0.055, 0.06, 1.22), M["wood_dark"]), 0.004)
        # 窗楣必须**高于**窗框顶（框顶 5.785）：压在框上会在窗顶拉出一条闪烁的糊边
        # 窗楣加深到 0.20 并埋进墙 5 cm（抬高后只留 0.14 会悬在墙面外）
        self.add(box("tw_win_lintel", (cx, T_Y1 + 0.05, 5.885), (1.12, 0.20, 0.16),
                     M["stone_light"]), 0.010)
        # 下层箭孔
        self.add(box("tw_slit", (cx, T_Y1 + 0.04, 2.10), (0.14, 0.14, 0.66), M["coal"]), 0.006)
        self.add(box("tw_slit_f", (cx, T_Y1 + 0.01, 2.10), (0.26, 0.12, 0.80), M["stone_mid"]), 0.008)
        # 角楼旗杆（总高约 11.7，比铁匠铺 11.05 略高）
        self.add(revolve("tw_pole", [(0.042, 0.0), (0.038, 1.20)], 6, (cx, cy, cap_z + 0.90),
                         M["wood_dark"]), 0.0, 1)
        self.add(revolve("tw_ball", [(0.055, 0.0), (0.045, 0.04), (0.02, 0.10)], 6,
                         (cx, cy, cap_z + 2.06), M["gold"]), 0.0, 1)
        prof = [(0.0, 0.0), (0.94, -0.07), (0.76, -0.30), (0.94, -0.54), (0.0, -0.56)]
        self.add(extrude("tw_flag", prof, "Y", 0.04, (cx, cap_z + 1.94), M["team"], offset=cy), 0.004)
        # 徽记底边 = 旗顶 − 0.50，总高 0.40：旗面在 x 0.13–0.44 区间内净高 0.52，
        # 上下各留 0.05 以上（徽记中心 cy+0.033 → 贴回布面 2 mm，原 v3.4 是 cy+0.035）
        self.crest("tw_crest", "Y", cx + 0.286, cy + 0.033, cap_z + 1.455, 0.36)

    # ── 5. 营门（一级门槛 + 双开门 + 门楣带 + 门楣盾）──────────────────────
    def gate(self):
        M = self.M
        gw = GATE_W * 0.5
        # 门洞里的暖光（贴在后墙上）
        self.add(box("gate_glow", (0, YF - 0.76, 1.86), (GATE_W - 0.16, 0.04, 2.76), M["glow"]))
        # 拱券石 + 门框 + 拱心石
        self.add(arch_band("gate_arch", 0.0, GATE_SPRING, gw, gw + 0.26,
                           YF - 0.06, YF + 0.13, M["stone_light"], segs=10), 0.020)
        for sgn in (-1, 1):
            self.add(box("gate_jamb", (sgn * (gw + 0.12), YF + 0.04, GATE_SPRING * 0.5 + 0.22),
                         (0.24, 0.24, GATE_SPRING - 0.44), M["stone_light"]), 0.018)
        # 不做拱心石：深色方块压在拱顶会读成"门洞里吊着一块石头"，
        # 拱券本身（arch_band）已经足够读"石头门洞"。
        # 双开木门（各向里开 20°）
        leaf = (GATE_W - 0.12) * 0.5
        for sgn in (-1, 1):
            a = math.radians(20)
            rot_z = -a if sgn < 0 else math.pi + a
            hx = sgn * (gw - 0.04)
            px = hx + math.cos(rot_z) * leaf * 0.5
            py = (YF - 0.30) + math.sin(rot_z) * leaf * 0.5
            self.add(box("gate_leaf", (px, py, 1.90), (leaf, 0.10, 2.80),
                         M["wood_dark"], rot=(0, 0, rot_z)), 0.014)
            for k in (-1, 1):
                self.add(box("gate_seam", (px + k * 0.18 * math.cos(rot_z),
                                           py + k * 0.18 * math.sin(rot_z), 1.90),
                             (0.04, 0.03, 2.66), M["wood_dark"], rot=(0, 0, rot_z)), 0.002)
            for zz in (1.16, 2.44):
                self.add(box("gate_iron", (px, py, zz), (leaf - 0.10, 0.12, 0.10),
                             M["iron"], rot=(0, 0, rot_z)), 0.006)
        # 门框两侧的阵营色壁柱（0.32 宽，读"门套"）
        for sgn in (-1, 1):
            self.add(box("gate_pilaster", (sgn * 1.32, YF + 0.08, 2.13), (0.32, 0.14, 3.44),
                         M["team"]), 0.010)
            self.add(box("gate_pilaster_t", (sgn * 1.32, YF + 0.10, 3.78), (0.36, 0.16, 0.10),
                         M["team_trim"]), 0.004)
        # 门楣横带：从门套顶上拉一条，把门与二层木构连起来（也是阵营色的大面）
        self.add(box("gate_band", (0, YF + 0.06, 3.90), (GATE_W + 0.74, 0.13, 0.10),
                     M["team"]), 0.008)
        self.add(box("gate_band_t", (0, YF + 0.08, 3.945), (GATE_W + 0.78, 0.15, 0.035),
                     M["team_trim"]), 0.004)
        # 门楣盾（压在横带上）
        self.kite("shield_gate", (0.0, YF + 0.20, 4.72), "Y", SHIELD_W * 0.86, SHIELD_H * 0.86)

    # ── 5.5 门楼 ────────────────────────────────────────────────────────────
    def gatehouse(self):
        """门楼：女儿墙上凸起的一段，带 3 个垛口。

        v3.3 加：俯视时前墙原本只有一圈垛口，看不出"门在哪"。门楼给前墙一个凸出的体量，
        正立面多一层轮廓，俯视也能一眼找到入口。
        """
        M = self.M
        w = 1.55                     # 半宽
        y0, y1 = YF - 0.02, YF + 0.42
        z0, z1 = H2 + PARA - 0.22, H2 + PARA + 1.04
        cy = (y0 + y1) * 0.5
        self.add(box("gh_body", (0, cy, (z0 + z1) * 0.5), (w * 2, y1 - y0, z1 - z0),
                     M["stone_light"]), 0.026)
        self.add(box("gh_cap", (0, cy + 0.02, z1 + 0.05), (w * 2 + 0.10, y1 - y0 + 0.10, 0.10),
                     M["stone_dark"]), 0.008)
        for i, dx in enumerate((-0.88, 0.0, 0.88)):
            self.add(box("gh_merlon%d" % i, (dx, cy, z1 + 0.10 + 0.26),
                         (0.64, y1 - y0, 0.52), M["stone_mid"]), 0.012)
            self.add(box("gh_merlon_cap%d" % i, (dx, cy, z1 + 0.10 + 0.55),
                         (0.68, y1 - y0 + 0.04, 0.06), M["stone_dark"]), 0.004)
        # 门楼正面一个箭孔：不加的话正面就是一块素方板，只有顶上三个齿
        self.add(box("gh_slit", (0.0, y1 - 0.03, z0 + 0.66), (0.18, 0.10, 0.68), M["coal"]), 0.004)
        self.add(box("gh_slit_f", (0.0, y1 - 0.05, z0 + 0.66), (0.34, 0.10, 0.84),
                     M["stone_mid"]), 0.006)
        # 门楼下的托石（让体量"坐"在墙上而不是浮着）
        for sgn in (-1, 1):
            self.add(box("gh_corbel", (sgn * (w - 0.18), cy, z0 - 0.14),
                         (0.34, y1 - y0 + 0.06, 0.28), M["stone_mid"]), 0.010)

    # ── 6. 二层半木构 ───────────────────────────────────────────────────────
    def timber(self):
        M = self.M
        yy = YF + 0.055
        z0, z1 = H1 + 0.20, H2 - 0.34
        # 前墙：门套右侧到角楼、左侧到角墙
        xs = (-4.86, -3.68, -2.50, -1.48, 1.48, 2.44)
        for x in xs:
            self.add(box("post", (x, yy, (z0 + z1) * 0.5), (0.19, 0.13, z1 - z0),
                         M["wood_dark"]), 0.009)
        for zz in (z0 + 0.05, (z0 + z1) * 0.5, z1 - 0.05):
            self.add(box("rail", (-1.24, yy, zz), (W2 + T_X0 - 0.34, 0.14, 0.16),
                         M["wood_dark"]), 0.009)
        for (xa, xb) in ((-4.86, -3.68), (-3.68, -2.50), (-2.50, -1.32), (1.32, 2.50)):
            mid = (xa + xb) * 0.5
            self.add(beam("brace", (xa + 0.09, yy, z0 + 0.16), (mid, yy, z0 + 0.72),
                          0.11, 0.09, M["wood_dark"]), 0.005)
            self.add(beam("brace", (xb - 0.09, yy, z0 + 0.16), (mid, yy, z0 + 0.72),
                          0.11, 0.09, M["wood_dark"]), 0.005)
        # 侧墙 + 后墙
        for sx in (-1, 1):
            for yy2 in (-3.10, -1.86, -0.62, 0.62, 1.86, 3.10):
                self.add(box("stud", (sx * (W2 + 0.02), yy2, (z0 + z1) * 0.5),
                             (0.12, 0.18, z1 - z0), M["wood_dark"]), 0.007)
            for zz in (z0 + 0.05, z1 - 0.05):
                self.add(box("rail_side", (sx * (W2 + 0.02), (YB + YF) * 0.5, zz),
                             (0.13, YF - YB - 0.40, 0.16), M["wood_dark"]), 0.007)
        for x in (-4.80, -3.50, -2.20, -0.90, 0.40, 1.70, 3.00, 4.30):
            self.add(box("post_b", (x, YB - 0.055, (z0 + z1) * 0.5), (0.19, 0.13, z1 - z0),
                         M["wood_dark"]), 0.009)
        for zz in (z0 + 0.05, z1 - 0.05):
            self.add(box("rail_b", (0, YB - 0.055, zz), (W2 * 2 - 0.30, 0.14, 0.16),
                         M["wood_dark"]), 0.009)

    # ── 7. 窗 ───────────────────────────────────────────────────────────────
    def windows(self):
        M = self.M
        # 一层前墙（门左两扇；门右到角楼只有 1.3 m，开不了窗）
        for x in (-4.16, -2.80):
            self.arch_win("win_f", (x, YF + 0.03, 2.12), 0.52, 1.22, "Y")
        # 一层侧墙（落在扶壁之间）
        for sx in (-1, 1):
            for yy in (-1.70, 0.50):
                self.arch_win("win_s", (sx * (W2 + 0.01), yy, 1.94), 0.54, 1.26, "X", out=sx)
        # 一层后墙
        for x in (-2.30, 0.0, 2.30):
            self.arch_win("win_b", (x, YB - 0.03, 1.94), 0.52, 1.22, "Y", out=-1)
        # 二层前墙（木构之间的小方窗）：门楣带两侧各一，右侧一扇
        # 只留右边一扇点灯（岗哨值夜），左边那扇是冷玻璃 —— 全亮会读成"整层都有人"
        self.win2("win2", (-2.10, YF + 0.19, 5.56), 0.60, 1.06)
        self.win2("win2", (1.10, YF + 0.19, 5.56), 0.60, 1.06, mat=M["glow"], tag="_lit")
        # 二层侧墙
        for sx in (-1, 1):
            for yy in (-2.40, 1.60):
                self.add(box("win2s", (sx * (W2 + 0.13), yy, 5.56), (0.10, 0.58, 1.06), M["glass"]))
                for k in (-1, 1):
                    self.add(box("win2s_fL", (sx * (W2 + 0.17), yy + k * 0.36, 5.56),
                                 (0.14, 0.14, 1.24), M["wood_dark"]), 0.008)
                    self.add(box("win2s_fT", (sx * (W2 + 0.17), yy, 5.56 + k * 0.60),
                                 (0.14, 0.86, 0.14), M["wood_dark"]), 0.008)

    def win2(self, name, center, w, h, mat=None, tag=""):
        """二层木构间的小方窗：玻璃 + 木框 + 十字棂 + 石窗台。mat 默认冷玻璃。"""
        M = self.M
        mat = M["glass"] if mat is None else mat
        cx, cy, cz = center
        self.add(box(name + tag, (cx, cy, cz), (w, 0.10, h), mat))
        for sgn in (-1, 1):
            self.add(box(name + "_fL", (cx + sgn * (w * 0.5 + 0.07), cy + 0.06, cz),
                         (0.14, 0.16, h + 0.30), M["wood_dark"]), 0.008)
            self.add(box(name + "_fT", (cx, cy + 0.06, cz + sgn * (h * 0.5 + 0.08)),
                         (w + 0.28, 0.16, 0.15), M["wood_dark"]), 0.008)
        self.add(box(name + "_bar", (cx, cy + 0.14, cz), (0.055, 0.05, h + 0.06),
                     M["wood_dark"]), 0.003)
        self.add(box(name + "_bar2", (cx, cy + 0.14, cz), (w + 0.02, 0.05, 0.055),
                     M["wood_dark"]), 0.003)
        self.add(box(name + "_sill", (cx, cy + 0.08, cz - h * 0.5 - 0.09), (w + 0.34, 0.22, 0.11),
                     M["stone_light"]), 0.008)

    def arch_win(self, name, center, w, h, face, out=1, mat=None):
        M = self.M
        mat = M["glass"] if mat is None else mat
        cx, cy, cz = center
        hw = w * 0.5
        straight = h - hw
        if face == "Y":
            self.add(extrude(name, arch_profile(w, straight, segs=6), "Y", 0.10, (cx, cz),
                             mat, offset=cy), 0.0)
            self.add(arch_band(name + "_arch", cx, cz + straight, hw, hw + 0.13,
                               cy + out * 0.04, cy + out * 0.12, M["stone_light"], segs=6), 0.008)
            for sgn in (-1, 1):
                self.add(box(name + "_jamb", (cx + sgn * (hw + 0.06), cy + out * 0.06,
                                              cz + straight * 0.5),
                             (0.12, 0.12, straight), M["stone_light"]), 0.006)
            self.add(box(name + "_bar", (cx, cy + out * 0.08, cz + straight * 0.5),
                         (0.05, 0.06, straight), M["wood_dark"]), 0.003)
            self.add(box(name + "_sill", (cx, cy + out * 0.06, cz - 0.062),
                         (w + 0.28, 0.20, 0.10), M["stone_light"]), 0.008)
        else:
            self.add(extrude(name, arch_profile(w, straight, segs=6), "X", 0.10, (cy, cz),
                             mat, offset=cx + out * 0.01), 0.0)
            self.add(arch_band(name + "_arch", cx, cz + straight, hw, hw + 0.13,
                               cy - hw - 0.13, cy + hw + 0.13, M["stone_light"], segs=6), 0.008)
            for sgn in (-1, 1):
                self.add(box(name + "_jamb", (cx + out * 0.06, cy + sgn * (hw + 0.06),
                                              cz + straight * 0.5),
                             (0.12, 0.12, straight), M["stone_light"]), 0.006)
            self.add(box(name + "_bar", (cx + out * 0.08, cy, cz + straight * 0.5),
                         (0.06, 0.05, straight), M["wood_dark"]), 0.003)
            self.add(box(name + "_sill", (cx + out * 0.06, cy, cz - 0.062),
                         (0.20, w + 0.28, 0.10), M["stone_light"]), 0.008)

    # ── 8. 阵营色标准模块 ───────────────────────────────────────────────────
    def kite(self, name, center, face, w, h, out=1):
        M = self.M
        cx, cy, cz = center
        if face == "Y":
            self.add(kite_shield(name + "_rim", (cx, cy, cz), w + 0.14, h + 0.14, 0.08,
                                 M["gold"]), 0.012)
            self.add(kite_shield(name + "_field", (cx, cy + 0.05, cz), w, h, 0.09,
                                 M["team"]), 0.012)
            # 盾是"上宽下尖"，纹章要往上挪一点，不然视觉重心掉在尖底上
            # 徽记压在盾面上：盾面厚 0.09、圆心在 cy+0.05，前表面 cy+0.095。
            # 徽记中心 cy+0.090 → 背面埋进盾面 8 mm，正面凸出 8 mm（旧版悬空 7 mm）
            self.emblem(name, "Y", cx, cy + 0.090, cz + h * 0.06, w, h, shield=False)
        else:
            hw, hh = w * 0.5, h * 0.5
            prof = [(-hh, hw), (hh, hw), (hh * 0.90, -hw * 0.12), (0.0, -hw), (-hh * 0.90, -hw * 0.12)]
            pb = [(p[0] - 0.07, p[1] + 0.07) for p in prof]
            self.add(extrude(name + "_rim", pb, "X", 0.08, (cy, cz), M["gold"],
                             offset=cx + out * 0.01), 0.012)
            self.add(extrude(name + "_field", prof, "X", 0.09, (cy, cz), M["team"],
                             offset=cx + out * 0.06), 0.012)
            self.emblem(name, "X", cx + out * 0.090, cy, cz + h * 0.06, w, h, shield=False)

    def crest(self, name, face, cx, cy, cz, sz, out=1, shield=True):
        """联盟徽记：盾牌（金边蓝底）+ 王冠（冠带 + 三尖 + 三宝石）。

        cz = 底边（不是中心）。含盾时 宽 1.00·sz、高 1.05·sz；
        `shield=False` 时只画王冠 —— 用在本身就是一面盾的载体上，避免"盾中盾"。

        造型逻辑：这套建筑是"方石 + 垛口 + 蓝金"的语言，徽记也只用直边与折角 ——
        盾是 7 段折线（不是曲线），王冠是矩形 + 三角形，宝石是方点。
        金色只分两层（盾边 / 冠体），加一圈 coal 描边把金边从浅石墙上"切"出来。
        """
        M = self.M
        dep = 0.028

        def poly(tag, pts, mat, dy=0.0):
            p = [(u * sz, v * sz) for (u, v) in pts]
            if face == "Y":
                self.add(extrude(name + tag, p, "Y", dep, (cx, cz), mat, offset=cy + dy), 0.003)
            else:
                self.add(extrude(name + tag, p, "X", dep, (cy, cz), mat, offset=cx + out * dy), 0.003)

        def crown(du, dv, ch, dy0):
            """王冠：底边中点在 (du, dv)，高 ch、宽 1.30·ch。"""
            w = ch * 0.65
            poly("_band", [(du - w, dv), (du + w, dv), (du + w, dv + ch * 0.21),
                           (du - w, dv + ch * 0.21)], M["gold"], dy=dy0)
            for i, (a, b, top) in enumerate(((-0.94, -0.24, 0.74),
                                             (-0.20, 0.20, 1.00),
                                             (0.24, 0.94, 0.74))):
                poly("_spike%d" % i,
                     [(du + a * w, dv + ch * 0.19), (du + b * w, dv + ch * 0.19),
                      (du + (a + b) * 0.5 * w, dv + ch * top)],
                     M["gold"], dy=dy0 + 0.004)
            for i, uu in enumerate((-0.56, 0.0, 0.56)):
                g = ch * 0.058
                poly("_gem%d" % i, [(du + uu * w - g, dv + ch * 0.045),
                                    (du + uu * w + g, dv + ch * 0.045),
                                    (du + uu * w + g, dv + ch * 0.155),
                                    (du + uu * w - g, dv + ch * 0.155)],
                     M["coal"], dy=dy0 + 0.008)

        # 所有 v 都从 0（底边）往上数：extrude 的 v 是"加在原点上的坐标"，
        # 写成负数会让整块徽记沉到 cz 以下（旗帜上就是直接掉出旗面）
        if shield:
            # 直边占到 0.40 才开始收尖 —— 收得太早（原来的 0.62）王冠一放大就会从盾的
            # 斜边里穿出去；现在冠宽 0.60、盾腹宽 0.80，四周留 0.10
            edge = [(-0.50, 1.05), (0.50, 1.05), (0.50, 0.40), (0.28, 0.16), (0.0, 0.0),
                    (-0.28, 0.16), (-0.50, 0.40)]
            rim = [(-0.48, 1.03), (0.48, 1.03), (0.48, 0.40), (0.27, 0.18), (0.0, 0.035),
                   (-0.27, 0.18), (-0.48, 0.40)]
            field = [(-0.40, 0.94), (0.40, 0.94), (0.40, 0.38), (0.22, 0.16), (0.0, 0.10),
                     (-0.22, 0.16), (-0.40, 0.38)]
            poly("_edge", edge, M["coal"], dy=0.004)
            poly("_rim", rim, M["gold"], dy=0.008)
            poly("_field", field, M["roof_edge"], dy=0.012)
            crown(0.0, 0.40, 0.46, 0.017)
        else:
            crown(0.0, 0.0, 0.68, 0.0)

    def emblem(self, name, face, cx, cy, cz, w, h, shield=True):
        """把徽记放进纹章框：cz 是框中心，整体上移 5%。"""
        sz = min(w, h) * (0.80 if shield else 0.74)
        zc = cz + h * 0.05
        zb = zc - sz * (0.525 if shield else 0.34)
        if face == "Y":
            self.crest(name, "Y", cx, cy, zb, sz, shield=shield)
        else:
            self.crest(name, "X", cx, cy, zb, sz, out=(1 if cx > 0 else -1), shield=shield)

    def wallbanner(self, name, center, face, w=1.46, h=2.00, out=1):
        """挂在木构上的垂旗：挑杆 + 三只铁吊环 + 底角流苏。

        v3.5：原来是"一块贴在墙上的蓝布"（只有两根贴墙的横杆），远看分不清是旗还是墙板。
        现在杆子用铁托架挑离墙面 0.24、布用三只吊环挂在杆下、底角垂两枚流苏，
        形态上明确是"挂上去的旗"，旗面也就能放心做大。
        """
        M = self.M
        cx, cy, cz = center
        hw, hh = w * 0.5, h * 0.5
        prof = [(-hw, hh), (hw, hh), (hw, -hh * 0.78), (hw * 0.34, -hh),
                (-hw * 0.34, -hh), (-hw, -hh * 0.78)]
        rz = cz + hh + 0.140
        if face == "Y":
            self.add(extrude(name + "_cloth", prof, "Y", 0.06, (cx, cz), M["team"], offset=cy), 0.012)
            self.add(box(name + "_rod", (cx, cy, rz), (w + 0.38, 0.09, 0.09), M["wood_dark"]), 0.006)
            for sgn in (-1, 1):
                self.add(box(name + "_fin", (cx + sgn * (hw + 0.19), cy, rz),
                             (0.08, 0.11, 0.11), M["gold"]), 0.005)
                self.add(box(name + "_brk", (cx + sgn * hw * 0.70, cy - 0.11, rz - 0.02),
                             (0.05, 0.26, 0.05), M["iron"]), 0.003)
                self.add(box(name + "_tass", (cx + sgn * (hw - 0.05), cy, cz - hh * 0.78 - 0.10),
                             (0.075, 0.075, 0.20), M["team_trim"]), 0.004)
            for k in (-1, 0, 1):
                self.add(box(name + "_ring", (cx + k * hw * 0.54, cy, cz + hh + 0.055),
                             (0.05, 0.05, 0.11), M["iron"]), 0.003)
            # 布厚 0.06（cy±0.03）：徽记中心 cy + 0.023·out → 背面埋 7 mm、正面凸 6 mm。
            # 旧版 cy+0.075 是**悬在布前面 3.2 cm**，侧面看是一块飘着的金牌；
            # out 是"布朝外的方向"：后墙横幅的正面朝 −Y，不取反的话徽记会贴在布背面。
            self.emblem(name, "Y", cx, cy + 0.023 * out, cz + h * 0.01, w * 0.78, h * 0.60)
        else:
            self.add(extrude(name + "_cloth", prof, "X", 0.06, (cy, cz), M["team"], offset=cx), 0.012)
            self.add(box(name + "_rod", (cx, cy, rz), (0.09, w + 0.38, 0.09), M["wood_dark"]), 0.006)
            for sgn in (-1, 1):
                self.add(box(name + "_fin", (cx, cy + sgn * (hw + 0.19), rz),
                             (0.11, 0.08, 0.11), M["gold"]), 0.005)
                self.add(box(name + "_brk", (cx + out_sign(cx) * 0.11, cy + sgn * hw * 0.70, rz - 0.02),
                             (0.26, 0.05, 0.05), M["iron"]), 0.003)
                self.add(box(name + "_tass", (cx, cy + sgn * (hw - 0.05), cz - hh * 0.78 - 0.10),
                             (0.075, 0.075, 0.20), M["team_trim"]), 0.004)
            for k in (-1, 0, 1):
                self.add(box(name + "_ring", (cx, cy + k * hw * 0.54, cz + hh + 0.055),
                             (0.05, 0.05, 0.11), M["iron"]), 0.003)
            self.emblem(name, "X", cx + out_sign(cx) * 0.023, cy, cz + h * 0.01, w * 0.78, h * 0.60)

    def banner(self, name, x, z_top, w=BANNER_W, h=BANNER_H):
        M = self.M
        y = YF + 0.34
        self.add(box(name + "_rod", (x, y, z_top), (w + 0.18, 0.06, 0.06), M["wood_dark"]), 0.004)
        prof = [(-w * 0.5, 0.0), (w * 0.5, 0.0), (w * 0.5, -h * 0.80),
                (w * 0.10, -h), (-w * 0.10, -h), (-w * 0.5, -h * 0.80)]
        self.add(extrude(name + "_cloth", prof, "Y", 0.05, (x, z_top - 0.05), M["team"],
                         offset=y), 0.008)
        self.add(box(name + "_trim", (x, y, z_top - 0.07), (w + 0.06, 0.062, 0.07),
                     M["team_trim"]), 0.004)

    def heraldry(self):
        M = self.M
        # ① 女儿墙下的整圈阵营色饰带：v3.5 从 0.34 加高到 0.52 —— 这是正立面最醒目的一条
        #    横向色块，太窄时在 RTS 尺度只剩一根线（用户要"上面横线再大些"）
        BH = 0.70
        z_band = H2 - BH * 0.5 - 0.02
        self.add(box("band_f", ((-W2 + T_X0 - 0.08) * 0.5, YF + 0.19, z_band),
                     (W2 + T_X0 - 0.08, 0.13, BH), M["team"]), 0.010)
        # 金线比饰带顶面高 8 mm —— 两个顶面正好齐平时，俯视会沿饰带拉出一条闪线
        self.add(box("band_f_t", ((-W2 + T_X0 - 0.08) * 0.5, YF + 0.21, z_band + BH * 0.5 - 0.027),
                     (W2 + T_X0 - 0.08, 0.15, 0.07), M["team_trim"]), 0.004)
        for sx in (-1, 1):
            self.add(box("band_s", (sx * (W2 + 0.14), (YF + YB) * 0.5, z_band),
                         (0.13, YF - YB - 0.2, BH), M["team"]), 0.010)
            self.add(box("band_s_t", (sx * (W2 + 0.16), (YF + YB) * 0.5,
                                      z_band + BH * 0.5 - 0.027),
                         (0.15, YF - YB - 0.2, 0.07), M["team_trim"]), 0.004)
        self.add(box("band_b", (0, YB - 0.19, z_band), (W2 * 2 - 0.2, 0.13, BH),
                     M["team"]), 0.010)
        self.add(box("band_b_t", (0, YB - 0.21, z_band + BH * 0.5 - 0.027),
                     (W2 * 2 - 0.2, 0.15, 0.07), M["team_trim"]), 0.004)
        # ② 前墙大横幅（门左，带挑杆/吊环/流苏）
        self.wallbanner("wbanner_f", (-3.58, YF + 0.28, 5.40), "Y", 1.46, 1.96)
        # ③ 侧墙大横幅
        for sx, tag in ((-1, "L"), (1, "R")):
            self.wallbanner("wbanner_s" + tag, (sx * (W2 + 0.30), -0.30, 5.36), "X", 1.72, 2.08)
        # ④ 后墙横幅
        self.wallbanner("wbanner_b", (0, YB - 0.30, 5.34), "Y", 1.72, 2.06, out=-1)
        # ⑤ 盾：侧墙 + 角楼 + 门楣
        for sx, tag in ((-1, "L"), (1, "R")):
            self.kite("shield_s" + tag, (sx * (W2 + 0.07), 2.86, 2.30), "X", 1.04, 1.28, out=sx)
        self.kite("shield_tw", ((T_X0 + T_X1) * 0.5, T_Y1 + 0.12, 7.36), "Y", 1.02, 1.26)

    # ── 9. 屋顶平台 ─────────────────────────────────────────────────────────
    def roofdeck(self):
        M = self.M
        # 铺装层顶面 7.42，比墙顶 7.40 高 20 mm：
        # 两者同高的话，拖动视角时整块屋顶会大面积 z-fighting（这是上一版顶面闪烁的原因）
        Z = H2 + 0.02
        self.add(box("deck", (0, (YF + YB) * 0.5, H2 - 0.05), (W2 * 2 - 0.94, YF - YB - 0.94, 0.14),
                     M["stone_mid"]), 0.010)
        for i in range(4):
            yy = YB + 1.0 + i * 1.75
            self.add(box("deck_joint", (0, yy, Z + 0.005), (W2 * 2 - 1.10, 0.08, 0.02),
                         M["stone_mid"]), 0.0)
        # 中央旗杆
        self.add(box("pole_base", (0.0, -1.10, Z + 0.18), (0.46, 0.46, 0.36), M["iron"]), 0.008)
        self.add(revolve("pole", [(0.058, 0.0), (0.048, 2.90)], 8, (0.0, -1.10, Z + 0.30),
                         M["wood_dark"]), 0.0, 1)
        self.add(revolve("pole_ball", [(0.080, 0.0), (0.060, 0.05), (0.02, 0.12)], 8,
                         (0.0, -1.10, Z + 3.12), M["gold"]), 0.0, 1)
        fw, fh = 1.08, 0.72
        zt = Z + 2.94
        prof = [(0.0, 0.0), (fw, -0.09), (fw * 0.82, -fh * 0.5), (fw, -fh * 0.94), (0.0, -fh)]
        self.add(extrude("pole_flag", prof, "Y", 0.04, (0.0, zt), M["team"], offset=-1.08), 0.004)
        # 徽记底边 = 旗顶 − 0.585，总高 0.462、宽 0.44，四边都在旗内；
        # 中心 cy −1.047（原 −1.045）→ 贴回布面 2 mm，不再悬空
        self.crest("pole_crest", "Y", 0.30, -1.047, zt - 0.585, 0.44)
        # 屋顶楼梯间（1.45 × 1.35 + 单坡顶 + 门）
        sx0, sy0 = -3.55, -2.30
        # 楼梯间总高必须压在女儿墙顶（8.50）以下，否则从正面 / 侧面都会在垛口上探出一块
        self.add(box("ph_house", (sx0, sy0, Z + 0.45), (1.45, 1.35, 0.90), M["stone_light"]), 0.016)
        self.add(box("ph_house_base", (sx0, sy0, Z + 0.07), (1.61, 1.51, 0.14), M["stone_mid"]), 0.010)
        self.add(box("ph_roof", (sx0, sy0, Z + 0.95), (1.72, 1.62, 0.12), M["roof_edge"]), 0.010)
        self.add(box("ph_cap", (sx0, sy0, Z + 1.01), (1.66, 1.56, 0.04), M["stone_dark"]), 0.004)
        self.add(box("ph_door", (sx0, sy0 + 0.70, Z + 0.37), (0.74, 0.10, 0.74), M["wood_warm"]), 0.008)
        self.add(box("ph_door_f", (sx0, sy0 + 0.76, Z + 0.37), (0.90, 0.10, 0.86),
                     M["wood_dark"]), 0.006)
        # 屋顶瞭望矮墙 + 盾
        self.add(box("deck_wall", (0.10, YB + 0.82, Z + 0.38), (4.00, 0.28, 0.76), M["stone_light"]), 0.014)
        self.kite("shield_deck", (0.10, YB + 1.02, Z + 0.48), "Y", 0.82, 1.00)
        # 屋顶物资
        self.crate("deck_crate", (-3.55, -1.40), 0.82, 0.62, Z)
        self.barrel("deck_barrel", (3.95, -2.75), 0.34, 0.80, Z)
        for k in range(5):
            self.add(cyl("deck_bag", (3.10 + (k % 3) * 0.32, -2.00 + (k // 3) * 0.34,
                                      Z + 0.18 + (k // 3) * 0.32 + k * 0.012),
                         0.17, 0.58, 6, M["roof_wood"], axis="X"), 0.010)
        # 火盆架
        self.add(vcyl("brazier", (-1.15, 1.05, Z + 0.30), 0.46, 0.26, 8, M["iron"]), 0.010)
        self.add(vcyl("brazier_coal", (-1.15, 1.05, Z + 0.52), 0.36, 0.08, 8, M["coal"]), 0.006)
        for k in range(3):
            self.add(box("brazier_leg", (-1.15 + (k - 1) * 0.30, 1.05, Z + 0.15),
                         (0.08, 0.08, 0.30), M["iron"]), 0.003)

    # ── 10. 训练场（与主体咬合）────────────────────────────────────────────
    def yard(self):
        M = self.M
        z = YARD_Z
        # 三面围栏：左右两段的后端直接压在建筑基座侧面上（板中心埋进石台 0.14），
        # 建筑前墙就是场地的第四面 —— 不再是"建筑前面 2.5 m 处另立一个方框"。
        self.fence_run("fence_l", (-YARD_X, YARD_Y0), (0, 1), YARD_Y1 - YARD_Y0, z)
        self.fence_run("fence_r", (YARD_X, YARD_Y0), (0, 1), YARD_Y1 - YARD_Y0, z)
        # 前段：从转角内侧 0.06 起步、到门柱外侧 2.10 收头（转角与门柱都由别的件收口）
        for sgn in (-1, 1):
            # rail_dz −6 mm：前段横梁与侧段横梁在转角处同高会闪（侧段已经通长到转角）
            self.fence_run("fence_f", (sgn * (YARD_X - 0.06), YARD_Y1), (-sgn, 0),
                           YARD_X - 2.10 + 0.06, z, skip_first=True, rail_dz=-0.006)
        # 开口两侧门柱 + 门柱上的阵营色旗
        for sgn in (-1, 1):
            self.add(box("gate_post", (sgn * 1.90, YARD_Y1, z + 1.01), (0.30, 0.30, 2.02),
                         M["wood_warm"]), 0.012)
            self.add(cone("gate_cap", (sgn * 1.90, YARD_Y1, z + 2.02),
                          (sgn * 1.90, YARD_Y1, z + 2.24), 0.24, 4, M["wood_warm"]), 0.0, 1)
            self.add(box("gate_flag", (sgn * 1.90, YARD_Y1 + 0.155, z + 1.72),
                         (0.46, 0.03, 0.34), M["team"]), 0.004)
        # 靠建筑的两根围栏立柱挂阵营色小旗：把场地"染"成建筑的延伸
        for sgn in (-1, 1):
            self.add(box("fence_flag", (sgn * YARD_X + 0.02, YARD_Y0 + 0.34, z + 1.40),
                         (0.03, 0.34, 0.26), M["team"]), 0.004)
            self.add(box("fence_flag_t", (sgn * YARD_X + 0.02, YARD_Y0 + 0.34, z + 1.54),
                         (0.04, 0.36, 0.04), M["team_trim"]), 0.002)
        # ── 贴墙带（y 4.4–5.9）：道具与墙接触，读成"建筑带出来的院子" ──
        self.wall_pikes("pikes_wall", (-2.30, YF + 0.44))
        self.shield_row("shields_wall", (1.98, YF + 0.54))
        self.armor_stand("armor", (-4.45, 4.64))
        self.barrel("barrel_a", (-3.76, 4.56), 0.34, 0.80, z)
        self.crate("crate_b", (-2.98, 4.66), 0.62, 0.54, z + 0.05)
        # ── 训练带（y 6.0–8.8）：两个假人分列左右，沙坑在左 ──
        # 中线（|x| < 1.4、y 4.0–9.8）留空：这是从营门到围栏开口的进场走廊
        self.dummy("dummy_a", (-4.35, 5.95))
        self.dummy("dummy_b", (3.15, 6.95))
        # 练剑桩站进沙坑中心：空着的沙圈读成"水坑"，有根桩才是"操练位"
        self.pell("pell_a", (-2.65, 7.60), G_SAND)
        self.weapon_rack("wrack_a", (3.95, 8.45))
        # y > 8.2 一律留空：这是从大门到围栏开口的进场院，不摆任何东西

    def fence_run(self, name, p0, d, length, z0=0.0, skip_first=False, rail_dz=0.0):
        """板式木栅栏：竖板 + 两道横梁 + 立柱 + 四棱锥帽。

        `skip_first`：前段围栏从后段的端头起步，不跳过就会在转角处**放两块
        完全重合的板 + 两根重合的柱**（六个面全部共面 → 转角一直在闪）。
        转角由后段（y 向那两段）独占。
        """
        M = self.M
        n = int(length / 0.58)
        for i in range(n + 1):
            if skip_first and i == 0:
                continue
            t = i / max(n, 1)
            x = p0[0] + d[0] * t * length
            y = p0[1] + d[1] * t * length
            sx = 0.24 * abs(d[1]) + 0.07 * abs(d[0])
            sy = 0.24 * abs(d[0]) + 0.07 * abs(d[1])
            self.add(box(name + "_plank", (x, y, z0 + FENCE_H * 0.5), (sx, sy, FENCE_H),
                         M["wood_warm"]), 0.006)
        for zz in (0.38, 0.98):
            cx = p0[0] + d[0] * length * 0.5
            cy = p0[1] + d[1] * length * 0.5
            sx = abs(d[0]) * length + abs(d[1]) * 0.10
            sy = abs(d[1]) * length + abs(d[0]) * 0.10
            self.add(box(name + "_rail", (cx, cy, z0 + zz + rail_dz), (sx + 0.10, sy + 0.10, 0.14),
                         M["wood_dark"]), 0.006)
        m = max(2, int(length / 2.60))
        for i in range(m + 1):
            if skip_first and i == 0:
                continue
            t = i / m
            x = p0[0] + d[0] * t * length
            y = p0[1] + d[1] * t * length
            self.add(box(name + "_post", (x, y, z0 + FENCE_H * 0.55), (0.24, 0.24, FENCE_H * 1.10),
                         M["wood_dark"]), 0.008)
            self.add(cone(name + "_cap", (x, y, z0 + FENCE_H * 1.10),
                          (x, y, z0 + FENCE_H * 1.10 + 0.20), 0.18, 4, M["wood_dark"]), 0.0, 1)

    def wall_pikes(self, name, p):
        """墙根的一束立矛：4 支垂直立着，紧贴建筑前墙。"""
        M = self.M
        x, y = p
        for k in range(4):
            ox = (k - 1.5) * 0.15
            self.add(beam(name + "_shaft", (x + ox, y + ox * 0.06, YARD_Z + 0.02),
                          (x + ox, y + ox * 0.06, YARD_Z + 2.34), 0.044, 0.044,
                          M["wood_warm"]), 0.003)
            self.add(cone(name + "_tip", (x + ox, y + ox * 0.06, YARD_Z + 2.34),
                          (x + ox, y + ox * 0.06, YARD_Z + 2.60), 0.058, 4, M["iron"]), 0.0, 1)
        self.add(box(name + "_tie", (x, y, YARD_Z + 0.52), (0.62, 0.12, 0.10),
                     M["iron"]), 0.004)

    def shield_row(self, name, p):
        """墙根靠着的两面盾。

        v3.4：原来是三面 0.34 宽、间距 0.04 的盾 —— 渲染出来是一块 1.1 m 宽的蓝板，
        完全读不出"盾"。改成两面、间距 0.14、高度与倾角各不相同，才有"随手靠在墙上"的样子。
        """
        M = self.M
        x, y = p
        for k, (ox, hh, ang) in enumerate(((-0.26, 0.66, -0.20), (0.26, 0.58, -0.12))):
            self.add(box(name + "_b%d" % k, (x + ox, y, YARD_Z + 0.03 + hh * 0.5),
                         (0.36, 0.11, hh), M["team"], rot=(ang, 0, 0)), 0.008)
            self.add(box(name + "_t%d" % k, (x + ox, y + 0.005, YARD_Z + hh - 0.005),
                         (0.38, 0.13, 0.09), M["team_trim"], rot=(ang, 0, 0)), 0.004)
            self.add(box(name + "_r%d" % k, (x + ox, y + 0.02, YARD_Z + 0.02),
                         (0.40, 0.22, 0.05), M["wood_dark"]), 0.003)

    def pike_pile(self, name, p):
        """斜靠在一起的三支长矛堆。"""
        M = self.M
        x, y = p
        for k in range(3):
            ox = (k - 1) * 0.15
            self.add(beam(name + "_shaft", (x + ox, y, YARD_Z + 0.06),
                          (x + ox * 2.6, y + 0.34, YARD_Z + 2.44), 0.048, 0.048,
                          M["wood_warm"]), 0.003)
            self.add(cone(name + "_tip", (x + ox * 2.6, y + 0.34, YARD_Z + 2.44),
                          (x + ox * 2.8, y + 0.36, YARD_Z + 2.70), 0.06, 4, M["iron"]), 0.0, 1)

    def shield_stack(self, name, p):
        """三面盾靠在木架上。"""
        M = self.M
        x, y = p
        self.add(box(name + "_rack", (x, y + 0.16, YARD_Z + 0.30), (1.14, 0.14, 0.60),
                     M["wood_dark"]), 0.008)
        for k in range(3):
            self.add(box(name + "_b", (x + (k - 1) * 0.34, y + 0.04, YARD_Z + 0.48),
                         (0.32, 0.10, 0.70), M["team"]), 0.008)
            self.add(box(name + "_t", (x + (k - 1) * 0.34, y + 0.02, YARD_Z + 0.82),
                         (0.34, 0.12, 0.09), M["team_trim"]), 0.004)

    def straw_bale(self, name, p):
        """草垛：12 边圆柱 + 两道草绳。"""
        M = self.M
        x, y = p
        # 圆草卷（8 段）：草卷本来就是圆的，做成方的会和木箱撞造型。
        # "同一套"统一的是木架截面（0.18）和草绳样式，不是把圆件硬掰成方件。
        self.add(vcyl(name, (x, y, YARD_Z), 0.56, 0.86, 8, M["roof_wood"]), 0.018)
        self.add(tube_band(name + "_rope", (x, y), 0.575, 0.615, YARD_Z + 0.34, YARD_Z + 0.46,
                           8, M["wood_dark"]), 0.004)
        # 顶上的草茬：不加的话 0.68 × 0.90 的八边柱读成"陶坛"
        for k in range(4):
            a = math.pi * 0.5 * k + 0.4
            self.add(box(name + "_straw", (x + math.cos(a) * 0.28, y + math.sin(a) * 0.28,
                                           YARD_Z + 0.92),
                         (0.13, 0.13, 0.15), M["roof_wood"], rot=(0, 0, a)), 0.004)

    def pell(self, name, p, z0=YARD_Z):
        """练剑木桩：立柱 + 草包顶 + 横臂。z0 = 站的那一层地面。"""
        M = self.M
        x, y = p
        # 与假人同一套：方木立柱（0.18）+ 方草包 + 草绳 + 横臂
        self.add(box(name, (x, y, z0 + 0.86), (0.18, 0.18, 1.72), M["wood_warm"]), 0.008)
        self.add(box(name + "_top", (x, y, z0 + 1.58), (0.34, 0.32, 0.32), M["roof_wood"]), 0.010)
        self.add(box(name + "_cord", (x, y, z0 + 1.44), (0.38, 0.36, 0.07), M["wood_dark"]), 0.004)
        self.add(box(name + "_arm", (x, y, z0 + 1.28), (1.06, 0.14, 0.14), M["wood_dark"]), 0.006)

    def dummy(self, name, p):
        """草靶假人：十字木架 + 方草靶 + 草绳 + 头。"""
        M = self.M
        x, y = p
        z = YARD_Z
        self.add(vcyl(name + "_pad", (x, y, z), 0.80, 0.035, 8, M["earth_dark"]), 0.004)
        self.add(box(name + "_foot_x", (x, y, z + 0.17), (1.26, 0.18, 0.30), M["wood_dark"]), 0.008)
        # 十字底座：两根方木同高会共面（中间 18×18 mm 的小方块一直在闪），y 向那根压 3 mm
        self.add(box(name + "_foot_y", (x, y, z + 0.17), (0.18, 1.26, 0.284), M["wood_dark"]), 0.008)
        self.add(box(name + "_post", (x, y, z + 1.08), (0.17, 0.17, 1.96), M["wood_warm"]), 0.008)
        self.add(box(name + "_arm", (x, y, z + 1.62), (1.48, 0.16, 0.16), M["wood_warm"]), 0.008)
        for sgn in (-1, 1):
            self.add(beam(name + "_strut", (x + sgn * 0.70, y, z + 1.66), (x + sgn * 0.10, y, z + 1.22),
                          0.10, 0.09, M["wood_dark"]), 0.004)
        self.add(box(name + "_body", (x, y + 0.02, z + 0.90), (0.56, 0.42, 0.90), M["roof_wood"]), 0.014)
        for zz in (0.60, 1.20):
            self.add(box(name + "_cord", (x, y + 0.02, z + zz), (0.60, 0.46, 0.08),
                         M["wood_dark"]), 0.004)
        self.add(box(name + "_head", (x, y, z + 1.54), (0.36, 0.34, 0.42), M["roof_wood"]), 0.012)
        self.add(box(name + "_cord_n", (x, y, z + 1.36), (0.32, 0.30, 0.08), M["wood_dark"]), 0.003)

    def weapon_rack(self, name, p):
        """武器架：两立柱 + 三道横杆 + 四支长矛 + 两把剑。"""
        M = self.M
        x, y = p
        z = YARD_Z
        for sgn in (-1, 1):
            self.add(box(name + "_post", (x + sgn * 0.76, y, z + 0.80), (0.16, 0.16, 1.60),
                         M["wood_dark"]), 0.008)
            self.add(box(name + "_foot", (x + sgn * 0.76, y, z + 0.09), (0.30, 0.42, 0.18),
                         M["stone_mid"]), 0.008)
        for zz in (0.50, 1.00, 1.44):
            self.add(box(name + "_rail", (x, y, z + zz), (1.66, 0.13, 0.11), M["wood_dark"]), 0.006)
        for k in range(4):
            ox = -0.52 + k * 0.35
            self.add(beam(name + "_pike", (x + ox, y - 0.10, z + 0.28), (x + ox, y - 0.40, z + 2.50),
                          0.05, 0.05, M["wood_warm"]), 0.003)
            self.add(cone(name + "_tip", (x + ox, y - 0.40, z + 2.50), (x + ox, y - 0.43, z + 2.78),
                          0.07, 4, M["iron"]), 0.0, 1)
        for sgn in (-1, 1):
            self.add(beam(name + "_sword", (x + sgn * 0.60, y - 0.20, z + 0.24),
                          (x + sgn * 0.29, y - 0.28, z + 1.52), 0.09, 0.035, M["iron"]), 0.003)
            self.add(box(name + "_guard", (x + sgn * 0.30, y - 0.28, z + 1.54), (0.32, 0.06, 0.07),
                         M["gold"]), 0.003)
            self.add(box(name + "_grip", (x + sgn * 0.29, y - 0.28, z + 1.64), (0.08, 0.08, 0.17),
                         M["wood_dark"]), 0.003)

    def armor_stand(self, name, p):
        """盔甲架：木架 + 胸甲 + 肩甲 + 头盔 + 腿甲 + 阵营色披风。"""
        M = self.M
        x, y = p
        z = YARD_Z
        self.add(box(name + "_base", (x, y, z + 0.11), (0.92, 0.66, 0.22), M["wood_dark"]), 0.010)
        self.add(box(name + "_post", (x, y - 0.06, z + 1.06), (0.14, 0.14, 1.92), M["wood_dark"]), 0.006)
        self.add(box(name + "_shoulder", (x, y, z + 1.86), (0.88, 0.14, 0.14), M["wood_dark"]), 0.006)
        self.add(taper_box(name + "_chest", (x, y + 0.10, z + 1.50), (x, y + 0.10, z + 1.06),
                           0.60, 0.42, 0.29, 0.23, M["iron"]), 0.012)
        self.add(box(name + "_chest_band", (x, y + 0.10, z + 1.10), (0.44, 0.27, 0.08),
                     M["stone_dark"]), 0.004)
        for sgn in (-1, 1):
            self.add(box(name + "_pauldron", (x + sgn * 0.36, y + 0.06, z + 1.78),
                         (0.29, 0.32, 0.21), M["iron"], rot=(0, sgn * 0.22, 0)), 0.010)
        self.add(revolve(name + "_helm", [(0.0, 0.0), (0.19, 0.05), (0.22, 0.19), (0.16, 0.34),
                                          (0.0, 0.40)], 8, (x, y + 0.04, z + 1.98), M["iron"]), 0.010, 1)
        self.add(box(name + "_visor", (x, y + 0.23, z + 2.09), (0.32, 0.05, 0.09), M["coal"]), 0.003)
        for sgn in (-1, 1):
            self.add(box(name + "_leg", (x + sgn * 0.15, y + 0.06, z + 0.63), (0.19, 0.21, 0.82),
                         M["iron"]), 0.008)
        self.add(box(name + "_cape", (x, y - 0.23, z + 1.36), (0.70, 0.06, 1.06), M["team"]), 0.008)
        self.add(box(name + "_cape_t", (x, y - 0.25, z + 0.82), (0.70, 0.08, 0.10),
                     M["team_trim"]), 0.004)

    def target(self, name, p):
        """圆靶：立柱 + 两根斜撑 + 圆盘 + 同心环 + 靶心。"""
        M = self.M
        x, y = p
        z = YARD_Z
        self.add(box(name + "_post", (x, y, z + 0.84), (0.18, 0.18, 1.68), M["wood_dark"]), 0.008)
        for sgn in (-1, 1):
            self.add(beam(name + "_strut", (x + sgn * 0.60, y + 0.28, z + 0.08),
                          (x, y, z + 1.34), 0.10, 0.09, M["wood_dark"]), 0.004)
        self.add(cyl(name + "_face", (x, y + 0.06, z + 1.42), 0.70, 0.14, 12, M["roof_wood"]), 0.012)
        self.add(tube_band(name + "_ring", (x, y + 0.06), 0.50, 0.58, z + 1.49, z + 1.55, 12,
                           M["team"]), 0.006)
        self.add(tube_band(name + "_ring2", (x, y + 0.06), 0.24, 0.32, z + 1.49, z + 1.55, 12,
                           M["team_trim"]), 0.006)
        self.add(cyl(name + "_bull", (x, y + 0.14, z + 1.42), 0.12, 0.06, 12, M["gold"]), 0.004)
        self.add(box(name + "_band", (x, y + 0.06, z + 1.42), (1.50, 0.10, 0.06), M["iron"]), 0.003)

    def barrel(self, name, p, r, h, z0=0.0):
        M = self.M
        x, y = p
        self.add(lathe(name, [(0.0, z0, x, y), (r * 0.84, z0, x, y), (r, z0 + h * 0.34, x, y),
                              (r, z0 + h * 0.66, x, y), (r * 0.84, z0 + h, x, y),
                              (0.0, z0 + h, x, y)],
                       8, M["wood_warm"]), 0.014, 1)
        for zz in (h * 0.26, h * 0.74):
            self.add(tube_band(name + "_hoop", (x, y), r * 0.97, r * 1.03, z0 + zz, z0 + zz + 0.07,
                               8, M["iron"]), 0.004)
        # 板缝不单独做：lathe 的 12 段本身就有竖棱，再加 4 条 box 只会白涨 100 面

    def crate(self, name, p, w, h, z0=0.0):
        M = self.M
        x, y = p
        self.add(box(name, (x, y, z0 + h * 0.5), (w, w * 0.86, h), M["wood_warm"]), 0.012)
        for k in (-1, 1):
            self.add(box(name + "_band", (x, y, z0 + h * 0.5 + k * h * 0.28),
                         (w + 0.04, w * 0.90, 0.07), M["iron"]), 0.004)
        # 斜撑省掉：0.06 厚的对角条在 RTS 尺度上只有 2 像素，白涨 52 面/个

    # ── 11. 组装 ────────────────────────────────────────────────────────────
    def build(self):
        for step in (self.base, self.paving, self.drill, self.scatter,
                     self.mass, self.parapet, self.tower, self.gatehouse,
                     self.gate, self.timber, self.windows, self.heraldry,
                     self.roofdeck, self.yard):
            step()
        return self

    def finalize(self, bevel=True):
        for (ob, bev, sub, seg) in self.items:
            if self.smooth:
                # 曲面细分版：**先低模定形，再细分**，但只细分体量件。
                # 全部叠一层 Catmull-Clark 会到 30 万面（和"资产不重"冲突）；
                # 体量件（≥0.55 m）2 段倒角 + 1 级 CC 把棱真正磨圆，小件只倒角 ——
                # 远景里看不出差别，面数却只有全量的 1/4。
                # 只给"三个方向都够厚"的体量件上细分：一片围栏板（0.24×0.07×1.15）
                # 也算"最大边 > 0.55"，但它细分出来只是一堆用不上的面。
                co = ob.data.vertices
                dims = [max(v.co[i] for v in co) - min(v.co[i] for v in co) for i in range(3)]
                chunky = min(dims) >= 0.10 and dims[0] * dims[1] * dims[2] >= 0.12
                # 小件 1 段倒角就够（0.1 m 的倒角在 30 m 外只有半个像素）；
                # 体量件 2 段 + 1 级 CC，棱才真的是圆的。
                L.finalize(ob, bevel=max(bev, 0.010), seg=2 if chunky else 1,
                           sub=1 if chunky else 0, flat=False)
            else:
                # 低模只给体量件倒角：< 0.55 m 的件一个 box 从 26 面降到 6 面。
                # 倒角在 RTS 尺度上只有 1–2 像素宽，硬边反而更"低模"。
                co = ob.data.vertices
                # ob.dimensions 要 depsgraph 更新才准（这里还没 update），直接用顶点算
                dim = max(max(v.co[i] for v in co) - min(v.co[i] for v in co) for i in range(3))
                small = dim < 0.55
                b = 0.0 if (not bevel or small or bev < 0.008) else bev
                L.finalize(ob, bevel=b, seg=seg, sub=0, flat=True)
        objs = [it[0] for it in self.items]
        bpy.ops.object.select_all(action="DESELECT")
        for ob in objs:
            ob.select_set(True)
        bpy.context.view_layer.objects.active = objs[0]
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        bpy.ops.object.select_all(action="DESELECT")
        out = L.join_by_material(objs, prefix="BR")
        mirror_x(out)
        if self.unwrap:
            L.smart_uv(out)
        return out


def build(smooth=True, unwrap=True, bevel=True):
    m = Model(smooth, unwrap).build()
    objs = m.finalize(bevel=bevel)
    return objs, L.stats(objs)
