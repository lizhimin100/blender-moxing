"""fr_quick.py —— 四件火载体快速看片（低模 + 细分各一张，420px）。"""
import importlib
import os
import sys

import bpy

HERE = r"D:/测试一/blender/bs_v6"
ROOT = r"D:/测试一"
if HERE not in sys.path:
    sys.path.insert(0, HERE)
for _m in ("bslib", "dl_kit", "fr_model"):
    if _m in sys.modules:
        importlib.reload(sys.modules[_m])
import fr_model  # noqa: E402
import shotlib as S  # noqa: E402

OUT = os.path.join(ROOT, "docs", "火", "v1")
os.makedirs(OUT, exist_ok=True)
S.OUTSHOT = OUT

for cn in ("营火", "火把", "火炬", "火堆"):
    for tag, smooth in (("low", False), ("smooth", True)):
        S.clear_scene()
        objs, st = fr_model.build(cn, smooth=smooth)
        lo, hi = S.bounds(objs)
        print(cn, tag, "STATS", st, "SIZE",
              [round(v, 2) for v in (hi - lo)])
        S.setup_world()
        S.ground_plane()
        S.shot("%s_%s.png" % (cn, tag), objs, -34, 24, 1.08, res=460, samples=20)
print("FIRE_QUICK_DONE")
