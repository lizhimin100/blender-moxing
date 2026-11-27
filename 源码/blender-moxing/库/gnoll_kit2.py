"""gnoll_kit2.py —— 豺狼人（精模 / 硬边支线）**参数化组件库**

萨满、战士、斥候共用同一套解剖：长吻大耳、鬃冠、驼背、反关节腿、三趾爪、粗尾。
区别只在 `Gnoll` 里的一张尺寸表 + 材质表 + 头部剖面表 —— 换一组数就是另一只豺狼人，
而不是另一套代码。

用法（unit_xxx.py）：

    import gnoll_kit2 as GK
    S = GK.Gnoll(
        HIP=Vector((0.235, -0.020, 1.100)), ...,
        SKULL=[(-0.076, 1.90, 0.20, 0.21), ...],
        MATS={...}, M=dict(skin="皮肤", dark="皮肤暗", hi="皮肤亮", ...))
    S.setup()
    u = unitkit2.Unit2(PREFIX, S.MATS, low=low)
    GK.legs(u, S); GK.pelvis(u, S); GK.torso(u, S); GK.neck(u, S)
    GK.arms(u, S); GK.head(u, S); GK.tail(u, S)
    BONES = GK.bones(S, extra=[...])

口径（和萨满一致，不许改）：
  * 1 unit = 1 m；+Y 正面；+X 是角色右侧；脚底 z=0；原点在双足中间。
  * 一块 = 一根骨、权重 1.0；关节留缝，缝里是暗档内胆。
  * 皮肤三档（暗 < 中 < 亮）是这套资产的基本功，**不许只用一档**。
  * 笔触：皮肤体积 `chunk`，骨甲 `chunk2`，内胆 `facet`，刃 `sharp`；`soft` 只在必须真圆的件上。
"""
import math

from mathutils import Vector

import unitkit as KU
import unitkit2 as K


# ══ 小件 ════════════════════════════════════════════════════════════════════
def disc(name, center, normal, r, thick, n=10):
    c = Vector(center)
    ez = Vector(normal).normalized()
    up = Vector((0, 0, 1))
    if abs(ez.dot(up)) > 0.95:
        up = Vector((0, 1, 0))
    ex = up.cross(ez).normalized()
    ey = ez.cross(ex).normalized()
    rows = []
    for (o, rr) in ((-thick * 0.5, r * 0.82), (-thick * 0.5 + 0.006, r),
                    (thick * 0.5 - 0.006, r), (thick * 0.5, r * 0.82)):
        rows.append([tuple(c + ez * o + ex * (rr * math.cos(math.tau * k / n))
                           + ey * (rr * math.sin(math.tau * k / n))) for k in range(n)])
    return K.loft(name, rows, True)


def ring(name, center, normal, r_in, r_out, thick, n=8):
    c = Vector(center)
    ez = Vector(normal).normalized()
    up = Vector((0, 0, 1))
    if abs(ez.dot(up)) > 0.95:
        up = Vector((0, 1, 0))
    ex = up.cross(ez).normalized()
    ey = ez.cross(ex).normalized()
    rows = []
    for (o, rr) in ((-thick * 0.5, r_in), (-thick * 0.5, r_out),
                    (thick * 0.5, r_out), (thick * 0.5, r_in)):
        rows.append([tuple(c + ez * o + ex * (rr * math.cos(math.tau * k / n))
                           + ey * (rr * math.sin(math.tau * k / n))) for k in range(n)])
    verts = [p for r in rows for p in r]
    faces = []
    for i in range(4):
        j = (i + 1) % 4
        for k in range(n):
            k2 = (k + 1) % n
            faces.append((i * n + k, i * n + k2, j * n + k2, j * n + k))
    return KU._obj(name, verts, faces)


def octa(name, c, r, h=None, n=6):
    h = r if h is None else h
    c = Vector(c)
    ring_pts = [(c.x + r * math.cos(math.tau * k / n), c.y + r * math.sin(math.tau * k / n), c.z)
                for k in range(n)]
    verts = [tuple(c + Vector((0, 0, h)))] + ring_pts + [tuple(c - Vector((0, 0, h)))]
    faces = []
    for k in range(n):
        k2 = (k + 1) % n
        faces.append((0, 1 + k, 1 + k2))
        faces.append((n + 1, 1 + k2, 1 + k))
    return KU._obj(name, verts, faces)


def fin(name, y0, z0, y1, z1, w, t, bend=0.0):
    """鬃冠薄片：底边沿 Y 宽 w、沿 X 厚 t，往上收成一条窄脊。"""
    rows = []
    for (u, yy, zz, ww, tt) in ((0.0, y0, z0, w, t),
                                (0.55, y0 + (y1 - y0) * 0.52 + bend * 0.5,
                                 z0 + (z1 - z0) * 0.62, w * 0.66, t * 0.72),
                                (1.0, y1, z1, w * 0.10, t * 0.26)):
        rows.append([(tt * 0.5, yy - ww * 0.5, zz), (tt * 0.5, yy + ww * 0.5, zz),
                     (-tt * 0.5, yy + ww * 0.5, zz), (-tt * 0.5, yy - ww * 0.5, zz)])
    return K.loft(name, rows, True)


def ear_plate(name, root, tip, w0, w1, t0, t1):
    """大三角耳：沿耳轴的 3 站放样（根宽 → 中宽 → 尖），扁平、尖端锋利。"""
    p0, ex, ey, ez = KU.frame(root, tip, up=(0, 1, 0))
    L = (Vector(tip) - p0).length
    rows = []
    for (u, ww, tt) in ((0.0, w0, t0), (0.42, w1, t1 * 1.05), (1.0, w1 * 0.06, t1 * 0.22)):
        c = p0 + ez * (L * u)
        rows.append([tuple(c + ex * (ww * 0.5) + ey * (tt * 0.5)),
                     tuple(c + ex * (ww * 0.5) - ey * (tt * 0.5)),
                     tuple(c - ex * (ww * 0.5) - ey * (tt * 0.5)),
                     tuple(c - ex * (ww * 0.5) + ey * (tt * 0.5))])
    return K.loft(name, rows, True)


def boss(name, c, w, h, t, n=6):
    """朝 +Z 的扁平骨片（额骨 / 护符）。"""
    c = Vector(c)
    rows = []
    for (o, k) in ((-0.004, 0.90), (t, 1.0)):
        rows.append([(c.x + w * 0.5 * k * math.cos(math.tau * i / n),
                      c.y + h * 0.5 * k * math.sin(math.tau * i / n),
                      c.z + o) for i in range(n)])
    return K.loft(name, rows, True)


def shrink(ob, c, k):
    C = Vector(c)
    for v in ob.data.vertices:
        v.co = C + (v.co - C) * k
    return ob


def lerp(a, b, t):
    return Vector(a).lerp(Vector(b), t)


def mir(v):
    return Vector((-v[0], v[1], v[2]))


