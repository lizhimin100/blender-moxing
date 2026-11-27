"""anims_human.py —— 联盟人类（步兵 / 弩兵 / 农民）共用的动作基元

为什么要有这一层：三个兵种的身高/体宽不同（`human_kit2.Human`），但**走路的节奏、
脚的起落、躯干的沉降**必须是同一套，否则三个单位并排走会像三个游戏里的。

口径（与《单位资产规范》《精模单位_秘法》§5 一致）：
  * 逐帧烘焙（`poselib2.bake`），不用贝塞尔插关键帧 —— 四元数插值会让脚飘。
  * 支撑相脚**匀速后移**（不打滑），摆动相用 smoothstep，抬脚半正弦。
  * `chest_pitch` 负值 = 前倾；`hips_yaw` 正值 = 右肩朝前。
  * 踝高一律走 `S.foot_clear(pitch)` —— 脚一有 pitch，脚跟/脚尖就会切进地面。

用法（anims_xxx.py）：

    import anims_human as AH
    P = AH.pose(rig, S, dz=..., chest_pitch=...)
    AH.walk(P, S, t, step=0.30, lift=0.085, base_dz=-0.02)
    AH.finish(act)          # 统一插值处理 + 去掉动作
"""
import math

from mathutils import Vector

import poselib2 as PL


def smooth(u):
    u = max(0.0, min(1.0, u))
    return u * u * (3.0 - 2.0 * u)


# ══ 1. 姿态 / 脚 ════════════════════════════════════════════════════════════
def pose(rig, S, dz=0.0, dx=0.0, dy=0.0, **kw):
    """躯干层（腿单独摆），最后一律 `feet()` 落地。"""
    P = PL.Frame(rig)
    PL.stance(P, dz=dz, dx=dx, dy=dy, legs=False, **kw)
    return P


def leg(P, S, side, x, y, pitch=0.0, yaw=0.0, lift=0.0, spread=0.0):
    """单腿 IK：踝落在 (x, y, foot_clear(pitch)+lift)。"""
    s = 1 if side == "R" else -1
    pole = (s * 0.42, 1.0, 0.14)
    P.leg(side, Vector((x + s * spread, y, S.foot_clear(pitch) + lift)), pole, pitch, yaw)


def feet(P, S, r=None, l=None):
    """r/l = (x, y, pitch, yaw[, lift])，缺省是站立（与静止骨架一致）。"""
    r = r or (S.ANK.x, 0.0, 0.0, 4.0)
    l = l or (-S.ANK.x, 0.0, 0.0, -4.0)
    for side, v in (("R", r), ("L", l)):
        x, y, pitch, yaw = v[:4]
        lift = v[4] if len(v) > 4 else 0.0
        leg(P, S, side, x, y, pitch, yaw, lift)


def stand(P, S, x_scale=1.0, y=0.0):
    feet(P, S, (S.ANK.x * x_scale, y, 0.0, 4.0), (-S.ANK.x * x_scale, y, 0.0, -4.0))


# ══ 落地：脚底真的踩在地上（不是"算出来大概在地上"）════════════════════════
def sole(S):
    """懒建脚底点云（要骨架和网格都在场景里才能建）。一次建好挂在 Spec 上复用。"""
    import bpy
    cur = next((o for o in bpy.context.scene.objects if o.type == "ARMATURE"), None)
    if cur is None:
        return None
    have = getattr(S, "SOLE", None)
    # 同一个进程里重建过一次单位（全量档 + 低模档）就换一副点云，否则用的是旧骨架
    if have is None or have.arm is not cur:
        meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
        S.SOLE = PL.Sole(cur, meshes)
        print("[sole]", {k: len(v) for k, v in S.SOLE.pts.items()})
    return S.SOLE


def ground(P, S, target=0.0015, sides=("R", "L")):
    """每条动作 emit 的最后一句：把脚抬到刚好贴地（只抬不压）。"""
    return PL.ground(P, sole(S), target=target, sides=sides)


