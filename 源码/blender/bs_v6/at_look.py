"""at_look.py —— 箭塔快速看片（迭代用，写 docs/箭塔/_look）

    python build/bl_act.py act blender/bs_v6/at_look.py
"""
import importlib
import os
import sys

import bpy

HERE = r"D:/测试一/blender/bs_v6"
ROOT = r"D:/测试一"
if HERE not in sys.path:
    sys.path.insert(0, HERE)
for _m in ("bslib", "br_model", "wt_model", "at_model", "shotlib"):
    if _m in sys.modules:
        importlib.reload(sys.modules[_m])
import at_model  # noqa: E402
import shotlib as S  # noqa: E402

S.OUTSHOT = os.path.join(ROOT, "docs", "箭塔", "_look")
S.RES, S.SAMP = 860, 24


def main():
    os.makedirs(S.OUTSHOT, exist_ok=True)
    S.clear_scene()
    objs, st = at_model.build(smooth=True)
    print("STATS", st)
    lo, hi = S.bounds(objs)
    print("BBOX", [round(v, 2) for v in lo], [round(v, 2) for v in hi])
    S.setup_world()
    S.ground_plane()
    S.shot("_主图.png", objs, -34, 26, 1.06)
    S.shot("_正面.png", objs, 0, 6, 1.04)
    S.shot("_俯视.png", objs, -32, 58, 1.06)
    S.shot("_RTS.png", objs, -36, 42, 1.08)
    S.pshot("_平台.png", (-8.6, 9.8, 15.2), (0.0, 0.4, 12.2), lens=52)
    S.pshot("_门.png", (-4.0, 9.6, 3.4), (0.0, 2.2, 2.2), lens=58)
    print("LOOK_DONE")


main()
