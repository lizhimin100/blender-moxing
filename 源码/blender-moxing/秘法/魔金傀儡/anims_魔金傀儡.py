"""anims_魔金傀儡.py —— 魔金傀儡的 7 条动作

和破法者共用 `poselib2` 的姿态层；差别：
  * 体型 4.35 m，所有目标点按 U.* 常量算，不写死数字；
  * 纹路脉冲靠 `core / rune_chest / rune_R / rune_L` 四根骨的缩放（发光网格跟着放大），
    这几根骨只挂发光件，缩放它们不会带动甲片。
动作：idle(纹路呼吸+左右打量) / walk(1.33s 重步，步幅 1.0 m) / attack(右拳) /
      attack_alt(左拳) / dash(右肩领先的正面冲撞，原地发力) / hurt / death
"""
import math

import bpy
from mathutils import Vector

import poselib2 as PL
import unit_魔金傀儡 as U

FPS = 30
L_UA, L_FA = U.L_UPPER, U.L_FORE
L_TH, L_SH = U.L_THIGH, U.L_SHIN

REST_R = U.FIST_R.copy()
REST_L = U.FIST_L.copy()
FOOT_R = Vector((U.LEG_X, 0.015, U.Z_ANKLE))
FOOT_L = Vector((-U.LEG_X, 0.015, U.Z_ANKLE))

RUNES = ("core", "rune_chest", "rune_R", "rune_L")


def pose(rig, dz=0.0, dx=0.0, dy=0.0,
         hips_yaw=0.0, hips_pitch=0.0, hips_roll=0.0,
         spine_pitch=0.0, spine_yaw=0.0, spine_roll=0.0,
         chest_pitch=0.0, chest_yaw=0.0, chest_roll=0.0,
         head_pitch=0.0, head_yaw=0.0, head_roll=0.0):
    P = PL.Frame(rig)
    PL.stance(P, dz=dz, dx=dx, dy=dy, hips_yaw=hips_yaw, hips_pitch=hips_pitch,
              hips_roll=hips_roll, spine_pitch=spine_pitch, spine_yaw=spine_yaw,
              spine_roll=spine_roll, chest_pitch=chest_pitch, chest_yaw=chest_yaw,
              chest_roll=chest_roll, head_pitch=head_pitch, head_yaw=head_yaw,
              head_roll=head_roll, legs=False)
    return P


def stand(P, r=FOOT_R, l=FOOT_L, ry=4.0, ly=-4.0):
    P.leg("R", r, (0.35, 1.0, 0.10), 0.0, ry)
    P.leg("L", l, (-0.35, 1.0, 0.10), 0.0, ly)


# 靴底两个最低角相对踝关节的 (dy, dz) —— 脚掌绕踝转 pitch 时要把踝抬多高才不穿地
G_HEEL = (-0.189, -0.300)
G_TOE = (0.339, -0.300)


def foot_clear(pitch_deg):
    a = math.radians(pitch_deg)
    sa, ca = math.sin(a), math.cos(a)
    lo = min(G_HEEL[0] * sa + G_HEEL[1] * ca, G_TOE[0] * sa + G_TOE[1] * ca)
    return max(U.Z_ANKLE, -lo + 0.006)


def _fist(P, side, target, pole, min_r=0.0):
    """把拳心放到世界点 target；腕沿"肩→拳"回退 WRIST_OFF，指节朝该方向。

    `P.arm` 只改 upperarm/forearm，不动 hand；不补这一次 aim，拳头会一直保持
    站立时"垂着"的朝向 —— 挥拳就变成收肘短打、拳路也不成直线。

    min_r：拳心离肩的**最小距离**（按臂长归一）。躯干一转，肩会往前挪 30~40 cm，
    原来算好的世界点就会贴到肩膀上 —— 冲刺护体姿势因此变成"两手糊在胸口"。
    给一个下限，肘角就永远留在能读出来的范围里。
    """
    P.solve_T()
    S = P.T["upperarm_" + side]
    d = Vector(target) - S
    if d.length < 1e-6:
        return
    reach = (L_UA + L_FA) * 0.985 + U.WRIST_OFF
    d = d.normalized() * max(min(d.length, reach), (L_UA + L_FA) * min_r)
    dr = d.normalized()
    P.arm(side, S + d - dr * U.WRIST_OFF, pole)
    P.aim("hand_" + side, dr)


