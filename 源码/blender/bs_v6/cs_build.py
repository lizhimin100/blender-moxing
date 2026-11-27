"""cs_build.py —— 单座建筑：导入 → 量体 → 工地套件 → 骨架 → 导出 → 参数表。

用法（Blender 进程内）：
    import cs_build
    cs_build.build_one("箭塔", detail="low")

输入只有 4 样（`docs/建造系统/契约/<建筑>.json`）：
    footprint / height / yaw / attach

v2 起：**建筑本体不切层、不绑骨、不加动画**，原样导出。
"从下往上长"由引擎侧世界 Z 遮罩完成，区间写进参数表 `reveal`。
资产目录只留交付物（GLB + 图标），参数 / 体检全部落在 `docs/建造系统/`。
"""
import importlib
import json
import os
import sys

import bpy

HERE = "D:/测试一/blender/bs_v6"
ROOT = "D:/测试一"
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from assets_path import asset_path  # noqa: E402

ASSET = asset_path()
DOCS = os.path.join(ROOT, "docs", "建造系统")
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import cs_kit
import cs_rig

importlib.reload(cs_kit)
importlib.reload(cs_rig)


def reset():
    """彻底清场。不用 read_homefile —— 那之后 join 的 poll 会失败（见 export_blend）。"""
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for c in list(bpy.data.collections):
        bpy.data.collections.remove(c)
    for blk in (bpy.data.meshes, bpy.data.materials, bpy.data.images,
                bpy.data.cameras, bpy.data.lights, bpy.data.armatures,
                bpy.data.actions, bpy.data.texts):
        for it in list(blk):
            try:
                blk.remove(it)
            except Exception:
                pass


def import_all(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    return [o for o in bpy.data.objects if o not in before and o.type == "MESH"]


def merge(objs, name="Building"):
    for o in bpy.data.objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    ob.name = name
    ob.data.name = name
    ob.select_set(False)
    return ob


def contract_path(cn):
    return os.path.join(DOCS, "契约", f"{cn}.json")


def params_path(cn, detail="low"):
    if detail == "low":
        return os.path.join(DOCS, "参数", f"{cn}.json")
    return os.path.join(DOCS, "参数", f"{cn}_{detail}.json")


def manifest_for(cn):
    """量出一座建筑的 4 个输入（已存在则读，不覆盖人工改过的值）。"""
    p = contract_path(cn)
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return None


def measure_manifest(cn, fn):
    reset()
    objs = import_all(os.path.join(asset_path(cn), fn))
    lo, hi, body = cs_rig.measure(objs)
    H = hi.z
    W, D = hi.x - lo.x, hi.y - lo.y
    m = {
        "id": cn,
        "src": fn,
        "footprint": [round(W, 3), round(D, 3)],
        "height": round(H, 3),
        "yaw": 0,
        "attach": {
            "hoist": [round(lo.x - 0.55, 3), round(lo.y - 0.30, 3),
                      round(min(3.4, 0.26 * H), 3)],
            "banner": [round(lo.x - cs_kit.SCAF_M, 3), round(hi.y + cs_kit.SCAF_M, 3), 0.0],
        },
        "body": [round(v, 3) for v in body],
        "bbox_lo": [round(v, 3) for v in lo],
        "bbox_hi": [round(v, 3) for v in hi],
    }
    os.makedirs(os.path.dirname(contract_path(cn)), exist_ok=True)
    with open(contract_path(cn), "w", encoding="utf-8") as f:
        json.dump(m, f, ensure_ascii=False, indent=2)
    return m


def build_one(cn, detail="low", shots=False, out_name=None):
    man = manifest_for(cn)
    if man is None:
        srcs = sorted(f for f in os.listdir(asset_path(cn))
                      if f.endswith("_手游_近.glb"))
        src = srcs[0] if srcs else f"{cn}_低模.glb"
        man = measure_manifest(cn, src)

    W, D = man["footprint"]
    H = man["height"]
    body = tuple(man["body"]) if man.get("body") else (-W / 2, W / 2, -D / 2, D / 2)

    reset()
    objs = import_all(os.path.join(asset_path(cn), man["src"]))
    src_tri = 0
    for o in objs:
        o.data.calc_loop_triangles()
    src_tri = sum(len(o.data.loop_triangles) for o in objs)
    src_verts = sum(len(o.data.vertices) for o in objs)
    building = merge(objs)

    kit = cs_kit.Kit(W, D, H, attach=man.get("attach"), body=body).build()
    kit.detail = detail
    arm, t_end, marks = cs_rig.build(building, kit, H, yaw=man.get("yaw", 0),
                                     detail=detail)

    out = out_name or f"{cn}_建造.glb"
    path = os.path.join(asset_path(cn), out)
    bpy.ops.export_scene.gltf(
        filepath=path,
        export_format="GLB",
        use_selection=False,
        export_yup=True,
        export_apply=False,
        export_animations=True,
        export_animation_mode="ACTIONS",
        export_anim_single_armature=True,
        export_force_sampling=True,
        export_bake_animation=False,
        export_anim_slide_to_zero=True,
        export_optimize_animation_size=True,
        export_skins=True,
        export_def_bones=False,
        export_leaf_bone=False,
        export_cameras=False,
        export_lights=False,
    )

    rep = dict(man)
    rep.update(marks)
    rep["file"] = out
    rep["bytes"] = os.path.getsize(path)
    rep["detail"] = detail
    rep["src_tris"] = src_tri
    rep["src_verts"] = src_verts

    import cs_check
    importlib.reload(cs_check)
    rep["check"] = cs_check.run(arm, building, bpy.data.objects["SiteKit"],
                                H, marks, src_tri, src_verts)

    os.makedirs(os.path.dirname(params_path(cn, detail)), exist_ok=True)
    with open(params_path(cn, detail), "w", encoding="utf-8") as f:
        json.dump(rep, f, ensure_ascii=False, indent=2)

    print(f"[{cn}] {os.path.basename(path)} {rep['bytes']/1024:.0f} KB "
          f"reveal {marks['z0']}→{H:.2f}m  t {marks['t_rev0']}→{marks['t_rev1']}s "
          f"lifts={marks['n_lifts']} end={t_end:.2f}s")
    return rep
