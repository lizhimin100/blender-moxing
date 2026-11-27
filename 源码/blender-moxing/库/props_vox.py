"""props_vox.py —— 格网单位的"道具库"（长枪 / 长弓 / 箭筒 / 披风 / 箭）

为什么单独一件：v2 的长枪和长弓都是**每个兵种各写一遍**，于是"枪缨凸出两块方板"、
"弓叠 46 片 slab"这类问题只能各修一次。这一版把它们做成带参数的组件：

    spear(g, ...)     长枪（细杆 / 握把 / 箍 / 叶刃 / 缨）
    bow(g, ...)       长弓（连续放样的弓臂 + 弓弦 + 握把）
    quiver(g, ...)    箭筒（斜挂的筒身 + 三支箭）
    cape(g, ...)      披风（连续布片 + 金边）
    arrow_prop(g,...) 搭在弦上的箭

**单位统一（吃过亏）**：这个文件里所有坐标和尺寸都是**米**，写格子时由 `_sl()` 转成格。
v3 第一版把米直接传给了 `g.slab()`（它吃的是格），结果整根枪的贴片跑到身体中线上，
远看是"枪在旁边、箍在腰上"。以后新道具一律用 `_sl`。

三条纪律：
1. **弧线件一律连续放样**（`g.loft` / `g.sheet`），不许拿 slab 一片片叠 —— 叠出来的
   近共面侧壁在浏览器里会闪，正视还是楼梯。
2. **任何两层贴片的外表面至少错开 3 mm**，端点要塞进母件 1 cm，避免端盖共面。
3. 武器件挂 `big=True`：不参与总高 / 队色 / ⑬⑮ 判定。

坐标：建模期 +Y 正面、+Z 向上。武器挂在 `weapon_R`（枪/箭）与 `weapon_L`（弓），
骨原点 = **握把**，骨 +Y = 武器长轴、骨 −X = 正面（弓腹 / 刃面）。
"""
import math

import voxbase as V

CELL = V.CELL


def _sl(g, x, y, z, sx, sy, sz, color, part=None):
    """米 → 格，再交给 slab。所有道具的贴片都走这一个入口。"""
    return g.slab(x / CELL, y / CELL, z / CELL,
                  sx / CELL, sy / CELL, sz / CELL, color, part)


