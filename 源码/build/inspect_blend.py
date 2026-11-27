"""inspect_blend.py —— 只读检查一个 .blend 里到底装的是哪座建筑

    blender -b --python build/inspect_blend.py -- <path.blend>
"""
import sys

import bpy
from mathutils import Vector

path = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else ""
bpy.ops.wm.open_mainfile(filepath=path)

sc = bpy.context.scene
meshes = [o for o in sc.objects if o.type == "MESH"]
lo = Vector((1e9, 1e9, 1e9))
hi = Vector((-1e9, -1e9, -1e9))
tris = 0
for o in meshes:
    o.data.calc_loop_triangles()
    tris += len(o.data.loop_triangles)
    for c in o.bound_box:
        w = o.matrix_world @ Vector(c)
        for i in range(3):
            lo[i] = min(lo[i], w[i])
            hi[i] = max(hi[i], w[i])

print("FILE      :", path)
print("SCENES    :", [s.name for s in bpy.data.scenes])
print("ACTIVE    :", sc.name)
print("OBJECTS   :", len(meshes), [o.name for o in meshes][:12])
print("MATERIALS :", sorted(m.name for m in bpy.data.materials))
print("TRIS      :", tris)
print("BBOX_MIN  :", [round(v, 2) for v in lo])
print("BBOX_MAX  :", [round(v, 2) for v in hi])
print("SIZE      :", [round(v, 2) for v in (hi - lo)])
print("TEXTS     :", [t.name for t in bpy.data.texts])
