"""_probe_state2.py —— 高件清单（一次性，可删）"""
import sys

import bpy

HERE = r"D:/测试一/blender/bs_v6"
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import th_model, wt_model, br_model, lm_model, ms_model, sw_model, bs_model  # noqa


def probe(name, mod, topn=14):
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    m = mod.Model(False, unwrap=False).build()
    rows = []
    for it in m.items:
        ob = it[0]
        zz = [(ob.matrix_world @ v.co).z for v in ob.data.vertices]
        if not zz:
            continue
        rows.append((max(zz), min(zz), ob.name))
    rows.sort(reverse=True)
    print("== %s ==  (top %d)" % (name, topn))
    for hi, lo, nm in rows[:topn]:
        print("   %.2f .. %.2f  %s" % (lo, hi, nm))


probe("城镇大厅", th_model, 18)
probe("哨塔", wt_model, 12)
probe("神秘圣地", ms_model, 10)
