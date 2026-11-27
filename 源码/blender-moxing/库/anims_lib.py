"""anims_lib.py —— 格网档人形单位的动作基座（与 poselib2 配套）

三条纪律（和精模档一致，只是更硬）：
  * 一帧一帧烘焙：IK 只保证关键帧那帧落点对，帧间插值会让脚飘出去；
  * 根骨位移恒为 0（只有 walk_film / stagger 例外，格网档不做）；
  * 需要整段位移时改 `hips` 的 LOC（`place()`），不要动 root。

动作名沿用引擎六名：idle / walk / attack / hurt / death / cast。
"""
import math

import bpy
from mathutils import Matrix, Vector

import poselib2 as PL

FPS = 30
_ACTS = {}
_SOLE = None


def set_sole(sole):
    """把脚底点云交给烘焙器：每一帧出完姿态后把脚抬到贴地（只抬不压）。"""
    global _SOLE
    _SOLE = sole


# ── 参数插值（smoothstep）───────────────────────────────────────────────────
def _mix(a, b, u):
    if isinstance(a, bool) or isinstance(b, bool):
        return a if u < 1.0 else b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return a + (b - a) * u
    if isinstance(a, (tuple, list)) and isinstance(b, (tuple, list)):
        return tuple(_mix(x, y, u) for x, y in zip(a, b))
    if isinstance(a, Vector) and isinstance(b, Vector):
        return a.lerp(b, u)
    return a if u < 1.0 else b


def params_at(keys, i, default):
    """keys = [(frame, {参数…})]，返回第 i 帧插值后的完整参数字典。"""
    keys = sorted(keys, key=lambda kv: kv[0])
    j = 0
    while j + 1 < len(keys) and keys[j + 1][0] <= i:
        j += 1
    f0, a = keys[j]
    f1, b = keys[min(j + 1, len(keys) - 1)]
    u = 0.0 if f1 == f0 else (i - f0) / float(f1 - f0)
    u = max(0.0, min(1.0, u))
    u = u * u * (3.0 - 2.0 * u)
    out = dict(default)
    out.update(a)
    for k, bb in b.items():
        aa = out.get(k, bb)
        out[k] = _mix(aa, bb, u)
    return out


# ── 建动作 ──────────────────────────────────────────────────────────────────
def make(arm, name, end, keys, bake_fn, loc=("hips", "weapon_R", "weapon_L"),
         scl=(), loop=False, post=None):
    """把一段参数化的动作逐帧烘焙成 action。

    `post(P, p, i)` 在**落地校正之后**再跑一次：弓弦这类"必须对到手上"的零件
    只能放在这里算 —— 抬脚贴地把整个人往上顶了几厘米，姿态里算的弦长就对不上了。
    """
    rig = PL.Rig(arm)
    act = PL.new_action(arm, name)
    W = PL.Writer(rig, loc_bones=loc, scl_bones=scl)
    default = dict(keys[0][1])
    for k, d in keys:
        default.update(d)
    for i in range(end + 1):
        P = PL.Frame(rig)
        p = params_at(keys, i, default)
        if loop and i == end:
            p = params_at(keys, 0, default)      # 首末逐骨相同，避免浮点漂移
        bake_fn(P, p, i)
        if _SOLE is not None:
            P.solve_T()
            PL.ground(P, _SOLE)
        P.solve_T()
        if post is not None:
            post(P, p, i)
        W.key(P, i)
    PL.finish_action(act)
    _ACTS[act.name] = act
    print("[act] %-8s %5.2fs  f0..%d" % (name, end / float(FPS), end))
    return act


def clear_pose(arm):
    arm.animation_data.action = None
    for pb in arm.pose.bones:
        pb.matrix_basis.identity()
        pb.location = (0, 0, 0)
        pb.scale = (1, 1, 1)


def pose_at(arm, action, frame):
    """预览用：把骨架切到某条动作的某一帧。"""
    if arm.animation_data is None:
        arm.animation_data_create()
    act = bpy.data.actions[action]
    arm.animation_data.action = act
    try:
        arm.animation_data.action_slot = act.slots[0]
    except Exception:
        pass
    bpy.context.scene.frame_set(int(frame))
    bpy.context.view_layer.update()


