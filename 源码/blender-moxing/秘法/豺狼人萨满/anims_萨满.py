"""anims_萨满.py —— 豺狼人萨满的 5 条动作（+hurt）

口径同《精模单位_秘法》§5：
  * **逐帧写关键帧**（`_bake` + smoothstep）。
  * `P.arm()` 只改 upperarm / forearm，**必须补 hand 的朝向**；这里右手是"握杖"，
    所以用 `hand_rot()` 直接把手的**世界朝向**定死（杖身跟着手走，拳头才不会拧）。
  * `chest_pitch / hips_pitch` **正值 = 后仰**。
  * 脚有 pitch 时踝高必须走 `U.foot_clear(pitch)`，否则爪尖穿地。

巫杖的坐标约定（见 unit_萨满.py）：
  * `weapon_R` 的 **+Y 局部 = 杖顶方向**；`P.LOC["weapon_R"] = (0, d, 0)` 就是沿杖轴滑 d。
  * 手的世界朝向决定杖的朝向：`hand_rot(pitch=…, roll=…, yaw=…)` 是在**静止姿态**上叠一个
    世界旋转，所以 pitch=-78 → 杖身指向前方，roll=-90 → 杖身横过来指向左边。
  * `fx_ball` 是宝珠自己的骨（杖顶）：`P.LOC["fx_ball"] = (0, d, 0)` 让它沿杖轴飞出去。
  * `fx_arc` 是电弧骨：静止 scale=1（网格按 1/40 建，只有一粒灰），放大到 8~40 才是电流。

动作：
  idle   140f  电流把巫杖微微托起，三次脉冲里宝珠亮、电弧盘旋，头左右瞄
  walk    36f  大跨步（±0.22），支撑相匀速后移不打滑，杖随右手小幅前后
  attack  42f  杖顶放出一颗电球：前摇收杖下沉 → f18 向前刺出、宝珠飞 1.55 m → 收回
  cast    72f  巫杖**向右上斜举**（v3）：杖顶甩到右上、杖尾垂到左前下，
               杖身全程在身体右侧（离吻部 ≥0.16 m），双手一高一低握杖
  hurt    11f  后仰 + 侧闪（无位移）
  death   88f  中杖抽搐 → 左右摇晃两次 → 膝盖失力、向后倒地 → 巫杖脱手落地
"""
import math

import bpy
from mathutils import Matrix, Vector

import poselib2 as PL
import unit_萨满 as U

FPS = 30
L_UA, L_FA = U.L_UPPER, U.L_FORE
L_TH, L_SH = U.L_THIGH, U.L_SHIN

FOOT_R = U.HCK_R.copy()
FOOT_L = U.HCK_L.copy()
GRIP = U.GRIP.copy()
WRI_R0 = U.WRI_R.copy()
WRI_L0 = U.WRI_L.copy()
HDIR_L = U.HDIR_L.copy()

# 握点到腕的静止偏移（杖一挪，腕靠这个反推）
GRIP_OFF = U.GRIP - U.WRI_R

LOC_BONES = ("weapon_R", "fx_ball")
SCL_BONES = ("fx_arc", "fx_ball")


# ── 基础 ────────────────────────────────────────────────────────────────────
def pose(rig, dz=0.0, dx=0.0, dy=0.0, **kw):
    P = PL.Frame(rig)
    PL.stance(P, dz=dz, dx=dx, dy=dy, legs=False, **kw)
    return P


def stand(P, r=None, l=None):
    """r/l = (x, y, pitch, yaw)；不给就是静止站姿。"""
    r = r or (U.LEG_X, 0.015, 0.0, 4.0)
    l = l or (-U.LEG_X, 0.015, 0.0, -4.0)
    for side, (x, y, pitch, yaw) in (("R", r), ("L", l)):
        pole = (0.35, 1.0, 0.10) if side == "R" else (-0.35, 1.0, 0.10)
        P.leg(side, Vector((x, y, U.foot_clear(pitch))), pole, pitch, yaw)


def feet(P, r, l):
    """r/l = (x, y, pitch, yaw, lift) —— 带抬脚量。"""
    for side, (x, y, pitch, yaw, lift) in (("R", r), ("L", l)):
        pole = (0.35, 1.0, 0.10) if side == "R" else (-0.35, 1.0, 0.10)
        P.leg(side, Vector((x, y, U.foot_clear(pitch) + lift)), pole, pitch, yaw)


def hand_rot(P, side, pitch=0.0, roll=0.0, yaw=0.0):
    """把手的**世界朝向**定在"静止姿态 + 一个世界旋转"上（杖身跟着它走）。"""
    rest = P.rig.rest["hand_" + side][1]
    M = (Matrix.Rotation(math.radians(yaw), 3, "Z")
         @ Matrix.Rotation(math.radians(pitch), 3, "X")
         @ Matrix.Rotation(math.radians(roll), 3, "Y"))
    P.set_world("hand_" + side, M @ rest)
    return M


