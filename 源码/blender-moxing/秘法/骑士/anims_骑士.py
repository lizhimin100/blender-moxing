"""anims_骑士.py —— 联盟·骑士的 6 条动作（人马一体）

与破法者/魔金傀儡共用 `poselib2`，多出来的两件事：

1. **四条马腿**：`horse_upper/fore/hoofF`（前）与 `horse_thigh/shin/hoofH`（后）
   都是 3 段链 —— 两段 IK + 蹄骨单独摆平。前腿膝朝前（pole +Y），后腿飞节朝后（pole −Y）；
   这一条写反，马立刻变成狗。
2. **骑手不挂在马骨上**：`rider_root` 的父是 `root`，每帧由 `seat()` 放到鞍点，
   骑手自己的躯干/四肢再叠上去。所以"死亡"里骑手能摔到地上、马继续向前倒，
   一副骨架搞定，不需要两个 GLB 拼。

三条通用规矩（照抄手册）：
  * **逐帧写**关键帧（`_bake`）：双骨 IK 只保证关键帧那一帧落点正确；
  * `P.arm()`/`P.leg()` 只认 `upperarm_R`/`thigh_R` 这套名字，骑手是 `r_upperarm_R`，
    所以这里有 `rarm()` / `rleg()` 两个专用版；
  * `chest_pitch / hips_pitch` **正值 = 后仰，负值 = 前倾**。

动作：idle(120 侧身观察) · walk(36 快步) · attack(45 夹枪突刺) ·
      dash(110 人立前摇 + 冲锋保持) · hurt(12) · death(78 摔马 + 马前扑)
"""
import math

import bpy
from mathutils import Matrix, Vector

import horse_kit as HK
import poselib2 as PL
import unit_骑士 as U

FPS = 30
HOOF_Z = HK.FRONT_FET.z                 # 球节高度 = 蹄骨起点高度
REST_RR = U.SADDLE                      # rider_root 静止骨根 = 鞍点
ANK0 = {1: Vector((U.ANKLE.x, U.ANKLE.y, U.ANKLE.z)),
        -1: Vector((-U.ANKLE.x, U.ANKLE.y, U.ANKLE.z))}

W_BONES = ("rider_root", "weapon_R")


# ── 基础姿态 ────────────────────────────────────────────────────────────────
def pose(rig, dz=0.0, dx=0.0, dy=0.0,
         hips_yaw=0.0, hips_pitch=0.0, hips_roll=0.0,
         spine_pitch=0.0, spine_yaw=0.0, spine_roll=0.0,
         chest_pitch=0.0, chest_yaw=0.0, chest_roll=0.0,
         neck_pitch=0.0, neck_yaw=0.0, head_pitch=0.0, head_yaw=0.0,
         tail_yaw=0.0, tail_pitch=0.0):
    """马的躯干。dz/dx/dy 是整体世界位移（root 的 offset）。"""
    P = PL.Frame(rig)
    P.offset = Vector((dx, dy, dz))
    P.rot("horse_hips", (0, 0, 1), hips_yaw)
    P.rot("horse_hips", (1, 0, 0), hips_pitch)
    P.rot("horse_hips", (0, 1, 0), hips_roll)
    P.rot("horse_spine", (1, 0, 0), spine_pitch)
    P.rot("horse_spine", (0, 0, 1), spine_yaw)
    P.rot("horse_spine", (0, 1, 0), spine_roll)
    P.rot("horse_chest", (1, 0, 0), chest_pitch)
    P.rot("horse_chest", (0, 0, 1), chest_yaw)
    P.rot("horse_chest", (0, 1, 0), chest_roll)
    P.rot("horse_neck", (1, 0, 0), neck_pitch)
    P.rot("horse_neck", (0, 0, 1), neck_yaw)
    P.rot("horse_head", (1, 0, 0), head_pitch - neck_pitch * 0.45)
    P.rot("horse_head", (0, 0, 1), head_yaw - neck_yaw * 0.5)
    P.rot("horse_tail_01", (0, 0, 1), tail_yaw)
    P.rot("horse_tail_01", (1, 0, 0), tail_pitch)
    P.rot("horse_tail_02", (0, 0, 1), tail_yaw * 1.4)
    P.rot("horse_tail_02", (1, 0, 0), tail_pitch * 0.8)
    return P


