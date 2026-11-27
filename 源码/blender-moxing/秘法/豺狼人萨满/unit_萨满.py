"""unit_萨满.py —— 野怪·豺狼人萨满（精模 / 硬边支线）v2

**一句话**：1.95 m 的蓝皮豺狼人 —— 长吻大耳 + 鬃冠 + 驼背 + 反关节腿，右手一根
顶着青辉宝珠的骨爪巫杖。

v2 修的三件事（v1 的病根）：
  ① **皮肤只有一档亮蓝 → 读成塑料**。v2 上三档：皮肤暗(腹侧/内侧/下颌底/指缝/尾腹)
     < 皮肤(主体) < 皮肤亮(背脊/三角肌顶/大腿外/颅顶，≤15%)。
  ② **躯干是一根筒** → 拆成 胸(左右两块胸肌 + 中间 2 cm 胸沟) / 腹(三道腹肌横条，
     条间是皮肤暗) / 胯(独立骨盆体，比腰宽 5 cm)，三段之间还有 2.7~3 cm 的暗缝。
  ③ **腿是直的** → 三段折线做实：大腿 31° 前倾(直径 0.245) → 小腿 40° 后折(0.155)
     → 跖骨接近竖直(0.115) → 三趾爪(每趾 2 节 + 骨色尖爪，趾间 1.5 cm 缝)。

造型口径：
  * 1 unit = 1 m，+Y 正面，+X = 角色右侧，脚底 z = 0，原点在双足中间；
  * 站直头顶 1.950，包围盒约 2.02（耳尖 + 鬃冠）；
  * 一块 = 一根骨、权重 1.0；关节留缝，缝里是 `皮肤暗` / `皮革暗` 内胆；
  * 笔触：`chunk`（6 mm 单段倒角）给皮肤体积，`chunk2` 给骨甲，`facet` 给内胆，
    `sharp` 给电弧 —— **`soft` 一件都不用**。

配色秩序（9 味，蓝是最大色块，队色只走布与战纹）：
  皮革暗 0.05 < 皮肤暗 0.09 < 皮革 0.13 < 皮肤 0.20 < 皮肤亮 0.30 < 骨 0.62 < 辉
  （原 `锈铁` 让位给 `皮肤亮`：几处小件金属改成 `骨`，材质数锁在 9）

组件化（MODULES）：四层
  body   躯干三段 / 四肢 / 反关节腿 / 三趾爪 / 尾 / 腰布 + 骨珠腰带 / 左肩骨甲 / 绑带
  head   颅 + 长吻 + 下颌 + 獠牙 + 大三角耳 + 鬃冠 + 额骨
  staff  巫杖（六边木杆 + 3 道骨环 + 缠皮 + 骨爪托 + 宝珠 + 杖尾骨坠）—— 骨轴 = 杖身
  fx     两根绕杖顶盘旋的折线电弧（按 1/40 建，静止藏在宝珠里）
"""
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = HERE
while not os.path.isdir(os.path.join(ROOT, "库")):
    _up = os.path.dirname(ROOT)
    if _up == ROOT:
        break
    ROOT = _up
