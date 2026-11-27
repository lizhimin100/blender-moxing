"""ch_look.py —— 角色快速看片（不写正式交付目录）"""
import importlib
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = r"D:/测试一/blender/bs_v6"
OUT = r"D:/测试一/docs/剑士/_look"
if HERE not in sys.path:
    sys.path.insert(0, HERE)
for mod in ("bslib", "ch_model", "shotlib"):
    if mod in sys.modules:
        importlib.reload(sys.modules[mod])
import ch_model  # noqa: E402
import shotlib as S  # noqa: E402

S.OUTSHOT = OUT
S.RES, S.SAMP = 900, 40


def main():
    os.makedirs(OUT, exist_ok=True)
    S.clear_scene()
    objs, st = ch_model.build(smooth=True, bevel=True)
    print("STATS", st)
    for ob in objs:
        ob.data.calc_loop_triangles()
        print("  %-12s %5d tri" % (ob.name, len(ob.data.loop_triangles)))
    lo, hi = S.bounds(objs)
    print("BBOX", [round(v, 3) for v in lo], [round(v, 3) for v in hi],
          "SIZE", [round(v, 3) for v in (hi - lo)])
    S.setup_world()
    S.ground_plane()
    ctr = Vector(((lo.x + hi.x) * 0.5, 0.0, (lo.z + hi.z) * 0.5))
    span = max(hi.z - lo.z, hi.x - lo.x, hi.y - lo.y) * 1.10
    fixed = (ctr, span)
    S.shot("front.png", objs, 0, 4, fixed=fixed)
    S.shot("hero.png", objs, -32, 20, fixed=fixed)
    S.shot("side.png", objs, 90, 4, fixed=fixed)
    S.shot("back.png", objs, 180, 6, fixed=fixed)
    S.shot("top.png", objs, -32, 56, fixed=fixed)
    # 近景
    head = Vector((0, 0, 2.10))
    S.shot("head.png", objs, -26, 12, fixed=(head, 0.95))
    shield = Vector((-0.34, 0.10, 1.24))
    S.shot("shield.png", objs, -46, 10, fixed=(shield, 0.95))
    sword = Vector((0.40, 0.15, 0.80))
    S.shot("sword.png", objs, 26, 8, fixed=(sword, 0.85))
    print("DONE")


main()