def hleg(P, pair, side, ankle, pitch=0.0, yaw=0.0):
    """马腿：两段 IK + 蹄骨摆平。pair = "F"(前) / "H"(后)。"""
    up = "horse_upper_" + side if pair == "F" else "horse_thigh_" + side
    lo = "horse_fore_" + side if pair == "F" else "horse_shin_" + side
    hf = ("horse_hoofF_" if pair == "F" else "horse_hoofH_") + side
    P.solve_T()
    root = P.T[up]
    A = Vector(ankle)
    K = PL.ik2(root, A, P.rig.L(up), P.rig.L(lo),
               (0, 1.0 if pair == "F" else -1.0, 0))
    P.aim(up, K - root, chain=False)
    P.aim(lo, A - K, chain=False)
    R = (Matrix.Rotation(math.radians(yaw), 3, "Z")
         @ Matrix.Rotation(math.radians(pitch), 3, "X"))
    P.set_world(hf, R @ P.rig.rest[hf][1], chain=True)


def stand_legs(P, lift=(0, 0, 0, 0), dy=(0, 0, 0, 0), pitch=(0, 0, 0, 0),
               yaw=(4.0, -4.0, 3.0, -3.0), spread=0.0):
    """四蹄站位（世界坐标，绝对）。顺序 FR / FL / HR / HL。"""
    for i, (pair, side, s) in enumerate((("F", "R", 1), ("F", "L", -1),
                                         ("H", "R", 1), ("H", "L", -1))):
        base = HK.FRONT_FET if pair == "F" else HK.HIND_FET
        pa = math.radians(pitch[i])
        A = Vector((s * (base.x + spread), base.y + dy[i],
                    HOOF_Z * math.cos(pa) + 0.098 * abs(math.sin(pa)) + lift[i]))
        hleg(P, pair, side, A, pitch[i], yaw[i])


def rw(P, p):
    """骑手静止世界坐标 → 当前世界坐标（跟着 rider_root 走）。"""
    rr = "rider_root"
    Rd = P.R[rr] @ P.rig.rest[rr][1].inverted()
    return P.T[rr] + Rd @ (Vector(p) - P.rig.rest[rr][0])


def seat(P, dz=0.0, dx=0.0, dy=0.0):
    """把 rider_root 放到当前马背鞍点上。必须在写骑手躯干**之前**调用。"""
    P.solve_T()
    c = "horse_chest"
    rc = P.rig.rest[c]
    rel = rc[1].inverted() @ (REST_RR - rc[0])
    T = P.T[c] + P.R[c] @ rel
    Rr = P.R[c] @ rc[1].inverted() @ P.rig.rest["rider_root"][1]
    P.place("rider_root", T + Vector((dx, dy, dz)), Rr)


def rider_pose(P, hips_pitch=0.0, hips_yaw=0.0, hips_roll=0.0,
               spine_pitch=0.0, spine_yaw=0.0, chest_pitch=0.0, chest_yaw=0.0,
               chest_roll=0.0, head_pitch=0.0, head_yaw=0.0, head_roll=0.0):
    P.rot("r_hips", (1, 0, 0), hips_pitch)
    P.rot("r_hips", (0, 0, 1), hips_yaw)
    P.rot("r_hips", (0, 1, 0), hips_roll)
    P.rot("r_spine", (1, 0, 0), spine_pitch)
    P.rot("r_spine", (0, 0, 1), spine_yaw)
    P.rot("r_chest", (1, 0, 0), chest_pitch)
    P.rot("r_chest", (0, 0, 1), chest_yaw)
    P.rot("r_chest", (0, 1, 0), chest_roll)
    P.rot("r_head", (1, 0, 0), head_pitch)
    P.rot("r_head", (0, 0, 1), head_yaw)
    P.rot("r_head", (0, 1, 0), head_roll)


