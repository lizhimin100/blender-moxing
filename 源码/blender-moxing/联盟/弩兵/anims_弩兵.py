"""anims_弩兵.py —— 联盟弩兵 v4：重做 hurt / death，其余五条沿用旧关键帧

## 一、手是焊在弩上的（这条决定了全部写法）
`weapon` 骨挂在 **chest** 下，不在手骨下 —— 所以"人抓着弩"必须反过来做：
  1. 先让弩跟着胸走（`weapon_hold()`，不写 LOC，只吃父链）；
  2. 从弩骨的世界位姿反推两只手腕该在哪（`grip_world()`），IK 上去；
  3. 手掌朝向直接给死成 `R_weapon @ 静止相对朝向`（`weld_hands()`）。
握点在 rig 上只算一次，之后逐帧不变，所以"手 vs 弩"的相对位姿**永远等于静止姿态**。

## 二、静止姿态的手/弩间隙（unit_弩兵.fix_grip_clearance）
出厂网格的右拳是一整块方块，弩身原来从它的上沿穿过去（BVH 77 对面片）。
`load()` 里把手整体下移 26 mm、弩整体上移 55 mm，拳顶落在弩身底面下方 7 mm：
idle / idle_b / walk / shoot / reload / hurt / death 的 hand_*×weapon 逐帧全为 0。

## 三、五条旧动作一条关键帧都不重写
idle(0..120) / walk(0..30) / idle_b(0..90) / shoot(0..39) / reload(0..71) 原样保留，
只做三处微手术（`anim_tools`）：
  * walk：双臂 + 弩 + 弩矢锁到静止（旧版手会绕着弩转）；
  * walk：逐帧把 root 抬到"脚底贴地"（旧走路 f17 脚趾切地 12.9 mm）；
  * idle/idle_b/shoot/reload：腕骨焊回握姿；五条统一给头 +2°。

## 四、新两条
* hurt（9f）：后仰 + 侧闪，双手不离弩 —— 靠焊接白送；弩被带得抬 2 cm。
* death（32f）：中招 → 弩脱手砸地（`AH.drop_layered`，朝向先转位置后落）→ 跪 →
  向左侧倒 → f20 起逐骨定格到 f32。
"""
import math

import bpy
from mathutils import Matrix, Vector

import anim_tools as A
import anims_human as AH
import poselib2 as PL
import unit_弩兵 as U


class Spec:
    """这个骨架的尺寸（从 glb 量出来，与 unit_步兵 的口径一致）。"""

    def __init__(self):
        self.ANK = Vector((0.123, 0.0, 0.073))
        self.Z_ANKLE = 0.073
        self.HEEL_Y = -0.114
        self.TOE_Y = 0.270
        self.H = 1.70

    def foot_clear(self, pitch_deg):
        """方块脚绕踝转 pitch 后，踝要高到多少脚底才不切地。"""
        p = math.radians(pitch_deg)
        sp, cp = math.sin(p), math.cos(p)
        lo = 0.0
        for y in (self.HEEL_Y, self.TOE_Y):
            lo = max(lo, -(-self.Z_ANKLE * cp + y * sp))
        return lo


S = Spec()
FPS = 30
FLOOR_UP_MIN = 0.0086    # 弩躺平时最低点相对 weapon 骨 head 的 up（v4 出货几何实测）
FLOOR_GAP = 0.004        # 落地留 4 mm 余量，绝不切地
LOC_BONES = ("weapon",)
POLE = {"R": (0.60, 0.10, -0.79), "L": (-0.66, 0.35, -0.66)}
# 倒地后整个人侧躺，肘不能往"下"拐（会插进地里）——改成往侧面拐
POLE_FALL = {"R": (0.80, 0.32, -0.10), "L": (-0.80, 0.40, -0.10)}

# ── 手 → 弩 的固定相对位姿（rig 上只算一次）────────────────────────────────
_OFF, _REL, _HEAD, _ROT = {}, {}, None, None


