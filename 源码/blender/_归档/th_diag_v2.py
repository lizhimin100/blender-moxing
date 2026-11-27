import importlib, sys
sys.path.insert(0, r"D:/测试一/blender/bs_v6")
for m in ("bslib","br_model","th_model"):
    if m in sys.modules: importlib.reload(sys.modules[m])
import th_model
for sm in (False, True):
    objs, st = th_model.build(smooth=sm, unwrap=True)
    print("SMOOTH" if sm else "LOW", st)
    bpy.ops.object.select_all(action="DESELECT")
    lo = [min(v.co[i] for o in objs for v in o.data.vertices) for i in range(3)]
    hi = [max(v.co[i] for o in objs for v in o.data.vertices) for i in range(3)]
    print("BBOX", [round(x,2) for x in lo], [round(x,2) for x in hi])