def rleg(P, side, ankle, pitch=0.0, yaw=0.0, spread=0.0):
    """骑手的腿（骨名带 r_ 前缀）。"""
    s = 1 if side == "R" else -1
    up, lo, ft = "r_thigh_" + side, "r_shin_" + side, "r_foot_" + side
    P.solve_T()
    root = P.T[up]
    A = Vector(ankle)
    K = PL.ik2(root, A, P.rig.L(up), P.rig.L(lo), (s * 0.30, 1.0, 0.10))
    P.aim(up, K - root, chain=False)
    P.aim(lo, A - K, chain=False)
    R = (Matrix.Rotation(math.radians(yaw), 3, "Z")
         @ Matrix.Rotation(math.radians(pitch), 3, "X"))
    P.set_world(ft, R @ P.rig.rest[ft][1], chain=True)


def rider_legs(P, spread=0.0, fwd=0.0, drop=0.0, pitch=0.0, yaw=3.0):
    for side, s in (("R", 1), ("L", -1)):
        A = rw(P, ANK0[s]) + Vector((s * spread, fwd, drop))
        rleg(P, side, A, pitch, s * yaw)


def rarm(P, side, target, pole, min_r=0.0):
    """骑手的手：腕沿"肩→目标"回退 WRIST_OFF，掌朝该方向。"""
    s = 1 if side == "R" else -1
    P.solve_T()
    S = P.T["r_upperarm_" + side]
    d = Vector(target) - S
    if d.length < 1e-6:
        return
    reach = (U.L_UPPER + U.L_FORE) * 0.985 + U.WRIST_OFF
    d = d.normalized() * max(min(d.length, reach), (U.L_UPPER + U.L_FORE) * min_r)
    dr = d.normalized()
    W = S + d - dr * U.WRIST_OFF
    E = PL.ik2(S, W, P.rig.L("r_upperarm_" + side), P.rig.L("r_forearm_" + side), pole)
    P.aim("r_upperarm_" + side, E - S, chain=False)
    P.aim("r_forearm_" + side, W - E, chain=False)
    P.aim("r_hand_" + side, dr)


def _mix(a, b, u):
    if isinstance(a, dict):
        return {k: _mix(a[k], b[k], u) for k in a}
    if isinstance(a, (tuple, list)):
        return tuple(_mix(x, y, u) for x, y in zip(a, b))
    if isinstance(a, Vector):
        return Vector(a).lerp(Vector(b), u)
    if isinstance(a, str):
        return a if u < 0.5 else b
    return a + (b - a) * u


def _bake(keys, D, emit):
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


FIST_R0 = U.FIST_R.copy()
FIST_L0 = U.FIST_L.copy()
LANCE_UP = U.LANCE_D.copy()


def lance_aim(P, pitch=0.0, yaw=0.0, grip=0.0):
    """pitch 负 = 枪尖往下压；grip = 枪沿自身轴往前滑（突刺时手送出去）。"""
    M = (Matrix.Rotation(math.radians(yaw), 3, "Z")
         @ Matrix.Rotation(math.radians(pitch), 3, "X"))
    P.aim("weapon_R", M @ LANCE_UP, chain=False)
    if grip:
        P.LOC["weapon_R"] = Vector((0, grip, 0))


# ── 1. idle：马静立，骑手左右侧身观察 ───────────────────────────────────────
def a_idle(rig, D=120):
    act = PL.new_action(rig.arm, "idle")
    W = PL.Writer(rig, loc_bones=W_BONES)
    seq = [
        # f,   head_yaw, chest_yaw, neck_yaw, dz,     bob,  tail
        (0,     0.0,      0.0,      0.0,     0.000,  0.0,   0.0),
        (18,  -34.0,    -12.0,     -8.0,     0.006,  0.6,   6.0),
        (38,  -36.0,    -13.0,     -8.0,     0.004, -0.2,   4.0),
        (54,   -6.0,     -2.0,     -1.0,     0.008, -0.6,  -2.0),
        (74,   30.0,     11.0,      7.0,     0.005,  0.5,  -7.0),
        (94,   32.0,     12.0,      7.0,     0.003,  0.1,  -5.0),
        (108,   4.0,      1.0,      0.0,     0.007, -0.4,   1.0),
        (120,   0.0,      0.0,      0.0,     0.000,  0.0,   0.0),
    ]
    for (f, hy, cy, ny, dz, bob, tw) in seq:
        P = pose(rig, dz=dz, hips_yaw=cy * 0.18, chest_yaw=cy * 0.35,
                 neck_yaw=ny, head_yaw=hy, neck_pitch=-1.2 + bob * 0.8,
                 tail_yaw=tw, tail_pitch=2.0)
        stand_legs(P)
        seat(P)
        rider_pose(P, chest_yaw=cy * 0.55, spine_yaw=cy * 0.30, head_yaw=hy * 0.42,
                   chest_pitch=-1.5 + bob * 0.6, head_pitch=bob * 0.5)
        rider_legs(P)
        rarm(P, "R", rw(P, FIST_R0) + Vector((0, 0.004 * bob, 0.004 * bob)),
             (0.95, -0.30, -0.20))
        rarm(P, "L", rw(P, FIST_L0), (-0.95, -0.30, -0.20))
        W.key(P, f)
    PL.finish_action(act)
    return act


