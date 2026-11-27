"""anims_斥候.py —— 豺狼人斥候 v5：腰间低持（一手在前、一手在后）

## 这一版推翻的到底是什么

v4 的握点是照"手臂自然下垂"的终点抄的：`(±0.352, 0.176, 0.986)` —— 在**胯的两侧**。
手腕在体侧、刀尖朝下、肘只能往外撇，正面看就是"双手撑腰"。
更要命的是后手被塞进了胯里：客观体检（`库/audit_anim.py` 按顶点组拆骨做 BVH 互交）
实测 `hand_L×hips` **576 对三角面相交**、`weapon_L×hips` 435 对 —— 那只手不是摆在胯边，
是**埋进胯里**的。所以光调角度没用，得换语法。

## 新语法：腰间低持（low guard）

    蹲下            dz −0.19，髋 −5 / 腰 −9 / 胸 −14（合计前压 28°），头 +17 把视线抬回来
    一手在前        右手掌心 (0.176, 0.336, 0.928) —— 在**肚子前面** 17 cm 处，刃尖朝前下
    一手在后        左手掌心 (−0.306, −0.296, 0.982) —— 在**后胯外侧、披风之外**，刃尖朝后下
    两把刀都在腰线上  刃轴与水平面只差 30~36°，全程不抬肘、不过肩

"前/后"用世界 Y 拉开，不靠左右 —— 侧视剪影里一条从右手到左手的斜线，
俯视角下也读得出来（这是 96 px 下唯一还看得见的姿势信息）。

**披风让位**：后手的世界点在 `z=0.98` 处披风壳（椭圆 rx0.36/ry0.295，中心 y=−0.116）
的**外侧**，同时 `cape` 骨往右摆 5°，布让开 2 cm，手不会从布里穿出来。

## 五条动作

  idle   130f  蹲伏扫视：只看头（±30°）、重心左右 1.2 cm、一次换气；双手不离腰线
  walk    30f  蹲伏快走：腿走满（±0.20），手只做 ±1.8 cm 的反向小幅摆
  attack  40f  两段都在腰线：右匕前刺（f12 命中，+0.30 m）→ 左匕反手横扫（f26）
  hurt    10f  后仰侧闪，刀不散架
  death   62f  中招 → 腿一软 → 向左侧倒（左手撑地）→ 侧卧定格，双匕仍握在手里

## 帧长
idle 130 / walk 30 / attack 40 / hurt 10 / death 62，30 fps，逐帧烘焙。
"""
import math

import bpy
from mathutils import Matrix, Vector

import anims_human as AH
import poselib2 as PL
import unit_斥候_v3 as U

FPS = 30
S = U.S
LOC_BONES = ("weapon_R", "weapon_L")

# ── 唯一的一套架势：五条动作全部从这里出发 ────────────────────────────────
DZ = -0.212
BASE = dict(
    dz=DZ, dx=0.0, dy=0.0,
    hips_pitch=-7.0, hips_yaw=8.0, hips_roll=0.0,
    spine_pitch=-8.0,
    chest_pitch=-16.0, chest_yaw=24.0, chest_roll=0.0,
    head_pitch=20.0, head_yaw=3.0, head_roll=0.0,
    rfoot=(0.262, 0.232, 3.0, 11.0),
    lfoot=(-0.256, -0.224, -3.0, -19.0),
    # 前手（右）：肚子前面，刃尖朝前下 33°
    grp=Vector((0.180, 0.404, 0.952)),
    gdir=Vector((-0.16, 0.90, -0.40)),
    groll=0.0,
    # 后手（左）：后胯外侧、披风之外，刃尖朝后下 36°
    glp=Vector((-0.384, -0.324, 1.014)),
    ldir=Vector((-0.46, -0.62, -0.64)),
    lroll=0.0,
    csw=6.0, clift=-1.5,
    tailx=9.0, tailz=-8.0, tailz2=0.0,
)

# 肘往哪拐（pole 会被投影到"肩→腕"的垂面上）：
#   前手：肘往下、略往外 → 正面看肘藏在刀后面，不形成"撑腰三角"
#   后手：肘往下、略往前 → 肘不往身体后面翻
POLE_R = (0.52, 0.06, -0.85)
POLE_L = (-0.44, 0.20, -0.87)

