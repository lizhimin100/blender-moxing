"""iconlib.py —— 图标出图的公共部分（取景 / 布光 / 渲染设置）

从 icon_shots.py 里抽出来的，现在建筑图标（icon_shots）和单位图标（icon_units）
共用同一份。**布光与取景只有一处实现**，否则建筑和单位摆在一排菜单里
受光方向不一样，一眼看出是两批图。

三条硬要求（来源见 icon_shots.py 头部）：
  ① 透明底（film_transparent），世界光只照明不进画面；
  ② 相机相对布光，换机位时光位跟着转；
  ③ 顶点投影取景，不按包围盒（斜视角下盒子比剪影大一圈，图标会"飘在小框里"）。
"""

import math
import os

import bpy
from mathutils import Vector

MARGIN = 1.06          # 剪影外留 6%


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


def basis(az, el):
    """返回 (view, right, up)：view 指向相机（从目标往外）。"""
    a, e = math.radians(az), math.radians(el)
    view = Vector((math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), math.sin(e)))
    fwd = -view
    right = fwd.cross(Vector((0, 0, 1)))
    if right.length < 1e-6:
        right = Vector((1, 0, 0))
    right.normalize()
    up = right.cross(fwd).normalized()
    return view, right, up


def project_fit(objs, az, el, margin=MARGIN):
    """顶点投影取景：返回 (中心, 正交宽度, 剪影尺寸)。

    构图是**非对称**的：内容底边固定在画面下方 5%，顶部留 4%+ 给旗杆。
    四边等留白会把旗尖切在画框上，图标里被切的旗读起来像 bug。
    """
    view, right, up = basis(az, el)
    xs, ys, zs = [], [], []
    for ob in objs:
        if ob.type != "MESH":
            continue
        mw = ob.matrix_world
        for v in ob.data.vertices:
            p = mw @ v.co
            xs.append(p.dot(right))
            ys.append(p.dot(up))
            zs.append(p.dot(view))
    if not xs:
        raise ValueError("没有可投影的网格顶点")
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys), max(ys)
    w, h = x1 - x0, y1 - y0
    span = max(w * 1.06, h * 1.10)
    cx = (x0 + x1) * 0.5
    cy = y0 + span * (0.5 - 0.05)          # 底边落在画面 5% 处
    ctr = right * cx + up * cy + view * ((min(zs) + max(zs)) * 0.5)
    return ctr, span, (w, h)


def make_cam(ctr, span, az, el):
    view, _, _ = basis(az, el)
    cam = bpy.data.cameras.new("IconCam")
    cam.type = "ORTHO"
    cam.ortho_scale = span
    r = span * 4.0
    cam.clip_start = r * 0.2
    cam.clip_end = r * 3.0
    ob = bpy.data.objects.new("IconCam", cam)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = ctr + view * r
    ob.rotation_euler = (-view).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = ob
    return ob


def studio_world(strength=0.15):
    """中性环境光。film_transparent 下不影响底色，只负责把暗部抬起来。"""
    w = bpy.data.worlds.new("IconWorld")
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Color"].default_value = (0.28, 0.32, 0.40, 1.0)   # 略偏冷，与暖主光成对比
    bg.inputs["Strength"].default_value = strength
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])


def add_area(name, loc, energy, size, color, aim):
    d = bpy.data.lights.new(name, "AREA")
    d.energy = energy
    d.size = size
    d.color = color
    if hasattr(d, "use_shadow"):
        d.use_shadow = True
    ob = bpy.data.objects.new(name, d)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    ob.rotation_euler = (Vector(aim) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return ob


def studio_lights(ctr, span, az, el):
    """相机相对布光：主光永远在"画面左上、靠前"，与模型朝向无关。"""
    view, right, up = basis(az, el)
    s = span
    add_area("key", ctr + (-0.60 * right + 0.95 * up + 1.45 * view) * s,
             s * s * 118, s * 0.42, (1.00, 0.94, 0.85), ctr)
    add_area("fill", ctr + (1.15 * right + 0.10 * up + 0.95 * view) * s,
             s * s * 13, s * 1.05, (0.64, 0.78, 1.00), ctr)
    add_area("rim", ctr + (0.20 * right + 0.62 * up - 1.55 * view) * s,
             s * s * 62, s * 0.42, (1.00, 0.87, 0.72), ctr)
    add_area("bounce", ctr + (0.05 * right - 0.95 * up + 0.75 * view) * s,
             s * s * 4, s * 1.10, (0.84, 0.89, 1.00), ctr)


def set_render(res, samples, exposure=0.02):
    sc = bpy.context.scene
    sc.render.resolution_x = res
    sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = True                 # ← 透明底，图标的核心
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    sc.render.image_settings.color_depth = "8"
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


def render_to(path, res, samples):
    set_render(res, samples)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    return os.path.getsize(path)


def shoot(objs, az, el, out, res=512, samples=96):
    """一把梭：取景 → 机位 → 布光 → 出图。返回 (字节数, span, 剪影尺寸)。"""
    ctr, span, size2d = project_fit(objs, az, el)
    make_cam(ctr, span, az, el)
    studio_world()
    studio_lights(ctr, span, az, el)
    n = render_to(out, res, samples)
    return n, span, size2d
