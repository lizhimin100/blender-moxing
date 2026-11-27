"""parts_export.py —— 导出「跨建筑可复用零件」的独立 GLB

为什么只拆这一类：一座建筑拆成「台基 / 墙 / 门 / 后场」交付出去，在引擎里没有落点
（没人会往场景里拖一块「石壳」）；真正会被反复用的是**门、桶、箱、旗、柱、火盆**
这种尺度确定、位置自由的小件。所以这里只出这一层。

零件全部由 `dl_kit` / `dl_parts` 的函数按**标准尺寸**生成 —— 与建筑里用的是同一份代码，
不是从成品里抠出来的，所以比例、材质、倒角口径天然一致。

产物：`assets/建筑/零件/<名>.glb`（单位米，原点在占地中心，地面 z = 0）
材质：用桌面档的调色板材质（没打图集）。零件是给建模期复用和摆场用的，
      单件只有 2–6 个材质，不值得为它单独开一张图集。

用法：python build/bl_act.py act blender/bs_v6/parts_export.py
"""

import json
import os
import sys

import bpy

HERE = r"D:/测试一/blender/bs_v6"
ROOT = r"D:/测试一"
OUT = os.path.join(ROOT, "assets", "建筑", "零件")

if HERE not in sys.path:
    sys.path.insert(0, HERE)
import bslib as L      # noqa: E402
import dl_kit as K     # noqa: E402
import dl_parts as P   # noqa: E402

M = L.all_materials()
P.apply_team_style(P.LE_TEAM_STYLE)


def clear():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)


def flat(obs):
    """摊平返回值：dl_kit 里 banner 返回三元组，其余返回 list。"""
    out = []
    for it in obs:
        if isinstance(it, (list, tuple)):
            out.extend(flat(it))
        elif it is not None:
            out.append(it)
    return out


# ── 零件表：名字 → (构造, 倒角, 是否强制硬面) ───────────────────────────────
# 倒角给 3–8 mm：零件在近景里，太大会把 3 cm 的细节磨没，太小等于没有。
def _door():
    """双扇石门，**铰链在中间的门缝上**（与建筑里一致：hinge_x 是缝的位置，
    side 决定往哪边展开）。第一版把铰链放在 ±0.78 让两扇往外开，中间留了
    1.56 m 的洞 —— 那不是门，是两堵墙。"""
    parts = []
    w, h, t = 1.52, 2.06, 0.24
    for sgn in (1, -1):
        parts += P.door_leaf("pt_leaf%d" % (sgn > 0), 0.0, 0.0, 0.0, w, h, t,
                             sgn, 0.0, M, bands=2, studs=(0, 0),
                             panel=0.20, ring=(sgn < 0))
    parts += P.lock_bar("pt_bar", -1.42, 1.42, t * 0.5 + 0.055, 1.36, 0.075, M,
                        w=0.072)
    return parts


PARTS = (
    ("双扇石门", _door, 0.008, True),
    ("木桶", lambda: K.barrel("pt_barrel", 0.0, 0.0, 0.0), 0.006, False),
    ("木箱", lambda: K.crate("pt_crate", 0.0, 0.0, 0.0), 0.005, True),
    ("旗帜", lambda: K.banner("pt_banner", 0.0, 0.0, 2.10, 0.84, 1.30,
                             M["team"], M["team_trim"], M["wood_dark"]), 0.005, False),
    ("吊链", lambda: K.chain("pt_chain", 0.0, 0.0, 1.80, 0.0, 0.11,
                            M["iron"], links=7), 0.003, True),
    ("铁栅", lambda: K.grate("pt_grate", 0.0, 0.0, 0.02, 1.10, 0.80), 0.004, True),
    ("陶罐", lambda: K.pot("pt_pot", 0.0, 0.0, 0.0), 0.005, False),
    ("原木", lambda: K.log("pt_log", (-0.85, 0.0, 0.22), (0.85, 0.0, 0.22),
                          0.22, M["wood_dark"], M["wood_warm"]), 0.005, False),
    ("断柱", lambda: P.column_ruin("pt_col", 0.0, 0.0, 0.0, 2.30, 0.46, M,
                                  courses=4, seed=7), 0.008, True),
    ("火盆", lambda: P.brazier_tipped("pt_braz", 0.0, 0.0, 0.0, M, ang=0.6,
                                     mat_bowl="ancient", mat_rim="bronze"), 0.006, False),
    ("骨堆", lambda: P.bone_stack("pt_bone", 0.0, 0.0, 0.0, M, n=4, seed=19,
                                 r=0.046), 0.004, False),
    ("垂根", lambda: P.root_strands("pt_root", 0.0, 0.0, 2.20, M, n=3, seed=29,
                                   length=0.52), 0.003, False),
    ("地面铁栅", lambda: P.ground_grate("pt_ggrate", 0.0, 0.0, 0.0, M), 0.004, True),
)


def main():
    os.makedirs(OUT, exist_ok=True)
    receipt = {}
    for name, maker, bev, hard in PARTS:
        clear()
        obs = flat(maker())
        if not obs:
            print("  ! 空：", name)
            continue
        for ob in obs:
            L.finalize(ob, bevel=bev, seg=1, sub=0, flat=hard)
        for ob in bpy.data.objects:
            ob.select_set(True)
        bpy.context.view_layer.objects.active = obs[0]
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        for ob in bpy.data.objects:
            ob.select_set(False)
        objs = L.join_by_material(obs, prefix="PT")
        st = L.stats(objs)
        path = os.path.join(OUT, name + ".glb")
        for ob in bpy.data.objects:
            ob.select_set(ob in objs)
        bpy.context.view_layer.objects.active = objs[0]
        bpy.ops.export_scene.gltf(
            filepath=path, export_format="GLB", use_selection=True,
            export_apply=True, export_yup=True, export_materials="EXPORT",
            export_animations=False, export_skins=False,
        )
        receipt[name] = {"tris": st["tris"], "materials": st["materials"],
                         "bytes": os.path.getsize(path)}
        print("[part] %-8s %5d tri  %d 材质  %6d B" % (
            name, st["tris"], st["materials"], os.path.getsize(path)))
    print("PARTS_RECEIPT " + json.dumps(receipt, ensure_ascii=False))


main()
