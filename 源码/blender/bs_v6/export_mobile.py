"""export_mobile.py —— **手游档唯一导出入口**（图集 + 三级 LOD），两座建筑共用一份逻辑

    python build/bl_act.py act blender/bs_v6/export_mobile.py

每座建筑出三档，三档共用同一张图集与同一套材质（切档不掉材质、不重传贴图）：

    近  LOD0  全量构件、保留倒角
    中  LOD1  体积 ≥ 0.012 m³、去地面碎屑、**关倒角**
    远  LOD2  体积 ≥ 0.22 m³ + 旗/盾白名单、道具整组去掉、关倒角

材质从每座 19–20 个压到 **4 个**：主体图集 / team / team_trim / 自发光。
材质名必须保持 ASCII —— 换色脚本按名字找 `team` / `team_trim`。

产物：
    assets/<建筑>/<建筑>_手游_近.glb · _中.glb · _远.glb
    assets/<建筑>/图集/主体.png · ORM.png · 自发光.png
"""
import importlib
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
for _m in ("bslib", "bs_model", "br_model", "th_model", "wt_model", "fm_model",
           "lm_model", "ms_model", "sw_model", "at_model", "fs_model", "bs_atlas",
           "keep_model", "tent_model",
          "dl_parts", "dg_layout", "dg_model",
           "dl_kit", "dg_model", "uc_model", "tv_model", "fr_model"):
    if _m in sys.modules:
        importlib.reload(sys.modules[_m])
import bs_atlas  # noqa: E402
import bs_model  # noqa: E402
import br_model  # noqa: E402
import th_model  # noqa: E402
import wt_model  # noqa: E402
import fm_model  # noqa: E402
import lm_model  # noqa: E402
import ms_model  # noqa: E402
import sw_model  # noqa: E402
import at_model  # noqa: E402
import fs_model  # noqa: E402
import keep_model  # noqa: E402
import tent_model  # noqa: E402
import dg_model  # noqa: E402
import uc_model  # noqa: E402
import tv_model  # noqa: E402
import fr_model  # noqa: E402

# 三角面预算：近档比低模实拍高 20% 留余量，中/远按上一座的比例推
#
# 帐篷专用图集布局：帐篷用到 canvas / canvas_dark / site_rope 三档，不在
# bs_atlas.ATLAS_ORDER（43/45 格，剩两格不够三档）里。BUILD_LAYOUT 是九座与
# 状态资产 UV 的依据，不能动；所以在手游档这一层派生一份：列数不变、行 9 → 10，
# 只作用于显式传了 layout 的这几座。追加在表尾 → 旧索引一个都没动。
TENT_LAYOUT = bs_atlas.Layout(
    bs_atlas.COLS, bs_atlas.ROWS + 1, bs_atlas.SIZE, bs_atlas.PAD,
    list(bs_atlas.ATLAS_ORDER) + ["canvas", "canvas_dark", "site_rope"], "帐篷")

