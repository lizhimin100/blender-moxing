"""
ch_atlas.py —— 第十座（角色）的图集与 LOD 层

**与建筑同一条管线，只改行列**：
    建筑  5 列 × 6 行 / 512² / 内缩 22 / bs_atlas.ATLAS_ORDER
    角色  4 列 × 4 行 / 512² / 内缩 22 / 本文件的 CH_ORDER

为什么不复用 ATLAS_ORDER：角色要多一个 skin、一个 cloth、两档钢，
为了这四格去重出九座建筑的图集不划算（建筑的 UV 是按 ATLAS_ORDER 的下标钉死的）。
`Layout` 这层是 bs_atlas 里新抽出来的，建筑侧的默认值一个字节都没动。

材质（14 格，剩 2 格空）：
    steel / steel_dark   甲片亮面 / 暗面（新起的一档中灰钢，见 bslib 注释）
    iron / gold          关节铆钉 / 金属件
    skin / cloth         要求新增的两色（#D2A57F / #6E6250）
    cloth_dark           关节缝里的衬
    earth / earth_dark   束带 / 靴（借建筑的）
    wood_dark / wood_warm 剑柄、盾背 / 盾背板（借建筑的）
    dark                 眼缝、嘴、窗洞内壁
    team / team_trim     阵营主色 / 辅色（各自独立材质，换色只改这两个）
"""
import os

import bpy

import bs_atlas as A
import bslib as L

CH_ORDER = [
    "steel", "steel_dark", "iron", "gold",
    "skin", "cloth", "cloth_dark", "earth",
    "earth_dark", "wood_dark", "wood_warm", "dark",
    # team / team_trim 也占两格：`bs_atlas.pin_uv` 要求每个对象都能在布局里
    # 找到格心（建筑那套也是这么做的）。它们最后会被纯色材质替换，UV 用不到。
    "team", "team_trim",
]

CH_LAYOUT = A.Layout(4, 4, 512, 22, CH_ORDER, "角色")
CH_TAG = "主体"


def build_images(out_dir, label="剑士"):
    """4×4 / 512² 基础色 + ORM。角色没有自发光件，不出那张全黑的图。"""
    return A.build_images(out_dir, label=label, layout=CH_LAYOUT, include_emit=False)


def pin_uv(objs):
    A.pin_uv(objs, layout=CH_LAYOUT)


def pack(objs, imgs, prefix="CH"):
    return A.pack(objs, imgs, prefix=prefix)


# ── 角色尺度的 LOD ───────────────────────────────────────────────────────────
# 建筑的体积阈值（0.012 / 0.22 m³）放到角色上会把整条胳膊筛掉 ——
# 一条上臂只有 0.16×0.17×0.27 ≈ 0.007 m³。角色要按角色自己的尺度切。
LOD1_VOL = 0.00035      # 中景：铆钉 / 盾钉 / 通风孔 / 眼睛这一档先走
LOD2_VOL = 0.0035       # 远景：只留"读得出体量"的块

# 远景白名单：整组保留（这几件是识别度本身，按体积筛会散架）
LOD2_KEEP = ("hm_shell", "hm_dome", "hm_crest", "hm_face", "hm_brow",
             "bd_chest", "bd_pelvis", "bd_belt", "bd_plackart",
             "pd_shell", "pd_trim", "pd_lame",
             "lg_thigh", "lg_shin", "lg_boot", "lg_sole", "lg_poleyn",
             "ar_upper", "ar_fore", "ar_hand",
             "sh_face", "sh_rim", "sh_boss",
             "sw_blade", "sw_guard", "sw_grip",
             "jt_neck")
# 远景专属剔除（这些件在 20 px 高的角色上只是噪点）
LOD2_DROP = ("hm_eye", "hm_mouth", "hm_breath", "hm_ear", "bd_rivet",
             "sh_stud", "sh_line", "sh_bosering", "sh_plank", "sh_strap",
             "sh_grip", "sw_wrap", "sw_quillon", "lg_strapk", "bd_buckleg",
             "ts_", "ar_knuck", "ar_couter", "hm_nasal")


def _vol(ob):
    co = ob.data.vertices
    if not len(co):
        return 0.0
    d = [max(v.co[i] for v in co) - min(v.co[i] for v in co) for i in range(3)]
    return d[0] * d[1] * d[2]


def filter_lod(items, level):
    """0 = 全量；1 = 中景；2 = 远景。

    判据用**包围盒体积**（与建筑同一口径），但阈值按角色重算：
    角色最厚的块（胸甲）才 0.06 m³，建筑的门板都不止。
    """
    if level == 0:
        return list(items)
    thr = LOD1_VOL if level == 1 else LOD2_VOL
    keep, drop = [], []
    for it in items:
        ob = it[0]
        n = ob.name
        if level >= 2 and n.startswith(LOD2_DROP):
            drop.append(it)
            continue
        if _vol(ob) >= thr or n.startswith(LOD2_KEEP if level >= 2 else ()):
            keep.append(it)
        else:
            drop.append(it)
    # 被筛掉的必须从场景里删掉：只"不 join"的话它们会留在场景里
    # （建筑那边踩过一次，留下一片没走 mirror 的镜像件）
    for it in drop:
        try:
            bpy.data.objects.remove(it[0], do_unlink=True)
        except Exception:
            pass
    return keep


def stats(items):
    tris = 0
    for it in items:
        it[0].data.calc_loop_triangles()
        tris += len(it[0].data.loop_triangles)
    return {"parts": len(items), "tris": tris}
