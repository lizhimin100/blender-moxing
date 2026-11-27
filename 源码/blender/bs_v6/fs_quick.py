"""fs_quick.py —— 折壳入口的快速看片（改一版 → 出一版，别拿 48 采样等）"""
import importlib
import os
import sys

import bpy

HERE = r"D:/测试一/blender/bs_v6"
ROOT = r"D:/测试一"
if HERE not in sys.path:
    sys.path.insert(0, HERE)
for m in ("bslib", "dl_kit", "br_model", "wt_model", "fs_model", "shotlib"):
    if m in sys.modules:
        importlib.reload(sys.modules[m])
import fs_model  # noqa: E402
import shotlib as S  # noqa: E402

SHOTS = os.environ.get("FS_SHOTS", "main,front,top,rts,back")
S.OUTSHOT = os.path.join(ROOT, "docs", "折壳入口", "v2")
os.makedirs(S.OUTSHOT, exist_ok=True)
S.RES, S.SAMP = 760, 28

S.clear_scene()
objs, st = fs_model.build(smooth=True)
print("STATS", st)
lo, hi = S.bounds(objs)
print("SIZE", [round(v, 2) for v in (hi - lo)], "MIN", [round(v, 2) for v in lo])
S.setup_world()
S.ground_plane()
for tag in SHOTS.split(","):
    tag = tag.strip()
    if tag == "main":
        S.shot("q_main.png", objs, -34, 26, 1.06)
    elif tag == "front":
        S.shot("q_front.png", objs, 0, 6, 1.05)
    elif tag == "side":
        S.shot("q_side.png", objs, 90, 8, 1.05)
    elif tag == "top":
        S.shot("q_top.png", objs, -34, 58, 1.05)
    elif tag == "rts":
        S.shot("q_rts.png", objs, -36, 42, 1.08)
    elif tag == "back":
        S.shot("q_back.png", objs, 208, 24, 1.06)
    elif tag == "close":
        S.shot("q_close.png", objs, -14, 2, 1.0,
               fixed=(__import__("mathutils").Vector((-4.55, 0.40, 2.05)), 2.70), res=760, samples=28)
print("QUICK_DONE")
