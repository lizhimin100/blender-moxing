"""anims_破法者.py —— 破法者的 7 条动作

口径与《单位资产规范》一致：
  * 30 fps；idle / walk 首末帧逐骨矩阵差 = 0；attack 命中帧在 40%；
  * 躯干走 FK，四肢走双骨解析 IK（手/脚落在目标点，不手调角度）；
  * 名字只用引擎状态：idle / walk / attack / cast / hurt / death（+ idle_alt 剪辑件）。

本兵种特有的三件事：
  * `weapon_R` 局部 +Y = 十字刃的飞行轴 → 抛出去靠 `P.LOC["weapon_R"]=(0,d,0)`，
    自旋靠绕"当前骨轴"转（飞盘式：面朝前、绕法线转）。
  * `fx_cast` 骨缩放：静止 1.0（特效网格只有 1/44 大，看不见），施法放大到 45。
  * 盾挂在 forearm_L 上：左手去哪儿，盾跟到哪儿 —— 叉腰时盾自然垂到胯侧。
"""
import math

import bpy
from mathutils import Matrix, Vector

import poselib2 as PL
import unit_破法者 as U

FPS = 30
L_UA, L_FA = U.L_UPPER, U.L_FORE
L_TH, L_SH = U.L_THIGH, U.L_SHIN

REST_R = U.FIST_R.copy()
REST_L = U.FIST_L.copy()
FX_FULL = 1.0 / U.FX_K          # ≈45.5，施法时把特效骨放大到这个倍数

# 站姿：右脚略后、左脚略前外（重心在右腿）
FOOT_R = Vector((0.122, 0.010, 0.105))
FOOT_L = Vector((-0.126, 0.086, 0.105))


def _ik2(a, b, l1, l2, pole):
    return PL.ik2(a, b, l1, l2, pole)


def stand(P, feet=True):
    P.leg("R", FOOT_R, (0.35, 1.0, 0.10), 0.0, 3.0)
    P.leg("L", FOOT_L, (-0.35, 1.0, 0.10), 0.0, -9.0)


def pose(rig, dz=0.0, dx=0.0, dy=0.0,
         hips_yaw=0.0, hips_pitch=0.0, hips_roll=0.0,
         spine_pitch=0.0, spine_yaw=0.0,
         chest_pitch=0.0, chest_yaw=0.0, chest_roll=0.0,
         head_pitch=0.0, head_yaw=0.0, head_roll=0.0):
    P = PL.Frame(rig)
    PL.stance(P, dz=dz, dx=dx, dy=dy, hips_yaw=hips_yaw, hips_pitch=hips_pitch,
              hips_roll=hips_roll, spine_pitch=spine_pitch, spine_yaw=spine_yaw,
              chest_pitch=chest_pitch, chest_yaw=chest_yaw, chest_roll=chest_roll,
              head_pitch=head_pitch, head_yaw=head_yaw, head_roll=head_roll,
              legs=False)
    return P


def blade_spin(P, deg):
    """绕十字刃当前法线自旋（飞盘式）。"""
    axis = (P.R["weapon_R"] @ Vector((0, 1, 0))).normalized()
    P.apply("weapon_R", Matrix.Rotation(math.radians(deg), 3, axis))


def blade_aim(P, direction):
    P.aim("weapon_R", direction)


