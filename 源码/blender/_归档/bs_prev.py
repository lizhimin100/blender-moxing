"""
bs_prev.py —— 快速预览（低模 + 3 个机位），只为了在迭代时不浪费时间。

    python build/bl_rt.py act blender/bs_v6/bs_prev.py

产物：docs/_wip/v8p_hero.png / v8p_front.png / v8p_rts.png
"""
import importlib
import math
import os
import sys

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
import bslib  # noqa: E402
import bs_model  # noqa: E402

RES = int(os.environ.get("BS_RES", "840"))
SAMP = int(os.environ.get("BS_SAMP", "16"))
SMOOTH = os.environ.get("BS_SMOOTH", "0") == "1"


def clear_scene():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for blk in (bpy.data.meshes, bpy.data.materials, bpy.data.images,
                bpy.data.armatures, bpy.data.actions, bpy.data.cameras,
                bpy.data.lights, bpy.data.collections):
        for it in list(blk):
            try:
                blk.remove(it)
            except Exception:
                pass


def bounds(objs):
    lo = Vector((1e9, 1e9, 1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    for ob in objs:
        for c in ob.bound_box:
            w = ob.matrix_world @ Vector(c)
            for i in range(3):
                lo[i] = min(lo[i], w[i])
                hi[i] = max(hi[i], w[i])
    return lo, hi


def setup_world():
    w = bpy.data.worlds.new("W")
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    tex = nt.nodes.new("ShaderNodeTexGradient")
    mapn = nt.nodes.new("ShaderNodeMapping")
    texc = nt.nodes.new("ShaderNodeTexCoord")
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = (0.055, 0.062, 0.070, 1)
    ramp.color_ramp.elements[1].position = 1.0
    ramp.color_ramp.elements[1].color = (0.30, 0.35, 0.42, 1)
    mapn.inputs["Rotation"].default_value = (math.radians(90), 0, 0)
    nt.links.new(texc.outputs["Generated"], mapn.inputs["Vector"])
    nt.links.new(mapn.outputs["Vector"], tex.inputs["Vector"])
    nt.links.new(tex.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 1.05
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])


def add_area(name, loc, energy, size, color, aim):
    d = bpy.data.lights.new(name, "AREA")
    d.energy = energy
    d.size = size
    d.color = color
    ob = bpy.data.objects.new(name, d)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    ob.rotation_euler = (Vector(aim) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return ob


def add_point(name, loc, energy, color, radius=0.5):
    d = bpy.data.lights.new(name, "POINT")
    d.energy = energy
    d.color = color
    d.shadow_soft_size = radius
    ob = bpy.data.objects.new(name, d)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    return ob


def ground():
    me = bpy.data.meshes.new("ground")
    s = 60.0
    me.from_pydata([(-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0)], [], [(0, 1, 2, 3)])
    me.update()
    ob = bpy.data.objects.new("ground", me)
    bpy.context.scene.collection.objects.link(ob)
    mat = bpy.data.materials.new("M_ground")
    mat.use_nodes = True
    b = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*bslib.srgb("#4C5442"), 1)
    b.inputs["Roughness"].default_value = 0.95
    ob.data.materials.append(mat)
    return ob


def make_camera(target, span, az, el):
    cam = bpy.data.cameras.new("Cam")
    cam.type = "ORTHO"
    cam.ortho_scale = span
    ob = bpy.data.objects.new("Cam", cam)
    bpy.context.scene.collection.objects.link(ob)
    a, e = math.radians(az), math.radians(el)
    r = max(span * 4.0, 45.0)
    ob.location = target + Vector((math.sin(a) * math.cos(e) * r,
                                   math.cos(a) * math.cos(e) * r,
                                   math.sin(e) * r))
    ob.rotation_euler = (target - ob.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = ob
    return ob


def set_render(res, samples, exposure=0.35):
    sc = bpy.context.scene
    sc.render.resolution_x = res
    sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGB"
    sc.view_settings.view_transform = "AgX"
    for look in ("AgX - Punchy", "AgX - Medium High Contrast"):
        try:
            sc.view_settings.look = look
            break
        except Exception:
            continue
    sc.view_settings.exposure = exposure
    for name in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            sc.render.engine = name
            break
        except TypeError:
            continue
    ee = getattr(sc, "eevee", None)
    if ee is not None:
        for attr, val in (("taa_render_samples", samples), ("use_gtao", True),
                          ("use_shadows", True), ("use_raytracing", True),
                          ("use_volumetric_lights", False)):
            if hasattr(ee, attr):
                try:
                    setattr(ee, attr, val)
                except Exception:
                    pass


def fit_span(objs, az, el, margin=1.10):
    """把整件资产（含前场道具）按当前机位自动装进画幅。"""
    lo, hi = bounds(objs)
    ctr = (lo + hi) * 0.5
    a, e = math.radians(az), math.radians(el)
    d = -Vector((math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), math.sin(e)))
    right = d.cross(Vector((0, 0, 1))).normalized()
    up = right.cross(d).normalized()
    mx = my = 0.0
    for ob in objs:
        for c in ob.bound_box:
            p = (ob.matrix_world @ Vector(c)) - ctr
            mx = max(mx, abs(p.dot(right)))
            my = max(my, abs(p.dot(up)))
    return ctr, max(mx, my) * 2.0 * margin


def shot(name, ctr, span, az, el, res=RES, samples=SAMP):
    for ob in [o for o in bpy.context.scene.objects if o.type == "CAMERA"]:
        bpy.data.objects.remove(ob, do_unlink=True)
    make_camera(ctr, span, az, el)
    set_render(res, samples)
    path = os.path.join(OUT, name)
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("[render]", os.path.basename(path), os.path.getsize(path))


def main():
    os.makedirs(OUT, exist_ok=True)
    clear_scene()
    objs, st = bs_model.build(smooth=SMOOTH)
    print("STATS", st)
    lo, hi = bounds(objs)
    ctr = (lo + hi) * 0.5
    span = max(hi.x - lo.x, hi.z - lo.z) * 1.30
    setup_world()
    ground()
    add_area("key", ctr + Vector((-span * 1.15, span * 0.95, span * 1.20)),
             energy=span * span * 42, size=span * 0.70, color=(1.0, 0.92, 0.80), aim=ctr)
    add_area("fill", ctr + Vector((span * 1.45, -span * 0.55, span * 0.55)),
             energy=span * span * 12, size=span * 1.5, color=(0.62, 0.76, 1.0), aim=ctr)
    add_area("bounce", ctr + Vector((span * 0.15, span * 1.55, span * 0.10)),
             energy=span * span * 9, size=span * 1.6, color=(1.0, 0.90, 0.78), aim=ctr)
    # 炉口光要放在火焰"外面"：放在火里会把自发光表面打成惨白（上一版的粉色就是这个原因）
    add_point("forge", (-0.29, 5.34, 0.92), 380.0, (1.0, 0.44, 0.13), 0.42)
    add_point("forge2", (-0.29, 5.62, 1.75), 110.0, (1.0, 0.52, 0.20), 0.85)
    add_point("doorway", (2.93, 5.10, 1.30), 90.0, (1.0, 0.62, 0.30), 0.7)
    for name, az, el, mg in (("v8p_hero.png", -38, 32, 1.08),
                             ("v8p_front.png", 0, 6, 1.04),
                             ("v8p_rts.png", -40, 42, 1.06)):
        c2, s2 = fit_span(objs, az, el, mg)
        shot(name, c2, s2, az, el)
    shot("v8p_close.png", Vector((-0.29, 5.10, 2.55)), 7.4, az=-16, el=10)
    print("DONE")


main()
