"""_probe_up.py —— 升级态构件探针（一次性，可删）"""
import sys

import bpy

HERE = r"D:/测试一/blender/bs_v6"
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import st_kit as st
import st_upgrade as su

key = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "哨塔_升级"
cfg = su.CONFIG[key]
mod = __import__(cfg["mod"])
st.clear_scene()
m = mod.Model(False, unwrap=False).build()
items = list(m.items)
st.bake_transforms(items)
kept, caps, removed = st.cut_items(items, cfg["cut"])
chunks = st.raw_chunks(caps)
hints = cfg["hint"](cfg["cut"])
bpy.context.view_layer.update()
allit = kept + caps + chunks + hints
rows = []
for it in allit:
    ob = it[0]
    zs = [(ob.matrix_world @ v.co).z for v in ob.data.vertices]
    xs = [(ob.matrix_world @ v.co).x for v in ob.data.vertices]
    ys = [(ob.matrix_world @ v.co).y for v in ob.data.vertices]
    if not zs:
        continue
    if max(zs) > cfg["cut"] + 0.05:
        rows.append((max(zs), min(zs), max(xs) - min(xs), max(ys) - min(ys), ob.name))
rows.sort(reverse=True)
print("PROBE %s  cut=%.2f  above-cut items=%d" % (key, cfg["cut"], len(rows)))
for hi, lo, dx, dy, nm in rows[:40]:
    print("  z %.2f..%.2f  %.2fx%.2f  %s" % (lo, hi, dx, dy, nm))

print("CAPS:")
for it in caps:
    ob = it[0]
    vs = ob.data.vertices
    xs = [v.co.x for v in vs]; ys = [v.co.y for v in vs]; zs = [v.co.z for v in vs]
    print("  %-22s nv=%2d  %.2fx%.2f  z=%.2f  area=%.2f" % (
        ob.name, len(vs), max(xs)-min(xs), max(ys)-min(ys), zs[0],
        (max(xs)-min(xs))*(max(ys)-min(ys))))
