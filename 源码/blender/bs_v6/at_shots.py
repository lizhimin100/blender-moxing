"""at_shots.py —— 箭塔 v2 交付出图（与其余九座同一组机位、同一套布光）

    python build/bl_act.py act blender/bs_v6/at_shots.py

产物：docs/箭塔/v2/
  主图 / 正面 / 侧面 / 背面 / 俯视 / RTS / 门近景 / 亭内近景 / 箭顶近景 / 低模对照
"""
import importlib
import os
import sys

import bpy

HERE = r"D:/测试一/blender/bs_v6"
ROOT = r"D:/测试一"
OUTSHOT = os.path.join(ROOT, "docs", "箭塔", "v2")
OUTBLEND = os.path.join(ROOT, "blend", "箭塔")
if HERE not in sys.path:
    sys.path.insert(0, HERE)
for _m in ("bslib", "br_model", "wt_model", "at_model", "shotlib"):
    if _m in sys.modules:
        importlib.reload(sys.modules[_m])
import at_model  # noqa: E402
import shotlib as S  # noqa: E402

RES = 1200
SAMP = 64


def main():
    os.makedirs(OUTSHOT, exist_ok=True)
    os.makedirs(OUTBLEND, exist_ok=True)
    S.OUTSHOT = OUTSHOT
    S.RES, S.SAMP = RES, SAMP

    S.clear_scene()
    objs, st = at_model.build(smooth=True)
    print("STATS_SMOOTH", st)
    lo, hi = S.bounds(objs)
    print("BBOX_SMOOTH", [round(v, 2) for v in lo], [round(v, 2) for v in hi])
    print("SIZE_SMOOTH", [round(v, 2) for v in (hi - lo)])
    S.setup_world()
    S.ground_plane()
    hero = S.shot("主图.png", objs, -34, 26, 1.06)
    S.shot("正面.png", objs, 0, 6, 1.04)
    S.shot("侧面.png", objs, 90, 6, 1.04, res=int(RES * 0.92), samples=int(SAMP * 0.75))
    S.shot("背面.png", objs, 152, 26, 1.06, res=int(RES * 0.92), samples=int(SAMP * 0.75))
    S.shot("俯视.png", objs, -32, 58, 1.06)
    S.shot("RTS.png", objs, -36, 42, 1.08)
    S.pshot("门近景.png", (-4.0, 9.4, 3.2), (0.0, 2.2, 1.9), lens=58,
            res=int(RES * 0.92), samples=int(SAMP * 0.85))
    S.pshot("亭内近景.png", (-7.2, 8.4, 12.0), (0.2, 0.2, 10.5), lens=54,
            res=int(RES * 0.92), samples=int(SAMP * 0.85))
    S.pshot("箭顶近景.png", (-4.2, 5.6, 16.6), (0.0, 0.0, 15.4), lens=62,
            res=int(RES * 0.92), samples=int(SAMP * 0.85))
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUTBLEND, "箭塔.blend"),
                                compress=True)

    S.clear_scene()
    objs_l, st_l = at_model.build(smooth=False)
    print("STATS_LOW", st_l)
    S.setup_world()
    S.ground_plane()
    S.shot("低模对照.png", objs_l, -34, 26, 1.06, res=int(RES * 0.92),
           samples=int(SAMP * 0.5), fixed=hero)
    print("DONE")


main()
