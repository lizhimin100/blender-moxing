"""at_quick.py —— 箭塔构建冒烟：构件数 / bbox / tri / 材质（不出图、不导出）"""
import importlib
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


def main():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    m = at_model.Model(False, unwrap=False).build()
    print("BUILD_PARTS", len(m.items))
    objs, st = at_model.build(smooth=False, unwrap=False)
    lo = Vector((1e9, 1e9, 1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    for ob in objs:
        for c in ob.bound_box:
            w = ob.matrix_world @ Vector(c)
            for i in range(3):
                lo[i] = min(lo[i], w[i])
                hi[i] = max(hi[i], w[i])
    print("BBOX", [round(v, 3) for v in lo], [round(v, 3) for v in hi])
    print("SIZE", [round(v, 3) for v in (hi - lo)])
    print("STATS_LOW", st)
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    objs2, st2 = at_model.build(smooth=True, unwrap=False)
    print("STATS_SMOOTH", st2)
    for ob in objs2:
        print("  OBJ %-16s tris=%5d" % (ob.name, len(ob.data.loop_triangles)))


main()