# ══ 尺寸表 ══════════════════════════════════════════════════════════════════
class Gnoll:
    LEG_K = 1.0
    """一只豺狼人的全部尺寸 + 材质。默认值 = 萨满（1.95 m 蓝皮）。

    关节都按**右侧**给，左侧自动镜像。
    """

    NAME = "gnoll"
    PREFIX = "gn"

    # ── 关节点（右侧）────────────────────────────────────────────────────
    HIP = Vector((0.200, -0.020, 1.020))
    KNE = Vector((0.216, 0.170, 0.700))
    HCK = Vector((0.196, -0.145, 0.330))
    BAL = Vector((0.192, -0.130, 0.100))
    TOE = Vector((0.192, 0.190, 0.018))
    HEEL = Vector((0.190, -0.228, 0.000))
    TOE_Y = (-0.082, 0.020, 0.132)

    Z_WAIST = 1.120
    Z_CH0 = 1.270
    Z_NECK = 1.545
    Z_HEAD = 1.628
    SH = Vector((0.280, -0.010, 1.575))

    L_UPPER = 0.365
    L_FORE = 0.300

    # 腕与手的方向（由各 unit 按"手里拿什么"给定）
    POLE_R = (0.40, -0.60, -1.00)
    POLE_L = (-1.00, -0.30, 0.15)
    WRI_R = Vector((0.329, 0.252, 1.216))
    WRI_L = Vector((-0.388, 0.140, 0.972))
    HDIR_R = Vector((0.11, 0.58, -0.80))
    HDIR_L = Vector((0.0, 0.28, -0.96))

    TAIL0 = Vector((0.0, -0.168, 1.000))
    TAIL1 = Vector((0.046, -0.420, 0.902))
    TAIL2 = Vector((0.104, -0.722, 0.736))
    TAIL_R = (0.060, 0.045, 0.030)

    # ── 躯干剖面（z, cy, w, d, 切角）────────────────────────────────────
    CHEST = [(1.258, 0.014, 0.412, 0.322, 0.070),
             (1.330, 0.006, 0.494, 0.386, 0.084),
             (1.412, -0.006, 0.548, 0.430, 0.094),
             (1.492, -0.018, 0.562, 0.442, 0.098),
             (1.558, -0.036, 0.526, 0.414, 0.092),
             (1.624, -0.062, 0.442, 0.352, 0.080),
             (1.674, -0.082, 0.352, 0.284, 0.064),
             (1.700, -0.090, 0.286, 0.226, 0.052)]
    Z_ABD0 = 1.105
    ABD_W = 0.396
    HUMP = True

    # ── 头（y, zc, w, h）─────────────────────────────────────────────────
    SKULL = [(-0.076, 1.834, 0.186, 0.196),
             (-0.012, 1.822, 0.236, 0.256),
             (0.070, 1.812, 0.246, 0.256),
             (0.140, 1.796, 0.234, 0.240),
             (0.200, 1.780, 0.212, 0.206),
             (0.256, 1.762, 0.186, 0.176),
             (0.330, 1.744, 0.170, 0.156),
             (0.400, 1.734, 0.150, 0.136),
             (0.452, 1.728, 0.118, 0.108)]
    JAW = [(0.200, 1.690, 0.180, 0.074),
           (0.284, 1.678, 0.164, 0.066),
           (0.360, 1.670, 0.142, 0.054),
           (0.418, 1.666, 0.104, 0.042)]
    MUZZLE = ((0.180, 1.880, 0.158), (0.270, 1.848, 0.150),
              (0.360, 1.812, 0.132), (0.446, 1.766, 0.104))
    NOSE = ((0.398, 0.052, 0.020, 1.788), (0.418, 0.062, 0.026, 1.790),
            (0.438, 0.054, 0.020, 1.782))
    MOUTH = (0.076, 0.344, 1.706, 0.180, 0.009)
    FANG_U = (Vector((0.080, 0.372, 1.712)), Vector((0.004, 0.004, -0.044)), 0.032, 0.028)
    FANG_L = (Vector((0.072, 0.356, 1.696)), Vector((0.002, 0.002, 0.040)), 0.030, 0.026)
    EYE = (0.070, 0.298, 1.828, 0.040, 0.022, 0.026)
    SOCKET = (0.068, 0.280, 1.826, 0.062, 0.036, 0.040)
    BROW = (0.084, 0.282, 1.862, 0.092, 0.052, 0.020)
    BROW_BONE = (0.0, 0.156, 1.892, 0.074, 0.098, 0.024)
    BROW_RIM = (0.0, 0.152, 1.878, 0.104, 0.130, 0.016)
    EAR_ROOT = Vector((0.092, 0.042, 1.866))
    EAR_TIP = Vector((0.196, -0.092, 2.012))
    EAR_W = (0.116, 0.132, 0.056, 0.040)
    EAR_IN = (0.062, 0.070, 0.014, 0.012)
    SKULL_HI = True
    FINS = (("head", 0.104, 1.920, 0.048, 1.958, 0.116, 0.056),
            ("head", 0.020, 1.932, -0.052, 1.982, 0.128, 0.058),
            ("head", -0.058, 1.898, -0.134, 1.958, 0.110, 0.050),
            ("head", -0.082, 1.826, -0.160, 1.888, 0.098, 0.044),
            ("chest", -0.240, 1.688, -0.302, 1.758, 0.098, 0.030),
            ("chest", -0.274, 1.604, -0.336, 1.670, 0.090, 0.028),
            ("chest", -0.278, 1.514, -0.336, 1.578, 0.084, 0.026))
    MANE_N = ((0.0, -0.040, 1.756), (0.0, -0.228, 1.678), 0.140, 0.086)
    RUFF = True

    # ── 头部可选件 ──────────────────────────────────────────────────────
    BROW_BONE = None
    BROW_RIM = None

    # ── 材质 ────────────────────────────────────────────────────────────
    MATS = {}
    M = dict(skin="皮肤", dark="皮肤暗", hi="皮肤亮", bone="骨",
             leather="皮革", ldark="皮革暗", metal="锈铁", team="team", trim="team_trim")

    def __init__(self, **kw):
        for k, v in kw.items():
            if not hasattr(self, k):
                raise KeyError("Gnoll 没有字段 %s" % k)
            setattr(self, k, v)
        self.setup()

    # 派生量
    def setup(self):
        self.HIP_L = mir(self.HIP)
        self.KNE_L = mir(self.KNE)
        self.HCK_L = mir(self.HCK)
        self.BAL_L = mir(self.BAL)
        self.TOE_L = mir(self.TOE)
        self.HEEL_L = mir(self.HEEL)
        self.SH_L = mir(self.SH)
        self.WRI_L = Vector(self.WRI_L)
        self.HDIR_L = Vector(self.HDIR_L)
        self.L_THIGH = (self.KNE - self.HIP).length
        self.L_SHIN = (self.HCK - self.KNE).length
        self.L_FOOT = (self.BAL - self.HCK).length
        self.L_TOE = (self.TOE - self.BAL).length
        # 爪底接触点（相对跖骨根）：脚跟 / 掌垫 / 趾尖
        self.CONTACT = ((self.HEEL.y - self.HCK.y, self.HEEL.z - self.HCK.z),
                        (self.BAL.y - self.HCK.y, self.BAL.z - self.HCK.z + 0.005),
                        (self.TOE.y - 0.022 - self.HCK.y, self.TOE.z - self.HCK.z + 0.002))
        self.Z_HIP = self.HIP.z
        self.Z_TOP = self.SKULL[2][1] + self.SKULL[2][3] * 0.5
        self.ELB_R = _ik2(self.SH, self.WRI_R, self.L_UPPER, self.L_FORE, self.POLE_R)
        self.ELB_L = _ik2(self.SH_L, self.WRI_L, self.L_UPPER, self.L_FORE, self.POLE_L)

    def m(self, key):
        return self.M[key]

    def foot_clear(self, pitch_deg):
        """给定脚的 pitch，返回"爪底不穿地"所需要的跖骨根高度。"""
        a = math.radians(pitch_deg)
        sa, ca = math.sin(a), math.cos(a)
        lo = min(dy * sa + dz * ca for (dy, dz) in self.CONTACT)
        return -lo + 0.0012

    def side(self, s):
        return "R" if s > 0 else "L"

    def hip(self, s):
        return self.HIP if s > 0 else self.HIP_L

    def kne(self, s):
        return self.KNE if s > 0 else self.KNE_L

    def hck(self, s):
        return self.HCK if s > 0 else self.HCK_L

    def bal(self, s):
        return self.BAL if s > 0 else self.BAL_L

    def toe(self, s):
        return self.TOE if s > 0 else self.TOE_L

    def sh(self, s):
        return self.SH if s > 0 else self.SH_L

    def wri(self, s):
        return self.WRI_R if s > 0 else self.WRI_L

    def hdir(self, s):
        return self.HDIR_R if s > 0 else self.HDIR_L