# ══ 长枪 ════════════════════════════════════════════════════════════════════
def spear(g, part="spear", bone="weapon_R", x=0.40, y=0.10, z=0.80,
          butt=0.80, length=2.25, tassel=True):
    """长枪：握把在 z，鐏在 z-butt，尖端在 z+length-butt。

    比例（96 px 还要认出是"枪"）：杆 0.056 见方（细、直、长，和 0.2 见方的手臂对比）；
    叶刃 0.11 宽、0.31 长、三段收尖；缨挂在箍下面、**贴着杆往下垂**。
    """
    g.part(part, bone, big=True)
    z0 = z - butt
    z1 = z + (length - butt)
    z_blade = z1 - 0.34
    zb = z_blade + 0.09

    # 杆：连续放样，下粗上细
    g.loft([(x, y, z0 + 0.04), (x, y, z0 + 0.55), (x, y, z_blade + 0.02)],
           [0.030, 0.028, 0.024], [0.030, 0.028, 0.024], "wood")
    # 鐏（铁脚）
    _sl(g, x, y, z0 + 0.055, 0.078, 0.078, 0.115, "iron")
    _sl(g, x, y, z0 + 0.008, 0.068, 0.068, 0.028, "iron_dark")
    _sl(g, x, y, z0 + 0.118, 0.072, 0.072, 0.020, "iron_hi")
    # 握把缠皮：比杆粗 1 cm（拳头整个含住）
    _sl(g, x, y, z, 0.086, 0.086, 0.235, "leather_dark")
    for dz in (-0.085, 0.0, 0.085):
        _sl(g, x, y, z + dz, 0.094, 0.094, 0.026, "leather")
    # 中段铁箍 / 枪头下三道箍
    _sl(g, x, y, z_blade - 0.10, 0.066, 0.066, 0.028, "iron_hi")
    _sl(g, x, y, z_blade + 0.015, 0.070, 0.070, 0.030, "iron_hi")
    _sl(g, x, y, z_blade + 0.048, 0.080, 0.080, 0.026, "trim")
    _sl(g, x, y, z_blade + 0.075, 0.064, 0.064, 0.030, "steel_deep")

    # 叶刃：三段收尖 + 中央脊
    g.loft([(x, y, zb), (x, y, zb + 0.09), (x, y, zb + 0.17), (x, y, z1)],
           [0.054, 0.046, 0.026, 0.005], [0.014, 0.012, 0.008, 0.003], "steel")
    g.loft([(x, y + 0.010, zb + 0.01), (x, y + 0.008, zb + 0.12),
            (x, y + 0.005, z1 - 0.02)],
           [0.012, 0.009, 0.004], [0.004, 0.003, 0.002], "steel_edge")
    g.loft([(x, y - 0.010, zb + 0.01), (x, y - 0.008, zb + 0.12)],
           [0.012, 0.008], [0.004, 0.003], "steel_pale")

    if tassel:
        # 缨：束口 + 三缕贴着杆往下垂（唯一一处队色，不向两侧支棱）
        _sl(g, x, y, z_blade - 0.055, 0.086, 0.086, 0.034, "team")
        for dx, dy, ln in ((-0.030, 0.006, 0.150), (0.006, -0.030, 0.128),
                           (0.030, 0.012, 0.168)):
            g.loft([(x + dx, y + dy, z_blade - 0.070),
                    (x + dx * 1.25, y + dy, z_blade - 0.070 - ln)],
                   [0.016, 0.010], [0.014, 0.009], "team_deep")
        _sl(g, x, y, z_blade - 0.180, 0.052, 0.052, 0.030, "trim_dark")


# ══ 长弓 ════════════════════════════════════════════════════════════════════
def bow_bones(x=-0.40, y=0.10, span=1.16, brace=0.22, z_mid=0.80):
    """弓弦的两根骨：上段 / 下段，各自 head 在弓梢、+Y 指向弦中点。

    为什么要给弦单独的骨：弦必须**能拉开**。一根直的 loft 是刚性壳，拉弦手一动
    它不会跟着变形，看上去就是"手在拉空气"。拆成两段之后，每帧把骨的 +Y 转向
    "弓梢 → 拉弦手"，再沿 +Y 缩放（rest 长度 → 当前长度），弦自然形成三角形。
    骨挂在 `weapon_L` 下，所以弓怎么摆它们自动跟。

    只有弓箭手把这个列表塞进 `g.extra_bones`，人形基准的 25 根骨不动。
    """
    z0, z1 = z_mid - span / 2, z_mid + span / 2
    return [
        ("bow_up", (x + brace, y, z1 - 0.012), (x + brace, y, z_mid), "weapon_L"),
        ("bow_dn", (x + brace, y, z0 + 0.012), (x + brace, y, z_mid), "weapon_L"),
    ]


