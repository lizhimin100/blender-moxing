"""unit_斥候.py —— 野怪·豺狼人斥候（精模 / 硬边支线）v3

**一句话**：1.82 m 的棕灰皮豺狼人刺客 —— **连帽披风从头罩到小腿**、兜帽下露出长吻大耳，
腰间一圈备用匕首，两手各一把 0.46 m 的宽刃匕首，习惯性含胸蹲伏。

与战士/萨满共用 `gnoll_kit2`。差异：
  ① 尺寸最小（肩宽 0.50 / 身高 1.82），四肢细 20%，驼背更重（含胸）；
  ② 皮肤走**棕灰**（不饱和），队色只出现在披风内衬与兜帽缘；
  ③ 披风 = 兜帽（head 骨）+ 斗篷（cape 骨）+ 下摆破布，三段式；
  ④ 双匕首（weapon_R / weapon_L），刀身 0.46 m，**不做小刀片**。
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

import gnoll_kit2 as GK  # noqa: E402
import unitkit as KU  # noqa: E402
import unitkit2 as K  # noqa: E402

NAME = "豺狼人斥候"
PREFIX = "gr"

MATS = {
    "皮肤":      dict(hexcol="#6B5C4C", metal=0.00, rough=0.68),
    "皮肤暗":    dict(hexcol="#3A3027", metal=0.00, rough=0.72),
    "皮肤亮":    dict(hexcol="#8C7C68", metal=0.00, rough=0.62),
    "骨":        dict(hexcol="#C2B79E", metal=0.00, rough=0.58),
    "皮革":      dict(hexcol="#443528", metal=0.00, rough=0.80),
    "皮革暗":    dict(hexcol="#261C14", metal=0.00, rough=0.84),
    "布":        dict(hexcol="#4A4238", metal=0.00, rough=0.88),
    "布暗":      dict(hexcol="#2E2822", metal=0.00, rough=0.90),
    "锈铁":      dict(hexcol="#6A5040", metal=0.45, rough=0.56),
    "刃":        dict(hexcol="#71767D", metal=0.24, rough=0.56),
    "team":      dict(hexcol="#743A2E", metal=0.00, rough=0.72),
    "team_trim": dict(hexcol="#A99578", metal=0.10, rough=0.48),
}

# 双匕首握点（掌中心）
G_R = Vector((0.352, 0.176, 0.986))
G_L = Vector((-0.352, 0.176, 0.986))
DAG_LEN = 0.462

S = GK.Gnoll(
    NAME=NAME, PREFIX=PREFIX,
    MATS=MATS,
    M=dict(skin="皮肤", dark="皮肤暗", hi="皮肤亮", bone="骨",
           leather="皮革", ldark="皮革暗", metal="锈铁", team="team", trim="team_trim"),
    LEG_K=0.94,
    HIP=Vector((0.196, -0.018, 0.948)),
    KNE=Vector((0.212, 0.176, 0.640)),
    HCK=Vector((0.192, -0.150, 0.300)),
    BAL=Vector((0.188, -0.134, 0.092)),
    TOE=Vector((0.188, 0.176, 0.016)),
    HEEL=Vector((0.186, -0.232, 0.000)),
    TOE_Y=(-0.074, 0.018, 0.122),
    Z_WAIST=1.030, Z_CH0=1.170, Z_NECK=1.432, Z_HEAD=1.512,
    SH=Vector((0.272, -0.014, 1.462)),
    L_UPPER=0.338, L_FORE=0.286,
    WRI_R=Vector((0.336, 0.146, 0.984)),
    HDIR_R=Vector((0.06, 0.50, -0.86)),
    WRI_L=Vector((-0.336, 0.146, 0.984)),
    HDIR_L=Vector((-0.06, 0.50, -0.86)),
    TAIL0=Vector((0.0, -0.160, 0.930)),
    TAIL1=Vector((0.044, -0.396, 0.842)),
    TAIL2=Vector((0.098, -0.678, 0.700)),
    TAIL_R=(0.052, 0.040, 0.027),
    CHEST=[(1.174, 0.012, 0.386, 0.300, 0.066),
           (1.244, 0.004, 0.452, 0.356, 0.078),
           (1.312, -0.010, 0.492, 0.392, 0.086),
           (1.382, -0.026, 0.496, 0.396, 0.086),
           (1.442, -0.046, 0.452, 0.360, 0.078),
           (1.496, -0.072, 0.376, 0.300, 0.066),
           (1.536, -0.092, 0.296, 0.240, 0.052),
           (1.560, -0.100, 0.240, 0.192, 0.042)],
    Z_ABD0=1.012,
    # 头：窄长吻、大耳（侦察兵的辨识点在耳朵）
    SKULL=[(-0.078, 1.632, 0.180, 0.190),
           (-0.010, 1.622, 0.224, 0.244),
           (0.072, 1.612, 0.232, 0.244),
           (0.148, 1.596, 0.220, 0.228),
           (0.216, 1.580, 0.198, 0.196),
           (0.284, 1.562, 0.174, 0.166),
           (0.350, 1.544, 0.156, 0.144),
           (0.412, 1.530, 0.136, 0.122),
           (0.452, 1.524, 0.106, 0.096)],
    JAW=[(0.216, 1.480, 0.172, 0.068),
         (0.292, 1.470, 0.158, 0.060),
         (0.360, 1.464, 0.134, 0.050),
         (0.414, 1.462, 0.096, 0.038)],
    MUZZLE=((0.198, 1.696, 0.148), (0.276, 1.666, 0.140),
            (0.352, 1.636, 0.122), (0.436, 1.596, 0.094)),
    NOSE=((0.400, 0.048, 0.018, 1.594), (0.420, 0.058, 0.024, 1.596),
          (0.438, 0.050, 0.018, 1.588)),
    MOUTH=(0.070, 0.340, 1.498, 0.170, 0.008),
    FANG_U=(Vector((0.072, 0.362, 1.504)), Vector((0.003, 0.003, -0.040)), 0.030, 0.026),
    FANG_L=(Vector((0.066, 0.348, 1.490)), Vector((0.002, 0.002, 0.036)), 0.028, 0.024),
    EYE=(0.066, 0.276, 1.622, 0.038, 0.020, 0.024),
    SOCKET=(0.064, 0.260, 1.620, 0.058, 0.032, 0.036),
    BROW=(0.080, 0.264, 1.656, 0.086, 0.048, 0.018),
    BROW_BONE=None, BROW_RIM=None,
    EAR_ROOT=Vector((0.098, 0.030, 1.658)),
    EAR_TIP=Vector((0.246, -0.098, 1.802)),
    EAR_W=(0.122, 0.138, 0.052, 0.036),
    EAR_IN=(0.062, 0.072, 0.012, 0.010),
    FINS=(("head", 0.058, 1.716, -0.028, 1.744, 0.092, 0.040),
          ("head", -0.038, 1.700, -0.130, 1.720, 0.086, 0.036),
          ("chest", -0.210, 1.556, -0.268, 1.606, 0.084, 0.028)),
    MANE_N=((0.0, -0.052, 1.610), (0.0, -0.212, 1.548), 0.118, 0.076),
)

GK.set_arms(S, G_R, 0.086, (0.95, 0.36, -0.42))
S.HDIR_R = Vector((0.06, 0.50, -0.86)).normalized()
S.POLE_L = (-0.95, 0.36, -0.42)
S.setup()

MODULES = ("body", "head", "cloak", "gear", "daggers")

# 披风参数
CAPE_TOP = 1.500
CAPE_BOT = 0.560
HOOD_TOP = 1.836


# ══ 披风：兜帽（head）+ 斗篷（cape）══════════════════════════════════════════
# 兜帽分两件做，避免"开口行"和"整圈行"接在同一张网格里扭面：
#   ① cl_hood   身高 1.42→1.70 的环形围片，正面留出脸的开口（角度 52..308）；
#   ② cl_crown  1.68→1.84 的整圈帽顶，半径略大，压住接缝。
# 耳朵从帽顶侧后方**穿过布面**长出去 —— 这是真实的兜帽带耳孔，交接处压一圈
# 皮革耳箍（cl_earring）把"穿孔"讲清楚；三件同属 head 模块 + head 骨。
def cloak(u):
    hood = [(1.548, 68, 292, 0.150, 0.162, -0.038),
            (1.600, 62, 298, 0.156, 0.168, -0.042),
            (1.652, 56, 304, 0.156, 0.168, -0.046),
            (1.700, 50, 310, 0.142, 0.154, -0.050),
            (1.742, 46, 314, 0.114, 0.126, -0.054)]
    u.add(K.arc_panel("cl_hood", hood, 0.022, 18, None, (0.0, -0.020)),
          "head", "布", "chunk", "head", "hood")
    # 帽顶：整圈锥壳（开口在上方收掉）
    crown = [(1.712, -180, 180, 0.142, 0.154, -0.052),
             (1.752, -180, 180, 0.120, 0.132, -0.058),
             (1.792, -180, 180, 0.088, 0.100, -0.062),
             (1.826, -180, 180, 0.046, 0.056, -0.064)]
    u.add(K.arc_panel("cl_crown", crown, 0.022, 18, None, (0.0, -0.020)),
          "head", "布", "chunk", "head", "hood")
    u.add(GK.disc("cl_crown_cap", (0.0, -0.062, 1.824), (0, 0, 1), 0.054, 0.020, 12),
          "head", "布", "chunk", "head", "hood")
    # 帽檐滚边（team_trim，9 mm）
    u.add(K.arc_panel("cl_hood_trim",
                      [(1.544, 68, 292, 0.154, 0.166, -0.038),
                       (1.566, 66, 294, 0.154, 0.166, -0.040)],
                      0.030, 18, None, (0.0, -0.020)),
          "head", "team_trim", "chunk", "head", "hood")
    # 后颈围布：把兜帽和斗篷接起来（只走背侧 160°，避开三角肌）
    u.add(K.arc_panel("cl_cowl",
                      [(1.340, 106, 254, 0.228, 0.208, -0.090),
                       (1.440, 100, 260, 0.204, 0.188, -0.074),
                       (1.552, 96, 264, 0.168, 0.156, -0.056)],
                      0.020, 12, None, (0.0, -0.060)),
          "head", "布", "chunk", "head", "hood")
    # 帽里暗档
    u.add(K.arc_panel("cl_hood_in",
                      [(1.552, 72, 288, 0.132, 0.144, -0.036),
                       (1.620, 64, 296, 0.134, 0.146, -0.044),
                       (1.700, 50, 310, 0.122, 0.134, -0.050)],
                      0.010, 12, None, (0.0, -0.020)),
          "head", "布暗", "chunk", "head", "hood")
    # 帽尖（后脑一片三角布，披风从下面接出去）
    u.add(GK.fin("cl_hood_tip", -0.190, 1.756, -0.318, 1.700, 0.150, 0.026),
          "head", "布", "chunk", "head", "hood")
    # 耳箍：兜帽穿孔处一圈皮革
    for sx in (1, -1):
        er = Vector((sx * S.EAR_ROOT.x, S.EAR_ROOT.y, S.EAR_ROOT.z))
        et = Vector((sx * S.EAR_TIP.x, S.EAR_TIP.y, S.EAR_TIP.z))
        d = (et - er).normalized()
        u.add(GK.ring("cl_earring%d" % sx, tuple(er + d * 0.030),
                      tuple(d), 0.048, 0.066, 0.024, 8),
              "head", "皮革暗", "chunk", "head", "earring")

    # 斗篷：一整片，绕背 260°，从肩垂到小腿（前缘在身体两侧，正面也看得见）
    rows = [(1.500, 100, 260, 0.256, 0.182, -0.186),
            (1.380, 98, 262, 0.284, 0.202, -0.168),
            (1.210, 92, 268, 0.322, 0.242, -0.140),
            (1.020, 86, 274, 0.358, 0.292, -0.112),
            (0.840, 80, 280, 0.400, 0.346, -0.084),
            (0.680, 75, 285, 0.434, 0.388, -0.064),
            (CAPE_BOT, 71, 289, 0.456, 0.414, -0.048)]
    # 背后留 24° 的**尾巴开衩**：两片，尾巴从缝里出去
    for tag, lo, hi in (("L", None, 165), ("R", 195, None)):
        sub = []
        for (z, a0, a1, rx, ry, cy) in rows:
            sub.append((z, a0 if lo is None else lo, a1 if hi is None else hi, rx, ry, cy))
        u.add(K.arc_panel("cl_cape" + tag, sub, 0.022, 12, None, (0.0, -0.040)),
              "cape", "布", "chunk", "cloak", "cape")
    # 前缘两条队色内衬（正面是两道竖线）
    for s2 in (1, -1):
        sgn = 1 if s2 > 0 else -1
        u.add(K.arc_panel("cl_edge%d" % s2,
                          [(1.498, 100, 106, 0.260, 0.186, -0.184) if sgn > 0
                           else (1.498, 254, 260, 0.260, 0.186, -0.184),
                           (1.200, 92, 98, 0.328, 0.246, -0.138) if sgn > 0
                           else (1.200, 262, 268, 0.328, 0.246, -0.138),
                           (0.860, 82, 88, 0.416, 0.340, -0.078) if sgn > 0
                           else (0.860, 272, 278, 0.416, 0.340, -0.078),
                           (CAPE_BOT, 72, 78, 0.460, 0.418, -0.046) if sgn > 0
                           else (CAPE_BOT, 282, 288, 0.460, 0.418, -0.046)],
                          0.014, 3, None, (0.0, -0.060)),
              "cape", "team", "chunk", "cloak", "lining")
    # 下摆破布：八片
    for i in range(8):
        a = math.radians(70 + i * (220.0 / 7))
        if 163 < (70 + i * (220.0 / 7)) < 197:
            continue
        cx, cy = 0.462 * math.sin(a), -0.048 + 0.418 * math.cos(a)
        z0 = CAPE_BOT + 0.014
        z1 = CAPE_BOT - (0.086 if i % 2 else 0.046)
        u.add(KU.claw("cl_rag%d" % i, (cx, cy, z0), (cx * 1.03, cy * 1.02, z1),
                      0.098, 0.022), "cape", "布暗", "chunk", "cloak", "rag")
    # 下摆内侧一条暗带（走光时露出来）
    u.add(K.arc_panel("cl_lining",
                      [(CAPE_BOT + 0.180, 72, 288, 0.414, 0.356, -0.076),
                       (CAPE_BOT + 0.040, 69, 291, 0.456, 0.408, -0.048)],
                      0.010, 20, None, (0.0, -0.060)),
          "cape", "布暗", "chunk", "cloak", "lining")
    # 领口骨扣
    u.add(GK.ring("cl_clasp", (0.0, 0.212, 1.452), (0.10, 0.98, 0.16),
                  0.020, 0.034, 0.014, 6), "chest", "骨", "chunk", "cloak", "clasp")
    u.add(GK.octa("cl_clasp_b", (0.0, 0.226, 1.420), 0.026, 0.022, n=5),
          "chest", "骨", "chunk", "cloak", "clasp")


# ══ 匕首 ════════════════════════════════════════════════════════════════════
def _dagger(u, side, grip, hdir):
    bone = "weapon_" + side
    g = Vector(grip)
    d = Vector(hdir).normalized()
    # 局部系：ez = 刀轴（+Y），ex = 刀身宽度方向，ey = 刀身厚度方向
    up = Vector((0, 0, 1))
    ex = up.cross(d).normalized()
    ey = d.cross(ex).normalized()

    def P(x, y, t):
        return tuple(g + ex * x + ey * y + d * t)

    # 握柄（在拳心里，-0.15..0.014）
    rows = []
    for (t, w, th) in ((-0.150, 0.058, 0.052), (-0.120, 0.066, 0.060),
                       (-0.020, 0.066, 0.060), (0.014, 0.058, 0.052)):
        rows.append([P(x, y, t) for (x, y) in K.octs(w, th, 0.016, 0.014)])
    u.add(K.loft("dg_grip_" + side, rows), bone, "皮革", "chunk", "daggers", "grip")
    u.add(GK.ring("dg_guard_" + side, P(0, 0, 0.020), d, 0.030, 0.062, 0.020, 8),
          bone, "锈铁", "chunk2", "daggers", "guard")
    u.add(GK.octa("dg_pommel_" + side, P(0, 0, -0.176), 0.040, 0.034, n=6),
          bone, "锈铁", "chunk2", "daggers", "pommel")

    # 刀身：0.46 m，根部 0.070 宽，62% 后收尖；双面开刃（截面是扁六边）
    prof = ((0.034, 0.086, 0.026), (0.120, 0.094, 0.028), (0.240, 0.088, 0.026),
            (0.340, 0.078, 0.022), (0.408, 0.062, 0.017), (DAG_LEN - 0.030, 0.030, 0.010))
    rows = []
    for (t, w, th) in prof:
        rows.append([P(x, y, t) for (x, y) in K.octs(w, th, 0.028, 0.008)])
    u.add(K.loft("dg_blade_" + side, rows), bone, "刃", "facet", "daggers", "blade")
    u.add(KU.claw("dg_tip_" + side, P(0, 0, DAG_LEN - 0.034),
                  P(0, 0, DAG_LEN), 0.034, 0.016), bone, "刃", "facet", "daggers", "blade")
    # 血槽：沿刀轴一条窄脊（上下两片薄铁压出来的暗线）
    rows = [[P(x, y, t) for (x, y) in K.octs(0.020, 0.030, 0.004, 0.004)]
            for t in (0.060, 0.360)]
    u.add(K.loft("dg_full_" + side, rows), bone, "锈铁", "chunk", "daggers", "fuller")


# ══ 装备 ════════════════════════════════════════════════════════════════════
def gear(u):
    # 胸前斜挂的两条皮索 + 三枚备用小刀（刀柄朝下）
    A = Vector((-0.176, 0.212, 1.444))
    B = Vector((0.180, 0.234, 1.180))
    u.olimb("sg_bandolier", tuple(A), tuple(B),
            [(0.00, 0.070, 0.024, 0.012), (1.00, 0.070, 0.024, 0.012)],
            "chest", "皮革", "chunk", "gear", "bandolier")
    for i, t in enumerate((0.22, 0.46, 0.70)):
        p = A.lerp(B, t)
        u.olimb("sg_sheath%d" % i, tuple(p + Vector((0, 0.012, 0.014))),
                tuple(p + Vector((0.020, 0.010, -0.086))),
                [(0.00, 0.036, 0.030, 0.010), (1.00, 0.030, 0.026, 0.008)],
                "chest", "皮革暗", "chunk", "gear", "sheath")
        u.add(GK.octa("sg_knife%d" % i, tuple(p + Vector((0.024, 0.010, -0.098))),
                      0.024, 0.020, n=5), "chest", "骨", "chunk", "gear", "sheath")

    # 腰间匕首套（左右各一，空着 —— 手上那两把就是从这拔的）
    for s in (1, -1):
        u.olimb("sg_hip_sheath%d" % s,
                (s * 0.238, 0.086, 1.010), (s * 0.262, 0.028, 0.902),
                [(0.00, 0.062, 0.044, 0.014), (1.00, 0.050, 0.036, 0.012)],
                "hips", "皮革暗", "chunk", "gear", "hipsheath")
        u.add(GK.ring("sg_hip_ring%d" % s, (s * 0.246, 0.062, 0.968),
                      (s * 0.3, 0.5, -0.8), 0.028, 0.042, 0.016, 6),
              "hips", "锈铁", "chunk", "gear", "hipsheath")

    # 护腕：左右各两道皮环 + 一枚铁钉
    for s in (1, -1):
        side = S.side(s)
        wr = S.wri(s)
        el = S.ELB_R if s > 0 else S.ELB_L
        d = (wr - el).normalized()
        for i, t in enumerate((0.62, 0.80)):
            a = el + (wr - el) * t
            b = el + (wr - el) * (t + 0.10)
            u.olimb("sg_wrap%d_%d" % (s, i), tuple(a), tuple(b),
                    [(0.0, 0.114, 0.126, 0.030), (1.0, 0.110, 0.122, 0.028)],
                    "forearm_" + side, "皮革", "chunk", "gear", "wrap")
        u.rivet("sg_wrap_pin%d" % s,
                tuple(el + (wr - el) * 0.66 + Vector((0, -0.076, 0))),
                (0, -1, 0.2), "forearm_" + side, "锈铁",
                style="hard", module="gear", tag="wrap", r=0.015, h=0.011, n=6)

    # 右小腿绑带（不对称：只有右腿，跑起来一眼分得出左右）
    kn, hc = S.KNE, S.HCK
    u.olimb("sg_shinwrap", tuple(kn + (hc - kn) * 0.30), tuple(kn + (hc - kn) * 0.56),
            [(0.00, 0.140, 0.158, 0.036), (1.00, 0.128, 0.146, 0.032)],
            "shin_R", "布", "chunk", "gear", "shinwrap")
    u.olimb("sg_shinwrap2", tuple(kn + (hc - kn) * 0.60), tuple(kn + (hc - kn) * 0.74),
            [(0.00, 0.122, 0.140, 0.030), (1.00, 0.114, 0.132, 0.028)],
            "shin_R", "布暗", "chunk", "gear", "shinwrap")

    # 兜帽下的眼罩（左眼一块皮革，独眼斥候 —— 96 px 也看得见）
    u.box("sg_eyepatch", (-0.070, 0.284, 1.624), (0.074, 0.028, 0.042),
          "head", "皮革暗", rot=(0, math.radians(-12), 0.16), style="chunk",
          module="gear", tag="eyepatch")
    u.olimb("sg_eyestrap", (-0.104, 0.246, 1.664), (-0.176, 0.086, 1.686),
            [(0.00, 0.020, 0.016, 0.006), (1.00, 0.018, 0.014, 0.006)],
            "head", "皮革", "chunk", "gear", "eyepatch")


# ══ 组装 ════════════════════════════════════════════════════════════════════
def build(low=False, modules=None):
    want = set(MODULES if modules is None else modules)
    u = K.Unit2(PREFIX, MATS, low=low)
    if "body" in want:
        GK.legs(u, S)
        GK.pelvis(u, S, kilt=True, kilt_z=0.802, kilt_mat="皮革")
        GK.torso(u, S, straps=False, paint=None)
        GK.neck(u, S)
        GK.arms(u, S)
        for side, s, g in (("R", 1, G_R), ("L", -1, G_L)):
            GK.fist_around(u, S, side, g, S.hdir(s), (-s * 1.0, 0.10, 0.0),
                           r=0.036, k=0.94, cuff=True, tag="palm")
        GK.tail(u, S)
    if "head" in want:
        GK.head(u, S)
    if "cloak" in want:
        cloak(u)
    if "gear" in want:
        gear(u)
    if "daggers" in want:
        _dagger(u, "R", G_R, S.HDIR_R)
        _dagger(u, "L", G_L, S.HDIR_L)
    return u


def build_rig(name="RIG_" + NAME):
    extra = [
        ("weapon_R", tuple(G_R), tuple(G_R + S.HDIR_R * 0.22), "hand_R"),
        ("weapon_L", tuple(G_L), tuple(G_L + S.HDIR_L * 0.22), "hand_L"),
        ("cape", (0.0, -0.090, 1.470), (0.0, -0.150, 1.030), "chest"),
    ]
    return K.build_rig(GK.bones(S, extra=extra), name)


def report():
    return "\n".join([
        "[joints] hip=%.3f knee=(%.3f,%.3f) hock=(%.3f,%.3f) top=%.3f"
        % (S.Z_HIP, S.KNE.y, S.KNE.z, S.HCK.y, S.HCK.z, S.Z_TOP),
        "[leg] thigh=%.3f shin=%.3f foot=%.3f toe=%.3f"
        % (S.L_THIGH, S.L_SHIN, S.L_FOOT, S.L_TOE),
        "[dagger] len=%.3f grip=(%.3f,%.3f,%.3f)" % (DAG_LEN, G_R.x, G_R.y, G_R.z),
        "[cape] %.3f..%.3f" % (CAPE_TOP, CAPE_BOT),
    ])
