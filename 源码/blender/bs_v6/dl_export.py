"""dl_export.py —— 新资产的标准档导出：**低模 + 曲面细分** 两个 GLB

    blender -b --python blender/bs_v6/dl_export.py

产物（与九座同名同结构）：
    assets/<资产>/<资产>.glb        曲面细分版（宣传 / 端游）
    assets/<资产>/<资产>_低模.glb   低模版（手游 / 引擎默认）

注意：**不写 .blend、不写图集**——这份包只交付 GLB + 图标（assets 里不放中间产物）。
手游三档走 export_mobile.py（图集 + 三级 LOD）。
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
for m in ("bslib", "br_model", "wt_model", "dl_kit", "dl_parts", "dg_layout",
          "dg_model", "uc_model",
          "tv_model", "fr_model", "fs_model"):
    if m in sys.modules:
        importlib.reload(sys.modules[m])
import dg_model  # noqa: E402
import uc_model  # noqa: E402
import tv_model  # noqa: E402
import fr_model  # noqa: E402
import fs_model  # noqa: E402

TARGETS = {
    "地牢": {"mod": dg_model, "kw": {}, "prefix": "DG",
             "expect": ["ancient", "ancient_pale", "ancient_mid", "ancient_dark",
                        "moss_dark",
                        "bronze", "bronze_dark", "wood_dark", "wood_mid", "wood_warm",
                        "iron", "team", "team_trim", "coal", "ember",
                        "flame_out", "flame_in", "depth_glow", "paving", "earth",
                        "earth_dark", "stone_mid"],
             "front": 0.95},
    "地下城入口": {"mod": uc_model, "kw": {}, "prefix": "UC",
               "expect": ["ancient", "ancient_pale", "ancient_mid", "ancient_dark",
                        "moss_dark",
                          "bronze", "bronze_dark", "wood_dark", "wood_mid", "wood_warm",
                          "team", "team_trim", "coal", "ember", "flame_out", "flame_in",
                          "depth_glow", "paving", "earth", "earth_dark", "stone_mid",
                          "cloth_cream", "iron"],
               "front": 1.0},
    "酒馆内部": {"mod": tv_model, "kw": {}, "prefix": "TV",
              "expect": ["plaster", "copper", "cloth_cream", "ash", "ancient_dark",
                         "wood_dark", "wood_mid", "wood_warm", "stone_mid", "stone_light",
                         "iron", "team", "team_trim", "glass", "glow", "coal",
                         "ember", "flame_out", "flame_in"],
              "front": 1.0},
    "营火": {"mod": fr_model.module_for("营火"), "kw": {"name": "营火"}, "prefix": "CF",
           "expect": [], "front": 0.90},
    "火把": {"mod": fr_model.module_for("火把"), "kw": {"name": "火把"}, "prefix": "TR",
           "expect": [], "front": 0.90},
    "火炬": {"mod": fr_model.module_for("火炬"), "kw": {"name": "火炬"}, "prefix": "BZ",
           "expect": [], "front": 0.90},
    "火堆": {"mod": fr_model.module_for("火堆"), "kw": {"name": "火堆"}, "prefix": "BF",
           "expect": [], "front": 0.90},
    "折壳入口": {"mod": fs_model, "kw": {}, "prefix": "FS",
             "expect": ["ancient", "ancient_pale", "ancient_dark", "bone",
                        "bone_dark", "void", "door_stone", "moss_dark", "earth",
                        "earth_dark", "paving", "bronze", "wood_dark", "wood_mid",
                        "wood_warm", "team", "team_trim", "depth_glow",
                        "flame_out", "flame_in", "ember"],
             # 壳的体量天生在后侧（前场只有踏步与落石），比值 0.55 只用来判"没转 180°"
             "front": 0.55},
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


def verify(path, front):
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
    return {"meshes": len(objs), "tris": tris, "materials": names,
            "mat_count": len(names),
            "bbox_min": [round(v, 3) for v in lo],
            "bbox_max": [round(v, 3) for v in hi],
            "size": [round(v, 3) for v in (hi - lo)],
            "grounded": abs(lo.z) <= 0.06,
            "front_ok": bool(hi.y >= abs(lo.y) * front - 0.001)}


def build_one(cn, cfg):
    rec = {"asset": cn, "variants": {}, "ok": True}
    for suffix, smooth in (("_低模", False), ("", True)):
        clear_scene()
        if cfg["kw"]:
            m = cfg["mod"].Model(smooth, unwrap=True)
            m = m.build()
        else:
            m = cfg["mod"].Model(smooth, unwrap=True).build()
        objs = m.finalize(bevel=True)
        fname = cn + suffix + ".glb"
        path = asset_path(cn, fname)
        size = export_glb(objs, path)
        v = verify(path, cfg["front"])
        v.update({"file": fname, "bytes": size})
        rec["variants"][fname] = v
        if not (v["grounded"] and v["front_ok"]):
            rec["ok"] = False
        if cfg["expect"]:
            missing = sorted(set(cfg["expect"]) - set(v["materials"]))
            v["missing_materials"] = missing
    return rec


# 只重导列在这里的资产；设成 None 就是全部重导（改共用调色板时才需要）
RUN = ("地牢",)


def main():
    out = {"assets": {}, "ok": True}
    for cn, cfg in TARGETS.items():
        if RUN and cn not in RUN:
            continue
        r = build_one(cn, cfg)
        out["assets"][cn] = r
        out["ok"] = out["ok"] and r["ok"]
        print("[%s] %s" % (cn, {k: (v["tris"], v["bytes"], v["size"])
                                for k, v in r["variants"].items()}))
    print("DL_EXPORT_RECEIPT " + json.dumps(out, ensure_ascii=False))


main()
