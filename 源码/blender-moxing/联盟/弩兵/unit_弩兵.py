"""unit_弩兵.py —— 联盟弩兵

**出货走 `load()`**：导入出厂 glb（4,508 面 / 24 骨），只做 `fix_grip_clearance()` 的
两处顶点平移（手 -26 mm、弩 +55 mm），不重建网格。`build()` 是早期的源码重建实验
（7,206 / 8,966 面），只在 `run_弩兵_源码重建.py` 里用，出货不用。

识别点（RTS 40° 俯角，96px 高仍可指认）：
  ① 头颈：**宽檐铁盔**（kettle hat）+ 蓝色帽箍 + 后颈小羽；
  ② 躯干：**蓝底金冠胸兜**（与建筑旗帜同一枚徽记）+ 左肩三层甲片；
  ③ 下肢/武器：**双手端持的重弩**（横向弩臂 + 前踏环 + 上膛矢）+ 背后三支蓝羽弩矢。

修的是 v1 的三个问题：
  * 左手是 0.20 m 的大方块，绕腕骨转 → 走路上像"圆球绕弩旋转"。
    现在手改成 0.08 的握拳，并且走动作里腕骨旋转锁死；
  * 弩是一块薄木板，没有弩臂/弦/踏环/矢；
  * 阵营色只有一块胸兜，现在分低（腰带）/中（胸兜 + 弩身箍）/高（盔箍 + 羽）三带。
"""
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = HERE
while not os.path.isdir(os.path.join(ROOT, "库")):
    _up = os.path.dirname(ROOT)
    if _up == ROOT:
        break
    ROOT = _up
LIB = os.path.join(ROOT, "库")
if LIB not in sys.path:
    sys.path.insert(0, LIB)

import unitkit as K  # noqa: E402

NAME = "方块人_弩兵"
SRC = os.path.join(LIB, "_ref", "联盟", "方块人_弩兵.glb")

# ── 骨架关键点（从原 glb 直读，重建时不动骨架）─────────────────────────────
HIP_Z = 0.6793
CHEST_Z = 0.9982
HEAD_Z = 1.2404
LEG_X = 0.1229
SHOULDER = {"R": (0.2304, 0.0, 1.1518), "L": (-0.2304, 0.0, 1.1518)}
ELBOW = {"R": (0.2654, 0.1502, 0.9253), "L": (-0.1645, 0.2445, 1.0469)}
WRIST = {"R": (0.0780, 0.2726, 1.0619), "L": (0.0288, 0.4200, 1.0706)}
WEAPON_H = Vector((0.0473, 0.3627, 1.1028))
WEAPON_T = Vector((0.0146, 0.4607, 1.1085))
BOLT_H = Vector((0.0165, 0.4527, 1.1436))


def _bone(side, stem):
    return stem + "_" + side


# ── 弩的局部坐标系：fwd 沿弩轴、sv 侧向、up 向上（与 crossbow() 里的 P() 同一套）──
AX = (WEAPON_T - WEAPON_H).normalized()
SV = Vector((0, 0, 1)).cross(AX).normalized()
UP = AX.cross(SV)

# 握点（fwd/sv/up，单位 m）。数字来自 库/_probe_cb_bvh.py 打印的真实截面：
#   右手 fwd −0.116：弩身半宽 0.028 / 下半高 0.035，头顶 0.028 起是弩矢尾羽；
#   左手 fwd  0.088：弩身箍半宽 0.034 / 半高 0.043，弦在 sv ±0.061 之外。
GRIP = {
    "R": dict(f=(-0.138, -0.092), cav=0.033, outer=0.055,
              bot=-0.072, palm=-0.040, top=0.022, kn=(0.0, 1.0), kn_out=0.006),
    "L": dict(f=(0.066, 0.112), cav=0.038, outer=0.053,
              bot=-0.079, palm=-0.047, top=0.047, kn=(0.26, 0.96), kn_out=0.006),
}


def cb_pt(sx, fwd, upp):
    """弩局部坐标 → 世界坐标（几何只在静止姿态建一次）。"""
    return WEAPON_H + SV * sx + AX * fwd + UP * upp


def _cb_box(u, name, bone, mat, s0, s1, f0, f1, u0, u1, bevel=0.005):
    """在弩局部系里放一个方盒（world 轴对齐的 box() 做不到，用两排 loft）。"""
    rows = [[cb_pt(s0, f0, u0), cb_pt(s1, f0, u0), cb_pt(s1, f1, u0), cb_pt(s0, f1, u0)],
            [cb_pt(s0, f0, u1), cb_pt(s1, f0, u1), cb_pt(s1, f1, u1), cb_pt(s0, f1, u1)]]
    return u.add(K.loft(name, rows), bone, mat, bevel, 1, 0, False)