# ══ 1. 反关节腿 + 三趾爪 ════════════════════════════════════════════════════
def leg_one(u, S, s):
    side = S.side(s)
    th, sh, ft, to = "thigh_" + side, "shin_" + side, "foot_" + side, "toe_" + side
    hip, kne, hck, bal = S.hip(s), S.kne(s), S.hck(s), S.bal(s)
    k = S.LEG_K

    # 大腿：短而粗，前倾
    u.olimb("lg_thigh_" + side, tuple(hip + Vector((0, -0.012, 0.070)) * k), tuple(kne),
            [(0.00, 0.230 * k, 0.258 * k, 0.066 * k), (0.40, 0.246 * k, 0.272 * k, 0.070 * k),
             (1.00, 0.196 * k, 0.214 * k, 0.056 * k)],
            th, S.m("skin"), "chunk", "body", "thigh")
    u.olimb("lg_thigh_in_" + side,
            tuple(hip + Vector((-s * 0.052, -0.014, 0.020)) * k),
            tuple(kne + Vector((-s * 0.036, -0.004, 0.010)) * k),
            [(0.00, 0.100 * k, 0.242 * k, 0.032 * k), (1.00, 0.082 * k, 0.186 * k, 0.026 * k)],
            th, S.m("dark"), "chunk", "body", "thigh")
    u.add(K.arc_band("lg_thigh_hi_" + side,
                     tuple(hip + Vector((0, -0.012, 0.010)) * k),
                     tuple(kne + Vector((0, 0, 0.010)) * k),
                     0.110 * k, 0.088 * k, -34, 34, 1, 4, 0.014 * k,
                     (s * 0.94, -0.28, 0.18)),
          th, S.m("hi"), "chunk", "body", "thigh")
    u.add(ring("lg_knee_%s" % side, tuple(kne), tuple((kne - hip).normalized()),
               0.078 * k, 0.100 * k, 0.048 * k, 8), th, S.m("leather"), "chunk2", "body", "knee")

    # 小腿：向后折
    u.olimb("lg_shin_" + side, tuple(kne + Vector((0, -0.006, -0.012)) * k), tuple(hck),
            [(0.00, 0.158 * k, 0.176 * k, 0.048 * k), (0.40, 0.140 * k, 0.158 * k, 0.042 * k),
             (1.00, 0.106 * k, 0.120 * k, 0.032 * k)],
            sh, S.m("skin"), "chunk", "body", "shin")
    u.olimb("lg_shin_in_" + side,
            tuple(kne + Vector((-s * 0.042, 0.012, -0.034)) * k),
            tuple(hck + Vector((-s * 0.030, 0.006, 0.012)) * k),
            [(0.00, 0.066 * k, 0.160 * k, 0.020 * k), (1.00, 0.048 * k, 0.106 * k, 0.016 * k)],
            sh, S.m("dark"), "chunk", "body", "shin")
    for i, t in enumerate((0.28, 0.58)):
        a = lerp(kne, hck, t)
        b = lerp(kne, hck, t + 0.09)
        u.olimb("lg_wrap_%s%d" % (side, i), tuple(a), tuple(b),
                [(0.0, 0.156 * k - 0.05 * k * t, 0.174 * k - 0.05 * k * t, 0.046 * k),
                 (1.0, 0.150 * k - 0.05 * k * t, 0.168 * k - 0.05 * k * t, 0.044 * k)],
                sh, S.m("leather"), "chunk", "body", "wrap")
    u.add(disc("lg_wrap_pin_%s" % side,
               tuple(lerp(kne, hck, 0.34) + Vector((s * 0.074, -0.022, 0.010)) * k),
               (s, -0.25, 0.0), 0.019 * k, 0.018 * k, 6),
          sh, S.m("ldark"), "chunk", "body", "wrap")

    # 跖骨
    u.olimb("lg_meta_" + side, tuple(hck + Vector((0, 0.004, -0.008)) * k), tuple(bal),
            [(0.00, 0.116 * k, 0.128 * k, 0.032 * k), (0.55, 0.106 * k, 0.118 * k, 0.028 * k),
             (1.00, 0.112 * k, 0.122 * k, 0.030 * k)],
            ft, S.m("skin"), "chunk", "body", "meta")
    lx = S.HIP.x + 0.010 * k
    u.otube("lg_heel_" + side,
            [(0.058 * k, s * lx, -0.152 * k, 0.132 * k, 0.150 * k, 0.030 * k),
             (0.030 * k, s * lx, -0.156 * k, 0.140 * k, 0.158 * k, 0.032 * k),
             (0.000, s * lx, -0.156 * k, 0.128 * k, 0.146 * k, 0.028 * k)],
            ft, S.m("skin"), "chunk", "body", "paw", cw=0.028 * k)

    # 三趾：每趾 2 节 + 骨色尖爪
    ty0, ty1, ty2 = [v * k for v in getattr(S, "TOE_Y", (-0.082, 0.020, 0.132))]
    for i, (dx, ln, lw) in enumerate(((-0.073, 0.000, 0.056), (0.0, 0.012, 0.060),
                                      (0.073, 0.000, 0.056))):
        x = s * lx + dx * k
        y1, y2 = ty1 + ln * k, ty2 + ln * k
        u.olimb("lg_toe%s_a_%s" % (i, side), (x, ty0, 0.050 * k), (x, y1, 0.046 * k),
                [(0.00, lw * k, 0.084 * k, 0.020 * k), (1.00, lw * 0.98 * k, 0.080 * k, 0.019 * k)],
                to, S.m("skin"), "chunk", "body", "toe")
        u.olimb("lg_toe%s_b_%s" % (i, side), (x, y1 + 0.008 * k, 0.042 * k),
                (x, y2, 0.036 * k),
                [(0.00, lw * 0.94 * k, 0.070 * k, 0.017 * k),
                 (1.00, lw * 0.76 * k, 0.058 * k, 0.014 * k)],
                to, S.m("skin"), "chunk", "body", "toe")
        u.add(KU.claw("lg_claw%s_%s" % (i, side),
                      (x, y2 + 0.002, 0.030), (x + dx * 0.30, y2 + 0.058, 0.003),
                      0.044 * k, 0.034 * k), to, S.m("bone"), "chunk", "body", "claw")
    u.add(KU.claw("lg_dew_%s" % side,
                  tuple(hck + Vector((0, -0.036, 0.026)) * k),
                  tuple(hck + Vector((0, -0.104, -0.026)) * k), 0.040 * k, 0.034 * k),
          ft, S.m("bone"), "chunk", "body", "claw")


def legs(u, S):
    for s in (1, -1):
        leg_one(u, S, s)


