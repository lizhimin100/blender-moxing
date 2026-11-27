"""lm_look.py —— 伐木场快速看形体（低模 + 快渲染，用于迭代）

    python build/bl_act.py act blender/bs_v6/fm_look.py
"""
import importlib
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = r"D:/测试一/blender/bs_v6"
ROOT = r"D:/测试一"
OUT = os.path.join(ROOT, "docs", "伐木场", "_look")
if HERE not in sys.path:
    sys.path.insert(0, HERE)
for _m in ("bslib", "br_model", "lm_model"):
    if _m in sys.modules:
        importlib.reload(sys.modules[_m])
import bslib  # noqa: E402
import lm_model  # noqa: E402

RES = 900
SAMP = 16


def clear_scene():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for blk in (bpy.data.meshes, bpy.data.materials, bpy.data.images,
                bpy.data.cameras, bpy.data.lights, bpy.data.worlds):
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


def setup_world(strength=0.48):
    w = bpy.data.worlds.new("W")
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Color"].default_value = (0.16, 0.19, 0.22, 1)
    bg.inputs["Strength"].default_value = strength
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


def ground_plane():
    me = bpy.data.meshes.new("ground")
    s = 300.0
    me.from_pydata([(-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0)], [], [(0, 1, 2, 3)])
    me.update()
    ob = bpy.data.objects.new("ground", me)
    bpy.context.scene.collection.objects.link(ob)
    mat = bpy.data.materials.new("M_ground")
    mat.use_nodes = True
    b = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*bslib.srgb("#3F4638"), 1)
    b.inputs["Roughness"].default_value = 1.0
    ob.data.materials.append(mat)
    return ob


def light_rig(ctr, span, az, el):
    for ob in [o for o in bpy.context.scene.objects if o.type == "LIGHT"]:
        bpy.data.objects.remove(ob, do_unlink=True)
    a, e = math.radians(az), math.radians(el)
    view = Vector((math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), math.sin(e)))
    view.normalize()
    right = view.cross(Vector((0, 0, 1)))
    right.normalize()
    up = right.cross(view).normalized()
    s = span
    add_area("key", ctr + (-0.62 * right + 0.92 * up + 1.35 * view) * s,
             s * s * 112, s * 0.52, (1.00, 0.93, 0.82), ctr)
    add_area("fill", ctr + (1.15 * right + 0.10 * up + 0.95 * view) * s,
             s * s * 24, s * 1.15, (0.64, 0.78, 1.00), ctr)
    add_area("bounce", ctr + (0.05 * right - 0.95 * up + 0.75 * view) * s,
             s * s * 9, s * 1.25, (0.86, 0.90, 1.00), ctr)


def set_render(res, samples, exposure=0.20):
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
    sc.render.engine = "BLENDER_EEVEE"
    ee = getattr(sc, "eevee", None)
    if ee is not None:
        for attr, val in (("taa_render_samples", samples), ("use_gtao", True),
                          ("use_shadows", True), ("use_raytracing", True)):
            if hasattr(ee, attr):
                try:
                    setattr(ee, attr, val)
                except Exception:
                    pass


def fit_span(objs, az, el, margin=1.08):
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


def make_cam(target, span, az, el):
    for ob in [o for o in bpy.context.scene.objects if o.type == "CAMERA"]:
        bpy.data.objects.remove(ob, do_unlink=True)
    cam = bpy.data.cameras.new("Cam")
    cam.type = "ORTHO"
    cam.ortho_scale = span
    cam.clip_start = 1.0
    cam.clip_end = 300.0
    ob = bpy.data.objects.new("Cam", cam)
    bpy.context.scene.collection.objects.link(ob)
    a, e = math.radians(az), math.radians(el)
    r = 95.0
    ob.location = target + Vector((math.sin(a) * math.cos(e) * r,
                                   math.cos(a) * math.cos(e) * r,
                                   math.sin(e) * r))
    ob.rotation_euler = (target - ob.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = ob
    return ob


def shot(name, objs, az, el, margin=1.06, res=RES, samples=SAMP):
    ctr, span = fit_span(objs, az, el, margin)
    make_cam(ctr, span, az, el)
    light_rig(ctr, max(span, 16.0), az, el)
    set_render(res, samples)
    path = os.path.join(OUT, name)
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("[render]", name, os.path.getsize(path))


def pshot(name, loc, aim, lens=62, res=RES, samples=SAMP):
    for ob in [o for o in bpy.context.scene.objects if o.type == "CAMERA"]:
        bpy.data.objects.remove(ob, do_unlink=True)
    cam = bpy.data.cameras.new("Cam")
    cam.lens = lens
    cam.clip_start = 0.5
    cam.clip_end = 300.0
    ob = bpy.data.objects.new("Cam", cam)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = Vector(loc)
    ob.rotation_euler = (Vector(aim) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = ob
    d = Vector(loc) - Vector(aim)
    az = math.degrees(math.atan2(d.x, d.y))
    el = math.degrees(math.asin(max(-1.0, min(1.0, d.z / max(d.length, 1e-6)))))
    light_rig(Vector(aim), max(d.length * 0.55, 8.0), az, el)
    set_render(res, samples)
    path = os.path.join(OUT, name)
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("[render]", name, os.path.getsize(path))


def main():
    os.makedirs(OUT, exist_ok=True)
    clear_scene()
    objs, st = lm_model.build(smooth=False)
    print("STATS", st)
    lo, hi = bounds(objs)
    print("BBOX", [round(v, 2) for v in lo], [round(v, 2) for v in hi])
    setup_world()
    ground_plane()
    shot("look_main.png", objs, -34, 26, 1.05)
    shot("look_front.png", objs, 0, 4, 1.04)
    shot("look_top.png", objs, -32, 58, 1.05)
    shot("look_rts.png", objs, -36, 42, 1.05)
    pshot("look_saw.png", (5.6, 12.6, 6.2), (-1.5, 4.3, 4.2), lens=54)
    pshot("look_hut.png", (-11.4, 9.4, 4.2), (-4.4, 0.4, 2.6), lens=56)
    pshot("look_logs.png", (12.4, 9.0, 4.2), (5.9, -0.2, 1.2), lens=54)
    ctr, span = Vector((-1.5, 0.0, 4.0)), 8.6
    make_cam(ctr, span, 0, 2)
    light_rig(ctr, max(span, 12.0), 0, 2)
    set_render(900, 16)
    bpy.context.scene.render.filepath = os.path.join(OUT, "look_front_door.png")
    bpy.ops.render.render(write_still=True)
    print("DONE")


main()
