"""_probe_drift.py —— 旧动作里手腕相对"弩骨"的漂移（按弩骨局部坐标，单位 m）"""
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "_ref", "联盟", "方块人_弩兵.glb")

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.fps = 30
bpy.ops.import_scene.gltf(filepath=SRC)
bpy.context.view_layer.update()
arm = next(o for o in sc.objects if o.type == "ARMATURE")

# rest：骨的世界矩阵
rest = {}
for b in arm.data.bones:
    rest[b.name] = (arm.matrix_world @ b.matrix_local).copy()
Mw = rest["weapon"]
for s in ("R", "L"):
    off = Mw.inverted() @ rest["hand_" + s].translation
    print("[rest-off] hand_%s in weapon frame: (%.4f, %.4f, %.4f)" % (s, off.x, off.y, off.z))

for act in sorted(bpy.data.actions, key=lambda a: a.name):
    arm.animation_data_create()
    arm.animation_data.action = act
    try:
        arm.animation_data.action_slot = act.slots[0]
    except Exception:
        pass
    f0, f1 = (int(v) for v in act.frame_range)
    dev = {"R": [0, 0, 0], "L": [0, 0, 0]}
    rng = {"R": [1e9, -1e9], "L": [1e9, -1e9]}
    for f in range(f0, f1 + 1):
        sc.frame_set(f)
        bpy.context.view_layer.update()
        mw = (arm.matrix_world @ arm.pose.bones["weapon"].matrix).copy()
        inv = mw.inverted()
        for s in ("R", "L"):
            p = inv @ (arm.matrix_world @ arm.pose.bones["hand_" + s].matrix).translation
            d = p - Mw.inverted() @ rest["hand_" + s].translation
            for i in range(3):
                dev[s][i] = max(dev[s][i], abs(d[i]))
            rng[s][0] = min(rng[s][0], d.length)
            rng[s][1] = max(rng[s][1], d.length)
    print("[drift] %-8s f%3d..%3d  R max|d|=(%.3f,%.3f,%.3f) |d|[%.3f,%.3f]   L max|d|=(%.3f,%.3f,%.3f) |d|[%.3f,%.3f]"
          % (act.name, f0, f1, dev["R"][0], dev["R"][1], dev["R"][2], rng["R"][0], rng["R"][1],
             dev["L"][0], dev["L"][1], dev["L"][2], rng["L"][0], rng["L"][1]))