def _prep(rig):
    global _HEAD, _ROT
    if _OFF:
        return
    _HEAD, _ROT = rig.rest["weapon"]
    for s in ("R", "L"):
        h = rig.rest["hand_" + s]
        _OFF[s] = _ROT.inverted() @ (h[0] - _HEAD)
        _REL[s] = _ROT.inverted() @ h[1]


def weapon_hold(P):
    """弩"还握在手上"时的世界位姿（完全是父链算出来的，不写 LOC）。"""
    P.solve_T()
    return P.T["weapon"].copy(), P.R["weapon"].copy()


def grip_world(Tw, Rw, side):
    return Tw + Rw @ _OFF[side]


def weld_hands(P, Tw, Rw):
    """两只手焊到弩骨上：位置与朝向都给死，IK 只决定肘往哪拐。"""
    for s in ("R", "L"):
        P.arm(s, grip_world(Tw, Rw, s), POLE[s])
        P.set_world("hand_" + s, Rw @ _REL[s])


# ── 脚底贴地 ────────────────────────────────────────────────────────────────
# 共享库的 `AH.ground` 在本骨架上会整条 no-op：`AH.sole()` 把 toe_R/L 也算进点云，
# 而这套网格的 toe 组没有 >0.5 权重的顶点（实测 foot 各 288 点、toe 0 点），
# `Sole.ok()` 要求每根骨都有点 → 直接返回 False。这里只用 foot 组自己建一份。
_SOLE, _SOLE_ARM = None, None


def ground_feet(P, S, target=0.0015):
    global _SOLE, _SOLE_ARM
    arm = P.rig.arm
    if _SOLE is None or _SOLE_ARM is not arm:
        meshes = [o for o in bpy.context.scene.objects
                  if o.type == "MESH" and not o.name.startswith("Icosphere")]
        _SOLE = PL.Sole(arm, meshes, bones=("foot_R", "foot_L"))
        _SOLE_ARM = arm
        print("[sole] foot 点云", {k: len(v) for k, v in _SOLE.pts.items()})
    return PL.ground(P, _SOLE, target=target, sides=("R", "L"))


# ══ 参数化关键帧 ════════════════════════════════════════════════════════════
def _kd(f, **kw):
    d = dict(f=f, dz=0.0, dx=0.0, dy=0.0,
             hips_yaw=0.0, hips_pitch=0.0, hips_roll=0.0,
             spine_pitch=0.0, chest_pitch=0.0, chest_yaw=0.0, chest_roll=0.0,
             head_pitch=0.0, head_yaw=0.0, head_roll=0.0, lift=0.0,
             rfoot=(S.ANK.x, 0.0, 0.0, 4.0), lfoot=(-S.ANK.x, 0.0, 0.0, -4.0))
    d.update(kw)
    return f, d


def _body(rig, d):
    P = AH.pose(rig, S, dz=d["dz"], dx=d["dx"], dy=d["dy"],
                hips_yaw=d["hips_yaw"], hips_pitch=d["hips_pitch"],
                hips_roll=d["hips_roll"], spine_pitch=d["spine_pitch"],
                chest_pitch=d["chest_pitch"], chest_yaw=d["chest_yaw"],
                chest_roll=d["chest_roll"], head_pitch=d["head_pitch"],
                head_yaw=d["head_yaw"], head_roll=d["head_roll"])
    AH.feet(P, S, d["rfoot"], d["lfoot"])
    return P


def _baked(rig, name, keys, D):
    act = PL.new_action(rig.arm, name)
    W = PL.Writer(rig, loc_bones=LOC_BONES)

    def emit(f, d):
        P = _body(rig, d)
        Tw, Rw = weapon_hold(P)
        if d.get("lift"):
            Tw = Tw + Vector((0.0, 0.0, d["lift"]))
            P.place("weapon", Tw, Rw, chain=True)
        weld_hands(P, Tw, Rw)
        AH.ground(P, S)          # 共享库入口（本骨架 toe 组无权重，内部 no-op）
        ground_feet(P, S)        # 兜底：只用 foot 组量脚底
        W.key(P, f)

    PL.bake(keys, D, emit)
    PL.finish_action(act)
    return act


