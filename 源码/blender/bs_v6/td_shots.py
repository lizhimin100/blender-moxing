"""td_shots.py —— 地形地块出图（复用 shotlib 的机位与布光，和建筑图直接可比）

    blender.exe -b --factory-startup --python blender/bs_v6/td_shots.py

四张：
    地块_主图.png      3/4 机位（az -34 / el 26）
    地块_俯视.png      俯视（el 89，RTS 视角）
    地块_平铺.png      2×2 拼合（验证接缝）
    地块_低模对照.png  同一机位的低模版（对照"低模 → 细分"）
"""
import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import shotlib as S
import td_model as M

OUT = "D:/测试一/docs/地形/地块"
RES, SAMP = 1200, 64


def main():
    os.makedirs(OUT, exist_ok=True)
    S.OUTSHOT = OUT

    S.clear_scene()
    S.setup_world()
    objs, st = M.build(smooth=True)
    print("[TD]", st)
    S.shot("地块_主图.png", objs, -34, 26, margin=1.10, res=RES, samples=SAMP)
    S.shot("地块_俯视.png", objs, 0, 89, margin=1.06, res=RES, samples=SAMP)

    # 2×2 拼合：把整块复制三份平移，看接缝处的板形/沟槽是否接得上
    for ox, oy in ((M.W, 0.0), (0.0, M.W), (M.W, M.W)):
        for ob in list(objs):
            dup = ob.copy()
            dup.data = ob.data
            bpy.context.scene.collection.objects.link(dup)
            dup.location.x += ox
            dup.location.y += oy
            objs.append(dup)
    S.shot("地块_平铺.png", objs, -34, 38, margin=1.02, res=RES, samples=SAMP)

    # 低模对照
    S.clear_scene()
    S.setup_world()
    objs2, _ = M.build(smooth=False)
    S.shot("地块_低模对照.png", objs2, -34, 26, margin=1.10, res=RES, samples=SAMP)
    print("[TD DONE]")


main()
