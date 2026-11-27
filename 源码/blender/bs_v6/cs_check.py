"""cs_check.py —— 建造系统 v2 体检。

判据（v2 换了口径：不再有切层，所以没有 BAND_GAP）：
    BODY_RIG     0    建筑本体**没有父级、没有骨架修改器、没有动画**（不许缩放）
    BODY_TRIS    0    本体三角数 / 顶点数与源资产逐项一致（几何没被动过）
    BVH_CROSS    0    套件与建筑的真实三角形相交（满场帧：撤架前一帧）
    BOX_TALL     0    收尾帧地面以上还剩多少有面积的三角形
    SCAF_OVER    0    脚手架顶高 - 建筑高（>0 就是架子比楼还高，抢剪影）
"""
import json

import bpy
from mathutils.bvhtree import BVHTree


def run(arm, body, site, H, marks, src_tri, src_verts, out_json=None):
    sc = bpy.context.scene
    rep = {}

    # 1) 本体不许被任何东西驱动
    mods = [m.type for m in body.modifiers]
    rep["BODY_RIG"] = int(not (body.parent is None
                               and body.animation_data is None
                               and "ARMATURE" not in mods))
    rep["body_parent"] = body.parent.name if body.parent else None
    rep["body_mod"] = mods
    rep["body_anim"] = bool(body.animation_data)

    # 2) 几何逐项一致（"原始尺寸"的硬证据）
    body.data.calc_loop_triangles()
    rep["body_tris"] = len(body.data.loop_triangles)
    rep["body_verts"] = len(body.data.vertices)
    rep["src_tris"] = src_tri
    rep["src_verts"] = src_verts
    rep["BODY_TRIS"] = int(rep["body_tris"] != src_tri or rep["body_verts"] != src_verts)

    # 3) 满场：撤架前一帧（脚手架全在、建筑完整）
    f_full = max(1, int((marks["t_dis0"] - 0.02) * 30))
    sc.frame_set(f_full)
    dg = bpy.context.evaluated_depsgraph_get()
    tb = BVHTree.FromObject(body.evaluated_get(dg), dg, deform=True)
    ts = BVHTree.FromObject(site.evaluated_get(dg), dg, deform=True)
    rep["BVH_CROSS"] = len(tb.overlap(ts))

    # 4) 收尾干净：地面以上不应再有有面积的三角形
    sc.frame_set(int(marks["t_end"] * 30))
    dg = bpy.context.evaluated_depsgraph_get()
    ev = site.evaluated_get(dg)
    me = ev.to_mesh()
    rep["BOX_TALL"] = sum(1 for p in me.polygons
                          if p.center.z > 0.25 and p.area > 1e-6)
    ev.to_mesh_clear()

    # 5) 脚手架不许比楼高（只量 site_scaf_* 的顶点，队色旗杆不算）
    site.data.calc_loop_triangles()
    gi = {g.index for g in site.vertex_groups if g.name.startswith("site_scaf")}
    scaf_z = [v.co.z for v in site.data.vertices if any(g.group in gi for g in v.groups)]
    top = max(scaf_z) if scaf_z else 0.0
    rep["scaf_top"] = round(top, 2)
    rep["SCAF_OVER"] = round(max(0.0, top - H), 3)

    # 6) 显影区间
    rep["reveal_z0"] = marks["z0"]
    rep["reveal_z1"] = round(H, 3)
    rep["tri_body"] = rep["body_tris"]
    rep["tri_site"] = len(site.data.loop_triangles)
    rep["ok"] = (rep["BODY_RIG"] == 0 and rep["BODY_TRIS"] == 0
                 and rep["BVH_CROSS"] == 0 and rep["BOX_TALL"] == 0
                 and rep["SCAF_OVER"] <= 0.01)
    if out_json:
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(rep, f, ensure_ascii=False, indent=2)
    print("[check]", json.dumps(
        {k: rep[k] for k in ("BODY_RIG", "BODY_TRIS", "BVH_CROSS", "BOX_TALL",
                             "SCAF_OVER", "tri_body", "tri_site", "ok")},
        ensure_ascii=False))
    return rep