LIB = os.path.join(ROOT, "库")
for _p in (LIB, HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import unitkit2 as K  # noqa: E402
import unitkit as KU  # noqa: E402

NAME = "豺狼人萨满"
PREFIX = "gs"

# ── 尺寸表（m）──────────────────────────────────────────────────────────────
Z_HIP = 1.020
Z_WAIST = 1.120
Z_CH0 = 1.270
Z_SHLD = 1.575
Z_NECK = 1.545
Z_HEAD = 1.628
Z_TOP = 1.950

HIP_X = 0.200
LEG_X = 0.190
SH_X = 0.280

# 反关节腿（三段折线）：髋 → 膝(前下 31°) → 跖骨根(后下 40°) → 掌(接近竖直) → 趾尖
HIP_R = Vector((0.200, -0.020, 1.020))
KNE_R = Vector((0.216, 0.170, 0.700))
HCK_R = Vector((0.196, -0.145, 0.330))
BAL_R = Vector((0.192, -0.130, 0.100))
TOE_R = Vector((0.192, 0.190, 0.018))

L_THIGH = (KNE_R - HIP_R).length
L_SHIN = (HCK_R - KNE_R).length
L_FOOT = (BAL_R - HCK_R).length
L_TOE = (TOE_R - BAL_R).length
L_UPPER, L_FORE = 0.365, 0.300

SH_R = Vector((SH_X, -0.010, Z_SHLD))
SH_L = Vector((-SH_X, -0.010, Z_SHLD))

# 巫杖：杖身竖直立在**身体右前方**（不许挡脸）；骨轴 = 杖身，+Y 局部 = 杖顶
GRIP = Vector((0.338, 0.300, 1.150))
STAFF_X, STAFF_Y = GRIP.x, GRIP.y
STAFF_BUTT = 0.148
STAFF_TOP = 1.856
ORB_C = Vector((STAFF_X, STAFF_Y, 1.952))
ORB_R = 0.055
ORB_H = 0.062
FX_K = 1.0 / 40.0

WRI_R = GRIP - (GRIP - SH_R).normalized() * 0.082
WRI_L = Vector((-0.388, 0.140, 0.972))

HIP_L = Vector((-HIP_R.x, HIP_R.y, HIP_R.z))
KNE_L = Vector((-KNE_R.x, KNE_R.y, KNE_R.z))
HCK_L = Vector((-HCK_R.x, HCK_R.y, HCK_R.z))
BAL_L = Vector((-BAL_R.x, BAL_R.y, BAL_R.z))
TOE_L = Vector((-TOE_R.x, TOE_R.y, TOE_R.z))


def ik2(root, target, l1, l2, pole):
    root, target = Vector(root), Vector(target)
    d = target - root
    dist = min(d.length, (l1 + l2) * 0.999)
    dn = d.normalized()
    a = (l1 * l1 - l2 * l2 + dist * dist) / (2 * dist)
    h = math.sqrt(max(l1 * l1 - a * a, 0.0))
    p = Vector(pole) - dn * Vector(pole).dot(dn)
    if p.length < 1e-6:
        p = Vector((0, 0, 1)) - dn * dn.z
    p.normalize()
    return root + dn * a + p * h


ELB_R = ik2(SH_R, WRI_R, L_UPPER, L_FORE, (0.40, -0.60, -1.00))
ELB_L = ik2(SH_L, WRI_L, L_UPPER, L_FORE, (-1.0, -0.30, 0.15))

HDIR_R = (GRIP - WRI_R).normalized()
HDIR_L = Vector((0.0, 0.28, -0.96)).normalized()

# 尾巴：根 0.12 → 前段 0.09 → 末端 0.06，尾尖一撮深色毛
TAIL0 = Vector((0.0, -0.168, 1.000))
TAIL1 = Vector((0.046, -0.420, 0.902))
TAIL2 = Vector((0.104, -0.722, 0.736))


# ── 骨架（28 根）────────────────────────────────────────────────────────────
def _bones():
    b = [
        ("root",  (0, 0, 0), (0, 0, 0.35), None),
        ("hips",  (0, 0, Z_HIP), (0, 0, Z_WAIST), "root"),
        ("spine", (0, 0, Z_WAIST), (0, 0.012, Z_CH0), "hips"),
        ("chest", (0, 0.012, Z_CH0), (0, 0.045, Z_NECK), "spine"),
        ("neck",  (0, 0.045, Z_NECK), (0, 0.098, Z_HEAD), "chest"),
        ("head",  (0, 0.098, Z_HEAD), (0, 0.215, 1.782), "neck"),
    ]
    for s, side in ((1, "R"), (-1, "L")):
        sh = SH_R if s > 0 else SH_L
        el = ELB_R if s > 0 else ELB_L
        wr = WRI_R if s > 0 else WRI_L
        hd = HDIR_R if s > 0 else HDIR_L
        b += [
            ("shoulder_" + side, (s * 0.070, 0.010, 1.545), tuple(sh), "chest"),
            ("upperarm_" + side, tuple(sh), tuple(el), "shoulder_" + side),
            ("forearm_" + side, tuple(el), tuple(wr), "upperarm_" + side),
            ("hand_" + side, tuple(wr), tuple(wr + hd * 0.120), "forearm_" + side),
        ]
        hip = HIP_R if s > 0 else HIP_L
        kne = KNE_R if s > 0 else KNE_L
        hck = HCK_R if s > 0 else HCK_L
        bal = BAL_R if s > 0 else BAL_L
        toe = TOE_R if s > 0 else TOE_L
        b += [
            ("thigh_" + side, tuple(hip), tuple(kne), "hips"),
            ("shin_" + side, tuple(kne), tuple(hck), "thigh_" + side),
            ("foot_" + side, tuple(hck), tuple(bal), "shin_" + side),
            ("toe_" + side, tuple(bal), tuple(toe), "foot_" + side),
        ]
    b += [
        # 巫杖插座：**+Y 局部 = 杖顶方向**，所以 P.aim / P.LOC 都按"杖轴"理解
        ("weapon_R", tuple(GRIP), tuple(GRIP + Vector((0, 0, 0.30))), "hand_R"),
        ("weapon_L", tuple(WRI_L + HDIR_L * 0.090),
         tuple(WRI_L + HDIR_L * 0.090 + Vector((0, 0, 0.25))), "hand_L"),
        ("tail_01", tuple(TAIL0), tuple(TAIL1), "hips"),
        ("tail_02", tuple(TAIL1), tuple(TAIL2), "tail_01"),
        # 宝珠：单独一根骨，攻击时靠 LOC/SCL 变成飞出去的电球
        ("fx_ball", tuple(ORB_C), tuple(ORB_C + Vector((0, 0, 0.08))), "weapon_R"),
        ("fx_arc", tuple(ORB_C), tuple(ORB_C + Vector((0, 0, 0.07))), "weapon_R"),
    ]
    return b


BONES = _bones()
BONE_NAMES = [b[0] for b in BONES]

MODULES = ("body", "head", "staff", "fx")

MATS = {
    # 蓝皮肤三档（暗 < 中 < 亮）：明度阶梯是这套资产的基本功
    "皮肤暗":    dict(hexcol="#1B3A54", metal=0.00, rough=0.66),
    "皮肤":      dict(hexcol="#2E5C80", metal=0.00, rough=0.62),
    "皮肤亮":    dict(hexcol="#437AA3", metal=0.00, rough=0.56),
    "骨":        dict(hexcol="#C9BFA6", metal=0.00, rough=0.55),
    "皮革":      dict(hexcol="#4A3A2C", metal=0.00, rough=0.78),
    "皮革暗":    dict(hexcol="#2A2018", metal=0.00, rough=0.82),
    # 失落帝国队色，**不许改**
    "team":      dict(hexcol="#743A2E", metal=0.00, rough=0.70),
    "team_trim": dict(hexcol="#A99578", metal=0.10, rough=0.46),
    # 宝珠：底色压深、发光只给 1.0 —— estr 3.2 时图标一过 bloom 就整颗烧白，
    # "蓝光"的身份全丢；深青底 + 中等发光才能既发光又还是青的。
    "辉":        dict(hexcol="#1E8CC0", metal=0.00, rough=0.20,
                      emit="#22B4E8", estr=1.0),
}


# ══ 通用小件 ════════════════════════════════════════════════════════════════
def disc(name, center, normal, r, thick, n=10):
    c = Vector(center)
    ez = Vector(normal).normalized()
    up = Vector((0, 0, 1))
    if abs(ez.dot(up)) > 0.95:
        up = Vector((0, 1, 0))
    ex = up.cross(ez).normalized()
    ey = ez.cross(ex).normalized()
    rows = []
    for (o, rr) in ((-thick * 0.5, r * 0.82), (-thick * 0.5 + 0.006, r),
                    (thick * 0.5 - 0.006, r), (thick * 0.5, r * 0.82)):
        rows.append([tuple(c + ez * o + ex * (rr * math.cos(math.tau * k / n))
                           + ey * (rr * math.sin(math.tau * k / n))) for k in range(n)])
    return K.loft(name, rows, True)


def ring(name, center, normal, r_in, r_out, thick, n=8):
    c = Vector(center)
    ez = Vector(normal).normalized()
    up = Vector((0, 0, 1))
    if abs(ez.dot(up)) > 0.95:
        up = Vector((0, 1, 0))
    ex = up.cross(ez).normalized()
    ey = ez.cross(ex).normalized()
    rows = []
    for (o, rr) in ((-thick * 0.5, r_in), (-thick * 0.5, r_out),
                    (thick * 0.5, r_out), (thick * 0.5, r_in)):
        rows.append([tuple(c + ez * o + ex * (rr * math.cos(math.tau * k / n))
                           + ey * (rr * math.sin(math.tau * k / n))) for k in range(n)])
    verts = [p for r in rows for p in r]
    faces = []
    for i in range(4):
        j = (i + 1) % 4
        for k in range(n):
            k2 = (k + 1) % n
            faces.append((i * n + k, i * n + k2, j * n + k2, j * n + k))
    return KU._obj(name, verts, faces)


def octa(name, c, r, h=None, n=6):
    """双锥（宝珠 / 骨珠）：n=4 是标准八面体，n=5/6 是更多棱的珠子。"""
    h = r if h is None else h
    c = Vector(c)
    ring_pts = [(c.x + r * math.cos(math.tau * k / n), c.y + r * math.sin(math.tau * k / n), c.z)
                for k in range(n)]
    verts = [tuple(c + Vector((0, 0, h)))] + ring_pts + [tuple(c - Vector((0, 0, h)))]
    faces = []
    for k in range(n):
        k2 = (k + 1) % n
        faces.append((0, 1 + k, 1 + k2))
        faces.append((n + 1, 1 + k2, 1 + k))
    return KU._obj(name, verts, faces)


def fin(name, y0, z0, y1, z1, w, t, bend=0.0):
    """鬃冠薄片：底边沿 Y 宽 w、沿 X 厚 t，往上收成一条窄脊。"""
    rows = []
    for (u, yy, zz, ww, tt) in ((0.0, y0, z0, w, t),
                                (0.55, y0 + (y1 - y0) * 0.52 + bend * 0.5,
                                 z0 + (z1 - z0) * 0.62, w * 0.66, t * 0.72),
                                (1.0, y1, z1, w * 0.10, t * 0.26)):
        rows.append([(tt * 0.5, yy - ww * 0.5, zz), (tt * 0.5, yy + ww * 0.5, zz),
                     (-tt * 0.5, yy + ww * 0.5, zz), (-tt * 0.5, yy - ww * 0.5, zz)])
    return K.loft(name, rows, True)


def ear_plate(name, root, tip, w0, w1, t0, t1):
    """大三角耳：沿耳轴的 3 站放样（根宽 → 中宽 → 尖），扁平、尖端锋利。"""
    p0, ex, ey, ez = KU.frame(root, tip, up=(0, 1, 0))
    L = (Vector(tip) - p0).length
    rows = []
    for (u, ww, tt) in ((0.0, w0, t0), (0.42, w1, t1 * 1.05), (1.0, w1 * 0.06, t1 * 0.22)):
        c = p0 + ez * (L * u)
        rows.append([tuple(c + ex * (ww * 0.5) + ey * (tt * 0.5)),
                     tuple(c + ex * (ww * 0.5) - ey * (tt * 0.5)),
                     tuple(c - ex * (ww * 0.5) - ey * (tt * 0.5)),
                     tuple(c - ex * (ww * 0.5) + ey * (tt * 0.5))])
    return K.loft(name, rows, True)


def boss(name, c, w, h, t, n=6):
    """朝 +Z 的扁平骨片（额骨 / 护符）。"""
    c = Vector(c)
    rows = []
    for (o, k) in ((-0.004, 0.90), (t, 1.0)):
        rows.append([(c.x + w * 0.5 * k * math.cos(math.tau * i / n),
                      c.y + h * 0.5 * k * math.sin(math.tau * i / n),
                      c.z + o) for i in range(n)])
    return K.loft(name, rows, True)


def shrink(ob, c, k):
    C = Vector(c)
    for v in ob.data.vertices:
        v.co = C + (v.co - C) * k
    return ob


def lerp(a, b, t):
    return Vector(a).lerp(Vector(b), t)


# ══ 1. 反关节腿 + 三趾爪 ════════════════════════════════════════════════════
# 掌垫 / 爪尖三个接触点（相对跖骨根）：旋转后取最低的那个 = 不穿地的踝高
G_CONTACT = ((-0.228 - HCK_R.y, 0.000 - HCK_R.z),
             (0.112 - HCK_R.y, 0.005 - HCK_R.z),
             (0.168 - HCK_R.y, 0.002 - HCK_R.z))


def foot_clear(pitch_deg):
    """给定脚的 pitch，返回"爪底不穿地"所需要的跖骨根高度。"""
    a = math.radians(pitch_deg)
    sa, ca = math.sin(a), math.cos(a)
    lo = min(dy * sa + dz * ca for (dy, dz) in G_CONTACT)
    return -lo + 0.0012


def leg_one(u, s, side):
    th, sh, ft, to = ("thigh_" + side, "shin_" + side, "foot_" + side, "toe_" + side)
    hip = HIP_R if s > 0 else HIP_L
    kne = KNE_R if s > 0 else KNE_L
    hck = HCK_R if s > 0 else HCK_L
    bal = BAL_R if s > 0 else BAL_L

    # 大腿：短而粗（直径 0.245），前倾 31°
    u.olimb("lg_thigh_" + side, tuple(hip + Vector((0, -0.012, 0.070))), tuple(kne),
            [(0.00, 0.230, 0.258, 0.066), (0.40, 0.246, 0.272, 0.070),
             (1.00, 0.196, 0.214, 0.056)],
            th, "皮肤", "chunk", "body", "thigh")
    # 大腿内侧：皮肤暗
    u.olimb("lg_thigh_in_" + side,
            tuple(hip + Vector((-s * 0.052, -0.014, 0.020))),
            tuple(kne + Vector((-s * 0.036, -0.004, 0.010))),
            [(0.00, 0.100, 0.242, 0.032), (1.00, 0.082, 0.186, 0.026)],
            th, "皮肤暗", "chunk", "body", "thigh")
    # 大腿外侧：皮肤亮（受光面）
    u.add(K.arc_band("lg_thigh_hi_" + side,
                     tuple(hip + Vector((0, -0.012, 0.010))), tuple(kne + Vector((0, 0, 0.010))),
                     0.110, 0.088, -34, 34, 1, 4, 0.014, (s * 0.94, -0.28, 0.18)),
          th, "皮肤亮", "chunk", "body", "thigh")
    # 膝：皮革护膝
    u.add(ring("lg_knee_%s" % side, tuple(kne), tuple((kne - hip).normalized()),
               0.078, 0.100, 0.048, 8), th, "皮革", "chunk2", "body", "knee")

    # 小腿：向后折 40°
    u.olimb("lg_shin_" + side, tuple(kne + Vector((0, -0.006, -0.012))), tuple(hck),
            [(0.00, 0.158, 0.176, 0.048), (0.40, 0.140, 0.158, 0.042),
             (1.00, 0.106, 0.120, 0.032)],
            sh, "皮肤", "chunk", "body", "shin")
    u.olimb("lg_shin_in_" + side,
            tuple(kne + Vector((-s * 0.042, 0.012, -0.034))),
            tuple(hck + Vector((-s * 0.030, 0.006, 0.012))),
            [(0.00, 0.066, 0.160, 0.020), (1.00, 0.048, 0.106, 0.016)],
            sh, "皮肤暗", "chunk", "body", "shin")
    for i, t in enumerate((0.28, 0.58)):
        a = lerp(kne, hck, t)
        b = lerp(kne, hck, t + 0.09)
        u.olimb("lg_wrap_%s%d" % (side, i), tuple(a), tuple(b),
                [(0.0, 0.156 - 0.05 * t, 0.174 - 0.05 * t, 0.046),
                 (1.0, 0.150 - 0.05 * t, 0.168 - 0.05 * t, 0.044)],
                sh, "皮革", "chunk", "body", "wrap")
    u.add(disc("lg_wrap_pin_%s" % side,
               tuple(lerp(kne, hck, 0.34) + Vector((s * 0.074, -0.022, 0.010))),
               (s, -0.25, 0.0), 0.019, 0.018, 6), sh, "皮革暗", "chunk", "body", "wrap")

    # 跖骨：接近竖直落地的一根柱子
    u.olimb("lg_meta_" + side, tuple(hck + Vector((0, 0.004, -0.008))), tuple(bal),
            [(0.00, 0.116, 0.128, 0.032), (0.55, 0.106, 0.118, 0.028),
             (1.00, 0.112, 0.122, 0.030)],
            ft, "皮肤", "chunk", "body", "meta")
    # 后跟肉垫
    u.otube("lg_heel_" + side,
            [(0.058, s * LEG_X, -0.152, 0.132, 0.150, 0.030),
             (0.030, s * LEG_X, -0.156, 0.140, 0.158, 0.032),
             (0.000, s * LEG_X, -0.156, 0.128, 0.146, 0.028)],
            ft, "皮肤", "chunk", "body", "paw", cw=0.028)

    # 三趾：每趾 2 节 + 骨色尖爪，趾间 1.5 cm 缝（脚掌总宽 0.204，中趾最长）
    for i, (dx, ln, lw) in enumerate(((-0.073, 0.000, 0.056), (0.0, 0.028, 0.060),
                                      (0.073, 0.000, 0.056))):
        x = s * LEG_X + dx
        y1, y2 = 0.020 + ln, 0.108 + ln
        u.olimb("lg_toe%s_a_%s" % (i, side), (x, -0.082, 0.050), (x, y1, 0.046),
                [(0.00, lw, 0.084, 0.020), (1.00, lw * 0.98, 0.080, 0.019)],
                to, "皮肤", "chunk", "body", "toe")
        u.olimb("lg_toe%s_b_%s" % (i, side), (x, y1 + 0.008, 0.042), (x, y2, 0.036),
                [(0.00, lw * 0.94, 0.070, 0.017), (1.00, lw * 0.76, 0.058, 0.014)],
                to, "皮肤", "chunk", "body", "toe")
        u.add(KU.claw("lg_claw%s_%s" % (i, side),
                      (x, y2 + 0.002, 0.030), (x + dx * 0.30, y2 + 0.058, 0.003),
                      0.044, 0.034), to, "骨", "chunk", "body", "claw")
    # 后趾（悬在跖骨后面）
    u.add(KU.claw("lg_dew_%s" % side,
                  tuple(hck + Vector((0, -0.036, 0.026))),
                  tuple(hck + Vector((0, -0.104, -0.026))), 0.040, 0.034),
          ft, "骨", "chunk", "body", "claw")


def legs(u):
    for s, side in ((1, "R"), (-1, "L")):
        leg_one(u, s, side)


# ══ 2. 胯 / 腰布 / 骨珠腰带 ═════════════════════════════════════════════════
def pelvis(u):
    # 骨盆体：比腰宽 5 cm 的独立一块
    u.otube("bd_hip",
            [(0.926, 0, -0.010, 0.432, 0.336, 0.064),
             (0.972, 0, -0.010, 0.466, 0.356, 0.072),
             (1.030, 0, -0.008, 0.472, 0.360, 0.074),
             (1.074, 0, -0.006, 0.448, 0.344, 0.068)],
            "hips", "皮肤", "chunk", "body", "pelvis", cw=0.072)
    for s, side in ((1, "R"), (-1, "L")):
        u.add(K.arc_band("bd_hip_hi_" + side, (s * 0.10, -0.010, 0.980), (s * 0.10, -0.010, 1.050),
                         0.196, 0.216, -34, 34, 1, 4, 0.014, (s * 0.98, -0.12, 0.16)),
              "hips", "皮肤亮", "chunk", "body", "pelvis")

    # 腰布：前片 V 形下摆（网格自己搭），后/左/右三片平
    zs = ((1.062, 0.238, 0.192), (0.980, 0.248, 0.202),
          (0.900, 0.254, 0.208), (0.830, 0.250, 0.204))
    nu = 8
    grid = []
    for (z, rx, ry) in zs:
        grid.append([(rx * math.sin(math.radians(-34 + 68 * i / nu)),
                      ry * math.cos(math.radians(-34 + 68 * i / nu)), z)
                     for i in range(nu + 1)])
    row = []
    for i in range(nu + 1):
        a = math.radians(-34 + 68 * i / nu)
        k = abs(i - nu * 0.5) / (nu * 0.5)
        row.append((0.246 * math.sin(a), 0.202 * math.cos(a), 0.706 + 0.096 * k))
    grid.append(row)
    u.add(K.grid_shell("bd_loin_f", grid, 0.016, inside=(0, 0, 0.90)),
          "hips", "team", "chunk", "body", "loin")
    st = [(z, 146, 214, rx, ry) for (z, rx, ry) in zs]
    st.append((0.790, 150, 210, 0.244, 0.200))
    u.add(K.arc_panel("bd_loin_b", st, 0.016, 8, None, (0.0, 0.0)),
          "hips", "team", "chunk", "body", "loin")
    for s, side in ((1, "R"), (-1, "L")):
        a = (42, 138) if s > 0 else (-138, -42)
        st = [(z, a[0], a[1], rx + 0.010, ry + 0.004) for (z, rx, ry) in zs]
        st.append((0.796, a[0] + 4, a[1] - 4, 0.256, 0.206))
        u.add(K.arc_panel("bd_loin_" + side, st, 0.016, 6, None, (0.0, 0.0)),
              "hips", "team", "chunk", "body", "loin")
    # 里衬：一整圈皮革暗
    zsu = ((0.930, 0.228, 0.184), (0.840, 0.232, 0.188), (0.740, 0.218, 0.176))
    u.add(K.arc_panel("bd_loin_in", [(z, -180, 180, rx, ry) for (z, rx, ry) in zsu],
                      0.012, 16, None, (0.0, 0.0)),
          "hips", "皮革暗", "chunk", "body", "loin")

    # 骨珠腰带：9 颗小骨珠（直径 2.5 cm）串在腰布与胯之间
    for i in range(9):
        a = math.radians(-160 + i * 40)
        p = Vector((0.240 * math.sin(a), -0.008 + 0.198 * math.cos(a), 1.040))
        u.add(octa("bd_bead_b%d" % i, tuple(p), 0.0125, 0.017, n=5),
              "hips", "骨", "chunk", "body", "belt_bead")
    # 腰带
    u.otube("bd_belt",
            [(1.050, 0, -0.008, 0.482, 0.374, 0.074),
             (1.072, 0, -0.008, 0.492, 0.382, 0.076),
             (1.100, 0, -0.008, 0.482, 0.374, 0.074)],
            "hips", "皮革暗", "chunk", "body", "belt", cw=0.072)
    u.otube("bd_belt_trim",
            [(1.072, 0, -0.008, 0.498, 0.388, 0.076),
             (1.086, 0, -0.008, 0.498, 0.388, 0.076)],
            "hips", "team_trim", "chunk", "body", "belt", cw=0.072)
    u.add(octa("bd_buckle", (0.0, 0.210, 1.072), 0.034, 0.030, n=6),
          "hips", "骨", "chunk", "body", "belt")


# ══ 3. 躯干（胸肌 / 三道腹肌 / 独立骨盆，段间留暗缝）════════════════════════
CHEST = [(1.258, 0.014, 0.412, 0.322, 0.070),
         (1.330, 0.006, 0.494, 0.386, 0.084),
         (1.412, -0.006, 0.548, 0.430, 0.094),
         (1.492, -0.018, 0.562, 0.442, 0.098),
         (1.558, -0.036, 0.526, 0.414, 0.092),
         (1.624, -0.062, 0.442, 0.352, 0.080),
         (1.674, -0.082, 0.352, 0.284, 0.064),
         (1.700, -0.090, 0.286, 0.226, 0.052)]


def chest_wd(z):
    if z <= CHEST[0][0]:
        return CHEST[0][2], CHEST[0][3], CHEST[0][1]
    if z >= CHEST[-1][0]:
        return CHEST[-1][2], CHEST[-1][3], CHEST[-1][1]
    for i in range(len(CHEST) - 1):
        z0, c0, w0, d0, k0 = CHEST[i]
        z1, c1, w1, d1, k1 = CHEST[i + 1]
        if z0 <= z <= z1:
            t = (z - z0) / (z1 - z0)
            return (w0 + (w1 - w0) * t, d0 + (d1 - d0) * t, c0 + (c1 - c0) * t)


def abdomen_r(z):
    t = max(0.0, min(1.0, (z - 1.105) / (1.258 - 1.105)))
    return (0.396 + 0.052 * t, 0.318 + 0.040 * t, 0.004 + 0.010 * t)


def torso(u):
    # 内胆：一根暗档八角柱把三条缝兜住
    u.otube("bd_core",
            [(1.060, 0, -0.006, 0.404, 0.310, 0.058),
             (1.150, 0, 0.004, 0.372, 0.300, 0.054),
             (1.270, 0, 0.012, 0.406, 0.318, 0.060),
             (1.500, 0, -0.016, 0.520, 0.404, 0.080),
             (1.660, 0, -0.070, 0.352, 0.280, 0.058)],
            "spine", "皮肤暗", "facet", "body", "core", cw=0.058)

    # 腹：整段皮肤暗（腹侧），外面压三道腹肌横条（皮肤），条间是暗缝
    u.otube("bd_abdomen",
            [(1.105, 0, 0.004, 0.396, 0.318, 0.062),
             (1.150, 0, 0.007, 0.404, 0.324, 0.064),
             (1.205, 0, 0.011, 0.428, 0.344, 0.068),
             (1.256, 0, 0.013, 0.446, 0.356, 0.070)],
            "spine", "皮肤暗", "chunk", "body", "abdomen", cw=0.066)
    for i, (z0, z1) in enumerate(((1.112, 1.152), (1.168, 1.208), (1.224, 1.256))):
        w, d, cy = abdomen_r((z0 + z1) * 0.5)
        u.add(K.arc_panel("bd_ab%d" % i,
                          [(z0, -58, 58, w * 0.5 + 0.006, d * 0.5 + 0.006, cy + 0.004),
                           (z1, -58, 58, w * 0.5 + 0.004, d * 0.5 + 0.004, cy + 0.004)],
                          0.026, 6, None, (0.0, cy + 0.010)),
              "spine", "皮肤", "chunk", "body", "abs")

    # 胸
    u.otube("bd_chest", [(z, 0, c, w, d, k) for (z, c, w, d, k) in CHEST],
            "chest", "皮肤", "chunk", "body", "chest", cw=0.090)
    # 胸肌：左右各一块独立体，中间 2 cm 胸沟
    for s, side in ((1, "R"), (-1, "L")):
        u.otube("bd_pec_" + side,
                [(1.352, s * 0.108, 0.198, 0.150, 0.106, 0.040),
                 (1.404, s * 0.110, 0.202, 0.168, 0.118, 0.042),
                 (1.456, s * 0.108, 0.196, 0.166, 0.116, 0.042),
                 (1.500, s * 0.100, 0.180, 0.140, 0.098, 0.036)],
                "chest", "皮肤", "chunk", "body", "pec", cw=0.038)
    u.box("bd_cleft", (0.0, 0.196, 1.424), (0.026, 0.028, 0.150),
          "chest", "皮肤暗", style="chunk", module="body", tag="pec")

    # 肩背肉峰
    u.otube("bd_hump",
            [(1.470, 0, -0.150, 0.330, 0.220, 0.054),
             (1.545, 0, -0.176, 0.356, 0.244, 0.058),
             (1.620, 0, -0.180, 0.310, 0.206, 0.050),
             (1.690, 0, -0.160, 0.216, 0.146, 0.036)],
            "chest", "皮肤", "chunk", "body", "hump", cw=0.052)
    u.add(K.arc_panel("bd_back_hi",
                      [(1.430, 158, 202, 0.262, 0.212),
                       (1.500, 158, 202, 0.278, 0.228),
                       (1.570, 158, 202, 0.272, 0.222),
                       (1.640, 158, 202, 0.216, 0.176)],
                      0.012, 4, None, (0.0, -0.060)),
          "chest", "皮肤亮", "chunk", "body", "hump")

    # 斜挎皮索
    SA = Vector((-0.250, 0.070, 1.576))
    SB = Vector((-0.020, 0.208, 1.330))
    SC = Vector((0.196, 0.164, 1.086))
    for tag, p0, p1 in (("a", SA, SB), ("b", SB, SC)):
        u.olimb("bd_strap_" + tag, tuple(p0), tuple(p1),
                [(0.00, 0.066, 0.020, 0.012), (1.00, 0.066, 0.020, 0.012)],
                "chest", "皮革", "chunk", "body", "strap")
    for i, t in enumerate((0.30, 0.52, 0.74)):
        p = SA.lerp(SB, t) if t < 0.55 else SB.lerp(SC, (t - 0.55) / 0.45)
        u.add(KU.claw("bd_charm_%d" % i, tuple(p + Vector((0, 0.014, -0.012))),
                      tuple(p + Vector((0.006, 0.012, -0.086))), 0.032, 0.024),
              "chest", "骨", "chunk", "body", "charm")
    u.add(ring("bd_charm_ring", tuple(SB + Vector((0, 0.016, 0.010))), (0, 1, 0),
               0.014, 0.026, 0.014, 6), "chest", "骨", "chunk", "body", "charm")

    # 三道战纹（队色）
    for i, dx in enumerate((-0.052, -0.020, 0.012)):
        u.box("bd_paint_%d" % i, (dx - 0.074, 0.206, 1.372), (0.011, 0.010, 0.070),
              "chest", "team", rot=(0, math.radians(9), 0),
              style="chunk", module="body", tag="paint")


def neck(u):
    u.otube("bd_neck",
            [(1.452, 0, 0.024, 0.232, 0.240, 0.048),
             (1.540, 0, 0.056, 0.206, 0.214, 0.042),
             (1.622, 0, 0.090, 0.182, 0.190, 0.036),
             (1.700, 0, 0.108, 0.152, 0.160, 0.030)],
            "neck", "皮肤", "chunk", "body", "neck", cw=0.044)
    u.add(K.arc_panel("bd_neck_dark",
                      [(1.470, -40, 40, 0.126, 0.130),
                       (1.560, -38, 38, 0.112, 0.116),
                       (1.640, -34, 34, 0.098, 0.102)],
                      0.012, 4, None, (0.0, 0.070)),
          "neck", "皮肤暗", "chunk", "body", "neck")
    u.otube("bd_ruff",
            [(1.436, 0, 0.020, 0.286, 0.292, 0.058),
             (1.470, 0, 0.028, 0.268, 0.276, 0.054),
             (1.512, 0, 0.042, 0.232, 0.240, 0.046)],
            "neck", "皮肤暗", "chunk", "body", "ruff", cw=0.050)
    u.otube("bd_ruff2",
            [(1.556, 0, 0.062, 0.238, 0.246, 0.046),
             (1.596, 0, 0.076, 0.212, 0.220, 0.042)],
            "neck", "皮肤暗", "chunk", "body", "ruff", cw=0.042)

    for i in range(5):
        a = math.radians(-64 + i * 32)
        p = Vector((math.sin(a) * 0.198, 0.036 + math.cos(a) * 0.184,
                    1.466 - 0.032 * math.cos(a)))
        u.add(octa("bd_bead_%d" % i, tuple(p), 0.021, 0.026, n=5),
              "chest", "骨", "chunk", "body", "beads")
    u.add(KU.claw("bd_pend", (0.0, 0.244, 1.446), (0.0, 0.242, 1.356), 0.046, 0.034),
          "chest", "骨", "chunk", "body", "beads")
    u.add(ring("bd_pend_ring", (0.0, 0.246, 1.462), (0, 1, 0), 0.016, 0.026, 0.012, 6),
          "chest", "骨", "chunk", "body", "beads")


# ══ 4. 臂 / 手 ══════════════════════════════════════════════════════════════
def arm_one(u, s, side):
    sh = SH_R if s > 0 else SH_L
    el = ELB_R if s > 0 else ELB_L
    wr = WRI_R if s > 0 else WRI_L
    ua, fa = "upperarm_" + side, "forearm_" + side

    u.olimb("ar_delt_" + side, tuple(sh + Vector((-s * 0.030, 0.004, 0.048))),
            tuple(sh + (el - sh).normalized() * 0.170),
            [(0.00, 0.186, 0.196, 0.052), (0.55, 0.180, 0.190, 0.050),
             (1.00, 0.146, 0.156, 0.042)],
            ua, "皮肤", "chunk", "body", "delt")
    u.add(K.arc_band("ar_delt_hi_" + side,
                     tuple(sh + Vector((-s * 0.010, 0.000, 0.062))),
                     tuple(sh + (el - sh).normalized() * 0.150),
                     0.088, 0.074, -46, 46, 1, 4, 0.012, (s * 0.55, -0.10, 0.83)),
          ua, "皮肤亮", "chunk", "body", "delt")

    u.olimb("ar_upper_" + side, tuple(sh + (el - sh) * 0.10), tuple(el),
            [(0.00, 0.148, 0.160, 0.040), (0.55, 0.132, 0.144, 0.036),
             (1.00, 0.118, 0.128, 0.032)],
            ua, "皮肤", "chunk", "body", "upper")
    u.olimb("ar_upper_in_" + side,
            tuple(sh + (el - sh) * 0.14 + Vector((-s * 0.048, -0.026, 0))),
            tuple(el + Vector((-s * 0.040, -0.020, 0))),
            [(0.00, 0.056, 0.130, 0.018), (1.00, 0.048, 0.104, 0.016)],
            ua, "皮肤暗", "chunk", "body", "upper")
    if s < 0:
        for i in range(3):
            p = sh + (el - sh) * (0.30 + i * 0.070)
            u.box("ar_paint_%d" % i, tuple(p + Vector((-0.070, -0.014, 0.0))),
                  (0.012, 0.048, 0.020), ua, "team_trim", style="chunk",
                  module="body", tag="paint")

    u.add(ring("ar_elbow_%s" % side, tuple(el), tuple((el - sh).normalized()),
               0.062, 0.082, 0.044, 8), fa, "皮革", "chunk2", "body", "elbow")
    u.olimb("ar_fore_" + side, tuple(el + (wr - el) * 0.06), tuple(wr),
            [(0.00, 0.124, 0.136, 0.034), (0.50, 0.116, 0.126, 0.032),
             (1.00, 0.096, 0.104, 0.026)],
            fa, "皮肤", "chunk", "body", "fore")
    u.olimb("ar_fore_in_" + side,
            tuple(el + (wr - el) * 0.10 + Vector((-s * 0.042, -0.020, 0))),
            tuple(wr + Vector((-s * 0.030, -0.016, 0))),
            [(0.00, 0.046, 0.108, 0.014), (1.00, 0.036, 0.082, 0.012)],
            fa, "皮肤暗", "chunk", "body", "fore")
    for i, t in enumerate((0.52, 0.68)):
        a = lerp(el, wr, t)
        b = lerp(el, wr, t + 0.10)
        r = 0.124 - 0.02 * t
        u.olimb("ar_wrap_%s%d" % (side, i), tuple(a), tuple(b),
                [(0.0, r, r * 1.08, 0.032), (1.0, r * 0.96, r * 1.04, 0.030)],
                fa, "皮革", "chunk", "body", "wrap")
    u.add(disc("ar_wrap_pin_" + side,
               tuple(lerp(el, wr, 0.60) + Vector((0, -0.086, 0.0))),
               (0, -1, 0.2), 0.017, 0.015, 6), fa, "皮革暗", "chunk", "body", "wrap")


def hand_open(u, side):
    """左手：三指爪（拇指 + 两根长指），每根 2 节、关节留缝、指缝压暗。"""
    s = 1 if side == "R" else -1
    bone = "hand_" + side
    wr = WRI_R if s > 0 else WRI_L
    d = HDIR_R if s > 0 else HDIR_L
    palm = wr + d * 0.062
    u.olimb("hd_palm_" + side, tuple(wr + d * 0.008), tuple(palm + d * 0.050),
            [(0.00, 0.098, 0.072, 0.024), (0.55, 0.108, 0.078, 0.026),
             (1.00, 0.096, 0.070, 0.022)],
            bone, "皮肤", "chunk", "body", "palm")
    tip = palm + d * 0.052
    u.olimb("hd_gap_" + side, tuple(tip - d * 0.014), tuple(tip + d * 0.014),
            [(0.0, 0.104, 0.028, 0.008), (1.0, 0.100, 0.026, 0.008)],
            bone, "皮肤暗", "chunk", "body", "finger")
    for i, dx in enumerate((-0.036, 0.0, 0.036)):
        b = tip + Vector((dx * s, 0, 0))
        k1 = b + d * 0.044
        k2 = k1 + (d * 0.040 + Vector((0, 0.014, 0))).normalized() * 0.040
        u.olimb("hd_f%d_%s_a" % (i, side), tuple(b), tuple(k1),
                [(0.00, 0.030, 0.034, 0.009), (1.00, 0.026, 0.030, 0.008)],
                bone, "皮肤", "chunk", "body", "finger")
        u.olimb("hd_f%d_%s_b" % (i, side), tuple(k1 + d * 0.006), tuple(k2),
                [(0.00, 0.026, 0.030, 0.008), (1.00, 0.022, 0.026, 0.007)],
                bone, "皮肤", "chunk", "body", "finger")
        u.add(KU.claw("hd_c%d_%s" % (i, side), tuple(k2 + d * 0.004),
                      tuple(k2 + d * 0.034 + Vector((0, 0.014, -0.006))), 0.026, 0.020),
              bone, "骨", "chunk", "body", "claw")
    tb = palm + Vector((s * 0.012, 0.038, 0.026))
    t1 = tb + (d * 0.22 + Vector((0, 0.92, -0.32))).normalized() * 0.046
    u.olimb("hd_thumb_" + side, tuple(tb), tuple(t1),
            [(0.00, 0.034, 0.038, 0.010), (1.00, 0.028, 0.032, 0.008)],
            bone, "皮肤", "chunk", "body", "finger")
    u.add(KU.claw("hd_tclaw_" + side, tuple(t1),
                  tuple(t1 + (d * 0.3 + Vector((0, 0.6, -0.5))).normalized() * 0.030),
                  0.024, 0.018), bone, "骨", "chunk", "body", "claw")


def hand_fist(u, side):
    """右手：握拳攥住竖直的杖身（掌在杖的 +X 侧，三指横着绕过去）。"""
    bone = "hand_" + side
    G = GRIP
    u.otube("hd_fist_palm",
            [(G.z - 0.088, G.x + 0.066, G.y - 0.017, 0.086, 0.104, 0.026),
             (G.z - 0.040, G.x + 0.070, G.y - 0.013, 0.094, 0.112, 0.028),
             (G.z + 0.012, G.x + 0.068, G.y - 0.015, 0.088, 0.106, 0.026),
             (G.z + 0.046, G.x + 0.062, G.y - 0.023, 0.076, 0.092, 0.022)],
            bone, "皮肤", "chunk", "body", "palm", cw=0.024)
    u.otube("hd_fist_gap",
            [(G.z - 0.052, G.x + 0.040, G.y + 0.052, 0.030, 0.086, 0.008),
             (G.z + 0.038, G.x + 0.040, G.y + 0.052, 0.030, 0.086, 0.008)],
            bone, "皮肤暗", "chunk", "body", "finger", cw=0.008)
    for i, dz in enumerate((-0.064, -0.018, 0.028)):
        p0 = G + Vector((0.040, 0.027, dz))
        p1 = G + Vector((0.016, 0.089, dz))
        p2 = G + Vector((-0.044, 0.077, dz))
        u.olimb("hd_f%d_a" % i, tuple(p0), tuple(p1),
                [(0.00, 0.046, 0.046, 0.014), (1.00, 0.040, 0.042, 0.012)],
                bone, "皮肤", "chunk", "body", "finger")
        u.olimb("hd_f%d_b" % i, tuple(p1), tuple(p2),
                [(0.00, 0.040, 0.042, 0.012), (1.00, 0.032, 0.034, 0.010)],
                bone, "皮肤", "chunk", "body", "finger")
        u.add(KU.claw("hd_fc%d" % i, tuple(p2), tuple(p2 + Vector((-0.024, 0.008, -0.010))),
                      0.026, 0.020), bone, "骨", "chunk", "body", "claw")
    u.olimb("hd_thumb_a", tuple(G + Vector((0.072, -0.053, 0.000))),
            tuple(G + Vector((0.006, -0.067, -0.008))),
            [(0.00, 0.044, 0.048, 0.014), (1.00, 0.036, 0.040, 0.012)],
            bone, "皮肤", "chunk", "body", "finger")
    u.olimb("hd_thumb_b", tuple(G + Vector((0.006, -0.067, -0.008))),
            tuple(G + Vector((-0.046, -0.037, -0.016))),
            [(0.00, 0.036, 0.040, 0.012), (1.00, 0.028, 0.032, 0.010)],
            bone, "皮肤", "chunk", "body", "finger")
    d = (GRIP - SH_R).normalized()
    u.olimb("hd_cuff", tuple(WRI_R + d * 0.030), tuple(WRI_R - d * 0.006),
            [(0.0, 0.112, 0.120, 0.030), (1.0, 0.102, 0.110, 0.028)],
            bone, "皮革", "chunk", "body", "cuff")


def arms(u):
    for s, side in ((1, "R"), (-1, "L")):
        arm_one(u, s, side)
    hand_fist(u, "R")
    hand_open(u, "L")


# ══ 5. 左肩骨甲：3 片独立弧片 + 3 根骨刺（120° 包角）═══════════════════════
def pauldron(u):
    sh = SH_L
    el = ELB_L
    d = (el - sh).normalized()
    out = Vector((-0.88, -0.20, 0.42)).normalized()
    bone = "shoulder_L"
    plates = ((0.000, 0.072, 0.096, 0.118, 0.140),
              (0.080, 0.152, 0.126, 0.146, 0.100),
              (0.160, 0.226, 0.152, 0.164, 0.070))
    for i, (t0, t1, r0, r1, sl) in enumerate(plates):
        u.add(K.arc_band("pd_bone%d" % i, tuple(sh + d * t0), tuple(sh + d * t1),
                         r0, r1, -60, 60, 1, 5, 0.030, tuple(out), 0.006),
              bone, "骨", "chunk2", "body", "pauldron")
        base = sh + d * (t1 - 0.012) + out * (r1 * 0.88)
        tip = base + (out * 0.72 + d * 0.55).normalized() * sl
        u.add(KU.claw("pd_spike%d" % i, tuple(base), tuple(tip), 0.050, 0.040),
              bone, "骨", "chunk2", "body", "spike")
    u.add(disc("pd_cap", tuple(sh + d * 0.002), tuple(-d), 0.070, 0.026, 8),
          bone, "骨", "chunk2", "body", "pauldron")
    u.add(ring("pd_cap_rim", tuple(sh + d * 0.006), tuple(-d), 0.070, 0.086, 0.016, 8),
          bone, "team_trim", "chunk", "body", "pauldron")
    u.add(K.arc_band("pd_strap", tuple(sh + d * 0.238), tuple(sh + d * 0.284),
                     0.170, 0.166, -88, 88, 1, 5, 0.018, tuple(out)),
          bone, "皮革", "chunk", "body", "strap")


# ══ 6. 尾 ═══════════════════════════════════════════════════════════════════
def tail(u):
    segs = ((TAIL0, TAIL1, "tail_01", 0.060, 0.045, "皮肤"),
            (TAIL1, TAIL2, "tail_02", 0.045, 0.030, "皮肤暗"))
    for a, b, bone, r0, r1, mat in segs:
        u.olimb("tl_%s" % bone, tuple(a), tuple(b),
                [(0.00, r0 * 2, r0 * 2.1, r0 * 0.5),
                 (0.55, (r0 + r1), (r0 + r1) * 1.05, r1 * 0.55),
                 (1.00, r1 * 2, r1 * 2.1, r1 * 0.5)],
                bone, mat, "chunk", "body", "tail")
    u.add(K.arc_band("tl_belly", tuple(TAIL0 + (TAIL1 - TAIL0) * 0.10),
                     tuple(TAIL1), 0.058, 0.044, -46, 46, 1, 4, 0.010, (0, -0.35, -0.94)),
          "tail_01", "皮肤暗", "chunk", "body", "tail")
    d = (TAIL2 - TAIL1).normalized()
    for i, (off, ln, wd) in enumerate(((-0.030, 0.115, 0.058), (0.006, 0.135, 0.062),
                                      (0.038, 0.100, 0.050))):
        a = TAIL2 + Vector((off * 0.7, 0, 0))
        b = a + d * ln + Vector((off * 1.6, -0.020, -0.020))
        u.add(KU.claw("tl_tuft%d" % i, tuple(a), tuple(b), wd, 0.028),
              "tail_02", "皮革暗", "chunk", "body", "tuft")


# ══ 7. 头：颅 + 长吻 + 下颌 + 獠牙 + 大三角耳 + 鬃冠 ══════════════════════
SKULL = [(-0.076, 1.834, 0.186, 0.196),
         (-0.012, 1.822, 0.236, 0.256),
         (0.070, 1.812, 0.246, 0.256),
         (0.140, 1.796, 0.234, 0.240),
         (0.200, 1.780, 0.212, 0.206),
         (0.256, 1.762, 0.186, 0.176),
         (0.330, 1.744, 0.170, 0.156),
         (0.400, 1.734, 0.150, 0.136),
         (0.452, 1.728, 0.118, 0.108)]
JAW = [(0.200, 1.690, 0.180, 0.074),
       (0.284, 1.678, 0.164, 0.066),
       (0.360, 1.670, 0.142, 0.054),
       (0.418, 1.666, 0.104, 0.042)]


def head(u):
    rows = [[(x, y, zc + zz) for (x, zz) in K.octs(w, h, 0.036)]
            for (y, zc, w, h) in SKULL]
    u.add(K.loft("hd_skull", rows), "head", "皮肤", "chunk", "head", "skull")
    # 颅顶受光面
    u.add(K.loft("hd_skull_hi", [
        [(x, -0.020, 1.947 + z) for (x, z) in K.octs(0.112, 0.020, 0.008)],
        [(x, 0.070, 1.941 + z) for (x, z) in K.octs(0.130, 0.022, 0.009)],
        [(x, 0.140, 1.916 + z) for (x, z) in K.octs(0.116, 0.020, 0.008)]]),
        "head", "皮肤亮", "chunk", "head", "skull")
    rows = [[(x, y, zc + zz) for (x, zz) in K.octs(w, h, 0.022)]
            for (y, zc, w, h) in JAW]
    u.add(K.loft("hd_jaw", rows), "head", "皮肤", "chunk", "head", "jaw")
    # 下颌底面：皮肤暗
    u.add(K.loft("hd_jaw_dark", [
        [(x, 0.210, 1.648 + z) for (x, z) in K.octs(0.130, 0.018, 0.007)],
        [(x, 0.300, 1.652 + z) for (x, z) in K.octs(0.146, 0.020, 0.008)],
        [(x, 0.396, 1.646 + z) for (x, z) in K.octs(0.112, 0.016, 0.006)]]),
        "head", "皮肤暗", "chunk", "head", "jaw")

    strip = ((0.180, 1.880, 0.158), (0.270, 1.848, 0.150),
             (0.360, 1.812, 0.132), (0.446, 1.766, 0.104))
    rows = [[(x, y, z + zz) for (x, zz) in K.octs(w, 0.024, 0.008)]
            for (y, z, w) in strip]
    u.add(K.loft("hd_muzzle_dark", rows), "head", "皮肤暗", "chunk", "head", "muzzle")
    nose_rows = []
    for (yy, ww, hh, zc) in ((0.398, 0.052, 0.020, 1.788), (0.418, 0.062, 0.026, 1.790),
                             (0.438, 0.054, 0.020, 1.782)):
        nose_rows.append([(x, yy, zc + z) for (x, z) in K.octs(ww, hh, 0.008)])
    u.add(K.loft("hd_nose", nose_rows), "head", "皮革暗", "chunk", "head", "nose")
    for s in (1, -1):
        u.box("hd_mouth_%d" % s, (s * 0.076, 0.344, 1.706), (0.012, 0.180, 0.009),
              "head", "皮革暗", rot=(0, 0, -s * 0.05), style="chunk",
              module="head", tag="mouth")

    for s in (1, -1):
        ub = Vector((s * 0.080, 0.372, 1.712))
        u.add(KU.claw("hd_fang_u%d" % s, tuple(ub), tuple(ub + Vector((0.004 * s, 0.004, -0.044))),
                      0.032, 0.028), "head", "骨", "chunk", "head", "fang")
        lb = Vector((s * 0.072, 0.356, 1.696))
        u.add(KU.claw("hd_fang_l%d" % s, tuple(lb), tuple(lb + Vector((0.002 * s, 0.002, 0.040))),
                      0.030, 0.026), "head", "骨", "chunk", "head", "fang")

    for s in (1, -1):
        u.box("hd_socket_%d" % s, (s * 0.068, 0.280, 1.826), (0.062, 0.036, 0.040),
              "head", "皮革暗", rot=(math.radians(-14), math.radians(s * 14), -s * 0.28),
              style="chunk", module="head", tag="eye")
        u.box("hd_eye_%d" % s, (s * 0.070, 0.298, 1.828), (0.040, 0.022, 0.026),
              "head", "team_trim", rot=(math.radians(-14), math.radians(s * 14), -s * 0.28),
              style="chunk", module="head", tag="eye")
        u.box("hd_brow_%d" % s, (s * 0.084, 0.282, 1.862), (0.092, 0.052, 0.020),
              "head", "皮肤暗", rot=(0, math.radians(-14), -s * 0.24), style="chunk",
              module="head", tag="brow")

    for s, side in ((1, "R"), (-1, "L")):
        root = Vector((s * 0.092, 0.042, 1.866))
        tip = Vector((s * 0.196, -0.092, 2.012))
        u.add(ear_plate("hd_ear_" + side, tuple(root), tuple(tip),
                        0.116, 0.132, 0.056, 0.040),
              "head", "皮肤", "chunk", "head", "ear")
        r2 = root + (tip - root) * 0.16 + Vector((0, 0.022, 0))
        t2 = root + (tip - root) * 0.84 + Vector((0, 0.020, 0))
        u.add(ear_plate("hd_ear_in_" + side, tuple(r2), tuple(t2),
                        0.062, 0.070, 0.014, 0.012),
              "head", "皮肤暗", "chunk", "head", "ear")

    u.add(boss("hd_browbone", (0.0, 0.156, 1.892), 0.074, 0.098, 0.024, n=6),
          "head", "骨", "chunk2", "head", "browbone")
    u.add(boss("hd_browrim", (0.0, 0.152, 1.878), 0.104, 0.130, 0.016, n=6),
          "head", "team_trim", "chunk", "head", "browbone")

    fins = (("head", 0.104, 1.920, 0.048, 1.958, 0.116, 0.056),
            ("head", 0.020, 1.932, -0.052, 1.982, 0.128, 0.058),
            ("head", -0.058, 1.898, -0.134, 1.958, 0.110, 0.050),
            ("head", -0.082, 1.826, -0.160, 1.888, 0.098, 0.044),
            ("chest", -0.240, 1.688, -0.302, 1.758, 0.098, 0.030),
            ("chest", -0.274, 1.604, -0.336, 1.670, 0.090, 0.028),
            ("chest", -0.278, 1.514, -0.336, 1.578, 0.084, 0.026))
    for i, (bone, y0, z0, y1, z1, w, t) in enumerate(fins):
        u.add(fin("hd_fin%d" % i, y0, z0, y1, z1, w, t),
              bone, "皮革暗", "chunk", "head", "mane")
    u.add(KU.claw("hd_mane_n", (0.0, -0.040, 1.756), (0.0, -0.228, 1.678), 0.140, 0.086),
          "neck", "皮革暗", "chunk", "head", "mane")


# ══ 8. 巫杖（骨轴 = 杖身 = +Y 局部）════════════════════════════════════════
def _hexrow(z, r, phase=30.0):
    return [(STAFF_X + r * math.cos(math.radians(phase + 60 * k)),
             STAFF_Y + r * math.sin(math.radians(phase + 60 * k)), z) for k in range(6)]


def staff(u):
    bone = "weapon_R"
    st = ((STAFF_BUTT, 0.031), (0.32, 0.029), (0.62, 0.028), (0.92, 0.027),
          (1.20, 0.026), (1.46, 0.025), (1.66, 0.024), (1.80, 0.023),
          (STAFF_TOP, 0.022))
    u.add(K.loft("wp_shaft", [_hexrow(z, r) for (z, r) in st]),
          bone, "皮革暗", "facet", "staff", "shaft")
    for i, z in enumerate((0.700, 0.960, 1.320)):
        u.add(ring("wp_ring%d" % i, (STAFF_X, STAFF_Y, z), (0, 0, 1),
                   0.025, 0.037, 0.036, 6), bone, "骨", "chunk2", "staff", "ring")
    u.otube("wp_grip",
            [(1.078, STAFF_X, STAFF_Y, 0.062, 0.062, 0.018),
             (1.122, STAFF_X, STAFF_Y, 0.068, 0.068, 0.020),
             (1.182, STAFF_X, STAFF_Y, 0.068, 0.068, 0.020),
             (1.222, STAFF_X, STAFF_Y, 0.060, 0.060, 0.018)],
            bone, "皮革", "chunk", "staff", "grip", cw=0.018)
    u.otube("wp_grip_band",
            [(1.140, STAFF_X, STAFF_Y, 0.072, 0.072, 0.020),
             (1.162, STAFF_X, STAFF_Y, 0.072, 0.072, 0.020)],
            bone, "team", "chunk", "staff", "grip", cw=0.020)

    # 杖顶骨爪托：三根骨爪向上收拢抱珠（爪尖离珠面 1 cm）
    for i in range(3):
        a = math.radians(90 + 120 * i)
        b = Vector((STAFF_X + 0.038 * math.cos(a), STAFF_Y + 0.038 * math.sin(a),
                    STAFF_TOP - 0.022))
        m = Vector((STAFF_X + 0.080 * math.cos(a), STAFF_Y + 0.080 * math.sin(a),
                    ORB_C.z - 0.046))
        t = Vector((STAFF_X + 0.064 * math.cos(a), STAFF_Y + 0.064 * math.sin(a),
                    ORB_C.z + 0.012))
        u.add(KU.claw("wp_fork%d" % i, tuple(b), tuple(m), 0.034, 0.026),
              bone, "骨", "chunk2", "staff", "fork")
        u.add(KU.claw("wp_fork_t%d" % i, tuple(m), tuple(t), 0.028, 0.020),
              bone, "骨", "chunk2", "staff", "fork")
    u.add(ring("wp_seat", (STAFF_X, STAFF_Y, STAFF_TOP - 0.012), (0, 0, 1),
               0.024, 0.046, 0.032, 6), bone, "骨", "chunk2", "staff", "fork")
    # 宝珠（挂 fx_ball）
    u.add(octa("wp_orb", tuple(ORB_C), ORB_R, ORB_H, n=4),
          "fx_ball", "辉", "sharp", "staff", "orb")
    u.add(ring("wp_orb_seat", (STAFF_X, STAFF_Y, ORB_C.z - 0.064), (0, 0, 1),
               0.022, 0.040, 0.020, 6), "fx_ball", "骨", "chunk", "staff", "orb")

    u.add(ring("wp_butt", (STAFF_X, STAFF_Y, STAFF_BUTT + 0.030), (0, 0, 1),
               0.030, 0.044, 0.034, 6), bone, "骨", "chunk2", "staff", "butt")
    u.add(KU.claw("wp_butt_tooth", (STAFF_X, STAFF_Y + 0.030, STAFF_BUTT + 0.022),
                  (STAFF_X, STAFF_Y + 0.042, STAFF_BUTT - 0.048), 0.036, 0.028),
          bone, "骨", "chunk", "staff", "butt")


# ══ 9. 电弧（按 1/40 建，静止藏在宝珠里）═══════════════════════════════════
def fx(u):
    for i in range(2):
        pts = []
        for j in range(8):
            t = j / 7.0
            a = math.radians(28 + i * 172) + t * 5.0
            r = 0.088 + 0.042 * math.sin(t * math.pi * 1.3) + 0.012 * math.sin(t * 9.0)
            z = -0.070 + 0.150 * t
            pts.append(ORB_C + Vector((r * math.cos(a), r * math.sin(a), z)))
        rows = []
        for j, p in enumerate(pts):
            dd = (pts[min(j + 1, 7)] - pts[max(j - 1, 0)]).normalized()
            side = dd.cross(Vector((0, 0, 1)))
            if side.length < 1e-5:
                side = Vector((1, 0, 0))
            side.normalize()
            up = dd.cross(side).normalized()
            w = 0.013 * (1.0 - 0.45 * j / 7.0)
            rows.append([tuple(p + side * w + up * w * 0.5),
                         tuple(p + side * w - up * w * 0.5),
                         tuple(p - side * w - up * w * 0.5),
                         tuple(p - side * w + up * w * 0.5)])
        ob = K.loft("fx_arc%d" % i, rows, True)
        u.add(shrink(ob, ORB_C, FX_K), "fx_arc", "辉", "sharp", "fx", "arc")


# ══ 组装 ════════════════════════════════════════════════════════════════════
def build(low=False, modules=None):
    want = set(MODULES if modules is None else modules)
    u = K.Unit2(PREFIX, MATS, low=low)
    if "body" in want:
        legs(u)
        pelvis(u)
        torso(u)
        neck(u)
        arms(u)
        pauldron(u)
        tail(u)
    if "head" in want:
        head(u)
    if "staff" in want:
        staff(u)
    if "fx" in want:
        fx(u)
    return u


def build_rig(name="RIG_" + NAME):
    return K.build_rig(BONES, name)


def report():
    return "\n".join([
        "[joints] hip=%.3f knee=(%.3f,%.3f) hock=(%.3f,%.3f) ball=%.3f top=%.3f"
        % (Z_HIP, KNE_R.y, KNE_R.z, HCK_R.y, HCK_R.z, BAL_R.z, Z_TOP),
        "[leg] thigh=%.3f shin=%.3f foot=%.3f toe=%.3f reach=%.3f/%.3f"
        % (L_THIGH, L_SHIN, L_FOOT, L_TOE, (HCK_R - HIP_R).length, L_THIGH + L_SHIN),
        "[armR] elbow=(%.3f,%.3f,%.3f) wrist=(%.3f,%.3f,%.3f) reach=%.3f/%.3f"
        % (ELB_R.x, ELB_R.y, ELB_R.z, WRI_R.x, WRI_R.y, WRI_R.z,
           (WRI_R - SH_R).length, L_UPPER + L_FORE),
        "[staff] butt=%.3f top=%.3f orb=%.3f" % (STAFF_BUTT, STAFF_TOP, ORB_C.z),
        "[bones] %d" % len(BONES),
    ])
