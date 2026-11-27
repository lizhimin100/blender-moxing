"""unit_魔金傀儡.py —— 秘法·魔金傀儡 v2（精模 / 硬边支线）

v1 的问题：**读起来是"穿金甲的胖子/宇航员"，不是傀儡。**
  * 头是一颗光滑的蛋，只有一个眼缝 —— 没有"图腾面具"的味道；
  * 拳是一个带四个小凸点的水球 —— 完全没有指节结构；
  * 腿甲是贴着圆柱的弧形贴片，段与段之间只有 2 cm 缝，读不出"拼装"；
  * 抛光金 metal 0.95 / rough 0.16 太亮，像塑料电镀。

v2 的判据：**傀儡 = 用板拼出来的东西。**
  ① 所有体积件都能看出"这是几块板 + 几条缝"，缝里是铁色（每段 3~5 cm）；
  ② 关节是**外露的轴销**（圆柱 + 端盖）—— 这是"机械构造"的硬证据；
  ③ 头是一块**梯形面具**：平顶、平脸、一条横贯的发光眼缝，两侧各三颗铆钉；
  ④ 拳是**方块**：拳体 + 4 根手指各 2 节 + 指节横板 + 拇指 + 铁腕箍；
  ⑤ 胸口是**凹进去的熔炉口**（金唇边最高、炉膛最低、炉芯发光），不是贴片。

造型口径：
  * 1 unit = 1 m，+Y 正面，脚底 z = 0，原点在双足中间；总高 4.34 m（= 2.5 个步兵）；
  * 一块 = 一根骨、权重 1.0；关节留缝，缝里是铁色内胆。
  * 笔触：`chunk2/chunk3`（倒角 + 平面）为主，`facet` 给内胆，`soft` 只在靴头/肩顶各一处。

配色秩序（明度三档，同一色相内做层次，不换色）：
  铁 0.08（缝/内胆/轴销） < 金暗 0.20（次级板） < 金 0.42（主板） < 银金 0.62（边）
  + team 蓝只落在"熔炉环 / 腰带窄带"，辉 青只落在"眼缝 / 炉芯 / 纹路"。

组件化（MODULES）：四层
  body      腿/胯/腹/胸/臂/拳
  head      面具 + 眼缝 + 颌板 + 顶脊
  pauldron  三层叠片 ×2 + 肩轴销
  runes     熔炉核心 + 胸/肩/前臂/腿的发光纹（独立小件，供动画缩放脉冲）
"""
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = HERE
while not os.path.isdir(os.path.join(ROOT, "库")):
    _up = os.path.dirname(ROOT)
    if _up == ROOT:
        break
    ROOT = _up
