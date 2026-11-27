"""unit_战士.py —— 野怪·豺狼人战士（精模 / 硬边支线）v3

**一句话**：2.16 m 的棕皮豺狼人重步兵 —— 宽颅短吻、断耳、鬃冠到肩，右肩三层锈铁甲、
左手圆盾、右手一把 1.05 m 的宽刃砍刀。

与萨满共用 `gnoll_kit2`（腿/躯干/头/尾/手全是同一套组件），差异只在：
  ① 尺寸表更宽更矮（肩宽 0.66 / 腿短 8%）、皮肤换成棕色三档；
  ② 装备换阵营：锈铁 + 皮革（萨满是骨 + 骨甲），刀盾在**右/左**手；
  ③ 头部没有骨额板，改成皮革头箍 + 断耳（左耳缺口）；
  ④ team 只落在腰布 / 胸前战纹 / 盾面一角。

组件化：MODULES = body / head / gear / sword / shield（gear 里按 tag 分级，
`build(modules=["sword"])` 就能单独出一把刀）。
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

NAME = "豺狼人战士"
PREFIX = "gw"

# ── 材质（10 味；棕皮三档 + 锈铁 + 刃）──────────────────────────────────────
MATS = {
    "皮肤":      dict(hexcol="#7A4E2E", metal=0.00, rough=0.66),
    "皮肤暗":    dict(hexcol="#452818", metal=0.00, rough=0.70),
    "皮肤亮":    dict(hexcol="#9C6B42", metal=0.00, rough=0.60),
    "骨":        dict(hexcol="#C9BFA6", metal=0.00, rough=0.55),
    "皮革":      dict(hexcol="#4A3A2C", metal=0.00, rough=0.78),
    "皮革暗":    dict(hexcol="#2A2018", metal=0.00, rough=0.82),
    "锈铁":      dict(hexcol="#6E5142", metal=0.55, rough=0.52),
    "刃":        dict(hexcol="#7C8188", metal=0.28, rough=0.55),
    "team":      dict(hexcol="#743A2E", metal=0.00, rough=0.70),
    "team_trim": dict(hexcol="#A99578", metal=0.10, rough=0.46),
}

# 刀握点 / 盾心
GRIP = Vector((0.472, 0.238, 1.078))
SC = Vector((-0.432, 0.352, 1.300))     # shield center
SHIELD_N = Vector((0.26, 0.95, 0.12)).normalized()
SHIELD_R = 0.360

S = GK.Gnoll(
    NAME=NAME, PREFIX=PREFIX,
    MATS=MATS,
    M=dict(skin="皮肤", dark="皮肤暗", hi="皮肤亮", bone="骨",
           leather="皮革", ldark="皮革暗", metal="锈铁", team="team", trim="team_trim"),
    LEG_K=1.16,
    # 关节：比萨满矮 2 cm 的腿、宽 18% 的肩
    HIP=Vector((0.238, -0.022, 1.098)),
    KNE=Vector((0.258, 0.196, 0.752)),
    HCK=Vector((0.232, -0.168, 0.348)),
    BAL=Vector((0.228, -0.152, 0.104)),
    TOE=Vector((0.228, 0.212, 0.018)),
    HEEL=Vector((0.224, -0.262, 0.000)),
    TOE_Y=(-0.088, 0.022, 0.140),
    Z_WAIST=1.198, Z_CH0=1.368, Z_NECK=1.640, Z_HEAD=1.720,
    SH=Vector((0.330, -0.015, 1.688)),
    L_UPPER=0.398, L_FORE=0.328,
    WRI_L=Vector((-0.398, 0.238, 1.262)),
    HDIR_L=Vector((0.05, 0.93, -0.36)),
    TAIL0=Vector((0.0, -0.190, 1.078)),
    TAIL1=Vector((0.052, -0.452, 0.968)),
    TAIL2=Vector((0.118, -0.772, 0.798)),
    TAIL_R=(0.066, 0.050, 0.034),
    # 躯干：宽 14%、厚 12%
    CHEST=[(1.372, 0.014, 0.470, 0.362, 0.080),
           (1.448, 0.006, 0.564, 0.434, 0.096),
           (1.534, -0.006, 0.626, 0.484, 0.108),
           (1.618, -0.018, 0.642, 0.498, 0.112),
           (1.688, -0.036, 0.600, 0.466, 0.105),
           (1.756, -0.062, 0.504, 0.396, 0.091),
           (1.808, -0.082, 0.402, 0.320, 0.073),
           (1.836, -0.090, 0.326, 0.254, 0.059)],
    Z_ABD0=1.188,
    # 头：宽颅、短吻、重下颌
    SKULL=[(-0.086, 1.930, 0.202, 0.220),
           (-0.014, 1.918, 0.254, 0.286),
           (0.078, 1.906, 0.262, 0.286),
           (0.162, 1.886, 0.246, 0.264),
           (0.238, 1.866, 0.222, 0.222),
           (0.308, 1.846, 0.196, 0.184),
           (0.386, 1.824, 0.178, 0.162),
           (0.456, 1.810, 0.156, 0.140),
           (0.508, 1.802, 0.124, 0.112)],
    JAW=[(0.238, 1.760, 0.196, 0.082),
         (0.320, 1.744, 0.176, 0.072),
         (0.400, 1.732, 0.150, 0.058),
         (0.470, 1.726, 0.110, 0.046)],
    MUZZLE=((0.216, 1.976, 0.168), (0.310, 1.940, 0.160),
            (0.404, 1.896, 0.140), (0.498, 1.842, 0.108)),
    NOSE=((0.452, 0.056, 0.022, 1.860), (0.474, 0.068, 0.028, 1.862),
          (0.494, 0.058, 0.022, 1.854)),
    MOUTH=(0.083, 0.392, 1.778, 0.200, 0.010),
    FANG_U=(Vector((0.086, 0.418, 1.784)), Vector((0.004, 0.004, -0.050)), 0.038, 0.032),
    FANG_L=(Vector((0.078, 0.400, 1.766)), Vector((0.002, 0.002, 0.045)), 0.036, 0.030),
    EYE=(0.076, 0.312, 1.916, 0.044, 0.024, 0.028),
    SOCKET=(0.074, 0.294, 1.914, 0.068, 0.038, 0.044),
    BROW=(0.092, 0.296, 1.953, 0.100, 0.056, 0.022),
    BROW_BONE=None, BROW_RIM=None,
    EAR_ROOT=Vector((0.100, 0.044, 1.955)),
    EAR_TIP=Vector((0.224, -0.102, 2.112)),
    EAR_W=(0.130, 0.148, 0.062, 0.044),
    EAR_IN=(0.068, 0.078, 0.015, 0.013),
    FINS=(("head", 0.112, 1.982, 0.020, 2.028, 0.142, 0.060),
          ("head", 0.020, 1.998, -0.110, 2.036, 0.154, 0.062),
          ("head", -0.070, 1.966, -0.196, 1.998, 0.134, 0.054),
          ("head", -0.096, 1.890, -0.212, 1.938, 0.120, 0.048),
          ("chest", -0.256, 1.792, -0.330, 1.868, 0.128, 0.042),
          ("chest", -0.292, 1.694, -0.368, 1.774, 0.118, 0.038),
          ("chest", -0.300, 1.596, -0.376, 1.674, 0.108, 0.034)),
    MANE_N=((0.0, -0.044, 1.860), (0.0, -0.252, 1.772), 0.162, 0.098),
)

GK.set_arms(S, GRIP, 0.086, (0.55, -0.55, -0.75))
S.HDIR_R = (GRIP - S.WRI_R).normalized()
S.setup()

MODULES = ("body", "head", "gear", "sword", "shield")


# ══ 盾 ══════════════════════════════════════════════════════════════════════
def _disc_y(name, c, n_axis, r, thick, n=12, dome=0.0, back=0.0):
    """朝 +Y 的圆盘（盾面）：外缘 → 中心微鼓。n_axis 是法线。"""
    c = Vector(c)
    ez = Vector(n_axis).normalized()
    up = Vector((0, 0, 1))
    ex = up.cross(ez).normalized()
    ey = ez.cross(ex).normalized()
    rows = []
    for (o, rr) in ((-thick * 0.5 - back, r * 0.80), (-thick * 0.5, r * 0.96),
                    (-thick * 0.5, r), (-thick * 0.5 + dome, r * 0.62),
                    (-thick * 0.5 + dome * 1.55, r * 0.24),
                    (thick * 0.5 - 0.004, r * 0.94), (thick * 0.5, r * 0.80)):
        rows.append([tuple(c + ez * o + ex * (rr * math.cos(math.tau * k / n))
                           + ey * (rr * math.sin(math.tau * k / n))) for k in range(n)])
    return K.loft(name, rows, True)


def shield(u):
    k = 1.0
    C = SC
    ez = SHIELD_N
    up = Vector((0, 0, 1))
    ex = up.cross(ez).normalized()
    ey = ez.cross(ex).normalized()

    # 盾面：三段木色环带 + 中心鼓
    u.add(_disc_y("sh_face", C, ez, SHIELD_R, 0.052, 14, dome=0.036, back=0.020),
          "shield_L", "皮革", "chunk", "shield", "face")
    # 铁包边
    u.add(GK.ring("sh_rim", tuple(C), tuple(ez), SHIELD_R * 0.90, SHIELD_R * 1.02,
                  0.070, 14), "shield_L", "锈铁", "chunk2", "shield", "rim")
    # 木条缝：三条横贯的暗色薄板
    for i, off in enumerate((-0.145, 0.0, 0.145)):
        a = C + ey * off - ez * 0.028
        b = C + ey * off + ez * 0.028
        u.olimb("sh_plank%d" % i, tuple(a), tuple(b),
                [(0.0, 0.020, SHIELD_R * 1.52, 0.006), (1.0, 0.020, SHIELD_R * 1.52, 0.006)],
                "shield_L", "皮革暗", "chunk", "shield", "plank")
    # 中心骨凸 + 铁钉圈
    u.add(GK.octa("sh_boss", tuple(C + ez * 0.062), 0.088, 0.046, n=8),
          "shield_L", "骨", "chunk2", "shield", "boss")
    u.add(GK.ring("sh_boss_rim", tuple(C + ez * 0.040), tuple(ez), 0.086, 0.104, 0.020, 8),
          "shield_L", "锈铁", "chunk", "shield", "boss")
    for i in range(6):
        a = math.tau * i / 6 + 0.26
        p = C + ez * 0.034 + ex * (0.196 * math.cos(a)) + ey * (0.196 * math.sin(a))
        u.rivet("sh_stud%d" % i, tuple(p), tuple(ez), "shield_L", "锈铁",
                style="hard", module="shield", tag="stud", r=0.020, h=0.014, n=6)
    # 队色一角：右上的 90° 扇面（贴在盾面上 1.5 mm）
    st = []
    for (rr, dd) in ((0.10, 0.030), (0.28, 0.030)):
        st.append((rr, 6, 46, dd))
    grid = []
    for (rr, a0, a1, dd) in st:
        row = []
        for i in range(7):
            a = math.radians(a0 + (a1 - a0) * i / 6)
            row.append(tuple(C + ez * (0.030) + ex * (rr * math.cos(a))
                             + ey * (rr * math.sin(a))))
        grid.append(row)
    u.add(K.grid_shell("sh_team", grid, 0.010, inside=tuple(C)),
          "shield_L", "team", "chunk", "shield", "paint")
    # 背面中间握把（横杆）
    u.olimb("sh_bar", tuple(C - ez * 0.082 - ex * 0.115), tuple(C - ez * 0.082 + ex * 0.115),
            [(0.0, 0.040, 0.040, 0.012), (1.0, 0.040, 0.040, 0.012)],
            "shield_L", "皮革暗", "chunk", "shield", "bar")
    for sx in (-1, 1):
        u.add(GK.ring("sh_bar_cap%d" % sx, tuple(C - ez * 0.082 + ex * (0.115 * sx)),
                      tuple(ex), 0.020, 0.032, 0.018, 6),
              "shield_L", "锈铁", "chunk", "shield", "bar")


# ══ 刀 ══════════════════════════════════════════════════════════════════════
def sword(u):
    """宽刃砍刀：握把在下（z −0.17..+0.10 相对握点），护手 + 0.72 m 刀身，骨轴 = +Y = 刀尖。"""
    gx, gy, gz = GRIP
    u.otube("sw_grip",
            [(gz - 0.170, gx, gy, 0.062, 0.062, 0.018),
             (gz - 0.140, gx, gy, 0.070, 0.070, 0.020),
             (gz + 0.020, gx, gy, 0.070, 0.070, 0.020),
             (gz + 0.060, gx, gy, 0.062, 0.062, 0.018)],
            "weapon_R", "皮革", "chunk", "sword", "grip", cw=0.018)
    for i, z in enumerate((gz - 0.110, gz - 0.010)):
        u.add(GK.ring("sw_wrap%d" % i, (gx, gy, z), (0, 0, 1), 0.036, 0.045, 0.016, 6),
              "weapon_R", "皮革暗", "chunk", "sword", "grip")
    # 配重球（骨）
    u.add(GK.octa("sw_pommel", (gx, gy, gz - 0.196), 0.052, 0.044, n=6),
          "weapon_R", "骨", "chunk2", "sword", "pommel")
    # 护手：横贯 0.28 的锈铁条 + 两端下折
    u.box("sw_guard", (gx, gy, gz + 0.086), (0.300, 0.070, 0.048),
          "weapon_R", "锈铁", style="chunk2", module="sword", tag="guard")
    for s in (1, -1):
        u.box("sw_guard_end%d" % s, (gx + s * 0.150, gy, gz + 0.058), (0.056, 0.062, 0.070),
              "weapon_R", "锈铁", style="chunk2", module="sword", tag="guard")
        u.add(GK.octa("sw_guard_stud%d" % s, (gx + s * 0.150, gy, gz + 0.104), 0.026, 0.022, n=5),
              "weapon_R", "骨", "chunk", "sword", "guard")

    # 刀身：6 段放样，根部等宽 0.132，到 62% 后收尖
    rows = []
    prof = ((0.108, 0.136, 0.030), (0.180, 0.140, 0.032), (0.330, 0.132, 0.030),
            (0.480, 0.124, 0.027), (0.600, 0.112, 0.023), (0.700, 0.086, 0.018),
            (0.752, 0.020, 0.008))
    for (t, w, d) in prof:
        rows.append([(gx + x, gy + y, gz + t) for (x, y) in K.octs(w, d, 0.026, 0.010)])
    u.add(K.loft("sw_blade", rows), "weapon_R", "刃", "facet", "sword", "blade")
    # 血槽：两面各一条锈铁细线（刀身太薄，用 1.5 mm 的薄片压出一条暗线）
    for sy in (1, -1):
        u.box("sw_full%d" % sy, (gx, gy + sy * 0.013, gz + 0.400),
              (0.046, 0.006, 0.520), "weapon_R", "锈铁",
              style="chunk", module="sword", tag="fuller")
    # 刀尖加强脊
    u.add(KU.claw("sw_tip", (gx, gy, gz + 0.720), (gx, gy + 0.004, gz + 0.812),
                  0.070, 0.030), "weapon_R", "刃", "facet", "sword", "blade")


# ══ 装备 ════════════════════════════════════════════════════════════════════
def gear(u):
    # 右肩：三层锈铁甲 + 两根骨刺（与萨满的左肩骨甲镜像，语言换成铁）
    sh = S.SH
    el = S.ELB_R
    d = (el - sh).normalized()
    out = Vector((0.93, -0.26, 0.26)).normalized()
    bone = "shoulder_R"
    plates = ((-0.020, 0.078, 0.112, 0.150, 0.168),
              (0.070, 0.152, 0.156, 0.184, 0.124),
              (0.158, 0.240, 0.184, 0.202, 0.088))
    for i, (t0, t1, r0, r1, sl) in enumerate(plates):
        u.add(K.arc_band("gr_pauldron%d" % i, tuple(sh + d * t0), tuple(sh + d * t1),
                         r0, r1, -62, 62, 1, 5, 0.034, tuple(out), 0.008),
              bone, "锈铁", "chunk2", "gear", "pauldron")
        base = sh + d * (t1 - 0.014) + out * (r1 * 0.88)
        tip = base + (out * 0.70 + d * 0.60).normalized() * sl
        u.add(KU.claw("gr_spike%d" % i, tuple(base), tuple(tip), 0.052, 0.042),
              bone, "骨", "chunk2", "gear", "spike")
    u.add(GK.disc("gr_cap", tuple(sh + d * 0.002), tuple(-d), 0.074, 0.028, 8),
          bone, "锈铁", "chunk2", "gear", "pauldron")
    u.add(GK.ring("gr_cap_rim", tuple(sh + d * 0.008), tuple(-d), 0.074, 0.092, 0.018, 8),
          bone, "team_trim", "chunk", "gear", "pauldron")

    # 左肩：一条过肩皮带 + 上臂 team 布环（萨满是骨甲，这里刻意留空不对称）
    shl = S.SH_L
    u.olimb("gr_baldric", tuple(Vector((-0.150, -0.230, 1.760))),
            tuple(Vector((-0.316, 0.246, 1.500))),
            [(0.00, 0.086, 0.030, 0.014), (1.00, 0.086, 0.030, 0.014)],
            "chest", "皮革", "chunk", "gear", "harness")
    elb = S.ELB_L
    dvec = (elb - shl).normalized()
    for i, (t0, t1, mat) in enumerate(((0.16, 0.34, "team"), (0.34, 0.40, "team_trim"))):
        u.add(K.arc_band("gr_armband%d" % i, tuple(shl + dvec * t0), tuple(shl + dvec * t1),
                         0.090, 0.086, -104, 104, 1, 6, 0.018, (-0.86, -0.10, 0.10)),
              "upperarm_L", mat, "chunk", "gear", "armband")

    # 胸前 X 形皮带 + 骨扣
    A = Vector((-0.268, 0.284, 1.640))
    B = Vector((0.052, 0.372, 1.392))
    Cc = Vector((0.276, 0.266, 1.198))
    for tag, p0, p1 in (("a", A, B), ("b", B, Cc), ("c", B, Cc + Vector((0, -0.06, 0.28)))):
        u.olimb("gr_harness_" + tag, tuple(p0), tuple(p1),
                [(0.00, 0.080, 0.026, 0.014), (1.00, 0.080, 0.026, 0.014)],
                "chest", "皮革", "chunk", "gear", "harness")
    u.add(GK.ring("gr_harness_ring", tuple(B + Vector((0, 0.020, 0.0))), (0, 1, 0),
                  0.024, 0.040, 0.016, 6), "chest", "锈铁", "chunk", "gear", "harness")
    u.add(KU.claw("gr_pendant", tuple(B + Vector((0, 0.030, -0.020))),
                  tuple(B + Vector((0.004, 0.026, -0.116))), 0.056, 0.040),
          "chest", "骨", "chunk", "gear", "harness")

    # 头箍：皮革环 + 三枚铁钉（萨满是骨额板，这里是箍）
    u.add(K.arc_panel("gr_headband",
                      [(1.906, -180, 180, 0.148, 0.152, 0.020),
                       (1.944, -180, 180, 0.150, 0.154, 0.018),
                       (1.972, -180, 180, 0.140, 0.144, 0.014)],
                      0.026, 12, None, (0.0, 0.020)),
          "head", "皮革", "chunk", "gear", "headband")
    for i, a in enumerate((20, 90, 160)):
        p = Vector((0.150 * math.sin(math.radians(a)),
                    0.020 + 0.154 * math.cos(math.radians(a)), 1.944))
        n = Vector((math.sin(math.radians(a)), math.cos(math.radians(a)), 0.10))
        u.rivet("gr_bandstud%d" % i, tuple(p), tuple(n), "head", "锈铁",
                style="hard", module="gear", tag="headband", r=0.018, h=0.012, n=6)

    # 左耳缺口：一块皮革包住断口（左耳尖被削掉，接一小段皮革套）
    e0 = Vector((-S.EAR_ROOT.x, S.EAR_ROOT.y, S.EAR_ROOT.z))
    e1 = Vector((-S.EAR_TIP.x, S.EAR_TIP.y, S.EAR_TIP.z))
    dvec = (e1 - e0)
    u.olimb("gr_ear_wrap", tuple(e0 + dvec * 0.62), tuple(e0 + dvec * 0.80),
            [(0.0, 0.070, 0.052, 0.014), (1.0, 0.062, 0.046, 0.012)],
            "head", "皮革", "chunk", "gear", "earwrap")

    # 护胫：两片铁 + 膝钉
    for s in (1, -1):
        side = S.side(s)
        kn, hc = S.kne(s), S.hck(s)
        u.add(K.arc_band("gr_shin%d" % s, tuple(kn + (hc - kn) * 0.16),
                         tuple(kn + (hc - kn) * 0.62), 0.108, 0.098, -62, 62, 2, 5, 0.026,
                         (s * 0.86, -0.34, 0.38)),
              "shin_" + side, "锈铁", "chunk2", "gear", "shingua")
        u.rivet("gr_knee%d" % s, tuple(kn + Vector((s * 0.086, -0.010, 0.010))),
                (s, -0.2, 0.3), "thigh_" + side, "锈铁",
                style="hard", module="gear", tag="shingua", r=0.024, h=0.016, n=6)



# ══ 组装 ════════════════════════════════════════════════════════════════════
def build(low=False, modules=None):
    want = set(MODULES if modules is None else modules)
    u = K.Unit2(PREFIX, MATS, low=low)
    if "body" in want:
        GK.legs(u, S)
        GK.pelvis(u, S, kilt=True, kilt_z=0.905, kilt_mat="皮革")
        GK.torso(u, S, straps=False, paint=(-0.060, -0.028, 0.004))
        GK.neck(u, S)
        GK.arms(u, S)
        GK.fist_around(u, S, "R", GRIP, (0, 0, 1), (1, 0, 0), r=0.050, k=1.10,
                       cuff=True, tag="palm")
        GK.fist_around(u, S, "L", SC - SHIELD_N * 0.082, (1, 0, 0), (0, 1, 0),
                       r=0.040, k=1.06, cuff=True, tag="palm")
        GK.tail(u, S)
    if "head" in want:
        GK.head(u, S)
    if "gear" in want:
        gear(u)
    if "sword" in want:
        sword(u)
    if "shield" in want:
        shield(u)
    return u


def build_rig(name="RIG_" + NAME):
    extra = [
        ("weapon_R", tuple(GRIP), tuple(GRIP + Vector((0, 0, 0.30))), "hand_R"),
        ("shield_L", tuple(SC), tuple(SC + SHIELD_N * 0.16), "hand_L"),
    ]
    return K.build_rig(GK.bones(S, extra=extra), name)


def report():
    return "\n".join([
        "[joints] hip=%.3f knee=(%.3f,%.3f) hock=(%.3f,%.3f) ball=%.3f top=%.3f"
        % (S.Z_HIP, S.KNE.y, S.KNE.z, S.HCK.y, S.HCK.z, S.BAL.z, S.Z_TOP),
        "[leg] thigh=%.3f shin=%.3f foot=%.3f toe=%.3f"
        % (S.L_THIGH, S.L_SHIN, S.L_FOOT, S.L_TOE),
        "[arm] upper=%.3f fore=%.3f reach=%.3f/%.3f"
        % (S.L_UPPER, S.L_FORE, (S.WRI_R - S.SH).length, S.L_UPPER + S.L_FORE),
        "[grip] (%.3f,%.3f,%.3f) shield r=%.3f" % (GRIP.x, GRIP.y, GRIP.z, SHIELD_R),
    ])
