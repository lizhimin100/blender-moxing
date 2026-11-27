"""dl_quick.py —— 新资产快速看片：低模 + 细分各一张，480px / 16spp。

    echo dg_model > blender/bs_v6/_target.txt
    python build/bl_act.py act blender/bs_v6/dl_quick.py

产物 docs/<中文名>/v1/quick_low.png · quick_smooth.png
不写 .blend、不导出、不碰 assets —— 只用来在建模阶段看形体。
"""
import importlib
import os
import sys

import bpy

HERE = r"D:/测试一/blender/bs_v6"
ROOT = r"D:/测试一"
if HERE not in sys.path:
    sys.path.insert(0, HERE)

with open(os.path.join(HERE, "_target.txt"), encoding="utf-8") as f:
    TARGET = f.read().strip()

for _m in ("bslib", "br_model", "wt_model", "dl_kit", TARGET):
    if _m in sys.modules:
        importlib.reload(sys.modules[_m])

mod = importlib.import_module(TARGET)
import shotlib as S  # noqa: E402

CN = {"dg_model": "地牢", "uc_model": "地下城入口", "tv_model": "酒馆内部",
      "fr_model": "火"}[TARGET]
OUT = os.path.join(ROOT, "docs", CN, "v1")
os.makedirs(OUT, exist_ok=True)
S.OUTSHOT = OUT


def run(name, smooth, res=520, samp=24):
    S.clear_scene()
    objs, st = mod.build(smooth=smooth)
    print(name, "STATS", st)
    lo, hi = S.bounds(objs)
    print(name, "BBOX", [round(v, 2) for v in lo], [round(v, 2) for v in hi],
          "SIZE", [round(v, 2) for v in (hi - lo)])
    S.setup_world()
    S.ground_plane()
    S.shot("quick_%s.png" % name, objs, -34, 28, 1.04, res=res, samples=samp)
    S.shot("quick_%s_top.png" % name, objs, -34, 58, 1.04, res=res, samples=samp)
    return objs


run("low", False)
run("smooth", True)
print("QUICK_DONE")
