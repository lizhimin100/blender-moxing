"""_probe_handrot.py —— 旧动作里手掌朝向相对"焊死朝向"偏了多少度 + 实际穿透深度"""
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
GLB = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else os.path.join(
    os.path.dirname(os.path.dirname(HERE)), "assets", "单位", "联盟", "弩兵", "方块人_弩兵.glb")

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.fps = 30
bpy.ops.import_scene.gltf(filepath=GLB)
bpy.context.view_layer.update()
arm = next(o for o in sc.objects if o.type == "ARMATURE")

rest = {b.name: (b.head_local.copy(), b.matrix_local.to_3x3().copy()) for b in arm.data.bones}
wh, wr = rest["weapon"]
REL = {s: wr.inverted() @ rest["hand_" + s][1] for s in ("R", "L")}
OFF = {s: wr.inverted() @ (rest["hand_" + s][0] - wh) for s in ("R", "L")}

for name in ("idle", "idle_b", "walk", "shoot", "reload", "hurt", "death"):
    act = bpy.data.actions.get(name)
    if not act:
        continue
    arm.animation_data_create()
    arm.animation_data.action = act
    try:
        arm.animation_data.action_slot = act.slots[0]
    except Exception:
        pass
    f0, f1 = (int(v) for v in act.frame_range)
    worst = {s: 0.0 for s in ("R", "L")}
    wf = {s: 0 for s in ("R", "L")}
    for f in range(f0, f1 + 1):
        sc.frame_set(f)
        bpy.context.view_layer.update()
        mw = arm.pose.bones["weapon"].matrix.to_3x3()
        for s in ("R", "L"):
            mh = arm.pose.bones["hand_" + s].matrix.to_3x3()
            q = (mw @ REL[s]).to_quaternion().rotation_difference(mh.to_quaternion())
            deg = math.degrees(abs(q.angle))
            if deg > worst[s]:
                worst[s], wf[s] = deg, f
    print("[handrot] %-7s  R 最大偏 %.1f° @f%d    L 最大偏 %.1f° @f%d"
          % (name, worst["R"], wf["R"], worst["L"], wf["L"]))
