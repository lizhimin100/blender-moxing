"""_probe_sect.py —— 打印弩身在两个握点附近的真实截面（局部 sv/up 坐标）。"""
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for p in (HERE, os.path.join(ROOT, "联盟", "弩兵")):
    if p not in sys.path:
        sys.path.insert(0, p)

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
SRC = os.path.join(HERE, "_ref", "联盟", "方块人_弩兵.glb")
bpy.ops.import_scene.gltf(filepath=SRC)
arm = next(o for o in sc.objects if o.type == "ARMATURE")
for pb in arm.pose.bones:
    pb.matrix_basis.identity()
for o in [o for o in sc.objects if o.type == "MESH"]:
    bpy.data.objects.remove(o, do_unlink=True)

import unit_弩兵 as U
import unitkit as K

u = U.build(1)
objs = u.finish(prefix="unit")
u.bind(arm, objs)
bpy.context.view_layer.update()

h, t = U.WEAPON_H, U.WEAPON_T
ax = (t - h).normalized()
sv = Vector((0, 0, 1)).cross(ax).normalized()
up = ax.cross(sv)

pts = {}
for ob in objs:
    gi = {g.index: g.name for g in ob.vertex_groups}
    for v in ob.data.vertices:
        if not v.groups:
            continue
        g = max(v.groups, key=lambda x: x.weight)
        nm = gi.get(g.group, "?")
        if nm not in ("weapon", "prop_bolt"):
            continue
        p = ob.matrix_world @ v.co
        d = p - h
        pts.setdefault(nm, []).append((d.dot(ax), d.dot(sv), d.dot(up)))

for nm in ("weapon",):
    for label, s0 in (("R", -0.097), ("L", 0.058)):
        rows = [q for q in pts[nm] if abs(q[0] - s0) < 0.036 and abs(q[1]) < 0.09]
        rows.sort(key=lambda q: (round(q[0], 3), round(q[1], 3), round(q[2], 3)))
        print("== %s grip %s fwd=%.3f  n=%d" % (nm, label, s0, len(rows)))
        for q in rows:
            print("   fwd %+.3f  sv %+.3f  up %+.3f" % q)
print("== prop_bolt near grips")
for label, s0 in (("R", -0.097), ("L", 0.058)):
    rows = [q for q in pts["prop_bolt"] if abs(q[0] - s0) < 0.036]
    rows.sort(key=lambda q: (round(q[0], 3), round(q[1], 3), round(q[2], 3)))
    print("-- %s n=%d" % (label, len(rows)))
    for q in rows:
        print("   fwd %+.3f  sv %+.3f  up %+.3f" % q)