def weapon_floor_rot(rest_R, axdir=(0.34, 0.94, 0.0), upw=(0.0, 0.0, 1.0)):
    """弩躺在地上时 `weapon` 骨的世界朝向：弩轴水平、截面朝上（前踏环才不会插进地里）。

    G = 弩网格在静止姿态下的世界朝向（列 = ax / sv / up）；先把 G 换成"骨局部"里的
    朝向，再乘到目标世界朝向上 —— 这样换任何骨都口径一致。
    """
    A_ = AX
    G_rest = Matrix(((A_.x, SV.x, UP.x), (A_.y, SV.y, UP.y), (A_.z, SV.z, UP.z)))
    G_bone = rest_R.inverted() @ G_rest
    a = Vector(axdir).normalized()
    u = Vector(upw)
    u = (u - a * u.dot(a)).normalized()
    s = u.cross(a)
    G_t = Matrix(((a.x, s.x, u.x), (a.y, s.y, u.y), (a.z, s.z, u.z)))
    return G_t @ G_bone.inverted()


# 弩躺平后，最低点（前踏环横杆 up = −0.120）到骨 head 的落差
FLOOR_DZ = 0.120


def crown(u, cx, cz, ch, y, bone, mat_gold="team_trim", mat_gem="iron"):
    """三尖金冠（与建筑旗帜同一枚）：冠带 + 三尖 + 三方宝石。"""
    w = ch * 0.65
    u.plate("cr_band", [(cx - w, cz), (cx + w, cz), (cx + w, cz + ch * 0.21),
                        (cx - w, cz + ch * 0.21)], bone, mat_gold,
            axis="Y", thickness=0.010, offset=y, bevel=0.002, smooth=False)
    for i, (a, b, top) in enumerate(((-0.94, -0.24, 0.74), (-0.20, 0.20, 1.00),
                                     (0.24, 0.94, 0.74))):
        u.plate("cr_sp%d" % i,
                [(cx + a * w, cz + ch * 0.19), (cx + b * w, cz + ch * 0.19),
                 (cx + (a + b) * 0.5 * w, cz + ch * top)],
                bone, mat_gold, axis="Y", thickness=0.011, offset=y + 0.001,
                bevel=0.002, smooth=False)
    for i, uu in enumerate((-0.56, 0.0, 0.56)):
        g = ch * 0.058
        u.plate("cr_gem%d" % i,
                [(cx + uu * w - g, cz + ch * 0.045), (cx + uu * w + g, cz + ch * 0.045),
                 (cx + uu * w + g, cz + ch * 0.155), (cx + uu * w - g, cz + ch * 0.155)],
                bone, mat_gem, axis="Y", thickness=0.012, offset=y + 0.003,
                bevel=0.0015, smooth=False)


def tabard(u):
    """胸兜：蓝底 + 金边 + 金冠（与建筑垂旗同一套语言）。

    v2.1：下摆压到 z=0.72，从弩身下方露出来 —— 否则正面全被弩和手臂挡住，
    俯视时读不到阵营色。金冠落在腰带高度，正好当"带扣"。
    """
    prof = [(-0.075, 0.848), (0.0, 0.804), (0.075, 0.848),
            (0.075, 1.102), (0.0, 1.136), (-0.075, 1.102)]
    prof_g = [(-0.082, 0.842), (0.0, 0.794), (0.082, 0.842),
              (0.082, 1.108), (0.0, 1.144), (-0.082, 1.108)]
    u.plate("tb_edge", prof_g, "spine", "team_trim", axis="Y", thickness=0.012,
            offset=0.176, bevel=0.003, seg=1, smooth=False)
    u.plate("tb_field", prof, "spine", "team", axis="Y", thickness=0.022,
            offset=0.188, bevel=0.004, seg=1, smooth=False)
    crown(u, 0.0, 0.860, 0.062, 0.201, "spine")
    # 背面同一条垂布（背面朝 -Y，所以徽记画在 -0.19 一侧）
    prof_b = [(-0.074, 0.888), (0.0, 0.848), (0.074, 0.888),
              (0.074, 1.094), (0.0, 1.128), (-0.074, 1.094)]
    prof_bg = [(-0.081, 0.882), (0.0, 0.838), (0.081, 0.882),
               (0.081, 1.100), (0.0, 1.136), (-0.081, 1.100)]
    u.plate("tbB_edge", prof_bg, "spine", "team_trim", axis="Y", thickness=0.010,
            offset=-0.176, bevel=0.003, seg=1, smooth=False)
    u.plate("tbB_field", prof_b, "spine", "team", axis="Y", thickness=0.020,
            offset=-0.192, bevel=0.004, seg=1, smooth=False)
    crown(u, 0.0, 0.920, 0.056, -0.199, "spine")