# ══ 2. 胯 / 腰布 / 腰带 ═════════════════════════════════════════════════════
def pelvis(u, S, kilt=True, kilt_z=0.83, belt=True, beads=0, kilt_mat="team"):
    k = S.LEG_K
    zc = S.HIP.z
    u.otube("bd_hip",
            [(zc - 0.094 * k, 0, -0.010, 0.432 * k, 0.336 * k, 0.064 * k),
             (zc - 0.048 * k, 0, -0.010, 0.466 * k, 0.356 * k, 0.072 * k),
             (zc + 0.010 * k, 0, -0.008, 0.472 * k, 0.360 * k, 0.074 * k),
             (zc + 0.054 * k, 0, -0.006, 0.448 * k, 0.344 * k, 0.068 * k)],
            "hips", S.m("skin"), "chunk", "body", "pelvis", cw=0.072 * k)
    for s in (1, -1):
        u.add(K.arc_band("bd_hip_hi_" + S.side(s),
                         (s * 0.10 * k, -0.010, zc - 0.040 * k),
                         (s * 0.10 * k, -0.010, zc + 0.030 * k),
                         0.196 * k, 0.216 * k, -34, 34, 1, 4, 0.014 * k,
                         (s * 0.98, -0.12, 0.16)),
              "hips", S.m("hi"), "chunk", "body", "pelvis")

    if kilt:
        zs = ((zc + 0.042, 0.238 * k, 0.192 * k), (zc - 0.040, 0.248 * k, 0.202 * k),
              (zc - 0.120, 0.254 * k, 0.208 * k), (kilt_z, 0.250 * k, 0.204 * k))
        nu = 8
        grid = []
        for (z, rx, ry) in zs:
            grid.append([(rx * math.sin(math.radians(-34 + 68 * i / nu)),
                          ry * math.cos(math.radians(-34 + 68 * i / nu)), z)
                         for i in range(nu + 1)])
        row = []
        for i in range(nu + 1):
            a = math.radians(-34 + 68 * i / nu)
            kk = abs(i - nu * 0.5) / (nu * 0.5)
            row.append((0.246 * k * math.sin(a), 0.202 * k * math.cos(a),
                        kilt_z - 0.124 * k + 0.096 * k * kk))
        grid.append(row)
        u.add(K.grid_shell("bd_loin_f", grid, 0.016 * k, inside=(0, 0, zc - 0.12)),
              "hips", kilt_mat if kilt_mat in S.MATS else S.m("team"), "chunk", "body", "loin")
        st = [(z, 146, 214, rx, ry) for (z, rx, ry) in zs]
        st.append((kilt_z - 0.040, 150, 210, 0.244 * k, 0.200 * k))
        u.add(K.arc_panel("bd_loin_b", st, 0.016 * k, 8, None, (0.0, 0.0)),
              "hips", kilt_mat if kilt_mat in S.MATS else S.m("team"), "chunk", "body", "loin")
        for s in (1, -1):
            a = (42, 138) if s > 0 else (-138, -42)
            st = [(z, a[0], a[1], rx + 0.010, ry + 0.004) for (z, rx, ry) in zs]
            st.append((kilt_z - 0.034, a[0] + 4, a[1] - 4, 0.256 * k, 0.206 * k))
            u.add(K.arc_panel("bd_loin_" + S.side(s), st, 0.016 * k, 6, None, (0.0, 0.0)),
                  "hips", kilt_mat if kilt_mat in S.MATS else S.m("team"), "chunk", "body", "loin")
        zsu = ((zc - 0.090, 0.228 * k, 0.184 * k), (zc - 0.180, 0.232 * k, 0.188 * k),
               (kilt_z - 0.090, 0.218 * k, 0.176 * k))
        u.add(K.arc_panel("bd_loin_in", [(z, -180, 180, rx, ry) for (z, rx, ry) in zsu],
                          0.012 * k, 16, None, (0.0, 0.0)),
              "hips", S.m("ldark"), "chunk", "body", "loin")

    if beads:
        for i in range(beads):
            a = math.radians(-160 + i * (320.0 / max(1, beads - 1)))
            p = Vector((0.240 * k * math.sin(a), -0.008 + 0.198 * k * math.cos(a),
                        zc + 0.020 * k))
            u.add(octa("bd_bead_b%d" % i, tuple(p), 0.0125 * k, 0.017 * k, n=5),
                  "hips", S.m("bone"), "chunk", "body", "belt_bead")

    if belt:
        u.otube("bd_belt",
                [(zc + 0.030, 0, -0.008, 0.482 * k, 0.374 * k, 0.074 * k),
                 (zc + 0.052, 0, -0.008, 0.492 * k, 0.382 * k, 0.076 * k),
                 (zc + 0.080, 0, -0.008, 0.482 * k, 0.374 * k, 0.074 * k)],
                "hips", S.m("ldark"), "chunk", "body", "belt", cw=0.072 * k)
        u.otube("bd_belt_trim",
                [(zc + 0.052, 0, -0.008, 0.498 * k, 0.388 * k, 0.076 * k),
                 (zc + 0.066, 0, -0.008, 0.498 * k, 0.388 * k, 0.076 * k)],
                "hips", S.m("trim"), "chunk", "body", "belt", cw=0.072 * k)
        u.add(octa("bd_buckle", (0.0, 0.210 * k, zc + 0.052), 0.034 * k, 0.030 * k, n=6),
              "hips", S.m("bone"), "chunk", "body", "belt")


# ══ 3. 躯干 ═════════════════════════════════════════════════════════════════
def _chest_at(S, z):
    C = S.CHEST
    if z <= C[0][0]:
        return C[0][2], C[0][3], C[0][1]
    if z >= C[-1][0]:
        return C[-1][2], C[-1][3], C[-1][1]
    for i in range(len(C) - 1):
        z0, c0, w0, d0, _ = C[i]
        z1, c1, w1, d1, _ = C[i + 1]
        if z0 <= z <= z1:
            t = (z - z0) / (z1 - z0)
            return w0 + (w1 - w0) * t, d0 + (d1 - d0) * t, c0 + (c1 - c0) * t


