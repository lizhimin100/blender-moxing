"""audit_blends.py —— 一次开完 assets/*/*.blend，核对每份里装的对象前缀 / 尺寸

    blender -b --python build/audit_blends.py
"""
import glob
import os

import bpy
from mathutils import Vector

ROOT = r"D:/测试一/assets"
rows = []
for path in sorted(glob.glob(os.path.join(ROOT, "*", "*.blend"))):
    bpy.ops.wm.open_mainfile(filepath=path)
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
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
    prefixes = sorted({o.name.split("-")[0] for o in meshes})
    rows.append((os.path.relpath(path, ROOT), len(meshes), prefixes,
                 [round(v, 2) for v in (hi - lo)], tris,
                 sorted(m.name for m in bpy.data.materials)))

print("\n=== AUDIT ===")
for name, n, pre, size, tris, mats in rows:
    print("%-26s obj=%-3d prefix=%-8s size=%-22s tri=%-6d mats=%d %s"
          % (name, n, ",".join(pre), str(size), tris, len(mats), mats))
print("=== END ===")