# ── 2. walk：快步（对角双拍），步幅 0.60 m ──────────────────────────────────
K_STEP_F = 0.34
K_STEP_H = 0.36
K_SUP = 0.54


def _gait(ph, step, sup=K_SUP, lift=0.24):
    """(y 偏移, 抬脚, 蹄掌 pitch)。支撑相匀速后移 —— 不打滑。"""
    if ph < sup:
        return step - 2.0 * step * (ph / sup), 0.0, 0.0
    u = (ph - sup) / (1.0 - sup)
    s = u * u * (3.0 - 2.0 * u)
    y = -step + 2.0 * step * s
    z = lift * math.sin(math.pi * u) ** 0.85
    # pitch 在摆动相首末都必须回到 0（接地的两帧），否则 walk 闭不上环
    pitch = 32.0 * math.sin(math.pi * u) - 7.0 * math.sin(2.0 * math.pi * u)
    return y, z, pitch


def a_walk(rig, D=36):
    act = PL.new_action(rig.arm, "walk")
    W = PL.Writer(rig, loc_bones=W_BONES)
    for i in range(D + 1):
        t = i / D
        a2 = math.tau * t
        cy = math.cos(a2)
        # 对角双拍：FR+HL 同相；FL+HR 反相
        yf_r, zf_r, pf_r = _gait(t, K_STEP_F)
        yf_l, zf_l, pf_l = _gait((t + 0.5) % 1.0, K_STEP_F)
        yh_l, zh_l, ph_l = _gait(t, K_STEP_H, lift=0.20)
        yh_r, zh_r, ph_r = _gait((t + 0.5) % 1.0, K_STEP_H, lift=0.20)
        dz = -0.028 - 0.030 * math.cos(2.0 * a2)
        P = pose(rig, dz=dz,
                 hips_yaw=5.0 * cy, hips_roll=-4.0 * cy,
                 hips_pitch=1.6 * math.sin(2 * a2),
                 chest_yaw=-7.0 * cy, chest_roll=1.6 * cy,
                 chest_pitch=-2.6 + 1.8 * math.cos(2.0 * a2),
                 neck_pitch=-3.0 * math.cos(2.0 * a2), neck_yaw=2.0 * cy,
                 head_pitch=2.0 * math.cos(2.0 * a2),
                 tail_yaw=-7.0 * cy, tail_pitch=3.0 + 2.0 * math.sin(2 * a2))
        stand_legs(P, lift=(zf_r, zf_l, zh_r, zh_l),
                   dy=(yf_r, yf_l, yh_r, yh_l),
                   pitch=(pf_r, pf_l, ph_r, ph_l))
        seat(P)
        rider_pose(P, hips_pitch=1.2 * math.sin(2 * a2),
                   chest_pitch=-3.0 - 1.6 * math.cos(2.0 * a2),
                   chest_yaw=-2.5 * cy, spine_pitch=-1.0,
                   head_pitch=1.4 * math.cos(2.0 * a2), head_yaw=2.0 * cy)
        rider_legs(P)
        rarm(P, "R", rw(P, FIST_R0) + Vector((0.006, -0.012 * cy,
                                              0.012 * math.cos(2 * a2))),
             (0.95, -0.30, -0.20))
        rarm(P, "L", rw(P, FIST_L0) + Vector((0, 0.010 * cy, 0.010 * math.cos(2 * a2))),
             (-0.95, -0.30, -0.20))
        W.key(P, i)
    PL.finish_action(act)
    return act


