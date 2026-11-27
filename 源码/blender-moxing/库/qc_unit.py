"""qc_unit.py —— 单位出图（精模口径：有环境光，金属才不发黑）

用法：
  blender -b --factory-startup --python 库/qc_unit.py -- <glb> <outdir> [tag]
        [--anim <name> --frames 6] [--rtsanim] [--rest]

机位：front(+Y) / back / side / iso / rts(40°俯角) / top / rts96（缩到 96 px 高）
"""
import os
import sys
import math

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
GLB = argv[0]
OUT = os.path.abspath(argv[1])
TAG = argv[2] if len(argv) > 2 else os.path.splitext(os.path.basename(GLB))[0]
ANIM = argv[argv.index("--anim") + 1] if "--anim" in argv else None
NFRAMES = int(argv[argv.index("--frames") + 1]) if "--frames" in argv else 6
os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.render.fps = 30
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
mn = Vector((1e9, 1e9, 1e9))
mx = Vector((-1e9, -1e9, -1e9))
tris = 0
for o in objs:
    o.data.calc_loop_triangles()
    tris += len(o.data.loop_triangles)
    for v in o.data.vertices:
        p = o.matrix_world @ v.co
        for i in range(3):
            mn[i] = min(mn[i], p[i])
            mx[i] = max(mx[i], p[i])
print("== bbox ==", tuple(round(v, 3) for v in mn), tuple(round(v, 3) for v in mx),
      "size", tuple(round(mx[i] - mn[i], 3) for i in range(3)))
print("== tris ==", tris, "meshes", len(objs), "bones",
      len(arms[0].data.bones) if arms else 0)
for o in objs:
    print("   mesh", o.name, len(o.data.loop_triangles), [m.name for m in o.data.materials])

scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 760
scene.render.resolution_y = 760
scene.render.film_transparent = False
scene.render.image_settings.file_format = "PNG"
scene.view_settings.view_transform = "Standard"
scene.view_settings.look = "None"
scene.eevee.taa_render_samples = 32

# 环境：冷灰竖向渐变（金属靠它出层次，不靠灯）
world = bpy.data.worlds.new("W")
scene.world = world
world.use_nodes = True
nt = world.node_tree
nt.nodes.clear()
wout = nt.nodes.new("ShaderNodeOutputWorld")
bg = nt.nodes.new("ShaderNodeBackground")
ramp = nt.nodes.new("ShaderNodeValToRGB")
tex = nt.nodes.new("ShaderNodeTexGradient")
mapn = nt.nodes.new("ShaderNodeMapping")
texc = nt.nodes.new("ShaderNodeTexCoord")
ramp.color_ramp.elements[0].position = 0.0
ramp.color_ramp.elements[0].color = (0.075, 0.085, 0.100, 1)
ramp.color_ramp.elements[1].position = 1.0
ramp.color_ramp.elements[1].color = (0.46, 0.52, 0.60, 1)
mapn.inputs["Rotation"].default_value = (math.radians(90), 0, 0)
nt.links.new(texc.outputs["Generated"], mapn.inputs["Vector"])
nt.links.new(mapn.outputs["Vector"], tex.inputs["Vector"])
nt.links.new(tex.outputs["Fac"], ramp.inputs["Fac"])
nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
bg.inputs["Strength"].default_value = 0.85
nt.links.new(bg.outputs["Background"], wout.inputs["Surface"])


def add_light(name, loc, energy, size, color, aim=(0, 0, 0.95)):
    d = bpy.data.lights.new(name, "AREA")
    d.energy = energy
    d.size = size
    d.color = color
    ob = bpy.data.objects.new(name, d)
    scene.collection.objects.link(ob)
    ob.location = loc
    ob.rotation_euler = (Vector(aim) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return ob


add_light("key", (-2.6, 3.2, 3.6), 620, 3.2, (1.0, 0.96, 0.90))
add_light("fill", (3.4, 1.8, 1.9), 200, 3.6, (0.80, 0.88, 1.0))
add_light("rim", (0.8, -3.6, 2.6), 420, 2.6, (1.0, 0.90, 0.80))

bpy.ops.mesh.primitive_plane_add(size=24, location=(0, 0, -0.003))
ground = bpy.context.object
gm = bpy.data.materials.new("ground")
gm.use_nodes = True
gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.10, 0.11, 0.10, 1)
gm.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.94
ground.data.materials.append(gm)

cam_data = bpy.data.cameras.new("cam")
cam_data.type = "ORTHO"
cam = bpy.data.objects.new("cam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
height = mx.z - mn.z
cam_data.ortho_scale = height * 1.28


def shoot(name, azim, elev, dist=9.0, scale=None, res=None, target=None):
    t = Vector(target) if target else Vector((0, 0, height * 0.50))
    a = math.radians(azim)
    e = math.radians(elev)
    cam.location = t + Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e),
                               math.sin(e))) * dist
    cam.rotation_euler = (t - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam_data.ortho_scale = scale or height * 1.28
    if res:
        scene.render.resolution_x, scene.render.resolution_y = res
    else:
        scene.render.resolution_x = scene.render.resolution_y = 760
    scene.render.filepath = os.path.join(OUT, "%s_%s.png" % (TAG, name))
    bpy.ops.render.render(write_still=True)
    print("[shot]", scene.render.filepath)


shoot("front", 180, 3)
shoot("back", 0, 3)
shoot("side", 90, 3)
shoot("iso", 218, 22)
shoot("rts", 218, 40, scale=height * 1.42)
shoot("top", 0, 89, scale=max(mx.x - mn.x, mx.y - mn.y) * 1.30)
shoot("rts96", 218, 40, scale=height * 1.42, res=(150, 150))

if ANIM and arms:
    arm = arms[0]
    act = bpy.data.actions.get(ANIM)
    if act is None:
        print("[warn] no action", ANIM, "have", [a.name for a in bpy.data.actions])
    else:
        arm.animation_data_create()
        arm.animation_data.action = act
        try:
            arm.animation_data.action_slot = act.slots[0]
        except Exception:
            pass
        f0, f1 = act.frame_range
        for i in range(NFRAMES):
            f = int(round(f0 + (f1 - f0) * i / max(NFRAMES - 1, 1)))
            scene.frame_set(f)
            az, el = (218, 40) if "--rtsanim" in argv else (212, 10)
            sc = height * (2.30 if "--wide" in argv else 1.55)
            shoot("anim%02d_f%03d" % (i, f), az, el, scale=sc,
                  target=(0, 0.45 if "--wide" in argv else 0, height * 0.50))

print("[done]", TAG)
