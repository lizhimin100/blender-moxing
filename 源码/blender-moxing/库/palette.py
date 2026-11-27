"""palette.py —— 单位色板（与建筑同一套蓝金 + 野怪五区）。

纯数据，不依赖 bpy / PIL：Blender 侧和生产 PNG 的脚本共用这一份。
每个名字占图集一格（16×16 格、256²），UV 取格心。
"""

SIZE = 256
CELLS = 16
CELL = SIZE // CELLS

# (name, sRGB hex) —— 顺序即格号，**只在末尾追加**，不要插队
ENTRIES = [
    # 0–9 金属 / 皮革 / 布（联盟为主）
    ("steel",        "#949AA4"),
    ("steel_dark",   "#5E646D"),
    ("steel_light",  "#AEB3BB"),
    ("iron",         "#32353B"),
    ("gold",         "#D6A64A"),
    ("leather",      "#7B5A3A"),
    ("leather_dark", "#4A3624"),
    ("cloth",        "#6E6250"),
    ("cloth_dark",   "#4A4238"),
    ("skin",         "#D2A57F"),
    # 10–19 皮肤 / 木 / 深色
    ("skin_dark",    "#A97C58"),
    ("hair",         "#3B2A1E"),
    ("wood",         "#9B6236"),
    ("wood_dark",    "#3E2718"),
    ("dark",         "#1D1A17"),
    ("white",        "#E8E2D4"),
    ("stone",        "#9C968C"),
    ("stone_dark",   "#5C5852"),
    ("earth",        "#7B654C"),
    ("earth_dark",   "#55432F"),
    # 20–31 豺狼人毛 / 皮 / 骨
    ("fur_light",    "#B39A6E"),
    ("fur",          "#7A6850"),
    ("fur_dark",     "#4A3D2E"),
    ("fur_shadow",   "#332A20"),
    ("hide",         "#5A4028"),
    ("hide_dark",    "#3E2716"),
    ("bone",         "#E3D9C4"),
    ("bone_dark",    "#B8AC93"),
    ("iron_blue",    "#4C5058"),
    ("steel_cool",   "#6F7680"),
    ("tongue",       "#8E4A42"),
    ("eye_dark",     "#12100D"),
    # 32–39 预留：旗帜 / 阵营辅色 / 高光
    ("team_deep",    "#24488C"),
    ("team_pale",    "#4E7FD0"),
    ("gold_pale",    "#F1CD79"),
    ("gold_dark",    "#9C7428"),
    ("bone_pale",    "#F3ECDC"),
    ("fur_pale",     "#CDB78C"),
    ("ash",          "#8C8478"),
    ("rust",         "#8C4A32"),
]

INDEX = {name: i for i, (name, _) in enumerate(ENTRIES)}
COLOR = {name: h for name, h in ENTRIES}


def uv_of(name, inset=0.25):
    """格心 UV（inset 是格内的安全边距，单位=格）。"""
    i = INDEX[name]
    cx, cy = i % CELLS, i // CELLS
    u = (cx + 0.5) / CELLS
    v = 1.0 - (cy + 0.5) / CELLS
    return (u, v)