def torso(u, S, straps=True, paint=None, abs_n=3):
    k = S.LEG_K
    zc = S.HIP.z
    u.otube("bd_core",
            [(zc + 0.040, 0, -0.006, 0.404 * k, 0.310 * k, 0.058 * k),
             (zc + 0.130, 0, 0.004, 0.372 * k, 0.300 * k, 0.054 * k),
             (zc + 0.250, 0, 0.012, 0.406 * k, 0.318 * k, 0.060 * k),
             (zc + 0.480, 0, -0.016, 0.520 * k, 0.404 * k, 0.080 * k),
             (zc + 0.640, 0, -0.070, 0.352 * k, 0.280 * k, 0.058 * k)],
            "spine", S.m("dark"), "facet", "body", "core", cw=0.058 * k)

    a0 = S.Z_ABD0
    u.otube("bd_abdomen",
            [(a0, 0, 0.004, 0.396 * k, 0.318 * k, 0.062 * k),
             (a0 + 0.045, 0, 0.007, 0.404 * k, 0.324 * k, 0.064 * k),
             (a0 + 0.100, 0, 0.011, 0.428 * k, 0.344 * k, 0.068 * k),
             (S.Z_CH0 - 0.014, 0, 0.013, 0.446 * k, 0.356 * k, 0.070 * k)],
            "spine", S.m("dark"), "chunk", "body", "abdomen", cw=0.066 * k)
    for i in range(abs_n):
        z0 = a0 + 0.007 + i * 0.056
        z1 = z0 + 0.040
        tt = max(0.0, min(1.0, ((z0 + z1) * 0.5 - a0) / (S.Z_CH0 - 0.014 - a0)))
        w = (0.396 + 0.052 * tt) * k
        d = (0.318 + 0.040 * tt) * k
        cy = 0.004 + 0.010 * tt
        u.add(K.arc_panel("bd_ab%d" % i,
                          [(z0, -58, 58, w * 0.5 + 0.006, d * 0.5 + 0.006, cy + 0.004),
                           (z1, -58, 58, w * 0.5 + 0.004, d * 0.5 + 0.004, cy + 0.004)],
                          0.026 * k, 6, None, (0.0, cy + 0.010)),
              "spine", S.m("skin"), "chunk", "body", "abs")

    u.otube("bd_chest", [(z, 0, c, w, d, kk) for (z, c, w, d, kk) in S.CHEST],
            "chest", S.m("skin"), "chunk", "body", "chest", cw=0.090 * k)
    # 胸肌
    for s in (1, -1):
        z1, z2 = S.Z_CH0 + 0.082, S.Z_CH0 + 0.230
        u.otube("bd_pec_" + S.side(s),
                [(z1, s * 0.108 * k, 0.198 * k, 0.150 * k, 0.106 * k, 0.040 * k),
                 (z1 + 0.052, s * 0.110 * k, 0.202 * k, 0.168 * k, 0.118 * k, 0.042 * k),
                 (z1 + 0.104, s * 0.108 * k, 0.196 * k, 0.166 * k, 0.116 * k, 0.042 * k),
                 (z1 + 0.148, s * 0.100 * k, 0.180 * k, 0.140 * k, 0.098 * k, 0.036 * k)],
                "chest", S.m("skin"), "chunk", "body", "pec", cw=0.038 * k)
    u.box("bd_cleft", (0.0, 0.196 * k, S.Z_CH0 + 0.154), (0.026, 0.028, 0.150),
          "chest", S.m("dark"), style="chunk", module="body", tag="pec")

    if S.HUMP:
        u.otube("bd_hump",
                [(S.Z_CH0 + 0.200, 0, -0.150, 0.330 * k, 0.220 * k, 0.054 * k),
                 (S.Z_CH0 + 0.275, 0, -0.176, 0.356 * k, 0.244 * k, 0.058 * k),
                 (S.Z_CH0 + 0.350, 0, -0.180, 0.310 * k, 0.206 * k, 0.050 * k),
                 (S.Z_CH0 + 0.420, 0, -0.160, 0.216 * k, 0.146 * k, 0.036 * k)],
                "chest", S.m("skin"), "chunk", "body", "hump", cw=0.052 * k)
        u.add(K.arc_panel("bd_back_hi",
                          [(S.Z_CH0 + 0.160, 158, 202, 0.262 * k, 0.212 * k),
                           (S.Z_CH0 + 0.230, 158, 202, 0.278 * k, 0.228 * k),
                           (S.Z_CH0 + 0.300, 158, 202, 0.272 * k, 0.222 * k),
                           (S.Z_CH0 + 0.370, 158, 202, 0.216 * k, 0.176 * k)],
                          0.012 * k, 4, None, (0.0, -0.060)),
              "chest", S.m("hi"), "chunk", "body", "hump")

    if straps:
        SA = Vector((-0.250, 0.070, 1.576)) * 1.0
        SB = Vector((-0.020, 0.208, 1.330))
        SC = Vector((0.196, 0.164, 1.086))
        # 以腰高为基准整体平移，适配不同身高
        dz = S.Z_CH0 - 1.270
        SA.z += dz
        SB.z += dz
        SC.z += dz
        for tag, p0, p1 in (("a", SA, SB), ("b", SB, SC)):
            u.olimb("bd_strap_" + tag, tuple(p0), tuple(p1),
                    [(0.00, 0.066 * k, 0.020, 0.012), (1.00, 0.066 * k, 0.020, 0.012)],
                    "chest", S.m("leather"), "chunk", "body", "strap")

    if paint:
        # 三道战纹（队色）
        for i, dx in enumerate(paint):
            u.box("bd_paint_%d" % i, (dx, 0.226 * k, S.Z_CH0 + 0.102), (0.011, 0.030, 0.070 * k),
                  "chest", S.m("team"), rot=(0, math.radians(9), 0),
                  style="chunk", module="body", tag="paint")


def neck(u, S):
    k = S.LEG_K
    zc = S.Z_NECK
    u.otube("bd_neck",
            [(zc - 0.093, 0, 0.024, 0.232 * k, 0.240 * k, 0.048 * k),
             (zc - 0.005, 0, 0.056, 0.206 * k, 0.214 * k, 0.042 * k),
             (zc + 0.077, 0, 0.090, 0.182 * k, 0.190 * k, 0.036 * k),
             (zc + 0.155, 0, 0.108, 0.152 * k, 0.160 * k, 0.030 * k)],
            "neck", S.m("skin"), "chunk", "body", "neck", cw=0.044 * k)
    u.add(K.arc_panel("bd_neck_dark",
                      [(zc - 0.075, -40, 40, 0.126 * k, 0.130 * k),
                       (zc + 0.015, -38, 38, 0.112 * k, 0.116 * k),
                       (zc + 0.095, -34, 34, 0.098 * k, 0.102 * k)],
                      0.012 * k, 4, None, (0.0, 0.070)),
          "neck", S.m("dark"), "chunk", "body", "neck")
    if S.RUFF:
        u.otube("bd_ruff",
                [(zc - 0.109, 0, 0.020, 0.286 * k, 0.292 * k, 0.058 * k),
                 (zc - 0.075, 0, 0.028, 0.268 * k, 0.276 * k, 0.054 * k),
                 (zc - 0.033, 0, 0.042, 0.232 * k, 0.240 * k, 0.046 * k)],
                "neck", S.m("dark"), "chunk", "body", "ruff", cw=0.050 * k)
        u.otube("bd_ruff2",
                [(zc + 0.011, 0, 0.062, 0.238 * k, 0.246 * k, 0.046 * k),
                 (zc + 0.051, 0, 0.076, 0.212 * k, 0.220 * k, 0.042 * k)],
                "neck", S.m("dark"), "chunk", "body", "ruff", cw=0.042 * k)