# ── 1. idle：叉腰（重心在右腿，左手叉腰，右手垂着拎刃）────────────────────
def a_idle(rig, D=120):
    act = PL.new_action(rig.arm, "idle")
    W = PL.Writer(rig, loc_bones=("weapon_R",), scl_bones=("fx_cast",))
    HIP_R = Vector((0.302, 0.104, 1.002))

    keys = [
        # f,    dz,     sway,  roll, breath, hy,   hp
        (0,   0.000,  0.000, -1.6,  0.0,   0.0,  0.0),
        (20,  0.005,  0.006, -2.4,  1.4,  -2.0, -0.6),
        (40, -0.003,  0.002, -1.2, -0.6,  -3.0,  0.6),
        (60,  0.004, -0.004, -2.0,  1.2,   1.5, -0.4),
        (80, -0.002, -0.002, -1.4, -0.4,   2.5,  0.8),
        (100, 0.003,  0.003, -2.2,  1.0,   0.5, -0.2),
        (120, 0.000,  0.000, -1.6,  0.0,   0.0,  0.0),
    ]
    for (f, dz, sway, roll, breath, hy, hp) in keys:
        P = pose(rig, dz=dz, dx=sway, hips_roll=roll, chest_pitch=breath,
                 spine_pitch=breath * 0.4, head_yaw=hy, head_pitch=hp,
                 hips_yaw=roll * 0.4)
        stand(P)
        P.arm("R", HIP_R + Vector((0.002, 0.002, dz * 0.5)), (1.0, -0.25, -0.10))
        P.arm("L", REST_L + Vector((0, 0.002, dz * 0.35)), (-0.92, -0.66, -0.22))
        blade_spin(P, 14)
        P.SCL["fx_cast"] = 1.0
        W.key(P, f)
    PL.finish_action(act)
    return act


# ── 2. idle_alt：左右摇头（警觉地打量两侧）──────────────────────────────
def a_idle_alt(rig, D=96):
    act = PL.new_action(rig.arm, "idle_alt")
    W = PL.Writer(rig, loc_bones=("weapon_R",), scl_bones=("fx_cast",))
    seq = [
        # f,  head_yaw, chest_yaw, dz,     hp
        (0,    0.0,      0.0,      0.000,  0.0),
        (10,  -4.0,     -2.0,      0.004, -0.6),
        (24, -26.0,    -10.0,      0.002, -1.2),
        (34, -24.0,     -9.0,      0.002, -0.8),
        (46,  24.0,      9.0,      0.000, -1.4),
        (58,  26.0,     10.0,      0.000, -0.8),
        (70,  10.0,      4.0,      0.003, -0.4),
        (82,  -2.0,     -1.0,      0.002,  0.2),
        (96,   0.0,      0.0,      0.000,  0.0),
    ]
    for (f, hy, cy, dz, hp) in seq:
        P = pose(rig, dz=dz, hips_yaw=cy * 0.30, chest_yaw=cy, head_yaw=hy,
                 head_pitch=hp, chest_pitch=0.6)
        stand(P)
        P.arm("L", REST_L + Vector((0, 0.002, dz)), (-0.9, -0.7, -0.2))
        P.arm("R", REST_R + Vector((0, 0.002, dz)), (0.85, -0.75, -0.30))
        P.SCL["fx_cast"] = 1.0
        W.key(P, f)
    PL.finish_action(act)
    return act


# ── 3. walk：1.07 s 循环；步幅 0.38 m（单脚前后各 0.19），支撑脚不打滑 ────────
SB_STEP = 0.19                  # 单脚前后各 0.19 m（总跨 0.38）
SB_SUP = 0.55                   # 支撑相占比（>0.5 → 有双脚同时着地的重叠段）
# 靴底两个最低角相对踝关节的 (dy, dz) —— 算脚掌绕踝旋转时要把踝抬多高才不穿地
SB_HEEL = (-0.078, -0.103)
SB_TOE = (0.204, -0.103)


def foot_clear(pitch_deg):
    """脚掌绕踝转 pitch 后，靴底最低点仍在地面所需的最矮踝高。"""
    a = math.radians(pitch_deg)
    sa, ca = math.sin(a), math.cos(a)
    lo = min(SB_HEEL[0] * sa + SB_HEEL[1] * ca,
             SB_TOE[0] * sa + SB_TOE[1] * ca)
    return max(U.Z_ANKLE, -lo + 0.006)


