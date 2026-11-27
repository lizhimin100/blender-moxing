"""st_upgrade.py —— 升级态（把旧等级主体截断 + 静态工地 + 新等级暗示件）

统一配方（工单 2.1）：
    旧等级主体（高处截断 + 生料截面 raw，保留大部分识别特征）
  + 静态工地套件（cs_kit 几何固定摆好）
  + 少量新等级暗示构件（hint_*）

三件必须同时成立的事：
  ① **截断不是"砍掉"，是"还在长"**：断口要有生料截面与碎料，脚手架要围到
     断口**之上**一点点（那是下一步的作业面），但绝不高过原建筑总高。
  ② **识别特征必须活下来**：哨塔留下双段木构 + 两层挑台；城镇大厅留下石台、
     墙裙、腰线、三层开间的下两层。切到"什么都不剩"就不叫升级态。
  ③ **暗示件只做一处**：哨塔是顶上的铁箭，城镇大厅是下一等级的塔楼底座 +
     城垛。暗示件一多就变成"另一座建筑"，看不出是同一座在建。

朝向怎么判
----------
工地套件的放线框天生是**对称**的，所以 ±Y 包围盒比值在这里判不出朝向
（建筑本体是对称的院子 + 对称的围栏）。状态档因此多加一条**地标检查**：
在导出前按构件名前缀取一组"只可能在前面的东西"（门套 / 外梯 / 阶条），
要求它们的平均 y > 0.5 m。bbox 比值降级为"没转 180°"的粗筛。

本文件只管造型；截断 / 生料 / 合材质 / 导出在 st_kit.py。
"""
import json
import math
import os
import sys

import bpy

HERE = r"D:/测试一/blender/bs_v6"
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import bslib as L  # noqa: E402
import st_kit as st  # noqa: E402
from bslib import box, extrude  # noqa: E402
from assets_path import asset_path  # noqa: E402

ROOT = r"D:/测试一"
DOC = os.path.join(ROOT, "docs", "状态资产")


def M(name):
    return L.make_material(name)


# ── 暗示件：通用零件 ────────────────────────────────────────────────────────
def arrow(name, cx, cy, z0, h, shaft=0.13, head=0.86, yaw=45.0):
    """竖立的"铁箭"剪影（两片互成 90° 的箭形板 + 中心杆 + 金束 + 队色尾羽）。

    为什么是两片板而不是一圈羽：规则 K82 —— 绕轴一圈的羽从任何水平方向看都会
    合成一个梭形；两片互成 90° 的板在 3/4 机位读作完整的箭。
    `yaw` 默认 45°：交付图机位是 45° 方位，转到 45° 时一片板正对相机、
    另一片只偏 90°，箭的轮廓是完整的（箭塔 v2 就是这么定的）。
    """
    out = []
    out.append((box(name + "_shaft", (cx, cy, z0 + h * 0.44), (shaft, shaft, h * 0.88),
                    M("iron")), 0.0, 0, 1))
    out.append((box(name + "_collar", (cx, cy, z0 + h * 0.56), (0.20, 0.20, 0.11),
                    M("gold")), 0.0, 0, 1))
    # 箭头：带倒钩的箭镞（两片互成 90°）。**窄而高**才读成箭 ——
    # 0.86 × 1.06 的等宽风筝在 RTS 距离上是一颗"钉子头"（v1 的翻车）。
    hw, hh = head * 0.5, head * 1.55
    prof = [(-hw, 0.0), (-hw * 0.34, hh * 0.14), (hw * 0.34, hh * 0.14), (hw, 0.0),
            (0.0, hh)]
    for k, ang in enumerate((yaw, yaw + 90.0)):
        ob = extrude(name + "_head%d" % k, prof, "Y", 0.075, (0, 0), M("team_trim"))
        ob.rotation_euler = (0, 0, math.radians(ang))
        ob.location = (cx, cy, z0 + h * 0.60)
        out.append((ob, 0.0, 0, 1))
    # 尾羽：两片三角板
    for k, ang in enumerate((yaw, yaw + 90.0)):
        p = [(-0.07, 0.34), (0.07, 0.34), (0.22, 0.04), (0.07, -0.06),
             (-0.07, -0.06), (-0.22, 0.04)]
        ob = extrude(name + "_fletch%d" % k, p, "Y", 0.05, (0, 0), M("team"))
        ob.rotation_euler = (0, 0, math.radians(ang))
        ob.location = (cx, cy, z0 + h * 0.22)
        out.append((ob, 0.0, 0, 1))
    return out


