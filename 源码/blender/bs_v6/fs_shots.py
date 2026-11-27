"""fs_shots.py —— 折壳入口的交付出图（与九座 / 失落帝国同一套机位与布光）

    python build/bl_act.py act blender/bs_v6/fs_shots.py

产物：docs/折壳入口/v1/
  主图 / 正面 / 侧面 / 俯视 / RTS / 近景_抓痕 / 洞内
"""
import importlib
import os
import sys

import bpy
from mathutils import Vector

HERE = r"D:/测试一/blender/bs_v6"
ROOT = r"D:/测试一"
if HERE not in sys.path:
    sys.path.insert(0, HERE)
for m in ("bslib", "dl_kit", "br_model", "wt_model", "fs_model", "shotlib"):
    if m in sys.modules:
        importlib.reload(sys.modules[m])
import fs_model  # noqa: E402
import shotlib as S  # noqa: E402

RES, SAMP = 1000, 48
out = os.path.join(ROOT, "docs", "折壳入口", "v2")
os.makedirs(out, exist_ok=True)
S.OUTSHOT = out
S.RES, S.SAMP = RES, SAMP

S.clear_scene()
objs, st = fs_model.build(smooth=True)
print("STATS", st)
lo, hi = S.bounds(objs)
print("SIZE", [round(v, 2) for v in (hi - lo)])
S.setup_world()
S.ground_plane()

S.shot("主图.png", objs, -34, 26, 1.06)
S.shot("正面.png", objs, 0, 6, 1.06, res=int(RES * 0.92), samples=int(SAMP * 0.8))
S.shot("侧面.png", objs, 90, 8, 1.06, res=int(RES * 0.92), samples=int(SAMP * 0.8))
S.shot("俯视.png", objs, -34, 58, 1.05)
S.shot("RTS.png", objs, -36, 42, 1.08)
S.shot("背面.png", objs, 208, 24, 1.06, res=int(RES * 0.92), samples=int(SAMP * 0.8))
# 近景：门套 / 门扇 / 断链（短视频用的 0.5–2 m 机位）
S.shot("近景_门.png", objs, -30, 10, 1.0,
       fixed=(Vector((1.05, 1.20, 1.85)), 4.40), res=int(RES * 0.86), samples=SAMP)
# 洞内：从隧道里往外看（"走进去消失"那一镜）
S.pshot("隧道.png", (1.35, 5.60, 2.35), (-0.10, 0.70, 1.35), lens=21,
        res=int(RES * 0.86), samples=SAMP)

print("FS_SHOTS_DONE")
