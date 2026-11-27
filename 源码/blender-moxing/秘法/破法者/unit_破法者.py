"""unit_破法者.py —— 秘法·破法者 v2（精模 / 硬边支线）

v1 的问题：整件都是 `soft`（CC 细分）+ 圆截面，做出来是"橡皮泥骑士"——
盔是子弹头、护肩是两个圆球、四肢是圆管、裙甲是一个大钟罩把腿吞了。
和方块人（4 点方截面 + 平面着色）站在一起不是一家人。

v2 的判据：**低模骨架 = 硬平面，细节 = 棱上的倒角高光。**
  * 截面一律 `octs`（八边切角矩形）或 4 点方截面 —— 没有圆弧段；
  * 笔触 95% 是 `chunk/chunk2/facet`（倒角 + 平面着色），只有盔顶、透镜式的盾鼓面用 `soft`；
  * 每一条边都想清楚：要么是一条锐棱，要么是一条 6~13 mm 的倒角，不许"糊"。

造型口径（与方块人同一套资产规矩）：
  * 1 unit = 1 m，+Y 正面，脚底 z = 0，原点在双足中间；
  * 一块 = 一根骨、权重 1.0（刚性蒙皮）；关节留缝，缝里塞更深色的内胆。

三条读感（俯角 96 px 仍要指认）：
  ① 头：**方盔**（平顶 + 斜眉 + 下颌收）+ 一条横扫的金眉 + 被鼻梁劈开的两道蓝眼缝；
  ② 左：长鸢盾（蓝面 / 金边 / 银脊 / 金圆芯），占剪影 1/3 的重量；
  ③ 右：十字利刃 **跨 0.80 m**（D=0.40，v1 只有 0.57），四个尖角冲出身体轮廓。

配色秩序（明度从低到高，蓝只落三处）：
  布 0.055 < 钢暗 0.17 < team 0.21 < 钢 0.30 < 金 0.55 < 银 0.72
  蓝：盾面 / 裙衬 / 眼缝旁的盔箍。金：只做边和钉，不做面。

组件化（MODULES）：七层，各自成物体、各自可删
  body     腿/胯/躯干/臂/手
  head     方盔 + 面甲 + 眼缝 + 冠鳍
  pauldron 三层叠片护肩（绕上臂轴）
  skirt    前/侧/后三组刚性腿裙 + 蓝衬里
  shield   长面盾（独立 glb，挂 shield 骨）
  weapon   十字利刃（独立 glb，挂 weapon_R）
  fx       施法电弧（挂 fx_cast，静止缩到 1/45）
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
import unitkit as KU  # noqa: E402  （只借 _obj 拼自定义网格）

NAME = "破法者"
PREFIX = "sb"

# ── 尺寸表（m）──────────────────────────────────────────────────────────────
Z_ANKLE = 0.105
Z_KNEE = 0.478
Z_HIP = 0.900
Z_WAIST = 1.030
Z_CHEST = 1.160
Z_SHLD = 1.400
Z_NECK = 1.470
Z_TOP = 1.800
Z_CREST = 1.838
LEG_X = 0.118
SH_X = 0.200            # v1 = 0.176：肩要压过胯，剪影才是骑士不是陀螺

L_THIGH, L_SHIN = 0.435, 0.372
L_UPPER, L_FORE = 0.285, 0.265
WRIST_OFF = 0.055

SH_R = Vector((SH_X, 0.0, 1.402))
SH_L = Vector((-SH_X, 0.0, 1.402))

FIST_R = Vector((0.378, 0.180, 0.898))       # 右手：握十字刃
FIST_L = Vector((-0.352, 0.255, 1.005))      # 左手：握盾背把手

HIP_R = Vector((LEG_X, 0.0, Z_HIP))
HIP_L = Vector((-LEG_X, 0.0, Z_HIP))
ANK_R = Vector((LEG_X, 0.015, Z_ANKLE))
ANK_L = Vector((-LEG_X, 0.015, Z_ANKLE))
BALL_R = Vector((LEG_X, 0.120, 0.050))
TOE_R = Vector((LEG_X, 0.196, 0.032))


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


def wrist_of(fist, shoulder):
    return Vector(fist) - (Vector(fist) - Vector(shoulder)).normalized() * WRIST_OFF


WRI_R = wrist_of(FIST_R, SH_R)
WRI_L = wrist_of(FIST_L, SH_L)
ELB_R = ik2(SH_R, WRI_R, L_UPPER, L_FORE, (0.62, -1.05, -0.40))
ELB_L = ik2(SH_L, WRI_L, L_UPPER, L_FORE, (-0.62, -1.05, -0.40))
KNE_R = ik2(HIP_R, ANK_R, L_THIGH, L_SHIN, (0, 1.0, 0.12))
KNE_L = ik2(HIP_L, ANK_L, L_THIGH, L_SHIN, (0, 1.0, 0.12))

HDIR_R = (FIST_R - WRI_R).normalized()
HDIR_L = (FIST_L - WRI_L).normalized()

ARM_D = {1: (ELB_R - SH_R).normalized(), -1: (ELB_L - SH_L).normalized()}

# 十字刃：刃面 = XZ，法线 +Y；骨轴 = +Y（飞出去 = 骨局部 +Y，自旋 = 绕 Y）
BLADE_C = Vector((0.386, 0.352, 0.898))
BLADE_D = 0.360                 # v1 = 0.288；整跨 0.72 m（+25%）
BLADE_SPIN = -20.0              # 十字轻微倾斜，避免正面读成"T"字

# 长面盾
SHIELD_C = Vector((-0.420, 0.312, 1.020))
SH_N = Vector((0.36, 0.928, 0.06)).normalized()
SH_RR = Vector((SH_N.y, -SH_N.x, 0)).normalized()
SH_U = Vector((0, 0, 1))
SH_HALF = 0.214
SH_SPAN = 0.980
FX_K = 0.022


# ── 骨架 ────────────────────────────────────────────────────────────────────
def _bones():
    b = [
        ("root",  (0, 0, 0), (0, 0, 0.14), None),
        ("hips",  (0, 0, Z_HIP), (0, 0, Z_WAIST), "root"),
        ("spine", (0, 0, Z_WAIST), (0, 0, Z_CHEST), "hips"),
        ("chest", (0, 0, Z_CHEST), (0, 0, Z_SHLD), "spine"),
        ("neck",  (0, 0, Z_SHLD), (0, 0, Z_NECK), "chest"),
        ("head",  (0, 0, Z_NECK), (0, 0, 1.72), "neck"),
    ]
    for s, side in ((1, "R"), (-1, "L")):
        sh = SH_R if s > 0 else SH_L
        el = ELB_R if s > 0 else ELB_L
        wr = WRI_R if s > 0 else WRI_L
        hd = HDIR_R if s > 0 else HDIR_L
        b += [
            ("shoulder_" + side, (s * 0.048, 0, 1.390), tuple(sh), "chest"),
            ("upperarm_" + side, tuple(sh), tuple(el), "shoulder_" + side),
            ("forearm_" + side, tuple(el), tuple(wr), "upperarm_" + side),
            ("hand_" + side, tuple(wr), tuple(wr + hd * 0.104), "forearm_" + side),
        ]
        hip = HIP_R if s > 0 else HIP_L
        kne = KNE_R if s > 0 else KNE_L
        ank = ANK_R if s > 0 else ANK_L
        ball = BALL_R if s > 0 else Vector((-LEG_X, 0.120, 0.050))
        toe = TOE_R if s > 0 else Vector((-LEG_X, 0.196, 0.032))
        b += [
            ("thigh_" + side, tuple(hip), tuple(kne), "hips"),
            ("shin_" + side, tuple(kne), tuple(ank), "thigh_" + side),
            ("foot_" + side, tuple(ank), tuple(ball), "shin_" + side),
            ("toe_" + side, tuple(ball), tuple(toe), "foot_" + side),
        ]
    b += [
        ("weapon_R", tuple(FIST_R), tuple(FIST_R + Vector((0, 0.30, 0))), "hand_R"),
        ("weapon_L", tuple(FIST_L), tuple(FIST_L + Vector((0, 0.22, 0))), "hand_L"),
        ("shield", tuple(WRI_L), tuple(WRI_L + Vector((0, 0, 0.30))), "forearm_L"),
        ("fx_cast", tuple(BLADE_C), tuple(BLADE_C + Vector((0, 0.10, 0))), "weapon_R"),
    ]
    return b


BONES = _bones()
BONE_NAMES = [b[0] for b in BONES]

MODULES = ("body", "head", "pauldron", "skirt", "shield", "weapon", "fx")

MATS = {
    "钢":        dict(hexcol="#5D6A7C", metal=0.30, rough=0.42),
    "钢暗":      dict(hexcol="#38414E", metal=0.32, rough=0.48),
    "银":        dict(hexcol="#D6DEE8", metal=0.62, rough=0.20),
    "布":        dict(hexcol="#0E1218", metal=0.02, rough=0.92),
    # 队色必须与方块人 / 建筑完全同一组（assets 规范：换阵营只改这两个）：
    #   team      #2E5FB4  metal 0.00 rough 0.56
    #   team_trim #F1CD79  metal 0.10 rough 0.44
    # 精模原来写的是 #2B57A6 / #C99B45（更暗、更金属），换阵营时会和方块人对不上。
    "team":      dict(hexcol="#2E5FB4", metal=0.00, rough=0.56),
    "team_trim": dict(hexcol="#F1CD79", metal=0.10, rough=0.44),
    "辉":        dict(hexcol="#4FD8FF", metal=0.0, rough=0.26,
                      emit="#4FD8FF", estr=2.6),
}


# ── 通用小件 ────────────────────────────────────────────────────────────────
def dome_patch(name, center, rx, ry, rz, a0, a1, p0, p1, nu, nv, thick):
    """球面片：theta 从 +X 起绕 Z，phi 从 +Z 往下（度）。"""
    grid = []
    for j in range(nv + 1):
        phi = math.radians(p0 + (p1 - p0) * j / nv)
        row = []
        for i in range(nu + 1):
            th = math.radians(a0 + (a1 - a0) * i / nu)
            row.append((center[0] + rx * math.sin(phi) * math.cos(th),
                        center[1] + ry * math.sin(phi) * math.sin(th),
                        center[2] + rz * math.cos(phi)))
        grid.append(row)
    return K.grid_shell(name, grid, thick, inside=center)


def disc(name, center, normal, r, thick, n=8):
    """薄圆盘（倒角轮缘）：平面着色下读成一枚硬圆片，不是球。"""
    c = Vector(center)
    ez = Vector(normal).normalized()
    up = Vector((0, 0, 1))
    if abs(ez.dot(up)) > 0.95:
        up = Vector((0, 1, 0))
    ex = up.cross(ez).normalized()
    ey = ez.cross(ex).normalized()
    rows = []
    for (o, rr) in ((-thick * 0.5, r * 0.80), (-thick * 0.5 + 0.006, r),
                    (thick * 0.5 - 0.006, r), (thick * 0.5, r * 0.80)):
        rows.append([tuple(c + ez * o + ex * (rr * math.cos(math.tau * k / n))
                           + ey * (rr * math.sin(math.tau * k / n))) for k in range(n)])
    return K.loft(name, rows, True)


def ring(name, center, normal, r_in, r_out, thick, n=10):
    """扁环（护喉 / 圆芯外圈 / 靴口）：两个同心棱柱中间挖空。"""
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
    # 环形：侧面 + 内外壁（loft 的 caps 会封成圆盘，这里自己拼）
    verts = [p for r in rows for p in r]
    faces = []
    for i in range(4):
        j = (i + 1) % 4
        for k in range(n):
            k2 = (k + 1) % n
            faces.append((i * n + k, i * n + k2, j * n + k2, j * n + k))
    return KU._obj(name, verts, faces)


def fm(name, p0, p1, r0, r1, a0, a1, nv=2, nu=5, thick=0.024, out=(0, 1, 0)):
    """arc_band 的短写（这个文件里出现太多次）。"""
    return K.arc_band(name, p0, p1, r0, r1, a0, a1, nv, nu, thick, out)


# ── 1. 腿 ───────────────────────────────────────────────────────────────────
def legs(u):
    for s, side in ((1, "R"), (-1, "L")):
        x = s * LEG_X
        thigh, shin, foot, toe = ("thigh_" + side, "shin_" + side,
                                  "foot_" + side, "toe_" + side)
        hip = HIP_R if s > 0 else HIP_L
        kne = KNE_R if s > 0 else KNE_L
        ank = ANK_R if s > 0 else ANK_L
        fwd = (0, 1, 0)

        # 大腿：深色内胆（露在侧面缝里）+ 前外侧甲
        u.olimb("lg_thigh_" + side,
                tuple(hip + Vector((0, 0.004, -0.030))),
                tuple(kne + Vector((0, -0.008, 0.030))),
                [(0.00, 0.166, 0.176, 0.046), (0.55, 0.156, 0.166, 0.043),
                 (1.00, 0.142, 0.150, 0.038)],
                thigh, "布", "facet", "body", "thigh")
        u.add(fm("lg_cuisse_" + side, tuple(hip + Vector((0, 0.002, -0.048))),
                 tuple(kne + Vector((0, -0.008, 0.042))),
                 0.098, 0.085, -116, 116, 3, 5, 0.026, fwd),
              thigh, "钢", "chunk2", "body", "thigh")
        u.add(fm("lg_cuisse_rib_" + side, tuple(hip + Vector((0, 0.002, -0.060))),
                 tuple(kne + Vector((0, -0.008, 0.030))),
                 0.108, 0.095, -9, 9, 3, 1, 0.012, fwd),
              thigh, "银", "chunk", "body", "thigh")
        # 大腿上沿一道金箍（把甲片的起点收干净）
        u.add(fm("lg_cuisse_top_" + side, tuple(hip + Vector((0, 0.002, -0.046))),
                 tuple(hip + Vector((0, 0.002, -0.030))),
                 0.100, 0.102, -112, 112, 1, 5, 0.016, fwd),
              thigh, "team_trim", "chunk", "body", "thigh")

        # 膝：方护膝（比腿宽 3 cm）+ 正面一枚六角盖
        u.otube("lg_knee_" + side,
                [(kne.z + 0.062, x, -0.004, 0.170, 0.176, 0.048),
                 (kne.z + 0.010, x, 0.000, 0.184, 0.190, 0.052),
                 (kne.z - 0.048, x, -0.002, 0.172, 0.178, 0.048)],
                shin, "钢", "chunk2", "body", "knee", cw=0.05)
        u.add(K.plate("lg_knee_cap_" + side,
                      [(x - 0.078, kne.z - 0.004), (x - 0.042, kne.z + 0.084),
                       (x + 0.042, kne.z + 0.084), (x + 0.078, kne.z - 0.004),
                       (x + 0.042, kne.z - 0.092), (x - 0.042, kne.z - 0.092)],
                      thickness=0.020, offset=kne.y + 0.086, axis="Y"),
              shin, "钢暗", "chunk2", "body", "knee")
        u.rivet("lg_knee_stud_" + side, (x, kne.y + 0.110, kne.z - 0.004),
                (0, 1, 0), shin, "team_trim", "hard", "body", "knee", r=0.020, h=0.012)

        # 小腿：内胆 + 胫甲（下摆外张）+ 金靴口
        u.olimb("lg_shin_" + side,
                tuple(kne + Vector((0, 0, -0.010))),
                tuple(ank + Vector((0, 0, 0.052))),
                [(0.00, 0.148, 0.156, 0.040), (0.55, 0.132, 0.142, 0.036),
                 (1.00, 0.116, 0.124, 0.030)],
                shin, "布", "facet", "body", "shin")
        u.add(fm("lg_greave_" + side, tuple(kne + Vector((0, -0.002, -0.036))),
                 tuple(ank + Vector((0, 0.004, 0.062))),
                 0.088, 0.074, -122, 122, 3, 5, 0.022, fwd),
              shin, "钢", "chunk2", "body", "shin")
        u.add(fm("lg_greave_rib_" + side, tuple(kne + Vector((0, -0.002, -0.048))),
                 tuple(ank + Vector((0, 0.004, 0.052))),
                 0.096, 0.082, -8, 8, 3, 1, 0.012, fwd),
              shin, "银", "chunk", "body", "shin")
        u.otube("lg_cuff_" + side,
                [(0.150, x, 0.010, 0.148, 0.156, 0.038),
                 (0.176, x, 0.010, 0.156, 0.164, 0.040),
                 (0.194, x, 0.010, 0.140, 0.148, 0.036)],
                shin, "team_trim", "chunk", "body", "cuff", cw=0.04)

        # 靴：楔形硬盒（前掌宽、后跟窄、脚背一块斜板）
        u.otube("lg_boot_" + side,
                [(0.158, x, 0.010, 0.134, 0.150, 0.030),
                 (0.112, x, 0.030, 0.152, 0.208, 0.036),
                 (0.060, x, 0.070, 0.164, 0.268, 0.040),
                 (0.020, x, 0.088, 0.158, 0.276, 0.038)],
                foot, "钢", "chunk2", "body", "boot")
        u.box("lg_sole_" + side, (x, 0.088, 0.011), (0.168, 0.300, 0.022),
              foot, "布", style="hard", module="body", tag="boot")
        u.otube("lg_toe_cap_" + side,
                [(0.104, x, 0.128, 0.148, 0.108, 0.028),
                 (0.062, x, 0.150, 0.156, 0.124, 0.030),
                 (0.028, x, 0.160, 0.146, 0.126, 0.026)],
                toe, "钢暗", "chunk", "body", "boot", cw=0.03)
        u.box("lg_toe_rim_" + side, (x, 0.176, 0.036), (0.140, 0.026, 0.012),
              toe, "team_trim", style="hard", module="body", tag="boot")
        u.box("lg_heel_" + side, (x, -0.034, 0.056), (0.110, 0.060, 0.084),
              foot, "布", style="chunk", module="body", tag="boot")


# ── 2. 胯 / 腰带 ────────────────────────────────────────────────────────────
def pelvis(u):
    u.otube("bd_hip",
            [(0.836, 0, 0.004, 0.278, 0.214, 0.050),
             (0.900, 0, 0.004, 0.298, 0.230, 0.054),
             (0.966, 0, 0.004, 0.290, 0.222, 0.052),
             (1.016, 0, 0.004, 0.262, 0.204, 0.046)],
            "hips", "布", "facet", "body", "pelvis", cw=0.05)
    u.otube("bd_belt",
            [(0.976, 0, 0.004, 0.304, 0.238, 0.052),
             (1.006, 0, 0.004, 0.314, 0.246, 0.054),
             (1.038, 0, 0.004, 0.306, 0.240, 0.052)],
            "hips", "钢", "chunk2", "body", "belt", cw=0.05)
    u.otube("bd_belt_rim",
            [(1.036, 0, 0.004, 0.308, 0.242, 0.052),
             (1.050, 0, 0.004, 0.296, 0.232, 0.050)],
            "hips", "team_trim", "chunk", "body", "belt", cw=0.05)
    u.box("bd_buckle", (0, 0.132, 1.008), (0.092, 0.030, 0.062),
          "hips", "team_trim", style="chunk", module="body", tag="belt")
    u.box("bd_buckle_in", (0, 0.148, 1.008), (0.040, 0.014, 0.030),
          "hips", "布", style="hard", module="body", tag="belt")


# ── 3. 躯干 ─────────────────────────────────────────────────────────────────
def torso(u):
    u.otube("bd_ab",
            [(1.006, 0, 0.004, 0.248, 0.196, 0.046),
             (1.078, 0, 0.004, 0.258, 0.202, 0.048),
             (1.150, 0, 0.004, 0.276, 0.212, 0.050),
             (1.200, 0, 0.004, 0.292, 0.220, 0.052)],
            "spine", "布", "facet", "body", "abdomen", cw=0.05)
    for i, z in enumerate((1.042, 1.100)):
        u.arc("bd_abband%d" % i,
              [(z - 0.019, -110, 110, 0.152, 0.126),
               (z + 0.019, -110, 110, 0.156, 0.129)],
              0.020, "spine", "钢暗", "chunk", "body", "abdomen", nu=5,
              inside=(0, 0, z))

    u.otube("bd_chest",
            [(1.148, 0, 0.006, 0.276, 0.210, 0.052),
             (1.208, 0, 0.008, 0.330, 0.242, 0.060),
             (1.278, 0, 0.010, 0.372, 0.248, 0.064),
             (1.344, 0, 0.008, 0.356, 0.238, 0.060),
             (1.402, 0, 0.006, 0.302, 0.220, 0.052)],
            "chest", "钢", "chunk2", "body", "chest", cw=0.062)
    # 中脊（一条凸起的棱，不是贴片）
    u.arc("bd_sternum",
          [(1.170, -7, 7, 0.148, 0.118), (1.240, -7, 7, 0.186, 0.138),
           (1.310, -6, 6, 0.192, 0.136), (1.360, -6, 6, 0.170, 0.124)],
          0.018, "chest", "钢暗", "chunk", "body", "chest", nu=2, inside=(0, 0, 1.27))
    # 领口 V 形护板（3 列 → 折面，不是圆弧）
    for s in (1, -1):
        u.add(K.grid_shell("bd_collar_%d" % s, [[
            (s * 0.020, 0.128, 1.404), (s * 0.086, 0.120, 1.396),
            (s * 0.150, 0.092, 1.382)],
            [(s * 0.024, 0.146, 1.356), (s * 0.092, 0.138, 1.348),
             (s * 0.158, 0.104, 1.336)],
            [(s * 0.026, 0.156, 1.304), (s * 0.096, 0.148, 1.296),
             (s * 0.160, 0.110, 1.284)]], 0.024, inside=(0, 0, 1.35)),
            "chest", "钢", "chunk2", "body", "chest")
    # 胸徽：金菱形 + 蓝芯
    u.add(K.plate("bd_sigil", [(-0.046, 1.302), (0.0, 1.354), (0.046, 1.302),
                               (0.0, 1.250)], thickness=0.024, offset=0.150, axis="Y"),
          "chest", "team_trim", "chunk", "body", "sigil")
    u.add(K.plate("bd_sigil_in", [(-0.021, 1.302), (0.0, 1.330), (0.021, 1.302),
                                  (0.0, 1.274)], thickness=0.016, offset=0.162, axis="Y"),
          "chest", "team", "hard", "body", "sigil")
    for s in (1, -1):
        u.rivet("bd_collar_riv_%d" % s, (s * 0.158, 0.106, 1.340), (0, 1, 0.2),
                "chest", "team_trim", "hard", "body", "chest", r=0.014, h=0.010)

    u.otube("bd_gorget",
            [(1.344, 0, 0.006, 0.288, 0.208, 0.050),
             (1.378, 0, 0.006, 0.250, 0.188, 0.044),
             (1.404, 0, 0.004, 0.204, 0.162, 0.036)],
            "chest", "钢暗", "chunk2", "body", "gorget", cw=0.045)
    u.otube("bd_gorget_rim",
            [(1.400, 0, 0.004, 0.208, 0.166, 0.037),
             (1.414, 0, 0.004, 0.196, 0.156, 0.035)],
            "chest", "team_trim", "chunk", "body", "gorget", cw=0.04)


# ── 4. 臂 / 手 ──────────────────────────────────────────────────────────────
def arms(u):
    for s, side in ((1, "R"), (-1, "L")):
        sh = SH_R if s > 0 else SH_L
        el = ELB_R if s > 0 else ELB_L
        wr = WRI_R if s > 0 else WRI_L
        ua, fa = "upperarm_" + side, "forearm_" + side
        d = ARM_D[s]
        out = (s * 1.0, -0.18, 0.0)

        u.olimb("jt_shoulder_" + side, tuple(sh + Vector((0, 0, 0.030))),
                tuple(sh + d * 0.050),
                [(0.0, 0.146, 0.150, 0.040), (1.0, 0.140, 0.144, 0.038)],
                ua, "布", "facet", "body", "joint")
        u.olimb("ar_upper_" + side, tuple(sh + d * 0.006), tuple(el - d * 0.024),
                [(0.00, 0.136, 0.140, 0.036), (0.55, 0.126, 0.130, 0.033),
                 (1.00, 0.116, 0.120, 0.030)],
                ua, "布", "facet", "body", "upper")
        u.add(fm("ar_rere_" + side, tuple(sh + d * 0.012), tuple(el - d * 0.038),
                 0.084, 0.072, -120, 120, 2, 5, 0.024, out),
              ua, "钢", "chunk2", "body", "upper")
        u.add(fm("ar_rere_rim_" + side, tuple(el - d * 0.056), tuple(el - d * 0.034),
                 0.076, 0.080, -116, 116, 1, 5, 0.018, out),
              ua, "team_trim", "chunk", "body", "upper")

        u.olimb("jt_elbow_" + side, tuple(el - d * 0.034), tuple(el + (wr - el).normalized() * 0.034),
                [(0.0, 0.112, 0.116, 0.030), (1.0, 0.112, 0.116, 0.030)],
                fa, "布", "facet", "body", "joint")
        u.add(dome_patch("ar_cop_" + side, tuple(el + Vector((s * 0.006, -0.008, 0.002))),
                         0.072, 0.070, 0.076, -46 if s > 0 else 134,
                         46 if s > 0 else 226, 24, 92, 3, 2, 0.018),
              fa, "钢暗", "chunk", "body", "elbow")
        u.rivet("ar_cop_stud_" + side, tuple(el + Vector((s * 0.060, -0.030, 0.006))),
                (s * 0.6, -0.3, 0.2), fa, "team_trim", "hard", "body", "elbow",
                r=0.016, h=0.010)

        u.olimb("ar_fore_" + side, tuple(el + (wr - el).normalized() * 0.020),
                tuple(wr - (wr - el).normalized() * 0.010),
                [(0.00, 0.118, 0.122, 0.032), (0.55, 0.106, 0.110, 0.028),
                 (1.00, 0.096, 0.100, 0.026)],
                fa, "布", "facet", "body", "fore")
        u.add(fm("ar_vamb_" + side, tuple(el + (wr - el).normalized() * 0.026),
                 tuple(wr - (wr - el).normalized() * 0.014),
                 0.070, 0.062, -134, 134, 2, 5, 0.022, out),
              fa, "钢", "chunk2", "body", "fore")
        u.add(fm("ar_vamb_rib_" + side, tuple(el + (wr - el).normalized() * 0.030),
                 tuple(wr - (wr - el).normalized() * 0.020),
                 0.076, 0.068, -8, 8, 2, 1, 0.011, out),
              fa, "银", "chunk", "body", "fore")
        u.add(disc("ar_cuff_" + side, tuple(wr - (wr - el).normalized() * 0.006),
                   (wr - el), 0.070, 0.028, 10),
              fa, "team_trim", "chunk", "body", "cuff")

    hand(u, "R", FIST_R, HDIR_R)
    hand(u, "L", FIST_L, HDIR_L)


def hand(u, side, fist, hdir):
    bone = "hand_" + side
    fwd = Vector(hdir).normalized()
    up = (Vector((0, 0, 1)) - fwd * fwd.z).normalized()
    right = fwd.cross(up).normalized()
    c = Vector(fist)

    def P(x, y, z):
        return tuple(c + right * x + fwd * y + up * z)

    # 拳：4 点截面的硬方块（不是球）
    rows = []
    for (yy, w, d) in ((-0.058, 0.078, 0.064), (-0.024, 0.098, 0.086),
                       (0.020, 0.102, 0.092), (0.050, 0.090, 0.080),
                       (0.064, 0.062, 0.056)):
        rows.append([P(x, yy, z) for (x, z) in K.octs(w, d, 0.018)])
    u.add(K.loft("ar_fist_" + side, rows), bone, "钢", "chunk", "body", "hand")
    u.box("ar_knuckle_" + side, P(0.0, 0.042, 0.030), (0.090, 0.032, 0.024),
          bone, "银", style="chunk", module="body", tag="hand")
    u.olimb("ar_thumb_" + side, P(0.046, -0.030, 0.006), P(0.020, 0.036, 0.024),
            [(0.0, 0.042, 0.042, 0.012), (1.0, 0.034, 0.034, 0.010)],
            bone, "钢", "chunk", "body", "hand")
    u.box("ar_gripgap_" + side, P(0.0, 0.024, -0.006), (0.076, 0.034, 0.012),
          bone, "布", style="hard", module="body", tag="hand")


# ── 5. 护肩：绕上臂轴的三层锥面叠片 ─────────────────────────────────────────
def pauldrons(u):
    for s, side in ((1, "R"), (-1, "L")):
        sh = SH_R if s > 0 else SH_L
        d = ARM_D[s]
        out = (s * 1.0, -0.16, 0.30)
        base = sh + Vector((s * 0.002, 0, 0.018))

        # 顶盖（把开口封掉，俯视不漏）+ 一圈金边
        u.add(disc("pd_cap_" + side, tuple(base), tuple(-d), 0.080, 0.028, 8),
              "shoulder_" + side, "钢", "chunk2", "pauldron", "cap")
        u.add(ring("pd_cap_rim_" + side, tuple(base - d * 0.004), tuple(-d),
                   0.080, 0.096, 0.020, 8),
              "shoulder_" + side, "team_trim", "chunk", "pauldron", "rim")
        # 三层叠片：每层下沿比上层外扩 14~24 mm，层间露一条暗缝
        u.add(fm("pd_l1_" + side, tuple(base), tuple(base + d * 0.112),
                 0.078, 0.128, -112, 112, 2, 4, 0.032, out),
              "shoulder_" + side, "钢", "chunk2", "pauldron", "pauldron")
        u.add(fm("pd_l1_edge_" + side, tuple(base + d * 0.086), tuple(base + d * 0.108),
                 0.126, 0.132, -108, 108, 1, 4, 0.020, out),
              "shoulder_" + side, "team_trim", "chunk", "pauldron", "rim")
        u.add(fm("pd_l2_" + side, tuple(base + d * 0.104), tuple(base + d * 0.202),
                 0.146, 0.162, -106, 106, 1, 4, 0.030, out),
              "shoulder_" + side, "钢", "chunk2", "pauldron", "lame")
        u.add(fm("pd_l2_edge_" + side, tuple(base + d * 0.180), tuple(base + d * 0.200),
                 0.160, 0.164, -102, 102, 1, 4, 0.018, out),
              "shoulder_" + side, "team_trim", "chunk", "pauldron", "rim")
        u.add(fm("pd_l3_" + side, tuple(base + d * 0.196), tuple(base + d * 0.280),
                 0.176, 0.188, -98, 98, 1, 4, 0.028, out),
              "shoulder_" + side, "钢暗", "chunk2", "pauldron", "lame")
        u.add(fm("pd_l3_edge_" + side, tuple(base + d * 0.264), tuple(base + d * 0.282),
                 0.186, 0.190, -94, 94, 1, 4, 0.018, out),
              "shoulder_" + side, "team_trim", "chunk", "pauldron", "rim")
        # 顶层两枚钉
        for k, yy in enumerate((-0.048, 0.046)):
            u.rivet("pd_stud_%s%d" % (side, k),
                    tuple(base + Vector((s * 0.070, yy, 0.036))),
                    (s * 0.55, yy * 1.2, 0.82), "shoulder_" + side,
                    "team_trim", "hard", "pauldron", "stud", r=0.017, h=0.010)


# ── 6. 腿裙：前 / 侧 / 后 三组刚性甲片（把腿让出来）─────────────────────────
def skirt(u):
    """三组刚性腿裙 + 4 条蓝衬缝。

    v1 是一个闭合钟罩（腿被吞掉、剪影成陀螺）。v2 把裙甲拆成 4 块互相独立的硬片，
    片与片之间留 8° 缝、缝里透出 team 蓝 —— 蓝只走这一处，腿从小腿开始露出来。
    """
    GROUPS = (
        # (名字, a0, a1, [(z, rx, ry)])
        ("front", -38, 38,
         [(1.005, 0.150, 0.120), (0.930, 0.176, 0.142), (0.860, 0.196, 0.160),
          (0.810, 0.210, 0.172), (0.760, 0.222, 0.184)]),
        ("R", 46, 122,
         [(1.005, 0.152, 0.122), (0.920, 0.184, 0.148), (0.820, 0.216, 0.174),
          (0.730, 0.238, 0.192), (0.640, 0.256, 0.206)]),
        ("L", -122, -46,
         [(1.005, 0.152, 0.122), (0.920, 0.184, 0.148), (0.820, 0.216, 0.174),
          (0.730, 0.238, 0.192), (0.640, 0.256, 0.206)]),
        ("back", 148, 212,
         [(1.005, 0.152, 0.122), (0.930, 0.182, 0.146), (0.850, 0.206, 0.166),
          (0.770, 0.226, 0.182), (0.700, 0.240, 0.194)]),
    )

    def rr_at(rs, z):
        if z >= rs[0][0]:
            return rs[0][1], rs[0][2]
        if z <= rs[-1][0]:
            return rs[-1][1], rs[-1][2]
        for i in range(len(rs) - 1):
            if rs[i + 1][0] <= z <= rs[i][0]:
                t = (z - rs[i][0]) / (rs[i + 1][0] - rs[i][0])
                return (rs[i][1] + (rs[i + 1][1] - rs[i][1]) * t,
                        rs[i][2] + (rs[i + 1][2] - rs[i][2]) * t)
        return rs[-1][1], rs[-1][2]

    for (nm, a0, a1, rs) in GROUPS:
        st = [(z, a0, a1, rx, ry) for (z, rx, ry) in rs]
        u.arc("sk_%s" % nm, st, 0.028, "hips", "钢", "chunk2", "skirt", nm,
              nu=5, inside=(0, 0, 0.82))
        zb, rxb, ryb = rs[-1]
        u.arc("sk_%s_hem" % nm,
              [(zb + 0.006, a0, a1, rxb, ryb),
               (zb - 0.016, a0, a1, rxb * 1.010, ryb * 1.010)],
              0.022, "hips", "team_trim", "chunk2", "skirt", "hem", nu=5,
              inside=(0, 0, 0.82))
        u.arc("sk_%s_top" % nm,
              [(1.008, a0, a1, rs[0][1], rs[0][2]),
               (0.990, a0, a1, rs[0][1] + 0.005, rs[0][2] + 0.005)],
              0.020, "hips", "team_trim", "chunk", "skirt", "hem", nu=5,
              inside=(0, 0, 0.82))
        # 侧片两枚长钉（钉在弧面上，不是中轴）
        if nm in ("R", "L"):
            ang = math.radians(84 if nm == "R" else -84)
            for zz in (0.902, 0.748):
                rxv, ryv = rr_at(rs, zz)
                u.rivet("sk_%s_stud%d" % (nm, int(zz * 1000)),
                        (rxv * math.sin(ang), ryv * math.cos(ang), zz),
                        (math.sin(ang), math.cos(ang), 0),
                        "hips", "team_trim", "hard", "skirt", "stud",
                        r=0.016, h=0.010)

    # 前片正中一条金脊，把"围裙"劈成两半
    u.arc("sk_front_rib",
          [(1.000, -7, 7, 0.156, 0.126), (0.930, -7, 7, 0.182, 0.148),
           (0.860, -6, 6, 0.204, 0.168), (0.800, -6, 6, 0.218, 0.180)],
          0.014, "hips", "team_trim", "chunk", "skirt", "rib", nu=2,
          inside=(0, 0, 0.90))

    # 4 条蓝衬缝（塞在片间缝里，比甲面低 8 mm，永远压不着腿）
    for (nm, ac) in (("gf", 42), ("gr", 138), ("gl", -42), ("gb", -138)):
        st = []
        for (z, rx, ry) in ((1.002, 0.146, 0.117), (0.930, 0.170, 0.137),
                            (0.860, 0.190, 0.153), (0.790, 0.208, 0.168)):
            st.append((z, ac - 9, ac + 9, rx, ry))
        u.arc("sk_%s" % nm, st, 0.014, "hips", "team", "chunk2", "skirt", "under",
              nu=2, inside=(0, 0, 0.90))


# ── 7. 头：方盔 ─────────────────────────────────────────────────────────────
# 截面表：(z, 宽, 深)；切角 0.032 —— 侧壁几乎是竖的，顶是平的（大盔，不是子弹头）
_HELM = [(1.392, 0.180, 0.196), (1.420, 0.218, 0.236), (1.466, 0.234, 0.254),
         (1.556, 0.240, 0.260), (1.634, 0.240, 0.258), (1.694, 0.234, 0.250),
         (1.728, 0.222, 0.236), (1.752, 0.192, 0.204), (1.762, 0.120, 0.130)]
_HELM_Y = 0.010
_HELM_C = 0.032


def _se(a, w, d):
    """角度 0 = +Y 正前（与 arc_panel 同口径），正角往 +X 转 —— 射线打切角方截面。"""
    pts = K.octs(w, d, _HELM_C)
    dx, dy = math.sin(a), math.cos(a)     # 射线方向
    best = None
    n = len(pts)
    for i in range(n):
        ax, ay = pts[i]
        bx, by = pts[(i + 1) % n]
        ex, ey = bx - ax, by - ay
        den = dx * ey - dy * ex
        if abs(den) < 1e-12:
            continue
        t = (ax * ey - ay * ex) / den            # 沿射线的距离
        u = (ax * dy - ay * dx) / den            # 沿边的参数
        if t > 0 and -1e-9 <= u <= 1.0 + 1e-9:
            if best is None or t > best:
                best = t
    if best is None:
        best = max(w, d) * 0.5
    return (best * dx, best * dy)


def _helm_wd(z):
    if z <= _HELM[0][0]:
        return _HELM[0][1], _HELM[0][2]
    if z >= _HELM[-1][0]:
        return _HELM[-1][1], _HELM[-1][2]
    for i in range(len(_HELM) - 1):
        z0, w0, d0 = _HELM[i]
        z1, w1, d1 = _HELM[i + 1]
        if z0 <= z <= z1:
            t = (z - z0) / (z1 - z0)
            return w0 + (w1 - w0) * t, d0 + (d1 - d0) * t
    return _HELM[-1][1], _HELM[-1][2]


def helm_pt(a, z, off=1.0):
    w, d = _helm_wd(z)
    x, y = _se(a, w * off, d * off)
    return (x, y + _HELM_Y, z)


def helm_patch(name, zs, a0, a1, nu, off, thick):
    grid = []
    for z in zs:
        row = []
        for i in range(nu + 1):
            a = math.radians(a0 + (a1 - a0) * i / nu)
            row.append(helm_pt(a, z, off))
        grid.append(row)
    return K.grid_shell(name, grid, thick,
                        inside=(0, _HELM_Y, sum(zs) / len(zs)))


def head(u):
    u.olimb("jt_neck2", (0, 0.006, 1.320), (0, 0.006, 1.456),
            [(0.0, 0.150, 0.150, 0.040), (1.0, 0.136, 0.136, 0.036)],
            "neck", "布", "facet", "head", "neck")

    rows = []
    for (z, w, d) in _HELM:
        rows.append([(x, y + _HELM_Y, z) for (x, y) in K.octs(w, d, _HELM_C)])
    u.add(K.loft("hd_helm", rows), "head", "钢", "chunk2", "head", "helm")

    # 下颌面甲（到眼缝下沿）
    u.add(helm_patch("hd_chin", [1.398, 1.444, 1.492, 1.538], -66, 66, 8, 1.008, 0.016),
          "head", "钢暗", "chunk2", "head", "chin")
    # 眼缝：正面那一块折面上的一条暗槽（切角方盔的正面只有 ±34°）
    u.add(helm_patch("hd_slit", [1.538, 1.590], -34, 34, 4, 1.004, 0.012),
          "head", "布", "chunk", "head", "slit")
    # 两道蓝眼（矩形，不是圆点）
    for s2 in (1, -1):
        u.add(helm_patch("hd_eye_%d" % s2, [1.548, 1.580],
                         6 * s2, 31 * s2, 3, 1.030, 0.012),
              "head", "辉", "hard", "head", "eye")
    # 鼻梁：把眼缝劈成两道（俯视也认得出这是脸）
    u.add(helm_patch("hd_nose", [1.502, 1.552, 1.598], -7, 7, 2, 1.022, 0.028),
          "head", "钢", "chunk", "head", "nose")
    # 眉脊（金）：压在眼缝上沿，出一道硬投影
    u.add(helm_patch("hd_brow", [1.590, 1.618], -38, 38, 5, 1.018, 0.018),
          "head", "team_trim", "chunk", "head", "brow")
    # 眉心宝石
    bp = helm_pt(0, 1.640, 1.020)
    u.add(K.plate("hd_gem", [(-0.019, 1.662), (0.0, 1.684), (0.019, 1.662),
                             (0.0, 1.640)], thickness=0.018,
                  offset=bp[1] - 0.006, axis="Y"),
          "head", "team_trim", "chunk", "head", "brow")
    # 颊钉
    for s3 in (1, -1):
        cp = helm_pt(math.radians(s3 * 56), 1.496, 1.014)
        u.rivet("hd_cheek_%d" % s3, cp,
                (math.sin(math.radians(s3 * 56)), math.cos(math.radians(s3 * 56)), 0),
                "head", "team_trim", "hard", "head", "cheek", r=0.020, h=0.012)

    # 冠鳍：一片薄鳍，从额顶后掠（硬三角梳，不是圆丘/马尾）
    rows = []
    for (y, z, h) in ((0.086, 1.712, 0.006), (0.040, 1.750, 0.030),
                      (-0.014, 1.756, 0.042), (-0.068, 1.742, 0.030),
                      (-0.112, 1.716, 0.014), (-0.138, 1.690, 0.002)):
        rows.append([(-0.030, y, z), (0.030, y, z), (0.030, y - 0.006, z + h * 0.82),
                     (0.0, y - 0.013, z + h), (-0.030, y - 0.006, z + h * 0.82)])
    u.add(K.loft("hd_crest", rows), "head", "钢", "chunk", "head", "crest")

    # 后颈护 + 盔底金箍
    u.add(dome_patch("hd_nape", (0, 0.006, 1.512), 0.132, 0.140, 0.150,
                     104, 256, 44, 104, 6, 2, 0.020),
          "head", "钢", "chunk2", "head", "nape")
    u.add(helm_patch("hd_helm_rim", [1.388, 1.412], -180, 180, 22, 1.012, 0.014),
          "head", "team_trim", "chunk", "head", "rim")


# ── 8. 长面盾 ───────────────────────────────────────────────────────────────
def sh_pt(uu, v, depth=0.0, scale=1.0):
    """盾面坐标：uu∈[-1,1] 横向，v∈[0,1] 从上到下；depth 沿面法线。"""
    w = SH_HALF * scale * (1.0 - 0.90 * max(0.0, v) ** 2.55)
    z = (SHIELD_C.z + SH_SPAN * 0.5) - v * SH_SPAN
    bow = 0.070 * (1.0 - uu * uu) * scale
    return SHIELD_C + SH_RR * (uu * w) + SH_U * (z - SHIELD_C.z) + SH_N * (bow + depth)


def shield(u):
    grid = [[sh_pt(i / 6 * 2 - 1, j / 8, 0.0) for i in range(7)] for j in range(9)]
    u.add(K.grid_shell("sh_body", grid, 0.022, inside=tuple(SHIELD_C - SH_N * 0.30)),
          "shield", "钢", "chunk2", "shield", "body")

    gridr = [[sh_pt((i / 6 * 2 - 1) * 0.960, 0.014 + j / 8 * 0.968, 0.019, 0.980)
              for i in range(7)] for j in range(9)]
    u.add(K.grid_shell("sh_rim", gridr, 0.020, inside=tuple(SHIELD_C - SH_N * 0.30)),
          "shield", "team_trim", "chunk2", "shield", "rim")

    grid2 = [[sh_pt((i / 6 * 2 - 1) * 0.880, 0.042 + j / 8 * 0.906, 0.030, 0.935)
              for i in range(7)] for j in range(9)]
    u.add(K.grid_shell("sh_face", grid2, 0.016, inside=tuple(SHIELD_C - SH_N * 0.30)),
          "shield", "team", "chunk2", "shield", "face")

    vgrid = [[sh_pt(-0.058, 0.11 + j / 6 * 0.78, 0.042),
              sh_pt(0.0, 0.11 + j / 6 * 0.78, 0.050),
              sh_pt(0.058, 0.11 + j / 6 * 0.78, 0.042)] for j in range(7)]
    u.add(K.grid_shell("sh_rib_v", vgrid, 0.018,
                       inside=tuple(SHIELD_C - SH_N * 0.30)),
          "shield", "银", "chunk", "shield", "rib")

    hgrid = [[sh_pt(uu, 0.244 + j * 0.016, 0.042) for uu in
              (-0.66, -0.34, 0.0, 0.34, 0.66)] for j in range(3)]
    u.add(K.grid_shell("sh_rib_h", hgrid, 0.016,
                       inside=tuple(SHIELD_C - SH_N * 0.30)),
          "shield", "银", "chunk", "shield", "rib")

    c = sh_pt(0.0, 0.400, 0.058)
    u.add(ring("sh_boss", tuple(c), tuple(SH_N), 0.052, 0.090, 0.030, 12),
          "shield", "team_trim", "chunk", "shield", "boss")
    u.add(disc("sh_core", tuple(c + SH_N * 0.014), SH_N, 0.050, 0.020, 12),
          "shield", "辉", "chunk", "shield", "boss")
    # 沿边一圈金钉
    for i in range(10):
        t = 0.06 + 0.88 * i / 9
        p = sh_pt(-0.905, t, 0.026, 0.985)
        q = sh_pt(0.905, t, 0.026, 0.985)
        for pp in (p, q):
            u.rivet("sh_riv_%.2f_%d" % (t, 1 if pp is p else -1), tuple(pp), SH_N,
                    "shield", "team_trim", "hard", "shield", "rim", r=0.010, h=0.008)

    back = SHIELD_C - SH_N * 0.040
    u.box("sh_grip", tuple(back + SH_U * 0.010), (0.034, 0.150, 0.042),
          "shield", "布", style="chunk", module="shield", tag="back")
    for i, dz in enumerate((0.210, -0.170)):
        u.box("sh_strap%d" % i, tuple(back + SH_U * dz), (0.260, 0.032, 0.058),
              "shield", "布", style="hard", module="shield", tag="back")


# ── 9. 十字利刃（D = 0.40，整跨 0.80 m）─────────────────────────────────────
def blade(u):
    c = BLADE_C
    u.add(disc("wp_hub", tuple(c), (0, 1, 0), 0.068, 0.054, 10), "weapon_R",
          "钢", "chunk", "weapon", "hub")
    u.add(ring("wp_hub_ring", tuple(c), (0, 1, 0), 0.050, 0.066, 0.030, 10),
          "weapon_R", "team_trim", "chunk", "weapon", "hub")
    for s in (1, -1):
        u.add(disc("wp_core_%d" % s, tuple(c + Vector((0, s * 0.026, 0))), (0, 1, 0),
                   0.026, 0.014, 8), "weapon_R", "辉", "hard", "weapon", "core")

    # 四把**直刃**：靠根 39% 等宽（读成刀身），之后一条直线收到尖。
    # v2 早期版本用的是"叶形收腰"，在俯视里读成四片花瓣 —— 等宽段是关键。
    spin = math.radians(BLADE_SPIN)
    for i in range(4):
        a = math.radians(90 * i) + spin
        ex = Vector((math.cos(a), 0, math.sin(a)))
        ey = Vector((-math.sin(a), 0, math.cos(a)))
        rows = []
        for (t, w, th, back) in ((0.130, 0.062, 0.020, 0.000),
                                 (0.520, 0.059, 0.017, 0.004),
                                 (0.730, 0.041, 0.013, 0.009),
                                 (0.885, 0.022, 0.008, 0.013),
                                 (1.000, 0.004, 0.002, 0.017)):
            r = 0.058 + (BLADE_D - 0.058) * t
            ctr = c + ex * r + ey * back
            rows.append([tuple(ctr + ey * (w * 0.50) + Vector((0, th * 0.10, 0))),
                         tuple(ctr + ey * (w * 0.20) + Vector((0, th * 0.52, 0))),
                         tuple(ctr + ey * (-w * 0.20) + Vector((0, th * 0.52, 0))),
                         tuple(ctr + ey * (-w * 0.50) + Vector((0, th * 0.10, 0))),
                         tuple(ctr + ey * (-w * 0.20) + Vector((0, -th * 0.52, 0))),
                         tuple(ctr + ey * (w * 0.20) + Vector((0, -th * 0.52, 0)))])
        u.add(K.loft("wp_arm%d" % i, rows), "weapon_R", "银", "facet", "weapon", "arm")

        # 刃身正反两面各压一条钢色血槽 —— 把"白锥子"劈成 边/槽/边 三段明度
        for f in (1, -1):
            srows = []
            for (t, w2, off) in ((0.150, 0.017, 0.0), (0.500, 0.014, 0.003),
                                 (0.700, 0.009, 0.006)):
                r = 0.058 + (BLADE_D - 0.058) * t
                ctr = c + ex * r + ey * (off * 4)
                srows.append([tuple(ctr + ey * (w2 * 0.5) + Vector((0, f * 0.0112, 0))),
                              tuple(ctr + ey * (w2 * 0.5) + Vector((0, f * 0.0080, 0))),
                              tuple(ctr + ey * (-w2 * 0.5) + Vector((0, f * 0.0080, 0))),
                              tuple(ctr + ey * (-w2 * 0.5) + Vector((0, f * 0.0112, 0)))])
            u.add(K.loft("wp_fuller%d_%d" % (i, f), srows), "weapon_R", "钢",
                  "facet", "weapon", "arm")

        # 刃根一小段钢色护片，压住刃与毂的交界
        u.add(disc("wp_arm_root%d" % i, tuple(c + ex * 0.064), tuple((0, 1, 0)),
                   0.034, 0.026, 6), "weapon_R", "钢", "chunk", "weapon", "hub")

    u.add(K.olimb("wp_grip", tuple(c - Vector((0, 0.134, 0))),
                  tuple(c - Vector((0, 0.016, 0))),
                  [(0.0, 0.050, 0.050, 0.012), (1.0, 0.046, 0.046, 0.010)]),
          "weapon_R", "布", "chunk", "weapon", "grip")
    u.add(disc("wp_pommel", tuple(c - Vector((0, 0.140, 0))), (0, 1, 0),
               0.040, 0.024, 8), "weapon_R", "team_trim", "chunk", "weapon", "grip")


# ── 10. 施法闪电（fx_cast 骨：静止 scale=FX_K，施法放大到 1）──────────────
def fx(u):
    k = FX_K
    for i in range(4):
        a = math.radians(28 + i * 92)
        pts = []
        for j in range(6):
            t = j / 5
            r = 0.100 + 0.062 * t
            ang = a + 0.42 * math.sin(t * 7.0 + i * 1.7)
            z = -0.12 + 0.40 * t
            pts.append(BLADE_C + (Vector((r * math.cos(ang), 0.020 * math.sin(t * 9 + i),
                                          z + r * math.sin(ang) * 0.35)) * k))
        rows = []
        for j, p in enumerate(pts):
            w = 0.012 * (1.0 - 0.5 * j / 5) * k
            side = (pts[min(j + 1, 5)] - pts[max(j - 1, 0)]).normalized().cross(
                Vector((0, 1, 0))).normalized()
            rows.append([tuple(p + side * w), tuple(p + Vector((0, w * 0.5, 0))),
                         tuple(p - side * w), tuple(p - Vector((0, w * 0.5, 0)))])
        u.add(K.loft("fx_arc%d" % i, rows), "fx_cast", "辉", "sharp", "fx", "arc")

    for i, (r, z, sq) in enumerate(((0.132, 0.010, 1.0), (0.190, 0.060, 0.55))):
        rows = []
        for o in (-0.007, 0.007):
            rows.append([tuple(BLADE_C + Vector((r * math.cos(math.tau * kk / 16) * k,
                                                 r * math.sin(math.tau * kk / 16) * k * sq,
                                                 (z + o) * k))) for kk in range(16)])
        u.add(K.loft("fx_ring%d" % i, rows), "fx_cast", "辉", "sharp", "fx", "ring")


# ── 组装 ────────────────────────────────────────────────────────────────────
def build(low=False, modules=None, fx_scale=None):
    want = set(MODULES if modules is None else modules)
    u = K.Unit2(PREFIX, MATS, low=low)
    if "body" in want:
        legs(u)
        pelvis(u)
        torso(u)
        arms(u)
    if "pauldron" in want:
        pauldrons(u)
    if "skirt" in want:
        skirt(u)
    if "head" in want:
        head(u)
    if "shield" in want:
        shield(u)
    if "weapon" in want:
        blade(u)
    if "fx" in want:
        fx(u)
    return u


def build_rig(name="RIG_破法者"):
    return K.build_rig(BONES, name)


def report():
    return "\n".join([
        "[joints] hip=%.3f knee=(%.3f,%.3f) ankle=%.3f" % (Z_HIP, KNE_R.y, KNE_R.z, Z_ANKLE),
        "[armR] elbow=(%.3f,%.3f,%.3f) wrist=(%.3f,%.3f,%.3f) reach=%.3f/%.3f"
        % (ELB_R.x, ELB_R.y, ELB_R.z, WRI_R.x, WRI_R.y, WRI_R.z,
           (WRI_R - SH_R).length, L_UPPER + L_FORE),
        "[armL] elbow=(%.3f,%.3f,%.3f) wrist=(%.3f,%.3f,%.3f) reach=%.3f/%.3f"
        % (ELB_L.x, ELB_L.y, ELB_L.z, WRI_L.x, WRI_L.y, WRI_L.z,
           (WRI_L - SH_L).length, L_UPPER + L_FORE),
        "[blade] c=(%.3f,%.3f,%.3f) span=%.2f" % (BLADE_C.x, BLADE_C.y, BLADE_C.z, BLADE_D * 2),
        "[shield] c=(%.3f,%.3f,%.3f) span=%.2f" % (SHIELD_C.x, SHIELD_C.y, SHIELD_C.z, SH_SPAN),
        "[bones] %d" % len(BONES),
    ])
