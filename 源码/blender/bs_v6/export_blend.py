"""export_blend.py —— 出**交付用 .blend**（能在别的电脑的 Blender 里直接打开）

    python build/bl_act.py act blender/bs_v6/export_blend.py

为什么单独一个脚本：GLB 天生内嵌贴图，`.blend` 不会。
`blend/铁匠铺/铁匠铺.blend` 是出图用的展示场景（20 个纯色材质、没有贴图），
拿到别的机器上打开是"能开，但和游戏里不是一个东西"。
这里出的是**和游戏里一致的那一份**：图集 4 材质 + UV 钉格心 + 贴图 Pack 进文件。

三条硬性：
  ① `bpy.ops.file.pack_all()` —— 贴图打包进 .blend，换机器不会变洋红；
  ② `relative_remap=True` —— 路径写相对，不写 D:/测试一/...；
  ③ 文件里附一段说明文本（`bpy.data.texts`），接手的人打开就知道是什么、怎么用。

产物：assets/<建筑>/<建筑>.blend
"""
import importlib
import json
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else r"D:/测试一/blender/bs_v6"
ROOT = r"D:/测试一"
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from assets_path import asset_path  # noqa: E402
for _m in ("bslib", "bs_model", "br_model", "th_model", "wt_model", "fm_model",
           "lm_model", "ms_model", "sw_model", "at_model", "bs_atlas", "keep_model",
           "dl_parts", "dg_layout", "dg_model"):
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
import dl_parts  # noqa: E402
import dg_layout  # noqa: E402
import dg_model  # noqa: E402
import tent_model  # noqa: E402

# 与 export_mobile.py 的 TENT_LAYOUT 必须完全一致：.blend 里要重画一次同一张图集，
# 两张图的格子尺寸差一行，UV 就会采到隔壁颜色。列数不变、行 9 → 10，
# 三档帐篷专用（canvas / canvas_dark / site_rope 追加在 43 格之后）。
TENT_LAYOUT = bs_atlas.Layout(
    bs_atlas.COLS, bs_atlas.ROWS + 1, bs_atlas.SIZE, bs_atlas.PAD,
    list(bs_atlas.ATLAS_ORDER) + ["canvas", "canvas_dark", "site_rope"], "帐篷")

TARGETS = {
    "铁匠铺": {"module": bs_model, "prefix": "BS",
             "note": "铁匠铺 · 手游档（图集 4 材质 + 近景全量构件）"},
    "兵营": {"module": br_model, "prefix": "BR",
           "note": "兵营 · 手游档（图集 4 材质 + 近景全量构件）"},
    "城镇大厅": {"module": th_model, "prefix": "TH",
             "note": "城镇大厅 · 手游档（图集 4 材质 + 近景全量构件）"},
    "哨塔": {"module": wt_model, "prefix": "WT",
           "note": "哨塔 · 手游档（图集 4 材质 + 近景全量构件）"},
    "农场": {"module": fm_model, "prefix": "FM",
           "note": "农场 · 手游档（图集 4 材质 + 近景全量构件）"},
    "伐木场": {"module": lm_model, "prefix": "LM",
            "note": "伐木场 · 手游档（图集 4 材质 + 近景全量构件）"},
    "神秘圣地": {"module": ms_model, "prefix": "MS",
             "note": "神秘圣地 · 手游档（图集 4 材质 + 近景全量构件）"},
    "蒸汽车坊": {"module": sw_model, "prefix": "SW",
             "note": "蒸汽车坊 · 手游档（图集 4 材质 + 近景全量构件）"},
    "箭塔": {"module": at_model, "prefix": "AT",
           "note": "箭塔 · 手游档（图集 4 材质 + 近景全量构件）"},
    "折壳入口": {"module": fs_model, "prefix": "FS",
             "note": "折壳入口 · 手游档（图集 4 材质 + 近景全量构件）"},
    "城镇大厅二本": {"module": keep_model, "prefix": "KH",
                "note": "二本·石木戍堡 · 手游档（图集 4 材质 + 近景全量构件）"},
    "地牢": {"module": dg_model, "prefix": "DG",
           "note": "地牢入口 v2 · 手游档（图集 4 材质 + 近景全量构件）"},
    "初级帐篷": {"module": tent_model, "prefix": "TN1", "layout": TENT_LAYOUT,
             "note": "初级帐篷 · 手游档（图集 4 材质 + 近景全量构件）"},
    "中等帐篷": {"module": tent_model, "prefix": "TN2", "layout": TENT_LAYOUT,
             "note": "中等帐篷 · 手游档（图集 4 材质 + 近景全量构件）"},
    "豪华帐篷": {"module": tent_model, "prefix": "TN3", "layout": TENT_LAYOUT,
             "note": "豪华帐篷 · 手游档（图集 4 材质 + 近景全量构件）"},
}
RUN = ("初级帐篷", "中等帐篷", "豪华帐篷")