LIB = os.path.join(ROOT, "库")
for _p in (LIB, HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import unitkit2 as K  # noqa: E402
import unitkit as KU  # noqa: E402

NAME = "魔金傀儡"
PREFIX = "mg"

# ── 尺寸表（m）──────────────────────────────────────────────────────────────
Z_ANKLE = 0.300
Z_KNEE = 1.160
Z_HIP = 2.050
Z_WAIST = 2.300
Z_CHEST = 2.850
Z_SHLD = 3.420
Z_NECK = 3.600
Z_TOP = 4.340

HIP_X = 0.295
LEG_X = 0.365
SH_X = 0.600

L_THIGH, L_SHIN = 0.92, 0.88
L_UPPER, L_FORE = 0.70, 0.66

SH_R = Vector((SH_X, 0.0, Z_SHLD))
SH_L = Vector((-SH_X, 0.0, Z_SHLD))

FIST_R = Vector((0.985, 0.400, 1.960))
FIST_L = Vector((-0.985, 0.400, 1.960))
FIST_W, FIST_D, FIST_H = 0.680, 0.610, 0.650
WRIST_OFF = 0.285

HIP_R = Vector((HIP_X, 0.0, Z_HIP))
HIP_L = Vector((-HIP_X, 0.0, Z_HIP))
ANK_R = Vector((LEG_X, 0.015, Z_ANKLE))
ANK_L = Vector((-LEG_X, 0.015, Z_ANKLE))
BALL_R = Vector((LEG_X, 0.170, 0.120))
BALL_L = Vector((-LEG_X, 0.170, 0.120))
TOE_R = Vector((LEG_X, 0.300, 0.080))
TOE_L = Vector((-LEG_X, 0.300, 0.080))


def ik2(root, target, l1, l2, pole):
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


def wrist_of(fist, shoulder, off=WRIST_OFF):
    return Vector(fist) - (Vector(fist) - Vector(shoulder)).normalized() * off


WRI_R = wrist_of(FIST_R, SH_R)
WRI_L = wrist_of(FIST_L, SH_L)
ELB_R = ik2(SH_R, WRI_R, L_UPPER, L_FORE, (0.55, -1.00, 0.0))
ELB_L = ik2(SH_L, WRI_L, L_UPPER, L_FORE, (-0.55, -1.00, 0.0))
KNE_R = ik2(HIP_R, ANK_R, L_THIGH, L_SHIN, (0.0, 1.0, 0.0))
KNE_L = ik2(HIP_L, ANK_L, L_THIGH, L_SHIN, (0.0, 1.0, 0.0))

HDIR_R = (FIST_R - WRI_R).normalized()
HDIR_L = (FIST_L - WRI_L).normalized()
ARM_D = {1: (ELB_R - SH_R).normalized(), -1: (ELB_L - SH_L).normalized()}

CORE_C = Vector((0.0, 0.392, 2.988))
PAUL_C = Vector((0.605, -0.004, 3.395))


# ── 骨架（26 根：6 躯干 + 8 臂 + 8 腿 + 4 纹路）─────────────────────────────
def _bones():
    b = [
        ("root",  (0, 0, 0), (0, 0, 0.34), None),
        ("hips",  (0, 0, Z_HIP), (0, 0, Z_WAIST), "root"),
        ("spine", (0, 0, Z_WAIST), (0, 0, 2.72), "hips"),
        ("chest", (0, 0, 2.72), (0, 0, Z_SHLD), "spine"),
        ("neck",  (0, 0, Z_SHLD), (0, 0, 3.66), "chest"),
        ("head",  (0, 0, 3.66), (0, 0, 4.28), "neck"),
    ]
    for s, side in ((1, "R"), (-1, "L")):
        sh = SH_R if s > 0 else SH_L
        el = ELB_R if s > 0 else ELB_L
        wr = WRI_R if s > 0 else WRI_L
        hd = HDIR_R if s > 0 else HDIR_L
        b += [
            ("shoulder_" + side, (s * 0.10, 0, 3.36), tuple(sh), "chest"),
            ("upperarm_" + side, tuple(sh), tuple(el), "shoulder_" + side),
            ("forearm_" + side, tuple(el), tuple(wr), "upperarm_" + side),
            ("hand_" + side, tuple(wr), tuple(wr + hd * 0.24), "forearm_" + side),
        ]
        hip = HIP_R if s > 0 else HIP_L
        kne = KNE_R if s > 0 else KNE_L
        ank = ANK_R if s > 0 else ANK_L
        ball = BALL_R if s > 0 else BALL_L
        toe = TOE_R if s > 0 else TOE_L
        b += [
            ("thigh_" + side, tuple(hip), tuple(kne), "hips"),
            ("shin_" + side, tuple(kne), tuple(ank), "thigh_" + side),
            ("foot_" + side, tuple(ank), tuple(ball), "shin_" + side),
            ("toe_" + side, tuple(ball), tuple(toe), "foot_" + side),
        ]
    b += [
        ("rune_chest", (0, 0.335, 3.02), (0, 0.360, 3.22), "chest"),
        ("rune_R", (0.86, 0.00, 3.46), (0.94, 0.16, 3.46), "shoulder_R"),
        ("rune_L", (-0.86, 0.00, 3.46), (-0.94, 0.16, 3.46), "shoulder_L"),
        ("core", tuple(CORE_C), (CORE_C.x, CORE_C.y + 0.10, CORE_C.z), "chest"),
    ]
    return b


BONES = _bones()
BONE_NAMES = [b[0] for b in BONES]

MODULES = ("body", "head", "pauldron", "runes")

MATS = {
    "金":        dict(hexcol="#BE8F46", metal=0.82, rough=0.37),
    "金暗":      dict(hexcol="#7A5C2C", metal=0.86, rough=0.45),
    "铁":        dict(hexcol="#2C313B", metal=0.55, rough=0.56),
    # 队色同方块人 / 建筑的标准值（#2E5FB4 / #F1CD79），别在精模里另开一套
    "team":      dict(hexcol="#2E5FB4", metal=0.00, rough=0.56),
    "team_trim": dict(hexcol="#F1CD79", metal=0.10, rough=0.44),
    "辉":        dict(hexcol="#4FD8FF", metal=0.0, rough=0.20,
                      emit="#4FD8FF", estr=3.2),
}


# ══ 通用小件 ════════════════════════════════════════════════════════════════
def disc(name, center, normal, r, thick, n=10):
    c = Vector(center)
    ez = Vector(normal).normalized()
    up = Vector((0, 0, 1))
    if abs(ez.dot(up)) > 0.95:
        up = Vector((0, 1, 0))
    ex = up.cross(ez).normalized()
    ey = ez.cross(ex).normalized()
    rows = []
    for (o, rr) in ((-thick * 0.5, r * 0.84), (-thick * 0.5 + 0.008, r),
                    (thick * 0.5 - 0.008, r), (thick * 0.5, r * 0.84)):
        rows.append([tuple(c + ez * o + ex * (rr * math.cos(math.tau * k / n))
                           + ey * (rr * math.sin(math.tau * k / n))) for k in range(n)])
    return K.loft(name, rows, True)


def ring(name, center, normal, r_in, r_out, thick, n=12):
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


def hinge(name, center, axis, r, half_len, cap_r=None, cap_t=None):
    """外露轴销：一根圆柱 + 两端端盖。傀儡的"机械构造"全靠它。"""
    c = Vector(center)
    ez = Vector(axis).normalized()
    cap_r = r * 1.30 if cap_r is None else cap_r
    cap_t = r * 0.55 if cap_t is None else cap_t
    body = disc(name, tuple(c), tuple(ez), r, half_len * 2.0, 10)
    c1 = disc(name + "_c1", tuple(c + ez * (half_len + cap_t * 0.4)), tuple(ez),
              cap_r, cap_t, 8)
    c2 = disc(name + "_c2", tuple(c - ez * (half_len + cap_t * 0.4)), tuple(-ez),
              cap_r, cap_t, 8)
    return [body, c1, c2]


def fm(name, p0, p1, r0, r1, a0, a1, nv=1, nu=4, thick=0.05, out=(0, 1, 0)):
    return K.arc_band(name, p0, p1, r0, r1, a0, a1, nv, nu, thick, out)


def lat(a, b, t):
    return Vector(a).lerp(Vector(b), t)


# ══ 1. 腿：板 / 缝 / 轴销 ═══════════════════════════════════════════════════
LEG_FLESH = [(2.060, 0.470, 0.510), (1.880, 0.484, 0.524), (1.660, 0.466, 0.502),
             (1.380, 0.432, 0.470), (1.180, 0.408, 0.444), (1.000, 0.396, 0.430),
             (0.800, 0.382, 0.414), (0.560, 0.366, 0.394), (0.360, 0.350, 0.378)]


def leg_wd(z):
    if z >= LEG_FLESH[0][0]:
        return LEG_FLESH[0][1], LEG_FLESH[0][2]
    if z <= LEG_FLESH[-1][0]:
        return LEG_FLESH[-1][1], LEG_FLESH[-1][2]
    for i in range(len(LEG_FLESH) - 1):
        z0, w0, d0 = LEG_FLESH[i]
        z1, w1, d1 = LEG_FLESH[i + 1]
        if z1 <= z <= z0:
            t = (z - z0) / (z1 - z0)
            return w0 + (w1 - w0) * t, d0 + (d1 - d0) * t
    return LEG_FLESH[-1][1], LEG_FLESH[-1][2]


def leg_axis(side, z):
    hip, kne, ank = (HIP_R, KNE_R, ANK_R) if side == "R" else (HIP_L, KNE_L, ANK_L)
    if z >= kne.z:
        t = (z - hip.z) / (kne.z - hip.z)
        return tuple(lat(hip, kne, t))[:2]
    t = (z - kne.z) / (ank.z - kne.z)
    return tuple(lat(kne, ank, t))[:2]


def leg_r(z, extra=0.036):
    w, d = leg_wd(z)
    return max(w, d) * 0.5 + extra


def legs(u):
    for s, side in ((1, "R"), (-1, "L")):
        th, sh, ft, to = ("thigh_" + side, "shin_" + side, "foot_" + side, "toe_" + side)
        hip, kne, ank = (HIP_R, KNE_R, ANK_R) if s > 0 else (HIP_L, KNE_L, ANK_L)
        x = s * LEG_X

        # 铁内胆：一整根八角柱（大腿 + 小腿各一段，膝上重叠）
        for (bone, z0, z1) in ((th, 2.055, 1.170), (sh, 1.150, 0.400)):
            st = []
            for zz in (z0, (z0 + z1) * 0.5, z1):
                cx, cy = leg_axis(side, zz)
                w, d = leg_wd(zz)
                st.append((zz, cx, cy, w * 0.86, d * 0.86, 0.11))
            u.otube("lg_flesh_%s_%d" % (side, int(z0 * 100)), st, bone, "铁",
                    "facet", "body", "flesh")

        # 大腿：上板 / 下板，中间 4 cm 缝
        aa0, aa1 = (-40, 202) if s > 0 else (-202, 40)
        for (zz0, zz1, tag) in ((2.040, 1.700, "a"), (1.660, 1.290, "b")):
            p0 = Vector(leg_axis(side, zz0) + (zz0,))
            p1 = Vector(leg_axis(side, zz1) + (zz1,))
            u.add(fm("lg_cuisse_%s%s" % (side, tag), tuple(p0), tuple(p1),
                     leg_r(zz0), leg_r(zz1), aa0, aa1, 2, 6, 0.052, (0, 1, 0)),
                  th, "金暗", "chunk3", "body", "thigh")
            # 外侧面再加一块窄亮板（两层叠压，读成"拼上去的"）
            oa0, oa1 = (16, 168) if s > 0 else (-168, -16)
            u.add(fm("lg_cuisse_%s%s_o" % (side, tag), tuple(p0 + Vector((0, 0, -0.020))),
                     tuple(p1 + Vector((0, 0, 0.030))),
                     leg_r(zz0) + 0.018, leg_r(zz1) + 0.018, oa0, oa1, 1, 4,
                     0.040, (0, 1, 0)),
                  th, "金", "chunk2", "body", "thigh")
            # 板的下沿加厚一圈（读成"这块板的边"）
            u.add(fm("lg_cuisse_%s%s_lip" % (side, tag),
                     tuple(p1 + Vector((0, 0, 0.050))), tuple(p1 + Vector((0, 0, 0.012))),
                     leg_r(zz1) + 0.010, leg_r(zz1) + 0.014, aa0 + 4, aa1 - 4, 1, 6,
                     0.040, (0, 1, 0)),
                  th, "team_trim", "chunk", "body", "thigh")

        # 膝：方形护膝 + 一根横穿的轴销（端盖露在两侧）
        kz = kne.z
        u.otube("lg_knee_" + side,
                [(kz + 0.190, x * 0.92, -0.020, 0.430, 0.460, 0.100),
                 (kz + 0.070, x * 0.96, 0.006, 0.470, 0.500, 0.110),
                 (kz - 0.060, x * 0.97, 0.000, 0.450, 0.480, 0.104),
                 (kz - 0.180, x * 0.95, -0.014, 0.412, 0.444, 0.096)],
                sh, "金", "chunk3", "body", "knee", cw=0.11)
        kx, _ = leg_axis(side, kz)
        for ob in hinge("lg_knee_pin_" + side, (kx, kne.y + 0.020, kz),
                        (1, 0, 0), 0.105, 0.250, 0.140, 0.048):
            u.add(ob, sh, "铁", "chunk2", "body", "joint")
        u.add(fm("lg_knee_spike_" + side,
                 tuple(Vector((kx, kne.y + 0.026, kz + 0.090))),
                 tuple(Vector((kx, kne.y + 0.150, kz - 0.020))),
                 0.196, 0.150, -46, 46, 1, 3, 0.060, (0, 1, 0)),
              sh, "金", "chunk3", "body", "knee")
        u.add(fm("lg_knee_top_" + side,
                 tuple(Vector((kx, kne.y - 0.014, kz + 0.184))),
                 tuple(Vector((kx, kne.y - 0.014, kz + 0.156))),
                 0.238, 0.244, -100, 100, 1, 5, 0.030, (0, 1, 0)),
              sh, "team_trim", "chunk", "body", "knee")

        # 小腿：两段板 + 一道中脊
        for (zz0, zz1, tag) in ((1.090, 0.760, "a"), (0.720, 0.420, "b")):
            p0 = Vector(leg_axis(side, zz0) + (zz0,))
            p1 = Vector(leg_axis(side, zz1) + (zz1,))
            u.add(fm("lg_greave_%s%s" % (side, tag), tuple(p0), tuple(p1),
                     leg_r(zz0), leg_r(zz1), aa0, aa1, 2, 6, 0.048, (0, 1, 0)),
                  sh, "金暗", "chunk3", "body", "shin")
            oa0, oa1 = (16, 168) if s > 0 else (-168, -16)
            u.add(fm("lg_greave_%s%s_o" % (side, tag), tuple(p0 + Vector((0, 0, -0.018))),
                     tuple(p1 + Vector((0, 0, 0.026))),
                     leg_r(zz0) + 0.018, leg_r(zz1) + 0.018, oa0, oa1, 1, 4,
                     0.036, (0, 1, 0)),
                  sh, "金", "chunk2", "body", "shin")
            u.add(fm("lg_greave_%s%s_rib" % (side, tag), tuple(p0), tuple(p1),
                     leg_r(zz0) + 0.030, leg_r(zz1) + 0.030, -8, 8, 1, 1,
                     0.022, (0, 1, 0)),
                  sh, "金", "chunk", "body", "shin")

        # 踝轴销
        for ob in hinge("lg_ankle_pin_" + side, (x, 0.030, 0.380), (1, 0, 0),
                        0.082, 0.180, 0.112, 0.040):
            u.add(ob, sh, "铁", "chunk2", "body", "joint")

        # 靴：三段楔形（跟 / 掌 / 趾），趾端一块金板
        u.otube("lg_boot_" + side,
                [(0.440, x, 0.010, 0.396, 0.430, 0.090),
                 (0.300, x, 0.040, 0.446, 0.520, 0.100),
                 (0.150, x, 0.086, 0.474, 0.610, 0.106),
                 (0.040, x, 0.100, 0.460, 0.600, 0.100)],
                ft, "金", "chunk3", "body", "boot", cw=0.10)
        u.otube("lg_sole_" + side,
                [(0.000, x, 0.100, 0.430, 0.566, 0.086),
                 (0.052, x, 0.100, 0.452, 0.588, 0.090)],
                ft, "铁", "chunk2", "body", "boot", cw=0.09)
        u.otube("lg_toe_plate_" + side,
                [(0.176, x, 0.196, 0.400, 0.150, 0.070),
                 (0.096, x, 0.220, 0.418, 0.170, 0.074),
                 (0.038, x, 0.226, 0.402, 0.166, 0.070)],
                to, "金暗", "chunk2", "body", "boot", cw=0.075)
        u.box("lg_toe_rim_" + side, (x, 0.262, 0.070), (0.372, 0.052, 0.030),
              to, "team_trim", style="chunk", module="body", tag="boot")


# ══ 2. 胯 / 腰 ══════════════════════════════════════════════════════════════
def pelvis(u):
    u.otube("bd_hip",
            [(1.840, 0, 0.000, 0.840, 0.580, 0.130),
             (1.960, 0, -0.002, 0.960, 0.640, 0.150),
             (2.070, 0, -0.004, 0.980, 0.636, 0.152),
             (2.170, 0, -0.004, 0.870, 0.566, 0.134)],
            "hips", "金", "chunk3", "body", "pelvis", cw=0.14)
    # 胯前挡板（独立一块，和胯之间有缝）
    u.arc("bd_cod",
          [(1.860, -30, 30, 0.430, 0.322), (1.960, -30, 30, 0.480, 0.348),
           (2.060, -28, 28, 0.500, 0.344)],
          0.052, "hips", "金暗", "chunk2", "body", "pelvis", nu=4, inside=(0, 0, 2.0))
    # 腰带：铁色槽 + 金暗带 + 两段 team 蓝
    u.otube("bd_belt",
            [(2.168, 0, -0.004, 0.884, 0.570, 0.136),
             (2.212, 0, -0.004, 0.868, 0.558, 0.132),
             (2.256, 0, -0.004, 0.876, 0.564, 0.134),
             (2.288, 0, -0.004, 0.888, 0.572, 0.136)],
            "hips", "铁", "chunk2", "body", "belt", cw=0.13)
    u.otube("bd_belt_band",
            [(2.216, 0, -0.004, 0.880, 0.566, 0.134),
             (2.250, 0, -0.004, 0.882, 0.568, 0.134)],
            "hips", "金暗", "chunk", "body", "belt", cw=0.13)
    for s in (1, -1):
        u.arc("bd_team_%d" % s,
              [(2.218, s * 66, s * 114, 0.446, 0.288),
               (2.248, s * 66, s * 114, 0.444, 0.286)],
              0.026, "hips", "team", "chunk", "body", "belt", nu=3, inside=(0, 0, 2.23))


# ══ 3. 躯干 ═════════════════════════════════════════════════════════════════
CHEST = [(2.760, 1.000, 0.590, -0.010), (2.880, 1.140, 0.658, -0.014),
         (2.980, 1.220, 0.702, -0.018), (3.100, 1.240, 0.708, -0.018),
         (3.220, 1.216, 0.688, -0.016), (3.340, 1.146, 0.648, -0.012),
         (3.440, 1.040, 0.594, -0.008), (3.520, 0.898, 0.518, -0.006)]


def chest_wd(z):
    if z <= CHEST[0][0]:
        return CHEST[0][1], CHEST[0][2], CHEST[0][3]
    if z >= CHEST[-1][0]:
        return CHEST[-1][1], CHEST[-1][2], CHEST[-1][3]
    for i in range(len(CHEST) - 1):
        z0, w0, d0, c0 = CHEST[i]
        z1, w1, d1, c1 = CHEST[i + 1]
        if z0 <= z <= z1:
            t = (z - z0) / (z1 - z0)
            return (w0 + (w1 - w0) * t, d0 + (d1 - d0) * t, c0 + (c1 - c0) * t)
    return CHEST[-1][1], CHEST[-1][2], CHEST[-1][3]


def chest_front(z):
    w, d, cy = chest_wd(z)
    return cy + d * 0.5


def torso(u):
    # 铁内胆（连续的八角柱，把所有缝兜住）
    u.otube("bd_core",
            [(2.150, 0, 0.000, 0.720, 0.500, 0.100),
             (2.300, 0, -0.002, 0.780, 0.524, 0.108),
             (2.560, 0, -0.008, 0.900, 0.580, 0.122),
             (2.820, 0, -0.014, 1.100, 0.640, 0.146),
             (3.080, 0, -0.018, 1.190, 0.678, 0.156),
             (3.460, 0, -0.010, 1.000, 0.560, 0.132)],
            "chest", "铁", "facet", "body", "core", cw=0.12)

    # 腹：三段横板，板间 3.6 cm 铁缝；每段下沿一道暗金唇
    bands = [((2.288, 2.416), (0.860, 0.556), (0.912, 0.584), "金暗"),
             ((2.452, 2.596), (0.930, 0.592), (1.000, 0.628), "金"),
             ((2.632, 2.780), (1.020, 0.636), (1.116, 0.678), "金")]
    for i, ((z0, z1), (w0, d0), (w1, d1), mat) in enumerate(bands):
        u.arc("bd_ab%d" % i,
              [(z0, -180, 180, w0 * 0.5, d0 * 0.5),
               (z1 - 0.014, -180, 180, w1 * 0.5 - 0.004, d1 * 0.5 - 0.004),
               (z1, -180, 180, w1 * 0.5, d1 * 0.5)],
              0.050, "spine", mat, "chunk3", "body", "abdomen", nu=8,
              inside=(0, 0, (z0 + z1) * 0.5))
        u.arc("bd_ab%d_lip" % i,
              [(z1 - 0.050, -180, 180, w1 * 0.5 + 0.014, d1 * 0.5 + 0.014),
               (z1 - 0.014, -180, 180, w1 * 0.5 + 0.012, d1 * 0.5 + 0.012)],
              0.026, "spine", "金暗", "chunk", "body", "abdomen", nu=8,
              inside=(0, 0, z1))

    # 胸：主体八角柱 + 正面一块独立大胸板（比主体凸 3 cm）
    u.otube("bd_chest", [(z, 0, cy, w, d, 0.17) for (z, w, d, cy) in CHEST],
            "chest", "金", "chunk3", "body", "chest", cw=0.17)
    pec = []
    for z in (2.840, 2.960, 3.080, 3.200, 3.300, 3.380):
        w, d, cy = chest_wd(z)
        pec.append((z, -54, 54, w * 0.5 + 0.024, d * 0.5 + 0.024, cy))
    u.arc("bd_pec", pec, 0.056, "chest", "金", "chunk3", "body", "chest", nu=6,
          inside=(0, 0, 3.10))
    # 胸板上沿一道银金唇
    w, d, cy = chest_wd(3.380)
    u.arc("bd_pec_lip",
          [(3.340, -52, 52, w * 0.5 + 0.030, d * 0.5 + 0.030),
           (3.386, -52, 52, w * 0.5 + 0.026, d * 0.5 + 0.026)],
          0.030, "chest", "team_trim", "chunk2", "body", "chest", nu=6,
          inside=(0, 0, 3.36))
    # 胸口中脊（一条凸棱，把大平面劈开）
    st = []
    for z in (2.840, 2.980, 3.120, 3.260, 3.360):
        w, d, cy = chest_wd(z)
        st.append((z, -7, 7, w * 0.5 + 0.030, d * 0.5 + 0.030, cy))
    u.arc("bd_sternum", st, 0.030, "chest", "金暗", "chunk2", "body", "chest", nu=2,
          inside=(0, 0, 3.10))

    # 背：五块叠瓦脊板
    for i, z in enumerate((2.860, 3.000, 3.140, 3.276, 3.400)):
        w, d, cy = chest_wd(z)
        u.arc("bd_back%d" % i,
              [(z - 0.052, 176, 184, w * 0.5 + 0.014, d * 0.5 + 0.014, cy),
               (z + 0.052, 172, 188, w * 0.5 + 0.018, d * 0.5 + 0.018, cy)],
              0.044, "chest", "金暗" if i % 2 else "金", "chunk2", "body", "chest",
              nu=2, inside=(0, 0, z))

    # 护喉：三层台阶，把"头插在棍上"堵死
    u.otube("bd_gorget",
            [(3.470, 0, -0.006, 1.020, 0.570, 0.150),
             (3.520, 0, -0.006, 0.920, 0.520, 0.136),
             (3.570, 0, -0.006, 0.760, 0.450, 0.116),
             (3.612, 0, -0.006, 0.600, 0.390, 0.096)],
            "chest", "金暗", "chunk3", "body", "gorget", cw=0.11)
    u.otube("bd_gorget_rim",
            [(3.606, 0, -0.006, 0.606, 0.394, 0.098),
             (3.628, 0, -0.006, 0.566, 0.376, 0.092)],
            "chest", "team_trim", "chunk2", "body", "gorget", cw=0.10)


# ══ 4. 臂 / 拳 ══════════════════════════════════════════════════════════════
def arms(u):
    for s, side in ((1, "R"), (-1, "L")):
        sh = SH_R if s > 0 else SH_L
        el = ELB_R if s > 0 else ELB_L
        wr = WRI_R if s > 0 else WRI_L
        ua, fa = "upperarm_" + side, "forearm_" + side
        d = ARM_D[s]
        out = (s * 0.92, -0.39, 0.0)

        # 肩轴销（露在护肩下面）
        u.olimb("jt_shoulder_" + side, tuple(sh + Vector((0, 0, 0.040))),
                tuple(sh + d * 0.070),
                [(0.0, 0.300, 0.310, 0.090), (1.0, 0.286, 0.296, 0.086)],
                ua, "铁", "facet", "body", "joint")
        for ob in hinge("jt_shoulder_pin_" + side, tuple(sh), (s, 0, 0),
                        0.116, 0.196, 0.150, 0.048):
            u.add(ob, ua, "铁", "chunk2", "body", "joint")

        # 上臂：铁胆 + 上段板 + 下段板
        u.olimb("ar_upper_" + side, tuple(sh + d * 0.030), tuple(el - d * 0.040),
                [(0.00, 0.268, 0.276, 0.078), (0.55, 0.250, 0.258, 0.072),
                 (1.00, 0.236, 0.244, 0.068)],
                ua, "铁", "facet", "body", "upper")
        u.add(fm("ar_rere_" + side, tuple(sh + d * 0.060), tuple(sh + d * 0.330),
                 0.168, 0.156, -118, 118, 1, 4, 0.048, out),
              ua, "金暗", "chunk3", "body", "upper")
        u.add(fm("ar_rere_b_" + side, tuple(sh + d * 0.356), tuple(sh + d * 0.560),
                 0.152, 0.144, -112, 112, 1, 4, 0.044, out),
              ua, "金暗", "chunk2", "body", "upper")
        u.add(fm("ar_rere_rib_" + side, tuple(sh + d * 0.070), tuple(sh + d * 0.550),
                 0.180, 0.166, -9, 9, 2, 1, 0.024, out),
              ua, "team_trim", "chunk", "body", "upper")

        # 肘轴销 + 肘盖
        for ob in hinge("ar_elbow_pin_" + side, tuple(el), (s, 0, 0),
                        0.098, 0.170, 0.132, 0.046):
            u.add(ob, fa, "铁", "chunk2", "body", "joint")
        u.add(fm("ar_cop_" + side, tuple(el - d * 0.030), tuple(el + (wr - el).normalized() * 0.070),
                 0.164, 0.156, -96, 96, 1, 3, 0.052, out),
              fa, "金", "chunk3", "body", "elbow")

        # 前臂：铁胆 + 外张的护腕板（读成"倒锥"）
        u.olimb("ar_fore_" + side, tuple(el + (wr - el).normalized() * 0.060),
                tuple(wr - (wr - el).normalized() * 0.020),
                [(0.00, 0.240, 0.248, 0.070), (0.55, 0.256, 0.264, 0.074),
                 (1.00, 0.272, 0.280, 0.078)],
                fa, "铁", "facet", "body", "fore")
        u.add(fm("ar_vamb_" + side, tuple(el + (wr - el).normalized() * 0.070),
                 tuple(wr - (wr - el).normalized() * 0.030),
                 0.160, 0.184, -128, 128, 1, 5, 0.050, out),
              fa, "金", "chunk3", "body", "fore")
        u.add(fm("ar_vamb_rib_" + side, tuple(el + (wr - el).normalized() * 0.080),
                 tuple(wr - (wr - el).normalized() * 0.040),
                 0.172, 0.196, -8, 8, 1, 1, 0.024, out),
              fa, "team_trim", "chunk", "body", "fore")
        # 腕箍：铁色环 + 两枚销
        u.add(fm("ar_cuff_" + side, tuple(wr - (wr - el).normalized() * 0.060),
                 tuple(wr - (wr - el).normalized() * 0.005),
                 0.196, 0.200, -180, 180, 1, 6, 0.040, out),
              fa, "铁", "chunk2", "body", "cuff")

    fist(u, "R", FIST_R)
    fist(u, "L", FIST_L)


def fist(u, side, c):
    """方块拳：拳体 + 4 指 ×2 节（近节竖排在前脸）+ 指节横板 + 拇指 ×2 节 + 腕箍。

    v1 的错：一个 rrect 放样球 + 4 个横向小凸点 = 一颗"带疙瘩的水球"。
    v2 的判据：**正面必须能数出 4 根手指**，手指是独立方块、块间 12 mm 缝，
    指节上压一条横板，拇指从内侧斜扣过来。
    """
    bone = "hand_" + side
    s = 1 if side == "R" else -1
    hw, hd, hh = FIST_W * 0.5, FIST_D * 0.5, FIST_H * 0.5
    fy = hd * 0.86                       # 拳体正脸（手指从这里往前长）

    # 拳体：上宽下收的八角方块
    rows = []
    for (dz, k, dy) in ((hh, 0.84, -0.034), (hh * 0.78, 0.97, -0.012),
                        (hh * 0.20, 1.00, 0.002), (-hh * 0.40, 0.96, -0.002),
                        (-hh * 0.84, 0.86, -0.022), (-hh, 0.68, -0.044)):
        w = FIST_W * k
        d = FIST_D * 0.86 * min(1.0, k + 0.06)
        rows.append([(c.x + p[0], c.y + dy + p[1], c.z + dz)
                     for p in K.octs(w, d, 0.090)])
    u.add(K.loft("ar_fist_" + side, rows), bone, "金", "chunk3", "body", "hand")

    fw = 0.148
    gy = 0.012
    for i in range(4):
        fx = c.x + (i - 1.5) * (fw + gy)
        # 近节：正面竖排的一根粗指
        u.otube("ar_fing%d_%s_prox" % (i, side),
                [(c.z + 0.196, fx, c.y + fy + 0.008, fw, 0.120, 0.034),
                 (c.z + 0.120, fx, c.y + fy + 0.058, fw, 0.170, 0.038),
                 (c.z + 0.010, fx, c.y + fy + 0.062, fw, 0.176, 0.040),
                 (c.z - 0.062, fx, c.y + fy + 0.040, fw, 0.156, 0.036)],
                bone, "金", "chunk2", "body", "hand", cw=0.034)
        # 远节：往里扣
        u.otube("ar_fing%d_%s_dist" % (i, side),
                [(c.z - 0.058, fx, c.y + fy + 0.052, fw, 0.150, 0.034),
                 (c.z - 0.132, fx, c.y + fy + 0.016, fw, 0.132, 0.032),
                 (c.z - 0.196, fx, c.y + fy - 0.030, fw, 0.108, 0.030)],
                bone, "金暗", "chunk2", "body", "hand", cw=0.030)

    # 指节横板：压在四指根上（银金，读成"护手"）
    u.box("ar_knuckle_" + side, (c.x, c.y + fy + 0.070, c.z + 0.206),
          (FIST_W * 0.98, 0.150, 0.058), bone, "team_trim", style="chunk2",
          module="body", tag="hand")
    # 指缝底：一条铁色暗槽，让四指的缝读成"缝"而不是"洞"
    u.box("ar_fist_gap_" + side, (c.x, c.y + fy + 0.026, c.z - 0.020),
          (FIST_W * 0.90, 0.100, 0.026), bone, "铁", style="chunk",
          module="body", tag="hand")
    # 拇指：内侧两节，从腕侧斜扣到指节前方
    u.otube("ar_thumb_%s_a" % side,
            [(c.z + 0.208, c.x - s * (hw - 0.086), c.y + fy - 0.150, 0.150, 0.160, 0.036),
             (c.z + 0.086, c.x - s * (hw - 0.050), c.y + fy - 0.050, 0.162, 0.176, 0.038)],
            bone, "金", "chunk2", "body", "hand", cw=0.036)
    u.otube("ar_thumb_%s_b" % side,
            [(c.z + 0.086, c.x - s * (hw - 0.050), c.y + fy - 0.050, 0.162, 0.176, 0.038),
             (c.z - 0.026, c.x - s * (hw - 0.024), c.y + fy + 0.020, 0.150, 0.162, 0.036),
             (c.z - 0.116, c.x - s * (hw + 0.006), c.y + fy - 0.010, 0.134, 0.140, 0.032)],
            bone, "金暗", "chunk2", "body", "hand", cw=0.032)
    # 腕箍（铁色，填拳与前臂的缝）
    u.otube("ar_wrist_" + side,
            [(c.z + 0.372, c.x, c.y - 0.028, 0.316, 0.316, 0.076),
             (c.z + 0.296, c.x, c.y - 0.022, 0.330, 0.330, 0.080)],
            bone, "铁", "chunk2", "body", "joint", cw=0.075)


# ══ 5. 护肩：三层叠片 + 肩轴销端盖 ═════════════════════════════════════════
def pauldrons(u):
    for s, side in ((1, "R"), (-1, "L")):
        sh = SH_R if s > 0 else SH_L
        d = ARM_D[s]
        out = (s * 0.92, -0.39, 0.24)
        base = sh + Vector((0, 0, 0.010))

        u.add(disc("pd_cap_" + side, tuple(base), tuple(-d), 0.206, 0.066, 8),
              "shoulder_" + side, "金", "chunk3", "pauldron", "cap")
        u.add(ring("pd_cap_rim_" + side, tuple(base - d * 0.010), tuple(-d),
                   0.206, 0.240, 0.044, 8),
              "shoulder_" + side, "team_trim", "chunk2", "pauldron", "rim")
        u.add(fm("pd_l1_" + side, tuple(base), tuple(base + d * 0.300),
                 0.214, 0.286, -110, 110, 1, 4, 0.070, out),
              "shoulder_" + side, "金", "chunk3", "pauldron", "pauldron")
        u.add(fm("pd_l1_edge_" + side, tuple(base + d * 0.250), tuple(base + d * 0.300),
                 0.276, 0.290, -106, 106, 1, 4, 0.046, out),
              "shoulder_" + side, "team_trim", "chunk2", "pauldron", "rim")
        u.add(fm("pd_l2_" + side, tuple(base + d * 0.276), tuple(base + d * 0.470),
                 0.306, 0.334, -106, 106, 1, 4, 0.066, out),
              "shoulder_" + side, "金暗", "chunk3", "pauldron", "lame")
        u.add(fm("pd_l2_edge_" + side, tuple(base + d * 0.430), tuple(base + d * 0.470),
                 0.326, 0.336, -102, 102, 1, 4, 0.044, out),
              "shoulder_" + side, "team_trim", "chunk2", "pauldron", "rim")
        u.add(fm("pd_l3_" + side, tuple(base + d * 0.446), tuple(base + d * 0.620),
                 0.350, 0.366, -100, 100, 1, 4, 0.062, out),
              "shoulder_" + side, "金", "chunk3", "pauldron", "lame")
        # 肩顶三枚大铆钉：必须落在顶盖平面里（法线 = -d），否则会变成三根天线
        ez = -d
        ex = (Vector((1, 0, 0)) - ez * ez.x).normalized()
        ey = ez.cross(ex)
        for k, (uu, vv) in enumerate(((0.126, 0.0), (0.062, 0.112), (0.062, -0.112))):
            u.rivet("pd_stud_%s%d" % (side, k),
                    tuple(base + ex * uu + ey * vv),
                    tuple(ez), "shoulder_" + side,
                    "team_trim", "chunk", "pauldron", "stud", r=0.028, h=0.016, n=6)


# ══ 6. 头：图腾面具 ═════════════════════════════════════════════════════════
HELM = [(3.580, 0.380, 0.404), (3.652, 0.484, 0.506), (3.766, 0.522, 0.542),
        (3.900, 0.532, 0.548), (4.040, 0.526, 0.540), (4.132, 0.500, 0.512),
        (4.208, 0.436, 0.448), (4.256, 0.330, 0.342)]
HELM_Y = 0.012
HELM_C = 0.086


def helm_wd(z):
    if z <= HELM[0][0]:
        return HELM[0][1], HELM[0][2]
    if z >= HELM[-1][0]:
        return HELM[-1][1], HELM[-1][2]
    for i in range(len(HELM) - 1):
        z0, w0, d0 = HELM[i]
        z1, w1, d1 = HELM[i + 1]
        if z0 <= z <= z1:
            t = (z - z0) / (z1 - z0)
            return w0 + (w1 - w0) * t, d0 + (d1 - d0) * t
    return HELM[-1][1], HELM[-1][2]


def helm_patch(name, zs, a0, a1, nu, off, thick):
    grid = []
    for z in zs:
        w, d = helm_wd(z)
        row = []
        for i in range(nu + 1):
            a = math.radians(a0 + (a1 - a0) * i / nu)
            row.append(((w * 0.5 + off) * math.sin(a),
                        HELM_Y + (d * 0.5 + off) * math.cos(a), z))
        grid.append(row)
    return K.grid_shell(name, grid, thick, inside=(0, HELM_Y, sum(zs) / len(zs)))


def head(u):
    # 颈（粗，藏在护喉里；只露一条铁色缝）
    u.otube("jt_neck",
            [(3.360, 0, 0.008, 0.440, 0.440, 0.100),
             (3.500, 0, 0.008, 0.410, 0.414, 0.094),
             (3.652, 0, 0.008, 0.382, 0.390, 0.088)],
            "neck", "铁", "facet", "head", "neck", cw=0.09)

    # 面具本体：平顶、平脸的切角方柱
    u.add(K.otube("hd_mask_body", [(z, 0, HELM_Y, w, d, HELM_C) for (z, w, d) in HELM]),
          "head", "金", "chunk3", "head", "helm")
    # 顶盖：一块独立平板，比面具收 5 cm —— 读出"盖上去的"
    u.add(K.otube("hd_top",
                  [(4.238, 0, HELM_Y, 0.372, 0.384, 0.062),
                   (4.286, 0, HELM_Y, 0.312, 0.324, 0.052)],
                  0.07),
          "head", "金暗", "chunk3", "head", "helm")
    # 顶冠：三颗钉（不是"提手"）
    for k, yy in enumerate((-0.104, 0.0, 0.104)):
        u.rivet("hd_crown%d" % k, (0.0, HELM_Y + yy, 4.286), (0, 0, 1),
                "head", "team_trim", "chunk", "head", "crown", r=0.030, h=0.018, n=6)

    # 眼缝：正面上一条暗槽 + 里面一条发光带
    u.add(helm_patch("hd_slit", [3.872, 3.932], -31, 31, 4, 0.004, 0.032),
          "head", "铁", "chunk2", "head", "slit")
    u.add(helm_patch("hd_eye", [3.888, 3.918], -28, 28, 4, 0.022, 0.024),
          "head", "辉", "chunk", "head", "eye")
    # 鼻脊：一道竖棱把眼缝劈成两段 —— 图腾脸的核心
    u.add(helm_patch("hd_nose", [3.812, 3.900, 3.964], -7, 7, 2, 0.030, 0.044),
          "head", "金", "chunk2", "head", "nose")
    # 眉檐：比面具更宽的硬檐，给眼缝打一条阴影
    u.add(helm_patch("hd_brow", [3.934, 3.980], -31, 31, 4, 0.030, 0.038),
          "head", "金暗", "chunk3", "head", "brow")
    # 颌板：下巴一块独立板，四周留缝
    u.add(helm_patch("hd_jaw", [3.664, 3.722, 3.782], -30, 30, 4, 0.026, 0.038),
          "head", "金暗", "chunk2", "head", "jaw")
    # 两侧各三颗铆钉（面具的"钉阵"）—— 落在侧面上，不是正面
    for s2 in (1, -1):
        for k, zz in enumerate((3.700, 3.800, 3.862)):
            aa = math.radians(s2 * 78)
            w, d = helm_wd(zz)
            u.rivet("hd_stud_%d%d" % (s2, k),
                    ((w * 0.5 + 0.006) * math.sin(aa),
                     HELM_Y + (d * 0.5 + 0.006) * math.cos(aa), zz),
                    (math.sin(aa), math.cos(aa), 0),
                    "head", "金", "chunk", "head", "stud", r=0.024, h=0.012, n=6)
    # 面甲下缘一圈铁色槽
    u.add(helm_patch("hd_rim", [3.578, 3.612], -180, 180, 12, 0.006, 0.022),
          "head", "铁", "chunk", "head", "rim")
    # 后脑板
    u.arc("hd_nape",
          [(3.660, 100, 260, 0.262, 0.272), (3.780, 100, 260, 0.266, 0.276),
           (3.900, 100, 260, 0.268, 0.278)],
          0.036, "head", "金暗", "chunk2", "head", "nape", nu=6,
          inside=(0, HELM_Y, 3.78))


# ══ 7. 发光纹路 ═════════════════════════════════════════════════════════════
def chest_y(x, z):
    """胸板外表面在 (x,z) 处的高度 —— 把胸口的光纹贴死在曲面上，不许浮空。"""
    w, d, cy = chest_wd(z)
    rx = w * 0.5 + 0.024
    ry = d * 0.5 + 0.024
    t = min(0.985, abs(x) / rx)
    return cy + ry * math.sqrt(max(0.0, 1.0 - t * t)) + 0.028


def runes(u):
    cc = CORE_C
    # 熔炉口：八角金唇边（最高）→ 铁炉膛（最低）→ 发光炉芯，再压三道炉栅。
    # v1 是一个发光的圆贴片，读起来像"钢铁侠的反应炉"；加了炉栅才是"炉"。
    u.add(ring("mg_core_bezel", tuple(cc), (0, 1, 0), 0.150, 0.206, 0.048, 8),
          "core", "金", "chunk2", "runes", "core")
    u.add(disc("mg_core_floor", tuple(cc - Vector((0, 0.030, 0))), (0, 1, 0),
               0.158, 0.030, 8), "core", "铁", "chunk", "runes", "core")
    u.add(disc("mg_core_glow", tuple(cc - Vector((0, 0.014, 0))), (0, 1, 0),
               0.142, 0.020, 8), "core", "辉", "chunk", "runes", "core")
    for k, dx in enumerate((-0.074, 0.0, 0.074)):
        u.box("mg_core_bar%d" % k, (cc.x + dx, cc.y + 0.002, cc.z),
              (0.026, 0.044, 0.250), "core", "铁", style="chunk2",
              module="runes", tag="core")
    u.box("mg_core_barh", (cc.x, cc.y + 0.002, cc.z + 0.028),
          (0.286, 0.040, 0.024), "core", "金暗", style="chunk",
          module="runes", tag="core")

    # 熔炉两侧各两道水平排气槽：逐顶点贴到胸板曲面上（不许做成悬空平板）
    for i, (sx, zz) in enumerate(((1, 3.116), (1, 2.900), (-1, 3.116), (-1, 2.900))):
        quad = [(sx * 0.212, zz - 0.012), (sx * 0.346, zz - 0.010),
                (sx * 0.346, zz + 0.010), (sx * 0.212, zz + 0.012)]
        thick = 0.018
        front = [(x, chest_y(x, z) + thick, z) for (x, z) in quad]
        back = [(x, chest_y(x, z), z) for (x, z) in quad]
        n = len(quad)
        verts = front + back
        faces = [tuple(range(n)), tuple(range(2 * n - 1, n - 1, -1))]
        for j in range(n):
            j2 = (j + 1) % n
            faces.append((j, j2, n + j2, n + j))
        u.add(KU._obj("mg_rune_chest%d" % i, verts, faces),
              "rune_chest", "辉", "chunk", "runes", "rune")

    # 护肩：每片一条短光条（贴主片外表面）
    for s, side in ((1, "R"), (-1, "L")):
        sh = SH_R if s > 0 else SH_L
        d = ARM_D[s]
        out = (s * 0.92, -0.39, 0.24)
        for k, aa in enumerate((-34, 34)):
            u.add(fm("mg_rune_sh_%s%d" % (side, k),
                     tuple(sh + d * 0.210), tuple(sh + d * 0.360),
                     0.238, 0.286, aa - 7, aa + 7, 1, 1, 0.018, out),
                  "rune_" + side, "辉", "chunk", "runes", "rune")

    # 前臂：两条
    for s, side in ((1, "R"), (-1, "L")):
        el = ELB_R if s > 0 else ELB_L
        wr = WRI_R if s > 0 else WRI_L
        out = (s * 0.92, -0.39, 0.0)
        for k, a in enumerate((-26, 24)):
            u.add(fm("mg_rune_fa_%s%d" % (side, k),
                     tuple(el + (wr - el).normalized() * 0.140),
                     tuple(wr - (wr - el).normalized() * 0.070),
                     0.176, 0.200, a - 6, a + 6, 1, 1, 0.016, out),
                  "forearm_" + side, "辉", "chunk", "runes", "rune")

    # 腿：大腿、小腿各一条外侧光条
    for s, side in ((1, "R"), (-1, "L")):
        ang = s * 90.0
        for (bone, z0, z1, tag) in (("thigh_" + side, 1.960, 1.420, "th"),
                                    ("shin_" + side, 0.980, 0.520, "sh")):
            ax0, ay0 = leg_axis(side, z0)
            ax1, ay1 = leg_axis(side, z1)
            u.add(fm("mg_rune_%s_%s" % (tag, side),
                     (ax0, ay0, z0), (ax1, ay1, z1),
                     leg_r(z0) + 0.010, leg_r(z1) + 0.010,
                     ang - 7, ang + 7, 1, 1, 0.018, (0, 1, 0)),
                  bone, "辉", "chunk", "runes", "rune")


# ══ 组装 ════════════════════════════════════════════════════════════════════
def build(low=False, modules=None):
    want = set(MODULES if modules is None else modules)
    u = K.Unit2(PREFIX, MATS, low=low)
    if "body" in want:
        legs(u)
        pelvis(u)
        torso(u)
        arms(u)
    if "head" in want:
        head(u)
    if "pauldron" in want:
        pauldrons(u)
    if "runes" in want:
        runes(u)
    return u


def build_rig(name="RIG_魔金傀儡"):
    return K.build_rig(BONES, name)


def report():
    return "\n".join([
        "[joints] hip=%.3f knee=(%.3f,%.3f) ankle=%.3f top=%.3f"
        % (Z_HIP, KNE_R.y, KNE_R.z, Z_ANKLE, Z_TOP),
        "[armR] elbow=(%.3f,%.3f,%.3f) wrist=(%.3f,%.3f,%.3f) reach=%.3f/%.3f"
        % (ELB_R.x, ELB_R.y, ELB_R.z, WRI_R.x, WRI_R.y, WRI_R.z,
           (WRI_R - SH_R).length, L_UPPER + L_FORE),
        "[armL] elbow=(%.3f,%.3f,%.3f) wrist=(%.3f,%.3f,%.3f) reach=%.3f/%.3f"
        % (ELB_L.x, ELB_L.y, ELB_L.z, WRI_L.x, WRI_L.y, WRI_L.z,
           (WRI_L - SH_L).length, L_UPPER + L_FORE),
        "[fist] c=(%.3f,%.3f,%.3f) size=%.2fx%.2fx%.2f span_x=%.3f"
        % (FIST_R.x, FIST_R.y, FIST_R.z, FIST_W, FIST_D, FIST_H,
           (FIST_R.x + FIST_W * 0.5) * 2),
        "[bones] %d" % len(BONES),
    ])
