"""anims_战士.py —— 豺狼人战士的 6 条动作

口径同《精模单位_秘法》§5：
  * 逐帧烘焙（`PL.bake` + smoothstep）；
  * 腿走双骨 IK 到地面，踝高一律 `S.foot_clear(pitch)`；
  * `chest_pitch 正值 = 后仰`，`chest_yaw 正值 = 右肩朝前`；
  * 左手（盾）走 FK：盾跟着躯干走，不做世界点约束；
  * 右手（刀）平时 FK 摆臂，攻击/阵亡用 IK 把**握点**钉到世界点。

动作：
  idle   120f  左右侧身观察：重心左右移，胸 ±13°、头 ±32°，刀随呼吸轻晃
  walk    34f  大跨步 ±0.30（不是小碎步），盾前压、肩反相扭
  attack  46f  前摇抬刀 → 左脚向前踏一步 → 顺势斜劈 → 顿帧 → 收势回原位
  roar   110f  前摇（身体内敛、手臂收、头低）→ 张开（胸后仰、手臂外张、头抬起）
               → **保持 2.0 s**（只给 ±1.2° 颤动）→ 收
  hurt    12f  后仰 + 侧闪（无位移）
  death   84f  中招 → 两次摇晃 → 膝盖失力向后倒 → 刀、盾先后脱手落地
"""
import math

import bpy
from mathutils import Matrix, Vector

import poselib2 as PL
import unit_战士_v3 as U

FPS = 30
S = U.S

WR0 = S.WRI_R.copy()
GRIP0 = U.GRIP.copy()
GRIP_OFF = U.GRIP - S.WRI_R
WL0 = S.WRI_L.copy()

LOC_BONES = ("weapon_R", "shield_L")
SCL_BONES = ()

# 落地的刀 / 盾
_sw_rest = None
_sh_rest = None


def _lay(rest, axis_to, flat=Vector((0, 0, 1))):
    """把物体的主轴转到 axis_to 的旋转矩阵（保持 rest 的其它朝向尽量不变）。"""
    cur = (rest @ Vector((0, 1, 0))).normalized()
    q = cur.rotation_difference(Vector(axis_to).normalized())
    return q.to_matrix() @ rest


# ── 基础 ────────────────────────────────────────────────────────────────────
def pose(rig, dz=0.0, dx=0.0, dy=0.0, **kw):
    P = PL.Frame(rig)
    PL.stance(P, dz=dz, dx=dx, dy=dy, legs=False, **kw)
    return P


def stand(P, r=None, l=None):
    r = r or (S.HIP.x, 0.020, 0.0, 5.0)
    l = l or (-S.HIP.x, 0.020, 0.0, -5.0)
    for side, (x, y, pitch, yaw) in (("R", r), ("L", l)):
        pole = (0.40, 1.0, 0.10) if side == "R" else (-0.40, 1.0, 0.10)
        P.leg(side, Vector((x, y, S.foot_clear(pitch))), pole, pitch, yaw)


def feet(P, r, l):
    for side, v in (("R", r), ("L", l)):
        x, y, pitch, yaw = v[:4]
        lift = v[4] if len(v) > 4 else 0.0
        pole = (0.40, 1.0, 0.10) if side == "R" else (-0.40, 1.0, 0.10)
        P.leg(side, Vector((x, y, S.foot_clear(pitch) + lift)), pole, pitch, yaw)


def arm_fk(P, side, a=0.0, b=0.0, c=0.0, fa=0.0, fb=0.0, hand=(0.0, 0.0, 0.0)):
    P.rot("upperarm_" + side, (1, 0, 0), a)
    P.rot("upperarm_" + side, (0, 1, 0), b)
    P.rot("upperarm_" + side, (0, 0, 1), c)
    P.rot("forearm_" + side, (1, 0, 0), fa)
    P.rot("forearm_" + side, (0, 1, 0), fb)
    if any(hand):
        P.rot("hand_" + side, (1, 0, 0), hand[0])
        P.rot("hand_" + side, (0, 1, 0), hand[1])
        P.rot("hand_" + side, (0, 0, 1), hand[2])