README = """{note}

单位：1 unit = 1 m。原点在占地中心，z = 0 是地面。
朝向：Blender 里正面朝 +Y（导出 glTF 后变成 −Z，符合 Godot / Unity 的惯例）。

材质（共 4 个，名字不要改，换阵营靠改后两个）：
  主体      图集材质，颜色走 assets/<建筑>/图集/主体.png 与 ORM.png（已打包进本文件）
  team      阵营主色（纯色）
  team_trim 阵营辅色（纯色）
  自发光     火焰 / 炭 / 窗光（同一布局的自发光图）

贴图已 Pack 进本文件，换电脑直接打开即可，不需要带 PNG。
如果要替换图集：图像编辑器里选中「主体」，用新图 Replace 后重新 Pack。

同一目录下的 GLB 才是运行时文件：
  <建筑>_手游_近.glb  全量构件   ← 主用
  <建筑>_手游_中.glb  中景
  <建筑>_手游_远.glb  远景 / 缩略
"""


def hard_reset():
    """彻底清场：对象、集合、以及所有会被写进文件的 data-block。

    不用 `wm.read_homefile(use_empty=True)` —— 那个之后 `bpy.ops.object.join()`
    的 poll 会失败（context is incorrect），模型根本合并不出来。
    """
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for c in list(bpy.data.collections):
        bpy.data.collections.remove(c)
    for blk in (bpy.data.meshes, bpy.data.materials, bpy.data.images,
                bpy.data.cameras, bpy.data.lights, bpy.data.texts):
        for it in list(blk):
            try:
                blk.remove(it)
            except Exception:
                pass