# ══ 1. hurt（9f）：后仰 + 侧闪，双手不离弩 ══════════════════════════════════
def a_hurt(rig, D=9):
    keys = [
        _kd(0, chest_pitch=-2.0, head_pitch=1.0),
        # f2 中招：上身后仰、往右让，头被打得甩向左边；弩开始被带起来
        _kd(2, dz=-0.016, dx=0.026, hips_pitch=2.0, hips_yaw=-5.0, lift=0.008,
            chest_pitch=13.0, chest_roll=-9.0, chest_yaw=10.0,
            head_pitch=15.0, head_yaw=-11.0, head_roll=-8.0,
            rfoot=(S.ANK.x + 0.004, -0.014, -3.0, 6.0),
            lfoot=(-S.ANK.x - 0.026, 0.026, 4.0, -8.0)),
        # f4 顶点：肋下再吃一记，弩被带得抬 2 cm（手不离）
        _kd(4, dz=-0.026, dx=0.034, dy=-0.010, hips_pitch=4.0, hips_yaw=-8.0, lift=0.020,
            chest_pitch=16.0, chest_roll=-12.0, chest_yaw=13.0,
            head_pitch=18.0, head_yaw=-14.0, head_roll=-10.0,
            rfoot=(S.ANK.x + 0.008, -0.020, -4.0, 7.0),
            lfoot=(-S.ANK.x - 0.032, 0.030, 5.0, -9.0)),
        # f6 撑住：膝盖回弹，开始找平衡，弩落回 1 cm
        _kd(6, dz=-0.014, dx=0.014, hips_pitch=1.0, hips_yaw=-3.0, lift=0.010,
            chest_pitch=6.0, chest_roll=-4.0, chest_yaw=5.0,
            head_pitch=8.0, head_yaw=-5.0, head_roll=-3.0,
            rfoot=(S.ANK.x + 0.004, -0.008, -1.0, 5.0),
            lfoot=(-S.ANK.x - 0.014, 0.014, 2.0, -6.0)),
        _kd(9, chest_pitch=-2.0, head_pitch=1.0),
    ]
    return _baked(rig, "hurt", keys, D)


# 落地侧躺（可被 docs/_tmp 的调参脚本覆盖）：髋高按"侧躺半径"定，双腿折在身后
DEATH_SETTLED = dict(dz=-0.300, dx=-0.030, dy=0.070, hips_pitch=-16.0, hips_roll=-86.0,
                     chest_pitch=-4.0, chest_roll=-3.0, head_pitch=6.0, head_yaw=13.0,
                     rfoot=(S.ANK.x + 0.020, -0.400, 22.0, 10.0, 0.020),
                     lfoot=(-S.ANK.x - 0.010, -0.450, 18.0, -11.0, 0.020),
                     hR=Vector((0.200, -0.120, -0.160)), hL=Vector((-0.340, 0.140, -0.040)),
                     hyR=-24.0, hyL=20.0, drop=1.0, foot_roll=-86.0)


