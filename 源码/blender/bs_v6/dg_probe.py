"""dg_probe.py —— 只在桥接里跑：清场 → 建低模 → 打印统计（不导出、不渲染）"""
import importlib
import sys

import bpy

HERE = r"D:/测试一/blender/bs_v6"
if HERE not in sys.path:
    sys.path.insert(0, HERE)
for m in ("bslib", "br_model", "wt_model", "dl_kit", "dl_parts", "dg_layout", "dg_model"):
    if m in sys.modules:
        importlib.reload(sys.modules[m])

import dg_model  # noqa: E402

for ob in list(bpy.data.objects):
    bpy.data.objects.remove(ob, do_unlink=True)
for blk in (bpy.data.meshes, bpy.data.materials):
    for it in list(blk):
        if it.users == 0:
            blk.remove(it)

m = dg_model.Model(False, unwrap=False).build()
print("ITEMS", len(m.items))

# 落地的都列出来：min z 明显 <0 的、或者 bbox 顶得离谱的
bad = []
for (ob, bev, sub, seg) in m.items:
    zs = [(ob.matrix_world @ v.co).z for v in ob.data.vertices]
    if zs and min(zs) < -0.002:
        bad.append((ob.name, round(min(zs), 4), round(max(zs), 3)))
print("BELOW_ZERO", len(bad))
for b in bad[:30]:
    print("   ", b)

objs, st = dg_model.build(smooth=False, unwrap=False, bevel=False)
print("STATS", st)
lo = [min(min((ob.matrix_world @ v.co)[i] for v in ob.data.vertices) for ob in objs)
      for i in range(3)]
hi = [max(max((ob.matrix_world @ v.co)[i] for v in ob.data.vertices) for ob in objs)
      for i in range(3)]
print("BBOX", [round(v, 3) for v in lo], [round(v, 3) for v in hi],
      "SIZE", [round(hi[i] - lo[i], 3) for i in range(3)])
print("DG_PROBE_OK")