def build_one(key, cfg):
    out_dir = asset_path(key)
    atlas_dir = os.path.join(out_dir, "图集")
    hard_reset()

    # 图集必须已经由 export_mobile 生成；没有就先跑那个脚本
    png = os.path.join(atlas_dir, "主体.png")
    if not os.path.exists(png):
        return {"ok": False, "error": "缺图集，先跑 export_mobile.py"}
    imgs0 = bs_atlas.build_images(atlas_dir, label=key, layout=cfg.get("layout"))   # 幂等：重画一次，保证和 GLB 同源
    cs = {bs_atlas.TAG_ATLAS: "sRGB", "ORM": "Non-Color", bs_atlas.TAG_EMIT: "sRGB"}
    paths = {tag: img.filepath for tag, img in imgs0.items()}
    imgs = {}
    for tag, img in imgs0.items():
        img.colorspace_settings.name = cs[tag]
        imgs[tag] = img

    m = (cfg["module"].build_tier(key, smooth=False)
         if hasattr(cfg["module"], "build_tier")
         else cfg["module"].Model(False, unwrap=False).build())
    objs = m.finalize(bevel=True)
    bs_atlas.pin_uv(objs, cfg.get("layout"))
    packed = bs_atlas.pack(objs, imgs, prefix=cfg["prefix"])

    # join 会把原 20 个材质留在 bpy.data 里（对象的槽清空了，但 datablock 还在），
    # 不 purge 的话交出去的 .blend 材质列表里有 22 个材质，和"4 材质"的说法对不上。
    for m in list(bpy.data.materials):
        if m.users == 0:
            bpy.data.materials.remove(m)
    for me in list(bpy.data.meshes):
        if me.users == 0:
            bpy.data.meshes.remove(me)

    # 场景收拾：只留模型，命名清晰
    sc = bpy.context.scene
    sc.name = key
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0
    coll = bpy.data.collections.new(key)
    sc.collection.children.link(coll)
    for ob in packed:
        for c in list(ob.users_collection):
            c.objects.unlink(ob)
        coll.objects.link(ob)

    # 说明文本
    txt = bpy.data.texts.new("读我 · README")
    txt.write(README.format(note=cfg["note"]))

    # 打包之后 filepath 仍然是绝对路径（packed 图会保留"来源"路径）。
    # Pack 状态下不影响打开，但一旦有人 Unpack 就会往 D://测试一//... 里写，
    # 所以显式改成相对：//图集/xxx.png
    # 注意：**不能用 bpy.path.abspath(img.filepath)** —— 它按"当前会话的 blend 目录"解析，
    # 而这一轮会话里上一次打开的是另一座建筑的文件，会算出 "../兵营/图集/..." 这种错路径。
    # 路径源头就在 paths 里，直接用。
    # 图集固定落在 <out_dir>/图集/ 下，直接写死这一段，不经过 os.path.relpath ——
    # 它给的是反斜杠，换到 Linux / macOS 的 Blender 上会被当成文件名的一部分。
    for tag, p_ in paths.items():
        if tag in imgs:
            imgs[tag].filepath = "//图集/" + os.path.basename(p_)

    bpy.context.preferences.filepaths.use_relative_paths = True
    bpy.context.preferences.filepaths.save_version = 0     # 不要 .blend1 备份，交付目录要干净
    try:
        bpy.ops.file.pack_all()
    except Exception as exc:      # 没有可打包的图时不会报错，这里只兜底
        print("[warn] pack_all:", exc)

    path = os.path.join(out_dir, key + ".blend")
    # relative_remap=True 会拿"上一次打开的 .blend 的目录"当基准再重算一次，
    # 而上面已经把 filepath 写成相对了 —— 结果被重映射到 "../另一座建筑/图集/..."。
    # 路径由我们自己控制，这里必须关掉。
    bpy.ops.wm.save_as_mainfile(filepath=path, relative_remap=False,
                                compress=True, copy=False)
    return {"ok": True, "file": os.path.basename(path), "path": path,
            "bytes": os.path.getsize(path), "objects": len(packed)}


def verify(path):
    """重新打开文件回查：贴图是否真的打包、材质数、对象名、包围盒。"""
    bpy.ops.wm.open_mainfile(filepath=path)
    imgs = list(bpy.data.images)
    packed = [i.name for i in imgs if i.packed_file is not None]
    unpacked = [i.name for i in imgs if i.packed_file is None and i.source != "GENERATED"]
    mats = sorted(m.name for m in bpy.data.materials)
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    lo = [min(min((o.matrix_world @ v.co)[i] for v in o.data.vertices) for o in meshes) for i in range(3)]
    hi = [max(max((o.matrix_world @ v.co)[i] for v in o.data.vertices) for o in meshes) for i in range(3)]
    return {
        "images": [i.name for i in imgs],
        "packed": packed,
        "unpacked": unpacked,
        "all_packed": len(unpacked) == 0 and len(packed) > 0,
        "materials": mats,
        "objects": [o.name for o in meshes],
        "bbox_min": [round(v, 2) for v in lo],
        "bbox_max": [round(v, 2) for v in hi],
        "text_datablocks": [t.name for t in bpy.data.texts],
        "grounded": abs(lo[2]) <= 0.05,
    }


def main():
    receipt = {"targets": {}, "ok": True}
    # 先全部生成，再逐个打开回查：open_mainfile 会换掉整个文件上下文，
    # 混在生成循环里做，下一座建筑的 data-block 会被上一座污染。
    for key in RUN:
        receipt["targets"][key] = build_one(key, TARGETS[key])
    for key in RUN:
        r = receipt["targets"][key]
        if not r.get("ok"):
            receipt["ok"] = False
            continue
        r["verify"] = verify(r["path"])
        if not (r["verify"]["all_packed"] and r["verify"]["grounded"]):
            r["ok"] = False
            receipt["ok"] = False
    print("BLEND_RECEIPT " + json.dumps(receipt, ensure_ascii=False))


main()
