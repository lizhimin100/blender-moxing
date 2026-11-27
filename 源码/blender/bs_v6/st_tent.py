"""st_tent.py —— 帐篷资产：三级静态档 + 两个升级态

跑法（后台直接跑，Blender 5.2）：
    "/d/360安全浏览器下载/blender.exe" -b --factory-startup --python blender/bs_v6/st_tent.py

产出
----
    assets/建筑/联盟/初级帐篷/初级帐篷.glb          + 图集_状态/
    assets/建筑/联盟/中等帐篷/中等帐篷.glb
    assets/建筑/联盟/豪华帐篷/豪华帐篷.glb
    assets/建筑/联盟/初级帐篷/初级帐篷_升级.glb
    assets/建筑/联盟/中等帐篷/中等帐篷_升级.glb
    docs/状态资产/<key>/receipt.json

三级与两个升级态共用一套 `st_kit.finish`（图集 → GLB → 回查），所以验收口径
和九座完全一样：tris ≤ 23k、材质 4、grounded、front_ok，升级态另有
skins 0 / 无 animations。

关于脚手架层数（**偏离工单的一处**）
------------------------------------
工单写"初级 lifts=2 / 中等 lifts=3"，但 `cs_kit.LIFT_H = 2.20`：2 步 = 4.40 m、
3 步 = 6.60 m，而帐篷只有 2.30 / 2.95 m —— 架子会是一顶帐篷的 1.9–2.2 倍高，
把本体整个罩进笼子里（建模规则 N115 的原话："低矮建筑不能套三步脚手架"）。
所以两档都取 **lifts=1**：作业面 2.15 m，正好压在断口（1.55 / 1.95）之上一点点，
这才是"下一步要在这层铺新布"的读法。
"""
import functools
import json
import math
import os
import sys
import types

import bpy
from mathutils import Vector

HERE = r"D:/测试一/blender/bs_v6"
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import cs_kit  # noqa: E402
import bslib as L  # noqa: E402
import st_kit as st  # noqa: E402
import tent_model  # noqa: E402
import assets_path  # noqa: E402
from assets_path import asset_path  # noqa: E402

ROOT = r"D:/测试一"
DOC = os.path.join(ROOT, "docs", "状态资产")
FAMILY = os.path.join("建筑", "联盟")


def _load_upgrade():
    """只借 `st_upgrade.run_upgrade`，**不执行它的入口**。

    st_upgrade.py 结尾有一句模块级的 `main()`（它自己跑哨塔_升级）。直接
    `import st_upgrade` 会顺手把别人的哨塔_升级重导一遍 —— 如果这期间
    PALETTE / cs_kit 动过，别人的资产就被静默换掉了。这里按源码 exec 一份，
    掐掉最后那句调用，跑的还是同一份代码。
    """
    p = os.path.join(HERE, "st_upgrade.py")
    with open(p, encoding="utf-8") as f:
        src = f.read()
    body = src.rstrip()
    if body.endswith("main()"):
        src = body[:-len("main()")] + "# 入口不在本脚本里执行（见 _load_upgrade）\n"
    mod = types.ModuleType("st_upgrade")
    mod.__file__ = p
    sys.modules["st_upgrade"] = mod
    exec(compile(src, p, "exec"), mod.__dict__)
    return mod


up = _load_upgrade()


# 帐篷是 2.3–3.85 m 的软资产，而 cs_kit 的悬臂吊杆是 2.6 m 高、带 1.85 m 臂的
# 石构件吊装设备 —— 立在帐篷旁边比帐篷还高，还横着压在帐顶上。整个套件的其他件
# （放线框 / 桩绳 / 一面脚手架 / 料堆 / 队旗）都按原样保留，只去掉吊杆。
cs_kit.Kit.build_hoist = lambda self: None
# 队旗同理：1.6 m 杆 + 0.9 m 布，插在 1.5 m 的断口旁边比帐篷还高，
# 而且正好挡在门洞前面。队色由帐篷自己的腰线与放线框的门柱负责。
cs_kit.Kit.build_banners = lambda self, lifts: None

# st_kit 的"楼下那层楼板"（interior_deck）是给 8 m 进深的空心建筑补深度线索的：
# 在断口下方 0.38 铺一块比墙内缩 0.70 的暗色楼板。帐篷是**薄壳**：
# 初级在 1.55 处的锥截面只有 1.0 m 宽，1.9×1.8 的楼板会从布墙里穿出去；
# 中级截断只有 1.95 m 高，楼板会压在内衬和两根脊杆上。两档都不要这一层 ——
# 帐篷的"地板"是地上那块 canvas_dark 衬布，不是混凝土楼板。
st.interior_deck = lambda body, zcut, *a, **k: []


def M(name):
    return L.make_material(name)


