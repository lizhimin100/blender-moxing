"""bs_probe.py —— 射线诊断：把正面视图某几个像素反查成对象 + 材质。"""
import importlib
import os
import sys

import bpy
from mathutils import Vector

HERE = r"D:/测试一/blender/bs_v6"
if HERE not in sys.path:
    sys.path.insert(0, HERE)
for mod in ("bslib", "bs_model"):
    if mod in sys.modules:
        importlib.reload(sys.modules[mod])
import bs_model  # noqa: E402


def clear_scene():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for blk in (bpy.data.meshes, bpy.data.materials, bpy.data.images,
                bpy.data.armatures, bpy.data.actions, bpy.data.cameras, bpy.data.lights):
        for it in list(blk):
            try:
                blk.remove(it)
            except Exception:
                pass


def bounds(objs):
    lo = Vector((1e9, 1e9, 1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    for ob in objs:
        for c in ob.bound_box:
            w = ob.matrix_world @ Vector(c)
            for i in range(3):
                lo[i] = min(lo[i], w[i])
                hi[i] = max(hi[i], w[i])
    return lo, hi


clear_scene()
objs, _ = bs_model.build(smooth=True)
lo, hi = bounds(objs)
ctr = (lo + hi) * 0.5
span = max((hi - lo).x, (hi - lo).z) * 1.28 * 1.04

cam = bpy.data.cameras.new("Cam")
cam.type = "ORTHO"
cam.ortho_scale = span
co = bpy.data.objects.new("Cam", cam)
bpy.context.scene.collection.objects.link(co)
co.location = ctr + Vector((0.0, span * 4.0, 0.06 * span * 4.0))
co.rotation_euler = (ctr - co.location).to_track_quat("-Z", "Y").to_euler()
bpy.context.view_layer.update()

dg = bpy.context.evaluated_depsgraph_get()
mw = co.matrix_world
right = (mw.to_3x3() @ Vector((1, 0, 0))).normalized()
up = (mw.to_3x3() @ Vector((0, 1, 0))).normalized()
fwd = (mw.to_3x3() @ Vector((0, 0, -1))).normalized()

# 采样点用归一化屏幕坐标 (u 右, v 上)，范围 [-1, 1]
POINTS = [(u / 100.0, v / 100.0) for v in range(10, 40, 5) for u in range(-60, -10, 5)]
print("SPAN", round(span, 3), "CTR", [round(v, 2) for v in ctr])
for (u, v) in POINTS:
    origin = co.location + right * (u * span * 0.5) + up * (v * span * 0.5)
    hit, loc, nrm, idx, ob, mat = bpy.context.scene.ray_cast(dg, origin, fwd)
    if hit:
        m = ob.data.materials[0].name if ob.data.materials else "?"
        print(f"{u:+.1f},{v:+.1f} -> {ob.name:24s} {m:12s} loc=({loc.x:+.2f},{loc.y:+.2f},{loc.z:+.2f})")
    else:
        print(f"{u:+.1f},{v:+.1f} -> MISS")