def bow(g, part="bow", bone="weapon_L", x=-0.40, y=0.10,
        span=1.16, brace=0.22, n=26):
    """长弓：**一整条连续放样的 D 形弓臂** + 弓弦 + 握把。

    骨原点 = 握把，骨 +Y = 弓长轴（世界 +Z），骨 −X = 弓腹（朝目标）。
    弓臂在 x 上向后（+X）弯、弦在 +X 侧、握把在最前（x）。
    """
    g.part(part, bone, big=True)
    z_mid = 0.80
    z0, z1 = z_mid - span / 2, z_mid + span / 2

    def back_of(a):
        b = brace * (a ** 1.85)
        if a > 0.93:
            b += 0.018 * (a - 0.93) / 0.07
        return b

    pts, ws, ts = [], [], []
    for i in range(n + 1):
        t = i / float(n)
        a = abs(t * 2.0 - 1.0)
        pts.append((x + back_of(a), y, z0 + t * span))
        ws.append(0.030 + 0.026 * max(0.0, 1.0 - a * 1.6))
        ts.append(0.013 + 0.013 * max(0.0, 1.0 - a * 1.6))
    g.loft(pts, ws, ts, "wood")
    # 弓背受光：一条更细的带子贴在外侧（x 再退 9 mm，不是共面贴片）
    pts2, ws2, ts2 = [], [], []
    for i in range(n + 1):
        t = i / float(n)
        a = abs(t * 2.0 - 1.0)
        w = 0.030 + 0.026 * max(0.0, 1.0 - a * 1.6)
        pts2.append((x + back_of(a) - w + 0.002, y - 0.004, z0 + t * span))
        ws2.append(0.013)
        ts2.append(0.005)
    g.loft(pts2, ws2, ts2, "wood_hi")
    # 握把：缠皮 + 两道绳（比弓臂粗 12 mm）
    _sl(g, x, y, z_mid, 0.062, 0.076, 0.180, "leather_dark")
    for dz in (-0.055, 0.055):
        _sl(g, x, y, z_mid + dz, 0.070, 0.082, 0.022, "leather")

    # 弓弦：**两段**（上梢→中点 / 下梢→中点），各自挂一根弦骨，可被拉成 V 形。
    # 两段在中点互相嵌进 6 mm，端盖不共面。
    g.part("bowstring_up", "bow_up", soft=True, big=True)
    g.loft([(x + brace, y, z1 - 0.012), (x + brace, y, z_mid - 0.006)],
           [0.006, 0.006], [0.005, 0.005], "trim_hi")
    _sl(g, x + brace, y, z_mid + 0.052, 0.011, 0.007, 0.024, "trim_dark")   # 搭箭点
    g.part("bowstring_dn", "bow_dn", soft=True, big=True)
    g.loft([(x + brace, y, z0 + 0.012), (x + brace, y, z_mid + 0.006)],
           [0.006, 0.006], [0.005, 0.005], "trim_hi")


# ══ 箭 ══════════════════════════════════════════════════════════════════════
def arrow_prop(g, part="arrow", bone="weapon_R", x=0.40, y=0.10, z=0.80, length=1.0):
    """搭在弦上的箭：骨原点 = 箭尾，+Y（世界 +Z）= 箭杆方向。"""
    g.part(part, bone, big=True)
    g.loft([(x, y, z + 0.02), (x, y, z + length - 0.05)],
           [0.011, 0.009], [0.011, 0.009], "wood_dark")
    # 镞：一条连续收尖的放样（原来是两块 slab 叠着，侧面差 1 mm 会闪）
    g.loft([(x, y, z + length - 0.080), (x, y, z + length - 0.030),
            (x, y, z + length)],
           [0.013, 0.009, 0.002], [0.006, 0.005, 0.002], "steel_pale")
    _sl(g, x, y, z + 0.035, 0.017, 0.017, 0.028, "trim_dark")
    for i, a in enumerate((0.0, 90.0)):
        ca, sa = abs(math.cos(math.radians(a))), abs(math.sin(math.radians(a)))
        _sl(g, x, y, z + 0.075 + i * 0.002, 0.044 * ca + 0.008, 0.044 * sa + 0.008,
            0.070 + i * 0.006, "cloth_pale")