# ══ 4. 臂 ═══════════════════════════════════════════════════════════════════
def arm_one(u, S, s):
    side = S.side(s)
    sh, wr = S.sh(s), S.wri(s)
    el = S.ELB_R if s > 0 else S.ELB_L
    ua, fa = "upperarm_" + side, "forearm_" + side
    k = S.LEG_K

    u.olimb("ar_delt_" + side, tuple(sh + Vector((-s * 0.030, 0.004, 0.048)) * k),
            tuple(sh + (el - sh).normalized() * 0.170),
            [(0.00, 0.186 * k, 0.196 * k, 0.052 * k), (0.55, 0.180 * k, 0.190 * k, 0.050 * k),
             (1.00, 0.146 * k, 0.156 * k, 0.042 * k)],
            ua, S.m("skin"), "chunk", "body", "delt")
    u.add(K.arc_band("ar_delt_hi_" + side,
                     tuple(sh + Vector((-s * 0.010, 0.000, 0.062)) * k),
                     tuple(sh + (el - sh).normalized() * 0.150),
                     0.088 * k, 0.074 * k, -46, 46, 1, 4, 0.012,
                     (s * 0.55, -0.10, 0.83)),
          ua, S.m("hi"), "chunk", "body", "delt")

    u.olimb("ar_upper_" + side, tuple(sh + (el - sh) * 0.10), tuple(el),
            [(0.00, 0.148 * k, 0.160 * k, 0.040 * k), (0.55, 0.132 * k, 0.144 * k, 0.036 * k),
             (1.00, 0.118 * k, 0.128 * k, 0.032 * k)],
            ua, S.m("skin"), "chunk", "body", "upper")
    u.olimb("ar_upper_in_" + side,
            tuple(sh + (el - sh) * 0.14 + Vector((-s * 0.048, -0.026, 0)) * k),
            tuple(el + Vector((-s * 0.040, -0.020, 0)) * k),
            [(0.00, 0.056 * k, 0.130 * k, 0.018), (1.00, 0.048 * k, 0.104 * k, 0.016)],
            ua, S.m("dark"), "chunk", "body", "upper")

    u.add(ring("ar_elbow_%s" % side, tuple(el), tuple((el - sh).normalized()),
               0.062 * k, 0.082 * k, 0.044 * k, 8), fa, S.m("leather"), "chunk2", "body", "elbow")
    u.olimb("ar_fore_" + side, tuple(el + (wr - el) * 0.06), tuple(wr),
            [(0.00, 0.124 * k, 0.136 * k, 0.034 * k), (0.50, 0.116 * k, 0.126 * k, 0.032 * k),
             (1.00, 0.096 * k, 0.104 * k, 0.026 * k)],
            fa, S.m("skin"), "chunk", "body", "fore")
    u.olimb("ar_fore_in_" + side,
            tuple(el + (wr - el) * 0.10 + Vector((-s * 0.042, -0.020, 0)) * k),
            tuple(wr + Vector((-s * 0.030, -0.016, 0)) * k),
            [(0.00, 0.046 * k, 0.108 * k, 0.014), (1.00, 0.036 * k, 0.082 * k, 0.012)],
            fa, S.m("dark"), "chunk", "body", "fore")
    for i, t in enumerate((0.52, 0.68)):
        a = lerp(el, wr, t)
        b = lerp(el, wr, t + 0.10)
        r = (0.124 - 0.02 * t) * k
        u.olimb("ar_wrap_%s%d" % (side, i), tuple(a), tuple(b),
                [(0.0, r, r * 1.08, 0.032), (1.0, r * 0.96, r * 1.04, 0.030)],
                fa, S.m("leather"), "chunk", "body", "wrap")
    u.add(disc("ar_wrap_pin_" + side,
               tuple(lerp(el, wr, 0.60) + Vector((0, -0.086 * k, 0.0))),
               (0, -1, 0.2), 0.017 * k, 0.015 * k, 6),
          fa, S.m("ldark"), "chunk", "body", "wrap")


def arms(u, S):
    for s in (1, -1):
        arm_one(u, S, s)


# ══ 5. 手 ═══════════════════════════════════════════════════════════════════
def fist_around(u, S, side, center, axis, palm, r=0.055, k=1.0, cuff=True, tag="palm"):
    """握拳攥住一根沿 `axis` 的杆：掌心在 `palm` 方向，三指从 +Q 绕到 -P。

    萨满的巫杖、战士的刀柄、斥候的匕首共用这一套（换 axis / palm 就行）。
    """
    bone = "hand_" + side
    C = Vector(center)
    A = Vector(axis).normalized()
    P = Vector(palm)
    P = (P - A * P.dot(A)).normalized()
    Q = A.cross(P).normalized()
    m = lambda x, y, z: tuple(C + P * (x * k) + Q * (y * k) + A * (z * k))  # noqa: E731

    # 掌块：沿 A 放样 4 站
    rows = []
    for (t, w, d) in ((-0.088, 0.086, 0.104), (-0.040, 0.094, 0.112),
                      (0.012, 0.088, 0.106), (0.046, 0.076, 0.092)):
        rows.append((t * k, 0.066 * k, w * k, d * k))
    u.add(_frame_tube("hd_fist_palm_%s" % side, rows, C, A, P, Q, S, 0.024 * k),
          bone, S.m("skin"), "chunk", "body", tag)
    # 指缝内胆
    rows = []
    for t in (-0.052, 0.038):
        rows.append((t * k, 0.040 * k, 0.030 * k, 0.086 * k))
    u.add(_frame_tube("hd_fist_gap_%s" % side, rows, C, A, P, Q, S, 0.008 * k),
          bone, S.m("dark"), "chunk", "body", "finger")
    # 三指
    for i, dz in enumerate((-0.064, -0.018, 0.028)):
        p0 = C + P * (0.040 * k) + Q * (0.027 * k) + A * (dz * k)
        p1 = C + P * (0.016 * k) + Q * (0.089 * k) + A * (dz * k)
        p2 = C - P * (0.044 * k) + Q * (0.077 * k) + A * (dz * k)
        u.olimb("hd_f%d_a_%s" % (i, side), tuple(p0), tuple(p1),
                [(0.00, 0.046 * k, 0.046 * k, 0.014), (1.00, 0.040 * k, 0.042 * k, 0.012)],
                bone, S.m("skin"), "chunk", "body", "finger")
        u.olimb("hd_f%d_b_%s" % (i, side), tuple(p1), tuple(p2),
                [(0.00, 0.040 * k, 0.042 * k, 0.012), (1.00, 0.032 * k, 0.034 * k, 0.010)],
                bone, S.m("skin"), "chunk", "body", "finger")
        u.add(KU.claw("hd_fc%d_%s" % (i, side), tuple(p2),
                      tuple(p2 - P * (0.024 * k) + Q * (0.008 * k) - A * (0.010 * k)),
                      0.026 * k, 0.020 * k), bone, S.m("bone"), "chunk", "body", "claw")
    # 拇指
    u.olimb("hd_thumb_a_" + side, tuple(C + P * (0.072 * k) - Q * (0.053 * k)),
            tuple(C + P * (0.006 * k) - Q * (0.067 * k)),
            [(0.00, 0.044 * k, 0.048 * k, 0.014), (1.00, 0.036 * k, 0.040 * k, 0.012)],
            bone, S.m("skin"), "chunk", "body", "finger")
    u.olimb("hd_thumb_b_" + side, tuple(C + P * (0.006 * k) - Q * (0.067 * k)),
            tuple(C - P * (0.046 * k) - Q * (0.037 * k)),
            [(0.00, 0.036 * k, 0.040 * k, 0.012), (1.00, 0.028 * k, 0.032 * k, 0.010)],
            bone, S.m("skin"), "chunk", "body", "finger")
    if cuff:
        wr = S.wri(1 if side == "R" else -1)
        d = (C - wr).normalized()
        u.olimb("hd_cuff_" + side, tuple(wr + d * (0.030 * k)), tuple(wr - d * (0.006 * k)),
                [(0.0, 0.112 * k, 0.120 * k, 0.030), (1.0, 0.102 * k, 0.110 * k, 0.028)],
                bone, S.m("leather"), "chunk", "body", "cuff")


def _frame_tube(name, rows, C, A, P, Q, S, cw):
    """在 (P,Q,A) 局部系里按 (沿A, 沿P中心, w, d) 放样八边管。"""
    out = []
    for (t, pcen, w, d) in rows:
        base = C + A * t + P * pcen
        pts = K.octs(w, d, cw, cw)
        out.append([tuple(base + P * (x) + Q * (y)) for (x, y) in pts])
    return K.loft(name, out)


