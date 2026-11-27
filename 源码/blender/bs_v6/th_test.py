"""th_test.py —— 快速体检：建低模 + 细分，打印面数 / 包围盒 / 材质。"""
import importlib
import os
import sys

import bpy
from mathutils import Vector

HERE = r"D:/测试一/blender/bs_v6"
if HERE not in sys.path:
    sys.path.insert(0, HERE)
for _m in ("bslib", "br_model", "th_model"):
    if _m in sys.modules:
        importlib.reload(sys.modules[_m])
import th_model  # noqa: E402


def clear():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for blk in (bpy.data.meshes, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
        for it in list(blk):
            try:
                blk.remove(it)
            except Exception:
                pass


def bbox(objs):
    lo = Vector((1e9, 1e9, 1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    for ob in objs:
        for c in ob.bound_box:
            w = ob.matrix_world @ Vector(c)
            for i in range(3):
                lo[i] = min(lo[i], w[i])
                hi[i] = max(hi[i], w[i])
    return lo, hi


for smooth in (False, True):
    clear()
    objs, st = th_model.build(smooth=smooth)
    lo, hi = bbox(objs)
    print("SMOOTH" if smooth else "LOW", st)
    print("  bbox", [round(v, 3) for v in lo], [round(v, 3) for v in hi],
          "size", [round(hi[i] - lo[i], 3) for i in range(3)])
    print("  parts", len(th_model.Model(False).build().items))
print("DONE")
