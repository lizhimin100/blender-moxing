"""export_new_assets.py —— 新增建筑（城镇大厅二本 / 帐篷三级）的标准档导出

    blender -b --factory-startup --python blender/bs_v6/export_new_assets.py -- 城镇大厅二本

一条命令产出（与九座同名同结构）：
    assets/建筑/联盟/<名>/<名>_低模.glb     低模（引擎默认 / 手游形）
    assets/建筑/联盟/<名>/<名>.glb          曲面细分（宣传 / 端游）

为什么单独一支：`export_watchtower.py` 这类脚本是"一座一个 CONFIG"，
新增建筑若各写一份会把量体 / 回查的口径复制四遍。这里只保留一份，
TARGETS 里加一行就接上了。

**不做**手游三档与 .blend —— 那两个走 export_mobile.py / export_blend.py
（它们的 material/UV 通路与这里不同，混在一起会把图集写花）。
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

for _m in ("bslib", "br_model", "keep_model", "tent_model"):
    if _m in sys.modules:
        try:
            importlib.reload(sys.modules[_m])
        except Exception:
            pass

import keep_model  # noqa: E402
import tent_model  # noqa: E402

TARGETS = {
    "城镇大厅二本": {"mod": keep_model, "note": "二本·石木戍堡（Keep）"},
    # 帐篷三级的 Model 按 tier 走不同语法（不是缩放同一套几何），build_one 里
    # 走 `build_tier` 分支；`front` 0.95 —— 三顶帐篷的地钉在 ±Y 对称，
    # 包围盒比值恒为 1.0，这一项只用来判"没有整体转 180°"。
    "初级帐篷": {"mod": tent_model, "front": 0.95,
             "note": "初级帐篷 · 6 边锥 + 中柱 + 4 根斜拉绳"},
    "中等帐篷": {"mod": tent_model, "front": 0.95,
             "note": "中等帐篷 · 两面坡脊帐 + 前檐披 + 6 根地钉"},
    "豪华帐篷": {"mod": tent_model, "front": 0.95,
             "note": "豪华帐篷 · 木地台 + 四坡顶 + 内衬 + 双旗杆"},
}
RUN = ("城镇大厅二本",)
BUDGET = (24000, 70000)      # (低模, 细分)


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
              export_normals=True, export_tangents=False, export_texcoords=True,
              export_animations=False, export_skins=False)
    bpy.ops.export_scene.gltf(**kw)
    bpy.ops.object.select_all(action="DESELECT")
    return os.path.getsize(path)


def verify(path, front=1.0):
    clear_scene()
    bpy.ops.import_scene.gltf(filepath=path)
    objs = [o for o in bpy.context.scene.objects if o.type == "MESH" and any(o.data.materials)]
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
            "grounded": abs(lo.z) <= 0.12,
            "front_ok": bool(hi.y >= abs(lo.y) * front - 0.001)}


def build_one(key):
    cfg = TARGETS[key]
    mod = cfg["mod"]
    out_dir = asset_path(key)
    rec = {"asset": key, "note": cfg["note"], "variants": {}, "ok": True}
    for suffix, smooth, budget in (("_低模", False, BUDGET[0]), ("", True, BUDGET[1])):
        clear_scene()
        # 帐篷三级的 geometry 由 tier 决定（不是同一个 Model 的缩放），
        # 走模块自带的 build_tier(name, smooth)；其余建筑仍是 Model(smooth).build()
        if hasattr(mod, "build_tier"):
            m = mod.build_tier(key, smooth=smooth)
        else:
            m = mod.Model(smooth, unwrap=False).build()
        objs = m.finalize(bevel=True)
        fname = key + suffix + ".glb"
        path = os.path.join(out_dir, fname)
        size = export_glb(objs, path)
        v = verify(path, front=cfg.get("front", 1.06))
        v.update({"file": fname, "bytes": size, "budget": budget,
                  "over_budget": v["tris"] > budget,
                  "materials_ok": v["mat_count"] <= 22})  # 桌面档材质不压缩（4 材质是手游档 / 状态档的口径）
        rec["variants"][fname] = v
        if not (v["grounded"] and v["front_ok"] and v["materials_ok"]):
            rec["ok"] = False
        print("[%s] %-18s tris=%-6d mats=%-3d size=%s %s" %
              (key, fname, v["tris"], v["mat_count"], v["size"],
               "OK" if (v["grounded"] and v["front_ok"]) else "FAIL"))
    return rec


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    keys = argv or list(RUN)
    out = {"buildings": {}, "ok": True}
    for key in keys:
        r = build_one(key)
        out["buildings"][key] = r
        out["ok"] = out["ok"] and r["ok"]
    os.makedirs(os.path.join(ROOT, "docs", "状态资产"), exist_ok=True)
    with open(os.path.join(ROOT, "docs", "状态资产", "_新建筑导出.json"), "w",
              encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("NEW_EXPORT_RECEIPT " + json.dumps(
        {k: v["ok"] for k, v in out["buildings"].items()}, ensure_ascii=False))


main()