def tail(P, swing=0.0, lift=0.0):
    P.rot("tail_01", (0, 0, 1), swing)
    P.rot("tail_01", (1, 0, 0), lift)
    P.rot("tail_02", (0, 0, 1), swing * 0.85)
    P.rot("tail_02", (1, 0, 0), -lift * 0.6)


def _KD(f, **kw):
    d = dict(f=f, dz=0.0, dx=0.0, dy=0.0,
             hips_yaw=0.0, hips_pitch=0.0, hips_roll=0.0,
             spine_pitch=0.0, spine_yaw=0.0,
             chest_pitch=0.0, chest_yaw=0.0, chest_roll=0.0,
             head_pitch=0.0, head_yaw=0.0, head_roll=0.0,
             ra=0.0, rb=0.0, rc=0.0, rfa=0.0, rfb=0.0, rh=(0.0, 0.0, 0.0),
             la=0.0, lb=0.0, lc=0.0, lfa=0.0, lfb=0.0, lh=(0.0, 0.0, 0.0),
             ik=False, grip=GRIP0.copy(), gp=0.0, gr=0.0, gy=0.0,
             tailx=0.0, tailz=0.0,
             rfoot=(S.HIP.x, 0.020, 0.0, 5.0), lfoot=(-S.HIP.x, 0.020, 0.0, -5.0),
             sw=1.0, shd=1.0, swt=Vector((0.74, -0.50, 0.06)),
             sht=Vector((-0.70, -0.46, 0.07)))
    d.update(kw)
    return f, d


def _emit(rig, W):
    def emit(f, d):
        P = pose(rig, dz=d["dz"], dx=d["dx"], dy=d["dy"],
                 hips_yaw=d["hips_yaw"], hips_pitch=d["hips_pitch"],
                 hips_roll=d["hips_roll"], spine_pitch=d["spine_pitch"],
                 spine_yaw=d["spine_yaw"], chest_pitch=d["chest_pitch"],
                 chest_yaw=d["chest_yaw"], chest_roll=d["chest_roll"],
                 head_pitch=d["head_pitch"], head_yaw=d["head_yaw"],
                 head_roll=d["head_roll"])
        feet(P, d["rfoot"], d["lfoot"])
        # 左臂（盾）永远 FK
        arm_fk(P, "L", d["la"], d["lb"], d["lc"], d["lfa"], d["lfb"], d["lh"])
        if d["ik"]:
            PL.grip_pose(P, "R", d["grip"], GRIP_OFF, d["gp"], d["gr"], d["gy"],
                         pole=(0.62, -0.42, -0.66))
        else:
            arm_fk(P, "R", d["ra"], d["rb"], d["rc"], d["rfa"], d["rfb"], d["rh"])
        tail(P, d["tailx"], d["tailz"])
        if d["sw"] < 1.0:
            PL.drop_to(P, "weapon_R", d["swt"], _sw_drop(rig), d["sw"])
        if d["shd"] < 1.0:
            PL.drop_to(P, "shield_L", d["sht"], _sh_drop(rig), d["shd"])
        W.key(P, f)
    return emit


_SW_M = [None]
_SH_M = [None]


def _sw_drop(rig):
    if _SW_M[0] is None:
        _SW_M[0] = _lay(rig.rest["weapon_R"][1], (0.10, -0.99, 0.0)) if hasattr(rig, "rest") \
            else None
    return _SW_M[0]


def _sh_drop(rig):
    if _SH_M[0] is None:
        _SH_M[0] = None
    return _SH_M[0]


