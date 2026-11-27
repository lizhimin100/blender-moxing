"""检查_穿模.py —— 萨满各动作里「巫杖 × 身体/头」的逐帧相交与净空

用法：
  blender -b --factory-startup --python 秘法/豺狼人萨满/检查_穿模.py
  blender -b --factory-startup --python 秘法/豺狼人萨满/检查_穿模.py -- cast attack

输出：每个动作 RED 帧列表（BVH 相交三角数）+ 全动作最小净空（采样点距离）。
"""
import importlib
import os
import sys

import bpy
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = HERE
while not os.path.isdir(os.path.join(ROOT, "库")):
    _up = os.path.dirname(ROOT)
    if _up == ROOT:
        break
    ROOT = _up
LIB = os.path.join(ROOT, "库")
for _p in (LIB, HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import unitkit2 as K  # noqa: E402

for _m in ("unitkit2", "unit_萨满", "anims_萨满"):
    if _m in sys.modules:
        importlib.reload(sys.modules[_m])
import unit_萨满 as U  # noqa: E402
import anims_萨满 as A  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ONLY = set(argv) if argv else None

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.fps = 30

u = U.build(low=False)
objs = u.finish(prefix=U.PREFIX, join_by="module")
arm = U.build_rig()
u.bind(arm, objs)
A.build_all(arm)

by_name = {o.name: o for o in objs}
print("[objs]", list(by_name))
STAFF = [o for o in objs if o.name.endswith("_staff")]
BODY = [o for o in objs if o.name.endswith("_body")]
HEAD = [o for o in objs if o.name.endswith("_head")]
FX = [o for o in objs if o.name.endswith("_fx")]


def bvh(ob, dg):
    oe = ob.evaluated_get(dg)
    me = oe.to_mesh()
    mw = oe.matrix_world
    verts = [tuple(mw @ v.co) for v in me.vertices]
    polys = [tuple(p.vertices) for p in me.polygons]
    t = BVHTree.FromPolygons(verts, polys, all_triangles=False, epsilon=0.0)
    oe.to_mesh_clear()
    return t, verts


def gap(t, verts):
    """采样点 → 目标表面的最近距离（近似净空）。"""
    lo = 1e9
    for p in verts:
        hit, n, i, d = t.find_nearest(p)
        if d is not None:
            lo = min(lo, d)
    return lo


arm.animation_data_create()
for act in sorted(bpy.data.actions, key=lambda a: a.name):
    if ONLY and act.name not in ONLY:
        continue
    arm.animation_data.action = act
    try:
        arm.animation_data.action_slot = act.slots[0]
    except Exception:
        pass
    f0, f1 = (int(v) for v in act.frame_range)
    red = []
    worst = (1e9, -1)
    for f in range(f0, f1 + 1):
        scene.frame_set(f)
        bpy.context.view_layer.update()
        dg = bpy.context.evaluated_depsgraph_get()
        ts, vs = bvh(STAFF[0], dg)
        th, vh = bvh(HEAD[0], dg)
        tb, vb = bvh(BODY[0], dg)
        n_h = len(ts.overlap(th))
        n_b = len(ts.overlap(tb))
        if n_h:
            red.append((f, n_h))
        n_any = n_h or n_b
        g = gap(th, vs[::2])
        if g < worst[0]:
            worst = (g, f)
        if n_any and f % 4 == 0:
            print("    f%3d  head=%3d body=%3d  gap_head=%.4f" % (f, n_h, n_b, g))
    print("[%s] f%d..%d  HEAD-RED %d frames %s  min_gap %.4f @f%d"
          % (act.name, f0, f1, len(red), red, worst[0], worst[1]))

arm.animation_data.action = None
print("[done]")
