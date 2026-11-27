"""prev_vox.py —— 格网单位的快速预览（内存里直接建 + 出图，不走 glb）

用法：
  blender -b --factory-startup --python 库/prev_vox.py -- <unit_dir> <module> <outdir> [tag]
  可选：--res 760  --pose idle:20（先套一帧动作再拍）

产物：<outdir>/<tag>_front|side|iso|rts|rts96|back|top.png
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
TAG = argv[3] if len(argv) > 3 and not argv[3].startswith("--") else MOD
RES = int(argv[argv.index("--res") + 1]) if "--res" in argv else 760
POSE = argv[argv.index("--pose") + 1] if "--pose" in argv else None
SHOTS = argv[argv.index("--shots") + 1].split(",") if "--shots" in argv else \
    ["front", "side", "iso", "rts", "rts96", "back", "top"]

for _p in (os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "库"), UNIT_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import voxbase as V  # noqa: E402

if MOD in sys.modules:
    importlib.reload(sys.modules[MOD])
U = importlib.import_module(MOD)

os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.fps = 30

g = U.build()
ob = g.build(prefix=getattr(U, "PREFIX", "vox"))
arm = g.build_rig("RIG_" + g.name)
g.bind(arm, ob)
g.bake_preview(ob)
g.report()

if POSE:
    import anims_lib as PLib  # noqa: E402

    A_ = importlib.import_module("anims_" + getattr(U, "NAME", MOD))
    A_.build_all(arm)

# 描边（只在预览 / 图标里）
outline = argv.index("--no-outline") if "--no-outline" in argv else -1
if outline < 0:
    V.outline(ob, 0.010, arm=arm)

ob.data.calc_loop_triangles()
print("[tris]", len(ob.data.loop_triangles))
zs = [(ob.matrix_world @ v.co).z for v in ob.data.vertices]
xs = [(ob.matrix_world @ v.co).x for v in ob.data.vertices]
ys = [(ob.matrix_world @ v.co).y for v in ob.data.vertices]
H = max(zs) - min(zs)
print("[bbox] x %.3f..%.3f  y %.3f..%.3f  z %.3f..%.3f" %
      (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)))

scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = RES
scene.render.resolution_y = RES
scene.view_settings.view_transform = "Standard"
scene.render.film_transparent = True
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
try:
    scene.eevee.taa_render_samples = 24
except Exception:
    pass

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
ramp.color_ramp.elements[0].color = (0.085, 0.095, 0.110, 1)
ramp.color_ramp.elements[1].position = 1.0
ramp.color_ramp.elements[1].color = (0.42, 0.47, 0.54, 1)
mapn.inputs["Rotation"].default_value = (math.radians(90), 0, 0)
nt.links.new(texc.outputs["Generated"], mapn.inputs["Vector"])
nt.links.new(mapn.outputs["Vector"], tex.inputs["Vector"])
nt.links.new(tex.outputs["Fac"], ramp.inputs["Fac"])
nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
bg.inputs["Strength"].default_value = 0.9
nt.links.new(bg.outputs["Background"], wout.inputs["Surface"])


def add_light(name, loc, energy, size, color, aim=(0, 0, 0.95)):
    d = bpy.data.lights.new(name, "AREA")
    d.energy = energy
    d.size = size
    d.color = color
    ob_ = bpy.data.objects.new(name, d)
    scene.collection.objects.link(ob_)
    ob_.location = loc
    ob_.rotation_euler = (Vector(aim) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()


add_light("key", (-2.6, 3.2, 3.6), 700, 3.0, (1.0, 0.96, 0.90))
add_light("fill", (3.4, 1.8, 1.9), 240, 3.6, (0.80, 0.88, 1.0))
add_light("rim", (0.8, -3.6, 2.6), 520, 2.4, (1.0, 0.90, 0.80))

bpy.ops.mesh.primitive_plane_add(size=24, location=(0, 0, -0.004))
gm = bpy.data.materials.new("ground")
gm.use_nodes = True
gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.12, 0.13, 0.12, 1)
gm.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.94
bpy.context.object.data.materials.append(gm)

cam_data = bpy.data.cameras.new("cam")
cam_data.type = "ORTHO"
cam = bpy.data.objects.new("cam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam


def shoot(name, azim, elev, scale=None, res=None, center=None, fit=None):
    t = Vector((0, 0, (fit or H) * 0.50)) if center is None else Vector(center)
    a = math.radians(azim)
    e = math.radians(elev)
    cam.location = t + Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e),
                               math.sin(e))) * 9.0
    cam.rotation_euler = (t - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam_data.ortho_scale = scale or max(H, 1.2) * 1.16
    scene.render.resolution_x = scene.render.resolution_y = res or RES
    scene.render.filepath = os.path.join(OUT, "%s_%s.png" % (TAG, name))
    bpy.ops.render.render(write_still=True)
    print("[shot]", scene.render.filepath)


for s in SHOTS:
    if s == "front":
        shoot("front", 180, 2)
    elif s == "back":
        shoot("back", 0, 2)
    elif s == "side":
        shoot("side", 90, 2)
    elif s == "iso":
        shoot("iso", 218, 18)
    elif s == "rts":
        shoot("rts", 218, 38, scale=max(H, 1.2) * 1.34)
    elif s == "rts96":
        shoot("rts96", 218, 38, scale=max(H, 1.2) * 1.34, res=150)
    elif s == "top":
        shoot("top", 180, 78, scale=max(H, 1.2) * 1.16)

# 动作定格：--pose attack:10,14,18  → 每帧一张 iso + 一张侧视
if POSE:
    act, frames = POSE.split(":")
    for fr in [int(x) for x in frames.split(",")]:
        A_.pose_at(arm, act, fr)
        shoot("%s_%03d_iso" % (act, fr), 218, 18)
        shoot("%s_%03d_side" % (act, fr), 90, 6)
    A_.pose_at(arm, act, 0)
print("[done]", TAG)
