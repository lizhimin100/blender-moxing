"""dg_quick.py —— 只出四张评审图（不进 dl_shots 的交付流程），跑在桥接里。"""
import importlib
import os
import sys

import bpy

HERE = r"D:/测试一/blender/bs_v6"
ROOT = r"D:/测试一"
if HERE not in sys.path:
    sys.path.insert(0, HERE)
for m in ("bslib", "br_model", "wt_model", "dl_kit", "dl_parts", "dg_layout",
          "dg_model", "shotlib"):
    if m in sys.modules:
        importlib.reload(sys.modules[m])

import dg_model  # noqa: E402
import shotlib as S  # noqa: E402

OUT = os.path.join(ROOT, "docs", "地牢", "v2")
os.makedirs(OUT, exist_ok=True)
S.OUTSHOT = OUT
S.RES, S.SAMP = 900, 32
S.clear_scene()
objs, st = dg_model.build(smooth=True, unwrap=False)
print("STATS", st)
lo, hi = S.bounds(objs)
print("SIZE", [round(v, 2) for v in (hi - lo)])
S.setup_world()
S.ground_plane()
S.shot("主图.png", objs, -34, 26, 1.06)
S.shot("俯视.png", objs, -34, 58, 1.05)
S.shot("RTS.png", objs, -36, 42, 1.08)
S.shot("正面.png", objs, 0, 6, 1.05, res=820, samples=26)
S.pshot("近景_门.png", (3.35, 5.55, 3.05), (0.10, -0.55, 1.72), lens=42, res=900,
        samples=32)
S.pshot("近景_台阶.png", (-3.05, 5.55, 3.15), (-0.35, 1.35, 0.75), lens=58,
        res=900, samples=32)
print("DG_QUICK_DONE")
