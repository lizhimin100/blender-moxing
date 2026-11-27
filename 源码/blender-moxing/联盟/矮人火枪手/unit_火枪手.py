"""unit_火枪手.py —— 联盟·矮人火枪手（组件化方块人）

造型口径（承接 联盟步兵 / 弩兵 的方块人语言）：
  * 1 unit = 1 m，+Y 正面，脚底 z = 0，原点在双足中间；
  * 硬表面只倒角、有机体只用 Catmull-Clark，**永不叠加**；
  * 一块 = 一根骨、权重 1.0（刚性蒙皮），关节留缝、缝里塞更细的深色关节轴。

**方块人语言（与步兵/弩兵同一套，硬约束）**：
  * 四肢 = 4 点截面方棱柱（`blimb`），躯干/头/盔 = 矩形截面放样 + 平面着色；
  * 不用球、不用弧壳、不用 6/8 边圆管；全靠"块 + 小倒角 + 明度分档"出层次；
  * 手 = 一块方拳 + 一道指缝（不套手指/拇指）；胡子上不放任何金饰。

矮人的三条读感（与人类单位的区别**只靠比例**，不是整体缩放）：
  ① 3.5 头身、肩宽/身高 0.47、腿长/身高 0.36 —— 宽、短、厚；
  ② 头颈：**方桶盔**（四棱台 + 方檐 + 蓝帽箍）+ 前突方鼻 + **方辫大胡子**（第二剪影）；
  ③ 武器：**长管火枪** 1.08 m（比人还高），扛在右肩、枪口在盔顶之上 ——
     竖向道具是 RTS 俯角下最强的识别手段；左手扶腰带。
  * 联盟符号（三尖金冠）落在**胸前垂布中央**，与弩兵同一位；盔上不放徽。

组件化（MODULES）：五层，每层可单独 build / 导出 / 换装
  body     种族躯体（腿 / 胯 / 躯干 / 臂 / 手）
  head     头颅 + 桶盔 + 胡子
  shoulder 护肩（弧壳 + 三层叠片）
  gear     火药角 / 弹囊（可整组摘掉做轻装）
  weapon   火枪（独立 glb，挂 weapon_R，可插到任何有该插槽的单位上）

新增零件：parts 里加一行 + MODULE_OF 补一条前缀归属。
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

import unitkit as K  # noqa: E402

NAME = "方块人_矮人火枪手"

# ── 尺寸表（m）──────────────────────────────────────────────────────────────
Z_HIP = 0.520
Z_WAIST = 0.640
Z_CHEST = 0.780
Z_SHLD = 0.955
Z_NECK = 1.010
Z_HEADTOP = 1.290
Z_KNEE = 0.358
Z_ANKLE = 0.195
Z_BALL = 0.055
Z_TOE = 0.030
LEG_X = 0.132
HIP_X = 0.108
SH_X = 0.256
SH_Z = 0.900

# 武器：扛肩姿。握把在右胯前，枪管向上向后 30° —— 枪口过盔顶，是最强的竖向识别点
GUN_G = Vector((0.314, 0.292, 0.700))
GUN_A = Vector((0.05, -0.375, 0.926)).normalized()
GUN_L_BACK = 0.300
GUN_L_FWD = 0.800
WRIST_OFF = 0.072

BEARD_Z0, BEARD_Z1 = 0.780, 1.045


def _gun_axes():
    ez = (Vector((0, 0, 1)) - GUN_A * GUN_A.z).normalized()   # 枪的"上" ≈ 朝前
    ex = -(GUN_A.cross(ez)).normalized()                       # 枪的"右" ≈ +X
    return ex, ez


GX, GZ = _gun_axes()


def GP(x, y, z):
    """武器局部 → 世界：(x 侧向, y 沿枪管, z 枪面法线的"上")。"""
    return GUN_G + GX * x + GUN_A * y + GZ * z


# ── 骨架：先定关节，再定部件 ───────────────────────────────────────────────
def ik2(root, target, l1, l2, pole):
    root, target = Vector(root), Vector(target)
    d = target - root
    dist = min(d.length, (l1 + l2) * 0.9995)
    dn = d.normalized()
    a = (l1 * l1 - l2 * l2 + dist * dist) / (2 * dist)
    h = math.sqrt(max(l1 * l1 - a * a, 0.0))
    p = Vector(pole) - dn * Vector(pole).dot(dn)
    if p.length < 1e-6:
        p = Vector((0, 0, 1)) - dn * dn.z
    p.normalize()
    return root + dn * a + p * h


L_UPPER, L_FORE = 0.232, 0.222       # 臂展 0.454（矮人短臂）
L_THIGH = (Vector((LEG_X, 0.035, Z_KNEE)) - Vector((HIP_X, 0, Z_HIP))).length
L_SHIN = (Vector((LEG_X, 0.015, Z_ANKLE)) - Vector((LEG_X, 0.035, Z_KNEE))).length

SH_R = Vector((SH_X, 0.0, SH_Z))
SH_L = Vector((-SH_X, 0.0, SH_Z))


def _wrist(anchor, fist):
    """腕骨 = 拳心沿"拳→肘"方向回退 45 mm（手不是套在枪管上）。"""
    return Vector(fist) - (Vector(fist) - Vector(anchor)).normalized() * WRIST_OFF


FIST_R = GUN_G.copy()                                   # 右拳握枪
FIST_L = Vector((-0.196, 0.206, 0.650))                 # 左拳搭在左胯/腰带上
_W0 = _wrist(SH_R, FIST_R)
_E0 = ik2(SH_R, _W0, L_UPPER, L_FORE, (0.55, -1.10, -0.45))
WRI_R = _wrist(_E0, FIST_R)
ELB_R = ik2(SH_R, WRI_R, L_UPPER, L_FORE, (0.55, -1.10, -0.45))
_W1 = _wrist(SH_L, FIST_L)
_E1 = ik2(SH_L, _W1, L_UPPER, L_FORE, (-0.55, -1.10, -0.45))
WRI_L = _wrist(_E1, FIST_L)
ELB_L = ik2(SH_L, WRI_L, L_UPPER, L_FORE, (-0.55, -1.10, -0.45))

HIP_R = Vector((HIP_X, 0.0, Z_HIP))
HIP_L = Vector((-HIP_X, 0.0, Z_HIP))
ANK_R = Vector((LEG_X, 0.015, Z_ANKLE))
ANK_L = Vector((-LEG_X, 0.015, Z_ANKLE))
KNE_R = ik2(HIP_R, ANK_R, L_THIGH, L_SHIN, (0, 1.0, 0.15))
KNE_L = ik2(HIP_L, ANK_L, L_THIGH, L_SHIN, (0, 1.0, 0.15))

HDIR_R = (FIST_R - ELB_R).normalized()
HDIR_L = (FIST_L - ELB_L).normalized()

ROD_Z = -0.072
ROD0 = GP(0.0, 0.020, ROD_Z)
ROD1 = GP(0.0, 0.560, ROD_Z)


def _bones():
    b = [
        ("root",  (0, 0, 0),        (0, 0, 0.12),      None),
        ("hips",  (0, 0, Z_HIP),    (0, 0, Z_WAIST),   "root"),
        ("spine", (0, 0, Z_WAIST),  (0, 0, Z_CHEST),   "hips"),
        ("chest", (0, 0, Z_CHEST),  (0, 0, Z_SHLD),    "spine"),
        ("neck",  (0, 0, Z_SHLD),   (0, 0, Z_NECK),    "chest"),
        ("head",  (0, 0, Z_NECK),   (0, 0, Z_HEADTOP), "neck"),
    ]
    for s, side in ((1, "R"), (-1, "L")):
        sh = SH_R if s > 0 else SH_L
        el = ELB_R if s > 0 else ELB_L
        wr = WRI_R if s > 0 else WRI_L
        hd = HDIR_R if s > 0 else HDIR_L
        b += [
            ("shoulder_" + side, (s * 0.060, 0, 0.936), tuple(sh), "chest"),
            ("upperarm_" + side, tuple(sh), tuple(el), "shoulder_" + side),
            ("forearm_" + side, tuple(el), tuple(wr), "upperarm_" + side),
            ("hand_" + side, tuple(wr), tuple(wr + hd * 0.105), "forearm_" + side),
        ]
        hip = HIP_R if s > 0 else HIP_L
        kne = KNE_R if s > 0 else KNE_L
        ank = ANK_R if s > 0 else ANK_L
        b += [
            ("thigh_" + side, tuple(hip), tuple(kne), "hips"),
            ("shin_" + side, tuple(kne), tuple(ank), "thigh_" + side),
            ("foot_" + side, tuple(ank), (s * LEG_X, 0.115, Z_BALL), "shin_" + side),
            ("toe_" + side, (s * LEG_X, 0.115, Z_BALL), (s * LEG_X, 0.192, Z_TOE), "foot_" + side),
        ]
    b += [
        ("weapon_R", tuple(GUN_G), tuple(GUN_G + GUN_A * 0.30), "hand_R"),
        ("prop_ramrod", tuple(ROD0), tuple(ROD1), "weapon_R"),
        ("weapon_L", tuple(FIST_L), tuple(FIST_L + (FIST_L - ELB_L).normalized() * 0.20), "hand_L"),
    ]
    return b


BONES = _bones()
BONE_NAMES = [b[0] for b in BONES]

MODULE_OF = [
    ("lg_", "body"), ("bd_", "body"), ("ar_", "body"), ("jt_", "body"),
    ("hd_", "head"), ("bm_", "head"),
    ("pd_", "shoulder"),
    ("gr_", "gear"),
    ("wp_", "weapon"),
]
MODULES = ("body", "head", "shoulder", "gear", "weapon")


def module_of(part_name):
    for pre, mod in MODULE_OF:
        if part_name.startswith(pre):
            return mod
    return "body"


# ── 几何 helpers（方块人语言：4 点截面 + 平面着色）──────────────────────────
def blimb(name, p0, p1, secs, ch=0.018, up=(0, 0, 1)):
    """沿 p0→p1 的方截面肢体（4 点倒角截面 = 方块人语言）。"""
    p0v, ex, ey, ez = K.frame(p0, p1, up)
    L = (Vector(p1) - p0v).length
    rows = []
    for (t, w, d) in secs:
        c = p0v + ez * (L * t)
        rows.append([tuple(c + ex * x + ey * y) for (x, y) in K.poly_rect(w, d, ch)])
    return K.loft(name, rows)


def scrown(u, cx, cz, h, y, bone, w=None, pre="gr_"):
    """三尖金冠（与建筑垂旗同一枚）：冠带 + 三尖 + 三宝石。"""
    w = w or h * 0.66
    u.plate(pre + "crown_band", [(cx - w, cz), (cx + w, cz), (cx + w, cz + h * 0.26),
                                 (cx - w, cz + h * 0.26)], bone, "team_trim",
            axis="Y", thickness=0.010, offset=y, bevel=0.002, smooth=False)
    for i, (a, b, top) in enumerate(((-0.96, -0.28, 0.74), (-0.20, 0.20, 1.00),
                                     (0.28, 0.96, 0.74))):
        u.plate(pre + "crown_sp%d" % i,
                [(cx + a * w, cz + h * 0.24), (cx + b * w, cz + h * 0.24),
                 (cx + (a + b) * 0.5 * w, cz + h * top)],
                bone, "team_trim", axis="Y", thickness=0.011, offset=y + 0.001,
                bevel=0.0015, smooth=False)
    for i, uu in enumerate((-0.56, 0.0, 0.56)):
        g = h * 0.05
        u.plate(pre + "crown_gem%d" % i,
                [(cx + uu * w - g, cz + h * 0.05), (cx + uu * w + g, cz + h * 0.05),
                 (cx + uu * w + g, cz + h * 0.17), (cx + uu * w - g, cz + h * 0.17)],
                bone, "iron", axis="Y", thickness=0.012, offset=y + 0.003,
                bevel=0.0012, smooth=False)


# ── 1. 腿（方棱柱大腿/小腿 + 方靴）──────────────────────────────────────────
def legs(u, detail=1):
    for s, side in ((1, "R"), (-1, "L")):
        x = s * LEG_X
        foot, shin, thigh = "foot_" + side, "shin_" + side, "thigh_" + side

        # 靴：底 / 筒 / 包头 / 口沿（四件都是方盒）
        u.box("lg_sole_" + side, (x, 0.052, 0.019), (0.198, 0.332, 0.038),
              foot, "earth_dark", bevel=0.006, seg=1)
        u.add(blimb("lg_boot_" + side, (x, 0.020, 0.030), (x, 0.012, 0.188),
                    [(0.0, 0.188, 0.302), (0.55, 0.182, 0.266), (1.0, 0.178, 0.232)],
                    ch=0.020),
              foot, "leather_dark", 0.008, 2, 0, False)
        u.box("lg_toe_" + side, (x, 0.196, 0.056), (0.180, 0.108, 0.064),
              foot, "steel_dark", bevel=0.008, seg=1)
        u.box("lg_cuff_" + side, (x, 0.010, 0.180), (0.192, 0.242, 0.034),
              foot, "leather", bevel=0.005, seg=1)
        if detail:
            u.box("lg_strap_" + side, (x, 0.020, 0.132), (0.202, 0.038, 0.026),
                  foot, "leather_dark", bevel=0.003, seg=1)
            u.box("lg_buckle_" + side, (s * 0.104, 0.020, 0.132), (0.020, 0.046, 0.030),
                  foot, "gold", bevel=0.0025, seg=1)

        # 踝缝
        u.box("jt_ankle_" + side, (x, 0.014, 0.192), (0.128, 0.134, 0.028),
              shin, "cloth_dark", bevel=0.003, seg=1)

        # 小腿（方）+ 护胫（平板）+ 亮脊
        u.add(blimb("lg_shin_" + side, (x, 0.010, 0.198), (x, 0.006, 0.354),
                    [(0.0, 0.168, 0.182), (0.45, 0.162, 0.176), (1.0, 0.158, 0.170)],
                    ch=0.022),
              shin, "cloth_dark", 0.008, 2, 0, False)
        u.box("lg_greave_" + side, (x, 0.072, 0.288), (0.128, 0.056, 0.134),
              shin, "steel_dark", bevel=0.009, seg=2)
        u.box("lg_greave_rib_" + side, (x, 0.104, 0.288), (0.036, 0.018, 0.128),
              shin, "steel_light", bevel=0.004, seg=1)

        # 膝 + 膝缝
        u.box("lg_poleyn_" + side, (x, 0.056, 0.366), (0.148, 0.112, 0.070),
              shin, "steel", bevel=0.011, seg=2)
        u.box("jt_knee_" + side, (x, -0.004, 0.360), (0.150, 0.158, 0.030),
              thigh, "cloth_dark", bevel=0.003, seg=1)

        # 大腿（方）+ 腿甲
        u.add(blimb("lg_thigh_" + side, (x, 0.006, 0.368), (s * HIP_X, 0.0, 0.518),
                    [(0.0, 0.160, 0.174), (0.55, 0.172, 0.186), (1.0, 0.178, 0.192)],
                    ch=0.024),
              thigh, "cloth_dark", 0.008, 2, 0, False)
        u.box("lg_cuisse_" + side, (x, 0.078, 0.456), (0.142, 0.058, 0.118),
              thigh, "steel_dark", bevel=0.008, seg=2)


# ── 2. 胯 / 腰带 / 裙甲 ────────────────────────────────────────────────────
def hips(u, detail=1):
    rows = [[(x, y, z) for (x, y) in K.poly_rect(w, d, ch)]
            for (z, w, d, ch) in ((0.500, 0.332, 0.284, 0.046),
                                  (0.558, 0.358, 0.300, 0.050),
                                  (0.624, 0.374, 0.310, 0.052))]
    u.loft("bd_pelvis", rows, "hips", "cloth_dark", bevel=0.006, seg=2, sub=0, smooth=False)

    u.tube("bd_belt", [(0.594, 0, 0.0, 0.400, 0.326, 0.052),
                       (0.650, 0, 0.0, 0.394, 0.320, 0.052)],
           "hips", "team", bevel=0.005, seg=1, smooth=False)
    u.box("bd_buckle", (0, 0.176, 0.622), (0.096, 0.032, 0.058),
          "hips", "gold", bevel=0.007, seg=2)
    u.box("bd_buckle_in", (0, 0.194, 0.622), (0.044, 0.014, 0.026),
          "hips", "iron", bevel=0.003, seg=1)
    if detail:
        for s in (1, -1):
            u.box("bd_belt_stud_%d" % s, (s * 0.156, 0.114, 0.624), (0.026, 0.026, 0.026),
                  "hips", "iron", bevel=0.003, seg=1)

    # 裙甲：五片扁方板挂在腰带下（正面三片亮、两侧暗）
    for i, ang in enumerate((-72, -36, 0, 36, 72)):
        a = math.radians(ang)
        px, py = 0.156 * math.sin(a), 0.156 * math.cos(a)
        mat = "steel" if abs(ang) <= 40 else "steel_dark"
        w = 0.110 if abs(ang) <= 40 else 0.098
        u.box("bd_fauld%d" % i, (px, py, 0.556), (w, 0.032, 0.104),
              "hips", mat, bevel=0.007, seg=2, rot=(math.radians(-8), 0, -a))


# ── 3. 躯干（方盒胸甲 + 垂布在 gear 里）────────────────────────────────────
def torso(u, detail=1):
    coat = [[(x, y, z) for (x, y) in K.poly_rect(w, d, ch)]
            for (z, w, d, ch) in ((0.626, 0.354, 0.294, 0.048),
                                  (0.702, 0.380, 0.308, 0.050),
                                  (0.784, 0.402, 0.322, 0.052))]
    u.loft("bd_coat", coat, "spine", "cloth_dark", bevel=0.006, seg=2, sub=0, smooth=False)

    plate = [[(x, y, z) for (x, y) in K.poly_rect(w, d, ch)]
             for (z, w, d, ch) in ((0.788, 0.412, 0.330, 0.052),
                                   (0.852, 0.460, 0.358, 0.056),
                                   (0.918, 0.468, 0.352, 0.054),
                                   (0.954, 0.412, 0.310, 0.046))]
    u.loft("bd_chest", plate, "chest", "steel", bevel=0.010, seg=2, sub=0, smooth=False)

    u.plate("bd_plackart", [(-0.134, 0.794), (0.134, 0.794), (0.122, 0.746),
                            (0.0, 0.706), (-0.122, 0.746)],
            "chest", "steel_dark", axis="Y", thickness=0.024, offset=0.156,
            bevel=0.005, smooth=False)

    u.tube("bd_gorget", [(0.946, 0, 0.004, 0.250, 0.226, 0.040),
                         (0.996, 0, 0.006, 0.218, 0.198, 0.034)],
           "chest", "steel_dark", bevel=0.006, seg=1, smooth=False)
    u.box("jt_neck", (0, 0.010, 0.998), (0.158, 0.152, 0.078),
          "neck", "cloth_dark", bevel=0.005, seg=1)

    # 两条竖直皮带（压在胸甲正面，垂布两侧）
    for s in (1, -1):
        u.box("bd_harness_%d" % s, (s * 0.180, 0.172, 0.874), (0.052, 0.030, 0.154),
              "chest", "leather_dark", bevel=0.004, seg=1, rot=(0, s * math.radians(8), 0))
        u.box("bd_harn_buckle_%d" % s, (s * 0.180, 0.190, 0.800), (0.044, 0.016, 0.032),
              "chest", "team_trim", bevel=0.003, seg=1)
    if detail:
        for s in (1, -1):
            for (zz, xx) in ((0.826, 0.230), (0.910, 0.236)):
                u.box("bd_rivet_%d_%d" % (s, int(zz * 100)), (s * xx, 0.020, zz),
                      (0.022, 0.022, 0.022), "chest", "iron", bevel=0.002, seg=1)


# ── 4. 臂 / 手（方棱柱 + 一块方拳）──────────────────────────────────────────
def arms(u, detail=1):
    for s, side in ((1, "R"), (-1, "L")):
        sh = SH_R if s > 0 else SH_L
        el = ELB_R if s > 0 else ELB_L
        wr = WRI_R if s > 0 else WRI_L
        ua, fa = "upperarm_" + side, "forearm_" + side
        fdir = (el - sh).normalized()

        u.add(blimb("jt_shoulder_" + side, sh - fdir * 0.034, sh + fdir * 0.026,
                    [(0.0, 0.134, 0.142), (1.0, 0.138, 0.146)], ch=0.014),
              "shoulder_" + side, "cloth_dark", 0.004, 1, 0, False)
        u.add(blimb("ar_upper_" + side, sh + fdir * 0.006, el - fdir * 0.026,
                    [(0.0, 0.132, 0.140), (0.55, 0.124, 0.132), (1.0, 0.116, 0.124)],
                    ch=0.020),
              ua, "cloth", 0.006, 2, 0, False)
        u.add(blimb("ar_rerebrace_" + side, sh + fdir * 0.066, el - fdir * 0.066,
                    [(0.0, 0.142, 0.062), (1.0, 0.134, 0.058)], ch=0.014),
              ua, "steel_dark", 0.006, 2, 0, False)

        fdir2 = (wr - el).normalized()
        u.add(blimb("jt_elbow_" + side, el - fdir * 0.022, el + fdir * 0.024,
                    [(0.0, 0.096, 0.100), (1.0, 0.098, 0.102)], ch=0.012),
              fa, "cloth_dark", 0.004, 1, 0, False)
        u.add(blimb("ar_fore_" + side, el + fdir2 * 0.022, wr - fdir2 * 0.022,
                    [(0.0, 0.114, 0.120), (0.5, 0.106, 0.112), (1.0, 0.098, 0.104)],
                    ch=0.018),
              fa, "steel", 0.008, 2, 0, False)
        u.add(blimb("ar_bracer_" + side, el + fdir2 * 0.052, wr - fdir2 * 0.042,
                    [(0.0, 0.126, 0.070), (1.0, 0.114, 0.064)], ch=0.014),
              fa, "steel_dark", 0.006, 2, 0, False)
        u.add(blimb("ar_cuff_" + side, wr - fdir2 * 0.032, wr + fdir2 * 0.002,
                    [(0.0, 0.112, 0.118), (1.0, 0.106, 0.112)], ch=0.012),
              fa, "leather_dark", 0.005, 1, 0, False)

    fist(u, "R", "hand_R", FIST_R, GX, GUN_A, GZ, detail, grip=True)
    ey = Vector((0.10, 0.16, -0.98)).normalized()
    ez = (Vector((0, 1, 0)) - ey * ey.y).normalized()
    ex = ey.cross(ez).normalized()
    fist(u, "L", "hand_L", FIST_L, ex, ey, ez, detail, grip=False)


def fist(u, side, bone, c, ex, ey, ez, detail=1, grip=True):
    """方拳：**一块方块** + 一道指缝条。不套手指、不套拇指块 ——
    方块人尺度下手只负责"握住了"这个信息，多一块就变成肉团。"""
    def P(x, y, z):
        return tuple(Vector(c) + Vector(ex) * x + Vector(ey) * y + Vector(ez) * z)

    u.add(K.box("ar_fist_" + side, P(0, 0, 0), (0.092, 0.114, 0.098)),
          bone, "skin", 0.010, 2, 0, False)
    # 手就是一块方块：不加手指、不加指缝块（方块人尺度下多一块就变成"手上贴了零件"）


# ── 5. 护肩（三层扁方板，照联盟弩兵的叠片）──────────────────────────────────
def pauldrons(u, detail=1):
    for s, side in ((1, "R"), (-1, "L")):
        ua = "upperarm_" + side
        for i, (cx, cz, w, d, h, tilt, mat) in enumerate((
                (0.252, 0.954, 0.176, 0.222, 0.056, 34, "steel_cool"),
                (0.282, 0.914, 0.176, 0.208, 0.048, 50, "steel_dark"),
                (0.308, 0.874, 0.154, 0.190, 0.042, 62, "steel"))):
            u.box("pd_lame_%s%d" % (side, i), (s * cx, -0.004, cz), (w, d, h),
                  ua, mat, bevel=0.008, seg=1, rot=(0, s * math.radians(tilt), 0))



# ── 6. 头（方头 + 方盔 + 方胡子；冠徽在 gear 的垂布上）─────────────────────
def head(u, detail=1):
    # 头：一整块立方体（方块人的脸是"面"，不是球）
    u.box("hd_skull", (0, 0.006, 1.138), (0.272, 0.256, 0.248),
          "head", "skin", bevel=0.012, seg=2)
    u.box("hd_face", (0, 0.132, 1.124), (0.234, 0.026, 0.196),
          "head", "skin", bevel=0.006, seg=1)
    for s in (1, -1):
        u.box("hd_eye_%d" % s, (s * 0.058, 0.148, 1.152), (0.042, 0.010, 0.020),
              "head", "dark", bevel=0.001, seg=1)
        u.box("hd_brow_%d" % s, (s * 0.060, 0.150, 1.196), (0.050, 0.012, 0.014),
              "head", "hair", bevel=0.002, seg=1)
    u.box("hd_nose", (0, 0.156, 1.136), (0.052, 0.044, 0.062),
          "head", "skin_dark", bevel=0.006, seg=1)

    # 桶盔：四棱台壳 + 方檐 + 蓝帽箍（队色高带）+ 平顶 + 顶钮
    u.tube("hd_helm", [(1.224, 0, 0.010, 0.296, 0.288, 0.0),
                       (1.284, 0, 0.012, 0.302, 0.294, 0.0),
                       (1.316, 0, 0.012, 0.300, 0.292, 0.0)],
           "head", "steel_cool", bevel=0.010, seg=1, smooth=False)
    u.tube("hd_helm_cap", [(1.316, 0, 0.012, 0.300, 0.292, 0.0),
                           (1.352, 0, 0.012, 0.288, 0.280, 0.0),
                           (1.378, 0, 0.012, 0.256, 0.248, 0.0)],
           "head", "team", bevel=0.006, seg=1, smooth=False)
    u.box("hd_helm_knob", (0, 0.012, 1.386), (0.042, 0.040, 0.014),
          "head", "steel_dark", bevel=0.003, seg=1)

    # 护鼻 / 护颊 / 护颈 / 后颈队色巾脚
    u.box("hd_nasal", (0, 0.150, 1.202), (0.026, 0.024, 0.066),
          "head", "steel_dark", bevel=0.003, seg=1)
    for s in (1, -1):
        u.box("hd_cheek_%d" % s, (s * 0.144, 0.048, 1.152), (0.028, 0.108, 0.146),
              "head", "steel_cool", bevel=0.005, seg=1)
    u.box("hd_neckguard", (0, -0.146, 1.168), (0.286, 0.042, 0.152),
          "head", "steel_cool", bevel=0.006, seg=1, rot=(math.radians(-8), 0, 0))
    u.plate("hd_cloth_tail", [(-0.104, 1.212), (0.104, 1.212), (0.084, 1.058),
                              (0.0, 1.014), (-0.084, 1.058)],
            "head", "team", axis="Y", thickness=0.018, offset=-0.178,
            bevel=0.004, smooth=False)

    beard(u, detail)


def beard(u, detail=1):
    """上胡（腮 + 髭）+ 两条方辫（中缝分叉 = 矮人的第二剪影）。
    不加任何金环/金饰：胡子上只允许一种颜色。"""
    rows = [[(x, cy + y, z) for (x, y) in K.poly_rect(w, d, ch)]
            for (z, cy, w, d, ch) in ((1.062, 0.150, 0.164, 0.080, 0.014),
                                      (1.024, 0.156, 0.186, 0.090, 0.016),
                                      (0.994, 0.160, 0.184, 0.092, 0.016))]
    u.loft("bm_upper", rows, "head", "rust", bevel=0.008, seg=1, sub=0, smooth=False)
    if detail:
        u.box("bm_moustache", (0, 0.206, 1.050), (0.156, 0.030, 0.024),
              "head", "rust", bevel=0.006, seg=1, rot=(math.radians(-10), 0, 0))

    for s in (1, -1):
        rows = [[(s * cx + x, cy + y, z) for (x, y) in K.poly_rect(w, d, ch)]
                for (z, cx, cy, w, d, ch) in ((0.998, 0.078, 0.160, 0.092, 0.118, 0.016),
                                              (0.936, 0.082, 0.164, 0.096, 0.122, 0.018),
                                              (0.906, 0.084, 0.164, 0.088, 0.114, 0.016),
                                              (0.848, 0.088, 0.158, 0.070, 0.096, 0.012),
                                              (0.792, 0.092, 0.148, 0.026, 0.046, 0.006))]
        u.loft("bm_lobe_%d" % s, rows, "head", "rust", bevel=0.008, seg=1, sub=0, smooth=False)


# ── 7. 装具：胸前垂布（符号位）+ 火药角 + 弹囊 ──────────────────────────────
def gear(u, detail=1):
    # 垂布：蓝底 + 金边 + **金冠徽**（联盟符号位。盔上不放徽）
    prof = [(-0.070, 0.898), (0.0, 0.874), (0.070, 0.898),
            (0.070, 0.744), (0.0, 0.698), (-0.070, 0.744)]
    prof_g = [(-0.079, 0.906), (0.0, 0.878), (0.079, 0.906),
              (0.079, 0.737), (0.0, 0.687), (-0.079, 0.737)]
    u.plate("gr_tabard_edge", prof_g, "spine", "team_trim", axis="Y", thickness=0.022,
            offset=0.172, bevel=0.003, seg=1, smooth=False)
    u.plate("gr_tabard", prof, "spine", "team", axis="Y", thickness=0.020,
            offset=0.180, bevel=0.004, seg=1, smooth=False)
    scrown(u, 0.0, 0.702, 0.084, 0.203, "spine", w=0.038, pre="gr_")
    # 背面同一条垂布（背面朝 -Y，徽记画在 -0.20 一侧）
    prof_b = [(-0.070, 0.892), (0.0, 0.868), (0.070, 0.892),
              (0.070, 0.746), (0.0, 0.700), (-0.070, 0.746)]
    prof_bg = [(-0.079, 0.900), (0.0, 0.872), (0.079, 0.900),
               (0.079, 0.739), (0.0, 0.689), (-0.079, 0.739)]
    u.plate("gr_tabard_b_edge", prof_bg, "spine", "team_trim", axis="Y", thickness=0.030,
            offset=-0.194, bevel=0.003, seg=1, smooth=False)
    u.plate("gr_tabard_b", prof_b, "spine", "team", axis="Y", thickness=0.020,
            offset=-0.200, bevel=0.004, seg=1, smooth=False)
    scrown(u, 0.0, 0.706, 0.080, -0.212, "spine", w=0.036, pre="grB_")

    # 火药角（左胯，垂挂）
    path = [(-0.238, 0.030, 0.604), (-0.258, 0.072, 0.558),
            (-0.264, 0.106, 0.506), (-0.258, 0.124, 0.460)]
    secs = [(0.0, 0.092, 0.074), (0.45, 0.080, 0.062), (0.78, 0.054, 0.044),
            (1.0, 0.028, 0.024)]
    rows = []
    for (t, pw, pd) in secs:
        k = t * (len(path) - 1)
        i0 = min(int(k), len(path) - 2)
        f = k - i0
        c = Vector(path[i0]).lerp(Vector(path[i0 + 1]), f)
        rows.append([(c.x + x, c.y + y, c.z) for (x, y) in K.poly_rect(pw, pd, 0.010)])
    u.loft("gr_horn", rows, "hips", "wood", bevel=0.007, seg=1, sub=0, smooth=False)
    u.tube("gr_horn_mouth", [(0.438, -0.256, 0.128, 0.046, 0.040, 0.008),
                             (0.410, -0.254, 0.132, 0.034, 0.030, 0.006)],
           "hips", "dark", bevel=0.003, seg=1, smooth=False)
    if detail:
        u.box("gr_horn_ring0", (-0.256, 0.072, 0.540), (0.086, 0.068, 0.018),
              "hips", "gold", bevel=0.003, seg=1)
        u.box("gr_horn_strap", (-0.222, 0.030, 0.618), (0.030, 0.052, 0.068),
              "hips", "leather_dark", bevel=0.004, seg=1, rot=(0, math.radians(12), 0))

    # 弹药囊（右胯）
    u.box("gr_pouch", (0.210, 0.078, 0.588), (0.096, 0.084, 0.102),
          "hips", "leather", bevel=0.006, seg=1, rot=(0, math.radians(-6), math.radians(-8)))
    u.box("gr_pouch_flap", (0.210, 0.084, 0.634), (0.102, 0.092, 0.028),
          "hips", "leather_dark", bevel=0.005, seg=1, rot=(0, math.radians(-6), math.radians(-8)))
    u.box("gr_pouch_stud", (0.210, 0.126, 0.604), (0.022, 0.018, 0.022),
          "hips", "gold", bevel=0.0025, seg=1)


# ── 8. 火枪（独立组件；枪托与枪管都是方截面）────────────────────────────────
def _gsec(y, w, h, cz=0.0, ch=0.012):
    return [GP(u, y, cz + v) for (u, v) in K.poly_rect(w, h, ch)]


def _gring(name, u, y0, y1, w, h, cz, mat, bone="weapon_R", bev=0.004, ch=0.010):
    u.add(K.loft(name, [_gsec(y0, w, h, cz, ch), _gsec(y1, w, h, cz, ch)]),
          bone, mat, bev, 1, 0, False)


def _grot():
    from mathutils import Matrix
    M = Matrix((GX, GUN_A, GZ)).transposed()
    return M.to_euler()


def weapon(u, detail=1):
    """长管火枪（局部：y 沿枪管，z 枪面"上"，x 侧向）。"""
    ROT = _grot()

    def gbox(name, x, y, z, sx, sy, sz, mat, bone="weapon_R", bev=0.005):
        u.add(K.box(name, GP(x, y, z), (sx, sy, sz), rot=ROT),
              bone, mat, bev, 1, 0, False)

    # 木托：方截面放样
    stock = [(-0.300, 0.080, 0.150, -0.024, 0.016),
             (-0.244, 0.078, 0.144, -0.022, 0.018),
             (-0.162, 0.070, 0.104, -0.008, 0.014),
             (-0.064, 0.068, 0.096, -0.006, 0.012),
             (0.000, 0.070, 0.092, -0.006, 0.012),
             (0.120, 0.072, 0.088, -0.008, 0.012),
             (0.280, 0.070, 0.084, -0.010, 0.012),
             (0.440, 0.064, 0.080, -0.012, 0.010),
             (0.580, 0.058, 0.074, -0.014, 0.010)]
    u.add(K.loft("wp_stock", [_gsec(y, w, h, cz, ch) for (y, w, h, cz, ch) in stock]),
          "weapon_R", "wood", 0.006, 2, 0, False)
    _gring("wp_butt", u, -0.312, -0.296, 0.086, 0.166, -0.024, "gold", bev=0.005, ch=0.014)

    # 枪管：**方管**（4 点截面）
    barrel = [(0.020, 0.054, 0.058), (0.180, 0.052, 0.056), (0.380, 0.050, 0.054),
              (0.560, 0.048, 0.052), (0.700, 0.046, 0.050)]
    u.add(K.loft("wp_barrel", [_gsec(y, w, h, 0.030, 0.008) for (y, w, h) in barrel]),
          "weapon_R", "iron", 0.004, 1, 0, False)

    # 枪口：方箍 + 暗膛（不做喇叭口）
    _gring("wp_muzzle", u, 0.700, 0.744, 0.070, 0.074, 0.030, "gold", bev=0.005, ch=0.012)
    gbox("wp_bore", 0, 0.748, 0.030, 0.040, 0.014, 0.044, "dark", bev=0.002)
    if detail:
        gbox("wp_sight", 0, 0.700, 0.072, 0.014, 0.020, 0.016, "steel_cool", bev=0.002)

    # 两道金箍 + 一道队色箍
    _gring("wp_band0", u, 0.150, 0.176, 0.082, 0.098, -0.006, "gold", bev=0.005, ch=0.012)
    _gring("wp_band1", u, 0.470, 0.496, 0.076, 0.090, -0.008, "gold", bev=0.005, ch=0.012)
    _gring("wp_teamband", u, 0.230, 0.264, 0.080, 0.096, -0.007, "team", bev=0.004, ch=0.010)

    # 击发机构
    gbox("wp_lock", 0.040, 0.024, -0.022, 0.018, 0.150, 0.084, "steel_dark")
    gbox("wp_sideplate", -0.038, 0.024, -0.022, 0.012, 0.124, 0.058, "steel_dark", bev=0.003)
    gbox("wp_hammer", 0.040, 0.076, 0.020, 0.022, 0.036, 0.060, "iron")
    gbox("wp_hammer_jaw", 0.040, 0.096, 0.044, 0.024, 0.044, 0.022, "iron")
    gbox("wp_pan", 0.036, 0.054, 0.000, 0.030, 0.040, 0.024, "gold", bev=0.003)
    gbox("wp_trigger", 0, -0.046, -0.058, 0.022, 0.026, 0.046, "iron", bev=0.003)
    gbox("wp_guard", 0, -0.054, -0.084, 0.046, 0.086, 0.014, "steel_dark", bev=0.003)
    gbox("wp_guard_f", 0, -0.094, -0.066, 0.046, 0.016, 0.038, "steel_dark", bev=0.003)

    # 通条（独立骨 prop_ramrod）：方杆，半埋进护木槽
    u.add(blimb("wp_ramrod", GP(0, 0.010, -0.030), GP(0, 0.545, -0.030),
                [(0.0, 0.024, 0.024), (1.0, 0.024, 0.024)], ch=0.004),
          "prop_ramrod", "wood_dark", 0.0, 1, 0, False)
    gbox("wp_rod_tip", 0, 0.548, -0.030, 0.026, 0.022, 0.026, "gold", bone="prop_ramrod", bev=0.003)
    gbox("wp_rod_head", 0, 0.004, -0.030, 0.030, 0.024, 0.030, "gold", bone="prop_ramrod", bev=0.003)


# ── 组装 ───────────────────────────────────────────────────────────────────
def build(detail=1, modules=None):
    want = set(MODULES if modules is None else modules)
    u = K.Unit(NAME)
    if "body" in want:
        legs(u, detail)
        hips(u, detail)
        torso(u, detail)
        arms(u, detail)
    if "shoulder" in want:
        pauldrons(u, detail)
    if "head" in want:
        head(u, detail)
    if "gear" in want:
        gear(u, detail)
    if "weapon" in want:
        weapon(u, detail)
    u.modules = {ob.name: module_of(ob.name) for (ob, *_r) in u.parts}
    return u


def build_weapon_only(detail=1):
    u = K.Unit(NAME + "_weapon")
    weapon(u, detail)
    u.modules = {ob.name: "weapon" for (ob, *_r) in u.parts}
    return u


def build_rig(name="RIG_火枪手"):
    arm = bpy.data.armatures.new(name)
    ob = bpy.data.objects.new(name, arm)
    bpy.context.scene.collection.objects.link(ob)
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    for (bn, head, tail, parent) in BONES:
        eb = arm.edit_bones.new(bn)
        eb.head = Vector(head)
        eb.tail = Vector(tail)
        eb.roll = 0.0
        eb.use_connect = False
        if parent:
            eb.parent = arm.edit_bones[parent]
    bpy.ops.object.mode_set(mode="OBJECT")
    ob.show_in_front = True
    return ob


def low_poly_parts(u):
    """低模档 = 全部去倒角 + 单段。方块人本来就是硬边，去倒角只掉面、不改剪影。"""
    u.parts = [(ob, bone, mat, 0.0, 1, 0, smooth)
               for (ob, bone, mat, bev, seg, sub, smooth) in u.parts]
    return u


def report():
    out = ["[joints] hip=%.3f knee=%.3f ankle=%.3f" % (Z_HIP, KNE_R.z, ANK_R.z),
           "[arm] R elbow=(%.3f, %.3f, %.3f) reach=%.3f"
           % (ELB_R.x, ELB_R.y, ELB_R.z, (WRI_R - SH_R).length),
           "[arm] L elbow=(%.3f, %.3f, %.3f) reach=%.3f"
           % (ELB_L.x, ELB_L.y, ELB_L.z, (WRI_L - SH_L).length),
           "[leg] thigh=%.3f shin=%.3f" % (L_THIGH, L_SHIN),
           "[gun] butt=(%.3f, %.3f, %.3f) muzzle=(%.3f, %.3f, %.3f)"
           % (GP(0, -GUN_L_BACK, 0).x, GP(0, -GUN_L_BACK, 0).y, GP(0, -GUN_L_BACK, 0).z,
              GP(0, GUN_L_FWD, 0).x, GP(0, GUN_L_FWD, 0).y, GP(0, GUN_L_FWD, 0).z),
           "[bones] %d" % len(BONES)]
    return "\n".join(out)
