"""unit_长枪兵.py —— 联盟·长枪兵（格网档 v3）

v3 只动"看起来不对"的三处，基准身高/头/关节线一律不碰：

  ① **枪**：v2 的枪缨是两块 0.1 m 厚的方板横着支棱在枪头下面（用户说的"突出来的表格"），
     枪杆是 0.1 见方的粗木条，刃是锤子。v3 交给 `props_vox.spear()`：
     0.056 见方的细杆 + 三段收尖的叶刃 + 贴杆下垂的三缕缨，全部连续放样。
  ② **护颈**：v2 是两片 5.4 格宽、0.22 格厚的薄片，在肩上支出一圈"书桌沿"。
     v3 换成四片 0.03 厚的钢板围一圈（真的护颈，不是台面）。
  ③ **腿裙**：腰下垂五条皮甲片，把"睡衣"读法压掉，同时给下半身加一层细节。

其余（锅盔 / 蓝盔箍 / 胸牌 / 护腕 / 铁鞋头）沿用基准，队色仍是两道横线：
盔箍 + 胸牌。

    BASE = "v1"
    DIFF = ("大件:长枪 2.25 m", "装饰:护颈", "装饰:腿裙")
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
for _p in (os.path.join(ROOT, "库"), os.path.join(ROOT, "联盟", "基准"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import voxbase as V  # noqa: E402
import props_vox as P  # noqa: E402
import unit_基准 as B  # noqa: E402

BASE = "v1"
DIFF = ("大件:长枪 2.25 m", "装饰:护颈", "装饰:腿裙")
NAME = "长枪兵"
KEY = "长枪兵"
PREFIX = "sp"

OPT = dict(
    tunic="cloth_pale",
    tunic_dark="cloth",
    pants="cloth_dark",
    pants_hi="cloth",
    boot="leather_dark",
    belt="leather",
    metal="steel",
    metal_hi="steel_pale",
    metal_dark="steel_dark",
    sleeve="cloth",
    bracer="leather",
    skin="skin",
    harness="leather",
)

# 枪轴线（世界）：正好落在右手静止位置上，骨原点 = 握把
SPEAR_X, SPEAR_Y = 0.40, 0.10
SPEAR_BUTT, SPEAR_LEN = 0.80, 2.25


def helmet(g):
    """锅盔收口：把"白帽顶"压回钢色，加一道盔脊、一条鼻梁、一片后颈帘。

    基准的盔顶是 `steel_pale` 整层 + 四角切掉，远看像戴了顶白帽子。
    这里只改色 + 加三条 1 cm 级的脊线，不动格数与轮廓（总高仍是 17 格）。
    """
    g.use("head")
    g.tint(-2, 2, -2, 2, 16, 17, "steel_dark")             # 顶面压深，不再像白帽
    g.tint(-2, 2, -2, -1, 16, 17, "steel_dark")            # 后脑压暗
    g.tint(-1, 1, -2, 2, 16, 17, "steel")                  # 盔脊（染色，不加薄片）
    g.slab(0, 2.08, 15.04, 3.80, 0.05, 0.10, "steel_edge")  # 盔檐高光
    g.slab(0, 2.06, 14.42, 0.18, 0.07, 1.05, "steel_dark")  # 鼻梁
    g.slab(0, -2.03, 13.55, 3.2, 0.05, 0.90, "steel_dark")  # 后颈帘


def gorget(g):
    """护颈：四片 3 cm 厚的钢片围着领口一圈（不再是两片 0.22 m 厚的"书桌沿"）。"""
    g.use("torso")
    z = 12.72
    g.slab(0, 2.16, z, 3.10, 0.55, 0.26, "steel_dark")       # 前
    g.slab(0, -2.16, z, 3.10, 0.55, 0.26, "steel_dark")      # 后
    for sx in (-1, 1):
        g.slab(sx * 3.16, 0, z, 0.55, 3.10, 0.26, "steel_dark")   # 两侧
    g.slab(0, 2.19, z + 0.02, 2.30, 0.45, 0.08, "steel")     # 前片受光


def pteruges(g):
    """腿裙：腰带下垂四片前甲 + 两片侧甲 + 一片后摆，每片 2.2 格长。

    甲片是**贴片**：厚 0.3 格（3 cm），压进腰带 1.5 cm，离大腿面留 4 mm。
    底端压深一号、顶端一条金线 —— 三层读作"甲片叠压"，不是一块围裙。
    """
    g.use("pelvis")
    for x in (-1.62, -0.56, 0.56, 1.62):
        g.slab(x, 2.05, 7.95, 0.95, 0.30, 2.20, "leather")
        g.slab(x, 2.08, 7.20, 0.90, 0.30, 0.34, "leather_dark")
        g.slab(x, 2.09, 8.92, 0.88, 0.30, 0.10, "leather_hi")
    for sx in (-1, 1):
        g.slab(sx * 2.05, 0.02, 7.95, 0.30, 1.70, 2.20, "leather")
        g.slab(sx * 2.08, 0.02, 7.20, 0.30, 1.62, 0.34, "leather_dark")
    g.slab(0, -2.04, 7.98, 1.90, 0.30, 2.10, "leather_dark")   # 后摆一片


def build():
    g = V.Grid(NAME, team="联盟")
    B.assemble(g, OPT, kind="pot")
    gorget(g)
    helmet(g)
    pteruges(g)
    P.spear(g, x=SPEAR_X, y=SPEAR_Y, butt=SPEAR_BUTT, length=SPEAR_LEN)
    return g


def build_rig(name="RIG_" + NAME):
    return V.Grid(NAME, team="联盟").build_rig(name)


def report():
    return build().audit()


if __name__ == "__main__":
    build().report()
