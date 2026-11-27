"""anims_弓箭手.py —— 弓箭手六条动作（格网档 v3：举弓瞄准 / 行军步 / 后仰倒地）

v3 改的三件事：

1. **弓真正举起来**：左臂前伸到位（reach 0.44），弓腹朝瞄准线，弓轴竖直、上梢外倾 8°。
   弓握把由左肩 + 方向 + 距离推出来，躯干一转弓自动跟着走。
2. **行军步**：换 `anims_lib.march()`（26 帧、步幅 0.40、抬脚 0.155、胸胯 ±8° 反向），
   右臂反相摆 16 cm，弓随步轻微起伏 —— v2 的 0.25 步幅是"散步"的根源。
3. **死后仰倒地**：髋高链条 0.90 → 0.62 → 0.34 → 0.20，最后仰面躺平、
   双臂摊开、一条腿屈起，弓横在手边。`lift_fix` 只按身体兜底。
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = HERE
while not os.path.isdir(os.path.join(ROOT, "库")):
    _up = os.path.dirname(ROOT)
    if _up == ROOT:
        break
    ROOT = _up
for _p in (os.path.join(ROOT, "库"), os.path.join(ROOT, "联盟", "基准"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import anims_lib as A  # noqa: E402

NAME = "弓箭手"
ARROW_LEN = 1.02
POLE_L = (-0.74, 0.40, -0.54)     # 持弓臂：肘朝外下
POLE_R = (0.82, -0.30, 0.22)      # 拉弦臂：肘朝外后（略抬），不朝天


def bow_dirs(aim, cant=0.0):
    """由瞄准方向反解弓的两根轴：长轴（上下）⊥ aim，`cant` = 上梢外倾角。"""
    b = Vector(aim).normalized()
    up = Vector((0.0, 0.0, 1.0))
    lg = up - b * up.dot(b)
    if lg.length < 1e-4:
        lg = Vector((0.0, 1.0, 0.0))
    lg.normalize()
    side = lg.cross(b)
    if side.length > 1e-4:
        lg = (lg + side.normalized() * math.tan(math.radians(cant))).normalized()
    return lg, b


D = dict(
    dz=0.0, dx=0.0, dy=0.0,
    hy=0.0, hp=0.0, hr=0.0,
    sy=0.0, sp=0.0, sr=0.0,
    cy=0.0, cp=0.0, cr=0.0,
    hdy=0.0, hdp=0.0, hdr=0.0,
    fx_r=0.095, fy_r=0.015, fz_r=0.20, fp_r=0.0, fyaw_r=0.0,
    fx_l=-0.095, fy_l=0.015, fz_l=0.20, fp_l=0.0, fyaw_l=0.0,
    # 弓：瞄准方向 + 握点方向 + 左肩到掌心距离 + 上梢外倾
    ax=0.0, ay=1.0, az=0.02,
    gx=0.0, gy=0.26, gz=-0.965,
    reach=0.345,
    bow_up=0.0, cant=8.0,
    ux=0.0, uy=0.0, uz=0.0,          # 硬指弓长轴（倒地用）
    # 右手（拉弦 / 抽箭）
    wx=0.42, wy=0.02, wz=0.88,
    hook=0.0,
    pull=0.0,                        # 弦中点被拉弦手带走的比例（0 = 弦是直的）
    ascl=0.001,
    hipdrop=0.0, hipfwd=0.0,
)


def bake(P, p, i):
    A.stance(P, p)
    if p["hipdrop"] or p["hipfwd"]:
        P.solve_T()
        P.place("hips", P.T["hips"] + Vector((0.0, p["hipfwd"], -p["hipdrop"])))
    A.feet(P, p)
    P.solve_T()

    aim = Vector((p["ax"], p["ay"], p["az"]))
    if aim.length < 1e-5:
        aim = Vector((0.0, 1.0, 0.0))
    aim.normalize()
    gdir = Vector((p["gx"], p["gy"], p["gz"]))
    if gdir.length < 1e-5:
        gdir = aim.copy()
    gdir.normalize()
    S = P.T["upperarm_L"].copy()
    grip = S + gdir * p["reach"] + Vector((0.0, 0.0, p["bow_up"]))
    forced = Vector((p["ux"], p["uy"], p["uz"]))
    if forced.length > 1e-3:
        lg = forced.normalized()
        belly = aim - lg * aim.dot(lg)
        belly = belly.normalized() if belly.length > 1e-4 else Vector((0.0, 0.0, 1.0))
    else:
        lg, belly = bow_dirs(aim, p["cant"])
    A.hold(P, "L", grip, lg, -belly, POLE_L)

    if p["hook"] > 0.001:
        M = A.basis(-aim, (0.0, 0.0, 1.0))
        q = P.R["hand_R"].to_quaternion().slerp(M.to_quaternion(), p["hook"])
        P.set_world("hand_R", q.to_matrix())
    P.arm("R", Vector((p["wx"], p["wy"], p["wz"])), POLE_R)
    P.SCL["weapon_R"] = p["ascl"]

    # 箭：腕点 → 弓握把；用腕点当起点，手骨怎么转都不会把箭带歪
    if p["ascl"] > 0.5:
        P.solve_T()
        tail = P.T["hand_R"].copy()
        o = P.T["weapon_L"].copy()
        d = o - tail
        if d.length < 0.12:
            d = aim.copy()
        A.arrow_at(P, tail, tail + d.normalized() * ARROW_LEN, up=lg)


def string_pull(P, p, i):
    """弓弦：拉弦手把弦中点带走 → 上下两段各自转向"弓梢→中点"，再沿骨轴拉伸。

    必须放在 `anims_lib` 的 post 阶段（落地校正之后）算：脚贴地会把整个人往上
    顶 2~3 cm，姿态里算好的弦长就对不上掌心了（v3 实测差 9 cm）。
    弦是刚性的两段 loft（一根直的弦拉不开），骨缩放是这里唯一的形变手段。
    """
    pull = 0.0 if p is None else p.get("pull", 0.0)
    if pull <= 1e-4:
        return
    P.solve_T()
    palm = P.T["hand_R"] + (P.R["hand_R"] @ Vector((0.0, A.PALM_D, 0.0)))
    L0 = P.rig.L("bow_up")
    mid_rest = P.T["bow_up"] + (P.R["bow_up"] @ Vector((0.0, L0, 0.0)))
    mid = mid_rest.lerp(palm, min(1.0, pull))
    for bn in ("bow_up", "bow_dn"):
        d = mid - P.T[bn]
        if d.length < 1e-4:
            continue
        P.aim(bn, d)
        P.SCL[bn] = (1.0, max(0.2, d.length / max(P.rig.L(bn), 1e-5)), 1.0)


# ══ idle ════════════════════════════════════════════════════════════════════
#  弓挂在左手（弓背朝**前外**、弦朝身体，96 px 才认得出"这是弓"），右手自然垂；
#  呼吸 4 mm + 扫视 ±16°。
#
#  `aim` 是**弓背（凸面）**朝向，弦永远在它的反方向。v3 的 ax/ay 写反了
#  （弓背朝右后），于是待机/走路/受击三个动作里弦都朝外、弓腹贴脸 ——
#  读起来就是"弓拿反了"。这里把方向摆正：弓背朝左前、弦朝右后（身体内侧）。
CARRY = dict(ax=-0.92, ay=0.38, az=0.06, gx=-0.35, gy=0.72, gz=-0.60,
             reach=0.385, cant=0, bow_up=0.0)

IDLE = [
    (0,  dict(CARRY, wx=0.42, wy=0.02, wz=0.88)),
    (14, dict(CARRY, dz=0.004, hy=-4, cy=-4, hdy=-15, cp=1.2, hr=-1,
              wx=0.42, wy=0.03, wz=0.885)),
    (24, dict(CARRY, dz=0.002, hy=-5, cy=-5, hdy=-19, cp=1.0, hr=-1.5,
              wx=0.43, wy=0.04, wz=0.888)),
    (34, dict(CARRY, dz=0.0, hy=0, cy=0, hdy=0, cp=0, hr=0,
              wx=0.42, wy=0.02, wz=0.880)),
    (44, dict(CARRY, dz=0.004, hy=3, cy=3, hdy=13, cp=1.2, hr=1,
              wx=0.41, wy=0.00, wz=0.882)),
    (54, dict(CARRY, dz=0.002, hy=4, cy=4, hdy=16, cp=1.0, hr=1.2,
              wx=0.41, wy=-0.01, wz=0.885)),
    (60, dict(CARRY, wx=0.42, wy=0.02, wz=0.88)),
]

# ══ attack ══════════════════════════════════════════════════════════════════
#  0–4 举弓侧身 ｜ 4–9 右手过耳抽箭 ｜ 9–13 搭弦 ｜ 13–23 拉满
#  23–26 定住 ｜ 26 撒放 ｜ 26–38 送手 ｜ 38–54 收弓回挂
#
#  侧身角度是量出来的：胸 + 胯合计 −58°。再小，弓臂得横跨身体才够得到；
#  再大，拉弦肩缩到背后 0.35 m 以外，右手只剩直臂，肘立不起来。
#
#  拉弦手的位置按"下巴右侧"给：v3 把它放在 (0.48, −0.15, 1.32)，配上肘朝上，
#  从正面看就是"举弓投降"。现在是 (0.14, −0.02, 1.34)，肘朝外后。
AIM = dict(ax=0.0, ay=1.0, az=0.06, gx=0.26, gy=0.95, gz=0.08,
           reach=0.40, bow_up=0.02)

ATTACK = [
    (0,  dict(CARRY, wx=0.42, wy=0.02, wz=0.88)),
    (4,  dict(AIM, hy=-10, cy=-22, cp=-2, hdy=30, cant=10, reach=0.36,
              gx=0.34, gy=0.86, gz=0.30,
              fx_r=0.10, fy_r=-0.10, fx_l=-0.13, fy_l=0.10,
              wx=0.34, wy=-0.06, wz=1.20, ascl=0.001, pull=0.0, dz=-0.018)),
    (9,  dict(AIM, hy=-20, cy=-38, cp=-3, hdy=52, cant=8, reach=0.40,
              fx_r=0.10, fy_r=-0.12, fx_l=-0.13, fy_l=0.12,
              wx=0.28, wy=-0.12, wz=1.44, hook=0.35, ascl=0.001, pull=0.0,
              dz=-0.024)),
    (13, dict(AIM, hy=-20, cy=-38, cp=-3, hdy=52, cant=8, reach=0.395,
              fx_r=0.10, fy_r=-0.12, fx_l=-0.13, fy_l=0.12, hdp=3,
              wx=0.26, wy=0.20, wz=1.29, hook=0.7, ascl=1.0, pull=0.30,
              dz=-0.024)),
    (17, dict(AIM, hy=-20, cy=-38, cp=-2, hdy=50, cant=8, reach=0.395,
              fx_r=0.10, fy_r=-0.11, fx_l=-0.13, fy_l=0.11, hdp=3,
              wx=0.23, wy=0.10, wz=1.27, hook=1.0, ascl=1.0, pull=0.72,
              dz=-0.022)),
    (23, dict(AIM, hy=-20, cy=-38, cp=-3, hdy=46, cant=7, reach=0.395,
              fx_r=0.10, fy_r=-0.11, fx_l=-0.13, fy_l=0.11, hdp=3,
              wx=0.205, wy=-0.02, wz=1.258, hook=1.0, ascl=1.0, pull=1.0,
              dz=-0.022)),
    (26, dict(AIM, hy=-20, cy=-39, cp=-4, hdy=46, cant=6, reach=0.397,
              fx_r=0.10, fy_r=-0.11, fx_l=-0.13, fy_l=0.11, hdp=3,
              wx=0.203, wy=-0.03, wz=1.256, hook=1.0, ascl=1.0, pull=1.0,
              dz=-0.022)),
    # 撒放：弦先弹回（pull 掉到 0.16），手继续往后送
    (28, dict(AIM, hy=-19, cy=-35, cp=-3, hdy=44, cant=7, reach=0.397,
              fx_r=0.10, fy_r=-0.11, fx_l=-0.13, fy_l=0.11, hdp=3,
              wx=0.26, wy=-0.16, wz=1.27, hook=0.7, ascl=0.001, pull=0.16,
              dz=-0.018)),
    (33, dict(AIM, hy=-17, cy=-31, cp=-1, hdy=32, cant=8, reach=0.39,
              fx_r=0.10, fy_r=-0.09, fx_l=-0.13, fy_l=0.09,
              wx=0.28, wy=-0.14, wz=1.22, hook=0.3, ascl=0.001, pull=0.03,
              dz=-0.014)),
    (40, dict(hy=-11, cy=-20, cp=0, hdy=20, cant=9, gx=0.20, gy=0.70, gz=-0.30,
              ax=0.10, ay=0.86, az=0.05, reach=0.37,
              fx_r=0.10, fy_r=-0.05, fx_l=-0.13, fy_l=0.05,
              wx=0.40, wy=-0.06, wz=1.02, ascl=0.001, dz=-0.008)),
    (46, dict(CARRY, hy=-6, cy=-10, hdy=10, reach=0.36,
              fy_r=0.02, fy_l=0.02, wx=0.42, wy=0.0, wz=0.92, ascl=0.001)),
    (54, dict(CARRY, wx=0.42, wy=0.02, wz=0.88)),
]

# ══ hurt ════════════════════════════════════════════════════════════════════
HURT = [
    (0,  dict(CARRY, wx=0.42, wy=0.02, wz=0.88)),
    (2,  dict(CARRY, cp=11, hdp=15, dz=-0.018, dy=-0.022, hy=-4,
              reach=0.375, bow_up=-0.03, wx=0.40, wy=-0.02, wz=0.95)),
    (5,  dict(CARRY, cp=14, hdp=19, dz=-0.024, dy=-0.032, hy=-5, hr=-3,
              reach=0.36, bow_up=-0.05, wx=0.43, wy=-0.06, wz=0.97)),
    (8,  dict(CARRY, cp=5, hdp=7, dz=-0.008, dy=-0.010,
              reach=0.38, bow_up=-0.02, wx=0.38, wy=0.0, wz=0.90)),
    (14, dict(CARRY, wx=0.42, wy=0.02, wz=0.88)),
]

# ══ death ═══════════════════════════════════════════════════════════════════
#  后仰：腿一软 → 坐下去（髋 0.34）→ 背落地（髋 0.24）→ 仰面躺平（髋 0.20）
#  最后：双臂摊开、右膝屈起、头侧枕、弓横在手边。最低点按身体算。
DEATH = [
    (0,  dict(CARRY, wx=0.42, wy=0.02, wz=0.88)),
    (4,  dict(CARRY, cp=14, hdp=18, dz=-0.012, dy=-0.02, hy=-4, hr=-3,
              reach=0.37, wx=0.44, wy=-0.04, wz=0.94)),
    (12, dict(CARRY, cp=4, sp=4, dz=-0.12, dy=-0.02, hy=-2, hr=-6,
              fy_r=0.06, fz_r=0.24, fp_r=-30, fy_l=-0.02, fz_l=0.24, fp_l=-30,
              ax=0.1, ay=0.9, az=-0.2, reach=0.34,
              wx=0.46, wy=-0.10, wz=0.80)),
    # 坐下（髋 0.34），弓开始横过来
    (22, dict(ax=0.20, ay=0.90, az=-0.30, ux=0.92, uy=-0.39, uz=0.0, gx=0.25, gy=0.55, gz=-0.80,
              reach=0.34, cp=-6, sp=-4, hipdrop=0.56, hipfwd=-0.10,
              hr=-10, hy=-2, fy_r=0.20, fz_r=0.20, fp_r=-16,
              fy_l=0.10, fz_l=0.24, fp_l=-22, wx=0.50, wy=-0.16, wz=0.60)),
    # 背落地（髋 0.24）
    (34, dict(ax=0.30, ay=0.86, az=-0.40, ux=0.96, uy=-0.28, uz=0.0, gx=0.30, gy=0.40, gz=-0.86,
              reach=0.30, hp=44, cp=-10, sp=-4, hipdrop=0.66, hipfwd=-0.26,
              hr=-10, hy=-3, fy_r=0.30, fz_r=0.16, fp_r=-4,
              fy_l=0.22, fz_l=0.18, fp_l=-8, fx_r=0.16, fx_l=-0.18,
              pz_r=0.5, pz_l=0.5, wx=0.52, wy=-0.22, wz=0.40)),
    # 仰面躺平（髋 0.20）：双臂摊开、右膝屈起、头侧枕
    (46, dict(ax=0.10, ay=0.99, az=0.05, ux=0.99, uy=-0.14, uz=0.02,
              gx=-0.90, gy=0.10, gz=-0.42, reach=0.30,
              hp=86, cp=-6, sp=-2, hipdrop=0.700, hipfwd=-0.48,
              hr=-6, hy=-4, hdp=18, hdy=-20, hdr=7,
              fy_r=0.34, fz_r=0.09, fp_r=0,
              fy_l=0.10, fz_l=0.13, fp_l=-6, fx_l=-0.16, pz_l=0.9,
              wx=0.50, wy=-0.20, wz=0.14)),
    (58, dict(ax=0.10, ay=0.99, az=0.05, ux=0.99, uy=-0.14, uz=0.02,
              gx=-0.90, gy=0.10, gz=-0.42, reach=0.30,
              hp=87, cp=-5, sp=-2, hipdrop=0.701, hipfwd=-0.48,
              hr=-6, hy=-4, hdp=18, hdy=-22, hdr=8,
              fy_r=0.34, fz_r=0.09, fp_r=0,
              fy_l=0.10, fz_l=0.13, fp_l=-6, fx_l=-0.16, pz_l=0.9,
              wx=0.50, wy=-0.20, wz=0.14)),
]

# ══ cast ════════════════════════════════════════════════════════════════════
#  举弓朝天（齐射号令）：弓面转到正面，右手抬起示意
CAST = [
    (0,  dict(CARRY, wx=0.42, wy=0.02, wz=0.88)),
    (10, dict(ax=0.1, ay=0.30, az=0.95, gx=0.22, gy=0.55, gz=0.80, reach=0.36, cant=16,
              cy=-8, cp=4, hdp=8, dz=0.006, wx=0.34, wy=0.10, wz=1.02)),
    (20, dict(ax=0.15, ay=0.22, az=0.96, gx=0.26, gy=0.50, gz=0.83, reach=0.42, cant=18,
              cy=-4, cp=10, hdp=16, dz=0.018, fy_r=0.04, fy_l=-0.02,
              wx=0.30, wy=0.18, wz=1.24)),
    (28, dict(ax=0.15, ay=0.20, az=0.97, gx=0.26, gy=0.50, gz=0.83, reach=0.42, cant=18,
              cy=-3, cp=9, hdp=14, dz=0.016,
              wx=0.30, wy=0.18, wz=1.22)),
    (36, dict(CARRY, reach=0.39, wx=0.40, wy=0.06, wz=0.94)),
    (44, dict(CARRY, wx=0.42, wy=0.02, wz=0.88)),
]


def _m(arm, name, end, keys, loop=False):
    return A.make(arm, name, end, [(f, dict(D, **k)) for f, k in keys], bake,
                  loop=loop, scl=("weapon_R", "bow_up", "bow_dn"),
                  post=string_pull)


# ══ walk：解析式（支撑脚匀速后移）══════════════════════════════════════════
WALK_END = 26


def walk_pose(P, i, end):
    """行军步：左手持弓只做小幅反相，右臂自由摆 16 cm，弓随步频轻起伏。"""
    ph = (i % end) / float(end)
    p = dict(D, **CARRY)
    p.update(A.march(ph, stride=0.40, lift=0.155, lean=7.0, arm=1.0))
    swing = math.cos(2.0 * math.pi * ph)
    p["wx"] = 0.42
    p["wy"] = 0.02 - 0.16 * swing
    p["wz"] = 0.88 + 0.012 * abs(math.sin(2.0 * math.pi * ph))
    p["bow_up"] = 0.014 * math.sin(4.0 * math.pi * ph)
    p["cant"] = 10.0 + 3.0 * swing
    p["hdy"] = 1.6 * swing
    A.stance(P, p)
    A.feet(P, p)
    P.solve_T()
    aim = Vector((p["ax"], p["ay"], p["az"])).normalized()
    gdir = Vector((p["gx"], p["gy"], p["gz"])).normalized()
    lg, belly = bow_dirs(aim, p["cant"])
    S = P.T["upperarm_L"].copy()
    grip = S + gdir * p["reach"] + Vector((0.0, 0.0, p["bow_up"]))
    A.hold(P, "L", grip, lg, -belly, POLE_L)
    P.set_world("hand_R", A.basis((0.0, 0.34 * swing, -0.94), (0.0, 0.0, 1.0)))
    P.arm("R", Vector((p["wx"], p["wy"], p["wz"])), POLE_R)
    P.SCL["weapon_R"] = 0.001


# ══ icon：图标用的英雄姿势 ═══════════════════════════════════════════════════
#  弓斜举在身前（弓面 3/4 朝镜头，弧线读得出来）、右手搭在箭筒上。
ICON = dict(dict(CARRY, ax=-0.86, ay=0.44, az=0.06, gx=-0.52, gy=0.60, gz=-0.61,
                 reach=0.40, cant=16, bow_up=0.02),
            hy=-6, cy=-12, hdy=-10, cp=0.5, wx=0.44, wy=-0.06, wz=1.02)


def pose_icon(arm):
    A.make(arm, "icon", 0, [(0, dict(D, **ICON))], bake,
           scl=("weapon_R", "bow_up", "bow_dn"), post=string_pull)
    A.pose_at(arm, "icon", 0)


def build_all(arm):
    _m(arm, "idle", 60, IDLE, loop=True)
    A.make_fn(arm, "walk", WALK_END, walk_pose, loop=True,
              scl=("weapon_R", "bow_up", "bow_dn"), post=string_pull)
    _m(arm, "attack", 54, ATTACK)
    _m(arm, "hurt", 14, HURT)
    _m(arm, "death", 58, DEATH)
    _m(arm, "cast", 44, CAST)
    return ["idle", "walk", "attack", "hurt", "death", "cast"]


def pose_at(arm, action, frame):
    A.pose_at(arm, action, int(frame))