def a_walk(rig, D=32):
    act = PL.new_action(rig.arm, "walk")
    W = PL.Writer(rig, loc_bones=("weapon_R",), scl_bones=("fx_cast",))

    def leg_y(ph):
        if ph < SB_SUP:                       # 支撑：匀速后移（接触地面不打滑）
            return SB_STEP - 2.0 * SB_STEP * (ph / SB_SUP)
        u = (ph - SB_SUP) / (1.0 - SB_SUP)    # 摆动：smoothstep 前摆
        return -SB_STEP + 2.0 * SB_STEP * (u * u * (3.0 - 2.0 * u))

    def leg_z(ph):
        if ph < SB_SUP:
            return 0.0
        u = (ph - SB_SUP) / (1.0 - SB_SUP)
        z = 0.085 * math.sin(math.pi * u)
        if u < 0.34:                          # 刚离地那一下额外收脚
            z += 0.030 * math.sin(math.pi * u / 0.34)
        return z

    def foot_pitch(ph):
        if ph < SB_SUP:
            u = ph / SB_SUP
            if u < 0.45:                      # 脚跟着地 → 踩平
                k = u / 0.45
                return 9.0 * (1.0 - k * k * (3.0 - 2.0 * k))
            k = (u - 0.45) / 0.55             # 踩平 → 脚尖蹬地
            return -16.0 * (k * k * (3.0 - 2.0 * k))
        u = (ph - SB_SUP) / (1.0 - SB_SUP)
        if u < 0.55:                          # 离地 → 摆动中段抬脚尖
            k = u / 0.55
            return -16.0 + 28.0 * (k * k * (3.0 - 2.0 * k))
        k = (u - 0.55) / 0.45                 # 抬脚尖 → 回到落地的 9°
        return 12.0 - 3.0 * (k * k * (3.0 - 2.0 * k))

    for i in range(D + 1):
        t = i / D
        a2 = 2.0 * math.pi * t
        cy = math.cos(a2)
        P = pose(rig,
                 dz=-0.020 - 0.014 * math.cos(2.0 * a2),   # 接触帧最低
                 dx=0.016 * math.sin(a2),                  # 侧移跟支撑腿
                 hips_yaw=4.5 * cy, hips_roll=-3.5 * cy,
                 chest_yaw=-6.0 * cy, chest_roll=1.4 * cy,  # 与髋反相
                 chest_pitch=-2.2, spine_pitch=-0.88,       # 常驻微前倾
                 head_pitch=1.1 * math.cos(2.0 * a2))       # 轻微点头

        for side, s, ph in (("R", 1, t), ("L", -1, (t + 0.5) % 1.0)):
            fp = foot_pitch(ph)
            A = Vector((s * 0.122, 0.015 + leg_y(ph), foot_clear(fp) + leg_z(ph)))
            P.leg(side, A, (s * 0.30, 1.0, 0.12), fp, s * 3.0)

        # 左手（持盾）与右腿同相；右手（持刃）反相且滞后 0.08 个周期
        P.arm("L", REST_L + Vector((-0.008, -0.004 + 0.045 * cy, -0.004)),
              (-0.90, -0.65, -0.25))
        P.arm("R", REST_R + Vector((0.006,
                                    0.008 - 0.030 * math.cos(2 * math.pi * (t - 0.08)),
                                    0.0)),
              (0.85, -0.75, -0.30))
        blade_spin(P, 14)
        P.SCL["fx_cast"] = 1.0
        W.key(P, i)
    PL.finish_action(act)
    return act


