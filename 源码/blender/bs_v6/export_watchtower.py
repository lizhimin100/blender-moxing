"""export_watchtower.py —— 哨塔**唯一的导出入口**（标准档：低模 + 曲面细分）

    python build/bl_act.py act blender/bs_v6/export_watchtower.py

一条命令产出：低模版 + 细分版 + GLB 回查回执 + 几何工程文件。
CONFIG 是唯一真源；要加变体只改这里，不要另写第二条导出路径。
"""
import importlib
import json
import os
import sys

import bpy
from mathutils import Vector

HERE = r"D:/测试一/blender/bs_v6"
ROOT = r"D:/测试一"
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from assets_path import asset_path  # noqa: E402

for _m in ("bslib", "br_model", "wt_model"):
    if _m in sys.modules:
        importlib.reload(sys.modules[_m])
import wt_model  # noqa: E402

CONFIG = {
    "name": "哨塔",
    "version": "v1",
    "out_dir": asset_path("哨塔"),
    "blend_dir": os.path.join(ROOT, "blend", "哨塔"),
    "variants": [
        ("_低模", False, 18000),
        ("", True, 62000),
    ],
    "expected_materials": [
        "stone_light", "stone_mid", "stone_dark", "wood_mid", "wood_warm",
        "wood_dark", "roof", "roof_edge", "iron", "gold", "team", "team_trim",
        "coal", "glass", "ember", "flame_in", "earth", "paving", "moss",
    ],
    "unit": "m",
    "unwrap": True,
    "front_axis": "-Z",
}


def clear_scene():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for blk in (bpy.data.meshes, bpy.data.materials, bpy.data.images,
                bpy.data.armatures, bpy.data.actions, bpy.data.cameras,
                bpy.data.lights, bpy.data.collections):
        for it in list(blk):
            try:
                blk.remove(it)
            except Exception:
                pass


def export_glb(objs, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    for ob in objs:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    kw = dict(filepath=path, export_format="GLB", use_selection=True,
              export_yup=True, export_apply=False, export_materials="EXPORT",
              export_cameras=False, export_lights=False, export_extras=True,
              export_normals=True, export_tangents=False, export_texcoords=True)
    try:
        bpy.ops.export_scene.gltf(**kw)
    except TypeError:
        kw.pop("export_extras", None)
        bpy.ops.export_scene.gltf(**kw)
    bpy.ops.object.select_all(action="DESELECT")
    return os.path.getsize(path)


def verify_glb(path, expect_mats):
    clear_scene()
    bpy.ops.import_scene.gltf(filepath=path)
    objs = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    tris = 0
    lo = Vector((1e9, 1e9, 1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    for ob in objs:
        ob.data.calc_loop_triangles()
        tris += len(ob.data.loop_triangles)
        mw = ob.matrix_world
        for c in ob.bound_box:
            w = mw @ Vector(c)
            for i in range(3):
                lo[i] = min(lo[i], w[i])
                hi[i] = max(hi[i], w[i])
    names = sorted({m.name for o in objs for m in o.data.materials if m})
    return {
        "meshes": len(objs),
        "tris": tris,
        "materials": len(names),
        "materials_ok": set(names) == set(expect_mats),
        "missing_materials": sorted(set(expect_mats) - set(names)),
        "extra_materials": sorted(set(names) - set(expect_mats)),
        "bbox_min": [round(v, 3) for v in lo],
        "bbox_max": [round(v, 3) for v in hi],
        "size": [round(v, 3) for v in (hi - lo)],
        "grounded": abs(lo.z) <= 0.20,
        # 正面（+Y）有台阶、外梯与场地，比背墙一侧长
        "front_ok": bool(hi.y > abs(lo.y) * 1.05),
    }


def main():
    os.makedirs(CONFIG["out_dir"], exist_ok=True)
    os.makedirs(CONFIG["blend_dir"], exist_ok=True)
    receipt = {"asset": CONFIG["name"], "version": CONFIG["version"],
               "unit": CONFIG["unit"], "front_axis": CONFIG["front_axis"],
               "variants": {}}
    build_stats = {}
    ok = True

    for suffix, smooth, budget in CONFIG["variants"]:
        clear_scene()
        objs, st = wt_model.build(smooth=smooth, unwrap=CONFIG["unwrap"])
        build_stats[suffix or "smooth"] = st
        fname = CONFIG["name"] + suffix + ".glb"
        path = os.path.join(CONFIG["out_dir"], fname)
        size = export_glb(objs, path)
        v = verify_glb(path, CONFIG["expected_materials"])
        v.update({"file": fname, "bytes": size, "budget_tris": budget,
                  "over_budget": v["tris"] > budget})
        ok = ok and v["materials_ok"] and v["grounded"] and v["front_ok"] and not v["over_budget"]
        receipt["variants"][suffix or "smooth"] = v

    clear_scene()
    wt_model.build(smooth=True, unwrap=CONFIG["unwrap"])
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(CONFIG["blend_dir"],
                                                      CONFIG["name"] + "_几何.blend"))
    receipt["blend"] = CONFIG["name"] + "_几何.blend"
    receipt["topology"] = build_stats
    receipt["ok"] = ok
    print("EXPORT_RECEIPT " + json.dumps(receipt, ensure_ascii=False))


main()
