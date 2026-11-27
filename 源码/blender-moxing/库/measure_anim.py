"""measure_anim.py —— 量动作幅度与手/武器漂移。

用法：blender -b --factory-startup --python 库/measure_anim.py -- <glb> <action> <bone>
输出：每帧 bone 尾端世界坐标（m），并给出总位移 / 包围盒。
"""
import sys
import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
GLB, ACT, BONE = argv[0], argv[1], argv[2]
EXTRA = argv[3] if len(argv) > 3 else None

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.render.fps = 30
bpy.ops.import_scene.gltf(filepath=GLB)
arm = [o for o in bpy.context.scene.objects if o.type == "ARMATURE"][0]
act = bpy.data.actions.get(ACT)
arm.animation_data_create(); arm.animation_data.action = act
try:
    arm.animation_data.action_slot = act.slots[0]
except Exception:
    pass
a, b = int(act.frame_range[0]), int(act.frame_range[1])
pts = []
for f in range(a, b + 1):
    bpy.context.scene.frame_set(f)
    bpy.context.view_layer.update()
    pb = arm.pose.bones.get(BONE)
    pts.append(pb.tail.copy())
mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
travel = sum((pts[i] - pts[i - 1]).length for i in range(1, len(pts)))
print("ACTION", ACT, "frames", a, b, "bone", BONE)
print("  bbox", tuple(round(v, 3) for v in mn), tuple(round(v, 3) for v in mx))
print("  span", tuple(round(mx[i] - mn[i], 3) for i in range(3)), "pathlen", round(travel, 3))
for f, p in zip(range(a, b + 1), pts):
    print("   f%03d %7.3f %7.3f %7.3f" % (f, p.x, p.y, p.z))
if EXTRA:
    print("  extra: distance to", EXTRA)
    ds = []
    for f in range(a, b + 1):
        bpy.context.scene.frame_set(f)
        bpy.context.view_layer.update()
        p1 = arm.pose.bones[BONE].tail
        p2 = arm.pose.bones[EXTRA].head
        ds.append((p1 - p2).length)
    print("   min %.4f max %.4f mean %.4f" % (min(ds), max(ds), sum(ds) / len(ds)))