# ── 4. attack：扔出十字刃 → 飞出去自旋 → 回旋 → 一把抓住 ──────────────────
def a_attack(rig, D=45):
    act = PL.new_action(rig.arm, "attack")
    W = PL.Writer(rig, loc_bones=("weapon_R",), scl_bones=("fx_cast",))
    DIR = Vector((0.0, 0.945, 0.30)).normalized()

    def K(f, dz=0.0, hips_yaw=0.0, chest_yaw=0.0, chest_pitch=0.0, head_yaw=0.0,
          head_pitch=0.0, hand=None, dist=0.0, spin=0.0, aim=None, lhand=None):
        P = pose(rig, dz=dz, hips_yaw=hips_yaw, chest_yaw=chest_yaw,
                 chest_pitch=chest_pitch, head_yaw=head_yaw, head_pitch=head_pitch)
        stand(P)
        if hand is not None:
            P.arm("R", hand, (0.9, -0.5, -0.35))
        if aim is not None:
            blade_aim(P, aim)
        if spin:
            blade_spin(P, spin)
        P.LOC["weapon_R"] = Vector((0, dist, 0))
        if lhand is None:
            lhand = REST_L + Vector((0, 0, dz * 0.3))
        P.arm("L", lhand, (-0.9, -0.7, -0.25))
        P.SCL["fx_cast"] = 1.0
        W.key(P, f)

    # 起手
    K(0, hand=REST_R, lhand=REST_L)
    # 蓄力：身体右转、右手后拉、刃面甩到侧后
    K(5, dz=-0.012, hips_yaw=-8, chest_yaw=-16, chest_pitch=2.0, head_yaw=6,
      hand=Vector((0.352, 0.030, 1.010)), spin=-40,
      lhand=Vector((-0.235, 0.190, 0.980)))
    K(10, dz=-0.020, hips_yaw=-14, chest_yaw=-30, chest_pitch=4.0, head_yaw=10,
      hand=Vector((0.386, -0.070, 1.086)), spin=-150,
      lhand=Vector((-0.286, 0.150, 0.940)))
    # 挥出
    K(14, dz=-0.010, hips_yaw=-6, chest_yaw=-14, chest_pitch=1.0, head_yaw=4,
      hand=Vector((0.300, 0.170, 1.190)), spin=-210,
      lhand=Vector((-0.235, 0.200, 0.960)))
    # 释放（命中前）
    K(17, dz=0.004, hips_yaw=4, chest_yaw=10, chest_pitch=-3.0, head_yaw=-4,
      hand=Vector((0.246, 0.330, 1.246)), dist=0.02, spin=-260, aim=DIR,
      lhand=Vector((-0.318, 0.214, 0.972)))
    # 飞出：18 = 命中帧（40%）
    K(18, dz=0.004, hips_yaw=4, chest_yaw=10, chest_pitch=-3.0, head_yaw=-4,
      hand=Vector((0.244, 0.336, 1.250)), dist=0.34, spin=-330, aim=DIR,
      lhand=Vector((-0.318, 0.214, 0.972)))
    K(22, dz=0.002, hips_yaw=3, chest_yaw=8, chest_pitch=-2.0, head_yaw=-4,
      hand=Vector((0.250, 0.330, 1.238)), dist=0.86, spin=-620, aim=DIR,
      lhand=Vector((-0.312, 0.212, 0.976)))
    K(26, dz=0.000, hips_yaw=2, chest_yaw=6, chest_pitch=-1.0, head_yaw=-3,
      hand=Vector((0.256, 0.322, 1.228)), dist=1.52, spin=-880, aim=DIR,
      lhand=Vector((-0.306, 0.208, 0.978)))
    # 回旋
    K(31, dz=0.000, hips_yaw=0, chest_yaw=2, chest_pitch=0.0, head_yaw=-2,
      hand=Vector((0.262, 0.312, 1.222)), dist=1.16, spin=-1120, aim=DIR,
      lhand=Vector((-0.235, 0.204, 0.980)))
    K(35, dz=-0.006, hips_yaw=-2, chest_yaw=-3, chest_pitch=1.2, head_yaw=2,
      hand=Vector((0.286, 0.276, 1.180)), dist=0.48, spin=-1290, aim=DIR,
      lhand=Vector((-0.296, 0.200, 0.984)))
    # 接住：手往前一迎，刃回到掌心
    K(38, dz=-0.014, hips_yaw=-6, chest_yaw=-10, chest_pitch=3.0, head_yaw=4,
      hand=Vector((0.318, 0.196, 1.116)), dist=0.03, spin=-1440,
      aim=Vector((0, 0.88, 0.48)).normalized(),
      lhand=Vector((-0.302, 0.206, 0.978)))
    K(41, dz=-0.008, hips_yaw=-3, chest_yaw=-5, chest_pitch=1.4, head_yaw=2,
      hand=Vector((0.330, 0.180, 1.020)), spin=-1440,
      aim=Vector((0, 0.98, 0.20)).normalized(),
      lhand=Vector((-0.312, 0.216, 0.986)))
    K(45, hand=REST_R, lhand=REST_L)
    PL.finish_action(act)
    return act


