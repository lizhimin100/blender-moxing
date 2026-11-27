"""th_compare.py —— 三座建筑 1:1 并排，看"摆在一起会不会突兀"

    python build/bl_act.py act blender/bs_v6/th_compare.py

用**手游近景 GLB**（运行时真正用的那一档）直接导入，同一机位、同一布光，
间距按各自占地宽 + 2 m 摆，地面共用一块。
产物：docs/城镇大厅/v1/三座对照.png
"""
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = r"D:/测试一/blender/bs_v6"
ROOT = r"D:/测试一"
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from assets_path import asset_path  # noqa: E402

OUT = os.path.join(ROOT, "docs", "城镇大厅", "v3", "三座对照.png")
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import bslib  # noqa: E402

ASSETS = [("铁匠铺", "铁匠铺_手游_近.glb"), ("兵营", "兵营_手游_近.glb"),
          ("城镇大厅", "城镇大厅_手游_近.glb")]


def clear():
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


def setup_world(strength=1.05):
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


def ground():
    me = bpy.data.meshes.new("ground")
    s = 120.0
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


def main():
    clear()
    gap = 2.0
    x = 0.0
    placed = []
    for key, fname in ASSETS:
        path = asset_path(key, fname)
        bpy.ops.import_scene.gltf(filepath=path)
        objs = [o for o in bpy.context.selected_objects if o.type == "MESH"]
        lo, hi = bounds(objs)
        w = hi.x - lo.x
        # 先把这一座挪到 (x, 0)，再累计下一座的 x
        for ob in objs:
            ob.location.x += x - (lo.x + hi.x) * 0.5
            ob.location.y += -(lo.y + hi.y) * 0.5
        placed += objs
        print("[place]", key, "w=%.2f h=%.2f at x=%.2f" % (w, hi.z - lo.z, x))
        x += w + gap
    bpy.context.view_layer.update()

    setup_world()
    ground()
    lo, hi = bounds(placed)
    ctr = (lo + hi) * 0.5
    span = max(hi.x - lo.x, hi.z - lo.z)
    add_area("key", ctr + Vector((-span * 0.9, span * 1.0, span * 1.1)),
             energy=span * span * 34, size=span * 0.8, color=(1.0, 0.92, 0.80), aim=ctr)
    add_area("fill", ctr + Vector((span * 1.2, -span * 0.6, span * 0.5)),
             energy=span * span * 10, size=span * 1.5, color=(0.62, 0.76, 1.0), aim=ctr)
    add_area("bounce", ctr + Vector((0.0, span * 1.4, span * 0.15)),
             energy=span * span * 8, size=span * 1.6, color=(1.0, 0.90, 0.78), aim=ctr)

    cam = bpy.data.cameras.new("Cam")
    cam.type = "ORTHO"
    az, el = -26, 20
    # 主楼长到 24 m 后，原来的 1.02 只按 16:9 的宽度算，上下会被裁掉
    resx, resy = bpy.context.scene.render.resolution_x, bpy.context.scene.render.resolution_y
    need = max(hi.x - lo.x, (hi.z - lo.z) * resx / max(resy, 1))
    cam.ortho_scale = need * 1.30
    ob = bpy.data.objects.new("Cam", cam)
    bpy.context.scene.collection.objects.link(ob)
    a, e = math.radians(az), math.radians(el)
    r = max(span * 4.0, 60.0)
    ob.location = ctr + Vector((math.sin(a) * math.cos(e) * r,
                                math.cos(a) * math.cos(e) * r,
                                math.sin(e) * r))
    ob.rotation_euler = (ctr - ob.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = ob

    sc = bpy.context.scene
    sc.render.resolution_x = 1600
    sc.render.resolution_y = 900
    sc.render.image_settings.file_format = "PNG"
    sc.view_settings.view_transform = "AgX"
    for look in ("AgX - Punchy", "AgX - Medium High Contrast"):
        try:
            sc.view_settings.look = look
            break
        except Exception:
            continue
    sc.view_settings.exposure = 0.35
    sc.render.engine = "BLENDER_EEVEE"
    ee = getattr(sc, "eevee", None)
    if ee is not None:
        for attr, val in (("taa_render_samples", 48), ("use_gtao", True),
                          ("use_shadows", True), ("use_raytracing", True)):
            if hasattr(ee, attr):
                try:
                    setattr(ee, attr, val)
                except Exception:
                    pass
    sc.render.filepath = OUT
    bpy.ops.render.render(write_still=True)
    print("[render]", OUT, os.path.getsize(OUT))


main()