def half_rail(name, x0, x1, y, z, h=0.62, n=3):
    """一段"正在装"的栏杆：立柱 + 只上一半的扶手（有一跨缺扶手）。"""
    out = []
    step = (x1 - x0) / max(n, 1)
    for i in range(n + 1):
        out.append((box(name + "_post%d" % i, (x0 + step * i, y, z + h * 0.5),
                        (0.105, 0.105, h), M("wood_warm")), 0.006, 0, 1))
    out.append((box(name + "_rail", ((x0 + x1) * 0.5 - step * 0.25, y, z + h - 0.05),
                    (abs(x1 - x0) - step * 0.55, 0.07, 0.075), M("wood_dark")), 0.006, 0, 1))
    return out


def plank_stack(name, cx, cy, z, n=3):
    out = []
    for i in range(n):
        out.append((box(name + "_%d" % i, (cx + 0.03 * i, cy, z + 0.035 + i * 0.062),
                        (1.10 - 0.10 * i, 0.26, 0.055), M("wood_warm"),
                        rot=(0, 0, 0.05 * (i - 1))), 0.006, 0, 1))
    return out


def mortar(name, cx, cy, z):
    """灰浆槽 + 镘刀：断口边上"正在砌"的那一下。"""
    return [(box(name + "_tub", (cx, cy, z + 0.11), (0.62, 0.42, 0.22),
                 M("wood_mid")), 0.008, 0, 1),
            (box(name + "_lime", (cx, cy, z + 0.20), (0.52, 0.32, 0.05),
                 M("raw_stone")), 0.0, 0, 1),
            (box(name + "_trowel", (cx + 0.30, cy, z + 0.26), (0.20, 0.10, 0.02),
                 M("iron"), rot=(0, 0.5, 0.3)), 0.0, 0, 1)]


def course_of_stones(name, x0, x1, y, z, n=3, mat="raw_stone"):
    """断口上"刚砌了一半"的一皮石块：只砌三块，第四块的位置是空的。"""
    out = []
    step = (x1 - x0) / n
    for i in range(max(1, n - 1)):
        out.append((box("%s_%d" % (name, i), (x0 + step * (i + 0.5), y, z + 0.10),
                        (step * 0.86, 0.44, 0.20), M(mat),
                        rot=(0, 0, 0.04 * (i - 1))), 0.010, 0, 1))
    return out


