"""
bs_clip.py —— 找"穿模"：把每个构件包成 BVH，两两做相交测试。

    python build/bl_rt.py act blender/bs_v6/bs_clip.py

只看"可疑组 vs 其它"（屋面 / 坡棚 / 屋脊 / 楼阁 / 烟囱 / 山墙带 / 旗），
输出相互穿插的构件对与三角形交点数，按严重程度排序。
"""
import importlib
import os
import sys

import bpy
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else r"D:/测试一/blender/bs_v6"
if HERE not in sys.path:
    sys.path.insert(0, HERE)
for mod in ("bslib", "bs_model"):
    if mod in sys.modules:
        importlib.reload(sys.modules[mod])
import bs_model  # noqa: E402

SUSPECT = ("roof", "canopy", "ridge", "cup_", "crest", "ch_", "gable_band", "collar",
           "banner_", "vent_", "fascia", "barge", "rafter", "course", "wing_roof",
           "wing_ridge", "porch_roof", "hood", "flue")
# 同一组内部的交叉属于"故意叠在一起"，不报
SAME = ("roof_1", "roof_-1", "course")


def bvh_of(ob):
    me = ob.data
    mw = ob.matrix_world
    verts = [mw @ v.co for v in me.vertices]
    polys = [tuple(p.vertices) for p in me.polygons]
    return BVHTree.FromPolygons(verts, polys, all_triangles=False)


def main():
    m = bs_model.Model(False).build()
    bpy.context.view_layer.update()
    items = [it[0] for it in m.items]
    print("ITEMS", len(items))
    trees = {}
    for ob in items:
        try:
            trees[ob.name] = bvh_of(ob)
        except Exception as ex:
            print("bvh fail", ob.name, ex)
    hits = []
    for ob in items:
        n = ob.name
        if not any(n.startswith(s) for s in SUSPECT):
            continue
        ta = trees.get(n)
        if ta is None:
            continue
        for other in items:
            on = other.name
            if on == n or on in n or n in on:
                continue
            tb = trees.get(on)
            if tb is None:
                continue
            try:
                ov = ta.overlap(tb)
            except Exception:
                continue
            if ov:
                hits.append((len(ov), n, on))
    hits.sort(reverse=True)
    print("CLIP_PAIRS", len(hits))
    for cnt, a, b in hits[:70]:
        print("%4d  %-24s <-> %s" % (cnt, a, b))
    print("DONE")


main()
