"""probe_rig.py —— 打印骨架 rest 数据 / 动作表 / 指定帧的骨世界位置。

用法：blender -b --factory-startup --python 库/probe_rig.py -- <glb> [action]
"""
import sys
import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
GLB = argv[0]
ACT = argv[1] if len(argv) > 1 else None

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)
arm = [o for o in bpy.context.scene.objects if o.type == "ARMATURE"][0]
print("== armature", arm.name, "scale", tuple(arm.scale))
print("== bones", len(arm.data.bones))
for b in arm.data.bones:
    m = b.matrix_local
    print("  %-12s head=(%7.4f,%7.4f,%7.4f) tail=(%7.4f,%7.4f,%7.4f) roll-ax=(%5.2f,%5.2f,%5.2f) parent=%s"
          % (b.name, *b.head_local, *b.tail_local, *m.col[0][:3], b.parent.name if b.parent else "-"))
print("== pose nonzero")
for pb in arm.pose.bones:
    q = pb.matrix_basis.to_quaternion()
    t = pb.matrix_basis.translation
    if abs(q.angle) > 1e-4 or t.length > 1e-4:
        print("   ", pb.name, "angle", round(q.angle, 4), "t", tuple(round(v, 4) for v in t))
print("== actions")
for a in bpy.data.actions:
    print("   ", a.name, "range", tuple(round(v, 2) for v in a.frame_range), "users", a.users)
if ACT:
    act = bpy.data.actions.get(ACT)
    arm.animation_data_create(); arm.animation_data.action = act
    try:
        arm.animation_data.action_slot = act.slots[0] if len(act.slots) else None
    except Exception:
        pass
    for f in [0, 6, 12, 18, 24, 30, 36, 42, 48]:
        bpy.context.scene.frame_set(f)
        bpy.context.view_layer.update()
        print("-- frame", f)
        for nm in ("hand_R", "hand_L", "weapon", "head", "jaw", "toe_R", "toe_L"):
            pb = arm.pose.bones.get(nm)
            if pb:
                print("   ", nm, tuple(round(v, 3) for v in pb.head), "->", tuple(round(v, 3) for v in pb.tail))
