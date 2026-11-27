"""diag_unit.py —— 单件单位体检：静止姿态是否正常 + 出 320² 诊断图

    blender -b --factory-startup --python blender/bs_v6/diag_unit.py -- <glb相对路径> [标签]

打印：对象/顶点/骨骼/修改器、静止姿态包围盒、逐骨 matrix_basis 是否非单位。
产出：docs/_tmp/diag/<标签>.png
"""
import importlib
import os
import sys

import bpy
from mathutils import Vector

HERE = r"D:/测试一/blender/bs_v6"
ROOT = r"D:/测试一"
if HERE not in sys.path:
    sys.path.insert(0, HERE)
for _m in ("iconlib",):
    if _m in sys.modules:
        importlib.reload(sys.modules[_m])
import iconlib  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
rel = argv[0]
label = argv[1] if len(argv) > 1 else os.path.splitext(os.path.basename(rel))[0]
path = os.path.join(ROOT, rel)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=path)
bpy.context.view_layer.update()

objs = [o for o in bpy.context.scene.objects
        if o.type == "MESH"
        and not any(c.name == "glTF_not_exported" for c in o.users_collection)]

print("=" * 70)
print("[file]", rel)
print("[objects]", len(objs))
for o in objs:
    mods = [(m.type, getattr(m, "object", None).name if getattr(m, "object", None) else None)
            for m in o.modifiers]
    print("   ", o.name, "verts", len(o.data.vertices), "mods", mods,
          "parent", o.parent.name if o.parent else None)

arms = [o for o in bpy.context.scene.objects if o.type == "ARMATURE"]
for arm in arms:
    print("[armature]", arm.name, "bones", len(arm.pose.bones),
          "scale", tuple(round(v, 3) for v in arm.scale))
    odd = []
    for pb in arm.pose.bones:
        mb = pb.matrix_basis
        ident = all(abs(mb[i][j] - (1.0 if i == j else 0.0)) < 1e-5
                    for i in range(4) for j in range(4))
        if not ident:
            loc = tuple(round(v, 3) for v in pb.location)
            odd.append((pb.name, loc, round(pb.rotation_quaternion.angle, 2)))
    print("   pose.bones 非单位 basis:", len(odd), odd[:8])
    print("   rest 骨长越界(>2m 或 <0.01m):",
          [(b.name, round(b.length, 3)) for b in arm.data.bones
           if b.length > 2.0 or b.length < 0.01][:8])

dg = bpy.context.evaluated_depsgraph_get()
mn = Vector((1e9,) * 3)
mx = Vector((-1e9,) * 3)
for o in objs:
    ev = o.evaluated_get(dg)
    me = ev.to_mesh()
    for v in me.vertices:
        p = ev.matrix_world @ v.co
        for i in range(3):
            mn[i] = min(mn[i], p[i])
            mx[i] = max(mx[i], p[i])
    ev.to_mesh_clear()
print("[eval bbox] min", tuple(round(v, 3) for v in mn),
      "max", tuple(round(v, 3) for v in mx),
      "size", tuple(round(mx[i] - mn[i], 3) for i in range(3)))

out = os.path.join(ROOT, "docs", "_tmp", "diag", label + ".png")
iconlib.clear_scene()
bpy.ops.import_scene.gltf(filepath=path)
bpy.context.view_layer.update()
objs2 = [o for o in bpy.context.scene.objects
         if o.type == "MESH"
         and not any(c.name == "glTF_not_exported" for c in o.users_collection)]
n, span, sil = iconlib.shoot(objs2, 22, 14, out, res=320, samples=32)
print("[shot]", out, n, "span %.3f" % span, "sil %.3f x %.3f" % sil)
print("=" * 70)
