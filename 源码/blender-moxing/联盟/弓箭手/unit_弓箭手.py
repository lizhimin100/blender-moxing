"""unit_弓箭手.py —— 联盟·弓箭手（格网档 v3）

v3 的三处重做（都交给 `props_vox` 的组件，方便下一个兵种复用）：

  ① **弓**：v2 是 46 片互相重叠的 slab 叠出来的"木楼梯"，在浏览器里近共面侧壁会闪，
     正视还是一条锯齿。v3 用 `props_vox.bow()`：一整条连续放样的 D 形弓臂
     （26 环 + 背脊 + 弓弦 + 缠皮握把），弧是弧，也不会闪。
  ② **箭筒**：v2 是方盒 + 三支横插的箭（箭杆穿出筒壁）。v3 是斜挂的连续放样筒身，
     筒口有箍、三支箭从筒口斜探出来，羽毛错开。
  ③ **披风**：v2 一列格一列格往上垒，边缘是台阶。v3 是一张 7×6 的连续布片，
     上窄下宽、背后微鼓、下摆切 V、金边一条。

    BASE = "v1"
    DIFF = ("大件:长弓 1.16 m", "装饰:兜帽衬边", "装饰:披风", "装饰:箭筒")
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
DIFF = ("大件:长弓 1.16 m", "装饰:兜帽衬边", "装饰:披风", "装饰:箭筒")
NAME = "弓箭手"
KEY = "弓箭手"
PREFIX = "ar"

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
    bracer="leather_warm",
    skin="skin",
    chest="strap",
)

BOW_X, BOW_Y = -0.40, 0.10
BOW_SPAN, BOW_BRACE = 1.16, 0.22


def hood(g):
    """兜帽收口：顶面压一档、加一条折痕脊、后脑一个小尖、脸口一圈蓝衬边。"""
    g.use("head")
    g.tint(-2, 2, -2, 2, 16, 17, "cloth_dark")            # 顶面压两档，不再是"白帽"
    g.tint(-2, 2, -2, -1, 16, 17, "cloth_dark")
    g.tint(-1, 1, -2, 2, 16, 17, "cloth_pale")             # 折痕脊（染色，不加薄片）
    g.slab(0, -2.02, 16.30, 1.20, 0.06, 1.10, "cloth_dark")  # 后脑垂布
    # 脸口衬边（蓝）：三片，贴着脸颊与眉骨，不越出兜帽轮廓
    for sx in (-1, 1):
        g.slab(sx * 1.62, 2.05, 14.28, 0.34, 0.05, 1.56, "team_deep")
    g.slab(0, 2.07, 15.32, 3.10, 0.06, 0.28, "team_deep")
    g.slab(0, 2.05, 13.16, 1.55, 0.05, 0.22, "leather_dark")   # 下颏带


def vambrace(g):
    """左前臂护臂：弓箭手唯一的非对称件（挡弦）。薄片 1 cm，贴面 2 mm。

    前臂在 x −5..−3 格（−0.5..−0.3 m），正面朝 +Y，所以护板落在 y=1.07 格。
    """
    g.use("forearm_L")
    g.slab(-4.00, 1.07, 9.95, 1.35, 0.10, 1.55, "leather_warm")    # 正面护板
    g.slab(-4.00, 1.11, 10.55, 1.05, 0.06, 0.30, "leather_hi")     # 受光边
    g.slab(-5.06, 0.0, 9.95, 0.10, 1.35, 1.55, "leather_warm")     # 外侧面
    for z in (9.30, 10.45):
        g.slab(-4.00, 1.08, z, 1.39, 0.16, 0.20, "leather_dark")


def build():
    g = V.Grid(NAME, team="联盟")
    B.assemble(g, OPT, kind="hood")
    hood(g)
    vambrace(g)
    P.cape(g, top=1.265, hem=0.46, half_top=0.20, half_hem=0.285,
           y_top=-0.218, y_hem=-0.300, vhem=0.10)
    P.quiver(g)
    P.bow(g, x=BOW_X, y=BOW_Y, span=BOW_SPAN, brace=BOW_BRACE)
    # 弓弦的两段骨（拉弦用）：只有弓箭手有，人形基准 25 根不动
    g.extra_bones += P.bow_bones(BOW_X, BOW_Y, BOW_SPAN, BOW_BRACE)
    P.arrow_prop(g, x=0.40, y=0.10, length=1.02)
    return g


def build_rig(name="RIG_" + NAME):
    return V.Grid(NAME, team="联盟").build_rig(name)


def report():
    return build().audit()


if __name__ == "__main__":
    build().report()