def legs(u, detail=1):
    for s, side in ((1, "R"), (-1, "L")):
        x = s * LEG_X
        foot, shin, thigh = _bone(side, "foot"), _bone(side, "shin"), _bone(side, "thigh")
        # 靴
        u.box("sole_" + side, (x, 0.075, 0.022), (0.205, 0.355, 0.044), foot, "earth_dark", bevel=0.006)
        u.tube("boot_" + side, [(0.040, x, 0.045, 0.196, 0.306, 0.030),
                                (0.120, x, 0.030, 0.186, 0.278, 0.030),
                                (0.185, x, 0.014, 0.172, 0.232, 0.028)],
               foot, "leather_dark", bevel=0.010, sub=0, smooth=True, n=4)
        u.box("toe_" + side, (x, 0.205, 0.060), (0.174, 0.130, 0.070), foot, "steel_dark", bevel=0.008)
        u.box("boot_cuff_" + side, (x, 0.010, 0.198), (0.188, 0.248, 0.036), foot, "leather", bevel=0.005)
        if detail:
            for i, yy in enumerate((0.045, -0.055)):
                u.box("boot_strap_%s%d" % (side, i), (x, yy, 0.210), (0.194, 0.028, 0.024),
                      foot, "dark", bevel=0.002)
        # 踝缝
        u.tube("ankle_" + side, [(0.196, x, 0.010, 0.112, 0.118, 0.020),
                                 (0.222, x, 0.008, 0.114, 0.120, 0.020)],
               shin, "cloth_dark", bevel=0.004, smooth=False, n=4)
        # 小腿
        u.limb("shin_" + side, (x, 0.006, 0.215), (x, 0.004, 0.445), 0.086, 0.094,
               shin, "cloth", sides=6, sub=1, key="cloth")
        u.box("greave_" + side, (x, 0.072, 0.335), (0.150, 0.055, 0.200), shin, "steel_dark",
              bevel=0.010, seg=2)
        u.box("greave_rib_" + side, (x, 0.099, 0.335), (0.036, 0.020, 0.190), shin, "steel_light",
              bevel=0.004)
        # 膝
        u.box("poleyn_" + side, (x, 0.060, 0.462), (0.152, 0.120, 0.086), shin, "steel",
              bevel=0.012, seg=2)
        u.box("knee_gap_" + side, (x, 0.004, 0.458), (0.138, 0.146, 0.050), thigh, "cloth_dark",
              bevel=0.004, smooth=False)
        # 大腿
        u.limb("thigh_" + side, (x, 0.002, 0.470), (x, 0.0, 0.700), 0.104, 0.110,
               thigh, "cloth", sides=6, sub=1, key="cloth_dark")
        u.box("cuisse_" + side, (x, 0.072, 0.600), (0.158, 0.062, 0.160), thigh, "steel_dark",
              bevel=0.008, seg=2)
        if detail:
            # 裙甲三片（贴着胯部圆弧）
            for i, (ang, w, h) in enumerate(((10, 0.090, 0.150), (46, 0.086, 0.140), (82, 0.078, 0.122))):
                a = math.radians(ang)
                px, py = s * 0.176 * math.sin(a), 0.176 * math.cos(a)
                u.box("tasset_%s%d" % (side, i), (px, py, 0.742), (w, 0.026, h),
                      "hips", "steel_dark", bevel=0.006, rot=(math.radians(-6), 0, -s * a))


def hips(u, detail=1):
    u.tube("pelvis", [(0.630, 0, 0.0, 0.330, 0.268, 0.050),
                      (0.730, 0, 0.0, 0.356, 0.286, 0.054),
                      (0.812, 0, 0.0, 0.344, 0.276, 0.052)],
           "hips", "cloth_dark", bevel=0.0, sub=1, key="cloth_dark", n=6)
    u.tube("belt", [(0.800, 0, 0.0, 0.368, 0.294, 0.052),
                    (0.872, 0, 0.0, 0.364, 0.290, 0.052)],
           "hips", "team", bevel=0.006, smooth=False, n=6)
    # 带扣让位给胸兜上的金冠
    if detail:
        u.box("pouch", (0.182, 0.006, 0.748), (0.104, 0.090, 0.112), "hips", "leather",
              bevel=0.010, rot=(0, math.radians(8), 0))



