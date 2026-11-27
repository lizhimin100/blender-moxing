"""th_quick.py —— 城镇大厅 v3 的快速冒烟：构建一次、报包围盒 / 构件数 / 三角面。

    python build/bl_act.py act blender/bs_v6/th_quick.py
"""
import importlib
import json
import os
import sys

import bpy
from mathutils import Vector

HERE = r"D:/测试一/blender/bs_v6"
OUT = r"D:/测试一/docs/城镇大厅/v3/探针/quick.txt"
if HERE not in sys.path:
    sys.path.insert(0, HERE)
for _m in ("bslib", "br_model", "th_model"):
    if _m in sys.modules:
        importlib.reload(sys.modules[_m])
import th_model  # noqa: E402


def clear_scene():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for blk in (bpy.data.meshes, bpy.data.materials, bpy.data.images):
        for it in list(blk):
            try:
                blk.remove(it)
            except Exception:
                pass


def main():
    lines = []
    for tag, smooth in (("low", False), ("smooth", True)):
        clear_scene()
        m = th_model.Model(smooth, unwrap=False).build()
        n_items = len(m.items)
        objs = m.finalize(bevel=True)
        lo = Vector((1e9, 1e9, 1e9))
        hi = Vector((-1e9, -1e9, -1e9))
        tris = verts = faces = 0
        for ob in objs:
            ob.data.calc_loop_triangles()
            tris += len(ob.data.loop_triangles)
            verts += len(ob.data.vertices)
            faces += len(ob.data.polygons)
            for c in ob.bound_box:
                w = ob.matrix_world @ Vector(c)
                for i in range(3):
                    lo[i] = min(lo[i], w[i])
                    hi[i] = max(hi[i], w[i])
        size = [hi[i] - lo[i] for i in range(3)]
        lines.append("%-7s items=%d objs=%d tris=%d verts=%d faces=%d" %
                     (tag, n_items, len(objs), tris, verts, faces))
        lines.append("        bbox min=(%.3f, %.3f, %.3f) max=(%.3f, %.3f, %.3f)"
                     % (lo.x, lo.y, lo.z, hi.x, hi.y, hi.z))
        lines.append("        size=(%.3f, %.3f, %.3f)  mats=%d"
                     % (size[0], size[1], size[2],
                        len({mt.name for ob in objs for mt in ob.data.materials if mt})))
        lines.append("        front_ratio=%.2f  grounded=%s"
                     % (hi.y / max(1e-6, abs(lo.y)), abs(lo.z) <= 0.20))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))


main()
