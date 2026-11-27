"""cs_check.py —— 建造系统体检：归位一致 / 层缝连续 / 套件与建筑不相交 / 收尾干净。

在 cs_build.build_one 之后跑（同一场景），也可以单独 import 调用。
判据（对齐 docs/建模规则.md 的口径）：
    BVH_CROSS   0    套件与建筑的真实三角形相交
    BAND_GAP    0    层与层之间的缝 > 2 mm
    BOX_TALL    0    收尾帧还留有非零缩放的套件骨
"""
import json

import bpy
from mathutils.bvhtree import BVHTree


def _ev(ob, dg):
    return ob.evaluated_get(dg)


def run(arm, body, site, edges, marks, out_json=None):
    sc = bpy.context.scene
    rep = {}

    # 1) 满场：拆架前一帧（建筑已完、套件全在）
    f_full = max(1, int((marks["dismantle"] - 0.02) * 30))
    sc.frame_set(f_full)
    dg = bpy.context.evaluated_depsgraph_get()
    tb = BVHTree.FromObject(_ev(body, dg), dg, deform=True)
    ts = BVHTree.FromObject(_ev(site, dg), dg, deform=True)
    pairs = tb.overlap(ts)
    rep["BVH_CROSS"] = len(pairs)

    # 2) 层缝：用静置网格（不依赖动画），相邻层 z 接缝
    gaps = []
    me = body.data
    # 层边界来自顶点组的 z 极值
    for i in range(len(edges) - 2):
        g0 = body.vertex_groups[f"band_{i:02d}"].index
        g1 = body.vertex_groups[f"band_{i + 1:02d}"].index
        z0 = [v.co.z for v in me.vertices if any(g.group == g0 for g in v.groups)]
        z1 = [v.co.z for v in me.vertices if any(g.group == g1 for g in v.groups)]
        if z0 and z1:
            gaps.append(round(max(z0) - min(z1), 4))
    rep["BAND_GAP"] = max([abs(g) for g in gaps] or [0])
    rep["BAND_GAPS"] = gaps

    # 3) 收尾干净：套件在地面以上不应再有"有面积的三角形"
    sc.frame_set(int(marks["t_end"] * 30))
    dg = bpy.context.evaluated_depsgraph_get()
    ev = site.evaluated_get(dg)
    me = ev.to_mesh()
    above = 0
    for p in me.polygons:
        if p.center.z > 0.25 and p.area > 1e-6:
            above += 1
    rep["BOX_TALL"] = above
    rep["BOX_LEFT"] = []
    ev.to_mesh_clear()

    # 4) 体量
    body.data.calc_loop_triangles()
    site.data.calc_loop_triangles()
    rep["tri_body"] = len(body.data.loop_triangles)
    rep["tri_site"] = len(site.data.loop_triangles)
    lo = [min(v.co[i] for v in site.data.vertices) for i in range(3)]
    hi = [max(v.co[i] for v in site.data.vertices) for i in range(3)]
    rep["site_lo"] = [round(x, 2) for x in lo]
    rep["site_hi"] = [round(x, 2) for x in hi]
    rep["ok"] = (rep["BVH_CROSS"] == 0 and rep["BAND_GAP"] <= 0.002
                 and rep["BOX_TALL"] == 0)
    if out_json:
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(rep, f, ensure_ascii=False, indent=2)
    print("[check]", json.dumps({k: rep[k] for k in
                                 ("BVH_CROSS", "BAND_GAP", "BOX_TALL", "tri_body",
                                  "tri_site", "ok")}, ensure_ascii=False))
    return rep