def grip_pose(P, target, pitch=0.0, roll=0.0, yaw=0.0, pole=(0.55, -0.55, -0.75)):
    """把手心（=杖握点）放到世界点 target 上，同时把杖转到 (pitch, roll, yaw)。

    腕位置 = target − M·(握点−腕) —— 先定手的世界朝向，再解两骨 IK。
    """
    M = hand_rot(P, "R", pitch, roll, yaw)
    wrist = Vector(target) - (M @ GRIP_OFF)
    P.arm("R", wrist, pole)
    return wrist


def hand_aim(P, side, direction, pole):
    """左手：腕朝目标方向（不握杖，只做姿态）。"""
    P.aim("hand_" + side, direction)


def arm_to(P, side, wrist, pole):
    P.arm(side, Vector(wrist), pole)


def tail(P, swing=0.0, lift=0.0):
    P.rot("tail_01", (0, 0, 1), swing)
    P.rot("tail_01", (1, 0, 0), lift)
    P.rot("tail_02", (0, 0, 1), swing * 0.85)
    P.rot("tail_02", (1, 0, 0), -lift * 0.6)


def _arc(P, scale, spin=0.0, ball=1.0):
    P.SCL["fx_arc"] = scale
    P.SCL["fx_ball"] = ball
    if abs(spin) > 1e-9:
        P.rot("fx_arc", (0, 0, 1), spin, chain=False)


def _mix(a, b, u):
    if isinstance(a, (tuple, list)):
        return tuple(_mix(x, y, u) for x, y in zip(a, b))
    if isinstance(a, Vector):
        return Vector(a).lerp(Vector(b), u)
    return a + (b - a) * u


def _bake(keys, D, emit):
    """keys = [(frame, 参数字典)] —— 段内 smoothstep，**逐帧**回调。"""
    keys = sorted(keys, key=lambda kv: kv[0])
    for i in range(D + 1):
        j = 0
        while j + 1 < len(keys) and keys[j + 1][0] <= i:
            j += 1
        f0, a = keys[j]
        f1, b = keys[min(j + 1, len(keys) - 1)]
        u = 0.0 if f1 == f0 else (i - f0) / float(f1 - f0)
        u = max(0.0, min(1.0, u))
        u = u * u * (3.0 - 2.0 * u)
        emit(i, {k: _mix(a[k], b[k], u) for k in a})


def _KD(f, **kw):
    d = dict(f=f, dz=0.0, dx=0.0, dy=0.0, hips_yaw=0.0, hips_pitch=0.0, hips_roll=0.0,
             spine_pitch=0.0, chest_pitch=0.0, chest_yaw=0.0, chest_roll=0.0,
             head_pitch=0.0, head_yaw=0.0, head_roll=0.0,
             grip=GRIP.copy(), gp=0.0, gr=0.0, gy=0.0,
             lw=WRI_L0.copy(), ld=(0, 0.26, -0.96), lpos=-0.50, lgrip=1.0,
             lift=0.0, arc=1.0, spin=0.0, ball=1.0, tailx=0.0, tailz=0.0,
             rfoot=(U.LEG_X, 0.015, 0.0, 4.0), lfoot=(-U.LEG_X, 0.015, 0.0, -4.0))
    d.update(kw)
    return f, d


def _emit_of(rig, W):
    def emit(f, d):
        P = pose(rig, dz=d["dz"], dx=d["dx"], dy=d["dy"],
                 hips_yaw=d["hips_yaw"], hips_pitch=d["hips_pitch"],
                 hips_roll=d["hips_roll"], spine_pitch=d["spine_pitch"],
                 chest_pitch=d["chest_pitch"], chest_yaw=d["chest_yaw"],
                 chest_roll=d["chest_roll"], head_pitch=d["head_pitch"],
                 head_yaw=d["head_yaw"], head_roll=d["head_roll"])
        stand(P, d["rfoot"], d["lfoot"])
        grip_pose(P, d["grip"], d["gp"], d["gr"], d["gy"])
        arm_to(P, "L", d["lw"], (-0.9, -0.35, -0.30))
        hand_aim(P, "L", d["ld"], (-0.9, -0.35, -0.30))
        tail(P, d["tailx"], d["tailz"])
        P.LOC["weapon_R"] = Vector((0, d["lift"], 0))
        _arc(P, d["arc"], d["spin"], d["ball"])
        W.key(P, f)
    return emit