# ══ 2. 走循环 ═══════════════════════════════════════════════════════════════
def walk_leg(ph, step, lift, sup=0.56):
    """一条腿在相位 ph（0..1）时的 (前后位移, 抬脚, 脚 pitch)。

    支撑相 0..sup：脚从 +step 匀速走到 −step（不打滑）；
    摆动相 sup..1：smoothstep 回 +step，抬脚是半正弦。
    """
    if ph < sup:
        u = ph / sup
        y = step - 2.0 * step * u
        z = 0.0
        if u < 0.34:                                  # 脚跟着地 → 全脚掌
            pitch = 8.0 * (1.0 - smooth(u / 0.34))
        else:                                          # 蹬离
            pitch = -13.0 * smooth((u - 0.34) / 0.66)
    else:
        u = (ph - sup) / (1.0 - sup)
        y = -step + 2.0 * step * smooth(u)
        z = lift * math.sin(math.pi * u) ** 0.80
        if u < 0.5:
            pitch = -13.0 + 25.0 * smooth(u / 0.5)
        else:
            pitch = 12.0 - 4.0 * smooth((u - 0.5) / 0.5)
    return y, z, pitch


def walk(P, S, t, step=0.30, lift=0.085, base_dz=0.0, base_pitch=0.0,
         hips_yaw=7.0, chest_yaw=-8.0, chest_roll=1.6, head_yaw=3.0,
         sink=0.018, y_off=0.0, side_sway=0.030, spread=0.0):
    """把一帧走路叠到已建好的 P 上（t = 0..1，一个完整步幅）。"""
    a = 2.0 * math.pi * t
    cy = math.cos(a)
    # 落地时髋部再沉一点（每步一次）
    sk = 0.0
    for c in (0.0, 0.5):
        k = (t - c) % 1.0
        if k < 0.10:
            sk -= sink * math.sin(math.pi * k / 0.10)
    P.offset += Vector((side_sway * math.sin(a), 0.0,
                        base_dz - 0.020 * math.cos(2.0 * a) + sk))
    P.rot("hips", (0, 0, 1), hips_yaw * cy)
    P.rot("hips", (0, 1, 0), -4.0 * cy)
    P.rot("chest", (0, 0, 1), chest_yaw * cy)
    P.rot("chest", (0, 1, 0), chest_roll * cy)
    P.rot("chest", (1, 0, 0), base_pitch - 1.4 * math.cos(2.0 * a))
    P.rot("head", (0, 0, 1), head_yaw * cy)
    for side, s, ph in (("R", 1, t), ("L", -1, (t + 0.5) % 1.0)):
        y, z, pitch = walk_leg(ph, step, lift)
        leg(P, S, side, s * S.ANK.x, y_off + y, pitch, s * 5.0, z, spread)
    return P


# ══ 3. 受击 / 阵亡的通用骨架 ════════════════════════════════════════════════
def hurt_keys(dz0, pitch0, side=-1):
    """11 帧受击的通用参数序列：(帧, dz, dx, chest_pitch, chest_roll, head_pitch)。

    side=-1 表示被打得往左踉跄（+X 是角色右侧）。
    """
    return [
        (0, dz0, 0.0, pitch0, 0.0, 0.0),
        (3, dz0 - 0.030, 0.022 * side, pitch0 + 13.0, 7.0 * side, 12.0),
        (6, dz0 - 0.014, 0.010 * side, pitch0 - 5.0, 3.0 * side, 6.0),
        (9, dz0 - 0.004, 0.002 * side, pitch0 + 1.5, 1.0 * side, 1.0),
        (11, dz0, 0.0, pitch0, 0.0, 0.0),
    ]


def land_drop(P, S, drop=0.30, pitch=-8.0):
    """倒地时把整个骨架沉下去并前倾（root 只走 offset，不写死位置）。"""
    P.offset += Vector((0.0, 0.0, -drop))
    P.rot("hips", (1, 0, 0), pitch)


def drop_layered(P, bone, target, target_R, kp, kr):
    """脱手：**位置进度 kp 与姿态进度 kr 分开给**。

    `poselib2.drop_to` 用一个 k 同时插值位置和朝向 —— 武器还举在手上（z≈0.5）、
    朝向已经转到"平躺"时，刃尖会在半空中扫过地面（实测扎进地里 0.26 m）。
    这里让朝向先转（kr 超前），位置后落（kp 滞后），中途就不会切地。
    """
    P.solve_T()
    T0 = P.T[bone].copy()
    q0 = P.R[bone].to_quaternion()
    q1 = target_R.to_quaternion() if hasattr(target_R, "to_quaternion") else target_R.copy()
    q = q0.slerp(q1, kr)
    T = T0.lerp(Vector(target), kp)
    P.place(bone, T, q.to_matrix(), chain=True)
    return T


def finish(act):
    PL.finish_action(act)
    return act