# ── 3. attack：压低身体 → 夹枪突刺 ───────────────────────────────────────────
STAND = dict(lift=(0, 0, 0, 0), dy=(0, 0, 0, 0), pitch=(0, 0, 0, 0))


def _KD(f, **kw):
    d = dict(f=f, dz=0.0, hip_p=0.0, chest_p=0.0, chest_y=0.0, neck_p=-2.0,
             head_p=0.0, tail=0.0, legs=STAND, r_pitch=0.0, r_chest=-3.0,
             r_yaw=0.0, r_head=0.0, fist_r=(0.0, 0.0, 0.0),
             fist_l=(0.0, 0.0, 0.0), lance_p=0.0, lance_y=0.0, grip=0.0)
    d.update(kw)
    return f, d


def a_attack(rig, D=45):
    act = PL.new_action(rig.arm, "attack")
    W = PL.Writer(rig, loc_bones=W_BONES)
    KEYS = [
        _KD(0),
        # 蓄力：人往后坐、枪尖抬起、马头下压
        _KD(9, dz=-0.030, hip_p=2.0, chest_p=6.0, chest_y=-8.0, neck_p=3.0,
            head_p=2.0, r_pitch=-6.0, r_chest=7.0, r_yaw=-14.0, r_head=10.0,
            fist_r=(-0.02, -0.09, 0.07), fist_l=(0.01, -0.03, 0.02),
            lance_p=16.0, lance_y=-6.0),
        # 压低：身体前倾、枪开始下压、马前腿踏出半步
        _KD(15, dz=-0.060, hip_p=-3.0, chest_p=-7.0, chest_y=-3.0, neck_p=-6.0,
            head_p=-3.0, r_pitch=2.0, r_chest=-9.0, r_yaw=-4.0, r_head=3.0,
            fist_r=(0.01, -0.02, 0.02), fist_l=(0.0, 0.01, 0.0),
            lance_p=-22.0, grip=0.06,
            legs=dict(lift=(0, 0, 0, 0), dy=(0.10, 0.06, -0.04, -0.02),
                      pitch=(0, 0, -6, -4))),
        # 命中：躯干拧进枪里、枪尖压平、手向前送
        _KD(21, dz=-0.070, hip_p=-5.0, chest_p=-11.0, chest_y=6.0, neck_p=-9.0,
            head_p=-4.0, r_pitch=8.0, r_chest=-13.0, r_yaw=8.0, r_head=-4.0,
            fist_r=(0.01, 0.17, -0.03), fist_l=(-0.02, 0.06, 0.02),
            lance_p=-46.0, grip=0.30,
            legs=dict(lift=(0, 0, 0, 0), dy=(0.26, 0.20, -0.12, -0.08),
                      pitch=(2, 0, -12, -8))),
        # 顿帧
        _KD(25, dz=-0.072, hip_p=-5.0, chest_p=-12.0, chest_y=7.0, neck_p=-9.0,
            head_p=-4.0, r_pitch=9.0, r_chest=-14.0, r_yaw=9.0, r_head=-4.0,
            fist_r=(0.01, 0.182, -0.03), fist_l=(-0.02, 0.062, 0.02),
            lance_p=-48.0, grip=0.31,
            legs=dict(lift=(0, 0, 0, 0), dy=(0.27, 0.21, -0.12, -0.08),
                      pitch=(2, 0, -12, -8))),
        # 收枪
        _KD(34, dz=-0.030, hip_p=-1.0, chest_p=-2.0, chest_y=-2.0, neck_p=-2.0,
            r_chest=2.0, fist_r=(-0.01, 0.04, 0.02), lance_p=6.0, grip=0.05,
            legs=dict(lift=(0, 0, 0, 0), dy=(0.06, 0.04, -0.02, -0.01),
                      pitch=(0, 0, -2, -1))),
        _KD(45),
    ]

    def emit(f, d):
        P = pose(rig, dz=d["dz"], hips_pitch=d["hip_p"], chest_pitch=d["chest_p"],
                 chest_yaw=d["chest_y"], neck_pitch=d["neck_p"],
                 head_pitch=d["head_p"], tail_pitch=d["tail"])
        stand_legs(P, **d["legs"])
        seat(P)
        rider_pose(P, hips_pitch=d["r_pitch"], chest_pitch=d["r_chest"],
                   chest_yaw=d["r_yaw"], head_pitch=d["r_head"],
                   spine_pitch=d["r_chest"] * 0.35)
        rider_legs(P)
        rarm(P, "R", rw(P, FIST_R0) + Vector(d["fist_r"]), (0.95, -0.30, -0.10))
        rarm(P, "L", rw(P, FIST_L0) + Vector(d["fist_l"]), (-0.95, -0.30, -0.20))
        lance_aim(P, d["lance_p"], d["lance_y"], d["grip"])
        W.key(P, f)

    _bake(KEYS, D, emit)
    PL.finish_action(act)
    return act