BUILDINGS = {
    "铁匠铺": {
        "module": bs_model,
        "dir": asset_path("铁匠铺"),
        "prefix": "BS",
        "budgets": (18000, 9500, 3200),
        "front_ratio": 1.4,          # 正面 = 炉膛在前（+Y 明显长于 −Y）
    },
    "兵营": {
        "module": br_model,
        "dir": asset_path("兵营"),
        "prefix": "BR",
        "budgets": (22000, 12000, 4200),
        "front_ratio": 1.05,         # 正面 = 前场比后墙长
    },
    "城镇大厅": {
        "module": th_model,
        "dir": asset_path("城镇大厅"),
        "prefix": "TH",
        "budgets": (22000, 12000, 4200),
        "front_ratio": 1.18,         # 正面 = 台阶（+Y）一侧；v3 实测近档 1.32 / 远档 1.25
                                     # （远档删掉踏步后只剩颊墙在前，比值回落）
    },
    "哨塔": {
        "module": wt_model,
        "dir": asset_path("哨塔"),
        "prefix": "WT",
        "budgets": (18000, 10000, 3800),
        "front_ratio": 1.05,         # 正面 = 台阶 + 外梯 + 场地在前
    },
    "农场": {
        "module": fm_model,
        "dir": asset_path("农场"),
        "prefix": "FM",
        "budgets": (20000, 11000, 4500),
        "front_ratio": 1.10,         # 正面 = 大门一侧（+Y 是背面一侧的两倍多）
    },
    "伐木场": {
        "module": lm_model,
        "dir": asset_path("伐木场"),
        "prefix": "LM",
        "budgets": (20000, 11000, 4500),
        "front_ratio": 1.10,         # 正面 = 门架与轨道伸出的那一侧（+Y）
    },
    "神秘圣地": {
        "module": ms_model,
        "dir": asset_path("神秘圣地"),
        "prefix": "MS",
        "budgets": (16000, 9500, 4300),
        "front_ratio": 1.10,         # 正面 = 山门 + 台阶 + 四簇水晶（+Y 7.50 / −Y 6.45）
    },
    "蒸汽车坊": {
        "module": sw_model,
        "dir": asset_path("蒸汽车坊"),
        "prefix": "SW",
        "budgets": (17000, 11000, 4800),
        # 正面 = 门庭台阶 + 外挑吊梁（+Y 7.43 / −Y 7.05）。长屋本身后段更长，
        # 比值天生只有 1.05 —— 判"有没有转 180°"够用，别按别的座去拔高。
        "front_ratio": 1.03,
    },
    "地牢": {
        "module": dg_model,
        "dir": asset_path("地牢"),
        "prefix": "DG",
        "budgets": (10500, 6500, 4400),
        "front_ratio": 0.95,
    },
    "地下城入口": {
        "module": uc_model,
        "dir": asset_path("地下城入口"),
        "prefix": "UC",
        "budgets": (10500, 6500, 5100),
        "front_ratio": 1.00,
    },
    "酒馆内部": {
        "module": tv_model,
        "dir": asset_path("酒馆内部"),
        "prefix": "TV",
        "budgets": (12000, 7500, 6900),
        "front_ratio": 0.98,
    },
    "营火": {
        "module": fr_model.module_for("营火"),
        "dir": asset_path("营火"),
        "prefix": "CF",
        "budgets": (2000, 1500, 2000),
        "front_ratio": 0.90,
    },
    "火把": {
        "module": fr_model.module_for("火把"),
        "dir": asset_path("火把"),
        "prefix": "TR",
        "budgets": (1600, 1100, 1600),
        "front_ratio": 0.90,
    },
    "火炬": {
        "module": fr_model.module_for("火炬"),
        "dir": asset_path("火炬"),
        "prefix": "BZ",
        "budgets": (2200, 1500, 2200),
        "front_ratio": 0.90,
    },
    "火堆": {
        "module": fr_model.module_for("火堆"),
        "dir": asset_path("火堆"),
        "prefix": "BF",
        "budgets": (2200, 1500, 2200),
        "front_ratio": 0.90,
    },
    "折壳入口": {
        "module": fs_model,
        "dir": asset_path("折壳入口"),
        "prefix": "FS",
        "budgets": (11500, 6500, 3600),
        "front_ratio": 0.55,      # 壳在后侧，同 dl_export 的说明
    },
    # 第十六批（状态资产）：二本城镇大厅的标准手游档。front_ratio 1.06 ——
    # 门廊（+Y 5.85）比后墙（−Y 4.65）长，1.06 只用来判"没转 180°"。
    "城镇大厅二本": {
        "module": keep_model,
        "dir": asset_path("城镇大厅二本"),
        "prefix": "KH",
        "budgets": (24000, 13000, 4800),
        "front_ratio": 1.06,
    },
    "箭塔": {
        "module": at_model,
        "dir": asset_path("箭塔"),
        "prefix": "AT",
        "budgets": (21000, 12000, 4600),
        # 正面 = 台阶 + 胸墙 + 箭捆架（+Y 3.72 / −Y 3.42）；比值天生只有 1.09，
        # 判"有没有转 180°"够用。
        "front_ratio": 1.03,
    },
    # 第十七批（状态资产）：三顶帐篷。Model 按 tier 建（build_one 里走 build_tier），
    # front_ratio 0.95 —— 地钉在 ±Y 对称，包围盒比值恒为 1.0，这一项只判"没转身"。
    # 预算按各自低模实测给足：初级 748 / 中等 1080 / 豪华 1508 tris（含倒角的近档 ×3 左右）。
    "初级帐篷": {
        "module": tent_model,
        "dir": asset_path("初级帐篷"),
        "layout": TENT_LAYOUT,
        "prefix": "TN1",
        "budgets": (6000, 3500, 1800),
        "front_ratio": 0.95,
    },
    "中等帐篷": {
        "module": tent_model,
        "dir": asset_path("中等帐篷"),
        "layout": TENT_LAYOUT,
        "prefix": "TN2",
        "budgets": (8000, 4500, 2000),
        "front_ratio": 0.95,
    },
    "豪华帐篷": {
        "module": tent_model,
        "dir": asset_path("豪华帐篷"),
        "layout": TENT_LAYOUT,
        "prefix": "TN3",
        "budgets": (10000, 5500, 2500),
        "front_ratio": 0.95,
    },
}
RUN = ("初级帐篷", "中等帐篷", "豪华帐篷")
MAX_MATERIALS = 4


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
              export_image_format="AUTO")
    try:
        bpy.ops.export_scene.gltf(**kw)
    except TypeError:
        kw.pop("export_extras", None)
        bpy.ops.export_scene.gltf(**kw)
    bpy.ops.object.select_all(action="DESELECT")
    return os.path.getsize(path)


