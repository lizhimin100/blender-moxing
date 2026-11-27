"""qc_glb.py —— 导入一个 GLB，按固定机位出对照图 + 打印结构信息。

用法：
    blender -b --factory-startup --python 库/qc_glb.py -- <glb> <outdir> [tag]

机位：front(+Y) / side(+X) / top / iso / rts(40°俯角)。
动作条：可选，用 --anim <name> --frames 6 出连续帧。
"""
import os
import sys
import math
import json

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
GLB = argv[0]
OUT = os.path.abspath(argv[1])
TAG = argv[2] if len(argv) > 2 else os.path.splitext(os.path.basename(GLB))[0]
ANIM = None
NFRAMES = 6
if "--anim" in argv:
    ANIM = argv[argv.index("--anim") + 1]
if "--frames" in argv:
    NFRAMES = int(argv[argv.index("--frames") + 1])

os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)
if "--rest" in argv:
    for _a in [o for o in bpy.context.scene.objects if o.type == "ARMATURE"]:
        for _pb in _a.pose.bones:
            _pb.matrix_basis.identity()
    bpy.context.view_layer.update()

for o in list(bpy.context.scene.objects):
    if o.type == "MESH" and o.name.startswith("Icosphere"):
        bpy.data.objects.remove(o, do_unlink=True)
objs = [o for o in bpy.context.scene.objects if o.type == "MESH"]
arms = [o for o in bpy.context.scene.objects if o.type == "ARMATURE"]
print("== objects ==")
for o in bpy.context.scene.objects:
    print("  ", o.type, o.name, "verts", len(o.data.vertices) if o.type == "MESH" else "")
if arms:
    a = arms[0]
    print("== bones ==", len(a.data.bones))
    for b in a.data.bones:
        print("   ", b.name, "head", tuple(round(v, 4) for v in b.head_local),
              "parent", b.parent.name if b.parent else None)

# bbox
mn = Vector((1e9, 1e9, 1e9)); mx = Vector((-1e9, -1e9, -1e9))
for o in objs:
    for c in o.bound_box:
        p = o.matrix_world @ Vector(c)
        for i in range(3):
            mn[i] = min(mn[i], p[i]); mx[i] = max(mx[i], p[i])
print("== bbox ==", "min", tuple(round(v, 3) for v in mn), "max", tuple(round(v, 3) for v in mx),
      "size", tuple(round(mx[i] - mn[i], 3) for i in range(3)))
tris = 0
for o in objs:
    o.data.calc_loop_triangles()
    tris += len(o.data.loop_triangles)
    print("  mesh", o.name, "tris", len(o.data.loop_triangles), "mats", [m.name for m in o.data.materials],
          "vg", len(o.vertex_groups))
print("== tris ==", tris)

# scene setup
scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 720
scene.render.resolution_y = 720
scene.render.film_transparent = False
scene.render.image_settings.file_format = "PNG"
scene.view_settings.view_transform = "Standard"
scene.view_settings.look = "None"
scene.view_settings.exposure = 0.0
world = bpy.data.worlds.new("W") if not bpy.data.worlds else bpy.data.worlds[0]
scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.055, 0.06, 0.065, 1)
world.node_tree.nodes["Background"].inputs[1].default_value = 1.0

# three-point light
def add_light(name, kind, loc, energy, size=3.0, color=(1, 1, 1)):
    ld = bpy.data.lights.new(name, kind)
    ld.energy = energy
    ld.color = color
    if kind == "AREA":
        ld.size = size
    ob = bpy.data.objects.new(name, ld)
    scene.collection.objects.link(ob)
    ob.location = loc
    d = Vector((0, 0, 0.9)) - Vector(loc)
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return ob

add_light("key", "AREA", (-3.2, 3.6, 4.4), 700, 4.0, (1.0, 0.96, 0.90))
add_light("fill", "AREA", (3.8, 2.0, 2.2), 220, 4.0, (0.82, 0.88, 1.0))
add_light("rim", "AREA", (0.6, -4.2, 3.2), 420, 3.0, (1.0, 0.93, 0.85))

# ground
bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 0, -0.002))
ground = bpy.context.object
gm = bpy.data.materials.new("ground")
gm.use_nodes = True
gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.16, 0.17, 0.14, 1)
gm.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.95
ground.data.materials.append(gm)

# camera
cam_data = bpy.data.cameras.new("cam")
cam_data.type = "ORTHO"
cam = bpy.data.objects.new("cam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
center = (mn + mx) * 0.5
height = mx.z - mn.z
cam_data.ortho_scale = height * 1.32

def shoot(name, azim, elev, dist=8.0, target=None, scale=None):
    t = Vector(target) if target else Vector((0, 0, height * 0.48))
    a = math.radians(azim); e = math.radians(elev)
    cam.location = t + Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e))) * dist
    d = t - cam.location
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    cam_data.ortho_scale = scale or height * 1.32
    scene.render.filepath = os.path.join(OUT, "%s_%s.png" % (TAG, name))
    bpy.ops.render.render(write_still=True)
    print("[shot]", scene.render.filepath)

shoot("front", 180, 4)
shoot("back", 0, 4)
shoot("side", 90, 4)
shoot("top", 0, 89, scale=max(mx.x - mn.x, mx.y - mn.y) * 1.35)
shoot("iso", 215, 22)
shoot("rts", 215, 40, scale=height * 1.45)

# animation strip
if ANIM and arms:
    arm = arms[0]
    act = bpy.data.actions.get(ANIM)
    if act is None:
        print("[warn] no action", ANIM, "have", [a.name for a in bpy.data.actions])
    else:
        arm.animation_data_create()
        arm.animation_data.action = act
        try:
            slot = act.slots[0]
            arm.animation_data.action_slot = slot
        except Exception:
            pass
        f0, f1 = act.frame_range
        print("[anim]", ANIM, f0, f1)
        for i in range(NFRAMES):
            f = int(round(f0 + (f1 - f0) * i / max(NFRAMES - 1, 1)))
            scene.frame_set(f)
            _az, _el = (215, 40) if "--rtsanim" in argv else (212, 12)
            shoot("anim%02d_f%03d" % (i, f), _az, _el, scale=height * 1.55)

print("[done]", TAG)
