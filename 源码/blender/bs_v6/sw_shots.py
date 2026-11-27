"""sw_shots.py —— 蒸汽车坊 v3 交付出图（同一组机位、同一套布光；灯光随相机走）

    python build/bl_act.py act blender/bs_v6/sw_shots.py

产物：docs/蒸汽车坊/v3/
  主图 / 正面 / 侧面 / 背面 / 俯视 / RTS / 门庭近景 / 锅炉房近景 / 屋脊近景 /
  烟囱近景 / 低模对照

相机 / 布光 / 取景全部走 shotlib（九座共用一份），这里只留"拍哪几张"。
"""
import importlib
import os
import sys

import bpy

HERE = r"D:/测试一/blender/bs_v6"
ROOT = r"D:/测试一"
OUTSHOT = os.path.join(ROOT, "docs", "蒸汽车坊", "v3")
OUTBLEND = os.path.join(ROOT, "blend", "蒸汽车坊")
if HERE not in sys.path:
    sys.path.insert(0, HERE)
for _m in ("bslib", "br_model", "sw_model", "shotlib"):
    if _m in sys.modules:
        importlib.reload(sys.modules[_m])
import shotlib as S  # noqa: E402
import sw_model  # noqa: E402

RES = 1200
SAMP = 64


def main():
    os.makedirs(OUTSHOT, exist_ok=True)
    os.makedirs(OUTBLEND, exist_ok=True)
    S.OUTSHOT = OUTSHOT
    S.RES, S.SAMP = RES, SAMP

    S.clear_scene()
    objs, st = sw_model.build(smooth=True)
    print("STATS_SMOOTH", st)
    lo, hi = S.bounds(objs)
    print("BBOX_SMOOTH", [round(v, 2) for v in lo], [round(v, 2) for v in hi])
    print("SIZE_SMOOTH", [round(v, 2) for v in (hi - lo)])
    S.setup_world()
    S.ground_plane()
    hero = S.shot("主图.png", objs, -34, 26, 1.06)
    S.shot("正面.png", objs, 0, 6, 1.03)
    S.shot("侧面.png", objs, 90, 6, 1.04, res=int(RES * 0.92), samples=int(SAMP * 0.75))
    S.shot("背面.png", objs, 152, 26, 1.06, res=int(RES * 0.92), samples=int(SAMP * 0.75))
    S.shot("俯视.png", objs, -32, 58, 1.06)
    S.shot("RTS.png", objs, -36, 42, 1.08)
    S.pshot("门庭近景.png", (1.2, 12.2, 4.6), (0.2, 5.4, 2.6), lens=52,
            res=int(RES * 0.92), samples=int(SAMP * 0.85))
    S.pshot("锅炉房近景.png", (-9.6, 1.2, 4.8), (-5.1, -2.0, 2.4), lens=46,
            res=int(RES * 0.92), samples=int(SAMP * 0.85))
    S.pshot("屋脊近景.png", (-4.2, 13.0, 12.0), (0.0, 0.5, 8.4), lens=48,
            res=int(RES * 0.92), samples=int(SAMP * 0.85))
    S.pshot("烟囱近景.png", (-9.8, -10.2, 8.6), (-5.0, -5.2, 8.0), lens=55,
            res=int(RES * 0.92), samples=int(SAMP * 0.85))
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUTBLEND, "蒸汽车坊.blend"),
                                compress=True)

    S.clear_scene()
    objs_l, st_l = sw_model.build(smooth=False)
    print("STATS_LOW", st_l)
    S.setup_world()
    S.ground_plane()
    S.shot("低模对照.png", objs_l, -34, 26, 1.06, res=int(RES * 0.92),
           samples=int(SAMP * 0.5), fixed=hero)
    print("DONE")


main()