# ══ 2. death（32f）：弩脱手砸地 → 跪 → 向左侧倒 → 定格 ═════════════════════
def a_death(rig, D=32):
    act = PL.new_action(rig.arm, "death")
    W = PL.Writer(rig, loc_bones=LOC_BONES)
    # 落地姿态：弩轴仍朝"前偏左"（和握着时同向），截面朝上 —— 这样掉落过程里
    # 几乎不转，后半截不会扫到松开的手。
    R_FLOOR = U.weapon_floor_rot(rig.rest["weapon"][1], axdir=(-0.32, 0.95, 0.0))
    # 落点：zmin = T_z + FLOOR_UP_MIN（FLOOR_UP_MIN 是弩网格最低点相对 weapon 骨 head
    # 的 up 坐标，按出货几何实测；v4 把弩顶点上移过 55 mm，所以它是正的）
    T_FLOOR = Vector((0.30, 0.62, FLOOR_GAP - FLOOR_UP_MIN))

    def emit(f, d):
        P = _body(rig, d)
        # 倒地后整个人侧躺：脚也要跟着侧过来，否则会像"断脚踝"立在地上。
        # 走 P.leg 的 foot_roll 参数（不是另加一次 rot），AH.ground 重解腿时才会保留它。
        if d["foot_roll"]:
            for side in ("R", "L"):
                ank, pole, fp, fy, _fr = P.legargs[side]
                P.leg(side, ank, pole, fp, fy, d["foot_roll"])
        Tw, Rw = weapon_hold(P)
        for s in ("R", "L"):
            free = d["h" + s]
            k = max(0.0, min(1.0, (free.length - 0.100) / 0.100))
            P.arm(s, grip_world(Tw, Rw, s) + free, POLE_FALL[s])
            q_hold = (Rw @ _REL[s]).to_quaternion()
            q_free = (Matrix.Rotation(math.radians(d["hy" + s]), 3, "Z")
                      @ P.rig.rest["hand_" + s][1]).to_quaternion()
            P.set_world("hand_" + s, q_hold.slerp(q_free, k).to_matrix())
        AH.drop_layered(P, "weapon", T_FLOOR, R_FLOOR,
                        d["drop"], min(1.0, d["drop"] * 1.35))
        AH.ground(P, S)          # 共享库入口（本骨架 toe 组无权重，内部 no-op）
        ground_feet(P, S)        # 兜底：只用 foot 组量脚底
        W.key(P, f)

    def kd(f, **kw):
        d = dict(f=f, dz=0.0, dx=0.0, dy=0.0,
                 hips_yaw=0.0, hips_pitch=0.0, hips_roll=0.0,
                 spine_pitch=0.0, chest_pitch=0.0, chest_yaw=0.0, chest_roll=0.0,
                 head_pitch=0.0, head_yaw=0.0, head_roll=0.0,
                 rfoot=(S.ANK.x, 0.0, 0.0, 4.0), lfoot=(-S.ANK.x, 0.0, 0.0, -4.0),
                 hR=Vector((0.0, 0.0, 0.0)), hL=Vector((0.0, 0.0, 0.0)),
                 hyR=0.0, hyL=0.0, drop=0.0, foot_roll=0.0)
        d.update(kw)
        return f, d

    SETTLED = DEATH_SETTLED

    keys = [
        kd(0, chest_pitch=-2.0, head_pitch=1.0),
        # f2 中招：整个人往后一顿，弩还在手上
        kd(2, dz=-0.020, dx=0.020, hips_pitch=3.0, hips_yaw=-6.0,
           chest_pitch=12.0, chest_roll=-8.0, chest_yaw=9.0,
           head_pitch=14.0, head_yaw=-10.0, head_roll=-7.0,
           rfoot=(S.ANK.x + 0.004, -0.016, -3.0, 7.0),
           lfoot=(-S.ANK.x - 0.024, 0.024, 4.0, -8.0)),
        # f4 松手：两只手**先垂直往下退出夹钳**（夹钳上开口，只有这个方向不刮弩身）
        kd(4, dz=-0.052, dx=0.026, dy=0.008, hips_pitch=6.0, hips_yaw=-8.0,
           chest_pitch=15.0, chest_roll=-10.0, chest_yaw=12.0,
           head_pitch=17.0, head_yaw=-12.0, head_roll=-8.0,
           hR=Vector((0.010, 0.020, -0.095)), hL=Vector((-0.010, 0.020, -0.095)),
           hyR=-14.0, hyL=12.0, drop=0.0,
           rfoot=(S.ANK.x + 0.010, -0.026, -4.0, 8.0),
           lfoot=(-S.ANK.x - 0.030, 0.028, 5.0, -9.0)),
        # f6 手已退干净，弩脱手悬空一瞬（0.07 s）
        kd(6, dz=-0.098, dx=0.020, dy=0.014, hips_pitch=-2.0, hips_yaw=-6.0,
           chest_pitch=6.0, chest_roll=-9.0, chest_yaw=9.0,
           head_pitch=15.0, head_yaw=-9.0, head_roll=-6.0,
           hR=Vector((0.020, 0.020, -0.140)), hL=Vector((-0.020, 0.020, -0.140)),
           hyR=-18.0, hyL=15.0, drop=0.0,
           rfoot=(S.ANK.x + 0.014, -0.044, 6.0, 8.0),
           lfoot=(-S.ANK.x - 0.028, -0.010, 8.0, -9.0)),
        # f8 弩开始掉，人往下坐
        kd(8, dz=-0.140, dx=0.016, dy=0.020, hips_pitch=-8.0, hips_yaw=-5.0,
           chest_pitch=2.0, chest_roll=-9.0, chest_yaw=8.0,
           head_pitch=14.0, head_yaw=-7.0, head_roll=-5.0,
           hR=Vector((0.000, -0.105, -0.150)), hL=Vector((0.000, -0.105, -0.150)),
           hyR=-22.0, hyL=17.0, drop=0.20,
           rfoot=(S.ANK.x + 0.018, -0.058, 12.0, 9.0),
           lfoot=(-S.ANK.x - 0.028, -0.026, 14.0, -9.0)),
        # f11 弩在半空，膝盖已经着地
        kd(11, dz=-0.206, dy=0.030, hips_pitch=-20.0, hips_roll=-8.0,
           chest_pitch=-6.0, chest_roll=-8.0, head_pitch=13.0, head_yaw=-3.0,
           hR=Vector((0.100, -0.040, -0.200)), hL=Vector((-0.130, -0.030, -0.190)),
           hyR=-24.0, hyL=18.0, drop=0.86,
           rfoot=(S.ANK.x + 0.022, -0.070, 20.0, 9.0),
           lfoot=(-S.ANK.x - 0.026, -0.042, 24.0, -10.0)),
        # f14 弩砸地 + 跪稳
        kd(14, dz=-0.246, dy=0.038, hips_pitch=-34.0, hips_roll=-26.0,
           chest_pitch=-8.0, chest_roll=-8.0, head_pitch=10.0, head_yaw=2.0,
           hR=Vector((0.180, 0.030, -0.210)), hL=Vector((-0.230, 0.040, -0.200)),
           hyR=-26.0, hyL=20.0, drop=1.0,
           rfoot=(S.ANK.x + 0.030, -0.080, 26.0, 10.0, 0.004),
           lfoot=(-S.ANK.x - 0.034, -0.054, 30.0, -11.0, 0.004)),
        # f17 侧倒（身体开始绕 Y 滚，脚跟着侧过来）
        kd(17, dz=-0.330, dx=-0.010, dy=0.052, hips_pitch=-26.0, hips_roll=-58.0,
           chest_pitch=-6.0, chest_roll=-5.0, head_pitch=8.0, head_yaw=8.0,
           hR=Vector((0.240, -0.020, -0.190)), hL=Vector((-0.310, 0.070, -0.130)),
           hyR=-25.0, hyL=20.0, drop=1.0, foot_roll=-44.0,
           rfoot=(S.ANK.x + 0.034, -0.110, 30.0, 10.0, 0.030),
           lfoot=(-S.ANK.x - 0.028, -0.140, 28.0, -11.0, 0.028)),
    ]
    keys.append((20, dict(keys[-1][1], f=20, **SETTLED)))
    keys.append((32, dict(keys[-1][1], f=32)))
    PL.bake(keys, D, emit)
    PL.finish_action(act)
    return act