def torso(u, detail=1):
    u.tube("abdomen", [(0.850, 0, 0.0, 0.302, 0.250, 0.046),
                       (0.940, 0, 0.004, 0.326, 0.266, 0.050),
                       (1.005, 0, 0.006, 0.344, 0.276, 0.052)],
           "spine", "cloth", bevel=0.0, sub=1, key="cloth", n=6)
    # 胸甲：上宽下窄，正面一道中脊
    rows = []
    for (z, w, d, ridge) in ((0.995, 0.350, 0.278, 0.006),
                             (1.080, 0.404, 0.304, 0.018),
                             (1.160, 0.428, 0.318, 0.014),
                             (1.212, 0.360, 0.276, 0.006)):
        hw, hd = w * 0.5, d * 0.5
        sec = [(-hw * 0.9, -hd), (hw * 0.9, -hd), (hw, -hd * 0.42),
               (hw, hd * 0.66), (hw * 0.62, hd), (0.0, hd + ridge),
               (-hw * 0.62, hd), (-hw, hd * 0.66), (-hw, -hd * 0.42)]
        rows.append([(x, y - 0.004, z) for (x, y) in sec])
    u.loft("chest", rows, "chest", "steel", bevel=0.010, seg=2, sub=0, smooth=False)
    # 下缘 V 甲
    u.plate("plackart", [(-0.132, 1.010), (0.132, 1.010), (0.116, 0.940),
                         (0.0, 0.892), (-0.116, 0.940)],
            "chest", "steel_dark", axis="Y", thickness=0.028, offset=0.128,
            bevel=0.005, smooth=False)
    u.tube("gorget", [(1.196, 0, 0.0, 0.236, 0.214, 0.050),
                      (1.244, 0, 0.0, 0.206, 0.190, 0.044)],
           "chest", "steel_dark", bevel=0.006, smooth=False, n=6)
    u.box("collar", (0, 0.0, 1.248), (0.168, 0.162, 0.060), "neck", "cloth_dark", bevel=0.008)
    # 两侧皮衬：把整块钢胸甲"垫"起来，俯视时侧面不是一条灰边
    for s in (1, -1):
        u.box("jerkin_%d" % s, (s * 0.202, 0.000, 1.062), (0.046, 0.288, 0.208),
              "chest", "leather", bevel=0.008)
    if detail:
        # 双肩皮带 + 金扣（在弩身上方，正面可见）
        for s in (1, -1):
            u.box("chest_strap_%d" % s, (s * 0.074, 0.166, 1.152), (0.044, 0.028, 0.180),
                  "chest", "leather_dark", rot=(0, s * math.radians(20), 0), bevel=0.004)
            u.box("chest_stud_%d" % s, (s * 0.036, 0.180, 1.096), (0.040, 0.018, 0.030),
                  "chest", "team_trim", bevel=0.002)
        # 铆钉
        for s in (1, -1):
            for (zz, xx) in ((1.035, 0.170), (1.135, 0.185)):
                u.box("rivet_%d_%d" % (s, int(zz * 100)), (s * xx, 0.020, zz),
                      (0.022, 0.022, 0.022), "chest", "team_trim", bevel=0.002)


def arms(u, detail=1):
    for s, side in ((1, "R"), (-1, "L")):
        ua, fa, hd = _bone(side, "upperarm"), _bone(side, "forearm"), _bone(side, "hand")
        sh, el, wr = Vector(SHOULDER[side]), Vector(ELBOW[side]), Vector(WRIST[side])
        # 肩缝（暗衬）
        u.limb("shoulder_gap_" + side, sh + Vector((0, 0, 0.030)), sh + Vector((0, 0, -0.030)),
               0.070, 0.072, "clavicle_" + side if False else _bone(side, "shoulder"),
               "cloth_dark", sides=6, sub=0, bevel=0.0)
        # 上臂
        u.limb("upperarm_" + side, sh, el, 0.080, 0.066, ua, "cloth", sides=6, sub=1, key="leather_dark")
        u.limb("sleeve_" + side, sh.lerp(el, 0.10), sh.lerp(el, 0.30), 0.088, 0.082,
               ua, "leather", sides=6, sub=0)
        # 肘
        u.box("elbow_" + side, el, (0.108, 0.108, 0.090), fa, "steel_dark", bevel=0.008)
        # 前臂护臂
        u.limb("bracer_" + side, el, wr, 0.064, 0.054, fa, "steel", sides=6, sub=1, key="steel_dark")
        u.limb("cuff_" + side, wr - (wr - el).normalized() * 0.030, wr + (wr - el).normalized() * 0.012,
               0.062, 0.058, fa, "steel_dark", sides=6, sub=0)
        # 手：握拳（小、贴着弩身，不能像 v1 那样是个 0.2 m 的大方块）
        build_fist(u, side, hd, detail)


