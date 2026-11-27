"""tent_model.py —— 联盟帐篷三级：初级 / 中等 / 豪华

一句话定位
----------
帐篷是"平面布 + 细木杆"的资产，判据与石建筑**相反**：石建筑靠体块与线脚，
帐篷靠**坡面的倾斜角**与**杆的数量**。所以三级的差别不写在尺寸上，写在语法上：

    初级（h 2.30）  6 边阶梯锥 + 1 根中柱 + 1 层布，4 根斜拉绳从锥顶落到地钉
    中等（h 2.95）  两面坡脊帐 + 2 根脊杆 + 2 层布（外层 + 前檐披），6 根地钉
    豪华（h 3.85）  木地台 + 4 根外露角柱 + 四坡顶 + 3 层布（外层 / 内衬 / 门帘）
                    + 门口两根旗杆，8 根地钉

布只用 `canvas`（受光）/ `canvas_dark`（背光 / 内衬 / 拼缝）两档 —— 单档布在平光下
是一块奶油色板，两层叠不出体积。队色只做**一条**横带 + 一条细金线：
深色杆上的窄色条在 96 px 上读成"杆子花了"，不是"这是联盟的帐篷"。

拼缝（seam）是这套资产的关键零件
--------------------------------
一片 3.8 × 2.7 的光板在 38° 俯角下就是一块"硬纸板"。真实的帐篷布是**幅**拼的：
每 0.7–1.1 m 一道缝，缝上有一条 5 cm 的压条。有了压条，同一块平面立刻读成
"被绷起来的布"，而不是"切出来的一块板"（规则 C/E 里"布不能像硬纸板"那一条）。
压条走 `canvas_dark`，只靠明度差，不加第二种材质。

硬规矩（与九座一致）
--------------------
  * 1 unit = 1 m；原点占地中心，z = 0 地面；建模期 +Y 正面（门朝 +Y）。
    `finalize()` 最后沿 X 镜像 → 建模期 +X 在成品里是 −X。
  * 硬边：全部是 box / 平面多边形板，**没有一个回转体**。锥面是 6 片平面四边形，
    阶梯近似圆；布厚一律 ≥ 0.03（0.04），再薄倒角会把它啃穿。
  * 零浮空：杆落到地台面或地面，地钉沉进地面 3 cm，绳端落在钉身内部。

对象名前缀（体检按前缀分组）：tent_ 布 / tc_ 布饰 / pole_ 杆 / rg_ 脊 /
stake_ 地钉 / rope_ 绳 / door_ 门 / deck_ 地台 / flag_ 旗。
"""
import math

import br_model as BR
from bslib import box, beam, mesh_obj
from mathutils import Vector

P_CAN, P_DARK = "canvas", "canvas_dark"
P_TEAM, P_TRIM = "team", "team_trim"
P_WOOD, P_WOODD = "wood_warm", "wood_dark"
P_ROPE, P_IRON = "site_rope", "iron"

# 三级参数表。half_w / half_d 是占地半宽半深，h 是总高（含脊杆 / 锥顶）。
TIERS = {
    "初级帐篷": dict(half_w=1.30, half_d=1.25, h=2.30, poles=1, layers=1,
                  door_w=0.80, door_h=1.30, stakes=4, prefix="TN1",
                  note="6 边锥 + 中柱；4 根斜拉绳从锥顶落到地钉"),
    "中等帐篷": dict(half_w=1.80, half_d=1.65, h=2.95, poles=2, layers=2,
                  door_w=1.04, door_h=1.80, stakes=6, prefix="TN2",
                  note="两面坡脊帐 + 2 根脊杆 + 前檐披；6 根地钉"),
    "豪华帐篷": dict(half_w=2.45, half_d=2.25, h=3.85, poles=4, layers=3,
                  door_w=1.56, door_h=1.92, stakes=8, prefix="TN3",
                  note="木地台 + 4 根角柱 + 四坡顶 + 内衬 + 门帘 + 双旗杆；8 根地钉"),
}


# ── 几何基元（只有平面件，没有回转体）────────────────────────────────────────
def _nrm(pts):
    a, b, c = Vector(pts[0]), Vector(pts[1]), Vector(pts[2])
    n = (b - a).cross(c - a)
    return n.normalized() if n.length > 1e-9 else Vector((0.0, 0.0, 1.0))


def slab(name, pts, thick, inward, mat):
    """平面多边形板（3–6 点）：`pts` 是外表面，沿 inward 方向加厚。

    布的"厚度"必须是实体 —— 一片零厚度的面在 glTF 里没有背面，
    从帐篷内侧看就是一个洞（灯一照就穿）。
    """
    p = [Vector(q) for q in pts]
    n = _nrm(p)
    if n.dot(Vector(inward)) < 0.0:
        n = -n
    m = len(p)
    vs = [tuple(q) for q in p] + [tuple(q + n * thick) for q in p]
    faces = [tuple(range(m)), tuple(range(m, 2 * m))]
    for i in range(m):
        j = (i + 1) % m
        faces.append((i, j, m + j, m + i))
    return mesh_obj(name, vs, faces, mat)


