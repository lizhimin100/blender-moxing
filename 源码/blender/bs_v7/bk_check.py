# -*- coding: utf-8 -*-
"""bk_check.py —— 兵营体检（两槽制 / 800–1500 tri / 不靠截图）

十项，全过才许导出：
  ① 落地      min z == 0，底座 1.000×1.000×0.080
  ② 占地      除底座外所有零件 |x|,|y| <= 0.48
  ③ 高度      落在星级区间
  ④ 面数      800–1500（全局规范硬线）
  ⑤ 共面      两个零件顶面同高且 XY 重叠 > 4 mm²
  ⑥ 悬空      零件与所有其他零件 AABB 都不接触（2 mm 容差）
  ⑦ 队色      可见面积 10–28%
  ⑧ 细分      细分件 tri 占比 ≤ 20%
  ⑨ 材质槽    恰好 2 个：Mat_Neutral / Mat_TeamColor
  ⑩ 队色干净  Mat_TeamColor 的顶点色必须全白（否则换阵营会相乘变色）

用法：blender -b --factory-startup -P bk_check.py
"""
import json
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)

import mkit          # noqa: E402
import bk_model       # noqa: E402

OUT = os.path.join(ROOT, "docs", "_tmp", "v7")


def touch(a, b, tol=0.002):
    for i in range(3):
        if a[i] > b[i + 3] + tol or b[i] > a[i + 3] + tol:
            return False
    return True


def audit(star, verbose=True, pal=None):
    mkit.clear()
    ob, B = bk_model.build(star, pal=pal)
    ob.data.calc_loop_triangles()
    tris = len(ob.data.loop_triangles)
    lo = tuple(min(p[1][i] for p in B.info) for i in range(3))
    hi = tuple(max(p[2][i] for p in B.info) for i in range(3))
    size = tuple(hi[i] - lo[i] for i in range(3))

    issues = []

    # ① 落地 + 底座尺寸
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

    # ② 占地
    body = [p for p in B.info if not p[0].startswith("底座")]
    bx = max(max(abs(p[1][0]), abs(p[2][0])) for p in body)
    by = max(max(abs(p[1][1]), abs(p[2][1])) for p in body)
    if bx > 0.4805 or by > 0.4805:
        issues.append("OVER_096 x=%.3f y=%.3f" % (bx, by))

    # ③ 高度
    r = bk_model.STAR_RANGE[star]
    if not (r[0] - 0.001 <= hi[2] <= r[1] + 0.001):
        issues.append("HEIGHT %.3f not in %s" % (hi[2], r))

    # ④ 面数
    tr = bk_model.TRI_RANGE[star]
    if not (tr[0] <= tris <= tr[1]):
        issues.append("TRIS %d not in %s" % (tris, tr))

    # ⑤ 共面
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
        issues.append("COPLANAR_UP %d 组 %s" % (len(cop), cop[:5]))

    # ⑥ 悬空
    flo = []
    for i, a in enumerate(B.info):
        if a[1][2] <= 1e-5:
            continue
        if not any(touch((a[1] + a[2]), (B.info[j][1] + B.info[j][2]))
                   for j in range(len(B.info)) if j != i):
            flo.append((a[0], round(a[1][2], 3)))
    if flo:
        issues.append("FLOAT %s" % flo[:6])

    # ⑦ 队色
    team = B.team_area() * 100
    if team < 10.0:
        issues.append("TEAM_AREA %.1f%% < 10%%" % team)
    if team > 28.0:
        issues.append("TEAM_AREA %.1f%% > 28%%" % team)

    # ⑧ 细分
    soft = B.soft_ratio() * 100
    if soft > 20.0:
        issues.append("SOFT_RATIO %.1f%% > 20%%" % soft)

    # ⑨ 材质槽
    slots = [m.name for m in ob.data.materials]
    if set(slots) != {"Mat_Neutral", "Mat_TeamColor"} or len(slots) != 2:
        issues.append("SLOT %s" % slots)

    # ⑩ 队色顶点色必须全白
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

    res = {"star": star, "tris": tris, "verts": len(ob.data.vertices),
           "bbox": [round(v, 4) for v in size],
           "min": [round(v, 4) for v in lo], "max": [round(v, 4) for v in hi],
           "parts": len(B.info), "slots": slots,
           "team_area": round(team, 2), "soft": round(soft, 1),
           "slot_area": {k: round(v * 100, 1) for k, v in B.slot_area().items()},
           "issues": issues}
    if verbose:
        print("=" * 70)
        print("★%d  tris=%d  verts=%d  parts=%d  队色=%.1f%%  细分=%.1f%%"
              % (star, tris, len(ob.data.vertices), len(B.info), team, soft))
        print("   bbox  %.3f x %.3f x %.3f   z0=%.4f" % (size[0], size[1], size[2], lo[2]))
        print("   材质  %s  面积 %s" % (slots, res["slot_area"]))
        print("   结论  %s" % ("PASS" if not issues else " / ".join(issues)))
        for g in getattr(B, "groups", []):
            print("   %-10s %5d" % g)
        top = sorted(B.info, key=lambda p: -p[3])[:8]
        print("   最重零件: " + ", ".join("%s%d" % (p[0], p[3]) for p in top))
    return res, ob, B


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    allres = []
    for s in (1, 2, 3):
        rr, ob, B = audit(s)
        allres.append(rr)
    with open(os.path.join(OUT, "bk_check.json"), "w", encoding="utf-8") as f:
        json.dump(allres, f, ensure_ascii=False, indent=2)
    print("\nreport ->", os.path.join(OUT, "bk_check.json"))