def build_fist(u, side, bone, detail=1):
    """握拳 v3：把"包住弩身的实心方块"改成**三块夹钳**，任何面片都不与弩互穿。

    v2 的病根：拳块是以腕点为中心的 0.086×0.098×0.120 实心方块，弩身直接从
    方块正中穿过去（BVH 实测 259 对面片相交，最深 14.1 mm）。

    v3 的做法（数据全部来自 `库/_probe_cb_bvh.py` 的实测截面）：
      * **掌心**：一块垫在弩身下方的板，上表面压到弩身外表面 +4 mm；
      * **手背 / 手指**：两块竖板夹在弩身两侧，内表面离弩身 +4.5 mm；
      * 三块的内腔把弩身"含"住，留 4~5 mm 空气，**零面片相交**。
    两只手的握点按实测各自挪了 1~3 cm：
      * 右手后移 1.8 cm —— 原来压在扳机护圈上（护圈在 fwd −0.077…+0.029）；
      * 左手中段前移 3.1 cm —— 弩弦在 fwd 0.043 以后就出了弩身表面，
        原握点上弦正好从拳块中间穿过（sv ±0.055）；前移后弦在 sv ±0.065 之外。
    """
    g = GRIP[side]
    f0, f1 = g["f"]
    cav, outer = g["cav"], g["outer"]          # 内腔半宽 / 外侧半宽
    bot, palm, top = g["bot"], g["palm"], g["top"]

    # 掌心（底面）：内表面 = 弩身下表面 +2 mm
    _cb_box(u, "palm_" + side, bone, "leather", -outer, outer, f0, f1, bot, palm)
    # 手背（+sv 侧，RTS 机位看得见的那面）
    _cb_box(u, "handback_" + side, bone, "leather", cav, outer, f0, f1, bot, top)
    # 手指（−sv 侧，绕到弩身另一边）
    _cb_box(u, "fingers_" + side, bone, "leather_dark", -outer, -cav, f0, f1, bot, top)
    if detail:
        # 四指节：只做在握点前端一段（左手后端要让开弩弦），且只往 +sv **外侧**凸
        k0, k1 = g["kn"]
        a0, a1 = f0 + (f1 - f0) * k0, f0 + (f1 - f0) * k1
        n = 4
        for i in range(n):
            a = a0 + (a1 - a0) * (i + 0.5) / n
            hw = (a1 - a0) / n * 0.30
            _cb_box(u, "knuckle_%s%d" % (side, i), bone, "leather_dark",
                    outer - 0.002, outer + g["kn_out"], a - hw, a + hw,
                    palm + 0.006, top - 0.006, bevel=0.002)
        # 拇指：压在手指上（只往 −sv **外侧**凸，不碰弩）
        _cb_box(u, "thumb_" + side, bone, "skin",
                -outer - 0.013, -outer + 0.002, f1 - 0.018, f1,
                palm + 0.010, top - 0.004, bevel=0.003)


def pauldrons(u, detail=1):
    """三层弧片：从肩顶往下逐层外倾、逐层变小，像龙虾甲。"""
    for s, side in ((1, "R"), (-1, "L")):
        ua = _bone(side, "upperarm")
        for i, (cx, cz, w, d, h, tilt, mat) in enumerate((
                (0.232, 1.200, 0.152, 0.206, 0.058, 37, "steel"),
                (0.262, 1.154, 0.158, 0.196, 0.050, 52, "steel_dark"),
                (0.286, 1.106, 0.140, 0.178, 0.044, 64, "steel"))):
            u.box("pauldron_%s%d" % (side, i), (s * cx, -0.004, cz), (w, d, h),
                  ua, mat, bevel=0.009, seg=1, rot=(0, s * math.radians(tilt), 0))
        if detail:
            u.box("pauldron_rivet_" + side, (s * 0.238, 0.080, 1.224), (0.022, 0.022, 0.022),
                  ua, "team_trim", bevel=0.002)
            # 肩下皮垫，遮住甲片与上臂的缝