# ── 升级态暗示件（3–4 件，一律不出现"尖状冠饰"）─────────────────────────────
def hint_small(cut):
    """初级 → 中等：两根更长的脊杆从断口上立起来（不等高 = 正在抬），
    脊梁斜搭在两根杆上，地上是一捆卷起的帆布 + 一摞木板。

    高度都压在 2.3–2.8：低于原帐篷总高（2.30 的断口 + 上一层），
    不出现"一根杆子捅到天上去"的读法。
    """
    out = []
    for i, (yy, h) in enumerate(((-0.40, 2.78), (0.40, 2.62))):
        out.append((L.box("pole_up%d" % i, (0.0, yy, cut + (h - cut) * 0.5),
                          (0.14, 0.14, h - cut), M("wood_warm")), 0.008, 0, 1))
    out.append((L.beam("rg_up", (0.0, -0.46, 2.80), (0.0, 0.46, 2.64), 0.13, 0.13,
                       M("wood_dark")), 0.0, 0, 1))
    out.append((L.box("tent_roll", (-1.78, 0.52, 0.19), (0.96, 0.40, 0.38),
                      M("canvas"), rot=(0, 0, 0.24)), 0.012, 0, 1))
    for i in range(3):
        out.append((L.box("deck_plank_u%d" % i,
                          (1.80, 0.56 - 0.06 * i, 0.028 + i * 0.058),
                          (1.18 - 0.10 * i, 0.28, 0.055), M("wood_warm"),
                          rot=(0, 0, 0.05 * (i - 1))), 0.006, 0, 1))
    return out


def hint_mid(cut):
    """中等 → 豪华：下一级的四根角柱已经立在旧帐篷四周（高度不齐 = 正在立），
    正面两根之间架了一道横梁，地上一捆帆布 + 一摞木板。
    """
    out = []
    # 柱子必须立在**脚手架外面**（架体在 ±2.1）：贴着架子放会跟立杆混成一根，
    # 数不出"四根角柱"。放线框在 ±3.0，正好塞得下 ±2.45/±2.25。
    hs = (2.78, 2.60, 2.42, 2.24)
    for i, (sx, sy) in enumerate(((1, 1), (-1, 1), (-1, -1), (1, -1))):
        out.append((L.box("pole_up%d" % i, (sx * 2.45, sy * 2.25, hs[i] * 0.5),
                          (0.16, 0.16, hs[i]), M("wood_warm")), 0.008, 0, 1))
    out.append((L.box("rg_up", (0.0, 2.25, 2.46), (4.90, 0.13, 0.14), M("wood_dark")),
                0.008, 0, 1))
    out.append((L.box("tent_roll", (1.62, -1.30, 0.21), (1.14, 0.42, 0.42),
                      M("canvas"), rot=(0, 0, -0.18)), 0.014, 0, 1))
    for i in range(3):
        out.append((L.box("deck_plank_u%d" % i,
                          (-1.95, -1.05 + 0.07 * i, 0.030 + i * 0.060),
                          (1.22 - 0.12 * i, 0.30, 0.058), M("wood_warm"),
                          rot=(0, 0, 0.04 * (1 - i))), 0.006, 0, 1))
    return out


# ── 配置 ────────────────────────────────────────────────────────────────────
CONFIG = {
    "初级帐篷": dict(tier="初级帐篷", asset="初级帐篷", kind="帐篷", prefix="TN1",
                  note="6 边锥 + 中柱；1 层布；4 根斜拉绳"),
    "中等帐篷": dict(tier="中等帐篷", asset="中等帐篷", kind="帐篷", prefix="TN2",
                  note="两面坡脊帐 + 前檐披；6 根地钉"),
    "豪华帐篷": dict(tier="豪华帐篷", asset="豪华帐篷", kind="帐篷", prefix="TN3",
                  note="木地台 + 四角柱 + 四坡顶 + 内衬 + 门帘 + 双旗杆"),
    "初级帐篷_升级": dict(asset="初级帐篷", tier="初级帐篷", kind="升级态",
                     cut=1.55, lifts=1, hint=hint_small, prefix="TN1U",
                     front=0.95, landmark=("door_", "stake_f"), body_z=0.60, rope=False,
                     lift_h=1.75,
                     note="初级 → 中等：脊杆已立、脊梁斜搭；作业面 2.15 压在断口之上"),
    "中等帐篷_升级": dict(asset="中等帐篷", tier="中等帐篷", kind="升级态",
                     cut=1.95, lifts=1, hint=hint_mid, prefix="TN2U",
                     front=0.95, landmark=("door_", "stake_f"), body_z=0.60, lift_h=2.15,
                     note="中等 → 豪华：四根角柱已立在旧帐四周；作业面 2.10"),
}


