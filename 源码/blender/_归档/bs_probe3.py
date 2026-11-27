"""bs_probe3.py —— 指定机位 + 像素窗口，射线反查命中构件"""
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

TARGET = (-3.6, 3.3, 4.4)
SPAN = 3.4
AZ, EL = -42.0, -6.0
PX0, PX1, PY0, PY1 = 330, 520, 60, 200
RES = 900


def main():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    bs_model.build(smooth=False)
    cam_data = bpy.data.cameras.new("C")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = SPAN
    cam = bpy.data.objects.new("C", cam_data)
    bpy.context.scene.collection.objects.link(cam)
    tgt = Vector(TARGET)
    a, e = math.radians(AZ), math.radians(EL)
    r = 40.0
    cam.location = tgt + Vector((math.sin(a) * math.cos(e) * r,
                                 math.cos(a) * math.cos(e) * r,
                                 math.sin(e) * r))
    cam.rotation_euler = (tgt - cam.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = cam
    bpy.context.view_layer.update()
    mw = cam.matrix_world
    right = mw.to_3x3() @ Vector((1, 0, 0))
    up = mw.to_3x3() @ Vector((0, 1, 0))
    fwd = (mw.to_3x3() @ Vector((0, 0, -1))).normalized()
    dg = bpy.context.evaluated_depsgraph_get()
    hits = {}
    for px in range(PX0, PX1, 4):
        for py in range(PY0, PY1, 4):
            ndc_x = (px + 0.5) / RES * 2.0 - 1.0
            ndc_y = 1.0 - (py + 0.5) / RES * 2.0
            origin = mw.translation + right * (ndc_x * SPAN * 0.5) + up * (ndc_y * SPAN * 0.5)
            ok, loc, nrm, idx, ob, mat = bpy.context.scene.ray_cast(dg, origin, fwd)
            if ok and ob:
                key = (ob.name, (round(loc.x, 1), round(loc.y, 1), round(loc.z, 1)))
                hits[key] = hits.get(key, 0) + 1
    for (name, loc), n in sorted(hits.items(), key=lambda kv: -kv[1])[:18]:
        print("HIT %-20s at %s x%d" % (name, loc, n))
    print("DONE")


main()
