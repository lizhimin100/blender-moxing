"""prev_unit.py —— 精模单位的**快速预览**（不走 glb，内存里直接建 + 出图）

比 qc_unit.py 快一倍：省掉导出/导入，分辨率降到 560，只出 4 个机位。
造型迭代时用它；验收出图仍用 qc_unit.py（它才是六机位 + 96 px 口径）。

用法：
  blender -b --factory-startup --python 库/prev_unit.py -- <unit_dir> <module_name> <outdir> [tag] [--wire]
"""
import importlib
import math
import os
import sys

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
UNIT_DIR = os.path.abspath(argv[0])
MOD = argv[1]
OUT = os.path.abspath(argv[2])
TAG = argv[3] if len(argv) > 3 else MOD
RES = int(argv[argv.index("--res") + 1]) if "--res" in argv else 760

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, UNIT_DIR)
import unitkit2 as K  # noqa: E402

if MOD in sys.modules:
    importlib.reload(sys.modules[MOD])
U = importlib.import_module(MOD)

os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.fps = 30
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.fps = 30

u = U.build(low=False)
objs = u.finish(prefix=U.PREFIX, join_by="module")
arm = U.build_rig()
u.bind(arm, objs)

tris, mn, mx = K.stats(objs)
print("[tris]", tris, "size", tuple(round(mx[i] - mn[i], 3) for i in range(3)),
      "zmin %.4f" % mn.z)
print(U.report())
for o in objs:
    o.data.calc_loop_triangles()
    print("   %-14s %6d  %s" % (o.name, len(o.data.loop_triangles),
                                [m.name for m in o.data.materials if m]))

scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = RES
scene.render.resolution_y = RES
scene.render.film_transparent = False
scene.render.image_settings.file_format = "PNG"
scene.view_settings.view_transform = "Standard"
scene.eevee.taa_render_samples = 24

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


add_light("key", (-2.6, 3.2, 3.6), 620, 3.2, (1.0, 0.96, 0.90))
add_light("fill", (3.4, 1.8, 1.9), 200, 3.6, (0.80, 0.88, 1.0))
add_light("rim", (0.8, -3.6, 2.6), 420, 2.6, (1.0, 0.90, 0.80))

bpy.ops.mesh.primitive_plane_add(size=24, location=(0, 0, -0.003))
gm = bpy.data.materials.new("ground")
gm.use_nodes = True
gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.10, 0.11, 0.10, 1)
gm.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.94
bpy.context.object.data.materials.append(gm)

cam_data = bpy.data.cameras.new("cam")
cam_data.type = "ORTHO"
cam = bpy.data.objects.new("cam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
H = mx.z - mn.z
cam_data.ortho_scale = H * 1.24


def shoot(name, azim, elev, scale=None, res=None):
    t = Vector((0, 0, H * 0.50))
    a = math.radians(azim)
    e = math.radians(elev)
    cam.location = t + Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e),
                               math.sin(e))) * 9.0
    cam.rotation_euler = (t - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam_data.ortho_scale = scale or H * 1.24
    scene.render.resolution_x = scene.render.resolution_y = res or RES
    scene.render.filepath = os.path.join(OUT, "%s_%s.png" % (TAG, name))
    bpy.ops.render.render(write_still=True)
    print("[shot]", scene.render.filepath)


shoot("front", 180, 3)
shoot("side", 90, 3)
shoot("iso", 218, 20)
shoot("rts", 218, 40, scale=H * 1.40)
shoot("rts96", 218, 40, scale=H * 1.40, res=160)
print("[done]", TAG)
