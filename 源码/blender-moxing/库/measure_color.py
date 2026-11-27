"""measure_color.py —— 量可见阵营色占比 / 武器投影占比 / 剪影。

用法：
  blender -b --factory-startup --python 库/measure_color.py -- <glb> <outdir> <tag> [mode]
mode: front（默认）| rts
输出 PNG：<tag>_sil.png / <tag>_team.png / <tag>_weapon.png
"""
import os
import sys
import math

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
GLB, OUT, TAG = argv[0], os.path.abspath(argv[1]), argv[2]
MODE = argv[3] if len(argv) > 3 else "front"
ANIM = argv[4] if len(argv) > 4 else None
os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)
for o in list(bpy.context.scene.objects):
    if o.type == "MESH" and o.name.startswith("Icosphere"):
        bpy.data.objects.remove(o, do_unlink=True)

meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
if ANIM:
    _arm = [o for o in bpy.context.scene.objects if o.type == "ARMATURE"][0]
    _act = bpy.data.actions.get(ANIM)
    _arm.animation_data_create(); _arm.animation_data.action = _act
    try:
        _arm.animation_data.action_slot = _act.slots[0]
    except Exception:
        pass
    bpy.context.scene.frame_set(0)
scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 512
scene.render.resolution_y = 512
scene.render.film_transparent = False
scene.view_settings.view_transform = "Standard"
scene.view_settings.look = "None"
scene.view_settings.exposure = 0.0
world = bpy.data.worlds.new("W")
scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0, 0, 0, 1)
world.node_tree.nodes["Background"].inputs[1].default_value = 0.0

# bbox
mn = Vector((1e9,) * 3); mx = Vector((-1e9,) * 3)
for o in meshes:
    for c in o.bound_box:
        p = o.matrix_world @ Vector(c)
        for i in range(3):
            mn[i] = min(mn[i], p[i]); mx[i] = max(mx[i], p[i])
height = mx.z - mn.z

cam_data = bpy.data.cameras.new("c")
cam_data.type = "ORTHO"
cam_data.ortho_scale = height * 1.18
cam = bpy.data.objects.new("c", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
t = Vector((0, 0, height * 0.5))
if MODE == "rts":
    a, e = math.radians(215), math.radians(40)
    cam.location = t + Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e))) * 8
else:
    cam.location = t + Vector((0, 8, 0))
cam.rotation_euler = (t - cam.location).to_track_quat("-Z", "Y").to_euler()


def emat(name, rgb):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*rgb, 1.0)
    em.inputs["Strength"].default_value = 1.0
    nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
    return m


WHITE = emat("__white", (1, 1, 1))
BLACK = emat("__black", (0, 0, 0))

# 记住原来的材质
orig = {o.name: list(o.data.materials) for o in meshes}


def apply(white_names):
    for o in meshes:
        use_white = any(k in o.name for k in white_names)
        o.data.materials.clear()
        o.data.materials.append(WHITE if use_white else BLACK)


def shoot(name):
    scene.render.filepath = os.path.join(OUT, "%s_%s.png" % (TAG, name))
    bpy.ops.render.render(write_still=True)
    print("[shot]", scene.render.filepath)


apply(("unit_team", "unit_trim", "unit_tribe"))
shoot("team")
apply(("unit_weapon",))
shoot("weapon")
apply(("unit_body", "unit_team", "unit_trim", "unit_weapon", "unit_eye", "unit_tribe"))
shoot("sil")

# 恢复（不保存，只是好习惯）
for o in meshes:
    o.data.materials.clear()
    for m in orig[o.name]:
        o.data.materials.append(m)
print("[done]", TAG, MODE)
