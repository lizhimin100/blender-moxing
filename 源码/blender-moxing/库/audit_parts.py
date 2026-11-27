"""audit_parts.py —— 零件级相交审计（精模单位专用）

思路：把单位按"零件"拆开（join_by="part"），逐件建 BVH，两两求交。
报告分三档：
  RED    跨模块 / 跨肢体的相交（手插进裙子、盾插进腿、刃插进胸）—— 必须修
  YELLOW 同模块但不同骨的相交（甲片压甲片之外的意外重叠）—— 需要人看一眼
  GREEN  父子骨 / 同骨 的相交（关节套筒、甲片压在肢体上）—— 设计如此，忽略

用法：
  blender -b --factory-startup --python 库/audit_parts.py -- <unit_module_dir> <module_name> [--anim]
"""
import importlib
import sys
import os

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
UNIT_DIR = os.path.abspath(argv[0])
MOD = argv[1]
WITH_ANIM = "--anim" in argv

_root = UNIT_DIR
while not os.path.isdir(os.path.join(_root, "库")):
    _up = os.path.dirname(_root)
    if _up == _root:
        break
    _root = _up
sys.path.insert(0, os.path.join(_root, "库"))
sys.path.insert(0, UNIT_DIR)
import unitkit2 as K  # noqa: E402

if MOD in sys.modules:
    importlib.reload(sys.modules[MOD])
U = importlib.import_module(MOD)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.render.fps = 30
u = U.build(low=False)
objs = u.finish(prefix=U.PREFIX, join_by="part")
arm = U.build_rig()
u.bind(arm, objs)

# 骨名 → 祖先集合
parent = {b.name: (b.parent.name if b.parent else None) for b in arm.data.bones}


def anc(n):
    out = []
    while n:
        out.append(n)
        n = parent.get(n)
    return out


def related(a, b):
    return a in anc(b) or b in anc(a) or a == b


mods = {}
for m in u.meta:
    mods[m["obj"]] = (m["module"], m["bone"])

trees = {}
for ob in objs:
    me = ob.data
    verts = [tuple(v.co) for v in me.vertices]
    polys = [tuple(p.vertices) for p in me.polygons]
    trees[ob.name] = BVHTree.FromPolygons(verts, polys, all_triangles=False, epsilon=0.0)

names = sorted(trees)
red, yellow = [], []
for i in range(len(names)):
    for j in range(i + 1, len(names)):
        a, b = names[i], names[j]
        ma, ba = mods.get(a, ("?", "?"))
        mb, bb = mods.get(b, ("?", "?"))
        if related(ba, bb):
            continue
        ov = trees[a].overlap(trees[b])
        if not ov:
            continue
        row = (len(ov), a, b, ma, mb, ba, bb)
        if ma != mb:
            red.append(row)
        else:
            yellow.append(row)

print("== RED (跨模块) ==", len(red))
for r in sorted(red, reverse=True)[:40]:
    print("  %4d  %-22s x %-22s  [%s/%s] x [%s/%s]" % r)
print("== YELLOW (同模块跨骨) ==", len(yellow))
for r in sorted(yellow, reverse=True)[:40]:
    print("  %4d  %-22s x %-22s  %s x %s" % (r[0], r[1], r[2], r[5], r[6]))

if WITH_ANIM:
    print("== ANIM zmin ==")
    arm.animation_data_create()
    for act in sorted(bpy.data.actions, key=lambda a: a.name):
        arm.animation_data.action = act
        try:
            arm.animation_data.action_slot = act.slots[0]
        except Exception:
            pass
        f0, f1 = (int(v) for v in act.frame_range)
        zmin = 1e9
        for f in range(f0, f1 + 1, max(1, (f1 - f0) // 12)):
            bpy.context.scene.frame_set(f)
            bpy.context.view_layer.update()
            dg = bpy.context.evaluated_depsgraph_get()
            for ob in objs:
                oe = ob.evaluated_get(dg)
                me = oe.to_mesh()
                for v in me.vertices:
                    zmin = min(zmin, (oe.matrix_world @ v.co).z)
                oe.to_mesh_clear()
        print("  %-10s zmin=%.4f" % (act.name, zmin))
    arm.animation_data.action = None

print("[done]")
