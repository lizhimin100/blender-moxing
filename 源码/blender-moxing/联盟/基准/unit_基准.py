"""unit_基准.py —— 联盟格网基准身 v1（17 格 / 4 格头 / 6 格躯干 / 六条关节线）

这是**基准**，不是某个兵种：`assemble()` 只搭"一个联盟士兵的身体"，
兵种差异（大件 + 装饰）留给派生文件（`unit_长枪兵.py` / `unit_弓箭手.py`）。

基准锁死（派生不许改，见 `文档/格网单位规范.md` §2.1）：
  格 0.1 · 总高 17 格 · 头 4 格宽（x −2..2, z 13..17）· 躯干 6 格（x −3..3, y −2..2, z 10..13）
  关节 z：0 / 2 / 6 / 9 / 13 / 17 · 眼 slab 0.6×0.5 · 队色横线 ≤2 道 · 材质三槽

剪影的四条处理（这套基准好看的全部原因，改之前先读）
  ① **胸宽腰窄**：z 12..13 是 6 格，z 10..12 收到 4 格。6 格躯干 + 两侧各 2 格手臂
     如果一路等宽，就是一块 10 格宽的板 —— 腋下必须让出 1 格缺口。
  ② **两腿之间一条暗缝**：4 格总宽是定死的（腿会碰在一起），靠内侧列压暗两档读出两条腿。
  ③ **甲片一律"贴片"不"填格"**：护肩 / 护膝 / 胸牌都是亚格薄片，与母件留 0.04–0.08 格间隙。
     用格子填甲片必然与母件共面（z-fighting），这是格网档唯一的硬伤来源。
  ④ **正面只留三个读点**：盔箍（蓝）、胸牌（蓝 + 金框）、腰带（皮 + 金扣）。
     其余全部是同色系的明度差 —— 色一多，96 px 就糊成一团。

配色秩序（明度从低到高）：
  铁 0.20 < 皮暗 0.30 < 钢暗 0.42 < 皮 0.48 < 钢 0.58 < 布暗 0.69 < 布 0.79 < 布亮 0.87
  蓝只落两处（盔箍 + 胸牌），金只做框、扣、包角。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = HERE
while not os.path.isdir(os.path.join(ROOT, "库")):
    _up = os.path.dirname(ROOT)
    if _up == ROOT:
        break
    ROOT = _up
for _p in (os.path.join(ROOT, "库"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import voxbase as V  # noqa: E402

BASE = "v1"
DIFF = ("基准",)
NAME = "unit_基准"
PREFIX = "base"

OPT = dict(
    tunic="cloth_pale",       # 戎装主色
    tunic_dark="cloth",       # 下摆 / 背心
    pants="cloth_dark",       # 裤（比戎装深一档，上半身才立得住）
    pants_hi="cloth",
    boot="leather_dark",
    belt="leather",
    metal="steel",            # 盔 / 护肩 / 护膝
    metal_hi="steel_pale",
    metal_dark="steel_dark",
    sleeve="cloth",           # 上臂布袖
    bracer="leather",         # 前臂护腕
    skin="skin",
    chest="panel",            # "panel" 队色胸牌 / "strap" 皮背带（弓箭手）
)


# ── 腿 ──────────────────────────────────────────────────────────────────────
def legs(g, o):
    """靴 / 绑腿 / 裤 / 护膝。内侧列压暗 = 两条腿之间的暗缝。"""
    seam_p = V.darken(o["pants"], 2, 0.88)
    seam_b = V.darken(o["boot"], 2, 0.86)

    # 脚（骨 foot_R）：铁鞋底 + 皮鞋面
    g.part("foot_R", "foot_R")
    g.box(0, 2, -1, 1, 0, 1, "iron")
    g.box(0, 2, -1, 1, 1, 2, o["boot"])
    g.box(0, 2, -1, 0, 1, 2, "leather_dark")
    g.tint(0, 1, -1, 1, 0, 2, seam_b)
    g.slab(1.0, 1.01, 1.45, 1.55, 0.08, 0.55, "leather_hi")     # 鞋舌

    # 趾（骨 toe_R）：铁包头，比鞋面矮一格 —— 剪影上才读得出"脚"
    g.part("toe_R", "toe_R")
    g.box(0, 2, 1, 2, 0, 1, "iron")
    g.slab(1.0, 2.01, 0.52, 1.5, 0.08, 0.4, "steel_deep")

    # 小腿（骨 shin_R）
    g.part("shin_R", "shin_R")
    g.box(0, 2, -1, 1, 2, 3, "leather_dark")                    # 靴口 / 绑腿
    g.box(0, 2, -1, 1, 3, 6, o["pants"])
    g.box(0, 2, -1, 1, 3, 4, o["pants_hi"])                     # 小腿肚受光
    g.tint(0, 1, -1, 1, 2, 6, seam_p)
    g.tint(0, 1, -1, 1, 2, 3, seam_b)
    g.box(0, 2, -1, 1, 2, 3, "leather_dark")
    # 护膝：一条绕到两侧的甲箍（比贴片耐看，也不挡膝弯）
    g.slab(1.0, 1.02, 5.15, 1.9, 0.14, 1.05, o["metal"])
    g.slab(1.0, 1.09, 5.55, 1.4, 0.06, 0.30, o["metal_hi"])

    # 大腿（骨 thigh_R）
    g.part("thigh_R", "thigh_R")
    g.box(0, 2, -1, 1, 6, 9, o["pants"])
    g.box(0, 2, -1, 1, 8, 9, "cloth_dark")
    g.tint(0, 1, -1, 1, 6, 9, seam_p)
    g.cut(-1, 1, -1, 1, 8, 9)                                   # 裆下开 V 口，两条腿分开
    g.sleeve("knee", V.darken(o["pants"], 2), 0.5, 1.5, -0.5, 0.5, 5, 6)

    for pn in ("foot_R", "toe_R", "shin_R", "thigh_R"):
        g.mirror(pn)


# ── 腰 ──────────────────────────────────────────────────────────────────────
def pelvis(g, o):
    """腰带一圈（4 格宽）+ 裆。腰线 z=10 藏在腰带里，转身不露缝。"""
    g.part("pelvis", "hips")
    g.box(-2, 2, -1, 2, 9, 10, o["belt"])
    g.box(-2, 2, 1, 2, 9, 10, "leather_hi")
    g.box(-2, 2, -1, 0, 9, 10, "leather_dark")
    g.slab(0, 2.03, 9.5, 0.85, 0.10, 0.62, "trim")              # 腰扣
    g.slab(0, 2.11, 9.5, 0.30, 0.06, 0.30, "trim_hi")
    # 胯套筒（父件 hips 伸进大腿）
    g.sleeve("hip", V.darken(o["pants"], 2), 0.5, 1.5, -0.5, 0.5, 7.5, 8.5, part="pelvis")
    g.sleeve("hip", V.darken(o["pants"], 2), -1.5, -0.5, -0.5, 0.5, 7.5, 8.5, part="pelvis")


# ── 躯干 ────────────────────────────────────────────────────────────────────
def torso(g, o):
    """胸宽腰窄；正面只有三个读点：蓝胸牌 + 金框 + 皮肩带。"""
    g.part("torso", "chest")
    g.box(-2, 2, -2, 2, 10, 11, o["tunic"])
    g.box(-3, 3, -2, 2, 11, 13, o["tunic"])
    g.box(-2, 2, -2, 2, 10, 11, o["tunic_dark"])                # 下摆压暗
    g.box(-2, 2, -2, -1, 10, 13, "cloth_dark")                  # 背心深一号
    g.box(-3, 3, -2, -1, 12, 13, "cloth_dark")

    # 胸牌：金框（后）+ 队色面（前），两层差 0.04 格；chest="strap" 时换成斜挎皮带
    # 队色占比就靠这一块控制：框 2.0×1.55、面 1.55×1.15，投影约 6 列（≈5%）
    if o.get("chest", "panel") == "panel":
        g.slab(0, 2.02, 11.42, 2.00, 0.08, 1.55, "trim")
        g.slab(0, 2.06, 11.42, 1.55, 0.06, 1.15, "team")
        g.slab(0, 2.09, 11.80, 1.20, 0.05, 0.12, "team_hi")     # 面上一道高光
        for x in (-1.42, 0.92):
            g.slab(x, 2.01, 12.42, 0.52, 0.10, 1.10, "leather")
    else:
        # 斜挎皮带（弓手的"轻装"读法）：右肩 → 左胯。**用放样带，不用九级台阶**
        # ——一级一块 slab 会让九片正面共面，浏览器里整条带子闪。
        g.loft([(0.145, 0.208, 1.235), (-0.145, 0.208, 1.030)],
               0.036, 0.006, "leather", normal=(0.0, 1.0, 0.0))
        g.loft([(0.145, 0.219, 1.240), (-0.145, 0.219, 1.036)],
               0.011, 0.003, "leather_hi", normal=(0.0, 1.0, 0.0))
        g.slab(0, 2.13, 11.32, 0.66, 0.06, 0.66, "trim")        # 胸扣
        g.slab(0, 2.16, 11.32, 0.30, 0.04, 0.30, "leather_dark")
    if o.get("harness"):
        # 胸甲背带：两条从肩到腰的皮带，压在胸牌**外侧**（读作"挂甲"，不是围裙）
        # 第三层（gold clasp）必须比第一层再往外 3 mm：原先是 2.09 对 2.07，
        # 外面只差 1 mm，落在 zfight 容差（1.2 mm）里 → 判成共面对。
        for sx in (-2.42, 2.42):
            g.slab(sx, 2.07, 11.45, 0.52, 0.10, 2.50, o["harness"])
            g.slab(sx, 2.06, 11.45, 0.30, 0.09, 2.30, V.darken(o["harness"], 1))
            g.slab(sx, 2.12, 12.45, 0.56, 0.08, 0.22, "trim_dark")
    # 领口压边
    g.slab(0, 1.98, 12.78, 2.8, 0.10, 0.30, "leather_dark")
    # 肩套筒（父件 chest 伸进上臂）
    g.sleeve("shoulder", V.darken(o["tunic"], 2), 3, 4, -0.5, 0.5, 12, 13, part="torso")
    g.sleeve("shoulder", V.darken(o["tunic"], 2), -4, -3, -0.5, 0.5, 12, 13, part="torso")
    # 脖子（挂在 neck 骨上，头一转会露出来）—— 居中的 1 格柱，按套筒处理（允许半格）
    g.part("neck", "neck")
    g.sleeve("neck", "skin_dark", -0.5, 0.5, -0.5, 0.5, 13.1, 14, part="neck")


# ── 头 ──────────────────────────────────────────────────────────────────────
def head(g, o, kind="pot"):
    """kind="pot" 锅盔（长枪兵）/ "hood" 兜帽（弓箭手，见派生文件）。"""
    g.part("head", "head")
    g.box(-2, 2, -2, 2, 13, 17, o["skin"])
    if kind == "pot":
        g.box(-2, 2, -2, 2, 15, 17, o["metal"])                 # 盔体
        g.box(-2, 2, -2, -1, 13, 15, o["metal_dark"])           # 后脑压暗
        g.box(-2, -1, -2, 2, 13, 15, o["metal"])                # 右颊
        g.box(1, 2, -2, 2, 13, 15, o["metal"])                  # 左颊
        g.tint(-2, 2, -2, 2, 15, 16, "team")                    # 队色盔箍（1 道）
        g.box(-2, 2, -2, -1, 15, 16, "team_deep")
        g.tint(-2, 2, -2, 2, 16, 17, "steel_pale")              # 盔顶受光
        for cx0, cy0 in ((-2, -2), (1, -2), (-2, 1), (1, 1)):   # 盔顶切角
            g.cut(cx0, cx0 + 1, cy0, cy0 + 1, 16, 17)
        g.slab(0, 2.01, 15.02, 3.9, 0.06, 0.20, "steel_pale")   # 盔檐
        g.slab(0, 2.03, 14.92, 2.1, 0.05, 0.14, "steel_deep")   # 眉眼阴影
        g.slab(0, -2.01, 13.7, 3.9, 0.06, 1.2, "steel_deep")    # 后颈护片
        g.slab(0, 2.02, 13.02, 1.4, 0.06, 0.18, "leather_dark") # 下颏带
    else:
        g.box(-2, 2, -2, 2, 14, 17, o["tunic_dark"])
        g.box(-2, 2, -2, 2, 15, 17, o["tunic"])
        g.box(-2, 2, -2, -1, 13, 17, o["tunic"])                # 后帘
        g.box(-2, -1, -2, 2, 13, 17, o["tunic_dark"])
        g.box(1, 2, -2, 2, 13, 17, o["tunic_dark"])
        g.tint(-2, 2, -2, 2, 15, 16, "team")                    # 队色帽箍（在眉上）
        g.box(-2, 2, -2, -1, 15, 16, "team_deep")
        for cx0, cy0 in ((-2, -2), (1, -2), (-2, 1), (1, 1)):
            g.cut(cx0, cx0 + 1, cy0, cy0 + 1, 16, 17)

    # 五官（slab 亚格）
    for sx in (-0.78, 0.78):
        g.slab(sx, 2.04, 14.50, 0.62, 0.08, 0.50, "eye")
    g.slab(0, 2.07, 14.02, 0.42, 0.16, 0.52, "skin_dark")       # 鼻
    g.slab(0, 2.03, 13.40, 0.50, 0.06, 0.16, "skin_dark")       # 嘴
    g.slab(0, 2.02, 13.92, 1.9, 0.05, 0.10, "skin_dark")        # 腮线
    g.use("head").feat.append(("eye", 2.04))


# ── 臂 ──────────────────────────────────────────────────────────────────────
def arms(g, o):
    """上臂 2 格 + 前臂 2 格 + 手 2 格；护肩是套在上臂顶上的两层壳。"""
    g.part("upperarm_R", "upperarm_R")
    g.box(3, 5, -1, 1, 11, 13, o["sleeve"])
    g.box(3, 5, -1, 1, 11, 12, V.darken(o["sleeve"], 1))
    g.sleeve("elbow", V.darken(o["sleeve"], 2), 3.5, 4.5, -0.5, 0.5, 10, 11)
    # 护肩：两层叠壳，和上臂留 0.1 格间隙，绝不共面
    g.slab(4.0, 0.0, 12.16, 2.34, 2.34, 1.06, o["metal"])
    g.slab(4.0, 0.0, 12.74, 2.10, 2.10, 0.40, o["metal"])
    g.slab(4.0, 0.0, 12.96, 1.70, 1.70, 0.22, o["metal_hi"])    # 第三层：收口高光

    g.part("forearm_R", "forearm_R")
    g.box(3, 5, -1, 1, 9, 11, o["sleeve"])
    g.box(3, 5, -1, 1, 9, 10, o["bracer"])
    g.slab(4.0, 1.01, 9.85, 1.55, 0.08, 0.20, "leather_hi")

    g.part("hand_R", "hand_R")
    g.box(3, 5, -1, 1, 7, 9, o["skin"])
    g.box(3, 5, -1, 1, 7, 8, "skin_dark")                       # 指节压暗
    g.slab(3.32, 1.01, 8.35, 0.44, 0.08, 0.7, "skin_dark")       # 拇指
    g.slab(4.0, -1.01, 8.3, 1.1, 0.06, 0.5, "skin_dark")

    for pn in ("upperarm_R", "forearm_R", "hand_R"):
        g.mirror(pn)


def assemble(g, o=None, kind="pot"):
    o = dict(OPT, **(o or {}))
    legs(g, o)
    pelvis(g, o)
    torso(g, o)
    arms(g, o)
    head(g, o, kind=kind)
    return g


def build(overrides=None, kind="pot", name="基准预览", team="联盟"):
    g = V.Grid(name, team=team)
    assemble(g, overrides, kind=kind)
    return g


def report():
    return build().audit()
