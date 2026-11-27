"""anims_长枪兵.py —— 长枪兵六条动作（格网档 v3：双手突刺 / 行军步 / 跪倒前扑）

v2 被指出的三个问题，这一版逐条对应：

1. **攻击是单手** —— v3 用 `anims_lib.two_hand_points()`：**两只手各给世界点**，
   枪轴由"后手→前手"定死，前送靠 `slide`（枪在手里滑）。这样"双手掐杆"与
   "枪往前扎"同时成立，前手也不会被枪轴拽出够得着的范围（v2 的掌-轴偏差 0.15 m）。
   几何上"双手 + 枪指正前"做不到（肩距 0.76 / 臂长 0.40），所以是**侧身斜刺**：
   枪轴 45°，靠胸/胯反向拧 40° 把枪口对到正前。
2. **走路像散步/大猩猩** —— `anims_lib.march()`：26 帧一周期、步幅 0.40、
   抬脚 0.155、骨盆两步一周期起伏、胸胯 ±8° 反向、左臂摆 0.16。
3. **死在半空 / 肢体怪** —— 死亡改成明确的髋高链条：跪（髋 0.46）→ 前扑（髋 0.26）
   → 面朝下（髋 0.20），双手前伸撑地、右膝屈在身下、头侧枕，枪滑到身侧。
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

NAME = "长枪兵"
POLE_R = (0.74, 0.26, -0.62)      # 右臂：肘朝外下
POLE_L = (-0.64, 0.44, -0.62)     # 左臂：肘朝外下前

D = dict(
    dz=0.0, dx=0.0, dy=0.0,
    hy=0.0, hp=0.0, hr=0.0,
    sy=0.0, sp=0.0, sr=0.0,
    cy=0.0, cp=0.0, cr=0.0,
    hdy=0.0, hdp=0.0, hdr=0.0,
    fx_r=0.100, fy_r=0.015, fz_r=0.20, fp_r=0.0, fyaw_r=0.0,
    fx_l=-0.100, fy_l=0.015, fz_l=0.20, fp_l=0.0, fyaw_l=0.0,
    # 双手持枪：两只手掌心（世界）+ 沿枪轴前送
    rx=0.40, ry=0.15, rz=0.80,        # 后手（右）
    lx=-0.20, ly=0.24, lz=0.95,       # 前手（左）；two=0 时是自由手的目标
    slide=0.0,
    two=0,                            # 1 = 两只手都在枪上
    front="L",                        # 哪只手在前（枪尖朝哪）
    # 自由手（单手待机/行军）时枪的轴向
    sax=0.02, say=-0.05, saz=0.999,
    # 自由左手的朝向（手骨 +Y）；倒地时指前，站立时指下
    lhx=0.0, lhy=0.30, lhz=-0.95,
    # 刃面朝向（骨 +X）：默认竖直，图标里改成"朝镜头"才看得见叶刃的宽面
    xbx=0.0, xby=0.0, xbz=1.0,
    hipdrop=0.0, hipfwd=0.0,
)


def bake(P, p, i):
    A.stance(P, p)
    if p["hipdrop"] or p["hipfwd"]:
        P.solve_T()
        P.place("hips", P.T["hips"] + Vector((0.0, p["hipfwd"], -p["hipdrop"])))
    A.feet(P, p)
    P.solve_T()
    pr = Vector((p["rx"], p["ry"], p["rz"]))
    if p["two"]:
        A.two_hand_points(P, pr, Vector((p["lx"], p["ly"], p["lz"])),
                          POLE_R, POLE_L, slide=p["slide"],
                          x_hint=(0.0, 0.0, 1.0), front=p["front"])
    else:
        ydir = Vector((p["sax"], p["say"], p["saz"]))
        if ydir.length < 1e-5:
            ydir = Vector((0.0, 0.0, 1.0))
        ydir.normalize()
        xdir = Vector((p["xbx"], p["xby"], p["xbz"]))
        if xdir.length < 1e-5 or abs(xdir.normalized().dot(ydir)) > 0.95:
            xdir = Vector((1.0, 0.0, 0.0))
        A.hold(P, "R", pr, ydir, xdir, POLE_R, slide=p["slide"])
        P.set_world("hand_L", A.basis((p["lhx"], p["lhy"], p["lhz"]), (0.0, 0.0, 1.0)))
        P.arm("L", Vector((p["lx"], p["ly"], p["lz"])), POLE_L)


# ══ idle ════════════════════════════════════════════════════════════════════
#  枪拄地（鐏 z=0）、右手在胯侧握把、左手搭在腰带上。呼吸 4 mm + 扫视 ±15°。
STAND = dict(rx=0.43, ry=0.20, rz=0.860, sax=0.02, say=-0.05, saz=0.9985,
             slide=-0.052, two=0, lx=-0.22, ly=0.32, lz=0.92)

IDLE = [
    (0,  dict(STAND)),
    (14, dict(STAND, dz=0.004, hy=-3, cy=-4, hdy=-14, cp=1.0, hr=-1,
              ry=0.205, lx=-0.225, ly=0.325, lz=0.922)),
    (24, dict(STAND, dz=0.002, hy=-4, cy=-5, hdy=-17, cp=0.8, hr=-1.2,
              ry=0.205, lx=-0.228, ly=0.330, lz=0.923)),
    (34, dict(STAND, dz=0.0, hy=0, cy=0, hdy=0, cp=0, hr=0,
              lx=-0.220, ly=0.320, lz=0.920)),
    (44, dict(STAND, dz=0.004, hy=3, cy=4, hdy=12, cp=1.0, hr=1,
              ry=0.195, lx=-0.216, ly=0.312, lz=0.922)),
    (54, dict(STAND, dz=0.002, hy=3, cy=4, hdy=14, cp=0.8, hr=1.2,
              ry=0.195, lx=-0.214, ly=0.310, lz=0.923)),
    (60, dict(STAND)),
]

# ══ attack ══════════════════════════════════════════════════════════════════
#  v4：**单手直刺**。v3 用双手两点定枪轴，在"肩距 0.76 / 臂长 0.40"的手短条件下，
#  两点连线必然和身体朝向差 40~60°，结果就是"枪先穿过身体、再向斜右扎出去"。
#  长枪最本分的刺法是：**右手单手端枪、枪轴直接压在正前方**，左臂向后甩做平衡。
#  唯一的要求是掌心前送 + 枪在手里前滑，两段加起来给足枪尖行程。
#
#  0–6   提枪：枪从拄地立起来，收左手
#  6–12  蓄力：枪轴压平（枪尖抬 12°）、重心后坐、右肩后拉
#  12–18 突刺：掌心前送 0.34 m + 机枪前滑 0.50 m，髋前送、前腿压步
#  18–24 命中保持（2 mm 抖动）
#  24–34 收枪、撤步
#  34–48 立枪回站
TH = dict(hy=12, sy=5, cy=16, cp=-4, hdy=-20, hdp=2)

# 提枪：右肘收到腰侧，枪斜指前上 45°，左手抬到胸前护住中线
READY = dict(two=0, front="R", rx=0.41, ry=0.10, rz=1.00,
             sax=0.05, say=0.70, saz=0.71, slide=-0.09,
             xbx=0.0, xby=0.0, xbz=1.0,
             lx=-0.29, ly=0.20, lz=1.02, lhx=-0.30, lhy=0.55, lhz=-0.78, **TH)
# 蓄力：枪轴压到 16°，右手后拉、掌心回收，髋后坐、右肩再往后
WIND = dict(READY, rx=0.41, ry=0.00, rz=1.02,
            sax=0.06, say=0.96, saz=0.27, slide=-0.17,
            hy=16, sy=6, cy=20, cp=-5, hdy=-26, hdp=3,
            dz=-0.030, fy_r=0.11, fy_l=-0.11, fp_r=-4,
            lx=-0.27, ly=0.23, lz=1.07)
# 突刺：掌心前送、枪沿自身轴前滑、髋前送、前腿压步、左臂后甩
THRUST = dict(READY, rx=0.33, ry=0.40, rz=1.02,
              sax=0.02, say=0.9995, saz=-0.03, slide=0.50,
              hy=7, sy=3, cy=11, cp=-9, hdy=-10, hdp=-3,
              hipfwd=0.10, dz=-0.042, hr=1,
              fy_r=0.22, fy_l=-0.14, fp_r=7, fp_l=-17, fyaw_r=-4,
              lx=-0.45, ly=-0.17, lz=0.90, lhx=0.10, lhy=-0.62, lhz=-0.78)
HOLD = dict(THRUST, slide=0.52, ry=0.418, hipfwd=0.105, dz=-0.043)

ATTACK = [
    (0,  dict(STAND)),
    (6,  dict(READY, dz=-0.010, fy_r=0.03, fy_l=-0.04)),
    (12, dict(WIND)),
    (18, dict(THRUST)),
    (24, dict(HOLD)),
    (30, dict(READY, slide=0.04, ry=0.16, rz=0.99, dz=-0.014, hipfwd=0.03,
              hy=9, cy=12, fy_r=0.13, fy_l=-0.07, hr=0.5)),
    (38, dict(STAND, hy=-5, cy=-9, hdy=11, cp=-2, slide=-0.02,
              rx=0.40, ry=0.17, rz=0.90, sax=0.05, say=0.22, saz=0.97,
              lx=-0.26, ly=0.27, lz=0.99, fy_r=0.04, fy_l=-0.02, dz=-0.006)),
    (48, dict(STAND)),
]

# ══ hurt ════════════════════════════════════════════════════════════════════
HURT = [
    (0,  dict(STAND)),
    (2,  dict(STAND, cp=11, hdp=15, dz=-0.016, dy=-0.02, hy=-3,
              ry=0.14, rz=0.815, sax=0.10, say=-0.22, saz=0.97, slide=-0.01,
              lx=-0.19, ly=0.26, lz=0.94)),
    (5,  dict(STAND, cp=14, hdp=19, dz=-0.022, dy=-0.03, hy=-4, hr=-3,
              ry=0.13, rz=0.83, sax=0.14, say=-0.30, saz=0.94, slide=0.0,
              lx=-0.18, ly=0.28, lz=0.93)),
    (8,  dict(STAND, cp=5, hdp=7, dz=-0.008, dy=-0.01, slide=-0.005)),
    (14, dict(STAND)),
]

# ══ death ═══════════════════════════════════════════════════════════════════
#  站立 → 膝一软 → 单膝跪（髋 0.46）→ 前扑（髋 0.28）→ 面朝下（髋 0.20）
#  最后：双手前伸撑地、右膝屈在身下、头侧枕，枪横在手边。
DEATH = [
    (0,  dict(STAND)),
    (4,  dict(STAND, cp=12, hdp=16, dz=-0.012, dy=-0.02, hy=-4, slide=-0.02,
              rx=0.42, ry=0.10, rz=0.79, lx=-0.20, ly=0.26, lz=0.94)),
    (10, dict(STAND, hp=-8, cp=14, sp=6, dz=-0.10, hy=-4, hr=-3, hdp=10,
              ry=0.10, rz=0.66, sax=-0.10, say=-0.28, saz=0.80, slide=0.02,
              fy_r=0.02, fz_r=0.22, fp_r=-16, fy_l=-0.04, fz_l=0.22, fp_l=-16,
              lx=-0.30, ly=0.26, lz=0.72)),
    # 单膝跪：左膝落地（踝在身后），右脚撑住；髋 0.46
    (20, dict(STAND, hp=-18, cp=16, sp=6, hipdrop=0.44, hipfwd=0.06,
              hy=-6, hr=-4, hdp=4, hdy=-8,
              ry=0.16, rz=0.52, sax=-0.06, say=0.55, saz=0.58, slide=0.10,
              fy_r=0.12, fz_r=0.20, fp_r=-4,
              fy_l=-0.16, fz_l=0.10, fp_l=-46, pz_l=0.55,
              lx=-0.30, ly=0.30, lz=0.56)),
    # 前扑：髋下沉到 0.30 并前送，双手向前撑地
    (30, dict(STAND, hp=-52, cp=14, sp=6, hipdrop=0.57, hipfwd=0.30,
              hy=-6, hr=-3, hdp=-8, hdy=-14,
              ry=0.20, rz=0.30, sax=-0.04, say=0.62, saz=0.34, slide=0.18,
              fy_r=0.04, fz_r=0.14, fp_r=-8,
              fy_l=-0.18, fz_l=0.11, fp_l=-22, pz_l=0.7,
              lx=-0.28, ly=0.84, lz=0.22)),
    # 面朝下：髋 (0, 0.55, 0.20)，双手前伸撑地、右膝微屈、头侧枕
    (42, dict(STAND, hp=-88, cp=3, sp=1, hipdrop=0.655, hipfwd=0.56,
              lhx=0.0, lhy=1.0, lhz=0.0,
              hy=-4, hr=-2, hdp=-4, hdy=-18, hdr=9,
              ry=0.24, rz=0.12, sax=-0.02, say=0.99, saz=0.04, slide=0.26,
              fy_r=0.10, fz_r=0.10, fp_r=0,
              fy_l=-0.24, fz_l=0.10, fp_l=-6, pz_l=0.9,
              lx=-0.26, ly=1.30, lz=0.13)),
    (60, dict(STAND, hp=-89, cp=2, sp=1, hipdrop=0.656, hipfwd=0.56,
              lhx=0.0, lhy=1.0, lhz=0.0,
              hy=-4, hr=-2, hdp=-4, hdy=-20, hdr=10,
              ry=0.24, rz=0.12, sax=-0.02, say=0.99, saz=0.04, slide=0.26,
              fy_r=0.10, fz_r=0.10, fp_r=0,
              fy_l=-0.24, fz_l=0.10, fp_l=-6, pz_l=0.9,
              lx=-0.26, ly=1.30, lz=0.13)),
]

# ══ cast ════════════════════════════════════════════════════════════════════
#  举枪朝天（齐刺号令）：双手上杆、枪轴立到 70°，抬头。
#  两只手**都留在身体右侧**（x 0.22~0.34）—— v3 的后手放在中线 (x=−0.02)，
#  枪轴从右腰斜穿到脸上，枪杆正好从鼻梁前面过去。
CAST = [
    (0,  dict(STAND)),
    (10, dict(two=1, front="L", rx=0.38, ry=0.16, rz=1.06,
              lx=0.38, ly=0.18, lz=1.34, slide=0.26,
              cy=-6, cp=4, hdp=10, dz=0.004)),
    (20, dict(two=1, front="L", rx=0.38, ry=0.15, rz=1.04,
              lx=0.38, ly=0.17, lz=1.42, slide=0.34,
              cy=-4, cp=9, hdp=16, dz=0.012,
              fy_r=0.03, fy_l=-0.01)),
    (28, dict(two=1, front="L", rx=0.38, ry=0.15, rz=1.04,
              lx=0.38, ly=0.17, lz=1.42, slide=0.34,
              cy=-3, cp=8, hdp=14, dz=0.010)),
    (36, dict(STAND, two=0, rx=0.38, ry=0.15, rz=0.86, sax=0.0, say=0.0, saz=1.0,
              slide=0.12, cy=-2, cp=2, hdy=2, lx=-0.22, ly=0.26, lz=0.98)),
    (44, dict(STAND)),
]


def _m(arm, name, end, keys, loop=False):
    return A.make(arm, name, end, [(f, dict(D, **k)) for f, k in keys], bake, loop=loop)


# ══ walk：解析式（支撑脚匀速后移）══════════════════════════════════════════
WALK_END = 26


def walk_pose(P, i, end):
    """行军步：枪斜扛在右胯前（鐏后下沉、尖前上挑），左臂反相摆 16 cm。"""
    ph = (i % end) / float(end)
    p = dict(D, **STAND)
    p.update(A.march(ph, stride=0.40, lift=0.155, lean=8.0, arm=1.0))
    swing = math.cos(2.0 * math.pi * ph)
    p["two"] = 0
    p["slide"] = -0.02 + 0.02 * swing
    p["sax"], p["say"], p["saz"] = 0.03, 0.36 + 0.03 * swing, 0.93
    p["rx"], p["ry"], p["rz"] = 0.42, 0.20 + 0.012 * swing, 0.94 + 0.010 * abs(swing)
    p["lx"] = -0.40 + 0.02 * swing
    p["ly"] = 0.02 - 0.16 * swing
    p["lz"] = 0.90 + 0.012 * abs(math.sin(2.0 * math.pi * ph))
    p["hdy"] = 1.6 * swing
    A.stance(P, p)
    A.feet(P, p)
    P.solve_T()
    ydir = Vector((p["sax"], p["say"], p["saz"])).normalized()
    A.hold(P, "R", Vector((p["rx"], p["ry"], p["rz"])), ydir, (0.0, 0.0, 1.0),
           POLE_R, slide=p["slide"])
    P.set_world("hand_L", A.basis((0.0, 0.34 * swing, -0.94), (0.0, 0.0, 1.0)))
    P.arm("L", Vector((p["lx"], p["ly"], p["lz"])), POLE_L)


# ══ icon：图标用的英雄姿势（不导出，只给 icon_vox 渲一张）════════════════════
#  枪斜拄在右脚边（斜 38°）、左手搭腰带、胸微转向镜头 —— 斜线比竖线更像"旗"，
#  也让 2.25 m 的枪塞进 512 的画面里（竖枪会顶出画框）。
ICON = dict(STAND, rx=0.30, ry=0.10, rz=0.70,
            sax=0.32, say=0.56, saz=0.76, slide=-0.02,
            xbx=0.90, xby=0.44, xbz=0.0,
            hy=-7, cy=-12, hdy=-4, cp=0.5,
            lx=-0.20, ly=0.26, lz=0.95)


def pose_icon(arm):
    A.make(arm, "icon", 0, [(0, dict(D, **ICON))], bake)
    A.pose_at(arm, "icon", 0)


def build_all(arm):
    _m(arm, "idle", 60, IDLE, loop=True)
    A.make_fn(arm, "walk", WALK_END, walk_pose, loop=True)
    _m(arm, "attack", 48, ATTACK)
    _m(arm, "hurt", 14, HURT)
    _m(arm, "death", 60, DEATH)
    _m(arm, "cast", 44, CAST)
    return ["idle", "walk", "attack", "hurt", "death", "cast"]


def pose_at(arm, action, frame):
    A.pose_at(arm, action, int(frame))