def verify(path, front_ratio):
    """重新导入回查：材质数 / 三角面 / 贴地 / 朝向 / 贴图。"""
    clear_scene()
    bpy.ops.import_scene.gltf(filepath=path)
    objs = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    tris = 0
    lo = Vector((1e9, 1e9, 1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    has_tex = False
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
    names = sorted({m.name for o in objs for m in o.data.materials if m})
    return {
        "meshes": len(objs),
        "surfaces": len(names),
        "materials": names,
        "tris": tris,
        "bbox_min": [round(v, 3) for v in lo],
        "bbox_max": [round(v, 3) for v in hi],
        "size": [round(v, 3) for v in (hi - lo)],
        "grounded": abs(lo.z) <= 0.05,
        # 正面朝向：glTF 里正面是 −Z，Blender 里对应 +Y，所以看 +Y 是否比 −Y 长
        "front_ok": bool(hi.y > abs(lo.y) * front_ratio),
        "has_texture": has_tex,
    }


def run_one(key, cfg, atlas_paths, cs):
    out_dir = cfg["dir"]
    os.makedirs(out_dir, exist_ok=True)
    receipt = {"asset": key, "variants": {}, "ok": True}
    variants = (("%s_手游_近.glb" % key, 0, cfg["budgets"][0]),
                ("%s_手游_中.glb" % key, 1, cfg["budgets"][1]),
                ("%s_手游_远.glb" % key, 2, cfg["budgets"][2]))
    for fname, level, budget in variants:
        clear_scene()
        # 清场景会连 Image 数据块一起删掉（那是刚生成的图集），从磁盘重新 load
        imgs = {}
        for tag, p in atlas_paths.items():
            img = bpy.data.images.load(p, check_existing=False)
            img.colorspace_settings.name = cs[tag]
            imgs[tag] = img
        m = (cfg["module"].build_tier(key, smooth=False)
             if hasattr(cfg["module"], "build_tier")
             else cfg["module"].Model(False, unwrap=False).build())
        m.items = bs_atlas.filter_lod(m.items, level)
        parts = len(m.items)
        # LOD1/2 关倒角：远景看不出 2 cm 的棱，但倒角会把大件面数翻 2–3 倍
        objs = m.finalize(bevel=(level == 0))
        bs_atlas.pin_uv(objs, cfg.get("layout"))
        packed = bs_atlas.pack(objs, imgs, prefix=cfg["prefix"])
        # 中立阵营的阵营色覆盖：和桌面档同一个来源（dg_model.TEAM_STYLE），
        # 不然桌面是锈红、手游是联盟蓝（图集档会按 PALETTE 重建 team 材质）。
        try:
            import dl_parts as _dp
            _dp.apply_team_style(getattr(cfg["module"], "TEAM_STYLE", None))
        except Exception as _e:
            print("[team-style] skip:", _e)
        path = os.path.join(out_dir, fname)
        size = export_glb(packed, path)
        v = verify(path, cfg["front_ratio"])
        v.update({"file": fname, "bytes": size, "build_parts": parts,
                  "budget_tris": budget, "over_budget": v["tris"] > budget,
                  "materials_ok": v["surfaces"] <= MAX_MATERIALS})
        receipt["variants"][fname] = v
        if not (v["materials_ok"] and v["grounded"] and v["front_ok"]
                and not v["over_budget"] and v["has_texture"]):
            receipt["ok"] = False
    return receipt


def main():
    # 图集每座建筑各一份（格子内容相同，但 PNG 分开存，改其中一座不牵连另一座）
    receipts = {}
    for key in RUN:
        cfg = BUILDINGS[key]
        atlas_dir = os.path.join(ROOT, "docs", "_tmp", "图集", key)
        os.makedirs(atlas_dir, exist_ok=True)
        imgs0 = bs_atlas.build_images(atlas_dir, label=key, layout=cfg.get("layout"))
        paths = {k: v.filepath for k, v in imgs0.items()}
        cs = {bs_atlas.TAG_ATLAS: "sRGB", "ORM": "Non-Color", bs_atlas.TAG_EMIT: "sRGB"}
        receipts[key] = run_one(key, cfg, paths, cs)
        receipts[key]["atlas"] = {k: os.path.basename(p) for k, p in paths.items()}
    out = {"mode": "手游档（图集 + 3 级 LOD）", "buildings": receipts,
           "ok": all(r["ok"] for r in receipts.values())}
    print("MOBILE_RECEIPT " + json.dumps(out, ensure_ascii=False))


main()