# 左肩（锁骨）微抬 + 外旋：兜帽后缘和三角肌在这副骨架上本来只差 8 mm，
# 躯干一前压就顶上。抬 8° 把两者分开（实测 254 对 → 0）。
SH_L = (-8.0, -8.0)

# 腰线握点跟着躯干扭 —— 手是"长在身上的"，不是钉在世界里的
CY0 = 0.012


def _prep(rig):
    """握点相对 hand 骨的局部偏移（掌心 ≠ 腕点，差 3 cm，不补就会捏着刀尖）。"""
    rig.grip_local = {}
    for s, G, W in (("R", U.G_R, S.WRI_R), ("L", U.G_L, S.WRI_L)):
        R = rig.rest["hand_" + s][1]
        rig.grip_local[s] = R.transposed() @ (Vector(G) - Vector(W))


def _kd(f, **kw):
    d = dict(BASE)
    d["f"] = f
    d.update(kw)
    return f, d


def _yaw(v, deg):
    """绕竖直轴（过 chest 骨 head 的 y）转一个点/方向。"""
    if abs(deg) < 1e-9:
        return Vector(v)
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    x, y = v[0], v[1] - CY0
    return Vector((x * c - y * s, x * s + y * c + CY0, v[2]))


def _twist(d):
    """当前帧躯干相对基准转了多少度（hips + chest，spine 没单独给 yaw）。"""
    return ((d["hips_yaw"] + d["chest_yaw"])
            - (BASE["hips_yaw"] + BASE["chest_yaw"]))


def _feet(P, d):
    for side, v in (("R", d["rfoot"]), ("L", d["lfoot"])):
        x, y, pitch, yaw = v[:4]
        lift = v[4] if len(v) > 4 else 0.0
        pole = (0.36, 1.0, 0.12) if side == "R" else (-0.36, 1.0, 0.12)
        P.leg(side, Vector((x, y, S.foot_clear(pitch) + lift)), pole, pitch, yaw)


def _hands(P, d):
    """握点写在**躯干坐标系**里（= BASE 姿态下的世界点），逐帧按躯干扭转搬过去。

    这样"手↔胯↔披风"的相对位置恒等于基准姿态 —— 扫视、走路、出刀都不会
    因为胸一转就把后手推进披风里（这是 v4 最贵的一课）。
    """
    tw = _twist(d) * d.get("tw", 1.0)
    PL.grip_at(P, "R", _yaw(d["grp"], tw), _yaw(d["gdir"], tw), d["groll"], POLE_R)
    PL.grip_at(P, "L", _yaw(d["glp"], tw), _yaw(d["ldir"], tw), d["lroll"], POLE_L)


def _extra(P, d):
    P.rot("shoulder_L", (0, 1, 0), SH_L[0])
    P.rot("shoulder_L", (0, 0, 1), SH_L[1])
    P.rot("tail_01", (0, 0, 1), d["tailx"])
    P.rot("tail_01", (1, 0, 0), d["tailz"])
    P.rot("tail_02", (1, 0, 0), d["tailz2"])
    P.rot("cape", (0, 0, 1), d["csw"])
    P.rot("cape", (1, 0, 0), d["clift"])


def _emit(rig, W, loop_D=None):
    first = []

    def emit(f, d):
        P = PL.Frame(rig)
        PL.stance(P, dz=d["dz"], dx=d["dx"], dy=d["dy"], legs=False,
                  hips_yaw=d["hips_yaw"], hips_pitch=d["hips_pitch"],
                  hips_roll=d["hips_roll"], spine_pitch=d["spine_pitch"],
                  chest_pitch=d["chest_pitch"], chest_yaw=d["chest_yaw"],
                  chest_roll=d["chest_roll"], head_pitch=d["head_pitch"],
                  head_yaw=d["head_yaw"], head_roll=d["head_roll"])
        _feet(P, d)
        _hands(P, d)
        _extra(P, d)
        AH.ground(P, S)
        if f == 0:
            first.append(P)
        elif loop_D is not None and f == loop_D and first:
            P = first[0]
        W.key(P, f)
    return emit


