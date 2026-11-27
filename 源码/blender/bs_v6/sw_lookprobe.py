"""sw_lookprobe.py —— 车坊单点复核（改哪看哪）：主图 / 门庭 / 门正

    python build/bl_act.py act blender/bs_v6/sw_lookprobe.py

写进 docs/蒸汽车坊/_look/，不进正式交付目录。
"""
import importlib
import os
import sys

HERE = r"D:/测试一/blender/bs_v6"
ROOT = r"D:/测试一"
if HERE not in sys.path:
    sys.path.insert(0, HERE)
for _m in ("bslib", "br_model", "sw_model", "shotlib"):
    if _m in sys.modules:
        importlib.reload(sys.modules[_m])
import shotlib as S  # noqa: E402
import sw_model  # noqa: E402

S.OUTSHOT = os.path.join(ROOT, "docs", "蒸汽车坊", "_look")
S.RES = 900
S.SAMP = 40


def main():
    os.makedirs(S.OUTSHOT, exist_ok=True)
    S.clear_scene()
    objs, st = sw_model.build(smooth=True)
    print("STATS", st)
    S.setup_world()
    S.ground_plane()
    S.shot("_主图.png", objs, -34, 26, 1.06)
    S.pshot("_门庭.png", (1.2, 12.2, 4.6), (0.2, 5.4, 2.6), lens=52)
    S.pshot("_门正.png", (0.0, 10.4, 3.4), (0.0, 5.35, 2.35), lens=58)
    print("LOOK_DONE")


main()