def _bil(A, B, C, D, s, t):
    """四边形双线性取样：s 沿 A→B（下沿），t 由下沿升到上沿（D→C）。"""
    lo = Vector(A).lerp(Vector(B), s)
    hi = Vector(D).lerp(Vector(C), s)
    return lo.lerp(hi, t)


def _off(pts, n, d):
    v = Vector(n)
    return [tuple(Vector(p) + v * d) for p in pts]


class Model(BR.Model):
    """三级共用一个 Model：`tier` 决定走哪套语法（不缩放同一套几何）。"""

    def __init__(self, smooth, unwrap=True, tier="初级帐篷", rope=True):
        BR.Model.__init__(self, smooth, unwrap)
        self.tier = tier
        self.cfg = dict(TIERS[tier])
        # 升级态：旧帐篷的斜拉绳系在锥顶，截断之后会剩一截上端悬空的绳头
        # （体检判 FLOAT）。所以升级态只留地钉、不留绳 —— "绳已经解了、钉还在地上"
        # 本来就是拆到一半的样子。
        self.rope = rope

    # ── 小工具 ──────────────────────────────────────────────────────────────
    def cloth(self, name, pts, inward, thick=0.04, mat=P_CAN):
        """一片布：40 mm 厚、硬边、不倒角（倒角会把薄板啃穿）。"""
        return self.add(slab(name, pts, thick, inward, self.M[mat]), 0.006)

    def sheet(self, name, pts, n, mat, out=0.020, thick=0.022):
        """贴在布面上的饰条（队色带 / 门套）：外表面沿 n 外移 out，厚度朝里。

        `out` 必须真的外移（1–2 cm）：队色带与布同高会共面闪烁；但厚度要朝里
        吃进布里，否则整条带子是"贴纸浮在布前面 1.5 cm"（侧面一眼就看出来）。
        """
        return self.add(slab(name, _off(pts, n, out), thick, (-n[0], -n[1], -n[2]),
                             self.M[mat]), 0.004)

    def seam(self, name, p0, p1, w=0.055, mat=P_DARK, lift=(0.0, 0.0, 0.0)):
        """布面拼缝压条：沿 p0→p1 的一条方料，直径 w。

        压在缝上（一半吃进布、一半凸出来），靠 `canvas_dark` 与布的明度差读出来。
        这是"帐篷布"与"硬纸板"的分界线，三顶帐篷都不能省。
        """
        a = Vector(p0) + Vector(lift)
        b = Vector(p1) + Vector(lift)
        return self.add(beam(name, a, b, w, w * 0.78, self.M[mat]), 0.0)

    def stick(self, name, c, s, mat=P_WOOD, bev=0.008):
        return self.add(box(name, c, s, self.M[mat]), bev)

    def guy(self, tag, anchor, fx, fy):
        """地钉 + 斜拉绳：绳从 anchor 落到钉身（钉顶 0.52，钉身沉地 3 cm）。"""
        self.stick("stake_" + tag, (fx, fy, 0.245), (0.075, 0.075, 0.55), P_WOOD, 0.006)
        self.stick("stake_band_" + tag, (fx, fy, 0.455), (0.086, 0.086, 0.055), P_WOODD, 0.004)
        if self.rope:
            self.add(beam("rope_" + tag, anchor, (fx, fy, 0.44),
                          0.036, 0.036, self.M[P_ROPE]), 0.0)

    def lantern(self, cx, cy, z=0.0):
        """门口内侧的一盏小灯：自发光芯 + 铁座。

        没有它，开着的门洞在阴影里就是一个纯黑方块（分不清"门开着"还是"贴了黑片"）。
        """
        self.stick("door_lamp_base", (cx, cy, z + 0.018), (0.20, 0.20, 0.036), P_IRON, 0.004)
        self.stick("door_lamp", (cx, cy, z + 0.135), (0.145, 0.145, 0.20), "glow", 0.004)

    def floor(self, w, d, z=0.0):
        """帐内衬布地面：走 canvas_dark，从门洞里看是一片压暗的地面。

        尺寸必须**内接**在布占地里：初级是六边形占地，1.55×1.45 的方布四角
        会从布脚穿出去（v1 在门口露出一块棕色方板）。
        """
        self.add(box("tent_floor", (0.0, 0.0, z + 0.015), (w, d, 0.03),
                     self.M[P_DARK]), 0.004)

    def hem(self, name, p0, p1, z0, z1, n, trim=True):
        """竖墙上一段队色带：p0/p1 是墙线的两个 (x, y) 端点，z0–z1 是绝对高度。

        用绝对高度而不是"沿墙面的比例"：山墙是梯形（门边 2.47、墙角 1.48），
        按比例算出来的带子会跟着坡度爬，一条横线变成斜线。
        """
        q = [(p0[0], p0[1], z0), (p1[0], p1[1], z0), (p1[0], p1[1], z1), (p0[0], p0[1], z1)]
        self.sheet(name, q, n, P_TEAM, 0.014, 0.020)
        if trim:
            q2 = [(p0[0], p0[1], z1), (p1[0], p1[1], z1),
                  (p1[0], p1[1], z1 + 0.042), (p0[0], p0[1], z1 + 0.042)]
            self.sheet(name + "_t", q2, n, P_TRIM, 0.014, 0.016)

    # ── 初级：6 边阶梯锥 + 中柱 ─────────────────────────────────────────────
    def _tier1(self, c):
        hw, hd = c["half_w"], c["half_d"]
        z_top, k_top = 2.18, 0.135
        door_w, door_h = c["door_w"], c["door_h"]

        B = [Vector((hw * math.cos(math.radians(60 * k)),
                     hd * math.sin(math.radians(60 * k)), 0.0)) for k in range(6)]
        T = [Vector((p.x * k_top, p.y * k_top, z_top)) for p in B]

        for k in range(6):
            A, Bp = B[k], B[(k + 1) % 6]
            C, D = T[(k + 1) % 6], T[k]
            mid = (A + Bp) * 0.5
            inward = (-mid.x, -mid.y, -0.35)
            n = _nrm([A, Bp, C, D])
            if n.dot(Vector(inward)) < 0.0:
                n = -n
            base_w = (Bp - A).length
            # 六条棱上的拼缝（一半吃进两侧的布，一半凸出来）
            self.seam("tc_seam%d" % k, B[k], T[k], 0.06)
            if k != 1:                                   # 不是正面：一整片
                self.cloth("tent_w%d" % k, [A, Bp, C, D], inward)
                self._cone_hem("tc_hem%d" % k, [A, Bp, C, D], n, 0.0, 1.0, z_top)
                self.stick("rg_foot%d" % k, (mid.x, mid.y, 0.030),
                           (abs(Bp.x - A.x) + 0.05, abs(Bp.y - A.y) + 0.05, 0.06),
                           P_WOODD, 0.004)
                continue
            # 正面：左右两片 + 上方一片，中间是**真开**的门洞
            dw = door_w * 0.5
            ds = dw / base_w
            s0, s1 = 0.5 - ds, 0.5 + ds
            t0 = door_h / z_top
            q = lambda a, b: _bil(A, Bp, C, D, a, b)
            self.cloth("tent_door_l", [q(0, 0), q(s0, 0), q(s0, 1), q(0, 1)], inward)
            self.cloth("tent_door_r", [q(s1, 0), q(1, 0), q(1, 1), q(s1, 1)], inward)
            self.cloth("tent_door_top", [q(s0, t0), q(s1, t0), q(s1, 1), q(s0, 1)], inward)
            self._cone_hem("tc_hem_l", [q(0, 0), q(s0, 0), q(s0, 1), q(0, 1)], n, 0.0, 1.0, z_top)
            self._cone_hem("tc_hem_r", [q(s1, 0), q(1, 0), q(1, 1), q(s1, 1)], n, 0.0, 1.0, z_top)
            # 门套：两竖 + 一横，压在布的边缘上（布厚 40、门套凸 14）
            self.sheet("door_jamb_l", [q(s0 - 0.045, 0), q(s0 + 0.030, 0),
                                       q(s0 + 0.030, t0), q(s0 - 0.045, t0)],
                       n, P_DARK, 0.014, 0.026)
            self.sheet("door_jamb_r", [q(s1 - 0.030, 0), q(s1 + 0.045, 0),
                                       q(s1 + 0.045, t0), q(s1 - 0.030, t0)],
                       n, P_DARK, 0.014, 0.026)
            self.sheet("door_head", [q(s0 - 0.045, t0 - 0.030), q(s1 + 0.045, t0 - 0.030),
                                     q(s1 + 0.045, t0 + 0.030), q(s0 - 0.045, t0 + 0.030)],
                       n, P_DARK, 0.014, 0.026)
            # 卷起的门帘：横在门洞上沿（帆布卷 + 一道束绳）
            e0, e1 = q(s0, t0), q(s1, t0)
            mx, my, mz = (e0.x + e1.x) * 0.5, (e0.y + e1.y) * 0.5, (e0.z + e1.z) * 0.5
            self.stick("door_roll", (mx, my - 0.07, mz + 0.05),
                       (abs(e1.x - e0.x) + 0.10, 0.135, 0.135), P_DARK, 0.010)
            self.stick("door_roll_tie", (mx, my - 0.14, mz + 0.05),
                       (0.075, 0.030, 0.150), P_ROPE, 0.002)
            # 门口的压布木：只压在两侧布脚上，不横穿门洞
            for sgn in (-1, 1):
                self.stick("rg_foot_d%d" % sgn,
                           (sgn * (dw + (base_w * 0.5 - dw) * 0.5), A.y, 0.030),
                           (base_w * 0.5 - dw - 0.02, 0.09, 0.06), P_WOODD, 0.004)

        # 锥顶：封口布（盖住顶环，不留空心）+ 中柱柱头
        lid = [Vector((p.x * 1.04, p.y * 1.04, z_top)) for p in T]
        self.add(slab("rg_lid", lid, 0.048, (0, 0, -1), self.M[P_DARK]), 0.006)
        self.stick("pole_center", (0.0, 0.0, 1.15), (0.11, 0.11, 2.30), P_WOOD, 0.010)
        self.stick("pole_center_cap", (0.0, 0.0, 2.250), (0.155, 0.155, 0.055), P_WOODD, 0.004)

        self.floor(1.02, 0.96)
        self.lantern(0.0, 0.62, 0.03)
        self.stick("door_mat", (0.0, hd + 0.21, 0.011), (0.92, 0.54, 0.022), P_DARK, 0.003)
        # 4 根斜拉绳：从锥顶拉到四角地钉。
        # 贴着地拉一圈细绳在 RTS 尺度上是噪点；从高处拉下来的斜线才读成"帐篷绷住了"。
        for i, (sx, sy) in enumerate(((1, 1), (-1, 1), (-1, -1), (1, -1))):
            self.guy("s%d" % i, (sx * 0.145, sy * 0.145, 2.135), sx * 1.74, sy * 1.52)

    def _cone_hem(self, name, quad, n, s0, s1, z_top):
        """锥面上的一圈队色带：离地 0.195–0.372（配一条金线）。

        高度刻意压在"裙摆"这一档：38° 俯角看过去仍是一条横线，
        再高就爬到坡面中央、跟着锥面斜掉了。
        """
        A, Bp, C, D = quad
        f = lambda s, z: _bil(A, Bp, C, D, s, z / z_top)
        self.sheet(name, [f(s0, 0.195), f(s1, 0.195), f(s1, 0.330), f(s0, 0.330)],
                   n, P_TEAM, 0.014, 0.020)
        self.sheet(name + "_t", [f(s0, 0.330), f(s1, 0.330), f(s1, 0.372), f(s0, 0.372)],
                   n, P_TRIM, 0.014, 0.016)

    # ── 中等：两面坡脊帐 + 前檐披 ──────────────────────────────────────────
    def _tier2(self, c):
        hw, hd = c["half_w"], c["half_d"]
        z_r, z_e = 2.84, 1.58              # 布上表面：脊 / 檐墙顶（墙 1.6 m、坡 35°）
        slope = (z_r - z_e) / hw
        ov_x, ov_y = 1.92, 1.78            # 屋面挑出：檐口 0.12、山墙 0.13
        door_w, door_h = c["door_w"], c["door_h"]
        dw = door_w * 0.5
        z_ev = z_r - slope * ov_x          # 檐口标高

        # ① 两片坡（下表面定在脊线/檐线上，厚度朝上）+ 每 0.72 m 一道拼缝
        for sgn in (-1, 1):
            A = (0.0, -ov_y, z_r)
            Bp = (0.0, ov_y, z_r)
            Cc = (sgn * ov_x, ov_y, z_ev)
            D = (sgn * ov_x, -ov_y, z_ev)
            self.cloth("tent_roof%d" % sgn, [A, Bp, Cc, D], (0, 0, 1), 0.05)
            # 檐口立面：布边只有 5 cm 厚，远看会消失，补一条 5 cm 的暗边收头
            self.sheet("tc_eave%d" % sgn,
                       [Cc, D, (D[0], D[1], D[2] - 0.052), (Cc[0], Cc[1], Cc[2] - 0.052)],
                       (sgn * 0.7, 0, 0.7), P_DARK, 0.0, 0.030)
            for i, yy in enumerate((-1.45, -0.72, 0.0, 0.72, 1.45)):
                self.seam("tc_rseam%d_%d" % (sgn, i), (0.0, yy, z_r),
                          (sgn * ov_x, yy, z_ev), 0.05, lift=(0, 0, 0.050))
        # ② 侧面竖墙（顶边塞进屋面 3 cm，檐下不留缝）+ 两道竖缝
        for sgn in (-1, 1):
            q = [(sgn * hw, -hd, 0.0), (sgn * hw, hd, 0.0),
                 (sgn * hw, hd, z_e + 0.03), (sgn * hw, -hd, z_e + 0.03)]
            self.cloth("tent_side%d" % sgn, q, (-sgn, 0, 0))
            self.hem("tc_hem_s%d" % sgn, (sgn * hw, -hd), (sgn * hw, hd),
                     0.195, 0.400, (sgn, 0, 0))
            for i, yy in enumerate((-0.55, 0.55)):
                self.seam("tc_wseam%d_%d" % (sgn, i), (sgn * hw, yy, 0.0),
                          (sgn * hw, yy, z_e + 0.02), 0.05, lift=(sgn * 0.022, 0, 0))
        # ③ 前 / 后山墙：前墙按门洞拆三片
        zl = lambda x: z_r + 0.03 - slope * abs(x)
        yf, yb = hd, -hd
        self.cloth("tent_gable_b",
                   [(-hw, yb, 0.0), (hw, yb, 0.0), (hw, yb, zl(hw)),
                    (0.0, yb, zl(0)), (-hw, yb, zl(hw))], (0, 1, 0))
        self.cloth("tent_gable_l",
                   [(-hw, yf, 0.0), (-dw, yf, 0.0), (-dw, yf, zl(dw)), (-hw, yf, zl(hw))],
                   (0, -1, 0))
        self.cloth("tent_gable_r",
                   [(dw, yf, 0.0), (hw, yf, 0.0), (hw, yf, zl(hw)), (dw, yf, zl(dw))],
                   (0, -1, 0))
        self.cloth("tent_gable_t",
                   [(-dw, yf, door_h), (dw, yf, door_h), (dw, yf, zl(dw)),
                    (0.0, yf, zl(0)), (-dw, yf, zl(dw))], (0, -1, 0))
        # 腰线：四面墙一圈，门洞两侧断开（不横穿门）
        self.hem("tc_hem_fl", (-hw + 0.02, yf), (-dw - 0.02, yf), 0.195, 0.400, (0, 1, 0))
        self.hem("tc_hem_fr", (dw + 0.02, yf), (hw - 0.02, yf), 0.195, 0.400, (0, 1, 0))
        self.hem("tc_hem_b", (-hw + 0.02, yb), (hw - 0.02, yb), 0.195, 0.400, (0, -1, 0))
        # 门套（两竖 + 门楣）+ 卷起的门帘
        for sgn in (-1, 1):
            self.sheet("door_jamb%d" % sgn,
                       [(sgn * dw - 0.05, yf, 0.0), (sgn * dw + 0.05, yf, 0.0),
                        (sgn * dw + 0.05, yf, door_h + 0.045),
                        (sgn * dw - 0.05, yf, door_h + 0.045)],
                       (0, 1, 0), P_DARK, 0.016, 0.028)
        self.sheet("door_head", [(-dw - 0.05, yf, door_h - 0.045), (dw + 0.05, yf, door_h - 0.045),
                                 (dw + 0.05, yf, door_h + 0.045), (-dw - 0.05, yf, door_h + 0.045)],
                   (0, 1, 0), P_DARK, 0.016, 0.028)
        self.stick("door_roll", (0.0, yf + 0.085, door_h + 0.10),
                   (door_w + 0.14, 0.135, 0.135), P_DARK, 0.010)
        self.stick("door_roll_tie", (0.0, yf + 0.165, door_h + 0.10),
                   (0.075, 0.030, 0.150), P_ROPE, 0.002)
        # ④ 前檐披（第二层布）：从山墙 2.12 斜挑出去 1.05 m，两根前柱撑着
        aw = [(-1.00, yf - 0.08, 2.12), (1.00, yf - 0.08, 2.12),
              (1.10, 2.62, 1.74), (-1.10, 2.62, 1.74)]
        self.cloth("tent_awning", aw, (0, 0, 1), 0.042)
        # 檐披上沿的挂杆：钉在山墙外侧，檐披是"挂在杆上"而不是"悬在门前"
        self.stick("pole_awbar", (0.0, yf + 0.035, 2.058), (2.20, 0.075, 0.070), P_WOODD, 0.006)
        for sgn in (-1, 1):
            self.stick("pole_awring%d" % sgn, (sgn * 1.02, yf + 0.035, 2.050),
                       (0.09, 0.09, 0.10), P_IRON, 0.003)
        for i, xx in enumerate((-0.55, 0.55)):
            self.seam("tc_aseam%d" % i, (xx, yf - 0.08, 2.12), (xx * 1.10, 2.62, 1.74),
                      0.048, lift=(0, 0, 0.048))
        for sgn in (-1, 1):
            self.stick("pole_aw%d" % sgn, (sgn * 0.95, 2.48, 0.89),
                       (0.075, 0.075, 1.78), P_WOOD, 0.008)
        # 檐披前缘的队色垂布（全帐最醒目的那条横线）+ 一条金线
        self.sheet("tc_band_f", [(-1.10, 2.62, 1.560), (1.10, 2.62, 1.560),
                                 (1.10, 2.62, 1.740), (-1.10, 2.62, 1.740)],
                   (0, 1, 0), P_TEAM, 0.012, 0.026)
        self.sheet("tc_band_ft", [(-1.10, 2.62, 1.516), (1.10, 2.62, 1.516),
                                  (1.10, 2.62, 1.562), (-1.10, 2.62, 1.562)],
                   (0, 1, 0), P_TRIM, 0.012, 0.020)
        # ⑤ 脊：两根脊杆（帐内）+ 一根压脊木（绑在布上，剪影里的那条线）
        for i, yy in enumerate((-1.15, 1.15)):
            self.stick("pole_ridge%d" % i, (0.0, yy, 1.42), (0.115, 0.115, 2.84), P_WOOD, 0.008)
        self.stick("rg_beam", (0.0, 0.04, 2.915), (0.115, 3.60, 0.075), P_WOODD, 0.006)
        for i, yy in enumerate((-1.28, 1.28)):
            self.stick("rg_lash%d" % i, (0.0, yy, 2.905), (0.170, 0.075, 0.115), P_ROPE, 0.003)

        self.floor(2.30, 2.15)
        self.lantern(0.0, 1.05, 0.03)
        self.stick("door_mat", (0.0, hd + 0.19, 0.011), (1.28, 0.52, 0.022), P_DARK, 0.003)
        # 6 根地钉 + 斜拉绳（檐口 → 地钉）
        for i, (sx, yy) in enumerate(((1, 1.42), (-1, 1.42), (1, 0.0),
                                      (-1, 0.0), (1, -1.42), (-1, -1.42))):
            self.guy("s%d" % i, (sx * ov_x, yy, z_ev + 0.02),
                     sx * 2.34, yy * 1.24 if yy else 0.0)

    # ── 豪华：地台 + 四角柱 + 四坡顶 + 三层布 ──────────────────────────────
    def _tier3(self, c):
        hw, hd = c["half_w"], c["half_d"]
        door_w, door_h = c["door_w"], c["door_h"]
        dw = door_w * 0.5
        z_deck = 0.18
        z_e, z_r = 2.46, 3.72              # 屋面下表面：檐口 / 短脊
        zt = 2.48                          # 布墙顶（塞进屋面 2 cm）
        px, py = hw + 0.07, hd + 0.07      # 角柱中心（在布外面 → "4 根柱"数得出来）

        # ① 木地台：底板 + 8 条板条（条间 6 cm 缝，缝里露出底板 = 真缝）
        self.stick("deck_base", (0.0, 0.0, 0.070), (hw * 2 + 0.20, hd * 2 + 0.20, 0.14),
                   "wood_mid", 0.010)
        n_pl, gap = 8, 0.06
        w_pl = ((hd * 2 + 0.20) - gap * (n_pl - 1)) / n_pl
        for i in range(n_pl):
            yy = -(hd + 0.10) + w_pl * 0.5 + i * (w_pl + gap)
            self.stick("deck_plank%d" % i, (0.0, yy, 0.160),
                       (hw * 2 + 0.20, w_pl, 0.04), P_WOOD, 0.006)
        # ② 四根角柱 + 檐圈梁（柱顶 = 檐口标高，正好托住四坡顶的四个角）
        for i, (sx, sy) in enumerate(((1, 1), (-1, 1), (-1, -1), (1, -1))):
            self.stick("pole_corner%d" % i, (sx * px, sy * py, 1.310),
                       (0.16, 0.16, 2.30), P_WOOD, 0.010)
        for i, sy in enumerate((-1, 1)):
            self.stick("pole_eave_y%d" % i, (0.0, sy * py, 2.410),
                       (px * 2 + 0.16, 0.095, 0.105), P_WOODD, 0.006)
        for i, sx in enumerate((-1, 1)):
            self.stick("pole_eave_x%d" % i, (sx * px, 0.0, 2.410),
                       (0.095, py * 2 + 0.16, 0.105), P_WOODD, 0.006)
        # ③ 外层布：三面竖墙 + 前面拆三片（左右 + 门楣上片）
        for sgn in (-1, 1):
            self.cloth("tent_side%d" % sgn,
                       [(sgn * hw, -hd, z_deck - 0.02), (sgn * hw, hd, z_deck - 0.02),
                        (sgn * hw, hd, zt), (sgn * hw, -hd, zt)], (-sgn, 0, 0))
            for i, yy in enumerate((-0.70, 0.70)):
                self.seam("tc_wseam%d_%d" % (sgn, i), (sgn * hw, yy, z_deck),
                          (sgn * hw, yy, zt), 0.05, lift=(sgn * 0.022, 0, 0))
        self.cloth("tent_back", [(-hw, -hd, z_deck - 0.02), (hw, -hd, z_deck - 0.02),
                                 (hw, -hd, zt), (-hw, -hd, zt)], (0, 1, 0))
        self.cloth("tent_front_l", [(-hw, hd, z_deck - 0.02), (-dw, hd, z_deck - 0.02),
                                    (-dw, hd, zt), (-hw, hd, zt)], (0, -1, 0))
        self.cloth("tent_front_r", [(dw, hd, z_deck - 0.02), (hw, hd, z_deck - 0.02),
                                    (hw, hd, zt), (dw, hd, zt)], (0, -1, 0))
        self.cloth("tent_front_t", [(-dw, hd, door_h), (dw, hd, door_h),
                                    (dw, hd, zt), (-dw, hd, zt)], (0, -1, 0))
        # ④ 四坡顶：檐口压着四根角柱，收到一段 1.1 m 的短脊
        ry = 0.55
        qd = dict(
            f=[(-hw, hd, z_e), (hw, hd, z_e), (ry, ry, z_r), (-ry, ry, z_r)],
            b=[(hw, -hd, z_e), (-hw, -hd, z_e), (-ry, -ry, z_r), (ry, -ry, z_r)],
            r=[(hw, -hd, z_e), (hw, hd, z_e), (0.0, ry, z_r), (0.0, -ry, z_r)],
            l=[(-hw, hd, z_e), (-hw, -hd, z_e), (0.0, -ry, z_r), (0.0, ry, z_r)])
        for nm in ("f", "b", "r", "l"):
            self.cloth("tent_roof_" + nm, qd[nm], (0, 0, 1), 0.05)
            # 每面三道下坡拼缝（沿"檐边 → 短脊"的双线性参数）
            A, Bp, Cc, D = [Vector(p) for p in qd[nm]]
            for i, s in enumerate((0.25, 0.50, 0.75)):
                self.seam("tc_rseam_%s%d" % (nm, i), A.lerp(Bp, s), D.lerp(Cc, s),
                          0.05, lift=(0, 0, 0.054))
        # 四条戗脊（两个坡面相接的那条线，压条一上就"立"起来了）
        for i, (sx, sy) in enumerate(((1, 1), (-1, 1), (-1, -1), (1, -1))):
            self.seam("tc_hip%d" % i, (sx * hw, sy * hd, z_e + 0.02),
                      (0.0, sy * ry, z_r + 0.02), 0.065, lift=(0, 0, 0.012))
        # 压脊木：绑在短脊上（这一条是剪影最上面的那条线，总高 3.85）
        self.stick("rg_beam", (0.0, 0.0, 3.805), (0.135, 1.34, 0.09), P_WOODD, 0.006)
        for i, yy in enumerate((-0.50, 0.50)):
            self.stick("rg_lash%d" % i, (0.0, yy, 3.795), (0.185, 0.08, 0.125), P_ROPE, 0.003)
        # ⑤ 内衬（第二层布）：后墙 + 两侧。门洞里看进去是压暗的第二层，
        #    没有它，"开着的门"和"一块黑片"就分不开。
        self.cloth("tent_lin_b", [(-hw + 0.10, -hd + 0.07, z_deck), (hw - 0.10, -hd + 0.07, z_deck),
                                  (hw - 0.10, -hd + 0.07, 2.40), (-hw + 0.10, -hd + 0.07, 2.40)],
                   (0, 1, 0), 0.03, P_DARK)
        for sgn in (-1, 1):
            self.cloth("tent_lin%d" % sgn,
                       [(sgn * (hw - 0.07), -hd + 0.10, z_deck), (sgn * (hw - 0.07), hd - 0.10, z_deck),
                        (sgn * (hw - 0.07), hd - 0.10, 2.40), (sgn * (hw - 0.07), -hd + 0.10, 2.40)],
                       (-sgn, 0, 0), 0.03, P_DARK)
        # ⑥ 第三层布：门帘两片（掀到两侧、用绳束住）
        for sgn in (-1, 1):
            self.cloth("tent_curtain%d" % sgn,
                       [(sgn * dw, hd - 0.03, 0.20), (sgn * (dw - 0.34), hd - 0.26, 0.20),
                        (sgn * (dw - 0.34), hd - 0.26, 2.02), (sgn * dw, hd - 0.03, 2.02)],
                       (-sgn, 1, 0), 0.032, P_DARK)
            self.seam("tc_curseam%d" % sgn, (sgn * (dw - 0.17), hd - 0.145, 0.20),
                      (sgn * (dw - 0.17), hd - 0.145, 2.02), 0.045)
            self.stick("tc_tie%d" % sgn, (sgn * (dw - 0.17), hd - 0.155, 1.22),
                       (0.30, 0.075, 0.075), P_ROPE, 0.003)
        # 门套 + 门楣横带（队色横线 ①，压在门楣上片、避开门上方那道檐梁）
        for sgn in (-1, 1):
            self.sheet("door_jamb%d" % sgn,
                       [(sgn * dw - 0.05, hd, z_deck - 0.02), (sgn * dw + 0.05, hd, z_deck - 0.02),
                        (sgn * dw + 0.05, hd, door_h + 0.03), (sgn * dw - 0.05, hd, door_h + 0.03)],
                       (0, 1, 0), P_DARK, 0.016, 0.030)
        self.sheet("tc_band_f", [(-hw, hd, 1.98), (hw, hd, 1.98), (hw, hd, 2.18), (-hw, hd, 2.18)],
                   (0, 1, 0), P_TEAM, 0.014, 0.024)
        self.sheet("tc_band_ft", [(-hw, hd, 1.936), (hw, hd, 1.936),
                                  (hw, hd, 1.982), (-hw, hd, 1.982)],
                   (0, 1, 0), P_TRIM, 0.014, 0.020)
        # 墙脚一圈腰线（与门楣带相距 1.5 m 的空暗部，不是"包装带"）
        self.hem("tc_hem_fl", (-hw + 0.02, hd), (-dw - 0.02, hd), 0.32, 0.62, (0, 1, 0))
        self.hem("tc_hem_fr", (dw + 0.02, hd), (hw - 0.02, hd), 0.32, 0.62, (0, 1, 0))
        self.hem("tc_hem_b", (-hw + 0.02, -hd), (hw - 0.02, -hd), 0.32, 0.62, (0, -1, 0))
        for sgn in (-1, 1):
            self.hem("tc_hem_s%d" % sgn, (sgn * hw, -hd + 0.02), (sgn * hw, hd - 0.02),
                     0.32, 0.62, (sgn, 0, 0))
        # ⑦ 门口两根旗杆（在布外面，柱脚踩在地台上）
        for sgn in (-1, 1):
            self.stick("flag_pole%d" % sgn, (sgn * 1.34, hd + 0.04, 1.83),
                       (0.075, 0.075, 3.34), P_WOODD, 0.008)
            self.stick("flag_arm%d" % sgn, (sgn * 1.53, hd + 0.04, 3.455),
                       (0.42, 0.05, 0.05), P_WOODD, 0.003)
            self.cloth("flag_pen%d" % sgn,
                       [(sgn * 1.35, hd + 0.04, 3.43), (sgn * 1.35, hd + 0.04, 2.93),
                        (sgn * 1.72, hd + 0.04, 3.00), (sgn * 1.70, hd + 0.04, 3.43)],
                       (0, -1, 0), 0.026, P_TEAM)

        self.floor(4.50, 4.10, z_deck)
        self.lantern(0.0, 1.45, z_deck)
        self.stick("door_mat", (0.0, hd + 0.26, 0.011), (1.50, 0.60, 0.022), P_DARK, 0.003)
        # ⑧ 8 根地钉：四角 + 两侧各两根（正面中间不立钉 —— 绳会横穿门洞）
        feet = [(3.02, 2.82), (-3.02, 2.82), (-3.02, -2.82), (3.02, -2.82),
                (3.22, 1.20), (-3.22, 1.20), (3.22, -1.20), (-3.22, -1.20)]
        for i, (fx, fy) in enumerate(feet[:c["stakes"]]):
            ax = max(-hw, min(hw, fx * 0.80))
            ay = max(-hd, min(hd, fy * 0.86))
            self.guy("s%d" % i, (ax, ay, z_e + 0.03), fx, fy)

    # ── 组装 ────────────────────────────────────────────────────────────────
    def build(self):
        t = self.tier
        if t == "初级帐篷":
            self._tier1(self.cfg)
        elif t == "中等帐篷":
            self._tier2(self.cfg)
        elif t == "豪华帐篷":
            self._tier3(self.cfg)
        else:
            raise KeyError("未知等级：%s" % t)
        return self


def build_tier(name, smooth=False):
    """按等级名搭一顶帐篷，返回**已经 build 完**的 Model。"""
    return Model(smooth, unwrap=False, tier=name).build()
