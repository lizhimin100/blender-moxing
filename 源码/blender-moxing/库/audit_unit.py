"""audit_unit.py —— 单位交付自检（读数，不出图）。

用法：blender -b --factory-startup --python 库/audit_unit.py -- <glb>
输出：一行行可粘贴的回执。
"""
import sys
import math

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
GLB = argv[0]

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.render.fps = 30
bpy.ops.import_scene.gltf(filepath=GLB)
objs = [o for o in bpy.context.scene.objects if o.type == "MESH" and not o.name.startswith("Icosphere")]
arm = [o for o in bpy.context.scene.objects if o.type == "ARMATURE"][0]
for pb in arm.pose.bones:
    pb.matrix_basis.identity()

# ① 权重
verts = 0
zero = 0
max_inf = 0
unnorm = 0
for o in objs:
    for v in o.data.vertices:
        verts += 1
        s = sum(g.weight for g in v.groups)
        n = len(v.groups)
        max_inf = max(max_inf, n)
        if s < 1e-6:
            zero += 1
        elif abs(s - 1.0) > 1e-3:
            unnorm += 1
print("① 权重 verts=%d zero=%d max_inf=%d unnorm=%d" % (verts, zero, max_inf, unnorm))

# ② 接地 / bbox
mn = Vector((1e9,) * 3); mx = Vector((-1e9,) * 3)
for o in objs:
    for v in o.data.vertices:
        p = o.matrix_world @ v.co
        for i in range(3):
            mn[i] = min(mn[i], p[i]); mx[i] = max(mx[i], p[i])
print("② 接地 min_z=%.5f max_z=%.4f bbox_x=[%.3f,%.3f] bbox_y=[%.3f,%.3f]"
      % (mn.z, mx.z, mn.x, mx.x, mn.y, mx.y))

# ③ 动作
acts = sorted(bpy.data.actions, key=lambda a: a.name)
print("③ 动作 %d %s" % (len(acts), ", ".join(a.name for a in acts)))
arm.animation_data_create()
for a in acts:
    arm.animation_data.action = a
    try:
        arm.animation_data.action_slot = a.slots[0]
    except Exception:
        pass
    f0, f1 = a.frame_range
    # loop Δ
    def pose_at(f):
        bpy.context.scene.frame_set(int(f), subframe=float(f - int(f)))
        bpy.context.view_layer.update()
        return [pb.matrix.copy() for pb in arm.pose.bones]
    p0 = pose_at(f0)
    p1 = pose_at(f1)
    dmax = 0.0
    for m0, m1 in zip(p0, p1):
        for r in range(4):
            for c in range(4):
                dmax = max(dmax, abs(m0[r][c] - m1[r][c]))
    # root motion
    pts = []
    for f in range(int(f0), int(f1) + 1):
        bpy.context.scene.frame_set(f)
        bpy.context.view_layer.update()
        pts.append(arm.pose.bones["root"].head.copy())
    root_d = max((p - pts[0]).length for p in pts) if pts else 0.0
    print("   %-10s %5.2fs loop_Δ=%.2e root=%.5f" % (a.name, (f1 - f0) / 30.0, dmax, root_d))

# ④ 面数 / 材质 / mesh
tris = 0
for o in objs:
    o.data.calc_loop_triangles()
    tris += len(o.data.loop_triangles)
print("④ 面数 %d  meshes=%d  %s" % (tris, len(objs), [(o.name, len(o.data.loop_triangles)) for o in objs]))
print("   materials %s" % sorted(m.name for m in bpy.data.materials if m.users))

# ⑤ 骨数
print("⑤ 骨数 %d" % len(arm.data.bones))

# ⑥ 部件质心（前 3 与最低 3）—— 看有没有飞件
lows = []
for o in objs:
    for v in o.data.vertices:
        lows.append((v.co.z, o.name))
lows.sort()
print("⑥ 最低点 %s" % [(round(z, 3), n) for z, n in lows[:3]])

print("[done]", GLB)
