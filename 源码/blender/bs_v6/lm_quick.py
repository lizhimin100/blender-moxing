"""lm_quick.py —— 伐木场构建冒烟：bbox / 构件数 / tri / 材质（不出图、不导出）"""
import importlib
import sys

import bpy
from mathutils import Vector

HERE = r"D:/测试一/blender/bs_v6"
if HERE not in sys.path:
    sys.path.insert(0, HERE)
for _m in ("bslib", "br_model", "lm_model"):
    if _m in sys.modules:
        importlib.reload(sys.modules[_m])
import lm_model  # noqa: E402


def main():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    m = lm_model.Model(False, unwrap=False).build()
    parts = len(m.items)
    objs, st = lm_model.build(smooth=False, unwrap=False)
    lo = Vector((1e9, 1e9, 1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    for ob in objs:
        for c in ob.bound_box:
            w = ob.matrix_world @ Vector(c)
            for i in range(3):
                lo[i] = min(lo[i], w[i])
                hi[i] = max(hi[i], w[i])
    print("BUILD_PARTS", parts)
    print("BBOX", [round(v, 3) for v in lo], [round(v, 3) for v in hi])
    print("SIZE", [round(v, 3) for v in (hi - lo)])
    print("STATS", st)
    for ob in objs:
        print("  OBJ %-16s tris=%5d" % (ob.name, len(ob.data.loop_triangles)))


main()
