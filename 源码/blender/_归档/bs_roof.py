"""bs_roof.py —— 屋顶/屋脊近景诊断（看清上部的穿模）"""
import importlib, math, os, sys
import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else r"D:/测试一/blender/bs_v6"
ROOT = r"D:/测试一"
OUT = os.path.join(ROOT, "docs", "_wip")
if HERE not in sys.path:
    sys.path.insert(0, HERE)
for mod in ("bslib", "bs_model"):
    if mod in sys.modules:
        importlib.reload(sys.modules[mod])
import bslib, bs_model  # noqa


def clear_scene():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for blk in (bpy.data.meshes, bpy.data.materials, bpy.data.images, bpy.data.cameras,
                bpy.data.lights, bpy.data.collections):
        for it in list(blk):
            try:
                blk.remove(it)
            except Exception:
                pass


def setup_world():
    w = bpy.data.worlds.new("W")
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Color"].default_value = (0.32, 0.38, 0.46, 1)
    bg.inputs["Strength"].default_value = 1.1
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])


def add_area(loc, energy, size, color, aim):
    d = bpy.data.lights.new("a", "AREA")
    d.energy, d.size, d.color = energy, size, color
    ob = bpy.data.objects.new("a", d)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    ob.rotation_euler = (Vector(aim) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()


def shot(name, target, span, az, el):
    cam = bpy.data.cameras.new("C")
    cam.type = "ORTHO"
    cam.ortho_scale = span
    ob = bpy.data.objects.new("C", cam)
    bpy.context.scene.collection.objects.link(ob)
    a, e = math.radians(az), math.radians(el)
    r = 40.0
    ob.location = Vector(target) + Vector((math.sin(a) * math.cos(e) * r,
                                           math.cos(a) * math.cos(e) * r,
                                           math.sin(e) * r))
    ob.rotation_euler = (Vector(target) - ob.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = ob
    sc = bpy.context.scene
    sc.render.resolution_x = sc.render.resolution_y = 900
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    sc.view_settings.view_transform = "AgX"
    for look in ("AgX - Punchy", "AgX - Medium High Contrast"):
        try:
            sc.view_settings.look = look
            break
        except Exception:
            continue
    sc.view_settings.exposure = 0.45
    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            sc.render.engine = eng
            break
        except TypeError:
            continue
    ee = getattr(sc, "eevee", None)
    if ee is not None and hasattr(ee, "taa_render_samples"):
        ee.taa_render_samples = 24
    sc.render.filepath = os.path.join(OUT, name)
    bpy.ops.render.render(write_still=True)
    print("[render]", name)
    bpy.data.objects.remove(ob, do_unlink=True)


def main():
    os.makedirs(OUT, exist_ok=True)
    clear_scene()
    objs, st = bs_model.build(smooth=True)
    print("STATS", st)
    setup_world()
    add_area((-14, 14, 22), 5200, 9, (1.0, 0.94, 0.85), (0, 0, 7))
    add_area((12, -10, 14), 1600, 12, (0.62, 0.76, 1.0), (0, 0, 7))
    shot("roof_ridge.png", (-0.2, 2.2, 9.0), 5.2, az=-24, el=16)
    shot("roof_cupola.png", (0, -1.5, 9.3), 3.4, az=-30, el=22)
    shot("roof_chimney.png", (3.2, 4.0, 9.2), 3.6, az=-12, el=10)
    shot("roof_flue.png", (-0.3, 5.0, 6.4), 3.6, az=-20, el=14)
    shot("roof_top.png", (0, 0.0, 5.0), 13.0, az=-35, el=52)
    shot("anvil_close.png", (0.10, 6.9, 1.0), 3.0, az=-22, el=14)
    print("DONE")


main()