def _legs(P, r, l):
    """r/l = (x, y, foot_pitch, foot_yaw)；踝高按 pitch 自动抬到不穿地。

    硬约束：**R 脚的 x 必须 > 0、L 脚 < 0**。传进来的元组按 (R, L) 排，不是按"前后"排 ——
    v2 的 attack_alt（左拳）就是按"前脚/后脚"排的，s=-1 时左右互换，两只脚在中轴交叉成 X。
    """
    for side, (x, y, pitch, yaw) in (("R", r), ("L", l)):
        if (side == "R") != (x > 0):
            print("[warn _legs] 脚位左右颠倒: %s foot x=%.3f" % (side, x))
        pole = (0.35, 1.0, 0.10) if side == "R" else (-0.35, 1.0, 0.10)
        P.leg(side, Vector((x, y, foot_clear(pitch))), pole, pitch, yaw)


def _mix(a, b, u):
    if isinstance(a, (tuple, list)):
        return tuple(_mix(x, y, u) for x, y in zip(a, b))
    if isinstance(a, Vector):
        return Vector(a).lerp(Vector(b), u)
    return a + (b - a) * u


def _bake(keys, D, emit):
    """keys = [(frame, 参数字典)] —— 段内 smoothstep 插值，**逐帧**回调 emit(f, 参数)。

    必须逐帧写：双骨 IK 只保证"关键帧那一帧"手脚落在目标点；两帧之间插值四元数
    （尤其 Bezier 逐分量插值）会让踝关节飘出去 —— 脚交叉、穿地 5 cm 都是这么来的。
    """
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


def _runes_simple(P, s=0.0):
    """s∈[-1,1] —— 纹路脉动。1 档：核心 1.05、纹条沿轴 +4%。"""
    P.SCL["core"] = 1.0 + 0.05 * s
    P.SCL["rune_chest"] = (1.0, 1.0, 1.0 + 0.05 * s)
    P.SCL["rune_R"] = (1.0, 1.0, 1.0 + 0.04 * s)
    P.SCL["rune_L"] = (1.0, 1.0, 1.0 + 0.04 * s)


# ── 1. idle：纹路呼吸发光 + 头左右打量 ─────────────────────────────────────
def a_idle(rig, D=150):
    act = PL.new_action(rig.arm, "idle")
    W = PL.Writer(rig, scl_bones=RUNES)
    seq = [
        # f,   head_yaw, chest_yaw, dz,    glow
        (0,     0.0,      0.0,     0.000,  0.0),
        (14,   -6.0,     -2.0,     0.010,  0.7),
        (30,  -24.0,     -7.0,     0.006,  1.0),
        (44,  -22.0,     -6.5,     0.006,  0.2),
        (60,   -4.0,     -1.0,     0.012,  0.6),
        (78,   22.0,      6.0,     0.004,  1.0),
        (92,   24.0,      6.5,     0.004, -0.2),
        (108,  6.0,       2.0,     0.010,  0.4),
        (126,  0.0,       0.0,     0.006,  0.9),
        (150,  0.0,       0.0,     0.000,  0.0),
    ]
    for (f, hy, cy, dz, gl) in seq:
        P = pose(rig, dz=dz, hips_yaw=cy * 0.25, chest_yaw=cy, head_yaw=hy,
                 head_pitch=-0.8, chest_pitch=-0.5 - 0.4 * gl)
        stand(P)
        P.arm("R", REST_R + Vector((0, 0, dz * 0.5)), (0.95, -0.35, -0.10))
        P.arm("L", REST_L + Vector((0, 0, dz * 0.5)), (-0.95, -0.35, -0.10))
        _runes_simple(P, gl)
        W.key(P, f)
    PL.finish_action(act)
    return act


# ── 2. walk：1.33 s 循环，重步（步幅 1.0 m，单脚前后各 0.50）────────────────
MG_STEP = 0.50
MG_SUP = 0.55                    # 支撑相占比