def head(u, detail=1):
    # 颈 / 锁子头巾：把"光头 + 铁锅"变成"戴盔的兵"
    u.tube("neck", [(1.168, 0, 0.006, 0.148, 0.144, 0.034),
                    (1.268, 0, 0.008, 0.156, 0.150, 0.036)],
           "neck", "cloth_dark", bevel=0.006, sub=0, smooth=False, n=6)
    for s in (1, -1):
        u.box("coif_%d" % s, (s * 0.106, 0.010, 1.362), (0.040, 0.216, 0.204),
              "head", "cloth_dark", bevel=0.006)
    u.box("coif_back", (0, -0.098, 1.366), (0.228, 0.042, 0.214), "head", "cloth_dark", bevel=0.006)
    # 头骨 / 脸
    u.tube("skull", [(1.262, 0, 0.012, 0.214, 0.212, 0.0),
                     (1.370, 0, 0.012, 0.222, 0.218, 0.0),
                     (1.486, 0, 0.006, 0.218, 0.212, 0.0)],
           "head", "skin", bevel=0.0, sub=1, key="skin", n=6)
    u.box("face", (0, 0.122, 1.378), (0.176, 0.050, 0.168), "head", "skin", bevel=0.008)
    u.box("jaw", (0, 0.126, 1.304), (0.152, 0.048, 0.058), "head", "skin_dark", bevel=0.007)
    for s in (1, -1):
        u.box("eye_%d" % s, (s * 0.040, 0.150, 1.400), (0.036, 0.010, 0.020), "head", "dark", bevel=0.001)
        u.box("brow_%d" % s, (s * 0.043, 0.152, 1.422), (0.044, 0.010, 0.012), "head", "hair", bevel=0.001)
    u.box("nose", (0, 0.158, 1.362), (0.038, 0.026, 0.050), "head", "skin_dark", bevel=0.004)
    u.box("mouth", (0, 0.162, 1.322), (0.056, 0.010, 0.010), "head", "dark", bevel=0.001)
    u.box("chin_strap", (0, 0.120, 1.292), (0.180, 0.024, 0.018), "head", "leather_dark", bevel=0.002)
    # 宽檐盔
    u.box("helm_brim_lo", (0, 0.008, 1.486), (0.306, 0.270, 0.020), "head", "steel_dark",
          bevel=0.007, seg=1)
    u.box("helm_brim_hi", (0, 0.008, 1.503), (0.282, 0.246, 0.018), "head", "steel",
          bevel=0.006, seg=1)
    u.tube("helm_dome", [(1.507, 0, 0.010, 0.264, 0.246, 0.0),
                         (1.550, 0, 0.010, 0.260, 0.242, 0.0),
                         (1.596, 0, 0.010, 0.214, 0.200, 0.0),
                         (1.646, 0, 0.010, 0.050, 0.046, 0.0)],
           "head", "steel", bevel=0.0, sub=1, key="steel", n=6, smooth=False)
    u.tube("helm_band", [(1.528, 0, 0.010, 0.276, 0.258, 0.0),
                         (1.552, 0, 0.010, 0.272, 0.254, 0.0)],
           "head", "team", bevel=0.004, smooth=False, n=6)
    u.tube("helm_knob", [(1.644, 0, 0.010, 0.072, 0.066, 0.0),
                         (1.668, 0, 0.010, 0.046, 0.042, 0.0)],
           "head", "steel_dark", bevel=0.003, smooth=False, n=6)
    # 鼻梁护条 + 护颊
    u.box("nasal", (0, 0.150, 1.436), (0.024, 0.022, 0.082), "head", "steel_dark", bevel=0.003)
    for s in (1, -1):
        u.box("cheek_%d" % s, (s * 0.112, 0.068, 1.400), (0.026, 0.094, 0.102),
              "head", "steel_dark", bevel=0.005)
    # 后颈队色小羽（高带）
    u.plate("plume", [(-0.030, 1.552), (0.030, 1.552), (0.020, 1.662), (-0.010, 1.690)],
            "head", "team", axis="Y", thickness=0.016, offset=-0.152,
            bevel=0.002, smooth=False)
    u.box("plume_tip", (0, -0.160, 1.684), (0.030, 0.020, 0.024), "head", "team_trim", bevel=0.002)


def quiver(u, detail=1):
    """右胯的弩矢匣：三支短矢 + 蓝羽，挂在腰带上。
    不放到背后 —— 背后是垂布，箭袋会被布挡成"浮在空中的三根蓝签"。"""
    qx, qy, qz = 0.206, -0.040, 0.812
    tilt = (0.0, math.radians(8), math.radians(-16))
    u.box("quiver_body", (qx, qy, qz), (0.088, 0.096, 0.210), "hips", "leather",
          bevel=0.010, rot=tilt)
    u.box("quiver_band", (qx, qy, qz + 0.060), (0.100, 0.108, 0.028), "hips", "leather_dark",
          bevel=0.004, rot=tilt)
    u.box("quiver_cap", (qx, qy, qz + 0.102), (0.096, 0.104, 0.018), "hips", "earth_dark",
          bevel=0.004, rot=tilt)
    if detail:
        for i, (dx, dy) in enumerate(((-0.024, 0.010), (0.0, -0.014), (0.024, 0.008))):
            bx, by = qx + dx, qy + dy
            u.box("bolt_shaft_%d" % i, (bx, by, qz + 0.165), (0.011, 0.011, 0.150),
                  "hips", "wood", bevel=0.001, rot=tilt)
            u.box("bolt_fletch_%d" % i, (bx, by, qz + 0.232), (0.034, 0.012, 0.058),
                  "hips", "team", bevel=0.002, rot=tilt)
            u.box("bolt_fletch2_%d" % i, (bx, by, qz + 0.232), (0.012, 0.034, 0.058),
                  "hips", "team", bevel=0.002, rot=tilt)


