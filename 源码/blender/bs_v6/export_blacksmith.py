"""
export_blacksmith.py —— 铁匠铺**唯一的导出入口**

     python build/bl_rt.py act blender/bs_v6/export_blacksmith.py

做四件事，跑完打印一条 JSON 回执：
  ① 建低模 / 平滑两版（形体只在这里定尺寸）
  ② 导出 GLB 到 assets/godot/blacksmith_v6/
  ③ **重新导入**刚导出的 GLB 回查（材质名集合 / 三角面 / 贴地 / 朝向 / 面数预算）
  ④ 把 .blend 工程存到 blend/bs_v6/

以后要加阵营变体、加 LOD、改成 FBX，都只改这一个文件的 CONFIG，
不要再往别处写第二条导出路径。

v8 说明：模型在本轮不要求导出，但**出口只有一个**这件事必须保持 ——
    python build/bl_rt.py act blender/bs_v6/export_blacksmith.py
一条命令同时产出「低模版 + 细分版 + 回查回执 + 工程文件」。
"""
import json
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else r"D:/测试一/blender/bs_v6"
ROOT = r"D:/测试一"
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from assets_path import asset_path  # noqa: E402

import importlib

import bslib  # noqa: E402
import bs_model  # noqa: E402

# 常驻内核会缓存模块：每次导出前强制重载，否则改完代码还跑老版本
for _m in ("bslib", "bs_model"):
    if _m in sys.modules:
        importlib.reload(sys.modules[_m])

# ── CONFIG（唯一真源）────────────────────────────────────────────────────────
CONFIG = {
    "name": "铁匠铺",
    "version": "v10",
    "out_dir": asset_path("铁匠铺"),
    "blend_dir": os.path.join(ROOT, "blend", "铁匠铺"),
    "variants": [
        # (文件名后缀, smooth?, 三角面预算)
        ("_低模", False, 18000),
        ("", True, 62000),
    ],
    "expected_materials": [
        "stone_light", "stone_mid", "stone_dark", "roof", "roof_edge", "roof_wood",
        "wood_warm", "wood_dark", "iron", "gold", "team", "team_trim",
        "coal", "ember", "flame_out", "flame_in", "glow",
        # v10：前场地面分层（夯土 / 铺石 / 草簇）与兵营同一套地面语汇
        "earth", "paving", "moss",
    ],
    "unit": "m",
    # 拓扑/贴图规范：默认摊一套 UV（以后上图集/贴花/烘 AO 直接可用）。
    # 没有贴图需求时可以关掉，低模省 ~140 KB、细分省 ~420 KB。
    "unwrap": True,
    "front_axis": "-Z",          # 导出后正面朝 −Z（Blender 建模期朝 +Y）
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
    """重新导入刚导出的 GLB，独立回查（不复用内存里的对象）。"""
    clear_scene()
    bpy.ops.import_scene.gltf(filepath=path)
    objs = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    tris = 0
    lo = Vector((1e9, 1e9, 1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    fire_lo = Vector((1e9, 1e9, 1e9))
    fire_hi = Vector((-1e9, -1e9, -1e9))
    has_fire = False
    for ob in objs:
        ob.data.calc_loop_triangles()
        tris += len(ob.data.loop_triangles)
        mw = ob.matrix_world
        for c in ob.bound_box:
            w = mw @ Vector(c)
            for i in range(3):
                lo[i] = min(lo[i], w[i])
                hi[i] = max(hi[i], w[i])
        mats = {m.name for m in ob.data.materials if m}
        if mats & {"flame_out", "flame_in", "ember"}:
            has_fire = True
            for c in ob.bound_box:
                w = mw @ Vector(c)
                for i in range(3):
                    fire_lo[i] = min(fire_lo[i], w[i])
                    fire_hi[i] = max(fire_hi[i], w[i])
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
        "grounded": abs(lo.z) <= 0.05,
        # glTF → Blender 会把 −Z（正面）映回 +Y：炉火必须落在 +Y 侧
        "front_ok": bool(has_fire and (fire_lo.y + fire_hi.y) * 0.5 > 1.0),
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
        objs, st = bs_model.build(smooth=smooth, unwrap=CONFIG["unwrap"])
        build_stats[suffix or "smooth"] = st
        fname = CONFIG["name"] + suffix + ".glb"
        path = os.path.join(CONFIG["out_dir"], fname)
        size = export_glb(objs, path)
        v = verify_glb(path, CONFIG["expected_materials"])
        v.update({"file": fname, "bytes": size, "budget_tris": budget,
                  "over_budget": v["tris"] > budget})
        ok = ok and v["materials_ok"] and v["grounded"] and v["front_ok"] and not v["over_budget"]
        receipt["variants"][suffix or "smooth"] = v

    # 工程文件（平滑版）
    clear_scene()
    objs, _ = bs_model.build(smooth=True, unwrap=CONFIG["unwrap"])
    # 注意：这里存的是"纯几何版"（没有相机 / 灯光 / 世界），
    # 展示用的 blacksmith_v8.blend 由 bs_shots.py 负责存（带完整布光与相机）。
    # 两者分开，避免导出把演示场景覆盖成一份"打开全是灰模"的文件。
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(CONFIG["blend_dir"],
                                                      CONFIG["name"] + "_几何.blend"))
    receipt["blend"] = CONFIG["name"] + "_几何.blend"
    receipt["topology"] = build_stats
    receipt["ok"] = ok
    print("EXPORT_RECEIPT " + json.dumps(receipt, ensure_ascii=False))


main()