# ── 4. dash：人立前摇 → 压低夹枪 → 保持冲锋姿势 ─────────────────────────────
PLANT = dict(lift=(0, 0, 0, 0), dy=(0.05, 0.04, -0.06, -0.05), pitch=(0, 0, -8, -6))
REAR = dict(lift=(0.52, 0.50, 0.0, 0.0), dy=(0.30, 0.26, -0.02, -0.01),
            pitch=(38, 36, -6, -5))
GALLOP = dict(lift=(0.30, 0.06, 0.05, 0.16), dy=(0.40, -0.12, -0.26, 0.20),
              pitch=(24, -10, -16, 12))


def a_dash(rig, D=110):
    act = PL.new_action(rig.arm, "dash")
    W = PL.Writer(rig, loc_bones=W_BONES)
    KEYS = [
        _KD(0),
        _KD(8, dz=-0.045, hip_p=-2.0, chest_p=-3.0, neck_p=-5.0,
            r_chest=-6.0, fist_r=(-0.01, -0.05, 0.04), lance_p=6.0, legs=PLANT),
        # 前摇顶点：人立（马身抬起 26°、前蹄抱胸、颈上扬）
        _KD(20, dz=0.0, hip_p=26.0, chest_p=10.0, neck_p=8.0, head_p=-4.0,
            tail=10.0, legs=REAR, r_pitch=-16.0, r_chest=10.0, r_head=8.0,
            fist_r=(-0.03, -0.13, 0.09), fist_l=(0.01, -0.04, 0.03), lance_p=22.0),
        _KD(28, dz=0.005, hip_p=22.0, chest_p=8.0, neck_p=6.0, tail=8.0,
            legs=dict(lift=(0.42, 0.40, 0.0, 0.0), dy=(0.34, 0.30, -0.02, -0.01),
                      pitch=(32, 30, -6, -5)),
            r_pitch=-12.0, r_chest=6.0, fist_r=(-0.02, -0.10, 0.07), lance_p=16.0),
        # 落蹄 → 压低夹枪
        _KD(38, dz=-0.075, hip_p=-4.0, chest_p=-8.0, neck_p=-8.0, head_p=-3.0,
            legs=dict(lift=(0, 0, 0, 0), dy=(0.22, 0.18, -0.14, -0.10),
                      pitch=(0, 0, -14, -10)),
            r_pitch=6.0, r_chest=-14.0, r_head=-5.0,
            fist_r=(0.01, 0.13, -0.02), fist_l=(-0.01, 0.05, 0.02),
            lance_p=-42.0, grip=0.26),
        _KD(46, dz=-0.085, hip_p=-6.0, chest_p=-11.0, neck_p=-10.0, head_p=-4.0,
            tail=-6.0, legs=GALLOP, r_pitch=8.0, r_chest=-16.0, r_head=-6.0,
            fist_r=(0.01, 0.16, -0.03), fist_l=(-0.01, 0.06, 0.02),
            lance_p=-46.0, grip=0.30),
    ]
    for f in range(52, 97, 4):
        br = math.sin(math.tau * 1.6 * (f - 52) / 44.0)
        KEYS.append(_KD(f, dz=-0.085 + 0.008 * br, hip_p=-6.0 + 0.6 * br,
                        chest_p=-11.0 - 0.8 * br, neck_p=-10.0 + 1.0 * br,
                        head_p=-4.0, tail=-6.0 + 3.0 * br,
                        legs=dict(lift=(0.30 + 0.02 * br, 0.06, 0.05, 0.16),
                                  dy=(0.40, -0.12, -0.26, 0.20),
                                  pitch=(24, -10, -16, 12)),
                        r_pitch=8.0, r_chest=-16.0 - 0.8 * br, r_head=-6.0,
                        fist_r=(0.01, 0.16, -0.03), fist_l=(-0.01, 0.06, 0.02),
                        lance_p=-46.0, grip=0.30))
    KEYS += [
        _KD(102, dz=-0.040, hip_p=-2.0, chest_p=-4.0, neck_p=-4.0,
            legs=PLANT, r_chest=-6.0, fist_r=(0.0, 0.05, 0.0),
            lance_p=-6.0, grip=0.08),
        _KD(110),
    ]

    def emit(f, d):
        P = pose(rig, dz=d["dz"], hips_pitch=d["hip_p"], chest_pitch=d["chest_p"],
                 neck_pitch=d["neck_p"], head_pitch=d["head_p"], tail_pitch=d["tail"])
        stand_legs(P, **d["legs"])
        seat(P)
        rider_pose(P, hips_pitch=d["r_pitch"], chest_pitch=d["r_chest"],
                   head_pitch=d["r_head"], spine_pitch=d["r_chest"] * 0.4)
        rider_legs(P)
        rarm(P, "R", rw(P, FIST_R0) + Vector(d["fist_r"]), (0.95, -0.30, -0.10))
        rarm(P, "L", rw(P, FIST_L0) + Vector(d["fist_l"]), (-0.95, -0.30, -0.20))
        lance_aim(P, d["lance_p"], 0.0, d["grip"])
        W.key(P, f)

    _bake(KEYS, D, emit)
    PL.finish_action(act)
    return act


