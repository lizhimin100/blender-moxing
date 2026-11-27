"""ch_teamshare.py —— 量块面剑士的阵营色可见占比（与前九座同一口径）

    python build/bl_act.py act blender/bs_v6/ch_teamshare.py

做法：同一个机位渲两张图 ——
    A. 全黑 + film_transparent → alpha 就是角色剪影
    B. 只把 team / team_trim 换成纯白自发光、其余全黑 → 白像素就是阵营色
占比 = B 的白像素 / A 的 alpha 像素。正视 / 3/4 / 俯视 各量一次。

角色的通过线是 **15–20%**（建筑是 6–9%）：角色小、盾面又是一整块大色块，
RTS 里认阵营主要靠它，所以口径必须比建筑高一档。
"""
import importlib
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = r"D:/测试一/blender/bs_v6"
ROOT = r"D:/测试一"
OUT = os.path.join(ROOT, "docs", "剑士", "v1", "探针")
if HERE not in sys.path:
    sys.path.insert(0, HERE)
for mod in ("bslib", "ch_model", "shotlib"):
    if mod in sys.modules:
        importlib.reload(sys.modules[mod])
import ch_model  # noqa: E402
import shotlib as S  # noqa: E402

RES = 640
CTR = Vector((0.0, 0.0, 1.285))
SPAN = 2.83


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


def render(path, az, el, res=RES):
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
    S.make_cam(CTR, SPAN, az, el)
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


def count(path, res=RES):
    img = bpy.data.images.load(path)
    px = list(img.pixels)
    sil = team = 0
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
    S.clear_scene()
    objs, st = ch_model.build(smooth=True, bevel=True)
    print("STATS", st)
    if bpy.context.scene.world is None:
        bpy.context.scene.world = bpy.data.worlds.new("W")
    bpy.context.scene.world.use_nodes = True
    bg = bpy.context.scene.world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Strength"].default_value = 0.0

    white = flat_mat("M_white", 1.0)
    black = flat_mat("M_black", 0.0)
    orig = {ob.name: (ob.data.materials[0] if ob.data.materials else None) for ob in objs}

    out = {}
    for tag, az, el in (("front", 0, 0), ("hero", -32, 20), ("top", -32, 56)):
        for ob in objs:
            for i in range(len(ob.data.materials)):
                ob.data.materials[i] = black
        render(os.path.join(OUT, "mask_%s_a.png" % tag), az, el)
        for ob in objs:
            nm = orig[ob.name].name if orig[ob.name] else ""
            mat = white if nm in ("team", "team_trim") else black
            for i in range(len(ob.data.materials)):
                ob.data.materials[i] = mat
        pb = os.path.join(OUT, "mask_%s_b.png" % tag)
        render(pb, az, el)
        sil, team, bands = count(pb)
        pct = 100.0 * team / max(sil, 1)
        out[tag] = {"pct": round(pct, 2), "bands": bands}
        print("[teamshare] %-5s silhouette=%d team_px=%d -> %.2f%%  bands=%s"
              % (tag, sil, team, pct, bands))
    print("TEAMSHARE " + repr(out))
    print("DONE")


main()
