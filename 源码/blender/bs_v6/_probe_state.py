"""_probe_state.py —— 量体探针：各建筑总高 / 各层标高 / 部件数（一次性，可删）"""
import importlib
import sys

import bpy

HERE = r"D:/测试一/blender/bs_v6"
if HERE not in sys.path:
    sys.path.insert(0, HERE)
for m in ("bslib", "br_model", "th_model", "wt_model", "br_model", "lm_model",
          "ms_model", "sw_model", "bs_model"):
    if m in sys.modules:
        importlib.reload(sys.modules[m])
import bs_model, br_model, th_model, wt_model, lm_model, ms_model, sw_model  # noqa


def probe(name, mod):
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    m = mod.Model(False, unwrap=False).build()
    items = m.items
    zs = []
    for it in items:
        ob = it[0]
        for v in ob.data.vertices:
            p = ob.matrix_world @ v.co
            zs.append(p.z)
    tris = 0
    for it in items:
        it[0].data.calc_loop_triangles()
        tris += len(it[0].data.loop_triangles)
    print("PROBE %s items=%d tris=%d zmax=%.3f zmin=%.3f" %
          (name, len(items), tris, max(zs), min(zs)))
    # 高度直方图：每个 1 m 内有多少构件完全高于该层
    import collections
    lo = collections.Counter()
    for it in items:
        ob = it[0]
        zz = [(ob.matrix_world @ v.co).z for v in ob.data.vertices]
        lo[int(max(zz))] += 1
    top = sorted(lo.items())
    print("   zmax hist:", top[-8:])


for nm, md in (("城镇大厅", th_model), ("哨塔", wt_model), ("兵营", br_model),
               ("伐木场", lm_model), ("神秘圣地", ms_model), ("蒸汽车坊", sw_model),
               ("铁匠铺", bs_model)):
    probe(nm, md)
