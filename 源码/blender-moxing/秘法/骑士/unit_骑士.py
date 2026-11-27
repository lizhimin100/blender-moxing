"""unit_骑士.py —— 联盟·骑士（精模 / 硬边支线，**人马一体**）

造型口径：1 unit = 1 m，+Y 正面，+X = 角色右侧，四蹄落地 z = 0。
  * **语言对齐步兵**：甲色是暖象牙（不是破法者的冷钢），队色蓝走"面"、金只做"边"，
    皮革棕做过渡；蓝只落四处（鞍垫 / 马衣 / 盔箍 / 胸褡），金只做线。
  * **马是主体量的 2/3**：没有马的骑士只是一杆枪。马腿四段、马衣下摆、面甲蓝翎
    把"骑兵"这三个字在 96 px 里写清楚。
  * 一体化的代价：骑手不挂在马的骨链上，而是每帧被 `place()` 放到鞍点上 ——
    这样"死亡"里骑手能摔到地上，而马继续向前倒，不需要第二副骨架。

组件化（MODULES）：
  horse    桶身 / 颈 / 头 / 尾 / 四条腿（含蹄）
  tack     鞍 / 马衣 / 胸甲 / 面甲 / 缰绳 / 马镫
  body     骑手：腿 / 胯 / 躯干 / 臂 / 手
  head     大盔 + 面甲 + 眼缝 + 蓝箍 + 冠脊
  pauldron 两层叠片护肩 ×2
  weapon   骑枪（独立 glb，挂 weapon_R）
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
import horse_kit as HK  # noqa: E402

NAME = "骑士"
PREFIX = "kn"

# ── 骑手尺寸表（m，全部是坐姿的世界坐标）─────────────────────────────────────
Z_SEAT = 1.660
Z_HIP = 1.740
Z_WAIST = 1.860
Z_CHEST = 1.980
Z_SHLD = 2.095
Z_NECK = 2.150
Z_TOP = 2.435            # 盔顶（不含冠脊）
Z_CREST = 2.492

SH_X = 0.215
HIP_X = 0.125
KNEE = Vector((0.356, 0.196, 1.516))
ANKLE = Vector((0.368, 0.104, 1.196))
TOE = Vector((0.368, 0.224, 1.166))

L_THIGH = (KNEE - Vector((HIP_X, -0.055, Z_HIP))).length
L_SHIN = (ANKLE - KNEE).length
L_UPPER, L_FORE = 0.290, 0.265
WRIST_OFF = 0.060

SH_R = Vector((SH_X, -0.012, Z_SHLD))
SH_L = Vector((-SH_X, -0.012, Z_SHLD))

# ── 骑枪：从镫后的枪尾穿过右手，枪尖指向前上方 ──────────────────────────────
LANCE_BUTT = Vector((0.440, -0.230, 0.980))
LANCE_TIP = Vector((0.330, 0.780, 2.820))
LANCE_D = (LANCE_TIP - LANCE_BUTT).normalized()
LANCE_L = (LANCE_TIP - LANCE_BUTT).length
GRIP_T = (1.870 - LANCE_BUTT.z) / (LANCE_TIP.z - LANCE_BUTT.z)
FIST_R = LANCE_BUTT + (LANCE_TIP - LANCE_BUTT) * GRIP_T      # ≈ (0.391, 0.251, 1.870)
FIST_L = Vector((-0.206, 0.330, 1.800))                       # 左手：前伸抓缰

SADDLE = Vector((0.0, -0.055, Z_HIP))


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
ELB_R = ik2(SH_R, WRI_R, L_UPPER, L_FORE, (0.90, -0.55, -0.55))
ELB_L = ik2(SH_L, WRI_L, L_UPPER, L_FORE, (-0.90, -0.55, -0.55))
KNE_R = ik2(Vector((HIP_X, -0.055, Z_HIP)), ANKLE, L_THIGH, L_SHIN, (0.20, 1.0, 0.10))
KNE_L = Vector((-KNE_R.x, KNE_R.y, KNE_R.z))
HDIR_R = (FIST_R - WRI_R).normalized()
HDIR_L = (FIST_L - WRI_L).normalized()
ARM_D = {1: (ELB_R - SH_R).normalized(), -1: (ELB_L - SH_L).normalized()}

# 枪的重心参数（挂在 weapon_R 上，局部 +Y = 枪尖方向）
LANCE_GRIP_LOCAL = 0.0


# ── 骨架 ────────────────────────────────────────────────────────────────────
def _bones():
    b = [
        ("root", (0, 0, 0), (0, 0, 0.16), None),
        # 马：胯→腰→胸→颈→头（沿 +Y 推进，旋转 chest 就是"抬前身"）
        ("horse_hips", (0, -0.620, 1.315), (0, -0.250, 1.372), "root"),
        ("horse_spine", (0, -0.250, 1.372), (0, 0.240, 1.352), "horse_hips"),
        ("horse_chest", (0, 0.240, 1.352), (0, 0.560, 1.372), "horse_spine"),
        ("horse_neck", (0, 0.500, 1.400), (0, 0.990, 1.925), "horse_chest"),
        ("horse_head", (0, 0.990, 1.925), (0, 1.400, 1.620), "horse_neck"),
        ("horse_tail_01", (0, -0.900, 1.500), (0, -1.020, 1.270), "horse_hips"),
        ("horse_tail_02", (0, -1.020, 1.270), (0, -1.090, 1.020), "horse_tail_01"),
        # 骑手：挂在 root 上（不挂马），每帧由 place() 放上鞍点
        ("rider_root", tuple(SADDLE), (0, -0.055, Z_HIP + 0.09), "root"),
        ("r_hips", (0, -0.055, Z_HIP), (0, -0.050, Z_WAIST), "rider_root"),
        ("r_spine", (0, -0.050, Z_WAIST), (0, -0.040, Z_CHEST), "r_hips"),
        ("r_chest", (0, -0.040, Z_CHEST), (0, -0.030, Z_SHLD), "r_spine"),
        ("r_head", (0, -0.030, Z_NECK), (0, -0.025, Z_TOP - 0.02), "r_chest"),
    ]
    for s, side in ((1, "R"), (-1, "L")):
        sh = SH_R if s > 0 else SH_L
        el = ELB_R if s > 0 else ELB_L
        wr = WRI_R if s > 0 else WRI_L
        hd = HDIR_R if s > 0 else HDIR_L
        b += [
            ("r_shoulder_" + side, (s * 0.060, -0.020, Z_SHLD + 0.005), tuple(sh), "r_chest"),
            ("r_upperarm_" + side, tuple(sh), tuple(el), "r_shoulder_" + side),
            ("r_forearm_" + side, tuple(el), tuple(wr), "r_upperarm_" + side),
            ("r_hand_" + side, tuple(wr), tuple(wr + hd * 0.098), "r_forearm_" + side),
        ]
        hip = Vector((s * HIP_X, -0.055, Z_HIP))
        knee = KNE_R if s > 0 else KNE_L
        ank = Vector((s * ANKLE.x, ANKLE.y, ANKLE.z))
        toe = Vector((s * TOE.x, TOE.y, TOE.z))
        b += [
            ("r_thigh_" + side, tuple(hip), tuple(knee), "r_hips"),
            ("r_shin_" + side, tuple(knee), tuple(ank), "r_thigh_" + side),
            ("r_foot_" + side, tuple(ank), tuple(toe), "r_shin_" + side),
        ]
        # 马腿：前腿 3 段 / 后腿 3 段（上段把股+胫并成一根，靠飞节尖补形）
        fs = Vector((s * HK.FRONT_SH.x, HK.FRONT_SH.y, HK.FRONT_SH.z))
        bk = Vector((s * HK.FRONT_KNEE.x, HK.FRONT_KNEE.y, HK.FRONT_KNEE.z))
        bf = Vector((s * HK.FRONT_FET.x, HK.FRONT_FET.y, HK.FRONT_FET.z))
        bt = Vector((s * HK.FRONT_TOE.x, HK.FRONT_TOE.y, HK.FRONT_TOE.z))
        hs = Vector((s * HK.HIND_HIP.x, HK.HIND_HIP.y, HK.HIND_HIP.z))
        hk = Vector((s * HK.HIND_HOCK.x, HK.HIND_HOCK.y, HK.HIND_HOCK.z))
        hf = Vector((s * HK.HIND_FET.x, HK.HIND_FET.y, HK.HIND_FET.z))
        ht = Vector((s * HK.HIND_TOE.x, HK.HIND_TOE.y, HK.HIND_TOE.z))
        b += [
            ("horse_upper_" + side, tuple(fs), tuple(bk), "horse_chest"),
            ("horse_fore_" + side, tuple(bk), tuple(bf), "horse_upper_" + side),
            ("horse_hoofF_" + side, tuple(bf), tuple(bt), "horse_fore_" + side),
            ("horse_thigh_" + side, tuple(hs), tuple(hk), "horse_hips"),
            ("horse_shin_" + side, tuple(hk), tuple(hf), "horse_thigh_" + side),
            ("horse_hoofH_" + side, tuple(hf), tuple(ht), "horse_shin_" + side),
        ]
    b += [
        ("weapon_R", tuple(FIST_R), tuple(FIST_R + LANCE_D * 0.30), "r_hand_R"),
        ("weapon_L", tuple(FIST_L), tuple(FIST_L + Vector((0, 0.22, 0))), "r_hand_L"),
    ]
    return b


BONES = _bones()
BONE_NAMES = [b[0] for b in BONES]

MODULES = ("horse", "tack", "body", "head", "pauldron", "weapon")

MATS = {
    "马体":      dict(hexcol="#523A28", metal=0.00, rough=0.56),
    "皮革暗":    dict(hexcol="#241A12", metal=0.02, rough=0.64),
    "蹄":        dict(hexcol="#171210", metal=0.06, rough=0.32),
    "甲":        dict(hexcol="#D6CBB6", metal=0.14, rough=0.44),
    "甲暗":      dict(hexcol="#A2937A", metal=0.18, rough=0.50),
    "钢":        dict(hexcol="#949CA6", metal=0.62, rough=0.30),
    "钢暗":      dict(hexcol="#565D68", metal=0.55, rough=0.40),
    "皮革":      dict(hexcol="#6E4C32", metal=0.02, rough=0.55),
    "team":      dict(hexcol="#2E5FB4", metal=0.00, rough=0.56),
    "team_trim": dict(hexcol="#F1CD79", metal=0.10, rough=0.44),
}


# ── 小件 ────────────────────────────────────────────────────────────────────
def fm(name, p0, p1, r0, r1, a0, a1, nv=2, nu=5, thick=0.024, out=(0, 1, 0)):
    return K.arc_band(name, p0, p1, r0, r1, a0, a1, nv, nu, thick, out)


def dome_patch(name, center, rx, ry, rz, a0, a1, p0, p1, nu, nv, thick):
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


# ── 1. 骑手的腿（坐姿：大腿前伸、小腿垂下、脚踩镫）──────────────────────────
def legs(u):
    for s, side in ((1, "R"), (-1, "L")):
        hip = Vector((s * HIP_X, -0.055, Z_HIP))
        knee = KNE_R if s > 0 else KNE_L
        ank = Vector((s * ANKLE.x, ANKLE.y, ANKLE.z))
        toe = Vector((s * TOE.x, TOE.y, TOE.z))
        th, sn, ft = "r_thigh_" + side, "r_shin_" + side, "r_foot_" + side
        out = (s * 0.92, 0.10, 0.36)

        # 大腿：软甲内胆 + 外甲片 + 上沿金箍
        u.olimb("kn_thigh_" + side, hip + (knee - hip) * -0.06, knee + (hip - knee) * 0.10,
                [(0.00, 0.196, 0.206, 0.052), (0.50, 0.182, 0.192, 0.048),
                 (1.00, 0.164, 0.172, 0.042)],
                th, "钢暗", "facet", "body", "thigh")
        u.add(fm("kn_cuisse_" + side, hip + (knee - hip) * 0.02, knee + (hip - knee) * 0.16,
                 0.106, 0.090, -118, 118, 3, 6, 0.028, out),
              th, "甲", "chunk2", "body", "thigh")
        u.add(fm("kn_cuisse_rib_" + side, hip + (knee - hip) * 0.06, knee + (hip - knee) * 0.10,
                 0.116, 0.100, -10, 10, 3, 1, 0.014, out),
              th, "team_trim", "chunk", "body", "thigh")
        # 膝：方护膝 + 金铆
        u.otube("kn_poleyn_" + side,
                [(knee.z + 0.072, knee.x, knee.y - 0.006, 0.186, 0.196, 0.052),
                 (knee.z + 0.010, knee.x, knee.y + 0.002, 0.202, 0.212, 0.056),
                 (knee.z - 0.062, knee.x, knee.y - 0.004, 0.168, 0.180, 0.046)],
                sn, "钢", "chunk2", "body", "knee", cw=0.05)
        u.add(dome_patch("kn_knee_cap_" + side, (knee.x, knee.y + 0.030, knee.z),
                         0.086, 0.082, 0.090, -40 if s > 0 else 140,
                         40 if s > 0 else 220, 26, 96, 3, 2, 0.020),
              sn, "钢暗", "chunk", "body", "knee")
        u.rivet("kn_knee_stud_" + side, (knee.x, knee.y + 0.098, knee.z - 0.006),
                (0, 1, 0.1), sn, "team_trim", "hard", "body", "knee", r=0.020, h=0.012)

        # 小腿：内胆 + 胫甲 + 靴
        u.olimb("kn_shin_" + side, knee + (ank - knee) * 0.14, ank + (knee - ank) * 0.06,
                [(0.00, 0.156, 0.166, 0.042), (0.55, 0.138, 0.148, 0.036),
                 (1.00, 0.124, 0.132, 0.032)],
                sn, "钢暗", "facet", "body", "shin")
        u.add(fm("kn_greave_" + side, knee + (ank - knee) * 0.20, ank + (knee - ank) * 0.02,
                 0.094, 0.078, -112, 112, 3, 6, 0.026, out),
              sn, "钢暗", "chunk2", "body", "shin")
        u.add(fm("kn_greave_top_" + side, knee + (ank - knee) * 0.16, knee + (ank - knee) * 0.24,
                 0.098, 0.100, -118, 118, 1, 6, 0.018, out),
              sn, "team_trim", "chunk", "body", "shin")
        # 靴（前掌朝 +Y，脚背一块斜板）
        u.otube("kn_sabaton_" + side,
                [(ank.z + 0.046, ank.x, ank.y - 0.010, 0.140, 0.156, 0.032),
                 (ank.z - 0.006, ank.x, ank.y + 0.026, 0.150, 0.208, 0.036),
                 (ank.z - 0.040, ank.x, ank.y + 0.052, 0.152, 0.246, 0.036)],
                ft, "皮革暗", "chunk2", "body", "boot")
        u.box("kn_sole_" + side, (toe.x, toe.y - 0.020, ank.z - 0.054),
              (0.168, 0.270, 0.020), ft, "皮革暗", style="hard", module="body", tag="boot")
        u.otube("kn_toe_" + side,
                [(ank.z + 0.010, toe.x, toe.y - 0.060, 0.150, 0.110, 0.030),
                 (ank.z - 0.030, toe.x, toe.y - 0.020, 0.156, 0.126, 0.032)],
                ft, "钢暗", "chunk", "body", "boot", cw=0.03)
        u.box("kn_toe_rim_" + side, (toe.x, toe.y + 0.026, ank.z - 0.040),
              (0.140, 0.024, 0.014), ft, "team_trim", style="hard", module="body", tag="boot")


# ── 2. 胯 / 腰裙 ────────────────────────────────────────────────────────────
def pelvis(u):
    u.otube("kn_hip",
            [(Z_SEAT + 0.010, 0, -0.050, 0.300, 0.240, 0.052),
             (Z_SEAT + 0.086, 0, -0.050, 0.318, 0.252, 0.056),
             (Z_WAIST - 0.010, 0, -0.048, 0.302, 0.240, 0.052)],
            "r_hips", "钢暗", "facet", "body", "pelvis", cw=0.05)
    u.otube("kn_belt",
            [(Z_WAIST - 0.030, 0, -0.048, 0.320, 0.254, 0.054),
             (Z_WAIST + 0.010, 0, -0.048, 0.330, 0.262, 0.056),
             (Z_WAIST + 0.040, 0, -0.048, 0.322, 0.256, 0.054)],
            "r_hips", "皮革", "chunk2", "body", "belt", cw=0.05)
    u.box("kn_buckle", (0, 0.084, Z_WAIST + 0.004), (0.096, 0.030, 0.064),
          "r_hips", "team_trim", style="chunk", module="body", tag="belt")
    u.box("kn_buckle_in", (0, 0.100, Z_WAIST + 0.004), (0.040, 0.014, 0.032),
          "r_hips", "team", style="hard", module="body", tag="belt")
    # 腰裙：前 / 左 / 右三片（后片短，因为后面是鞍）
    prof_f = [(-0.150, Z_SEAT - 0.010), (0.0, Z_SEAT - 0.034), (0.150, Z_SEAT - 0.010),
              (0.162, Z_SEAT + 0.034), (0.0, Z_SEAT + 0.052), (-0.162, Z_SEAT + 0.034)]
    u.add(K.plate("kn_fauld_f", prof_f, thickness=0.024, offset=-0.062 + 0.150, axis="Y"),
          "r_hips", "甲", "chunk2", "body", "fauld")
    u.add(K.plate("kn_fauld_f_rim",
                  [(-0.156, Z_SEAT + 0.002), (0.156, Z_SEAT + 0.002),
                   (0.150, Z_SEAT - 0.020), (-0.150, Z_SEAT - 0.020)],
                  thickness=0.026, offset=-0.062 + 0.156, axis="Y"),
          "r_hips", "team_trim", "chunk", "body", "fauld")
    for s in (1, -1):
        u.add(K.plate("kn_fauld_s_%d" % s,
                      [(-0.070, Z_SEAT - 0.016), (0.086, Z_SEAT + 0.004),
                       (0.096, Z_SEAT + 0.036), (-0.070, Z_SEAT + 0.044)],
                      thickness=0.024, offset=s * 0.156, axis="X"),
              "r_hips", "甲暗", "chunk2", "body", "fauld")
        u.add(K.plate("kn_fauld_b_%d" % s,
                      [(0.060, Z_SEAT + 0.002), (0.196, Z_SEAT + 0.018),
                       (0.198, Z_SEAT + 0.044), (0.060, Z_SEAT + 0.050)],
                      thickness=0.022, offset=s * 0.140, axis="X"),
              "r_hips", "甲暗", "chunk2", "body", "fauld")


# ── 3. 躯干 ─────────────────────────────────────────────────────────────────
def torso(u):
    u.otube("kn_ab",
            [(Z_WAIST - 0.020, 0, -0.048, 0.276, 0.222, 0.048),
             (Z_WAIST + 0.060, 0, -0.046, 0.290, 0.230, 0.050),
             (Z_CHEST - 0.010, 0, -0.042, 0.306, 0.240, 0.052)],
            "r_spine", "钢暗", "facet", "body", "abdomen", cw=0.05)
    for i, z in enumerate((Z_WAIST + 0.010, Z_WAIST + 0.070)):
        u.arc("kn_abband%d" % i,
              [(z - 0.022, -108, 108, 0.152, 0.122), (z + 0.022, -108, 108, 0.156, 0.125)],
              0.022, "r_spine", "甲暗", "chunk", "body", "abdomen", nu=6,
              inside=(0, 0, z), center=(0, -0.046))
    # 腰带环（把腹甲和腰裙收干净）
    u.arc("kn_waistband",
          [(Z_WAIST - 0.052, -112, 112, 0.156, 0.126),
           (Z_WAIST - 0.014, -112, 112, 0.160, 0.129)],
          0.020, "r_spine", "team_trim", "chunk", "body", "abdomen", nu=6,
          inside=(0, 0, Z_WAIST - 0.03), center=(0, -0.046))

    # 胸甲：八边 + 中脊 + 蓝胸褡
    u.otube("kn_chest",
            [(Z_CHEST - 0.030, 0, -0.040, 0.300, 0.236, 0.052),
             (Z_CHEST + 0.046, 0, -0.036, 0.360, 0.262, 0.060),
             (Z_CHEST + 0.096, 0, -0.034, 0.376, 0.258, 0.062),
             (Z_SHLD - 0.010, 0, -0.030, 0.336, 0.240, 0.056),
             (Z_SHLD + 0.030, 0, -0.028, 0.286, 0.216, 0.048)],
            "r_chest", "甲", "chunk2", "body", "chest", cw=0.062)
    # 中脊（贴着胸甲前面的一条凸棱，不是一根贴片）
    u.add(K.grid_shell("kn_sternum", [
        [(-0.022, 0.070, Z_CHEST - 0.030), (0.0, 0.082, Z_CHEST - 0.030),
         (0.022, 0.070, Z_CHEST - 0.030)],
        [(-0.024, 0.104, Z_CHEST + 0.040), (0.0, 0.118, Z_CHEST + 0.040),
         (0.024, 0.104, Z_CHEST + 0.040)],
        [(-0.022, 0.092, Z_CHEST + 0.116), (0.0, 0.104, Z_CHEST + 0.116),
         (0.022, 0.092, Z_CHEST + 0.116)],
    ], 0.018, inside=(0, 0, Z_CHEST + 0.04)),
          "r_chest", "甲暗", "chunk", "body", "chest")
    # 蓝色胸褡：一条从领口到腰的竖带（步兵的识别点）
    u.add(K.grid_shell("kn_tabard", [
        [(-0.062, 0.088, Z_SHLD + 0.012), (0.062, 0.088, Z_SHLD + 0.012)],
        [(-0.070, 0.104, Z_CHEST + 0.086), (0.070, 0.104, Z_CHEST + 0.086)],
        [(-0.062, 0.100, Z_CHEST - 0.020), (0.062, 0.100, Z_CHEST - 0.020)],
        [(-0.050, 0.090, Z_WAIST - 0.010), (0.050, 0.090, Z_WAIST - 0.010)],
    ], 0.020, inside=(0, 0, Z_CHEST + 0.02)),
          "r_chest", "team", "chunk2", "body", "tabard")
    u.add(K.grid_shell("kn_tabard_rim", [
        [(-0.080, 0.084, Z_SHLD + 0.016), (-0.062, 0.088, Z_SHLD + 0.012)],
        [(-0.088, 0.102, Z_CHEST + 0.090), (-0.070, 0.104, Z_CHEST + 0.086)],
        [(-0.080, 0.098, Z_CHEST - 0.020), (-0.062, 0.100, Z_CHEST - 0.020)],
    ], 0.014, inside=(0, 0, Z_CHEST + 0.02)),
          "r_chest", "team_trim", "chunk", "body", "tabard")
    u.add(K.grid_shell("kn_tabard_rim2", [
        [(0.062, 0.088, Z_SHLD + 0.012), (0.080, 0.084, Z_SHLD + 0.016)],
        [(0.070, 0.104, Z_CHEST + 0.086), (0.088, 0.102, Z_CHEST + 0.090)],
        [(0.062, 0.100, Z_CHEST - 0.020), (0.080, 0.098, Z_CHEST - 0.020)],
    ], 0.014, inside=(0, 0, Z_CHEST + 0.02)),
          "r_chest", "team_trim", "chunk", "body", "tabard")
    # 徽记：蓝底金菱（胸褡正中）
    u.add(K.plate("kn_sigil", [(-0.050, Z_CHEST + 0.078), (0.0, Z_CHEST + 0.130),
                               (0.050, Z_CHEST + 0.078), (0.0, Z_CHEST + 0.026)],
                  thickness=0.020, offset=0.128, axis="Y"),
          "r_chest", "team_trim", "chunk", "body", "sigil")
    u.add(K.plate("kn_sigil_in", [(-0.024, Z_CHEST + 0.078), (0.0, Z_CHEST + 0.106),
                                  (0.024, Z_CHEST + 0.078), (0.0, Z_CHEST + 0.050)],
                  thickness=0.014, offset=0.140, axis="Y"),
          "r_chest", "team", "hard", "body", "sigil")
    # 护喉
    u.otube("kn_gorget",
            [(Z_SHLD - 0.030, 0, -0.028, 0.286, 0.214, 0.048),
             (Z_SHLD + 0.024, 0, -0.026, 0.236, 0.186, 0.040),
             (Z_NECK + 0.010, 0, -0.024, 0.186, 0.156, 0.032)],
            "r_chest", "甲暗", "chunk2", "body", "gorget", cw=0.045)
    u.otube("kn_gorget_rim",
            [(Z_NECK + 0.006, 0, -0.024, 0.190, 0.160, 0.033),
             (Z_NECK + 0.026, 0, -0.024, 0.178, 0.150, 0.031)],
            "r_chest", "team_trim", "chunk", "body", "gorget", cw=0.04)


# ── 4. 臂 ───────────────────────────────────────────────────────────────────
def arms(u):
    for s, side in ((1, "R"), (-1, "L")):
        sh = SH_R if s > 0 else SH_L
        el = ELB_R if s > 0 else ELB_L
        wr = WRI_R if s > 0 else WRI_L
        ua, fa = "r_upperarm_" + side, "r_forearm_" + side
        d = ARM_D[s]
        out = (s * 1.0, -0.20, -0.10)

        u.olimb("kn_jt_sh_" + side, sh + d * -0.060, sh + d * 0.040,
                [(0.0, 0.170, 0.176, 0.048), (1.0, 0.166, 0.170, 0.046)],
                ua, "钢暗", "facet", "body", "joint")
        u.olimb("kn_upper_" + side, sh + d * 0.010, el - d * 0.024,
                [(0.00, 0.150, 0.156, 0.040), (0.55, 0.140, 0.146, 0.036),
                 (1.00, 0.128, 0.134, 0.032)],
                ua, "钢暗", "facet", "body", "upper")
        u.add(fm("kn_rere_" + side, sh + d * 0.020, el - d * 0.044,
                 0.092, 0.080, -118, 118, 2, 6, 0.026, out),
              ua, "甲", "chunk2", "body", "upper")
        u.add(fm("kn_rere_rim_" + side, el - d * 0.074, el - d * 0.048,
                 0.084, 0.088, -114, 114, 1, 6, 0.020, out),
              ua, "team_trim", "chunk", "body", "upper")

        u.olimb("kn_jt_el_" + side, el - d * 0.036,
                el + (wr - el).normalized() * 0.036,
                [(0.0, 0.124, 0.128, 0.032), (1.0, 0.124, 0.128, 0.032)],
                fa, "钢暗", "facet", "body", "joint")
        u.add(dome_patch("kn_couter_" + side, tuple(el + Vector((s * 0.010, -0.014, 0.004))),
                         0.080, 0.078, 0.084, -44 if s > 0 else 136,
                         44 if s > 0 else 224, 24, 94, 3, 2, 0.020),
              fa, "甲暗", "chunk", "body", "elbow")
        u.rivet("kn_couter_stud_" + side, tuple(el + Vector((s * 0.062, -0.038, 0.008))),
                (s * 0.6, -0.4, 0.2), fa, "team_trim", "hard", "body", "elbow",
                r=0.017, h=0.011)

        u.olimb("kn_fore_" + side, el + (wr - el).normalized() * 0.022,
                wr - (wr - el).normalized() * 0.006,
                [(0.00, 0.130, 0.134, 0.034), (0.55, 0.116, 0.120, 0.030),
                 (1.00, 0.106, 0.110, 0.028)],
                fa, "钢暗", "facet", "body", "fore")
        u.add(fm("kn_vamb_" + side, el + (wr - el).normalized() * 0.030,
                 wr - (wr - el).normalized() * 0.010,
                 0.078, 0.068, -132, 132, 2, 6, 0.024, out),
              fa, "甲", "chunk2", "body", "fore")
        u.add(fm("kn_vamb_rib_" + side, el + (wr - el).normalized() * 0.034,
                 wr - (wr - el).normalized() * 0.014,
                 0.084, 0.074, -9, 9, 2, 1, 0.012, out),
              fa, "甲暗", "chunk", "body", "fore")
        u.rivet("kn_cuff_" + side, tuple(wr - (wr - el).normalized() * 0.012),
                tuple(wr - el), fa, "team_trim", "chunk", "body", "cuff",
                r=0.076, h=0.030, n=10)

    gauntlet(u, "R", FIST_R, HDIR_R)
    gauntlet(u, "L", FIST_L, HDIR_L)


def gauntlet(u, side, fist, hdir):
    bone = "r_hand_" + side
    fwd = Vector(hdir).normalized()
    up = (Vector((0, 0, 1)) - fwd * fwd.z).normalized()
    right = fwd.cross(up).normalized()
    c = Vector(fist)

    def P(x, y, z):
        return tuple(c + right * x + fwd * y + up * z)

    rows = []
    for (yy, w, d) in ((-0.055, 0.082, 0.070), (-0.020, 0.104, 0.094),
                       (0.022, 0.108, 0.100), (0.052, 0.094, 0.086),
                       (0.068, 0.064, 0.058)):
        rows.append([P(x, yy, z) for (x, z) in K.octs(w, d, 0.018)])
    u.add(K.loft("kn_fist_" + side, rows), bone, "甲", "chunk", "body", "hand")
    u.box("kn_knuckle_" + side, P(0.0, 0.044, 0.030), (0.094, 0.034, 0.024),
          bone, "钢", style="chunk", module="body", tag="hand")
    u.olimb("kn_thumb_" + side, P(0.048, -0.028, 0.006), P(0.022, 0.038, 0.024),
            [(0.0, 0.044, 0.044, 0.012), (1.0, 0.036, 0.036, 0.010)],
            bone, "甲暗", "chunk", "body", "hand")
    u.box("kn_gaunt_cuff_" + side, P(0.0, -0.052, 0.0), (0.116, 0.040, 0.112),
          bone, "team_trim", style="chunk", module="body", tag="hand")


# ── 5. 护肩（两层叠片，语言同破法者但更"轻"）────────────────────────────────
def pauldrons(u):
    for s, side in ((1, "R"), (-1, "L")):
        sh = SH_R if s > 0 else SH_L
        d = ARM_D[s]
        out = (s * 0.94, -0.16, 0.30)
        base = sh + Vector((s * 0.012, 0, -0.012))
        u.add(fm("kn_pld_a_" + side, base + d * -0.070, base + d * 0.075,
                 0.118, 0.150, -108, 108, 3, 7, 0.030, out),
              "r_upperarm_" + side, "甲暗", "chunk2", "pauldron", "pld1")
        u.add(fm("kn_pld_a_rim_" + side, base + d * 0.062, base + d * 0.090,
                 0.152, 0.156, -104, 104, 1, 7, 0.024, out),
              "r_upperarm_" + side, "team_trim", "chunk", "pauldron", "pld1")
        u.add(fm("kn_pld_b_" + side, base + d * 0.086, base + d * 0.200,
                 0.150, 0.178, -100, 100, 3, 7, 0.028, out),
              "r_upperarm_" + side, "钢暗", "chunk2", "pauldron", "pld2")
        u.add(fm("kn_pld_b_in_" + side, base + d * 0.196, base + d * 0.236,
                 0.176, 0.170, -96, 96, 1, 7, 0.026, out),
              "r_upperarm_" + side, "team", "chunk", "pauldron", "pld2")
        # 顶盖：八角盘 + 金环（俯视不漏）
        u.add(K.olimb("kn_pld_cap_" + side, base + Vector((s * 0.044, 0, 0.034)),
                      base + Vector((s * 0.092, 0, 0.070)),
                      [(0.0, 0.150, 0.150, 0.040), (1.0, 0.120, 0.120, 0.032)]),
              "r_upperarm_" + side, "甲暗", "chunk2", "pauldron", "pld1")
        u.rivet("kn_pld_stud_" + side, tuple(base + Vector((s * 0.098, 0, 0.076))),
                (s * 0.6, 0, 0.8), "r_upperarm_" + side, "team_trim", "hard",
                "pauldron", "pld1", r=0.030, h=0.016)


# ── 6. 大盔 ─────────────────────────────────────────────────────────────────
def head(u):
    z0 = Z_NECK + 0.012
    zt = Z_TOP
    # 盔体：八边、微收、平顶
    u.otube("kn_helm",
            [(z0 - 0.030, 0, -0.024, 0.210, 0.212, 0.040),
             (z0 + 0.020, 0, -0.024, 0.238, 0.238, 0.046),
             (z0 + 0.090, 0, -0.024, 0.248, 0.246, 0.048),
             (z0 + 0.160, 0, -0.022, 0.244, 0.240, 0.048),
             (zt - 0.030, 0, -0.020, 0.222, 0.220, 0.044),
             (zt, 0, -0.018, 0.184, 0.186, 0.038)],
            "r_head", "甲", "chunk2", "head", "helm", cw=0.055)
    # 下颌 / 面甲：一整片正面折面（不是弧），眼缝是两道横槽
    u.add(K.grid_shell("kn_visor", [
        [(-0.104, 0.086, z0 + 0.008), (-0.036, 0.106, z0 + 0.008),
         (0.036, 0.106, z0 + 0.008), (0.104, 0.086, z0 + 0.008)],
        [(-0.112, 0.094, z0 + 0.070), (-0.038, 0.116, z0 + 0.070),
         (0.038, 0.116, z0 + 0.070), (0.112, 0.094, z0 + 0.070)],
        [(-0.110, 0.092, z0 + 0.128), (-0.038, 0.114, z0 + 0.128),
         (0.038, 0.114, z0 + 0.128), (0.110, 0.092, z0 + 0.128)],
    ], 0.026, inside=(0, -0.02, z0 + 0.07)),
          "r_head", "甲", "chunk2", "head", "visor")
    # 眼缝：一条横贯的深槽 + 上下两条金线（俯角下读成"一道黑 + 两道金"）
    u.box("kn_slit", (0, 0.128, z0 + 0.100), (0.176, 0.030, 0.036),
          "r_head", "钢暗", style="facet", module="head", tag="slit")
    u.box("kn_slit_up", (0, 0.132, z0 + 0.126), (0.196, 0.026, 0.014),
          "r_head", "team_trim", style="chunk", module="head", tag="slit")
    u.box("kn_slit_dn", (0, 0.130, z0 + 0.074), (0.190, 0.026, 0.012),
          "r_head", "team_trim", style="chunk", module="head", tag="slit")
    # 鼻脊：从盔顶压到眼缝
    u.add(K.plate("kn_nasal", [(-0.020, z0 + 0.108), (0.020, z0 + 0.108),
                               (0.014, zt - 0.030), (-0.014, zt - 0.030)],
                  thickness=0.024, offset=0.128, axis="Y"),
          "r_head", "甲暗", "chunk", "head", "nasal")
    # 颈围：盔底一圈深色皮，把"头"和"肩"从明度上切开
    u.otube("kn_neckgap",
            [(z0 - 0.036, 0, -0.024, 0.196, 0.198, 0.038),
             (z0 - 0.004, 0, -0.024, 0.202, 0.204, 0.038)],
            "r_head", "皮革暗", "chunk", "head", "neckgap", cw=0.04)
    # 蓝箍（步兵的识别点：盔沿一圈蓝，压一条金线）
    u.otube("kn_helm_band",
            [(z0 + 0.024, 0, -0.024, 0.246, 0.246, 0.047),
             (z0 + 0.052, 0, -0.024, 0.252, 0.252, 0.048),
             (z0 + 0.074, 0, -0.024, 0.246, 0.246, 0.047)],
            "r_head", "team", "chunk2", "head", "band", cw=0.05)
    u.otube("kn_helm_band_rim",
            [(z0 + 0.070, 0, -0.024, 0.249, 0.249, 0.047),
             (z0 + 0.082, 0, -0.024, 0.244, 0.244, 0.046)],
            "r_head", "team_trim", "chunk", "head", "band", cw=0.045)
    # 冠脊：一片竖立的蓝鳍（步兵顶脊的放大版）
    u.add(K.plate("kn_crest", [(-0.130, zt - 0.030), (0.070, zt - 0.026),
                               (0.048, zt + 0.048), (-0.112, zt + 0.040)],
                  thickness=0.030, offset=0.0, axis="Y"),
          "r_head", "team", "chunk", "head", "crest")
    u.add(K.plate("kn_crest_rim", [(-0.136, zt - 0.024), (-0.118, zt - 0.020),
                                   (-0.120, zt + 0.044), (-0.138, zt + 0.040)],
                  thickness=0.032, offset=0.0, axis="Y"),
          "r_head", "team_trim", "chunk", "head", "crest")
    # 颊甲（两片，把脸收窄）
    for s in (1, -1):
        u.add(K.plate("kn_cheek_%d" % s,
                      [(-0.020, z0 + 0.010), (0.070, z0 + 0.030),
                       (0.078, z0 + 0.110), (-0.014, z0 + 0.104)],
                      thickness=0.026, offset=s * 0.108, axis="X"),
              "r_head", "甲暗", "chunk2", "head", "cheek")
        u.rivet("kn_cheek_riv_%d" % s, (s * 0.124, 0.030, z0 + 0.062),
                (s * 1.0, 0.12, 0), "r_head", "team_trim", "hard", "head", "cheek",
                r=0.014, h=0.010)


# ── 7. 骑枪 ─────────────────────────────────────────────────────────────────
def lance(u):
    """骨轴 = 枪尖方向。握点在 t=GRIP_T，绕骨轴自转 = 枪身滚转。"""
    d = LANCE_D
    up = Vector((0, 0, 1))
    ex = LANCE_D.cross(up)
    if ex.length < 1e-4:
        ex = Vector((1, 0, 0))
    ex.normalize()
    ey = d.cross(ex).normalized()
    B = LANCE_BUTT

    def P(t, x=0.0, y=0.0):
        return tuple(B + d * (LANCE_L * t) + ex * x + ey * y)

    # 枪杆：0→0.86 收细，握把处略粗
    rows = []
    for (t, r) in ((0.00, 0.026), (0.06, 0.038), (0.42, 0.042), (0.55, 0.040),
                   (0.80, 0.032), (0.90, 0.026)):
        rows.append([P(t, x, y) for (x, y) in K.octs(r * 2, r * 2, r * 0.55)])
    u.add(K.loft("kn_lance_shaft", rows), "weapon_R", "皮革暗", "chunk2", "weapon", "shaft")
    # 枪尖：菱形叶刃（两段折面，压一条钢脊）
    tip = []
    for (t, w) in ((0.885, 0.030), (0.918, 0.082), (0.960, 0.056), (1.0, 0.0)):
        tip.append([P(t, x, y) for (x, y) in K.octs(w, w * 0.42, w * 0.30)])
    u.add(K.loft("kn_lance_tip", tip), "weapon_R", "钢", "chunk", "weapon", "tip")
    u.add(K.loft("kn_lance_rib", [
        [P(0.88, x, y) for (x, y) in K.octs(0.016, 0.052, 0.004)],
        [P(0.955, x, y) for (x, y) in K.octs(0.010, 0.030, 0.003)],
    ]), "weapon_R", "钢暗", "sharp", "weapon", "tip")
    # 护手（锥形护腕盘）+ 金环
    u.add(K.olimb("kn_lance_vamp", P(0.548), P(0.610),
                  [(0.0, 0.070, 0.070, 0.020), (1.0, 0.108, 0.108, 0.030)]),
          "weapon_R", "甲", "chunk2", "weapon", "vamp")
    u.rivet("kn_lance_vamp_rim", P(0.606), tuple(d), "weapon_R", "team_trim",
            "chunk", "weapon", "vamp", r=0.108, h=0.018, n=10)
    # 握把包皮
    u.add(K.olimb("kn_lance_grip", P(0.430), P(0.520),
                  [(0.0, 0.096, 0.096, 0.026), (1.0, 0.092, 0.092, 0.026)]),
          "weapon_R", "皮革", "chunk", "weapon", "grip")
    # 旗（team 蓝 + 金边）：贴枪杆挂一片梯形三角旗，向右侧展开
    pen = [
        [P(0.815, 0.000, 0.0), P(0.815, 0.052, 0.0), P(0.815, 0.100, 0.0)],
        [P(0.762, 0.006, 0.0), P(0.742, 0.078, 0.0), P(0.700, 0.148, 0.0)],
    ]
    u.add(K.grid_shell("kn_pennon", pen, 0.012,
                       inside=tuple(Vector(pen[0][0]).lerp(Vector(pen[1][2]), 0.4)
                                    + ey * 0.0)),
          "weapon_R", "team", "sharp", "weapon", "pennon")
    u.add(K.grid_shell("kn_pennon_rim", [
        [P(0.762, 0.006, 0.0), P(0.742, 0.078, 0.0), P(0.700, 0.148, 0.0)],
        [P(0.750, 0.008, 0.0), P(0.730, 0.082, 0.0), P(0.688, 0.152, 0.0)],
    ], 0.014, inside=tuple(P(0.75, 0.06, 0.0))),
          "weapon_R", "team_trim", "sharp", "weapon", "pennon")


def build(low=False, modules=None):
    want = set(MODULES if modules is None else modules)
    u = K.Unit2(PREFIX, MATS, low=low)
    if "horse" in want:
        HK.body(u)
        HK.legs(u)
        HK.neck(u)
        HK.head(u)
        HK.tail(u)
    if "tack" in want:
        HK.tack(u)
    if "body" in want:
        legs(u)
        pelvis(u)
        torso(u)
        arms(u)
    if "pauldron" in want:
        pauldrons(u)
    if "head" in want:
        head(u)
    if "weapon" in want:
        lance(u)
    return u


def build_rig(name="RIG_骑士"):
    return K.build_rig(BONES, name)


def report():
    return "\n".join([
        "[rider] seat z=%.3f hip z=%.3f helm=%.3f" % (Z_SEAT, Z_HIP, Z_TOP),
        "[thigh] len=%.3f shin=%.3f knee=(%.3f,%.3f)" % (L_THIGH, L_SHIN, KNE_R.y, KNE_R.z),
        "[armR] elbow=(%.3f,%.3f,%.3f) wrist=(%.3f,%.3f,%.3f) reach=%.3f/%.3f"
        % (ELB_R.x, ELB_R.y, ELB_R.z, WRI_R.x, WRI_R.y, WRI_R.z,
           (WRI_R - SH_R).length, L_UPPER + L_FORE),
        "[lance] len=%.3f grip=(%.3f,%.3f,%.3f) tip=(%.3f,%.3f,%.3f)"
        % (LANCE_L, FIST_R.x, FIST_R.y, FIST_R.z, LANCE_TIP.x, LANCE_TIP.y, LANCE_TIP.z),
        "[bones] %d  [modules] %s" % (len(BONES), ",".join(MODULES)),
    ])
