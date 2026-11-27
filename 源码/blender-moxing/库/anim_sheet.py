"""anim_sheet.py —— 内存里建单位 + 只跑一条动作 + 逐帧出图（动作审图专用）

比 run_xxx.py 快很多（不导出 glb、不建全部动作），用来逐帧看动作。

用法：
  blender -b --factory-startup --python 库/anim_sheet.py -- \
      <unit_dir> <module> <outdir> <action> [--frames 0,17,21] [--az 200] [--el 8]
      [--res 620] [--all]   # --all = 出全部动作的首末帧对照

机位默认 200°(左前 3/4) / 8°：能同时看脚、拳、剪影。
"""
import importlib
import math
import os
import sys

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def flag(name, default=None):
    if name in argv:
        return argv[argv.index(name) + 1] if argv.index(name) + 1 < len(argv) else True
    return default


UNIT_DIR = os.path.abspath(argv[0])
MOD = argv[1]
OUT = os.path.abspath(argv[2])
ACT = argv[3] if len(argv) > 3 else "idle"
FRAMES = [int(v) for v in flag("--frames", "").split(",") if v.strip()]
AZ = float(flag("--az", 200))
EL = float(flag("--el", 8))
RES = int(flag("--res", 620))
# 倒地类动作会跑出画面：--scale 放大取景框、--ty 把取景中心往后挪（倒地朝 -Y）
SCALE_K = float(flag("--scale", 1.30))
TY = float(flag("--ty", 0.0))

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, UNIT_DIR)
import unitkit2 as K  # noqa: E402

if MOD in sys.modules:
    importlib.reload(sys.modules[MOD])
U = importlib.import_module(MOD)
for _m in ("poselib2",):
    if _m in sys.modules:
        importlib.reload(sys.modules[_m])

os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.fps = 30

u = U.build(low=False)
objs = u.finish(prefix=U.PREFIX, join_by="module")
arm = U.build_rig()
u.bind(arm, objs)
tris, mn, mx = K.stats(objs)
H = mx.z - mn.z
print("[tris]", tris, "H %.3f" % H)

import poselib2 as PL  # noqa: E402
AN = importlib.import_module("anims_" + U.NAME)
rig = PL.Rig(arm)
act = getattr(AN, "a_" + ACT)(rig)
arm.animation_data.action = act
arm.animation_data_create() if arm.animation_data is None else None
arm.animation_data.action = act
try:
    arm.animation_data.action_slot = act.slots[0]
except Exception:
    pass

scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = scene.render.resolution_y = RES
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

bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 0, -0.003))
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
cam_data.ortho_scale = H * SCALE_K


def shoot(name, az, el, scale=None, target=None):
    t = Vector(target) if target else Vector((0, TY, H * 0.50))
    a = math.radians(az)
    e = math.radians(el)
    cam.location = t + Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e),
                               math.sin(e))) * 14.0
    cam.rotation_euler = (t - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam_data.ortho_scale = scale or H * SCALE_K
    scene.render.filepath = os.path.join(OUT, "%s.png" % name)
    bpy.ops.render.render(write_still=True)
    print("[shot]", scene.render.filepath)


f0, f1 = (int(v) for v in act.frame_range)
frames = FRAMES or [int(round(f0 + (f1 - f0) * i / 5.0)) for i in range(6)]
for f in frames:
    scene.frame_set(f)
    bpy.context.view_layer.update()
    shoot("f%03d_az%d" % (f, int(AZ)), AZ, EL)
    # 侧视：看脚有没有交叉 / 前后位移
    shoot("f%03d_side" % f, 90, 4)
print("[done]", ACT, frames)