# ── 哨塔：10.55 截断（保留 61% 高度 + 石基 + 中层挑台 + 两段木构）─────────────
def hint_watchtower(cut):
    """截断后往上接的三件事：铺一半的楼板 + 下一等级的亭架 + 铁箭。

    截断位置刻意选在**上段木构的腰上**（8.16–11.16 的中段），不是为了凑高度：
    切在挑台上沿会得到一个"桌面"，读成"屋顶被拆了"；切在木构腰上才有
    "这根柱子还要再长一截"的意思，断口也是木头的生料色。

    楼板**只铺一半**（前排三块 + 左侧两块，右后角空着露出塔内）：铺满就变成
    "平屋顶"，截断与生料截面全被自己盖掉。
    """
    out = []
    # 1) 铺一半的楼板（左前角两块通长 + 一块短板，右后角留空露出塔内）
    for i, y in enumerate((-1.08, -0.72)):
        out.append((box("hint_deck_%d" % i, (-0.30, y, cut + 0.055), (2.42, 0.31, 0.09),
                        M("wood_warm")), 0.006, 0, 1))
    out.append((box("hint_deck_h0", (-1.02, -0.36, cut + 0.055), (0.94, 0.31, 0.09),
                    M("wood_mid")), 0.006, 0, 1))
    # 2) 下一等级的亭架：两根更高的角柱 + 横梁 + 斜撑 + 队色漆线
    for i, (x, y) in enumerate(((1.42, 1.42), (-1.42, 1.42))):
        out.append((box("hint_frame_col%d" % i, (x, y, cut + 1.05), (0.16, 0.16, 2.10),
                        M("wood_dark")), 0.006, 0, 1))
        out.append((L.beam("hint_frame_brace%d" % i, (x, y - 0.10, cut + 1.30),
                           (x, y - 0.92, cut + 1.94), 0.09, 0.09,
                           M("wood_dark")), 0.0, 0, 1))
    out.append((box("hint_frame_beam", (0, 1.42, cut + 2.02), (3.00, 0.14, 0.16),
                    M("wood_warm")), 0.006, 0, 1))
    out.append((box("hint_frame_trim", (0, 1.42, cut + 1.91), (2.72, 0.035, 0.06),
                    M("team")), 0.0, 0, 1))
    # 3) 下一等级的屋面骨架：四根角柱（高度不齐 = 正在立）+ 脊梁 + 两面坡的椽。
    #    **不做箭饰**，也不做"一根独柱顶个金球"：任何"立在最高处的尖状物"在
    #    RTS 距离上都读成"已经装好的冠饰"，和"还在施工"是矛盾的。
    for i, (x, y, h) in enumerate(((1.42, 1.42, 2.10), (-1.42, 1.42, 1.95),
                                   (1.42, -1.42, 1.55), (-1.42, -1.42, 1.32))):
        out.append((box("hint_post%d" % i, (x, y, cut + h * 0.5), (0.16, 0.16, h),
                        M("wood_dark")), 0.006, 0, 1))
    out.append((box("hint_ridge", (0, -0.30, cut + 1.86), (3.10, 0.14, 0.16),
                    M("wood_warm")), 0.006, 0, 1))
    out.append((box("hint_ridge_trim", (0, -0.30, cut + 1.76), (2.76, 0.035, 0.06),
                    M("team")), 0.0, 0, 1))
    for i, x in enumerate((-1.05, 0.15, 1.05)):
        for s in (-1, 1):
            out.append((L.beam("hint_rafter_%d_%d" % (i, s),
                               (x, -0.30 + s * 0.10, cut + 1.80),
                               (x, -0.30 + s * 1.55, cut + 0.92), 0.10, 0.12,
                               M("wood_mid")), 0.006, 0, 1))
    # 一摞还没架的椽：平放在断口右后角
    for i in range(3):
        out.append((box("hint_rafter_%d" % i, (0.86, 0.30 + 0.24 * i, cut + 0.15 + 0.10 * i),
                        (1.70, 0.13, 0.10), M("wood_mid"),
                        rot=(0, 0, 0.05 * (i - 1))), 0.006, 0, 1))
    out += plank_stack("hint_plank", 1.15, -1.05, cut + 0.10, n=2)
    return out


# ── 城镇大厅：7.30 截断（保留石台 + 墙裙 + 一层拱窗 + 第一道腰线）────────────
def hint_townhall(cut):
    """下一等级（二本 Keep）的塔楼底座 + 城垛，从断口上冒出来 1.2 m。"""
    out = []
    # 塔楼底座：7.30 起、1.5 × 1.5、到 9.1；只砌到"腰线"那么高，上面是断的
    out.append((box("hint_tower_base", (-2.55, -0.60, cut + 0.85), (1.55, 1.55, 1.70),
                    M("stone_light")), 0.020, 0, 1))
    out.append((box("hint_tower_belt", (-2.55, -0.60, cut + 1.62), (1.72, 1.72, 0.16),
                    M("stone_dark")), 0.010, 0, 1))
    out += course_of_stones("hint_tower_stone", -3.30, -1.80, -1.90, cut + 1.62, n=3)
    # 女墙的一段（下一等级的城垛）：只砌 3 个垛，第四个空着
    for i, x in enumerate((1.10, 1.92, 2.74)):
        out.append((box("hint_merlon_%d" % i, (x, 3.02, cut + 0.30), (0.62, 0.46, 0.60),
                        M("stone_light")), 0.012, 0, 1))
    out.append((box("hint_parapet", (-0.55, 3.02, cut + 0.10), (3.30, 0.44, 0.20),
                    M("stone_mid")), 0.012, 0, 1))
    # 队色：女墙顶上一道浅漆线（第二等级的标志色位置）
    out.append((box("hint_team_line", (1.92, 3.02, cut + 0.615), (2.30, 0.48, 0.045),
                    M("team")), 0.0, 0, 1))
    out += plank_stack("hint_plank", 0.30, 0.90, cut + 0.01, n=2)
    out += mortar("hint_mortar", -1.05, 1.55, cut + 0.01)
    return out


