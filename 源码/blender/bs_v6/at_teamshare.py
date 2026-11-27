"""at_teamshare.py —— 量箭塔的阵营色可见占比 + 高度分布（与前九座同一口径）

    python build/bl_act.py act blender/bs_v6/at_teamshare.py

做法：同一个机位渲两张图 ——
    A. 全黑 + film_transparent → alpha 就是建筑剪影
    B. 只把 team / team_trim 换成纯白自发光、其余全黑 → 白像素就是阵营色
占比 = B 的白像素 / A 的 alpha 像素。正视 / 3/4 / 俯视 各量一次，
并按画面高度把剪影切成三段（低 0–35% / 中 35–68% / 高 68–100%）看分布。
"""
import importlib
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = r"D:/测试一/blender/bs_v6"
ROOT = r"D:/测试一"
OUT = os.path.join(ROOT, "docs", "箭塔", "v2", "探针")
if HERE not in sys.path:
    sys.path.insert(0, HERE)
for mod in ("bslib", "br_model", "wt_model", "at_model"):
    if mod in sys.modules:
        importlib.reload(sys.modules[mod])
import at_model  # noqa: E402

RES = 640


def clear_scene():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for blk in (bpy.data.meshes, bpy.data.materials, bpy.data.images,
                bpy.data.cameras, bpy.data.lights):
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


def fit_span(objs, az, el, margin=1.06):
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


def make_cam(ctr, span, az, el):
    for ob in [o for o in bpy.context.scene.objects if o.type == "CAMERA"]:
        bpy.data.objects.remove(ob, do_unlink=True)
    cam = bpy.data.cameras.new("Cam")
    cam.type = "ORTHO"
    cam.ortho_scale = span
    ob = bpy.data.objects.new("Cam", cam)
    bpy.context.scene.collection.objects.link(ob)
    a, e = math.radians(az), math.radians(el)
    r = max(span * 4.0, 45.0)
    ob.location = ctr + Vector((math.sin(a) * math.cos(e) * r,
                                math.cos(a) * math.cos(e) * r,
                                math.sin(e) * r))
    ob.rotation_euler = (ctr - ob.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = ob


def flat_mat(name, strength):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (1, 1, 1, 1)
    em.inputs["Strength"].default_value = strength
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
    return m


def render(path, res=RES):
    sc = bpy.context.scene
    sc.render.resolution_x = res
    sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = True
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    sc.view_settings.view_transform = "Standard"
    for name in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            sc.render.engine = name
            break
        except TypeError:
            continue
    ee = getattr(sc, "eevee", None)
    if ee is not None and hasattr(ee, "taa_render_samples"):
        ee.taa_render_samples = 4
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


def count(path, res=RES):
    img = bpy.data.images.load(path)
    px = list(img.pixels)
    n = len(px) // 4
    sil = 0
    team = 0
    rows = []
    for y in range(res):
        s = t = 0
        base = y * res
        for x in range(res):
            i = (base + x) * 4
            if px[i + 3] > 0.5:
                s += 1
                if px[i] > 0.5 and px[i + 1] > 0.5 and px[i + 2] > 0.5:
                    t += 1
        rows.append((s, t))
        sil += s
        team += t
    bpy.data.images.remove(img)
    # rows[0] 是画面最底部（Blender 图像从下往上）
    ys = [y for y, (s, t) in enumerate(rows) if s > 0]
    bands = {}
    if ys:
        y0, y1 = ys[0], ys[-1]
        h = max(y1 - y0, 1)
        for name, a, b in (("low", 0.0, 0.35), ("mid", 0.35, 0.68), ("high", 0.68, 1.0)):
            ss = tt = 0
            for y in range(y0 + int(h * a), y0 + int(h * b) + 1):
                ss += rows[y][0]
                tt += rows[y][1]
            bands[name] = round(100.0 * tt / max(ss, 1), 2)
    return sil, team, bands


def main():
    os.makedirs(OUT, exist_ok=True)
    clear_scene()
    objs, st = at_model.build(smooth=True)
    print("STATS", st)
    if bpy.context.scene.world is None:
        bpy.context.scene.world = bpy.data.worlds.new("W")
    bpy.context.scene.world.use_nodes = True
    bg = bpy.context.scene.world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Strength"].default_value = 0.0

    white = flat_mat("M_white", 1.0)
    black = flat_mat("M_black", 0.0)
    orig = {ob.name: (ob.data.materials[0] if ob.data.materials else None)
            for ob in objs}

    out = {}
    for tag, az, el in (("front", 0, 0), ("hero", -34, 26), ("top", -32, 58)):
        for ob in objs:
            for i in range(len(ob.data.materials)):
                ob.data.materials[i] = black
        ctr, span = fit_span(objs, az, el)
        make_cam(ctr, span, az, el)
        pa = os.path.join(OUT, "mask_%s_a.png" % tag)
        render(pa)
        for ob in objs:
            nm = orig[ob.name].name if orig[ob.name] else ""
            mat = white if nm in ("team", "team_trim") else black
            for i in range(len(ob.data.materials)):
                ob.data.materials[i] = mat
        pb = os.path.join(OUT, "mask_%s_b.png" % tag)
        render(pb)
        sil, team, bands = count(pb)
        pct = 100.0 * team / max(sil, 1)
        out[tag] = {"pct": round(pct, 2), "bands": bands}
        print("[teamshare] %-5s silhouette=%d team_px=%d -> %.2f%%  bands=%s"
              % (tag, sil, team, pct, bands))
    print("TEAMSHARE " + repr(out))
    print("DONE")


main()