# ── 1. idle：电流托起巫杖，三次脉冲 ─────────────────────────────────────────
def a_idle(rig, D=140):
    act = PL.new_action(rig.arm, "idle")
    W = PL.Writer(rig, loc_bones=LOC_BONES, scl_bones=SCL_BONES)
    keys = [
        _KD(0,   dz=-0.004, head_yaw=0.0, grip=GRIP, lift=0.000, arc=1.0, tailx=0),
        _KD(12,  dz=-0.012, head_yaw=-6.0, head_pitch=1.0, chest_yaw=-2.0,
            lift=0.022, arc=8.0, spin=26, ball=1.01, tailx=-6),
        # 脉冲 1：杖整根离地 6.2 cm、电弧炸开
        _KD(30,  dz=-0.018, head_yaw=-19.0, head_pitch=2.5, chest_yaw=-5.0,
            lift=0.062, arc=34.0, spin=140, ball=1.07, tailx=-13),
        _KD(44,  dz=-0.008, head_yaw=-12.0, head_pitch=0.5, chest_yaw=-3.5,
            lift=0.030, arc=10.0, spin=205, ball=1.02, tailx=-8),
        # 脉冲 2：最高 7.5 cm
        _KD(60,  dz=-0.020, head_yaw=3.0, head_pitch=-1.5, chest_yaw=1.0,
            lift=0.075, arc=40.0, spin=330, ball=1.10, tailx=2),
        _KD(74,  dz=-0.010, head_yaw=11.0, head_pitch=0.5, chest_yaw=3.0,
            lift=0.034, arc=12.0, spin=400, ball=1.02, tailx=9),
        # 脉冲 3
        _KD(92,  dz=-0.019, head_yaw=20.0, head_pitch=2.5, chest_yaw=5.0,
            lift=0.066, arc=36.0, spin=530, ball=1.06, tailx=15),
        _KD(106, dz=-0.007, head_yaw=13.0, head_pitch=0.0, chest_yaw=3.0,
            lift=0.026, arc=10.0, spin=590, ball=1.01, tailx=9),
        _KD(120, dz=-0.011, head_yaw=4.0, head_pitch=1.0, chest_yaw=1.0,
            lift=0.012, arc=7.0, spin=655, ball=1.02, tailx=3),
        _KD(130, dz=-0.005, head_yaw=1.0, lift=0.003, arc=3.0, spin=690, tailx=0),
        _KD(140, dz=-0.004, head_yaw=0.0, grip=GRIP, lift=0.000, arc=1.0, spin=720),
    ]
    _bake(keys, D, _emit_of(rig, W))
    PL.finish_action(act)
    return act


# ── 2. walk：36f 循环，步幅 ±0.22 ───────────────────────────────────────────
SP = 0.22
SUP = 0.58