# ── 5. hurt ─────────────────────────────────────────────────────────────────
def a_hurt(rig, D=12):
    act = PL.new_action(rig.arm, "hurt")
    W = PL.Writer(rig, loc_bones=W_BONES)
    seq = [(0, 0.0, 0.0, 0.0), (3, -0.035, 5.0, -6.0), (7, -0.016, 2.0, -3.0),
           (12, 0.0, 0.0, 0.0)]
    for (f, dz, cp, cy) in seq:
        P = pose(rig, dz=dz, chest_pitch=cp, chest_yaw=cy, neck_pitch=cp * 1.4,
                 head_pitch=cp * 0.8, tail_pitch=-4.0)
        stand_legs(P, dy=(-0.02, -0.01, 0.03, 0.02))
        seat(P)
        rider_pose(P, chest_pitch=-cp * 1.2, chest_yaw=-cy * 1.4, head_pitch=cp * 1.6)
        rider_legs(P)
        rarm(P, "R", rw(P, FIST_R0) + Vector((0, -0.02, -0.02)), (0.95, -0.3, -0.1))
        rarm(P, "L", rw(P, FIST_L0) + Vector((0, -0.01, 0.0)), (-0.95, -0.3, -0.2))
        W.key(P, f)
    PL.finish_action(act)
    return act


# ── 6. death：骑手向右摔下，马人立后向前扑倒 ────────────────────────────────
LEGSETS = {
    "stand": STAND,
    "rear": REAR,
    "step": dict(lift=(0.02, 0.0, 0.0, 0.0), dy=(0.16, 0.12, -0.08, -0.06),
                 pitch=(18, 14, -10, -8)),
    "knee": dict(lift=(0.06, 0.04, 0.0, 0.0), dy=(0.06, 0.02, -0.20, -0.17),
                 pitch=(30, 26, -18, -14)),
    "down": dict(lift=(0.02, 0.01, 0.0, 0.0), dy=(-0.10, -0.14, -0.34, -0.30),
                 pitch=(50, 46, -24, -20)),
}