# ── 通用姿态零件 ────────────────────────────────────────────────────────────
def stance(P, p):
    """躯干 + 头 + 双脚（系数全从参数字典里读，缺省 0）。"""
    PL.stance(
        P, dz=p.get("dz", 0.0), dx=p.get("dx", 0.0), dy=p.get("dy", 0.0),
        hips_yaw=p.get("hy", 0.0), hips_pitch=p.get("hp", 0.0), hips_roll=p.get("hr", 0.0),
        spine_pitch=p.get("sp", 0.0), spine_yaw=p.get("sy", 0.0), spine_roll=p.get("sr", 0.0),
        chest_pitch=p.get("cp", 0.0), chest_yaw=p.get("cy", 0.0), chest_roll=p.get("cr", 0.0),
        head_pitch=p.get("hdp", 0.0), head_yaw=p.get("hdy", 0.0), head_roll=p.get("hdr", 0.0),
        legs=False,
    )


def feet(P, p, sides=("R", "L")):
    """脚：前后/左右/抬脚/俯仰逐个给（walk 用）。

    膝的朝向由 `p[x,y,z]_<side>` 给（默认"朝前朝外"）；倒地一类动作要把它掰到
    "朝上"，否则躺下以后膝盖会朝地面折。
    """
    for side in sides:
        k = side.lower()
        ank = Vector((p.get("fx_" + k, 0.10 if side == "R" else -0.10),
                      p.get("fy_" + k, 0.015),
                      p.get("fz_" + k, 0.20)))
        pole = (p.get("px_" + k, 0.32 if side == "R" else -0.32),
                p.get("py_" + k, 1.0), p.get("pz_" + k, 0.10))
        P.leg(side, ank, pole, p.get("fp_" + k, 0.0), p.get("fyaw_" + k, 0.0))


def aim_group(P, side, wrist, wdir, bone=None, pole=(0.6, 0.2, -0.78)):
    """把手腕送到 wrist，并把 weapon_<side> 的 +Y 指向 wdir（手连带转）。"""
    bone = bone or ("weapon_" + side)
    PL.aim_weapon(P, side, bone, Vector(wdir), 0.0)
    P.arm(side, Vector(wrist), pole)


def hand_on(P, side, wrist, hdir=(0, 1, 0), pole=(0.55, -0.55, -0.75)):
    P.aim("hand_" + side, Vector(hdir))
    P.arm(side, Vector(wrist), pole)


def grip_point(P, bone, t):
    """武器骨轴线上距骨根 t 米的世界点（第二只手抓这里）。t 可以为负（骨根下方）。"""
    P.solve_T()
    return P.T[bone] + (P.R[bone] @ Vector((0, 1, 0))) * t


# ══ 握持组件（武器定向 / 双手 / 落械）════════════════════════════════════════
#
# 这一组解决的是同一件事：**"手在哪、武器朝哪"要分开写，但结果必须自洽**。
# 之前两份动作脚本把两者混在一个 wd 向量里，于是"手够到了、枪歪了"或者
# "枪对了、手插进胸口"这类问题只能靠试。这里的契约是：
#
#   手的位置 由 IK 目标给（可测：够不够得着）
#   武器的位姿 由 (y_dir, x_dir) 两根轴给（可测：和瞄准线夹角多少度）
#   两者之间只留一个物理常量 —— 握持半径 HAND_R（掌心到武器轴的距离）
#
# 轴向约定（和 voxbase 的建模坐标一致）：
#   武器骨 +Y = 武器长轴（枪指前 / 弓臂朝上 / 箭朝前）
#   武器骨 -X = "正面"（弓腹 / 刃面朝向）
# 所以 `x_dir` 给的是**背面**（弓弦那侧 / 刀背那侧）的世界方向。

HAND_R = 0.10          # 掌心到武器轴的距离（正好是拳头的半宽）
PALM_D = 0.10          # 掌心在 hand 骨局部 +Y 上的距离（hand 骨长 0.20 的一半）


def basis(y_dir, x_dir):
    """正交基：+Y = y_dir，+X = x_dir 去掉 y 分量后归一，+Z = X×Y。"""
    y = Vector(y_dir).normalized()
    x = Vector(x_dir)
    x = x - y * x.dot(y)
    if x.length < 1e-6:
        x = Vector((0, 0, 1)) if abs(y.z) < 0.9 else Vector((1, 0, 0))
        x = x - y * x.dot(y)
    x.normalize()
    z = x.cross(y)
    M = Matrix.Identity(3)
    M.col[0], M.col[1], M.col[2] = x, y, z
    return M