def a_walk(rig, D=36):
    act = PL.new_action(rig.arm, "walk")
    W = PL.Writer(rig, loc_bones=LOC_BONES, scl_bones=SCL_BONES)

    def leg_y(ph):
        if ph < SUP:                                  # 支撑：匀速后移（不打滑）
            return SP - 2.0 * SP * (ph / SUP)
        u = (ph - SUP) / (1.0 - SUP)                  # 摆动：smoothstep 前摆
        return -SP + 2.0 * SP * (u * u * (3.0 - 2.0 * u))

    def leg_lift(ph):
        if ph < SUP:
            return 0.0
        u = (ph - SUP) / (1.0 - SUP)
        return 0.135 * math.sin(math.pi * u) ** 0.80

    def foot_pitch(ph):
        if ph < SUP:
            u = ph / SUP
            if u < 0.35:
                k = u / 0.35
                return 7.0 * (1.0 - k * k * (3.0 - 2.0 * k))
            k = (u - 0.35) / 0.65
            return -11.0 * (k * k * (3.0 - 2.0 * k))
        u = (ph - SUP) / (1.0 - SUP)
        if u < 0.5:
            k = u / 0.5
            return -11.0 + 22.0 * (k * k * (3.0 - 2.0 * k))
        k = (u - 0.5) / 0.5
        return 11.0 - 4.0 * (k * k * (3.0 - 2.0 * k))

    for i in range(D + 1):
        t = i / D
        a2 = 2.0 * math.pi * t
        cy = math.cos(a2)
        sink = 0.0
        for c in (0, D // 2):
            k = i - c
            if 0 <= k <= 3:
                sink -= 0.016 * math.sin(math.pi * k / 3.0)
        P = pose(rig,
                 dz=-0.022 - 0.020 * math.cos(2.0 * a2) + sink,
                 dx=0.030 * math.sin(a2),
                 hips_yaw=7.0 * cy, hips_roll=-4.0 * cy,
                 chest_yaw=-8.0 * cy, chest_roll=1.6 * cy,
                 chest_pitch=-3.0 - 1.2 * math.cos(2.0 * a2),
                 spine_pitch=-1.4, head_pitch=1.4 * math.cos(2.0 * a2),
                 head_yaw=2.5 * cy)
        for side, s, ph in (("R", 1, t), ("L", -1, (t + 0.5) % 1.0)):
            fp = foot_pitch(ph)
            A = Vector((s * U.LEG_X, 0.015 + leg_y(ph), U.foot_clear(fp) + leg_lift(ph)))
            P.leg(side, A, (s * 0.30, 1.0, 0.12), fp, s * 5.0)
        # 右手握杖：杖保持竖直，只手随身体前后小幅摆（幅度小，不打到自己）
        sw = 0.045 * cy
        grip_pose(P, GRIP + Vector((0.010 * cy, sw, -0.022 - 0.020 * math.cos(2.0 * a2))),
                  0.0, 0.0, -2.0 * cy, pole=(0.55, -0.55, -0.75))
        arm_to(P, "L", WRI_L0 + Vector((-0.012 * cy, -sw * 1.2, -0.022)),
               (-0.9, -0.35, -0.30))
        hand_aim(P, "L", HDIR_L, (-0.9, -0.35, -0.30))
        tail(P, -9.0 * cy, 3.0 * math.cos(2.0 * a2))
        P.LOC["weapon_R"] = Vector((0, 0.006, 0))
        _arc(P, 3.0 + 2.5 * math.sin(4 * math.pi * t), 360.0 * t, 1.0)
        W.key(P, i)
    PL.finish_action(act)
    return act


# ── 3. attack：杖顶放出电球（命中帧 f18）────────────────────────────────────
def a_attack(rig, D=42):
    act = PL.new_action(rig.arm, "attack")
    W = PL.Writer(rig, loc_bones=LOC_BONES, scl_bones=SCL_BONES)

    STAND_R = (U.LEG_X, 0.015, 0.0, 4.0)
    STAND_L = (-U.LEG_X, 0.015, 0.0, -4.0)
    BACK_R = (U.LEG_X + 0.020, -0.075, -6.0, 6.0)
    BACK_L = (-U.LEG_X - 0.010, 0.055, 2.0, -6.0)
    FWD_R = (U.LEG_X + 0.030, 0.145, 4.0, 8.0)
    FWD_L = (-U.LEG_X - 0.020, -0.090, -8.0, -8.0)

    keys = [
        _KD(0, grip=GRIP, lw=WRI_L0, ld=HDIR_L, arc=1.0),
        # 前摇：杖向后收（杖顶甩到身后上方）、身体下沉、左肩后拉
        _KD(9, dz=-0.058, dy=-0.035, hips_yaw=-5.0, chest_yaw=-13.0, chest_pitch=3.0,
            head_yaw=7.0, head_pitch=2.0,
            grip=Vector((0.298, 0.132, 1.232)), gp=54.0, gr=0.0, gy=8.0,
            lw=Vector((-0.336, 0.020, 1.046)), ld=(-0.34, 0.46, -0.55),
            ball=0.90, arc=14.0, spin=40, tailx=10,
            rfoot=BACK_R, lfoot=BACK_L),
        # 启动：髋先转，重心前压
        _KD(13, dz=-0.048, dy=0.050, hips_yaw=6.0, chest_yaw=-4.0, chest_pitch=-4.0,
            head_yaw=3.0, grip=Vector((0.290, 0.330, 1.230)), gp=-24.0, gy=2.0,
            lw=Vector((-0.290, 0.245, 1.150)), ld=(-0.16, 0.94, -0.30),
            ball=0.02, arc=26.0, spin=90, tailx=-6,
            rfoot=FWD_R, lfoot=FWD_L),
        # 命中 f18：杖刺出、宝珠沿杖轴飞出去
        _KD(18, dz=-0.040, dy=0.115, hips_yaw=10.0, chest_yaw=14.0, chest_pitch=-7.0,
            spine_pitch=-2.5, head_yaw=-4.0, head_pitch=-1.0,
            grip=Vector((0.292, 0.556, 1.222)), gp=-84.0, gy=-4.0,
            lw=Vector((-0.258, 0.610, 1.118)), ld=(-0.08, 0.99, 0.06),
            ball=1.00, arc=34.0, spin=220, lift=0.0, tailx=-12,
            rfoot=FWD_R, lfoot=FWD_L),
        # 顿帧：宝珠停在 1.55 m 处
        _KD(23, dz=-0.044, dy=0.118, hips_yaw=10.0, chest_yaw=13.0, chest_pitch=-6.0,
            spine_pitch=-2.0, head_yaw=-4.0,
            grip=Vector((0.292, 0.556, 1.218)), gp=-84.0, gy=-4.0,
            lw=Vector((-0.258, 0.612, 1.114)), ld=(-0.08, 0.99, 0.06),
            ball=1.06, arc=22.0, spin=300, tailx=-10,
            rfoot=FWD_R, lfoot=FWD_L),
        # 收势
        _KD(32, dz=-0.030, dy=0.020, hips_yaw=4.0, chest_yaw=-4.0, chest_pitch=-1.0,
            head_yaw=-2.0, grip=Vector((0.318, 0.330, 1.190)), gp=-18.0,
            lw=Vector((-0.330, 0.230, 1.040)), ld=(-0.4, 0.6, -0.6),
            ball=0.60, arc=8.0, spin=340, tailx=-4),
        _KD(42, grip=GRIP, lw=WRI_L0, ld=HDIR_L, arc=1.0, ball=1.0, spin=360),
    ]

    # 宝珠的飞行距离按"命中/顿帧"分档插值：0 → 1.55 → 收回
    flight = {0: 0.0, 9: 0.0, 13: 0.16, 18: 1.20, 23: 1.20, 32: 0.22, 42: 0.0}
    fs = sorted(flight)
    for _, k in keys:
        k["fly"] = flight[k["f"]]

    def emit(f, d):
        P = pose(rig, dz=d["dz"], dx=d["dx"], dy=d["dy"],
                 hips_yaw=d["hips_yaw"], hips_pitch=d["hips_pitch"],
                 spine_pitch=d["spine_pitch"], chest_pitch=d["chest_pitch"],
                 chest_yaw=d["chest_yaw"], chest_roll=d["chest_roll"],
                 head_pitch=d["head_pitch"], head_yaw=d["head_yaw"])
        stand(P, d["rfoot"], d["lfoot"])
        grip_pose(P, d["grip"], d["gp"], d["gr"], d["gy"])
        arm_to(P, "L", d["lw"], (-0.85, -0.30, -0.35))
        hand_aim(P, "L", d["ld"], (-0.85, -0.30, -0.35))
        tail(P, d["tailx"], d["tailz"])
        P.LOC["weapon_R"] = Vector((0, d["lift"], 0))
        P.LOC["fx_ball"] = Vector((0, d["fly"], 0))
        _arc(P, d["arc"], d["spin"], d["ball"])
        W.key(P, f)

    _bake(keys, D, emit)
    PL.finish_action(act)
    return act


# ── 4. cast：巫杖**竖举在身体右侧**，左手前伸引电（v3）─────────────────────
# v2 的病根：杖从右前"横"到左上方，扫过的弧线正好穿过长吻（实测 25 帧与头相交）。
# 几何上的死结：吻尖伸到 y=0.452，而握点只能到 y≈0.42 —— 只要杖身经过脸部高度，
# 就必然切进吻部。所以 v3 不横举了：**握点抬到 x≈0.42（头宽之外）、杖身基本竖直
# 微外倾 12°**，杖顶升到 2.62 m；左手不再抓杖，改成前伸的开爪引电。
# 判据：全帧杖 × 头相交 0、净空 ≥0.10 m。
CAST_HOLD = Vector((0.420, 0.395, 1.900))


def a_cast(rig, D=72):
    act = PL.new_action(rig.arm, "cast")
    W = PL.Writer(rig, loc_bones=("weapon_R", "fx_ball"), scl_bones=("fx_arc", "fx_ball"))

    def emit(f, d):
        P = pose(rig, dz=d["dz"], dx=d["dx"], dy=d["dy"],
                 hips_yaw=d["hips_yaw"], hips_pitch=d["hips_pitch"],
                 spine_pitch=d["spine_pitch"], chest_pitch=d["chest_pitch"],
                 chest_yaw=d["chest_yaw"], chest_roll=d["chest_roll"],
                 head_pitch=d["head_pitch"], head_yaw=d["head_yaw"])
        feet(P, (d["rf"][0], d["rf"][1], d["rf"][2], d["rf"][3], 0.0),
             (d["lf"][0], d["lf"][1], d["lf"][2], d["lf"][3], 0.0))
        grip_pose(P, d["grip"], d["gp"], d["gr"], d["gy"], pole=(0.95, -0.10, -0.45))
        arm_to(P, "L", d["lw"], (-0.92, -0.30, -0.26))
        hand_aim(P, "L", d["ld"], (-0.92, -0.30, -0.26))
        tail(P, d["tailx"], d["tailz"])
        P.LOC["weapon_R"] = Vector((0, d["lift"], 0))
        _arc(P, d["arc"], d["spin"], d["ball"])
        W.key(P, f)

    DEF_R = (U.LEG_X, 0.015, 0.0, 4.0)
    DEF_L = (-U.LEG_X, 0.015, 0.0, -4.0)

    def KC(f, **kw):
        kw.setdefault("rf", DEF_R)
        kw.setdefault("lf", DEF_L)
        return _KD(f, **kw)

    keys = [
        KC(0, grip=GRIP, gp=0.0, gr=0.0, gy=0.0, arc=1.0, lw=WRI_L0, ld=HDIR_L),
        # 下沉蓄势：杖竖着压在身体右侧（x 0.33，头宽之外），左手抬到腹前
        KC(10, dz=-0.058, chest_pitch=2.0, head_pitch=3.0, head_yaw=-5.0,
            grip=Vector((0.345, 0.300, 1.040)), gp=2.0, gr=3.0, gy=0.0,
            lw=Vector((-0.392, 0.140, 1.020)), ld=(-0.5, 0.45, -0.74),
            arc=10.0, spin=60, ball=1.02, tailx=8,
            rf=(U.LEG_X + 0.020, 0.055, 0.0, 8.0), lf=(-U.LEG_X - 0.020, 0.055, 0.0, -8.0)),
        # 举到胸口：握点沿身体右侧上移，杖身仍近竖直
        KC(20, dz=-0.020, chest_pitch=0.0, head_pitch=-1.0, head_yaw=-7.0, chest_yaw=3.0,
            grip=Vector((0.390, 0.350, 1.480)), gp=-2.0, gr=7.0, gy=-1.0,
            lw=Vector((-0.372, 0.320, 1.420)), ld=(-0.34, 0.80, -0.49),
            arc=22.0, spin=160, ball=1.06, tailx=4,
            rf=(U.LEG_X + 0.030, 0.045, 0.0, 10.0), lf=(-U.LEG_X - 0.030, 0.045, 0.0, -10.0)),
        # 举到耳高：杖顶开始压向右上
        KC(28, dz=-0.008, chest_pitch=-2.0, spine_pitch=-0.5, head_pitch=-5.0,
            head_yaw=-10.0, chest_yaw=5.0, hips_yaw=2.0,
            grip=Vector((0.412, 0.380, 1.780)), gp=-3.0, gr=10.0, gy=-2.0,
            lw=Vector((-0.372, 0.330, 1.840)), ld=(-0.30, 0.55, 0.78),
            arc=30.0, spin=230, ball=1.10, tailx=2,
            rf=(U.LEG_X + 0.033, 0.055, 0.0, 10.0), lf=(-U.LEG_X - 0.033, 0.055, 0.0, -10.0)),
        # 顶点：杖顶 2.62 m，宝珠在右上；左手开爪前伸引电
        KC(38, dz=0.004, chest_pitch=-4.0, spine_pitch=-1.0, head_pitch=-8.0,
            head_yaw=-13.0, chest_yaw=7.0, hips_yaw=3.0,
            grip=CAST_HOLD, gp=-4.0, gr=12.0, gy=-2.0,
            lw=Vector((-0.360, 0.268, 1.980)), ld=(-0.24, 0.30, 0.92),
            arc=42.0, spin=330, ball=1.22, tailx=-6,
            rf=(U.LEG_X + 0.035, 0.060, 0.0, 10.0), lf=(-U.LEG_X - 0.035, 0.060, 0.0, -10.0)),
        # 电流抖动
        KC(44, dz=0.002, chest_pitch=-3.6, head_pitch=-7.4, head_yaw=-12.0, chest_yaw=6.4,
            hips_yaw=3.0, grip=CAST_HOLD + Vector((0.003, 0.002, 0.003)), gp=-4.0, gr=13.6,
            gy=-2.0, lw=Vector((-0.352, 0.280, 1.992)), ld=(-0.20, 0.26, 0.94),
            arc=31.0, spin=400, ball=1.14,
            rf=(U.LEG_X + 0.035, 0.060, 0.0, 10.0), lf=(-U.LEG_X - 0.035, 0.060, 0.0, -10.0)),
        KC(50, dz=0.006, chest_pitch=-4.4, head_pitch=-8.6, head_yaw=-14.0, chest_yaw=7.6,
            hips_yaw=3.0, grip=CAST_HOLD + Vector((-0.003, -0.002, 0.005)), gp=-3.4, gr=10.4,
            gy=-2.0, lw=Vector((-0.368, 0.258, 1.972)), ld=(-0.28, 0.34, 0.90),
            arc=38.0, spin=470, ball=1.24,
            rf=(U.LEG_X + 0.035, 0.060, 0.0, 10.0), lf=(-U.LEG_X - 0.035, 0.060, 0.0, -10.0)),
        KC(56, dz=0.002, chest_pitch=-3.4, head_pitch=-7.0, head_yaw=-12.0, chest_yaw=6.0,
            hips_yaw=2.0, grip=CAST_HOLD, gp=-4.0, gr=12.0, gy=-2.0,
            lw=Vector((-0.360, 0.266, 1.978)), ld=(-0.24, 0.30, 0.92),
            arc=30.0, spin=520, ball=1.12,
            rf=(U.LEG_X + 0.035, 0.060, 0.0, 10.0), lf=(-U.LEG_X - 0.035, 0.060, 0.0, -10.0)),
        # 落杖：回胸口，再收回体侧
        KC(64, dz=-0.020, chest_pitch=1.0, head_pitch=1.0, head_yaw=-4.0, chest_yaw=2.0,
            grip=Vector((0.380, 0.345, 1.430)), gp=-6.0, gr=8.0, gy=-2.0,
            lw=Vector((-0.388, 0.250, 1.210)), ld=(-0.4, 0.5, -0.76),
            arc=8.0, spin=580, ball=1.0, tailx=2,
            rf=(U.LEG_X + 0.020, 0.045, 0.0, 6.0), lf=(-U.LEG_X - 0.020, 0.045, 0.0, -6.0)),
        KC(72, grip=GRIP, gp=0.0, gr=0.0, gy=0.0, arc=1.0, spin=600, ball=1.0,
           lw=WRI_L0, ld=HDIR_L),
    ]
    _bake(keys, D, emit)
    PL.finish_action(act)
    return act


# ── 6. death：中杖 → 摇晃 → 膝盖失力 → 向后倒地 → 巫杖脱手 ─────────────────
# 倒地姿态用**世界坐标**写（腕/踝都直接给落点），不靠 FK 猜角度：
#   躺下后手腕要落在地面 z≈0.10、脚踝留在原地 z≈0.13，
#   躯干靠 hips_pitch（+95 = 向后躺平）+ dz/dy 把骨盆挪到 (0,-0.50,0.26)。
def a_death(rig, D=88):
    act = PL.new_action(rig.arm, "death")
    W = PL.Writer(rig, loc_bones=("weapon_R", "fx_ball"), scl_bones=("fx_arc", "fx_ball"))

    # 落地的巫杖：杖轴沿 -Y 躺在右手侧（身体倒向 -Y）
    DROP_R = Matrix.Rotation(math.radians(90), 3, "X") @ rig.rest["weapon_R"][1]

    def emit(f, d):
        P = pose(rig, dz=d["dz"], dx=d["dx"], dy=d["dy"],
                 hips_pitch=d["hp"], hips_roll=d["hr"], hips_yaw=d["hy"],
                 spine_pitch=d["sp"], chest_pitch=d["cp"], chest_roll=d["cr"],
                 chest_yaw=d["cy"],
                 head_pitch=d["headp"], head_yaw=d["heady"], head_roll=d["headr"])
        for side, s in (("R", 1), ("L", -1)):
            P.leg(side, Vector(d["ank" + side]), (s * 0.45, 0.80, 0.50),
                  d["fp" + side], d["fy" + side])
        P.arm("R", d["wR"], (0.55, -0.35, -0.60))
        P.aim("hand_R", d["hR"])
        P.arm("L", d["wL"], (-0.85, -0.35, -0.35))
        P.aim("hand_L", d["hL"])
        P.rot("tail_01", (0, 0, 1), d["tailx"])
        P.rot("tail_01", (1, 0, 0), d["tailz"])
        P.rot("tail_02", (1, 0, 0), d["tailz2"])
        _arc(P, d["arc"], d["spin"], d["ball"])
        if d["drop"] > 0.0:
            PL.drop_to(P, "weapon_R", d["wt"], DROP_R, d["drop"])
        W.key(P, f)

    WR0, WL0 = U.WRI_R.copy(), U.WRI_L.copy()

    def KD(f, **kw):
        d = dict(f=f, dz=0.0, dx=0.0, dy=0.0, hp=0.0, hr=0.0, hy=0.0,
                 sp=0.0, cp=0.0, cr=0.0, cy=0.0,
                 headp=0.0, heady=0.0, headr=0.0,
                 wR=WR0, wL=WL0, hR=(0.0, 0.05, 1.0), hL=(0.0, 0.28, -0.96),
                 ankR=(U.LEG_X, 0.015, 0.335), ankL=(-U.LEG_X, 0.015, 0.335),
                 fpR=0.0, fpL=0.0, fyR=4.0, fyL=-4.0,
                 arc=1.0, spin=0.0, ball=1.0, tailx=0.0, tailz=0.0, tailz2=0.0,
                 drop=0.0, wt=Vector((0.72, -0.55, 0.075)))
        d.update(kw)
        return f, d

    keys = [
        KD(0),
        # 中杖：胸口一缩、头猛抬
        KD(4, dz=-0.024, cp=6.0, sp=1.5, headp=11.0, heady=-4.0,
           wR=WR0 + Vector((0.0, -0.02, 0.01)), wL=WL0 + Vector((-0.02, -0.02, 0.02)),
           hL=(-0.35, 0.30, -0.88), arc=6.0, spin=80, ball=0.9, tailx=10),
        # 摇晃 1：向左塌
        KD(13, dz=-0.060, dx=-0.022, hr=-7.0, cp=7.0, cr=-6.0, cy=-5.0,
           headp=13.0, heady=-9.0, headr=-8.0,
           wR=Vector((0.316, 0.230, 1.150)), wL=Vector((-0.430, 0.130, 1.020)),
           hL=(-0.55, 0.20, -0.80), arc=4.0, spin=150, ball=0.75, tailx=16,
           ankL=(-U.LEG_X - 0.020, -0.045, 0.335), fpL=-4.0, fyL=-9.0),
        # 摇晃 2：向右回摆
        KD(22, dz=-0.085, dx=0.028, hr=7.0, cp=4.0, cr=7.0, cy=6.0,
           headp=8.0, heady=9.0, headr=7.0,
           wR=Vector((0.360, 0.250, 1.060)), wL=Vector((-0.372, 0.180, 0.940)),
           hL=(-0.30, 0.35, -0.88), arc=3.0, spin=220, ball=0.6, tailx=-14,
           ankR=(U.LEG_X + 0.030, -0.030, 0.340), fpR=-6.0, fyR=10.0),
        # 膝盖失力：整个人往下坐
        KD(32, dz=-0.245, dy=-0.080, hp=-3.0, hr=1.0, cp=2.0, headp=3.0, heady=3.0,
           wR=Vector((0.420, 0.190, 0.760)), wL=Vector((-0.400, 0.150, 0.640)),
           hR=(0.2, 0.1, 1.0), hL=(-0.3, 0.3, -0.9),
           arc=2.0, spin=290, ball=0.5, tailx=-4, tailz=-4,
           ankR=(U.LEG_X + 0.035, -0.020, 0.340), ankL=(-U.LEG_X - 0.030, 0.005, 0.340),
           fpR=4.0, fyR=12.0, fpL=2.0, fyL=-12.0),
        # 向后倒：胯翻、躯干抡下去，右手往右侧撑
        KD(42, dz=-0.560, dy=-0.380, hp=52.0, hr=8.0, cp=-3.0, headp=-6.0, heady=-2.0,
           wR=Vector((0.560, -0.270, 0.320)), wL=Vector((-0.370, -0.180, 0.480)),
           hR=(0.42, 0.82, 0.28), hL=(-0.35, 0.35, -0.87),
           arc=1.4, spin=340, ball=0.4, tailx=2, tailz=-55,
           ankR=(U.LEG_X + 0.030, -0.010, 0.350), ankL=(-U.LEG_X - 0.025, 0.015, 0.350),
           fpR=10.0, fyR=16.0, fpL=8.0, fyL=-16.0),
        # 触地（肩背落地）
        KD(52, dz=-0.760, dy=-0.600, hp=86.0, hr=24.0, cp=-2.0, headp=-12.0,
           heady=-6.0, headr=-4.0,
           wR=Vector((0.660, -0.640, 0.350)), wL=Vector((-0.330, -0.760, 0.370)),
           hR=(0.55, 0.72, 0.42), hL=(-0.45, 0.30, -0.84),
           arc=1.0, spin=400, ball=0.30, tailx=0, tailz=-88, tailz2=-30,
           ankR=(U.LEG_X + 0.028, -0.020, 0.360), ankL=(-U.LEG_X - 0.022, 0.005, 0.360),
           fpR=22.0, fyR=20.0, fpL=26.0, fyL=-20.0, drop=0.30,
           wt=Vector((0.72, -0.62, 0.14))),
        # 弹一下落定
        KD(60, dz=-0.728, dy=-0.665, hp=93.0, hr=40.0, cp=-1.0, headp=-14.0,
           heady=-7.0, headr=-6.0,
           wR=Vector((0.680, -0.655, 0.340)), wL=Vector((-0.300, -0.800, 0.360)),
           hR=(0.60, 0.70, 0.38), hL=(-0.40, 0.25, -0.88),
           arc=1.0, spin=430, ball=0.2, tailx=0, tailz=-95, tailz2=-45,
           ankR=(U.LEG_X + 0.030, -0.035, 0.365), ankL=(-U.LEG_X - 0.025, -0.010, 0.365),
           fpR=26.0, fyR=22.0, fpL=30.0, fyL=-22.0, drop=1.0),
        KD(70, dz=-0.716, dy=-0.658, hp=91.0, hr=38.0, cp=-1.0, headp=-13.0,
           heady=-7.0, headr=-6.0,
           wR=Vector((0.675, -0.650, 0.108)), wL=Vector((-0.305, -0.782, 0.208)),
           hR=(0.60, 0.70, 0.38), hL=(-0.40, 0.25, -0.88),
           arc=1.0, spin=440, ball=0.18, tailx=0, tailz=-95, tailz2=-45,
           ankR=(U.LEG_X + 0.030, -0.035, 0.365), ankL=(-U.LEG_X - 0.025, -0.010, 0.365),
           fpR=26.0, fyR=22.0, fpL=30.0, fyL=-22.0, drop=1.0),
        KD(88, dz=-0.720, dy=-0.660, hp=91.0, hr=38.0, cp=-1.0, headp=-13.0,
           heady=-7.0, headr=-6.0,
           wR=Vector((0.675, -0.652, 0.108)), wL=Vector((-0.305, -0.784, 0.208)),
           hR=(0.60, 0.70, 0.38), hL=(-0.40, 0.25, -0.88),
           arc=1.0, spin=450, ball=0.16, tailx=0, tailz=-95, tailz2=-45,
           ankR=(U.LEG_X + 0.030, -0.035, 0.365), ankL=(-U.LEG_X - 0.025, -0.010, 0.365),
           fpR=26.0, fyR=22.0, fpL=30.0, fyL=-22.0, drop=1.0),
    ]
    _bake(keys, D, emit)
    PL.finish_action(act)
    return act


# ── 5. hurt：后仰 + 侧闪（无位移）────────────────────────────────────────────
def a_hurt(rig, D=11):
    act = PL.new_action(rig.arm, "hurt")
    W = PL.Writer(rig, loc_bones=LOC_BONES, scl_bones=SCL_BONES)
    keys = [
        _KD(0, grip=GRIP),
        _KD(3, dz=-0.026, dx=-0.020, hips_pitch=4.0, chest_pitch=10.0, chest_roll=-6.0,
            chest_yaw=-7.0, head_pitch=9.0, head_yaw=-5.0, head_roll=-5.0,
            grip=GRIP + Vector((-0.030, -0.045, -0.010)), gp=12.0, gy=-8.0,
            lw=WRI_L0 + Vector((-0.035, -0.030, 0.030)), ld=(-0.4, 0.2, -0.85),
            arc=6.0, spin=60, tailx=12,
            rfoot=(U.LEG_X, 0.015, 0.0, 4.0), lfoot=(-U.LEG_X - 0.020, -0.050, -4.0, -8.0)),
        _KD(7, dz=-0.012, dx=-0.008, hips_pitch=1.6, chest_pitch=4.0, chest_roll=-2.4,
            chest_yaw=-3.0, head_pitch=3.6, head_yaw=-2.0,
            grip=GRIP + Vector((-0.012, -0.018, -0.004)), gp=5.0, gy=-3.0,
            lw=WRI_L0 + Vector((-0.014, -0.012, 0.012)), ld=HDIR_L,
            arc=3.0, spin=180, tailx=6,
            lfoot=(-U.LEG_X - 0.008, -0.020, -1.0, -6.0)),
        _KD(11, grip=GRIP, arc=1.0, spin=360),
    ]
    _bake(keys, D, _emit_of(rig, W))
    PL.finish_action(act)
    return act


def build_all(arm, only=None):
    rig = PL.Rig(arm)
    table = [("idle", a_idle), ("walk", a_walk), ("attack", a_attack),
             ("cast", a_cast), ("hurt", a_hurt), ("death", a_death)]
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
