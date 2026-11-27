"""th_wip.py -- 城镇大厅快速取景迭代（只渲染 4 张低分辨率图，不进交付目录）"""
import importlib
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = r"D:/测试一/blender/bs_v6"
ROOT = r"D:/测试一"
OUT = os.path.join(ROOT, "docs", "城镇大厅", "v2", "_wip")
if HERE not in sys.path:
    sys.path.insert(0, HERE)
for _m in ("bslib", "br_model", "th_model"):
    if _m in sys.modules:
        importlib.reload(sys.modules[_m])
import bslib  # noqa: E402
import th_model  # noqa: E402


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


def setup_world(strength=0.45):
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
    s = 90.0
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


def fit(objs, az, el, margin=1.08):
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


def shot(name, objs, az, el, margin=1.08, res=760):
    ctr, span = fit(objs, az, el, margin)
    cam = bpy.data.cameras.new("Cam")
    cam.type = "ORTHO"
    cam.ortho_scale = span
    ob = bpy.data.objects.new("Cam", cam)
    bpy.context.scene.collection.objects.link(ob)
    a, e = math.radians(az), math.radians(el)
    r = 80.0
    ob.location = ctr + Vector((math.sin(a) * math.cos(e) * r,
                                math.cos(a) * math.cos(e) * r,
                                math.sin(e) * r))
    ob.rotation_euler = (ctr - ob.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = ob
    sc = bpy.context.scene
    sc.render.resolution_x = res
    sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    sc.view_settings.view_transform = "AgX"
    try:
        sc.view_settings.look = "AgX - Punchy"
    except Exception:
        pass
    sc.view_settings.exposure = 0.20
    sc.render.engine = "BLENDER_EEVEE"
    ee = getattr(sc, "eevee", None)
    if ee is not None:
        for attr, val in (("taa_render_samples", 24), ("use_gtao", True),
                          ("use_shadows", True), ("use_raytracing", True)):
            if hasattr(ee, attr):
                try:
                    setattr(ee, attr, val)
                except Exception:
                    pass
    for old in [o for o in sc.objects if o.type == "CAMERA" and o is not ob]:
        bpy.data.objects.remove(old, do_unlink=True)
    path = os.path.join(OUT, name)
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("[render]", name, os.path.getsize(path))


def main():
    os.makedirs(OUT, exist_ok=True)
    clear_scene()
    objs, st = th_model.build(smooth=True)
    print("STATS", st)
    lo, hi = bounds(objs)
    print("BBOX", tuple(round(v, 2) for v in lo), tuple(round(v, 2) for v in hi))
    setup_world()
    ground_plane()
    ctr = (lo + hi) * 0.5
    span = max(hi.x - lo.x, hi.z - lo.z)
    add_area("key", ctr + Vector((-span * 1.05, span * 1.00, span * 1.35)),
             energy=span * span * 120, size=span * 0.55, color=(1.0, 0.93, 0.82), aim=ctr)
    add_area("fill", ctr + Vector((span * 1.50, -span * 0.45, span * 0.55)),
             energy=span * span * 22, size=span * 1.3, color=(0.64, 0.78, 1.0), aim=ctr)
    add_area("rim", ctr + Vector((span * 0.75, -span * 1.15, span * 0.85)),
             energy=span * span * 70, size=span * 0.55, color=(1.0, 0.86, 0.70), aim=ctr)
    add_area("bounce", ctr + Vector((span * 0.10, span * 1.45, span * 0.10)),
             energy=span * span * 10, size=span * 1.6, color=(1.0, 0.90, 0.78), aim=ctr)
    shot("wip_hero.png", objs, -38, 30, 1.08)
    shot("wip_front.png", objs, 0, 6, 1.04)
    shot("wip_side.png", objs, 90, 6, 1.04)
    shot("wip_top.png", objs, -40, 42, 1.06)
    shot("wip_hero_r.png", objs, 38, 30, 1.08)
    shot("wip_hero_l.png", objs, -58, 28, 1.08)
    shot("wip_hero_m.png", objs, -48, 30, 1.08)
    shot("wip_roof.png", objs, -50, 48, 1.10)
    print("DONE")


main()