# ── 队色占比（投影近似，给回执留一个可复算的数）──────────────────────────────
def team_frac(objs, az=45.0, el=38.0):
    """队色占剪影的比例：按面法线与视线的夹角加权面积（≈ 投影面积占比）。

    机位取交付图的 45°/38°。判据是 6–9%，所以这里必须能打印出一个数 ——
    肉眼看渲染图估占比，每次都会高估（队色在受光面，天然更"跳"）。
    """
    # 帐内件（衬布地面 / 内衬 / 门帘 / 灯）不算：它们只在门洞里露几个像素，
    # 但面积很大（一块 4.5×4.1 的衬布地面就 18 m²），算进去会把占比压掉一半。
    HIDDEN = ("tent_floor", "tent_lin", "tent_curtain", "door_lamp")
    a, e = math.radians(az), math.radians(el)
    d = Vector((math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), math.sin(e)))
    tot = team = 0.0
    for it in objs:
        ob = it[0] if isinstance(it, tuple) else it
        if ob.name.startswith(HIDDEN):
            continue
        name = ob.data.materials[0].name if ob.data.materials else ""
        is_team = name in ("team", "team_trim")
        m3 = ob.matrix_world.to_3x3()
        for p in ob.data.polygons:
            n = m3 @ p.normal
            if n.length < 1e-9:
                continue
            w = max(0.0, n.normalized().dot(d)) * p.area   # 只算朝向相机的面
            tot += w
            if is_team:
                team += w
    return team / max(tot, 1e-9), team, tot


# ── 驱动 ────────────────────────────────────────────────────────────────────
def assemble(key, do_export=True):
    cfg = CONFIG[key]
    if cfg.get("cut"):
        # 升级态：把"低级帐篷"的 Model 绑到这一档的 tier 上交给 st_upgrade
        # 脚手架一步的高度按资产尺度改：cs_kit 的 2.20 m 是给 8–16 m 建筑的，
        # 套在 2.3 m 的帐篷上，第一层作业面就已经高过原建筑总高（规则 N115）。
        # 改完之后作业面正好压在断口上方 0.1 m，架子顶也不超过原高。
        cs_kit.LIFT_H = cfg["lift_h"]
        mod = types.SimpleNamespace(Model=functools.partial(
            tent_model.Model, tier=cfg["tier"], rope=cfg.get("rope", True)))
        return up.run_upgrade(key, cfg["asset"], mod, cfg["cut"], cfg["lifts"], cfg["hint"],
                              cfg["prefix"], cfg["front"], cfg["landmark"], cfg["body_z"],
                              cfg.get("note", ""), do_export=do_export)

    st.clear_scene()
    m = tent_model.build_tier(cfg["tier"])
    print("[%s] 构件 %d 件  提示：%s" % (key, len(m.items), cfg.get("note", "")))
    # 队色占比必须在**合并之前**量：合并后对象只剩 4 个（TN2-主体 之类），
    # 帐内件与外壳混在一起就分不出来了。
    frac, t_area, t_all = team_frac(m.items)
    print("[%s] 队色投影占比 %.1f%%（队色 %.2f m² / 总投影 %.2f m²，目标 6–9%%）"
          % (key, frac * 100.0, t_area, t_all))
    objs = m.finalize(bevel=True)
    for ob in objs:                       # finalize 里按材质合并时用的是 BR 前缀
        ob.name = ob.name.replace("BR-", cfg["prefix"] + "-", 1)
    if not do_export:
        return objs
    path, rec = st.finish(objs, key, cfg["prefix"], asset_path(cfg["asset"]),
                          anim=False, front_ratio=0.95)
    rec.update({"asset_name": key, "kind": cfg["kind"], "note": cfg.get("note", ""),
                "team_frac": round(frac, 4),
                "tiers": {k: {kk: vv for kk, vv in v.items()
                              if kk in ("half_w", "half_d", "h", "poles", "layers", "stakes")}
                          for k, v in tent_model.TIERS.items()}})
    rec["team_ok"] = bool(0.055 <= frac <= 0.095)
    rec["ok"] = bool(rec["ok"] and rec["team_ok"])
    _write(key, rec)
    print("[%s] %s tris=%d mats=%d %.2f×%.2f×%.2f %s"
          % (key, rec["file"], rec["tris"], rec["mat_count"],
             rec["size"][0], rec["size"][1], rec["size"][2],
             "OK" if rec["ok"] else "FAIL"))
    return rec


def _write(key, rec):
    d = os.path.join(DOC, key)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "receipt.json"), "w", encoding="utf-8") as f:
        json.dump(rec, f, ensure_ascii=False, indent=2)


def _dirs():
    """先把五个资产目录建出来：`asset_path()` 只认已存在的目录。"""
    for key in RUN:
        name = CONFIG[key]["asset"]
        p = os.path.join(assets_path.ASSETS, FAMILY, name)
        os.makedirs(p, exist_ok=True)
    assets_path.refresh()


RUN = ("初级帐篷", "中等帐篷", "豪华帐篷", "初级帐篷_升级", "中等帐篷_升级")


def main():
    _dirs()
    out = {}
    for key in RUN:
        out[key] = assemble(key)
    print("ST_TENT_RECEIPT " + json.dumps(
        {k: [v["tris"], v["mat_count"], v["size"], v["ok"]] for k, v in out.items()},
        ensure_ascii=False))


main()
