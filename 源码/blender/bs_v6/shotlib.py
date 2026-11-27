"""shotlib.py —— 建筑交付出图的公共底片：清场 / 世界 / 相机 / 布光 / 取景

九座建筑共用同一套"观感标准"，所以这些函数必须只有一份实现：
换机位时灯光跟着相机转（相机相对布光），换建筑时只换 module + 机位表。

用法：
    import shotlib as S
    S.OUTSHOT = r".../docs/箭塔/v1"
    S.RES, S.SAMP = 1200, 64
    S.clear_scene()
    objs, st = mod.build(smooth=True)
    S.setup_world(); S.ground_plane()
    S.shot("主图.png", objs, -34, 26, 1.06)

坐标约定：X 右、Y 前（+Y = 正面）、Z 上；方位角 0 = 正对正面，正数往 +X 转；
仰角 0 = 平视。交付前模型已沿 X 镜像，所以画面里的"右"是建模期的 −X。
"""
import math
import os

import bpy
from mathutils import Vector

import bslib

RES = 1200
SAMP = 64
OUTSHOT = ""
GROUND = "#3F4638"


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
    """冷灰竖向渐变环境：上亮下暗，读作"阴天棚拍"，不抢建筑自己的明度秩序。"""
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
    ramp.color_ramp.elements[0].color = (0.050, 0.058, 0.064, 1)
    ramp.color_ramp.elements[1].position = 1.0
    ramp.color_ramp.elements[1].color = (0.30, 0.34, 0.38, 1)
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
    s = 300.0
    me.from_pydata([(-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0)], [], [(0, 1, 2, 3)])
    me.update()
    ob = bpy.data.objects.new("ground", me)
    bpy.context.scene.collection.objects.link(ob)
    mat = bpy.data.materials.new("M_ground")
    mat.use_nodes = True
    b = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*bslib.srgb(GROUND), 1)
    b.inputs["Roughness"].default_value = 1.0
    if "Specular IOR Level" in b.inputs:
        b.inputs["Specular IOR Level"].default_value = 0.0
    ob.data.materials.append(mat)
    return ob


def clear_lights():
    for ob in [o for o in bpy.context.scene.objects if o.type == "LIGHT"]:
        bpy.data.objects.remove(ob, do_unlink=True)


def light_rig(ctr, span, az, el):
    """相机相对布光：每张图的明暗关系一致，不靠固定世界灯碰运气。

    主光在画面左上、略靠相机（暖）；右补光冷、背后反弹极弱 —— 三盏就够，
    再多会把低模的棱磨平。
    """
    clear_lights()
    a, e = math.radians(az), math.radians(el)
    view = Vector((math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), math.sin(e)))
    view.normalize()
    right = view.cross(Vector((0, 0, 1)))
    if right.length < 1e-6:
        right = Vector((1, 0, 0))
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
    for nm in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            sc.render.engine = nm
            break
        except TypeError:
            continue
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
    cam.clip_end = 400.0
    ob = bpy.data.objects.new("Cam", cam)
    bpy.context.scene.collection.objects.link(ob)
    a, e = math.radians(az), math.radians(el)
    r = 120.0
    ob.location = target + Vector((math.sin(a) * math.cos(e) * r,
                                   math.cos(a) * math.cos(e) * r,
                                   math.sin(e) * r))
    ob.rotation_euler = (target - ob.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = ob
    return ob


def shot(name, objs, az, el, margin=1.08, res=None, samples=None, fixed=None,
         out=None):
    if fixed:
        ctr, span = fixed
    else:
        ctr, span = fit_span(objs, az, el, margin)
    make_cam(ctr, span, az, el)
    light_rig(ctr, max(span, 16.0), az, el)
    set_render(res or RES, samples or SAMP)
    path = os.path.join(out or OUTSHOT, name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("[render]", name, os.path.getsize(path))
    return ctr, span


def pshot(name, loc, aim, lens=70, res=None, samples=None, out=None):
    for ob in [o for o in bpy.context.scene.objects if o.type == "CAMERA"]:
        bpy.data.objects.remove(ob, do_unlink=True)
    cam = bpy.data.cameras.new("Cam")
    cam.lens = lens
    cam.clip_start = 0.5
    cam.clip_end = 400.0
    ob = bpy.data.objects.new("Cam", cam)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = Vector(loc)
    ob.rotation_euler = (Vector(aim) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = ob
    d = Vector(loc) - Vector(aim)
    az = math.degrees(math.atan2(d.x, d.y))
    el = math.degrees(math.asin(max(-1.0, min(1.0, d.z / max(d.length, 1e-6)))))
    light_rig(Vector(aim), max(d.length * 0.55, 8.0), az, el)
    set_render(res or RES, samples or SAMP)
    path = os.path.join(out or OUTSHOT, name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("[render]", name, os.path.getsize(path))