# ── 二本 Keep：8.60 截断（保留两层石墙 + 门楼 + 前角楼）──────────────────────
def hint_keep(cut):
    """下一等级（三本 Castle）的中央塔身 + 尖顶基座。"""
    out = []
    out.append((box("hint_up_tower", (0, -0.70, cut + 1.15), (2.30, 2.30, 2.30),
                    M("stone_light")), 0.018, 0, 1))
    out.append((box("hint_up_belt", (0, -0.70, cut + 2.18), (2.50, 2.50, 0.18),
                    M("stone_mid")), 0.010, 0, 1))
    out.append((box("hint_up_gold", (0, -0.70, cut + 2.30), (2.56, 2.56, 0.055),
                    M("gold")), 0.0, 0, 1))
    out += course_of_stones("hint_up_stone", -1.15, 1.15, 0.55, cut + 2.30, n=3)
    out += half_rail("hint_up_rail", 2.55, 3.85, 4.08, cut + 0.01, h=0.66, n=2)
    out += plank_stack("hint_up_plank", -2.20, 1.10, cut + 0.01, n=3)
    out += mortar("hint_up_mortar", 1.10, 1.75, cut + 0.01)
    return out


# ── 帐篷：截断（顶布被掀掉，只剩杆和一圈裙布）────────────────────────────────
def hint_tent(cut, half_w, pole_h):
    out = []
    for i, (x, y) in enumerate(((-half_w * 0.9, half_w * 0.9), (half_w * 0.9, half_w * 0.9))):
        out.append((box("hint_pole_%d" % i, (x, y, cut + (pole_h - cut) * 0.5),
                        (0.13, 0.13, pole_h - cut), M("wood_warm")), 0.006, 0, 1))
    out.append((box("hint_ridge", (0, half_w * 0.9, pole_h - 0.10), (half_w * 1.9, 0.11, 0.12),
                    M("wood_dark")), 0.006, 0, 1))
    out.append((box("hint_trim", (0, half_w * 0.9, pole_h - 0.20), (half_w * 1.8, 0.035, 0.05),
                    M("team")), 0.0, 0, 1))
    out.append((box("hint_canvas_roll", (half_w * 0.55, -half_w * 0.5, cut + 0.22),
                    (1.05, 0.36, 0.34), M("canvas"), rot=(0, 0, 0.2)), 0.010, 0, 1))
    out += plank_stack("hint_plank", -half_w * 0.45, -half_w * 0.55, cut + 0.01, n=2)
    return out


# ── 驱动 ────────────────────────────────────────────────────────────────────
CONFIG = {
    "哨塔_升级": dict(asset="哨塔", mod="wt_model", cut=10.55, lifts=4, body_z=1.60,
                   hint=hint_watchtower, prefix="WT", front=0.95,
                   landmark=("ldr_", "gate_", "step_"),
                   note="一本/二本共用；队色与旗由引擎侧切换"),
    "城镇大厅_升级1": dict(asset="城镇大厅", mod="th_model", cut=7.30, lifts=4, body_z=1.80,
                      hint=hint_townhall, prefix="TH", front=0.95,
                      landmark=("gate_", "step_", "plinth"),
                      note="一本 v3 → 二本 Keep"),
    "城镇大厅_升级2": dict(asset="城镇大厅", mod="keep_model", cut=8.60, lifts=5, body_z=1.80,
                      hint=hint_keep, prefix="KH", front=0.95,
                      landmark=("gate_", "step_", "porch", "door_"),
                      note="二本 Keep → 三本"),
}


def _front_landmark(items, prefixes):
    """只可能长在正面的构件（门套 / 外梯 / 阶条）的平均 y。"""
    ys = []
    for it in items:
        ob = it[0]
        if not ob.name.startswith(prefixes):
            continue
        for v in ob.data.vertices:
            ys.append((ob.matrix_world @ v.co).y)
    if not ys:
        return None
    return sum(ys) / len(ys)


