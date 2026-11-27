"""st_atlas.py —— **状态档图集**（升级态 / 训练态 / 科研态 / 帐篷共用一套布局）

为什么另起一套布局，而不是往 `bs_atlas.ATLAS_ORDER` 末尾追加
------------------------------------------------------------
建筑图集 5×9 = 45 格已经用掉 43 格，只剩 2 格；状态档需要 6 个工地色
+ 生料石 / 生料木 + 两档帆布 = 10 格。往里加必须扩行（9 → 10 行），
扩行会把每一格的像素高度改一次 —— 按规则 N120，那要求**重生成图集与重导 GLB
成对执行**，也就是九座建筑的手游档、建造档、.blend 全部重出。为了七个状态件
动九座已交付资产的图集，风险完全不成比例。

所以状态档用**独立布局**：同样是 5×8 / 512² / 内缩 22，只是格子里的材质表不同。
旧图集一个字节都不用动，状态档自己一份 PNG，两套互相不知道对方存在。
图集材质名仍然是 `主体` / `team` / `team_trim` / `自发光` —— 引擎侧只有这四根线。
"""
import os

import bs_atlas
import bslib as L

# 5 列 × 8 行 = 40 格，用 37 格。**这张表的顺序 = 状态档的 UV 契约**，改顺序 = 改 UV。
STATE_ORDER = [
    # 建筑本体（九座用到的那一档明度秩序，子集）
    "stone_light", "stone_mid", "stone_dark", "roof", "roof_edge", "roof_pale",
    "roof_wood", "wood_warm", "wood_mid", "wood_dark", "iron", "gold",
    "paving", "earth", "earth_dark", "moss", "glass",
    # 自发光（炉火 / 火焰 / 晶体 / 门内灯）
    "ember", "flame_out", "flame_in", "glow", "crystal", "crystal_pale",
    # 阵营色（必须是独立材质，不进图集：换阵营只改这两个）
    "team", "team_trim",
    # 工地六色（cs_kit 建同名材质，这里只负责图集填色）
    "site_timber", "site_timber_dark", "site_rope", "site_stone",
    "site_iron", "site_cloth",
    # 生料截面（未完工的断口）+ 帐篷帆布两档
    "raw_stone", "raw_wood", "canvas", "canvas_dark",
    # 杂项
    "coal", "sand",
    # 门内灯（2.10 的自发光强度，比 glow 亮一档）。追加在末尾，前 37 格索引不动。
    "door_light",
    # 烟（铁匠铺炉口的烟团）。#8B8880 是唯一一档"冷灰"，用它才不像一块石头。
    "ash",
]

STATE_LAYOUT = bs_atlas.Layout(5, 8, 512, 22, STATE_ORDER, "状态档")

# 状态档的自发光基准强度。建筑图集用 1.8（火 / 窗光 / 水晶都够）；状态档多了
# "白天也看得见的门内灯"，1.8 在日光下读作浅色漆板，2.6 才读成"里面有灯"。
# 只在本模块生成图集 / 合材质时改这一个全局，建筑档的导出流程（export_mobile）
# 不经过这里，仍是 1.8。
EMIT_STRENGTH = 2.6


def _use_emit():
    bs_atlas.EMIT_STRENGTH = EMIT_STRENGTH

# 生料的映射：断口按"被切断的母材"选，石材 / 瓦 / 土一个色，木构一个色。
RAW_OF = {
    "stone_light": "raw_stone", "stone_mid": "raw_stone", "stone_dark": "raw_stone",
    "paving": "raw_stone", "earth": "raw_stone", "earth_dark": "raw_stone",
    "sand": "raw_stone", "roof": "raw_stone", "roof_edge": "raw_stone",
    "roof_pale": "raw_stone", "roof_wood": "raw_wood", "moss": "raw_stone",
    "wood_warm": "raw_wood", "wood_mid": "raw_wood", "wood_dark": "raw_wood",
    "iron": "raw_stone", "gold": "raw_stone", "site_timber": "raw_wood",
    "site_timber_dark": "raw_wood", "site_stone": "raw_stone",
}


def raw_mat(name):
    return RAW_OF.get(name, "raw_stone")


def build_images(out_dir, label, include_emit=True, size=512):
    """生成状态档图集（基础色 / ORM / 自发光）。返回 {tag: Image}。"""
    os.makedirs(out_dir, exist_ok=True)
    _use_emit()
    return bs_atlas.build_images(out_dir, size=size, label=label,
                                 layout=STATE_LAYOUT, include_emit=include_emit)


def missing(objs):
    """检查有没有材质不在 STATE_ORDER 里（pin_uv 会直接抛 KeyError，提前报更清楚）。"""
    out = set()
    for ob in objs:
        for m in ob.data.materials:
            if m and m.name not in STATE_LAYOUT.order:
                out.add(m.name)
    return sorted(out)


def pin_uv(objs):
    return bs_atlas.pin_uv(objs, layout=STATE_LAYOUT)


def pack(objs, imgs, prefix):
    _use_emit()
    return bs_atlas.pack(objs, imgs, prefix=prefix)
