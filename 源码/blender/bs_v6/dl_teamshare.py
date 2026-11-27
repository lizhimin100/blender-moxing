"""dl_teamshare.py —— 新资产的阵营色可见占比（与九座同一口径）

    blender -b --python blender/bs_v6/dl_teamshare.py

同一个机位渲两张：A 剪影 alpha；B 只把 team/team_trim 换成纯白自发光。
占比 = B 白像素 / A alpha 像素；按画面高度切三段看分布。
"""
import importlib
import json
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = r"D:/测试一/blender/bs_v6"
ROOT = r"D:/测试一"
if HERE not in sys.path:
    sys.path.insert(0, HERE)
for m in ("bslib", "dl_kit", "dl_parts", "dg_layout", "dg_model", "uc_model",
          "tv_model", "fr_model", "fs_model"):
    if m in sys.modules:
        importlib.reload(sys.modules[m])
import dg_model  # noqa: E402
import uc_model  # noqa: E402
import tv_model  # noqa: E402
import fr_model  # noqa: E402
import fs_model  # noqa: E402

RES = 520
ASSETS = [("地牢", dg_model, {}), ("折壳入口", fs_model, {}), ("地下城入口", uc_model, {}),
          ("酒馆内部", tv_model, {}),
          ("营火", fr_model.module_for("营火"), {"name": "营火"}),
          ("火把", fr_model.module_for("火把"), {"name": "火把"}),
          ("火炬", fr_model.module_for("火炬"), {"name": "火炬"}),
          ("火堆", fr_model.module_for("火堆"), {"name": "火堆"})]
VIEWS = [("正", 0, 8), ("三四", -34, 28), ("俯", -34, 56)]


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
    cam = bpy.data.cameras.new("Cam")
    cam.type = "ORTHO"
    cam.ortho_scale = span
    ob = bpy.data.objects.new("Cam", cam)
    bpy.context.scene.collection.objects.link(ob)
    a, e = math.radians(az), math.radians(el)
    r = max(span * 4.0, 45.0)
    ob.location = ctr + Vector((math.sin(a) * math.cos(e) * r,
                                math.cos(a) * math.cos(e) * r, math.sin(e) * r))
    ob.rotation_euler = (ctr - ob.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = ob


def flat_mat(name, strength=1.0):
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


def render(path):
    sc = bpy.context.scene
    sc.render.resolution_x = RES
    sc.render.resolution_y = RES
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


def read_px(path):
    img = bpy.data.images.load(path)
    n = RES * RES
    buf = [0.0] * (n * 4)
    img.pixels.foreach_get(buf)
    bpy.data.images.remove(img)
    return buf


def run(cn, mod, kw):
    clear_scene()
    if kw:
        m = mod.Model(False, unwrap=False)
        m = m.build()
    else:
        m = mod.Model(False, unwrap=False).build()
    objs = m.finalize(bevel=True)
    names = [o.data.materials[0].name if o.data.materials else "" for o in objs]
    tmp = os.path.join(ROOT, "docs", cn, "v1", "_mask")
    os.makedirs(tmp, exist_ok=True)
    out = {}
    black = flat_mat("_black", 0.0)
    white = flat_mat("_white", 3.0)
    for tag, az, el in VIEWS:
        ctr, span = fit_span(objs, az, el)
        make_cam(ctr, span, az, el)
        for o in objs:
            o.data.materials.clear()
            o.data.materials.append(black)
        pa = os.path.join(tmp, "a.png")
        render(pa)
        for o, nm in zip(objs, names):
            o.data.materials.clear()
            o.data.materials.append(white if nm in ("team", "team_trim") else black)
        pb = os.path.join(tmp, "b.png")
        render(pb)
        a_buf = read_px(pa)
        b_buf = read_px(pb)
        sil = sum(1 for i in range(RES * RES) if a_buf[i * 4 + 3] > 0.5)
        team = 0
        seg = [0, 0, 0]
        for y in range(RES):
            row = y * RES
            for x in range(RES):
                i = (row + x) * 4
                if b_buf[i] > 0.6 and b_buf[i + 3] > 0.5:
                    team += 1
                    seg[min(2, y * 3 // RES)] += 1
        out[tag] = {"silhouette": sil, "team": team,
                    "ratio": round(100.0 * team / max(sil, 1), 2),
                    "seg": [round(100.0 * v / max(team, 1), 1) for v in seg]}
    print("TEAM", cn, json.dumps(out, ensure_ascii=False))
    return out


res = {}
for cn, mod, kw in ASSETS:
    res[cn] = run(cn, mod, kw)
p = os.path.join(ROOT, "docs", "新资产阵营色.json")
with open(p, "w", encoding="utf-8") as f:
    json.dump(res, f, ensure_ascii=False, indent=2)
print("TEAMSHARE_DONE " + json.dumps(res, ensure_ascii=False))
