"""dl_shots.py —— 三套建筑 + 四件火的交付出图（与九座同一套机位 / 布光）

    blender -b --python blender/bs_v6/dl_shots.py

产物：docs/<资产>/v1/
  主图 / 正面 / 侧面 / 俯视 / RTS      （建筑）
  主图 / 俯视                          （火）
"""
import importlib
import os
import sys

import bpy

HERE = r"D:/测试一/blender/bs_v6"
ROOT = r"D:/测试一"
if HERE not in sys.path:
    sys.path.insert(0, HERE)
for m in ("bslib", "dl_kit", "dl_parts", "dg_layout", "dg_model", "uc_model",
          "tv_model", "fr_model", "shotlib"):
    if m in sys.modules:
        importlib.reload(sys.modules[m])
import dg_model  # noqa: E402
import uc_model  # noqa: E402
import tv_model  # noqa: E402
import fr_model  # noqa: E402
import shotlib as S  # noqa: E402

RES, SAMP = 1000, 48


def build(cn):
    if cn == "地牢":
        return dg_model.build(smooth=True)
    if cn == "地下城入口":
        return uc_model.build(smooth=True)
    if cn == "酒馆内部":
        return tv_model.build(smooth=True)
    return fr_model.build(cn, smooth=True)


RUN = ("地牢",)

for cn in ("地牢", "地下城入口", "酒馆内部"):
    if cn not in RUN:
        continue
    # 版本目录跟资产走：改版过的进 v2，没改过的还是 v1
    out = os.path.join(ROOT, "docs", cn, "v2" if cn == "地牢" else "v1")
    os.makedirs(out, exist_ok=True)
    S.OUTSHOT = out
    S.RES, S.SAMP = RES, SAMP
    S.clear_scene()
    objs, st = build(cn)
    print(cn, "STATS", st)
    lo, hi = S.bounds(objs)
    print(cn, "SIZE", [round(v, 2) for v in (hi - lo)])
    S.setup_world()
    S.ground_plane()
    S.shot("主图.png", objs, -34, 26, 1.06)
    S.shot("正面.png", objs, 0, 6, 1.05, res=int(RES * 0.92),
           samples=int(SAMP * 0.8))
    S.shot("侧面.png", objs, 90, 8, 1.05, res=int(RES * 0.92),
           samples=int(SAMP * 0.8))
    S.shot("俯视.png", objs, -34, 58, 1.05)
    S.shot("RTS.png", objs, -36, 42, 1.08)

for cn in ("营火", "火把", "火炬", "火堆"):
    out = os.path.join(ROOT, "docs", "火", "v1")
    os.makedirs(out, exist_ok=True)
    S.OUTSHOT = out
    S.RES, S.SAMP = 760, 40
    S.clear_scene()
    objs, st = build(cn)
    print(cn, "STATS", st)
    S.setup_world()
    S.ground_plane()
    S.shot("%s_主图.png" % cn, objs, -34, 24, 1.10, res=760, samples=40)

print("DL_SHOTS_DONE")
