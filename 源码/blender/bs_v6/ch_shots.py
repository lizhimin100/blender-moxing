"""ch_shots.py —— 块面剑士交付出图（与九座建筑同一套 shotlib）

    python build/bl_act.py act blender/bs_v6/ch_shots.py

机位是**固定常量**，不为某一张图单独调 —— 一套图里出现两个视角就是不合格。
出图用**手游近档**（图集 + 三个材质），这样图上看到的颜色就是引擎里看到的颜色。
"""
import importlib
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = r"D:/测试一/blender/bs_v6"
ROOT = r"D:/测试一"
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from assets_path import asset_path  # noqa: E402

OUT = os.path.join(ROOT, "docs", "剑士", "v1")
if HERE not in sys.path:
    sys.path.insert(0, HERE)
for mod in ("bslib", "bs_atlas", "ch_atlas", "ch_model", "shotlib"):
    if mod in sys.modules:
        importlib.reload(sys.modules[mod])
import ch_atlas  # noqa: E402
import ch_model  # noqa: E402
import shotlib as S  # noqa: E402

S.OUTSHOT = OUT
S.RES, S.SAMP = 1200, 64
ATLAS = asset_path("剑士", "图集")

CTR = Vector((0.0, 0.02, 1.29))
SPAN = 2.85


def clear_scene():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for blk in (bpy.data.meshes, bpy.data.materials, bpy.data.images,
                bpy.data.cameras, bpy.data.lights, bpy.data.armatures):
        for it in list(blk):
            try:
                blk.remove(it)
            except Exception:
                pass


def atlas_model(level=0, bevel=True):
    imgs = {}
    for tag, fn in (("主体", "主体.png"), ("ORM", "ORM.png")):
        img = bpy.data.images.load(os.path.join(ATLAS, fn), check_existing=False)
        img.colorspace_settings.name = "sRGB" if tag != "ORM" else "Non-Color"
        imgs[tag] = img
    m = ch_model.Model(False, level).build()
    m.items = ch_atlas.filter_lod(m.items, level)
    objs = m.finalize(bevel=bevel, rig=False)
    ch_atlas.pin_uv(objs)
    objs = ch_atlas.pack(objs, imgs, prefix="CH")
    ch_model.build_armature(objs)
    return objs


def main():
    os.makedirs(OUT, exist_ok=True)
    clear_scene()
    objs = atlas_model(0, True)
    S.setup_world()
    S.ground_plane()
    fixed = (CTR, SPAN)
    S.shot("主图.png", objs, -32, 20, fixed=fixed)
    S.shot("正面.png", objs, 0, 4, fixed=fixed)
    S.shot("侧面.png", objs, 90, 4, fixed=fixed)
    S.shot("背面.png", objs, 180, 6, fixed=fixed)
    S.shot("俯视.png", objs, -32, 56, fixed=fixed)
    S.shot("RTS.png", objs, -38, 46, fixed=fixed)
    S.shot("头近景.png", objs, -26, 12, fixed=(Vector((0, 0.02, 2.10)), 0.86))
    S.shot("盾近景.png", objs, -44, 10, fixed=(Vector((-0.36, 0.10, 1.22)), 0.95))
    S.shot("剑近景.png", objs, 28, 8, fixed=(Vector((0.40, 0.14, 0.86)), 0.90))

    # 低模对照（同一机位、同一取景，只换几何）
    clear_scene()
    objs2 = atlas_model(2, False)
    S.setup_world()
    S.ground_plane()
    S.shot("低模对照.png", objs2, -32, 20, fixed=fixed)
    print("DONE")


main()