def anchor(P, side):
    """武器骨原点在 hand 骨**静止局部系**里的偏移（常量，只算一次）。"""
    hh, hR = P.rig.rest["hand_" + side]
    wh, _ = P.rig.rest["weapon_" + side]
    return hR.inverted() @ (wh - hh)


def weapon_frame(P, side, y_dir, x_dir, bone=None):
    """把武器骨转到 (y_dir, x_dir) 定义的朝向 —— **转的是 hand**，拳头跟着武器一起转。

    枪/弓/箭都是"握在手里"的，单独转 weapon 骨会让武器在拳头里自转（看着像脱手）。
    """
    bone = bone or ("weapon_" + side)
    M = basis(y_dir, x_dir)
    D = M @ P.R[bone].inverted()
    P.apply("hand_" + side, D, chain=True)
    return M


def palm_of(P, side):
    """掌心世界点（= hand 骨中点，所有"握持"都以它为基准，不以腕为基准）。"""
    P.solve_T()
    return P.T["hand_" + side] + (P.R["hand_" + side] @ Vector((0, PALM_D, 0)))


def hold(P, side, palm, y_dir, x_dir, pole, bone=None, slide=0.0, align=True):
    """**握点驱动**：掌心送到 palm，武器按 (y_dir, x_dir) 定向，再沿自身长轴滑 slide。

    `align=True` 把武器轴**对到掌心上**。为什么需要这一条：武器骨的静止位置在掌心
    前方 0.1 m（那是给剑柄留的"握持半径"），弓和枪要是照这个偏移摆，长件会整体
    偏出半个身位 —— v1 的弓就是这么插进胸口的。对齐之后 `weapon_*` 的骨原点 =
    掌心 = 杆轴，手里那一块被拳头整个含住，读数才是"握着"。

    `slide` 是"换把"：枪在手里前后滑，等价于给 weapon 骨一个局部 +Y 平移 ——
    这一条让同一根枪既能拄地、又能端平突刺，不用改模型上的骨原点。
    """
    bone = bone or ("weapon_" + side)
    weapon_frame(P, side, y_dir, x_dir, bone)
    Rh = P.R["hand_" + side]
    wrist = Vector(palm) - Rh @ Vector((0, PALM_D, 0))
    P.arm(side, wrist, pole)
    off = Vector((0.0, slide, 0.0))
    if align:
        # 掌心 → 武器原点 的世界偏移，用武器局部坐标抵掉（只抵垂轴分量，不抵杆向）
        d = Rh @ Vector((0.0, 0.0, HAND_R))
        off = off - (P.R[bone].inverted() @ d)
    if off.length > 1e-9:
        P.LOC[bone] = off
    P.solve_T()
    return wrist, P.T[bone]


def two_hand(P, side, palm, y_dir, x_dir, t2, other=None, pole_r=(0.55, 0.10, -0.80),
             pole_l=(-0.55, 0.20, -0.78), slide=0.0):
    """双手持长杆：主轴手给掌心 + 杆向，副手自动落到杆上 `t2` 处（沿长轴，米）。

    `t2` 为正 = 朝武器 +Y（枪尖那侧）。副手的掌心直接落在杆轴上（偏 HAND_R 的握持半径
    由掌心—杆轴距离体现，量出来应当在 0.08~0.13 之间）。
    """
    other = other or ("L" if side == "R" else "R")
    _, o = hold(P, side, palm, y_dir, x_dir, pole_r, slide=slide)
    p2 = o + (P.R["weapon_" + side] @ Vector((0, 1, 0))) * t2
    P.aim("hand_" + other, Vector(y_dir))
    wrist2 = p2 - (P.R["hand_" + other] @ Vector((0, PALM_D, 0)))
    P.arm(other, wrist2, pole_l)
    return p2


def arrow_at(P, tail, tip, up=(0, 0, 1), bone="weapon_R", side="R"):
    """箭：骨原点 = 箭尾，+Y = 箭杆方向。整支箭用 place() 搬到世界点。

    箭是"半路出现"的（从箭筒抽出来），不跟着手骨转，所以走 place 而不是 hold。
    """
    d = Vector(tip) - Vector(tail)
    if d.length < 1e-6:
        return None
    M = basis(d, up)
    P.place(bone, Vector(tail), M, chain=True)
    return M