# ── 5. cast：举刃过顶 + 蓝色电弧（fx_cast 从 1 放大到 45）──────────────────
def a_cast(rig, D=60):
    act = PL.new_action(rig.arm, "cast")
    W = PL.Writer(rig, loc_bones=("weapon_R",), scl_bones=("fx_cast",))
    UP = Vector((0.02, 0.42, 0.90)).normalized()

    def K(f, dz=0.0, hips_yaw=0.0, chest_yaw=0.0, chest_pitch=0.0, chest_roll=0.0,
          head_pitch=0.0, head_yaw=0.0, hand=None, aim=None, dist=0.0, fx=1.0,
          lhand=None):
        P = pose(rig, dz=dz, hips_yaw=hips_yaw, chest_yaw=chest_yaw,
                 chest_pitch=chest_pitch, chest_roll=chest_roll,
                 head_pitch=head_pitch, head_yaw=head_yaw)
        stand(P)
        if hand is not None:
            P.arm("R", hand, (0.95, -0.30, -0.15))
        if aim is not None:
            blade_aim(P, aim)
        P.LOC["weapon_R"] = Vector((0, dist, 0))
        if lhand is None:
            lhand = REST_L + Vector((0, 0, dz * 0.3))
        P.arm("L", lhand, (-0.9, -0.7, -0.25))
        P.SCL["fx_cast"] = fx
        W.key(P, f)

    K(0, hand=REST_R, lhand=REST_L)
    # 下沉蓄势
    K(6, dz=-0.020, chest_pitch=4.0, head_pitch=2.0,
      hand=Vector((0.360, 0.120, 0.860)), lhand=Vector((-0.330, 0.250, 0.990)))
    # 举起来
    K(14, dz=-0.006, hips_yaw=4, chest_yaw=-8, chest_pitch=-4.0, chest_roll=-2.0,
      head_pitch=-6.0, head_yaw=4,
      hand=Vector((0.236, 0.118, 1.688)), aim=UP, dist=0.02,
      lhand=Vector((-0.352, 0.286, 1.048)))
    # 顶点顿一下 + 电弧爆开
    K(20, dz=0.004, hips_yaw=5, chest_yaw=-10, chest_pitch=-7.0, chest_roll=-3.0,
      head_pitch=-9.0, head_yaw=5,
      hand=Vector((0.238, 0.124, 1.764)), aim=UP, dist=0.02, fx=FX_FULL,
      lhand=Vector((-0.360, 0.296, 1.062)))
    # 抖动（电弧闪）
    for i, (f, k) in enumerate(((24, 0.72), (27, 1.06), (30, 0.64), (33, 1.0),
                                (36, 0.80), (39, 1.02))):
        K(f, dz=0.002, hips_yaw=5, chest_yaw=-10, chest_pitch=-6.4 - 0.4 * i,
          chest_roll=-3.0, head_pitch=-8.4, head_yaw=5,
          hand=Vector((0.238 + 0.004 * math.sin(i * 2.1), 0.124, 1.762)),
          aim=UP, dist=0.02, fx=FX_FULL * k,
          lhand=Vector((-0.360, 0.296, 1.060)))
    # 收
    K(46, dz=-0.008, hips_yaw=2, chest_yaw=-4, chest_pitch=-1.0, chest_roll=-1.0,
      head_pitch=-3.0, hand=Vector((0.238, 0.180, 1.406)), fx=FX_FULL * 0.30,
      aim=Vector((0, 0.86, 0.50)).normalized(),
      lhand=Vector((-0.336, 0.266, 1.016)))
    K(52, dz=-0.004, chest_pitch=1.0, hand=Vector((0.320, 0.180, 1.010)), fx=1.0,
      lhand=Vector((-0.330, 0.258, 1.002)))
    K(60, hand=REST_R, lhand=REST_L)
    PL.finish_action(act)
    return act


