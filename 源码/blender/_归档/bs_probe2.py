"""bs_probe2.py —— 对"悬空薄片"做射线反查：告诉我是哪个构件"""
import importlib, math, os, sys
import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else r"D:/测试一/blender/bs_v6"
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


def main():
    clear_scene()
    bs_model.build(smooth=False)
    cam_data = bpy.data.cameras.new("C")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = 3.4
    cam = bpy.data.objects.new("C", cam_data)
    bpy.context.scene.collection.objects.link(cam)
    target = Vector((0.0, -1.5, 9.3))
    az, el, r = -30.0, 22.0, 40.0
    a, e = math.radians(az), math.radians(el)
    cam.location = target + Vector((math.sin(a) * math.cos(e) * r,
                                    math.cos(a) * math.cos(e) * r,
                                    math.sin(e) * r))
    cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = cam
    bpy.context.view_layer.update()
    mw = cam.matrix_world
    right = mw.to_3x3() @ Vector((1, 0, 0))
    up = mw.to_3x3() @ Vector((0, 1, 0))
    fwd = (mw.to_3x3() @ Vector((0, 0, -1))).normalized()
    span = 3.4
    dg = bpy.context.evaluated_depsgraph_get()
    hits = {}
    for px in range(190, 320, 5):
        for py in range(460, 560, 5):
            ndc_x = (px + 0.5) / 900.0 * 2.0 - 1.0
            ndc_y = 1.0 - (py + 0.5) / 900.0 * 2.0
            origin = mw.translation + right * (ndc_x * span * 0.5) + up * (ndc_y * span * 0.5)
            ok, loc, nrm, idx, ob, mat = bpy.context.scene.ray_cast(dg, origin, fwd)
            if ok and ob:
                key = (ob.name, (round(loc.x, 1), round(loc.y, 1), round(loc.z, 1)))
                hits.setdefault(key, 0)
                hits[key] += 1
    for (name, loc), n in sorted(hits.items(), key=lambda kv: -kv[1])[:14]:
        print("HIT %-22s at %s  x%d" % (name, loc, n))
    print("DONE")


main()
