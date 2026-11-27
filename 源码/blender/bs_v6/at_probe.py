"""at_probe.py —— 箭塔 v2 的快速几何探针：只看能不能建起来、尺寸多少、构件数多少

    python build/bl_act.py act blender/bs_v6/at_probe.py
"""
import importlib
import os
import sys

import bpy
from mathutils import Vector

HERE = r"D:/测试一/blender/bs_v6"
if HERE not in sys.path:
    sys.path.insert(0, HERE)
for _m in ("bslib", "br_model", "wt_model", "at_model"):
    if _m in sys.modules:
        importlib.reload(sys.modules[_m])
import at_model  # noqa: E402

for ob in list(bpy.data.objects):
    bpy.data.objects.remove(ob, do_unlink=True)

m = at_model.Model(False, unwrap=False).build()
print("PARTS", len(m.items))
bpy.context.view_layer.update()

lo = Vector((1e9, 1e9, 1e9))
hi = Vector((-1e9, -1e9, -1e9))
for it in m.items:
    ob = it[0]
    for c in ob.bound_box:
        w = ob.matrix_world @ Vector(c)
        for i in range(3):
            lo[i] = min(lo[i], w[i])
            hi[i] = max(hi[i], w[i])
print("BBOX", [round(v, 2) for v in lo], [round(v, 2) for v in hi])
print("SIZE", [round(v, 2) for v in (hi - lo)])
names = sorted({it[0].name.split("_")[0] for it in m.items})
print("PREFIX", names)
