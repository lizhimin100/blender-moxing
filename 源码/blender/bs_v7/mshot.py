# -*- coding: utf-8 -*-
"""mshot.py —— 微缩件的出图底片（1 m 件专用）

与 bs_v6 的 shotlib 的区别：那套是"6 m 建筑 + 大地面 + 冷灰影棚"，
这套是"沙盘摆件 + 白底/渐变 + 硬光短影"，机位更近、光更硬、边缘要亮。

所有出图都走 **Standard 色彩变换**：交付图的颜色必须等于色板本身，
不走 AgX（会把 #2554A8 压成灰蓝、把 #D9A441 洗成土黄）。
"""
import math

import bpy
from mathutils import Vector

WORLD = (0.055, 0.060, 0.070)      # 渐变环境：上亮下暗
GROUND = (0.30, 0.31, 0.28)


def clear():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for blk in (bpy.data.meshes, bpy.data.materials, bpy.data.cameras,
                bpy.data.lights, bpy.data.worlds):
        for it in list(blk):
            try:
                blk.remove(it)
            except Exception:
                pass


def scene(res=(900, 900), samp=64, transparent=True, exposure=0.0):
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_EEVEE'
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = transparent
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGBA'
    sc.render.image_settings.color_depth = '8'
    sc.view_settings.view_transform = 'Standard'
    sc.view_settings.look = 'None'
    sc.view_settings.exposure = exposure
    sc.view_settings.gamma = 1.0
    try:
        sc.eevee.taa_render_samples = samp
        sc.eevee.use_raytracing = False
        sc.eevee.use_shadows = True
    except Exception:
        pass
    return sc


def world(top=(0.80, 0.78, 0.73), bottom=(0.62, 0.60, 0.56), strength=0.36):
    """背景亮、环境暗：用 Light Path 的 Is Camera Ray 把"看到的背景"和"照明的环境"
    分开。否则想要浅背景就得把 ambient 拉到 1.0，整个模型瞬间拍平。"""
    w = bpy.data.worlds.new("W")
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    mix = nt.nodes.new("ShaderNodeMixShader")
    lp = nt.nodes.new("ShaderNodeLightPath")
    bg_cam = nt.nodes.new("ShaderNodeBackground")
    bg_lit = nt.nodes.new("ShaderNodeBackground")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    tex = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    mapr = nt.nodes.new("ShaderNodeMapRange")
    mapr.inputs["From Min"].default_value = -0.3
    mapr.inputs["From Max"].default_value = 1.4
    nt.links.new(tex.outputs["Generated"], sep.inputs["Vector"])
    nt.links.new(sep.outputs["Z"], mapr.inputs["Value"])
    nt.links.new(mapr.outputs["Result"], ramp.inputs["Fac"])
    ramp.color_ramp.elements[0].color = (*bottom, 1)
    ramp.color_ramp.elements[1].color = (*top, 1)
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[1].position = 0.62
    nt.links.new(ramp.outputs["Color"], bg_cam.inputs["Color"])
    bg_cam.inputs["Strength"].default_value = 1.0
    bg_lit.inputs["Color"].default_value = (0.55, 0.58, 0.64, 1)
    bg_lit.inputs["Strength"].default_value = strength
    nt.links.new(lp.outputs["Is Camera Ray"], mix.inputs["Fac"])
    nt.links.new(bg_lit.outputs["Background"], mix.inputs[1])
    nt.links.new(bg_cam.outputs["Background"], mix.inputs[2])
    nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])
    return w


def ground(size=14.0, color=GROUND):
    me = bpy.data.meshes.new("地面")
    me.from_pydata([(-size, -size, 0), (size, -size, 0), (size, size, 0), (-size, size, 0)],
                   [], [(0, 1, 2, 3)])
    ob = bpy.data.objects.new("地面", me)
    bpy.context.collection.objects.link(ob)
    m = bpy.data.materials.new("地面")
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = 0.92
    me.materials.append(m)
    return ob


def sun(az_deg, el_deg, energy=3.6, angle=0.6):
    d = bpy.data.lights.new("日", 'SUN')
    d.energy = energy
    d.angle = math.radians(angle)
    ob = bpy.data.objects.new("日", d)
    bpy.context.collection.objects.link(ob)
    a, e = math.radians(az_deg), math.radians(el_deg)
    v = Vector((math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), math.sin(e)))
    ob.rotation_euler = v.to_track_quat('Z', 'Y').to_euler()   # 灯头 -Z 必须指向原点
    ob.location = v * 4.0
    return ob


def area(name, az_deg, el_deg, energy, size=3.0, dist=3.2, color=(1, 1, 1)):
    d = bpy.data.lights.new(name, 'AREA')
    d.energy = energy
    d.size = size
    d.color = color
    ob = bpy.data.objects.new(name, d)
    bpy.context.collection.objects.link(ob)
    a, e = math.radians(az_deg), math.radians(el_deg)
    v = Vector((math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), math.sin(e)))
    ob.location = v * dist + Vector((0, 0, 0.6))
    ob.rotation_euler = v.to_track_quat('Z', 'Y').to_euler()
    return ob


def cam(az, el, target=(0.0, 0.0, 0.55), dist=4.0, lens=85, ortho=None):
    c = bpy.data.cameras.new("机")
    ob = bpy.data.objects.new("机", c)
    bpy.context.collection.objects.link(ob)
    a, e = math.radians(az), math.radians(el)
    v = Vector((math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), math.sin(e)))
    t = Vector(target)
    ob.location = t + v * dist
    ob.rotation_euler = (ob.location - t).to_track_quat('Z', 'Y').to_euler()
    if ortho:
        c.type = 'ORTHO'
        c.ortho_scale = ortho
    else:
        c.lens = lens
    bpy.context.scene.camera = ob
    return ob


def fit(ob, corners, az, el, margin=1.08, ortho=True, lens=85, center=None):
    """按世界包围盒自动取景。corners = 8 个世界坐标点；center = 视点中心（必须给，
    否则 |dot| 里混进"物体离原点多远"，跨度会算成 2.4 倍）。"""
    if center is None:
        center = [sum(p[i] for p in corners) / len(corners) for i in range(3)]
    corners = [[p[i] - center[i] for i in range(3)] for p in corners]
    a, e = math.radians(az), math.radians(el)
    v = Vector((math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), math.sin(e)))
    q = v.to_track_quat('Z', 'Y')
    rot = q.to_matrix()
    right, up = rot @ Vector((1, 0, 0)), rot @ Vector((0, 1, 0))
    mx = max(abs(Vector(p).dot(right)) for p in corners)
    my = max(abs(Vector(p).dot(up)) for p in corners)
    span = 2 * max(mx, my) * margin
    if ortho:
        ob.data.type = 'ORTHO'
        ob.data.ortho_scale = span
    else:
        fov = 2 * math.atan(0.5 * 36.0 / lens)
        ob.location = ob.location  # 由调用方定
    return span


def bbox_corners(objs):
    lo = Vector((1e9, 1e9, 1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    for ob in objs:
        for c in ob.bound_box:
            w = ob.matrix_world @ Vector(c)
            for i in range(3):
                lo[i] = min(lo[i], w[i])
                hi[i] = max(hi[i], w[i])
    return [Vector((x, y, z)) for x in (lo.x, hi.x) for y in (lo.y, hi.y) for z in (lo.z, hi.z)], lo, hi


def render(path, samples=None):
    sc = bpy.context.scene
    if samples:
        sc.eevee.taa_render_samples = samples
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    return path