# ══ 箭筒 ════════════════════════════════════════════════════════════════════
def quiver(g, part="quiver", bone="chest", n=3):
    """斜挂在右后肩的箭筒：筒身连续放样，筒口有箍，三支箭斜探出来。"""
    g.part(part, bone)
    p0 = (0.16, -0.30, 0.76)
    p1 = (0.08, -0.24, 1.26)
    mid = ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2, (p0[2] + p1[2]) / 2)
    g.loft([p0, mid, p1], [0.062, 0.058, 0.066], [0.062, 0.058, 0.066], "leather")
    g.loft([(p0[0] + 0.004, p0[1] - 0.003, p0[2] + 0.02),
            (p1[0] + 0.004, p1[1] - 0.003, p1[2] - 0.04)],
           [0.031, 0.033], [0.031, 0.033], "leather_dark")
    # 筒口 / 筒底加强箍（比筒身粗 8 mm，不会和筒面共面）
    _sl(g, p1[0], p1[1], p1[2] - 0.042, 0.140, 0.140, 0.040, "leather_hi")
    _sl(g, p1[0], p1[1], p1[2] - 0.068, 0.132, 0.132, 0.014, "trim_dark")
    _sl(g, p0[0], p0[1], p0[2] + 0.02, 0.126, 0.126, 0.030, "leather_dark")

    g.part(part + "_arrows", bone, soft=True)
    for i in range(n):
        dx = (i - 1) * 0.042
        dy = 0.012 * (i - 1)
        tail = (p1[0] + dx, p1[1] + dy, p1[2] - 0.06)
        tip = (p1[0] + dx * 1.35, p1[1] + dy * 1.2 - 0.03, p1[2] + 0.30 + 0.03 * i)
        g.loft([tail, tip], [0.010, 0.008], [0.010, 0.008], "wood_dark")
        _sl(g, tip[0], tip[1], tip[2] + 0.02, 0.020, 0.010, 0.050, "steel_pale")
        for k, a in enumerate((0.0, 90.0)):
            ca, sa = abs(math.cos(math.radians(a))), abs(math.sin(math.radians(a)))
            _sl(g, tip[0], tip[1], tip[2] - 0.048 - k * 0.004,
                0.034 * ca + 0.006, 0.034 * sa + 0.006, 0.056 + k * 0.006, "cloth")


# ══ 披风 ════════════════════════════════════════════════════════════════════
def cape(g, part="cape", bone="chest", top=1.27, hem=0.44, cols=7, rows=6,
         half_top=0.20, half_hem=0.28, y_top=-0.215, y_hem=-0.335, vhem=0.10):
    """披风：一张连续布片（7×6 点阵），下摆切 V，背后微鼓。

    连续布片只有一层壳 + 一圈封口，不会有几十片共面的布片互相打架；
    6 行就够做出"上窄下宽 + 后飘"的曲面。
    """
    g.part(part, bone, soft=True)
    grid = []
    for i in range(rows):
        u = i / float(rows - 1)
        z = hem + (top - hem) * u
        half = half_top + (half_hem - half_top) * (1.0 - u) ** 1.2
        yb = y_top + (y_hem - y_top) * (1.0 - u) ** 1.35
        row = []
        for j in range(cols):
            s = j / float(cols - 1) * 2.0 - 1.0
            zz = z + (vhem * (1.0 - abs(s)) if i == 0 else 0.0)
            yy = yb - 0.030 * (1.0 - s * s) * (1.0 - u)
            row.append((s * half, yy, zz))
        grid.append(row)
    g.sheet(grid, 0.008, "team")
    # 金边：沿下摆一条细带，压在下摆**外侧** 6 mm，不共面
    hempts = []
    for j in range(cols):
        s = j / float(cols - 1) * 2.0 - 1.0
        hempts.append((s * half_hem, y_hem - 0.030 * (1.0 - s * s) - 0.006,
                       hem + vhem * (1.0 - abs(s)) - 0.004))
    g.loft(hempts, 0.012, 0.012, "trim_dark", normal=(0.0, 1.0, 0.0))
    # 肩扣
    for sx in (-1, 1):
        _sl(g, sx * 0.155, -0.206, top - 0.03, 0.052, 0.052, 0.052, "trim")