# ══ 3. 五条旧动作：关键帧不动，只做微手术 ═══════════════════════════════════
OLD = ("idle", "idle_b", "walk", "shoot", "reload")


def weld_old_hands(arm, act, near=0.015, far=0.090):
    """把旧动作里**手掌的世界朝向**拧成"握弩朝向"，位置与时序一概不动。

    为什么要这一步：旧版的腕骨根本没被约束过（实测手掌朝向偏离握弩朝向 91°~250°），
    旧拳块是个近立方体，转多少都看不出来。现在手是夹钳，差 12° 就够让四角扎进弩身。
    这里只在手还贴着弩（离握点 <1.5 cm）时焊满，手飞出去（idle_b / reload 抽矢）
    就按 smoothstep 退回原朝向，不会把手腕拧成麻花。
    """
    scene = bpy.context.scene
    arm.animation_data_create()
    arm.animation_data.action = act
    try:
        arm.animation_data.action_slot = act.slots[0]
    except Exception:
        pass
    f0, f1 = (int(v) for v in act.frame_range)
    plan = []
    for f in range(f0, f1 + 1):
        scene.frame_set(f)
        bpy.context.view_layer.update()
        wm = arm.pose.bones["weapon"].matrix
        Rw, Tw = wm.to_3x3(), wm.translation.copy()
        row = []
        for s in ("R", "L"):
            pb = arm.pose.bones["hand_" + s]
            cur = pb.matrix.copy()
            wrist = cur.translation.copy()
            q = (Rw @ _REL[s]).to_quaternion()
            M = q.to_matrix().to_4x4()
            M.translation = wrist
            row.append((s, M))
        plan.append((f, row))
    for f, row in plan:
        scene.frame_set(f)
        bpy.context.view_layer.update()
        for s, M in row:
            pb = arm.pose.bones["hand_" + s]
            pb.matrix = M
            pb.keyframe_insert("rotation_quaternion", frame=f)
    arm.animation_data.action = None
    for pb in arm.pose.bones:
        pb.matrix_basis.identity()


