"""unit_shot.py —— 单位动作出图（迭代专用：一次跑多条动作、多机位）

    blender -b --factory-startup --python 库/unit_shot.py -- \
        <unit_dir> <unit_module> <anims_module> <outdir> \
        [--actions idle,walk] [--n 5] [--frames 0,10,20] [--az 200] [--el 8] \
        [--scale 1.34] [--res 520] [--rts] [--close x,y,z,s] [--tag p]

两种接入方式都支持（有 load() 用 load，否则 build()）。
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
        i = argv.index(name) + 1
        return argv[i] if i < len(argv) else True
    return default


UNIT_DIR = os.path.abspath(argv[0])
UMOD, AMOD = argv[1], argv[2]
OUT = os.path.abspath(argv[3])
ACTIONS = [s for s in str(flag("--actions", "idle")).split(",") if s]
NF = int(flag("--n", 5))
FRAMES = [int(v) for v in str(flag("--frames", "")).split(",") if v.strip()]
AZ = float(flag("--az", 200))
EL = float(flag("--el", 8))
SCALE = float(flag("--scale", 1.34))
RES = int(flag("--res", 520))
TAG = str(flag("--tag", ""))
CLOSE = flag("--close", None)
WIDE = float(flag("--wide", 1.0))

HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (HERE, UNIT_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.fps = 30
for _m in ("unitkit", "unitkit2", "gnoll_kit", "gnoll_kit2", "poselib2",
           "anims_human", UMOD, AMOD, "human_kit2"):
    if _m in sys.modules:
        importlib.reload(sys.modules[_m])
U = importlib.import_module(UMOD)
A = importlib.import_module(AMOD)

if hasattr(U, "load"):
    root, arm, meshes = U.load()
    objs = list(meshes)
else:
    u = U.build(low=False)
    objs = u.finish(prefix=U.PREFIX, join_by="module")
    arm = U.build_rig()
    u.bind(arm, objs)

if hasattr(A, "build_all"):
    A.build_all(arm)
else:
    A.build(arm)
print("[actions]", [a.name for a in bpy.data.actions])

mn = Vector((1e9,) * 3)
mx = Vector((-1e9,) * 3)
for o in objs:
    for v in o.data.vertices:
        p = o.matrix_world @ v.co
        for i in range(3):
            mn[i] = min(mn[i], p[i])
            mx[i] = max(mx[i], p[i])
H = mx.z - mn.z

os.makedirs(OUT, exist_ok=True)
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = scene.render.resolution_y = RES
scene.render.film_transparent = False
scene.render.image_settings.file_format = "PNG"
scene.view_settings.view_transform = "Standard"
scene.eevee.taa_render_samples = 20

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


def shoot(name, az, el, scale=None, target=None, res=None):
    t = Vector(target) if target else Vector((0, 0.02, H * 0.48))
    a, e = math.radians(az), math.radians(el)
    cam.location = t + Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e),
                               math.sin(e))) * 14.0
    cam.rotation_euler = (t - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam_data.ortho_scale = (scale or H * SCALE) * WIDE
    if res:
        scene.render.resolution_x, scene.render.resolution_y = res
    else:
        scene.render.resolution_x = scene.render.resolution_y = RES
    scene.render.filepath = os.path.join(OUT, "%s.png" % name)
    bpy.ops.render.render(write_still=True)


arm.animation_data_create()
for act_name in ACTIONS:
    act = bpy.data.actions.get(act_name)
    if act is None:
        print("[warn] no action", act_name)
        continue
    arm.animation_data.action = act
    try:
        arm.animation_data.action_slot = act.slots[0]
    except Exception:
        pass
    f0, f1 = (int(round(v)) for v in act.frame_range)
    if FRAMES:
        frames = FRAMES
    else:
        frames = [int(round(f0 + (f1 - f0) * i / max(NF - 1, 1))) for i in range(NF)]
    pre = (TAG + "_" if TAG else "") + act_name
    for f in frames:
        scene.frame_set(f)
        bpy.context.view_layer.update()
        shoot("%s_f%03d_az%d" % (pre, f, int(AZ)), AZ, EL)
        shoot("%s_f%03d_side" % (pre, f), 90, 4)
        if CLOSE:
            x, y, z, s = [float(v) for v in str(CLOSE).split(",")]
            shoot("%s_f%03d_close" % (pre, f), 205, 12, scale=s, target=(x, y, z))
        if "--rts" in argv:
            shoot("%s_f%03d_rts" % (pre, f), 218, 40, scale=H * 1.42,
                  res=(150, 150))
    print("[ok]", act_name, frames)

arm.animation_data.action = None
print("[done]")