# ── 1. idle：左右侧身观察 ───────────────────────────────────────────────────
def a_idle(rig, D=120):
    act = PL.new_action(rig.arm, "idle")
    W = PL.Writer(rig, loc_bones=LOC_BONES, scl_bones=SCL_BONES)
    keys = [
        _KD(0,   dz=-0.006, dy=0.004, chest_pitch=-2.0, head_pitch=1.0,
            ra=-2.0, rfa=6.0, la=0.0, lfa=4.0, tailx=2, tailz=-2),
        # 侧身看左：胸 -13°、头 -32°
        _KD(16,  dz=-0.012, dx=-0.016, hips_yaw=-5.0, chest_yaw=-13.0, chest_roll=-3.0,
            head_yaw=-30.0, head_pitch=-2.0, head_roll=-3.0,
            ra=-6.0, rb=-3.0, rfa=10.0, la=-4.0, lfa=8.0, tailx=14, tailz=-3),
        _KD(28,  dz=-0.014, dx=-0.018, hips_yaw=-5.0, chest_yaw=-13.0, chest_roll=-3.0,
            head_yaw=-34.0, head_pitch=-1.0, head_roll=-3.0,
            ra=-7.0, rb=-3.0, rfa=11.0, la=-5.0, lfa=9.0, tailx=16, tailz=-3),
        _KD(42,  dz=-0.008, dx=0.004, hips_yaw=-1.0, chest_yaw=-3.0,
            head_yaw=-8.0, ra=-3.0, rfa=7.0, la=-1.0, lfa=5.0, tailx=4, tailz=-2),
        # 侧身看右：胸 +14°、头 +30°
        _KD(58,  dz=-0.012, dx=0.018, hips_yaw=5.0, chest_yaw=14.0, chest_roll=3.0,
            head_yaw=28.0, head_pitch=-2.0, head_roll=3.0,
            ra=-1.0, rb=2.0, rfa=5.0, la=4.0, lfb=-2.0, tailx=-12, tailz=-2),
        _KD(72,  dz=-0.015, dx=0.020, hips_yaw=5.0, chest_yaw=15.0, chest_roll=3.0,
            head_yaw=32.0, head_pitch=-1.0, head_roll=3.0,
            ra=0.0, rb=2.0, rfa=4.0, la=5.0, lfb=-2.0, tailx=-15, tailz=-2),
        _KD(88,  dz=-0.008, dy=0.002, chest_pitch=-2.0, head_yaw=6.0,
            ra=-2.0, rfa=6.0, la=1.0, lfa=4.0, tailx=-4, tailz=-2),
        # 低吼一口：胸一压、头一低（呼吸高点）
        _KD(102, dz=-0.018, dy=0.006, chest_pitch=-4.0, head_pitch=4.0,
            ra=-1.0, rfa=8.0, la=-1.0, lfa=5.0, tailx=2, tailz=-1),
        _KD(120, dz=-0.006, dy=0.004, chest_pitch=-2.0, head_pitch=1.0,
            ra=-2.0, rfa=6.0, la=0.0, lfa=4.0, tailx=2, tailz=-2),
    ]
    PL.bake(keys, D, _emit(rig, W))
    PL.finish_action(act)
    return act


# ── 2. walk：34f，步幅 ±0.30 ────────────────────────────────────────────────
SP = 0.30
SUP = 0.58