def floor_lift(arm, act, target=0.0012):
    """旧动作逐帧把 root 抬到"最低点刚好贴地"（只抬不压）。

    为什么要这一步：旧走路的踝高是按**解析公式**给的，脚一 pitch，脚尖就切进地面
    （实测 f17 切 12.9 mm、f11 切 8 mm）。这里直接量求值后网格的最低点，差多少抬多少，
    只改 root 的 location，不动任何关节角度，也不改节奏。
    """
    meshes = [o for o in bpy.context.scene.objects
              if o.type == "MESH" and not o.name.startswith("Icosphere")]
    scene = bpy.context.scene
    arm.animation_data_create()
    arm.animation_data.action = act
    try:
        arm.animation_data.action_slot = act.slots[0]
    except Exception:
        pass
    f0, f1 = (int(v) for v in act.frame_range)
    need, base = {}, {}
    for f in range(f0, f1 + 1):
        scene.frame_set(f)
        bpy.context.view_layer.update()
        dg = bpy.context.evaluated_depsgraph_get()
        z = 1e9
        for ob in meshes:
            oe = ob.evaluated_get(dg)
            me = oe.to_mesh()
            mw = oe.matrix_world
            for v in me.vertices:
                zz = (mw @ v.co).z
                if zz < z:
                    z = zz
            oe.to_mesh_clear()
        need[f] = max(0.0, target - z)
        base[f] = arm.pose.bones["root"].location.copy()
    if not any(v > 1e-6 for v in need.values()):
        arm.animation_data.action = None
        return 0
    # 平滑包络：邻域取 max（把尖峰摊成驼峰）后三点平均，但每帧都不低于实际需求
    env = {f: max(need.get(g, 0.0) for g in (f - 1, f, f + 1) if g in need) for f in need}
    lift = {}
    for f in need:
        ns = [env[g] for g in (f - 1, f, f + 1) if g in env]
        lift[f] = max(need[f], sum(ns) / len(ns))
    lift[f1] = lift[f0] = max(lift[f0], lift[f1])      # 循环首末一致
    R0 = arm.data.bones["root"].matrix_local.to_3x3().inverted()
    for f in sorted(need):
        scene.frame_set(f)
        bpy.context.view_layer.update()
        pb = arm.pose.bones["root"]
        pb.location = base[f] + (R0 @ Vector((0.0, 0.0, lift[f])))
        pb.keyframe_insert("location", frame=f)
    for fc in A.fcurves(act):
        fc.update()
    arm.animation_data.action = None
    for pb in arm.pose.bones:
        pb.matrix_basis.identity()
    print("[anim] %-6s 抬 root 贴地：0 → %.1f mm（%d 帧有修正）"
          % (act.name, max(lift.values()) * 1000, sum(1 for v in lift.values() if v > 1e-6)))
    return sum(1 for v in lift.values() if v > 1e-6)


