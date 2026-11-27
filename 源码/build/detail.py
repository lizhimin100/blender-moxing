"""
detail.py —— 细节档位开关（v5.1）

为什么要一个开关而不是两套模型：
  同一套参数化描述同时产出"低模"与"细模"，剪影、比例、染色位完全一致，
  以后要做细分/烘焙也只需在低模上做，不会出现两份对不上的资产。

  LOWPOLY=1 时：
    · 圆截面降到 6 边（桶、磨石、原木端面、筒仓）
    · 不生成椽、不生成瓦皮（屋面 = 一整块薄壳 + 脊）
    · 屋面网格 2×2（不再按 1.1 m 切格）
    · 丢弃最大尺寸 < 0.30 m 的装饰件（保留阵营色 / 自发光 / 职责构件）

目标：每座 ≤ 4 000 三角面，剪影与细模一致。
"""
import os

LOW = os.environ.get("LOWPOLY", "") == "1"

# 低于这个尺寸的构件在低模里直接不生成（阵营色与发光件除外）
MIN_PART = 0.55
KEEP_MATS = {"cloth_team", "emblem", "ember", "window", "gold"}
KEEP_ROLES = {"duty", "roof", "cap", "gate"}


def sides(n):
    """圆截面的边数：低模一律 6 边。"""
    return 6 if LOW else n


def keep(part):
    """低模的构件筛选。结构件一律保留，碎装饰按尺寸裁。"""
    if not LOW:
        return True
    if part.get("role") in KEEP_ROLES:
        return True
    if part["mat"] in KEEP_MATS:
        return True
    return max(part["box"][3:]) >= MIN_PART
