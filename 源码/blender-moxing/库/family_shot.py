"""family_shot.py —— 把若干 GLB 并排摆开出一张"全家福"（美术检查用）

用法：
  blender -b --factory-startup --python 库/family_shot.py -- <out.png> <glb1> <glb2> ...
"""
import math
import os
import sys

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = os.path.abspath(argv[0])
PATHS = [os.path.abspath(p) for p in argv[1:]]

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.fps = 30
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 1500
scene.render.resolution_y = 760
scene.render.film_transparent = False
scene.render.image_settings.file_format = "PNG"
scene.view_settings.view_transform = "Standard"
scene.eevee.taa_render_samples = 48

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


def add_light(name, loc, energy, size, color, aim=(0, 0, 1.0)):
    d = bpy.data.lights.new(name, "AREA")
    d.energy = energy
    d.size = size
    d.color = color
    ob = bpy.data.objects.new(name, d)
    scene.collection.objects.link(ob)
    ob.location = loc
    ob.rotation_euler = (Vector(aim) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()


add_light("key", (-3.4, 4.0, 4.4), 1150, 4.0, (1.0, 0.96, 0.90))
add_light("fill", (4.2, 2.4, 2.4), 380, 4.4, (0.80, 0.88, 1.0))
add_light("rim", (1.0, -4.6, 3.2), 780, 3.2, (1.0, 0.90, 0.80))

bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, -0.004))
gm = bpy.data.materials.new("ground")
gm.use_nodes = True
gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.10, 0.11, 0.10, 1)
gm.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.94
bpy.context.object.data.materials.append(gm)

# 导入并排开（间距按各自的包围盒算）
total = 0.0
boxes = []
for p in PATHS:
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=p)
    added = [o for o in bpy.data.objects if o not in before]
    meshes = [o for o in added if o.type == "MESH"
              and not any(c.name == "glTF_not_exported" for c in o.users_collection)]
    roots = [o for o in added if o.parent is None and o.type in ("EMPTY", "ARMATURE")]
    mn = Vector((1e9,) * 3)
    mx = Vector((-1e9,) * 3)
    for ob in meshes:
        for v in ob.data.vertices:
            w = ob.matrix_world @ v.co
            for i in range(3):
                mn[i] = min(mn[i], w[i])
                mx[i] = max(mx[i], w[i])
    boxes.append((roots, mn, mx))
    total += (mx.x - mn.x) + 0.36

x = -total * 0.5
for roots, mn, mx in boxes:
    dx = x - mn.x
    for ob in roots:
        ob.location.x += dx
    x += (mx.x - mn.x) + 0.36

H = max(mx.z for _, _, mx in boxes)
cam_data = bpy.data.cameras.new("cam")
cam_data.type = "ORTHO"
cam_data.ortho_scale = total * 1.06
cam = bpy.data.objects.new("cam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
t = Vector((0, 0, H * 0.46))
az, el = math.radians(206), math.radians(16)
cam.location = t + Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el),
                           math.sin(el))) * 18.0
cam.rotation_euler = (t - cam.location).to_track_quat("-Z", "Y").to_euler()

os.makedirs(os.path.dirname(OUT), exist_ok=True)
scene.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print("[family]", OUT)