def crossbow(u, detail=1):
    """重弩：沿 weapon 骨轴。弩臂是**扁刀片**（俯视宽、正面薄），
    前踏环、上膛矢、蓝箍金线；矢尖伸出弩身 0.13 m，正面能看到一个亮点。"""
    h, t = WEAPON_H, WEAPON_T
    ax = (t - h).normalized()
    sv = Vector((0, 0, 1)).cross(ax).normalized()
    up = ax.cross(sv)

    def P(sx, fwd, upp=0.0):
        return h + sv * sx + ax * fwd + up * upp

    # 弩身
    secs = []
    for (fwd, w, hh) in ((-0.140, 0.052, 0.060), (-0.080, 0.058, 0.074),
                         (0.000, 0.062, 0.078), (0.100, 0.056, 0.072),
                         (0.200, 0.050, 0.064), (0.255, 0.046, 0.056)):
        secs.append([P(-w * 0.5, fwd, -hh * 0.5), P(w * 0.5, fwd, -hh * 0.5),
                     P(w * 0.5, fwd, hh * 0.5), P(-w * 0.5, fwd, hh * 0.5)])
    u.add(K.loft("cb_stock", secs), "weapon", "主体", 0.007, 1, 0, False, key="wood")
    # 中段蓝箍 + 金线
    for nm, f0, f1, w, hh, mat, bev in (
            ("cb_band", 0.030, 0.090, 0.068, 0.086, "team", 0.003),
            ("cb_band_gold", 0.094, 0.104, 0.066, 0.084, "team_trim", 0.002)):
        rows = []
        for fwd in (f0, f1):
            rows.append([P(-w * 0.5, fwd, -hh * 0.5), P(w * 0.5, fwd, -hh * 0.5),
                         P(w * 0.5, fwd, hh * 0.5), P(-w * 0.5, fwd, hh * 0.5)])
        u.add(K.loft(nm, rows), "weapon", mat, bev, 1, 0, False)
    # 弩臂：扁刀片（4 站）
    for s in (1, -1):
        stations = [(0.170, 0.050, 0.028), (0.100, 0.046, 0.025),
                    (0.205, 0.036, 0.020), (0.305, 0.022, 0.013)]
        rows = []
        for (side, fw, fh) in ((0.0, 0.050, 0.028), (0.100, 0.046, 0.025),
                               (0.205, 0.036, 0.020), (0.305, 0.022, 0.013)):
            fwd = 0.170 + side * 0.24
            upp = 0.006 + side * 0.05
            rows.append([P(s * side, fwd - fw, upp - fh), P(s * side, fwd + fw, upp - fh),
                         P(s * side, fwd + fw, upp + fh), P(s * side, fwd - fw, upp + fh)])
        u.add(K.loft("cb_limb_%d" % s, rows), "weapon", "steel_dark", 0.004, 1, 0, False)
        u.add(K.box("cb_tip_%d" % s, P(s * 0.307, 0.242, 0.020), (0.028, 0.028, 0.026)),
              "weapon", "team_trim", 0.003, 1, 0, False)
        # 弦
        u.add(K.limb("cb_string_%d" % s, P(s * 0.303, 0.240, 0.020), P(0, 0.018, 0.026),
                     0.006, 0.006, sides=4), "weapon", "dark", 0.0, 1, 0, False)
    # 弦枕 / 扳机 / 护圈
    u.add(K.box("cb_nut", P(0, 0.012, 0.030), (0.062, 0.055, 0.052)), "weapon", "steel_dark",
          0.005, 1, 0, False)
    u.add(K.box("cb_nock", P(0, 0.018, 0.026), (0.020, 0.030, 0.024)), "weapon", "team_trim",
          0.002, 1, 0, False)
    u.add(K.box("cb_trigger", P(0, -0.055, -0.052), (0.024, 0.064, 0.024)), "weapon", "iron",
          0.003, 1, 0, False)
    u.add(K.box("cb_guard", P(0, -0.022, -0.072), (0.064, 0.108, 0.018)), "weapon", "iron",
          0.003, 1, 0, False)
    # 前踏环
    for s in (1, -1):
        u.add(K.box("cb_stirrup_%d" % s, P(s * 0.062, 0.272, -0.060), (0.022, 0.022, 0.104)),
              "weapon", "steel_dark", 0.004, 1, 0, False)
    u.add(K.box("cb_stirrup_bar", P(0, 0.272, -0.108), (0.146, 0.024, 0.024)),
          "weapon", "steel_dark", 0.004, 1, 0, False)
    # 前准星（金珠）
    u.add(K.box("cb_sight", P(0, 0.232, 0.058), (0.018, 0.018, 0.022)), "weapon",
          "team_trim", 0.002, 1, 0, False)
    # 上膛矢：杆 + 亮铁尖 + 蓝羽
    u.add(K.box("cb_bolt", P(0, 0.150, 0.070), (0.018, 0.300, 0.018)), "prop_bolt", "wood",
          0.001, 1, 0, False)
    u.add(K.claw("cb_bolt_tip", P(0, 0.300, 0.070), P(0, 0.372, 0.070), 0.030, 0.026),
          "prop_bolt", "steel_light", 0.0, 1, 0, False)
    for s in (1, -1):
        u.add(K.box("cb_fletch_%d" % s, P(s * 0.026, -0.092, 0.070), (0.036, 0.080, 0.008)),
              "prop_bolt", "team", 0.001, 1, 0, False)
        u.add(K.box("cb_fletch2_%d" % s, P(0, -0.092, 0.070 + s * 0.026), (0.008, 0.080, 0.036)),
              "prop_bolt", "team", 0.001, 1, 0, False)


