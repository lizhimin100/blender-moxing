"""dl_cs.py —— 三套新建筑的建造动画（v2 世界 Z 显影 + 工地套件）

    blender -b --python blender/bs_v6/dl_cs.py

只做地牢 / 地下城入口 / 酒馆内部；四件火是道具，不带建造动画。
首跑自动量体并写 docs/建造系统/契约/<建筑>.json，之后可手改。
"""
import importlib
import json
import os
import sys

import bpy

HERE = r"D:/测试一/blender/bs_v6"
ROOT = r"D:/测试一"
if HERE not in sys.path:
    sys.path.insert(0, HERE)
for m in ("bslib", "br_model", "wt_model", "dl_kit", "cs_kit", "cs_rig", "cs_check",
          "cs_build"):
    if m in sys.modules:
        importlib.reload(sys.modules[m])
import cs_build  # noqa: E402

RUN = ("地牢",)

out = {}
for cn in RUN:
    out[cn] = cs_build.build_one(cn, detail="low")
print("DL_CS_RECEIPT " + json.dumps(
    {k: {"file": v.get("file"), "bytes": v.get("bytes"), "reveal": v.get("reveal"),
         "check": v.get("check")} for k, v in out.items()}, ensure_ascii=False))