def a_walk(rig, D=40):
    act = PL.new_action(rig.arm, "walk")
    W = PL.Writer(rig, scl_bones=RUNES)

    def leg_y(ph):
        if ph < MG_SUP:                        # 支撑：匀速后移（不打滑）
            return MG_STEP - 2.0 * MG_STEP * (ph / MG_SUP)
        u = (ph - MG_SUP) / (1.0 - MG_SUP)     # 摆动：smoothstep 前摆
        return -MG_STEP + 2.0 * MG_STEP * (u * u * (3.0 - 2.0 * u))

    def leg_z(ph):
        if ph < MG_SUP:
            return 0.0
        u = (ph - MG_SUP) / (1.0 - MG_SUP)
        z = 0.260 * math.sin(math.pi * u)
        if u < 0.30:
            z += 0.060 * math.sin(math.pi * u / 0.30)   # 离地那一下收脚
        return z

    def foot_pitch(ph):
        if ph < MG_SUP:
            u = ph / MG_SUP
            if u < 0.42:                       # 脚跟着地 → 踩平
                k = u / 0.42
                return 14.0 * (1.0 - k * k * (3.0 - 2.0 * k))
            k = (u - 0.42) / 0.58              # 踩平 → 脚尖蹬离
            return -13.0 * (k * k * (3.0 - 2.0 * k))
        u = (ph - MG_SUP) / (1.0 - MG_SUP)
        if u < 0.55:
            k = u / 0.55
            return -13.0 + 32.0 * (k * k * (3.0 - 2.0 * k))
        k = (u - 0.55) / 0.45
        return 19.0 - 5.0 * (k * k * (3.0 - 2.0 * k))

    for i in range(D + 1):
        t = i / D
        a2 = 2.0 * math.pi * t
        cy = math.cos(a2)
        # 落地后 2 帧的"沉降"（每步一次：接触帧 f0 / f20）
        sink = 0.0
        for c in (0, D // 2):
            k = i - c
            if 0 <= k <= 4:
                sink -= 0.030 * math.sin(math.pi * k / 4.0)
        chest_pitch = -4.0 + sink * 50.0       # 沉降时再前压 1.5°

        P = pose(rig,
                 dz=-0.0625 - 0.0425 * math.cos(2.0 * a2) + sink,   # 接触帧砸到 -0.105
                 dx=0.055 * math.sin(a2),                          # 重心压向支撑腿
                 hips_yaw=7.0 * cy, hips_roll=-5.5 * cy,
                 chest_yaw=-9.0 * cy, chest_roll=1.9 * cy,          # 与髋反相
                 chest_pitch=chest_pitch, spine_pitch=chest_pitch * 0.4,
                 head_pitch=1.6 * math.cos(2.0 * a2))

        for side, s, ph in (("R", 1, t), ("L", -1, (t + 0.5) % 1.0)):
            fp = foot_pitch(ph)
            A = Vector((s * U.LEG_X, 0.015 + leg_y(ph), foot_clear(fp) + leg_z(ph)))
            P.leg(side, A, (s * 0.30, 1.0, 0.12), fp, s * 4.0)

        # 两拳沿 Y 摆 ±0.16，与同侧腿反相
        sw = 0.16 * cy
        _fist(P, "R", REST_R + Vector((0.010, -sw, 0.010)), (0.95, -0.40, -0.10))
        _fist(P, "L", REST_L + Vector((-0.010, sw, 0.010)), (-0.95, -0.40, -0.10))
        _runes_simple(P, 0.35 * math.sin(4 * math.pi * t))
        W.key(P, i)
    PL.finish_action(act)
    return act


# ── 3/4. attack：右拳 / 左拳（拳路按"当前姿态的肩点"算，直线出拳）──────────
def _punch(rig, name, side, D=40):
    s = 1 if side == "R" else -1
    other = "L" if s > 0 else "R"
    act = PL.new_action(rig.arm, name)
    W = PL.Writer(rig, scl_bones=RUNES)
    rest = REST_R if s > 0 else REST_L
    rest_o = REST_L if s > 0 else REST_R
    POLE = (s * 0.25, -0.30, -1.0)                 # 肘朝下后方
    POLE_O = (-s * 0.25, -0.30, -1.0)
    STAND = ((U.LEG_X, 0.015, 0.0, 4.0), (-U.LEG_X, 0.015, 0.0, -4.0))
    # 上步的脚在"出拳那一侧"。元组顺序是 (R, L)，所以必须按 s 分派，
    # 不能按"前脚/后脚"写死 —— 否则左手拳时两只脚会左右互换、在中轴交叉。
    FRONT = (s * U.LEG_X, 0.160, 0.0, s * 8.0)
    BACK = (-s * U.LEG_X, -0.085, -6.0, -s * 6.0)
    STEPPED = (FRONT, BACK) if s > 0 else (BACK, FRONT)
    FRONT_M = (s * U.LEG_X, 0.160, 0.0, s * 8.0)
    BACK_M = (-s * U.LEG_X, -0.060, -4.0, -s * 6.0)
    MID = (FRONT_M, BACK_M) if s > 0 else (BACK_M, FRONT_M)
    DIR = Vector((s * 0.10, 0.975, 0.06)).normalized()      # 略向内、略向上
    REACH = (L_UA + L_FA) * 0.985

    def KD(f, **kw):
        d = dict(f=f, dz=0.0, dy=0.0, hips_yaw=0.0, chest_yaw=0.0, chest_pitch=0.0,
                 spine_pitch=0.0, head_yaw=0.0, head_pitch=0.0, glow=0.0,
                 fist=rest, back=rest_o, legs=STAND, shoot=0.0, pad=0.0)
        d.update(kw)
        return f, d

    KEYS = [
        KD(0),
        # 蓄力：躯干往出拳的反方向拧（背对目标），重心后坐，拳收到肋侧
        KD(8, dz=-0.070, dy=-0.050, hips_yaw=-s * 8, chest_yaw=-s * 20,
           chest_pitch=2.0, spine_pitch=1.0, head_yaw=s * 12, glow=0.30,
           fist=Vector((s * 0.70, -0.28, U.Z_CHEST - 0.10)),
           back=Vector((-s * 1.00, -0.10, U.Z_CHEST - 0.30))),
        # 启动：髋先转，前脚上步，拳开始走直线
        KD(12, dz=-0.050, dy=0.030, hips_yaw=s * 8, chest_yaw=-s * 8,
           chest_pitch=-3.0, spine_pitch=-1.0, head_yaw=s * 4, glow=0.65,
           fist=Vector((s * 0.52, 0.42, U.Z_CHEST + 0.06)),
           back=Vector((-s * 1.05, -0.20, U.Z_CHEST - 0.25)),
           legs=MID),
        # 命中（42.5%）：胸腔拧进拳里、前倾，另一手肘向后抽
        KD(17, dz=-0.050, dy=0.120, hips_yaw=s * 10, chest_yaw=s * 18,
           chest_pitch=-6.0, spine_pitch=-2.5, head_yaw=-s * 5, head_pitch=1.0,
           glow=1.0, shoot=1.0, legs=STEPPED,
           back=Vector((-s * 1.02, -0.50, U.Z_CHEST - 0.13))),
        # 顿帧：拳再往前 0.015，胸腔回 2°
        KD(21, dz=-0.055, dy=0.115, hips_yaw=s * 10, chest_yaw=s * 16,
           chest_pitch=-4.5, spine_pitch=-2.0, head_yaw=-s * 5, head_pitch=0.8,
           glow=0.85, shoot=1.0, pad=0.015, legs=STEPPED,
           back=Vector((-s * 1.00, -0.46, U.Z_CHEST - 0.15))),
        # 收
        KD(30, dz=-0.045, dy=0.020, hips_yaw=s * 2, chest_yaw=-s * 4,
           chest_pitch=0.5, head_yaw=-s * 2, glow=0.25,
           fist=Vector((s * 0.74, 0.10, U.Z_CHEST - 0.18)),
           back=Vector((-s * 0.96, 0.10, U.Z_CHEST - 0.45))),
        KD(40),
    ]

    def _pose_of(d):
        P = pose(rig, dz=d["dz"], dy=d["dy"], hips_yaw=d["hips_yaw"],
                 hips_pitch=d["chest_pitch"] * 0.35, chest_yaw=d["chest_yaw"],
                 chest_pitch=d["chest_pitch"], spine_pitch=d["spine_pitch"],
                 head_yaw=d["head_yaw"], head_pitch=d["head_pitch"])
        _legs(P, d["legs"][0], d["legs"][1])
        return P

    # 命中/顿帧的拳心 = 当前姿态下的肩点 + DIR * (腕伸到 98.5% 臂长 + 腕到拳心)
    #   —— WRIST_OFF 必须加回来，否则腕只到 77% 臂长，肘弯成"收着打"的钩拳
    for _, k in KEYS:
        if k["shoot"]:
            Q = _pose_of(k)
            Q.solve_T()
            k["fist"] = Q.T["upperarm_" + side] + DIR * (REACH + U.WRIST_OFF + k["pad"])

    def emit(f, d):
        P = _pose_of(d)
        _fist(P, side, d["fist"], POLE)
        _fist(P, other, d["back"], POLE_O)
        _runes_simple(P, d["glow"])
        W.key(P, f)

    _bake(KEYS, D, emit)
    PL.finish_action(act)
    return act


def a_attack(rig, D=40):
    return _punch(rig, "attack", "R", D)


def a_attack_alt(rig, D=40):
    return _punch(rig, "attack_alt", "L", D)


# ── 5. dash：右肩领先的正面冲撞（原地发力，2.6 s）──────────────────────────
def a_dash(rig, D=78):
    act = PL.new_action(rig.arm, "dash")
    W = PL.Writer(rig, scl_bones=RUNES)
    PR = (0.60, -0.25, -1.0)
    PL_ = (-0.60, -0.25, -1.0)
    STAND = ((U.LEG_X, 0.015, 0.0, 4.0), (-U.LEG_X, 0.015, 0.0, -4.0))
    # 冲刺姿态（f20 起保持到 f70）：右拳压胸前当护盾、左拳甩在身后
    RUN_R = Vector((0.10, 0.52, U.Z_CHEST - 0.06))
    RUN_L = Vector((-0.66, -0.34, U.Z_CHEST - 0.30))
    RUN_LEGS = ((0.40, 0.42, 0.0, 8.0), (-0.36, -0.30, -22.0, -8.0))

    def KD(f, **kw):
        d = dict(f=f, dz=0.0, hips_yaw=0.0, hips_pitch=0.0, chest_yaw=0.0,
                 chest_pitch=0.0, spine_pitch=0.0, head_yaw=0.0, head_pitch=0.0,
                 glow=0.0, fistR=REST_R, fistL=REST_L, legs=STAND)
        d.update(kw)
        return f, d

    KEYS = [
        KD(0),
        # 下沉起势：双臂开始抬起、错开
        KD(7, dz=-0.110, hips_pitch=-2.0, chest_pitch=-4.0, spine_pitch=-1.5,
           chest_yaw=4.0, glow=0.35,
           fistR=Vector((0.72, 0.34, U.Z_CHEST + 0.02)),
           fistL=Vector((-0.86, 0.16, U.Z_CHEST - 0.55))),
        # 前摇：右拳护面门、左拳在体侧后方低位（两手错开）
        KD(13, dz=-0.145, hips_pitch=-4.0, hips_yaw=4.0, chest_yaw=10.0,
           chest_pitch=-8.0, spine_pitch=-3.0, head_pitch=3.0, glow=0.55,
           fistR=Vector((0.34, 0.66, U.Z_CHEST + 0.32)),
           fistL=Vector((-0.72, 0.10, U.Z_CHEST - 0.42)),
           legs=((0.375, 0.120, 0.0, 6.0), (-0.370, -0.100, -10.0, -6.0))),
        # 蹬地启动：肩向前挺，右肩领先，前腿跨出、后腿撑直蹬地
        KD(20, dz=-0.120, hips_pitch=-7.0, hips_yaw=8.0, chest_yaw=16.0,
           chest_pitch=-17.0, spine_pitch=-6.0, head_pitch=6.0, glow=0.85,
           fistR=RUN_R, fistL=RUN_L, legs=RUN_LEGS),
    ]
    # f26→f70 保持冲刺姿势：只给发力颤动与纹路呼吸（没有净位移）
    for f in range(26, 71, 4):
        br = math.sin(2.0 * math.pi * 2.0 * (f - 26) / 44.0)
        KEYS.append(KD(f, dz=-0.120 + 0.006 * br, hips_pitch=-7.0, hips_yaw=8.0,
                       chest_yaw=16.0, chest_pitch=-17.0 - 1.2 * br,
                       spine_pitch=-6.0, head_pitch=6.0, glow=0.60 + 0.25 * br,
                       fistR=RUN_R, fistL=RUN_L, legs=RUN_LEGS))
    KEYS += [
        # 收势（方便引擎混合回 idle）
        KD(74, dz=-0.080, hips_pitch=-3.0, hips_yaw=4.0, chest_yaw=8.0,
           chest_pitch=-8.0, spine_pitch=-2.5, head_pitch=3.0, glow=0.40,
           fistR=Vector((0.62, 0.42, U.Z_CHEST - 0.05)),
           fistL=Vector((-0.80, 0.05, U.Z_CHEST - 0.30)),
           legs=((0.372, 0.260, 0.0, 6.0), (-0.366, -0.190, -8.0, -6.0))),
        KD(78),
    ]

    def emit(f, d):
        P = pose(rig, dz=d["dz"], hips_yaw=d["hips_yaw"],
                 hips_pitch=d["hips_pitch"], chest_yaw=d["chest_yaw"],
                 chest_pitch=d["chest_pitch"], spine_pitch=d["spine_pitch"],
                 head_yaw=d["head_yaw"], head_pitch=d["head_pitch"])
        _legs(P, d["legs"][0], d["legs"][1])
        _fist(P, "R", d["fistR"], PR, min_r=0.47)
        _fist(P, "L", d["fistL"], PL_, min_r=0.40)
        _runes_simple(P, d["glow"])
        W.key(P, f)

    _bake(KEYS, D, emit)
    PL.finish_action(act)
    return act


# ── 6. hurt ──────────────────────────────────────────────────────────────
def a_hurt(rig, D=12):
    act = PL.new_action(rig.arm, "hurt")
    W = PL.Writer(rig, scl_bones=RUNES)
    seq = [(0, 0.000, 0.0, 0.0), (3, -0.030, 9.0, -7.0),
           (7, -0.014, 4.0, -3.0), (12, 0.000, 0.0, 0.0)]
    for (f, dz, cp, cy) in seq:
        P = pose(rig, dz=dz, chest_pitch=cp, chest_yaw=cy, head_pitch=cp * 0.8,
                 hips_pitch=cp * 0.3, hips_yaw=cy * 0.3)
        stand(P)
        P.arm("R", REST_R + Vector((0.02, -0.02, dz * 0.4)), (0.95, -0.4, 0.0))
        P.arm("L", REST_L + Vector((-0.02, -0.02, dz * 0.4)), (-0.95, -0.4, 0.0))
        _runes_simple(P, -0.4)
        W.key(P, f)
    PL.finish_action(act)
    return act


# ── 7. death：顿 → 单膝跪 → 上身前扑 → 静止 ────────────────────────────
def a_death(rig, D=54):
    act = PL.new_action(rig.arm, "death")
    W = PL.Writer(rig, scl_bones=RUNES)
    seq = [
        (0,  0.000,  0.0,  0.0,  0.0),
        (5, -0.035, -5.0, -9.0,  5.0),
        (12, -0.110,  9.0, 14.0,  5.0),
        (20, -0.260, 17.0, 26.0,  8.0),
        (28, -0.430, 23.0, 36.0, 11.0),
        (34, -0.520, 26.0, 42.0, 14.0),
        (40, -0.545, 27.0, 44.0, 16.0),
        (54, -0.545, 27.0, 44.0, 16.0),
    ]
    for (f, dz, hip, cp, hp) in seq:
        P = pose(rig, dz=dz, hips_pitch=hip, chest_pitch=cp, head_pitch=hp,
                 head_yaw=-3.0 * (dz / -0.545), chest_yaw=-5.0 * (dz / -0.545))
        q = dz / -0.545
        # 踝高必须按脚的 pitch 算（脚跟会往下掉），否则跪姿里鞋跟会切进地面
        P.leg("R", Vector((U.LEG_X, 0.015 + 0.20 * q,
                           foot_clear(0.0) + 0.02 * q)),
              (0.35, 1.0, 0.10), 0.0, 4.0)
        P.leg("L", Vector((-U.LEG_X, 0.015 - 0.10 * q,
                           foot_clear(16.0 * q) + 0.05 * q)),
              (-0.35, 1.0, 0.10), 16.0 * q, -6.0)
        P.arm("R", REST_R + Vector((0.03, -0.06, dz * 0.45)), (0.95, -0.3, 0.0))
        P.arm("L", REST_L + Vector((-0.03, -0.06, dz * 0.45)), (-0.95, -0.3, 0.0))
        _runes_simple(P, -1.0 * q)
        W.key(P, f)
    PL.finish_action(act)
    return act


def build_all(arm, only=None):
    rig = PL.Rig(arm)
    table = [("idle", a_idle), ("walk", a_walk), ("attack", a_attack),
             ("attack_alt", a_attack_alt), ("dash", a_dash),
             ("hurt", a_hurt), ("death", a_death)]
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