DEATH_KEYS = [
    # f, dz,   hip_p, chest_p, neck_p, head_p, legs,    rx,    ry,    rz,   ryaw, rpitch, rroll, useabs, r_chest, r_head
    (0,   0.00,   0.0,   0.0,  -2.0,   0.0, "stand",  0.00,  0.00, 0.00,   0.0,   0.0,    0.0, 0,  -3.0,  0.0),
    (6,  -0.02,  -1.0,  -2.0,  -4.0,   1.0, "stand",  0.00,  0.00, 0.00,  -4.0,   3.0,   -6.0, 0,  -6.0,  6.0),
    (14,  0.00,  26.0,   9.0,   9.0,  -5.0, "rear",   0.30, -0.02, 1.98, -18.0,  12.0,  -34.0, 1, -10.0, 14.0),
    (22,  0.00,  18.0,   6.0,   5.0,  -3.0, "rear",  -0.70, -0.14, 1.62, -34.0,  20.0,  -62.0, 1, -12.0, 16.0),
    (30, -0.15, -14.0,  -9.0,  -8.0,   3.0, "step",  -1.02, -0.24, 0.90, -46.0,  16.0,  -80.0, 1, -10.0, 10.0),
    (40, -0.26, -16.0,  -8.0, -20.0,  20.0, "knee",  -1.14, -0.28, 0.42, -50.0,  10.0,  -84.0, 1,  -6.0,  4.0),
    (52, -0.30, -18.0,  -6.0, -22.0,  22.0, "down",  -1.14, -0.28, 0.42, -50.0,  10.0,  -84.0, 1,  -5.0,  2.0),
    (78, -0.31, -18.0,  -6.0, -22.0,  22.0, "down",  -1.14, -0.28, 0.42, -50.0,  10.0,  -84.0, 1,  -5.0,  2.0),
]


def a_death(rig, D=78):
    act = PL.new_action(rig.arm, "death")
    W = PL.Writer(rig, loc_bones=W_BONES)
    keys = []
    for row in DEATH_KEYS:
        (f, dz, hp, cp, np_, hdp, legs, rx, ry, rz, ryaw, rpitch, rroll,
         useabs, rch, rhd) = row
        keys.append((f, dict(f=f, dz=dz, hp=hp, cp=cp, np_=np_, hdp=hdp,
                             legs=LEGSETS[legs], rx=rx, ry=ry, rz=rz,
                             ryaw=ryaw, rpitch=rpitch, rroll=rroll,
                             useabs=float(useabs), rch=rch, rhd=rhd)))

    def emit(f, d):
        P = pose(rig, dz=d["dz"], hips_pitch=d["hp"], chest_pitch=d["cp"],
                 neck_pitch=d["np_"], head_pitch=d["hdp"], tail_pitch=-6.0)
        stand_legs(P, **d["legs"])
        seat(P)
        rr = "rider_root"
        if d["useabs"] > 0.5:
            # 已经离开鞍座：走绝对世界点，别再跟着马往下坠
            M = (Matrix.Rotation(math.radians(d["ryaw"]), 3, "Z")
                 @ Matrix.Rotation(math.radians(d["rpitch"]), 3, "X")
                 @ Matrix.Rotation(math.radians(d["rroll"]), 3, "Y"))
            Rr = M @ P.rig.rest[rr][1]
            P.place(rr, Vector((d["rx"], d["ry"], d["rz"])), Rr)
        rider_pose(P, chest_pitch=d["rch"], head_pitch=d["rhd"])
        rider_legs(P, pitch=14.0 if d["useabs"] > 0.5 else 0.0)
        rarm(P, "R", rw(P, FIST_R0) + Vector((0, 0.02 if d["useabs"] > 0.5 else 0.0, 0)),
             (0.95, -0.3, -0.1))
        rarm(P, "L", rw(P, FIST_L0), (-0.95, -0.3, -0.2))
        if d["useabs"] > 0.5:
            P.aim("weapon_R", Vector((-0.45, 0.80, -0.40)).normalized(), chain=False)
        else:
            lance_aim(P, 0.0)
        W.key(P, f)

    _bake(keys, D, emit)
    PL.finish_action(act)
    return act


def build_all(arm, only=None):
    rig = PL.Rig(arm)
    table = [("idle", a_idle), ("walk", a_walk), ("attack", a_attack),
             ("dash", a_dash), ("hurt", a_hurt), ("death", a_death)]
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
