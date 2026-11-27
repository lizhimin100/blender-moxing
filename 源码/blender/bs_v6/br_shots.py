"""
br_shots.py —— 兵营 v4 交付出图（固定机位 + 自动装幅）

    python build/bl_act.py act blender/bs_v6/br_shots.py

产物：docs/br_v4/
  barracks_v4.png            3/4 主图（曲面细分版）
  barracks_v4_front.png      正立面
  barracks_v4_side.png       侧立面
  barracks_v4_back.png       背 3/4
  barracks_v4_rts.png        RTS 45° 俯视
  barracks_v4_yard.png       训练场近景（地面细节）
  barracks_v4_flag.png       旗面近景（盾 + 王冠徽记，v3.4 原样）
  barracks_v4_lowpoly.png    低模版（同主图机位，做低模 / 细分对照）
"""
import importlib
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = r"D:/测试一/blender/bs_v6"
ROOT = r"D:/测试一"
OUTSHOT = os.path.join(ROOT, "docs", "兵营", "v4")
OUTBLEND = os.path.join(ROOT, "blend", "兵营")
if HERE not in sys.path:
    sys.path.insert(0, HERE)
for _m in ("bslib", "br_model"):
    if _m in sys.modules:
        importlib.reload(sys.modules[_m])
import bslib  # noqa: E402
import br_model as bs_model  # noqa: E402

RES = int(os.environ.get("BR_RES", "1200"))
SAMP = int(os.environ.get("BR_SAMP", "64"))


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


def add_point(name, loc, energy, color, radius=0.5):
    d = bpy.data.lights.new(name, "POINT")
    d.energy = energy
    d.color = color
    d.shadow_soft_size = radius
    ob = bpy.data.objects.new(name, d)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
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


def make_camera(target, span, az, el):
    for ob in [o for o in bpy.context.scene.objects if o.type == "CAMERA"]:
        bpy.data.objects.remove(ob, do_unlink=True)
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


def shot(name, objs, az, el, margin=1.08, res=RES, samples=SAMP, fixed=None):
    if fixed:
        ctr, span = fixed
    else:
        ctr, span = fit_span(objs, az, el, margin)
    make_camera(ctr, span, az, el)
    set_render(res, samples)
    path = os.path.join(OUTSHOT, name)
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("[render]", name, os.path.getsize(path))


def pshot(name, loc, aim, lens=90, res=RES, samples=SAMP):
    """透视近景：正交近景会把 4 cm 的构件压平。"""
    for ob in [o for o in bpy.context.scene.objects if o.type == "CAMERA"]:
        bpy.data.objects.remove(ob, do_unlink=True)
    cam = bpy.data.cameras.new("Cam")
    cam.lens = lens
    ob = bpy.data.objects.new("Cam", cam)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = Vector(loc)
    ob.rotation_euler = (Vector(aim) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = ob
    set_render(res, samples)
    path = os.path.join(OUTSHOT, name)
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("[render]", name, os.path.getsize(path))


def stage(objs):
    lo, hi = bounds(objs)
    ctr = (lo + hi) * 0.5
    span = max(hi.x - lo.x, hi.z - lo.z)
    setup_world()
    ground_plane()
    add_area("key", ctr + Vector((-span * 1.15, span * 0.95, span * 1.20)),
             energy=span * span * 42, size=span * 0.70, color=(1.0, 0.92, 0.80), aim=ctr)
    add_area("fill", ctr + Vector((span * 1.45, -span * 0.55, span * 0.55)),
             energy=span * span * 12, size=span * 1.5, color=(0.62, 0.76, 1.0), aim=ctr)
    add_area("bounce", ctr + Vector((span * 0.15, span * 1.55, span * 0.10)),
             energy=span * span * 9, size=span * 1.6, color=(1.0, 0.90, 0.78), aim=ctr)
    # 门洞里的暖光只放在门洞里：放在院子里会在夯土上烧出一块白斑
    add_point("gate_lamp", (0.0, 3.55, 2.05), 42.0, (1.0, 0.62, 0.30), 0.50)


def main():
    os.makedirs(OUTSHOT, exist_ok=True)
    os.makedirs(OUTBLEND, exist_ok=True)

    # ── 曲面细分版（交付主图）──────────────────────────────────────────────
    clear_scene()
    objs, st = bs_model.build(smooth=True)
    print("STATS_SMOOTH", st)
    stage(objs)
    ctr, span = fit_span(objs, -38, 30, 1.08)
    shot("主图.png", objs, -38, 30, 1.08)
    shot("正面.png", objs, 0, 6, 1.04)
    shot("侧面.png", objs, 90, 6, 1.04, res=1100, samples=48)
    shot("背面.png", objs, 148, 28, 1.06, res=1100, samples=48)
    shot("俯视.png", objs, -40, 42, 1.06)
    pshot("训练场近景.png", (-6.8, 12.6, 7.4), (-1.2, 6.6, 0.4), lens=62,
          res=1200, samples=56)
    pshot("旗面近景.png", (-1.30, 1.85, 10.86), (-0.56, -1.06, 10.02), lens=88,
          res=1200, samples=56)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUTBLEND, "兵营.blend"))

    # ── 低模版（同主图机位）────────────────────────────────────────────────
    clear_scene()
    objs_l, st_l = bs_model.build(smooth=False)
    print("STATS_LOW", st_l)
    stage(objs_l)
    shot("低模对照.png", objs_l, -38, 30, 1.08, res=1100, samples=32,
         fixed=(ctr, span))
    print("DONE")


main()
