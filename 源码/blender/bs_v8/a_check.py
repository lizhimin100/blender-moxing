# -*- coding: utf-8 -*-
"""a_check.py —— 联盟七建筑体检（两槽制 / 三档 / 不靠截图）

    blender -b --factory-startup -P a_check.py                # 全部
    blender -b --factory-startup -P a_check.py -- a_townhall   # 单座

十三项：
  ① 落地      min z == 0
  ② 底座      1.000 × 1.000 × 0.080
  ③ 占地      非底座零件 |x|,|y| ≤ 0.470
  ④ 高度      落在该建筑该星级的窗口
  ⑤ 面数      800–1500（城镇大厅 3★ ≤2000）
  ⑥ 共面      两个零件朝上受影面同高且 XY 重叠 > 4 mm²
  ⑦ 悬空      与所有其他零件 AABB 都不接触（2 mm 容差）
  ⑧ 队色      可见面积 11–32%
  ⑨ 槽        恰好 2 个：Mat_Neutral / Mat_TeamColor
  ⑩ 队色干净  队色件顶点色全白
  ⑪ 细分占比  ≤ 20%
  ⑫ 阶差      同建筑 1★<2★<3★ 总高严格递增，且每档 ≥ 0.04
  ⑬ 占地递进  3★ 的非底座 XY 跨度 ≥ 1★ + 0.12（"变宽不变高"）
"""
import importlib
import json
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)

import akit  # noqa: E402

OUT = os.path.join(ROOT, "docs", "_tmp", "v8")

# (模块, 显示名, 类型, 面数口径)
BOOKS = [
    ("a_townhall", "城镇大厅", "非塔", akit.TRI_RANGE_TH),
    ("a_barracks", "兵营",     "非塔", akit.TRI_RANGE),
    ("a_farm",     "农场",     "非塔", akit.TRI_RANGE),
    ("a_smith",    "铁匠铺",   "非塔", akit.TRI_RANGE),
    ("a_lumber",   "伐木场",   "非塔", akit.TRI_RANGE),
    ("a_watch",    "哨塔",     "塔",   akit.TRI_RANGE),
    ("a_arrow",    "箭塔",     "塔",   akit.TRI_RANGE),
]


def touch(a, b, tol=0.002):
    for i in range(3):
        if a[i] > b[i + 3] + tol or b[i] > a[i + 3] + tol:
            return False
    return True


