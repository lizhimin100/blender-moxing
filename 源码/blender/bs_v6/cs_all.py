"""cs_all.py —— 九座批量：量体 → 建造系统 → 导出 → 体检 → 汇总。

在 Blender 进程内跑：
    python build/bl_act.py act blender/bs_v6/cs_all.py
"""
import importlib
import json
import os
import sys

import bpy

HERE = "D:/测试一/blender/bs_v6"
ROOT = "D:/测试一"
sys.path.insert(0, HERE)

import cs_kit
import cs_rig
import cs_build
import cs_check

for m in (cs_kit, cs_rig, cs_build, cs_check):
    importlib.reload(m)

BUILDINGS = ["铁匠铺", "兵营", "城镇大厅", "哨塔", "农场", "伐木场", "神秘圣地",
             "蒸汽车坊", "箭塔", "地牢", "地下城入口", "酒馆内部"]


def main(only=None, detail="low"):
    out = {}
    for cn in (only or BUILDINGS):
        try:
            out[cn] = cs_build.build_one(cn, detail=detail, shots=False)
        except Exception as exc:
            import traceback
            traceback.print_exc()
            out[cn] = {"error": repr(exc)}
    p = os.path.join(ROOT, "docs", "建造系统", "汇总.json")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("=== 汇总 ===")
    for cn, r in out.items():
        if "error" in r:
            print(f"{cn}: ERROR {r['error']}")
            continue
        c = r.get("check", {})
        print(f"{cn:5s} {r['bytes']/1024:6.0f}KB  {r['t_end']:.2f}s  "
              f"reveal {r['z0']:.2f}-{r['z_rev1']:.2f}m / {r['rev']:.2f}s  "
              f"lifts {r['n_lifts']}  tri {c.get('tri_body',0)}+{c.get('tri_site',0)}  "
              f"rig {c.get('BODY_RIG')} tris {c.get('BODY_TRIS')}  "
              f"cross {c.get('BVH_CROSS')}  left {c.get('BOX_TALL')}  ok {c.get('ok')}")


main()
