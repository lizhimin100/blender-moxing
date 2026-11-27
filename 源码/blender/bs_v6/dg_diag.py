import importlib, sys
import bpy
HERE = r"D:/测试一/blender/bs_v6"
if HERE not in sys.path: sys.path.insert(0, HERE)
for m in ("bslib","br_model","wt_model","dl_kit","dl_parts","dg_layout","dg_model"):
    if m in sys.modules: importlib.reload(sys.modules[m])
import dg_model
for ob in list(bpy.data.objects):
    bpy.data.objects.remove(ob, do_unlink=True)
m = dg_model.Model(False, unwrap=False).build()
bpy.context.view_layer.update()
bad = []
for (ob, bev, sub, seg) in m.items:
    zs = [(ob.matrix_world @ v.co).z for v in ob.data.vertices]
    if zs and min(zs) < -0.002:
        bad.append((ob.name, round(min(zs), 3), round(max(zs), 3)))
print("BELOW", len(bad))
for b in bad[:12]:
    print("   ", b)
print("DIAG_OK")