def hand_at(P, side, palm, y_dir, z_dir=(0.0, 0.0, 1.0), pole=(0.55, -0.55, -0.75)):
    """空手（或副手）：**掌心**送到 palm，手骨 +Y 沿 y_dir、+Z 沿 z_dir。

    和 `hold` 的分工：hold 是"握着武器"（还要转武器），这里只是"手摆到某点"。
    副手抓杆用它最省事 —— 杆在哪儿是画出来的，手只要贴上去。
    """
    M = basis(y_dir, z_dir)
    P.set_world("hand_" + side, M)
    wrist = Vector(palm) - M @ Vector((0.0, PALM_D, 0.0))
    P.arm(side, wrist, pole)
    return wrist


def drop_to(P, bone, ground_z, axis_dir, k=1.0, side_hint=(1, 0, 0)):
    """脱手落地：把武器骨从"跟着手"插值到"躺在地上"（k=0 在手上，k=1 已落地）。"""
    P.solve_T()
    T0 = P.T[bone].copy()
    q0 = P.R[bone].to_quaternion()
    M = basis(axis_dir, side_hint)
    q1 = M.to_quaternion()
    q = q0.slerp(q1, k)
    T = Vector((T0.x, T0.y, T0.z)).lerp(Vector((T0.x, T0.y, ground_z)), k)
    P.place(bone, T, q.to_matrix(), chain=True)
    return T


# ══ 行军步（逐帧解析，不走关键帧插值）══════════════════════════════════════
def march(ph, stride=0.40, lift=0.155, lean=8.0, sway=1.0, heel=15.0, toe=-34.0,
          drop=0.048, bounce=0.020, arm=1.0):
    """一个完整周期（两步）的行军步。ph ∈ [0,1)，0 = **右脚跟着地**。

    和 v2 的 `gait()` 的区别（v2 被评价"像散步 / 像大猩猩"）：

    | 项 | v2 | v3 | 为什么 |
    |---|---|---|---|
    | 周期 | 32 帧（1.07 s） | 26 帧（0.87 s） | 4 km/h 行军 ≈ 140 步/分；1.07 s 是散步 |
    | 步幅 | 0.245 m | 0.40 m | 腿长 0.68 的几何上限是 ~0.42（要有落脚余量） |
    | 抬脚 | 0.145 | 0.155 + 脚尖先抬 | 摆动相脚掌必须离地，不然是拖步 |
    | 骨盆 | 常量 −0.05 | −0.048 ± 0.020（两步一周期） | 支撑中期最高、触地最低 —— 这就是"弹" |
    | 躯干 | 只前倾 | 前倾 + 胸胯反向 ±7° + 肩随步转 | 行军的力量来自躯干扭转，不是腿 |
    | 手臂 | 0.075 | 0.16（配合肘部） | 摆臂幅度决定"有没有在走" |

    支撑脚必须**匀速后移**（引擎按位移推角色，脚才不打滑）。参数化插值做不到这一点，
    所以整个动作走 `make_fn` 逐帧算。
    """
    d = {}
    # 骨盆高度：触地最低，支撑中期最高（一个周期两次起伏）
    d["dz"] = -drop + bounce * (1.0 - math.cos(4.0 * math.pi * ph)) * 0.5
    for side, off in (("r", 0.0), ("l", 0.5)):
        u = (ph + off) % 1.0
        if u < 0.5:                                  # 支撑相：脚在地上，匀速后移
            t = u / 0.5
            y = stride * 0.5 - stride * t
            z = 0.0
            if t < 0.16:                             # 脚跟着地 → 全掌
                pitch = heel * (1.0 - t / 0.16)
            elif t < 0.58:                           # 全掌
                pitch = 0.0
            else:                                    # 蹬地 → 脚尖
                pitch = toe * (t - 0.58) / 0.42
        else:                                        # 摆动相：先抬脚尖再前送
            t = (u - 0.5) / 0.5
            e = t * t * (3.0 - 2.0 * t)
            y = -stride * 0.5 + stride * e
            z = lift * math.sin(math.pi * t) ** 0.75
            pitch = toe * (1.0 - t) ** 2 * (1.0 - 0.25 * t) + heel * (t ** 2.6)
        d["fy_" + side] = 0.015 + y
        d["fz_" + side] = 0.20 + z
        d["fp_" + side] = pitch
        d["fx_" + side] = (0.095 if side == "r" else -0.095) * (1.0 + 0.06 * sway)
        d["fyaw_" + side] = (-5.0 if side == "r" else 5.0)
    c, s = math.cos(2.0 * math.pi * ph), math.sin(2.0 * math.pi * ph)
    d["hy"] = 6.0 * c * sway * arm          # 胯随迈步转
    d["cy"] = -8.0 * c * sway * arm         # 胸反向（行军的关键一条）
    d["cr"] = -2.0 * c * sway * arm
    d["hr"] = 2.4 * s * sway                # 摆动侧骨盆略沉
    d["cp"] = -lean
    d["sp"] = -lean * 0.30
    d["hdp"] = lean * 0.55                  # 头抬起来看前方
    d["hdy"] = 1.4 * c * sway
    return d