def assemble(key, do_export=True):
    cfg = CONFIG[key]
    return run_upgrade(key, cfg["asset"], __import__(cfg["mod"]), cfg["cut"],
                       cfg["lifts"], cfg["hint"], cfg["prefix"], cfg["front"],
                       cfg["landmark"], cfg["body_z"], cfg.get("note", ""),
                       do_export=do_export)


def run_upgrade(key, asset, mod, cut, lifts, hint, prefix, front, landmark,
                body_z, note="", do_export=True):
    """通用升级态：截断 mod 的主体 → 生料 → 静态工地 → hint 暗示件 → 图集 → GLB。"""
    cfg = dict(asset=asset, cut=cut, lifts=lifts, hint=hint, prefix=prefix,
               front=front, landmark=landmark, body_z=body_z, note=note)
    st.clear_scene()
    m = mod.Model(False, unwrap=False).build()
    items = list(m.items)
    st.bake_transforms(items)
    _lo0, hi0, _b0 = st.measure(items)
    kept, caps, removed = st.cut_items(items, cfg["cut"])
    chunks = st.raw_chunks(caps) + st.cap_joists(caps)
    # 自检：截断之后不该还有本体构件浮在断口之上（曾经因为 matrix_world 是旧缓存，
    # 4 根山墙斜撑被"完整保留"在半空里）。允许 0.25 m：断口抖动 + 圆角。
    strays = []
    for it in kept:
        ob = it[0]
        z = max((v.co.z for v in ob.data.vertices), default=-9)
        if z > cfg["cut"] + 0.25:
            strays.append((ob.name, round(z, 2)))
    if strays:
        print("   !! 断口以上残留 %d 件：%s" % (len(strays), strays[:6]))
    lo, hi, body_all = st.measure(kept + caps)
    deck = st.interior_deck(body_all, cfg["cut"] - 0.02)
    W, D = body_all[1] - body_all[0], body_all[3] - body_all[2]
    body = st.measure_body(kept, cfg["body_z"]) or body_all
    kit = st.static_site(W, D, hi0.z, body=body, lifts=cfg["lifts"])
    site = st.site_objects(kit)
    hints = cfg["hint"](cfg["cut"])
    fy = _front_landmark(kept, cfg["landmark"])
    m.items = kept + caps + chunks + hints + deck + site
    print("[%s] 截断 z=%.2f  保留 %d / 删 %d  生料 %d  碎料 %d  暗示 %d  套件 %d  正面地标 y=%s"
          % (key, cfg["cut"], len(kept), len(removed), len(caps),
             len(chunks) + len(deck), len(hints), len(site),
             "None" if fy is None else round(fy, 2)))
    objs = m.finalize(bevel=True)
    if not do_export:
        return objs
    path, rec = st.finish(objs, key, cfg["prefix"], asset_path(cfg["asset"]),
                          anim=False, front_ratio=cfg["front"])
    rec.update({"asset_name": key, "kind": "升级态", "cut_z": cfg["cut"],
                "note": cfg["note"], "lifts": cfg["lifts"],
                "body": [round(v, 3) for v in body],
                "plot": [round(v, 3) for v in body_all],
                "kept": len(kept), "removed": len(removed), "caps": len(caps),
                "chunks": len(chunks), "hints": len(hints),
                "front_landmark_y": None if fy is None else round(fy, 3)})
    rec["front_landmark_ok"] = bool(fy is None or fy > 0.5)
    rec["ok"] = bool(rec["ok"] and rec["front_landmark_ok"])
    _write(key, rec)
    print("[%s] %s tris=%d mats=%d %s" %
          (key, rec["file"], rec["tris"], rec["mat_count"], "OK" if rec["ok"] else "FAIL"))
    return rec


def _write(key, rec):
    d = os.path.join(DOC, key)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "receipt.json"), "w", encoding="utf-8") as f:
        json.dump(rec, f, ensure_ascii=False, indent=2)


RUN = ("城镇大厅_升级1", "城镇大厅_升级2", "哨塔_升级")


def main():
    out = {}
    for key in RUN:
        out[key] = assemble(key)
    print("ST_UPGRADE_RECEIPT " + json.dumps(
        {k: [v["tris"], v["mat_count"], v["ok"]] for k, v in out.items()},
        ensure_ascii=False))


main()