def _baked(rig, name, keys, D, loop=False):
    act = PL.new_action(rig.arm, name)
    W = PL.Writer(rig, loc_bones=LOC_BONES)
    PL.bake(keys, D, _emit(rig, W, loop_D=D if loop else None))
    PL.finish_action(act)
    return act


# ══ 1. idle（130f）═════════════════════════════════════════════════════════
def a_idle(rig, D=130):
    """蹲着扫视。**手是锚**：胸腔转 20°，肩会前后挪 5 cm，手却几乎不动 ——
    这正是"刀握在腰上、身体在动"的观感，也是它不会读成叉腰的原因。"""
    keys = [
        _kd(0),
        _kd(14, dz=DZ - 0.006, dx=-0.012, hips_yaw=-4.0, chest_pitch=-15.4,
            chest_yaw=6.0, head_yaw=-27.0, head_pitch=15.0, head_roll=-3.0,
            grp=BASE["grp"] + Vector((0.004, 0.006, 0.004)),
            gdir=BASE["gdir"] + Vector((-0.03, 0.0, 0.02)),
            glp=BASE["glp"] + Vector((0.004, -0.004, 0.003)),
            tailx=14.0, csw=-7.0, clift=-2.2),
        _kd(30, dz=DZ - 0.010, dx=-0.015, hips_yaw=-4.0, chest_pitch=-15.0,
            chest_yaw=4.0, chest_roll=-2.5, head_yaw=-31.0, head_pitch=14.0,
            head_roll=-4.0,
            grp=BASE["grp"] + Vector((0.006, 0.008, 0.002)),
            glp=BASE["glp"] + Vector((0.005, -0.006, 0.002)),
            tailx=17.0, csw=-8.0, clift=-2.4),
        _kd(46, dz=DZ - 0.005, dx=-0.004, chest_yaw=8.0, head_yaw=-9.0,
            head_pitch=16.0,
            grp=BASE["grp"] + Vector((0.002, 0.003, 0.001)),
            tailx=4.0, csw=-6.0, clift=-1.8),
        # 看右（同一套幅度，镜像）
        _kd(64, dz=DZ - 0.006, dx=0.012, hips_yaw=-2.0, chest_pitch=-15.4,
            chest_yaw=15.0, chest_roll=2.5, head_yaw=16.0, head_pitch=15.0,
            head_roll=3.0,
            grp=BASE["grp"] + Vector((-0.004, 0.004, 0.004)),
            gdir=BASE["gdir"] + Vector((0.02, 0.0, 0.03)),
            glp=BASE["glp"] + Vector((-0.004, -0.002, 0.002)),
            tailx=-8.0, csw=-3.0, clift=-2.2),
        _kd(80, dz=DZ - 0.010, dx=0.015, hips_yaw=-2.0, chest_pitch=-15.0,
            chest_yaw=18.0, chest_roll=3.0, head_yaw=20.0, head_pitch=14.0,
            head_roll=4.0,
            grp=BASE["grp"] + Vector((-0.006, 0.006, 0.002)),
            glp=BASE["glp"] + Vector((-0.006, -0.002, 0.002)),
            tailx=-11.0, csw=-2.0, clift=-2.4),
        _kd(96, dz=DZ - 0.005, dx=0.004, chest_yaw=12.0, head_yaw=4.0,
            head_pitch=16.0,
            grp=BASE["grp"] + Vector((-0.002, 0.002, 0.001)),
            tailx=0.0, csw=-4.0, clift=-1.8),
        # 一次换气：肩一沉，两把刀一起低 6 mm（手跟着刀，不脱手）
        _kd(108, dz=DZ - 0.012, chest_pitch=-15.6, spine_pitch=-9.6,
            head_pitch=18.0,
            grp=BASE["grp"] + Vector((0.0, 0.002, -0.006)),
            glp=BASE["glp"] + Vector((0.0, -0.002, -0.006)),
            groll=5.0, tailx=2.0, clift=-0.8),
        _kd(130),
    ]
    return _baked(rig, "idle", keys, D, loop=True)


# ══ 2. walk（30f）══════════════════════════════════════════════════════════
SP = 0.20
SUP = 0.56


