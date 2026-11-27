"""cs_one.py —— 单座重跑（桥接用）。

    python build/bl_act.py act blender/bs_v6/cs_one.py 箭塔
"""
import importlib
import sys

sys.path.insert(0, "D:/测试一/blender/bs_v6")
import cs_build
importlib.reload(cs_build)

import bpy  # noqa: E402

CN = "箭塔"
try:
    CN = [a for a in sys.argv if a in
          ("铁匠铺", "兵营", "城镇大厅", "哨塔", "农场", "伐木场", "神秘圣地",
           "蒸汽车坊", "箭塔")][-1]
except Exception:
    pass

r = cs_build.build_one(CN)
print("OK", CN, r["bytes"], r["check"].get("ok"))