def hand_open(u, S, side, wrist=None, d=None, k=1.0):
    """三指爪（张开）：拇指 + 三根长指，每根 2 节、关节留缝。"""
    s = 1 if side == "R" else -1
    bone = "hand_" + side
    wr = S.wri(s) if wrist is None else Vector(wrist)
    dd = S.hdir(s) if d is None else Vector(d).normalized()
    palm = wr + dd * (0.062 * k)
    u.olimb("hd_palm_" + side, tuple(wr + dd * 0.008), tuple(palm + dd * (0.050 * k)),
            [(0.00, 0.098 * k, 0.072 * k, 0.024), (0.55, 0.108 * k, 0.078 * k, 0.026),
             (1.00, 0.096 * k, 0.070 * k, 0.022)],
            bone, S.m("skin"), "chunk", "body", "palm")
    tip = palm + dd * (0.052 * k)
    u.olimb("hd_gap_" + side, tuple(tip - dd * 0.014), tuple(tip + dd * 0.014),
            [(0.0, 0.104 * k, 0.028, 0.008), (1.0, 0.100 * k, 0.026, 0.008)],
            bone, S.m("dark"), "chunk", "body", "finger")
    for i, dx in enumerate((-0.036, 0.0, 0.036)):
        b = tip + Vector((dx * s * k, 0, 0))
        k1 = b + dd * (0.044 * k)
        k2 = k1 + (dd * 0.040 + Vector((0, 0.014, 0))).normalized() * (0.040 * k)
        u.olimb("hd_f%d_%s_a" % (i, side), tuple(b), tuple(k1),
                [(0.00, 0.030 * k, 0.034 * k, 0.009), (1.00, 0.026 * k, 0.030 * k, 0.008)],
                bone, S.m("skin"), "chunk", "body", "finger")
        u.olimb("hd_f%d_%s_b" % (i, side), tuple(k1 + dd * 0.006), tuple(k2),
                [(0.00, 0.026 * k, 0.030 * k, 0.008), (1.00, 0.022 * k, 0.026 * k, 0.007)],
                bone, S.m("skin"), "chunk", "body", "finger")
        u.add(KU.claw("hd_c%d_%s" % (i, side), tuple(k2 + dd * 0.004),
                      tuple(k2 + dd * (0.034 * k) + Vector((0, 0.014, -0.006))),
                      0.026 * k, 0.020 * k), bone, S.m("bone"), "chunk", "body", "claw")
    tb = palm + Vector((s * 0.012 * k, 0.038 * k, 0.026 * k))
    t1 = tb + (dd * 0.22 + Vector((0, 0.92, -0.32))).normalized() * (0.046 * k)
    u.olimb("hd_thumb_" + side, tuple(tb), tuple(t1),
            [(0.00, 0.034 * k, 0.038 * k, 0.010), (1.00, 0.028 * k, 0.032 * k, 0.008)],
            bone, S.m("skin"), "chunk", "body", "finger")
    u.add(KU.claw("hd_tclaw_" + side, tuple(t1),
                  tuple(t1 + (dd * 0.3 + Vector((0, 0.6, -0.5))).normalized() * (0.030 * k)),
                  0.024 * k, 0.018 * k), bone, S.m("bone"), "chunk", "body", "claw")


# ══ 6. 头 ═══════════════════════════════════════════════════════════════════
def head(u, S):
    k = S.LEG_K
    rows = [[(x, y, zc + zz) for (x, zz) in K.octs(w, h, 0.036 * k)]
            for (y, zc, w, h) in S.SKULL]
    u.add(K.loft("hd_skull", rows), "head", S.m("skin"), "chunk", "head", "skull")
    if S.SKULL_HI:
        i0, i1, i2 = 1, 2, 3
        u.add(K.loft("hd_skull_hi", [
            [(x, S.SKULL[i0][0] + 0.010, S.SKULL[i0][1] + S.SKULL[i0][3] * 0.5)
             for (x, z) in K.octs(S.SKULL[i0][2] * 0.46, 0.020 * k, 0.008 * k)],
            [(x, S.SKULL[i1][0], S.SKULL[i1][1] + S.SKULL[i1][3] * 0.5)
             for (x, z) in K.octs(S.SKULL[i1][2] * 0.52, 0.022 * k, 0.009 * k)],
            [(x, S.SKULL[i2][0], S.SKULL[i2][1] + S.SKULL[i2][3] * 0.48)
             for (x, z) in K.octs(S.SKULL[i2][2] * 0.48, 0.020 * k, 0.008 * k)]]),
            "head", S.m("hi"), "chunk", "head", "skull")

    rows = [[(x, y, zc + zz) for (x, zz) in K.octs(w, h, 0.022 * k)]
            for (y, zc, w, h) in S.JAW]
    u.add(K.loft("hd_jaw", rows), "head", S.m("skin"), "chunk", "head", "jaw")
    j = S.JAW
    u.add(K.loft("hd_jaw_dark", [
        [(x, j[0][0] + 0.010, j[0][1] - 0.042 * k + z) for (x, z) in K.octs(j[0][2] * 0.72, 0.018 * k, 0.007)],
        [(x, j[1][0], j[1][1] - 0.026 * k + z) for (x, z) in K.octs(j[1][2] * 0.88, 0.020 * k, 0.008)],
        [(x, j[3][0] - 0.022 * k, j[3][1] - 0.020 * k + z) for (x, z) in K.octs(j[3][2] * 1.06, 0.016 * k, 0.006)]]),
        "head", S.m("dark"), "chunk", "head", "jaw")

    rows = [[(x, y, z + zz) for (x, zz) in K.octs(w, 0.024 * k, 0.008 * k)]
            for (y, z, w) in S.MUZZLE]
    u.add(K.loft("hd_muzzle_dark", rows), "head", S.m("dark"), "chunk", "head", "muzzle")
    nose_rows = []
    for (yy, ww, hh, zc) in S.NOSE:
        nose_rows.append([(x, yy, zc + z) for (x, z) in K.octs(ww, hh, 0.008)])
    u.add(K.loft("hd_nose", nose_rows), "head", S.m("ldark"), "chunk", "head", "nose")
    mx, my, mz, ml, mh = S.MOUTH
    for s in (1, -1):
        u.box("hd_mouth_%d" % s, (s * mx, my, mz), (0.012, ml, mh),
              "head", S.m("ldark"), rot=(0, 0, -s * 0.05), style="chunk",
              module="head", tag="mouth")

    for s in (1, -1):
        base, dv, w, th = S.FANG_U
        ub = Vector((s * base.x, base.y, base.z))
        u.add(KU.claw("hd_fang_u%d" % s, tuple(ub),
                      tuple(ub + Vector((dv.x * s, dv.y, dv.z))), w, th),
              "head", S.m("bone"), "chunk", "head", "fang")
        base, dv, w, th = S.FANG_L
        lb = Vector((s * base.x, base.y, base.z))
        u.add(KU.claw("hd_fang_l%d" % s, tuple(lb),
                      tuple(lb + Vector((dv.x * s, dv.y, dv.z))), w, th),
              "head", S.m("bone"), "chunk", "head", "fang")

    ex, ey, ez, ew, ed, eh = S.EYE
    sx, sy, sz, sw, sd, sh = S.SOCKET
    bx, by, bz, bw, bd, bh = S.BROW
    for s in (1, -1):
        u.box("hd_socket_%d" % s, (s * sx, sy, sz), (sw, sd, sh),
              "head", S.m("ldark"), rot=(math.radians(-14), math.radians(s * 14), -s * 0.28),
              style="chunk", module="head", tag="eye")
        u.box("hd_eye_%d" % s, (s * ex, ey, ez), (ew, ed, eh),
              "head", S.m("trim"), rot=(math.radians(-14), math.radians(s * 14), -s * 0.28),
              style="chunk", module="head", tag="eye")
        u.box("hd_brow_%d" % s, (s * bx, by, bz), (bw, bd, bh),
              "head", S.m("dark"), rot=(0, math.radians(-14), -s * 0.24), style="chunk",
              module="head", tag="brow")

    for s in (1, -1):
        side = S.side(s)
        root = Vector((s * S.EAR_ROOT.x, S.EAR_ROOT.y, S.EAR_ROOT.z))
        tip = Vector((s * S.EAR_TIP.x, S.EAR_TIP.y, S.EAR_TIP.z))
        w0, w1, t0, t1 = S.EAR_W
        u.add(ear_plate("hd_ear_" + side, tuple(root), tuple(tip), w0, w1, t0, t1),
              "head", S.m("skin"), "chunk", "head", "ear")
        i0, i1, i2, i3 = S.EAR_IN
        r2 = root + (tip - root) * 0.16 + Vector((0, 0.022, 0))
        t2 = root + (tip - root) * 0.84 + Vector((0, 0.020, 0))
        u.add(ear_plate("hd_ear_in_" + side, tuple(r2), tuple(t2), i0, i1, i2, i3),
              "head", S.m("dark"), "chunk", "head", "ear")

    if S.BROW_BONE:
        x, y, z, w, h, t = S.BROW_BONE
        u.add(boss("hd_browbone", (0.0, y, z), w, h, t, n=6),
              "head", S.m("bone"), "chunk2", "head", "browbone")
        x, y, z, w, h, t = S.BROW_RIM
        u.add(boss("hd_browrim", (0.0, y, z), w, h, t, n=6),
              "head", S.m("trim"), "chunk", "head", "browbone")

    for i, (bone, y0, z0, y1, z1, w, t) in enumerate(S.FINS):
        u.add(fin("hd_fin%d" % i, y0, z0, y1, z1, w * k, t * k),
              bone, S.m("ldark"), "chunk", "head", "mane")
    if S.MANE_N[0] is not None:
        a, b, w, th = S.MANE_N
        u.add(KU.claw("hd_mane_n", tuple(a), tuple(b), w * k, th * k),
              "neck", S.m("ldark"), "chunk", "head", "mane")


