"""probe_glb.py —— 快速查一件 GLB：对象 / 材质色 / 包围盒 / 骨 / 动作 / 零件中心

用法：
  blender -b --factory-startup --python 库/probe_glb.py -- <glb> [--parts]
"""
import os
import sys

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
GLB = argv[0]
PARTS = "--parts" in argv

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)
bpy.context.view_layer.update()

meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
arms = [o for o in bpy.context.scene.objects if o.type == "ARMATURE"]
mn = Vector((1e9,) * 3)
mx = Vector((-1e9,) * 3)
tris = 0
for o in meshes:
    o.data.calc_loop_triangles()
    tris += len(o.data.loop_triangles)
    for v in o.data.vertices:
        p = o.matrix_world @ v.co
        for i in range(3):
            mn[i] = min(mn[i], p[i])
            mx[i] = max(mx[i], p[i])
print("== bbox ==", tuple(round(v, 3) for v in mn), tuple(round(v, 3) for v in mx))
print("== size ==", tuple(round(mx[i] - mn[i], 3) for i in range(3)), "tris", tris)
print("== meshes ==", [(o.name, len(o.data.loop_triangles)) for o in meshes])
for o in meshes:
    print("   ", o.name, "verts", len(o.data.vertices), "vgroups",
          len(o.vertex_groups), [m.name for m in o.data.materials if m])
print("== bones ==", len(arms[0].data.bones) if arms else 0)
if arms:
    for b in arms[0].data.bones:
        h = b.head_local
        print("   %-16s head (%.3f, %.3f, %.3f) len %.3f parent %s"
              % (b.name, h.x, h.y, h.z, b.length, b.parent.name if b.parent else "-"))
print("== actions ==", [(a.name, tuple(int(v) for v in a.frame_range)) for a in bpy.data.actions])

print("== materials ==")
for m in bpy.data.materials:
    if not m.use_nodes:
        continue
    for n in m.node_tree.nodes:
        if n.type == "BSDF_PRINCIPLED":
            c = n.inputs["Base Color"].default_value
            print("   %-16s rgb (%.3f %.3f %.3f)  metal %.2f rough %.2f"
                  % (m.name, c[0], c[1], c[2], n.inputs["Metallic"].default_value,
                     n.inputs["Roughness"].default_value))
            break

if PARTS and meshes:
    print("== part clusters (per material island center) ==")