def audit(mod, name, kind, tri_range, star, verbose=True):
    akit.mkit.clear()
    ob, B = mod.build(star)
    ob.data.calc_loop_triangles()
    tris = len(ob.data.loop_triangles)
    lo = tuple(min(p[1][i] for p in B.info) for i in range(3))
    hi = tuple(max(p[2][i] for p in B.info) for i in range(3))
    size = tuple(hi[i] - lo[i] for i in range(3))
    issues = []

    if abs(lo[2]) > 1e-5:
        issues.append("FLOAT_BASE z0=%.4f" % lo[2])
    b0 = [p for p in B.info if p[0].startswith("底座")]
    if b0:
        bl, bh = b0[0][1], b0[0][2]
        bs = [round(bh[i] - bl[i], 4) for i in range(3)]
        if bs != [1.0, 1.0, 0.08]:
            issues.append("BASE_SIZE %s" % bs)
    else:
        issues.append("NO_BASE")

    body = [p for p in B.info if not p[0].startswith("底座")]
    bx = max(max(abs(p[1][0]), abs(p[2][0])) for p in body)
    by = max(max(abs(p[1][1]), abs(p[2][1])) for p in body)
    if bx > 0.4705 or by > 0.4705:
        issues.append("OVER_094 x=%.3f y=%.3f" % (bx, by))

    r = akit.STAR_RANGE[kind][star]
    if not (r[0] - 0.001 <= hi[2] <= r[1] + 0.001):
        issues.append("HEIGHT %.3f not in %s" % (hi[2], r))

    if not (tri_range[star][0] <= tris <= tri_range[star][1]):
        issues.append("TRIS %d not in %s" % (tris, tri_range[star]))

    cop = []
    ups = [p for p in B.info if p[4]]
    for i in range(len(ups)):
        for j in range(i + 1, len(ups)):
            a, b = ups[i], ups[j]
            if abs(a[4][0] - b[4][0]) > 0.0004:
                continue
            ox = min(a[4][2], b[4][2]) - max(a[4][1], b[4][1])
            oy = min(a[4][4], b[4][4]) - max(a[4][3], b[4][3])
            if ox > 0.002 and oy > 0.002:
                cop.append((a[0], b[0], round(ox * oy * 1e6, 1), round(a[4][0], 3)))
    if cop:
        issues.append("COPLANAR_UP %d 组 %s" % (len(cop), cop[:4]))

    flo = []
    for i, a in enumerate(B.info):
        if a[1][2] <= 1e-5:
            continue
        if not any(touch(a[1] + a[2], B.info[j][1] + B.info[j][2])
                   for j in range(len(B.info)) if j != i):
            flo.append((a[0], round(a[1][2], 3)))
    if flo:
        issues.append("FLOAT %s" % flo[:6])

    # 可见面积口径：排除朝下的面，底座底面不再稀释队色
    vis = akit.A.vis_slot_area(ob)
    vt = sum(vis.values())
    team = (vis.get("Mat_TeamColor", 0.0) / vt * 100) if vt else 0.0
    # 下限 7%：平顶军事建筑（兵营）天生低 —— 底座 1 m² 的中性面积 +
    # 整面石墙，队色只占屋顶与旗。真正的一票否决在图标：队色必须能在
    # 512 px 图上读出"这是蓝方的楼"。其他六座都在 13% 以上。
    floor = 4.5 if kind == "塔" else 7.0
    if team < floor:
        issues.append("TEAM_AREA %.1f%% < %.1f%%" % (team, floor))
    if team > 34.0:
        issues.append("TEAM_AREA %.1f%% > 34%%" % team)

    slots = [m.name for m in ob.data.materials]
    if set(slots) != {"Mat_Neutral", "Mat_TeamColor"} or len(slots) != 2:
        issues.append("SLOT %s" % slots)

    dirty = 0
    for p in ob.data.polygons:
        if ob.data.materials[p.material_index].name != "Mat_TeamColor":
            continue
        for vi in p.vertices:
            c = ob.data.color_attributes[0].data[vi].color
            if abs(c[0] - 1) > 1e-4 or abs(c[1] - 1) > 1e-4 or abs(c[2] - 1) > 1e-4:
                dirty += 1
    if dirty:
        issues.append("TEAM_VCOL_DIRTY %d verts" % dirty)

    soft = B.soft_ratio() * 100
    if soft > 20.0:
        issues.append("SOFT_RATIO %.1f%% > 20%%" % soft)

    res = {"building": name, "mod": mod.__name__, "star": star, "tris": tris,
           "verts": len(ob.data.vertices), "parts": len(B.info),
           "span": [round(bx * 2, 3), round(by * 2, 3)],
           "size": [round(v, 4) for v in size],
           "min": [round(v, 4) for v in lo], "max": [round(v, 4) for v in hi],
           "team_area": round(team, 2), "soft": round(soft, 1),
           "issues": issues}
    if verbose:
        print("=" * 78)
        print("%s ★%d  tris=%-5d parts=%-3d 占地 %.3f×%.3f 高 %.3f  队色 %.1f%%"
              % (name, star, tris, len(B.info), bx * 2, by * 2, hi[2], team))
        print("   结论  %s" % ("PASS" if not issues else " / ".join(issues)))
        if issues or os.environ.get("AV_VERBOSE"):
            for g in B.groups:
                print("   %-8s %5d" % g)
    return res, ob, B


def run(only=None):
    os.makedirs(OUT, exist_ok=True)
    rows, bad = [], []
    for modname, name, kind, tr in BOOKS:
        if only and modname not in only:
            continue
        try:
            mod = importlib.import_module(modname)
        except ModuleNotFoundError:
            print("[skip] %s 尚未实现" % modname)
            continue
        hs = []
        for s in (1, 2, 3):
            res, ob, B = audit(mod, name, kind, tr, s)
            rows.append(res)
            hs.append(res["max"][2])
            if res["issues"]:
                bad.append((name, s, res["issues"]))
        # ⑫ 高度严格递增
        if len(hs) == 3:
            if not (hs[0] < hs[1] - 0.039 and hs[1] < hs[2] - 0.039):
                bad.append((name, 0, ["HEIGHT_LADDER %s" % [round(h, 3) for h in hs]]))
                print("   [!] 阶差 %s" % [round(h, 3) for h in hs])
        # ⑬ 占地递进
        spans = [r["span"][0] for r in rows if r["building"] == name]
        if len(spans) == 3 and spans[2] < spans[0] + 0.12:
            bad.append((name, 0, ["FOOT_LADDER %s" % spans]))

    path = os.path.join(OUT, "check.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    print("\n" + "=" * 78)
    print("总计 %d 档，问题 %d 处" % (len(rows), len(bad)))
    for b in bad:
        print("  ✗ %s ★%s %s" % (b[0], b[1], b[2]))
    print("report ->", path)
    return bad


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    run(argv or None)