# ══ 7. 尾 ═══════════════════════════════════════════════════════════════════
def tail(u, S):
    r0, r1, r2 = S.TAIL_R
    segs = ((S.TAIL0, S.TAIL1, "tail_01", r0, r1, S.m("skin")),
            (S.TAIL1, S.TAIL2, "tail_02", r1, r2, S.m("dark")))
    for a, b, bone, ra, rb, mat in segs:
        u.olimb("tl_%s" % bone, tuple(a), tuple(b),
                [(0.00, ra * 2, ra * 2.1, ra * 0.5),
                 (0.55, (ra + rb), (ra + rb) * 1.05, rb * 0.55),
                 (1.00, rb * 2, rb * 2.1, rb * 0.5)],
                bone, mat, "chunk", "body", "tail")
    u.add(K.arc_band("tl_belly", tuple(S.TAIL0 + (S.TAIL1 - S.TAIL0) * 0.10),
                     tuple(S.TAIL1), r0 * 0.97, r1 * 0.98, -46, 46, 1, 4, 0.010,
                     (0, -0.35, -0.94)),
          "tail_01", S.m("dark"), "chunk", "body", "tail")
    d = (S.TAIL2 - S.TAIL1).normalized()
    for i, (off, ln, wd) in enumerate(((-0.030, 0.115, 0.058), (0.006, 0.135, 0.062),
                                      (0.038, 0.100, 0.050))):
        a = S.TAIL2 + Vector((off * 0.7, 0, 0))
        b = a + d * ln + Vector((off * 1.6, -0.020, -0.020))
        u.add(KU.claw("tl_tuft%d" % i, tuple(a), tuple(b), wd, 0.028 * 0.85),
              "tail_02", S.m("ldark"), "chunk", "body", "tuft")


# ══ 8. 骨架 ═════════════════════════════════════════════════════════════════
def bones(S, extra=(), hands=True):
    """标准豺狼人骨架。extra 里可以塞武器插座 / 披风链 / 道具骨。"""
    b = [
        ("root", (0, 0, 0), (0, 0, 0.35), None),
        ("hips", (0, 0, S.Z_HIP), (0, 0, S.Z_WAIST), "root"),
        ("spine", (0, 0, S.Z_WAIST), (0, 0.012, S.Z_CH0), "hips"),
        ("chest", (0, 0.012, S.Z_CH0), (0, 0.045, S.Z_NECK), "spine"),
        ("neck", (0, 0.045, S.Z_NECK), (0, 0.098, S.Z_HEAD), "chest"),
        ("head", (0, 0.098, S.Z_HEAD), (0, 0.215, S.Z_HEAD + 0.154), "neck"),
    ]
    for s in (1, -1):
        side = S.side(s)
        sh, el, wr = S.sh(s), (S.ELB_R if s > 0 else S.ELB_L), S.wri(s)
        hd = S.hdir(s)
        b += [
            ("shoulder_" + side, (s * 0.070, 0.010, S.SH.z - 0.030), tuple(sh), "chest"),
            ("upperarm_" + side, tuple(sh), tuple(el), "shoulder_" + side),
            ("forearm_" + side, tuple(el), tuple(wr), "upperarm_" + side),
        ]
        if hands:
            b.append(("hand_" + side, tuple(wr), tuple(wr + hd * 0.120), "forearm_" + side))
        hip, kne, hck, bal, toe = S.hip(s), S.kne(s), S.hck(s), S.bal(s), S.toe(s)
        b += [
            ("thigh_" + side, tuple(hip), tuple(kne), "hips"),
            ("shin_" + side, tuple(kne), tuple(hck), "thigh_" + side),
            ("foot_" + side, tuple(hck), tuple(bal), "shin_" + side),
            ("toe_" + side, tuple(bal), tuple(toe), "foot_" + side),
        ]
    b += [
        ("tail_01", tuple(S.TAIL0), tuple(S.TAIL1), "hips"),
        ("tail_02", tuple(S.TAIL1), tuple(S.TAIL2), "tail_01"),
    ]
    for e in extra:
        b.append(e)
    return b


def set_arms(S, grip, wrist_off=0.082, pole_hint=(0.4, -0.6, -1.0)):
    """按"手里握点"反推右腕与手的方向，并解出肘（静止姿态用）。"""
    SGRIP = Vector(grip)
    d = (SGRIP - S.SH).normalized()
    S.WRI_R = SGRIP - d * wrist_off
    S.HDIR_R = d
    S.POLE_R = pole_hint
    S.ELB_R = _ik2(S.SH, S.WRI_R, S.L_UPPER, S.L_FORE, pole_hint)


def _ik2(root, target, l1, l2, pole):
    root, target = Vector(root), Vector(target)
    d = target - root
    dist = min(d.length, (l1 + l2) * 0.999)
    dn = d.normalized()
    a = (l1 * l1 - l2 * l2 + dist * dist) / (2 * dist)
    h = math.sqrt(max(l1 * l1 - a * a, 0.0))
    p = Vector(pole) - dn * Vector(pole).dot(dn)
    if p.length < 1e-6:
        p = Vector((0, 0, 1)) - dn * dn.z
    p.normalize()
    return root + dn * a + p * h


def _elb(S, s):
    return S.ELB_R if s > 0 else S.ELB_L