def a_walk(rig, D=30):
    act = PL.new_action(rig.arm, "walk")
    W = PL.Writer(rig, loc_bones=LOC_BONES)

    def leg_y(ph):
        if ph < SUP:
            return SP - 2.0 * SP * (ph / SUP)
        u = (ph - SUP) / (1.0 - SUP)
        return -SP + 2.0 * SP * (u * u * (3.0 - 2.0 * u))

    def leg_lift(ph):
        if ph < SUP:
            return 0.0
        u = (ph - SUP) / (1.0 - SUP)
        return 0.082 * math.sin(math.pi * u) ** 0.80

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
        return 13.0 - 5.0 * (k * k * (3.0 - 2.0 * k))

    for i in range(D + 1):
        t = 0.0 if i == D else i / float(D)
        a2 = 2.0 * math.pi * t
        cy = math.cos(a2)
        c2 = math.cos(2.0 * a2)
        sink = 0.0
        for c in (0, D // 2):
            k = i - c
            if 0 <= k <= 3:
                sink -= 0.013 * math.sin(math.pi * k / 3.0)
        dz = DZ - 0.012 * c2 + sink
        hz = dz - DZ
        d = dict(BASE)
        d.update(dict(
            dz=dz, dx=0.018 * math.sin(a2),
            hips_yaw=-3.0 + 6.0 * cy, hips_roll=-3.0 * cy,
            chest_yaw=10.0 - 5.0 * cy, chest_pitch=-14.5 - 1.4 * c2,
            chest_roll=1.6 * cy, head_yaw=-7.0 + 2.0 * cy,
            head_pitch=17.0 + 1.2 * c2,
            grp=BASE["grp"] + Vector((-0.005 * abs(cy), 0.010 * cy,
                                      0.020 + hz - 0.004 * c2)),
            gdir=BASE["gdir"] + Vector((0.0, 0.0, 0.05 * cy)),
            glp=BASE["glp"] + Vector((0.005 * abs(cy), -0.012 * cy,
                                      hz - 0.004 * c2)),
            ldir=BASE["ldir"] + Vector((0.0, 0.0, -0.04 * cy)),
            tailx=7.0 - 9.0 * cy, tailz=-7.0 - 3.0 * c2,
            csw=-5.0 + 4.0 * cy, clift=-1.5 - 2.0 * c2,
        ))
        P = PL.Frame(rig)
        PL.stance(P, dz=d["dz"], dx=d["dx"], legs=False,
                  hips_yaw=d["hips_yaw"], hips_pitch=d["hips_pitch"],
                  hips_roll=d["hips_roll"], spine_pitch=d["spine_pitch"],
                  chest_pitch=d["chest_pitch"], chest_yaw=d["chest_yaw"],
                  chest_roll=d["chest_roll"], head_pitch=d["head_pitch"],
                  head_yaw=d["head_yaw"], head_roll=d["head_roll"])
        for side, s, ph in (("R", 1, t), ("L", -1, (t + 0.5) % 1.0)):
            fp = foot_pitch(ph)
            A = Vector((s * 0.242, 0.010 + leg_y(ph),
                        S.foot_clear(fp) + leg_lift(ph)))
            P.leg(side, A, (s * 0.36, 1.0, 0.12), fp, s * 7.0)
        _hands(P, d)
        _extra(P, d)
        AH.ground(P, S)
        W.key(P, i)
    PL.finish_action(act)
    return act


# ══ 3. attack（40f）：两段都在腰线上 ════════════════════════════════════════
def a_attack(rig, D=40):
    """右匕前刺（f12）→ 顿 3 帧 → 左匕反手横扫（f26）→ 顿 → 回架。

    关键约束：**两把刀的刀尖全程不高于胸口**（z ≤ 1.10）。抬肘、过肩都不许做 ——
    那会把"腰间低持"读成"举刀砍"，五种状态之间混切就会跳。

    写法：握点全部写在**基准系**（= BASE 姿态下的世界点），出手的距离主要靠
    `_twist` 把上半身转出去带 —— 所以手臂不用伸直也能够到 0.26 m，
    肘始终是弯的，读起来是"腰发力"而不是"抡胳膊"。
    """
    def K(f, **kw):
        kw.setdefault("tw", 0.0)     # 手写世界坐标
        return _kd(f, **kw)

    keys = [
        K(0),
        # 蓄：躯干往回拧 12°（右肩后收），前手顺着力道往回带 8 cm，重心再沉 1 cm
        K(5, dz=DZ - 0.010, dy=-0.010, hips_yaw=4.0, chest_yaw=12.0,
            chest_pitch=-14.0, head_yaw=6.0, head_pitch=17.0,
            grp=Vector((0.256, 0.372, 0.944)),
            gdir=Vector((0.02, 0.72, -0.69)),
            glp=BASE["glp"] + Vector((0.0, -0.012, -0.004)),
            ldir=Vector((0.10, -0.86, -0.50)),
            tailx=15.0, csw=4.0, clift=-2.4),
        # 命中 f12：躯干拧出去 14°，前手再送 0.22 m —— 合起来 0.26 m 的刺
        K(12, dz=DZ - 0.004, dy=0.050, hips_yaw=14.0, chest_yaw=32.0,
            chest_pitch=-16.0, chest_roll=-2.0, head_yaw=-6.0, head_pitch=18.0,
            grp=Vector((0.206, 0.612, 0.972)),
            gdir=Vector((0.02, 0.99, -0.10)),
            rfoot=(0.250, 0.262, 4.0, 10.0),
            lfoot=(-0.240, -0.236, -4.0, -19.0),
            glp=BASE["glp"] + Vector((0.004, -0.014, -0.002)),
            tailx=-9.0, csw=9.0, clift=-0.6),
        # 顿帧 3 帧：只走 2 mm
        K(15, dz=DZ - 0.005, dy=0.048, hips_yaw=13.0, chest_yaw=31.0,
            chest_pitch=-16.0, chest_roll=-2.0, head_yaw=-6.0, head_pitch=18.0,
            grp=Vector((0.208, 0.604, 0.970)),
            gdir=Vector((0.02, 0.99, -0.10)),
            rfoot=(0.250, 0.260, 4.0, 10.0),
            lfoot=(-0.240, -0.234, -4.0, -19.0),
            glp=BASE["glp"] + Vector((0.004, -0.014, -0.002)),
            tailx=-8.0, csw=9.0, clift=-0.6),
        # 收右手、同时把左手从后胯往前带（第二段的起手）
        K(21, dz=DZ - 0.008, dy=0.016, hips_yaw=6.0, chest_yaw=14.0,
            chest_pitch=-14.0, head_yaw=4.0, head_pitch=17.0,
            grp=Vector((0.222, 0.418, 0.938)),
            gdir=Vector((-0.04, 0.86, -0.51)),
            glp=Vector((-0.436, -0.300, 1.000)),
            ldir=Vector((-0.10, -0.30, -0.95)),
            tailx=3.0, csw=2.0, clift=-1.4),
        # 左匕低刺 f26：左手沿自己那一侧送到 0.56（+0.29 m），刀身压平；
        # 躯干反向拧（chest_yaw 24→8），左肩顶出去给这一刀让路
        K(26, dz=DZ - 0.012, dy=0.034, hips_yaw=-4.0, chest_yaw=8.0,
            chest_pitch=-14.5, chest_roll=2.0, head_yaw=12.0, head_pitch=16.0,
            grp=Vector((0.216, 0.360, 0.918)),
            gdir=Vector((-0.08, 0.82, -0.57)),
            glp=Vector((-0.300, 0.566, 0.962)),
            ldir=Vector((0.04, 0.98, -0.18)),
            tailx=-13.0, csw=-2.0, clift=0.6),
        K(29, dz=DZ - 0.013, dy=0.032, hips_yaw=-4.0, chest_yaw=8.5,
            chest_pitch=-14.5, chest_roll=2.0, head_yaw=12.0, head_pitch=16.0,
            grp=Vector((0.218, 0.358, 0.916)),
            gdir=Vector((-0.08, 0.82, -0.57)),
            glp=Vector((-0.298, 0.558, 0.960)),
            ldir=Vector((-0.30, 0.84, -0.45)),
            tailx=-13.0, csw=-2.0, clift=0.6),
        # 回手：从身侧绕回去，刀尖朝外下，别让刃口扫过左腿
        K(32, dz=DZ - 0.008, dy=0.016, hips_yaw=2.0, chest_yaw=14.0,
           chest_pitch=-15.0, head_yaw=6.0, head_pitch=17.0,
           grp=Vector((0.226, 0.386, 0.936)),
           gdir=Vector((-0.16, 0.82, -0.55)),
           glp=Vector((-0.430, -0.190, 1.006)),
           ldir=Vector((-0.52, -0.40, -0.75)),
           tailx=1.0, csw=1.0, clift=-1.4),
        # 收势：回到腰间低持，方便混回 idle
        K(34, dz=DZ - 0.004, dy=0.006, hips_yaw=7.0, chest_yaw=22.0,
            chest_pitch=-14.0, head_yaw=4.0, head_pitch=17.0,
            grp=BASE["grp"] + Vector((0.006, 0.026, 0.006)),
            glp=Vector((-0.336, -0.300, 0.996)),
            ldir=Vector((0.14, -0.80, -0.58)),
            tailx=3.0, csw=3.0, clift=-1.4),
        K(40),
    ]
    return _baked(rig, "attack", keys, D)


# ══ 4. hurt（10f）══════════════════════════════════════════════════════════
def a_hurt(rig, D=10):
    keys = [
        _kd(0),
        # 中招：整条躯干后仰（pitch 由 −14 翻到 +4）、往左上侧闪，头被甩向右侧
        _kd(3, dz=DZ - 0.024, dx=-0.022, hips_yaw=-7.0, hips_pitch=2.0,
            chest_pitch=4.0, chest_roll=-8.0, chest_yaw=2.0,
            head_pitch=26.0, head_yaw=-16.0, head_roll=-9.0,
            grp=BASE["grp"] + Vector((-0.016, -0.032, 0.020)),
            gdir=Vector((-0.12, 0.72, -0.68)),
            glp=BASE["glp"] + Vector((-0.010, -0.018, -0.014)),
            ldir=Vector((0.16, -0.86, -0.48)),
            rfoot=(0.256, 0.196, 3.0, 12.0),
            lfoot=(-0.262, -0.226, -5.0, -16.0),
            tailx=18.0, csw=-1.0, clift=-3.4),
        _kd(6, dz=DZ - 0.010, dx=-0.008, hips_yaw=-4.0, hips_pitch=-2.0,
            chest_pitch=-8.0, chest_roll=-3.0, chest_yaw=6.0,
            head_pitch=21.0, head_yaw=-11.0, head_roll=-3.0,
            grp=BASE["grp"] + Vector((-0.006, -0.014, 0.008)),
            glp=BASE["glp"] + Vector((-0.004, -0.008, -0.006)),
            tailx=10.0, clift=-2.4),
        _kd(10),
    ]
    return _baked(rig, "hurt", keys, D)


# ══ 5. death（62f）：腿一软 → 跪下去 → 上身折到地上 → 定格 ════════════════
def a_death(rig, D=62):
    """死在**蹲姿**里：膝盖先软，上身顺着原有的前倾一路折到地面。

    为什么不往后倒：后倒要把整条躯干放平，披风会从身下顶出来，而且豺狼人的长吻
    会仰天支着；前折只是把已经压了 34° 的躯干再加 50°，腿的 IK 解和基准姿态同源，
    不会出现"腿飞起来"的折叠。双匕最后摊在双手两侧、刃面朝上。
    """
    act = PL.new_action(rig.arm, "death")
    W = PL.Writer(rig, loc_bones=LOC_BONES)

    def kd(f, **kw):
        d = dict(BASE)
        d["f"] = f
        d["tw"] = 0.0
        d.update(kw)
        return f, d

    keys = [
        kd(0),
        # 中招：胸口一挺、头后仰
        kd(4, dz=DZ - 0.016, dx=-0.016, hips_pitch=-3.0, chest_pitch=-6.0,
           chest_roll=-6.0, chest_yaw=20.0, head_pitch=28.0, head_yaw=-10.0,
           head_roll=-8.0,
           grp=BASE["grp"] + Vector((-0.026, -0.040, 0.018)),
           gdir=Vector((-0.20, 0.84, -0.50)),
           glp=BASE["glp"] + Vector((-0.014, -0.020, -0.010)),
           tailx=20.0, csw=10.0, clift=-3.4),
        # 膝盖软：整个人往下沉 14 cm，两只手往下散
        kd(12, dz=DZ - 0.140, dx=-0.020, dy=0.010, hips_pitch=-14.0,
           chest_pitch=-12.0, chest_roll=-4.0, chest_yaw=18.0,
           head_pitch=24.0, head_yaw=-4.0, head_roll=-5.0,
           grp=Vector((0.430, 0.400, 0.720)),
           gdir=Vector((-0.56, 0.62, -0.55)),
           glp=Vector((-0.470, -0.100, 0.780)),
           ldir=Vector((-0.62, -0.42, -0.66)),
           rfoot=(0.268, 0.246, 6.0, 12.0),
           lfoot=(-0.262, -0.236, -6.0, -20.0),
           tailx=16.0, csw=12.0, clift=-1.0),
        # 跪下去 + 上身开始折
        kd(22, dz=DZ - 0.300, dx=-0.010, dy=0.070, hips_pitch=-40.0,
           chest_pitch=-14.0, chest_roll=-2.0, chest_yaw=16.0,
           head_pitch=20.0, head_yaw=2.0, head_roll=-3.0,
           grp=Vector((0.452, 0.436, 0.400)),
           gdir=Vector((-0.62, 0.60, -0.50)),
           glp=Vector((-0.470, 0.395, 0.430)),
           ldir=Vector((-0.78, 0.42, -0.46)),
           rfoot=(0.276, 0.286, 12.0, 13.0),
           lfoot=(-0.268, -0.212, -4.0, -21.0),
           tailx=12.0, csw=14.0, clift=1.0),
        # 垮下去：跪坐 + 上身垂到膝上，双手摊在身体两侧的地上
        kd(32, dz=DZ - 0.380, dy=0.096, hips_pitch=-40.0,
           chest_pitch=-10.0, chest_roll=-2.0, chest_yaw=14.0,
           head_pitch=20.0, head_yaw=12.0, head_roll=-6.0,
           grp=Vector((0.442, 0.462, 0.120)),
           gdir=Vector((-0.34, 0.92, 0.06)), groll=84.0,
           glp=Vector((-0.480, 0.220, 0.140)),
           ldir=Vector((-0.10, 0.99, 0.06)), lroll=-86.0,
           rfoot=(0.280, 0.300, 16.0, 14.0),
           lfoot=(-0.272, -0.196, -2.0, -22.0),
           tailx=6.0, csw=15.0, clift=3.0),
        # 定格
        kd(40, dz=DZ - 0.392, dy=0.100, hips_pitch=-43.0,
           chest_pitch=-9.0, chest_roll=-2.0, chest_yaw=13.0,
           head_pitch=18.0, head_yaw=14.0, head_roll=-6.0,
           grp=Vector((0.444, 0.464, 0.104)),
           gdir=Vector((-0.34, 0.93, 0.06)), groll=84.0,
           glp=Vector((-0.482, 0.224, 0.124)),
           ldir=Vector((-0.10, 0.99, 0.06)), lroll=-86.0,
           rfoot=(0.280, 0.302, 17.0, 14.0),
           lfoot=(-0.272, -0.194, -2.0, -22.0),
           tailx=5.0, csw=15.0, clift=3.0),
    ]
    keys.append((D, dict(keys[-1][1], f=D)))
    PL.bake(keys, D, _emit(rig, W))
    PL.finish_action(act)
    return act


def build_all(arm, only=None):
    rig = PL.Rig(arm)
    _prep(rig)
    table = [("idle", a_idle), ("walk", a_walk), ("attack", a_attack),
             ("hurt", a_hurt), ("death", a_death)]
    out = []
    for name, fn in table:
        if only and name not in only:
            continue
        old = bpy.data.actions.get(name)
        if old:
            bpy.data.actions.remove(old)
        act = fn(rig)
        act.name = name
        act.use_fake_user = True
        out.append(name)
        print("[anim]", name, "frames", tuple(int(v) for v in act.frame_range))
    arm.animation_data.action = None
    for pb in arm.pose.bones:
        pb.matrix_basis.identity()
    return out