# ══ 双手持长杆（长枪）══════════════════════════════════════════════════════
def two_hand_points(P, palm_r, palm_l, pole_r, pole_l, slide=0.0,
                    x_hint=(0.0, 0.0, 1.0), z_dir=(0.0, 0.0, 1.0), front="L"):
    """**两只手各给一个世界点**，枪轴 = 后手→前手，`slide` 让枪从手里往前送。

    这是长枪唯一正确的双手模型：v2 用"前手挂在枪轴 t2 处"，枪一前送前手就被拽出
    够得着的范围（实测掌-轴 0.15 m）。换成两点定轴之后：

      * 枪轴一定穿过两只手掌（构造保证）；
      * 前送靠 `slide`（枪在手里滑），两只手的世界位置可以各自独立设计；
      * 于是"双手掐杆 + 枪往前扎"同时成立，不用去改臂长。

    返回 (轴向量, 前手掌心世界点)。
    """
    pr, pl = Vector(palm_r), Vector(palm_l)
    # 枪尖朝哪只手：`front="L"` = 左手在前（枪轴 = 右手→左手）；
    # `front="R"` = 右手在前（枪轴 = 左手→右手）。武器永远挂在右手上，
    # 所以 "右手在前" 时副手是**后手**（世界点在枪轴负方向）。
    d = (pl - pr) if front == "L" else (pr - pl)
    if d.length < 1e-5:
        d = Vector((0.0, 1.0, 0.0))
    d.normalize()
    x = Vector(x_hint)
    if abs(x.dot(d)) > 0.95:
        x = Vector((1.0, 0.0, 0.0))
    hold(P, "R", pr, d, x, pole_r, slide=slide)
    hand_at(P, "L", pl, d, z_dir, pole_l)
    return d, pl


def shaft_dir(p0, p1):
    """两点定枪轴（从鐏指向枪尖），返回单位向量。"""
    v = Vector(p1) - Vector(p0)
    return v.normalized() if v.length > 1e-6 else Vector((0.0, 0.0, 1.0))

def make_fn(arm, name, end, fn, loc=("hips", "weapon_R", "weapon_L"), scl=(),
            loop=False, post=None):
    """逐帧解析动作：fn(P, i, end) 直接出姿态，不经过参数插值。

    循环动作把 `loop=True` 打开：第 end 帧强制用第 0 帧的姿态，首末逐骨完全相等。
    """
    rig = PL.Rig(arm)
    act = PL.new_action(arm, name)
    W = PL.Writer(rig, loc_bones=loc, scl_bones=scl)
    P0 = None
    for i in range(end + 1):
        if loop and i == end and P0 is not None:
            P = PL.loop_key(P0, PL.Frame(rig))
        else:
            P = PL.Frame(rig)
            fn(P, i, end)
            if i == 0:
                P0 = P
        if _SOLE is not None:
            P.solve_T()
            PL.ground(P, _SOLE)
        P.solve_T()
        if post is not None:
            post(P, None, i)
        W.key(P, i)
    PL.finish_action(act)
    _ACTS[act.name] = act
    print("[act] %-8s %5.2fs  f0..%d  (解析)" % (name, end / float(FPS), end))
    return act

