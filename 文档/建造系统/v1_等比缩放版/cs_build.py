"""cs_build.py —— 单座建筑：导入 → 量体 → 工地套件 → 骨架 → 导出 → 参数表。

用法（Blender 进程内）：
    import cs_build
    cs_build.build_one("箭塔", detail="low", shots=True)

输入只有 4 样（见 assets/<建筑>/建造.json）：
    footprint / height / yaw / attach
本脚本负责把 footprint 之外的东西全部推出来。
"""
import importlib
import json
import math
import os
import sys

import bpy

HERE = "D:/测试一/blender/bs_v6"
ROOT = "D:/测试一"
ASSET = os.path.join(ROOT, "assets")
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


def manifest_for(cn, fn=None):
    """量出一座建筑的 4 个输入（已存在则读，不覆盖人工改过的值）。"""
    p = os.path.join(ASSET, cn, "建造.json")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return None


def measure_manifest(cn, fn):
    reset()
    objs = import_all(os.path.join(ASSET, cn, fn))
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
    with open(os.path.join(ASSET, cn, "建造.json"), "w", encoding="utf-8") as f:
        json.dump(m, f, ensure_ascii=False, indent=2)
    return m


def build_one(cn, detail="low", shots=False, out_name=None):
    man = manifest_for(cn)
    if man is None:
        srcs = [f for f in os.listdir(os.path.join(ASSET, cn)) if f.endswith("_手游_近.glb")]
        src = srcs[0] if srcs else f"{cn}_低模.glb"
        man = measure_manifest(cn, src)

    W, D = man["footprint"]
    H = man["height"]
    body = tuple(man["body"]) if man.get("body") else (-W / 2, W / 2, -D / 2, D / 2)

    reset()
    objs = import_all(os.path.join(ASSET, cn, man["src"]))
    building = merge(objs)
    edges = cs_rig.band_edges(H)
    kit = cs_kit.Kit(W, D, H, edges, attach=man.get("attach"), body=body).build()
    kit.detail = detail
    arm, t_end, marks = cs_rig.build(building, kit, edges, yaw=man.get("yaw", 0),
                                     detail=detail)

    out = out_name or f"{cn}_建造.glb"
    path = os.path.join(ASSET, cn, out)
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
    pj = "建造参数.json" if detail == "low" else f"建造参数_{detail}.json"
    with open(os.path.join(ASSET, cn, pj), "w", encoding="utf-8") as f:
        json.dump(rep, f, ensure_ascii=False, indent=2)

    print(f"[{cn}] {os.path.basename(path)} {rep['bytes']/1024:.0f} KB "
          f"t_end={t_end:.2f}s bands={marks['n_bands']} lifts={marks['n_lifts']}")

    import cs_check
    importlib.reload(cs_check)
    chk = cs_check.run(arm, bpy.data.objects["Building"], bpy.data.objects["SiteKit"],
                       edges, marks, os.path.join(ASSET, cn, "建造体检.json"))
    rep["check"] = chk

    if shots:
        shot_frames(cn, t_end, marks)
    pj = "建造参数.json" if detail == "low" else f"建造参数_{detail}.json"
    with open(os.path.join(ASSET, cn, pj), "w", encoding="utf-8") as f:
        json.dump(rep, f, ensure_ascii=False, indent=2)
    return rep


# ── 关键帧出图（在同一个场景里，导出后跑）──
SHOT_T = (0.16, 0.34, 0.55, 0.75, 0.92)


def shot_frames(cn, t_end, marks):
    import shotlib as S
    importlib.reload(S)
    out = os.path.join(ROOT, "docs", "建造系统", cn)
    os.makedirs(out, exist_ok=True)
    S.OUTSHOT = out
    S.setup_world()
    ground = S.ground_plane()
    objs = [o for o in bpy.context.scene.objects if o.type == "MESH" and o is not ground]
    S.RES, S.SAMP = 1100, 48
    sc = bpy.context.scene
    for i, f in enumerate(SHOT_T):
        t = round(t_end * f, 2)
        sc.frame_set(int(t * cs_rig.FPS))
        S.shot(f"{cn}_建造_{i}_{t:.2f}s.png", objs, -34, 26, 1.10)
    sc.frame_set(int(t_end * cs_rig.FPS))
    S.shot(f"{cn}_完成.png", objs, -34, 26, 1.10)
    sc.frame_set(int((marks["dismantle"] - 0.12) * cs_rig.FPS))
    S.shot(f"{cn}_俯视_施工.png", objs, -34, 58, 1.10)
