"""icon_vox.py —— 格网单位图标：用 GLB 里的几何直接渲一张 512 透明底（不画）

用法（后台或桥接都行）：
  blender -b --factory-startup --python 库/icon_vox.py -- <unit_dir> <module> <out_png> [action] [frame]

v3 的改动（为了和 `方块人_联盟步兵_图标.png` 对齐）：
  * 机位改成 az 206° / elev 12°、正交、ortho_scale 2.05 —— 和步兵那张同一套取景，
    人物在画面里高度约 83%（步兵 96%，但他没有 2.25 m 的枪）；
  * 用 `anims_<兵种>.pose_icon()` 的**英雄姿势**（枪斜拄 / 弓斜举），
    这样长枪不会顶出画框，斜线也比竖线更像"兵"；
  * 背景透明，卡面交给 `icon_post_vox.py`（暖灰渐变 + 暗边 + 金线 = 步兵那张的规格）。
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
ACT = argv[3] if len(argv) > 3 else "icon"
FRAME = int(argv[4]) if len(argv) > 4 else 0
RES = 512
SCALE = 2.05          # 画面覆盖的世界高度（米）—— 统一口径，图标之间才"一样大"
AZ, EL = 206.0, 12.0

for _p in (os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "库"), UNIT_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import voxbase as V  # noqa: E402
import anims_lib as ALIB  # noqa: E402

for _m in ("voxbase", "poselib2", "anims_lib", "props_vox", MOD,
           "anims_" + MOD.split("unit_")[-1]):
    if _m in sys.modules:
        importlib.reload(sys.modules[_m])
U = importlib.import_module(MOD)
A = importlib.import_module("anims_" + U.NAME)

os.makedirs(os.path.dirname(OUT), exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.fps = 30

g = U.build()
ob = g.build(prefix=U.PREFIX)
arm = g.build_rig("RIG_" + U.NAME)
g.bind(arm, ob)
g.bake_preview(ob)
if ACT == "icon" and hasattr(A, "pose_icon"):
    A.pose_icon(arm)
else:
    A.build_all(arm)
    A.pose_at(arm, ACT, FRAME)
V.outline(ob, 0.010, arm=arm)

scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = scene.render.resolution_y = RES
scene.render.film_transparent = True
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.view_settings.view_transform = "Standard"
try:
    scene.eevee.taa_render_samples = 64
except Exception:
    pass

world = bpy.data.worlds.new("W")
scene.world = world
world.use_nodes = True
nt = world.node_tree
nt.nodes.clear()
wout = nt.nodes.new("ShaderNodeOutputWorld")
bg = nt.nodes.new("ShaderNodeBackground")
bg.inputs["Color"].default_value = (0.30, 0.34, 0.40, 1)
bg.inputs["Strength"].default_value = 0.75
nt.links.new(bg.outputs["Background"], wout.inputs["Surface"])


def add_light(name, loc, energy, size, color, aim=(0, 0, 0.95)):
    d = bpy.data.lights.new(name, "AREA")
    d.energy = energy
    d.size = size
    d.color = color
    o = bpy.data.objects.new(name, d)
    scene.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = (Vector(aim) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()


add_light("key", (-2.4, 3.0, 3.9), 1050, 2.6, (1.0, 0.95, 0.88))
add_light("fill", (3.4, 1.8, 1.9), 130, 3.6, (0.80, 0.88, 1.0))
add_light("rim", (0.8, -3.6, 2.6), 620, 2.2, (1.0, 0.90, 0.80))

cam_data = bpy.data.cameras.new("cam")
cam_data.type = "ORTHO"
cam = bpy.data.objects.new("cam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
t = Vector((0.0, 0.0, 0.98))
a, e = math.radians(AZ), math.radians(EL)
cam.location = t + Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e),
                           math.sin(e))) * 9.0
cam.rotation_euler = (t - cam.location).to_track_quat("-Z", "Y").to_euler()
cam_data.ortho_scale = SCALE
scene.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print("[icon]", OUT)