# ── 6. hurt：0.37 s，被砸得一缩 ─────────────────────────────────────────
def a_hurt(rig, D=11):
    act = PL.new_action(rig.arm, "hurt")
    W = PL.Writer(rig, loc_bones=("weapon_R",), scl_bones=("fx_cast",))
    seq = [
        (0, 0.000, 0.0, 0.0, 0.0),
        (3, -0.016, 8.0, -7.0, 9.0),
        (6, -0.008, 3.5, -3.0, 4.0),
        (11, 0.000, 0.0, 0.0, 0.0),
    ]
    for (f, dz, cp, cy, hp) in seq:
        P = pose(rig, dz=dz, chest_pitch=cp, chest_yaw=cy, head_pitch=hp,
                 hips_pitch=cp * 0.3, hips_yaw=cy * 0.3)
        stand(P)
        P.arm("R", REST_R + Vector((0.01, -0.01, dz * 0.4)), (0.9, -0.6, -0.3))
        P.arm("L", REST_L + Vector((-0.01, 0.01, dz * 0.4)), (-0.9, -0.7, -0.2))
        P.SCL["fx_cast"] = 1.0
        W.key(P, f)
    PL.finish_action(act)
    return act


# ── 7. death：跪倒 → 撑盾 → 低垂，末 0.4 s 绝对静止 ──────────────────────
def a_death(rig, D=46):
    act = PL.new_action(rig.arm, "death")
    W = PL.Writer(rig, loc_bones=("weapon_R",), scl_bones=("fx_cast",))
    seq = [
        # f,   dz,     hips_pitch, chest_pitch, head_pitch, head_yaw, chest_yaw
        (0,   0.000,   0.0,       0.0,         0.0,       0.0,      0.0),
        (4,  -0.020,  -4.0,      -8.0,         6.0,      -4.0,     -6.0),
        (10, -0.090,   8.0,      12.0,         6.0,      -6.0,     -8.0),
        (16, -0.160,  16.0,      24.0,         9.0,      -7.0,     -9.0),
        (22, -0.235,  22.0,      34.0,        12.0,      -6.0,     -8.0),
        (27, -0.272,  25.0,      40.0,        15.0,      -5.0,     -7.0),
        (32, -0.282,  26.0,      42.0,        16.0,      -5.0,     -7.0),
        (46, -0.282,  26.0,      42.0,        16.0,      -5.0,     -7.0),
    ]
    for (f, dz, hip, cp, hp, hy, cy) in seq:
        P = pose(rig, dz=dz, hips_pitch=hip, chest_pitch=cp, head_pitch=hp,
                 head_yaw=hy, chest_yaw=cy, hips_yaw=cy * 0.3)
        # 跪：右腿在前、左膝下沉；脚掌随之下压
        q = dz / -0.282
        P.leg("R", Vector((0.140, 0.020 + 0.140 * q, U.Z_ANKLE + 0.006)),
              (0.35, 1.0, 0.10), 0.0, 5.0)
        P.leg("L", Vector((-0.146, 0.080 - 0.040 * q, U.Z_ANKLE + 0.013)),
              (-0.35, 1.0, 0.10), 8.0 * q, -9.0)
        P.arm("R", REST_R + Vector((0.02, -0.03, dz * 0.5)), (0.95, -0.45, -0.4))
        P.arm("L", REST_L + Vector((-0.02, 0.02, dz * 0.4)), (-0.95, -0.55, -0.3))
        P.SCL["fx_cast"] = 1.0
        W.key(P, f)
    PL.finish_action(act)
    return act


def build_all(arm, only=None):
    rig = PL.Rig(arm)
    table = [("idle", a_idle), ("idle_alt", a_idle_alt), ("walk", a_walk),
             ("attack", a_attack), ("cast", a_cast), ("hurt", a_hurt),
             ("death", a_death)]
    out = []
    for name, fn in table:
        if only and name not in only:
            continue
        act = fn(rig)
        act.name = name
        out.append(name)
        print("[anim]", name, "frames", tuple(int(v) for v in act.frame_range))
    arm.animation_data.action = None
    for pb in arm.pose.bones:
        pb.matrix_basis.identity()
    return out
