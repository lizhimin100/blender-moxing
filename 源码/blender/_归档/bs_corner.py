"""bs_corner.py —— 四个檐角近景（找屋面/封檐板/山墙的对接错位）"""
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
import bs_model  # noqa


def clear_scene():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for blk in (bpy.data.meshes, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
        for it in list(blk):
            try:
                blk.remove(it)
            except Exception:
                pass


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
    try:
        sc.view_settings.look = "AgX - Punchy"
    except Exception:
        pass
    sc.view_settings.exposure = 0.55
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
    bs_model.build(smooth=True)
    w = bpy.data.worlds.new("W")
    bpy.context.scene.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Color"].default_value = (0.42, 0.46, 0.52, 1)
        bg.inputs["Strength"].default_value = 1.2
    add_area((-14, 16, 14), 4200, 10, (1.0, 0.95, 0.88), (0, 0, 4))
    add_area((14, -12, 12), 1500, 12, (0.62, 0.76, 1.0), (0, 0, 4))
    # 主屋四个檐角（檐口 + 山墙封边 + 墙角的交汇处）
    shot("corner_fl.png", (-3.6, 3.3, 4.4), 3.4, az=-42, el=-6)
    shot("corner_fr.png", (3.6, 3.3, 4.4), 3.4, az=42, el=-6)
    shot("corner_bl.png", (-3.6, -3.6, 4.4), 3.4, az=-138, el=-6)
    shot("corner_top.png", (-3.9, 3.2, 4.6), 3.0, az=-30, el=38)
    print("DONE")


main()
