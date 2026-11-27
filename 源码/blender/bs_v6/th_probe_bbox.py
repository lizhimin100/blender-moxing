"""th_probe_bbox.py —— 找出超出预期包围盒的构件。"""
import importlib
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

for ob in list(bpy.data.objects):
    bpy.data.objects.remove(ob, do_unlink=True)
m = th_model.Model(False, unwrap=False).build()
rows = []
for ob in [it[0] for it in m.items]:
    pts = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    lo = [min(p[i] for p in pts) for i in range(3)]
    hi = [max(p[i] for p in pts) for i in range(3)]
    if hi[2] > 16.2 or abs(lo[0]) > 5.4 or abs(hi[0]) > 5.4:
        rows.append((ob.name, [round(v, 3) for v in lo], [round(v, 3) for v in hi]))
for r in rows[:40]:
    print(*r)
print("total", len(rows))
