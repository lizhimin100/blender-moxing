"""closeup_anim.py —— 固定机位放大看某个部位在各动作帧的变化。

用法：
  blender -b --factory-startup --python 库/closeup_anim.py -- <glb> <outdir> <tag> <anim> <x> <y> <z> <scale>
"""
import os
import sys
import math
import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
GLB, OUT, TAG, ANIM = argv[0], os.path.abspath(argv[1]), argv[2], argv[3]
TX, TY, TZ, SCALE = (float(v) for v in argv[4:8])
N = int(argv[8]) if len(argv) > 8 else 8
os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)
for o in list(bpy.context.scene.objects):
    if o.type == "MESH" and o.name.startswith("Icosphere"):
        bpy.data.objects.remove(o, do_unlink=True)

scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 640
scene.render.resolution_y = 640
scene.view_settings.view_transform = "Standard"
world = bpy.data.worlds.new("W") if not bpy.data.worlds else bpy.data.worlds[0]
scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.05, 0.055, 0.06, 1)

def light(name, loc, e, size=2.0):
    ld = bpy.data.lights.new(name, "AREA"); ld.energy = e; ld.size = size
    ob = bpy.data.objects.new(name, ld); scene.collection.objects.link(ob); ob.location = loc
    ob.rotation_euler = (Vector((TX, TY, TZ)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()

light("k", (TX - 1.6, TY + 2.0, TZ + 2.2), 300, 2.2)
light("f", (TX + 2.0, TY + 1.0, TZ + 0.8), 90, 2.5)
light("r", (TX + 0.4, TY - 2.2, TZ + 1.6), 180, 2.0)

cd = bpy.data.cameras.new("c"); cd.type = "ORTHO"; cd.ortho_scale = SCALE
cam = bpy.data.objects.new("c", cd); scene.collection.objects.link(cam); scene.camera = cam
t = Vector((TX, TY, TZ))
cam.location = t + Vector((math.sin(math.radians(215)) * 0.8, -math.cos(math.radians(215)) * 0.8, 0.35)) * 5
cam.rotation_euler = (t - cam.location).to_track_quat("-Z", "Y").to_euler()

arm = [o for o in scene.objects if o.type == "ARMATURE"][0]
act = bpy.data.actions.get(ANIM)
arm.animation_data_create(); arm.animation_data.action = act
try:
    arm.animation_data.action_slot = act.slots[0] if hasattr(act, "slots") and len(act.slots) else None
except Exception:
    pass
f0, f1 = act.frame_range
print("[range]", f0, f1)
for i in range(N):
    f = int(round(f0 + (f1 - f0) * i / max(N - 1, 1)))
    scene.frame_set(f)
    scene.render.filepath = os.path.join(OUT, "%s_%s_%02d_f%03d.png" % (TAG, ANIM, i, f))
    bpy.ops.render.render(write_still=True)
    print("[saved]", scene.render.filepath)