def a_walk(rig, D=34):
    act = PL.new_action(rig.arm, "walk")
    W = PL.Writer(rig, loc_bones=LOC_BONES, scl_bones=SCL_BONES)

    def leg_y(ph):
        if ph < SUP:
            return SP - 2.0 * SP * (ph / SUP)
        u = (ph - SUP) / (1.0 - SUP)
        return -SP + 2.0 * SP * (u * u * (3.0 - 2.0 * u))

    def leg_lift(ph):
        if ph < SUP:
            return 0.0
        u = (ph - SUP) / (1.0 - SUP)
        return 0.165 * math.sin(math.pi * u) ** 0.80

    def foot_pitch(ph):
        if ph < SUP:
            u = ph / SUP
            if u < 0.35:
                k = u / 0.35
                return 9.0 * (1.0 - k * k * (3.0 - 2.0 * k))
            k = (u - 0.35) / 0.65
            return -13.0 * (k * k * (3.0 - 2.0 * k))
        u = (ph - SUP) / (1.0 - SUP)
        if u < 0.5:
            k = u / 0.5
            return -13.0 + 26.0 * (k * k * (3.0 - 2.0 * k))
        k = (u - 0.5) / 0.5
        return 13.0 - 4.0 * (k * k * (3.0 - 2.0 * k))

    for i in range(D + 1):
        t = i / D
        a2 = 2.0 * math.pi * t
        cy = math.cos(a2)
        sink = 0.0
        for c in (0, D // 2):
            k = i - c
            if 0 <= k <= 3:
                sink -= 0.020 * math.sin(math.pi * k / 3.0)
        P = pose(rig, dz=-0.026 - 0.024 * math.cos(2.0 * a2) + sink,
                 dx=0.038 * math.sin(a2),
                 hips_yaw=8.0 * cy, hips_roll=-5.0 * cy,
                 chest_yaw=-9.0 * cy, chest_roll=2.0 * cy,
                 chest_pitch=-3.0 - 1.4 * math.cos(2.0 * a2),
                 spine_pitch=-1.4, head_pitch=1.6 * math.cos(2.0 * a2),
                 head_yaw=3.0 * cy)
        for side, s, ph in (("R", 1, t), ("L", -1, (t + 0.5) % 1.0)):
            fp = foot_pitch(ph)
            A = Vector((s * S.HIP.x, 0.020 + leg_y(ph), S.foot_clear(fp) + leg_lift(ph)))
            P.leg(side, A, (s * 0.34, 1.0, 0.12), fp, s * 6.0)
        # 右臂：握刀随步伐前后摆（幅度压小，别甩到脸上）
        arm_fk(P, "R", a=-9.0 * cy, b=-4.0, c=0.0, fa=8.0 + 4.0 * cy)
        # 左臂（盾）：反向小摆，盾面始终朝前
        arm_fk(P, "L", a=5.0 * cy, b=2.0, c=-2.0, fa=6.0, fb=-2.0)
        tail(P, -10.0 * cy, 4.0 * math.cos(2.0 * a2))
        W.key(P, i)
    PL.finish_action(act)
    return act


# ── 3. attack：46f，踏一步 + 斜劈 ───────────────────────────────────────────
def a_attack(rig, D=46):
    act = PL.new_action(rig.arm, "attack")
    W = PL.Writer(rig, loc_bones=LOC_BONES, scl_bones=SCL_BONES)
    keys = [
        _KD(0, dz=-0.006, chest_pitch=-2.0, ra=-2.0, rfa=6.0, la=0.0, lfa=4.0),
        # 前摇：重心后坐、右肩后拉、刀抬到右后上方
        _KD(9, dz=-0.048, dy=-0.040, dx=0.010, hips_yaw=-8.0, chest_yaw=-19.0,
            chest_pitch=4.0, head_yaw=10.0, head_pitch=-3.0,
            ik=True, grip=Vector((0.470, 0.020, 1.520)), gp=44.0, gr=-16.0, gy=-10.0,
            la=-6.0, lb=4.0, lfa=10.0, tailx=12,
            rfoot=(S.HIP.x + 0.010, -0.060, -4.0, 8.0),
            lfoot=(-S.HIP.x - 0.010, 0.045, 2.0, -8.0)),
        # 起步：左脚向前踏出
        _KD(15, dz=-0.038, dy=0.070, hips_yaw=4.0, chest_yaw=-6.0, chest_pitch=0.0,
            head_yaw=2.0, head_pitch=-1.0,
            ik=True, grip=Vector((0.430, 0.230, 1.700)), gp=10.0, gr=-10.0, gy=-6.0,
            la=-2.0, lb=2.0, lfa=8.0, tailx=4,
            rfoot=(S.HIP.x + 0.020, 0.060, 2.0, 9.0),
            lfoot=(-S.HIP.x - 0.020, 0.300, 6.0, -6.0)),
        # 命中 f21：斜劈到底，刀尖落到身前下方
        _KD(21, dz=-0.070, dy=0.130, hips_yaw=14.0, chest_yaw=16.0, chest_pitch=-14.0,
            spine_pitch=-3.0, head_yaw=-6.0, head_pitch=6.0,
            ik=True, grip=Vector((0.250, 0.520, 1.020)), gp=-116.0, gr=-18.0, gy=6.0,
            la=6.0, lb=-3.0, lfa=12.0, tailx=-10,
            rfoot=(S.HIP.x + 0.030, 0.130, 6.0, 10.0),
            lfoot=(-S.HIP.x - 0.020, 0.330, 4.0, -8.0)),
        # 顿帧
        _KD(26, dz=-0.072, dy=0.132, hips_yaw=14.0, chest_yaw=15.0, chest_pitch=-15.0,
            spine_pitch=-3.0, head_yaw=-6.0, head_pitch=7.0,
            ik=True, grip=Vector((0.248, 0.525, 1.008)), gp=-118.0, gr=-18.0, gy=6.0,
            la=6.0, lb=-3.0, lfa=12.0, tailx=-8,
            rfoot=(S.HIP.x + 0.030, 0.130, 6.0, 10.0),
            lfoot=(-S.HIP.x - 0.020, 0.330, 4.0, -8.0)),
        # 收势：刀回到体侧，脚跟回原位
        _KD(36, dz=-0.030, dy=0.040, hips_yaw=4.0, chest_yaw=-2.0, chest_pitch=-3.0,
            head_yaw=-2.0, ik=True, grip=Vector((0.440, 0.230, 1.180)),
            gp=-30.0, gr=-4.0, gy=-2.0, la=0.0, lfa=6.0, tailx=0,
            rfoot=(S.HIP.x + 0.010, 0.050, 0.0, 7.0),
            lfoot=(-S.HIP.x - 0.010, 0.120, 0.0, -6.0)),
        _KD(46, dz=-0.006, chest_pitch=-2.0, ra=-2.0, rfa=6.0, la=0.0, lfa=4.0,
            rfoot=(S.HIP.x, 0.020, 0.0, 5.0), lfoot=(-S.HIP.x, 0.020, 0.0, -5.0)),
    ]
    PL.bake(keys, D, _emit(rig, W))
    PL.finish_action(act)
    return act


# ── 4. roar：110f，前摇 → 张开 → 保持 2 s ───────────────────────────────────
def a_roar(rig, D=110):
    act = PL.new_action(rig.arm, "roar")
    W = PL.Writer(rig, loc_bones=LOC_BONES, scl_bones=SCL_BONES)
    keys = [
        _KD(0, dz=-0.006, chest_pitch=-2.0, ra=-2.0, rfa=6.0, la=0.0, lfa=4.0),
        # 前摇：整个人缩起来，肩内扣、头压低、刀收在身前
        _KD(18, dz=-0.090, dy=-0.030, hips_pitch=-3.0, chest_pitch=-13.0, chest_yaw=-6.0,
            chest_roll=3.0, head_pitch=15.0, head_yaw=4.0,
            ra=-14.0, rb=-16.0, rc=-8.0, rfa=34.0, la=-10.0, lb=14.0, lfa=26.0,
            tailx=16, tailz=-6),
        # 爆发：胸后仰、双臂外张、头抬起（吼）
        _KD(32, dz=0.010, dy=0.024, hips_pitch=2.0, chest_pitch=14.0, chest_yaw=2.0,
            chest_roll=-2.0, head_pitch=-22.0, head_yaw=0.0,
            ra=6.0, rb=-40.0, rc=6.0, rfa=-10.0, la=4.0, lb=24.0, lfa=-6.0,
            tailx=-18, tailz=-8),
        # 保持 2.0 s：只给 ±1.2° 的发力颤动
        _KD(40, dz=0.012, hips_pitch=4.0, chest_pitch=13.6, head_pitch=-21.4,
            ra=5.4, rb=-39.0, rc=5.4, rfa=-9.4, la=3.6, lb=23.4, lfa=-5.4,
            tailx=-16, tailz=4),
        _KD(52, dz=0.016, hips_pitch=2.2, chest_pitch=14.4, head_pitch=-22.4,
            ra=6.6, rb=-40.4, rc=6.6, rfa=-10.4, la=4.4, lb=24.4, lfa=-6.4,
            tailx=-18, tailz=4),
        _KD(64, dz=0.011, hips_pitch=1.8, chest_pitch=13.8, head_pitch=-21.6,
            ra=5.8, rb=-39.4, rc=5.8, rfa=-9.8, la=3.8, lb=23.8, lfa=-5.8,
            tailx=-17, tailz=4),
        _KD(76, dz=0.015, hips_pitch=2.2, chest_pitch=14.2, head_pitch=-22.2,
            ra=6.2, rb=-40.0, rc=6.2, rfa=-10.0, la=4.2, lb=24.0, lfa=-6.2,
            tailx=-18, tailz=4),
        _KD(88, dz=0.010, hips_pitch=1.6, chest_pitch=13.4, head_pitch=-21.0,
            ra=5.4, rb=-38.8, rc=5.4, rfa=-9.2, la=3.6, lb=23.2, lfa=-5.6,
            tailx=-15, tailz=3),
        # 收：肩放下、胸回正
        _KD(98, dz=-0.026, hips_pitch=0.0, chest_pitch=4.0, head_pitch=-6.0,
            ra=2.0, rb=-16.0, rc=4.0, rfa=2.0, la=2.0, lb=12.0, lfa=0.0,
            tailx=-4, tailz=0),
        _KD(110, dz=-0.006, chest_pitch=-2.0, ra=-2.0, rfa=6.0, la=0.0, lfa=4.0),
    ]
    PL.bake(keys, D, _emit(rig, W))
    PL.finish_action(act)
    return act


# ── 5. hurt ─────────────────────────────────────────────────────────────────
def a_hurt(rig, D=12):
    act = PL.new_action(rig.arm, "hurt")
    W = PL.Writer(rig, loc_bones=LOC_BONES, scl_bones=SCL_BONES)
    keys = [
        _KD(0, dz=-0.006, chest_pitch=-2.0, ra=-2.0, rfa=6.0),
        _KD(3, dz=-0.036, dx=-0.024, hips_pitch=5.0, chest_pitch=12.0, chest_roll=-7.0,
            chest_yaw=-8.0, head_pitch=10.0, head_yaw=-6.0, head_roll=-6.0,
            ra=-8.0, rb=4.0, rfa=14.0, la=-6.0, lb=-4.0, lfa=12.0, tailx=14,
            rfoot=(S.HIP.x, 0.020, 0.0, 5.0),
            lfoot=(-S.HIP.x - 0.024, -0.055, -4.0, -10.0)),
        _KD(7, dz=-0.020, dx=-0.010, hips_pitch=2.0, chest_pitch=5.0, chest_roll=-3.0,
            chest_yaw=-3.0, head_pitch=4.0, head_yaw=-2.0,
            ra=-4.0, rb=2.0, rfa=9.0, la=-2.0, lb=-2.0, lfa=7.0, tailx=7,
            lfoot=(-S.HIP.x - 0.010, -0.020, -1.0, -7.0)),
        _KD(12, dz=-0.006, chest_pitch=-2.0, ra=-2.0, rfa=6.0),
    ]
    PL.bake(keys, D, _emit(rig, W))
    PL.finish_action(act)
    return act


# ── 6. death：84f，摇晃 → 后倒 → 刀盾脱手 ───────────────────────────────────
def a_death(rig, D=84):
    act = PL.new_action(rig.arm, "death")
    W = PL.Writer(rig, loc_bones=LOC_BONES, scl_bones=SCL_BONES)
    swM = _lay(rig.rest["weapon_R"][1], (0.18, -0.98, 0.02))
    shM = _lay(rig.rest["shield_L"][1], (0.0, 0.10, 1.0))
    SW_T = Vector((0.760, -0.520, 0.060))
    SH_T = Vector((-0.700, -0.430, 0.070))

    def emit(f, d):
        P = pose(rig, dz=d["dz"], dx=d["dx"], dy=d["dy"],
                 hips_yaw=d["hips_yaw"], hips_pitch=d["hips_pitch"],
                 hips_roll=d["hips_roll"], spine_pitch=d["spine_pitch"],
                 chest_pitch=d["chest_pitch"], chest_yaw=d["chest_yaw"],
                 chest_roll=d["chest_roll"], head_pitch=d["head_pitch"],
                 head_yaw=d["head_yaw"], head_roll=d["head_roll"])
        for side, s in (("R", 1), ("L", -1)):
            P.leg(side, Vector(d["ank" + side]), (s * 0.50, 0.85, 0.45),
                  d["fp" + side], d["fy" + side])
        P.arm("R", d["wR"], (0.55, -0.40, -0.55))
        P.aim("hand_R", d["hR"])
        P.arm("L", d["wL"], (-0.85, -0.35, -0.35))
        P.aim("hand_L", d["hL"])
        P.rot("tail_01", (0, 0, 1), d["tailx"])
        P.rot("tail_01", (1, 0, 0), d["tailz"])
        P.rot("tail_02", (1, 0, 0), d["tailz2"])
        if d["sw"] > 0.0:
            PL.drop_to(P, "weapon_R", d["swt"], swM, d["sw"])
        if d["shd"] > 0.0:
            PL.drop_to(P, "shield_L", d["sht"], shM, d["shd"])
        W.key(P, f)

    def KD(f, **kw):
        d = dict(f=f, dz=0.0, dx=0.0, dy=0.0, hips_yaw=0.0, hips_pitch=0.0, hips_roll=0.0,
                 spine_pitch=0.0, chest_pitch=0.0, chest_yaw=0.0, chest_roll=0.0,
                 head_pitch=0.0, head_yaw=0.0, head_roll=0.0,
                 wR=WR0, wL=WL0, hR=(0.0, 0.10, 1.0), hL=(0.0, 0.28, -0.96),
                 ankR=(S.HIP.x, 0.020, 0.335), ankL=(-S.HIP.x, 0.020, 0.335),
                 fpR=0.0, fpL=0.0, fyR=5.0, fyL=-5.0,
                 tailx=0.0, tailz=0.0, tailz2=0.0, sw=0.0, shd=0.0,
                 swt=SW_T, sht=SH_T)
        d.update(kw)
        return f, d

    keys = [
        KD(0),
        KD(4, dz=-0.030, chest_pitch=7.0, head_pitch=12.0, head_yaw=-5.0,
           wR=WR0 + Vector((0.0, -0.02, 0.01)), tailx=10, ankR=(S.HIP.x, 0.020, 0.335)),
        # 摇晃 1（向左）
        KD(13, dz=-0.070, dx=-0.026, hips_roll=-7.0, chest_pitch=8.0, chest_roll=-7.0,
           head_pitch=14.0, head_yaw=-10.0, head_roll=-9.0,
           wR=Vector((0.430, 0.170, 1.150)), hR=(0.10, 0.20, 0.97),
           wL=Vector((-0.470, 0.140, 1.120)), hL=(-0.30, 0.30, -0.90),
           tailx=16, ankL=(-S.HIP.x - 0.026, -0.030, 0.340), fpL=-4.0, fyL=-10.0),
        # 摇晃 2（向右）
        KD(23, dz=-0.098, dx=0.030, hips_roll=8.0, chest_pitch=5.0, chest_roll=8.0,
           head_pitch=9.0, head_yaw=11.0, head_roll=8.0,
           wR=Vector((0.500, 0.190, 1.020)), hR=(0.20, 0.30, 0.93),
           wL=Vector((-0.420, 0.150, 1.000)), hL=(-0.20, 0.35, -0.91),
           tailx=-14, ankR=(S.HIP.x + 0.030, -0.020, 0.345), fpR=-6.0, fyR=11.0),
        # 膝盖失力
        KD(33, dz=-0.250, dy=-0.040, hips_pitch=-4.0, chest_pitch=3.0, head_pitch=4.0,
           wR=Vector((0.470, 0.220, 0.760)), hR=(0.20, 0.30, 0.93),
           wL=Vector((-0.430, 0.180, 0.760)), hL=(-0.30, 0.30, -0.90),
           tailx=0, ankR=(S.HIP.x + 0.020, 0.010, 0.350), ankL=(-S.HIP.x - 0.020, 0.030, 0.350),
           fpR=-4.0, fyR=9.0, fpL=-4.0, fyL=-9.0),
        # 向后倒（胯翻、刀先脱手）
        KD(43, dz=-0.560, dy=-0.300, hips_pitch=48.0, chest_pitch=-4.0, head_pitch=-8.0,
           wR=Vector((0.640, -0.140, 0.360)), hR=(0.30, 0.60, 0.74),
           wL=Vector((-0.520, -0.100, 0.420)), hL=(-0.30, 0.40, -0.86),
           tailx=4, tailz=-62, tailz2=-18, ankR=(S.HIP.x + 0.020, 0.020, 0.360), ankL=(-S.HIP.x - 0.020, 0.040, 0.360),
           fpR=-10.0, fyR=12.0, fpL=-8.0, fyL=-12.0, sw=0.45,
           swt=Vector((0.740, -0.440, 0.20)), shd=0.85,
           sht=Vector((-0.690, -0.400, 0.150))),
        # 触地
        KD(53, dz=-0.748, dy=-0.560, hips_pitch=86.0, hips_roll=-26.0, chest_pitch=-2.0,
           head_pitch=-14.0, head_yaw=-6.0,
           wR=Vector((0.700, -0.620, 0.130)), hR=(0.60, 0.66, 0.45),
           wL=Vector((-0.360, -0.700, 0.180)), hL=(-0.45, 0.30, -0.84),
           tailx=0, tailz=-92, tailz2=-26,
           ankR=(S.HIP.x + 0.040, 0.060, 0.360), ankL=(-S.HIP.x - 0.030, 0.080, 0.360),
           fpR=24.0, fyR=20.0, fpL=28.0, fyL=-20.0, sw=1.0, shd=1.0,
           sht=Vector((-0.700, -0.430, 0.090))),
        KD(62, dz=-0.772, dy=-0.575, hips_pitch=91.0, hips_roll=-30.0, chest_pitch=-1.0,
           head_pitch=-16.0, head_yaw=-7.0,
           wR=Vector((0.706, -0.628, 0.120)), hR=(0.60, 0.66, 0.45),
           wL=Vector((-0.350, -0.712, 0.175)), hL=(-0.45, 0.30, -0.84),
           tailx=0, tailz=-95, tailz2=-28,
           ankR=(S.HIP.x + 0.045, 0.070, 0.362), ankL=(-S.HIP.x - 0.035, 0.090, 0.362),
           fpR=26.0, fyR=21.0, fpL=30.0, fyL=-21.0, sw=1.0, shd=1.0),
        KD(70, dz=-0.760, dy=-0.570, hips_pitch=90.0, hips_roll=-29.0, chest_pitch=-1.0,
           head_pitch=-15.0, head_yaw=-7.0,
           wR=Vector((0.704, -0.626, 0.122)), hR=(0.60, 0.66, 0.45),
           wL=Vector((-0.352, -0.708, 0.176)), hL=(-0.45, 0.30, -0.84),
           tailx=0, tailz=-95, tailz2=-28,
           ankR=(S.HIP.x + 0.045, 0.070, 0.362), ankL=(-S.HIP.x - 0.035, 0.090, 0.362),
           fpR=26.0, fyR=21.0, fpL=30.0, fyL=-21.0, sw=1.0, shd=1.0),
        KD(84, dz=-0.764, dy=-0.572, hips_pitch=90.0, hips_roll=-29.0, chest_pitch=-1.0,
           head_pitch=-15.0, head_yaw=-7.0,
           wR=Vector((0.704, -0.626, 0.122)), hR=(0.60, 0.66, 0.45),
           wL=Vector((-0.352, -0.708, 0.176)), hL=(-0.45, 0.30, -0.84),
           tailx=0, tailz=-95, tailz2=-28,
           ankR=(S.HIP.x + 0.045, 0.070, 0.362), ankL=(-S.HIP.x - 0.035, 0.090, 0.362),
           fpR=26.0, fyR=21.0, fpL=30.0, fyL=-21.0, sw=1.0, shd=1.0),
    ]
    PL.bake(keys, D, emit)
    PL.finish_action(act)
    return act


def build_all(arm, only=None):
    rig = PL.Rig(arm)
    table = [("idle", a_idle), ("walk", a_walk), ("attack", a_attack),
             ("roar", a_roar), ("hurt", a_hurt), ("death", a_death)]
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