def build(detail=1):
    u = K.Unit(NAME)
    legs(u, detail)
    hips(u, detail)
    torso(u, detail)
    arms(u, detail)
    pauldrons(u, detail)
    tabard(u)
    head(u, detail)
    quiver(u, detail)
    crossbow(u, detail)
    return u


# ══ 加载旧资产 + 握持间隙修正（只位移顶点，不重建网格）════════════════════════
# 出厂网格（4508 面）的右拳是一整块 0.16×0.15 的方块，弩身直接从它的上沿穿过去：
# 静止姿态实测拳顶在弩局部 up +0.044、弩身底面 +0.040 → 相嵌 4 mm，BVH 报 77 对面片；
# 动作里（腕骨被焊到弩上，相对位姿与静止一致）最深处约 22 mm。
# 只做两件**平移**，不动任何面：手整体下移、弩整体上移，让拳顶落到弩身底面下方 2 mm，
# 视觉上仍"托住/夹住"弩身。位移量由 docs/_tmp/cb2_tune.py 扫出来：-0.026 时
# idle/idle_b/walk/shoot/reload/hurt/death 的 hand_*×weapon 全部为 0。
GRIP_HAND_DZ = -0.026      # 手（hand_L/R 组顶点）下移
GRIP_WEAPON_DZ = 0.055     # 弩（weapon + prop_bolt 组顶点）上移；death 的 FLOOR_UP_MIN 按这个值实测


def _shift_group(ob, names, dz):
    """把"主权重在这些骨上"的顶点沿世界 Z 平移（刚性蒙皮，一块骨一组顶点）。"""
    import bmesh
    idx = {g.index for g in ob.vertex_groups if g.name in names}
    if not idx:
        return 0
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    layer = bm.verts.layers.deform.active
    n = 0
    if layer is not None:
        for v in bm.verts:
            g = v[layer]
            if not g:
                continue
            if max(g.keys(), key=lambda k: g[k]) in idx:
                v.co.z += dz
                n += 1
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()
    return n


def fix_grip_clearance(meshes, hand_dz=None, weapon_dz=None):
    """手 / 弩 顶点各平移一点点，消掉"拳块被弩身穿透"。返回 (手顶点数, 弩顶点数)。"""
    hd = GRIP_HAND_DZ if hand_dz is None else hand_dz
    wd = GRIP_WEAPON_DZ if weapon_dz is None else weapon_dz
    nh = nw = 0
    for ob in meshes:
        nh += _shift_group(ob, ("hand_L", "hand_R"), hd)
        nw += _shift_group(ob, ("weapon", "prop_bolt"), wd)
    print("[grip] 手 %+dmm（%d 顶点） / 弩 %+dmm（%d 顶点）"
          % (round(hd * 1000), nh, round(wd * 1000), nw))
    return nh, nw


def load():
    """导入旧 glb（不重建网格）→ 握持间隙修正 → 返回 (root, arm, meshes)。"""
    bpy.ops.import_scene.gltf(filepath=SRC)
    sc = bpy.context.scene
    root = next(o for o in sc.objects if o.type == "EMPTY")
    arm = next(o for o in sc.objects if o.type == "ARMATURE")
    for o in [o for o in sc.objects if o.type == "MESH" and o.name.startswith("Icosphere")]:
        bpy.data.objects.remove(o, do_unlink=True)
    meshes = [o for o in sc.objects if o.type == "MESH"]
    fix_grip_clearance(meshes)
    for pb in arm.pose.bones:
        pb.matrix_basis.identity()
    bpy.context.view_layer.update()
    return root, arm, meshes


def build_rig():
    """兼容 run_unit 的入口：返回导入的骨架（需要在 load() 之后调用）。"""
    return next(o for o in bpy.context.scene.objects if o.type == "ARMATURE")
