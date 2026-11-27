"""export_char.py —— 第十座（块面剑士）唯一导出入口

    python build/bl_act.py act blender/bs_v6/export_char.py

和建筑的区别只有三条，别的都一样：

  ① **不对称件不走镜像**：盾/剑在 `finalize()` 里镜像之后才生成，
     挂 `shield.L` / `weapon.R` 两根骨（见 ch_model 顶部说明）。
  ② **图集是角色自己的 4×4**（`ch_atlas.CH_LAYOUT`），不与建筑共用。
  ③ **三个材质**（主体 / team / team_trim），没有自发光。

产物（`assets/剑士/`）：
    剑士.glb              曲面细分版（宣传 / 端游）
    剑士_低模.glb          未合图集的低模（对照）
    剑士_手游_近/中/远.glb  图集 + 三级 LOD（默认用近）
    图集/主体.png · ORM.png
    剑士.blend            打包贴图的工程文件
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

OUT_DIR = asset_path("剑士")
if HERE not in sys.path:
    sys.path.insert(0, HERE)
for _m in ("bslib", "bs_atlas", "ch_atlas", "ch_model"):
    if _m in sys.modules:
        importlib.reload(sys.modules[_m])
import bs_atlas  # noqa: E402
import ch_atlas  # noqa: E402
import ch_model  # noqa: E402

KEY = "剑士"
PREFIX = "CH"
BUDGETS = (14000, 7000, 3000)
MAX_MATERIALS = 4
FRONT_RATIO = 1.02          # 正面 = 盾牌探出的 +Y 一侧（0.33 / 0.22）


def clear_scene():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for blk in (bpy.data.meshes, bpy.data.materials, bpy.data.images,
                bpy.data.cameras, bpy.data.lights, bpy.data.armatures):
        for it in list(blk):
            try:
                blk.remove(it)
            except Exception:
                pass


def export_glb(objs, path, extra=()):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    # 清场：只留要导的对象。`use_selection` 在 5.2 上不可靠 —— 启动文件里
    # 遗留的一个 icosphere 被塞进了 GLB，回查时 bbox 变成 ±1（踩过）。
    keep = {ob.name for ob in list(objs) + list(extra)}
    for ob in list(bpy.data.objects):
        if ob.name not in keep:
            bpy.data.objects.remove(ob, do_unlink=True)
    bpy.ops.object.select_all(action="DESELECT")
    for ob in list(objs) + list(extra):
        ob.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    kw = dict(filepath=path, export_format="GLB", use_selection=True,
              export_yup=True, export_apply=False, export_materials="EXPORT",
              export_cameras=False, export_lights=False, export_extras=True,
              export_normals=True, export_tangents=False, export_texcoords=True,
              export_skins=True, export_def_bones=False,
              export_image_format="AUTO")
    try:
        bpy.ops.export_scene.gltf(**kw)
    except TypeError:
        for k in ("export_extras", "export_def_bones"):
            kw.pop(k, None)
        bpy.ops.export_scene.gltf(**kw)
    bpy.ops.object.select_all(action="DESELECT")
    return os.path.getsize(path)


def verify(path):
    """重新导入回查：材质数 / 三角面 / 贴地 / 朝向 / 骨骼 / 顶点组。"""
    clear_scene()
    bpy.ops.import_scene.gltf(filepath=path)
    def _helper(ob):
        # glTF 导入器会为了"骨骼自定义形状"造一个 icosphere 放进
        # `glTF_not_exported` 集合 —— 它不是资产的一部分，不能进 bbox
        return any(c.name.startswith("glTF_not_exported") for c in ob.users_collection)

    objs = [o for o in bpy.context.scene.objects
            if o.type == "MESH" and len(o.data.vertices) and not _helper(o)]
    arms = [o for o in bpy.context.scene.objects
            if o.type == "ARMATURE" and not _helper(o)]
    tris = 0
    lo = Vector((1e9, 1e9, 1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    has_tex = False
    groups = set()
    for ob in objs:
        ob.data.calc_loop_triangles()
        tris += len(ob.data.loop_triangles)
        mw = ob.matrix_world
        for c in ob.bound_box:
            w = mw @ Vector(c)
            for i in range(3):
                lo[i] = min(lo[i], w[i])
                hi[i] = max(hi[i], w[i])
        for m in ob.data.materials:
            if m and m.use_nodes and any(n.type == "TEX_IMAGE" for n in m.node_tree.nodes):
                has_tex = True
        groups.update(g.name for g in ob.vertex_groups)
    names = sorted({m.name for o in objs for m in o.data.materials if m})
    return {
        "meshes": len(objs),
        "armatures": len(arms),
        "bones": len(arms[0].data.bones) if arms else 0,
        "vgroups": len(groups),
        "materials": names,
        "surfaces": len(names),
        "tris": tris,
        "bbox_min": [round(v, 3) for v in lo],
        "bbox_max": [round(v, 3) for v in hi],
        "size": [round(v, 3) for v in (hi - lo)],
        "grounded": abs(lo.z) <= 0.05,
        "front_ok": bool(hi.y > abs(lo.y) * FRONT_RATIO),
        "has_texture": has_tex,
    }


def build_layer(level, bevel):
    """建一层：level=0/1/2 → 手游三档。返回 (objs, 构件数, 材质字典)。"""
    clear_scene()
    imgs = None
    if level is not None:
        imgs = {}
        for tag, p in ATLAS_PATHS.items():
            img = bpy.data.images.load(p, check_existing=False)
            img.colorspace_settings.name = "sRGB" if tag != "ORM" else "Non-Color"
            imgs[tag] = img
        m = ch_model.Model(False, level).build()
        m.items = ch_atlas.filter_lod(m.items, level)
        parts = len(m.items)
        objs = m.finalize(bevel=bevel, rig=False)
        ch_atlas.pin_uv(objs)
        objs = ch_atlas.pack(objs, imgs, prefix=PREFIX)
        ch_model.build_armature(objs)
        return objs, parts
    raise ValueError


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    receipt = {"asset": KEY, "ok": True, "variants": {}, "standard": {}}

    # ── ① 图集（每座一份，改角色不牵连建筑）──
    atlas_dir = os.path.join(OUT_DIR, "图集")
    imgs0 = ch_atlas.build_images(atlas_dir, label=KEY)
    global ATLAS_PATHS
    ATLAS_PATHS = {k: v.filepath for k, v in imgs0.items()}
    receipt["atlas"] = {k: os.path.basename(p) for k, p in ATLAS_PATHS.items()}

    # ── ② 标准档：细分版 + 低模（14 材质，未合图集）──
    for tag, smooth, bevel, fname in (("smooth", True, True, "%s.glb" % KEY),
                                      ("low", False, True, "%s_低模.glb" % KEY)):
        clear_scene()
        objs, st = ch_model.build(smooth=smooth, unwrap=True, bevel=bevel)
        path = os.path.join(OUT_DIR, fname)
        size = export_glb(objs, path, extra=[o for o in bpy.context.scene.objects
                                             if o.type == "ARMATURE"])
        v = verify(path)
        v.update({"file": fname, "bytes": size, "build_tris": st["tris"]})
        receipt["standard"][fname] = v
        if not (v["grounded"] and v["front_ok"] and v["armatures"]):
            receipt["ok"] = False

    # ── ③ 手游三档（图集 + LOD）──
    for level, fname, budget in ((0, "%s_手游_近.glb" % KEY, BUDGETS[0]),
                                 (1, "%s_手游_中.glb" % KEY, BUDGETS[1]),
                                 (2, "%s_手游_远.glb" % KEY, BUDGETS[2])):
        objs, parts = build_layer(level, bevel=(level == 0))
        path = os.path.join(OUT_DIR, fname)
        size = export_glb(objs, path, extra=[o for o in bpy.context.scene.objects
                                             if o.type == "ARMATURE"])
        v = verify(path)
        v.update({"file": fname, "bytes": size, "build_parts": parts,
                  "budget_tris": budget, "over_budget": v["tris"] > budget,
                  "materials_ok": v["surfaces"] <= MAX_MATERIALS})
        receipt["variants"][fname] = v
        if not (v["materials_ok"] and v["grounded"] and v["front_ok"]
                and not v["over_budget"] and v["has_texture"] and v["armatures"]):
            receipt["ok"] = False

    # ── ④ .blend（打包贴图的工程文件）──
    clear_scene()
    imgs = {}
    for tag, p in ATLAS_PATHS.items():
        img = bpy.data.images.load(p, check_existing=False)
        img.colorspace_settings.name = "sRGB" if tag != "ORM" else "Non-Color"
        imgs[tag] = img
    m = ch_model.Model(False, 0).build()
    objs = m.finalize(bevel=True, rig=False)
    ch_atlas.pin_uv(objs)
    objs = ch_atlas.pack(objs, imgs, prefix=PREFIX)
    ch_model.build_armature(objs)
    txt = bpy.data.texts.new("读我")
    txt.write(
        "块面剑士（第十座）\n"
        "1 unit = 1 m；原点在双足中间，z=0 是地面；正面朝 +Y（导出 glTF 后是 -Z）。\n"
        "材质三个：主体（图集）/ team / team_trim。换阵营只改后两个。\n"
        "骨架 21 根：root→pelvis→spine→chest→neck→head；四肢 .L/.R；\n"
        "盾挂 shield.L、剑挂 weapon.R（都在镜像之后单独生成，所以不会左右各一份）。\n"
        "改颜色：图集/主体.png 的 4×4 格子，顺序见 ch_atlas.CH_ORDER。\n")
    bpy.context.preferences.filepaths.save_version = 0
    blend = os.path.join(OUT_DIR, "%s.blend" % KEY)
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=blend, relative_remap=True)
    receipt["blend"] = {"file": os.path.basename(blend),
                        "bytes": os.path.getsize(blend)}

    with open(os.path.join(ROOT, "docs", "剑士", "receipt.json"), "w",
              encoding="utf-8") as f:
        json.dump(receipt, f, ensure_ascii=False, indent=1)
    print("CHAR_RECEIPT " + json.dumps(receipt, ensure_ascii=False))


main()