def patch_old(arm):
    walk = A.get("walk")
    if walk:
        n = A.lock_bones(walk, ["shoulder_R", "shoulder_L", "upperarm_R", "upperarm_L",
                                "forearm_R", "forearm_L", "hand_R", "hand_L",
                                "weapon", "prop_bolt"], loc=True)
        print("[anim] walk 锁住双臂 + 弩（%d 根骨），手不再绕弩转" % n)
    for nm in ("idle", "idle_b", "shoot", "reload"):
        a = A.get(nm)
        if a:
            A.lock_bones(a, ["hand_R", "hand_L"], loc=True)
            weld_old_hands(arm, a)
    for nm in OLD:
        a = A.get(nm)
        if a:
            A.add_local_rot(a, "head", (1, 0, 0), 2.0)
    arm.animation_data.action = None
    for pb in arm.pose.bones:
        pb.matrix_basis.identity()
    for nm in OLD:                                  # 腕骨/FK 手术之后才量得到真实最低点
        a = A.get(nm)
        if a:
            floor_lift(arm, a)
    print("[anim] 旧动作保留：%s（腕骨焊回握姿 + 头部 +2° + 脚底贴地校正）"
          % ", ".join(OLD))


TABLE = [("hurt", a_hurt), ("death", a_death)]


def build_all(arm, only=None):
    """体检脚本（pose_check / unit_shot）的入口：返回**全部七条**动作名。

    旧五条是"手术保留"的，不重建关键帧，但必须一起列出来才检查得到。
    """
    rig = PL.Rig(arm)
    _prep(rig)
    patch_old(arm)
    arm.animation_data.action = None
    out = []
    for name in OLD:
        if only and name not in only:
            continue
        if bpy.data.actions.get(name):
            out.append(name)
    for name, fn in TABLE:
        if only and name not in only:
            continue
        old = bpy.data.actions.get(name)
        if old:
            bpy.data.actions.remove(old)
        act = fn(rig)
        act.name = name
        act.use_fake_user = True
        out.append(name)
        print("[anim] %-6s 重做，帧 %s" % (name, tuple(int(v) for v in act.frame_range)))
    arm.animation_data.action = None
    for pb in arm.pose.bones:
        pb.matrix_basis.identity()
    return out


def build(arm):
    """先给旧动作做手术，再覆盖 hurt / death。返回 [(名字, 帧范围)]。"""
    rig = PL.Rig(arm)
    _prep(rig)
    patch_old(arm)
    arm.animation_data.action = None
    out = []
    for name, fn in TABLE:
        old = bpy.data.actions.get(name)
        if old:
            bpy.data.actions.remove(old)
        act = fn(rig)
        act.name = name
        act.use_fake_user = True
        out.append((name, tuple(int(v) for v in act.frame_range)))
        print("[anim] %-6s 重做，帧 %s" % (name, out[-1][1]))
    arm.animation_data.action = None
    for pb in arm.pose.bones:
        pb.matrix_basis.identity()
    return out
